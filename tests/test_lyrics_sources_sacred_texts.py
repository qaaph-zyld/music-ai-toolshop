"""sacred-texts.com adapter tests (wave B, agent I7).

Covers ``sources/sacred_texts.py`` — the static Child Ballads mirror —
against committed fixtures:

- ``sacred_texts_ch250_excerpt.html`` — synthetic SvelteKit page whose
  ``chapterContent.contentHtml`` mirrors the real wire format: version
  headings ``250A:``/``250B:``, inline stanza refs ``250A.1``, a ``Refrain:``
  paragraph, an asterism break, an editorial notes paragraph, and the
  transcription's real latin-1 mojibake (``â`` + C1 controls for ``’``).
  Ballad text: Child #250 "Henry Martyn" — the book is 1882–98, public
  domain.
- ``sacred_texts_no_chapter.html`` — page without ``chapterContent``.
- ``sacred_texts_ch002_prose.html`` — chapter block but only prose (lacuna
  shape → ``no-ballad-text`` drop).

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
import sources.sacred_texts as st  # noqa: E402
import fetch_lyrics_source as dispatcher  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
PAGE_250 = (FIXTURES / "sacred_texts_ch250_excerpt.html").read_text(
    encoding="utf-8")
PAGE_NOCH = (FIXTURES / "sacred_texts_no_chapter.html").read_text(
    encoding="utf-8")
PAGE_PROSE = (FIXTURES / "sacred_texts_ch002_prose.html").read_text(
    encoding="utf-8")


class FakeResp:
    def __init__(self, text="", status=200, headers=None):
        self.text = text
        self.status_code = status
        self.headers = headers or {"Content-Type": "text/html"}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
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


@pytest.fixture(autouse=True)
def _no_net(monkeypatch):
    sess = FakeSession({})
    monkeypatch.setattr(st, "_SESSION", sess)
    monkeypatch.setattr(st, "_LIMITER", common.RateLimiter(0))
    return sess


def _entry(n=250, title="Child ballad 250"):
    return common.CatalogEntry(
        source_id="sacred_texts", foreign_identifier=f"child-{n:03d}",
        title=title, url=st.PAGE_TEMPLATE.format(n=n),
        creator="Traditional", category="child-ballads",
        license="LicenseRef-public-domain",
        license_url=st.PD_LICENSE_URL, license_tier="pd",
        release_ok="yes", meta={"child_number": n})


# ---------------------------------------------------------------------------
# contract shape
# ---------------------------------------------------------------------------


class TestContract:
    def test_module_shape(self):
        assert st.SOURCE_ID == "sacred_texts"
        assert callable(st.iter_catalog)
        assert callable(st.license_of)
        assert callable(st.fetch_lyrics)

    def test_registry_row_matches_adapter(self):
        import sources.registry as registry
        row = registry.get("sacred_texts")
        assert row["adapter"] == "sacred_texts"
        assert row["fetch_policy"] == "auto"
        assert row["license_tier"] == "pd"
        assert row["corpus_tag"] == "sacred-texts"

    def test_no_toolshop_import(self):
        src = (EXTRACTOR / "sources" / "sacred_texts.py").read_text(
            encoding="utf-8")
        assert "import toolshop" not in src


# ---------------------------------------------------------------------------
# iter_catalog — deterministic enumeration, zero network
# ---------------------------------------------------------------------------


class TestIterCatalog:
    def test_enumerates_all_305_without_network(self, _no_net):
        entries = list(st.iter_catalog())
        assert len(entries) == 305
        assert _no_net.calls == []          # catalog stage fetches nothing
        assert entries[0].foreign_identifier == "child-001"
        assert entries[-1].foreign_identifier == "child-305"

    def test_entry_fields_and_license(self, _no_net):
        e = next(iter(st.iter_catalog()))
        assert e.source_id == "sacred_texts"
        assert e.url == "https://sacred-texts.com/neu/eng/child/ch001.htm"
        assert e.creator == "Traditional"
        assert e.category == "child-ballads"
        assert e.license == "LicenseRef-public-domain"
        assert e.license_tier == "pd"
        assert e.release_ok == "yes"
        assert e.meta["child_number"] == 1

    def test_limit_offset(self, _no_net):
        entries = list(st.iter_catalog(limit=3, offset=2))
        assert [e.foreign_identifier for e in entries] == [
            "child-003", "child-004", "child-005"]

    def test_catalog_schema_conformance(self, _no_net):
        e = next(iter(st.iter_catalog(limit=1)))
        d = e.to_dict()
        for k in ("source", "external_id", "foreign_identifier", "title",
                  "url", "creator", "category", "status", "drop_reason",
                  "license_tier", "release_ok", "license_ref", "meta"):
            assert k in d, f"catalog row missing '{k}'"
        assert d["source"] == "sacred_texts"
        assert d["status"] == "pending"

    def test_license_of_is_pd_with_notice(self, _no_net):
        info = st.license_of(_entry())
        assert info.license == "LicenseRef-public-domain"
        assert info.license_tier == "pd"
        assert info.release_ok == "yes"
        assert "public domain" in (info.copyright_notice or "").lower()


# ---------------------------------------------------------------------------
# chapter extraction + ballad parsing
# ---------------------------------------------------------------------------


class TestParsing:
    def test_extract_chapter(self):
        ch = st.extract_chapter(PAGE_250)
        assert ch is not None
        assert "<h1>250A: Henry Martyn</h1>" in ch["content_html"]
        assert "250A.1" in ch.get("content_text", "")
        assert st.extract_chapter(PAGE_NOCH) is None

    def test_parse_ballad_versions_stanzas(self):
        parsed = st.parse_ballad_html(
            st.extract_chapter(PAGE_250)["content_html"])
        assert parsed["title"] == "Henry Martyn"
        assert parsed["ballad_refs"] == ["250A", "250B"]
        stanzas = [u for u in parsed["units"] if u["kind"] == "stanza"]
        refrains = [u for u in parsed["units"] if u["kind"] == "refrain"]
        assert [u["ref"] for u in stanzas] == [
            "250A.1", "250A.2", "250A.3", "250B.1"]
        assert len(refrains) == 1
        # refrain follows the 250B stanza block → it belongs to version 250B
        assert refrains[0]["ref"] == "250B Refrain 1"
        # prose before the first version head lands in notes
        assert any("Notes paragraph" in n for n in parsed["notes"])
        # asterism break dropped
        assert not any("* * *" in u["text"] for u in parsed["units"])

    def test_stanza_text_and_mojibake_repair(self):
        parsed = st.parse_ballad_html(
            st.extract_chapter(PAGE_250)["content_html"])
        stanzas = {u["ref"]: u["text"] for u in parsed["units"]
                   if u["kind"] == "stanza"}
        assert "IN merry Scotland" in stanzas["250A.1"]
        # â + C1-control mojibake repaired to the curly apostrophe
        assert "winter\u2019s" in stanzas["250A.3"]
        assert "\u0080" not in stanzas["250A.3"]


# ---------------------------------------------------------------------------
# fetch_lyrics — song JSON v2 + drops
# ---------------------------------------------------------------------------


def _fetch(monkeypatch, n, page_html, title=None):
    sess = FakeSession({f"ch{n:03d}.htm": FakeResp(page_html)})
    monkeypatch.setattr(st, "_SESSION", sess)
    monkeypatch.setattr(st, "_LIMITER", common.RateLimiter(0))
    return st.fetch_lyrics(_entry(n, title or f"Child ballad {n}"))


class TestFetchLyrics:
    def test_song_json_v2_fields(self, monkeypatch):
        song = _fetch(monkeypatch, 250, PAGE_250)
        assert song["title"] == "Henry Martyn"
        assert song["primary_artist"] == "Traditional"   # NOT NULL contract
        assert song["artist"] == "Traditional"
        assert song["category"] == "child-ballads"
        assert song["corpus"] == "sacred-texts"
        assert song["source"] == "sacred_texts"
        assert song["foreign_identifier"] == "child-250"
        assert song["source_url"] == \
            "https://sacred-texts.com/neu/eng/child/ch250.htm"
        assert song["creator"] == "Traditional"
        assert song["license"] == "LicenseRef-public-domain"
        assert song["license_tier"] == "pd"
        assert song["release_ok"] == "yes"
        assert "public domain" in song["copyright_notice"].lower()
        assert "IN merry Scotland" in song["clean_lyrics"]
        labels = [s["label"] for s in song["sections"]]
        assert labels == ["250A.1", "250A.2", "250A.3", "250B.1",
                          "250B Refrain 1"]
        assert song["meta"]["child_number"] == 250
        assert song["meta"]["editor"] == "Francis James Child"
        assert song["meta"]["version_refs"] == ["250A", "250B"]
        assert song["meta"]["stanza_count"] == 4
        assert song["language"] == "en"

    def test_page_missing_drops(self, monkeypatch):
        sess = FakeSession({})      # default 404
        monkeypatch.setattr(st, "_SESSION", sess)
        monkeypatch.setattr(st, "_LIMITER", common.RateLimiter(0))
        with pytest.raises(common.DropItem) as ei:
            st.fetch_lyrics(_entry(7))
        assert ei.value.reason == "page-missing"

    def test_no_chapter_content_drops(self, monkeypatch):
        with pytest.raises(common.DropItem) as ei:
            _fetch(monkeypatch, 250, PAGE_NOCH)
        assert ei.value.reason == "no-chapter-content"

    def test_prose_only_drops(self, monkeypatch):
        with pytest.raises(common.DropItem) as ei:
            _fetch(monkeypatch, 2, PAGE_PROSE)
        assert ei.value.reason == "no-ballad-text"


# ---------------------------------------------------------------------------
# dispatcher end-to-end through the real adapter (network stubbed)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_dispatcher_writes_corpus(self, tmp_path, monkeypatch):
        sess = FakeSession({
            "ch001.htm": FakeResp(PAGE_250),
            "ch002.htm": FakeResp(PAGE_PROSE),
            "ch003.htm": FakeResp(PAGE_NOCH),
        })
        monkeypatch.setattr(st, "_SESSION", sess)
        monkeypatch.setattr(st, "_LIMITER", common.RateLimiter(0))
        rc = dispatcher.run("sacred_texts", adapter=st, data_dir=tmp_path,
                            limit=3, quiet=True)
        assert rc == 0
        corpus_root = tmp_path / "lyrics" / "sacred-texts"
        assert (corpus_root / "_catalog.json").exists()
        assert (corpus_root / "_index.json").exists()
        songs = sorted((corpus_root / "child-ballads").glob("*.json"))
        assert len(songs) == 1                    # only ch001 fetched
        song = json.loads(songs[0].read_text(encoding="utf-8"))
        assert song["license_tier"] == "pd" and song["release_ok"] == "yes"
        assert song["title"] == "Henry Martyn"
        doc = json.loads((corpus_root / "_catalog.json")
                         .read_text(encoding="utf-8"))
        by_fid = {e["foreign_identifier"]: e for e in doc["entries"]}
        assert len(by_fid) == 305                 # full catalog listed
        assert by_fid["child-001"]["status"] == "fetched"
        assert by_fid["child-002"]["status"] == "dropped"
        assert by_fid["child-002"]["drop_reason"] == "no-ballad-text"
        assert by_fid["child-003"]["status"] == "dropped"
        assert by_fid["child-003"]["drop_reason"] == "no-chapter-content"
