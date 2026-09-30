"""Catalog-only / manual adapter tests — WA agent I4 (SPEC §6.3/§7.2/§9).

Covers ``sources/pdinfo.py`` (title-index harvester, catalog-only),
``sources/looperman.py`` (manual metadata import, ZERO network code), the
gray registry rows (voclr / acapellas4u / paid packs — registry rows only,
no adapter files), and the fetch-policy gate for EVERY non-auto source.

sys.path shim per SPEC §7 — folder scripts live in
``Genious_lyrics_extractor/``; tests live in root ``tests/``. No
``import toolshop`` anywhere under test.
"""

from __future__ import annotations

import importlib
import json
import re
import socket
import subprocess
import sys
import types
from pathlib import Path

import pytest

# -- sys.path shim into the extractor folder (SPEC §7) -----------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources.catalog as catalog_mod  # noqa: E402
import sources.looperman as looperman  # noqa: E402
import sources.pdinfo as pdinfo  # noqa: E402
import sources.registry as registry  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402
from sources import _common as common  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
PDINFO_LIST_HTML = FIXTURES / "pdinfo_list_sample.html"
PDINFO_GENRE_HTML = FIXTURES / "pdinfo_genre_sample.html"
LOOPERMAN_JSON = FIXTURES / "looperman_export_sample.json"
LOOPERMAN_CSV = FIXTURES / "looperman_export_sample.csv"
LOOPERMAN_PATH = EXTRACTOR / "sources" / "looperman.py"

#: SPEC §2.1 frozen matrix — (license_tier, fetch_policy, adapter,
#:  corpus_tag, license_ref_default). Encodes the GATE R roster; drift in
#:  registry.json fails here, not silently downstream.
#: AMENDED by wave-A I3 (registry.json notes): SPEC's separate
#:  sr_wikisource/en_wikisource rows are merged into ONE wikisource_pd
#:  row/corpus per the I3 task prompt; gutenberg corpus_tag is underscored
#:  (corpus dir lyrics/gutenberg_pd).
EXPECTED_ROWS = {
    "genius": ("study-only", "auto", None, "genius-pro", "proprietary"),
    "wikisource_pd": ("pd", "auto", "wikisource_pd", "wikisource_pd",
                      "LicenseRef-public-domain"),
    "gutenberg_pd": ("pd", "auto", "gutenberg_pd", "gutenberg_pd",
                     "LicenseRef-public-domain"),
    "mudcat_digitrad": ("pd", "auto", "mudcat_digitrad", "mudcat-digitrad",
                        "LicenseRef-public-domain"),
    "hymnary": ("pd", "auto", "hymnary", "hymnary",
                "LicenseRef-public-domain"),
    "sacred_texts": ("pd", "auto", "sacred_texts", "sacred-texts",
                     "LicenseRef-public-domain"),
    "ccmixter": ("cc-by", "auto", "ccmixter", "ccmixter", "CC-BY-4.0"),
    "jamendo": ("cc-by", "auto", "jamendo", "jamendo", "CC-BY-4.0"),
    "lrclib": ("study-only", "auto", "lrclib", "lrclib", "proprietary"),
    "pdinfo": ("pd", "catalog-only", "pdinfo", "pdinfo",
               "LicenseRef-public-domain"),
    "looperman": ("uploader-terms", "manual", "looperman", "looperman",
                  "proprietary"),
    "voclr": ("uncleared", "catalog-only", None, "voclr", "proprietary"),
    "acapellas4u": ("uncleared", "catalog-only", None, "acapellas4u",
                    "proprietary"),
    "techhousemarket": ("paid-rf", "manual", None, None, "proprietary"),
    "loopmasters": ("paid-rf", "manual", None, None, "proprietary"),
    "splice": ("paid-rf", "manual", None, None, "proprietary"),
    "vocalfy": ("paid-rf", "manual", None, None, "proprietary"),
    "studiotronnic": ("paid-rf", "manual", None, None, "proprietary"),
    "weaponsounds": ("paid-rf", "manual", None, None, "proprietary"),
}

NON_AUTO_IDS = sorted(
    r["id"] for r in registry.list_sources() if r["fetch_policy"] != "auto"
)
ADAPTERLESS_IDS = sorted(
    r["id"] for r in registry.list_sources() if r.get("adapter") is None
)


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class FakeResp:
    def __init__(self, text="", status=200, headers=None, json_data=None):
        self.text = text
        self.status_code = status
        self.headers = headers or {}
        self._json = json_data

    def json(self):
        if self._json is not None:
            return self._json
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """requests.Session stand-in: serves queued responses, records calls."""

    def __init__(self, responses=None):
        self.responses = list(responses or [FakeResp()])
        self.calls = []

    def get(self, url, **kw):
        self.calls.append({"url": url, **kw})
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


def _no_pace():
    return common.RateLimiter(0, sleep=lambda s: None)


# ---------------------------------------------------------------------------
# Frozen registry rows — SPEC §2.1 conformance (task 3)
# ---------------------------------------------------------------------------


class TestFrozenRegistryRows:
    def test_registry_schema_clean(self):
        problems = registry.validate()
        assert problems == [], f"registry schema violations: {problems}"

    def test_all_20_rows_match_spec_matrix(self):
        rows = {r["id"]: r for r in registry.list_sources()}
        assert set(rows) == set(EXPECTED_ROWS), (
            f"row ids drifted: missing={set(EXPECTED_ROWS) - set(rows)} "
            f"extra={set(rows) - set(EXPECTED_ROWS)}")
        for rid, (tier, pol, adapter, ctag, licref) in EXPECTED_ROWS.items():
            row = rows[rid]
            assert row["license_tier"] == tier, rid
            assert row["fetch_policy"] == pol, rid
            assert row.get("adapter") == adapter, rid
            assert row.get("corpus_tag") == ctag, rid
            assert row.get("license_ref_default") == licref, rid

    @pytest.mark.parametrize("sid", ADAPTERLESS_IDS)
    def test_registry_only_rows_have_no_adapter_file(self, sid):
        """voclr/acapellas4u/genius/paid packs are registry ROWS ONLY —
        no sources/<id>.py may exist while adapter is null (GATE R)."""
        row = registry.get(sid)
        assert row.get("adapter") is None
        mod = EXTRACTOR / "sources" / f"{sid}.py"
        assert not mod.exists(), f"{mod} exists but registry adapter is null"

    def test_cut_section(self):
        cut = {r["id"]: r["reason"] for r in registry.list_cut()}
        assert set(cut) == {"musixmatch", "fma", "wikimedia_commons",
                            "contemplator"}
        assert all(cut.values()), "every cut row needs a reason"


# ---------------------------------------------------------------------------
# Policy gate — EVERY catalog-only/manual source refuses fetch
# ---------------------------------------------------------------------------


class TestPolicyGate:
    @pytest.mark.parametrize("sid", NON_AUTO_IDS)
    def test_require_fetchable_raises(self, sid):
        row = registry.get(sid)
        assert row["fetch_policy"] in ("catalog-only", "manual")
        with pytest.raises(registry.FetchPolicyError):
            registry.require_fetchable(row)

    @pytest.mark.parametrize("sid", NON_AUTO_IDS)
    def test_dispatcher_refuses_fetch(self, sid, tmp_path):
        """A fetch run on a catalog-only/manual source exits 2 BEFORE any
        catalog/adapter work (SPEC §6.4)."""
        rc = dispatcher.run(sid, data_dir=tmp_path, quiet=True)
        assert rc == 2, f"{sid}: fetch run must refuse (rc=2), got {rc}"

    @pytest.mark.parametrize("sid", ADAPTERLESS_IDS)
    def test_catalog_only_on_adapterless_row_fails_clean(self, sid, tmp_path):
        """--catalog-only still fails clearly when adapter is null."""
        rc = dispatcher.run(sid, data_dir=tmp_path, catalog_only=True,
                            quiet=True)
        assert rc == 2

    @pytest.mark.parametrize("sid", ["genius"])
    def test_auto_but_adapterless_raises(self, sid, tmp_path):
        rc = dispatcher.run(sid, data_dir=tmp_path, quiet=True)
        assert rc == 2


# ---------------------------------------------------------------------------
# Module contract — SPEC §6.3/§7.2
# ---------------------------------------------------------------------------


class TestAdapterContract:
    def test_pdinfo_module_shape(self):
        assert pdinfo.SOURCE_ID == "pdinfo"
        assert callable(pdinfo.iter_catalog)
        assert callable(pdinfo.license_of)
        assert not hasattr(pdinfo, "fetch_lyrics"), \
            "catalog-only source must not ship fetch_lyrics"

    def test_looperman_module_shape(self):
        assert looperman.SOURCE_ID == "looperman"
        assert callable(looperman.iter_catalog)
        assert callable(looperman.license_of)
        assert not hasattr(looperman, "fetch_lyrics"), \
            "manual source must not ship fetch_lyrics"

    def test_every_shipped_adapter_matches_policy(self):
        """Same contract as W1's tolerant test, evaluated against the
        modules that exist NOW: auto -> 3 fns; catalog-only/manual ->
        iter_catalog (+license_of), NO fetch_lyrics."""
        for row in registry.list_sources():
            name = row.get("adapter")
            if not name:
                continue
            mod_file = EXTRACTOR / "sources" / f"{name}.py"
            if not mod_file.exists():
                continue  # adapter lands in a later wave
            mod = registry.resolve_adapter(row)
            assert hasattr(mod, "iter_catalog"), name
            assert hasattr(mod, "license_of"), name
            if row["fetch_policy"] == "auto":
                assert hasattr(mod, "fetch_lyrics"), name
            else:
                assert not hasattr(mod, "fetch_lyrics"), name


# ---------------------------------------------------------------------------
# Looperman — ZERO NETWORK contract (BLOCKER per R3 §1 / SPEC §7.2)
# ---------------------------------------------------------------------------


class TestLoopermanNoNetwork:
    """Looperman ToS bans scraping AND ML training verbatim (R3 §1), so
    sources/looperman.py must contain zero network code — proven three ways:
    source-text scan, absent fetch_lyrics, and a fresh-interpreter import
    that must place no network stack in sys.modules."""

    _BANNED_PATTERNS = (
        r"^\s*import\s+requests\b", r"^\s*from\s+requests\b",
        r"^\s*import\s+urllib\b", r"^\s*from\s+urllib\b",
        r"^\s*import\s+urllib3\b", r"^\s*from\s+urllib3\b",
        r"^\s*import\s+http\b", r"^\s*from\s+http\b",
        r"^\s*import\s+socket\b", r"^\s*from\s+socket\b",
        r"^\s*import\s+ssl\b", r"^\s*from\s+ssl\b",
        r"^\s*import\s+httpx\b", r"^\s*from\s+httpx\b",
        r"^\s*import\s+aiohttp\b", r"^\s*from\s+aiohttp\b",
        r"^\s*import\s+ftplib\b", r"^\s*import\s+smtplib\b",
        r"\burlopen\b", r"\burlretrieve\b",
        r"\brequests\.", r"\burllib\.", r"\bhttpx\.",
        r"\bsocket\.", r"\baiohttp\.",
        r"https?://",
    )

    def test_looperman_source_contains_no_network_code(self):
        """Source-text proof: no network imports, no fetch calls, no URL
        constants. The docstring may mention the domain name but never a
        fetchable URL."""
        src = LOOPERMAN_PATH.read_text(encoding="utf-8")
        for pat in self._BANNED_PATTERNS:
            assert not re.search(pat, src, re.M), \
                f"network code found in looperman.py: {pat!r}"

    def test_looperman_has_no_fetch_lyrics(self):
        mod = importlib.import_module("sources.looperman")
        assert not hasattr(mod, "fetch_lyrics"), \
            "manual sources must not define fetch_lyrics (SPEC §6.3)"

    def test_looperman_import_pulls_no_network_stack(self):
        """Fresh-interpreter proof: importing sources.looperman must not
        add requests/urllib/http/socket/ssl to sys.modules — the module
        carries no network stack at all, not even transitively. (Delta
        measured against interpreter startup, which already holds
        urllib.parse via site hooks.)"""
        code = (
            "import sys\n"
            "before = set(sys.modules)\n"
            f"sys.path.insert(0, {str(EXTRACTOR)!r})\n"
            "import sources.looperman\n"
            "net = ('requests', 'urllib', 'urllib3', 'http', 'socket',\n"
            "       'ssl', 'httpx', 'aiohttp', 'ftplib', 'smtplib')\n"
            "bad = sorted(m for m in set(sys.modules) - before\n"
            "           if m.split('.')[0] in net)\n"
            "print(bad)\n"
            "sys.exit(1 if bad else 0)\n"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=60,
        )
        assert res.returncode == 0, (
            f"network modules leaked via looperman import: "
            f"{res.stdout.strip()} / {res.stderr.strip()}")
        assert res.stdout.strip() == "[]"

    def test_iter_catalog_runs_with_sockets_blocked(self, monkeypatch):
        """Runtime proof: even if a code path somehow reached for the
        network, a blocked socket layer must not stop iter_catalog."""
        def boom(*a, **k):
            raise AssertionError("network access attempted in looperman")
        monkeypatch.setattr(socket, "create_connection", boom)
        monkeypatch.setattr(socket.socket, "connect", boom)
        entries = list(looperman.iter_catalog(path=LOOPERMAN_JSON))
        assert entries, "iter_catalog must parse the export with no network"

    def test_license_of_is_constant_policy(self):
        info = looperman.license_of({"title": "x"})
        assert info["license_tier"] == "uploader-terms"
        assert info["release_ok"] == "no"
        assert info["license"] == "proprietary"


# ---------------------------------------------------------------------------
# Looperman — hand-export import behavior
# ---------------------------------------------------------------------------


class TestLoopermanImport:
    def test_json_export_rows(self):
        entries = list(looperman.iter_catalog(path=LOOPERMAN_JSON))
        assert len(entries) == 3
        by_fid = {e["foreign_identifier"]: e for e in entries}
        e = by_fid["22017"]
        assert e["source_id"] == "looperman" == e["source"]
        assert e["title"] == "Fixture Rain Chant"
        assert e["creator"] == "voxsmith" and e["artist"] == "voxsmith"
        assert e["license_tier"] == "uploader-terms"
        assert e["license"] == "proprietary" == e["license_ref"]
        assert e["release_ok"] == "no"
        assert e["status"] == "pending" and e["fetched"] is False
        meta = e["meta"]
        assert meta["bpm"] == 126 and meta["key"] == "Am"
        assert meta["genre"] == "Electronic"
        assert meta["usage"] == "Free Non Commercial Only"
        assert meta["has_lyrics"] is True
        assert meta["import_provenance"] == LOOPERMAN_JSON.name
        # derived fid for the row with no explicit id
        assert any(fid.startswith("lp-") for fid in by_fid)

    def test_free_text_fields_refused(self):
        """Uploader © text must never reach the catalog (R3 §1)."""
        entries = list(looperman.iter_catalog(path=LOOPERMAN_JSON))
        e = next(x for x in entries if x["foreign_identifier"] == "22017")
        blob = json.dumps(e, ensure_ascii=False)
        assert "FIXTURE uploader free text" not in blob
        assert "FIXTURE lyric placeholder" not in blob
        for banned in ("description", "lyrics", "lyric", "comment", "notes"):
            assert banned not in e["meta"]

    def test_csv_export_rows(self):
        entries = list(looperman.iter_catalog(path=LOOPERMAN_CSV))
        assert len(entries) == 3
        by_fid = {e["foreign_identifier"]: e for e in entries}
        e = by_fid["22040"]
        assert e["creator"] == "melodica_jane"
        assert e["meta"]["bpm"] == 140 and e["meta"]["key"] == "F#m"
        assert e["meta"]["usage"] == "Free Commercial & Non Commercial"

    def test_dropzone_directory_discovery(self, tmp_path):
        """A directory path scans *.json/*.jsonl/*.csv and dedups by fid —
        the same song appearing in two exports merges into one row."""
        zone = tmp_path / "_import"
        zone.mkdir()
        zone.joinpath("a.json").write_text(
            LOOPERMAN_JSON.read_text(encoding="utf-8"), encoding="utf-8")
        zone.joinpath("b.csv").write_text(
            LOOPERMAN_CSV.read_text(encoding="utf-8"), encoding="utf-8")
        entries = list(looperman.iter_catalog(path=zone))
        fids = [e["foreign_identifier"] for e in entries]
        assert len(fids) == len(set(fids)) == 5  # 3 json + 3 csv − dup 22017
        dup = next(e for e in entries if e["foreign_identifier"] == "22017")
        # last export file wins on metadata refresh (b.csv parsed after a.json)
        assert dup["meta"]["import_provenance"] == "b.csv"

    def test_catalog_json_fallback(self, tmp_path):
        """No _import files → the hand-maintained _catalog.json itself is
        the import source (SPEC §9); round-trip is fid-idempotent."""
        corpus = tmp_path / "lyrics" / "looperman"
        corpus.mkdir(parents=True)
        existing = {
            "version": 1, "source": "looperman", "corpus": "looperman",
            "entries": [
                {"source": "looperman", "foreign_identifier": "99001",
                 "title": "Hand Kept Row", "creator": "upldr",
                 "status": "fetched",
                 "meta": {"bpm": 88, "key": "Gm"}},
            ],
        }
        (corpus / "_catalog.json").write_text(
            json.dumps(existing, ensure_ascii=False), encoding="utf-8")
        entries = list(looperman.iter_catalog(data_dir=tmp_path))
        assert len(entries) == 1
        e = entries[0]
        assert e["foreign_identifier"] == "99001"
        assert e["creator"] == "upldr" and e["meta"]["bpm"] == 88
        assert e["status"] == "fetched" and e["fetched"] is True

    def test_empty_sources_yield_nothing(self, tmp_path):
        assert list(looperman.iter_catalog(data_dir=tmp_path)) == []

    def test_limit_offset(self):
        all_e = list(looperman.iter_catalog(path=LOOPERMAN_JSON))
        assert len(list(looperman.iter_catalog(path=LOOPERMAN_JSON,
                                               limit=1))) == 1
        assert (list(looperman.iter_catalog(path=LOOPERMAN_JSON,
                                            offset=2)) == all_e[2:])

    def test_dispatcher_catalog_only_end_to_end(self, tmp_path, monkeypatch):
        """Real adapter resolution through the dispatcher: the drop-zone
        under TOOLSHOP_DATA_DIR feeds _catalog.json."""
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        zone = tmp_path / "lyrics" / "looperman" / "_import"
        zone.mkdir(parents=True)
        zone.joinpath("export.json").write_text(
            LOOPERMAN_JSON.read_text(encoding="utf-8"), encoding="utf-8")
        rc = dispatcher.run("looperman", data_dir=tmp_path,
                            catalog_only=True, quiet=True)
        assert rc == 0
        doc = json.loads(
            (tmp_path / "lyrics" / "looperman" / "_catalog.json")
            .read_text(encoding="utf-8"))
        assert len(doc["entries"]) == 3
        for e in doc["entries"]:
            assert e["status"] == "pending" and e["fetched"] is False
            assert e["license_tier"] == "uploader-terms"
            assert e["release_ok"] == "no"


# ---------------------------------------------------------------------------
# PDInfo — title-list parsing + catalog harvest
# ---------------------------------------------------------------------------


class TestPdinfoParser:
    def _entries_best(self):
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        return pdinfo.parse_list_page(
            html, list_kind="best-known", list_label="best-a",
            page_url="https://fixture/best-a")

    def test_best_list_rows(self):
        rows = self._entries_best()
        songs = [r for r in rows if r["row_kind"] == "song"]
        xref = [r for r in rows if r["row_kind"] == "see-also"]
        assert len(songs) == 4 and len(xref) == 1

        kettle = next(r for r in songs if r["title"] == "Ballad Of The Test Kettle")
        assert kettle["genre"] == "Popular Song"
        assert kettle["year"] == 1914
        assert kettle["attribution"] == "w.m. Ada Fields, Walter Testman"
        assert kettle["product_id"] == "TP00012"

        meadow = next(r for r in songs if r["title"] == "A Fixture Meadow")
        assert meadow["year"] == 1777 and meadow["attribution"] == "Traditional"

        nocred = next(r for r in songs if "No Credits" in r["title"])
        assert nocred["year"] is None and nocred["attribution"] == ""

        assert xref[0]["title"] == "A B C Fixture"
        assert xref[0]["canonical_title"] == "Alphabet Fixture Song"

    def test_genre_page_markup_variant(self):
        html = PDINFO_GENRE_HTML.read_text(encoding="utf-8")
        rows = pdinfo.parse_list_page(
            html, list_kind="genre", list_label="genre-hymns",
            page_url="https://fixture/hymns")
        assert len(rows) == 2
        abide = rows[0]
        assert abide["title"] == "Abide With Fixture"
        assert abide["year"] == 1844  # <span class="b"> year markup
        assert "Lytton, Henry F." in abide["attribution"]

    def test_lyric_snippets_never_harvested(self):
        """V/C/N/P dbk blocks are ignored — this is a title index."""
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        rows = pdinfo.parse_list_page(html, list_kind="best-known",
                                      list_label="best-a")
        blob = json.dumps(rows, ensure_ascii=False)
        assert "FIXTURE verse placeholder" not in blob
        assert "FIXTURE chorus placeholder" not in blob
        for r in rows:
            assert "lyrics" not in r and "verse" not in r

    def test_empty_page_yields_nothing(self):
        assert pdinfo.parse_list_page("", list_kind="x", list_label="x") == []

    def test_catalog_entry_fields(self, tmp_path):
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        session = FakeSession([FakeResp(html)])
        entries = list(pdinfo.iter_catalog(
            session=session, cache_dir=tmp_path / "cache",
            pages=[("pd-song-list/pd-song-list-best-a.php",
                    "best-known", "best-a")],
            limiter=_no_pace()))
        assert len(entries) == 5  # 4 songs + 1 see-also
        by_fid = {e.foreign_identifier: e for e in entries}
        e = by_fid["pdinfo-TP00012"]  # cart id -> stable foreign_identifier
        assert e.title == "Ballad Of The Test Kettle"
        assert e.creator == "Ada Fields, Walter Testman"
        assert e.license == "LicenseRef-public-domain"
        assert e.license_tier == "pd" and e.release_ok == "yes"
        assert e.category == "" and e.status == "pending"
        assert e.meta["pd_claim"] == "unverified"
        assert e.meta["fetch_hint"] == "resolve-via-wikisource"
        assert e.meta["lists"] == ["best-a"]
        assert e.source_url.startswith("https://")
        x = by_fid["pdinfo-xref-best-a-a-b-c-fixture"]
        assert x.meta["row_kind"] == "see-also"
        assert x.meta["canonical_title"] == "Alphabet Fixture Song"

    def test_license_of_pd_constant(self):
        info = pdinfo.license_of(None)
        assert info.license == "LicenseRef-public-domain"
        assert info.license_tier == "pd" and info.release_ok == "yes"


class TestPdinfoHarvest:
    def test_dedup_across_lists(self, tmp_path):
        """Same product id on two lists → one entry, merged list provenance."""
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        session = FakeSession([FakeResp(html)])
        pages = [
            ("pd-song-list/pd-song-list-best-a.php", "best-known", "best-a"),
            ("pd-music-genres/pd-popular-songs.php", "genre", "genre-popular-songs"),
        ]
        entries = list(pdinfo.iter_catalog(
            session=session, cache_dir=tmp_path / "cache",
            pages=pages, limiter=_no_pace()))
        # FakeSession repeats last response → both pages return fixture html
        e = next(x for x in entries if x.foreign_identifier == "pdinfo-TP00012")
        assert sorted(e.meta["lists"]) == ["best-a", "genre-popular-songs"]

    def test_404_page_tolerated(self, tmp_path):
        session = FakeSession([FakeResp(status=404)])
        entries = list(pdinfo.iter_catalog(
            session=session, cache_dir=tmp_path / "cache",
            pages=[("pd-song-list/pd-song-list-less-g.php",
                    "less-known", "less-g")],
            limiter=_no_pace()))
        assert entries == []

    def test_cache_hit_needs_no_network(self, tmp_path, monkeypatch):
        """A cached page replays with session=None and polite_get banned —
        the fetch-once contract is real."""
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / pdinfo._cache_name("pd-song-list/pd-song-list-best-a.php")
         ).write_text(PDINFO_LIST_HTML.read_text(encoding="utf-8"),
                      encoding="utf-8")

        def boom(*a, **k):
            raise AssertionError("network attempted on cache hit")
        monkeypatch.setattr(pdinfo, "polite_get", boom)

        entries = list(pdinfo.iter_catalog(
            session=None, cache_dir=cache,
            pages=[("pd-song-list/pd-song-list-best-a.php",
                    "best-known", "best-a")],
            limiter=_no_pace()))
        assert len(entries) == 5

    def test_fetch_writes_cache(self, tmp_path):
        cache = tmp_path / "cache"
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        session = FakeSession([FakeResp(html)])
        entries = list(pdinfo.iter_catalog(
            session=session, cache_dir=cache,
            pages=[("pd-song-list/pd-song-list-best-a.php",
                    "best-known", "best-a")],
            limiter=_no_pace()))
        assert len(entries) == 5
        assert (cache / pdinfo._cache_name(
            "pd-song-list/pd-song-list-best-a.php")).exists()
        # second run from cache: session exhausted (empty) but still works
        session2 = FakeSession([])
        session2.responses = []  # would IndexError if network attempted
        entries2 = list(pdinfo.iter_catalog(
            session=session2, cache_dir=cache,
            pages=[("pd-song-list/pd-song-list-best-a.php",
                    "best-known", "best-a")],
            limiter=_no_pace()))
        assert len(entries2) == 5

    def test_limit_offset(self, tmp_path):
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        session = FakeSession([FakeResp(html)])
        kw = dict(session=session, cache_dir=tmp_path / "cache",
                  pages=[("p.php", "best-known", "best-a")], limiter=_no_pace())
        all_e = list(pdinfo.iter_catalog(**kw))
        assert len(list(pdinfo.iter_catalog(limit=1, **kw))) == 1
        assert [e.foreign_identifier for e in
                pdinfo.iter_catalog(offset=2, **kw)] == \
               [e.foreign_identifier for e in all_e[2:]]

    def test_dispatcher_catalog_only_end_to_end(self, tmp_path):
        """The dispatcher's catalog-only path persists pdinfo entries into
        <corpus>/_catalog.json (the corpus dir comes from the registry)."""
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        session = FakeSession([FakeResp(html)])
        cache = tmp_path / "cache"

        def _iter(limit=None, offset=0):
            return pdinfo.iter_catalog(
                limit=limit, offset=offset, session=session, cache_dir=cache,
                pages=[("pd-song-list/pd-song-list-best-a.php",
                        "best-known", "best-a")],
                limiter=_no_pace())

        adapter = types.SimpleNamespace(SOURCE_ID="pdinfo",
                                        iter_catalog=_iter,
                                        license_of=pdinfo.license_of)
        rc = dispatcher.run("pdinfo", adapter=adapter, data_dir=tmp_path,
                            catalog_only=True, quiet=True)
        assert rc == 0
        doc = json.loads(
            (tmp_path / "lyrics" / "pdinfo" / "_catalog.json")
            .read_text(encoding="utf-8"))
        assert len(doc["entries"]) == 5
        for e in doc["entries"]:
            assert e["status"] == "pending"
            assert e["license_tier"] == "pd" and e["release_ok"] == "yes"
            assert e["meta"]["fetch_hint"] == "resolve-via-wikisource"
            assert e["meta"]["pd_claim"] == "unverified"


# ---------------------------------------------------------------------------
# Catalog schema conformance — serialized rows carry the frozen field set
# ---------------------------------------------------------------------------


class TestCatalogSchema:
    REQUIRED_FIELDS = (
        "source", "external_id", "title", "artist", "url",
        "license_tier", "license_ref", "release_ok", "fetched",
        "foreign_identifier", "creator", "source_url", "license",
        "license_url", "category", "status", "meta",
    )

    def test_pdinfo_rows_serialize(self, tmp_path):
        cat = catalog_mod.Catalog.for_corpus(
            tmp_path, source_id="pdinfo", corpus="pdinfo")
        html = PDINFO_LIST_HTML.read_text(encoding="utf-8")
        session = FakeSession([FakeResp(html)])
        entries = list(pdinfo.iter_catalog(
            session=session, cache_dir=tmp_path / "c",
            pages=[("p.php", "best-known", "best-a")], limiter=_no_pace()))
        cat.upsert_entries(entries)
        cat.save()
        doc = json.loads(cat.path.read_text(encoding="utf-8"))
        for e in doc["entries"]:
            for f in self.REQUIRED_FIELDS:
                assert f in e, f"catalog row missing field {f}"
            assert e["status"] in common.ALL_STATUSES

    def test_looperman_rows_serialize(self, tmp_path):
        cat = catalog_mod.Catalog.for_corpus(
            tmp_path, source_id="looperman", corpus="looperman")
        cat.upsert_entries(looperman.iter_catalog(path=LOOPERMAN_JSON))
        cat.save()
        doc = json.loads(cat.path.read_text(encoding="utf-8"))
        for e in doc["entries"]:
            for f in self.REQUIRED_FIELDS:
                assert f in e, f"catalog row missing field {f}"
            assert e["status"] in common.ALL_STATUSES
            assert e["license_tier"] == "uploader-terms"
