"""lyrics-sr lane — cohort derivation on folded artist aliases + NULL backfill.

lrclib lists artists in plain ASCII ('Maya Berovic', 'CØBY') while
COHORT_MAP keys carry diacritics ('Maya Berović', 'Coby').  Cohort
resolution must fold both sides, and ``backfill_genre_cohort`` fills NULL
rows in place — scoped by corpus, never overwriting an existing cohort.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from toolshop.lyricsdb import (
    backfill_genre_cohort,
    build_database,
    derive_genre_cohort,
)


def _song(title: str, artist: str, lines: list, **kw) -> dict:
    body = "\n".join(lines)
    song = {
        "title": title,
        "artist": artist,
        "primary_artist": artist,
        "featured_artists": [],
        "url": "",
        "language": None,
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


def _rows(db: Path, sql: str, params=()):
    conn = sqlite3.connect(db)
    out = conn.execute(sql, params).fetchall()
    conn.close()
    return out


# ── Folded alias matching ─────────────────────────────────────────────

def test_folded_primary_matches_diacritic_key(tmp_path):
    """'Maya Berovic' (ASCII) must hit COHORT_MAP['Maya Berović'] -> pop."""
    root = tmp_path / "lrclib"
    _write(root, "maya-berovic-solo", "m.json",
           _song("Pikachu", "Maya Berovic", ["neka linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="lrclib")
    assert _rows(db, "SELECT genre_cohort FROM songs")[0][0] == "pop"


def test_stylised_o_slash_matches(tmp_path):
    """'CØBY' folds to 'coby' -> drill_trap (short key, word boundary)."""
    root = tmp_path / "lrclib"
    _write(root, "coby-solo", "c.json",
           _song("Ruke", "CØBY", ["neka linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="lrclib")
    assert _rows(db, "SELECT genre_cohort FROM songs")[0][0] == "drill_trap"


def test_derive_featured_keeps_exact_only():
    """Featured role skips substring/folder fallbacks — exact map only."""
    # exact key still resolves regardless of role
    assert derive_genre_cohort("Jala Brat", "featured", "someone-else") == "drill_trap"
    # substring fallback is solo-only
    assert derive_genre_cohort("Jala Brat & Random", "featured", "other") is None


# ── Backfill ──────────────────────────────────────────────────────────

def test_backfill_fills_null_scoped(tmp_path):
    root = tmp_path / "lrclib"
    _write(root, "relja-solo", "r.json",
           _song("A", "Relja", ["neka linija"]))
    _write(root, "x-solo", "x.json",
           _song("B", "Unmapped Artist", ["neka linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="lrclib")

    conn = sqlite3.connect(db)
    # Force the mapped song back to NULL to simulate a pre-fold ingest.
    conn.execute("UPDATE songs SET genre_cohort = NULL WHERE title = 'A'")
    # Move the unmapped song to another corpus to prove scoping.
    conn.execute("UPDATE songs SET corpus = 'other' WHERE title = 'B'")
    conn.commit()

    assert backfill_genre_cohort(conn, corpus="lrclib") == 1
    conn.commit()
    conn.close()

    rows = dict(_rows(db, "SELECT title, genre_cohort FROM songs"))
    assert rows["A"] == "pop"
    assert rows["B"] is None  # 'other' corpus untouched


def test_backfill_never_overwrites(tmp_path):
    root = tmp_path / "genius"
    _write(root, "relja-solo", "r.json",
           _song("A", "Relja", ["neka linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-pro")

    conn = sqlite3.connect(db)
    conn.execute("UPDATE songs SET genre_cohort = 'drill_trap' WHERE title = 'A'")
    conn.commit()
    assert backfill_genre_cohort(conn) == 0
    conn.close()

    assert _rows(db, "SELECT genre_cohort FROM songs")[0][0] == "drill_trap"


def test_unmapped_stays_null_after_backfill(tmp_path):
    root = tmp_path / "lrclib"
    _write(root, "thcf-solo", "t.json",
           _song("A", "THCF", ["neka linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="lrclib")

    conn = sqlite3.connect(db)
    assert backfill_genre_cohort(conn, corpus="lrclib") == 0
    conn.close()
    assert _rows(db, "SELECT genre_cohort FROM songs")[0][0] is None
