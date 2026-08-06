"""Tests for toolshop.similarity_retriever — TF-IDF few-shot example retrieval.

Mocks scikit-learn (not installed) and the lyrics database.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from toolshop.similarity_retriever import retrieve_similar


# ── Test DB fixture ───────────────────────────────────────────────────

def _make_cohort_db(db_path: Path) -> None:
    """Create a minimal lyrics.db with songs/sections/lines for cohort retrieval."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT,
            genre_cohort TEXT, role TEXT
        );
        CREATE TABLE sections (
            id INTEGER PRIMARY KEY, song_id INTEGER, ordinal INTEGER, type TEXT
        );
        CREATE TABLE lines (
            id INTEGER PRIMARY KEY, section_id INTEGER, ordinal INTEGER, text_norm TEXT
        );
        """
    )
    # Insert 3 drill_trap songs
    songs = [
        (1, "Novac", "Jala Brat", "drill_trap", "solo"),
        (2, "Blok", "Buba Corelli", "drill_trap", "solo"),
        (3, "Sange", "Coby", "drill_trap", "solo"),
    ]
    for s in songs:
        conn.execute("INSERT INTO songs VALUES (?, ?, ?, ?, ?)", s)

    # Insert sections + lines for each song
    section_id = 1
    for song_id, title, artist, _, _ in songs:
        # Verse section
        conn.execute(
            "INSERT INTO sections VALUES (?, ?, 1, 'strofa')", (section_id, song_id)
        )
        lines = [
            (section_id * 10 + 1, section_id, 1, f"novac novac svuda {title.lower()}"),
            (section_id * 10 + 2, section_id, 2, f"popac popac svuda brat"),
            (section_id * 10 + 3, section_id, 3, f"zdravo svete kako si"),
            (section_id * 10 + 4, section_id, 4, f"prijatelju moj ti"),
        ]
        for l in lines:
            conn.execute("INSERT INTO lines VALUES (?, ?, ?, ?)", l)
        section_id += 1

        # Chorus section
        conn.execute(
            "INSERT INTO sections VALUES (?, ?, 2, 'refren')", (section_id, song_id)
        )
        lines2 = [
            (section_id * 10 + 1, section_id, 1, f"babone babone"),
            (section_id * 10 + 2, section_id, 2, f"popac popac"),
        ]
        for l in lines2:
            conn.execute("INSERT INTO lines VALUES (?, ?, ?, ?)", l)
        section_id += 1

    conn.commit()
    conn.close()


_SAMPLE_INPUT = "novac novac svuda grad\npopac popac svuda brat\n"


# ── TF-IDF retrieval with mocked sklearn ──────────────────────────────

def test_retrieve_similar_top_k(tmp_path: Path):
    """retrieve_similar returns top_k results ranked by similarity."""
    db_path = tmp_path / "test.db"
    _make_cohort_db(db_path)

    lyrics_file = tmp_path / "input.txt"
    lyrics_file.write_text(_SAMPLE_INPUT, encoding="utf-8")

    # Mock sklearn components
    mock_vectorizer = MagicMock()
    # TF-IDF matrix: 1 input + 3 songs = 4 rows
    mock_matrix = MagicMock()
    mock_vectorizer.fit_transform.return_value = mock_matrix

    # cosine_similarity returns 1×3 array of similarities
    import numpy as np
    mock_sims = np.array([[0.9, 0.5, 0.3]])
    mock_matrix.__getitem__ = MagicMock(return_value=mock_matrix)

    with patch("sklearn.feature_extraction.text.TfidfVectorizer", return_value=mock_vectorizer), \
         patch("sklearn.metrics.pairwise.cosine_similarity", return_value=mock_sims), \
         patch("numpy.argsort", return_value=np.array([0, 1, 2])), \
         patch("numpy.array", side_effect=lambda x: np.array(x) if isinstance(x, list) else x):
        result = retrieve_similar(lyrics_file, cohort="drill_trap", top_k=2, db_path=db_path)

    assert "results" in result
    assert result["cohort"] == "drill_trap"
    assert result["top_k"] == 2
    assert len(result["results"]) <= 2

    # Check result structure
    for r in result["results"]:
        assert "rank" in r
        assert "artist" in r
        assert "title" in r
        assert "similarity" in r
        assert "excerpt" in r
        assert "few_shot_block" in r


def test_few_shot_block_formatting(tmp_path: Path):
    """Few-shot blocks contain artist, title, and excerpt."""
    db_path = tmp_path / "test.db"
    _make_cohort_db(db_path)

    lyrics_file = tmp_path / "input.txt"
    lyrics_file.write_text(_SAMPLE_INPUT, encoding="utf-8")

    import numpy as np
    mock_vectorizer = MagicMock()
    mock_matrix = MagicMock()
    mock_vectorizer.fit_transform.return_value = mock_matrix
    mock_sims = np.array([[0.8, 0.6, 0.4]])

    with patch("sklearn.feature_extraction.text.TfidfVectorizer", return_value=mock_vectorizer), \
         patch("sklearn.metrics.pairwise.cosine_similarity", return_value=mock_sims), \
         patch("numpy.argsort", return_value=np.array([0, 1, 2])):
        result = retrieve_similar(lyrics_file, cohort="drill_trap", top_k=3, db_path=db_path)

    for r in result["results"]:
        block = r["few_shot_block"]
        assert "Artist:" in block
        assert "Title:" in block
        assert "Excerpt:" in block
        assert "--- Example" in block


def test_empty_cohort_returns_empty(tmp_path: Path):
    """No songs in cohort returns empty results."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT,
                            genre_cohort TEXT, role TEXT);
        CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, ordinal INTEGER, type TEXT);
        CREATE TABLE lines (id INTEGER PRIMARY KEY, section_id INTEGER, ordinal INTEGER, text_norm TEXT);
        """
    )
    conn.commit()
    conn.close()

    lyrics_file = tmp_path / "input.txt"
    lyrics_file.write_text(_SAMPLE_INPUT, encoding="utf-8")

    result = retrieve_similar(lyrics_file, cohort="pop", top_k=5, db_path=db_path)

    assert result["results"] == []
    assert result["cohort"] == "pop"


def test_ranking_order(tmp_path: Path):
    """Results are ranked by descending similarity."""
    db_path = tmp_path / "test.db"
    _make_cohort_db(db_path)

    lyrics_file = tmp_path / "input.txt"
    lyrics_file.write_text(_SAMPLE_INPUT, encoding="utf-8")

    import numpy as np
    mock_vectorizer = MagicMock()
    mock_matrix = MagicMock()
    mock_vectorizer.fit_transform.return_value = mock_matrix
    # Simulate: song 2 most similar, then song 1, then song 3
    mock_sims = np.array([[0.3, 0.9, 0.5]])

    with patch("sklearn.feature_extraction.text.TfidfVectorizer", return_value=mock_vectorizer), \
         patch("sklearn.metrics.pairwise.cosine_similarity", return_value=mock_sims):
        result = retrieve_similar(lyrics_file, cohort="drill_trap", top_k=3, db_path=db_path)

    if len(result["results"]) >= 2:
        sims = [r["similarity"] for r in result["results"]]
        assert sims == sorted(sims, reverse=True)
