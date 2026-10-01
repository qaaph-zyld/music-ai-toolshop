"""atlas + comparisons on a hand-built mini corpus (fixture lines only, no real lyrics).

Both modules may only ever output statistics or single words: every test that
reads their blobs or printed output asserts that no corpus line text leaks.
"""

import builtins
import math
import os
import shutil
import sqlite3
import statistics
from collections import Counter

import pytest
from conftest import SCHEMA
from toolshop.syllables import count_line

from mairina import atlas, cli, comparisons, corpus, devices, rank
from mairina.used import tokenize

# word -> (lemma, upos)
LEX = {w: (l, u) for w, l, u in [
    ("usne", "usna", "NOUN"), ("crvene", "crven", "ADJ"), ("ko", "ko", "PRON"),
    ("lava", "lava", "NOUN"), ("pitaj", "pitati", "VERB"), ("je", "biti", "AUX"),
    ("gazda", "gazda", "NOUN"), ("hladna", "hladan", "ADJ"), ("led", "led", "NOUN"),
    ("tiho", "tiho", "ADV"), ("kao", "kao", "SCONJ"), ("da", "da", "SCONJ"),
    ("spava", "spavati", "VERB"), ("lep", "lep", "ADJ"), ("san", "san", "NOUN"),
    ("i", "i", "CCONJ"), ("miran", "miran", "ADJ"), ("poput", "poput", "ADP"),
    ("vode", "voda", "NOUN"), ("ostra", "ostar", "ADJ"), ("me", "ja", "PRON"),
    ("noz", "noz", "NOUN"), ("jak", "jak", "ADJ"), ("devito", "devito", "PROPN"),
    ("laku", "lak", "ADJ"), ("noc", "noc", "NOUN"), ("majko", "majka", "NOUN"),
    ("brate", "brat", "NOUN"), ("zid", "zid", "NOUN"), ("svetla", "svetao", "ADJ"),
    ("zvezda", "zvezda", "NOUN"), ("thelion", "thelion", "NOUN"),
    ("wanders", "wander", "VERB"), ("lamb", "lamb", "NOUN")]}

SONG1_VERSE = [
    "usne crvene ko lava",            # simile: ko + noun
    "pitaj ko je gazda",              # 'ko' = who: not a simile
    "hladna ko led",
    "tiho kao da spava",              # 'kao da' = conjunction: low confidence
    "lep kao san i miran poput vode",
    "ostra ko me noz",                # clitic between the marker and the noun
    "jak ko devito",                  # artist name: never a comparison word
    "usne crvene ko lava",            # refrain repeated in the same song: counts once
    "laku noc majko",                 # anaphora pair
    "laku noc brate",
    "noc je jak kao zid",             # the only simile line that mentions 'noc'
]
SONG1_FILLER = ["lava noc", "san led"] * 12          # consecutive lines share no opening
# (song id, cohort, target_artist, primary_artist, corpus, [(section type, lines)])
SONGS = [
    (1, "drill_trap", "devito", "Devito", "genius-pro",
     [("strofa", SONG1_VERSE), ("strofa", SONG1_FILLER)]),
    (2, "pop", "jala", "Jala", "genius-pro",
     [("strofa", ["svetla kao zvezda", "svetla kao zvezda", "hladna ko led"])]),
    (3, "drill_trap", "devito", "Devito", "genius-pro", [("strofa", ["usne crvene ko lava"])]),
    (4, None, "rasta", "Rasta", "genius-pro", [("strofa", ["svetla kao zvezda"])]),
    (5, "pop", "englishbard", "English Bard", "gutenberg_pd",
     [("strofa", ["thelion wanders kao lamb"])]),
]
ALL_TEXTS = [t for *_s, secs in SONGS for _ty, lines in secs for t in lines]
LONG_TEXTS = sorted({t for t in ALL_TEXTS if len(t.split()) >= 3})
DRILL_LINES = SONG1_VERSE + SONG1_FILLER + ["usne crvene ko lava"]


def build_mini(path):
    con = sqlite3.connect(str(path))
    con.executescript(SCHEMA)
    n = {"sec": 0, "line": 0, "tok": 0}
    for sid, cohort, target, primary, corp, sections in SONGS:
        con.execute("INSERT INTO songs VALUES (?,?,?,?,?,?)",
                    (sid, f"song{sid}", primary, target, cohort, corp))
        for stype, lines in sections:
            n["sec"] += 1
            con.execute("INSERT INTO sections VALUES (?,?,?,?)", (n["sec"], sid, n["sec"], stype))
            for ordinal, text in enumerate(lines, 1):
                n["line"] += 1
                con.execute("INSERT INTO lines VALUES (?,?,?,?,?,?,?)",
                            (n["line"], n["sec"], ordinal, text, text.lower(),
                             len(text.split()), count_line(text)))
                for i, form in enumerate(text.split()):
                    lemma, upos = LEX[form]
                    n["tok"] += 1
                    con.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?)",
                                (n["tok"], n["line"], i, form, lemma, upos, None, 0, "latin"))
    con.commit()
    con.close()
    return path


@pytest.fixture(scope="module")
def mini_db(tmp_path_factory):
    return build_mini(tmp_path_factory.mktemp("mini") / "lyrics.db")


@pytest.fixture(scope="module")
def mini_index(mini_db, tmp_path_factory):
    return corpus.load_index(mini_db, tmp_path_factory.mktemp("mini_cache"))


@pytest.fixture(scope="module")
def mini_atlas(mini_db, tmp_path_factory):
    return atlas.load(mini_db, tmp_path_factory.mktemp("mini_atlas"), notify=False)


@pytest.fixture()
def run(mini_db, data_dir, capsys, monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: pytest.fail("the CLI must never prompt"))

    def _run(*argv, db=mini_db):
        code = cli.main([str(a) for a in argv], lyrics_db=db, data_dir=data_dir)
        out = capsys.readouterr()
        return code, out.out, out.err
    return _run


def _leaves(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert isinstance(k, str)
            yield from _leaves(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from _leaves(v)
    else:
        yield obj


def _no_line_text(text: str):
    low = text.lower()
    for line in LONG_TEXTS:
        assert line not in low, f"corpus line leaked: {line!r}"


# --- devices refactor ------------------------------------------------------------------

def test_simile_positions_carry_marker_and_token_indexes():
    assert devices.simile_positions("usne crvene ko lava") == [("ko", 2, 3)]
    assert devices.simile_positions("K’o mafija") == [("k'o", 0, 2)]
    assert devices.simile_positions("ko ti je dao sve?") == []              # question: who
    assert devices.simile_positions("hladan kao") == [("kao", 1, 2)]        # marker ends the line
    toks, pos = devices.simile_scan("lep kao san i miran poput vode")
    assert [(m, toks[j]) for m, _i, j in pos] == [("kao", "san"), ("poput", "vode")]
    assert devices.simile_confidence("kao", "da", False) == "low"
    assert devices.simile_confidence("kao", "san", False) == "high"
    assert devices.simile_confidence("ko", "lava", True) == "low"
    assert devices.simile_confidence("ko", "lava", False) == "medium"
    assert devices.simile_confidence("poput", None, False) == "high"


def test_name_drop_phrase_matching_survives_the_first_token_index():
    gaz = frozenset({"acme corp", "panama", "mali tabak"})
    hit = lambda line: {d["span"] for d in devices.analyze_line(line, gazetteer=gaz)
                        if d["kind"] == "name_drop"}
    assert hit("vozim acme corp do panama") == {"acme corp", "panama"}
    assert hit("corp acme panama") == {"panama"}                    # wrong order: no phrase
    assert hit("acme sada corp") == set()                           # not contiguous
    assert hit("mali tabak i mali tabak") == {"mali tabak"}


def test_anaphora_runs_match_the_verse_analysis():
    tokens = [tokenize(l) for l in ["laku noc majko", "laku noc brate", "sve drugo", "da se vratim",
                                    "da se sakrijem"]]
    assert devices.anaphora_runs(tokens) == [(0, 2, 2)]            # function-word openings: none


# --- atlas -----------------------------------------------------------------------------

def test_atlas_counts_lanes_and_respects_corpus_scope(mini_atlas):
    lanes = mini_atlas["lanes"]
    assert lanes["drill"]["n_lines"] == len(DRILL_LINES) == 36
    assert lanes["pop"]["n_lines"] == 3                    # the gutenberg_pd line is not counted
    assert lanes["all"]["n_lines"] == 40                   # + the no-cohort song, still no English
    assert set(lanes) == {"drill", "pop", "all"}
    assert lanes["drill"]["counts"]["simile"] == 9
    assert lanes["drill"]["counts"]["anaphora"] == 2
    assert set(mini_atlas["artists"]) == {"devito"}        # jala/rasta have < 30 lines
    assert mini_atlas["artists"]["devito"]["n_lines"] == 36
    assert mini_atlas["v"] == atlas.ATLAS_VERSION


def test_atlas_numbers_match_an_independent_recomputation(mini_atlas):
    st = mini_atlas["lanes"]["drill"]
    syl = [count_line(t) for t in DRILL_LINES]
    assert st["median_syl"] == statistics.median(syl)
    num = st["numeric"]
    assert num["syllables"]["mean"] == pytest.approx(statistics.mean(syl))
    assert num["syllables"]["std"] == pytest.approx(statistics.pstdev(syl))
    words = [len(t.split()) for t in DRILL_LINES]
    assert num["words"]["mean"] == pytest.approx(statistics.mean(words))
    dens = [devices.consonance_density(t) for t in DRILL_LINES]
    assert st["cons_mean"] == pytest.approx(statistics.mean(dens))
    assert num["cons_density"]["std"] == pytest.approx(statistics.pstdev(dens))
    p = num["allit"]["mean"]
    assert 0.0 <= p <= 1.0 and num["allit"]["std"] == pytest.approx(math.sqrt(p * (1 - p)))
    assert all(v["n"] == 36 for v in num.values())
    priors = atlas.lane_numeric(mini_atlas, "drill")
    assert set(priors) == set(devices.NUMERIC_FEATURES)
    assert priors["syllables"] == (num["syllables"]["mean"], num["syllables"]["std"])
    assert atlas.lane_numeric({"lanes": {}}, "drill") == {}


def test_atlas_blob_and_table_hold_statistics_only(mini_atlas):
    for leaf in _leaves(mini_atlas):
        assert leaf is None or isinstance(leaf, (int, float)), f"non-stat value in blob: {leaf!r}"
    _no_line_text(repr(mini_atlas))
    table = "\n".join(atlas.render(mini_atlas, "drill", ("devito", "nobody")))
    _no_line_text(table)
    assert "lane drill" in table and "artist devito" in table
    assert "no atlas row" in table and "nobody" in table
    assert "lyrics" in table.splitlines()[0]              # 'stats only - no lyrics shown'
    assert "devito" in "\n".join(atlas.render(mini_atlas, "all"))       # slugs listed, no lines


def test_atlas_is_cached_in_cache_dir_and_rebuilt_on_change(mini_db, tmp_path, monkeypatch):
    db = tmp_path / "lyrics.db"
    shutil.copy(mini_db, db)
    cache = tmp_path / "cache"
    blob = atlas.load(db, cache, notify=False)
    cfile = atlas.cache_path(db, cache)
    assert cfile.is_file() and cfile.name.startswith("atlas_") and cfile.parent == cache
    assert not list(cache.glob("*.tmp"))
    monkeypatch.setattr(atlas, "_scan", lambda *a: pytest.fail("cache hit must not rescan"))
    assert atlas.load(db, cache, notify=False) == blob
    monkeypatch.undo()
    calls = []
    real = atlas._scan
    monkeypatch.setattr(atlas, "_scan", lambda *a: (calls.append(1), real(*a))[1])
    atlas.load(db, cache, rebuild=True, notify=False)
    assert len(calls) == 1
    st = db.stat()
    os.utime(db, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))      # db changed
    atlas.load(db, cache, notify=False)
    assert len(calls) == 2


def test_atlas_checks_annotation_and_guards_against_writers(mini_db, tmp_path):
    bare = tmp_path / "bare.db"
    shutil.copy(mini_db, bare)
    con = sqlite3.connect(str(bare))
    con.execute("DELETE FROM tokens")
    con.commit()
    con.close()
    with pytest.raises(corpus.CorpusNotAnnotated):
        atlas.load(bare, tmp_path / "c1", notify=False)
    assert not list((tmp_path / "c1").glob("atlas_*"))
    busy = tmp_path / "busy.db"
    shutil.copy(mini_db, busy)
    (tmp_path / "busy.db-wal").write_bytes(b"x" * 10)                   # a live writer
    with pytest.raises(corpus.DbUnavailable, match="being written"):
        atlas.load(busy, tmp_path / "c2", notify=False)
    with pytest.raises(corpus.DbUnavailable):
        atlas.load(tmp_path / "gone.db", tmp_path / "c3")


def test_atlas_never_modifies_lyrics_db(mini_db, tmp_path):
    before = (mini_db.stat().st_mtime_ns, mini_db.stat().st_size, sorted(os.listdir(mini_db.parent)))
    atlas.load(mini_db, tmp_path / "cache", rebuild=True, notify=False)
    comparisons.collect(mini_db, "all", (), None, corpus.load_index(mini_db, tmp_path / "cache"))
    after = (mini_db.stat().st_mtime_ns, mini_db.stat().st_size, sorted(os.listdir(mini_db.parent)))
    assert before == after


def test_atlas_cli_prints_stats_and_writes_only_its_cache(run, data_dir):
    code, out, _ = run("atlas", "--lane", "drill", "--artist", "devito")
    assert code == 0 and "lane drill" in out and "artist devito" in out and "36" in out
    _no_line_text(out)
    assert list(data_dir.glob("atlas_*.pkl"))
    assert not (data_dir / "mairina.db").exists()                       # atlas logs nothing
    code, out, _ = run("atlas", "--artist", "jala")
    assert code == 0 and "no atlas row" in out
    with pytest.raises(SystemExit):
        run("atlas", "--lane", "jazz")


def test_atlas_cli_fails_cleanly_without_the_db(run, tmp_path):
    code, _, err = run("atlas", db=tmp_path / "gone" / "lyrics.db")
    assert code == 2 and "gone" in err


# --- comparisons -----------------------------------------------------------------------

def _collect(mini_db, mini_index, lane="all", artists=(), theme=None):
    return comparisons.collect(mini_db, lane, artists, theme, mini_index)


def test_comparisons_are_single_words_and_ko_who_is_excluded(mini_db, mini_index):
    counts = _collect(mini_db, mini_index, "drill")
    assert counts == Counter({"lava": 2, "led": 1, "san": 1, "vode": 1, "noz": 1, "zid": 1})
    assert all(" " not in w and w.isalpha() for w in counts)
    for absent in ("gazda", "je", "spava", "devito", "lamb", "thelion"):
        assert absent not in counts        # who / kao da / artist name / English corpus
    # a refrain repeated inside one song counts once; the same line in another song counts again
    assert counts["lava"] == 2


def test_comparisons_lane_artist_and_theme_filters(mini_db, mini_index):
    assert _collect(mini_db, mini_index, "pop") == Counter({"zvezda": 1, "led": 1})
    assert _collect(mini_db, mini_index, "all")["zvezda"] == 2          # pop song + no-cohort song
    assert _collect(mini_db, mini_index, "all", ("jala",)) == Counter({"zvezda": 1, "led": 1})
    assert _collect(mini_db, mini_index, "all", ("nobody",)) == Counter()
    assert _collect(mini_db, mini_index, "all", theme="noc") == Counter({"zid": 1})
    assert _collect(mini_db, mini_index, "all", theme="lava") == Counter()   # the theme is no answer
    assert _collect(mini_db, mini_index, "all", theme="xyz") == Counter()


def test_comparison_scan_is_guarded_and_read_only(mini_db, mini_index, tmp_path):
    busy = tmp_path / "busy.db"
    shutil.copy(mini_db, busy)
    (tmp_path / "busy.db-journal").write_bytes(b"x")
    with pytest.raises(corpus.DbUnavailable, match="being written"):
        comparisons.collect(busy, "all", (), None, mini_index)
    with pytest.raises(corpus.DbUnavailable):
        comparisons.collect(tmp_path / "gone.db", "all", (), None, mini_index)


def test_rank_words_scores_simile_use_then_frequency_and_applies_boosts(mini_index):
    counts = Counter({"lava": 2, "led": 1, "san": 1})
    res = comparisons.rank_words(counts, mini_index, "drill", (), 0.0, None)
    assert res[0].candidate == "lava" and all(s.kind == "compare" for s in res)
    assert res[0].features["simile-use"] == pytest.approx(math.log1p(2), abs=1e-3)
    assert res[0].meta["count"] == 2 and "freq" in res[0].features
    assert "simile-use" in rank.explain(res[0])
    assert all("fresh" not in s.features for s in res)                  # fresh 0.0: no penalty
    fresh = comparisons.rank_words(counts, mini_index, "drill", (), 1.0, None)
    assert all("fresh" in s.features for s in fresh)
    base = {s.candidate: s.score for s in res}
    boosted = comparisons.rank_words(counts, mini_index, "drill", (), 0.0, {"san": (4, 0, 0)})
    by = {s.candidate: s for s in boosted}
    assert by["san"].score > base["san"] and "votes" in by["san"].features
    assert by["led"].score == base["led"]
    assert [s.candidate for s in comparisons.rank_words(counts, mini_index, "drill", (), 0.0, None)] \
        == [s.candidate for s in res]                                   # deterministic


def test_compare_cli_lists_single_words_and_logs_the_shown_list(run, data_dir):
    code, out, _ = run("compare", "--lane", "drill", "--fresh", "0")
    assert code == 0 and "Comparisons" in out and "list=#1" in out
    rows = [l for l in out.splitlines()[1:] if l.strip()]
    words = [l.split()[1] for l in rows]
    assert words[0] == "lava" and set(words) == {"lava", "led", "san", "vode", "noz", "zid"}
    assert all(" " not in w for w in words) and "2x" in rows[0]
    _no_line_text(out)
    con = sqlite3.connect(str(data_dir / "mairina.db"))
    kinds = con.execute("SELECT DISTINCT kind, query FROM shown").fetchall()
    assert kinds == [("compare", "lane=drill,theme=")]
    assert [r[0] for r in con.execute("SELECT candidate FROM shown ORDER BY rank")] == words
    code, out, _ = run("vote", "1+", "2-")
    assert code == 0 and "Saved 2 vote(s) on list #1 (compare)" in out


def test_compare_cli_theme_artist_max_and_errors(run, data_dir):
    code, out, _ = run("compare", "--theme", "noc", "--fresh", "0")
    assert code == 0 and "theme=noc" in out and [l.split()[1] for l in out.splitlines()[1:]] == ["zid"]
    con = sqlite3.connect(str(data_dir / "mairina.db"))
    assert con.execute("SELECT query FROM shown").fetchone()[0] == "lane=all,theme=noc"
    code, out, _ = run("compare", "--artist", "jala", "--max", "1", "--fresh", "0")
    assert code == 0 and len([l for l in out.splitlines()[1:] if l.strip()]) == 1
    code, out, _ = run("compare", "--artist", "nobody")
    assert code == 0 and "No comparison words" in out and "Hint" in out
    code, _, err = run("compare", "--theme", "dva reci")
    assert code == 1 and "one word" in err
    with pytest.raises(SystemExit):
        run("compare", "--lane", "jazz")


def test_compare_cli_stats_count_the_new_kind(run):
    run("compare", "--lane", "drill")
    run("vote", "1+")
    code, out, _ = run("stats")
    assert code == 0 and "compare 1 lists" in out and "Votes: 1" in out
