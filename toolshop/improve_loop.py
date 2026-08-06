"""Iterative Improvement Loop (B9).

Runs an iterative process to improve lyrics by identifying the weakest
quality component (Structural, Rhyme, Lexical, Repetition) using
``ai_scorer.score_lyrics()`` and suggesting improvements based on other
internal modules.

Internal dependencies (``ai_scorer``, ``structure_template``,
``scheme_checker``) are built in parallel — imports use try/except fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH


def _import_scorer():
    """Import ai_scorer with fallback."""
    try:
        from toolshop.ai_scorer import score_lyrics
        return score_lyrics
    except ImportError:
        return None


def _import_structure_template():
    """Import structure_template with fallback."""
    try:
        from toolshop.structure_template import generate_template
        return generate_template
    except ImportError:
        return None


def _import_scheme_checker():
    """Import scheme_checker with fallback."""
    try:
        from toolshop.scheme_checker import check_scheme
        return check_scheme
    except ImportError:
        return None


def _identify_weakest(
    components: Dict[str, Any],
) -> str:
    """Identify the weakest quality component.

    Args:
        components: Dict from ai_scorer with keys 'structural', 'rhyme',
            'lexical', 'repetition', each containing a 'score' field.

    Returns:
        Component name with the lowest score.
    """
    scores = {}
    for name in ("structural", "rhyme", "lexical", "repetition"):
        comp = components.get(name, {})
        if isinstance(comp, dict):
            scores[name] = comp.get("score", 0)
        else:
            scores[name] = 0

    return min(scores, key=scores.get)


def _generate_suggestions(
    weakest: str,
    input_path: Path,
    cohort: str,
    db_path: Path,
    score_result: Dict[str, Any],
) -> List[str]:
    """Generate improvement suggestions for the weakest component.

    Args:
        weakest: Name of the weakest component.
        input_path: Path to current lyrics file.
        cohort: Genre cohort.
        db_path: Database path.
        score_result: Full score dict from ai_scorer.

    Returns:
        List of suggestion strings for human review.
    """
    suggestions: List[str] = []

    if weakest == "structural":
        gen_template = _import_structure_template()
        if gen_template is not None:
            tmpl = gen_template(cohort=cohort, db_path=db_path)
            sections = tmpl.get("sections", [])
            suggestions.append(
                f"Structural template for {cohort} "
                f"({tmpl.get('total_lines', 0)} lines, "
                f"{len(sections)} sections):"
            )
            for sec in sections:
                suggestions.append(
                    f"  - {sec.get('type', '?')}: "
                    f"{sec.get('lines', 0)} lines, "
                    f"rhyme scheme {sec.get('rhyme_scheme', 'N/A')}"
                )
        else:
            suggestions.append(
                "structural: structure_template module not available. "
                "Consider adjusting section count to 6-8 for "
                f"{cohort} cohort."
            )

    elif weakest == "rhyme":
        check_scheme = _import_scheme_checker()
        if check_scheme is not None:
            scheme_result = check_scheme(
                input_path=input_path, db_path=db_path
            )
            for sec in scheme_result.get("sections", []):
                broken = sec.get("broken_lines", [])
                fixes = sec.get("fixes", [])
                if broken:
                    suggestions.append(
                        f"Rhyme issue in {sec.get('type', '?')}: "
                        f"{len(broken)} broken line(s)"
                    )
                    for fix in fixes[:3]:
                        suggestions.append(f"  Fix: {fix}")
                else:
                    suggestions.append(
                        f"Rhyme OK in {sec.get('type', '?')}: "
                        f"scheme {sec.get('detected_scheme', 'N/A')}"
                    )
        else:
            suggestions.append(
                "rhyme: scheme_checker module not available. "
                "Review end-rhyme consistency in each section."
            )

    elif weakest == "lexical":
        comp = score_result.get("components", {}).get("lexical", {})
        ttr = comp.get("ttr", 0) if isinstance(comp, dict) else 0
        if ttr > 0.55:
            suggestions.append(
                f"lexical: TTR={ttr:.3f} is high. "
                "Reduce vocabulary variety — repeat key words for emphasis. "
                "Aim for TTR 0.40-0.50 in rap lyrics."
            )
        elif ttr < 0.35:
            suggestions.append(
                f"lexical: TTR={ttr:.3f} is low. "
                "Add vocabulary variety — use synonyms, metaphors. "
                "Aim for TTR 0.40-0.50 in rap lyrics."
            )
        else:
            suggestions.append(
                f"lexical: TTR={ttr:.3f} is in range. "
                "Focus on word choice quality over variety."
            )

    elif weakest == "repetition":
        comp = score_result.get("components", {}).get("repetition", {})
        hook_count = comp.get("hook_count", 0) if isinstance(comp, dict) else 0
        suggestions.append(
            f"repetition: hook_count={hook_count}. "
            "Ensure the hook/chorus is repeated 2-3 times. "
            "Vary verse content while keeping the hook consistent."
        )

    return suggestions


def _read_revised_input(input_path: Path) -> str:
    """Read revised input from file or stdin.

    If the file has been modified, reads the file. Otherwise, prompts
    the user to paste revised lyrics via stdin.
    """
    try:
        return Path(input_path).read_text(encoding="utf-8")
    except Exception:
        print("Could not read file. Paste revised lyrics (Ctrl+D to finish):")
        lines = sys.stdin.readlines()
        return "".join(lines)


def improve_loop(
    input_path: Path,
    cohort: str,
    iterations: int = 3,
    target_score: int = 65,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run an iterative improvement loop on lyrics.

    Args:
        input_path: Path to the lyrics text file.
        cohort: Genre cohort (``drill_trap`` or ``pop``).
        iterations: Maximum number of improvement iterations.
        target_score: Stop when overall score reaches this value.
        db_path: Database path. Defaults to ``DEFAULT_DB_PATH``.

    Returns:
        Dict with ``baseline_score``, ``iterations`` (list of per-iteration
        dicts with score, weakest_component, suggestions, delta), and
        ``final_score``.
    """
    score_lyrics = _import_scorer()
    if score_lyrics is None:
        return {
            "error": "ai_scorer module not available. "
                     "It is being built in parallel.",
        }

    db = Path(db_path) if db_path else DEFAULT_DB_PATH

    # Baseline score
    baseline = score_lyrics(
        input_path=input_path, cohort=cohort, db_path=db
    )
    baseline_score = baseline.get("overall_score", 0)
    current_score = baseline_score

    print(f"\n=== Iterative Improvement Loop ===")
    print(f"Baseline score: {baseline_score}")
    print(f"Target: {target_score} | Max iterations: {iterations}")

    history: List[Dict[str, Any]] = []

    for i in range(1, iterations + 1):
        print(f"\n--- Iteration {i}/{iterations} ---")

        if current_score >= target_score:
            print(f"Target score {target_score} reached. Stopping.")
            break

        components = baseline.get("components", {})
        weakest = _identify_weakest(components)
        print(f"Weakest component: {weakest}")

        suggestions = _generate_suggestions(
            weakest=weakest,
            input_path=input_path,
            cohort=cohort,
            db_path=db,
            score_result=baseline,
        )
        print("Suggestions:")
        for s in suggestions:
            print(f"  {s}")

        # Accept revised input
        print(
            f"\nEdit {input_path} with the suggestions above, "
            "then press Enter to continue (or type 'skip' to stop)..."
        )
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            user_input = "skip"

        if user_input.lower() == "skip":
            print("Skipping remaining iterations.")
            break

        # Re-read and re-score
        _read_revised_input(input_path)
        revised = score_lyrics(
            input_path=input_path, cohort=cohort, db_path=db
        )
        revised_score = revised.get("overall_score", 0)
        delta = revised_score - current_score

        print(f"Revised score: {revised_score} (delta: {delta:+d})")

        history.append({
            "iteration": i,
            "score": revised_score,
            "weakest_component": weakest,
            "suggestions": suggestions,
            "delta": delta,
        })

        baseline = revised
        current_score = revised_score

    print(f"\n=== Loop Complete ===")
    print(f"Baseline: {baseline_score} → Final: {current_score}")

    return {
        "baseline_score": baseline_score,
        "iterations": history,
        "final_score": current_score,
        "target_score": target_score,
        "target_reached": current_score >= target_score,
    }
