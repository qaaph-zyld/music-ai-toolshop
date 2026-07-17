"""Flow analyzer v1 — syllable density, pattern detection, section flow.

Computes per-song flow profiles from the syllable counts stored in the
``lines`` table. Detects patterns like uniform, alternating, accelerating,
decelerating, or free flow.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import sqlite3


@dataclass
class SectionFlow:
    """Flow metrics for a single section."""

    section_type: str
    section_number: Optional[int]
    line_count: int
    avg_syllables: float
    syllable_counts: List[int]
    pattern: str


@dataclass
class FlowProfile:
    """Flow profile for an entire song."""

    song_id: int
    title: str
    artist: str
    avg_syllables_per_line: float
    syllable_density: float
    speed_variation: float
    pattern: str
    sections: List[SectionFlow] = field(default_factory=list)


def detect_patterns(syllable_counts: List[int]) -> str:
    """Detect the flow pattern from a sequence of syllable counts.

    Patterns:
    - ``uniform``: all lines have the same syllable count (±1)
    - ``alternating``: lines alternate between two distinct lengths
    - ``accelerating``: syllable counts consistently increase
    - ``decelerating``: syllable counts consistently decrease
    - ``free``: no clear pattern

    Args:
        syllable_counts: List of syllable counts per line.

    Returns:
        Pattern name string.
    """
    if not syllable_counts:
        return "free"

    if len(syllable_counts) == 1:
        return "uniform"

    # Check uniform: all within ±1 of the mean
    mean_val = statistics.mean(syllable_counts)
    if all(abs(s - mean_val) <= 1 for s in syllable_counts):
        return "uniform"

    # Check alternating: even-indexed and odd-indexed lines form two groups
    if len(syllable_counts) >= 4:
        even = syllable_counts[0::2]
        odd = syllable_counts[1::2]
        even_mean = statistics.mean(even)
        odd_mean = statistics.mean(odd)
        if abs(even_mean - odd_mean) >= 3:
            if all(abs(s - even_mean) <= 2 for s in even) and all(
                abs(s - odd_mean) <= 2 for s in odd
            ):
                return "alternating"

    # Check accelerating: consistently increasing
    diffs = [syllable_counts[i + 1] - syllable_counts[i] for i in range(len(syllable_counts) - 1)]
    if all(d >= -1 for d in diffs) and sum(diffs) >= len(syllable_counts):
        return "accelerating"

    # Check decelerating: consistently decreasing
    if all(d <= 1 for d in diffs) and sum(diffs) <= -len(syllable_counts):
        return "decelerating"

    return "free"


def section_flow(
    conn: sqlite3.Connection, section_id: int
) -> Optional[SectionFlow]:
    """Compute flow metrics for a single section.

    Args:
        conn: Database connection.
        section_id: Section ID from the sections table.

    Returns:
        SectionFlow object or None if section has no lines.
    """
    cursor = conn.cursor()
    cursor.execute(
        """SELECT type, type_number, syllable_count
           FROM sections s
           LEFT JOIN lines l ON l.section_id = s.id
           WHERE s.id = ?
           ORDER BY l.ordinal""",
        (section_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return None

    sec_type = rows[0][0]
    sec_num = rows[0][1]
    syl_counts = [r[2] for r in rows if r[2] is not None]
    if not syl_counts:
        return None

    avg_syl = round(statistics.mean(syl_counts), 2)
    pattern = detect_patterns(syl_counts)

    return SectionFlow(
        section_type=sec_type,
        section_number=sec_num,
        line_count=len(syl_counts),
        avg_syllables=avg_syl,
        syllable_counts=syl_counts,
        pattern=pattern,
    )


def flow_profile(conn: sqlite3.Connection, song_id: int) -> Dict:
    """Compute the full flow profile for a song.

    Args:
        conn: Database connection.
        song_id: Song ID.

    Returns:
        Dict with flow profile data.
    """
    cursor = conn.cursor()

    # Get song metadata
    cursor.execute(
        "SELECT title, primary_artist FROM songs WHERE id = ?", (song_id,)
    )
    row = cursor.fetchone()
    if not row:
        return {}
    title, artist = row

    # Get all syllable counts for the song
    cursor.execute(
        """SELECT l.syllable_count
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           WHERE s.song_id = ?
           ORDER BY s.ordinal, l.ordinal""",
        (song_id,),
    )
    all_syl = [r[0] for r in cursor.fetchall() if r[0] is not None]
    if not all_syl:
        return {
            "song_id": song_id,
            "title": title,
            "artist": artist,
            "avg_syllables_per_line": 0,
            "syllable_density": 0,
            "speed_variation": 0,
            "pattern": "free",
            "sections": [],
        }

    avg_syl = round(statistics.mean(all_syl), 2)
    # Syllable density: avg syllables / avg words per line (approx from DB)
    cursor.execute(
        """SELECT avg(word_count), avg(syllable_count)
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           WHERE s.song_id = ?""",
        (song_id,),
    )
    avg_words, avg_syl_db = cursor.fetchone()
    density = round(avg_syl_db / avg_words, 4) if avg_words and avg_words > 0 else 0.0

    # Speed variation: coefficient of variation of syllable counts
    if len(all_syl) > 1:
        cv = round(statistics.stdev(all_syl) / statistics.mean(all_syl), 4)
    else:
        cv = 0.0

    # Overall pattern
    pattern = detect_patterns(all_syl)

    # Per-section flow
    cursor.execute(
        "SELECT id FROM sections WHERE song_id = ? ORDER BY ordinal",
        (song_id,),
    )
    section_ids = [r[0] for r in cursor.fetchall()]
    sections = []
    for sid in section_ids:
        sf = section_flow(conn, sid)
        if sf:
            sections.append({
                "type": sf.section_type,
                "number": sf.section_number,
                "line_count": sf.line_count,
                "avg_syllables": sf.avg_syllables,
                "pattern": sf.pattern,
            })

    return {
        "song_id": song_id,
        "title": title,
        "artist": artist,
        "avg_syllables_per_line": avg_syl,
        "syllable_density": density,
        "speed_variation": cv,
        "pattern": pattern,
        "sections": sections,
    }


def artist_flow_summary(
    conn: sqlite3.Connection, artist: Optional[str] = None
) -> List[Dict]:
    """Compute per-artist flow summary statistics.

    Args:
        conn: Database connection.
        artist: Filter to a specific artist (None = all artists).

    Returns:
        List of dicts with per-artist flow stats.
    """
    cursor = conn.cursor()
    if artist:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(DISTINCT s.id) as song_count,
                round(avg(l.syllable_count), 2) as avg_syllables_per_line,
                round(avg(CAST(l.syllable_count AS FLOAT) / NULLIF(l.word_count, 0)), 4) as avg_density,
                0 as avg_speed_variation,
                'free' as dominant_pattern
               FROM songs s
               JOIN sections sec ON sec.song_id = s.id
               JOIN lines l ON l.section_id = sec.id
               WHERE s.primary_artist = ? AND s.corpus = 'genius-pro'
                 AND l.syllable_count IS NOT NULL AND l.word_count > 0
               GROUP BY s.primary_artist
               ORDER BY song_count DESC""",
            (artist,),
        )
    else:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(DISTINCT s.id) as song_count,
                round(avg(l.syllable_count), 2) as avg_syllables_per_line,
                round(avg(CAST(l.syllable_count AS FLOAT) / NULLIF(l.word_count, 0)), 4) as avg_density,
                0 as avg_speed_variation,
                'free' as dominant_pattern
               FROM songs s
               JOIN sections sec ON sec.song_id = s.id
               JOIN lines l ON l.section_id = sec.id
               WHERE s.corpus = 'genius-pro'
                 AND l.syllable_count IS NOT NULL AND l.word_count > 0
               GROUP BY s.primary_artist
               ORDER BY song_count DESC"""
        )

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
