"""Tests for toolshop.themes — section doc assembly + cohort mix aggregation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from toolshop.themes import (
    assemble_section_docs,
    compute_cohort_mix,
)


def _build_test_db(db_path: Path) -> None:
    """Build a minimal DB with sections, lines, and section_topics for mix testing."""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT,
            role TEXT, genre_cohort TEXT);
        CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
        CREATE TABLE lines (id INTEGER PRIMARY KEY, section_id INTEGER, ordinal INTEGER,
            text_raw TEXT, text_norm TEXT, word_count INTEGER, syllable_count INTEGER);
        CREATE TABLE topics (topic_id INTEGER PRIMARY KEY, label TEXT, top_terms TEXT,
            size INTEGER, exemplar_section_id INTEGER);
        CREATE TABLE section_topics (section_id INTEGER NOT NULL, topic_id INTEGER NOT NULL,
            probability REAL, PRIMARY KEY (section_id, topic_id));
    """)

    # 2 drill songs, 2 pop songs
    conn.execute("INSERT INTO songs VALUES (1, 'D1', 'Buba', 'solo', 'drill_trap')")
    conn.execute("INSERT INTO songs VALUES (2, 'D2', 'Jala', 'solo', 'drill_trap')")
    conn.execute("INSERT INTO songs VALUES (3, 'P1', 'Nikolija', 'solo', 'pop')")
    conn.execute("INSERT INTO songs VALUES (4, 'P2', 'Senidah', 'solo', 'pop')")

    # Sections: 2 per song = 8 total
    # Sections 1-4 → drill, sections 5-8 → pop
    for sid in range(1, 9):
        song_id = (sid - 1) // 2 + 1
        conn.execute(f"INSERT INTO sections VALUES ({sid}, {song_id}, 'strofa', 1)")

    # Lines: 3 lines per section (meets min_section_lines=2)
    for sid in range(1, 9):
        for line_ord in range(1, 4):
            conn.execute(
                f"INSERT INTO lines VALUES ({(sid-1)*3+line_ord}, {sid}, {line_ord}, "
                f"'test line {line_ord}', 'test line {line_ord}', 2, 3)"
            )

    # Topics
    conn.execute("INSERT INTO topics VALUES (0, '0_money_cash', '[\"cash\",\"money\"]', 4, 1)")
    conn.execute("INSERT INTO topics VALUES (1, '1_love_heart', '[\"love\",\"heart\"]', 4, 5)")

    # Section topics: drill sections → topic 0, pop sections → topic 1
    for sid in range(1, 5):
        conn.execute(f"INSERT INTO section_topics VALUES ({sid}, 0, 0.9)")
    for sid in range(5, 9):
        conn.execute(f"INSERT INTO section_topics VALUES ({sid}, 1, 0.85)")

    conn.commit()
    conn.close()


# ── Section doc assembly ──────────────────────────────────────────────

def test_assemble_section_docs_basic(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    docs = assemble_section_docs(conn, min_section_lines=2)
    assert len(docs) == 8  # all 8 sections have 3 lines
    assert all(d["text"] for d in docs)
    assert "section_id" in docs[0]
    assert "song_id" in docs[0]
    conn.close()


def test_assemble_section_docs_min_lines_filter(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    # All sections have 3 lines, so min_section_lines=4 should filter all out
    docs = assemble_section_docs(conn, min_section_lines=4)
    assert len(docs) == 0
    conn.close()


def test_assemble_section_docs_min_lines_3(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    # min_section_lines=3 should include all (they have exactly 3)
    docs = assemble_section_docs(conn, min_section_lines=3)
    assert len(docs) == 8
    conn.close()


# ── Cohort mix ────────────────────────────────────────────────────────

def test_compute_cohort_mix(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    result = compute_cohort_mix(conn)

    assert "cohort_mix" in result
    assert "artist_mix" in result

    # drill_trap should have all sections in topic 0
    drill = result["cohort_mix"]["drill_trap"]
    assert len(drill) == 1
    assert drill[0]["topic_id"] == 0
    assert drill[0]["section_count"] == 4
    assert abs(drill[0]["share"] - 1.0) < 0.01

    # pop should have all sections in topic 1
    pop = result["cohort_mix"]["pop"]
    assert len(pop) == 1
    assert pop[0]["topic_id"] == 1
    assert pop[0]["section_count"] == 4
    assert abs(pop[0]["share"] - 1.0) < 0.01

    conn.close()


def test_compute_cohort_mix_per_artist(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    result = compute_cohort_mix(conn)
    artist_mix = result["artist_mix"]

    # Buba should have 2 sections in topic 0
    buba = artist_mix["Buba"]
    assert len(buba) == 1
    assert buba[0]["topic_id"] == 0
    assert buba[0]["section_count"] == 2

    # Nikolija should have 2 sections in topic 1
    nikolija = artist_mix["Nikolija"]
    assert len(nikolija) == 1
    assert nikolija[0]["topic_id"] == 1
    assert nikolija[0]["section_count"] == 2

    conn.close()


def test_compute_cohort_mix_excludes_featured(tmp_path):
    db = tmp_path / "test.db"
    _build_test_db(db)
    conn = sqlite3.connect(db)

    # Add a featured song with a section in topic 0
    conn.execute("INSERT INTO songs VALUES (5, 'F1', 'X', 'featured', 'drill_trap')")
    conn.execute("INSERT INTO sections VALUES (9, 5, 'strofa', 1)")
    conn.execute("INSERT INTO section_topics VALUES (9, 0, 0.9)")
    conn.commit()

    result = compute_cohort_mix(conn)

    # Featured song's section should NOT appear in drill_trap mix
    drill = result["cohort_mix"]["drill_trap"]
    total_drill = sum(t["section_count"] for t in drill)
    assert total_drill == 4  # still 4, not 5

    conn.close()


# ── Integration test (skip-guarded) ───────────────────────────────────

@pytest.mark.slow
def test_bertopic_integration():
    """Live BERTopic fit on a tiny corpus — requires bertopic + sentence-transformers."""
    pytest.importorskip("bertopic", reason="[lyrics-nlp] extra not installed")
    pytest.importorskip("sentence_transformers", reason="[lyrics-nlp] extra not installed")

    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer

    docs = [
        "novac pare kesh lova",
        "brat brat brat brat",
        "ljubav srce suze",
        "novac pare kesh lova",
        "brat brat brat brat",
        "ljubav srce suze",
        "novac pare kesh lova",
        "brat brat brat brat",
        "ljubav srce suze",
        "novac pare kesh lova",
    ]

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    embeddings = model.encode(docs)

    topic_model = BERTopic(min_topic_size=2, random_state=42, calculate_probabilities=False)
    topics, probs = topic_model.fit_transform(docs, embeddings)

    assert len(topics) == len(docs)
    # At least one real topic (not all outliers)
    real_topics = [t for t in topics if t != -1]
    assert len(real_topics) >= 1
