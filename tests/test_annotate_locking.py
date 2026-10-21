"""Tests for annotate locking/preflight and honest status (lyrics-sr A1a).

SR-3 died 2026-10-13 on 'database is locked' mid-batch while the status JSON
kept claiming the run was alive.  These tests cover the write preflight
(refuse vs wait), bounded commit retry with an honest failure status, and the
MAirina gate block (``mairina/corpus.py check_annotated`` semantics).
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
from types import SimpleNamespace

import pytest

import toolshop.annotate as annotate_mod
from toolshop.annotate import annotate_lines, run_annotation


_SCHEMA = """
CREATE TABLE lines (id INTEGER PRIMARY KEY, text_raw TEXT, text_norm TEXT, section_id INTEGER, word_count INTEGER, syllable_count INTEGER);
CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT, corpus TEXT, language TEXT);
CREATE TABLE tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, line_id INTEGER, ordinal INTEGER, form TEXT, lemma TEXT, upos TEXT, feats TEXT, is_oov INTEGER DEFAULT 0, source_script TEXT);
CREATE TABLE entities (id INTEGER PRIMARY KEY AUTOINCREMENT, song_id INTEGER, section_id INTEGER, line_id INTEGER, text TEXT, ner_type TEXT);
"""


def _fixture_db(tmp_path, songs):
    """songs = [(corpus, language, [(text_raw, text_norm), ...]), ...] -> db Path."""
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.executescript(_SCHEMA)
    sid = sec = lid = 0
    for corpus, language, lines in songs:
        sid += 1
        sec += 1
        conn.execute(
            "INSERT INTO songs (id, title, primary_artist, corpus, language) VALUES (?, 't', 'a', ?, ?)",
            (sid, corpus, language),
        )
        conn.execute(
            "INSERT INTO sections (id, song_id, type, ordinal) VALUES (?, ?, 'x', 1)",
            (sec, sid),
        )
        for raw, norm in lines:
            lid += 1
            conn.execute(
                "INSERT INTO lines (id, text_raw, text_norm, section_id) VALUES (?, ?, ?, ?)",
                (lid, raw, norm, sec),
            )
    conn.commit()
    conn.close()
    return db


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


def _wal_db(db):
    """Put the fixture db in WAL mode (persisted in the db header)."""
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()


# ── (i) preflight refuses while another connection holds the write lock ──

def test_preflight_refuses_when_writer_holds_lock(tmp_path, fake_classla):
    db = _fixture_db(tmp_path, [("genius-pro", "sr", [("prva linija", "prva linija")])])
    _wal_db(db)
    writer = sqlite3.connect(db, isolation_level=None, check_same_thread=False)
    writer.execute("BEGIN IMMEDIATE")
    status = tmp_path / "status.json"
    try:
        with pytest.raises(SystemExit) as ei:
            run_annotation(
                db_path=db, corpora=["genius-pro"], languages=["sr"],
                status_path=status, busy_timeout_ms=300,
            )
        assert ei.value.code != 0
    finally:
        writer.execute("ROLLBACK")
        writer.close()
    blob = json.loads(status.read_text(encoding="utf-8"))
    assert blob["finished"] is False
    assert "error" in blob
    assert "locked" in blob["error"].lower()


# ── (ii) lock released inside the timeout -> the run completes ─────────

def test_preflight_waits_and_completes_after_release(tmp_path, fake_classla):
    db = _fixture_db(
        tmp_path,
        [("genius-pro", "sr", [("prva linija", "prva linija"), ("druga", "druga")])],
    )
    _wal_db(db)
    writer = sqlite3.connect(db, isolation_level=None, check_same_thread=False)
    writer.execute("BEGIN IMMEDIATE")
    threading.Timer(0.5, lambda: writer.execute("ROLLBACK")).start()
    status = tmp_path / "status.json"
    summary = run_annotation(
        db_path=db, corpora=["genius-pro"], languages=["sr"],
        status_path=status, busy_timeout_ms=10000,
    )
    writer.close()
    blob = json.loads(status.read_text(encoding="utf-8"))
    assert blob["finished"] is True
    assert "finished_at" in blob
    assert blob["lines_done"] == 2
    assert "error" not in blob
    assert blob["mairina_gate"]["genius-pro"] == {
        "non_empty": 2, "annotated": 2, "pct": 100.0
    }
    assert blob["mairina_gate"]["pass"] is True
    assert summary["lines_annotated"] == 2


# ── (iii) forced commit failure -> honest status; resume skips committed ──

class _FlakyConn:
    """Delegates to a real connection but raises 'database is locked' from
    the Nth ``commit()`` on (every attempt, so the bounded retry exhausts)."""

    def __init__(self, real, fail_on):
        self._real = real
        self._fail_on = fail_on
        self.commit_calls = 0

    def __getattr__(self, name):
        return getattr(self._real, name)

    def commit(self):
        self.commit_calls += 1
        if self.commit_calls >= self._fail_on:
            raise sqlite3.OperationalError("database is locked")
        return self._real.commit()


def test_commit_failure_writes_honest_status_and_resume_skips(
    tmp_path, fake_classla, monkeypatch
):
    monkeypatch.setattr(annotate_mod, "_COMMIT_RETRY_BACKOFF_S", (0, 0, 0))
    texts = [("linija %d" % i, "linija %d" % i) for i in range(600)]
    db = _fixture_db(tmp_path, [("genius-pro", "sr", texts)])
    status = tmp_path / "status.json"
    conn = sqlite3.connect(db)
    proxy = _FlakyConn(conn, fail_on=2)  # batch-1 commit ok, final commit fails
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        annotate_lines(
            proxy, corpora=["genius-pro"], languages=["sr"], status_path=status
        )
    blob = json.loads(status.read_text(encoding="utf-8"))
    assert blob["finished"] is False
    assert "failed_at" in blob
    assert "locked" in blob["error"].lower()
    assert blob["lines_done"] == 500  # only the committed batch counts

    summary = annotate_lines(
        conn, corpora=["genius-pro"], languages=["sr"], status_path=status
    )
    assert summary["lines_annotated"] == 100  # exactly the uncommitted lines
    done = {r[0] for r in conn.execute("SELECT DISTINCT line_id FROM tokens")}
    assert len(done) == 600
    conn.close()
    blob2 = json.loads(status.read_text(encoding="utf-8"))
    assert blob2["finished"] is True
    assert blob2["lines_done"] == 100


# ── (iv) mairina_gate vs a hand-computed fixture ───────────────────────

def test_mairina_gate_counts_only_scoped_languages_and_nonempty_norm(
    tmp_path, fake_classla
):
    db = _fixture_db(tmp_path, [
        # genius-pro / sr: 'prva linija' is counted and annotated; 'druga' gets
        # tokens but its empty text_norm keeps it out of BOTH counts; 'treca'
        # has a whitespace-only text_norm -> also out.
        ("genius-pro", "sr", [("prva linija", "prva linija"),
                              ("druga", ""),
                              ("treca", "   ")]),
        # language out of scope / NULL -> never in numerator or denominator.
        ("genius-pro", "en", [("english line", "english line")]),
        ("genius-pro", None, [("misterija", "misterija")]),
        # lrclib / sr: 'l1' counted + annotated; the empty-text_raw line is
        # never annotated (annotate selects on text_raw) but its non-empty
        # text_norm still lands in the gate denominator.
        ("lrclib", "sr", [("l1", "l1"), ("", "nema raw")]),
    ])
    status = tmp_path / "status.json"
    conn = sqlite3.connect(db)
    annotate_lines(
        conn, corpora=["genius-pro", "lrclib"], languages=["sr"], status_path=status
    )
    conn.close()
    gate = json.loads(status.read_text(encoding="utf-8"))["mairina_gate"]
    assert gate["genius-pro"] == {"non_empty": 1, "annotated": 1, "pct": 100.0}
    assert gate["lrclib"] == {"non_empty": 2, "annotated": 1, "pct": 50.0}
    assert gate["pass"] is False


# ── annotate_reminder (cli.py is not importable from the worktree) ──────

def test_annotate_reminder_mentions_gate_and_command():
    from toolshop.lyricsdb import annotate_reminder

    note = annotate_reminder("D:\\data\\lyrics.db")
    assert "offline" in note.lower()
    assert "lyrics annotate" in note
    assert "--corpus genius-pro" in note
    assert "--corpus lrclib" in note
    assert "--language sr" in note
    assert "--resume" in note
    assert 'D:\\data\\lyrics.db' in note


def test_annotate_reminder_uses_sys_executable(monkeypatch):
    from toolshop.lyricsdb import annotate_reminder

    monkeypatch.setattr(sys, "executable", "X:\\fake\\python.exe")
    note = annotate_reminder("D:\\data\\lyrics.db")
    assert "X:\\fake\\python.exe" in note
    assert "Music-AI-Toolshop" not in note
