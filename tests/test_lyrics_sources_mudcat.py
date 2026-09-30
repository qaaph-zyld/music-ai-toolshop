"""mudcat_digitrad adapter tests (wave B, agent I6).

Covers ``sources/mudcat_digitrad.py`` against the committed synthetic fixture
``tests/fixtures/lyrics_sources/mudcat_digitrad_sample.ask`` — an authored
askSam-shaped binary blob (magic head + UI script fields + ``\\x1c``-separated
records with ``filename[ <id>`` markers and provenance tails). ALL text is
self-authored synthetic: no sourced lyric text, and the copyright-flagged
records carry fabricated notices only (SPEC §7 fixture rule).

Fixture record map (10 records):
- TSTROLL1   pending — PD-style record, (Trad.) credit, tune/initials/date
             trailer, @tags, note: source line, inline [C] chord brackets
- TSTCOPY1   dropped — ``Copyright 1999`` notice (copyright-word)
- TSTTRL1    dropped — ``© 2001`` in its own trailer tail (copyright-sign)
- TSTAFTR    dropped — same © field leaks into its region lead (propagation)
- TSTPERM    dropped — "reproduced … permission of" grant (permission-grant)
- TSTJUNK    dropped — title is comma-joined initials (title-unresolved)
- TSTNOLY    dropped — title + source note only (no-lyric-text)
- TSTROLL1~2 pending — duplicate filename marker, deterministic ~2 suffix
- TSTDIAC    pending — cp1252 diacritics (Œ/É/à/ï/ü/ñ) + @french tag
- TSTBARE    pending — no author credit → creator falls back 'Traditional'

sys.path shim per SPEC §7. NO ``import toolshop``.
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources._common as common  # noqa: E402
import sources.mudcat_digitrad as mudcat  # noqa: E402
import sources.registry as registry  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
ASK_FIXTURE = FIXTURES / "mudcat_digitrad_sample.ask"
TITLES_FIXTURE = FIXTURES / "mudcat_titles_sample.txt"


@pytest.fixture()
def src_dir(tmp_path, monkeypatch):
    """Stage the committed fixtures as a real ``_src`` dir and point the
    adapter at it (module seam — no env needed for direct calls)."""
    src = tmp_path / "_src"
    src.mkdir()
    (src / "Z02.ASK").write_bytes(ASK_FIXTURE.read_bytes())
    (src / "TITLES").write_bytes(TITLES_FIXTURE.read_bytes())
    monkeypatch.setattr(mudcat, "_SRC_DIR", src)
    mudcat._RECORD_CACHE.clear()
    mudcat._TITLES_CACHE.clear()
    return src


@pytest.fixture()
def entries(src_dir):
    return {e.foreign_identifier: e for e in mudcat.iter_catalog()}


# ---------------------------------------------------------------------------
# contract shape (SPEC §6.3 / §7 test 2)
# ---------------------------------------------------------------------------


class TestContract:
    def test_module_shape(self):
        assert mudcat.SOURCE_ID == "mudcat_digitrad"
        assert callable(mudcat.iter_catalog)
        assert callable(mudcat.license_of)
        assert callable(mudcat.fetch_lyrics)

    def test_registry_row_matches_adapter(self):
        row = registry.get("mudcat_digitrad")
        assert row["adapter"] == "mudcat_digitrad"
        assert row["fetch_policy"] == "auto"
        assert row["license_tier"] == "pd"
        assert row["corpus_tag"] == "mudcat-digitrad"
        assert row["license_ref_default"] == "LicenseRef-public-domain"
        assert set(row["categories"]) == {"dt"}


# ---------------------------------------------------------------------------
# archive decoding + record parsing
# ---------------------------------------------------------------------------


class TestParsing:
    def test_decodes_all_records(self, src_dir):
        recs = mudcat.records(src_dir)
        fids = [r["foreign_identifier"] for r in recs]
        assert len(recs) == 10
        assert fids == [
            "TSTROLL1", "TSTCOPY1", "TSTTRL1", "TSTAFTR", "TSTPERM",
            "TSTJUNK", "TSTNOLY", "TSTROLL1~2", "TSTDIAC", "TSTBARE",
        ]

    def test_title_and_ui_rejection(self, src_dir):
        """The binary askSam head + UI script fields must not become the
        first record's title."""
        recs = {r["foreign_identifier"]: r for r in mudcat.records(src_dir)}
        assert recs["TSTROLL1"]["title"] == "ROLLING DOWN THE TEST LANE"
        assert recs["TSTROLL1"]["suspect_title"] is False

    def test_diacritics_and_subtitle(self, src_dir):
        recs = {r["foreign_identifier"]: r for r in mudcat.records(src_dir)}
        assert recs["TSTDIAC"]["title"] == "CŒUR DE TEST ÉTÉ"
        assert recs["TSTDIAC"]["creator"] == "Anaïs Fictive"
        assert "Voilà" in "\n".join(recs["TSTDIAC"]["lyric_fields"])

    def test_traditional_fallback(self, src_dir):
        recs = {r["foreign_identifier"]: r for r in mudcat.records(src_dir)}
        assert recs["TSTBARE"]["creator"] == "Traditional"

    def test_provenance_tail(self, src_dir):
        recs = {r["foreign_identifier"]: r for r in mudcat.records(src_dir)}
        r = recs["TSTROLL1"]
        assert r["tune"] == "TSTROLL1"
        assert r["transcriber"] == "TC"
        assert r["dt_date"] == "oct97"
        assert set(r["tags"]) == {"test", "demo"}

    def test_duplicate_filename_suffix(self, src_dir):
        recs = mudcat.records(src_dir)
        dups = [r for r in recs if r["filename"] == "TSTROLL1"]
        assert len(dups) == 2
        assert {r["foreign_identifier"] for r in dups} == {
            "TSTROLL1", "TSTROLL1~2"}
        assert dups[1]["creator"] == "Variant Two"


# ---------------------------------------------------------------------------
# catalog-stage drops (SPEC §9: ©-flagged never reach disk)
# ---------------------------------------------------------------------------


class TestCatalogDrops:
    def test_statuses(self, entries):
        assert entries["TSTROLL1"].status == "pending"
        assert entries["TSTROLL1~2"].status == "pending"
        assert entries["TSTDIAC"].status == "pending"
        assert entries["TSTBARE"].status == "pending"
        for fid in ("TSTCOPY1", "TSTTRL1", "TSTAFTR", "TSTPERM"):
            assert entries[fid].status == "dropped"
            assert entries[fid].drop_reason.startswith("copyright-flagged:")
        assert entries["TSTJUNK"].status == "dropped"
        assert entries["TSTJUNK"].drop_reason == "title-unresolved"
        assert entries["TSTNOLY"].status == "dropped"
        assert entries["TSTNOLY"].drop_reason == "no-lyric-text"

    def test_marker_names_auditable(self, entries):
        assert entries["TSTCOPY1"].meta["copyright_marker"] == "copyright-word"
        assert entries["TSTTRL1"].meta["copyright_marker"] == "copyright-sign"
        assert entries["TSTPERM"].meta["copyright_marker"] == "permission-grant"

    def test_pending_license_fields(self, entries):
        e = entries["TSTROLL1"]
        assert e.license_tier == "pd"
        assert e.release_ok == "yes"
        assert e.license == "LicenseRef-public-domain"
        assert e.license_url.endswith("/publicdomain/mark/1.0/")
        assert e.category == "dt"
        assert e.source_url == "https://mudcat.org/download.cfm"
        # manifest note (GATE 0 Q4) — charter context rides meta
        assert "not-for-profit" in e.meta["charter_note"]

    def test_catalog_dict_schema(self, entries):
        d = entries["TSTROLL1"].to_dict()
        for k in ("source", "external_id", "foreign_identifier", "title",
                  "creator", "artist", "url", "source_url", "license",
                  "license_url", "license_tier", "license_ref", "release_ok",
                  "copyright_notice", "category", "status", "drop_reason",
                  "meta", "fetched"):
            assert k in d, k
        assert d["source"] == "mudcat_digitrad"
        assert d["external_id"] == "TSTROLL1"
        assert d["status"] in common.ALL_STATUSES

    def test_iter_catalog_limit_offset(self, src_dir):
        assert len(list(mudcat.iter_catalog(limit=3))) == 3
        second = list(mudcat.iter_catalog(limit=1, offset=1))
        assert second[0].foreign_identifier == "TSTCOPY1"


# ---------------------------------------------------------------------------
# license_of — pd/yes for unflagged, DropItem for flagged
# ---------------------------------------------------------------------------


class TestLicenseOf:
    def test_unflagged_pd_release(self, entries):
        info = mudcat.license_of(entries["TSTROLL1"])
        assert info.license == "LicenseRef-public-domain"
        assert info.license_tier == "pd"
        assert info.release_ok == "yes"

    @pytest.mark.parametrize(
        "fid", ["TSTCOPY1", "TSTTRL1", "TSTAFTR", "TSTPERM"])
    def test_flagged_raise_dropitem(self, entries, fid):
        with pytest.raises(common.DropItem) as ei:
            mudcat.license_of(entries[fid])
        assert "copyright-flagged" in ei.value.reason


# ---------------------------------------------------------------------------
# fetch_lyrics — song JSON v2, never for flagged records
# ---------------------------------------------------------------------------


class TestFetchLyrics:
    def test_song_json_v2(self, entries):
        song = mudcat.fetch_lyrics(entries["TSTROLL1"])
        assert song["title"] == "ROLLING DOWN THE TEST LANE"
        assert song["corpus"] == "mudcat-digitrad"
        assert song["source"] == "mudcat_digitrad"
        assert song["foreign_identifier"] == "TSTROLL1"
        assert song["license"] == "LicenseRef-public-domain"
        assert song["license_tier"] == "pd"
        assert song["release_ok"] == "yes"
        assert "not-for-profit" in song["modified_note"]
        assert song["source_url"] == "https://mudcat.org/download.cfm"
        assert song["creator"] == "Trad."
        # [C]/[G7] chord brackets are stripped from clean, kept in raw
        assert "[C]" not in song["clean_lyrics"]
        assert "[C]" in song["raw_lyrics"]
        assert "Rolling down the test lane" in song["clean_lyrics"]
        assert song["sections"]
        assert song["meta"]["dt_filename"] == "TSTROLL1"
        assert song["meta"]["tags"] == ["test", "demo"]
        assert "Transcribed for the synthetic fixture" in \
            song["meta"]["source_line"]

    def test_diacritic_song_and_language(self, entries):
        song = mudcat.fetch_lyrics(entries["TSTDIAC"])
        assert song["title"] == "CŒUR DE TEST ÉTÉ"
        assert "Voilà" in song["raw_lyrics"]
        assert song["language"] == "fr"      # @french tag
        assert song["creator"] == "Anaïs Fictive"

    def test_traditional_fallback_artist(self, entries):
        song = mudcat.fetch_lyrics(entries["TSTBARE"])
        assert song["primary_artist"] == "Traditional"
        assert song["language"] == "en"

    @pytest.mark.parametrize(
        "fid", ["TSTCOPY1", "TSTTRL1", "TSTAFTR", "TSTPERM"])
    def test_flagged_never_returns_song(self, entries, fid):
        """A copyright-flagged item must NEVER produce a song dict —
        defense-in-depth checks both stored meta and the archive record."""
        with pytest.raises(common.DropItem):
            mudcat.fetch_lyrics(entries[fid])


# ---------------------------------------------------------------------------
# offline guarantee + download path
# ---------------------------------------------------------------------------


class TestArchiveAcquisition:
    def test_offline_when_src_exists(self, src_dir, monkeypatch):
        def boom(*a, **kw):
            raise AssertionError("network must not be touched")
        monkeypatch.setattr(mudcat, "_get", boom)
        mudcat._RECORD_CACHE.clear()
        assert len(list(mudcat.iter_catalog(src_dir=src_dir))) == 10

    def test_download_once_when_missing(self, tmp_path, monkeypatch):
        """Empty _src → one polite_get of the zip → unpack → parse."""
        ask_bytes = ASK_FIXTURE.read_bytes()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Z02.ASK", ask_bytes)
            zf.writestr("TITLES", TITLES_FIXTURE.read_bytes())
        zip_bytes = buf.getvalue()

        calls = []

        class FakeResp:
            content = zip_bytes

        def fake_get(url, **kw):
            calls.append(url)
            return FakeResp()

        monkeypatch.setattr(mudcat, "_get", fake_get)
        src = tmp_path / "fresh_src"
        mudcat._RECORD_CACHE.clear()
        mudcat._TITLES_CACHE.clear()
        try:
            recs = mudcat.records(src)
            assert len(recs) == 10
            assert calls == [mudcat.DOWNLOAD_URL]
            state = json.loads(
                (src / "_fetch_state.json").read_text(encoding="utf-8"))
            assert state["downloaded"] is True
            assert state["sha256"]
            # second call is fully offline (zip + ask now present)
            calls.clear()
            mudcat._RECORD_CACHE.clear()
            assert len(mudcat.records(src)) == 10
            assert calls == []
        finally:
            pass


# ---------------------------------------------------------------------------
# dispatcher end-to-end (network fully stubbed — fixture _src)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_dispatcher_run(self, tmp_path, monkeypatch):
        # adapter seam: fixture _src; runner seam: data_dir -> tmp corpus
        fx_src = tmp_path / "lyrics" / "mudcat-digitrad" / "_src"
        fx_src.mkdir(parents=True)
        (fx_src / "Z02.ASK").write_bytes(ASK_FIXTURE.read_bytes())
        (fx_src / "TITLES").write_bytes(TITLES_FIXTURE.read_bytes())
        monkeypatch.setattr(mudcat, "_SRC_DIR", fx_src)
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        mudcat._RECORD_CACHE.clear()
        mudcat._TITLES_CACHE.clear()

        rc = dispatcher.run("mudcat_digitrad", adapter=mudcat,
                            data_dir=tmp_path, quiet=True)
        assert rc == 0
        corpus_root = tmp_path / "lyrics" / "mudcat-digitrad"
        doc = json.loads((corpus_root / "_catalog.json")
                         .read_text(encoding="utf-8"))
        assert doc["source"] == "mudcat_digitrad"
        assert doc["corpus"] == "mudcat-digitrad"
        by_fid = {e["foreign_identifier"]: e for e in doc["entries"]}
        assert len(by_fid) == 10
        for fid in ("TSTROLL1", "TSTROLL1~2", "TSTDIAC", "TSTBARE"):
            assert by_fid[fid]["status"] == "fetched"
        for fid in ("TSTCOPY1", "TSTTRL1", "TSTAFTR", "TSTPERM"):
            assert by_fid[fid]["status"] == "dropped"
            assert by_fid[fid]["drop_reason"].startswith("copyright-flagged")
        assert by_fid["TSTJUNK"]["drop_reason"] == "title-unresolved"
        assert by_fid["TSTNOLY"]["drop_reason"] == "no-lyric-text"

        dt_dir = corpus_root / "dt"
        songs = sorted(dt_dir.glob("*.json"))
        assert len(songs) == 4
        # no copyright-flagged song JSON exists anywhere in the corpus
        for p in songs:
            s = json.loads(p.read_text(encoding="utf-8"))
            assert s["release_ok"] == "yes"
            assert s["license_tier"] == "pd"
            assert s["modified_note"]
            assert s["source"] == "mudcat_digitrad"
            assert s["corpus"] == "mudcat-digitrad"
        fids_on_disk = {s["foreign_identifier"] for s in (
            json.loads(p.read_text(encoding="utf-8")) for p in songs)}
        assert fids_on_disk == {
            "TSTROLL1", "TSTROLL1~2", "TSTDIAC", "TSTBARE"}

        index = json.loads((corpus_root / "_index.json")
                           .read_text(encoding="utf-8"))
        assert len(index) >= 3        # TSTROLL1 pair share (title,artist?) key
        for e in index:
            assert e["license"] == "LicenseRef-public-domain"
            assert e["release_ok"] == "yes"
            assert e["license_tier"] == "pd"

    def test_resume_skips_fetched(self, tmp_path, monkeypatch):
        fx_src = tmp_path / "lyrics" / "mudcat-digitrad" / "_src"
        fx_src.mkdir(parents=True)
        (fx_src / "Z02.ASK").write_bytes(ASK_FIXTURE.read_bytes())
        monkeypatch.setattr(mudcat, "_SRC_DIR", fx_src)
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        mudcat._RECORD_CACHE.clear()
        rc1 = dispatcher.run("mudcat_digitrad", adapter=mudcat,
                             data_dir=tmp_path, quiet=True, resume=True)
        assert rc1 == 0
        corpus_root = tmp_path / "lyrics" / "mudcat-digitrad"
        doc = json.loads((corpus_root / "_catalog.json")
                         .read_text(encoding="utf-8"))
        n_fetched = sum(1 for e in doc["entries"]
                        if e["status"] == "fetched")
        rc2 = dispatcher.run("mudcat_digitrad", adapter=mudcat,
                             data_dir=tmp_path, quiet=True, resume=True)
        assert rc2 == 0
        doc = json.loads((corpus_root / "_catalog.json")
                         .read_text(encoding="utf-8"))
        # nothing re-fetched, nothing un-dropped
        assert sum(1 for e in doc["entries"]
                   if e["status"] == "fetched") == n_fetched


# ---------------------------------------------------------------------------
# live archive smoke — only runs when the real _src exists (not committed)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_real_archive_smoke():
    """Parses the real downloaded archive if present; skips cleanly
    otherwise. Asserts the corpus-level invariants from the pilot."""
    src = registry.lyrics_root() / "mudcat-digitrad" / "_src"
    if not (src / "Z02.ASK").exists():
        pytest.skip("real DigiTrad archive not present under _src")
    recs = mudcat.records(src)
    assert len(recs) > 8000
    flagged = [r for r in recs if r["copyright"]]
    assert len(flagged) > 1000      # the archive carries ~1.6k © items
    fids = [r["foreign_identifier"] for r in recs]
    assert len(set(fids)) == len(fids)  # foreign ids are unique post-suffix
