"""Tests for multi-corpus lyrics.db — SPEC §4/§5 contract tests.

Covers: license-column migration (migrate-on-open), corpus-scoped dedup and
rebuild (F9 — cross-corpus duplicates are correct), incremental additive mode
with metrics/rhymes only for new ids, and license-field ingestion from song
JSON v2 / _index.json. Default corpus behavior (genius-pro) must be unchanged.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from toolshop.lyricsdb import (
    build_database,
    corpus_dir_for,
    ensure_license_columns,
    CORPUS_TAG,
)

from _fixture_support import LYRICS_MIN_FIXTURE


# ── Helpers ───────────────────────────────────────────────────────────

def _song(title: str, artist: str, lines: list, **kw) -> dict:
    """Minimal song JSON v2."""
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


def _write_corpus(root: Path, category: str, songs: list) -> None:
    cat = root / category
    cat.mkdir(parents=True, exist_ok=True)
    for s in songs:
        slug = re.sub(
            r"[^a-z0-9]+", "-",
            f"{s.get('primary_artist') or s.get('artist')}-{s['title']}".lower(),
        ).strip("-")
        (cat / f"{slug}.json").write_text(
            json.dumps(s, ensure_ascii=False), encoding="utf-8"
        )


def _counts(db_path: Path, corpus: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    out = {
        "songs": conn.execute(
            "SELECT COUNT(*) FROM songs WHERE corpus=?", (corpus,)
        ).fetchone()[0],
        "sections": conn.execute(
            "SELECT COUNT(*) FROM sections se JOIN songs s ON se.song_id=s.id"
            " WHERE s.corpus=?", (corpus,),
        ).fetchone()[0],
        "lines": conn.execute(
            "SELECT COUNT(*) FROM lines l JOIN sections se ON l.section_id=se.id"
            " JOIN songs s ON se.song_id=s.id WHERE s.corpus=?", (corpus,),
        ).fetchone()[0],
        "metrics": conn.execute(
            "SELECT COUNT(*) FROM song_metrics m JOIN songs s ON m.song_id=s.id"
            " WHERE s.corpus=?", (corpus,),
        ).fetchone()[0],
        "rhymes": conn.execute(
            "SELECT COUNT(*) FROM line_rhymes lr JOIN songs s ON lr.song_id=s.id"
            " WHERE s.corpus=?", (corpus,),
        ).fetchone()[0],
    }
    conn.close()
    return out


def _pd_song(title: str, artist: str, fid: str, lines: list) -> dict:
    return _song(
        title, artist, lines,
        corpus="testpd", source="testpd", foreign_identifier=fid,
        source_url=f"https://example.org/{fid}",
        creator=artist, creator_url=None, copyright_notice=None,
        modified_note=None, license="LicenseRef-public-domain",
        license_url="https://creativecommons.org/publicdomain/mark/1.0/",
        license_tier="pd", release_ok="yes", derived_from=None,
        script="latin",
    )


# ── Corpus-scoped dedup / cross-corpus duplicates (F9) ────────────────

def test_cross_corpus_duplicates_kept(tmp_path):
    """Same (title, artist) in two corpora → both rows kept (F9)."""
    root_a = tmp_path / "corpA"
    root_b = tmp_path / "corpB"
    _write_corpus(root_a, "cat", [_song("Shared", "Artist", ["novac popac", "da ne mi"])])
    _write_corpus(root_b, "cat", [_song("Shared", "Artist", ["novac popac", "da ne mi"])])

    db = tmp_path / "t.db"
    build_database(root=root_a, db_path=db, corpus="corp-a")
    build_database(root=root_b, db_path=db, corpus="corp-b")

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT corpus FROM songs WHERE title='Shared' ORDER BY corpus"
    ).fetchall()
    conn.close()
    assert sorted(r[0] for r in rows) == ["corp-a", "corp-b"]


def test_intra_corpus_dedup_unchanged(tmp_path):
    """Two files with same (title, artist) in ONE corpus → one dropped."""
    root = tmp_path / "corpA"
    s = _song("Dup", "Artist", ["novac popac"])
    _write_corpus(root, "cat1", [s])
    _write_corpus(root, "cat2", [s])
    db = tmp_path / "t.db"
    summary = build_database(root=root, db_path=db, corpus="corp-a")
    assert summary["songs_ingested"] == 1
    assert summary["duplicates_dropped"] == 1


# ── Rebuild is corpus-scoped ──────────────────────────────────────────

def test_rebuild_leaves_other_corpora_untouched(tmp_path):
    root_a = tmp_path / "corpA"
    root_b = tmp_path / "corpB"
    _write_corpus(root_a, "cat", [_song("A1", "ArtA", ["novac popac"])])
    _write_corpus(root_b, "cat", [_song("B1", "ArtB", ["zdravo svete"])])
    db = tmp_path / "t.db"
    build_database(root=root_a, db_path=db, corpus="corp-a")
    build_database(root=root_b, db_path=db, corpus="corp-b")
    before_b = _counts(db, "corp-b")

    # Rebuild A — B must be byte-identical
    build_database(root=root_a, db_path=db, corpus="corp-a")
    after_b = _counts(db, "corp-b")
    assert before_b == after_b
    assert _counts(db, "corp-a")["songs"] == 1

    # Rebuild A again — counts stable (idempotent)
    s2 = build_database(root=root_a, db_path=db, corpus="corp-a")
    assert s2["songs_ingested"] == 1
    assert _counts(db, "corp-b") == before_b


# ── Incremental additive mode ─────────────────────────────────────────

def test_incremental_is_additive_and_idempotent(tmp_path):
    """incremental=True never drops rows; run twice → identical counts."""
    root = tmp_path / "corpA"
    _write_corpus(root, "cat", [
        _song("One", "ArtA", ["novac popac", "da ne mi"]),
        _song("Two", "ArtA", ["zdravo svete", "prst je rec"]),
    ])
    db = tmp_path / "t.db"
    s1 = build_database(root=root, db_path=db, corpus="corp-a", incremental=True)
    assert s1["songs_ingested"] == 2
    assert s1["already_present"] == 0
    c1 = _counts(db, "corp-a")

    s2 = build_database(root=root, db_path=db, corpus="corp-a", incremental=True)
    assert s2["songs_ingested"] == 0
    assert s2["already_present"] == 2
    assert _counts(db, "corp-a") == c1

    # metrics/rhymes were NOT re-inserted for existing songs
    assert c1["metrics"] == 2
    assert c1["rhymes"] > 0


def test_incremental_ingests_only_new_files(tmp_path):
    root = tmp_path / "corpA"
    _write_corpus(root, "cat", [_song("One", "ArtA", ["novac popac", "da ne mi"])])
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="corp-a", incremental=True)

    # A second song file appears on disk
    _write_corpus(root, "cat", [_song("Two", "ArtA", ["zdravo svete", "prst rec"])])
    s = build_database(root=root, db_path=db, corpus="corp-a", incremental=True)
    assert s["songs_ingested"] == 1
    assert s["already_present"] == 1
    c = _counts(db, "corp-a")
    assert c["songs"] == 2
    assert c["metrics"] == 2  # metrics only for new id — no dup for song One


def test_incremental_fid_arm_catches_renamed_title(tmp_path):
    """Upstream title edit: same foreign_identifier, new title → skipped."""
    root = tmp_path / "corpPD"
    _write_corpus(root, "cat", [
        _pd_song("Old Title", "Trad", "fid-1", ["novac popac"]),
    ])
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="testpd", incremental=True)

    # Rewrite the file with a different title but same fid
    cat = root / "cat"
    for f in cat.glob("*.json"):
        f.unlink()
    _write_corpus(cat.parent, "cat", [
        _pd_song("Renamed Title", "Trad", "fid-1", ["novac popac"]),
    ])
    s = build_database(root=root, db_path=db, corpus="testpd", incremental=True)
    assert s["songs_ingested"] == 0
    assert s["already_present"] == 1
    conn = sqlite3.connect(db)
    assert conn.execute(
        "SELECT title FROM songs WHERE corpus='testpd'"
    ).fetchone()[0] == "Old Title"  # untouched — refresh is rebuild's job
    conn.close()


def test_incremental_rebuild_mode_replaces_corpus(tmp_path):
    """--rebuild on one corpus re-derives it fully; other corpora keep rows."""
    root_a = tmp_path / "corpA"
    root_b = tmp_path / "corpB"
    _write_corpus(root_a, "cat", [
        _song("A1", "ArtA", ["novac popac"]),
        _song("A2", "ArtA", ["zdravo svete"]),
    ])
    _write_corpus(root_b, "cat", [_song("B1", "ArtB", ["mama voda"])])
    db = tmp_path / "t.db"
    build_database(root=root_a, db_path=db, corpus="corp-a")
    build_database(root=root_b, db_path=db, corpus="corp-b")

    # Remove one file from corpus A, rebuild → only A shrinks.
    victim = sorted((root_a / "cat").glob("*.json"))[0]
    victim.unlink()
    s = build_database(root=root_a, db_path=db, corpus="corp-a")
    assert s["songs_ingested"] == 1
    assert _counts(db, "corp-a")["songs"] == 1
    assert _counts(db, "corp-b")["songs"] == 1


# ── License fields populated ──────────────────────────────────────────

def test_license_fields_ingested(tmp_path):
    root = tmp_path / "corpPD"
    _write_corpus(root, "cat", [
        _pd_song("Ballad", "Traditional", "pg-1", ["novac popac", "da ne mi"]),
    ])
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="testpd")

    conn = sqlite3.connect(db)
    row = conn.execute(
        """SELECT license_tier, license_ref, license_url, release_ok,
                  creator, source_url, foreign_identifier, script
           FROM songs WHERE corpus='testpd'"""
    ).fetchone()
    conn.close()
    assert row == (
        "pd", "LicenseRef-public-domain",
        "https://creativecommons.org/publicdomain/mark/1.0/", "yes",
        "Traditional", "https://example.org/pg-1", "pg-1", "latin",
    )


def test_license_defaults_when_fields_absent(tmp_path):
    """Song JSON without a license block gets the corpus default tier."""
    root = tmp_path / "corpA"  # unknown corpus → builtin safe defaults
    _write_corpus(root, "cat", [_song("X", "Y", ["novac popac"])])
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="no-such-registry-corpus")
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT license_tier, release_ok FROM songs WHERE corpus='no-such-registry-corpus'"
    ).fetchone()
    conn.close()
    assert row == ("study-only", "no")


# ── Migrate-on-open (SPEC §4.2, contract test 4) ──────────────────────

def _v1_songs_schema() -> str:
    """The pre-migration songs CREATE TABLE (v1 columns only)."""
    return """
    CREATE TABLE songs (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        corpus           TEXT    NOT NULL DEFAULT 'genius-pro',
        category         TEXT,
        title            TEXT    NOT NULL,
        primary_artist   TEXT    NOT NULL,
        featured_artists TEXT,
        url              TEXT,
        language         TEXT,
        source_path      TEXT,
        ingested_at      TEXT    NOT NULL,
        role             TEXT,
        target_artist    TEXT,
        genre_cohort     TEXT
    )"""


def test_ensure_license_columns_migrates_v1(tmp_path):
    db = tmp_path / "v1.db"
    conn = sqlite3.connect(db)
    conn.execute(_v1_songs_schema())
    conn.execute(
        """INSERT INTO songs (corpus, category, title, primary_artist,
           featured_artists, url, language, source_path, ingested_at,
           role, target_artist, genre_cohort)
           VALUES ('genius-pro','a-solo','Old Song','Old Artist',
                   '[]','','','p','2026-01-01','solo','a',NULL)"""
    )
    conn.commit()

    v1_cols = [r[1] for r in conn.execute("PRAGMA table_info(songs)")]
    assert "license_tier" not in v1_cols

    n = ensure_license_columns(conn)
    assert n == 1

    cols = [r[1] for r in conn.execute("PRAGMA table_info(songs)")]
    for c in ("license_tier", "license_ref", "license_url", "release_ok",
              "creator", "creator_url", "source_url", "copyright_notice",
              "modified_note", "foreign_identifier", "script", "derived_from"):
        assert c in cols, f"missing column {c}"

    row = conn.execute(
        "SELECT license_tier, license_ref, release_ok FROM songs"
    ).fetchone()
    assert row == ("study-only", "proprietary", "no")

    # v1 columns byte-identical
    row = conn.execute(
        "SELECT corpus, title, primary_artist, role, target_artist FROM songs"
    ).fetchone()
    assert row == ("genius-pro", "Old Song", "Old Artist", "solo", "a")

    # Idempotent — second call is a no-op
    assert ensure_license_columns(conn) == 0
    conn.close()


def test_ensure_license_columns_on_fresh_schema(tmp_path):
    """On a fresh v2 DB the guard is a no-op (columns already in CREATE)."""
    db = tmp_path / "fresh.db"
    conn = sqlite3.connect(db)
    from toolshop.lyricsdb import _create_schema
    _create_schema(conn)
    assert ensure_license_columns(conn) == 0
    conn.close()


# ── Genius default behavior unchanged ─────────────────────────────────

def test_genius_default_corpus_and_license_backfill(tmp_path):
    """corpus=None → 'genius-pro' rows with study-only/proprietary/no."""
    db = tmp_path / "g.db"
    summary = build_database(root=LYRICS_MIN_FIXTURE, db_path=db)
    assert summary["corpus"] == CORPUS_TAG
    assert summary["incremental"] is False
    assert summary["songs_ingested"] == 3  # unchanged fixture counts
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT DISTINCT corpus, license_tier, license_ref, release_ok FROM songs"
    ).fetchall()
    conn.close()
    assert rows == [("genius-pro", "study-only", "proprietary", "no")]


def test_corpus_dir_for_resolution():
    assert corpus_dir_for("genius-pro") == "genius"
    assert corpus_dir_for("ccmixter") == "ccmixter"
    assert corpus_dir_for("mudcat-digitrad") == "mudcat-digitrad"
    assert corpus_dir_for("definitely-not-a-corpus") is None


# ── rhyme_miner --corpus boundaries ───────────────────────────────────

def _multi_db(tmp_path) -> Path:
    """Two-corpora DB: genius-like corpus + a pd corpus."""
    root_a = tmp_path / "ga"
    root_b = tmp_path / "pb"
    _write_corpus(root_a, "fake-solo", [
        _song("GA1", "Gen Artist", ["novac novac", "popac popac", "zdravo svete"]),
    ])
    _write_corpus(root_b, "dt", [
        _pd_song("PB1", "Pd Artist", "p1", ["mama mama", "voda voda", "prst prst"]),
    ])
    db = tmp_path / "multi.db"
    build_database(root=root_a, db_path=db, corpus="genius-pro")
    build_database(root=root_b, db_path=db, corpus="pd-corp")
    return db


def test_rhyme_stats_corpus_boundaries(tmp_path):
    from toolshop.rhyme_miner import get_artist_rhyme_stats
    db = _multi_db(tmp_path)
    conn = sqlite3.connect(db)

    default_rows = get_artist_rhyme_stats(conn)
    assert {r["primary_artist"] for r in default_rows} == {"Gen Artist"}

    pd_rows = get_artist_rhyme_stats(conn, corpus="pd-corp")
    assert {r["primary_artist"] for r in pd_rows} == {"Pd Artist"}

    all_rows = get_artist_rhyme_stats(conn, corpus="all")
    assert {r["primary_artist"] for r in all_rows} == {"Gen Artist", "Pd Artist"}

    # artist + corpus combination
    assert get_artist_rhyme_stats(conn, artist="Pd Artist", corpus="genius-pro") == []
    assert len(get_artist_rhyme_stats(conn, artist="Pd Artist", corpus="pd-corp")) == 1
    conn.close()


def test_rhyme_fingerprints_corpus_boundaries(tmp_path):
    from toolshop.rhyme_miner import get_artist_rhyme_fingerprints
    db = _multi_db(tmp_path)
    conn = sqlite3.connect(db)

    # Both fixture categories derive role='solo' → fingerprint-visible.
    default_rows = get_artist_rhyme_fingerprints(conn)
    assert {r["primary_artist"] for r in default_rows} == {"Gen Artist"}

    pd_rows = get_artist_rhyme_fingerprints(conn, corpus="pd-corp")
    assert {r["primary_artist"] for r in pd_rows} == {"Pd Artist"}

    all_rows = get_artist_rhyme_fingerprints(conn, corpus="all")
    assert {r["primary_artist"] for r in all_rows} == {"Gen Artist", "Pd Artist"}
    conn.close()
