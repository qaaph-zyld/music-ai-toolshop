"""Gutenberg PD adapter tests — lyrics-sources wave A, agent I3.

Covers ``sources/gutenberg_pd.py``: catalog-first behavior over the
curated WORKS table, sanctioned-mirror URL construction
(aleph.gutenberg.org directory listings only — no /ebooks/ or /files/
crawl), PG header/footer slicing, per-work back-matter cut points, the
three splitters (sotw / child / caps), and offline-catalog merging.

All network-shaped paths are served by fakes or a pre-seeded ``_src``
text cache under a tmp TOOLSHOP_DATA_DIR — no live hits except the
@pytest.mark.slow block.
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

import sources.gutenberg_pd as gb  # noqa: E402
import sources.registry as registry  # noqa: E402
from sources import _common as common  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lyrics_sources"

_LDB_SPEC = importlib.util.spec_from_file_location(
    "lyricsdb_standalone_gb", REPO_ROOT / "toolshop" / "lyricsdb.py")
_ldb = importlib.util.module_from_spec(_LDB_SPEC)
sys.modules["lyricsdb_standalone_gb"] = _ldb  # dataclasses need sys.modules
_LDB_SPEC.loader.exec_module(_ldb)


class FakeResp:
    def __init__(self, text="", json_data=None):
        self.text = text
        self._json = json_data
        self.status_code = 200
        self.headers = {}
        self.content = text.encode("utf-8")

    def json(self):
        return self._json if self._json is not None else json.loads(self.text)

    def raise_for_status(self):
        pass


class FakeAlephSession:
    """Directory-listing + text-file fakes keyed by URL."""

    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(url)
        body = self.mapping.get(url, "")
        return FakeResp(text=body)


def _no_pace():
    return common.RateLimiter(0, sleep=lambda s: None)


def _seed(tmp_path, ebook, fixture_name):
    root = tmp_path / "lyrics" / "gutenberg_pd" / "_src"
    root.mkdir(parents=True, exist_ok=True)
    (root / f"pg{ebook}.txt").write_text(
        (FIXTURES / fixture_name).read_text(encoding="utf-8"),
        encoding="utf-8")


# ---------------------------------------------------------------------------
# Contract + registry row
# ---------------------------------------------------------------------------


class TestContract:
    def test_module_shape(self):
        assert gb.SOURCE_ID == "gutenberg_pd"
        assert callable(gb.iter_catalog) and callable(gb.license_of)
        assert callable(gb.fetch_lyrics)

    def test_registry_row(self):
        row = registry.get("gutenberg_pd")
        assert row["license_tier"] == "pd" and row["fetch_policy"] == "auto"
        assert row["corpus_tag"] == "gutenberg_pd"
        assert {"child-ballads", "songs-of-the-west", "elizabethan",
                "yorkshire", "misc"} <= set(row["categories"])

    def test_license_of_default(self):
        e = common.CatalogEntry(source_id="gutenberg_pd",
                                foreign_identifier="pg1:0")
        info = gb.license_of(e)
        assert info.license_tier == "pd" and info.release_ok == "yes"
        assert info.license == "LicenseRef-public-domain"


# ---------------------------------------------------------------------------
# Sanctioned-mirror retrieval (no /ebooks/, no /files/)
# ---------------------------------------------------------------------------


class TestSanctionedRetrieval:
    def test_aleph_dir_layout(self):
        assert gb._aleph_dir(56625) == \
            "https://aleph.gutenberg.org/5/6/6/2/56625/"
        assert gb._aleph_dir(2831) == \
            "https://aleph.gutenberg.org/2/8/3/2831/"

    def test_txt_candidate_preference(self):
        html = ('<a href="56625-h.zip">z</a> <a href="56625-0.txt">o</a> '
                '<a href="56625-8.txt">8</a> <a href="other.txt">x</a>')
        assert gb._txt_candidates(html, 56625)[0] == "56625-8.txt"

    def test_no_human_facing_urls_in_module(self):
        """Text retrieval goes only through the sanctioned aleph mirror —
        www.gutenberg.org/ebooks/<n> is emitted as source_url metadata only,
        never passed to polite_get; no /files/ crawl URLs exist."""
        src = (EXTRACTOR / "sources" / "gutenberg_pd.py") \
            .read_text(encoding="utf-8")
        assert "polite_get(GUTENBERG_EBOOK_URL" not in src
        assert "/files/" not in src
        assert "aleph.gutenberg.org" in src
        # every polite_get call site targets the aleph mirror dir
        for line in src.split("\n"):
            if "polite_get(" in line and "def polite_get" not in line:
                assert "aleph" in line.lower() or "_aleph_dir" in line

    def test_ensure_text_uses_mirror_listing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        mapping = {
            gb._aleph_dir(56625): '<a href="56625-8.txt">t</a>',
            gb._aleph_dir(56625) + "56625-8.txt":
                (FIXTURES / "pg_56625_excerpt.txt").read_text("utf-8"),
        }
        sess = FakeAlephSession(mapping)
        p = gb._ensure_text(56625, session=sess, limiter=_no_pace())
        assert p.exists() and p.stat().st_size > 0
        # directory listing fetched, then the -8.txt member — and nothing
        # on www.gutenberg.org/ebooks or /files/
        assert sess.calls[0].endswith("/56625/")
        assert all("aleph.gutenberg.org" in c for c in sess.calls)
        assert all("/ebooks/" not in c and "/files/" not in c
                   for c in sess.calls)
        # cache hit on second call -> no new request
        gb._ensure_text(56625, session=sess, limiter=_no_pace())
        assert len(sess.calls) == 2


# ---------------------------------------------------------------------------
# Region slicing + splitters (fixture excerpts, PD content)
# ---------------------------------------------------------------------------


class TestSplitting:
    def _work(self, ebook):
        return gb._WORK_BY_EBOOK[ebook]

    def test_sotw_split(self):
        text = (FIXTURES / "pg_56625_excerpt.txt").read_text("utf-8")
        songs = gb.split_songs(text, self._work(56625))
        titles = [t for t, _ in songs]
        assert titles == ["By Chance It Was", "The Test Song"]
        _t, blocks = songs[0]
        assert [b["label"] for b in gb._stanzas(blocks, True)] == \
            ["Strofa 1", "Strofa 2"]
        first = blocks[0]
        assert first[0].strip() == "1"          # printed stanza number
        assert "By chance it was I met my love;" in "\n".join(first)
        # arranger/[Music] apparatus never enters a stanza
        assert not any("Music" in l or "Arranged" in l
                       for _, bl in songs for l in sum(bl, []))
        # NOTES ON THE SONGS terminates the lyric region
        blob = "\n".join(t + " " + str(b) for t, b in songs)
        assert "Woodrich" not in blob and "blacksmith" not in blob

    def test_child_split_variants(self):
        text = (FIXTURES / "pg_44969_excerpt.txt").read_text("utf-8")
        songs = gb.split_songs(text, self._work(44969))
        titles = [t for t, _ in songs]
        assert titles == ["Riddles Wisely Expounded [A]",
                          "Riddles Wisely Expounded [B]"]
        a_blocks = songs[0][1]
        assert len(a_blocks) == 2                 # stanzas 1 and 2
        flat = "\n".join(l for b in a_blocks for l in b)
        assert "There were three sisters" in flat
        assert "Broadwood" not in flat            # apparatus skipped
        b_flat = "\n".join(l for b in songs[1][1] for l in b)
        assert "bonny broom" in b_flat

    def test_caps_split(self):
        text = (FIXTURES / "pg_27129_excerpt.txt").read_text("utf-8")
        songs = gb.split_songs(text, self._work(27129))
        titles = [t for t, _ in songs]
        assert "Come, Live With Me And Be My Love" in titles
        assert "There Is A Lady Sweet And Kind" in titles
        assert len(songs) == 2                    # CONTENTS rows not songs
        first = songs[0][1]
        assert "Come live with me" in "\n".join(sum(first, []))

    def test_slice_region_strips_boilerplate(self):
        text = (FIXTURES / "pg_56625_excerpt.txt").read_text("utf-8")
        body = gb._slice_region(text)
        assert "use of anyone anywhere" not in body
        assert "End of the Project Gutenberg" not in body
        assert "SONGS OF THE WEST" in body

    def test_strofa_labels_parse(self):
        for lab in ("Strofa 1", "Strofa 12"):
            p = _ldb.parse_section_label(lab)
            assert p.type == "strofa"


# ---------------------------------------------------------------------------
# iter_catalog + fetch_lyrics over a seeded _src cache
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_iter_catalog_seeded(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        _seed(tmp_path, 56625, "pg_56625_excerpt.txt")
        # narrow WORKS to the seeded ebook so no other network is needed
        monkeypatch.setattr(gb, "WORKS",
                            (gb._WORK_BY_EBOOK[56625],))
        monkeypatch.setattr(gb, "_WORK_BY_EBOOK",
                            {56625: gb._WORK_BY_EBOOK[56625]})
        entries = list(gb.iter_catalog(limiter=_no_pace()))
        assert [e.foreign_identifier for e in entries] == \
            ["pg56625:0", "pg56625:1"]
        e = entries[0]
        assert e.category == "songs-of-the-west"
        assert e.artist == "Traditional" and e.license_tier == "pd"
        assert e.source_url == "https://www.gutenberg.org/ebooks/56625"
        assert e.meta["ebook"] == 56625 and e.meta["song_idx"] == 0

    def test_fetch_lyrics_seeded(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        _seed(tmp_path, 56625, "pg_56625_excerpt.txt")
        e = common.CatalogEntry(
            source_id="gutenberg_pd", foreign_identifier="pg56625:0",
            title="By Chance It Was", artist="Traditional",
            source_url="https://www.gutenberg.org/ebooks/56625",
            license="LicenseRef-public-domain", license_tier="pd",
            release_ok="yes", category="songs-of-the-west",
            meta={"ebook": 56625, "work_key": "songs-of-the-west",
                  "song_idx": 0})
        song = gb.fetch_lyrics(e, limiter=_no_pace())
        assert song["title"] == "By Chance It Was"
        assert song["corpus"] == song["source"] == "gutenberg_pd"
        assert song["language"] == "en" and song["script"] == "latin"
        assert song["primary_artist"] == "Traditional"
        assert song["release_ok"] == "yes" and song["license_tier"] == "pd"
        assert "By chance it was I met my love;" in song["clean_lyrics"]
        assert [s["label"] for s in song["sections"]] == \
            ["Strofa 1", "Strofa 2"]
        assert song["meta"]["ebook"] == 56625
        assert "aleph.gutenberg.org" in song["meta"]["mirror"]

    def test_offline_catalog_merge(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        src = tmp_path / "lyrics" / "gutenberg_pd" / "_src"
        src.mkdir(parents=True)
        (src / "pg_catalog.json").write_text(json.dumps(
            {"works": [{"ebook": 99999, "key": "x", "title": "X Songs",
                        "category": "misc", "kind": "caps"}]}),
            encoding="utf-8")
        (src / "pg99999.txt").write_text(
            (FIXTURES / "pg_27129_excerpt.txt").read_text("utf-8"),
            encoding="utf-8")
        monkeypatch.setattr(gb, "WORKS", ())
        entries = list(gb.iter_catalog(limiter=_no_pace()))
        assert entries and all(e.meta["ebook"] == 99999 for e in entries)


# ---------------------------------------------------------------------------
# Live smoke — @pytest.mark.slow
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestLiveSmoke:
    def test_live_aleph_56625(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        p = gb._ensure_text(56625)
        assert p.stat().st_size > 100_000
