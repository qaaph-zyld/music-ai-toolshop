"""stars + fingerprint: star -> stars -> unstar, shrinkage math, compare wording (raw star
mean, n flag), lane semantics, `mt me` and the xray `vs★` column. Fixture corpus and
hand-written lines only."""

import builtins
import json
import math

import pytest
from toolshop.syllables import count_line

from mairina import atlas, cli, devices, fingerprint, keys, votes

VERSE = ("[Verse 1]\n"
         "Usne crvene ko lava –\n"
         "s tobom uvek ludilo\n"
         "\n"
         "(niko ne pomisli da spava)\n"
         "Separe je naš, najluđi smo – znaš\n"
         "Mala, mogla si da me imaš,\n"
         "u Panameri da se snimaš\n")


@pytest.fixture()
def run(corpus_db, data_dir, capsys, monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda *a: pytest.fail("the CLI must never prompt"))

    def _run(*argv, db=corpus_db):
        code = cli.main([str(a) for a in argv], lyrics_db=db, data_dir=data_dir)
        out = capsys.readouterr()
        return code, out.out, out.err
    return _run


@pytest.fixture()
def verse(tmp_path):
    f = tmp_path / "verse.txt"
    f.write_text(VERSE, encoding="utf-8")
    return f


def _db(data_dir):
    return votes.connect(data_dir / "mairina.db")


def _con(tmp_path, name):
    """A mairina db with the stars table. Rows are never committed: a connection
    reads its own writes, and every commit costs real disk time."""
    con = votes.connect(tmp_path / f"{name}.db")
    fingerprint.ensure(con)
    return con


def _add(con, **feats):
    """Insert a star row with chosen features (no analysis needed)."""
    base = {"syllables": 9, "words": 5, "cons_density": 0.4, "end_tail": 4, "multi_len": 0,
            "allit": False, "kinds": []}
    base.update(feats)
    tags = base.pop("tags", [])
    lane = base.pop("lane", "drill")
    con.execute("INSERT INTO stars(ts, file, line_no, text, lane, tags_json, feats_json) "
                "VALUES ('2026-01-01T00:00:00', 'f.txt', 1, 'x', ?, ?, ?)",
                (lane, json.dumps(tags), json.dumps(base)))


# --- star / stars / unstar ------------------------------------------------------------

def test_star_stars_unstar_round_trip(run, verse, data_dir):
    code, out, _ = run("star", verse, 2, "--tag", "Punchline", "--tag", "double-meaning",
                       "--lane", "drill")
    assert code == 0 and out.startswith("★ #1 line 2 ")
    assert "s tobom uvek ludilo" in out and "[punchline, double-meaning]" in out
    code, out, _ = run("stars")
    assert code == 0 and "1 star(s)" in out and "#1" in out and "line 2" in out
    assert "No stars yet" in run("stars", "--lane", "pop")[1]
    row = _db(data_dir).execute("SELECT line_no, text, lane, tags_json, feats_json FROM stars").fetchone()
    assert row[:3] == (2, "s tobom uvek ludilo", "drill")
    assert json.loads(row[3]) == ["punchline", "double-meaning"]
    feats = json.loads(row[4])
    assert feats["syllables"] == count_line("s tobom uvek ludilo") and feats["words"] == 4
    assert feats["end_tail"] == len(keys.tail_key("ludilo", 2))
    assert {"cons_density", "multi_len", "allit", "kinds"} <= set(feats)
    code, out, _ = run("unstar", 1)
    assert code == 0 and "Removed" in out
    assert "No stars yet" in run("stars")[1]
    code, _, err = run("unstar", 1)
    assert code == 1 and "No star #1" in err


def test_starring_the_same_line_again_merges_tags_instead_of_double_counting(run, verse, data_dir):
    run("star", verse, 3, "--tag", "metaphor")
    code, out, _ = run("star", verse, 3, "--tag", "wordplay", "--tag", "metaphor")
    assert code == 0 and "(updated)" in out and "[metaphor, wordplay]" in out
    con = _db(data_dir)
    assert con.execute("SELECT COUNT(*) FROM stars").fetchone()[0] == 1
    run("star", verse, 3, "--lane", "drill")          # another lane is a separate star
    assert con.execute("SELECT COUNT(*) FROM stars").fetchone()[0] == 2


def test_line_numbers_are_the_xray_row_numbers(run, verse):
    lines = fingerprint.lyric_lines(verse)
    assert len(lines) == 6 and lines[2].startswith("(niko")      # header and blank line skipped
    code, xray, _ = run("xray", verse)
    assert len([r for r in xray.splitlines()[1:]]) == 6
    code, out, _ = run("star", verse, 3)
    assert code == 0 and "line 3" in out and "(niko ne pomisli da spava)" in out


def test_star_input_errors_exit_1_and_write_nothing(run, verse, tmp_path, data_dir):
    for n in (0, 7, -1):
        code, _, err = run("star", verse, n)
        assert code == 1 and "out of range" in err and "6 lyric line" in err
    code, _, err = run("star", tmp_path / "nope.txt", 1)
    assert code == 1 and "not found" in err
    code, _, err = run("star", verse, 1, "--tag", "   ")
    assert code == 1 and "Empty tag" in err
    code, _, err = run("star", verse, 1, "--tag", "x" * 41)
    assert code == 1 and "too long" in err
    assert _db(data_dir).execute("SELECT COUNT(*) FROM stars").fetchone()[0] == 0
    with pytest.raises(SystemExit):
        run("star", verse, 1, "--lane", "jazz")


def test_snapshot_features_are_mechanical_measurements(run, verse, data_dir):
    run("star", verse, 5)                                   # 'Mala, mogla si da me imaš,'
    run("star", verse, 6)                                   # 'u Panameri da se snimaš'
    rows = _db(data_dir).execute("SELECT text, feats_json FROM stars ORDER BY id").fetchall()
    f5, f6 = json.loads(rows[0][1]), json.loads(rows[1][1])
    assert f5["multi_len"] == f6["multi_len"] == 5          # shared vowel tail 'iaeia'
    assert "multisyllabic_rhyme" in f5["kinds"] and f5["kinds"] == sorted(f5["kinds"])
    assert f6["end_tail"] == len(keys.tail_key("snimaš", 2)) == 4
    assert f6["allit"] is False                             # se+snimaš: clitic, not alliteration
    assert f5["syllables"] == count_line(rows[0][0])


def test_star_degrades_when_lyrics_db_is_missing(run, verse, tmp_path):
    code, out, err = run("star", verse, 1, db=tmp_path / "gone" / "lyrics.db")
    assert code == 0 and "★ #1" in out and "Note:" in err


def test_read_only_commands_do_not_create_mairina_db(run, verse, data_dir):
    run("stars")
    run("me")
    run("xray", verse)
    code, _, err = run("unstar", 1)
    assert code == 1 and not (data_dir / "mairina.db").exists()


# --- fingerprint maths ----------------------------------------------------------------

def test_shrinkage_matches_the_empirical_bayes_formula(tmp_path):
    con = _con(tmp_path, "m")
    for _ in range(3):
        _add(con, syllables=9)
    fp = fingerprint.fingerprint(con, "drill", {"syllables": (12.0, 3.0)})
    s = fp["numeric"]["syllables"]
    assert fp["n"] == 3 and s["mean"] == 9.0
    assert s["shrunk"] == pytest.approx((3 * 9 + 8 * 12) / (3 + 8))      # 11.18...
    assert s["mu"] == 12.0 and s["sigma"] == 3.0 and s["sigma_source"] == "lane"
    for _ in range(5):
        _add(con, syllables=9)
    s = fingerprint.fingerprint(con, "drill", {"syllables": (12.0, 3.0)})["numeric"]["syllables"]
    assert s["shrunk"] == pytest.approx((8 * 9 + 8 * 12) / 16)          # n == k: halfway


def test_more_stars_pull_the_fingerprint_toward_your_mean(tmp_path):
    con = _con(tmp_path, "m")
    shrunk = []
    for _ in range(40):
        _add(con, syllables=6)
        shrunk.append(fingerprint.fingerprint(con, "drill", {"syllables": (12.0, 3.0)}
                                              )["numeric"]["syllables"]["shrunk"])
    assert shrunk == sorted(shrunk, reverse=True) and 12 > shrunk[0] > shrunk[-1] > 6


def test_low_confidence_flag_and_rates(tmp_path):
    con = _con(tmp_path, "m")
    for i in range(9):
        _add(con, tags=["punchline"] if i < 3 else [], kinds=["simile"] if i % 3 == 0 else [],
             allit=i < 2)
    fp = fingerprint.fingerprint(con, "drill", {})
    assert fp["n"] == 9 and fp["low_confidence"] is True
    assert fp["tag_rates"] == {"punchline": pytest.approx(3 / 9)}
    assert fp["kind_rates"] == {"simile": pytest.approx(3 / 9)}
    assert fp["allit_rate"] == pytest.approx(2 / 9)
    _add(con)
    assert fingerprint.fingerprint(con, "drill", {})["low_confidence"] is False     # n == 10


def test_sigma_falls_back_to_the_stars_then_to_one_and_no_prior_means_plain_mean(tmp_path):
    con = _con(tmp_path, "m")
    for syl in (8, 10):
        _add(con, syllables=syl)
    no_prior = fingerprint.fingerprint(con, "drill", None)["numeric"]["syllables"]
    assert no_prior["shrunk"] == 9.0 and no_prior["mu"] is None
    assert no_prior["sigma"] == pytest.approx(1.0) and no_prior["sigma_source"] == "stars"
    zero_sigma = fingerprint.fingerprint(con, "drill", {"syllables": (12.0, 0.0)})["numeric"]["syllables"]
    assert zero_sigma["sigma_source"] == "stars" and zero_sigma["sigma"] == pytest.approx(1.0)
    assert zero_sigma["shrunk"] == pytest.approx((2 * 9 + 8 * 12) / 10)         # prior mean still used
    con2 = _con(tmp_path, "m2")
    _add(con2, syllables=9)
    only = fingerprint.fingerprint(con2, "drill", None)["numeric"]["syllables"]
    assert only["sigma"] == 1.0 and only["sigma_source"] == "default"


def test_lane_semantics_all_pools_every_star(tmp_path):
    con = _con(tmp_path, "m")
    _add(con, lane="drill")
    _add(con, lane="pop")
    assert fingerprint.fingerprint(con, "drill")["n"] == 1
    assert fingerprint.fingerprint(con, "pop")["n"] == 1
    assert fingerprint.fingerprint(con, "all")["n"] == 2
    assert [r["lane"] for r in fingerprint.stars(con)] == ["drill", "pop"]
    assert fingerprint.fingerprint(con, "pop")["n"] == 1 and not fingerprint.unstar(con, 99)


# --- compare --------------------------------------------------------------------------

def _fp(tmp_path, n=3):
    con = _con(tmp_path, "m")
    for _ in range(n):
        _add(con, syllables=9, words=5, cons_density=0.4, end_tail=4, allit=False)
    priors = {"syllables": (9.0, 3.0), "words": (5.0, 2.0), "cons_density": (0.4, 0.2),
              "end_tail": (4.0, 1.0), "allit": (0.0, 0.5)}
    return fingerprint.fingerprint(con, "drill", priors)


def test_compare_names_the_largest_deviations_in_plain_words(tmp_path):
    fp = _fp(tmp_path)
    text = "mala mogla si da"                                   # 6 syllables, 4 words
    assert count_line(text) == 6
    out = fingerprint.compare(text, fp)
    assert "shorter than your ★ lines: 6 vs 9 syllables (n=3)" in out


def test_compare_orders_by_abs_z_and_returns_at_most_three(tmp_path):
    fp = _fp(tmp_path)
    dev = fingerprint.deviations("da me", fp)                   # clitics only
    zs = [abs(z) for _f, z, _p in dev]
    assert zs == sorted(zs, reverse=True) and len(dev) >= 4
    assert [f for f, _z, _p in dev][:3] == ["end_tail", "syllables", "cons_density"]
    out = fingerprint.compare("da me", fp)
    assert len(out) == 3
    assert out[0] == "shorter end-rhyme tail than your ★ lines: 0 vs 4 letters (n=3)"
    assert out[1] == "shorter than your ★ lines: 2 vs 9 syllables (n=3)"
    assert out[2] == "sparser consonance than your ★ lines: 0.00 vs 0.40 (n=3)"
    assert fingerprint.compare("da me", fp, top=1) == out[:1]


def test_compare_directions_and_alliteration_wording(tmp_path):
    fp = _fp(tmp_path)
    long_line = "pet puta pada preko puta pustog puta"
    out = " | ".join(fingerprint.compare(long_line, fp, top=5))
    assert "longer than your ★ lines" in out or "more words" in out
    assert "alliteration here; your ★ lines run only ~0% alliterative" in out
    quiet = " | ".join(fingerprint.compare("mala voda", dict(
        fp, numeric={**fp["numeric"],
                     "allit": dict(fp["numeric"]["allit"], mean=0.7, shrunk=0.7)}), top=5))
    assert "no alliteration here; your ★ lines run ~70% alliterative (n=3)" in quiet
    typical = "mala mogla si da me imaš sad"                    # near the fingerprint everywhere
    near = fingerprint.deviations(typical, fp)
    assert all(abs(z) >= fingerprint.MIN_Z for _f, z, _p in near)


def test_compare_is_empty_without_stars_or_deviation(tmp_path):
    empty = fingerprint.fingerprint(_con(tmp_path, "e"), "drill", {})
    assert empty["n"] == 0 and fingerprint.compare("bilo sta", empty) == []
    assert fingerprint.compare("bilo sta", None) == []
    fp = _fp(tmp_path)
    exact = {k: dict(v) for k, v in fp["numeric"].items()}
    for f in exact.values():
        f["sigma"] = 1e9                                       # nothing can deviate
    assert fingerprint.compare("bilo sta", dict(fp, numeric=exact)) == []


# --- CLI: me / xray vs★ ---------------------------------------------------------------

def test_me_prints_the_fingerprint_with_low_confidence(run, verse, data_dir):
    code, out, _ = run("me", "--lane", "drill")
    assert code == 0 and "No stars yet" in out
    for n in (1, 5, 6):
        run("star", verse, n, "--lane", "drill", "--tag", "punchline" if n > 1 else "metaphor")
    code, out, _ = run("me", "--lane", "drill")
    assert code == 0 and "n=3" in out and "low confidence (<10 stars)" in out
    assert "syllables" in out and "cons_density" in out and "end_tail" in out
    assert "punchline 67%" in out and "metaphor 33%" in out
    assert "lane mu" in out
    assert not any(l.startswith(("Usne", "u Panameri")) for l in out.splitlines())   # numbers only
    assert "No stars yet" in run("me", "--lane", "pop")[1]
    for sid in (1, 2, 3):
        run("unstar", sid)
    assert "No stars yet" in run("me", "--lane", "drill")[1]


def test_me_without_a_corpus_prior_uses_plain_means(run, verse, tmp_path):
    missing = tmp_path / "gone" / "lyrics.db"
    run("star", verse, 1, db=missing)
    code, out, err = run("me", db=missing)
    assert code == 0 and "n=1" in out and "no corpus prior" in out and "Note:" in err


def test_xray_adds_vs_star_only_from_three_stars(run, verse, data_dir):
    def vs_rows():
        code, out, _ = run("xray", verse, "--lane", "drill")
        assert code == 0
        return [l for l in out.splitlines()[1:] if "vs★" in l], len(out.splitlines()) - 1

    run("star", verse, 1, "--lane", "drill")
    run("star", verse, 2, "--lane", "drill")
    assert vs_rows()[0] == []                               # 2 stars: no column
    run("star", verse, 6, "--lane", "drill")
    rows, total = vs_rows()
    assert total == 6 and len(rows) == 6                    # 3 stars: every line gets one
    assert all(" | vs★ " in r for r in rows)
    assert any("your ★ lines" in r for r in rows)
    assert not any("alliterat" in r.split("vs★", 1)[1] for r in rows)    # the row shows allit ✓ itself
    assert all(r.endswith("(n=3)") for r in rows)           # low n is always said, 'close to' too
    assert list(data_dir.glob("atlas_*.pkl"))               # priors came from the cached atlas
    code, out, _ = run("xray", verse, "--lane", "pop")
    assert "vs★" not in out                                 # no pop stars
    code, out, _ = run("xray", verse, "--lane", "all")
    assert "vs★" in out                                     # 'all' pools every star
    run("unstar", 3)
    assert vs_rows()[0] == []                               # back to 2 stars: column gone


def test_star_fingerprint_compare_round_trip_through_the_atlas(run, verse, data_dir, corpus_db):
    for n in (1, 2, 3):
        run("star", verse, n, "--lane", "drill")
    blob = atlas.load(corpus_db, data_dir, notify=False)
    priors = atlas.lane_numeric(blob, "drill")
    fp = fingerprint.fingerprint(_db(data_dir), "drill", priors)
    assert fp["n"] == 3 and set(fp["numeric"]) == set(devices.NUMERIC_FEATURES)
    mu, sigma = priors["syllables"]
    rows = [json.loads(r[0])["syllables"] for r in
            _db(data_dir).execute("SELECT feats_json FROM stars")]
    mean = sum(rows) / 3
    assert fp["numeric"]["syllables"]["shrunk"] == pytest.approx((3 * mean + 8 * mu) / 11)
    if sigma > 0:
        assert math.isclose(fp["numeric"]["syllables"]["sigma"], sigma)
    else:                                               # fixture lane has one syllable count
        assert fp["numeric"]["syllables"]["sigma_source"] == "stars"
    # the words quote the stars' own raw means, computed here independently of the module
    feats = [json.loads(r[0]) for r in _db(data_dir).execute("SELECT feats_json FROM stars")]
    raw = {f: sum(float(x[f]) for x in feats) / 3 for f in ("syllables", "words", "end_tail")}
    devs = {f: p for f, _z, p in fingerprint.deviations("u panameri da se snimaš", fp)}
    assert devs and all(p.endswith("(n=3)") for p in devs.values())
    for f, unit in (("syllables", " syllables"), ("words", ""), ("end_tail", " letters")):
        if f in devs:
            assert f" vs {fingerprint._n(raw[f])}{unit} (n=3)" in devs[f]
    assert fp["numeric"]["syllables"]["shrunk"] != fp["numeric"]["syllables"]["mean"]   # they differ
    assert "syllables" in devs or "words" in devs or "end_tail" in devs


def test_snapshot_allit_and_kinds_count_strong_alliteration_only():
    rep = devices.analyze_verse(["kučka kuca kroz kapiju", "sala šalju", "mala voda"])
    strong, weak, none = (fingerprint.snapshot(lr) for lr in rep.lines)
    assert strong["allit"] is True and "alliteration" in strong["kinds"]
    assert weak["allit"] is False and "alliteration" not in weak["kinds"]
    assert any(d["kind"] == "alliteration" and d["confidence"] == "low" for d in rep.lines[1].devices)
    assert none["allit"] is False
    # compare() measures the line with the very same definition
    assert fingerprint._values("kučka kuca kroz kapiju")["allit"] == 1.0
    assert fingerprint._values("sala šalju")["allit"] == 0.0


# --- wave 2R: raw-mean wording, n flag, wordless lines, lane 'all', feats version ---------

RAW_PRIORS = {"syllables": (12.0, 3.0), "words": (7.0, 2.0), "cons_density": (0.8, 0.2),
              "end_tail": (5.0, 1.0), "allit": (0.5, 0.5)}


def _raw_fp(tmp_path, name="raw"):
    """3 stars whose raw means (8 syl, 4 words, ...) differ clearly from the shrunk values."""
    con = _con(tmp_path, name)
    for i in range(3):
        _add(con, syllables=8, words=4, cons_density=0.5, end_tail=3, allit=i == 0)
    return fingerprint.fingerprint(con, "drill", RAW_PRIORS)


def test_phrases_quote_the_raw_star_mean_and_the_shrunk_value_only_ranks(tmp_path):
    fp = _raw_fp(tmp_path)
    nf = fp["numeric"]
    assert nf["syllables"]["mean"] == 8 and nf["syllables"]["shrunk"] == pytest.approx(120 / 11)
    dev = {f: (z, p) for f, z, p in fingerprint.deviations("da me", fp)}       # clitics only
    assert dev["syllables"][1] == "shorter than your ★ lines: 2 vs 8 syllables (n=3)"
    assert dev["words"][1] == "fewer words than your ★ lines: 2 vs 4 (n=3)"
    assert dev["cons_density"][1] == "sparser consonance than your ★ lines: 0.00 vs 0.50 (n=3)"
    assert dev["end_tail"][1] == "shorter end-rhyme tail than your ★ lines: 0 vs 3 letters (n=3)"
    assert dev["allit"][1] == "no alliteration here; your ★ lines run ~33% alliterative (n=3)"
    # z is still measured against the shrunk mean and the lane sigma (ranking only)
    assert dev["syllables"][0] == pytest.approx((2 - 120 / 11) / 3.0)
    for _z, phrase in dev.values():
        for shrunk_text in ("10.9", "6.2", "0.72", "4.5", "45%"):      # the shrunk values
            assert shrunk_text not in phrase


def test_phrases_carry_the_actual_n_below_ten_stars_and_none_from_ten(tmp_path):
    line = "pet puta pada preko puta pustog puta"
    for n in (1, 3, 9, 10, 40):
        con = _con(tmp_path, f"n{n}")
        for _ in range(n):
            _add(con, syllables=6, words=3, cons_density=0.2, end_tail=2, allit=False)
        phrases = fingerprint.compare(line, fingerprint.fingerprint(con, "drill", RAW_PRIORS), top=5)
        assert len(phrases) >= 2, n
        if n < 10:
            assert all(p.endswith(f" (n={n})") for p in phrases), phrases
        else:
            assert not any("(n=" in p for p in phrases), phrases


def test_a_line_between_the_raw_and_the_shrunk_mean_gets_no_contradicting_sentence(tmp_path):
    fp = _raw_fp(tmp_path)                       # raw mean 8 syllables, shrunk 10.9
    between, equal = "u panameri da se snimaš", "usne crvene ko lava"
    assert (count_line(between), count_line(equal)) == (9, 8)
    for text in (between, equal):                # '9 vs 8' beside a below-prior z would lie
        assert "syllables" not in {f for f, _z, _p in fingerprint.deviations(text, fp)}
    assert "syllables" in {f for f, _z, _p in fingerprint.deviations("da me", fp)}


def test_stars_on_wordless_lines_are_rejected_and_nothing_is_stored(run, tmp_path, data_dir):
    f = tmp_path / "w.txt"
    f.write_text("...\n123\n— —\nreal words here\n", encoding="utf-8")
    for n in (1, 2, 3):
        code, out, err = run("star", f, n)
        assert code == 1 and "no words" in err and out == ""
    con = _db(data_dir)
    assert con.execute("SELECT COUNT(*) FROM stars").fetchone()[0] == 0
    with pytest.raises(votes.VoteError, match="no words"):
        fingerprint.star(con, f, 2)
    code, out, _ = run("star", f, 4)                        # a real line still works
    assert code == 0 and "real words here" in out
    assert con.execute("SELECT COUNT(*) FROM stars").fetchone()[0] == 1


def test_a_star_saved_with_the_default_lane_counts_in_every_lane_view(run, verse, data_dir):
    for n in (1, 2, 6):
        run("star", verse, n)                               # default lane 'all'
    run("star", verse, 3, "--lane", "pop")                  # a lane-specific star
    con = _db(data_dir)
    lanes = lambda lane: [r["lane"] for r in fingerprint.stars(con, lane)]
    assert lanes("drill") == ["all", "all", "all"]          # 'all' stars in, the pop star out
    assert lanes("pop") == ["all", "all", "all", "pop"]
    assert lanes("all") == lanes(None) == ["all", "all", "all", "pop"]
    assert fingerprint.fingerprint(con, "drill")["n"] == 3
    code, out, _ = run("me", "--lane", "drill")
    assert code == 0 and "n=3" in out and "No stars yet" not in out
    assert "3 star(s)" in run("stars", "--lane", "drill")[1]
    code, out, _ = run("xray", verse, "--lane", "drill")
    rows = out.splitlines()[1:]
    assert len(rows) == 6 and all(" | vs★ " in r and r.endswith("(n=3)") for r in rows)
    code, out, _ = run("xray", verse, "--lane", "pop")      # the pop star joins the pop view only
    assert all(r.endswith("(n=4)") for r in out.splitlines()[1:])


def test_new_star_snapshots_carry_the_feats_version_and_old_rows_read_as_zero(
        run, verse, data_dir, tmp_path):
    run("star", verse, 2)
    stored = json.loads(_db(data_dir).execute("SELECT feats_json FROM stars").fetchone()[0])
    assert fingerprint.FEATS_VERSION == 1 and stored["feats_version"] == 1
    assert fingerprint.stars(_db(data_dir))[0]["feats"]["feats_version"] == 1
    old = _con(tmp_path, "old")
    _add(old)                                               # a snapshot written before the key
    assert "feats_version" not in json.loads(old.execute("SELECT feats_json FROM stars").fetchone()[0])
    assert fingerprint.stars(old)[0]["feats"]["feats_version"] == 0
    assert fingerprint.fingerprint(old, "drill", {})["n"] == 1          # still usable, no migration
