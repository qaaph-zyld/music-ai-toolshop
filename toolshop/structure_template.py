"""Structure template generator for genre-specific lyric scaffolding.

Queries ``lyrics.db`` for cohort-specific section type distributions and
generates a template with section types, target line counts, and rhyme
schemes.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH

# Default rhyme schemes per section type.
_SCHEME_MAP: Dict[str, str] = {
    "strofa": "AABB",
    "refren": "AABB",
    "bridge": "ABAB",
    "prerefren": "AABB",
    "postrefren": "AABB",
    "intro": "free",
    "outro": "free",
    "hook": "AABB",
    "instrumental": "",
    "interlude": "free",
    "spoken": "free",
    "call_response": "ABAB",
    "tekst": "AABB",
    "other": "AABB",
}


def _query_section_distribution(
    conn: sqlite3.Connection, cohort: str
) -> List[Dict]:
    """Return section type frequency for a cohort, sorted by count descending."""
    cursor = conn.execute(
        """SELECT s.type, count(*) as cnt
           FROM sections s
           JOIN songs sg ON s.song_id = sg.id
           WHERE sg.genre_cohort = ? AND sg.role = 'solo'
           GROUP BY s.type
           ORDER BY cnt DESC""",
        (cohort,),
    )
    return [{"type": r[0], "count": r[1]} for r in cursor.fetchall()]


def _query_avg_lines_per_type(
    conn: sqlite3.Connection, cohort: str
) -> Dict[str, float]:
    """Return average lines per section type for a cohort."""
    cursor = conn.execute(
        """SELECT s.type, round(avg(l.cnt), 0) as avg_lines
           FROM sections s
           JOIN songs sg ON s.song_id = sg.id
           JOIN (
               SELECT section_id, count(*) as cnt
               FROM lines
               GROUP BY section_id
           ) l ON l.section_id = s.id
           WHERE sg.genre_cohort = ? AND sg.role = 'solo'
           GROUP BY s.type""",
        (cohort,),
    )
    return {r[0]: int(r[1]) for r in cursor.fetchall()}


def _query_common_orderings(
    conn: sqlite3.Connection, cohort: str, limit: int = 20
) -> List[List[str]]:
    """Return common section orderings for a cohort."""
    cursor = conn.execute(
        """SELECT group_concat(s.type, '|') as ordering
           FROM sections s
           JOIN songs sg ON s.song_id = sg.id
           WHERE sg.genre_cohort = ? AND sg.role = 'solo'
           GROUP BY sg.id
           ORDER BY sg.id""",
        (cohort,),
    )
    orderings = [r[0].split("|") for r in cursor.fetchall() if r[0]]
    # Count frequency of each ordering.
    ordering_counter = Counter(tuple(o) for o in orderings)
    return [list(o) for o, _ in ordering_counter.most_common(limit)]


def _build_progression(
    distribution: List[Dict],
    orderings: List[List[str]],
    num_sections: int,
    cohort: str,
) -> List[str]:
    """Build a section progression of length num_sections."""
    # Try the most common ordering first.
    for ordering in orderings:
        if len(ordering) >= num_sections:
            return ordering[:num_sections]

    # If no ordering is long enough, extend the most common one.
    if orderings:
        base = list(orderings[0])
    else:
        # Fallback: use top types from distribution.
        base = [d["type"] for d in distribution[:3]]

    # Extend by cycling through common types (strofa, refren alternation).
    common_types = [d["type"] for d in distribution if d["type"] in ("strofa", "refren")]
    if not common_types:
        common_types = [d["type"] for d in distribution[:2]]

    while len(base) < num_sections:
        # Alternate strofa/refren for the remaining slots.
        base.append(common_types[len(base) % len(common_types)])

    return base[:num_sections]


def _enforce_pop_hook_forward(progression: List[str]) -> List[str]:
    """For pop: ensure refren (chorus) appears by section 2 (index 1)."""
    if len(progression) < 2:
        return progression
    # Check if any of the first 2 sections is a refren/hook.
    hook_types = {"refren", "hook"}
    if not any(t in hook_types for t in progression[:2]):
        # Insert refren after the first section.
        progression.insert(1, "refren")
    return progression


def generate_template(
    cohort: str,
    db_path: Optional[Path] = None,
    num_sections: int = 6,
) -> Dict:
    """Generate a structure template for a genre cohort.

    Queries ``lyrics.db`` for cohort-specific section type distribution,
    average lines per section type, and common section orderings.  Generates
    a template with target line counts and rhyme schemes.

    Args:
        cohort: Genre cohort (``"drill_trap"`` or ``"pop"``).
        db_path: Path to ``lyrics.db``.  Defaults to ``DEFAULT_DB_PATH``.
        num_sections: Target number of sections in the template.

    Returns:
        Dict with keys:
            - ``sections``: list of ``{"type", "lines", "rhyme_scheme"}``
            - ``cohort``: the cohort string
            - ``total_lines``: sum of all section line counts
    """
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))

    try:
        distribution = _query_section_distribution(conn, cohort)
        avg_lines = _query_avg_lines_per_type(conn, cohort)
        orderings = _query_common_orderings(conn, cohort)
    finally:
        conn.close()

    # Build the section progression.
    progression = _build_progression(distribution, orderings, num_sections, cohort)

    # Cohort-specific adjustments.
    if cohort == "pop":
        progression = _enforce_pop_hook_forward(progression)
        # Trim back to num_sections if we inserted.
        progression = progression[:num_sections]
    elif cohort == "drill_trap":
        # Drill: allow verse-dominant — no forced early chorus.
        pass

    # Build section dicts with line counts and rhyme schemes.
    sections: List[Dict] = []
    for sec_type in progression:
        lines = avg_lines.get(sec_type, 8)  # Default 8 lines if type unknown.
        scheme = _SCHEME_MAP.get(sec_type, "AABB")
        sections.append({
            "type": sec_type,
            "lines": lines,
            "rhyme_scheme": scheme,
        })

    total_lines = sum(s["lines"] for s in sections)

    return {
        "sections": sections,
        "cohort": cohort,
        "total_lines": total_lines,
    }
