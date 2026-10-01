"""atlas + comparisons on a hand-built mini corpus (fixture lines only, no real lyrics).

Both modules may only ever output statistics or single words: every test that
reads their blobs or printed output asserts that no corpus line text leaks.
"""

import builtins
import math
import os
import pickle
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
    ("wanders", "wander", "VERB"), ("lamb", "lamb", "NOUN"),
    # alliteration fixtures
    ("kučka", "kučka", "NOUN"), ("kuca", "kuca", "NOUN"), ("kroz", "kroz", "ADP"),
    ("kapiju", "kapija", "NOUN"), ("sala", "sala", "NOUN"), ("šalju", "slati", "VERB"),
    ("mala", "mali", "ADJ"), ("voda", "voda", "NOUN"), ("ima", "imati", "VERB"),
    ("ona", "ona", "PRON"), ("oko", "oko", "NOUN"),
    # comparison stopword fixtures
    ("sve", "sav", "ADJ"), ("onaj", "onaj", "DET"), ("ti", "ti", "PRON"), ("moja", "moj", "ADJ"),
    ("mama", "mama", "NOUN"), ("mojih", "moj", "ADJ"), ("nijedna", "nijedan", "ADJ"),
    ("taj", "taj", "ADJ"), ("tih", "taj", "ADJ"), ("bela", "beo", "ADJ"), ("mek", "mek", "ADJ"),
    ("hladan", "hladan", "ADJ"),
    # comparison fragment fixtures
    ("la", "la", "NOUN"), ("gt", "gt", "NOUN"), ("ap", "ap", "NOUN"), ("krv", "krv", "NOUN")]}

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


def build_mini(path, songs=None):
    con = sqlite3.connect(str(path))
    con.executescript(SCHEMA)
    n = {"sec": 0, "line": 0, "tok": 0}
    for sid, cohort, target, primary, corp, sections in (songs or SONGS):
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
    assert lanes["drill"]["counts"]["simile"] == 8      # 9 simile lines, minus 'tiho kao da spava'
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
    assert "--mode" not in out and "assonance" not in out and "--fresh" not in out   # compare has none
    assert "relax --artist or --theme" in out and "--lane all" in out
    code, out, _ = run("rhyme", "xyz", "--artist", "nobody")                 # the other lists keep theirs
    assert "--mode assonance" in out
    code, _, err = run("compare", "--theme", "dva reci")
    assert code == 1 and "one word" in err
    with pytest.raises(SystemExit):
        run("compare", "--lane", "jazz")


def test_compare_cli_stats_count_the_new_kind(run):
    run("compare", "--lane", "drill")
    run("vote", "1+")
    code, out, _ = run("stats")
    assert code == 0 and "compare 1 lists" in out and "Votes: 1" in out


# --- wave 2F: strong-only alliteration in the atlas -------------------------------------

def test_atlas_allit_rate_counts_strong_alliteration_only(tmp_path):
    songs = [(1, "drill_trap", "devito", "Devito", "genius-pro",
              [("strofa", ["kučka kuca kroz kapiju",   # strong: k, k, k
                           "sala šalju",                # weak: s/š same class
                           "mala voda",                        # none
                           "ima ona oko"])])]                  # vowel onsets: none
    db = build_mini(tmp_path / "lyrics.db", songs)
    blob = atlas.load(db, tmp_path / "cache", notify=False)
    st = blob["lanes"]["drill"]
    assert st["n_lines"] == 4 and st["counts"]["allit"] == 1
    assert st["numeric"]["allit"]["mean"] == pytest.approx(0.25)
    assert blob["v"] == atlas.ATLAS_VERSION == 3


# --- wave 2R: the atlas simile rate counts what compare counts -------------------------

def test_atlas_simile_rate_counts_non_low_confidence_similes_only(tmp_path):
    songs = [(1, "drill_trap", "devito", "Devito", "genius-pro",
              [("strofa", ["usne crvene ko lava",              # mid-line 'ko': medium, counts
                           "tiho kao da spava",                 # 'kao da' = conjunction: low
                           "ko lava",                           # line-initial 'ko': low
                           "lep kao san i miran poput vode",    # two high similes, one line
                           "mala voda"])])]                     # none
    db = build_mini(tmp_path / "lyrics.db", songs)
    blob = atlas.load(db, tmp_path / "cache", notify=False)
    st = blob["lanes"]["drill"]
    assert st["n_lines"] == 5 and st["counts"]["simile"] == 2
    assert blob["artists"] == {}                                # < 30 lines: no artist row
    idx = corpus.load_index(db, tmp_path / "cache")
    # compare reads the very same lines: the low-confidence markers give it nothing either
    assert comparisons.collect(db, "drill", (), None, idx) == Counter(
        {"lava": 1, "san": 1, "vode": 1})
    row = atlas.render(blob, "drill")[2]
    assert row.split()[:4] == ["lane", "drill", "5", "40.0"]    # 2 of 5 lines


def test_a_version_2_atlas_cache_is_rebuilt(mini_db, tmp_path, monkeypatch):
    db = tmp_path / "lyrics.db"
    shutil.copy(mini_db, db)
    cache = tmp_path / "cache"
    blob = atlas.load(db, cache, notify=False)
    assert blob["v"] == 3
    with open(atlas.cache_path(db, cache), "wb") as fh:           # a cache written by wave 2F
        pickle.dump(dict(blob, v=2), fh)
    calls = []
    real = atlas._scan
    monkeypatch.setattr(atlas, "_scan", lambda *a: (calls.append(1), real(*a))[1])
    assert atlas.load(db, cache, notify=False)["v"] == 3 and len(calls) == 1


# --- wave 2F: comparison stopwords -----------------------------------------------------

STOP_SONGS = [(1, "drill_trap", "devito", "Devito", "genius-pro", [("strofa", [
    "svetla kao sve",            # pronoun-like ADJ (stoplist) and nothing after it
    "jak ko onaj zid",           # DET is skipped, the noun after it counts
    "lep ko ti",                 # PRON (and a clitic)
    "mek ko moja mama",          # stoplist form 'moja', then 'mama'
    "hladan ko mojih led",       # inflected: caught through the lemma 'moj'
    "bela kao nijedna",
    "tih ko taj san",            # stoplist form 'taj' (and lemma), then 'san'
    "jak ko led"])])]            # control: an ordinary noun


@pytest.fixture(scope="module")
def stop_db(tmp_path_factory):
    return build_mini(tmp_path_factory.mktemp("stop") / "lyrics.db", STOP_SONGS)


def test_stopwords_and_pronoun_upos_are_never_comparison_words(stop_db, tmp_path):
    idx = corpus.load_index(stop_db, tmp_path)
    counts = comparisons.collect(stop_db, "drill", (), None, idx)
    assert counts == Counter({"led": 2, "zid": 1, "mama": 1, "san": 1})
    for gone in ("sve", "onaj", "ti", "moja", "mojih", "nijedna", "taj", "tih"):
        assert gone not in counts
    ranked = comparisons.rank_words(counts, idx, "drill", (), 0.0, None)
    assert {s.candidate for s in ranked} == {"led", "zid", "mama", "san"}


def test_comparison_word_filter_uses_upos_form_and_lemma():
    class Idx:
        artist_names = frozenset({"devito"})
        forms = {"mali": {"upos": "ADJ", "lemma": "mali"}, "lava": {"upos": "NOUN", "lemma": "lava"},
                 "tog": {"upos": "DET", "lemma": "taj"}, "njega": {"upos": "PRON", "lemma": "on"},
                 "sve": {"upos": "ADJ", "lemma": "sav"}, "mojih": {"upos": "ADJ", "lemma": "moj"},
                 "devito": {"upos": "PROPN", "lemma": "devito"},
                 "svaki": {"upos": "ADJ", "lemma": "svaki"}, "led": {"upos": "NOUN", "lemma": "led"}}
    ok = lambda w, skip=None: comparisons._comparison_word(w, Idx(), skip)
    assert ok("mali") == "mali" and ok("lava") == "lava" and ok("led") == "led"
    assert ok("tog") is None and ok("njega") is None          # majority UPOS DET / PRON
    assert ok("sve") is None and ok("svaki") is None          # stoplist on the form
    assert ok("mojih") is None                                # stoplist on the lemma
    assert ok("devito") is None and ok("nepoznata") is None   # artist name / not in the index
    assert ok("lava", "lava") is None                         # the theme word itself


FRAGMENT_SONGS = [(1, "drill_trap", "devito", "Devito", "genius-pro", [("strofa", [
    "hladna ko la",              # 2 letters
    "jak ko gt",                 # no vowel
    "lep ko ap san",             # 'ap' is skipped, the noun after it counts
    "mek ko krv",                # no vowel letter, but a syllabic r: a real word
    "jak ko led"])])]            # control


@pytest.fixture(scope="module")
def fragment_db(tmp_path_factory):
    return build_mini(tmp_path_factory.mktemp("frag") / "lyrics.db", FRAGMENT_SONGS)


def test_fragments_are_never_comparison_words(fragment_db, tmp_path):
    idx = corpus.load_index(fragment_db, tmp_path)
    counts = comparisons.collect(fragment_db, "drill", (), None, idx)
    assert counts == Counter({"san": 1, "krv": 1, "led": 1})
    for gone in ("la", "gt", "ap"):
        assert gone not in counts
    ranked = comparisons.rank_words(counts, idx, "drill", (), 0.0, None)
    assert {s.candidate for s in ranked} == {"san", "krv", "led"}


def test_comparison_word_fragment_filter_units():
    class Idx:
        artist_names = frozenset()
        forms = {w: {"upos": "NOUN", "lemma": w} for w in
                 ("la", "ap", "gt", "ko", "krv", "prst", "led", "lava", "mrk", "tmn")}
    ok = lambda w: comparisons._comparison_word(w, Idx(), None)
    assert comparisons.MIN_WORD_LETTERS == 3
    assert ok("la") is None and ok("ap") is None              # under 3 letters
    assert ok("gt") is None and ok("tmn") is None             # no nucleus at all
    assert ok("krv") == "krv" and ok("prst") == "prst" and ok("mrk") == "mrk"   # syllabic r
    assert ok("led") == "led" and ok("lava") == "lava"


def test_stopword_list_is_exactly_the_agreed_one():
    agreed = """sve svi svaki svaka svako nijedna nijedan nijedno takav takva taj ta to ovaj ova
        ovo onaj ona neki neka svoj svoja moj moja tvoj tvoja isti ista sam sama ceo cela celi"""
    assert comparisons.STOPWORDS == frozenset(agreed.split())
    assert comparisons.STOP_UPOS == frozenset({"DET", "PRON"})
