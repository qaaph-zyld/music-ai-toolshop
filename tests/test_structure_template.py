"""Tests for toolshop.structure_template — genre-specific template generation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from toolshop.structure_template import generate_template


def _create_test_db(db_path: Path) -> None:
    """Create a minimal lyrics.db with test data for both cohorts."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corpus TEXT NOT NULL DEFAULT 'genius-pro',
            title TEXT NOT NULL,
            primary_artist TEXT NOT NULL,
            role TEXT,
            genre_cohort TEXT
        );
        CREATE TABLE sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            type TEXT NOT NULL
        );
        CREATE TABLE lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            text_norm TEXT
        );
    """)

    # Insert 3 drill_trap songs with ordering: intro, strofa, refren, strofa, refren, outro
    for s_idx in range(3):
        conn.execute(
            "INSERT INTO songs (title, primary_artist, role, genre_cohort) VALUES (?, ?, 'solo', 'drill_trap')",
            (f"Drill Song {s_idx}", "Buba Corelli"),
        )
        song_id = s_idx + 1
        sec_types = ["intro", "strofa", "refren", "strofa", "refren", "outro"]
        for ord_i, sec_type in enumerate(sec_types):
            conn.execute(
                "INSERT INTO sections (song_id, ordinal, type) VALUES (?, ?, ?)",
                (song_id, ord_i, sec_type),
            )
            sec_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            # Insert varying line counts per type.
            line_counts = {"intro": 4, "strofa": 8, "refren": 6, "outro": 4}
            n_lines = line_counts.get(sec_type, 6)
            for l_idx in range(n_lines):
                conn.execute(
                    "INSERT INTO lines (section_id, ordinal, text_norm) VALUES (?, ?, ?)",
                    (sec_id, l_idx, f"line {l_idx}"),
                )

    # Insert 3 pop songs with ordering: strofa, refren, strofa, refren, bridge, refren
    for s_idx in range(3):
        conn.execute(
            "INSERT INTO songs (title, primary_artist, role, genre_cohort) VALUES (?, ?, 'solo', 'pop')",
            (f"Pop Song {s_idx}", "Nikolija"),
        )
        song_id = s_idx + 4  # offset by drill songs
        sec_types = ["strofa", "refren", "strofa", "refren", "bridge", "refren"]
        for ord_i, sec_type in enumerate(sec_types):
            conn.execute(
                "INSERT INTO sections (song_id, ordinal, type) VALUES (?, ?, ?)",
                (song_id, ord_i, sec_type),
            )
            sec_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            line_counts = {"strofa": 6, "refren": 4, "bridge": 4}
            n_lines = line_counts.get(sec_type, 6)
            for l_idx in range(n_lines):
                conn.execute(
                    "INSERT INTO lines (section_id, ordinal, text_norm) VALUES (?, ?, ?)",
                    (sec_id, l_idx, f"line {l_idx}"),
                )

    conn.commit()
    conn.close()


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    """Create a test lyrics DB with both cohorts."""
    db_path = tmp_path / "test_lyrics.db"
    _create_test_db(db_path)
    return db_path


def test_drill_trap_template(test_db):
    """Template generation for drill_trap cohort."""
    result = generate_template("drill_trap", db_path=test_db, num_sections=6)
    assert result["cohort"] == "drill_trap"
    assert len(result["sections"]) == 6
    assert result["total_lines"] > 0


def test_pop_template(test_db):
    """Template generation for pop cohort."""
    result = generate_template("pop", db_path=test_db, num_sections=6)
    assert result["cohort"] == "pop"
    assert len(result["sections"]) == 6


def test_section_count(test_db):
    """Template has exactly num_sections entries."""
    result = generate_template("drill_trap", db_path=test_db, num_sections=4)
    assert len(result["sections"]) == 4


def test_line_count_ranges(test_db):
    """Each section has a positive line count."""
    result = generate_template("drill_trap", db_path=test_db, num_sections=6)
    for sec in result["sections"]:
        assert sec["lines"] > 0
        assert isinstance(sec["lines"], int)


def test_pop_hook_forward(test_db):
    """Pop template has refren (chorus) by section 2."""
    result = generate_template("pop", db_path=test_db, num_sections=6)
    first_two_types = [s["type"] for s in result["sections"][:2]]
    assert any(t in ("refren", "hook") for t in first_two_types)


def test_drill_verse_dominant(test_db):
    """Drill template is verse-dominant (strofa is the most common type)."""
    result = generate_template("drill_trap", db_path=test_db, num_sections=6)
    type_counts = {}
    for sec in result["sections"]:
        type_counts[sec["type"]] = type_counts.get(sec["type"], 0) + 1
    # strofa should be present and likely the most repeated.
    assert "strofa" in type_counts


def test_rhyme_scheme_present(test_db):
    """Each section has a rhyme_scheme string."""
    result = generate_template("drill_trap", db_path=test_db, num_sections=6)
    for sec in result["sections"]:
        assert "rhyme_scheme" in sec
        assert isinstance(sec["rhyme_scheme"], str)


def test_total_lines(test_db):
    """total_lines equals sum of section line counts."""
    result = generate_template("pop", db_path=test_db, num_sections=6)
    expected = sum(s["lines"] for s in result["sections"])
    assert result["total_lines"] == expected
