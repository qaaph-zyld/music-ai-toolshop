"""hints: thumbs on xray hint rules; 3 down and 0 up mutes a rule for this user."""

import builtins
import sqlite3

import pytest

from mairina import cli, hints, rules, votes


@pytest.fixture()
def con(tmp_path):
    c = votes.connect(tmp_path / "m.db")
    hints.ensure(c)
    return c


@pytest.fixture()
def run(corpus_db, data_dir, capsys, monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: pytest.fail("the CLI must never prompt"))

    def _run(*argv, db=corpus_db):
        code = cli.main([str(a) for a in argv], lyrics_db=db, data_dir=data_dir)
        out = capsys.readouterr()
        return code, out.out, out.err
    return _run


def test_votes_are_recorded_and_counted_per_rule(con):
    assert hints.vote(con, "cliche", -1) == (0, 1)
    assert hints.vote(con, "cliche", -1) == (0, 2)
    assert hints.vote(con, "calque", 1) == (1, 0)
    assert hints.counts(con) == {"cliche": (0, 2), "calque": (1, 0)}


def test_mute_needs_three_down_and_no_up(con):
    for _ in range(2):
        hints.vote(con, "cliche", -1)
    assert hints.muted(con) == []                       # 2 down: not yet
    hints.vote(con, "cliche", -1)
    assert hints.muted(con) == ["cliche"]               # 3 down, 0 up
    hints.vote(con, "cliche", 1)
    assert hints.muted(con) == []                       # one up-vote prevents the mute
    for _ in range(5):
        hints.vote(con, "self_rhyme", -1)
    hints.vote(con, "calque", -1)
    assert hints.muted(con) == ["self_rhyme"]           # sorted, per rule, calque has only 1 down


def test_reset_unmutes_and_forgets_the_votes(con):
    for _ in range(3):
        hints.vote(con, "cliche", -1)
    assert hints.muted(con) == ["cliche"]
    assert hints.reset(con, "cliche") == 3
    assert hints.muted(con) == [] and hints.counts(con) == {}


def test_reset_of_a_rule_leaves_other_mutes_alone(con):
    for _ in range(3):
        hints.vote(con, "cliche", -1)
        hints.vote(con, "calque", -1)
    assert hints.muted(con) == ["calque", "cliche"]
    hints.reset(con, "cliche")
    assert hints.muted(con) == ["calque"]


def test_bad_rule_ids_and_votes_are_rejected(con):
    for bad in ("", "a b", "a;drop table x", "rule/1"):
        with pytest.raises(votes.VoteError):
            hints.vote(con, bad, -1)
        with pytest.raises(votes.VoteError):
            hints.reset(con, bad)
    with pytest.raises(votes.VoteError):
        hints.vote(con, "cliche", 0)
    assert hints.counts(con) == {}                      # nothing was saved


def test_readers_tolerate_a_db_without_the_table(tmp_path):
    bare = sqlite3.connect(str(tmp_path / "bare.db"))
    assert hints.counts(bare) == {} and hints.muted(bare) == [] and hints.reset(bare, "cliche") == 0


def test_hint_votes_never_touch_the_v1_tables(tmp_path):
    base = votes.connect(tmp_path / "a.db")
    v1 = dict(base.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall())
    other = votes.connect(tmp_path / "b.db")
    hints.vote(other, "cliche", -1)
    after = dict(other.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall())
    assert {k: after[k] for k in v1} == v1 and "hint_votes" in after


@pytest.fixture()
def cliche_lexicon(monkeypatch):
    lex = {"calques": [], "cliches": ["plamen ljubavi"], "abstract": set(), "concrete": set(),
           "ekavica": set(), "ijekavica": set()}
    monkeypatch.setattr(rules, "load_lexicons", lambda: lex)


def _verse(tmp_path):
    f = tmp_path / "v.txt"
    f.write_text("plamen ljubavi gori u meni\nusne crvene ko lava\n", encoding="utf-8")
    return f


def test_muted_rule_disappears_from_xray_and_shows_in_stats(run, tmp_path, data_dir, cliche_lexicon):
    f = _verse(tmp_path)
    code, out, _ = run("xray", f)
    assert code == 0 and "cliché?" in out and "muted hints" not in out
    assert not (data_dir / "mairina.db").exists()                 # xray never creates the db
    for _ in range(2):
        code, out, _ = run("hint-vote", "cliche", "-")
        assert code == 0 and "Muted" not in out
    code, out, _ = run("hint-vote", "cliche", "-")
    assert code == 0 and "0 up / 3 down" in out and "Muted" in out
    code, out, _ = run("xray", f)
    assert "cliché?" not in out and "muted hints: cliche" in out.splitlines()[0]
    code, out, _ = run("stats")
    assert "Muted hint rules: cliche" in out


def test_reset_brings_the_hint_back_and_an_upvote_prevents_muting(run, tmp_path, cliche_lexicon):
    f = _verse(tmp_path)
    for _ in range(3):
        run("hint-vote", "cliche", "-")
    assert "cliché?" not in run("xray", f)[1]
    code, out, _ = run("hint-vote", "cliche", "reset")
    assert code == 0 and "3 vote(s) removed" in out
    assert "cliché?" in run("xray", f)[1]
    assert "Muted hint rules" not in run("stats")[1]
    run("hint-vote", "cliche", "+")
    for _ in range(4):
        run("hint-vote", "cliche", "-")
    assert "cliché?" in run("xray", f)[1]                        # 1 up keeps it alive


def test_unknown_rule_id_is_saved_with_a_note_and_bad_ids_exit_1(run):
    code, out, err = run("hint-vote", "mystery_rule", "-")
    assert code == 0 and "1 down" in out and "not a known hint rule" in err
    code, _, err = run("hint-vote", "bad id!", "-")
    assert code == 1 and "Bad rule id" in err
    with pytest.raises(SystemExit):
        run("hint-vote", "cliche", "maybe")
