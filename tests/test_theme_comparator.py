"""Tests for toolshop.theme_comparator — JSD computation and theme comparison."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pytest

from toolshop.theme_comparator import (
    _compute_jsd,
    _compute_input_distribution,
    _jsd_manual,
    _load_cohort_distribution,
    _parse_input_sections,
    compare_themes,
)


# ── JSD computation ────────────────────────────────────────────────────

def test_jsd_identical_distributions():
    """JSD of identical distributions should be 0."""
    p = [0.5, 0.3, 0.2]
    q = [0.5, 0.3, 0.2]
    jsd = _compute_jsd(p, q)
    assert jsd < 1e-10


def test_jsd_disjoint_distributions():
    """JSD distance of disjoint distributions should be sqrt(ln 2)."""
    import math as _math
    p = [1.0, 0.0]
    q = [0.0, 1.0]
    jsd = _compute_jsd(p, q)
    expected = _math.sqrt(_math.log(2))
    assert abs(jsd - expected) < 1e-6


def test_jsd_manual_matches_scipy():
    """Manual JSD should match scipy if scipy is available."""
    try:
        from scipy.spatial.distance import jensenshannon
    except ImportError:
        pytest.skip("scipy not installed")
    p = [0.4, 0.4, 0.2]
    q = [0.2, 0.3, 0.5]
    expected = float(jensenshannon(p, q))
    manual = _jsd_manual(p, q)
    assert abs(manual - expected) < 1e-6


def test_jsd_manual_symmetric():
    """JSD should be symmetric: JSD(p||q) == JSD(q||p)."""
    p = [0.5, 0.3, 0.2]
    q = [0.1, 0.6, 0.3]
    assert abs(_jsd_manual(p, q) - _jsd_manual(q, p)) < 1e-10


# ── Input distribution ─────────────────────────────────────────────────

def test_compute_input_distribution_basic():
    topics = [0, 0, 1, 1, 2]
    dist = _compute_input_distribution(topics, num_topics=3)
    assert abs(dist[0] - 0.4) < 1e-6
    assert abs(dist[1] - 0.4) < 1e-6
    assert abs(dist[2] - 0.2) < 1e-6


def test_compute_input_distribution_with_outliers():
    """Topic -1 (outliers) should be excluded from distribution."""
    topics = [-1, 0, 0, 1]
    dist = _compute_input_distribution(topics, num_topics=3)
    assert dist[0] == pytest.approx(2 / 3)
    assert dist[1] == pytest.approx(1 / 3)
    assert dist[2] == 0.0


def test_compute_input_distribution_all_outliers():
    """If all topics are -1, distribution should be all zeros."""
    topics = [-1, -1, -1]
    dist = _compute_input_distribution(topics, num_topics=3)
    assert all(d == 0.0 for d in dist)


# ── Input section parsing ──────────────────────────────────────────────

def test_parse_input_sections_with_labels():
    text = "[Verse 1]\nFirst line\nSecond line\n\n[Chorus]\nChorus line\n"
    sections = _parse_input_sections(text)
    assert len(sections) == 2
    assert "first line" in sections[0]["text"].lower()
    assert "chorus line" in sections[1]["text"].lower()


def test_parse_input_sections_no_labels():
    """Text without labels should produce one 'other' section."""
    text = "Just some lyrics\nwithout any labels\n"
    sections = _parse_input_sections(text)
    assert len(sections) == 1
    assert sections[0]["section_type"] == "other"


# ── Cohort distribution loading ────────────────────────────────────────

def _build_test_db(db_path: Path) -> None:
    """Build a minimal DB with section_topics for cohort distribution testing."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT,
            role TEXT, genre_cohort TEXT);
        CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
        CREATE TABLE topics (topic_id INTEGER PRIMARY KEY, label TEXT, top_terms TEXT,
            size INTEGER, exemplar_section_id INTEGER);
        CREATE TABLE section_topics (section_id INTEGER NOT NULL, topic_id INTEGER NOT NULL,
            probability REAL, PRIMARY KEY (section_id, topic_id));
    """)
    conn.execute("INSERT INTO songs VALUES (1, 'D1', 'Buba', 'solo', 'drill_trap')")
    conn.execute("INSERT INTO songs VALUES (2, 'P1', 'Nikolija', 'solo', 'pop')")
    conn.execute("INSERT INTO sections VALUES (1, 1, 'strofa', 1)")
    conn.execute("INSERT INTO sections VALUES (2, 1, 'strofa', 2)")
    conn.execute("INSERT INTO sections VALUES (3, 2, 'strofa', 1)")
    conn.execute("INSERT INTO sections VALUES (4, 2, 'strofa', 2)")
    conn.execute("INSERT INTO topics VALUES (0, '0_money', '[\"cash\",\"money\"]', 2, 1)")
    conn.execute("INSERT INTO topics VALUES (1, '1_love', '[\"love\",\"heart\"]', 2, 3)")
    conn.execute("INSERT INTO section_topics VALUES (1, 0, 0.9)")
    conn.execute("INSERT INTO section_topics VALUES (2, 0, 0.85)")
    conn.execute("INSERT INTO section_topics VALUES (3, 1, 0.88)")
    conn.execute("INSERT INTO section_topics VALUES (4, 1, 0.92)")
    conn.commit()
    conn.close()


def test_load_cohort_distribution(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    ids, props, terms = _load_cohort_distribution(conn, "drill_trap")
    assert ids == [0]
    assert abs(props[0] - 1.0) < 1e-6
    assert "cash" in terms[0]

    ids, props, terms = _load_cohort_distribution(conn, "pop")
    assert ids == [1]
    assert abs(props[0] - 1.0) < 1e-6
    conn.close()


def test_load_cohort_distribution_empty(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    ids, props, terms = _load_cohort_distribution(conn, "nonexistent")
    assert ids == []
    assert props == []
    conn.close()


# ── compare_themes fallback ────────────────────────────────────────────

def test_compare_themes_no_db(tmp_path):
    """Should return error dict when DB doesn't exist."""
    lyrics = tmp_path / "lyrics.txt"
    lyrics.write_text("[Verse 1]\nTest lyrics\n", encoding="utf-8")
    result = compare_themes(
        input_path=lyrics,
        cohort="drill_trap",
        db_path=tmp_path / "nonexistent.db",
    )
    assert "error" in result
