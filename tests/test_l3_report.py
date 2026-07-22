"""Tests for toolshop.l3_report — discrimination report and JSD."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from toolshop.l3_report import _jsd, generate_report


def _build_report_db(db_path: Path) -> None:
    """Build a minimal DB with tokens, slang_terms, topics, section_topics."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT,
            role TEXT, genre_cohort TEXT);
        CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
        CREATE TABLE lines (id INTEGER PRIMARY KEY, section_id INTEGER, ordinal INTEGER,
            text_raw TEXT, text_norm TEXT, word_count INTEGER, syllable_count INTEGER);
        CREATE TABLE tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, line_id INTEGER, ordinal INTEGER,
            form TEXT, lemma TEXT, upos TEXT, feats TEXT, is_oov INTEGER DEFAULT 0, source_script TEXT);
        CREATE TABLE entities (id INTEGER PRIMARY KEY AUTOINCREMENT, song_id INTEGER, section_id INTEGER,
            line_id INTEGER, text TEXT, ner_type TEXT);
        CREATE TABLE slang_terms (id INTEGER PRIMARY KEY AUTOINCREMENT, form TEXT, lemma TEXT,
            freq INTEGER, drill_freq REAL, pop_freq REAL, distinctiveness REAL, is_oov INTEGER DEFAULT 0);
        CREATE TABLE topics (topic_id INTEGER PRIMARY KEY, label TEXT, top_terms TEXT,
            size INTEGER, exemplar_section_id INTEGER);
        CREATE TABLE section_topics (section_id INTEGER NOT NULL, topic_id INTEGER NOT NULL,
            probability REAL, PRIMARY KEY (section_id, topic_id));
    """)

    # Songs: 2 drill, 2 pop
    conn.execute("INSERT INTO songs VALUES (1, 'D1', 'Buba', 'solo', 'drill_trap')")
    conn.execute("INSERT INTO songs VALUES (2, 'D2', 'Jala', 'solo', 'drill_trap')")
    conn.execute("INSERT INTO songs VALUES (3, 'P1', 'Nikolija', 'solo', 'pop')")
    conn.execute("INSERT INTO songs VALUES (4, 'P2', 'Senidah', 'solo', 'pop')")

    # Sections
    for sid in range(1, 9):
        song_id = (sid - 1) // 2 + 1
        conn.execute(f"INSERT INTO sections VALUES ({sid}, {song_id}, 'strofa', 1)")

    # Lines
    for sid in range(1, 9):
        conn.execute(f"INSERT INTO lines VALUES ({sid}, {sid}, 1, 'test', 'test', 1, 1)")

    # Tokens (minimal)
    conn.execute("INSERT INTO tokens (line_id, ordinal, form, lemma, upos, source_script) VALUES (1, 1, 'test', 'test', 'NOUN', 'latin')")

    # Entities
    conn.execute("INSERT INTO entities (song_id, section_id, line_id, text, ner_type) VALUES (1, 1, 1, 'Beograd', 'LOC')")

    # Slang terms: drill-distinctive and pop-distinctive
    conn.execute("INSERT INTO slang_terms (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov) VALUES ('brata', 'brat', 29, 1.85, 0.0, 2.23, 1)")
    conn.execute("INSERT INTO slang_terms (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov) VALUES ('swag', 'swag', 27, 1.72, 0.0, 2.15, 1)")
    conn.execute("INSERT INTO slang_terms (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov) VALUES ('twerka', 'twerka', 21, 0.0, 3.11, -2.85, 1)")
    conn.execute("INSERT INTO slang_terms (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov) VALUES ('nagrada', 'nagrada', 17, 0.0, 2.51, -2.59, 1)")

    # Topics
    conn.execute("INSERT INTO topics VALUES (0, '0_ona_je_joj_nju', '[\"ona\",\"je\"]', 100, 1)")
    conn.execute("INSERT INTO topics VALUES (1, '1_drip_braca_brat', '[\"drip\",\"braca\"]', 50, 3)")

    # Section topics: drill sections → topic 0,1; pop sections → topic 0 only
    for sid in range(1, 5):
        conn.execute(f"INSERT INTO section_topics VALUES ({sid}, 0, 0.9)")
    for sid in range(1, 3):
        conn.execute(f"INSERT INTO section_topics VALUES ({sid}, 1, 0.8)")
    for sid in range(5, 9):
        conn.execute(f"INSERT INTO section_topics VALUES ({sid}, 0, 0.9)")

    conn.commit()
    conn.close()


# ── JSD ───────────────────────────────────────────────────────────────

def test_jsd_identical_distributions():
    p = [1, 2, 3]
    q = [1, 2, 3]
    assert abs(_jsd(p, q)) < 0.001


def test_jsd_completely_different():
    p = [1, 0, 0]
    q = [0, 0, 1]
    assert _jsd(p, q) > 0.5  # high divergence


def test_jsd_different_lengths():
    p = [1, 2, 3]
    q = [1, 2]
    # Should not raise
    score = _jsd(p, q)
    assert score >= 0


def test_jsd_zero_distribution():
    p = [0, 0, 0]
    q = [1, 2, 3]
    assert _jsd(p, q) == 0.0


# ── Report generation ─────────────────────────────────────────────────

def test_generate_report_basic(tmp_path):
    db = tmp_path / "test.db"
    _build_report_db(db)
    conn = sqlite3.connect(db)

    report = generate_report(conn)

    assert "annotation" in report
    assert "slang" in report
    assert "themes" in report
    assert "gate_passed" in report

    assert report["slang"]["drill_distinctive"] >= 2
    assert report["slang"]["pop_distinctive"] >= 2
    assert report["slang"]["strong_terms"] >= 4  # all 4 have |dist| > 1

    conn.close()


def test_generate_report_gate_pass(tmp_path):
    db = tmp_path / "test.db"
    _build_report_db(db)
    conn = sqlite3.connect(db)

    report = generate_report(conn)
    assert report["gate_passed"] is True

    conn.close()


def test_generate_report_gate_fail_no_slang(tmp_path):
    db = tmp_path / "test.db"
    _build_report_db(db)
    conn = sqlite3.connect(db)

    # Remove all slang terms
    conn.execute("DELETE FROM slang_terms")
    conn.commit()

    report = generate_report(conn)
    assert report["gate_passed"] is False

    conn.close()
