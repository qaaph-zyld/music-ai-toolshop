"""Tests for ``Genious_lyrics_extractor/make_lrclib_seed.py`` (P2-A/S1).

The seed generator reads ``lyrics.db`` via sqlite3 directly (no toolshop
import) and emits ``<data>/lyrics/lrclib/_seed.json`` shaped
``{"entries": [{"artist":..., "title":...}]}`` — the file
``sources/lrclib.py:_load_seed`` reads. Rows carry artist+title facts
only (genius has no album/duration → adapter routes to ``/api/search``).

Invariants under test:

- corpus filter: only ``--corpus`` rows (default ``genius-pro``) are seeded
- dedup: normalized ``(artist,title)`` — lowercase + strip + collapse
  whitespace — collapses case/space variants
- empty title/artist rows are skipped
- entries are sorted so re-running rewrites the file byte-identical
- ``--dry-run`` prints the count only and writes nothing
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import make_lrclib_seed as seed  # noqa: E402


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    """Temp lyrics.db-shaped fixture: 3 distinct genius-pro rows, 1
    case-variant duplicate, 1 non-genius row, 1 empty-title row."""
    path = tmp_path / "lyrics.db"
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE songs ("
        "  id INTEGER PRIMARY KEY, corpus TEXT, title TEXT,"
        "  primary_artist TEXT, foreign_identifier TEXT)")
    con.executemany(
        "INSERT INTO songs (corpus, title, primary_artist,"
        " foreign_identifier) VALUES (?,?,?,?)",
        [
            ("genius-pro", "Song One", "Artist Alpha", "g1"),
            ("genius-pro", "Song Two", "Artist Beta", "g2"),
            ("genius-pro", "Song Three", "Artist Gamma", "g3"),
            # case/whitespace variant of g1 — must dedup away
            ("genius-pro", "  SONG   ONE ", "artist alpha", "g4"),
            ("other-corpus", "Other Song", "Other Artist", "o1"),
            ("genius-pro", "", "No Title Artist", "g5"),  # skipped
        ],
    )
    con.commit()
    con.close()
    return path


# ---------------------------------------------------------------------------
# build_entries — query + dedup + sort
# ---------------------------------------------------------------------------


class TestBuildEntries:
    def test_emits_exactly_three_entries(self, db):
        """3 genius-pro rows + case-variant dup → 3 entries; non-genius
        and empty-title rows excluded."""
        entries = seed.build_entries(db)
        assert entries == [
            {"artist": "Artist Alpha", "title": "Song One"},
            {"artist": "Artist Beta", "title": "Song Two"},
            {"artist": "Artist Gamma", "title": "Song Three"},
        ]

    def test_entries_are_artist_title_only(self, db):
        """No album/duration keys — that is what routes the adapter to
        /api/search instead of /api/get."""
        for e in seed.build_entries(db):
            assert set(e.keys()) == {"artist", "title"}

    def test_dedup_collapses_case_variant(self, db):
        """The '  SONG   ONE ' / 'artist alpha' variant of g1 does not
        produce a fourth entry; the canonical (first-by-fid) casing is
        kept."""
        entries = seed.build_entries(db)
        titles = [e["title"] for e in entries]
        assert titles.count("Song One") == 1
        assert all(e["artist"] == "Artist Alpha" for e in entries
                   if e["title"] == "Song One")

    def test_corpus_filter(self, db):
        """--corpus override scopes the seed to another corpus."""
        entries = seed.build_entries(db, corpus="other-corpus")
        assert entries == [{"artist": "Other Artist",
                            "title": "Other Song"}]

    def test_unknown_corpus_yields_empty(self, db):
        assert seed.build_entries(db, corpus="no-such-corpus") == []

    def test_whitespace_normalisation_key(self):
        """_norm: lowercase + strip + collapse interior whitespace."""
        assert seed._norm("  Artist   Alpha  ") == "artist alpha"
        assert seed._norm(None) == ""
        assert seed._clean("  Song   One ") == "Song One"


# ---------------------------------------------------------------------------
# main() — end-to-end: file shape, idempotence, dry-run
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_seed_json_shape(self, db, tmp_path):
        out = tmp_path / "lyrics" / "lrclib" / "_seed.json"
        rc = seed.main(["--db", str(db), "--out", str(out)])
        assert rc == 0
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert set(doc.keys()) == {"entries"}
        assert len(doc["entries"]) == 3
        # the exact dict shape sources.lrclib._norm_seed_row accepts
        for e in doc["entries"]:
            assert set(e.keys()) == {"artist", "title"}

    def test_idempotent_byte_identical_rewrite(self, db, tmp_path):
        out = tmp_path / "_seed.json"
        assert seed.main(["--db", str(db), "--out", str(out)]) == 0
        first = out.read_bytes()
        assert seed.main(["--db", str(db), "--out", str(out)]) == 0
        assert out.read_bytes() == first  # sorted → byte-identical

    def test_dry_run_prints_count_only(self, db, tmp_path, capsys):
        out = tmp_path / "_seed.json"
        rc = seed.main(["--db", str(db), "--out", str(out), "--dry-run"])
        assert rc == 0
        assert capsys.readouterr().out.strip() == "3"
        assert not out.exists()  # count only — nothing written

    def test_corpus_flag(self, db, tmp_path):
        out = tmp_path / "_seed.json"
        rc = seed.main(["--db", str(db), "--corpus", "other-corpus",
                        "--out", str(out)])
        assert rc == 0
        doc = json.loads(out.read_text(encoding="utf-8"))
        assert doc["entries"] == [{"artist": "Other Artist",
                                   "title": "Other Song"}]

    def test_missing_db_errors(self, tmp_path, capsys):
        rc = seed.main(["--db", str(tmp_path / "absent.db"), "--dry-run"])
        assert rc == 2
        assert "not found" in capsys.readouterr().err

    def test_toolshop_data_dir_resolution(self, db, tmp_path, monkeypatch):
        """Default out path honours TOOLSHOP_DATA_DIR:
        <data>/lyrics/lrclib/_seed.json."""
        data = tmp_path / "data"
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(data))
        rc = seed.main(["--db", str(db)])
        assert rc == 0
        out = data / "lyrics" / "lrclib" / "_seed.json"
        assert out.exists()
        assert len(json.loads(out.read_text(encoding="utf-8"))
                   ["entries"]) == 3


# ---------------------------------------------------------------------------
# adapter contract — the emitted file must round-trip through
# sources.lrclib._load_seed (the consumer this seed is built for)
# ---------------------------------------------------------------------------


class TestAdapterContract:
    def test_seed_loads_via_lrclib_adapter(self, db, tmp_path):
        import sources.lrclib as lrclib

        out = tmp_path / "_seed.json"
        assert seed.main(["--db", str(db), "--out", str(out)]) == 0

        entries = list(lrclib.iter_catalog(seed=out))
        assert len(entries) == 3
        assert entries[0].title == "Song One"
        assert entries[0].artist == "Artist Alpha"
        # no album/duration → meta carries Nones → _lookup takes /api/search
        assert entries[0].meta == {"album": None, "duration": None}
        assert entries[0].foreign_identifier.startswith("seed:")
