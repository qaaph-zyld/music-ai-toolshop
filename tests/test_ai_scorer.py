"""Tests for toolshop.ai_scorer — 4-component quality scoring."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from toolshop.ai_scorer import score_lyrics


def _create_test_db(db_path: Path) -> None:
    """Create a minimal lyrics.db with song_metrics and song_rhyme_metrics."""
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
        CREATE TABLE song_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            total_words INTEGER,
            unique_words INTEGER,
            ttr REAL,
            line_count INTEGER,
            avg_words_per_line REAL,
            avg_syllables_per_line REAL,
            hook_repetition_max INTEGER,
            hook_repetition_ratio REAL,
            english_loanword_rate REAL,
            section_type_counts TEXT
        );
        CREATE TABLE song_rhyme_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            rhyme_factor REAL,
            pct_multis REAL,
            internal_rhyme_rate REAL,
            dominant_scheme TEXT,
            top_vowel_pairs TEXT
        );
    """)

    # Insert 5 drill_trap songs with metrics.
    for i in range(5):
        conn.execute(
            "INSERT INTO songs (title, primary_artist, role, genre_cohort) VALUES (?, ?, 'solo', 'drill_trap')",
            (f"Drill Song {i}", "Buba Corelli"),
        )
        song_id = i + 1
        # Insert 6 sections per song.
        for ord_i in range(6):
            conn.execute(
                "INSERT INTO sections (song_id, ordinal, type) VALUES (?, ?, ?)",
                (song_id, ord_i, "strofa"),
            )
        # song_metrics: line_count=40, ttr=0.07, avg_syl=8, hook_ratio=0.15
        conn.execute(
            """INSERT INTO song_metrics
               (song_id, total_words, unique_words, ttr, line_count,
                avg_words_per_line, avg_syllables_per_line,
                hook_repetition_max, hook_repetition_ratio,
                english_loanword_rate, section_type_counts)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (song_id, 300, 21, 0.07, 40, 7.5, 8.0, 3, 0.15, 0.05, "{}"),
        )
        # song_rhyme_metrics: rf=0.56, pct_multis=0.49, irr=0.35
        conn.execute(
            """INSERT INTO song_rhyme_metrics
               (song_id, rhyme_factor, pct_multis, internal_rhyme_rate,
                dominant_scheme, top_vowel_pairs)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (song_id, 0.56, 0.49, 0.35, "AABB", "[]"),
        )

    conn.commit()
    conn.close()


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    """Create a test lyrics DB with drill_trap baseline data."""
    db_path = tmp_path / "test_scorer.db"
    _create_test_db(db_path)
    return db_path


@pytest.fixture
def sample_lyrics(tmp_path: Path) -> Path:
    """Write a sample AI lyrics file for scoring."""
    lyrics = """[Strofa 1]
novac novac novac novac
popac popac popac popac
lovac lovac lovac lovac
novac novac novac novac

[Refren]
novac popac lovac novac
popac lovac novac popac
novac popac lovac novac
popac lovac novac popac

[Strofa 2]
novac novac novac novac
popac popac popac popac
lovac lovac lovac lovac
novac novac novac novac

[Refren]
novac popac lovac novac
popac lovac novac popac
novac popac lovac novac
popac lovac novac popac
"""
    p = tmp_path / "sample_lyrics.txt"
    p.write_text(lyrics, encoding="utf-8")
    return p


def test_score_returns_dict(test_db, sample_lyrics):
    """score_lyrics returns a dict with overall_score and components."""
    result = score_lyrics(sample_lyrics, cohort="drill_trap", db_path=test_db)
    assert isinstance(result, dict)
    assert "overall_score" in result
    assert "components" in result


def test_overall_score_range(test_db, sample_lyrics):
    """Overall score is between 0 and 100."""
    result = score_lyrics(sample_lyrics, cohort="drill_trap", db_path=test_db)
    assert 0 <= result["overall_score"] <= 100


def test_component_score_ranges(test_db, sample_lyrics):
    """Each component score is between 0 and 100."""
    result = score_lyrics(sample_lyrics, cohort="drill_trap", db_path=test_db)
    for comp_name in ("structural", "rhyme", "lexical", "repetition"):
        score = result["components"][comp_name]["score"]
        assert 0 <= score <= 100, f"{comp_name} score {score} out of range"


def test_component_metrics_present(test_db, sample_lyrics):
    """Each component has metrics and baselines."""
    result = score_lyrics(sample_lyrics, cohort="drill_trap", db_path=test_db)
    for comp_name in ("structural", "rhyme", "lexical", "repetition"):
        comp = result["components"][comp_name]
        assert "metrics" in comp
        assert "baselines" in comp


def test_rhyme_metrics_computed(test_db, sample_lyrics):
    """Rhyme component has rhyme_factor, pct_multis, internal_rhyme_rate."""
    result = score_lyrics(sample_lyrics, cohort="drill_trap", db_path=test_db)
    rhyme = result["components"]["rhyme"]
    assert "rhyme_factor" in rhyme["metrics"]
    assert "pct_multis" in rhyme["metrics"]
    assert "internal_rhyme_rate" in rhyme["metrics"]


def test_high_rhyme_factor_scores_higher(test_db, tmp_path):
    """Lyrics with high rhyme factor should score higher on rhyme than no-rhyme lyrics."""
    # High rhyme lyrics.
    high_rhyme = """[Strofa 1]
novac novac
popac popac
lovac lovac
novac novac

[Refren]
novac popac
popac lovac
novac popac
popac lovac
"""
    high_path = tmp_path / "high_rhyme.txt"
    high_path.write_text(high_rhyme, encoding="utf-8")

    # No rhyme lyrics.
    no_rhyme = """[Strofa 1]
da ne mi ti on ona
mi ti on ona da ne
ne da ti mi on ona
on ona da ne ti mi

[Refren]
da ne mi ti on ona
mi ti on ona da ne
ne da ti mi on ona
on ona da ne ti mi
"""
    no_path = tmp_path / "no_rhyme.txt"
    no_path.write_text(no_rhyme, encoding="utf-8")

    high_result = score_lyrics(high_path, cohort="drill_trap", db_path=test_db)
    no_result = score_lyrics(no_path, cohort="drill_trap", db_path=test_db)

    high_rhyme_score = high_result["components"]["rhyme"]["score"]
    no_rhyme_score = no_result["components"]["rhyme"]["score"]
    assert high_rhyme_score >= no_rhyme_score


def test_overall_is_weighted_average(test_db, sample_lyrics):
    """Overall score equals 25% weighted sum of component scores."""
    result = score_lyrics(sample_lyrics, cohort="drill_trap", db_path=test_db)
    comps = result["components"]
    expected = (
        comps["structural"]["score"] * 0.25
        + comps["rhyme"]["score"] * 0.25
        + comps["lexical"]["score"] * 0.25
        + comps["repetition"]["score"] * 0.25
    )
    assert abs(result["overall_score"] - round(expected, 2)) < 0.1
