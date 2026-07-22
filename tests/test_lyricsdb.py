"""Tests for toolshop.lyricsdb — schema, label parser, loader, dedup."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from toolshop.lyricsdb import (
    parse_section_label,
    normalize_text,
    build_database,
    DEFAULT_DB_PATH,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lyrics_min"


# ── Section label parser ──────────────────────────────────────────────

@pytest.mark.parametrize("label,expected_type,expected_num,expected_performers", [
    ("Refren", "refren", None, []),
    ("Refren: Peki & Jala Brat", "refren", None, ["Peki", "Jala Brat"]),
    ("Strofa 1", "strofa", 1, []),
    ("Strofa 2: Jala Brat", "strofa", 2, ["Jala Brat"]),
    ("Strofa 3: Peki & Jala Brat", "strofa", 3, ["Peki", "Jala Brat"]),
    ("Chorus", "refren", None, []),
    ("Verse 1", "strofa", 1, []),
    ("Verse 2: Coby", "strofa", 2, ["Coby"]),
    ("Pre-Chorus", "prerefren", None, []),
    ("Bridge", "bridge", None, []),
    ("Intro", "intro", None, []),
    ("Outro", "outro", None, []),
    ("Hook", "hook", None, []),
    ("Hook: Buba Corelli", "hook", None, ["Buba Corelli"]),
    ("Unknown Section", "other", None, []),
    ("", "other", None, []),
])
def test_parse_section_label(label, expected_type, expected_num, expected_performers):
    result = parse_section_label(label)
    assert result.type == expected_type
    assert result.type_number == expected_num
    assert result.performers == expected_performers


# ── Expanded label parser tests (T5-L2) ───────────────────────────────

@pytest.mark.parametrize("label,expected_type,expected_num,expected_performers", [
    # Serbian synonyms for known types
    ("Pred-Refren", "prerefren", None, []),
    ("Predrefren", "prerefren", None, []),
    ("Pred-refren", "prerefren", None, []),
    ("Predrefren: Jala Brat", "prerefren", None, ["Jala Brat"]),
    ("Pred-Refren: Jala Brat & Buba Corelli", "prerefren", None, ["Jala Brat", "Buba Corelli"]),
    ("Post-Refren", "postrefren", None, []),
    ("Postrefren", "postrefren", None, []),
    ("Post-refren", "postrefren", None, []),
    ("Post-Refren: Jala Brat", "postrefren", None, ["Jala Brat"]),
    ("Post-Chorus", "postrefren", None, []),
    ("Post-Hook", "postrefren", None, []),
    ("Post-Hook: Sajfer", "postrefren", None, ["Sajfer"]),
    ("Uvod", "intro", None, []),
    ("Uvod: Jala Brat", "intro", None, ["Jala Brat"]),
    ("Uvod: Buba Corelli", "intro", None, ["Buba Corelli"]),
    ("Završetak", "outro", None, []),
    ("Završetak: Buba Corelli", "outro", None, ["Buba Corelli"]),
    ("Završetak: Jala Brat & Buba Corelli", "outro", None, ["Jala Brat", "Buba Corelli"]),
    ("Prelaz", "bridge", None, []),
    ("Prelaz: Jala Brat", "bridge", None, ["Jala Brat"]),
    ("Prijelaz: Buba Corelli", "bridge", None, ["Buba Corelli"]),
    ("Most", "bridge", None, []),
    ("Most: Jala Brat", "bridge", None, ["Jala Brat"]),
    ("Refrain", "refren", None, []),
    ("Refrain: Jala Brat", "refren", None, ["Jala Brat"]),
    ("Pre-Hook", "prerefren", None, []),
    ("Pre-Hook: Buba Corelli", "prerefren", None, ["Buba Corelli"]),
    # New section types
    ("Izgovoreno", "spoken", None, []),
    ("Instrumentalna pauza", "instrumental", None, []),
    ("Tekst iz isječka", "interlude", None, []),
    ("Improvizacija: Coby", "spoken", None, ["Coby"]),
    # Trailing colon with empty performers
    ("Refren:", "refren", None, []),
    ("Strofa 1:", "strofa", 1, []),
    ("Strofa 2:", "strofa", 2, []),
    # Dash separator instead of colon
    ("Refren - Jala Brat", "refren", None, ["Jala Brat"]),
    ("Strofa 4 - Voke", "strofa", 4, ["Voke"]),
    ("Intro - Njota Njole", "intro", None, ["Njota Njole"]),
    # Reversed format: "Artist:Type"
    ("Buba Corelli:Refren", "refren", None, ["Buba Corelli"]),
    ("Buba Corelli:Strofa 1", "strofa", 1, ["Buba Corelli"]),
    ("Buba Corelli:Prelaz", "bridge", None, ["Buba Corelli"]),
    ("Jala: Vers", "strofa", None, ["Jala"]),
    # Typos
    ("Brigde: Coby", "bridge", None, ["Coby"]),
    ("Post-Refern: Jala", "postrefren", None, ["Jala"]),
    ("Stofa 4: Shtela", "strofa", 4, ["Shtela"]),
    ("Stofa 1: Mayer", "strofa", 1, ["Mayer"]),
    # Compound labels with slash
    ("Refrain/Refren: Ghetto Phénomène", "refren", None, ["Ghetto Phénomène"]),
    ("Strofa 1/Couplet 1: Jala Brat", "strofa", 1, ["Jala Brat"]),
    ("Couplet 4/Strofa 4: Jala Brat", "strofa", 4, ["Jala Brat"]),
    # Part N (verse equivalent)
    ("Part 2: RAF Camora", "strofa", 2, ["RAF Camora"]),
    ("Part 1: Jasko", "strofa", 1, ["Jasko"]),
    # Intro/Uvod compound
    ("Intro/Uvod", "intro", None, []),
    # Chorus Variation
    ("Chorus Variation", "refren", None, []),
    ("Pre-Chorus Variation: Severina", "prerefren", None, ["Severina"]),
    # Genuinely unknown → stays other
    ("...", "other", None, []),
    # Song-title placeholder labels → classified as 'tekst' (not 'other')
    ("Tekst pjesme \"Hakimi\"", "tekst", None, []),
    ("Songtext zu „Ferrari 488\"", "tekst", None, []),
    ("?", "other", None, []),
    ("Mayer", "other", None, []),
    ("...", "other", None, []),
    # ASCII-folded variants (diacritics stripped in source, map keys are folded)
    ("Zavrsetak", "outro", None, []),
    ("Zavrsetak: Buba Corelli", "outro", None, ["Buba Corelli"]),
    ("Predrefren", "prerefren", None, []),
    ("Postrefren", "postrefren", None, []),
])
def test_parse_section_label_expanded(label, expected_type, expected_num, expected_performers):
    result = parse_section_label(label)
    assert result.type == expected_type, f"Label '{label}': expected {expected_type}, got {result.type}"
    assert result.type_number == expected_num, f"Label '{label}': expected num {expected_num}, got {result.type_number}"
    assert result.performers == expected_performers, f"Label '{label}': expected {expected_performers}, got {result.performers}"


# ── Text normalization ────────────────────────────────────────────────

def test_normalize_text_basic():
    assert normalize_text("Hello World") == "hello world"


def test_normalize_text_cyrillic():
    # Cyrillic text should be transliterated to Latin and ASCII-folded
    result = normalize_text("прст је реч")
    assert "п" not in result  # no Cyrillic chars remain
    # ASCII-fold strips diacritics: č→c, ć→c, š→s, ž→z, đ→dj
    assert result == "prst je rec"


def test_normalize_text_already_latin():
    # Already-Latin text should just be lowercased
    assert normalize_text("Zna se ko je Peka") == "zna se ko je peka"


def test_normalize_text_empty():
    assert normalize_text("") == ""


def test_normalize_text_cyrillic_latin_unify():
    # Regression: Cyrillic and diacritic-stripped Latin must produce identical text_norm.
    # This is the core defect fix — without ASCII-fold, Cyrillic "Изаћи ћу" → "izaći ću"
    # while Latin "Izaci cu" → "izaci cu", corrupting TTR/rhyme matching.
    cyrillic = normalize_text("Изаћи ћу")
    latin = normalize_text("Izaci cu")
    assert cyrillic == latin, f"Cyrillic '{cyrillic}' != Latin '{latin}'"
    assert cyrillic == "izaci cu"


def test_normalize_text_diacritic_folding():
    # Latin text WITH diacritics should also be folded to match stripped corpus.
    assert normalize_text("izaći ću") == "izaci cu"
    assert normalize_text("čšž") == "csz"
    assert normalize_text("đ") == "dj"


# ── Loader / build_database ───────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_lyrics.db"


def test_build_database_ingest(tmp_db):
    """Build DB from fixture corpus and verify counts."""
    summary = build_database(root=FIXTURE_ROOT, db_path=tmp_db)

    # 4 files on disk, but alpha appears in 2 folders → dedup to 3 unique songs
    assert summary["songs_ingested"] == 3
    assert summary["duplicates_dropped"] == 1
    assert summary["songs_skipped"] == 0


def test_build_database_tables_exist(tmp_db):
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()

    for table in ("songs", "sections", "lines"):
        cursor.execute(f"SELECT count(*) FROM {table}")
        assert cursor.fetchone()[0] > 0, f"Table {table} is empty"

    conn.close()


def test_build_database_sections_count(tmp_db):
    summary = build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    # Alpha has 3 sections, Beta has 2 sections, Multi has 2 sections → 7 total (dedup removes one alpha)
    assert summary["sections_ingested"] == 7


def test_build_database_lines_have_syllables(tmp_db):
    """Every line must have a non-null syllable_count."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM lines WHERE syllable_count IS NULL")
    null_count = cursor.fetchone()[0]
    assert null_count == 0, f"{null_count} lines have NULL syllable_count"
    conn.close()


def test_build_database_dedup_log(tmp_db):
    summary = build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    assert len(summary["dedup_log"]) == 1
    dropped = summary["dedup_log"][0]
    assert "Test Song Alpha" in dropped["title"]
    assert "Fake Artist" in dropped["primary_artist"]


def test_build_database_cyrillic_normalized(tmp_db):
    """Cyrillic song text must be transliterated in text_norm."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT text_norm FROM lines WHERE text_raw LIKE '%прст%'")
    rows = cursor.fetchall()
    assert len(rows) > 0, "No lines with Cyrillic text found"
    for (text_norm,) in rows:
        assert "п" not in text_norm, f"Cyrillic chars remain in normalized text: {text_norm}"
    conn.close()


def test_build_database_performers_parsed(tmp_db):
    """Section performers should be stored as JSON array."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT performers FROM sections WHERE label_raw LIKE '%Buddy%'")
    rows = cursor.fetchall()
    assert len(rows) > 0
    performers = json.loads(rows[0][0])
    assert "Buddy" in performers
    conn.close()


def test_build_database_idempotent(tmp_db):
    """Running build_database twice should produce the same counts (full rebuild)."""
    s1 = build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    s2 = build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    assert s1["songs_ingested"] == s2["songs_ingested"]
    assert s1["sections_ingested"] == s2["sections_ingested"]


def test_build_database_corpus_column(tmp_db):
    """songs.corpus column must default to 'genius-pro'."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT corpus FROM songs")
    corpora = [r[0] for r in cursor.fetchall()]
    assert corpora == ["genius-pro"]
    conn.close()


def test_build_database_section_types(tmp_db):
    """Section type normalization should map both Serbian and English labels."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT type FROM sections ORDER BY type")
    types = [r[0] for r in cursor.fetchall()]
    # Alpha has refren, strofa; Beta has strofa, refren
    assert "refren" in types
    assert "strofa" in types
    conn.close()


def test_build_database_role_and_cohort(tmp_db):
    """songs table must have role, target_artist, genre_cohort columns populated."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT role, target_artist, genre_cohort FROM songs")
    rows = cursor.fetchall()
    assert len(rows) > 0
    for role, target_artist, genre_cohort in rows:
        assert role is not None
        assert target_artist is not None
        # genre_cohort may be NULL for non-target artists
    conn.close()


# ── L3 schema tests ───────────────────────────────────────────────────

def test_l3_tables_exist(tmp_db):
    """L3 tables (tokens, entities, slang_terms, topics, section_topics) must be created."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    cursor = conn.cursor()
    for table in ("tokens", "entities", "slang_terms", "topics", "section_topics"):
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        assert cursor.fetchone() is not None, f"Table {table} not created"
    conn.close()


def test_l3_tokens_insert_and_read(tmp_db):
    """Insert and read back a token row with source_script."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    conn.execute("PRAGMA foreign_keys=ON")
    # Get a real line_id
    line_id = conn.execute("SELECT id FROM lines LIMIT 1").fetchone()[0]
    conn.execute(
        "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, feats, is_oov, source_script)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (line_id, 1, "test", "test", "NOUN", "Case=Nom", 0, "latin"),
    )
    conn.commit()
    row = conn.execute(
        "SELECT form, lemma, upos, source_script FROM tokens WHERE line_id=?", (line_id,)
    ).fetchone()
    assert row == ("test", "test", "NOUN", "latin")
    conn.close()


def test_l3_entities_insert_and_read(tmp_db):
    """Insert and read back an entity row with line provenance."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    conn.execute("PRAGMA foreign_keys=ON")
    song_id = conn.execute("SELECT id FROM songs LIMIT 1").fetchone()[0]
    section_id = conn.execute("SELECT id FROM sections LIMIT 1").fetchone()[0]
    line_id = conn.execute("SELECT id FROM lines LIMIT 1").fetchone()[0]
    conn.execute(
        "INSERT INTO entities (song_id, section_id, line_id, text, ner_type)"
        " VALUES (?, ?, ?, ?, ?)",
        (song_id, section_id, line_id, "Beograd", "LOC"),
    )
    conn.commit()
    row = conn.execute(
        "SELECT text, ner_type FROM entities WHERE line_id=?", (line_id,)
    ).fetchone()
    assert row == ("Beograd", "LOC")
    conn.close()


def test_l3_topics_and_section_topics_insert(tmp_db):
    """Insert and read back topic + section_topic assignment."""
    build_database(root=FIXTURE_ROOT, db_path=tmp_db)
    conn = sqlite3.connect(tmp_db)
    conn.execute("PRAGMA foreign_keys=ON")
    section_id = conn.execute("SELECT id FROM sections LIMIT 1").fetchone()[0]
    conn.execute(
        "INSERT INTO topics (topic_id, label, top_terms, size, exemplar_section_id)"
        " VALUES (?, ?, ?, ?, ?)",
        (0, "love", '["ljubav","srce"]', 10, section_id),
    )
    conn.execute(
        "INSERT INTO section_topics (section_id, topic_id, probability)"
        " VALUES (?, ?, ?)",
        (section_id, 0, 0.85),
    )
    conn.commit()
    row = conn.execute(
        "SELECT t.label, st.probability FROM section_topics st"
        " JOIN topics t ON st.topic_id = t.topic_id WHERE st.section_id=?",
        (section_id,),
    ).fetchone()
    assert row == ("love", 0.85)
    conn.close()
