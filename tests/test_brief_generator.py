"""Tests for toolshop.brief_generator — Suno-ready writing briefs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from toolshop.lyricsdb import build_database
from toolshop.brief_generator import (
    generate_brief,
    format_brief,
    format_suno_prompt,
)
from toolshop.rimer_db import build_rimer_db

# Debt 13b: never point build_database() at the TRACKED fixture - it writes
# _dedup_log.json back into `root` and dirties the tree. See _fixture_support.
from _fixture_support import LYRICS_MIN_FIXTURE as FIXTURE_ROOT


# ── Helpers ───────────────────────────────────────────────────────────


def _seed_brief_data(conn: sqlite3.Connection) -> None:
    """Seed DB with fingerprint, theme, and rhyme data for brief generation."""
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

    # Insert line_rhymes for rimer DB
    cur.execute("DELETE FROM line_rhymes")
    line_ids_by_song: dict[int, list[int]] = {}
    for sid in song_ids:
        rows = cur.execute(
            "SELECT l.id FROM lines l JOIN sections s ON l.section_id=s.id WHERE s.song_id=? ORDER BY l.id",
            (sid,),
        ).fetchall()
        line_ids_by_song[sid] = [r[0] for r in rows]

    # Create some rhyme groups with different end words
    s0 = line_ids_by_song[song_ids[0]]
    s2 = line_ids_by_song[song_ids[2]]
    if len(s0) >= 4:
        for lid in [s0[2], s0[3]]:
            cur.execute(
                "INSERT INTO line_rhymes (song_id, line_id, rhyme_group, rhyme_type, vowel_skeleton, match_length, position) VALUES (?, ?, 0, 'end', 'e', 1, 'end')",
                (song_ids[0], lid),
            )
    if len(s2) >= 3:
        for lid in [s2[0], s2[2]]:
            cur.execute(
                "INSERT INTO line_rhymes (song_id, line_id, rhyme_group, rhyme_type, vowel_skeleton, match_length, position) VALUES (?, ?, 0, 'end', 'oe', 2, 'end')",
                (song_ids[2], lid),
            )

    conn.commit()


@pytest.fixture
def brief_db(tmp_path):
    """Build a fixture DB, seed it, and build rimer DB."""
    db_path = tmp_path / "test_brief.db"
    build_database(root=FIXTURE_ROOT, db_path=db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    _seed_brief_data(conn)
    conn.close()
    build_rimer_db(db_path)
    return db_path


# ── Tests ─────────────────────────────────────────────────────────────


def test_generate_brief_by_artist(brief_db):
    """generate_brief with artist returns a complete brief dict."""
    brief = generate_brief(artist="Test Artist A", db_path=brief_db)
    assert isinstance(brief, dict)
    assert brief["name"] == "Test Artist A"
    assert brief["cohort"] == "drill_trap"
    assert brief["song_count"] > 0
    assert "craft_targets" in brief
    assert "structure" in brief
    assert "themes" in brief
    assert "rhyme_pairs" in brief
    assert "suno_hints" in brief


def test_generate_brief_by_cohort(brief_db):
    """generate_brief with cohort only returns a valid brief."""
    brief = generate_brief(cohort="drill_trap", db_path=brief_db)
    assert brief["cohort"] == "drill_trap"
    assert brief["song_count"] > 0
    assert "craft_targets" in brief
    assert "structure" in brief


def test_generate_brief_with_topic(brief_db):
    """generate_brief includes topic hint when provided."""
    brief = generate_brief(artist="Test Artist A", topic="street life", db_path=brief_db)
    assert brief["topic"] == "street life"


def test_generate_brief_requires_artist_or_cohort(brief_db):
    """generate_brief raises ValueError when neither artist nor cohort given."""
    with pytest.raises(ValueError, match="Either artist or cohort"):
        generate_brief(db_path=brief_db)


def test_generate_brief_craft_targets(brief_db):
    """Craft targets contain expected fields from fingerprint."""
    brief = generate_brief(artist="Test Artist A", db_path=brief_db)
    ct = brief["craft_targets"]
    assert "rhyme_factor" in ct
    assert "pct_multis" in ct
    assert "ttr" in ct
    assert "dominant_schemes" in ct
    assert ct["rhyme_factor"] > 0


def test_generate_brief_structure(brief_db):
    """Structure template has sections with type, lines, and rhyme_scheme."""
    brief = generate_brief(cohort="drill_trap", db_path=brief_db)
    template = brief["structure"]
    assert "sections" in template
    assert len(template["sections"]) > 0
    for sec in template["sections"]:
        assert "type" in sec
        assert "lines" in sec
        assert "rhyme_scheme" in sec


def test_generate_brief_themes(brief_db):
    """Themes list contains top topics for the cohort."""
    brief = generate_brief(cohort="drill_trap", db_path=brief_db)
    themes = brief["themes"]
    assert isinstance(themes, list)
    # Fixture seeds 2 topics
    if themes:
        assert "label" in themes[0]
        assert "top_terms" in themes[0]


def test_format_brief(brief_db):
    """format_brief produces a readable text brief."""
    brief = generate_brief(artist="Test Artist A", db_path=brief_db)
    text = format_brief(brief)
    assert isinstance(text, str)
    assert "SUNO BRIEF" in text
    assert "STRUCTURE" in text
    assert "CRAFT TARGETS" in text
    assert "Test Artist A" in text


def test_format_brief_with_topic(brief_db):
    """format_brief includes topic hint when present."""
    brief = generate_brief(cohort="pop", topic="love and loss", db_path=brief_db)
    text = format_brief(brief)
    assert "TOPIC HINT" in text
    assert "love and loss" in text


def test_format_suno_prompt(brief_db):
    """format_suno_prompt produces a condensed prompt string."""
    brief = generate_brief(cohort="drill_trap", db_path=brief_db)
    prompt = format_suno_prompt(brief)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "rhyme density" in prompt


def test_format_suno_prompt_with_topic(brief_db):
    """format_suno_prompt includes topic when provided."""
    brief = generate_brief(cohort="drill_trap", topic="hustle", db_path=brief_db)
    prompt = format_suno_prompt(brief)
    assert "hustle" in prompt


def test_generate_brief_unknown_artist(brief_db):
    """generate_brief with unknown artist returns brief with 0 songs."""
    brief = generate_brief(artist="Nonexistent Artist", db_path=brief_db)
    assert brief["song_count"] == 0
    # Should still produce a valid structure
    assert "structure" in brief
