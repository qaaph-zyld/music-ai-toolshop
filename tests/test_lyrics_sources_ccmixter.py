"""ccMixter adapter tests (wave A, agent I2).

Covers ``sources/ccmixter.py`` against the committed fixture
``tests/fixtures/lyrics_sources/ccmixter_query_page.json`` — a real
``f=json&dataview=default`` Query API page (5 cleared CC-BY/PD upload rows)
plus synthetic metadata-only rows for NC/SA/sampling+/unknown license
mapping. NO live fetch in the default suite — the live smoke test is
``@pytest.mark.slow`` and skips cleanly when the network is unavailable.

sys.path shim per SPEC §7. NO ``import toolshop``.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources._common as common  # noqa: E402
import sources.ccmixter as ccmixter  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
API_PAGE = FIXTURES / "ccmixter_query_page.json"


class FakeResp:
    def __init__(self, json_data=None, status=200, headers=None):
        self._json = json_data
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self._json

    @property
    def text(self):
        return json.dumps(self._json)

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Serves queued JSON responses; records (url, params, headers)."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kw):
        self.calls.append({"url": url, **kw})
        if len(self.responses) > 1:
            return FakeResp(self.responses.pop(0))
        return FakeResp(self.responses[0])


@pytest.fixture()
def page_items():
    return json.loads(API_PAGE.read_text(encoding="utf-8"))


@pytest.fixture()
def page_session(page_items):
    return FakeSession([page_items])


def _entry_for(item, lane="by"):
    return ccmixter._item_to_entry(item, lane)


# ---------------------------------------------------------------------------
# contract shape (SPEC §6.3 / §7 test 2)
# ---------------------------------------------------------------------------


class TestContract:
    def test_module_shape(self):
        assert ccmixter.SOURCE_ID == "ccmixter"
        assert callable(ccmixter.iter_catalog)
        assert callable(ccmixter.license_of)
        assert callable(ccmixter.fetch_lyrics)

    def test_registry_row_matches_adapter(self):
        import sources.registry as registry
        row = registry.get("ccmixter")
        assert row["adapter"] == "ccmixter"
        assert row["fetch_policy"] == "auto"
        assert row["politeness"]["min_interval_s"] >= 1.5
        assert "{contact}" in row["politeness"]["user_agent"]
        assert set(row["categories"]) == {
            "acappella-by", "acappella-pd", "acappella-nc", "acappella-sa"}


# ---------------------------------------------------------------------------
# iter_catalog — parsing, lanes, paging, politeness
# ---------------------------------------------------------------------------


class TestIterCatalog:
    def test_emits_entries_with_per_item_license_fields(
            self, page_items, page_session):
        entries = list(ccmixter.iter_catalog(
            lanes=["by"], session=page_session))
        assert len(entries) == len(page_items)
        by_fid = {e.foreign_identifier: e for e in entries}
        e = by_fid["47456"]
        assert e.title == "Homesick"
        assert e.creator == "kizzylotus"
        assert e.creator_url == "https://ccmixter.org/people/kizzylotus"
        assert e.url == "https://ccmixter.org/files/kizzylotus/47456"
        assert e.source_url == "https://ccmixter.org/files/kizzylotus/47456"
        assert e.license == "CC-BY-3.0"
        assert e.license_tier == "cc-by"
        assert e.release_ok == "yes"
        assert e.category == "acappella-by"
        # lyric source rides the catalog meta (halves the request budget)
        assert "Lyrics" in e.meta["description_plain"]
        # pd-lane content resolves to the release-safe pd bucket —
        # ccMixter 'public domain' marks are dedications, never CC0 (SPEC §1.3)
        pd_e = by_fid["31321"]
        assert pd_e.license == "LicenseRef-public-domain"
        assert pd_e.license_url == ccmixter.CCMIXTER_PD_MARK_URL
        assert pd_e.license_tier == "pd"
        assert pd_e.release_ok == "yes"
        assert pd_e.category == "acappella-pd"

    def test_request_params_and_politeness(self, page_items):
        clock = [0.0]
        sleeps = []
        lim = common.RateLimiter(
            1.5, sleep=lambda s: sleeps.append(s), now=lambda: clock[0])
        sess = FakeSession([page_items, page_items])
        entries = list(ccmixter.iter_catalog(
            lanes=["by", "pd"], session=sess, limiter=lim))
        # one request per lane (10 < PAGE_SIZE terminates each lane)
        assert len(sess.calls) == 2
        lics = {c["params"]["lic"] for c in sess.calls}
        assert lics == {"by", "pd"}
        for c in sess.calls:
            assert c["params"]["f"] == "json"
            assert c["params"]["dataview"] == "default"
            assert c["params"]["tags"] == "acappella"
            assert c["params"]["limit"] == ccmixter.PAGE_SIZE
            ua = c["headers"]["User-Agent"]
            assert "toolshop-lyrics" in ua and "contact" in ua
            assert c["url"] == "https://ccmixter.org/api/query"
        # second lane call was paced to the registry 1.5 s interval
        assert sleeps and sleeps[0] == pytest.approx(1.5)
        # round-robin interleave: both lanes' items appear early
        assert len(entries) == 2 * len(page_items)

    def test_offset_limit_slice(self, page_items, page_session):
        entries = list(ccmixter.iter_catalog(
            lanes=["by"], session=page_session, limit=3, offset=2))
        assert len(entries) == 3
        fids = [e.foreign_identifier for e in entries]
        assert fids == [str(page_items[i]["upload_id"]) for i in (2, 3, 4)]

    def test_paging_until_short_page(self):
        def synth(i):
            return {"upload_id": i, "upload_name": f"P{i}",
                    "user_real_name": "u", "license_url":
                    "http://creativecommons.org/licenses/by/4.0/",
                    "file_page_url": f"https://ccmixter.org/files/u/{i}",
                    "upload_description_plain": "", "upload_extra": {}}
        full = [synth(i) for i in range(ccmixter.PAGE_SIZE)]  # exactly full
        last = [synth(1000), synth(1001)]                      # short -> stop
        sess = FakeSession([full, last])
        entries = list(ccmixter.iter_catalog(lanes=["by"], session=sess,
                                             limiter=common.RateLimiter(
                                                 0, sleep=lambda s: None)))
        assert len(entries) == ccmixter.PAGE_SIZE + 2
        assert len(sess.calls) == 2

    def test_env_lanes_override(self, page_items, page_session, monkeypatch):
        monkeypatch.setenv("CCMIXTER_LANES", "nc")
        list(ccmixter.iter_catalog(session=page_session))
        assert page_session.calls[0]["params"]["lic"] == "nc"

    def test_unknown_lane_rejected(self, page_session):
        with pytest.raises(ValueError, match="unknown ccmixter lic lane"):
            list(ccmixter.iter_catalog(lanes=["bogus"], session=page_session))


# ---------------------------------------------------------------------------
# license_of — URL -> tier mapping (SPEC §7 test 3, §9)
# ---------------------------------------------------------------------------


class TestLicenseMapping:
    @pytest.mark.parametrize("url,license,tier,release", [
        ("http://creativecommons.org/licenses/by/2.5/", "CC-BY-2.5", "cc-by", "yes"),
        ("http://creativecommons.org/licenses/by/3.0/", "CC-BY-3.0", "cc-by", "yes"),
        ("https://creativecommons.org/licenses/by/4.0/", "CC-BY-4.0", "cc-by", "yes"),
        ("http://creativecommons.org/licenses/by-nc/2.5/", "CC-BY-NC-2.5", "cc-by-nc", "no"),
        ("http://creativecommons.org/licenses/by-nc/3.0/", "CC-BY-NC-3.0", "cc-by-nc", "no"),
        ("https://creativecommons.org/licenses/by-nc/4.0/", "CC-BY-NC-4.0", "cc-by-nc", "no"),
        ("http://creativecommons.org/licenses/by-sa/3.0/", "CC-BY-SA-3.0", "cc-by-sa", "conditional"),
        ("https://creativecommons.org/licenses/sampling+/1.0/",
         "LicenseRef-sampling-plus-1.0", "study-only", "no"),
        # ccMixter reports its PD-dedication lane as publicdomain/zero/1.0 —
        # remapped to LicenseRef-public-domain, never CC0-1.0 (SPEC §1.3)
        ("http://creativecommons.org/publicdomain/zero/1.0/",
         "LicenseRef-public-domain", "pd", "yes"),
        ("http://creativecommons.org/publicdomain/mark/1.0/",
         "LicenseRef-public-domain", "pd", "yes"),
        ("https://example.org/not-a-license", "unknown", "study-only", "no"),
        (None, "unknown", "study-only", "no"),
    ])
    def test_url_to_tier(self, url, license, tier, release):
        e = common.CatalogEntry(source_id="ccmixter", license_url=url)
        info = ccmixter.license_of(e)
        assert info.license == license
        assert info.license_tier == tier
        assert info.release_ok == release

    def test_fixture_rows_resolve(self, page_items):
        """Each fixture row resolves to the expected tier/release pair."""
        by_fid = {str(i["upload_id"]): i for i in page_items}
        expected = {
            "47456": ("CC-BY-3.0", "cc-by", "yes"),
            "33699": ("CC-BY-3.0", "cc-by", "yes"),
            "41323": ("CC-BY-3.0", "cc-by", "yes"),
            "31321": ("LicenseRef-public-domain", "pd", "yes"),
            "22762": ("LicenseRef-public-domain", "pd", "yes"),
            "900001": ("CC-BY-NC-3.0", "cc-by-nc", "no"),
            "900002": ("CC-BY-SA-3.0", "cc-by-sa", "conditional"),
            "900003": ("LicenseRef-sampling-plus-1.0", "study-only", "no"),
            "900004": ("unknown", "study-only", "no"),
            "900005": ("CC-BY-4.0", "cc-by", "yes"),
        }
        for fid, (lic, tier, rel) in expected.items():
            e = _entry_for(by_fid[fid])
            assert (e.license, e.license_tier, e.release_ok) == (lic, tier, rel), fid

    def test_ccplus_recorded_in_copyright_notice(self, page_items):
        item = next(i for i in page_items if i["upload_id"] == 900005)
        e = _entry_for(item)
        info = ccmixter.license_of(e)
        assert info.license_tier == "cc-by"          # tier kept (SPEC §6.3)
        assert info.release_ok == "yes"
        assert "ccplus" in (info.copyright_notice or "").lower()

    def test_lic_pd_maps_to_public_domain_ref(self):
        """SPEC §1.3 / R1 §3 (frozen): ccMixter ``lic=pd`` items are PD
        dedications-by-declaration — the site has no CC0. Its
        ``publicdomain/zero/1.0`` report must resolve to
        ``LicenseRef-public-domain`` + the PD mark URL, never ``CC0-1.0``."""
        e = common.CatalogEntry(
            source_id="ccmixter",
            license_url="http://creativecommons.org/publicdomain/zero/1.0/")
        info = ccmixter.license_of(e)
        assert info.license == "LicenseRef-public-domain"
        assert info.license_url == ccmixter.CCMIXTER_PD_MARK_URL
        assert info.license_url.endswith("/publicdomain/mark/1.0/")
        assert info.license_tier == "pd"
        assert info.release_ok == "yes"

    def test_never_upgrades_existing_restriction(self):
        """license_of may only DOWNGRADE — a row already at 'no' stays 'no'
        even when the URL resolves to a release-safe license."""
        e = common.CatalogEntry(
            source_id="ccmixter", release_ok="no", license_tier="study-only",
            license_url="https://creativecommons.org/licenses/by/4.0/")
        info = ccmixter.license_of(e)
        assert info.release_ok == "no"
        assert info.license_tier == "study-only"

    def test_category_derives_from_resolved_license(self, page_items):
        """License class drives the corpus category (release-auditable disk
        layout, SPEC §3.2) — a by-nc item found in the by lane still lands
        under acappella-nc, not the lane it was listed under."""
        item = next(i for i in page_items if i["upload_id"] == 900001)
        e = _entry_for(item, lane="by")          # hypothetical mis-lane
        assert e.category == "acappella-nc"
        sa = _entry_for(
            next(i for i in page_items if i["upload_id"] == 900002))
        assert sa.category == "acappella-sa"


# ---------------------------------------------------------------------------
# lyric extraction
# ---------------------------------------------------------------------------


class TestExtraction:
    def _desc(self, page_items, fid):
        return next(i for i in page_items if i["upload_id"] == fid)[
            "upload_description_plain"]

    def test_header_extraction_and_mojibake_fix(self, page_items):
        res = ccmixter.extract_lyrics(self._desc(page_items, 47456))
        assert res is not None
        raw, clean, sections, how = res
        assert how == "header"
        assert "Take me home" in clean
        # 'â\x80\x99' mojibake repaired to the curly apostrophe (U+2019)
        assert "I’ve seen the flip side of your moon" in clean
        assert "â" not in clean
        # the prose lead-in is not lyric text
        assert "collaborator Heiko" not in clean
        assert len(sections) >= 5  # verse stanzas

    def test_signature_footer_stripped(self, page_items):
        res = ccmixter.extract_lyrics(self._desc(page_items, 31321))
        assert res is not None
        _, clean, _, how = res
        assert how == "header"
        assert "I will persist" in clean
        assert "Joe D. Lincoln" not in clean  # trailing signature dropped

    def test_indented_lyric_lines(self, page_items):
        res = ccmixter.extract_lyrics(self._desc(page_items, 22762))
        assert res is not None
        _, clean, _, _ = res
        assert "Breves dies hominis" in clean
        assert "    Breves" not in clean  # 4-space indents normalised

    def test_verse_run_without_header(self, page_items):
        """33699 has NO marker header: title line, then verse stanzas, a
        ____ divider, then trailing prose. Verse-run strategy finds the
        lyric region and excludes the prose tail."""
        res = ccmixter.extract_lyrics(self._desc(page_items, 33699))
        assert res is not None
        _, clean, sections, how = res
        assert how == "verse-run"
        assert "chosen we wander in a web of derision" in clean
        assert "very personal song" not in clean   # trailing prose excluded
        assert "Thanks to Gurdonark" not in clean
        assert len(sections) >= 3

    def test_prose_only_returns_none(self, page_items):
        assert ccmixter.extract_lyrics(self._desc(page_items, 41323)) is None
        assert ccmixter.extract_lyrics("") is None
        assert ccmixter.extract_lyrics(None) is None

    def test_synthetic_header_row(self, page_items):
        res = ccmixter.extract_lyrics(self._desc(page_items, 900001))
        assert res is not None
        _, clean, _, how = res
        assert how == "header"
        assert "line one of the test verse" in clean

    def test_short_couplet_rejected(self):
        """A lone 2-line couplet inside prose is not a lyric sheet."""
        desc = ("This is a long prose paragraph about the recording process "
                "with plenty of words and sentence endings.\n\n"
                "roses are red\nviolets are blue\n\n"
                "More prose follows here to close the description out "
                "properly with detail.")
        assert ccmixter.extract_lyrics(desc) is None


# ---------------------------------------------------------------------------
# fetch_lyrics — song JSON v2 + drop path
# ---------------------------------------------------------------------------


class TestFetchLyrics:
    def _entry(self, page_items, fid, lane="by"):
        return _entry_for(
            next(i for i in page_items if i["upload_id"] == fid), lane)

    def test_song_json_v2_fields(self, page_items):
        song = ccmixter.fetch_lyrics(self._entry(page_items, 47456))
        assert song["title"] == "Homesick"
        assert song["primary_artist"] == "kizzylotus"     # NOT NULL contract
        assert song["artist"] == "kizzylotus"
        assert song["category"] == "acappella-by"
        assert song["url"] == "https://ccmixter.org/files/kizzylotus/47456"
        assert song["corpus"] == "ccmixter"
        assert song["source"] == "ccmixter"
        assert song["foreign_identifier"] == "47456"
        assert song["source_url"] == "https://ccmixter.org/files/kizzylotus/47456"
        assert song["creator"] == "kizzylotus"
        assert song["creator_url"] == "https://ccmixter.org/people/kizzylotus"
        assert song["license"] == "CC-BY-3.0"
        assert song["license_url"] == "http://creativecommons.org/licenses/by/3.0/"
        assert song["license_tier"] == "cc-by"
        assert song["release_ok"] == "yes"
        assert song["language"] == "en"
        assert "Take me home" in song["clean_lyrics"]
        assert len(song["sections"]) >= 2
        assert song["meta"]["extraction"] == "header"

    def test_pd_item_release_safe(self, page_items):
        song = ccmixter.fetch_lyrics(self._entry(page_items, 31321, "pd"))
        assert song["license"] == "LicenseRef-public-domain"
        assert song["license_url"] == ccmixter.CCMIXTER_PD_MARK_URL
        assert song["license_tier"] == "pd"
        assert song["release_ok"] == "yes"
        assert song["category"] == "acappella-pd"
        assert song["language"] == "en"

    def test_latin_text_language_guess(self, page_items):
        song = ccmixter.fetch_lyrics(self._entry(page_items, 22762, "pd"))
        assert song["language"] == "la"

    def test_no_lyric_text_drops(self, page_items):
        with pytest.raises(common.DropItem) as ei:
            ccmixter.fetch_lyrics(self._entry(page_items, 41323))
        assert ei.value.reason == "no-lyric-text"

    def test_ids_refetch_fallback(self, page_items):
        """A catalog row without stored descriptions refetches the single
        upload via ids= (one polite request) before extracting."""
        bare = common.CatalogEntry(
            source_id="ccmixter", foreign_identifier="47456",
            title="Homesick", url="https://ccmixter.org/files/kizzylotus/47456",
            creator="kizzylotus", category="acappella-by",
            license_url="http://creativecommons.org/licenses/by/3.0/",
            license="CC-BY-3.0", license_tier="cc-by", release_ok="yes",
            meta={})
        target = next(i for i in page_items if i["upload_id"] == 47456)
        sess = FakeSession([[target]])
        song = ccmixter.fetch_lyrics(bare, session=sess)
        assert len(sess.calls) == 1
        assert sess.calls[0]["params"]["ids"] == "47456"
        assert "Take me home" in song["clean_lyrics"]


# ---------------------------------------------------------------------------
# dispatcher end-to-end through the real adapter (network stubbed)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_dispatcher_writes_corpus(self, page_items, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ccmixter, "_api_query",
            lambda params, **kw: page_items if params.get("lic") == "by" else [])
        rc = dispatcher.run("ccmixter", adapter=ccmixter,
                            data_dir=tmp_path, quiet=True)
        assert rc == 0
        corpus_root = tmp_path / "lyrics" / "ccmixter"
        assert (corpus_root / "_catalog.json").exists()
        assert (corpus_root / "_index.json").exists()
        by_dir = corpus_root / "acappella-by"
        pd_dir = corpus_root / "acappella-pd"
        by_songs = sorted(by_dir.glob("*.json"))
        pd_songs = sorted(pd_dir.glob("*.json"))
        # lyric-bearing fixture rows: 47456, 33699 (by) + 31321, 22762 (pd)
        assert len(by_songs) == 2 and len(pd_songs) == 2
        song = json.loads(by_songs[0].read_text(encoding="utf-8"))
        assert song["license_tier"] == "cc-by"
        assert song["release_ok"] == "yes"
        # dropped entries are recorded, never written
        doc = json.loads((corpus_root / "_catalog.json")
                         .read_text(encoding="utf-8"))
        by_status = {str(e["foreign_identifier"]): e
                     for e in doc["entries"]}
        assert by_status["41323"]["status"] == "dropped"
        assert by_status["41323"]["drop_reason"] == "no-lyric-text"
        # NC study-tier item was fetched into its own license-classed dir
        assert by_status["900001"]["status"] == "fetched"
        assert by_status["900001"]["license_tier"] == "cc-by-nc"
        assert by_status["900001"]["release_ok"] == "no"
        nc_songs = sorted((corpus_root / "acappella-nc").glob("*.json"))
        assert len(nc_songs) == 1
        for fid in ("900002", "900003", "900004", "900005"):
            assert by_status[fid]["status"] == "dropped"
        # index carries license fields (F8): 2 by + 2 pd + 1 nc
        index = json.loads((corpus_root / "_index.json")
                           .read_text(encoding="utf-8"))
        assert len(index) == 5
        tiers = sorted(e["license_tier"] for e in index)
        assert tiers == ["cc-by", "cc-by", "cc-by-nc", "pd", "pd"]
        release = sorted(e["release_ok"] for e in index)
        assert release == ["no", "yes", "yes", "yes", "yes"]
        for e in index:
            assert e["corpus"] == "ccmixter"
            assert e["source"] == "ccmixter"
            assert e["license"] and e["license_url"]
            assert e["creator"]


# ---------------------------------------------------------------------------
# live smoke — slow marker only, degrades gracefully offline (F5)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_live_catalog_smoke():
    """Real API hit: 4 items across the release-safe lanes. Skips cleanly
    when the proxy/network fails."""
    try:
        entries = list(itertools.islice(
            ccmixter.iter_catalog(limit=4), 4))
    except Exception as e:  # pragma: no cover - network dependent
        pytest.skip(f"ccmixter unreachable from this environment: {e}")
    assert len(entries) == 4
    assert all(e.foreign_identifier for e in entries)
    assert all(e.license for e in entries)
    assert all(e.license_tier in
               {"cc-by", "cc0", "pd", "cc-by-nc", "cc-by-sa", "study-only"}
               for e in entries)
