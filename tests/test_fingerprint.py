"""Tests for toolshop.fingerprint — per-artist pro fingerprints from persisted data."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from toolshop.lyricsdb import build_database
from toolshop.fingerprint import (
    build_fingerprint,
    build_cohort_fingerprint,
    render_fingerprint_md,
    render_report,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lyrics_min"


# ── Helpers ───────────────────────────────────────────────────────────


def _seed_fingerprint_data(conn: sqlite3.Connection) -> None:
    """Insert song_rhyme_metrics, song_metrics, tokens, entities, topics,
    and section_topics rows for two artists so fingerprint functions have
    realistic data to aggregate.

    Uses the songs/sections/lines already created by build_database.
    """
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    # Update song artists + cohorts to match target artists
    songs = cur.execute("SELECT id, title FROM songs ORDER BY id").fetchall()
    if len(songs) < 3:
        pytest.skip("Fixture DB has fewer than 3 songs")

    # Assign songs to known artists
    song_ids = [s[0] for s in songs]
    # Song 0,1 → "Test Artist A" (drill_trap), Song 2 → "Test Artist B" (pop)
    cur.execute(
        "UPDATE songs SET primary_artist=?, role='solo', genre_cohort='drill_trap' WHERE id=?",
        ("Test Artist A", song_ids[0]),
    )
    cur.execute(
        "UPDATE songs SET primary_artist=?, role='solo', genre_cohort='drill_trap' WHERE id=?",
        ("Test Artist A", song_ids[1]),
    )
    cur.execute(
        "UPDATE songs SET primary_artist=?, role='solo', genre_cohort='pop' WHERE id=?",
        ("Test Artist B", song_ids[2]),
    )

    # Delete existing metrics rows (build_database already inserted some)
    cur.execute("DELETE FROM song_metrics")
    cur.execute("DELETE FROM song_rhyme_metrics")

    # Insert song_metrics for each song
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

    # Insert song_rhyme_metrics for each song
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

    # Insert tokens for distinctive vocabulary
    # Get line_ids for each song
    for sid in song_ids:
        line_ids = cur.execute(
            "SELECT l.id FROM lines l JOIN sections s ON l.section_id=s.id WHERE s.song_id=? ORDER BY l.id LIMIT 5",
            (sid,),
        ).fetchall()
        if not line_ids:
            continue
        for ordinal, (line_id,) in enumerate(line_ids):
            # Insert a few tokens with different UPOS
            tokens = [
                ("brat", "brat", "NOUN", 0),
                ("grad", "grad", "NOUN", 0),
                ("on", "on", "PRON", 0),  # should be filtered out
                ("i", "i", "CCONJ", 0),   # should be filtered out
                ("zmija", "zmija", "NOUN", 0),
            ]
            for tok_ordinal, (form, lemma, upos, is_oov) in enumerate(tokens):
                cur.execute(
                    """INSERT INTO tokens
                       (line_id, ordinal, form, lemma, upos, feats, is_oov, source_script)
                       VALUES (?, ?, ?, ?, ?, NULL, ?, 'latin')""",
                    (line_id, tok_ordinal, form, lemma, upos, is_oov),
                )

    # Insert entities
    for sid in song_ids[:2]:
        section_id = cur.execute(
            "SELECT id FROM sections WHERE song_id=? LIMIT 1", (sid,)
        ).fetchone()[0]
        line_id = cur.execute(
            "SELECT l.id FROM lines l JOIN sections s ON l.section_id=s.id WHERE s.song_id=? LIMIT 1",
            (sid,),
        ).fetchone()[0]
        cur.execute(
            "INSERT INTO entities (song_id, section_id, line_id, text, ner_type) VALUES (?, ?, ?, ?, ?)",
            (sid, section_id, line_id, "Beograd", "LOC"),
        )
        cur.execute(
            "INSERT INTO entities (song_id, section_id, line_id, text, ner_type) VALUES (?, ?, ?, ?, ?)",
            (sid, section_id, line_id, "Jala", "PER"),
        )

    # Insert topics + section_topics
    for sid in song_ids:
        section_id = cur.execute(
            "SELECT id FROM sections WHERE song_id=? LIMIT 1", (sid,)
        ).fetchone()[0]
        cur.execute(
            "INSERT OR IGNORE INTO topics (topic_id, label, top_terms, size, exemplar_section_id) VALUES (?, ?, ?, ?, ?)",
            (0, "street_life", json.dumps(["grad", "brat"]), 10, section_id),
        )
        cur.execute(
            "INSERT OR IGNORE INTO topics (topic_id, label, top_terms, size, exemplar_section_id) VALUES (?, ?, ?, ?, ?)",
            (1, "love", json.dumps(["srce", "ljubav"]), 8, section_id),
        )
        cur.execute(
            "INSERT OR IGNORE INTO section_topics (section_id, topic_id, probability) VALUES (?, ?, ?)",
            (section_id, 0, 0.8),
        )
        cur.execute(
            "INSERT OR IGNORE INTO section_topics (section_id, topic_id, probability) VALUES (?, ?, ?)",
            (section_id, 1, 0.5),
        )

    conn.commit()


@pytest.fixture
def fp_db(tmp_path):
    """Build a fixture DB and seed it with fingerprint test data."""
    db_path = tmp_path / "test_fp.db"
    build_database(root=FIXTURE_ROOT, db_path=db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    _seed_fingerprint_data(conn)
    yield conn
    conn.close()


# ── Tests ─────────────────────────────────────────────────────────────


def test_fingerprint_returns_dict(fp_db):
    """build_fingerprint returns a dict with expected top-level keys."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    assert isinstance(fp, dict)
    expected_keys = {"artist", "cohort", "song_count", "rhyme_craft", "structure", "lexical", "content"}
    assert expected_keys <= set(fp.keys())


def test_fingerprint_song_count(fp_db):
    """Fingerprint should report correct solo song count."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    assert fp["song_count"] == 2


def test_fingerprint_rhyme_craft(fp_db):
    """Rhyme craft section has median RF, IQR, %multis, internal rate, schemes, vowel pairs."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    rc = fp["rhyme_craft"]
    assert "rhyme_factor_median" in rc
    assert "rhyme_factor_iqr" in rc
    assert "pct_multis_median" in rc
    assert "internal_rhyme_rate_median" in rc
    assert "dominant_schemes" in rc
    assert "top_vowel_pairs" in rc
    # Artist A has RF 0.55 and 0.65 → median 0.6
    assert rc["rhyme_factor_median"] == pytest.approx(0.6, abs=0.01)


def test_fingerprint_structure(fp_db):
    """Structure section has section-type distribution, avg sections, avg lines, refren share, hook repetition."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    st = fp["structure"]
    assert "section_type_distribution" in st
    assert "avg_sections_per_song" in st
    assert "avg_lines_per_section" in st
    assert "refren_share" in st
    assert "hook_repetition_ratio" in st


def test_fingerprint_lexical(fp_db):
    """Lexical section has TTR, syllables distribution, distinctive vocabulary top-20."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    lex = fp["lexical"]
    assert "ttr_median" in lex
    assert "syllables_per_line_median" in lex
    assert "distinctive_vocabulary" in lex
    # Distinctive vocabulary should be a list of (word, freq) pairs
    assert isinstance(lex["distinctive_vocabulary"], list)
    # PRON and CCONJ should be filtered out
    vocab_words = [item[0] if isinstance(item, (list, tuple)) else item for item in lex["distinctive_vocabulary"]]
    assert "on" not in vocab_words  # PRON filtered
    assert "i" not in vocab_words   # CCONJ filtered
    assert "brat" in vocab_words or "grad" in vocab_words or "zmija" in vocab_words


def test_fingerprint_content(fp_db):
    """Content section has top entities (PER/LOC/ORG) and top-5 topics with shares."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    ct = fp["content"]
    assert "top_entities" in ct
    assert "top_topics" in ct
    # Entities should be separated by type
    entities = ct["top_entities"]
    assert "PER" in entities or "LOC" in entities
    # Topics should have label + share
    topics = ct["top_topics"]
    assert isinstance(topics, list)
    if topics:
        assert len(topics[0]) == 2  # (label, share)


def test_cohort_fingerprint(fp_db):
    """build_cohort_fingerprint aggregates across all solo artists in a cohort."""
    fp = build_cohort_fingerprint(fp_db, "drill_trap")
    assert isinstance(fp, dict)
    assert fp["cohort"] == "drill_trap"
    assert fp["song_count"] == 2  # Test Artist A has 2 songs, both drill_trap
    assert "rhyme_craft" in fp
    assert "structure" in fp


def test_fingerprint_cohort_pop(fp_db):
    """Cohort fingerprint for pop should find Test Artist B's 1 song."""
    fp = build_cohort_fingerprint(fp_db, "pop")
    assert fp["cohort"] == "pop"
    assert fp["song_count"] == 1


def test_fingerprint_no_songs(fp_db):
    """Fingerprint for a non-existent artist should return song_count=0."""
    fp = build_fingerprint(fp_db, "Nonexistent Artist")
    assert fp["song_count"] == 0


def test_fingerprint_golden_snapshot(fp_db):
    """Golden snapshot: build_fingerprint for Test Artist A produces deterministic output."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    # Verify key numeric values are stable
    assert fp["artist"] == "Test Artist A"
    assert fp["cohort"] == "drill_trap"
    assert fp["song_count"] == 2
    rc = fp["rhyme_craft"]
    assert rc["rhyme_factor_median"] == pytest.approx(0.6, abs=0.01)
    assert rc["pct_multis_median"] == pytest.approx(0.85, abs=0.01)
    # Schemes: AABB and ABAB each appear once
    schemes = rc["dominant_schemes"]
    assert isinstance(schemes, dict)
    assert schemes.get("AABB") == 1
    assert schemes.get("ABAB") == 1


def test_render_fingerprint_md(fp_db):
    """render_fingerprint_md produces a markdown string with expected sections."""
    fp = build_fingerprint(fp_db, "Test Artist A")
    md = render_fingerprint_md(fp)
    assert isinstance(md, str)
    assert "Test Artist A" in md
    assert "drill_trap" in md
    assert "Rhyme Craft" in md or "Rhyme" in md
    assert "Structure" in md
    assert "Lexical" in md or "Vocabulary" in md
    assert "Content" in md or "Topics" in md
    # No lyric text should appear
    assert "text_raw" not in md
    assert "text_norm" not in md


def test_render_report(fp_db):
    """render_report produces a full markdown report string."""
    md = render_report(
        fp_db,
        artists=["Test Artist A", "Test Artist B"],
        cohorts=["drill_trap", "pop"],
    )
    assert isinstance(md, str)
    assert "Pro Fingerprints" in md or "Fingerprints" in md
    # Should contain artist pages
    assert "Test Artist A" in md
    assert "Test Artist B" in md
    # Should contain cohort pages
    assert "drill_trap" in md
    assert "pop" in md
