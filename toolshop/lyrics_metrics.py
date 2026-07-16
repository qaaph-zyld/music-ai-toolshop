"""Baseline lyrics metrics — per-song and per-artist statistics.

Populates the ``song_metrics`` table during ``build-db`` and provides
per-artist aggregate views via SQL.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from typing import Any, Dict, List, Optional

# ── English loanword heuristic (ported from lyrics_research/scripts/analyze_lyrics.py) ──

_COMMON_ENGLISH = {
    "the", "and", "for", "you", "are", "not", "but", "with", "your", "from",
    "have", "has", "had", "this", "that", "when", "where", "what", "who",
    "how", "why", "yes", "no", "hey", "ho", "go", "tell", "know", "time",
    "its", "just", "only", "like", "all", "get", "got", "can", "will", "would",
    "show", "some", "everybody", "put", "hands", "up", "we", "ve", "ll", "re",
    "oh", "yeah", "u", "mwah", "kiss", "da", "ba", "he", "she", "they", "them",
    "his", "her", "our", "my", "mine", "it", "is", "am", "be", "been",
    "being", "do", "does", "did", "done", "doing", "so", "if", "because", "as",
    "than", "then", "now", "here", "there", "again", "once", "never", "always",
    "every", "one", "two", "three", "four", "first", "last", "next", "other",
    "new", "old", "good", "bad", "big", "small", "little", "right", "left",
    "love", "live", "alive", "high", "drive", "dry", "forever", "toy", "boy",
    "game", "chess", "single", "multiplayer", "artificial", "intelligence",
    "modern", "technology", "generation", "queen", "king", "boom", "bang",
    "bitch", "mode", "switch", "broke", "gangsta", "nasty", "girl", "squad",
    "fashion", "models", "money", "cash", "drill", "trap", "rap", "magic",
    "playback", "vroom", "ave", "choky", "felna", "brena", "hotel", "barca",
    "face", "supreme", "bmw", "benz", "red", "bull", "dior", "gucci",
    "fendi", "vuitton", "louis", "paciotti", "martini", "bikini", "popov",
    "amor", "naomi", "dogg", "tarantino", "wannabe", "taxi", "tv",
}

_WORD_RE = re.compile(r"\b\w+\b")


def _tokenize(text: str) -> List[str]:
    """Lowercase word tokens."""
    return _WORD_RE.findall(text.lower())


def compute_song_metrics(conn: sqlite3.Connection, song_id: int) -> Dict[str, Any]:
    """Compute metrics for a single song from the DB and return as dict.

    Reads lines from the DB (joined via sections), computes:
    - total_words, unique_words, TTR
    - line_count, avg_words_per_line, avg_syllables_per_line
    - hook_repetition_max, hook_repetition_ratio
    - english_loanword_rate
    - section_type_counts (JSON)
    """
    cursor = conn.cursor()

    # Get all lines for this song
    cursor.execute(
        """SELECT l.text_norm, l.word_count, l.syllable_count
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           WHERE s.song_id = ?
           ORDER BY s.ordinal, l.ordinal""",
        (song_id,),
    )
    rows = cursor.fetchall()

    if not rows:
        return {
            "total_words": 0,
            "unique_words": 0,
            "ttr": 0.0,
            "line_count": 0,
            "avg_words_per_line": 0.0,
            "avg_syllables_per_line": 0.0,
            "hook_repetition_max": 0,
            "hook_repetition_ratio": 0.0,
            "english_loanword_rate": 0.0,
            "section_type_counts": json.dumps({}),
        }

    all_text = " ".join(r[0] or "" for r in rows)
    tokens = _tokenize(all_text)
    total_words = len(tokens)
    unique_words = len(set(tokens))
    ttr = round(unique_words / total_words, 4) if total_words else 0.0

    line_count = len(rows)
    word_counts = [r[1] or 0 for r in rows]
    syl_counts = [r[2] or 0 for r in rows]
    avg_words = round(sum(word_counts) / line_count, 2) if line_count else 0.0
    avg_syl = round(sum(syl_counts) / line_count, 2) if line_count else 0.0

    # Hook repetition: count repeated normalized lines
    line_texts = [(r[0] or "").strip() for r in rows]
    line_counter = Counter(line_texts)
    max_repeat = max(line_counter.values()) if line_counter else 0
    repeated_lines = sum(1 for c in line_counter.values() if c > 1)
    hook_ratio = round(repeated_lines / line_count, 4) if line_count else 0.0

    # English loanword rate
    english_count = sum(1 for t in tokens if t in _COMMON_ENGLISH)
    eng_rate = round(english_count / total_words, 4) if total_words else 0.0

    # Section type counts
    cursor.execute(
        "SELECT type, count(*) FROM sections WHERE song_id = ? GROUP BY type",
        (song_id,),
    )
    type_counts = {row[0]: row[1] for row in cursor.fetchall()}

    return {
        "total_words": total_words,
        "unique_words": unique_words,
        "ttr": ttr,
        "line_count": line_count,
        "avg_words_per_line": avg_words,
        "avg_syllables_per_line": avg_syl,
        "hook_repetition_max": max_repeat,
        "hook_repetition_ratio": hook_ratio,
        "english_loanword_rate": eng_rate,
        "section_type_counts": json.dumps(type_counts, ensure_ascii=False),
    }


def populate_song_metrics(conn: sqlite3.Connection) -> int:
    """Compute and insert metrics for all songs. Returns count of songs processed."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM songs")
    song_ids = [r[0] for r in cursor.fetchall()]

    for song_id in song_ids:
        metrics = compute_song_metrics(conn, song_id)
        conn.execute(
            """INSERT INTO song_metrics
               (song_id, total_words, unique_words, ttr, line_count,
                avg_words_per_line, avg_syllables_per_line,
                hook_repetition_max, hook_repetition_ratio,
                english_loanword_rate, section_type_counts)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                song_id,
                metrics["total_words"],
                metrics["unique_words"],
                metrics["ttr"],
                metrics["line_count"],
                metrics["avg_words_per_line"],
                metrics["avg_syllables_per_line"],
                metrics["hook_repetition_max"],
                metrics["hook_repetition_ratio"],
                metrics["english_loanword_rate"],
                metrics["section_type_counts"],
            ),
        )

    conn.commit()
    return len(song_ids)


# ── Per-artist aggregate views ────────────────────────────────────────

_ARTIST_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_artist_stats AS
SELECT
    s.primary_artist,
    count(*) AS song_count,
    round(avg(m.total_words), 1) AS avg_total_words,
    round(avg(m.unique_words), 1) AS avg_unique_words,
    round(avg(m.ttr), 4) AS avg_ttr,
    round(avg(m.line_count), 1) AS avg_line_count,
    round(avg(m.avg_words_per_line), 2) AS avg_words_per_line,
    round(avg(m.avg_syllables_per_line), 2) AS avg_syllables_per_line,
    round(avg(m.hook_repetition_max), 2) AS avg_hook_repetition_max,
    round(avg(m.hook_repetition_ratio), 4) AS avg_hook_repetition_ratio,
    round(avg(m.english_loanword_rate), 4) AS avg_english_loanword_rate
FROM songs s
JOIN song_metrics m ON s.id = m.song_id
WHERE s.corpus = 'genius-pro'
GROUP BY s.primary_artist
ORDER BY song_count DESC;
"""


def create_artist_views(conn: sqlite3.Connection) -> None:
    """Create per-artist aggregate SQL views."""
    conn.executescript(_ARTIST_VIEW_SQL)
    conn.commit()


def get_artist_stats(conn: sqlite3.Connection, artist: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return per-artist stats, optionally filtered by artist name."""
    cursor = conn.cursor()
    if artist:
        cursor.execute(
            """SELECT * FROM v_artist_stats WHERE primary_artist = ?""",
            (artist,),
        )
    else:
        cursor.execute("SELECT * FROM v_artist_stats")

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_top_words_for_artist(
    conn: sqlite3.Connection, artist: str, limit: int = 20
) -> List[tuple]:
    """Return top-N words for an artist across all their songs."""
    cursor = conn.cursor()
    cursor.execute(
        """SELECT l.text_norm
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           JOIN songs sg ON s.song_id = sg.id
           WHERE sg.primary_artist = ? AND sg.corpus = 'genius-pro'""",
        (artist,),
    )
    all_text = " ".join(r[0] or "" for r in cursor.fetchall())
    tokens = _tokenize(all_text)
    return Counter(tokens).most_common(limit)


def get_section_type_distribution(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Return section type distribution across the whole corpus."""
    cursor = conn.cursor()
    cursor.execute(
        """SELECT s.type, count(*) as cnt
           FROM sections s
           JOIN songs sg ON s.song_id = sg.id
           WHERE sg.corpus = 'genius-pro'
           GROUP BY s.type
           ORDER BY cnt DESC"""
    )
    return [{"type": r[0], "count": r[1]} for r in cursor.fetchall()]


def get_syllable_distribution(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Return syllables-per-line distribution (binned)."""
    cursor = conn.cursor()
    cursor.execute(
        """SELECT
             CASE
               WHEN syllable_count <= 2 THEN '0-2'
               WHEN syllable_count <= 5 THEN '3-5'
               WHEN syllable_count <= 8 THEN '6-8'
               WHEN syllable_count <= 12 THEN '9-12'
               ELSE '13+'
             END AS bucket,
             count(*) AS cnt
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           JOIN songs sg ON s.song_id = sg.id
           WHERE sg.corpus = 'genius-pro'
           GROUP BY bucket
           ORDER BY bucket"""
    )
    return [{"bucket": r[0], "count": r[1]} for r in cursor.fetchall()]
