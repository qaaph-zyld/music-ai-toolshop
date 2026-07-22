"""Tests for toolshop.annotate — CLASSLA annotation helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolshop.annotate import (
    _classify_source_script,
    _token_row_builder,
    _ner_extractor,
    coverage_summary,
)


# ── Source script classification ──────────────────────────────────────

def test_classify_cyrillic():
    assert _classify_source_script("Ово је текст") == "cyrillic"


def test_classify_latin():
    assert _classify_source_script("Ovo je tekst") == "latin"


def test_classify_empty():
    assert _classify_source_script("") == "latin"


def test_classify_mixed_cyrillic_dominant():
    # Even one Cyrillic char triggers cyrillic
    assert _classify_source_script("test текст") == "cyrillic"


# ── Token row builder ─────────────────────────────────────────────────

def test_token_row_builder_basic():
    token = SimpleNamespace(text="kuca", upos="NOUN", lemma="kucati", feats="Case=Nom")
    row = _token_row_builder(42, 1, token, "latin")
    assert row["line_id"] == 42
    assert row["ordinal"] == 1
    assert row["form"] == "kuca"
    assert row["lemma"] == "kucati"
    assert row["upos"] == "NOUN"
    assert row["feats"] == "Case=Nom"
    assert row["is_oov"] == 0
    assert row["source_script"] == "latin"


def test_token_row_builder_cyrillic():
    token = SimpleNamespace(text="кућа", upos="NOUN", lemma="кућа", feats="Case=Nom")
    row = _token_row_builder(10, 3, token, "cyrillic")
    assert row["source_script"] == "cyrillic"
    assert row["form"] == "кућа"


def test_token_row_builder_null_upos():
    token = SimpleNamespace(text="x", upos=None, lemma="x", feats=None)
    row = _token_row_builder(1, 1, token, "latin")
    assert row["upos"] == "_"
    assert row["feats"] == "_"


# ── NER extractor ─────────────────────────────────────────────────────

def test_ner_extractor_with_ents():
    """Test NER extraction using doc.ents (stanza-style)."""
    ent1 = SimpleNamespace(text="Beograd", type="LOC")
    ent2 = SimpleNamespace(text="Jala Brat", type="PER")
    doc = SimpleNamespace(ents=[ent1, ent2])

    entities = _ner_extractor(doc, song_id=1, section_id=2, line_id=3)
    assert len(entities) == 2
    assert entities[0]["text"] == "Beograd"
    assert entities[0]["ner_type"] == "LOC"
    assert entities[0]["line_id"] == 3
    assert entities[1]["text"] == "Jala Brat"
    assert entities[1]["ner_type"] == "PER"


def test_ner_extractor_empty():
    """No entities in doc."""
    doc = SimpleNamespace(ents=[])
    entities = _ner_extractor(doc, 1, 2, 3)
    assert entities == []


def test_ner_extractor_word_level():
    """Test NER extraction from per-word ner tags (BIO scheme)."""
    words = [
        SimpleNamespace(text="Buba", ner="B-PER"),
        SimpleNamespace(text="Corelli", ner="I-PER"),
        SimpleNamespace(text="u", ner="O"),
        SimpleNamespace(text="Beogradu", ner="B-LOC"),
    ]
    doc = SimpleNamespace(ents=None)
    # Patch iter_words to return our mock words
    doc.iter_words = lambda: iter(words)

    entities = _ner_extractor(doc, 1, 2, 3)
    assert len(entities) == 2
    assert entities[0]["text"] == "Buba Corelli"
    assert entities[0]["ner_type"] == "PER"
    assert entities[1]["text"] == "Beogradu"
    assert entities[1]["ner_type"] == "LOC"


# ── Coverage summary ──────────────────────────────────────────────────

def test_coverage_summary(tmp_path):
    """Coverage summary on a minimal DB with tokens."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE lines (id INTEGER PRIMARY KEY, text_raw TEXT, text_norm TEXT, section_id INTEGER, word_count INTEGER, syllable_count INTEGER);
        CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
        CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT);
        CREATE TABLE tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, line_id INTEGER, ordinal INTEGER, form TEXT, lemma TEXT, upos TEXT, feats TEXT, is_oov INTEGER DEFAULT 0, source_script TEXT);
        CREATE TABLE entities (id INTEGER PRIMARY KEY AUTOINCREMENT, song_id INTEGER, section_id INTEGER, line_id INTEGER, text TEXT, ner_type TEXT);
        INSERT INTO lines VALUES (1, 'test', 'test', 1, 1, 1);
        INSERT INTO lines VALUES (2, 'test2', 'test2', 1, 1, 1);
        INSERT INTO tokens (line_id, ordinal, form, lemma, upos, source_script) VALUES (1, 1, 'test', 'test', 'NOUN', 'latin');
        INSERT INTO entities (song_id, section_id, line_id, text, ner_type) VALUES (1, 1, 1, 'Beograd', 'LOC');
    """)
    conn.commit()

    result = coverage_summary(conn)
    assert result["total_lines"] == 2
    assert result["annotated_lines"] == 1
    assert result["entity_count"] == 1
    assert "latin" in result["by_script"]
    conn.close()


# ── Integration test (skip-guarded) ───────────────────────────────────

@pytest.mark.slow
def test_classla_integration():
    """Live CLASSLA pipeline test — requires classla + sr model."""
    pytest.importorskip("classla", reason="[lyrics-nlp] extra not installed")
    import classla

    nlp = classla.Pipeline("sr", type="nonstandard")
    doc = nlp("Ovo je test recenica o Beogradu.")

    # Should produce tokens
    words = list(doc.iter_words())
    assert len(words) > 0
    assert words[0].text == "Ovo"
