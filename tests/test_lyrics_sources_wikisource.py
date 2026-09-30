"""Wikisource PD adapter tests — lyrics-sources wave A, agent I3.

Covers ``sources/wikisource_pd.py``: MediaWiki categorymembers/parse
fixture traversal, the six frozen sr branches + en categories, the
per-page license-template gate (PD / CC-BY-SA conditional / NC drop),
Cyrillic -> Latin + diacritic-fold normalization (lyricsdb parity),
canonical ``Strofa N`` section labels, and the no-network default
(all hits served by a FakeSession; real API hits are @pytest.mark.slow).

sys.path shim per SPEC §7. No ``import toolshop`` — the lyricsdb section
parser is loaded by file path so the eager toolshop package init never
runs.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources.registry as registry  # noqa: E402
import sources.wikisource_pd as ws  # noqa: E402
from sources import _common as common  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
TREE = json.loads(
    (FIXTURES / "mw_sr_category_tree.json").read_text(encoding="utf-8"))


def _parse_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


#: real section-label parser, loaded by path (bypasses toolshop __init__)
_LDB_SPEC = importlib.util.spec_from_file_location(
    "lyricsdb_standalone", REPO_ROOT / "toolshop" / "lyricsdb.py")
_ldb = importlib.util.module_from_spec(_LDB_SPEC)
sys.modules["lyricsdb_standalone"] = _ldb  # dataclasses need sys.modules
_LDB_SPEC.loader.exec_module(_ldb)


class FakeResp:
    def __init__(self, json_data=None, text=""):
        self._json = json_data
        self.text = text
        self.status_code = 200
        self.headers = {}
        self.content = text.encode("utf-8")

    def json(self):
        if self._json is not None:
            return self._json
        return json.loads(self.text)

    def raise_for_status(self):
        pass


class FakeWikiSession:
    """Serves categorymembers (incl. cmcontinue pages encoded as a list of
    member-lists) and action=parse responses from fixtures. Serial by
    construction — records every call for politeness assertions."""

    def __init__(self, tree=None, parses=None):
        self.tree = tree or TREE["cats"]
        self.parses = parses or {}
        self.calls = []

    def get(self, url, params=None, **kw):
        params = dict(params or {})
        self.calls.append({"url": url, "params": params})
        if params.get("list") == "categorymembers":
            node = self.tree.get(params["cmtitle"],
                                 {"pages": [], "subcats": []})
            key = "pages" if params.get("cmtype") == "page" else "subcats"
            val = node.get(key, [])
            cont = params.get("cmcontinue")
            if isinstance(val, list) and val and isinstance(val[0], list):
                idx = int(cont) if cont else 0
                chunk = val[idx] if idx < len(val) else []
                data = {"query": {"categorymembers": chunk}}
                if idx + 1 < len(val):
                    data["continue"] = {"cmcontinue": str(idx + 1)}
                return FakeResp(json_data=data)
            return FakeResp(json_data={"query": {"categorymembers": val}})
        if params.get("action") == "parse":
            return FakeResp(json_data=self.parses.get(str(params["pageid"]),
                                                    {}))
        return FakeResp(json_data={})


def _no_pace():
    return common.RateLimiter(0, sleep=lambda s: None)


def _entry(fid="sr:902", title="Два бора и јела", wiki="sr", slug="zenske",
           pageid="902"):
    return common.CatalogEntry(
        source_id=ws.SOURCE_ID, foreign_identifier=fid, title=title,
        url=f"https://{wiki}.wikisource.org/wiki/{title}", artist="x",
        creator="x", source_url=f"https://{wiki}.wikisource.org/wiki/{title}",
        license="LicenseRef-public-domain", license_url="", license_tier="pd",
        release_ok="yes", category=slug,
        meta={"wiki": wiki, "pageid": pageid, "page_title": title})


SR_WIKITEXT = _parse_fixture("mw_sr_parse_poem.json")["parse"]["wikitext"]

#: `{{стих|5}}` on its own line is a stanza marker -> after removal the
#: blank line is a real stanza boundary, so raw keeps the two blocks.
EXPECTED_SR_RAW = (
    "Два су бора напоредо расла,\n"
    "Међу њима танковрха јела;\n"
    "То не била два бора зелена,\n"
    "Ни међ’ њима танковрха јела,\n"
    "\n"
    "Већ то била два брата рођена:\n"
    "Једно Павле, а друго Радуле,\n"
    "Међу њима сестрица Јелица\n"
    "Браћа сеју врло миловала,\n"
    "Сваку су јој милост доносила,")

EXPECTED_SR_CLEAN = (
    "Dva su bora naporedo rasla,\n"
    "Medju njima tankovrha jela;\n"
    "To ne bila dva bora zelena,\n"
    "Ni medj’ njima tankovrha jela,\n"
    "\n"
    "Vec to bila dva brata rodjena:\n"
    "Jedno Pavle, a drugo Radule,\n"
    "Medju njima sestrica Jelica\n"
    "Braca seju vrlo milovala,\n"
    "Svaku su joj milost donosila,")


# ---------------------------------------------------------------------------
# Module contract + merged registry row
# ---------------------------------------------------------------------------


class TestContract:
    def test_module_shape(self):
        assert ws.SOURCE_ID == "wikisource_pd"
        assert callable(ws.iter_catalog)
        assert callable(ws.license_of)
        assert callable(ws.fetch_lyrics)

    def test_registry_row(self):
        row = registry.get("wikisource_pd")
        assert row["license_tier"] == "pd" and row["fetch_policy"] == "auto"
        assert row["adapter"] == "wikisource_pd"
        assert row["corpus_tag"] == "wikisource_pd"
        for slug in ("zenske", "epske", "lirske", "vuk-zbirke", "erlangen",
                     "ostalo", "folk-songs", "ballads", "traditional-ballads",
                     "song-books", "hymns", "poetry-collections"):
            assert slug in row["categories"]
        pol = row["politeness"]
        assert pol["min_interval_s"] >= 1.5 and pol["maxlag"] == 5

    def test_license_of_default(self):
        info = ws.license_of(_entry())
        assert info.license_tier == "pd" and info.release_ok == "yes"
        assert info.license == "LicenseRef-public-domain"


# ---------------------------------------------------------------------------
# Catalog traversal (fixtures, no network)
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_branch_assignment_and_continuation(self):
        sess = FakeWikiSession()
        entries = {e.foreign_identifier: e
                   for e in ws.iter_catalog(session=sess, limiter=_no_pace())}
        assert entries["sr:901"].category == "ostalo"
        assert entries["sr:902"].category == "zenske"
        assert entries["sr:905"].category == "zenske"   # cmcontinue page 2
        assert entries["sr:1602"].category == "ostalo"  # Караџићев циклус
        assert entries["sr:903"].category == "vuk-zbirke"
        assert entries["sr:904"].category == "erlangen"
        assert entries["en:7701"].category == "folk-songs"

    def test_entry_shape(self):
        e = next(iter(ws.iter_catalog(limit=1, session=FakeWikiSession(), limiter=_no_pace())))
        assert e.source_id == "wikisource_pd"
        assert e.license_tier == "pd" and e.release_ok == "yes"
        assert e.meta["wiki"] == "sr"
        assert e.source_url.startswith("https://sr.wikisource.org/wiki/")

    def test_limit_offset(self):
        s1, s2 = FakeWikiSession(), FakeWikiSession()
        all_e = list(ws.iter_catalog(session=s1, limiter=_no_pace()))
        assert len(list(ws.iter_catalog(limit=2, session=s2, limiter=_no_pace()))) == 2
        assert [e.foreign_identifier
                for e in ws.iter_catalog(offset=1, session=s2, limiter=_no_pace())] == \
            [e.foreign_identifier for e in all_e[1:]]

    def test_maxlag_sent(self):
        FakeWikiSession()  # ctor only
        sess = FakeWikiSession()
        list(ws.iter_catalog(limit=1, session=sess, limiter=_no_pace()))
        assert all(c["params"].get("maxlag") == "5" for c in sess.calls)


# ---------------------------------------------------------------------------
# License-template gate (SPEC §9)
# ---------------------------------------------------------------------------


class TestLicenseGate:
    def test_nonpd_template_drops(self):
        sess = FakeWikiSession(parses={
            "9901": _parse_fixture("mw_sr_parse_nonpd.json")})
        with pytest.raises(common.DropItem, match="non-pd-license"):
            ws.fetch_lyrics(_entry(fid="sr:9901", pageid="9901"),
                            session=sess, limiter=_no_pace())

    def test_ccbysa_downgrades_to_conditional(self):
        sess = FakeWikiSession(parses={
            "9902": _parse_fixture("mw_sr_parse_ccsa.json")})
        song = ws.fetch_lyrics(_entry(fid="sr:9902", pageid="9902"),
                               session=sess, limiter=_no_pace())
        assert song["license_tier"] == "cc-by-sa"
        assert song["release_ok"] == "conditional"
        assert song["license"] == "CC-BY-SA-4.0"

    def test_pd_template_and_absent_template_pass(self):
        sess = FakeWikiSession(
            parses={"902": _parse_fixture("mw_sr_parse_poem.json"),
                    "7701": _parse_fixture("mw_en_parse_ballad.json")})
        assert ws.fetch_lyrics(_entry(), session=sess, limiter=_no_pace())["license_tier"] == "pd"
        en = ws.fetch_lyrics(_entry(fid="en:7701", wiki="en", pageid="7701",
                                    title="The Riddles Wisely Expounded",
                                    slug="folk-songs"), session=sess, limiter=_no_pace())
        assert en["license_tier"] == "pd" and en["release_ok"] == "yes"

    def test_scan_function(self):
        assert ws.scan_license_templates(SR_WIKITEXT)[0] == "ok"
        v, _, off = ws.scan_license_templates("{{CC-BY-NC-4.0}}")
        assert v == "non-pd" and "CC-BY-NC" in off
        v, _, _ = ws.scan_license_templates("{{PD-US|1924}} {{header}}")
        assert v == "ok"
        v, _, _ = ws.scan_license_templates("{{CC-BY-SA-3.0}}")
        assert v == "conditional"


# ---------------------------------------------------------------------------
# Wikitext cleaning + normalization (F4: Cyrillic -> Latin + fold)
# ---------------------------------------------------------------------------


class TestCleaning:
    def test_wikitext_to_verse(self):
        assert ws.wikitext_to_verse(SR_WIKITEXT) == EXPECTED_SR_RAW

    def test_latin_fold(self):
        assert ws._latin(EXPECTED_SR_RAW) == EXPECTED_SR_CLEAN

    def test_container_templates_kept_others_dropped(self):
        out = ws.wikitext_to_verse(
            "{{Поезија|\nЈедан два три четири,\nпет шест седам осам,\n}}\n"
            "{{стих|5}}\nдевет десет једанаест,\nдванаест тринаест четрнаест,\nпетнаест.")
        assert "Један два три четири" in out
        assert "5" not in out.split("\n")[2]
        assert "{{" not in out

    def test_disambiguation_drops(self):
        sess = FakeWikiSession(
            parses={"7702": _parse_fixture("mw_en_parse_versions.json")})
        with pytest.raises(common.DropItem):
            ws.fetch_lyrics(_entry(fid="en:7702", wiki="en", pageid="7702",
                                   title="A Song", slug="folk-songs"),
                            session=sess, limiter=_no_pace())


# ---------------------------------------------------------------------------
# Full fetch_lyrics song schema + normalization (verbatim asserts)
# ---------------------------------------------------------------------------


class TestFetchSong:
    def test_sr_song_normalization_verbatim(self):
        sess = FakeWikiSession(
            parses={"902": _parse_fixture("mw_sr_parse_poem.json")})
        song = ws.fetch_lyrics(_entry(), session=sess, limiter=_no_pace())
        assert song["raw_lyrics"] == EXPECTED_SR_RAW       # Cyrillic kept
        assert song["clean_lyrics"] == EXPECTED_SR_CLEAN   # Latin + fold
        assert song["script"] == "cyrillic-original"
        assert song["language"] == "sr"
        assert song["artist"] == song["primary_artist"] == "Narodna pesma"
        assert song["corpus"] == song["source"] == "wikisource_pd"
        assert song["foreign_identifier"] == "sr:902"
        assert [s["label"] for s in song["sections"]] == \
            ["Strofa 1", "Strofa 2"]
        assert song["sections"][0]["content"].split("\n")[0] == \
            "Dva su bora naporedo rasla,"
        assert "cyrtranslit" in song["meta"]["normalization"]
        # frozen category landing slug kept
        assert song["category"] == "zenske"

    def test_en_song(self):
        sess = FakeWikiSession(
            parses={"7701": _parse_fixture("mw_en_parse_ballad.json")})
        song = ws.fetch_lyrics(
            _entry(fid="en:7701", wiki="en", pageid="7701",
                   title="The Riddles Wisely Expounded", slug="folk-songs"),
            session=sess, limiter=_no_pace())
        assert song["script"] == "latin" and song["language"] == "en"
        assert song["primary_artist"] == "Traditional"
        assert "There were three sisters" in song["clean_lyrics"]

    def test_strofa_label_parses_as_strofa(self):
        """Canonical-label contract: lyricsdb folds 'Strofa N' to kind
        'strofa' (NOT 'other') — asserted against the real parser."""
        p = _ldb.parse_section_label("Strofa 1")
        assert p.type == "strofa" and p.type_number == 1
        p2 = _ldb.parse_section_label("Strofa")
        assert p2.type == "strofa"


# ---------------------------------------------------------------------------
# Live smoke (excluded by default — @pytest.mark.slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestLiveSmoke:
    def test_live_sr_page(self):
        e = _entry(fid="sr:1602", pageid="1602",
                   title="Бог ником дужан не остаје")
        song = ws.fetch_lyrics(e)
        assert song["script"] == "cyrillic-original"
        assert song["clean_lyrics"] and song["raw_lyrics"]

    def test_live_catalog_first_entries(self):
        es = list(ws.iter_catalog(limit=2))
        assert len(es) == 2
