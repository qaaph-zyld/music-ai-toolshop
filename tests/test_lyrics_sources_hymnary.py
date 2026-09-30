"""hymnary.org adapter tests (wave B, agent I7).

Covers ``sources/hymnary.py`` against committed fixtures:
- ``hymnary_instances_export.csv`` — synthetic ``in:instances`` CSV export
  (6 textAuthNumbers incl. boundary cases TEST1931 / CC1930 / GC2-no-year).
- ``hymnary_text_amazing_grace.html`` — synthetic ``/text/<id>`` page:
  infoTable, Author block, numbered rep-text stanzas, "Olney Hymns, 1779"
  attribution, instance cards w/ Date fields + a /page/ scan link + a
  duplicated card href.
- ``hymnary_text_modern_rep.html`` — rep text attributed "Ancient & Modern,
  2013" but a 1908 instance card exists (modified_note path).
- ``hymnary_text_1930.html`` / ``hymnary_text_1931.html`` — exact boundary.
- ``hymnary_text_nodate.html`` — nothing resolvable → hard drop.

NO live fetch in the default suite — FakeSession serves every GET.
sys.path shim per SPEC §7. NO ``import toolshop``.
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
import sources.hymnary as hymnary  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
CSV_EXPORT = (FIXTURES / "hymnary_instances_export.csv").read_text(encoding="utf-8")
PAGE_AG = (FIXTURES / "hymnary_text_amazing_grace.html").read_text(encoding="utf-8")
PAGE_MODERN = (FIXTURES / "hymnary_text_modern_rep.html").read_text(encoding="utf-8")
PAGE_1930 = (FIXTURES / "hymnary_text_1930.html").read_text(encoding="utf-8")
PAGE_1931 = (FIXTURES / "hymnary_text_1931.html").read_text(encoding="utf-8")
PAGE_NODATE = (FIXTURES / "hymnary_text_nodate.html").read_text(encoding="utf-8")


class FakeResp:
    def __init__(self, text="", status=200, headers=None):
        self.text = text
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Maps URL substrings → FakeResp; records every URL fetched."""

    def __init__(self, mapping, default=None):
        self.mapping = dict(mapping)
        self.default = default or FakeResp("<html></html>", status=404)
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(url)
        for key, resp in self.mapping.items():
            if key in url:
                return resp
        return self.default


def _csv_resp(text=CSV_EXPORT):
    return FakeResp(text, headers={"Content-Type": "text/csv"})


@pytest.fixture(autouse=True)
def _no_net(monkeypatch):
    """Route every adapter GET through the injected session + no-wait limiter."""
    sess = FakeSession({"export=csv": _csv_resp()})
    monkeypatch.setattr(hymnary, "_SESSION", sess)
    monkeypatch.setattr(hymnary, "_LIMITER", common.RateLimiter(0))
    return sess


def _entry(fid, title="", **meta):
    return common.CatalogEntry(
        source_id="hymnary", foreign_identifier=fid, title=title,
        url=f"https://hymnary.org/text/{fid}", creator="Fixture Author",
        category="pre-1931", meta=meta)


# ---------------------------------------------------------------------------
# contract shape (SPEC §6.3 / §7)
# ---------------------------------------------------------------------------


class TestContract:
    def test_module_shape(self):
        assert hymnary.SOURCE_ID == "hymnary"
        assert callable(hymnary.iter_catalog)
        assert callable(hymnary.license_of)
        assert callable(hymnary.fetch_lyrics)

    def test_registry_row_matches_adapter(self):
        import sources.registry as registry
        row = registry.get("hymnary")
        assert row["adapter"] == "hymnary"
        assert row["fetch_policy"] == "auto"
        assert row["license_tier"] == "pd"
        assert row["corpus_tag"] == "hymnary"

    def test_no_toolshop_import(self):
        src = (EXTRACTOR / "sources" / "hymnary.py").read_text(encoding="utf-8")
        assert "import toolshop" not in src


# ---------------------------------------------------------------------------
# iter_catalog — CSV-primary lane
# ---------------------------------------------------------------------------


class TestIterCatalog:
    def test_csv_lane_merges_seed_exports(self, _no_net):
        entries = list(hymnary.iter_catalog())
        by_fid = {e.foreign_identifier: e for e in entries}
        # 5 unique texts across the fixture export (12 seed calls return the
        # same body — dedupe by textAuthNumber collapses them)
        assert len(by_fid) == 5
        ag = by_fid["amazing_grace_how_sweet_the_sound"]
        assert ag.title == "Amazing grace! (how sweet the sound)"
        assert ag.creator == "John Newton"
        assert ag.url.endswith("/text/amazing_grace_how_sweet_the_sound")
        assert ag.category == "pre-1931"
        assert ag.meta["lane"] == "csv-export"
        # both fixture instances merged, years resolved via hymnalID suffix
        assert ag.meta["instance_years"] == [1908, 1992]
        assert ag.meta["min_instance_year"] == 1908
        assert {i["hymnal_id"] for i in ag.meta["instances"]} == {
            "OSSN1908", "NHCS1992"}

    def test_csv_lane_limit_offset(self, _no_net):
        entries = list(hymnary.iter_catalog(limit=2, offset=1))
        fids = [e.foreign_identifier for e in entries]
        assert fids == ["modern_only_hymn", "o_god_our_help_in_ages_past"]

    def test_catalog_schema_conformance(self, _no_net):
        e = next(iter(hymnary.iter_catalog(limit=1)))
        d = e.to_dict()
        for k in ("source", "external_id", "foreign_identifier", "title",
                  "url", "creator", "category", "status", "drop_reason",
                  "license_tier", "release_ok", "license_ref", "meta"):
            assert k in d, f"catalog row missing '{k}'"
        assert d["source"] == "hymnary"
        assert d["status"] == "pending"

    def test_html_fallback_when_csv_dead(self, monkeypatch):
        """CSV lane raises (403 HTML instead of CSV) → HTML fallback walks
        seed pages' /text/ links instead of silently emitting nothing."""
        monkeypatch.setattr(hymnary, "HTML_SEED_TEXTS", ("seed",))
        monkeypatch.setattr(
            hymnary, "_SESSION",
            FakeSession({
                "export=csv": FakeResp("<html>blocked</html>", status=403),
                "/text/seed": FakeResp(
                    '<a href="/text/first_hymn">x</a>'
                    '<a href="/text/second_hymn">y</a>'),
            }))
        entries = list(hymnary.iter_catalog())
        assert [e.foreign_identifier for e in entries] == [
            "first_hymn", "second_hymn"]
        assert all(e.meta["lane"] == "html-fallback" for e in entries)


# ---------------------------------------------------------------------------
# year-gate helpers + license_of — the 1931 boundary
# ---------------------------------------------------------------------------


class TestYearGate:
    def test_hymnal_id_suffix(self):
        assert hymnary.year_from_hymnal_id("OSSN1908") == 1908
        assert hymnary.year_from_hymnal_id("CC1930") == 1930
        assert hymnary.year_from_hymnal_id("TEST1931") == 1931
        assert hymnary.year_from_hymnal_id("GC2") is None
        assert hymnary.year_from_hymnal_id("") is None
        assert hymnary.year_from_hymnal_id(None) is None

    def test_pd_status(self):
        assert hymnary.pd_status([]) == "unresolved"
        assert hymnary.pd_status([None]) == "unresolved"
        assert hymnary.pd_status([1930]) == "pd"
        assert hymnary.pd_status([1779, 1992]) == "pd"
        assert hymnary.pd_status([1931]) == "post-1930"
        assert hymnary.pd_status([1992, 2008]) == "post-1930"

    def test_1931_instance_dropped(self):
        """Exact boundary: a hymn resolving only to 1931 must drop — 1931 is
        NOT public domain under the ≤1930 rule."""
        e = _entry("post_1931_test_hymn", instance_years=[1931])
        with pytest.raises(common.DropItem) as ei:
            hymnary.license_of(e)
        assert ei.value.reason == "post-1930-instance:min=1931"

    def test_1930_instance_retained(self):
        """Exact boundary: 1930 IS retained (pre-1931)."""
        e = _entry("o_god_our_help_in_ages_past", instance_years=[1930])
        info = hymnary.license_of(e)
        assert info.license == "LicenseRef-public-domain"
        assert info.license_tier == "pd"
        assert info.release_ok == "yes"

    def test_no_years_passes_to_fetch_gate(self):
        """Unresolved catalog rows defer to fetch_lyrics' authoritative gate
        (license_of must NOT silently assume PD — it returns a bare
        LicenseInfo, and fetch drops when nothing resolves)."""
        e = _entry("undated_hymn")
        info = hymnary.license_of(e)
        assert info.license_tier is None and info.release_ok is None


# ---------------------------------------------------------------------------
# text-page parsing
# ---------------------------------------------------------------------------


class TestPageParsing:
    def test_parse_amazing_grace_page(self):
        page = hymnary.parse_text_page(PAGE_AG)
        assert page["title"] == "Amazing grace! (how sweet the sound)"
        assert page["author"] == "John Newton"
        assert page["author_url"] == "https://hymnary.org/person/Newton_John"
        assert page["meter"] == "8.6.8.6"
        assert page["language"] == "English"
        assert page["copyright_field"] == "Public Domain"
        assert page["first_line"] == "Amazing grace! how sweet the sound"
        assert len(page["rep_stanzas"]) == 3
        assert page["rep_stanzas"][0].startswith("Amazing grace!")
        # leading stanza number stripped
        assert not page["rep_stanzas"][0].startswith("1 ")
        assert page["rep_attribution"] == "Olney Hymns, 1779"
        assert page["rep_year"] == 1779

    def test_instance_cards_dedupe_and_no_scans(self):
        cards = hymnary.parse_instance_cards(
            hymnary._section_html(PAGE_AG, "instances"))
        # /page/61 scan link excluded; the NHCS1992 href appears twice but
        # yields ONE card (linkbox + heading share the URL)
        assert len(cards) == 2
        ossn = next(c for c in cards if c["hymnal_id"] == "OSSN1908")
        assert ossn["year"] == 1908
        assert ossn["number"] == "53"
        nhcs = next(c for c in cards if c["hymnal_id"] == "NHCS1992")
        assert nhcs["year"] == 1992
        page_urls = [c["url"] for c in cards]
        assert not any("/page/" in u for u in page_urls)

    def test_years_in_text(self):
        assert hymnary.years_in_text("Ancient & Modern, 2013") == [2013]
        assert hymnary.years_in_text("Olney Hymns, 1779") == [1779]
        assert hymnary.years_in_text("no year here") == []
        assert hymnary.years_in_text(None) == []


# ---------------------------------------------------------------------------
# fetch_lyrics — gate + song JSON v2
# ---------------------------------------------------------------------------


def _fetch(monkeypatch, fid, page_html, csv_text=CSV_EXPORT,
           title="", **meta):
    sess = FakeSession({
        f"/text/{fid}": FakeResp(page_html),
        "export=csv": _csv_resp(csv_text),
    })
    monkeypatch.setattr(hymnary, "_SESSION", sess)
    monkeypatch.setattr(hymnary, "_LIMITER", common.RateLimiter(0))
    return hymnary.fetch_lyrics(_entry(fid, title=title, **meta))


class TestFetchLyrics:
    def test_song_json_v2_fields(self, monkeypatch):
        song = _fetch(monkeypatch, "amazing_grace_how_sweet_the_sound", PAGE_AG)
        assert song["title"] == "Amazing grace! (how sweet the sound)"
        assert song["primary_artist"] == "John Newton"   # NOT NULL contract
        assert song["artist"] == "John Newton"
        assert song["category"] == "pre-1931"
        assert song["corpus"] == "hymnary"
        assert song["source"] == "hymnary"
        assert song["foreign_identifier"] == "amazing_grace_how_sweet_the_sound"
        assert song["source_url"].endswith(
            "/text/amazing_grace_how_sweet_the_sound")
        assert song["creator"] == "John Newton"
        assert song["creator_url"].endswith("/person/Newton_John")
        assert song["license"] == "LicenseRef-public-domain"
        assert song["license_tier"] == "pd"
        assert song["release_ok"] == "yes"
        assert song["copyright_notice"] == "Public Domain"
        assert "Amazing grace!" in song["clean_lyrics"]
        assert len(song["sections"]) == 3
        assert song["meta"]["pd_year"] == 1779
        assert song["meta"]["min_instance_year"] == 1908
        assert song["meta"]["rep_text_year"] == 1779
        assert song["modified_note"] is None

    def test_modern_rep_records_pd_basis(self, monkeypatch):
        """Rep text from a 2013 hymnal but a 1908 instance exists → emit with
        modified_note naming exactly what was shown vs the PD basis."""
        song = _fetch(monkeypatch, "modern_rep_hymn", PAGE_MODERN)
        assert song["meta"]["rep_text_year"] == 2013
        assert song["meta"]["pd_year"] == 1908
        assert "Ancient" in (song["meta"]["rep_text_source"] or "")
        assert song["modified_note"] and "1908" in song["modified_note"]
        assert song["license_tier"] == "pd" and song["release_ok"] == "yes"

    def test_1930_boundary_page_retained(self, monkeypatch):
        """Fetch-level boundary: attribution 1930 → pd_year 1930, released."""
        song = _fetch(monkeypatch, "boundary_1930_hymn", PAGE_1930)
        assert song["meta"]["pd_year"] == 1930
        assert song["license_tier"] == "pd"
        assert song["release_ok"] == "yes"

    def test_1931_boundary_page_dropped(self, monkeypatch):
        """Fetch-level boundary: only year 1931 resolvable → dropped, never
        silently assumed PD."""
        with pytest.raises(common.DropItem) as ei:
            _fetch(monkeypatch, "boundary_1931_hymn", PAGE_1931,
                   csv_text="a,b\n1,2\n")
        assert ei.value.reason == "post-1930-instance:min=1931"

    def test_unresolvable_date_dropped(self, monkeypatch):
        """No year anywhere (page empty, CSV row GC2 has no suffix) → hard
        drop 'date-unresolvable'. Silent PD assumption is a blocker."""
        with pytest.raises(common.DropItem) as ei:
            _fetch(monkeypatch, "undated_hymn", PAGE_NODATE)
        assert ei.value.reason == "date-unresolvable"

    def test_no_lyric_text_drops(self, monkeypatch):
        blank = PAGE_AG.replace('<div class="authority_columns">', '<div>')
        with pytest.raises(common.DropItem) as ei:
            _fetch(monkeypatch, "amazing_grace_how_sweet_the_sound", blank)
        assert ei.value.reason == "no-lyric-text"


# ---------------------------------------------------------------------------
# dispatcher end-to-end through the real adapter (network stubbed)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_dispatcher_writes_corpus(self, tmp_path, monkeypatch):
        sess = FakeSession({
            "export=csv": _csv_resp(),
            "/text/amazing_grace_how_sweet_the_sound": FakeResp(PAGE_AG),
            "/text/o_god_our_help_in_ages_past": FakeResp(PAGE_1930),
            "/text/undated_hymn": FakeResp(PAGE_NODATE),
        })
        monkeypatch.setattr(hymnary, "_SESSION", sess)
        monkeypatch.setattr(hymnary, "_LIMITER", common.RateLimiter(0))
        rc = dispatcher.run("hymnary", adapter=hymnary,
                            data_dir=tmp_path, quiet=True)
        assert rc == 0
        corpus_root = tmp_path / "lyrics" / "hymnary"
        assert (corpus_root / "_catalog.json").exists()
        assert (corpus_root / "_index.json").exists()
        songs = sorted((corpus_root / "pre-1931").glob("*.json"))
        # fetched: amazing_grace (1779/1908) + o_god (1930 boundary)
        assert len(songs) == 2
        doc = json.loads((corpus_root / "_catalog.json")
                         .read_text(encoding="utf-8"))
        by_fid = {e["foreign_identifier"]: e for e in doc["entries"]}
        assert by_fid["post_1931_test_hymn"]["status"] == "dropped"
        assert by_fid["post_1931_test_hymn"]["drop_reason"] == \
            "post-1930-instance:min=1931"
        assert by_fid["modern_only_hymn"]["status"] == "dropped"
        assert by_fid["modern_only_hymn"]["drop_reason"] == \
            "post-1930-instance:min=1992"
        assert by_fid["undated_hymn"]["status"] == "dropped"
        assert by_fid["undated_hymn"]["drop_reason"] == "date-unresolvable"
        assert by_fid["amazing_grace_how_sweet_the_sound"]["status"] == "fetched"
        song = json.loads(songs[0].read_text(encoding="utf-8"))
        assert song["license_tier"] == "pd" and song["release_ok"] == "yes"
