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
# wave p2_b G-fix: splitters for the six previously-empty works
# (child vols II–V, songs-of-the-west, bundle-of-ballads).
# All fixtures are hand-crafted — no real corpus text is committed.
# ---------------------------------------------------------------------------


def _pg(body: str) -> str:
    return ("*** START OF THE PROJECT GUTENBERG EBOOK 1 ***\n"
            + body
            + "\n*** END OF THE PROJECT GUTENBERG EBOOK 1 ***\n")


_CHILD = {"kind": "child", "category": "child-ballads"}
_SOTW = {"kind": "sotw", "category": "songs-of-the-west"}
_CAPS_PL = {"kind": "caps", "category": "misc",
            "flush_left_heads": True, "caps_paren": True}


class TestChildVolsCoverage:
    """Child vols II–V: first ballad >40, unlettered texts, =X.=/#X.#
    variant marks, APPENDIX/ADDITIONS-AND-CORRECTIONS supplements."""

    def test_first_ballad_may_exceed_last_plus_40(self):
        """Vol. II opens at ballad 54 — the +40 lookahead window must only
        apply to *subsequent* ballads (PG47692 layout)."""
        body = """
54

THE SYNTHETIC BALLAD TITLE

        #A.# 'Fake Source,' Imaginary Book, p. 1.

Prose commentary about the synthetic ballad and its history.

* * *

A

        Source line for variant A.

    1

    First synthetic verse line,
      second synthetic verse line,
    third line of the verse,
      fourth line of the verse.

    2

    More synthetic verse here,
      continuing the stanza,
    and a third line now,
      finishing the verse.
"""
        songs = gb.split_songs(_pg(body), _CHILD)
        titles = [t for t, _ in songs]
        assert titles == ["The Synthetic Ballad Title [A]"]
        assert len(songs[0][1]) == 2

    def test_unlettered_text_after_star_rule(self):
        """'HOBIE NOBLE' style: single text, no variant letter, text begins
        right after the '* * *' commentary rule (PG63116)."""
        body = """
190

JAMIE-LIKE BALLAD

  Citation source, Imaginary Book, p. 3.

Commentary paragraph about this ballad.

* * *

  1

  Verse line one here,
    indented second line,
  verse line three here,
    indented fourth line.

  2

  Second stanza begins,
    with more verse,
  third line follows now,
    fourth line ends it.
"""
        songs = gb.split_songs(_pg(body), _CHILD)
        assert [t for t, _ in songs] == ["Jamie-Like Ballad"]
        assert len(songs[0][1]) == 2

    def test_unlettered_text_without_star_rule(self):
        """'CAPTAIN WARD' style (vol. V): unlettered main text not preceded
        by a '* * *' rule — accepted because no variant head follows."""
        body = """
287

WARD-LIKE BALLAD

Long commentary paragraph that runs for a while without any rule line
or variant letter and then gives the whole text immediately below.

    1

    Strike-like verse the first,
      with a second line,
    third line of the stanza,
      fourth line closes it.

    2

    Second stanza opens here,
      with another line,
    third line of the stanza,
      fourth line closes it.
"""
        songs = gb.split_songs(_pg(body), _CHILD)
        assert [t for t, _ in songs] == ["Ward-Like Ballad"]

    def test_quoted_stanza_in_commentary_rejected(self):
        """'BONNY BEE HOM' style: a stanza quoted inside the commentary is
        followed soon by the real 'A' head — must not open an unlettered
        text (PG47692)."""
        body = """
92

BALLAD WITH QUOTE

Citation paragraph mentioning a related piece which runs thus:

    1

    Quoted stanza line one,
      quoted stanza line two,
    quoted stanza line three,
      quoted stanza line four.

A

        Source of variant A.

    1

    Real variant verse here,
      second line of verse,
    third line of the verse,
      fourth line ends stanza.
"""
        songs = gb.split_songs(_pg(body), _CHILD)
        assert [t for t, _ in songs] == ["Ballad With Quote [A]"]

    def test_decorated_variant_marks_guarded(self):
        """Vol. V '=C.=' variant heads; '=A.=' before variant-reading notes
        is a notes-section head and must not open a variant (PG71104)."""
        body = """
267

HEIR-LIKE BALLAD

* * *

A

  1

  Variant a verse line,
    second line now,
  third line of verse,
    fourth line ends.

B

  1

  Variant b verse line,
    second line now,
  third line of verse,
    fourth line ends.

=A.=

 5^1. variant reading note.
 7^1. another note here.

=C.=

 The editor comment about the source goes here.

    1

    Variant c verse line,
      second line now,
    third line of verse,
      fourth line ends.
"""
        songs = gb.split_songs(_pg(body), _CHILD)
        titles = [t for t, _ in songs]
        assert "Heir-Like Ballad [A]" in titles
        assert "Heir-Like Ballad [B]" in titles
        assert "Heir-Like Ballad [C]" in titles
        # the '=A.=' notes head did not open a second '[A]' variant
        assert titles.count("Heir-Like Ballad [A]") == 1

    def test_appendix_pieces_then_next_ballad(self):
        """Per-ballad APPENDIX (PG47692 ballad 61): CAPS piece heads inside
        are songs of their own; the next numbered heading resumes ballads."""
        body = """
61

SIR-LIKE BALLAD

* * *

A

  1

  Main text verse line,
    second line now,
  third line of verse,
    fourth line ends.

APPENDIX

Commentary on the appendix piece that follows below.

SIR TESTLING

        Imaginary MS., fol. 5b.

    1

    Appendix verse line one,
      line two now,
    line three of it,
      line four ends.

62

NEXT BALLAD

* * *

A

  1

  Next ballad verse,
    second line now,
  third line of it,
      fourth line ends.
"""
        songs = gb.split_songs(_pg(body), _CHILD)
        titles = [t for t, _ in songs]
        assert "Sir-Like Ballad [A]" in titles
        assert "Sir Testling" in titles
        assert "Next Ballad [A]" in titles

    def test_additions_corrections_embeds_versions(self):
        """ADDITIONS AND CORRECTIONS (PG62474): full versions printed in
        the correction section are captured; citation heads are not."""
        body = """
85

LADY-LIKE BALLAD

* * *

A

  1

  Main text verse line,
    second line now,
  third line of verse,
    fourth line ends.

ADDITIONS AND CORRECTIONS

VOL. I.

P. 276. In an imaginary journal there is a copy taken from singing.

GILES-LIKE COLLINS AND LADY-LIKE

  1

  Version verse line one,
    second line now,
  third line of verse,
    fourth line ends.

II, 28.

G. L. K.
"""
        songs = gb.split_songs(_pg(body), _CHILD)
        titles = [t for t, _ in songs]
        assert "Lady-Like Ballad [A]" in titles
        assert "Giles-Like Collins And Lady-Like" in titles
        assert not any(t.startswith(("Vol", "Ii", "G. L", "P."))
                       for t in titles)


class TestSotwCoverage:
    def test_toc_end_head_row_does_not_truncate(self):
        """PG56625's CONTENTS lists 'NOTES ON THE SONGS.' verbatim before
        the first 'No. N' heading — must not end the lyric region."""
        body = """
CONTENTS

    1. FIRST SONG TITLE.
    NOTES ON THE SONGS.

PREFACE--INTRODUCTION.

No. 1 BY SYNTHETIC CHANCE

  1

  By chance it was a line,
    second line now,
  third line of the song,
    fourth line ends.

  2

  Second stanza opens,
    second line now,
  third line of the song,
    fourth line ends.

No. 2 SECOND SONG TITLE

  1

  Another song begins,
    second line now,
  third line of the song,
    fourth line ends.

NOTES ON THE SONGS

  Back-matter notes go here and they must stop the region.
"""
        songs = gb.split_songs(_pg(body), _SOTW)
        assert [t for t, _ in songs] == \
            ["By Synthetic Chance", "Second Song Title"]


class TestCapsFlagsCoverage:
    """PG2831 bundle-of-ballads: TOC 'GLOSSARY' row, flush-left headings,
    parenthesised qualifier, indented refrain lines."""

    def test_toc_glossary_row_and_real_glossary(self):
        body = """
CONTENTS.

     GLOSSARY

INTRODUCTION BY THE EDITOR.

FIRST TEST BALLAD.

     Verse line one here,
       second line indented,
     third line of the verse,
       fourth line ends it.

GLOSSARY.

     Back-matter glossary line that must not be a song.
"""
        songs = gb.split_songs(_pg(body), _CAPS_PL)
        assert [t for t, _ in songs] == ["First Test Ballad"]

    def test_paren_qualifier_heading(self):
        body = """
CHEVY-LIKE CHASE (the later version.)

     God prosper long the line,
       our lives and safeties all!
     A woeful hunting once did,
       in chase-like hills befall.

     To drive the deer with hounds,
       the earl-like took the way;
     the child may rue that is,
       the hunting of that day!
"""
        songs = gb.split_songs(_pg(body), _CAPS_PL)
        assert [t for t, _ in songs] == \
            ["Chevy-Like Chase (The Later Version)"]

    def test_indented_caps_refrain_stays_verse(self):
        """'UNWORTHY BARBARA ALLEN.' style: an indented all-caps refrain is
        verse, not a heading — the song is not split apart."""
        body = """
BARBARA-LIKE BALLAD.

     As she was walking on,
       she heard the bell a ring;
     and every stroke did seem,
       REFRAIN-LIKE CAPS THING.

     She turned her body round,
       and spied the corpse a late;
     whilst all her friends cried,
       REFRAIN-LIKE CAPS THING.
"""
        songs = gb.split_songs(_pg(body), _CAPS_PL)
        assert [t for t, _ in songs] == ["Barbara-Like Ballad"]
        flat = "\n".join(l for b in songs[0][1] for l in b)
        assert "REFRAIN-LIKE CAPS THING" in flat

    def test_part_heads_continue_parent_song(self):
        """'SECOND FYTTE.'/'PART THE SECOND.' divide one long ballad —
        they continue the parent song rather than opening anonymous
        fragments (pg2831 ADAM BELL; pg7535 THE HEIR OF LINNE)."""
        body = """
ADAM-LIKE BALLAD.

     Verse line one of part,
       second line goes here,
     third line of the verse,
       fourth line closes it.

SECOND FYTTE.

     Second fytte opens now,
       second line goes here,
     third line of the verse,
       fourth line closes it.

     FIRST PART.

     A part-head may be indented;
       it still is no verse line,
     third line of the verse,
       fourth line closes it.
"""
        songs = gb.split_songs(_pg(body), _CAPS_PL)
        assert [t for t, _ in songs] == ["Adam-Like Ballad"]
        flat = "\n".join(l for b in songs[0][1] for l in b)
        assert "SECOND FYTTE" not in flat
        assert "FIRST PART" not in flat
        assert "Second fytte opens now" in flat


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
