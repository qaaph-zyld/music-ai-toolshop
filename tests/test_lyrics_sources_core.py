"""Core tests for the license-tiered lyrics-source infrastructure (W1).

Covers ``sources/_common.py`` (vendored RobotsPolicy, polite_get pacing,
catalog/song/index writers, TASL), ``sources/registry.py`` (frozen schema +
fetch-policy gate), ``sources/catalog.py`` (resumable _catalog.json), and the
``fetch_lyrics_source.py`` dispatcher.

sys.path shim per SPEC §7: folder scripts live in ``Genious_lyrics_extractor/``
while tests live in root ``tests/`` (pytest.ini testpaths). NO ``import
toolshop`` anywhere under test — the eager package __init__ costs ~70 s.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

# -- sys.path shim into the extractor folder (SPEC §7) -----------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources._common as common  # noqa: E402
import sources.catalog as catalog_mod  # noqa: E402
import sources.registry as registry  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
TEST_REGISTRY = FIXTURES / "registry_test.json"


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


def make_adapter(items=None, song_factory=None, on_fetch=None):
    """Injected adapter module object satisfying the SPEC §6.3 contract."""
    mod = types.ModuleType("fake_auto_adapter")
    mod.SOURCE_ID = "fake_auto"
    state = {"fetch_calls": 0}
    items = items if items is not None else [
        common.CatalogEntry(
            source_id="fake_auto", foreign_identifier="f-1",
            title="Kafu mi Draga", url="https://example.org/s/1",
            creator="Uploader One", category="folk",
            license="LicenseRef-public-domain", license_tier="pd",
            release_ok="yes",
        ),
        common.CatalogEntry(
            source_id="fake_auto", foreign_identifier="f-2",
            title="Täterprofil ćevap", url="https://example.org/s/2",
            creator="Uploader Two", category="misc",
            license="CC-BY-4.0", license_tier="cc-by", release_ok="yes",
        ),
    ]

    def iter_catalog(limit=None, offset=0):
        out = list(items)
        if offset:
            out = out[offset:]
        if limit is not None:
            out = out[:limit]
        return iter(out)

    def license_of(entry):
        return common.LicenseInfo(
            license=entry.license or "LicenseRef-public-domain",
            license_url=entry.license_url,
            license_tier=entry.license_tier or "pd",
            release_ok=entry.release_ok or "yes",
        )

    def fetch_lyrics(entry):
        state["fetch_calls"] += 1
        if on_fetch:
            on_fetch(entry)
        if song_factory:
            return song_factory(entry)
        return {
            "title": entry.title,
            "primary_artist": entry.creator or "Traditional",
            "artist": entry.creator or "Traditional",
            "category": entry.category,
            "url": entry.url,
            "language": "sr",
            "raw_lyrics": "prva strofa teksta\ndruga strofa teksta",
            "clean_lyrics": "prva strofa teksta\ndruga strofa teksta",
            "sections": [{"label": None, "content": "prva strofa teksta"}],
        }

    mod.iter_catalog = iter_catalog
    mod.license_of = license_of
    mod.fetch_lyrics = fetch_lyrics
    mod._state = state
    return mod


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_registry_loads_and_conforms(self):
        problems = registry.validate()
        assert problems == [], f"frozen registry schema violations: {problems}"
        rows = registry.list_sources()
        assert len(rows) == 19, (
            f"expected 19 frozen rows (wave-A I3 merged sr/en wikisource "
            f"-> wikisource_pd), got {len(rows)}")

    def test_frozen_rows_and_genius_exception(self):
        genius = registry.get("genius")
        assert genius["corpus_tag"] == "genius-pro"
        assert genius["corpus_dir"] == "genius"  # the ONE legacy exception
        for row in registry.list_sources():
            if row["id"] == "genius":
                continue
            assert registry.corpus_dir(row) == row.get("corpus_tag"), row["id"]
        cut_ids = {r["id"] for r in registry.list_cut()}
        assert cut_ids == {"musixmatch", "fma", "wikimedia_commons",
                           "contemplator"}

    def test_get_unknown_source_raises_keyerror(self):
        with pytest.raises(KeyError, match="unknown source id"):
            registry.get("does_not_exist")

    def test_enum_membership(self):
        for row in registry.list_sources():
            assert row["license_tier"] in registry.LICENSE_TIERS
            assert row["fetch_policy"] in registry.FETCH_POLICIES

    def test_jamendo_env_gate_row(self):
        row = registry.get("jamendo")
        assert row["env_gate"] == "JAMENDO_CLIENT_ID"
        assert row["fetch_policy"] == "auto"
        assert row["adapter"] == "jamendo"


# ---------------------------------------------------------------------------
# fetch policy gate — catalog-only/manual sources raise on fetch
# ---------------------------------------------------------------------------


class TestFetchPolicy:
    @pytest.mark.parametrize("sid", ["voclr", "acapellas4u"])
    def test_catalog_only_source_raises_on_fetch(self, sid):
        row = registry.get(sid)
        assert row["fetch_policy"] == "catalog-only"
        with pytest.raises(registry.FetchPolicyError, match="catalog-only"):
            registry.require_fetchable(row)

    @pytest.mark.parametrize("sid", ["looperman", "techhousemarket", "splice"])
    def test_manual_source_raises_on_fetch(self, sid):
        row = registry.get(sid)
        assert row["fetch_policy"] == "manual"
        with pytest.raises(registry.FetchPolicyError, match="manual"):
            registry.require_fetchable(row)

    def test_registry_row_only_raises_on_fetch(self):
        row = registry.get("genius")  # auto policy but adapter: null
        with pytest.raises(registry.FetchPolicyError, match="adapter=null"):
            registry.require_fetchable(row)

    def test_adapterless_source_resolve_raises(self):
        with pytest.raises(registry.FetchPolicyError, match="no adapter"):
            registry.resolve_adapter(registry.get("voclr"))

    def test_dispatcher_refuses_catalog_only_source(self, tmp_path, capsys):
        rc = dispatcher.run(
            "fake_catalog", registry_path=TEST_REGISTRY, data_dir=tmp_path
        )
        assert rc == 2
        assert "catalog-only" in capsys.readouterr().err

    def test_dispatcher_refuses_manual_source(self, tmp_path, capsys):
        rc = dispatcher.run(
            "fake_manual", registry_path=TEST_REGISTRY, data_dir=tmp_path
        )
        assert rc == 2
        assert "manual" in capsys.readouterr().err

    def test_dispatcher_refuses_adapterless_catalog(self, tmp_path, capsys):
        # --catalog-only on a row with adapter:null is still a clear error
        rc = dispatcher.run(
            "fake_catalog", registry_path=TEST_REGISTRY, data_dir=tmp_path,
            catalog_only=True,
        )
        assert rc == 2
        assert "no adapter" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# RobotsPolicy (vendored) + polite_get
# ---------------------------------------------------------------------------


class TestRobotsAndFetch:
    def _policy(self, monkeypatch, tmp_path):
        robots_txt = (FIXTURES / "robots_sample.txt").read_text(encoding="utf-8")
        monkeypatch.setattr(
            common, "requests",
            types.SimpleNamespace(get=lambda *a, **k: FakeResp(robots_txt)),
        )
        return common.RobotsPolicy(robots_url="https://example.org/robots.txt")

    def test_robots_gate_blocks_disallowed_path(self, monkeypatch, tmp_path):
        pol = self._policy(monkeypatch, tmp_path)
        assert pol.can_fetch("/private/secret") is False
        assert pol.can_fetch("/tmp/file") is False
        assert pol.can_fetch("/internal/x") is False  # toolshop group rule
        assert pol.can_fetch("/search") is False      # second * group
        # AI-bot groups (GPTBot/ClaudeBot 'Disallow: /') must NOT apply to us
        assert pol.can_fetch("/") is True
        assert pol.can_fetch("/wiki/Some_Page") is True

    def test_robots_policy_base_url_derivation(self, monkeypatch):
        captured = {}
        def fake_get(url, **kw):
            captured["url"] = url
            return FakeResp("User-agent: *\nDisallow: /no\n")
        monkeypatch.setattr(common, "requests",
                            types.SimpleNamespace(get=fake_get))
        pol = common.RobotsPolicy(base_url="https://example.org")
        assert pol.can_fetch("/no/x") is False
        assert captured["url"] == "https://example.org/robots.txt"

    def test_polite_get_robots_disallowed_raises(self, monkeypatch):
        robots_txt = (FIXTURES / "robots_sample.txt").read_text(encoding="utf-8")
        monkeypatch.setattr(
            common, "requests",
            types.SimpleNamespace(get=lambda *a, **k: FakeResp(robots_txt)),
        )
        pol = common.RobotsPolicy(robots_url="https://example.org/robots.txt")
        with pytest.raises(common.RobotsDisallowedError):
            common.polite_get("https://example.org/private/x",
                              robots=pol, session=FakeSession())

    def test_polite_get_unreachable_robots_allows(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("network down")
        monkeypatch.setattr(common, "requests",
                            types.SimpleNamespace(get=boom))
        pol = common.RobotsPolicy(robots_url="https://example.org/robots.txt")
        assert pol.can_fetch("/anything") is True  # conservative-allow

    def test_rate_limiter_sleeps(self):
        slept = []
        clock = [0.0]
        lim = common.RateLimiter(
            1.5, sleep=lambda s: slept.append(s), now=lambda: clock[0]
        )
        lim.wait()
        clock[0] += 0.4          # only 0.4 s elapsed
        lim.wait()
        assert slept == [pytest.approx(1.1)]  # topped up to the 1.5 s interval
        clock[0] += 10.0         # long gap — no sleep needed
        lim.wait()
        assert len(slept) == 1

    def test_polite_get_paces_requests(self, monkeypatch):
        # every polite_get through a shared limiter respects min_interval_s
        lim = common.RateLimiter(1.5, sleep=lambda s: None,
                                 now=lambda: t[0])
        t = [0.0]
        session = FakeSession([FakeResp("ok1"), FakeResp("ok2")])
        common.polite_get("https://example.org/a", session=session,
                          limiter=lim, user_agent="test-ua")
        common.polite_get("https://example.org/b", session=session,
                          limiter=lim, user_agent="test-ua")
        assert lim.slept and lim.slept[0] == pytest.approx(1.5)
        assert len(session.calls) == 2
        ua = session.calls[0]["headers"]["User-Agent"]
        assert ua == "test-ua"
        assert session.calls[0]["headers"]["Accept-Encoding"] == "gzip"

    def test_polite_get_429_retries_with_retry_after(self, monkeypatch):
        sleeps = []
        session = FakeSession([
            FakeResp(status=429, headers={"Retry-After": "7"}),
            FakeResp("fine"),
        ])
        resp = common.polite_get(
            "https://example.org/x", session=session,
            limiter=common.RateLimiter(0, sleep=lambda s: None),
            sleep=lambda s: sleeps.append(s), max_retries=2,
        )
        assert resp.text == "fine"
        assert sleeps == [7.0]
        assert len(session.calls) == 2

    def test_polite_get_mediawiki_maxlag_backoff(self, monkeypatch):
        sleeps = []
        session = FakeSession([
            FakeResp(json_data={"error": {"code": "maxlag"}},
                     headers={"Content-Type": "application/json"}),
            FakeResp(json_data={"parse": {"wikitext": "ok"}},
                     headers={"Content-Type": "application/json"}),
        ])
        resp = common.polite_get(
            "https://sr.wikisource.org/w/api.php", session=session,
            params={"action": "parse"},
            limiter=common.RateLimiter(0, sleep=lambda s: None),
            sleep=lambda s: sleeps.append(s),
        )
        assert resp.json()["parse"]["wikitext"] == "ok"
        assert sleeps and sleeps[0] >= 5.0  # default maxlag backoff

    def test_polite_get_ua_template_contact_env(self, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_CONTACT", "me@example.org")
        ua = common.default_user_agent("fake_auto",
                                       "toolshop-x/1.0 (+contact: {contact})")
        assert ua == "toolshop-x/1.0 (+contact: me@example.org)"
        monkeypatch.setenv("TOOLSHOP_LYRICS_UA", "custom-ua/9")
        assert common.default_user_agent() == "custom-ua/9"


# ---------------------------------------------------------------------------
# license helpers + TASL
# ---------------------------------------------------------------------------


class TestLicenseHelpers:
    @pytest.mark.parametrize("url,expected", [
        ("https://creativecommons.org/licenses/by/4.0/", "CC-BY-4.0"),
        ("https://creativecommons.org/licenses/by-nc/2.5/", "CC-BY-NC-2.5"),
        ("https://creativecommons.org/licenses/by-sa/3.0/", "CC-BY-SA-3.0"),
        ("https://creativecommons.org/licenses/sampling+/1.0/",
         "LicenseRef-sampling-plus-1.0"),
        ("https://creativecommons.org/publicdomain/zero/1.0/", "CC0-1.0"),
        ("https://creativecommons.org/publicdomain/mark/1.0/",
         "LicenseRef-public-domain"),
        ("https://example.org/no-license-here", None),
        (None, None),
    ])
    def test_license_from_url(self, url, expected):
        assert common.license_from_url(url) == expected

    def test_license_policy_for(self):
        assert common.license_policy_for("CC-BY-4.0") == ("cc-by", "yes")
        assert common.license_policy_for("CC-BY-SA-4.0") == ("cc-by-sa",
                                                             "conditional")
        assert common.license_policy_for("CC-BY-NC-4.0") == ("cc-by-nc", "no")
        assert common.license_policy_for("proprietary") == ("study-only", "no")
        assert common.license_policy_for("weird-token") == (None, None)

    def test_tasl_credit(self):
        song = json.loads(
            (FIXTURES / "sample_pd_song.json").read_text(encoding="utf-8"))
        line = common.tasl_credit(song)
        assert '"Zorana (Test Dawn Song)" by Fixture Author' in line
        assert "source: https://example.org/wiki/Zorana_test" in line
        assert "CC0-1.0" in line and "publicdomain/zero/1.0" in line


# ---------------------------------------------------------------------------
# song JSON writer + index writer
# ---------------------------------------------------------------------------


class TestSongAndIndexWriters:
    def test_write_song_json_schema_and_diacritics(self, tmp_path):
        song = json.loads(
            (FIXTURES / "sample_pd_song.json").read_text(encoding="utf-8"))
        song["title"] = "Täterprofil ćevap — đŧ"
        path = common.write_song_json(song, tmp_path, "folk")
        assert path.exists() and path.with_suffix(".txt").exists()
        raw = path.read_text(encoding="utf-8")
        assert "Täterprofil ćevap" in raw  # ensure_ascii=False
        loaded = json.loads(raw)
        for field in common.SONG_LICENSE_FIELDS:
            assert field in loaded, f"missing v2 field {field}"
        assert loaded["release_ok"] == "yes" and loaded["license_tier"] == "cc0"
        # safe defaults applied when adapter forgets (never auto-release)
        bare = common.write_song_json(
            {"title": "X", "primary_artist": "Y", "clean_lyrics": "t"},
            tmp_path, "folk")
        bare_loaded = json.loads(bare.read_text(encoding="utf-8"))
        assert bare_loaded["license_tier"] == "study-only"
        assert bare_loaded["release_ok"] == "no"

    def test_fid_collision_gets_suffixed(self, tmp_path):
        s1 = {"title": "Same", "primary_artist": "A", "clean_lyrics": "a",
              "foreign_identifier": "id-1"}
        s2 = {"title": "Same", "primary_artist": "A", "clean_lyrics": "b",
              "foreign_identifier": "id-2"}
        p1 = common.write_song_json(s1, tmp_path, "c")
        p2 = common.write_song_json(s2, tmp_path, "c")
        assert p1 != p2 and p1.exists() and p2.exists()

    def test_detect_script(self):
        assert common.detect_script("Женске песме") == "cyrillic"
        assert common.detect_script("plain latin") == "latin"
        assert common.detect_script("123 !?") is None
        assert common.detect_script(None) is None

    def test_index_entries_carry_license_fields(self, tmp_path):
        song = json.loads(
            (FIXTURES / "sample_pd_song.json").read_text(encoding="utf-8"))
        common.write_song_json(song, tmp_path, "folk")
        song2 = dict(song)
        song2["title"] = "Druga Pesma"
        song2["foreign_identifier"] = "fixture-002"
        song2["license"] = "CC-BY-4.0"
        song2["license_tier"] = "cc-by"
        common.write_song_json(song2, tmp_path, "misc")
        result = common.write_index(tmp_path)

        index_path = tmp_path / "_index.json"
        assert index_path.exists()
        index = json.loads(index_path.read_text(encoding="utf-8"))
        assert len(index) == 2 == len(result["index"])
        for entry in index:
            for f in common.INDEX_LICENSE_FIELDS:
                assert f in entry, f"index entry missing license field {f}"
            assert entry["corpus"] == "fake-auto"
            assert entry["source"] == "fake_auto"
            assert entry["license_tier"] in ("cc0", "cc-by")
            assert entry["release_ok"] == "yes"
            assert entry["status"] == "completed"
            assert "/" in entry["json_path"]
        by_fid = {e["foreign_identifier"]: e for e in index}
        assert by_fid["fixture-002"]["license"] == "CC-BY-4.0"

    def test_index_dedup_corps_scoped(self, tmp_path):
        song = json.loads(
            (FIXTURES / "sample_pd_song.json").read_text(encoding="utf-8"))
        common.write_song_json(song, tmp_path, "folk")
        dupe = dict(song)
        dupe.pop("foreign_identifier")  # same (title, artist) key, no fid
        common.write_song_json(dupe, tmp_path, "misc")
        result = common.write_index(tmp_path)
        assert len(result["index"]) == 1
        assert len(result["dedup_log"]) == 1
        assert result["dedup_log"][0]["title"] == song["title"]


# ---------------------------------------------------------------------------
# catalog (resumable work queue)
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_catalog_roundtrip_and_task_fields(self, tmp_path):
        cat = catalog_mod.Catalog.for_corpus(
            tmp_path, source_id="fake_auto", corpus="fake-auto")
        added = cat.upsert_entries([
            common.CatalogEntry(source_id="fake_auto", foreign_identifier="e1",
                                title="Song One", url="https://x/1",
                                creator="C", category="folk",
                                license="CC-BY-4.0", license_tier="cc-by",
                                release_ok="yes"),
        ])
        assert added == 1
        cat.mark("e1", "fetched", json_path="folk/a-b.json")

        reloaded = catalog_mod.Catalog.load_or_create(cat.path)
        e = reloaded.find("e1")
        assert e["status"] == "fetched"
        # task-named fields present in the serialized row
        for f in ("source", "external_id", "title", "artist", "url",
                  "license_tier", "license_ref", "release_ok", "fetched"):
            assert f in e, f"catalog row missing task field {f}"
        assert e["fetched"] is True and e["license_ref"] == "CC-BY-4.0"

    def test_resume_skips_completed_items(self, tmp_path):
        cat = catalog_mod.Catalog.for_corpus(tmp_path, source_id="fake_auto")
        cat.upsert_entries([
            common.CatalogEntry(source_id="fake_auto", foreign_identifier="a",
                                title="A", url="u1", status="fetched"),
            common.CatalogEntry(source_id="fake_auto", foreign_identifier="b",
                                title="B", url="u2", status="failed"),
            common.CatalogEntry(source_id="fake_auto", foreign_identifier="c",
                                title="C", url="u3", status="pending"),
            common.CatalogEntry(source_id="fake_auto", foreign_identifier="d",
                                title="D", url="u4", status="dropped"),
        ])
        pending = cat.pending(resume=True)
        fids = [e["foreign_identifier"] for e in pending]
        assert fids == ["b", "c"]  # fetched + dropped skipped; failed retried
        # without resume, fetched entries are eligible again (refresh),
        # but deliberately dropped entries are never silently re-queued
        fids_all = [e["foreign_identifier"] for e in cat.pending(resume=False)]
        assert set(fids_all) == {"a", "b", "c"}

    def test_pending_limit_offset_category(self, tmp_path):
        cat = catalog_mod.Catalog.for_corpus(tmp_path, source_id="fake_auto")
        cat.upsert_entries([
            common.CatalogEntry(source_id="fake_auto",
                                foreign_identifier=f"k{i}", title=f"T{i}",
                                url=f"u{i}", category="folk" if i % 2 else "misc")
            for i in range(6)
        ])
        assert len(cat.pending(resume=True, limit=2)) == 2
        assert len(cat.pending(resume=True, offset=4)) == 2
        folk = cat.pending(resume=True, category="folk")
        assert all(e["category"] == "folk" for e in folk) and len(folk) == 3

    def test_upsert_preserves_terminal_status(self, tmp_path):
        cat = catalog_mod.Catalog.for_corpus(tmp_path, source_id="fake_auto")
        cat.upsert_entries([common.CatalogEntry(
            source_id="fake_auto", foreign_identifier="x", title="X")])
        cat.mark("x", "dropped", drop_reason="copyright-flag")
        # a re-list of the same upstream id must not resurrect the drop
        cat.upsert_entries([common.CatalogEntry(
            source_id="fake_auto", foreign_identifier="x", title="X2")])
        assert cat.find("x")["status"] == "dropped"
        assert cat.find("x")["drop_reason"] == "copyright-flag"
        assert cat.find("x")["title"] == "X2"  # metadata still refreshed


# ---------------------------------------------------------------------------
# dispatcher end-to-end (injected adapter, tmp data dir — no network)
# ---------------------------------------------------------------------------


class TestDispatcher:
    def test_end_to_end_fetch_and_resume(self, tmp_path, monkeypatch):
        adapter = make_adapter()
        rc = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, quiet=True,
        )
        assert rc == 0
        corpus_root = tmp_path / "lyrics" / "fake-auto"
        assert (corpus_root / "_catalog.json").exists()
        assert (corpus_root / "_index.json").exists()
        songs = sorted((corpus_root / "folk").glob("*.json")) + \
            sorted((corpus_root / "misc").glob("*.json"))
        assert len(songs) == 2
        loaded = json.loads(songs[0].read_text(encoding="utf-8"))
        assert loaded["corpus"] == "fake-auto"
        assert loaded["source"] == "fake_auto"
        assert loaded["foreign_identifier"]
        catalog_doc = json.loads(
            (corpus_root / "_catalog.json").read_text(encoding="utf-8"))
        assert all(e["status"] == "fetched" for e in catalog_doc["entries"])

        # resume: a second run must skip completed items entirely
        rc2 = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, resume=True, quiet=True,
        )
        assert rc2 == 0
        assert adapter._state["fetch_calls"] == 2  # still 2 — none re-fetched

    def test_limit_and_offset(self, tmp_path):
        adapter = make_adapter()
        rc = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, limit=1, quiet=True,
        )
        assert rc == 0
        assert adapter._state["fetch_calls"] == 1
        # resume (no offset) picks up the remaining pending item
        rc = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, resume=True, quiet=True,
        )
        assert rc == 0
        assert adapter._state["fetch_calls"] == 2

        # offset slices the *eligible* list (batch.py discover_files order):
        # a fresh corpus + offset=1 skips f-1 and fetches only f-2
        d2 = tmp_path / "second"
        adapter2 = make_adapter()
        rc = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter2,
            data_dir=d2, offset=1, quiet=True,
        )
        assert rc == 0
        assert adapter2._state["fetch_calls"] == 1
        doc = json.loads(
            (d2 / "lyrics" / "fake-auto" / "_catalog.json")
            .read_text(encoding="utf-8"))
        by_fid = {e["foreign_identifier"]: e for e in doc["entries"]}
        assert by_fid["f-1"]["status"] == "pending"
        assert by_fid["f-2"]["status"] == "fetched"

    def test_catalog_only_mode(self, tmp_path):
        adapter = make_adapter()
        rc = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, catalog_only=True, quiet=True,
        )
        assert rc == 0
        assert adapter._state["fetch_calls"] == 0
        doc = json.loads(
            (tmp_path / "lyrics" / "fake-auto" / "_catalog.json")
            .read_text(encoding="utf-8"))
        assert len(doc["entries"]) == 2
        assert all(e["status"] == "pending" for e in doc["entries"])

    def test_env_gate_blocks_when_unset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FAKE_LYRICS_KEY_FOR_TESTS", raising=False)
        adapter = make_adapter()
        rc = dispatcher.run(
            "fake_gated", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, quiet=True,
        )
        assert rc == 2
        assert adapter._state["fetch_calls"] == 0
        monkeypatch.setenv("FAKE_LYRICS_KEY_FOR_TESTS", "k")
        rc = dispatcher.run(
            "fake_gated", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, quiet=True,
        )
        assert rc == 0

    def test_failed_item_marked_and_continues(self, tmp_path):
        def boom(entry):
            if entry.foreign_identifier == "f-1":
                raise RuntimeError("upstream exploded")
        adapter = make_adapter(on_fetch=boom)
        rc = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, quiet=True,
        )
        assert rc == 0  # failures are per-item, not fatal
        doc = json.loads(
            (tmp_path / "lyrics" / "fake-auto" / "_catalog.json")
            .read_text(encoding="utf-8"))
        by_fid = {e["foreign_identifier"]: e for e in doc["entries"]}
        assert by_fid["f-1"]["status"] == "failed"
        assert "upstream exploded" in by_fid["f-1"]["error"]
        assert by_fid["f-2"]["status"] == "fetched"

    def test_dropitem_marks_dropped(self, tmp_path):
        def drop(entry):
            raise common.DropItem("no-lyric-text")
        adapter = make_adapter(on_fetch=drop)
        rc = dispatcher.run(
            "fake_auto", registry_path=TEST_REGISTRY, adapter=adapter,
            data_dir=tmp_path, quiet=True,
        )
        assert rc == 0
        doc = json.loads(
            (tmp_path / "lyrics" / "fake-auto" / "_catalog.json")
            .read_text(encoding="utf-8"))
        assert all(e["status"] == "dropped" for e in doc["entries"])
        assert all(e["drop_reason"] == "no-lyric-text"
                   for e in doc["entries"])
        # dropped items produced no song files
        assert not list((tmp_path / "lyrics" / "fake-auto").glob("*/*.json"))


# ---------------------------------------------------------------------------
# structural guarantees
# ---------------------------------------------------------------------------


class TestStructural:
    def test_no_toolshop_import_anywhere(self):
        """F-B1: folder scripts must never import toolshop (70s eager init).
        Line-anchored regex — the prose rule itself mentions the phrase."""
        import re
        pat = re.compile(r"^\s*(?:import|from)\s+toolshop\b", re.M)
        targets = list((EXTRACTOR / "sources").glob("*.py")) + [
            EXTRACTOR / "fetch_lyrics_source.py"]
        assert targets, "no sources/*.py found"
        for f in targets:
            src = f.read_text(encoding="utf-8")
            assert not pat.search(src), f"toolshop import in {f}"

    def test_registry_json_committed_and_valid(self):
        doc = json.loads(registry.REGISTRY_PATH.read_text(encoding="utf-8"))
        assert doc["version"] == 1
        assert len(doc["sources"]) == 19  # I3 merged sr/en wikisource

    def test_named_adapters_resolve_or_defer(self):
        """Contract (SPEC §7.1): every non-null adapter name must map to an
        importable sources/<name>.py. W1 ships no adapter modules — the check
        fires for whatever exists now and stays green as WA lands them."""
        sources_dir = EXTRACTOR / "sources"
        for row in registry.list_sources():
            name = row.get("adapter")
            if not name:
                continue
            mod_file = sources_dir / f"{name}.py"
            if not mod_file.exists():
                continue  # adapter lands in wave WA — registry row is ahead
            mod = registry.resolve_adapter(row)
            assert hasattr(mod, "iter_catalog"), name
            assert hasattr(mod, "license_of"), name
            if row["fetch_policy"] == "auto":
                assert hasattr(mod, "fetch_lyrics"), name
            else:
                assert not hasattr(mod, "fetch_lyrics"), name

    def test_data_dir_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path / "x"))
        assert registry.data_dir() == (tmp_path / "x").resolve()
