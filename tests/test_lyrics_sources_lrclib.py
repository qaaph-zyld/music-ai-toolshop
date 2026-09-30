"""Tests for the LRCLIB adapter (wave B / I8).

Two invariants under test (SPEC §9 + wave-B contract):

- **study-only FOREVER**: every catalog row and every fetched song carries
  ``license='proprietary', license_tier='study-only', release_ok='no'``.
  A lrclib row with ``release_ok='yes'`` is a release blocker.
- **shared ≥1.5 s pacing** even though the API tolerates ~20 req/s — the
  adapter passes ``min_interval_s >= 1.5`` to ``polite_get`` on every call.

Fetch order per SPEC §9: ``/api/get-cached`` → ``/api/get`` (exact
signature) or ``/api/search`` when the seed row lacks album/duration.
All transport is faked — committed fixtures are synthetic (no real lyric
text, per SPEC §7 gray-source rule).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources._common as common  # noqa: E402
import sources.registry as registry  # noqa: E402
import sources.lrclib as lrclib  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"


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


class FakeTransport:
    """polite_get stand-in keyed by URL path; records every call."""

    def __init__(self, routes):
        self.routes = {k: list(v) for k, v in routes.items()}
        self.calls = []

    def __call__(self, url, source_id=None, *, params=None, session=None,
                 min_interval_s=None, **kw):
        self.calls.append({"url": url, "params": params or {},
                           "min_interval_s": min_interval_s})
        path = url.split("lrclib.net")[-1]
        q = self.routes.get(path)
        if q is None:
            raise RuntimeError(f"no route for {url}")
        item = q.pop(0) if len(q) > 1 else q[0]
        item.raise_for_status()  # mirror polite_get's 4xx behaviour
        return item


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _entry(title="Synthetic Song", artist="Fixture Artist",
           album="Fixture Album", duration=200.5, **kw):
    return common.CatalogEntry(
        source_id="lrclib", title=title, artist=artist,
        foreign_identifier=lrclib._seed_fid(
            {"artist": artist, "title": title,
             "album": album, "duration": duration}),
        category="tracks",
        meta={"album": album, "duration": duration}, **kw)


# ---------------------------------------------------------------------------
# iter_catalog — the seed file reader (no network anywhere)
# ---------------------------------------------------------------------------


class TestSeedCatalog:
    def test_seed_json_rows(self):
        seed = FIXTURES / "lrclib_seed.json"
        entries = list(lrclib.iter_catalog(seed=seed))
        assert len(entries) == 4
        e = entries[0]
        assert e.source_id == "lrclib"
        assert e.title == "Synthetic Song"
        assert e.artist == "Fixture Artist"
        assert e.category == "tracks"
        assert e.meta == {"album": "Fixture Album", "duration": 200.5}
        assert e.foreign_identifier.startswith("seed:")

    def test_seed_csv_rows(self):
        entries = list(lrclib.iter_catalog(seed=FIXTURES / "lrclib_seed.csv"))
        assert len(entries) == 3
        assert entries[0].meta["duration"] == 200.5
        assert entries[2].meta["album"] is None
        assert entries[2].meta["duration"] is None

    def test_seed_fid_stable_across_relists(self):
        a = list(lrclib.iter_catalog(seed=FIXTURES / "lrclib_seed.json"))
        b = list(lrclib.iter_catalog(seed=FIXTURES / "lrclib_seed.json"))
        assert [e.key() for e in a] == [e.key() for e in b]

    def test_limit_offset(self):
        seed = FIXTURES / "lrclib_seed.json"
        assert len(list(lrclib.iter_catalog(seed=seed, limit=2))) == 2
        rest = list(lrclib.iter_catalog(seed=seed, offset=2))
        assert len(rest) == 2 and rest[0].title == "Instrumental Cut"

    def test_missing_seed_yields_nothing(self, tmp_path, monkeypatch):
        monkeypatch.delenv(lrclib.SEED_ENV, raising=False)
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        assert lrclib.seed_path() is None
        assert list(lrclib.iter_catalog()) == []

    def test_seed_env_override(self, monkeypatch, tmp_path):
        env_seed = tmp_path / "s.json"
        env_seed.write_text('[{"artist": "A", "title": "T"}]',
                            encoding="utf-8")
        monkeypatch.setenv(lrclib.SEED_ENV, str(env_seed))
        entries = list(lrclib.iter_catalog())
        assert len(entries) == 1 and entries[0].title == "T"


# ---------------------------------------------------------------------------
# THE INVARIANT: study-only forever — release_ok='no', always
# ---------------------------------------------------------------------------


class TestReleaseOkInvariant:
    def test_license_of_is_locked_study_only(self):
        for e in lrclib.iter_catalog(seed=FIXTURES / "lrclib_seed.json"):
            info = lrclib.license_of(e)
            assert info.license == "proprietary"
            assert info.license_tier == "study-only"
            assert info.release_ok == "no"  # FOREVER — never 'yes'

    def test_every_catalog_row_is_release_ok_no(self):
        """A lrclib catalog row with release_ok='yes' is a blocker."""
        for e in lrclib.iter_catalog(seed=FIXTURES / "lrclib_seed.json"):
            assert e.release_ok == "no", f"invariant violated: {e.title}"
            assert e.license_tier == "study-only"
            assert e.license == "proprietary"

    def test_every_fetched_song_is_release_ok_no(self, monkeypatch):
        """The invariant holds through the full fetch path, for every
        upstream record shape (full, synced-only, search hit)."""
        got = _load("lrclib_get_response.json")
        synced_only = _load("lrclib_get_synced_only.json")
        search = _load("lrclib_search_response.json")
        routes = {
            "/api/get-cached": [FakeResp(status=404)],
            "/api/get": [FakeResp(json_data=got)],
            "/api/search": [FakeResp(json_data=search),
                            FakeResp(json_data=synced_only)],
        }
        t = FakeTransport(routes)
        monkeypatch.setattr(lrclib, "polite_get", t)

        for entry in [
            _entry(),                                        # get path
            _entry(album=None, duration=None),               # search path
            _entry(title="Synced Only", album=None,
                   duration=None),                           # search → hit
        ]:
            song = lrclib.fetch_lyrics(entry)
            assert song["release_ok"] == "no", song["title"]
            assert song["license_tier"] == "study-only"
            assert song["license"] == "proprietary"
            assert song["license_url"] is None


# ---------------------------------------------------------------------------
# fetch_lyrics — endpoint order + field capture
# ---------------------------------------------------------------------------


class TestFetchLyrics:
    def test_get_cached_preferred(self, monkeypatch):
        got = _load("lrclib_get_response.json")
        t = FakeTransport({"/api/get-cached": [FakeResp(json_data=got)]})
        monkeypatch.setattr(lrclib, "polite_get", t)
        song = lrclib.fetch_lyrics(_entry())
        assert song["meta"]["matched_via"] == "get-cached"
        assert len(t.calls) == 1 and "/api/get-cached" in t.calls[0]["url"]
        assert song["title"] == "Synthetic Song"
        assert song["primary_artist"] == "Fixture Artist"
        assert song["foreign_identifier"] == "999001"  # LRCLIB id (SPEC §1.3)
        assert "Synthetic plain line one" in song["clean_lyrics"]
        # the three captured lyric payloads (SPEC §3.3)
        assert song["raw_lyrics"].startswith("Synthetic plain line one")
        assert "[00:12.34]" in song["synced_lyrics"]
        assert "start_ms: 12340" in song["lyricsfile"]

    def test_cached_miss_falls_back_to_get(self, monkeypatch):
        got = _load("lrclib_get_response.json")
        t = FakeTransport({
            "/api/get-cached": [FakeResp(status=404)],
            "/api/get": [FakeResp(json_data=got)],
        })
        monkeypatch.setattr(lrclib, "polite_get", t)
        song = lrclib.fetch_lyrics(_entry())
        assert song["meta"]["matched_via"] == "get"
        assert [c["url"].split("lrclib.net")[-1] for c in t.calls] == \
            ["/api/get-cached", "/api/get"]

    def test_full_miss_drops_not_found(self, monkeypatch):
        t = FakeTransport({
            "/api/get-cached": [FakeResp(status=404)],
            "/api/get": [FakeResp(status=404)],
        })
        monkeypatch.setattr(lrclib, "polite_get", t)
        with pytest.raises(common.DropItem, match="not-found"):
            lrclib.fetch_lyrics(_entry())

    def test_search_path_when_signature_incomplete(self, monkeypatch):
        search = _load("lrclib_search_response.json")
        t = FakeTransport({"/api/search": [FakeResp(json_data=search)]})
        monkeypatch.setattr(lrclib, "polite_get", t)
        song = lrclib.fetch_lyrics(_entry(album=None, duration=None))
        assert song["meta"]["matched_via"] == "search"
        # exact (title, artist) hit preferred over the karaoke variant
        assert song["foreign_identifier"] == "999001"
        assert len(t.calls) == 1
        assert t.calls[0]["params"]["track_name"] == "Synthetic Song"

    def test_search_empty_drops(self, monkeypatch):
        t = FakeTransport({"/api/search": [FakeResp(json_data=[])]})
        monkeypatch.setattr(lrclib, "polite_get", t)
        with pytest.raises(common.DropItem, match="not-found"):
            lrclib.fetch_lyrics(_entry(album=None, duration=None))

    def test_instrumental_drops(self, monkeypatch):
        inst = _load("lrclib_instrumental.json")
        t = FakeTransport({"/api/get-cached": [FakeResp(json_data=inst)]})
        monkeypatch.setattr(lrclib, "polite_get", t)
        with pytest.raises(common.DropItem, match="instrumental"):
            lrclib.fetch_lyrics(
                _entry(title="Instrumental Cut", duration=210))

    def test_no_lyrics_drops(self, monkeypatch):
        rec = _load("lrclib_get_response.json")
        rec["plainLyrics"] = None
        rec["syncedLyrics"] = None
        t = FakeTransport({"/api/get-cached": [FakeResp(json_data=rec)]})
        monkeypatch.setattr(lrclib, "polite_get", t)
        with pytest.raises(common.DropItem, match="no-lyrics"):
            lrclib.fetch_lyrics(_entry())

    def test_synced_only_derives_plain(self, monkeypatch):
        rec = _load("lrclib_get_synced_only.json")
        t = FakeTransport({"/api/get-cached": [FakeResp(json_data=rec)]})
        monkeypatch.setattr(lrclib, "polite_get", t)
        song = lrclib.fetch_lyrics(_entry(title="Synced Only", duration=190))
        assert "[ti:" not in song["clean_lyrics"]
        assert "Synced invented line" in song["clean_lyrics"]
        assert song["synced_lyrics"].startswith("[ti:")
        assert "start_ms: 5000" in song["lyricsfile"]
        assert song["meta"]["hasWordSync"] is True

    def test_pacing_at_least_1_5s_every_call(self, monkeypatch):
        """~20 req/s ceiling honored via the shared ≥1.5 s floor anyway."""
        rec = _load("lrclib_get_response.json")
        t = FakeTransport({
            "/api/get-cached": [FakeResp(status=404)],
            "/api/get": [FakeResp(json_data=rec), FakeResp(json_data=rec)],
            "/api/search": [FakeResp(json_data=[])],
        })
        monkeypatch.setattr(lrclib, "polite_get", t)
        lrclib.fetch_lyrics(_entry())
        with pytest.raises(common.DropItem):
            lrclib.fetch_lyrics(_entry(album=None, duration=None))
        assert len(t.calls) == 3
        for c in t.calls:
            assert c["min_interval_s"] >= 1.5

    def test_request_params_signature(self, monkeypatch):
        rec = _load("lrclib_get_response.json")
        t = FakeTransport({"/api/get-cached": [FakeResp(json_data=rec)]})
        monkeypatch.setattr(lrclib, "polite_get", t)
        lrclib.fetch_lyrics(_entry())
        p = t.calls[0]["params"]
        assert p == {"track_name": "Synthetic Song",
                     "artist_name": "Fixture Artist",
                     "album_name": "Fixture Album", "duration": 200}


# ---------------------------------------------------------------------------
# end-to-end through the W1 dispatcher (fake transport, tmp data dir)
# ---------------------------------------------------------------------------


class TestDispatcherEndToEnd:
    def test_run_writes_study_only_corpus(self, monkeypatch, tmp_path):
        got = _load("lrclib_get_response.json")
        search = _load("lrclib_search_response.json")
        t = FakeTransport({
            "/api/get-cached": [FakeResp(json_data=got),
                                FakeResp(status=404),
                                FakeResp(json_data=got)],
            "/api/get": [FakeResp(json_data=got)],
            "/api/search": [FakeResp(json_data=search)],
        })
        monkeypatch.setattr(lrclib, "polite_get", t)
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        monkeypatch.setenv(lrclib.SEED_ENV,
                           str(FIXTURES / "lrclib_seed.json"))
        rc = dispatcher.run("lrclib", data_dir=tmp_path, quiet=True)
        assert rc == 0

        corpus = tmp_path / "lyrics" / "lrclib"
        catalog = json.loads(
            (corpus / "_catalog.json").read_text(encoding="utf-8"))
        statuses = {e["status"] for e in catalog["entries"]}
        assert statuses <= {"fetched", "dropped"}
        for e in catalog["entries"]:
            assert e["release_ok"] == "no" and e["license_tier"] == "study-only"

        songs = list((corpus / "tracks").glob("*.json"))
        assert songs, "expected fetched song JSONs"
        for s in songs:
            doc = json.loads(s.read_text(encoding="utf-8"))
            assert doc["release_ok"] == "no"           # INVARIANT on disk
            assert doc["license_tier"] == "study-only"
            assert doc["license"] == "proprietary"

        index = json.loads((corpus / "_index.json").read_text(encoding="utf-8"))
        for e in index:
            assert e["release_ok"] == "no"
            assert e["license_tier"] == "study-only"


# ---------------------------------------------------------------------------
# live smoke — marked slow; degrades gracefully offline (SPEC §7 F5)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_live_lrclib_lookup():
    """One real get-cached lookup; skipped naturally when the network is
    unreachable (offline-degrade, not failure)."""
    entry = _entry(title="One More Time", artist="Daft Punk",
                   album="Discovery", duration=320)
    try:
        song = lrclib.fetch_lyrics(entry)
    except common.DropItem as d:
        pytest.skip(f"upstream miss: {d.reason}")
    except Exception as e:  # offline/proxy failure → skip, don't fail
        pytest.skip(f"lrclib unreachable: {e}")
    assert song["release_ok"] == "no"
    assert song["clean_lyrics"]
