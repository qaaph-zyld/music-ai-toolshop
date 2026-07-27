"""Corpus intelligence — lyrics DB → production suggestions.

Queries the ``lyrics.db`` SQLite database (742 songs, 5,493 sections, 36,572 lines)
to provide genre-aware production suggestions: BPM, key, arrangement, drum patterns,
and flow-to-MIDI mapping.

Uses :mod:`toolshop.lyricsdb` for the DB path and schema.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH


# Genre → typical BPM (from corpus analysis)
GENRE_BPM: Dict[str, int] = {
    "drill_trap": 138,
    "drill": 138,
    "trap": 140,
    "pop": 120,
    "boom_bap": 90,
}

# Genre → common keys
GENRE_KEYS: Dict[str, List[str]] = {
    "drill_trap": ["Gm", "Dm", "Fm", "Cm", "Am"],
    "drill": ["Gm", "Dm", "Fm", "Cm"],
    "trap": ["Gm", "Fm", "Dm", "Am"],
    "pop": ["Cm", "Am", "Bb", "Gm", "Dm"],
    "boom_bap": ["Am", "Dm", "Em", "Gm"],
}

# Genre → drum pattern name (maps to generators.DRUM_PRESETS)
GENRE_DRUM_PATTERN: Dict[str, str] = {
    "drill_trap": "drill",
    "drill": "drill",
    "trap": "trap",
    "pop": "pop",
    "boom_bap": "boom_bap",
}

# Default arrangement templates (bars per section)
ARRANGEMENT_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "drill_trap": [
        {"section": "intro", "bars": 4},
        {"section": "verse", "bars": 16},
        {"section": "chorus", "bars": 8},
        {"section": "verse", "bars": 16},
        {"section": "chorus", "bars": 8},
        {"section": "bridge", "bars": 8},
        {"section": "chorus", "bars": 8},
        {"section": "outro", "bars": 4},
    ],
    "pop": [
        {"section": "intro", "bars": 4},
        {"section": "verse", "bars": 8},
        {"section": "chorus", "bars": 8},
        {"section": "verse", "bars": 8},
        {"section": "chorus", "bars": 8},
        {"section": "bridge", "bars": 4},
        {"section": "chorus", "bars": 8},
        {"section": "outro", "bars": 4},
    ],
}


def _get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a read-only connection to lyrics.db."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Lyrics DB not found at {path}. Run `toolshop lyrics build-db` first."
        )
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def suggest_bpm(genre: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Suggest a BPM for a genre based on corpus data.

    Tries to query the DB for median BPM of the cohort. Falls back to
    hardcoded :data:`GENRE_BPM` if DB is unavailable or has no tempo data.
    """
    genre_key = genre.lower().replace("-", "_").replace(" ", "_")

    # Try DB query first
    try:
        conn = _get_conn(db_path)
        cursor = conn.execute(
            """SELECT AVG(m.bpm) as avg_bpm, COUNT(*) as cnt
               FROM song_metrics m
               JOIN songs s ON m.song_id = s.id
               WHERE s.genre_cohort = ? AND s.role = 'solo'
               AND m.bpm IS NOT NULL AND m.bpm > 0""",
            (genre_key,),
        )
        row = cursor.fetchone()
        conn.close()

        if row and row["cnt"] > 0 and row["avg_bpm"]:
            bpm = round(row["avg_bpm"])
            return {
                "bpm": bpm,
                "source": "corpus_avg",
                "sample_size": row["cnt"],
                "genre": genre_key,
            }
    except (FileNotFoundError, sqlite3.Error):
        pass

    # Fallback to hardcoded
    bpm = GENRE_BPM.get(genre_key, 140)
    return {
        "bpm": bpm,
        "source": "preset",
        "sample_size": 0,
        "genre": genre_key,
    }


def suggest_key(genre: str) -> Dict[str, Any]:
    """Suggest common keys for a genre."""
    genre_key = genre.lower().replace("-", "_").replace(" ", "_")
    keys = GENRE_KEYS.get(genre_key, ["Gm", "Dm", "Cm"])
    return {
        "keys": keys,
        "primary": keys[0],
        "genre": genre_key,
        "source": "corpus_presets",
    }


def suggest_arrangement(genre: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Suggest an arrangement (section sequence + lengths) for a genre.

    Tries to query section type distribution from the DB. Falls back to
    hardcoded templates.
    """
    genre_key = genre.lower().replace("-", "_").replace(" ", "_")

    # Try DB query for section distribution
    try:
        conn = _get_conn(db_path)
        cursor = conn.execute(
            """SELECT sec.section_type, COUNT(*) as count, AVG(line_count) as avg_lines
               FROM sections sec
               JOIN songs s ON sec.song_id = s.id
               WHERE s.genre_cohort = ? AND s.role = 'solo'
               GROUP BY sec.section_type
               ORDER BY count DESC""",
            (genre_key,),
        )
        rows = cursor.fetchall()
        conn.close()

        if rows:
            section_stats = [
                {
                    "section": r["section_type"],
                    "count": r["count"],
                    "avg_lines": round(r["avg_lines"] or 0, 1),
                }
                for r in rows
            ]
            template = ARRANGEMENT_TEMPLATES.get(genre_key, ARRANGEMENT_TEMPLATES["drill_trap"])
            return {
                "arrangement": template,
                "section_stats": section_stats,
                "genre": genre_key,
                "source": "corpus+template",
            }
    except (FileNotFoundError, sqlite3.Error):
        pass

    # Fallback
    template = ARRANGEMENT_TEMPLATES.get(genre_key, ARRANGEMENT_TEMPLATES["drill_trap"])
    return {
        "arrangement": template,
        "section_stats": [],
        "genre": genre_key,
        "source": "template_only",
    }


def suggest_pattern(genre: str) -> Dict[str, Any]:
    """Suggest a drum pattern name for a genre."""
    genre_key = genre.lower().replace("-", "_").replace(" ", "_")
    pattern_name = GENRE_DRUM_PATTERN.get(genre_key, "drill")
    return {
        "pattern": pattern_name,
        "genre": genre_key,
    }


def get_section_stats(genre: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Get section type statistics for a genre cohort from the DB."""
    genre_key = genre.lower().replace("-", "_").replace(" ", "_")
    conn = _get_conn(db_path)

    cursor = conn.execute(
        """SELECT sec.section_type, COUNT(*) as count,
                  AVG(sec.line_count) as avg_lines,
                  AVG(sec.word_count) as avg_words
           FROM sections sec
           JOIN songs s ON sec.song_id = s.id
           WHERE s.genre_cohort = ? AND s.role = 'solo'
           GROUP BY sec.section_type
           ORDER BY count DESC""",
        (genre_key,),
    )
    rows = cursor.fetchall()

    stats = [
        {
            "section": r["section_type"],
            "count": r["count"],
            "avg_lines": round(r["avg_lines"] or 0, 1),
            "avg_words": round(r["avg_words"] or 0, 1),
        }
        for r in rows
    ]

    # Total sections
    cursor2 = conn.execute(
        """SELECT COUNT(*) as total
           FROM sections sec
           JOIN songs s ON sec.song_id = s.id
           WHERE s.genre_cohort = ? AND s.role = 'solo'""",
        (genre_key,),
    )
    total = cursor2.fetchone()["total"]

    conn.close()

    return {
        "genre": genre_key,
        "total_sections": total,
        "section_types": stats,
    }


def flow_to_midi(
    lyrics_file: str, max_density: int = 16
) -> Dict[str, Any]:
    """Map lyrics syllable density to MIDI note density.

    Parses a lyrics file, computes syllables per line, and maps to
    note density values (fast flow = 16th notes, slow = quarter notes).

    Args:
        lyrics_file: Path to a text file with lyrics (one line per line).
        max_density: Maximum notes per bar (default 16 = 16th notes).
    """
    from toolshop.syllables import count_syllables

    path = Path(lyrics_file)
    if not path.exists():
        raise FileNotFoundError(f"Lyrics file not found: {path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    densities: List[Dict[str, Any]] = []
    for i, line in enumerate(lines):
        syl = count_syllables(line)
        # Map syllable count to note density
        # 1-2 syllables → quarter notes (4 per bar)
        # 3-5 → eighth notes (8)
        # 6-8 → 16th notes (16)
        # 9+ → 16th notes with some 32nd
        if syl <= 2:
            density = 4
        elif syl <= 5:
            density = 8
        elif syl <= 8:
            density = 16
        else:
            density = 16  # cap at 16th notes

        densities.append({
            "line": i + 1,
            "text": line[:60] + "..." if len(line) > 60 else line,
            "syllables": syl,
            "note_density": density,
            "grid": f"1/{density}",
        })

    avg_density = sum(d["note_density"] for d in densities) / len(densities) if densities else 0

    return {
        "file": str(path),
        "total_lines": len(lines),
        "avg_note_density": round(avg_density, 1),
        "lines": densities,
    }
