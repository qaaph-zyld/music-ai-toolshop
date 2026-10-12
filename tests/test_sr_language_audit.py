"""Tests for toolshop.sr_language_audit — per-song sr/en verdict."""

from __future__ import annotations

import sqlite3

import pytest

from toolshop.sr_language_audit import (
    _score_song,
    _verdict,
    audit_languages,
    apply_languages,
    MIN_TOKENS,
)


_SCHEMA = """
CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT, primary_artist TEXT, corpus TEXT, language TEXT);
CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT, ordinal INTEGER);
CREATE TABLE lines (id INTEGER PRIMARY KEY, text_raw TEXT, text_norm TEXT, section_id INTEGER, word_count INTEGER, syllable_count INTEGER);
"""


def _db(tmp_path, songs):
    """songs = [(corpus, artist, title, [lines])]"""
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.executescript(_SCHEMA)
    sid = sec = lid = 0
    for corpus, artist, title, lines in songs:
        sid += 1
        sec += 1
        conn.execute(
            "INSERT INTO songs (id, title, primary_artist, corpus) VALUES (?, ?, ?, ?)",
            (sid, title, artist, corpus),
        )
        conn.execute(
            "INSERT INTO sections (id, song_id, type, ordinal) VALUES (?, ?, 'v', 1)",
            (sec, sid),
        )
        for text in lines:
            lid += 1
            conn.execute(
                "INSERT INTO lines (id, text_raw, text_norm, section_id) VALUES (?, ?, ?, ?)",
                (lid, text, text.lower(), sec),
            )
    conn.commit()
    conn.close()
    return db


_SR_LINES = [
    "i ja sam bio tu kad nema nikoga",
    "sve sto hoces nocas mozes da uzmes",
    "nije mi zao jer sam bio mlad i lud",
    "ako hoces sa mnom moras da znas da ja necu stati",
] * 10

_EN_LINES = [
    "the night is young and we are going out",
    "i will be there when you need me the most",
    "this is what we have been waiting for all the time",
    "you don't know what it is that you are doing to me",
] * 10


def test_score_serbian_text():
    stats = _score_song(" ".join(_SR_LINES))
    assert stats["score"] >= 0.05
    assert stats["en_hits"] < stats["sr_hits"]


def test_score_english_text():
    stats = _score_song(" ".join(_EN_LINES))
    assert stats["score"] <= -0.02


def test_score_diacritic_boost():
    stats = _score_song("noćas život može da bude sve što hoćeš")
    assert stats["diacritic"] >= 3


def test_verdict_empty_is_ambiguous():
    assert _verdict({"tokens": 0, "score": 0.0}) == "ambiguous"
    assert _verdict({"tokens": MIN_TOKENS - 1, "score": 0.9}) == "ambiguous"


def test_audit_and_apply_roundtrip(tmp_path):
    db = _db(
        tmp_path,
        [
            ("lrclib", "Jala Brat", "sr pesma", _SR_LINES),
            ("lrclib", "A-ha", "en song", _EN_LINES),
            ("lrclib", "X", "tiny", ["da"]),
            ("genius-pro", "Senidah", "sr2", _SR_LINES),
        ],
    )
    report = audit_languages(db, corpora=["lrclib"])
    assert report["summary"] == {"sr": 1, "en": 1, "ambiguous": 1}
    by_title = {s["title"]: s for s in report["songs"]}
    assert by_title["sr pesma"]["verdict"] == "sr"
    assert by_title["en song"]["verdict"] == "en"
    assert by_title["tiny"]["verdict"] == "ambiguous"

    dry = apply_languages(db, corpora=["lrclib"], dry_run=True)
    assert dry["would_update"] == 2

    applied = apply_languages(db, corpora=["lrclib"], dry_run=False)
    assert applied["updated"] == 2
    conn = sqlite3.connect(db)
    langs = dict(conn.execute("SELECT title, language FROM songs").fetchall())
    conn.close()
    assert langs["sr pesma"] == "sr"
    assert langs["en song"] == "en"
    assert langs["tiny"] is None          # ambiguous untouched
    assert langs["sr2"] is None           # outside corpus scope untouched


def test_apply_only_writes_changed(tmp_path):
    db = _db(tmp_path, [("lrclib", "Jala Brat", "sr pesma", _SR_LINES)])
    conn = sqlite3.connect(db)
    conn.execute("UPDATE songs SET language='sr'")
    conn.commit()
    conn.close()
    out = apply_languages(db, corpora=["lrclib"], dry_run=False)
    assert out["updated"] == 0
