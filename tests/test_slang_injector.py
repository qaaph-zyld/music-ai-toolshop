"""Tests for toolshop.slang_injector — slang injection post-processor."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from toolshop.slang_injector import inject_slang


# ── Test DB fixture ───────────────────────────────────────────────────

_SAMPLE_LYRICS = """\
[Verse 1]
novac novac svuda grad
popac popac svuda brat
zdravo svete kako si
prijatelju moj ti

[Chorus]
babone babone
popac popac
babone babone
popac popac
"""


def _make_slang_db(db_path: Path) -> None:
    """Create a minimal lyrics.db with slang_terms table and sample data."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS slang_terms (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            form            TEXT,
            lemma           TEXT,
            freq            INTEGER,
            drill_freq      REAL,
            pop_freq        REAL,
            distinctiveness REAL,
            is_oov          INTEGER DEFAULT 0
        )"""
    )
    # Insert drill-distinctive terms (positive distinctiveness)
    sample_terms = [
        ("braca", "brat", 10, 15.0, 1.0, 3.9, 1),
        ("sange", "sanga", 8, 12.0, 0.5, 4.6, 1),
        ("game", "game", 6, 9.0, 1.0, 3.2, 1),
        ("blok", "blok", 5, 8.0, 0.5, 4.0, 1),
        ("cash", "cash", 4, 7.0, 0.5, 3.8, 1),
    ]
    for form, lemma, freq, drill, pop, dist, oov in sample_terms:
        conn.execute(
            "INSERT INTO slang_terms (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (form, lemma, freq, drill, pop, dist, oov),
        )
    conn.commit()
    conn.close()


# ── Slang replacement ─────────────────────────────────────────────────

def test_slang_replacement_produces_modified_text(tmp_path: Path):
    """inject_slang returns modified text different from original."""
    db_path = tmp_path / "test.db"
    _make_slang_db(db_path)

    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_SAMPLE_LYRICS, encoding="utf-8")

    result = inject_slang(lyrics_file, cohort="drill_trap", density=0.1, db_path=db_path)

    assert "modified_text" in result
    assert "injections" in result
    assert "final_density" in result
    assert "cohort" in result
    assert result["cohort"] == "drill_trap"
    # With density 0.1 and enough candidates, should have some injections
    if result["injections"]:
        modified = result["modified_text"]
        assert modified != _SAMPLE_LYRICS


def test_injection_logging(tmp_path: Path):
    """Each injection has line, original, replacement, distinctiveness."""
    db_path = tmp_path / "test.db"
    _make_slang_db(db_path)

    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_SAMPLE_LYRICS, encoding="utf-8")

    result = inject_slang(lyrics_file, cohort="drill_trap", density=0.15, db_path=db_path)

    for inj in result["injections"]:
        assert "line" in inj
        assert "original" in inj
        assert "replacement" in inj
        assert "distinctiveness" in inj
        assert isinstance(inj["line"], int)
        assert inj["line"] >= 1  # 1-indexed


# ── Density calculation ───────────────────────────────────────────────

def test_density_calculation(tmp_path: Path):
    """final_density is a float between 0 and 1."""
    db_path = tmp_path / "test.db"
    _make_slang_db(db_path)

    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_SAMPLE_LYRICS, encoding="utf-8")

    result = inject_slang(lyrics_file, cohort="drill_trap", density=0.2, db_path=db_path)

    assert isinstance(result["final_density"], float)
    assert 0.0 <= result["final_density"] <= 1.0


# ── Cohort filtering ──────────────────────────────────────────────────

def test_cohort_filter_drill(tmp_path: Path):
    """drill_trap cohort loads terms with positive distinctiveness."""
    db_path = tmp_path / "test.db"
    _make_slang_db(db_path)

    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_SAMPLE_LYRICS, encoding="utf-8")

    result = inject_slang(lyrics_file, cohort="drill_trap", density=0.1, db_path=db_path)

    # All injected terms should be from drill-distinctive set
    for inj in result["injections"]:
        assert inj["distinctiveness"] > 0.5


def test_cohort_filter_pop_returns_empty(tmp_path: Path):
    """pop cohort with only drill-distinctive terms returns no injections."""
    db_path = tmp_path / "test.db"
    _make_slang_db(db_path)

    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_SAMPLE_LYRICS, encoding="utf-8")

    result = inject_slang(lyrics_file, cohort="pop", density=0.1, db_path=db_path)

    assert result["injections"] == []
    assert result["final_density"] == 0.0


# ── No slang terms in DB ──────────────────────────────────────────────

def test_no_slang_terms(tmp_path: Path):
    """Empty slang_terms table returns original text with no injections."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """CREATE TABLE slang_terms (
            id INTEGER PRIMARY KEY, form TEXT, lemma TEXT, freq INTEGER,
            drill_freq REAL, pop_freq REAL, distinctiveness REAL, is_oov INTEGER
        )"""
    )
    conn.commit()
    conn.close()

    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_SAMPLE_LYRICS, encoding="utf-8")

    result = inject_slang(lyrics_file, cohort="drill_trap", density=0.1, db_path=db_path)

    assert result["injections"] == []
    assert result["modified_text"] == _SAMPLE_LYRICS
