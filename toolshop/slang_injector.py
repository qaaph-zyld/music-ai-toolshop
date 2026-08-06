"""Slang injection post-processor for AI-generated lyrics.

Reads plain-text lyrics, queries the ``slang_terms`` table for
cohort-distinctive slang, and replaces generic words with slang
equivalents to approach a target slang density.

Usage::

    from toolshop.slang_injector import inject_slang
    result = inject_slang(Path("ai_lyrics.txt"), cohort="drill_trap", density=0.05)
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyrics_analyzer import _tokenize
from toolshop.lyricsdb import DEFAULT_DB_PATH, normalize_text

# Cohort → distinctiveness filter direction.
# drill_trap: positive distinctiveness (drill-distinctive terms)
# pop: negative distinctiveness (pop-distinctive terms)
_COHORT_FILTERS: Dict[str, Tuple[str, float]] = {
    "drill_trap": (">", 0.5),
    "pop": ("<", -0.5),
}

# Common stopwords / function words that should never be replaced.
_STOPWORDS = frozenset(
    "i da na sa za u je su se ne to odo be od do po ko ni ti mi on ona "
    "ono oni one mi vi oni njih njo nju njega nje njima njima te me "
    "the a an and or but in on at to for of is are was were be been "
    "this that these those it its my your his her our their "
    "not no yes very just so too also".split()
)


def _load_slang_terms(
    conn: sqlite3.Connection, cohort: str, limit: int = 50
) -> List[Dict[str, Any]]:
    """Load cohort-distinctive slang terms from the database.

    Uses the same distinctiveness logic as ``lexicon.get_slang_terms``:
    positive distinctiveness = drill-distinctive, negative = pop-distinctive.
    """
    op, threshold = _COHORT_FILTERS.get(cohort, (">", 0.5))

    query = (
        f"SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness "
        f"FROM slang_terms "
        f"WHERE distinctiveness {op} ? "
        f"ORDER BY abs(distinctiveness) DESC "
        f"LIMIT ?"
    )

    rows = conn.execute(query, (threshold, limit)).fetchall()
    return [
        {
            "form": r[0],
            "lemma": r[1],
            "freq": r[2],
            "drill_freq": r[3],
            "pop_freq": r[4],
            "distinctiveness": r[5],
        }
        for r in rows
    ]


def _is_slang_term(word: str, slang_forms: set[str]) -> bool:
    """Check if a word is already a slang term."""
    return word.lower() in slang_forms


def _find_candidates(
    lines: List[str],
    slang_terms: List[Dict[str, Any]],
    slang_forms: set[str],
    density: float,
) -> List[Dict[str, Any]]:
    """Find replacement candidates in the input text.

    Strategy: identify non-slang, non-stopword words whose length matches
    a slang term.  Prioritize replacements by distinctiveness (higher = better).
    """
    # Build slang term lookup by word length for quick matching
    slang_by_length: Dict[int, List[Dict[str, Any]]] = {}
    for term in slang_terms:
        length = len(term["form"])
        slang_by_length.setdefault(length, []).append(term)

    # Sort each length bucket by distinctiveness (most distinctive first)
    for bucket in slang_by_length.values():
        bucket.sort(key=lambda t: abs(t["distinctiveness"]), reverse=True)

    candidates: List[Dict[str, Any]] = []
    total_tokens = 0
    slang_count = 0

    for line_idx, line in enumerate(lines):
        words = re.findall(r"\b\w+\b", line)
        total_tokens += len(words)

        for word_pos, word in enumerate(words):
            wl = word.lower()
            if wl in _STOPWORDS:
                continue
            if _is_slang_term(wl, slang_forms):
                slang_count += 1
                continue

            # Check if there's a slang term of the same length
            bucket = slang_by_length.get(len(word), [])
            if not bucket:
                # Try ±1 length tolerance
                for delta in (-1, 1):
                    bucket = slang_by_length.get(len(word) + delta, [])
                    if bucket:
                        break

            if bucket:
                best_term = bucket[0]
                candidates.append({
                    "line": line_idx,
                    "word_pos": word_pos,
                    "original": word,
                    "replacement": best_term["form"],
                    "distinctiveness": best_term["distinctiveness"],
                })

    # Calculate how many injections we need to hit target density
    if total_tokens == 0:
        return []

    current_density = slang_count / total_tokens
    target_count = int(density * total_tokens) - slang_count
    if target_count <= 0:
        return []

    # Limit candidates to what we need, prioritizing highest distinctiveness
    candidates.sort(key=lambda c: abs(c["distinctiveness"]), reverse=True)
    return candidates[:target_count]


def _apply_replacements(
    lines: List[str],
    candidates: List[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Apply replacements to lines and return (modified_text, injections_log).

    Replacements preserve the original word's position in the line.
    """
    # Group candidates by line
    by_line: Dict[int, List[Dict[str, Any]]] = {}
    for c in candidates:
        by_line.setdefault(c["line"], []).append(c)

    modified_lines: List[str] = []
    injections: List[Dict[str, Any]] = []

    for line_idx, line in enumerate(lines):
        if line_idx not in by_line:
            modified_lines.append(line)
            continue

        # Sort replacements right-to-left to preserve positions
        line_candidates = sorted(
            by_line[line_idx], key=lambda c: c["word_pos"], reverse=True
        )

        words = re.findall(r"\b\w+\b", line)
        for c in line_candidates:
            if c["word_pos"] < len(words):
                original_word = words[c["word_pos"]]
                # Preserve case: if original was capitalized, capitalize replacement
                replacement = c["replacement"]
                if original_word[0].isupper():
                    replacement = replacement.capitalize()

                words[c["word_pos"]] = replacement
                injections.append({
                    "line": line_idx + 1,  # 1-indexed for user readability
                    "original": original_word,
                    "replacement": c["replacement"],
                    "distinctiveness": c["distinctiveness"],
                })

        # Rebuild line from words, preserving non-word segments
        modified_lines.append(_rebuild_line(line, words))

    return "\n".join(modified_lines), injections


def _rebuild_line(original: str, new_words: List[str]) -> str:
    """Rebuild a line replacing word tokens with new_words, preserving punctuation."""
    result: List[str] = []
    word_idx = 0
    last_end = 0

    for m in re.finditer(r"\b\w+\b", original):
        result.append(original[last_end:m.start()])
        if word_idx < len(new_words):
            result.append(new_words[word_idx])
            word_idx += 1
        else:
            result.append(m.group())
        last_end = m.end()

    result.append(original[last_end:])
    return "".join(result)


def inject_slang(
    input_path: Path,
    cohort: str,
    density: float = 0.05,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Inject cohort-distinctive slang into AI-generated lyrics.

    Args:
        input_path: Path to a plain-text lyrics file.
        cohort: Target genre cohort ("drill_trap" or "pop").
        density: Target slang token ratio (slang tokens / total tokens).
        db_path: Path to lyrics.db.  Defaults to ``DEFAULT_DB_PATH``.

    Returns:
        Dict with:
            - modified_text: lyrics text with slang injected
            - injections: list of {line, original, replacement, distinctiveness}
            - final_density: achieved slang density (0.0–1.0)
            - cohort: the cohort used
            - target_density: the requested density
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    text = Path(input_path).read_text(encoding="utf-8")
    raw_lines = text.split("\n")
    normalized_lines = [normalize_text(l) for l in raw_lines if l.strip()]

    # Load slang terms from DB
    conn = sqlite3.connect(str(db_path))
    slang_terms = _load_slang_terms(conn, cohort, limit=50)
    conn.close()

    if not slang_terms:
        return {
            "modified_text": text,
            "injections": [],
            "final_density": 0.0,
            "cohort": cohort,
            "target_density": density,
        }

    slang_forms = {t["form"].lower() for t in slang_terms}

    # Find replacement candidates
    candidates = _find_candidates(
        normalized_lines, slang_terms, slang_forms, density
    )

    # Apply replacements on the original (non-normalized) lines
    # so the output preserves the user's formatting
    non_empty_lines = [l for l in raw_lines if l.strip()]
    modified_text, injections = _apply_replacements(non_empty_lines, candidates)

    # Compute final density
    all_tokens = _tokenize(modified_text)
    final_slang_count = sum(1 for t in all_tokens if t.lower() in slang_forms)
    final_density = round(final_slang_count / len(all_tokens), 4) if all_tokens else 0.0

    return {
        "modified_text": modified_text,
        "injections": injections,
        "final_density": final_density,
        "cohort": cohort,
        "target_density": density,
    }
