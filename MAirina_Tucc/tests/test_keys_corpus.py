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
    assert e["freq_by_cohort"] == {"drill_trap": 12}
    assert e["freq_by_artist"] == {"devito": 12}
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
