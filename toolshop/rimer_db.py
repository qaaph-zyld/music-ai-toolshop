"""Rimer DB — attested pro rhyme pairs from the corpus.

Extracts rhyme pairs from the ``line_rhymes`` table joined with ``lines``
to recover the actual words behind each vowel-skeleton match.  Pairs are
ranked by frequency, match length, and cohort distinctiveness, then stored
in a new ``rhyme_pairs`` table for fast lookup.

Usage::

    from toolshop.rimer_db import build_rimer_db, lookup_rhymes
    build_rimer_db(db_path)
    results = lookup_rhymes("zivot", cohort="drill_trap", top_k=10, db_path=db_path)
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyricsdb import DEFAULT_DB_PATH
from toolshop.rhyme_miner import _word_skeleton, vowel_skeleton

# ── Schema ────────────────────────────────────────────────────────────

_RIMER_SCHEMA = """
CREATE TABLE IF NOT EXISTS rhyme_pairs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vowel_skeleton  TEXT NOT NULL,
    match_length    INTEGER NOT NULL,
    word_a          TEXT NOT NULL,
    word_b          TEXT NOT NULL,
    frequency       INTEGER NOT NULL,
    drill_count     INTEGER DEFAULT 0,
    pop_count       INTEGER DEFAULT 0,
    cohort          TEXT,
    distinctiveness REAL DEFAULT 0.0
);
CREATE INDEX IF NOT EXISTS idx_rhyme_pairs_skeleton ON rhyme_pairs(vowel_skeleton);
CREATE INDEX IF NOT EXISTS idx_rhyme_pairs_word_a ON rhyme_pairs(word_a);
CREATE INDEX IF NOT EXISTS idx_rhyme_pairs_word_b ON rhyme_pairs(word_b);
"""

# ── Helpers ───────────────────────────────────────────────────────────

_WORD_RE = re.compile(r"[a-zA-Z]+")


def _last_n_words(text: str, n: int = 2) -> List[str]:
    """Return the last *n* words from a normalized text line."""
    if not text:
        return []
    words = _WORD_RE.findall(text)
    return words[-n:] if words else []


def _extract_word_pairs(
    lines_by_group: Dict[int, List[Tuple[str, str]]],
) -> List[Tuple[str, str, str, int]]:
    """Extract word pairs from lines in the same rhyme group.

    For each rhyme group with 2+ lines, pair the last words of each line
    with every other line in the group.

    Returns list of (word_a, word_b, vowel_skeleton, match_length) tuples.
    """
    pairs: List[Tuple[str, str, str, int]] = []
    for group_id, lines in lines_by_group.items():
        if len(lines) < 2:
            continue
        # Extract last word from each line
        last_words: List[Tuple[str, str, str]] = []  # (word, skeleton, text_norm)
        for text_norm, skeleton in lines:
            words = _WORD_RE.findall(text_norm or "")
            if not words:
                continue
            last_word = words[-1].lower()
            last_words.append((last_word, skeleton, text_norm))

        # Pair every combination within the group
        for i in range(len(last_words)):
            for j in range(i + 1, len(last_words)):
                wa, ska, _ = last_words[i]
                wb, skb, _ = last_words[j]
                if wa == wb:
                    continue
                # Use the shorter skeleton as the common key
                common_skel = ska if len(ska) <= len(skb) else skb
                ml = min(len(ska), len(skb))
                # Sort pair alphabetically for dedup
                if wa <= wb:
                    pairs.append((wa, wb, common_skel, ml))
                else:
                    pairs.append((wb, wa, common_skel, ml))
    return pairs


# ── Build ─────────────────────────────────────────────────────────────


def build_rimer_db(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Build the rhyme_pairs table from line_rhymes + lines + songs.

    Idempotent: drops and recreates ``rhyme_pairs`` on each call.

    Returns:
        Dict with 'total_pairs', 'unique_skeletons', 'drill_pairs', 'pop_pairs'.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")

    # Create schema
    conn.executescript(_RIMER_SCHEMA)

    # Wipe existing
    conn.execute("DELETE FROM rhyme_pairs")

    # Fetch all end-rhyme groups with their lines
    # Group by (song_id, rhyme_group) to get lines that rhyme together
    rows = conn.execute(
        """SELECT lr.song_id, lr.rhyme_group, lr.vowel_skeleton,
                  lr.match_length, l.text_norm, s.genre_cohort
           FROM line_rhymes lr
           JOIN lines l ON lr.line_id = l.id
           JOIN songs s ON lr.song_id = s.id
           WHERE lr.rhyme_type = 'end'
           ORDER BY lr.song_id, lr.rhyme_group, l.ordinal""",
    ).fetchall()

    # Group lines by (song_id, rhyme_group)
    groups: Dict[Tuple[int, int], List[Tuple[str, str, str]]] = defaultdict(list)
    group_meta: Dict[Tuple[int, int], Tuple[str, int, str]] = {}  # (skel, ml, cohort)

    for song_id, rhyme_group, skel, ml, text_norm, cohort in rows:
        key = (song_id, rhyme_group)
        groups[key].append((text_norm or "", skel, cohort or ""))
        if key not in group_meta:
            group_meta[key] = (skel, ml, cohort or "")

    # Extract word pairs from each group
    pair_counter: Counter = Counter()  # (word_a, word_b, skel, ml) → count
    drill_counter: Counter = Counter()
    pop_counter: Counter = Counter()

    for key, lines in groups.items():
        if len(lines) < 2:
            continue
        skel, ml, cohort = group_meta[key]
        last_words: List[str] = []
        for text_norm, _, _ in lines:
            words = _WORD_RE.findall(text_norm or "")
            if words:
                last_words.append(words[-1].lower())

        for i in range(len(last_words)):
            for j in range(i + 1, len(last_words)):
                wa, wb = last_words[i], last_words[j]
                if wa == wb:
                    continue
                # Sort alphabetically for dedup
                if wa > wb:
                    wa, wb = wb, wa
                pair_key = (wa, wb, skel, ml)
                pair_counter[pair_key] += 1
                if cohort == "drill_trap":
                    drill_counter[pair_key] += 1
                elif cohort == "pop":
                    pop_counter[pair_key] += 1

    # Insert into rhyme_pairs
    inserted = 0
    for (wa, wb, skel, ml), freq in pair_counter.items():
        dc = drill_counter.get((wa, wb, skel, ml), 0)
        pc = pop_counter.get((wa, wb, skel, ml), 0)
        # Cohort assignment
        if dc > 0 and pc == 0:
            cohort_label = "drill_trap"
        elif pc > 0 and dc == 0:
            cohort_label = "pop"
        elif dc > 0 and pc > 0:
            cohort_label = "shared"
        else:
            cohort_label = None
        # Distinctiveness: log-ratio drill vs pop (per-10K normalization)
        total_drill = sum(drill_counter.values()) or 1
        total_pop = sum(pop_counter.values()) or 1
        drill_rate = dc / total_drill * 10000
        pop_rate = pc / total_pop * 10000
        if drill_rate + pop_rate > 0:
            distinctiveness = math.log10((drill_rate + 1) / (pop_rate + 1))
        else:
            distinctiveness = 0.0

        conn.execute(
            """INSERT INTO rhyme_pairs
               (vowel_skeleton, match_length, word_a, word_b,
                frequency, drill_count, pop_count, cohort, distinctiveness)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (skel, ml, wa, wb, freq, dc, pc, cohort_label, round(distinctiveness, 4)),
        )
        inserted += 1

    conn.commit()

    # Stats
    stats = {
        "total_pairs": inserted,
        "unique_skeletons": conn.execute(
            "SELECT COUNT(DISTINCT vowel_skeleton) FROM rhyme_pairs"
        ).fetchone()[0],
        "drill_pairs": conn.execute(
            "SELECT COUNT(*) FROM rhyme_pairs WHERE drill_count > 0"
        ).fetchone()[0],
        "pop_pairs": conn.execute(
            "SELECT COUNT(*) FROM rhyme_pairs WHERE pop_count > 0"
        ).fetchone()[0],
    }

    conn.close()
    return stats


# ── Lookup ────────────────────────────────────────────────────────────


def lookup_rhymes(
    word: str,
    cohort: Optional[str] = None,
    top_k: int = 10,
    min_frequency: int = 1,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Return attested rhyme partners for *word* from the corpus.

    Args:
        word: The word to find rhymes for (will be lowercased + ASCII-folded).
        cohort: Filter to 'drill_trap', 'pop', or 'shared'.  None = all.
        top_k: Maximum number of results.
        min_frequency: Minimum corpus frequency for a pair to be included.
        db_path: Path to lyrics.db.

    Returns:
        List of dicts with: word, vowel_skeleton, match_length, frequency,
        drill_count, pop_count, cohort, distinctiveness.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Normalize the input word the same way the corpus is normalized
    from toolshop.lyricsdb import normalize_text

    norm_word = normalize_text(word).strip().lower()
    if not norm_word:
        return []

    # Also compute the word's vowel skeleton for matching
    word_skel = _word_skeleton(norm_word)

    conn = sqlite3.connect(str(db_path))

    query = """SELECT word_a, word_b, vowel_skeleton, match_length,
                      frequency, drill_count, pop_count, cohort, distinctiveness
               FROM rhyme_pairs
               WHERE (word_a = ? OR word_b = ?) AND frequency >= ?"""
    params: List[Any] = [norm_word, norm_word, min_frequency]

    if cohort is not None:
        if cohort == "drill_trap":
            query += " AND drill_count > 0"
        elif cohort == "pop":
            query += " AND pop_count > 0"
        elif cohort == "shared":
            query += " AND cohort = 'shared'"

    query += " ORDER BY frequency DESC, match_length DESC LIMIT ?"
    params.append(top_k)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    results: List[Dict[str, Any]] = []
    for row in rows:
        wa, wb, skel, ml, freq, dc, pc, coh, dist = row
        # Return the partner word (not the input word)
        partner = wb if wa == norm_word else wa
        results.append({
            "word": partner,
            "vowel_skeleton": skel,
            "match_length": ml,
            "frequency": freq,
            "drill_count": dc,
            "pop_count": pc,
            "cohort": coh,
            "distinctiveness": dist,
        })
    return results


def rank_pairs(
    cohort: Optional[str] = None,
    min_frequency: int = 2,
    min_match_length: int = 2,
    top_k: int = 50,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Return top rhyme pairs ranked by frequency and match length.

    Args:
        cohort: Filter to 'drill_trap', 'pop', or 'shared'.  None = all.
        min_frequency: Minimum corpus frequency.
        min_match_length: Minimum vowel-skeleton match length.
        top_k: Maximum number of results.
        db_path: Path to lyrics.db.

    Returns:
        List of dicts with: word_a, word_b, vowel_skeleton, match_length,
        frequency, drill_count, pop_count, cohort, distinctiveness.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(str(db_path))

    query = """SELECT word_a, word_b, vowel_skeleton, match_length,
                      frequency, drill_count, pop_count, cohort, distinctiveness
               FROM rhyme_pairs
               WHERE frequency >= ? AND match_length >= ?"""
    params: List[Any] = [min_frequency, min_match_length]

    if cohort is not None:
        if cohort == "drill_trap":
            query += " AND drill_count > 0"
        elif cohort == "pop":
            query += " AND pop_count > 0"
        elif cohort == "shared":
            query += " AND cohort = 'shared'"

    query += " ORDER BY frequency DESC, match_length DESC LIMIT ?"
    params.append(top_k)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    results: List[Dict[str, Any]] = []
    for row in rows:
        wa, wb, skel, ml, freq, dc, pc, coh, dist = row
        results.append({
            "word_a": wa,
            "word_b": wb,
            "vowel_skeleton": skel,
            "match_length": ml,
            "frequency": freq,
            "drill_count": dc,
            "pop_count": pc,
            "cohort": coh,
            "distinctiveness": dist,
        })
    return results
