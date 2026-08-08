"""Tests for toolshop.draft_scorer — 5-component scoring with originality check."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from toolshop.lyricsdb import build_database
from toolshop.draft_scorer import (
    score_draft,
    _ngram_overlap,
    _extract_ngrams,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lyrics_min"


# ── Helpers ───────────────────────────────────────────────────────────


def _seed_scorer_data(conn: sqlite3.Connection) -> None:
    """Seed DB with metrics data for scoring tests."""
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    songs = cur.execute("SELECT id FROM songs ORDER BY id").fetchall()
    if len(songs) < 3:
        pytest.skip("Fixture DB has fewer than 3 songs")

    song_ids = [s[0] for s in songs]

    # Assign artists + cohorts
    for sid in song_ids[:2]:
        cur.execute(
            "UPDATE songs SET primary_artist='Test Artist A', role='solo', genre_cohort='drill_trap' WHERE id=?",
            (sid,),
        )
    cur.execute(
        "UPDATE songs SET primary_artist='Test Artist B', role='solo', genre_cohort='pop' WHERE id=?",
        (song_ids[2],),
    )

    # Insert song_metrics
    cur.execute("DELETE FROM song_metrics")
    cur.execute("DELETE FROM song_rhyme_metrics")
    for sid in song_ids:
        cur.execute(
            """INSERT INTO song_metrics
               (song_id, total_words, unique_words, ttr, line_count,
                avg_words_per_line, avg_syllables_per_line,
                hook_repetition_max, hook_repetition_ratio,
                english_loanword_rate, section_type_counts)
               VALUES (?, 100, 60, 0.6, 10, 10.0, 8.5, 3, 0.15, 0.05, ?)""",
            (sid, json.dumps({"refren": 1, "strofa": 2})),
        )

    rhyme_data = [
        (song_ids[0], 0.55, 0.80, 0.85, "AABB", json.dumps([["ae", 5], ["ou", 3]])),
        (song_ids[1], 0.65, 0.90, 0.75, "ABAB", json.dumps([["ae", 4], ["ii", 2]])),
        (song_ids[2], 0.75, 0.92, 0.70, "AABB", json.dumps([["ou", 6], ["ei", 4]])),
    ]
    for sid, rf, pm, ir, scheme, vp in rhyme_data:
        cur.execute(
            """INSERT INTO song_rhyme_metrics
               (song_id, rhyme_factor, pct_multis, internal_rhyme_rate,
                dominant_scheme, top_vowel_pairs)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sid, rf, pm, ir, scheme, vp),
        )

    conn.commit()


@pytest.fixture
def scorer_db(tmp_path):
    """Build a fixture DB and seed it with scorer data."""
    db_path = tmp_path / "test_scorer.db"
    build_database(root=FIXTURE_ROOT, db_path=db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    _seed_scorer_data(conn)
    conn.close()
    return db_path


@pytest.fixture
def draft_file(tmp_path):
    """Create a simple draft lyrics file."""
    draft = tmp_path / "draft.txt"
    draft.write_text(
        "[Strofa 1]\n"
        "Walking down the street tonight\n"
        "Money cash and everything\n"
        "Another verse for the song\n"
        "Words are flowing all night long\n"
        "\n"
        "[Refren]\n"
        "Test line one here\n"
        "Test line two here\n",
        encoding="utf-8",
    )
    return draft


# ── N-gram extraction tests ───────────────────────────────────────────


def test_extract_ngrams_basic():
    """_extract_ngrams returns expected tuples."""
    tokens = ["a", "b", "c", "d"]
    ngrams = _extract_ngrams(tokens, n=3)
    assert ("a", "b", "c") in ngrams
    assert ("b", "c", "d") in ngrams
    assert len(ngrams) == 2


def test_extract_ngrams_short_input():
    """_extract_ngrams returns empty set for tokens shorter than n."""
    assert _extract_ngrams(["a", "b"], n=3) == set()


# ── N-gram overlap tests ──────────────────────────────────────────────


def test_ngram_overlap_no_match(scorer_db):
    """Draft with completely novel text has 0% overlap."""
    text = "zzz qqq xxx yyy www vvv uuu ttt sss rrr"
    result = _ngram_overlap(text, n=3, db_path=scorer_db)
    assert result["overlap_pct"] == 0.0
    assert result["matched_ngrams"] == 0
    assert result["source_songs"] == []


def test_ngram_overlap_copies_corpus(scorer_db):
    """Draft that copies a corpus line has high overlap."""
    # The fixture contains "walking down the street tonight"
    text = "walking down the street tonight money cash and everything"
    result = _ngram_overlap(text, n=3, db_path=scorer_db)
    assert result["overlap_pct"] > 0
    assert result["matched_ngrams"] > 0
    # Should identify source songs
    if result["source_songs"]:
        assert "song_id" in result["source_songs"][0]
        assert "title" in result["source_songs"][0]


def test_ngram_overlap_empty_text(scorer_db):
    """Empty text returns 100% originality (no n-grams to match)."""
    result = _ngram_overlap("", n=3, db_path=scorer_db)
    assert result["overlap_pct"] == 100.0
    assert result["total_draft_ngrams"] == 0


# ── score_draft tests ─────────────────────────────────────────────────


def test_score_draft_returns_5_components(scorer_db, draft_file):
    """score_draft returns 5 component scores."""
    result = score_draft(draft_file, cohort="drill_trap", db_path=scorer_db)
    assert "overall_score" in result
    assert "components" in result
    components = result["components"]
    assert "structural" in components
    assert "rhyme" in components
    assert "lexical" in components
    assert "repetition" in components
    assert "originality" in components


def test_score_draft_overall_range(scorer_db, draft_file):
    """Overall score is in 0-100 range."""
    result = score_draft(draft_file, cohort="drill_trap", db_path=scorer_db)
    assert 0 <= result["overall_score"] <= 100


def test_score_draft_originality_component(scorer_db, draft_file):
    """Originality component has expected structure."""
    result = score_draft(draft_file, cohort="drill_trap", db_path=scorer_db)
    orig = result["components"]["originality"]
    assert "score" in orig
    assert "metrics" in orig
    assert "overlap_pct" in orig["metrics"]
    assert 0 <= orig["score"] <= 100


def test_score_draft_vs_artist(scorer_db, draft_file):
    """--vs mode uses per-artist baselines."""
    result = score_draft(draft_file, artist="Test Artist A", db_path=scorer_db)
    assert result["comparison_target"] == "Test Artist A"


def test_score_draft_vs_artist_differs_from_cohort(scorer_db, draft_file):
    """Per-artist scoring may differ from cohort scoring."""
    artist_result = score_draft(draft_file, artist="Test Artist A", db_path=scorer_db)
    cohort_result = score_draft(draft_file, cohort="drill_trap", db_path=scorer_db)
    # Comparison targets should differ
    assert artist_result["comparison_target"] != cohort_result["comparison_target"]
    # Both should have valid scores
    assert 0 <= artist_result["overall_score"] <= 100
    assert 0 <= cohort_result["overall_score"] <= 100


def test_score_draft_novel_text_high_originality(scorer_db, tmp_path):
    """Draft with completely novel text gets high originality score."""
    draft = tmp_path / "novel.txt"
    draft.write_text(
        "[Strofa 1]\n"
        "zzz qqq xxx yyy www\n"
        "vvv uuu ttt sss rrr\n"
        "nnn mmm lll kkk jjj\n"
        "iii hhh ggg fff eee\n"
        "\n"
        "[Refren]\n"
        "ddd ccc bbb aaa zzz\n"
        "yyy www vvv uuu ttt\n",
        encoding="utf-8",
    )
    result = score_draft(draft, cohort="drill_trap", db_path=scorer_db)
    orig = result["components"]["originality"]
    assert orig["score"] == 100.0
    assert orig["metrics"]["overlap_pct"] == 0.0


def test_score_draft_copies_corpus_low_originality(scorer_db, tmp_path):
    """Draft that copies corpus lines gets lower originality score."""
    draft = tmp_path / "copy.txt"
    draft.write_text(
        "[Strofa 1]\n"
        "Walking down the street tonight\n"
        "Money cash and everything\n"
        "Another verse for the song\n"
        "Words are flowing all night long\n"
        "\n"
        "[Refren]\n"
        "Test line one here\n"
        "Test line two here\n"
        "Walking down the street tonight\n"
        "Money cash and everything\n",
        encoding="utf-8",
    )
    result = score_draft(draft, cohort="drill_trap", db_path=scorer_db)
    orig = result["components"]["originality"]
    # Should have some overlap with corpus
    assert orig["metrics"]["overlap_pct"] > 0
    assert orig["score"] < 100.0


def test_score_draft_comparison_target_cohort(scorer_db, draft_file):
    """Without artist, comparison_target is the cohort."""
    result = score_draft(draft_file, cohort="pop", db_path=scorer_db)
    assert result["comparison_target"] == "pop"
