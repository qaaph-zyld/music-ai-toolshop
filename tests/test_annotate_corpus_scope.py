"""Tests for corpus-scoped CLASSLA annotation (lyrics-sr lane).

``annotate_lines`` annotates the whole DB by default; ``corpora`` restricts
the line selection to songs of the given corpus tags. A fake ``classla``
module stands in for the real pipeline (real CLASSLA is covered by the
``slow`` integration test in test_annotate.py).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from types import SimpleNamespace
from typing import Optional

import pytest

from toolshop.annotate import annotate_lines, coverage_summary


_SCHEMA = """
CREATE TABLE lines (id INTEGER PRIMARY KEY, text_raw TEXT, text_norm TEXT, section_id INTEGER, word_count INTEGER, syllable_count INTEGER);
CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT, corpus TEXT, language TEXT);
CREATE TABLE tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, line_id INTEGER, ordinal INTEGER, form TEXT, lemma TEXT, upos TEXT, feats TEXT, is_oov INTEGER DEFAULT 0, source_script TEXT);
CREATE TABLE entities (id INTEGER PRIMARY KEY AUTOINCREMENT, song_id INTEGER, section_id INTEGER, line_id INTEGER, text TEXT, ner_type TEXT);
"""


def _fixture_db(tmp_path, *corpus_lines):
    """Build a tiny db: corpus_lines = [(corpus, [line_text, ...]), ...]."""
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.executescript(_SCHEMA)
    song_id = 0
    section_id = 0
    line_id = 0
    for corpus, texts in corpus_lines:
        song_id += 1
        section_id += 1
        conn.execute("INSERT INTO songs (id, title, primary_artist, corpus) VALUES (?, 't', 'a', ?)", (song_id, corpus))
        conn.execute("INSERT INTO sections (id, song_id, type, ordinal) VALUES (?, ?, 'x', 1)", (section_id, song_id))
        for text in texts:
            line_id += 1
            conn.execute(
                "INSERT INTO lines (id, text_raw, text_norm, section_id) VALUES (?, ?, ?, ?)",
                (line_id, text, text.lower(), section_id),
            )
    conn.commit()
    return conn


class _FakeDoc:
    ents = []

    def __init__(self, text):
        self._words = [
            SimpleNamespace(text=w, upos="NOUN", lemma=w.lower(), feats="_")
            for w in text.split()
        ]

    def iter_words(self):
        return iter(self._words)


class _FakePipeline:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, text):
        return _FakeDoc(text)


@pytest.fixture
def fake_classla(monkeypatch):
    fake = SimpleNamespace(Pipeline=_FakePipeline)
    monkeypatch.setitem(sys.modules, "classla", fake)
    return fake


def _annotated_line_ids(conn):
    return {r[0] for r in conn.execute("SELECT DISTINCT line_id FROM tokens")}


def test_corpus_scope_selects_only_target_corpus(tmp_path, fake_classla):
    conn = _fixture_db(tmp_path, ("genius-pro", ["prva linija", "druga linija"]), ("mudcat-digitrad", ["english line"]))
    annotate_lines(conn, corpora=["genius-pro"])
    assert _annotated_line_ids(conn) == {1, 2}
    conn.close()


def test_no_scope_annotates_everything(tmp_path, fake_classla):
    conn = _fixture_db(tmp_path, ("genius-pro", ["prva linija"]), ("mudcat-digitrad", ["english line"]))
    annotate_lines(conn)
    assert _annotated_line_ids(conn) == {1, 2}
    conn.close()


def test_multi_corpus_scope(tmp_path, fake_classla):
    conn = _fixture_db(
        tmp_path,
        ("genius-pro", ["a jedan"]),
        ("lrclib", ["a dva"]),
        ("genius-de", ["ein zwei"]),
    )
    annotate_lines(conn, corpora=["genius-pro", "lrclib"])
    assert _annotated_line_ids(conn) == {1, 2}
    conn.close()


def test_resume_skips_annotated_lines(tmp_path, fake_classla):
    conn = _fixture_db(tmp_path, ("genius-pro", ["prva", "druga", "treca"]))
    conn.execute(
        "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, source_script) VALUES (1, 1, 'x', 'x', 'X', 'latin')"
    )
    conn.commit()
    summary = annotate_lines(conn, corpora=["genius-pro"], resume=True)
    assert summary["lines_annotated"] == 2
    assert _annotated_line_ids(conn) == {1, 2, 3}
    conn.close()


def test_language_scope_skips_en_and_null(tmp_path, fake_classla):
    conn = _fixture_db(
        tmp_path,
        ("genius-pro", ["sr linija", "sr linija 2"]),
        ("genius-pro", ["en line"]),
        ("genius-pro", ["ambiguous line"]),
    )
    conn.execute("UPDATE songs SET language = 'sr' WHERE id = 1")
    conn.execute("UPDATE songs SET language = 'en' WHERE id = 2")
    conn.commit()
    annotate_lines(conn, corpora=["genius-pro"], languages=["sr"])
    assert _annotated_line_ids(conn) == {1, 2}
    conn.close()


def test_status_json_written(tmp_path, fake_classla):
    status = tmp_path / "status.json"
    texts = ["linija %d" % i for i in range(1200)]
    conn = _fixture_db(tmp_path, ("genius-pro", texts))
    annotate_lines(conn, corpora=["genius-pro"], status_path=status)
    blob = json.loads(status.read_text(encoding="utf-8"))
    assert blob["finished"] is True
    assert blob["lines_done"] == 1200
    assert blob["lines_total"] == 1200
    assert blob["corpora"] == ["genius-pro"]
    conn.close()


def test_coverage_summary_per_corpus(tmp_path):
    conn = _fixture_db(tmp_path, ("genius-pro", ["a", "b"]), ("mudcat-digitrad", ["c"]))
    conn.execute(
        "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, source_script) VALUES (1, 1, 'x', 'x', 'X', 'latin')"
    )
    conn.execute(
        "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, source_script) VALUES (3, 1, 'y', 'y', 'X', 'latin')"
    )
    conn.commit()
    cov = coverage_summary(conn)
    assert cov["by_corpus"]["genius-pro"] == {"total": 2, "annotated": 1, "pct": 50.0}
    assert cov["by_corpus"]["mudcat-digitrad"] == {"total": 1, "annotated": 1, "pct": 100.0}
    conn.close()
