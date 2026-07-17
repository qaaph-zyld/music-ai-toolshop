"""Cross-artist collaboration analysis.

Identifies duo/trio songs, attributes sections to performers, and compares
craft metrics (syllable density, TTR, rhyme density) between solo and
collaboration contexts.
"""

from __future__ import annotations

import json
import statistics
from typing import Dict, List, Optional

import sqlite3


def find_collab_songs(
    conn: sqlite3.Connection, artist: Optional[str] = None
) -> List[Dict]:
    """Find collaboration songs (duo, trio, featured).

    Args:
        conn: Database connection.
        artist: Filter to songs involving a specific artist.

    Returns:
        List of dicts with song_id, title, primary_artist, category,
        featured_artists, and collab_type ('duo', 'trio', 'featured').
    """
    cursor = conn.cursor()
    if artist:
        cursor.execute(
            """SELECT id, title, primary_artist, category, featured_artists
               FROM songs
               WHERE corpus = 'genius-pro'
                 AND (category LIKE '%duo%' OR category LIKE '%trio%'
                      OR category LIKE '%featured%'
                      OR featured_artists IS NOT NULL)
                 AND (primary_artist = ? OR featured_artists LIKE ?)
               ORDER BY title""",
            (artist, f"%{artist}%"),
        )
    else:
        cursor.execute(
            """SELECT id, title, primary_artist, category, featured_artists
               FROM songs
               WHERE corpus = 'genius-pro'
                 AND (category LIKE '%duo%' OR category LIKE '%trio%'
                      OR category LIKE '%featured%'
                      OR featured_artists IS NOT NULL)
               ORDER BY title"""
        )

    results = []
    for row in cursor.fetchall():
        song_id, title, primary_artist, category, feat_json = row
        featured = json.loads(feat_json) if feat_json else []

        if "trio" in (category or ""):
            collab_type = "trio"
        elif "duo" in (category or ""):
            collab_type = "duo"
        elif "featured" in (category or "") or featured:
            collab_type = "featured"
        else:
            collab_type = "solo"

        results.append({
            "song_id": song_id,
            "title": title,
            "primary_artist": primary_artist,
            "category": category,
            "featured_artists": featured,
            "collab_type": collab_type,
        })

    return results


def section_attribution(
    conn: sqlite3.Connection, song_id: int
) -> List[Dict]:
    """Attribute sections to performers based on section performers field.

    Args:
        conn: Database connection.
        song_id: Song ID.

    Returns:
        List of dicts with section_id, type, performers, line_count,
        avg_syllables.
    """
    cursor = conn.cursor()
    cursor.execute(
        """SELECT s.id, s.type, s.type_number, s.performers,
                  count(l.id) as line_count,
                  round(avg(l.syllable_count), 2) as avg_syllables
           FROM sections s
           LEFT JOIN lines l ON l.section_id = s.id
           WHERE s.song_id = ?
           GROUP BY s.id
           ORDER BY s.ordinal""",
        (song_id,),
    )

    results = []
    for row in cursor.fetchall():
        sec_id, sec_type, sec_num, perf_json, line_count, avg_syl = row
        performers = json.loads(perf_json) if perf_json else []
        results.append({
            "section_id": sec_id,
            "type": sec_type,
            "type_number": sec_num,
            "performers": performers,
            "line_count": line_count or 0,
            "avg_syllables": avg_syl or 0,
        })

    return results


def collab_craft_comparison(
    conn: sqlite3.Connection, artist: str
) -> Dict:
    """Compare craft metrics between solo and collaboration songs.

    Args:
        conn: Database connection.
        artist: Artist name to compare.

    Returns:
        Dict with solo_stats, collab_stats, and comparison metrics.
    """
    cursor = conn.cursor()

    # Solo songs
    cursor.execute(
        """SELECT
            count(*) as song_count,
            round(avg(sm.avg_syllables_per_line), 2) as avg_syllables_per_line,
            round(avg(sm.ttr), 4) as avg_ttr,
            round(avg(sm.avg_words_per_line), 2) as avg_words_per_line
           FROM songs s
           JOIN song_metrics sm ON sm.song_id = s.id
           WHERE s.primary_artist = ? AND s.corpus = 'genius-pro'
             AND s.category LIKE '%solo%'""",
        (artist,),
    )
    solo_row = cursor.fetchone()
    solo_stats = {
        "song_count": solo_row[0] or 0,
        "avg_syllables_per_line": solo_row[1] or 0,
        "avg_ttr": solo_row[2] or 0,
        "avg_words_per_line": solo_row[3] or 0,
    }

    # Collab songs (duo/trio/featured)
    cursor.execute(
        """SELECT
            count(*) as song_count,
            round(avg(sm.avg_syllables_per_line), 2) as avg_syllables_per_line,
            round(avg(sm.ttr), 4) as avg_ttr,
            round(avg(sm.avg_words_per_line), 2) as avg_words_per_line
           FROM songs s
           JOIN song_metrics sm ON sm.song_id = s.id
           WHERE s.primary_artist = ? AND s.corpus = 'genius-pro'
             AND (s.category LIKE '%duo%' OR s.category LIKE '%trio%'
                  OR s.category LIKE '%featured%')""",
        (artist,),
    )
    collab_row = cursor.fetchone()
    collab_stats = {
        "song_count": collab_row[0] or 0,
        "avg_syllables_per_line": collab_row[1] or 0,
        "avg_ttr": collab_row[2] or 0,
        "avg_words_per_line": collab_row[3] or 0,
    }

    # Compute deltas
    deltas = {}
    for key in ["avg_syllables_per_line", "avg_ttr", "avg_words_per_line"]:
        if solo_stats[key] and collab_stats[key]:
            deltas[key] = round(collab_stats[key] - solo_stats[key], 4)
        else:
            deltas[key] = None

    return {
        "artist": artist,
        "solo": solo_stats,
        "collab": collab_stats,
        "deltas": deltas,
    }


def artist_collab_summary(
    conn: sqlite3.Connection, artist: Optional[str] = None
) -> List[Dict]:
    """Per-artist collaboration summary.

    Args:
        conn: Database connection.
        artist: Filter to a specific artist.

    Returns:
        List of dicts with per-artist collab stats.
    """
    cursor = conn.cursor()
    if artist:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(CASE WHEN s.category LIKE '%solo%' THEN 1 END) as solo_song_count,
                count(CASE WHEN s.category LIKE '%duo%' OR s.category LIKE '%trio%'
                           OR s.category LIKE '%featured%' THEN 1 END) as collab_song_count,
                round(avg(sm.avg_syllables_per_line), 2) as avg_syllables_per_line,
                round(avg(sm.ttr), 4) as avg_ttr
               FROM songs s
               JOIN song_metrics sm ON sm.song_id = s.id
               WHERE s.primary_artist = ? AND s.corpus = 'genius-pro'
               GROUP BY s.primary_artist
               ORDER BY collab_song_count DESC""",
            (artist,),
        )
    else:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(CASE WHEN s.category LIKE '%solo%' THEN 1 END) as solo_song_count,
                count(CASE WHEN s.category LIKE '%duo%' OR s.category LIKE '%trio%'
                           OR s.category LIKE '%featured%' THEN 1 END) as collab_song_count,
                round(avg(sm.avg_syllables_per_line), 2) as avg_syllables_per_line,
                round(avg(sm.ttr), 4) as avg_ttr
               FROM songs s
               JOIN song_metrics sm ON sm.song_id = s.id
               WHERE s.corpus = 'genius-pro'
               GROUP BY s.primary_artist
               HAVING collab_song_count > 0
               ORDER BY collab_song_count DESC"""
        )

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
