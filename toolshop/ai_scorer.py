"""AI lyric quality scorer — 4-component z-score evaluation.

Scores AI-generated lyrics against genre cohort baselines from ``lyrics.db``
across four equally-weighted components: Structural, Rhyme, Lexical, and
Repetition.  Each component is normalised to 0–100 where 50 = cohort average.
"""

from __future__ import annotations

import re
import sqlite3
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyrics_analyzer import _tokenize
from toolshop.lyricsdb import DEFAULT_DB_PATH, normalize_text, parse_section_label
from toolshop.rhyme_miner import (
    find_internal_rhymes,
    find_rhymes,
    multisyllabic_rhymes,
    rhyme_factor,
)
from toolshop.syllables import count_line

_SECTION_LABEL_RE = re.compile(r"^\s*\[(.+?)\]\s*$")


def _parse_sections(text: str) -> List[Tuple[str, List[str]]]:
    """Parse lyrics text into sections.

    Lines starting with ``[Label]`` are section labels; subsequent lines
    until the next label form the section content.

    Returns:
        List of (section_type, [content_lines]) tuples.
    """
    sections: List[Tuple[str, List[str]]] = []
    current_type = "other"
    current_lines: List[str] = []

    for line in text.split("\n"):
        m = _SECTION_LABEL_RE.match(line)
        if m:
            # Save previous section.
            if current_lines:
                sections.append((current_type, current_lines))
            parsed = parse_section_label(m.group(1))
            current_type = parsed.type
            current_lines = []
        else:
            stripped = line.strip()
            if stripped:
                current_lines.append(stripped)

    if current_lines:
        sections.append((current_type, current_lines))

    return sections


def _z_score(value: float, mean: float, std: float) -> float:
    """Compute z-score with std=0 guard."""
    if std == 0:
        return 0.0
    return (value - mean) / std


def _z_to_score(z: float) -> float:
    """Map z-score to 0–100 scale where 50 = average."""
    score = 50.0 + (z * 25.0)
    return max(0.0, min(100.0, score))


def _query_cohort_baselines(
    conn: sqlite3.Connection, cohort: str
) -> Dict[str, Dict[str, float]]:
    """Query cohort-level baseline metrics from song_metrics and song_rhyme_metrics."""
    # song_metrics baselines.
    cursor = conn.execute(
        """SELECT avg(m.line_count), avg(m.ttr), avg(m.avg_syllables_per_line),
                  avg(m.hook_repetition_ratio),
                  count(DISTINCT s.id) as song_count,
                  avg(sec_count) as avg_sections
           FROM song_metrics m
           JOIN songs s ON m.song_id = s.id
           JOIN (
               SELECT song_id, count(*) as sec_count
               FROM sections GROUP BY song_id
           ) sc ON sc.song_id = s.id
           WHERE s.genre_cohort = ? AND s.role = 'solo'""",
        (cohort,),
    )
    row = cursor.fetchone()
    sm_baselines = {
        "avg_line_count": row[0] or 0.0,
        "avg_ttr": row[1] or 0.0,
        "avg_syllables_per_line": row[2] or 0.0,
        "avg_hook_repetition_ratio": row[3] or 0.0,
        "song_count": row[4] or 0,
        "avg_sections": row[5] or 0.0,
    }

    # song_rhyme_metrics baselines.
    cursor = conn.execute(
        """SELECT avg(srm.rhyme_factor), avg(srm.pct_multis),
                  avg(srm.internal_rhyme_rate)
           FROM song_rhyme_metrics srm
           JOIN songs s ON srm.song_id = s.id
           WHERE s.genre_cohort = ? AND s.role = 'solo'""",
        (cohort,),
    )
    row = cursor.fetchone()
    rm_baselines = {
        "avg_rhyme_factor": row[0] or 0.0,
        "avg_pct_multis": row[1] or 0.0,
        "avg_internal_rhyme_rate": row[2] or 0.0,
    }

    # Std devs for z-score computation.
    cursor = conn.execute(
        """SELECT m.line_count, m.ttr, m.avg_syllables_per_line,
                  m.hook_repetition_ratio
           FROM song_metrics m
           JOIN songs s ON m.song_id = s.id
           WHERE s.genre_cohort = ? AND s.role = 'solo'""",
        (cohort,),
    )
    rows = cursor.fetchall()
    sm_stds = {
        "line_count": statistics.pstdev([r[0] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "ttr": statistics.pstdev([r[1] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "avg_syllables_per_line": statistics.pstdev([r[2] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "hook_repetition_ratio": statistics.pstdev([r[3] or 0 for r in rows]) if len(rows) > 1 else 0.0,
    }

    cursor = conn.execute(
        """SELECT srm.rhyme_factor, srm.pct_multis, srm.internal_rhyme_rate
           FROM song_rhyme_metrics srm
           JOIN songs s ON srm.song_id = s.id
           WHERE s.genre_cohort = ? AND s.role = 'solo'""",
        (cohort,),
    )
    rows = cursor.fetchall()
    rm_stds = {
        "rhyme_factor": statistics.pstdev([r[0] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "pct_multis": statistics.pstdev([r[1] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "internal_rhyme_rate": statistics.pstdev([r[2] or 0 for r in rows]) if len(rows) > 1 else 0.0,
    }

    return {
        "song_metrics": sm_baselines,
        "song_rhyme_metrics": rm_baselines,
        "sm_stds": sm_stds,
        "rm_stds": rm_stds,
    }


def score_lyrics(
    input_path: Path,
    cohort: str = "drill_trap",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Score AI-generated lyrics against genre cohort baselines.

    Computes four equally-weighted component scores (Structural, Rhyme,
    Lexical, Repetition), each normalised to 0–100 where 50 = cohort
    average via z-score mapping.

    Args:
        input_path: Path to a plain-text file containing AI-generated lyrics.
        cohort: Genre baseline (``"drill_trap"`` or ``"pop"``).
        db_path: Path to ``lyrics.db``.  Defaults to ``DEFAULT_DB_PATH``.

    Returns:
        Dict with ``overall_score`` and ``components`` containing per-component
        scores and raw metrics.
    """
    # Read and normalize input.
    raw_text = Path(input_path).read_text(encoding="utf-8")
    normalized = normalize_text(raw_text)

    # Parse sections.
    sections = _parse_sections(normalized)
    all_lines: List[str] = []
    for _, lines in sections:
        all_lines.extend(lines)

    section_count = len(sections)
    total_lines = len(all_lines)

    # ── Structural metrics ──
    struct_input = {
        "section_count": section_count,
        "total_lines": total_lines,
    }

    # ── Rhyme metrics ──
    all_section_lines: List[str] = []
    for _, lines in sections:
        all_section_lines.extend(lines)

    rf = rhyme_factor(all_section_lines) if all_section_lines else 0.0
    multi_matches = multisyllabic_rhymes(all_section_lines) if all_section_lines else []
    multi_count = sum(len(m.line_indices) for m in multi_matches)
    pct_multis = round(multi_count / len(all_section_lines), 4) if all_section_lines else 0.0

    internal_count = 0
    for line in all_section_lines:
        if find_internal_rhymes(line, min_match=2):
            internal_count += 1
    internal_rhyme_rate = round(internal_count / total_lines, 4) if total_lines else 0.0

    rhyme_input = {
        "rhyme_factor": rf,
        "pct_multis": pct_multis,
        "internal_rhyme_rate": internal_rhyme_rate,
    }

    # ── Lexical metrics ──
    tokens = _tokenize(normalized)
    total_tokens = len(tokens)
    unique_tokens = len(set(tokens))
    ttr = round(unique_tokens / total_tokens, 4) if total_tokens else 0.0
    avg_syl = round(sum(count_line(l) for l in all_lines) / total_lines, 2) if total_lines else 0.0

    lexical_input = {
        "ttr": ttr,
        "avg_syllables_per_line": avg_syl,
    }

    # ── Repetition metrics ──
    from collections import Counter
    line_counter = Counter(all_lines)
    repeated = sum(1 for c in line_counter.values() if c > 1)
    hook_repetition_ratio = round(repeated / total_lines, 4) if total_lines else 0.0

    repetition_input = {
        "hook_repetition_ratio": hook_repetition_ratio,
    }

    # ── Query baselines from DB ──
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    try:
        baselines = _query_cohort_baselines(conn, cohort)
    finally:
        conn.close()

    sm = baselines["song_metrics"]
    rm = baselines["song_rhyme_metrics"]
    sm_stds = baselines["sm_stds"]
    rm_stds = baselines["rm_stds"]

    # ── Component scores via z-score ──
    # Structural: compare section_count and total_lines.
    avg_sections = sm.get("avg_sections", 0.0)
    avg_line_count = sm.get("avg_line_count", 0.0)
    # Use total_lines vs avg_line_count and section_count vs avg_sections.
    z_lines = _z_score(total_lines, avg_line_count, sm_stds.get("line_count", 0.0))
    z_sections = _z_score(section_count, avg_sections, 0.0)  # std=0 → z=0
    structural_score = _z_to_score((z_lines + z_sections) / 2)

    # Rhyme: rhyme_factor, pct_multis, internal_rhyme_rate (higher is better).
    z_rf = _z_score(rf, rm.get("avg_rhyme_factor", 0.0), rm_stds.get("rhyme_factor", 0.0))
    z_multis = _z_score(pct_multis, rm.get("avg_pct_multis", 0.0), rm_stds.get("pct_multis", 0.0))
    z_irr = _z_score(internal_rhyme_rate, rm.get("avg_internal_rhyme_rate", 0.0), rm_stds.get("internal_rhyme_rate", 0.0))
    rhyme_score = _z_to_score((z_rf + z_multis + z_irr) / 3)

    # Lexical: TTR and avg_syllables_per_line.
    z_ttr = _z_score(ttr, sm.get("avg_ttr", 0.0), sm_stds.get("ttr", 0.0))
    z_syl = _z_score(avg_syl, sm.get("avg_syllables_per_line", 0.0), sm_stds.get("avg_syllables_per_line", 0.0))
    lexical_score = _z_to_score((z_ttr + z_syl) / 2)

    # Repetition: hook_repetition_ratio.
    z_hook = _z_score(hook_repetition_ratio, sm.get("avg_hook_repetition_ratio", 0.0), sm_stds.get("hook_repetition_ratio", 0.0))
    repetition_score = _z_to_score(z_hook)

    # ── Weighted sum ──
    overall = (
        structural_score * 0.25
        + rhyme_score * 0.25
        + lexical_score * 0.25
        + repetition_score * 0.25
    )
    overall = round(overall, 2)

    return {
        "overall_score": overall,
        "components": {
            "structural": {
                "score": round(structural_score, 2),
                "metrics": struct_input,
                "baselines": {
                    "avg_sections": avg_sections,
                    "avg_line_count": avg_line_count,
                },
            },
            "rhyme": {
                "score": round(rhyme_score, 2),
                "metrics": rhyme_input,
                "baselines": {
                    "avg_rhyme_factor": rm.get("avg_rhyme_factor", 0.0),
                    "avg_pct_multis": rm.get("avg_pct_multis", 0.0),
                    "avg_internal_rhyme_rate": rm.get("avg_internal_rhyme_rate", 0.0),
                },
            },
            "lexical": {
                "score": round(lexical_score, 2),
                "metrics": lexical_input,
                "baselines": {
                    "avg_ttr": sm.get("avg_ttr", 0.0),
                    "avg_syllables_per_line": sm.get("avg_syllables_per_line", 0.0),
                },
            },
            "repetition": {
                "score": round(repetition_score, 2),
                "metrics": repetition_input,
                "baselines": {
                    "avg_hook_repetition_ratio": sm.get("avg_hook_repetition_ratio", 0.0),
                },
            },
        },
    }
