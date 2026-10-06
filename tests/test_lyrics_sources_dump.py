"""Wikisource XML-dump ingest tests — lyrics-sources P2, agent D1.

Covers ``sources/wikisource_dump.py`` (streaming parse, two-pass category
graph, candidate emission) and ``wikisource_dump_ingest.py`` (catalog/resume
semantics, song-JSON output) against the committed synthetic fixture
``tests/fixtures/lyrics_sources/wikisource_sample.xml`` — no network, no
real dump.

Key invariant: graph-derived membership. The poem page 902 links ONLY
``Категорија:Женске народне песме`` — a subcat of the Народне песме root —
so a name-match on the root would miss it; the pass-1 descendant set must
still claim it as ``zenske``.

sys.path shim per SPEC §7. No ``import toolshop``.
"""

from __future__ import annotations

import bz2
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = REPO_ROOT / "Genious_lyrics_extractor"
if str(EXTRACTOR) not in sys.path:
    sys.path.insert(0, str(EXTRACTOR))

import sources.wikisource_dump as wdump  # noqa: E402
import sources.wikisource_pd as ws  # noqa: E402
import wikisource_dump_ingest as ingest  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"
DUMP = FIXTURES / "wikisource_sample.xml"


def _corpus(tmp_path: Path) -> Path:
    return tmp_path / "lyrics" / "wikisource_pd"


def _catalog_counts(tmp_path: Path) -> dict:
    doc = json.loads(
        (_corpus(tmp_path) / "_catalog.json").read_text(encoding="utf-8"))
    out = {}
    for e in doc["entries"]:
        st = e.get("status") or "pending"
        out[st] = out.get(st, 0) + 1
    return out


# ---------------------------------------------------------------------------
# iter_dump_pages — streaming parse
# ---------------------------------------------------------------------------


class TestIterDumpPages:
    def test_pages_and_fields(self):
        pages = list(wdump.iter_dump_pages(DUMP))
        assert len(pages) == 14
        by_id = {p[1]: p for p in pages}
        ns, pid, title, wt = by_id["902"]
        assert ns == 0 and title == "Два бора и јела"
        assert "Два су бора напоредо расла" in wt
        assert by_id["5002"][0] == 14
        assert by_id["5002"][2] == "Категорија:Женске народне песме"
        # page id is the <page>/<id>, not the <revision>/<id>
        assert pid == "902"

    def test_bz2_roundtrip(self, tmp_path):
        packed = tmp_path / "sample.xml.bz2"
        packed.write_bytes(
            bz2.compress(DUMP.read_bytes()))
        pages = list(wdump.iter_dump_pages(packed))
        assert len(pages) == 14
        assert any(p[1] == "902" for p in pages)


# ---------------------------------------------------------------------------
# build_member_cats — pass-1 category graph
# ---------------------------------------------------------------------------


class TestMemberCats:
    def test_sr_descendant_set(self):
        mc = wdump.build_member_cats(DUMP, {"sr": ws.SR_ENTRY_POINTS})["sr"]
        # root itself
        assert mc["Категорија:Народне песме"] == "ostalo"
        # subcat reached ONLY via the graph (page->root parent link)
        assert mc["Категорија:Женске народне песме"] == "zenske"
        # Vuk book cat descends from the forced vuk-zbirke root
        assert mc["Категорија:Збирке Вука Стефановића Караџића"] == "vuk-zbirke"
        assert (mc["Категорија:Збирка народних песама Вук књига прва"]
                == "vuk-zbirke")
        # entry root with no ns-14 page in the dump still seeds itself
        assert mc["Категорија:Ерлангенски рукопис"] == "erlangen"
        # non-member cat is absent
        assert "Категорија:Усмена књижевност" not in mc

    def test_en_descendant_set(self):
        mc = wdump.build_member_cats(DUMP, {"en": ws.EN_CATEGORIES})["en"]
        assert mc["Category:Folk songs"] == "folk-songs"
        assert len(mc) == len(ws.EN_CATEGORIES)  # roots only, no subcats


# ---------------------------------------------------------------------------
# iter_dump_candidates — pass-2 ns-0 emission
# ---------------------------------------------------------------------------


class TestCandidates:
    def _sr(self):
        mc = wdump.build_member_cats(DUMP, {"sr": ws.SR_ENTRY_POINTS})["sr"]
        return {c.foreign_identifier: c
                for c in wdump.iter_dump_candidates(DUMP, "sr", mc)}

    def test_candidate_set_and_branches(self):
        cands = self._sr()
        # subcat member reached via graph — NOT by name match on the root
        assert cands["sr:902"].category == "zenske"
        assert cands["sr:903"].category == "vuk-zbirke"
        for fid in ("sr:9901", "sr:9902", "sr:9903", "sr:9904"):
            assert fid in cands  # license/shape verdicts happen downstream
        # non-member page never becomes a candidate
        assert "sr:9999" not in cands
        # en page is invisible to the sr member set
        assert "en:7701" not in cands
        assert set(cands) == {"sr:902", "sr:903", "sr:9901", "sr:9902",
                              "sr:9903", "sr:9904"}

    def test_candidate_shape(self):
        c = self._sr()["sr:902"]
        assert c.source_id == "wikisource_pd"
        assert c.license_tier == "pd" and c.release_ok == "yes"
        assert c.license == "LicenseRef-public-domain"
        assert c.meta["wiki"] == "sr" and c.meta["pageid"] == "902"
        assert c.meta["via"] == "dump"
        assert c.meta["member_cat"] == "Категорија:Женске народне песме"
        assert c.source_url.startswith("https://sr.wikisource.org/wiki/")
        # transient wikitext rides _wt and is NOT in serializable meta
        assert "Два су бора" in getattr(c, "_wt")
        assert "_wt" not in c.meta and "_wt" not in c.to_dict()["meta"]

    def test_en_candidate(self):
        mc = wdump.build_member_cats(DUMP, {"en": ws.EN_CATEGORIES})["en"]
        cands = {c.foreign_identifier: c
                 for c in wdump.iter_dump_candidates(DUMP, "en", mc)}
        assert set(cands) == {"en:7701"}
        assert cands["en:7701"].category == "folk-songs"
        assert cands["en:7701"].artist == "Traditional"


# ---------------------------------------------------------------------------
# wikisource_dump_ingest.run — catalog, verdicts, resume
# ---------------------------------------------------------------------------


class TestIngest:
    def test_sr_emit_drop_conditional(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        rc = ingest.run(str(DUMP), "sr")
        assert rc == 0
        assert _catalog_counts(tmp_path) == {"fetched": 3, "dropped": 3}
        corpus = _corpus(tmp_path)

        # -- emit: PD Cyrillic poem via SUBCAT membership -------------------
        zenske = sorted((corpus / "zenske").glob("*.json"))
        by_fid = {json.loads(p.read_text(encoding="utf-8"))
                  ["foreign_identifier"]: p for p in zenske}
        song = json.loads(by_fid["sr:902"].read_text(encoding="utf-8"))
        assert song["raw_lyrics"].split("\n")[0] == \
            "Два су бора напоредо расла,"           # Cyrillic kept raw
        assert song["clean_lyrics"].split("\n")[0] == \
            "Dva su bora naporedo rasla,"          # Latin + diacritic fold
        assert song["script"] == "cyrillic-original"
        assert song["language"] == "sr"
        assert [s["label"] for s in song["sections"]] == \
            ["Strofa 1", "Strofa 2"]
        assert song["corpus"] == song["source"] == "wikisource_pd"
        assert song["meta"]["via"] == "dump"
        assert song["meta"]["member_cat"] == \
            "Категорија:Женске народне песме"
        assert song["license_tier"] == "pd" and song["release_ok"] == "yes"
        txt = by_fid["sr:902"].with_suffix(".txt")
        assert txt.read_text(encoding="utf-8").startswith("Dva su bora")

        # -- emit: Vuk book-cat member --------------------------------------
        vuk = sorted((corpus / "vuk-zbirke").glob("*.json"))
        vuk_song = json.loads(vuk[0].read_text(encoding="utf-8"))
        assert vuk_song["foreign_identifier"] == "sr:903"
        assert vuk_song["category"] == "vuk-zbirke"

        # -- conditional: CC-BY-SA ------------------------------------------
        cond = next(json.loads(p.read_text(encoding="utf-8"))
                    for p in zenske
                    if json.loads(p.read_text(encoding="utf-8"))
                    ["foreign_identifier"] == "sr:9904")
        assert cond["license"] == "CC-BY-SA-4.0"
        assert cond["license_tier"] == "cc-by-sa"
        assert cond["release_ok"] == "conditional"

        # -- drops recorded with reasons in _catalog.json --------------------
        cat = json.loads((corpus / "_catalog.json").read_text(encoding="utf-8"))
        drops = {e["foreign_identifier"]: e["drop_reason"]
                 for e in cat["entries"] if e["status"] == "dropped"}
        assert drops["sr:9901"].startswith("non-pd-license-template")
        assert drops["sr:9902"] == "toc-or-index-page"
        assert drops["sr:9903"].startswith("too-short")
        # non-member page never entered the catalog at all
        assert "sr:9999" not in {e["foreign_identifier"]
                                 for e in cat["entries"]}

    def test_en_emit(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        rc = ingest.run(str(DUMP), "en")
        assert rc == 0
        assert _catalog_counts(tmp_path) == {"fetched": 1}
        songs = list((_corpus(tmp_path) / "folk-songs").glob("*.json"))
        assert len(songs) == 1
        song = json.loads(songs[0].read_text(encoding="utf-8"))
        assert song["foreign_identifier"] == "en:7701"
        assert song["language"] == "en" and song["script"] == "latin"
        assert song["primary_artist"] == "Traditional"
        assert "There were three sisters" in song["clean_lyrics"]
        assert song["meta"]["via"] == "dump"

    def test_resume_skips_terminal(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        assert ingest.run(str(DUMP), "sr") == 0
        capsys.readouterr()
        assert ingest.run(str(DUMP), "sr", resume=True) == 0
        out = capsys.readouterr().out
        assert "'terminal_skipped': 6" in out
        assert "'fetched': 0" in out
        assert _catalog_counts(tmp_path) == {"fetched": 3, "dropped": 3}

    def test_limit_offset(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        assert ingest.run(str(DUMP), "sr", limit=2, offset=1) == 0
        counts = _catalog_counts(tmp_path)
        assert counts.get("fetched", 0) + counts.get("dropped", 0) == 2

    def test_dump_song_matches_api_shape(self, tmp_path, monkeypatch):
        """Song parity: dump emit == _song_from_wikitext output + via/member."""
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        mc = wdump.build_member_cats(DUMP, {"sr": ws.SR_ENTRY_POINTS})["sr"]
        cand = next(c for c in wdump.iter_dump_candidates(DUMP, "sr", mc)
                    if c.foreign_identifier == "sr:902")
        api_song = ws._song_from_wikitext(cand, cand._wt, parsed_title=None)

        assert ingest.run(str(DUMP), "sr") == 0
        corpus = _corpus(tmp_path)
        dump_song = next(
            json.loads(p.read_text(encoding="utf-8"))
            for p in (corpus / "zenske").glob("*.json")
            if json.loads(p.read_text(encoding="utf-8"))
            ["foreign_identifier"] == "sr:902")
        # normalise_song (inside write_song_json) adds only the two
        # sync-field defaults on top of the builder output
        extra = set(dump_song) - set(api_song)
        assert extra == {"synced_lyrics", "lyricsfile"}
        assert dump_song["synced_lyrics"] is None
        assert dump_song["lyricsfile"] is None
        for k, v in api_song.items():
            if k == "meta":
                continue
            assert dump_song[k] == v, k
        extra = set(dump_song["meta"]) - set(api_song["meta"])
        assert extra == {"via", "member_cat"}
        for k, v in api_song["meta"].items():
            assert dump_song["meta"][k] == v, k


# ---------------------------------------------------------------------------
# Constant-memory sanity — the generator never materializes the page list
# ---------------------------------------------------------------------------


class TestStreaming:
    def test_iter_is_lazy(self):
        import types
        assert isinstance(wdump.iter_dump_pages(DUMP), types.GeneratorType)
        it = wdump.iter_dump_pages(DUMP)
        first = next(it)
        assert first[0] == 14  # first page in the fixture is a category
