"""xray CLI and the rhyme --line/--target shaping (fixture corpus, no real lyrics)."""

import builtins

import pytest

from mairina import cli, rank


@pytest.fixture()
def run(corpus_db, data_dir, capsys, monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: pytest.fail("the CLI must never prompt"))

    def _run(*argv, db=corpus_db):
        code = cli.main([str(a) for a in argv], lyrics_db=db, data_dir=data_dir)
        out = capsys.readouterr()
        return code, out.out, out.err
    return _run


def test_xray_row_shape_and_tags(run, tmp_path):
    f = tmp_path / "verse.txt"
    f.write_text(
        "usne crvene ko lava\n"
        "s tobom uvek ludilo\n"
        "niko ne pomisli da spava\n"
        "mala, mogla si da me imas\n"
        "u panameri da se snimas\n", encoding="utf-8")
    code, out, _ = run("xray", f, "--lane", "drill", "--section", "strofa")
    assert code == 0 and "X-ray 5 lines" in out
    rows = out.splitlines()
    assert "≈simile(ko)" in rows[1]                       # 'ko' mid-line is a simile
    assert "rhyme A" in rows[1] and "rhyme A" in rows[3]  # lava / spava
    assert "rhyme B" in rows[4] and "rhyme B" in rows[5]  # imas / snimas
    assert "rhyme -" in rows[2]                           # ludilo: no partner
    assert "≈multisyllabic_rhyme" in rows[4] and "≈multisyllabic_rhyme" in rows[5]
    assert " syl " in rows[1] and "cons " in rows[1]
    assert "allit" not in rows[5]                         # se+snimas are clitics, not allit
    assert "name_drop" not in out                         # no gazetteer hit on mala/niko


def test_xray_fails_cleanly_on_unannotated_db(run, corpus_db, tmp_path):
    import shutil
    import sqlite3
    bare = tmp_path / "bare.db"
    shutil.copy(corpus_db, bare)
    con = sqlite3.connect(str(bare))
    con.execute("DELETE FROM tokens")
    con.commit()
    con.close()
    f = tmp_path / "v.txt"
    f.write_text("ko lava pada\n", encoding="utf-8")
    code, _, err = run("xray", f, db=bare)
    assert code == 2 and "CLASSLA tokens" in err


def test_xray_degrades_without_lyrics_db(run, tmp_path):
    f = tmp_path / "v.txt"
    f.write_text("ko lava pada\n", encoding="utf-8")
    code, out, err = run("xray", f, db=tmp_path / "gone" / "lyrics.db")
    assert code == 0 and "Note:" in err and "syl" in out


def test_xray_missing_file_and_blank_file(run, tmp_path):
    code, _, err = run("xray", tmp_path / "nope.txt")
    assert code == 1 and "not found" in err
    f = tmp_path / "blank.txt"
    f.write_text("[Verse]\n\n", encoding="utf-8")
    code, out, _ = run("xray", f)
    assert code == 0 and "No lyric lines" in out


def test_rhyme_line_target_shows_gap_and_dom_class(run):
    code, out, _ = run("rhyme", "imaš", "--lane", "drill",
                       "--line", "mala mogla si da me", "--target", "9")
    assert code == 0
    assert "gap" in out                                   # the syllable-gap term is visible


def test_gap_feature_prefers_candidates_that_fill_the_line(index):
    base = rank.Ctx(index, "all")
    res = rank.rank("grade", base.vocab(), base)
    assert res and "gap" not in res[0].features and "dom-class" not in res[0].features
    shaped = rank.Ctx(index, "all", 0.5, (), None, "kratka", 4)
    res = rank.rank("grade", shaped.vocab(), shaped)     # line has 2 syl -> gap 2
    for s in res:
        assert "gap" in s.features and "gap" in rank.explain(s)
    assert any("dom-class" in s.features for s in res)   # 'k'-heavy line: plosive dominant
    assert "dom-class" in rank.explain(next(s for s in res if "dom-class" in s.features))


def test_anchors_rows_show_target_range(run):
    code, out, _ = run("anchors", "--scheme", "AABB", "--lane", "drill", "--rng-seed", "1")
    assert code == 0
    rows = [l for l in out.splitlines() if "[" in l and l.strip()[:1].isdigit()]
    assert len(rows) == 4
    assert all("syl n/a" in l for l in rows)              # fixture has no strofa/refren types


def test_xray_allit_flag_is_strong_alliteration_only(run, tmp_path):
    f = tmp_path / "v.txt"
    f.write_text("kučka kuca kroz kapiju\nsala šalju\nmala voda\n", encoding="utf-8")
    code, out, _ = run("xray", f)
    rows = out.splitlines()
    assert code == 0 and "allit ✓" in rows[1]               # k, k, k: same phoneme
    assert "allit" not in rows[2]                            # s/š: same class only (weak detail)
    assert "allit" not in rows[3]
