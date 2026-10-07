"""Tests for fid-aware dedup in build_unified_index / build_database.

G3 closeout: two failure classes on the genius-pro corpus —
  (a) slug collision: two distinct songs sharing one (title, artist) key
      (Lacku "Tenzija" ids 7117386/5446636) — distinct fids must NOT collapse;
  (b) id-less twin winning by scan order (Lacku "Južni Vetar" id 11679713
      losing to a NULL-id baseline file in an alphabetically-earlier dir) —
      the fid-bearing file must win.
genius_song_id now feeds ``foreign_identifier`` so rows carry a stable id.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from toolshop.lyricsdb import build_database


def _song(title: str, artist: str, lines: list, **kw) -> dict:
    body = "\n".join(lines)
    song = {
        "title": title,
        "artist": artist,
        "primary_artist": artist,
        "featured_artists": [],
        "url": "",
        "language": "",
        "raw_lyrics": body,
        "clean_lyrics": body,
        "sections": [{"label": None, "content": body}],
    }
    song.update(kw)
    return song


def _write(root: Path, category: str, filename: str, song: dict) -> Path:
    cat = root / category
    cat.mkdir(parents=True, exist_ok=True)
    p = cat / filename
    p.write_text(json.dumps(song, ensure_ascii=False), encoding="utf-8")
    return p


def _fid_rows(db: Path):
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT title, primary_artist, foreign_identifier, source_path, corpus"
        " FROM songs ORDER BY foreign_identifier"
    ).fetchall()
    conn.close()
    return rows


# ── (a) distinct fids under one key → both rows ────────────────────────

def test_distinct_fids_same_key_both_ingest(tmp_path):
    """Two different genius ids, same normalized (title, artist) → 2 rows."""
    root = tmp_path / "genius"
    _write(root, "lacku-solo", "lacku-tenzija.json",
           _song("Tenzija", "Lacku", ["prva pesma"], genius_song_id=7117386))
    _write(root, "lacku-solo", "lacku-tenzija-5446636.json",
           _song("Tenzija", "Lacku", ["druga pesma skroz drugacija"], genius_song_id=5446636))
    db = tmp_path / "t.db"
    s = build_database(root=root, db_path=db, corpus="genius-pro")

    assert s["songs_ingested"] == 2
    assert s["duplicates_dropped"] == 0
    fids = sorted(r[2] for r in _fid_rows(db))
    assert fids == ["5446636", "7117386"]


# ── (b) fid file beats NULL twin regardless of dir order ───────────────

def test_fid_file_beats_null_twin(tmp_path):
    """NULL-id file in an alphabetically-earlier dir must not shadow the id copy."""
    root = tmp_path / "genius"
    # 'aaa-' dir scans first; holds the id-less legacy twin.
    _write(root, "aaa-featured", "lacku-juzni-vetar.json",
           _song("Južni Vetar", "Lacku", ["stara kopija"]))
    _write(root, "lacku-solo", "lacku-juzni-vetar.json",
           _song("Južni Vetar", "Lacku", ["nova kopija bolja"], genius_song_id=11679713))
    db = tmp_path / "t.db"
    s = build_database(root=root, db_path=db, corpus="genius-pro")

    assert s["songs_ingested"] == 1
    assert s["duplicates_dropped"] == 1
    rows = _fid_rows(db)
    assert rows[0][2] == "11679713"
    assert rows[0][3].endswith("lacku-solo\\lacku-juzni-vetar.json") or \
        rows[0][3].endswith("lacku-solo/lacku-juzni-vetar.json")


def test_index_entries_carry_foreign_identifier(tmp_path):
    root = tmp_path / "genius"
    _write(root, "a-solo", "a-x.json",
           _song("X", "A", ["linija"], genius_song_id=42))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-pro")

    idx = json.loads((root / "_index.json").read_text(encoding="utf-8"))
    assert idx[0]["foreign_identifier"] == "42"
    assert idx[0]["genius_song_id"] == 42


# ── same-fid dup still collapses ───────────────────────────────────────

def test_same_fid_two_dirs_collapses(tmp_path):
    """Same genius id fetched into two dirs → one row (cross-dir dup)."""
    root = tmp_path / "genius"
    _write(root, "arafat-featured", "arafat-x.json",
           _song("X", "Arafat", ["ista pesma"], genius_song_id=2414649))
    _write(root, "fox-featured", "arafat-x.json",
           _song("X", "Arafat", ["ista pesma"], genius_song_id=2414649))
    db = tmp_path / "t.db"
    s = build_database(root=root, db_path=db, corpus="genius-pro")

    assert s["songs_ingested"] == 1
    assert s["duplicates_dropped"] == 1


# ── fid-less groups unchanged ──────────────────────────────────────────

def test_null_fid_group_first_wins(tmp_path):
    root = tmp_path / "genius"
    _write(root, "a-cat", "a-dup.json", _song("Dup", "A", ["v1"]))
    _write(root, "b-cat", "a-dup.json", _song("Dup", "A", ["v2"]))
    db = tmp_path / "t.db"
    s = build_database(root=root, db_path=db, corpus="genius-pro")

    assert s["songs_ingested"] == 1
    assert s["duplicates_dropped"] == 1
    assert _fid_rows(db)[0][2] is None


# ── incremental consistency ────────────────────────────────────────────

def test_incremental_fid_file_vs_null_row_same_key_skips(tmp_path):
    """A NULL-fid row already keyed in the corpus still shields the fid file."""
    root = tmp_path / "genius"
    _write(root, "a-cat", "a-x.json", _song("X", "A", ["linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-pro", incremental=True)

    # id-bearing twin of the same (title, artist) arrives later
    _write(root, "b-cat", "a-x.json",
           _song("X", "A", ["linija"], genius_song_id=99))
    s = build_database(root=root, db_path=db, corpus="genius-pro", incremental=True)

    assert s["songs_ingested"] == 0
    assert s["already_present"] == 1
