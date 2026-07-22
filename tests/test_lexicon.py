"""Tests for toolshop.lexicon — OOV mining + cohort distinctiveness."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from toolshop.lexicon import (
    _compute_distinctiveness,
    mine_slang,
    get_slang_terms,
)


def _build_test_db(db_path: Path) -> None:
    """Build a minimal DB with tokens for slang mining."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT,
            role TEXT, genre_cohort TEXT);
        CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
        CREATE TABLE lines (id INTEGER PRIMARY KEY, section_id INTEGER, ordinal INTEGER,
            text_raw TEXT, text_norm TEXT, word_count INTEGER, syllable_count INTEGER);
        CREATE TABLE tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, line_id INTEGER, ordinal INTEGER,
            form TEXT, lemma TEXT, upos TEXT, feats TEXT, is_oov INTEGER DEFAULT 0, source_script TEXT);
        CREATE TABLE slang_terms (id INTEGER PRIMARY KEY AUTOINCREMENT, form TEXT, lemma TEXT,
            freq INTEGER, drill_freq REAL, pop_freq REAL, distinctiveness REAL, is_oov INTEGER DEFAULT 0);
    """)

    # Insert songs: 2 drill, 2 pop
    conn.execute("INSERT INTO songs VALUES (1, 'Drill1', 'Buba', 'solo', 'drill_trap')")
    conn.execute("INSERT INTO songs VALUES (2, 'Drill2', 'Jala', 'solo', 'drill_trap')")
    conn.execute("INSERT INTO songs VALUES (3, 'Pop1', 'Nikolija', 'solo', 'pop')")
    conn.execute("INSERT INTO songs VALUES (4, 'Pop2', 'Senidah', 'solo', 'pop')")
    conn.execute("INSERT INTO songs VALUES (5, 'Featured', 'X', 'featured', 'drill_trap')")

    # Sections
    for sid in range(1, 6):
        conn.execute(f"INSERT INTO sections VALUES ({sid}, {sid}, 'strofa', 1)")

    # Lines
    for sid in range(1, 6):
        conn.execute(f"INSERT INTO lines VALUES ({sid}, {sid}, 1, 'test', 'test', 1, 1)")

    # Tokens: 'brat' appears 10x in drill, 1x in pop (drill-distinctive)
    # 'ljubav' appears 1x in drill, 10x in pop (pop-distinctive)
    # 'i' appears equally (not distinctive, and is a CCONJ so excluded)
    drill_tokens = [
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("i", "i", "CCONJ", 0),
    ]
    pop_tokens = [
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("ljubav", "ljubav", "NOUN", 1),
        ("brat", "brat", "NOUN", 1),
        ("i", "i", "CCONJ", 0),
    ]

    ordinal = 1
    for lemma, form, upos, is_oov in drill_tokens:
        conn.execute(
            "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, is_oov, source_script) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, ordinal, form, lemma, upos, is_oov, "latin"),
        )
        ordinal += 1

    ordinal = 1
    for lemma, form, upos, is_oov in pop_tokens:
        conn.execute(
            "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, is_oov, source_script) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (3, ordinal, form, lemma, upos, is_oov, "latin"),
        )
        ordinal += 1

    conn.commit()
    conn.close()


# ── Distinctiveness score ─────────────────────────────────────────────

def test_distinctiveness_drill_heavy():
    score = _compute_distinctiveness(10.0, 1.0)
    assert score > 0  # positive = drill-distinctive


def test_distinctiveness_pop_heavy():
    score = _compute_distinctiveness(1.0, 10.0)
    assert score < 0  # negative = pop-distinctive


def test_distinctiveness_equal():
    score = _compute_distinctiveness(5.0, 5.0)
    assert abs(score) < 0.1  # near zero


def test_distinctiveness_zero_freq():
    # Should not raise on zero frequencies
    score = _compute_distinctiveness(0.0, 0.0)
    assert score == 0.0  # log2(0.5/0.5) = 0


# ── Mine slang ────────────────────────────────────────────────────────

def test_mine_slang_basic(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    summary = mine_slang(conn)

    # 'brat' and 'ljubav' both have total freq >= 3
    assert summary["total_terms"] >= 2

    # Check that 'brat' is drill-distinctive
    terms = get_slang_terms(conn, cohort="drill_trap", top=10)
    forms = [t["form"] for t in terms]
    assert "brat" in forms

    # Check that 'ljubav' is pop-distinctive
    terms = get_slang_terms(conn, cohort="pop", top=10)
    forms = [t["form"] for t in terms]
    assert "ljubav" in forms

    conn.close()


def test_mine_slang_excludes_featured(tmp_path):
    """Featured songs should be excluded from cohort frequency."""
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    # Add tokens to the featured song (song 5, line 5)
    for i in range(20):
        conn.execute(
            "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, is_oov, source_script) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (5, i + 1, "featured_word", "featured_word", "NOUN", 1, "latin"),
        )
    conn.commit()

    summary = mine_slang(conn)
    terms = get_slang_terms(conn, top=100)
    forms = [t["form"] for t in terms]
    # 'featured_word' should not appear because it's from a featured song
    assert "featured_word" not in forms

    conn.close()


def test_mine_slang_excludes_function_words(tmp_path):
    """PUNCT, ADP, AUX, etc. should be excluded."""
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    # Add punctuation tokens
    for i in range(20):
        conn.execute(
            "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, is_oov, source_script) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 100 + i, ".", ".", "PUNCT", 0, "latin"),
        )
    conn.commit()

    mine_slang(conn)
    terms = get_slang_terms(conn, top=100)
    forms = [t["form"] for t in terms]
    assert "." not in forms

    conn.close()


def test_get_slang_terms_all(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    mine_slang(conn)
    terms = get_slang_terms(conn, top=100)
    assert len(terms) >= 2

    conn.close()
