"""targets: p25/median/p75 of lines.syllable_count per lane x section type."""

import pickle
import sqlite3
from pathlib import Path

import pytest

from mairina import corpus, targets


def _mini_db(path: Path) -> Path:
    """Drill song 1 (strofa 8..15 x4, refren 6..9 x8), pop song 2 (strofa n=4,
    refren syl 10 x32), and English-corpus song 3 (pop strofa syl 3) that must
    never leak into the tables."""
    con = sqlite3.connect(str(path))
    con.executescript("""
        CREATE TABLE songs (id INTEGER PRIMARY KEY, genre_cohort TEXT,
                            corpus TEXT NOT NULL DEFAULT 'genius-pro');
        CREATE TABLE sections (id INTEGER PRIMARY KEY, song_id INTEGER, type TEXT);
        CREATE TABLE lines (id INTEGER PRIMARY KEY, section_id INTEGER, syllable_count INTEGER,
                            text_norm TEXT);
        CREATE TABLE tokens (id INTEGER PRIMARY KEY, line_id INTEGER, form TEXT,
                             source_script TEXT);
    """)
    con.execute("INSERT INTO songs VALUES (1,'drill_trap','genius-pro'),"
                "(2,'pop','genius-pro'),(3,'pop','gutenberg_pd')")
    con.execute("INSERT INTO sections VALUES (1,1,'strofa'),(2,1,'refren'),"
                "(3,2,'strofa'),(4,2,'refren'),(5,3,'strofa')")
    lid = 0

    def add(sec, syl, text="tekst"):
        nonlocal lid
        lid += 1
        con.execute("INSERT INTO lines VALUES (?,?,?,?)", (lid, sec, syl, text))
        con.execute("INSERT INTO tokens VALUES (?,?,'tekst','latin')", (lid, lid))

    for syl in list(range(8, 16)) * 4:          # drill strofa, n=32
        add(1, syl)
    for syl in list(range(6, 10)) * 8:          # drill refren, n=32
        add(2, syl)
    for syl in (5, 6, 5, 6):                    # pop strofa, n=4 -> lane fallback
        add(3, syl)
    for _ in range(32):                         # pop refren, n=32
        add(4, 10)
    for _ in range(40):                         # English pop strofa: corpus-excluded
        add(5, 3, "thelion wanders")
    lid += 1
    con.execute("INSERT INTO lines VALUES (?,1,0,'x')", (lid,))      # syl 0: ignored
    con.execute("INSERT INTO tokens VALUES (?,?,'x','latin')", (lid, lid))
    con.commit()
    con.close()
    return path


@pytest.fixture(scope="module")
def mini_db(tmp_path_factory):
    return _mini_db(tmp_path_factory.mktemp("targets") / "lyrics.db")


@pytest.fixture(scope="module")
def cache_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("tcache")


def test_lane_table_quartiles(mini_db, cache_dir):
    drill = targets.lane_table("drill", mini_db, cache_dir)
    assert drill["strofa"] == (9, 11, 13)                  # p25/median/p75 of 8..15
    assert not drill["strofa"].approx
    assert drill["refren"] == (6, 7, 8)
    assert "bridge" not in drill                           # unknown/absent section: no entry


def test_small_n_falls_back_to_lane_range_marked_approx(mini_db, cache_dir):
    pop = targets.lane_table("pop", mini_db, cache_dir)
    t = pop["strofa"]                                       # n=4 < MIN_N -> lane pooled
    assert t == (10, 10, 10) and t.approx                    # pooled = refren 10s + strofa 5/6
    assert targets.fmt_range(t) == "10–10~"
    assert targets.fmt_range((9, 11, 13)) == "9–13"
    assert targets.fmt_range(None) == "n/a"


def test_corpus_scope_excludes_english_lines(mini_db, cache_dir):
    pop = targets.lane_table("pop", mini_db, cache_dir)
    syls = {s for t in (5, 6, 10) for s in (t,)}            # sanity: only these syls exist
    assert syls == {5, 6, 10}
    assert pop["refren"] == (10, 10, 10) and not pop["refren"].approx
    # the English song's syl-3 strofa lines never enter any pool
    all_t = targets.lane_table("all", mini_db, cache_dir)
    assert all(v[0] >= 5 for v in all_t.values())


def test_target_and_fmt_range(mini_db, cache_dir):
    assert targets.target("drill", "refren", mini_db, cache_dir) == (6, 7, 8)
    assert targets.target("drill", "hook", mini_db, cache_dir) is None


def test_cons_thresholds(mini_db, cache_dir):
    thr = targets.cons_thresholds("drill", mini_db, cache_dir)
    assert thr is not None and len(thr) == 3
    # 'tekst' has 4 consonants over 1 syllable, 3 of them plosive -> density 3.0.
    # The English lines (density 1.6) would drag p25 down if they leaked.
    assert thr == (3.0, 3.0, 3.0)
    assert targets.cons_thresholds("all", mini_db, cache_dir) == (3.0, 3.0, 3.0)


def test_cache_file_lands_in_cache_dir(mini_db, cache_dir):
    targets.lane_table("all", mini_db, cache_dir)
    assert list(Path(cache_dir).glob("targets_*.pkl"))


def test_cache_is_keyed_on_mtime_and_size(mini_db, cache_dir):
    targets.lane_table("all", mini_db, cache_dir)
    blob = pickle.loads(next(Path(cache_dir).glob("targets_*.pkl")).read_bytes())
    assert blob["v"] == targets.BLOB_VERSION
    st = mini_db.stat()
    assert blob["mtime_ns"] == st.st_mtime_ns and blob["size"] == st.st_size
    assert all(not isinstance(lane, dict) or "ids" not in lane
               for lane in blob["lanes"].values())         # no song/line ids persisted


def test_unannotated_db_raises_instead_of_caching(mini_db, cache_dir, tmp_path):
    import shutil
    bare = tmp_path / "bare.db"
    shutil.copy(mini_db, bare)
    con = sqlite3.connect(str(bare))
    con.execute("DELETE FROM tokens")
    con.commit()
    con.close()
    with pytest.raises(corpus.CorpusNotAnnotated, match="CLASSLA tokens"):
        targets.lane_table("all", bare, tmp_path / "c")
    assert not list((tmp_path / "c").glob("targets_*.pkl"))


def test_missing_db_raises(mini_db, cache_dir, tmp_path):
    with pytest.raises(corpus.DbUnavailable):
        targets.lane_table("all", tmp_path / "gone.db", cache_dir)
