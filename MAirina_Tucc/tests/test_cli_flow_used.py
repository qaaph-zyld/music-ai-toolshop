import builtins
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from mairina import cli, flow, used, votes


@pytest.fixture()
def run(corpus_db, data_dir, capsys, monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: pytest.fail("the CLI must never prompt"))

    def _run(*argv, db=corpus_db):
        code = cli.main([str(a) for a in argv], lyrics_db=db, data_dir=data_dir)
        out = capsys.readouterr()
        return code, out.out, out.err
    return _run


def test_rhyme_then_vote_then_stats(run, data_dir):
    code, out, _ = run("rhyme", "imaš", "--rng-seed", "1")
    assert code == 0 and "snimaš" in out and "uzimaš" in out and "perfect-2" in out
    code, out, _ = run("vote", "1+", "2-")
    assert code == 0 and "Saved 2 vote(s)" in out
    code, out, _ = run("stats")
    assert code == 0 and "Votes: 2 (up 1, down 1)" in out


def test_arm_is_recorded_and_both_arms_occur(tmp_path):
    rng = random.Random(0)
    assert {votes.assign_arm(rng) for _ in range(40)} == {"learned", "base"}
    con = votes.connect(tmp_path / "m.db")
    votes.log_shown(con, "rhyme", "q", "base", [("w", 1.0, {})])
    votes.log_shown(con, "rhyme", "q", "learned", [("w", 1.0, {})])
    assert [r[0] for r in con.execute("SELECT arm FROM shown ORDER BY id")] == ["base", "learned"]


def test_stats_ab_needs_100_votes(run, data_dir):
    run("rhyme", "imaš", "--rng-seed", "1")
    run("vote", "1+")
    code, out, _ = run("stats", "--ab")
    assert code == 0 and "Not enough data" in out
    con = votes.connect(data_dir / "mairina.db")
    for i in range(100):     # raw inserts: one transaction, far faster than 100 commits
        con.execute("INSERT INTO shown(ts,list_id,arm,ranker_version,kind,query,candidate,rank,score)"
                    " VALUES ('2026-01-01T00:00:00',?,?,'v1','rhyme','q','w',1,1.0)", (100 + i, votes.ARMS[i % 2]))
        con.execute("INSERT INTO votes VALUES (last_insert_rowid(), ?, '2026-01-01T00:00:00')", (1 if i % 4 else -1,))
    con.commit()
    code, out, _ = run("stats", "--ab")
    assert "Not enough data" not in out and "Verdict" in out and "arm learned" in out


def test_vote_error_paths_write_nothing(run, data_dir):
    code, _, err = run("vote", "1+")
    assert code == 1 and "No list" in err
    run("rhyme", "imaš", "--rng-seed", "1")
    code, _, err = run("vote", "1+", "99+")
    assert code == 1 and "out of range" in err
    code, _, err = run("vote", "abc")
    assert code == 1
    con = sqlite3.connect(str(data_dir / "mairina.db"))
    assert con.execute("SELECT COUNT(*) FROM votes").fetchone()[0] == 0


def test_missing_lyrics_db_exits_2_with_path(run, tmp_path):
    missing = tmp_path / "gone" / "lyrics.db"
    for cmd in (("rhyme", "imaš"), ("anchors",), ("multi", "da me imaš"), ("flow", str(tmp_path / "x.txt"))):
        (tmp_path / "x.txt").write_text("da te snimaš\n", encoding="utf-8")
        code, _, err = run(*cmd, db=missing)
        assert code == 2 and str(missing) in err


def test_empty_results_print_reason_and_hint_exit_0(run):
    code, out, _ = run("rhyme", "imaš", "--artist", "nobody")
    assert code == 0 and "No rhymes" in out and "Hint" in out
    code, out, _ = run("anchors", "--artist", "nobody")
    assert code == 0 and "No anchors" in out and "Hint" in out
    code, out, _ = run("multi", "xyz")
    assert code == 0 and "No multi" in out


def test_anchors_cli_output_and_determinism(run):
    _, a, _ = run("anchors", "--scheme", "AABB", "--rng-seed", "4")
    _, b, _ = run("anchors", "--scheme", "AABB", "--rng-seed", "4")
    strip = lambda t: [l for l in t.splitlines() if l[:3].strip().rstrip(".").isdigit() and "[" in l]
    assert len(strip(a)) == 4 and [l.split()[2] for l in strip(a)] == [l.split()[2] for l in strip(b)]


def test_fresh_out_of_range_rejected(run):
    with pytest.raises(SystemExit):
        run("rhyme", "imaš", "--fresh", "2")


def test_used_finds_words_shown_earlier(run, tmp_path, data_dir):
    run("rhyme", "imaš", "--lane", "drill", "--rng-seed", "1")
    run("multi", "da me imaš", "--rng-seed", "1")
    f = tmp_path / "verse.txt"
    f.write_text("[Verse]\nSve što SNIMAŠ, znaj\nja kažem da ekipa sad\n", encoding="utf-8")
    code, out, _ = run("used", f)
    assert code == 0 and "snimaš" in out and "da ekipa" in out
    con = sqlite3.connect(str(data_dir / "mairina.db"))
    assert con.execute("SELECT COUNT(*) FROM used WHERE candidate='snimaš'").fetchone()[0] == 1
    run("used", f)                                        # idempotent per (candidate, file)
    assert con.execute("SELECT COUNT(*) FROM used WHERE candidate='snimaš'").fetchone()[0] == 1


def test_used_ignores_suggestions_older_than_window(tmp_path):
    con = votes.connect(tmp_path / "m.db")
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    votes.log_shown(con, "rhyme", "q", "base", [("snimaš", 1.0, {})], ts=old)
    f = tmp_path / "v.txt"
    f.write_text("snimaš", encoding="utf-8")
    assert used.scan(f, 14, con) == [] and used.scan(f, 60, con) == ["snimaš"]


def test_used_boost_reaches_the_ranking(index, tmp_path):
    con = votes.connect(tmp_path / "m.db")
    votes.log_shown(con, "rhyme", "q", "learned", [("uzimaš", 1.0, {})])
    votes.mark_used(con, "uzimaš", "f.txt")
    assert votes.boosts(con)["uzimaš"] == (0, 0, 1)


def test_flow_counts_and_medians(run, tmp_path, corpus_db):
    f = tmp_path / "v.txt"
    f.write_text("[Verse 1]\nda te snimaš\n\nda me imaš sad opet\nje\n", encoding="utf-8")
    res = flow.flow(f, "drill", corpus_db)
    assert [(n, s) for n, s, _ in res.rows] == [(2, 4), (4, 7), (5, 1)]
    assert res.user_median == 4 and res.lane_median == 10
    assert flow.flow(f, "pop", corpus_db).lane_median == 7
    code, out, _ = run("flow", f, "--lane", "drill")
    assert code == 0 and "your median 4" in out and "median 10" in out
    code, _, err = run("flow", tmp_path / "missing.txt")
    assert code == 1 and "not found" in err


def test_lyrics_db_never_modified(run, corpus_db):
    before = corpus_db.stat().st_mtime_ns
    run("rhyme", "imaš")
    run("anchors", "--rng-seed", "1")
    run("multi", "da me imaš")
    assert corpus_db.stat().st_mtime_ns == before


def test_arm_is_independent_of_rng_seed(corpus_db, data_dir):
    import argparse
    args = argparse.Namespace(rng_seed=1)
    arms = {cli._setup(args, corpus_db, data_dir)[3] for _ in range(24)}
    assert arms == {"learned", "base"}                    # same --rng-seed, both arms drawn


def test_anchors_with_rng_seed_stay_reproducible(run):
    picks = []
    for _ in range(3):
        _, out, _ = run("anchors", "--rng-seed", "4")
        picks.append([l.split()[2] for l in out.splitlines() if "[" in l and l.strip()[0].isdigit()])
    assert picks[0] == picks[1] == picks[2] and len(picks[0]) == 4


def test_used_normalizes_nfd_text(tmp_path):
    import unicodedata
    con = votes.connect(tmp_path / "m.db")
    votes.log_shown(con, "rhyme", "q", "base", [("snimaš", 1.0, {}), ("čekaš", 0.9, {})])
    f = tmp_path / "nfd.txt"
    f.write_text(unicodedata.normalize("NFD", "sve što snimaš, ja čekaš"), encoding="utf-8")
    assert sorted(used.scan(f, 14, con)) == sorted(["snimaš", "čekaš"])


def test_used_falls_back_to_cp1250(tmp_path):
    con = votes.connect(tmp_path / "m.db")
    votes.log_shown(con, "rhyme", "q", "base", [("snimaš", 1.0, {}), ("čekaš", 0.9, {}), ("đon", 0.8, {})])
    f = tmp_path / "old.txt"
    f.write_bytes("sve što snimaš, ja čekaš, đon".encode("cp1250"))
    with pytest.raises(UnicodeDecodeError):
        f.read_bytes().decode("utf-8")
    assert sorted(used.scan(f, 14, con)) == sorted(["snimaš", "čekaš", "đon"])
