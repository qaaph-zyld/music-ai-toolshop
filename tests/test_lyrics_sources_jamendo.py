"""Tests for the Jamendo adapter (wave B / I8).

GATE R contract under test: ``sources/jamendo.py`` is **env-gated** —
absent ``JAMENDO_CLIENT_ID`` (env OR ``.env``) it performs ZERO network
calls, reports ``inert — register at devportal.jamendo.com``, and exits
cleanly. The inert path is the tested path; keyed paths run against
committed synthetic fixtures via fake sessions (SPEC §7).
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources._common as common  # noqa: E402
import sources.registry as registry  # noqa: E402
import sources.jamendo as jamendo  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"


# ---------------------------------------------------------------------------
# fakes (same shape as tests/test_lyrics_sources_core.py)
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


def _boom_session():
    """Session whose every .get explodes — zero-network proof."""
    class Boom:
        def get(self, url, **kw):
            raise AssertionError(f"network call attempted: {url}")
    return Boom()


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _no_real_pacing(monkeypatch):
    """Tests that route through the real ``polite_get`` (session-injected)
    must not pay real wall-clock pacing — inject no-op-sleep limiters into
    the shared per-source limiter table."""
    for src in ("jamendo", "lrclib", "_default"):
        monkeypatch.setitem(
            common._LIMITERS, src,
            common.RateLimiter(1.5, sleep=lambda s: None))


@pytest.fixture
def unkeyed(monkeypatch, tmp_path):
    """Guarantee the inert state: env var deleted AND .env pointed at a
    nonexistent path so a real key can never leak into the test."""
    monkeypatch.delenv(jamendo.ENV_VAR, raising=False)
    monkeypatch.setattr(jamendo, "DOTENV_PATH", tmp_path / "no_such.env")
    return tmp_path


# ---------------------------------------------------------------------------
# THE inert path — zero network, clean exit
# ---------------------------------------------------------------------------


class TestEnvGateInertPath:
    def test_missing_key_iter_catalog_raises_without_network(self, unkeyed):
        spy = _boom_session()
        with pytest.raises(common.EnvGateError) as ei:
            list(jamendo.iter_catalog(limit=5, session=spy))
        assert ei.value.env_var == "JAMENDO_CLIENT_ID"
        assert ei.value.source_id == "jamendo"

    def test_missing_key_fetch_lyrics_raises_without_network(self, unkeyed):
        entry = common.CatalogEntry(
            source_id="jamendo", foreign_identifier="100001",
            title="Synthetic Dawn", artist="Fixture Artist A",
            category="by")
        with pytest.raises(common.EnvGateError):
            jamendo.fetch_lyrics(entry, session=_boom_session())

    def test_missing_key_iter_catalog_allow_inert_yields_nothing(self, unkeyed):
        got = list(jamendo.iter_catalog(
            limit=5, session=_boom_session(), allow_inert=True))
        assert got == []

    def test_inert_report_exits_0_and_makes_no_requests(self, unkeyed, capsys,
                                                      monkeypatch):
        # belt-and-braces: any stray requests.get would explode
        monkeypatch.setattr(
            common, "requests",
            types.SimpleNamespace(
                get=lambda *a, **k: (_ for _ in ()).throw(
                    AssertionError("network call attempted"))))
        rc = jamendo.main([])
        out = capsys.readouterr().out
        assert rc == 0
        assert "inert" in out
        assert "devportal.jamendo.com" in out

    def test_status_reports_inert(self, unkeyed):
        st = jamendo.status()
        assert st["keyed"] is False and st["state"] == "inert"
        assert "devportal.jamendo.com" in st["message"]

    def test_dispatcher_env_gate_refuses_before_network(self, unkeyed,
                                                        tmp_path, capsys):
        """Under the W1 dispatcher the gate fires BEFORE any adapter code —
        exit 2, and no catalog fetch ever happens (zero network)."""
        rc = dispatcher.run("jamendo", data_dir=tmp_path, quiet=True)
        assert rc == 2
        assert "JAMENDO_CLIENT_ID" in capsys.readouterr().err
        # nothing was listed or written
        assert not (tmp_path / "lyrics" / "jamendo" / "_catalog.json").exists()

    def test_registry_row_is_env_gated(self):
        row = registry.get("jamendo")
        assert row["env_gate"] == "JAMENDO_CLIENT_ID"
        with pytest.raises(common.EnvGateError):
            registry.check_env_gate(row)


# ---------------------------------------------------------------------------
# env/.env resolution
# ---------------------------------------------------------------------------


class TestKeyResolution:
    def test_env_var_wins(self, monkeypatch):
        monkeypatch.setenv(jamendo.ENV_VAR, "envkey")
        monkeypatch.setattr(jamendo, "DOTENV_PATH",
                            Path("/nonexistent/.env"))
        assert jamendo.get_client_id() == "envkey"
        assert jamendo.is_keyed()

    def test_dotenv_fallback(self, monkeypatch, tmp_path):
        dotenv = tmp_path / ".env"
        dotenv.write_text(
            "# comment\nGenious_API='other'\n"
            "JAMENDO_CLIENT_ID='dotenvkey-42'\n", encoding="utf-8")
        monkeypatch.delenv(jamendo.ENV_VAR, raising=False)
        monkeypatch.setattr(jamendo, "DOTENV_PATH", dotenv)
        assert jamendo.get_client_id() == "dotenvkey-42"
        assert jamendo.is_keyed()
        assert jamendo.status()["state"] == "keyed"

    def test_bootstrap_env_populates_environ(self, monkeypatch, tmp_path):
        dotenv = tmp_path / ".env"
        dotenv.write_text('JAMENDO_CLIENT_ID="bootkey"\n', encoding="utf-8")
        monkeypatch.delenv(jamendo.ENV_VAR, raising=False)
        assert jamendo.bootstrap_env(dotenv) is True
        import os
        assert os.environ[jamendo.ENV_VAR] == "bootkey"


# ---------------------------------------------------------------------------
# keyed paths — fixture-driven, fake session (no real network)
# ---------------------------------------------------------------------------


class TestKeyedCatalog:
    def _entries(self):
        page = _load("jamendo_tracks_page.json")
        session = FakeSession([FakeResp(json_data=page)])
        return list(jamendo.iter_catalog(
            limit=200, session=session, client_id="fixture-key")), session

    def test_iter_catalog_maps_tracks(self):
        entries, session = self._entries()
        assert len(entries) == 6
        call = session.calls[0]
        assert call["url"].startswith("https://api.jamendo.com/v3.0/tracks")
        assert call["params"]["include"] == "lyrics"
        assert call["params"]["client_id"] == "fixture-key"
        e = entries[0]
        assert e.foreign_identifier == "100001"
        assert e.title == "Synthetic Dawn"
        # TASL: creator = artist_name; source_url = track page (task contract)
        assert e.creator == "Fixture Artist A"
        assert e.source_url == "https://www.jamendo.com/track/100001"
        assert e.creator_url == "https://www.jamendo.com/artist/9001"
        assert e.meta["lyrics_present"] is True

    def test_license_ccurl_to_spdx_mapping(self):
        entries, _ = self._entries()
        by_id = {e.foreign_identifier: e for e in entries}
        assert by_id["100001"].license == "CC-BY-4.0"
        assert by_id["100002"].license == "CC0-1.0"
        assert by_id["100003"].license == "CC-BY-SA-3.0"
        assert by_id["100004"].license == "CC-BY-NC-SA-4.0"
        assert by_id["100005"].license == "CC-BY-ND-4.0"
        assert by_id["100006"].license is None  # unresolvable → downgrade

    def test_categories_follow_license_class(self):
        entries, _ = self._entries()
        cats = {e.license: e.category for e in entries if e.license}
        assert cats["CC-BY-4.0"] == "by"
        assert cats["CC0-1.0"] == "cc0"
        assert cats["CC-BY-SA-3.0"] == "by-sa"
        assert cats["CC-BY-NC-SA-4.0"] == "by-nc"
        assert cats["CC-BY-ND-4.0"] == "by-nd"

    def test_tiers_and_release_ok(self):
        entries, _ = self._entries()
        by_id = {e.foreign_identifier: e for e in entries}
        assert (by_id["100001"].license_tier, by_id["100001"].release_ok) == \
            ("cc-by", "yes")
        assert (by_id["100002"].license_tier, by_id["100002"].release_ok) == \
            ("cc0", "yes")
        assert (by_id["100003"].license_tier, by_id["100003"].release_ok) == \
            ("cc-by-sa", "conditional")
        assert (by_id["100004"].license_tier, by_id["100004"].release_ok) == \
            ("cc-by-nc", "no")

    @pytest.mark.parametrize("url,tok,tier,rel,cat", [
        ("https://creativecommons.org/licenses/by/4.0/",
         "CC-BY-4.0", "cc-by", "yes", "by"),
        ("https://creativecommons.org/licenses/by-nc/2.5/",
         "CC-BY-NC-2.5", "cc-by-nc", "no", "by-nc"),
        ("https://creativecommons.org/publicdomain/zero/1.0/",
         "CC0-1.0", "cc0", "yes", "cc0"),
        ("https://example.org/weird",
         "unknown", "study-only", "no", "other"),
        (None, "unknown", "study-only", "no", "other"),
    ])
    def test_license_of(self, url, tok, tier, rel, cat):
        e = common.CatalogEntry(source_id="jamendo", license_url=url,
                                license=None)
        info = jamendo.license_of(e)
        assert info.license == tok
        assert info.license_tier == tier
        assert info.release_ok == rel
        assert jamendo.category_for_license(info.license) == cat

    def test_license_of_never_upgrades(self):
        """SPEC §6.3: license_of may only downgrade the registry default
        (cc-by/yes) — unresolvable URLs land study-only/no, never yes."""
        e = common.CatalogEntry(
            source_id="jamendo",
            license_url="https://example.org/not-a-cc-deed")
        info = jamendo.license_of(e)
        assert info.release_ok == "no"
        assert info.license_tier == "study-only"

    def test_paging(self, monkeypatch):
        """Multi-page walk with a slice-serving fake: PAGE_SIZE=2 forces
        3 full pages + a terminal empty page over the 6-row fixture."""
        page = _load("jamendo_tracks_page.json")
        results = page["results"]

        class SlicedSession:
            def __init__(self):
                self.calls = []

            def get(self, url, params=None, **kw):
                self.calls.append({"url": url, "params": dict(params or {})})
                off = params.get("offset", 0)
                lim = params.get("limit", 200)
                res = results[off:off + lim]
                return FakeResp(json_data={
                    "headers": {"status": "success", "code": 0,
                                "results_count": len(results)},
                    "results": res})

        monkeypatch.setattr(jamendo, "PAGE_SIZE", 2)
        session = SlicedSession()
        entries = list(jamendo.iter_catalog(
            session=session, client_id="k"))
        assert len(entries) == 6
        assert len(session.calls) == 4          # 3 full pages + empty page
        assert [c["params"]["offset"] for c in session.calls] == [0, 2, 4, 6]

        # bounded: limit=5 → pages of 2,2,1 then stop
        session2 = SlicedSession()
        entries = list(jamendo.iter_catalog(
            limit=5, session=session2, client_id="k"))
        assert len(entries) == 5
        assert len(session2.calls) == 3
        assert session2.calls[-1]["params"]["limit"] == 1

    def test_rate_limit_code6_backoff_then_success(self):
        limited = _load("jamendo_rate_limit.json")
        good = _load("jamendo_track_single.json")
        session = FakeSession([
            FakeResp(json_data=limited), FakeResp(json_data=good)])
        sleeps = []
        entries = list(jamendo.iter_catalog(
            limit=1, session=session, client_id="k",
            sleep=lambda s: sleeps.append(s)))
        assert len(entries) == 1
        assert sleeps and sleeps[0] > 0  # code-6 backoff happened

    def test_rate_limit_exhaustion_raises(self):
        limited = _load("jamendo_rate_limit.json")
        session = FakeSession([FakeResp(json_data=limited)])
        with pytest.raises(RuntimeError, match="rate-limit"):
            list(jamendo.iter_catalog(
                limit=1, session=session, client_id="k",
                sleep=lambda s: None))


class TestKeyedFetch:
    def _entry(self):
        return common.CatalogEntry(
            source_id="jamendo", foreign_identifier="100001",
            title="Synthetic Dawn", artist="Fixture Artist A",
            creator="Fixture Artist A",
            creator_url="https://www.jamendo.com/artist/9001",
            source_url="https://www.jamendo.com/track/100001",
            url="https://www.jamendo.com/track/100001",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            license="CC-BY-4.0", license_tier="cc-by", release_ok="yes",
            category="by", meta={"album_name": "Test EP"})

    def test_fetch_lyrics_song_v2(self):
        page = _load("jamendo_track_single.json")
        session = FakeSession([FakeResp(json_data=page)])
        song = jamendo.fetch_lyrics(self._entry(), session=session,
                                    client_id="k")
        assert session.calls[0]["params"]["id"] == "100001"
        assert song["corpus"] == "jamendo" and song["source"] == "jamendo"
        assert song["foreign_identifier"] == "100001"
        assert song["primary_artist"] == "Fixture Artist A"
        assert "Synthetic lyric line one" in song["raw_lyrics"]
        assert len(song["sections"]) == 2
        assert song["license"] == "CC-BY-4.0"
        assert song["license_tier"] == "cc-by" and song["release_ok"] == "yes"
        assert song["source_url"] == "https://www.jamendo.com/track/100001"

    def test_fetch_lyrics_drops_empty_lyrics(self):
        page = _load("jamendo_track_single.json")
        page["results"][0]["lyrics"] = ""
        session = FakeSession([FakeResp(json_data=page)])
        with pytest.raises(common.DropItem, match="no-lyric-text"):
            jamendo.fetch_lyrics(self._entry(), session=session, client_id="k")

    def test_fetch_lyrics_not_found_drops(self):
        empty = {"headers": {"status": "success", "code": 0,
                             "results_count": 0}, "results": []}
        session = FakeSession([FakeResp(json_data=empty)])
        with pytest.raises(common.DropItem, match="not-found"):
            jamendo.fetch_lyrics(self._entry(), session=session, client_id="k")


class TestEndToEndKeyed:
    def test_dispatcher_run_writes_corpus(self, monkeypatch, tmp_path):
        """Keyed run through the real W1 dispatcher against fake transport."""
        page = _load("jamendo_tracks_page.json")
        single = _load("jamendo_track_single.json")
        calls = []

        def fake_polite_get(url, source_id=None, params=None, **kw):
            calls.append(params or {})
            # catalog page (offset param) vs single-track fetch (id param)
            if params and params.get("id"):
                return FakeResp(json_data=single)
            return FakeResp(json_data=page)

        monkeypatch.setenv(jamendo.ENV_VAR, "fixture-key")
        monkeypatch.setattr(jamendo, "polite_get", fake_polite_get)
        rc = dispatcher.run("jamendo", data_dir=tmp_path, limit=1, quiet=True)
        assert rc == 0
        corpus = tmp_path / "lyrics" / "jamendo"
        assert (corpus / "_catalog.json").exists()
        songs = list((corpus / "by").glob("*.json"))
        assert len(songs) == 1
        song = json.loads(songs[0].read_text(encoding="utf-8"))
        assert song["license"] == "CC-BY-4.0" and song["release_ok"] == "yes"
        assert song["creator"] == "Fixture Artist A"
        index = json.loads((corpus / "_index.json").read_text(encoding="utf-8"))
        assert index[0]["license_tier"] == "cc-by"


# ---------------------------------------------------------------------------
# live smoke — skipped without a real key (and marked slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not __import__("os").environ.get("JAMENDO_CLIENT_ID"),
                    reason="JAMENDO_CLIENT_ID not set — adapter ships inert")
def test_live_jamendo_catalog_smoke():
    entries = list(jamendo.iter_catalog(limit=5))
    assert entries
    assert all(e.license_url for e in entries)
