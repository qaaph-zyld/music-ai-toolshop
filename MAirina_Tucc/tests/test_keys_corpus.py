import os
import shutil
import sqlite3

import pytest

from mairina import corpus, keys


def test_tail_keys_perfect_pairs():
    assert keys.tail_key("imaš") == keys.tail_key("snimaš") == "imaš"
    assert keys.tail_key("lava") == keys.tail_key("spava") == "ava"
    assert keys.tail_key("IMAŠ") == "imaš"


def test_tail_key_digraphs_are_single_sounds():
    assert keys.tail_key("zemlja") == "emlja"
    assert keys.consonant_units("budžak") == ["dž", "k"]
    assert keys.consonant_units("zemlja") == ["m", "lj"]
    assert keys.consonant_key("snimaš") == "mš"


def test_syllabic_r_is_a_nucleus():
    assert keys.tail_key("srce") == "rce"
    assert keys.nuclei_count("prst") == 1
    assert keys.tail_key("prst", 1) == "rst"
    assert keys.nuclei_count("trava") == 2          # r next to a vowel is not syllabic


def test_vowel_key_uses_toolshop_skeleton():
    assert keys.vowel_key("da me imaš") == "aeia"
    assert keys.vowel_tail("da me imaš", 2) == "ia"


def test_short_word_falls_back_to_whole_word():
    assert keys.tail_key("sve", 3) == "sve"


def test_corpus_hygiene(index):
    f = index.forms
    assert "лава" not in f                           # cyrillic dropped
    for junk in (",", "3", "hm", "$"):
        assert junk not in f                         # PUNCT, NUM, X, SYM dropped
    assert "Lava" not in f and "lava" in f           # lowercased keys merged
    assert f["lava"]["freq"] == 6 * 4 + 1 + 1


def test_corpus_majority_lemma_and_pos(index):
    assert index.forms["lava"]["lemma"] == "lava"    # 13 votes vs 'lav' 1
    assert index.forms["lava"]["upos"] == "NOUN"


def test_corpus_breakdowns(index):
    e = index.forms["snimaš"]
    assert e["freq_by_cohort"] == {"drill_trap": 17}
    assert e["freq_by_artist"] == {"devito": 17}
    assert e["n_songs"] == 2
    assert index.freq("snimaš", "pop") == 0
    assert index.freq("uzimaš", "pop") == 6
    assert index.freq("lava", "all", ("jala",)) == 6
    assert index.freq("snimaš", "drill", ("jala",)) == 0    # artist lens is a hard filter


def test_artist_lens_intersects_with_lane(index):
    assert index.freq("lava", "drill", ("jala",)) == 0      # jala only has pop songs
    assert index.freq("lava", "pop", ("jala",)) == 6
    assert index.freq("lava", "drill", ("devito",)) == 14   # 12 + the 'lav' and 'Lava' variants
    assert index.freq("lava", "all", ("devito", "jala")) == 14 + 6
    assert "lava" not in index.vocab("drill", ("jala",))
    assert "lava" in index.vocab("pop", ("jala",))


def test_artist_name_tokens_are_built_from_songs_and_kept_out_of_vocab(index):
    names = index.artist_names
    assert {"devito", "jala", "senida", "rasta"} <= names    # split on spaces/hyphens/'x'
    assert "x" not in names and "senidah" in names            # extra spelling variant
    assert "senida" in index.forms and "senida" not in index.vocab("all")
    assert "lava" not in names


def test_cache_is_reused_then_rebuilt_when_db_changes(corpus_db, tmp_path, monkeypatch):
    dbcopy = tmp_path / "copy.db"
    shutil.copy(corpus_db, dbcopy)
    corpus_db = dbcopy
    calls = []
    real = corpus._build
    monkeypatch.setattr(corpus, "_build", lambda p: calls.append(1) or real(p))
    a = corpus.load_index(corpus_db, tmp_path)
    b = corpus.load_index(corpus_db, tmp_path)
    assert len(calls) == 1 and a.forms == b.forms
    st = corpus_db.stat()
    os.utime(corpus_db, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    corpus.load_index(corpus_db, tmp_path)
    assert len(calls) == 2


def test_missing_db_names_expected_path(tmp_path):
    missing = tmp_path / "nope" / "lyrics.db"
    with pytest.raises(corpus.DbUnavailable) as exc:
        corpus.load_index(missing, tmp_path)
    assert str(missing) in str(exc.value)


def test_open_ro_refuses_writes_and_keeps_mtime(corpus_db):
    before = corpus_db.stat().st_mtime_ns
    con = corpus.open_ro(corpus_db)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("CREATE TABLE x(a)")
    con.close()
    assert corpus_db.stat().st_mtime_ns == before


@pytest.mark.parametrize("word", ["taboo", "woo", "kaboo", "xilofon", "quiz", "yeah", "aaa", "beer", "skiing", "zoo", "duu"])
def test_orthography_rejects_foreign_letters_and_doubled_vowels(word):
    assert not keys.is_serbian_orthography(word)


@pytest.mark.parametrize("word", ["lava", "imaš", "srce", "prst", "džaba", "ljubav", "nemirna"])
def test_orthography_accepts_serbian_words(word):
    assert keys.is_serbian_orthography(word)


def test_bigrams_are_adjacent_kept_tokens_in_one_line(index):
    b = index.bigrams
    assert ("da", "ekipa") in b                       # 'Da Ekipa' lowercased
    assert ("sade", "snimaš") in b and ("te", "snimaš") in b and ("grad", "sef") in b
    assert ("grade", "snimaš") not in b               # a dropped PUNCT token sits between
    assert ("pade", "snimaš") not in b                # a dropped Cyrillic token sits between
    assert ("ekipa", "sade") not in b                 # consecutive lines never pair
    assert ("na", "ekipa") not in b and ("kan", "sef") not in b
    assert all(isinstance(x, tuple) and len(x) == 2 and all(isinstance(w, str) and " " not in w for w in x)
               for x in b)                            # word pairs only, never lines
    assert "ekipa" in index.predecessors()["snimaš"] or "sade" in index.predecessors()["snimaš"]


def test_cache_version_bump_rebuilds_the_index(corpus_db, tmp_path, monkeypatch):
    calls = []
    real = corpus._build
    monkeypatch.setattr(corpus, "_build", lambda p: calls.append(1) or real(p))
    corpus.load_index(corpus_db, tmp_path)
    corpus.load_index(corpus_db, tmp_path)
    assert len(calls) == 1                             # cache hit
    monkeypatch.setattr(corpus, "CACHE_VERSION", corpus.CACHE_VERSION + 1)
    idx = corpus.load_index(corpus_db, tmp_path)       # same file, newer code version
    assert len(calls) == 2 and ("da", "ekipa") in idx.bigrams


def test_current_cache_version_stores_bigrams(corpus_db, tmp_path):
    import pickle
    corpus.load_index(corpus_db, tmp_path)
    blob = pickle.loads(next(tmp_path.glob("index_*.pkl")).read_bytes())
    assert blob["version"] == corpus.CACHE_VERSION == 4 and ("da", "ekipa") in blob["bigrams"]
    assert "songs" not in blob["forms"]["lava"]        # no song/line ids in the cache
    old = dict(blob, version=3)
    next(tmp_path.glob("index_*.pkl")).write_bytes(pickle.dumps(old))
    assert ("da", "ekipa") in corpus.load_index(corpus_db, tmp_path).bigrams


def test_only_genius_pro_corpus_is_indexed(index):
    # the gutenberg_pd fixture song contributes nothing: no forms, no bigrams,
    # no artist tokens, no entities (gazetteer side is tested in test_devices)
    assert "thelion" not in index.forms and "wanders" not in index.forms
    assert ("thelion", "wanders") not in index.bigrams
    assert "englishbard" not in index.artist_names and "english" not in index.artist_names
    assert index.freq("lava", "all") == 26                    # unchanged: 24 + lav/Lava variants


def test_digraph_exceptions_split_prefix_boundaries():
    assert keys.nuclei_count("nadživeti") == 4          # na-dži-ve-ti, not na-dže-ti
    assert keys.nuclei_count("injekcija") == 4           # in-jek-ci-ja
    assert keys.nuclei_count("podžupan") == 3            # po-džu-pan
    assert keys.nuclei_count("konjunkcija") == 4
    assert keys.tail_key("injekcija", 1) == "a"


def test_unannotated_corpus_raises_and_keeps_good_cache(corpus_db, tmp_path):
    bad = tmp_path / "bare.db"
    shutil.copy(corpus_db, bad)
    con = sqlite3.connect(str(bad))
    con.execute("DELETE FROM tokens")
    con.commit()
    con.close()
    with pytest.raises(corpus.CorpusNotAnnotated, match="CLASSLA tokens"):
        corpus.load_index(bad, tmp_path / "c1")
    assert not list((tmp_path / "c1").glob("index_*.pkl"))        # nothing cached

    # partial coverage (<90% of non-empty lines) also refuses
    con = sqlite3.connect(str(bad))
    n = con.execute("SELECT COUNT(*) FROM lines").fetchone()[0]
    con.execute("DELETE FROM tokens WHERE line_id > ?", (n * 0.8,))
    con.commit()
    con.close()
    with pytest.raises(corpus.CorpusNotAnnotated):
        corpus.load_index(bad, tmp_path / "c2")


def test_rebuild_never_overwrites_a_good_cache(corpus_db, tmp_path):
    import pickle
    db = tmp_path / "copy.db"
    shutil.copy(corpus_db, db)
    idx = corpus.load_index(db, tmp_path)                         # good cache written
    cfile = next(tmp_path.glob("index_*.pkl"))
    good = cfile.read_bytes()
    con = sqlite3.connect(str(db))                                # mutate the copy
    con.execute("DELETE FROM tokens")
    con.commit()
    con.close()
    with pytest.raises(corpus.CorpusNotAnnotated):
        corpus.load_index(db, tmp_path)                           # stale cache, rebuild fails
    assert cfile.read_bytes() == good                             # never overwritten
    assert pickle.loads(good)["forms"] == idx.forms


def test_build_guarded_refuses_wal_and_retries_on_change(tmp_path):
    db = tmp_path / "lyrics.db"
    db.write_bytes(b"0" * 100)
    (tmp_path / "lyrics.db-wal").write_bytes(b"")         # stale reader artifact
    (tmp_path / "lyrics.db-shm").write_bytes(b"x" * 64)   # -shm never signals a writer
    assert corpus.build_guarded(db, lambda: 1) == 1        # 0-byte wal is not a writer
    (tmp_path / "lyrics.db-wal").write_bytes(b"x")         # non-empty wal: live writer
    with pytest.raises(corpus.DbUnavailable, match="being written"):
        corpus.build_guarded(db, lambda: 1)
    (tmp_path / "lyrics.db-wal").unlink()
    (tmp_path / "lyrics.db-journal").write_bytes(b"")
    with pytest.raises(corpus.DbUnavailable, match="being written"):
        corpus.build_guarded(db, lambda: 1)
    (tmp_path / "lyrics.db-journal").unlink()
    (tmp_path / "lyrics.db-shm").unlink()

    calls = []
    def changes_once():
        calls.append(1)
        if len(calls) == 1:
            db.write_bytes(b"0" * 200)                  # db changed mid-build
        return "ok"
    assert corpus.build_guarded(db, changes_once) == "ok" and len(calls) == 2

    n = [0]
    def always_changes():
        n[0] += 1
        db.write_bytes(b"x" * (100 + n[0]))             # still changing on the retry
        return n[0]
    with pytest.raises(corpus.DbUnavailable, match="changed during"):
        corpus.build_guarded(db, always_changes)
    assert n[0] == 2                                    # retried exactly once


def test_load_index_retries_when_db_changes_mid_build(corpus_db, tmp_path, monkeypatch):
    db = tmp_path / "copy.db"
    shutil.copy(corpus_db, db)
    real = corpus._build
    calls = []
    def flaky(p):
        calls.append(1)
        out = real(p)
        if len(calls) == 1:
            db.write_bytes(db.read_bytes() + b" ")      # a writer touched it mid-build
        return out
    monkeypatch.setattr(corpus, "_build", flaky)
    idx = corpus.load_index(db, tmp_path)
    assert len(calls) == 2 and "lava" in idx.forms
