"""export_release.py tests (wave-5b gap-fix, SPEC §8.2 + §7 test 6).

Fixture: a tiny sqlite lyrics.db (v2 song schema) + an on-disk corpus dir of
song JSONs — NO ``import toolshop`` anywhere (F-B1; the script itself reads
sqlite3 directly). Asserts the release-gate contract:

- ``--release-cleared`` emits ONLY ``release_ok='yes'`` rows;
- ``conditional`` rows land in ``pending_decisions``, never in output —
  except items carrying a ``modified_note`` decision behind
  ``--include-conditional``;
- study-only / uncleared corpora contribute ZERO files to a release tree;
- CREDITS.md carries a TASL credit line per emitted item;
- no flag at all refuses (exit 2); ``--include-study`` is the explicit
  opt-in study tree.
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

import export_release  # noqa: E402

_PD_MARK = "https://creativecommons.org/publicdomain/mark/1.0/"

_V2_COLS = """
    id INTEGER PRIMARY KEY,
    corpus TEXT, category TEXT, title TEXT, primary_artist TEXT,
    featured_artists TEXT, url TEXT, language TEXT, source_path TEXT,
    ingested_at TEXT, role TEXT, target_artist TEXT, genre_cohort TEXT,
    license_tier TEXT, license_ref TEXT, license_url TEXT, release_ok TEXT,
    creator TEXT, creator_url TEXT, source_url TEXT, copyright_notice TEXT,
    modified_note TEXT, foreign_identifier TEXT, script TEXT,
    derived_from TEXT
"""


def _song_json(title, artist, lic, tier, ok, source_url, clean):
    return {
        "title": title,
        "primary_artist": artist,
        "artist": artist,
        "featured_artists": [],
        "category": "ballads",
        "corpus": "pd-corp",
        "source": "fixture",
        "url": source_url,
        "source_url": source_url,
        "creator": artist,
        "license": lic,
        "license_url": None,
        "license_tier": tier,
        "release_ok": ok,
        "raw_lyrics": clean,
        "clean_lyrics": clean,
        "sections": [],
        "meta": {},
    }


def _write_song(root: Path, corpus_dir: str, category: str, title: str,
                artist: str, lic: str, tier: str, ok: str,
                source_url: str, clean: str) -> Path:
    slug = f"{artist.lower().replace(' ', '-')}-{title.lower().replace(' ', '-')}"
    p = root / "lyrics" / corpus_dir / category / f"{slug}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    d = _song_json(title, artist, lic, tier, ok, source_url, clean)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    p.with_suffix(".txt").write_text(clean, encoding="utf-8")
    return p


def _row(id_, corpus, category, title, artist, tier, ref, lurl, ok,
         creator=None, source_url=None, note=None, source_path=None):
    return (
        id_, corpus, category, title, artist, "[]", source_url, "en",
        source_path, "2026-10-03", "solo", category, None,
        tier, ref, lurl, ok, creator, None, source_url, None,
        note, f"fid{id_}", "latin", None,
    )


@pytest.fixture()
def fixture_db(tmp_path):
    """Tiny 2-corpus DB: 'pd-corp' (mixed release states) + 'study-corp'
    (study-only). Returns (db_path, out_path-stem parent)."""
    db = tmp_path / "lyrics" / "lyrics.db"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db))
    conn.execute(f"CREATE TABLE songs ({_V2_COLS})")

    files = {}
    files[1] = _write_song(tmp_path, "pd-corp", "ballads", "Barbara Allen",
                           "Traditional", "LicenseRef-public-domain", "pd",
                           "yes", "http://pd.example/ba",
                           "In Scarlet town where I was born\nThere was a fair maid dwellin'")
    files[2] = _write_song(tmp_path, "pd-corp", "ballads", "BY Tune",
                           "Ann Omin", "CC-BY-3.0", "cc-by", "yes",
                           "http://cc.example/by",
                           "line one of the by tune\nline two of the by tune")
    files[3] = _write_song(tmp_path, "pd-corp", "ballads", "SA Tune",
                           "Si Ah", "CC-BY-SA-3.0", "cc-by-sa", "conditional",
                           "http://cc.example/sa",
                           "sa verse one\nsa verse two")
    files[4] = _write_song(tmp_path, "pd-corp", "ballads", "SA Cleared",
                           "Si Ah", "CC-BY-SA-3.0", "cc-by-sa", "conditional",
                           "http://cc.example/sa2",
                           "cleared sa verse\ncleared sa chorus")
    files[5] = _write_song(tmp_path, "pd-corp", "ballads", "NC Tune",
                           "En Cee", "CC-BY-NC-3.0", "cc-by-nc", "no",
                           "http://cc.example/nc",
                           "nc verse one\nnc verse two")
    files[7] = _write_song(tmp_path, "study-corp", "tracks", "Study Song",
                           "Pop Star", "proprietary", "study-only", "no",
                           "http://gen.example/1",
                           "study lyric one\nstudy lyric two")

    rows = [
        _row(1, "pd-corp", "ballads", "Barbara Allen", "Traditional",
             "pd", "LicenseRef-public-domain", _PD_MARK, "yes",
             creator="Traditional", source_url="http://pd.example/ba",
             source_path=str(files[1])),
        _row(2, "pd-corp", "ballads", "BY Tune", "Ann Omin",
             "cc-by", "CC-BY-3.0", "http://creativecommons.org/licenses/by/3.0/",
             "yes", creator="Ann Omin", source_url="http://cc.example/by",
             source_path=str(files[2])),
        _row(3, "pd-corp", "ballads", "SA Tune", "Si Ah",
             "cc-by-sa", "CC-BY-SA-3.0",
             "http://creativecommons.org/licenses/by-sa/3.0/", "conditional",
             creator="Si Ah", source_url="http://cc.example/sa",
             source_path=str(files[3])),
        _row(4, "pd-corp", "ballads", "SA Cleared", "Si Ah",
             "cc-by-sa", "CC-BY-SA-3.0",
             "http://creativecommons.org/licenses/by-sa/3.0/", "conditional",
             creator="Si Ah", source_url="http://cc.example/sa2",
             note="user decision: release cleared 2026-10-03",
             source_path=str(files[4])),
        _row(5, "pd-corp", "ballads", "NC Tune", "En Cee",
             "cc-by-nc", "CC-BY-NC-3.0",
             "http://creativecommons.org/licenses/by-nc/3.0/", "no",
             creator="En Cee", source_url="http://cc.example/nc",
             source_path=str(files[5])),
        _row(6, "pd-corp", "ballads", "Ghost Song", "Nobody",
             "pd", "LicenseRef-public-domain", _PD_MARK, "yes",
             creator="Nobody", source_url="http://pd.example/ghost",
             source_path=None),  # no source file -> skipped_missing_source
        _row(7, "study-corp", "tracks", "Study Song", "Pop Star",
             "study-only", "proprietary", None, "no",
             creator="Pop Star", source_url="http://gen.example/1",
             source_path=str(files[7])),
        _row(8, "study-corp", "tracks", "Study Two", "Pop Star",
             "study-only", "proprietary", None, "no",
             creator="Pop Star", source_url="http://gen.example/2",
             source_path=None),
    ]
    conn.executemany(
        "INSERT INTO songs VALUES (" + ",".join("?" * 25) + ")", rows)
    conn.commit()
    conn.close()
    return db


def _emitted_jsons(out: Path):
    return sorted(out.glob("*/*/*.json"))


def _read_manifest(out: Path):
    return json.loads((out / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))


class TestReleaseGate:
    def test_release_cleared_emits_only_yes(self, fixture_db, tmp_path):
        out = tmp_path / "rel"
        rc = export_release.main(
            ["--release-cleared", "--out", str(out), "--db", str(fixture_db)])
        assert rc == 0
        emitted = _emitted_jsons(out)
        titles = {json.loads(p.read_text(encoding="utf-8"))["title"]
                  for p in emitted}
        assert titles == {"Barbara Allen", "BY Tune"}
        # §7 audit: every emitted row is release_ok='yes'
        for p in emitted:
            d = json.loads(p.read_text(encoding="utf-8"))
            assert d["release_ok"] == "yes"
            assert p.with_suffix(".txt").exists()

    def test_conditional_lands_in_pending_decisions(self, fixture_db, tmp_path):
        out = tmp_path / "rel"
        export_release.main(
            ["--release-cleared", "--out", str(out), "--db", str(fixture_db)])
        man = _read_manifest(out)
        pend = {p["song_id"] for p in man["pending_decisions"]}
        assert pend == {3, 4}
        # never emitted, even the modified_note one (flag not passed)
        assert not any("sa-tune" in p.name or "sa-cleared" in p.name
                       for p in _emitted_jsons(out))

    def test_include_conditional_requires_modified_note(
            self, fixture_db, tmp_path):
        out = tmp_path / "rel"
        export_release.main(
            ["--release-cleared", "--include-conditional",
             "--out", str(out), "--db", str(fixture_db)])
        titles = {json.loads(p.read_text(encoding="utf-8"))["title"]
                  for p in _emitted_jsons(out)}
        assert "SA Cleared" in titles       # modified_note decision -> emitted
        assert "SA Tune" not in titles      # no decision -> still pending
        man = _read_manifest(out)
        assert {p["song_id"] for p in man["pending_decisions"]} == {3}

    def test_study_only_corpus_contributes_zero_files(
            self, fixture_db, tmp_path):
        out = tmp_path / "rel"
        export_release.main(
            ["--release-cleared", "--out", str(out), "--db", str(fixture_db)])
        # 'no' rows are never even candidates: no study-corp dir, no file
        assert not (out / "study-corp").exists()
        man = _read_manifest(out)
        assert "study-corp" not in man["counts_per_corpus"]

    def test_no_flag_refuses(self, fixture_db, tmp_path):
        with pytest.raises(SystemExit) as ei:
            export_release.main(["--out", str(tmp_path / "rel"),
                                 "--db", str(fixture_db)])
        assert ei.value.code == 2

    def test_unknown_corpus_refuses(self, fixture_db, tmp_path):
        rc = export_release.main(
            ["--release-cleared", "--corpus", "bogus-corp",
             "--out", str(tmp_path / "rel"), "--db", str(fixture_db)])
        assert rc == 2

    def test_corpus_filter(self, fixture_db, tmp_path):
        out = tmp_path / "rel"
        rc = export_release.main(
            ["--release-cleared", "--corpus", "study-corp",
             "--out", str(out), "--db", str(fixture_db)])
        assert rc == 0
        assert _emitted_jsons(out) == []   # study-corp emits nothing

    def test_blocker_audit_catches_unsafe_rows(self):
        """The pre-write audit is the BLOCKER backstop: a plan containing a
        release_ok != 'yes' row (that isn't a flagged+decided conditional)
        reports violations."""
        bad = [{"row": {"id": 9, "corpus": "study-corp", "title": "X",
                        "release_ok": "no", "modified_note": None},
                "song": {}, "rel_json": "x.json"}]
        assert export_release._audit_emit_plan(bad, False)
        cond = [{"row": {"id": 9, "corpus": "c", "title": "X",
                         "release_ok": "conditional", "modified_note": None},
                 "song": {}, "rel_json": "x.json"}]
        assert export_release._audit_emit_plan(cond, True)  # flag, no note
        ok = [{"row": {"id": 9, "corpus": "c", "title": "X",
                       "release_ok": "yes", "modified_note": None},
               "song": {}, "rel_json": "x.json"}]
        assert export_release._audit_emit_plan(ok, False) == []


class TestStudyMode:
    def test_include_study_emits_all_with_source(self, fixture_db, tmp_path):
        out = tmp_path / "study"
        rc = export_release.main(
            ["--include-study", "--out", str(out), "--db", str(fixture_db)])
        assert rc == 0
        emitted = _emitted_jsons(out)
        titles = {json.loads(p.read_text(encoding="utf-8"))["title"]
                  for p in emitted}
        assert titles == {"Barbara Allen", "BY Tune", "SA Tune",
                          "SA Cleared", "NC Tune", "Study Song"}
        man = _read_manifest(out)
        assert man["mode"] == "study"
        assert man["counts_per_corpus"] == {"pd-corp": 5, "study-corp": 1}
        # undecided conditionals still surface as pending release decisions
        assert {p["song_id"] for p in man["pending_decisions"]} == {3}
        # both source-less rows are reported
        assert {m["song_id"] for m in man["skipped_missing_source"]} == {6, 8}


class TestCreditsAndManifest:
    def test_credits_tasl_lines(self, fixture_db, tmp_path):
        out = tmp_path / "rel"
        export_release.main(
            ["--release-cleared", "--out", str(out), "--db", str(fixture_db)])
        credits = (out / "CREDITS.md").read_text(encoding="utf-8")
        assert "## pd-corp" in credits
        assert '"Barbara Allen" by Traditional' in credits
        assert "source: http://pd.example/ba" in credits
        assert ("license: LicenseRef-public-domain "
                f"({_PD_MARK})") in credits
        assert '"BY Tune" by Ann Omin' in credits
        assert "license: CC-BY-3.0" in credits
        # study/conditional items never appear in a release CREDITS.md
        assert "Study Song" not in credits
        assert "SA Tune" not in credits

    def test_manifest_per_item_fields(self, fixture_db, tmp_path):
        out = tmp_path / "rel"
        export_release.main(
            ["--release-cleared", "--out", str(out), "--db", str(fixture_db)])
        man = _read_manifest(out)
        assert man["mode"] == "release"
        assert man["total_emitted"] == 2
        assert man["counts_per_corpus"] == {"pd-corp": 2}
        assert man["license_histogram"] == {
            "LicenseRef-public-domain": 1, "CC-BY-3.0": 1}
        by_id = {i["song_id"]: i for i in man["items"]}
        assert set(by_id) == {1, 2}
        for f in ("title", "creator", "license_ref", "license_url",
                  "source_url", "release_ok", "path"):
            assert f in by_id[1]
        assert by_id[1]["license_ref"] == "LicenseRef-public-domain"
        assert by_id[1]["path"].startswith("pd-corp/ballads/")


class TestMigrateOnOpen:
    def test_v1_db_self_heals_and_emits_nothing_for_genius(self, tmp_path):
        """Vendored ensure_license_columns: a v1-schema DB (no license cols)
        opens cleanly; genius rows backfill to study-only/proprietary/no and
        produce ZERO release files."""
        db = tmp_path / "lyrics" / "lyrics.db"
        db.parent.mkdir(parents=True)
        conn = sqlite3.connect(str(db))
        conn.execute("""CREATE TABLE songs (
            id INTEGER PRIMARY KEY, corpus TEXT, category TEXT, title TEXT,
            primary_artist TEXT, source_path TEXT, url TEXT)""")
        conn.execute("INSERT INTO songs VALUES (1,'genius-pro','a-solo','T',"
                     "'Artist',NULL,'')")
        conn.commit()
        conn.close()
        out = tmp_path / "rel"
        rc = export_release.main(
            ["--release-cleared", "--out", str(out), "--db", str(db)])
        assert rc == 0
        assert _emitted_jsons(out) == []
        conn = sqlite3.connect(str(db))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(songs)")}
        assert {"license_tier", "license_ref", "release_ok"} <= cols
        row = conn.execute(
            "SELECT license_tier, license_ref, release_ok FROM songs"
        ).fetchone()
        assert row == ("study-only", "proprietary", "no")
        conn.close()
