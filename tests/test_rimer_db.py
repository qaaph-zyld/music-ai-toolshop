"""Tests for toolshop.rimer_db — attested pro rhyme pairs from the corpus."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from toolshop.lyricsdb import build_database
from toolshop.rimer_db import (
    build_rimer_db,
    lookup_rhymes,
    rank_pairs,
    _RIMER_SCHEMA,
)

# Debt 13b: never point build_database() at the TRACKED fixture - it writes
# _dedup_log.json back into `root` and dirties the tree. See _fixture_support.
from _fixture_support import LYRICS_MIN_FIXTURE as FIXTURE_ROOT


# ── Helpers ───────────────────────────────────────────────────────────


def _seed_rhyme_data(conn: sqlite3.Connection) -> None:
    """Insert line_rhymes rows for songs in different cohorts.

    Uses the songs/sections/lines already created by build_database.
    Creates rhyme groups that pair different end-words so the rimer DB
    has actual word pairs to extract.
    """
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    songs = cur.execute("SELECT id FROM songs ORDER BY id").fetchall()
    if len(songs) < 3:
        pytest.skip("Fixture DB has fewer than 3 songs")

    song_ids = [s[0] for s in songs]

    # Assign cohorts: songs 0,1 → drill_trap; song 2 → pop
    for sid in song_ids[:2]:
        cur.execute(
            "UPDATE songs SET primary_artist='Drill Artist', role='solo', genre_cohort='drill_trap' WHERE id=?",
            (sid,),
        )
    cur.execute(
        "UPDATE songs SET primary_artist='Pop Artist', role='solo', genre_cohort='pop' WHERE id=?",
        (song_ids[2],),
    )

    # Get line IDs for each song
    line_ids_by_song: dict[int, list[int]] = {}
    for sid in song_ids:
        rows = cur.execute(
            "SELECT l.id FROM lines l JOIN sections s ON l.section_id=s.id WHERE s.song_id=? ORDER BY l.id",
            (sid,),
        ).fetchall()
        line_ids_by_song[sid] = [r[0] for r in rows]

    # Clear existing line_rhymes
    cur.execute("DELETE FROM line_rhymes")

    # Build rhyme groups using available lines per song.
    # Each group needs 2+ lines from the same song with the same vowel_skeleton.
    # We assign skeletons that will produce word pairs from the fixture text.
    #
    # Song 0 (alpha) lines: "here", "here", "tonight", "everything", "song", "long"
    #   Group 0: lines[0]+lines[1] → "here"/"here" → same word, skipped by rimer
    #   Group 1: lines[4]+lines[5] → "song"/"long" → different words! skeleton "o"
    #   Group 2: lines[2]+lines[3] → "tonight"/"everything" → different, skeleton "e"
    #
    # Song 1 (beta) lines: "rec", "lep", "brzo" (after cyrtranslit+ASCII fold)
    #   Group 0: lines[0]+lines[1] → "rec"/"lep" → different words, skeleton "e"
    #
    # Song 2 (multi) lines: "kamineto", "kamineto", "zdravo", "kamineto", "kamineto"
    #   Group 0: lines[0]+lines[2] → "kamineto"/"zdravo" → different, skeleton "aoe"/"ao" → use "oe"
    #   Group 1: lines[1]+lines[3] → "kamineto"/"kamineto" → same word, skipped

    rhyme_groups: list[tuple[int, list[int], str, int]] = []

    # Song 0: use lines that have different end words
    s0 = line_ids_by_song[song_ids[0]]
    if len(s0) >= 6:
        rhyme_groups.append((song_ids[0], [s0[4], s0[5]], "o", 1))   # "song"/"long"
        rhyme_groups.append((song_ids[0], [s0[2], s0[3]], "e", 1))   # "tonight"/"everything"
    elif len(s0) >= 4:
        rhyme_groups.append((song_ids[0], [s0[2], s0[3]], "e", 1))
    elif len(s0) >= 2:
        rhyme_groups.append((song_ids[0], [s0[0], s0[1]], "ie", 2))

    # Song 1 (drill): use first 2 lines
    s1 = line_ids_by_song[song_ids[1]]
    if len(s1) >= 2:
        rhyme_groups.append((song_ids[1], [s1[0], s1[1]], "e", 1))

    # Song 2 (pop): use lines with different end words
    s2 = line_ids_by_song[song_ids[2]]
    if len(s2) >= 3:
        rhyme_groups.append((song_ids[2], [s2[0], s2[2]], "oe", 2))  # "kamineto"/"zdravo"
    elif len(s2) >= 2:
        rhyme_groups.append((song_ids[2], [s2[0], s2[1]], "oe", 2))

    # Insert each group with a unique (song_id, rhyme_group) key
    group_counter: dict[int, int] = {}
    for song_id, line_ids, skel, ml in rhyme_groups:
        gnum = group_counter.get(song_id, 0)
        group_counter[song_id] = gnum + 1
        for lid in line_ids:
            cur.execute(
                """INSERT INTO line_rhymes
                   (song_id, line_id, rhyme_group, rhyme_type, vowel_skeleton, match_length, position)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (song_id, lid, gnum, "end", skel, ml, "end"),
            )

    conn.commit()


@pytest.fixture
def rimer_db(tmp_path):
    """Build a fixture DB and seed it with rhyme data, then build rimer DB."""
    db_path = tmp_path / "test_rimer.db"
    build_database(root=FIXTURE_ROOT, db_path=db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    _seed_rhyme_data(conn)
    conn.close()
    build_rimer_db(db_path)
    return db_path


# ── Build tests ───────────────────────────────────────────────────────


def test_build_rimer_db_returns_stats(rimer_db):
    """build_rimer_db returns a stats dict with expected keys."""
    stats = build_rimer_db(rimer_db)
    assert isinstance(stats, dict)
    assert "total_pairs" in stats
    assert "unique_skeletons" in stats
    assert "drill_pairs" in stats
    assert "pop_pairs" in stats
    assert stats["total_pairs"] > 0


def test_build_rimer_db_idempotent(rimer_db):
    """Building twice produces the same result."""
    stats1 = build_rimer_db(rimer_db)
    stats2 = build_rimer_db(rimer_db)
    assert stats1 == stats2


def test_rhyme_pairs_table_exists(rimer_db):
    """rhyme_pairs table is created with expected columns."""
    conn = sqlite3.connect(str(rimer_db))
    cols = conn.execute("PRAGMA table_info(rhyme_pairs)").fetchall()
    col_names = {c[1] for c in cols}
    expected = {
        "id", "vowel_skeleton", "match_length", "word_a", "word_b",
        "frequency", "drill_count", "pop_count", "cohort", "distinctiveness",
    }
    assert expected <= col_names
    conn.close()


# ── Lookup tests ──────────────────────────────────────────────────────


def test_lookup_rhymes_returns_results(rimer_db):
    """lookup_rhymes returns attested partners for a word in the corpus."""
    # The fixture lines contain "here" as end word in multiple lines
    # After seeding, "tonight" and "everything" are in rhyme groups
    # We need to check what words actually got paired
    conn = sqlite3.connect(str(rimer_db))
    # Check what pairs exist
    rows = conn.execute("SELECT word_a, word_b, frequency FROM rhyme_pairs LIMIT 5").fetchall()
    conn.close()
    if not rows:
        pytest.skip("No rhyme pairs generated from fixture")

    # Pick a word from the first pair and look it up
    word = rows[0][0]
    results = lookup_rhymes(word, db_path=rimer_db)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all("word" in r for r in results)
    assert all("frequency" in r for r in results)


def test_lookup_rhymes_unknown_word(rimer_db):
    """lookup_rhymes returns empty list for a word not in the corpus."""
    results = lookup_rhymes("nonexistentword", db_path=rimer_db)
    assert results == []


def test_lookup_rhymes_cohort_filter(rimer_db):
    """lookup_rhymes with cohort filter returns only matching pairs."""
    conn = sqlite3.connect(str(rimer_db))
    # Find a word that has both drill and pop pairs
    rows = conn.execute(
        """SELECT word_a, word_b FROM rhyme_pairs
           WHERE drill_count > 0 AND pop_count > 0 LIMIT 1"""
    ).fetchall()
    conn.close()

    if not rows:
        pytest.skip("No shared pairs in fixture")

    word = rows[0][0]
    drill_results = lookup_rhymes(word, cohort="drill_trap", db_path=rimer_db)
    pop_results = lookup_rhymes(word, cohort="pop", db_path=rimer_db)

    assert all(r["drill_count"] > 0 for r in drill_results)
    assert all(r["pop_count"] > 0 for r in pop_results)


def test_lookup_rhymes_top_k(rimer_db):
    """lookup_rhymes respects top_k limit."""
    conn = sqlite3.connect(str(rimer_db))
    rows = conn.execute("SELECT word_a FROM rhyme_pairs LIMIT 1").fetchall()
    conn.close()
    if not rows:
        pytest.skip("No pairs in fixture")

    word = rows[0][0]
    results = lookup_rhymes(word, top_k=1, db_path=rimer_db)
    assert len(results) <= 1


# ── Rank tests ────────────────────────────────────────────────────────


def test_rank_pairs_returns_results(rimer_db):
    """rank_pairs returns pairs sorted by frequency."""
    results = rank_pairs(min_frequency=1, top_k=10, db_path=rimer_db)
    assert isinstance(results, list)
    if len(results) >= 2:
        # Verify sorted by frequency descending
        assert results[0]["frequency"] >= results[1]["frequency"]


def test_rank_pairs_min_frequency(rimer_db):
    """rank_pairs respects min_frequency."""
    results = rank_pairs(min_frequency=100, top_k=10, db_path=rimer_db)
    assert all(r["frequency"] >= 100 for r in results)


def test_rank_pairs_cohort_filter(rimer_db):
    """rank_pairs with cohort filter returns only matching pairs."""
    drill_results = rank_pairs(cohort="drill_trap", min_frequency=1, top_k=50, db_path=rimer_db)
    assert all(r["drill_count"] > 0 for r in drill_results)


# ── Empty / edge cases ────────────────────────────────────────────────


def test_build_rimer_db_empty(tmp_path):
    """build_rimer_db on a DB with no line_rhymes produces empty table."""
    db_path = tmp_path / "empty.db"
    build_database(root=FIXTURE_ROOT, db_path=db_path)
    # Clear line_rhymes
    conn = sqlite3.connect(str(db_path))
    conn.execute("DELETE FROM line_rhymes")
    conn.commit()
    conn.close()

    stats = build_rimer_db(db_path)
    assert stats["total_pairs"] == 0
    assert stats["unique_skeletons"] == 0
