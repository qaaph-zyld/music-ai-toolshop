import random

import pytest

from mairina import anchors as A, keys, multis as M, rank, votes


def ctx(index, lane="all", fresh=0.5, artists=(), boosts=None):
    return rank.Ctx(index, lane, fresh, tuple(artists), boosts)


def words(res):
    return [s.candidate for s in res]


def test_rhyme_lists_perfect_matches_first_with_breakdown(index):
    c = ctx(index, "drill")
    res = rank.rank("imaš", c.vocab(), c)
    assert words(res)[0] == "snimaš"
    top = res[0]
    assert top.kind == "perfect-2" and top.features["perfect-2"] == 6.0
    assert "freq" in top.features and "fresh" in top.features
    assert "perfect-2" in rank.explain(top)
    assert "imaš" not in words(res)                    # never the target itself


def test_lane_and_artist_lens_are_hard_filters(index):
    drill = words(rank.rank("imaš", ctx(index, "drill").vocab(), ctx(index, "drill")))
    pop = words(rank.rank("imaš", ctx(index, "pop").vocab(), ctx(index, "pop")))
    assert "snimaš" in drill and "uzimaš" not in drill
    assert "uzimaš" in pop and "snimaš" not in pop
    lens = ctx(index, "all", artists=("jala",))
    assert "snimaš" not in words(rank.rank("imaš", lens.vocab(), lens))


def test_fresh_zero_removes_penalty(index):
    c0, c1 = ctx(index, fresh=0.0), ctx(index, fresh=1.0)
    r0 = rank.rank("lava", c0.vocab(), c0)[0]
    r1 = next(s for s in rank.rank("lava", c1.vocab(), c1) if s.candidate == r0.candidate)
    assert "fresh" not in r0.features and r1.features["fresh"] < 0


def test_votes_change_order_deterministically(index):
    base = ctx(index, "all")
    order = words(rank.rank("imaš", base.vocab(), base))
    assert order.index("snimaš") < order.index("uzimaš")     # more frequent first
    boosted = ctx(index, "all", boosts={"uzimaš": (5, 0, 0)})
    a = words(rank.rank("imaš", boosted.vocab(), boosted))
    b = words(rank.rank("imaš", boosted.vocab(), boosted))
    assert a == b and a.index("uzimaš") < a.index("snimaš")
    down = ctx(index, "all", boosts={"snimaš": (0, 5, 0)})
    assert words(rank.rank("imaš", down.vocab(), down)).index("uzimaš") < order.index("snimaš") + 5
    used = ctx(index, "all", boosts={"uzimaš": (0, 0, 1)})
    assert rank.rank("imaš", used.vocab(), used)[0].candidate == "uzimaš"


def test_anchors_aabb_two_groups_distinct(index):
    res = A.anchors(index, "AABB", rng=random.Random(1))
    assert [a.group for a in res] == ["A", "A", "B", "B"]
    assert len({a.word for a in res}) == 4
    assert len({a.lemma for a in res}) == 4
    assert res[0].key == res[1].key and res[2].key == res[3].key and res[0].key != res[2].key
    assert all(a.upos in A.CONTENT_POS for a in res)
    assert not {a.word for a in res} & {"da", "me", "te", "je", "ne"}


def test_anchors_deterministic_with_rng_seed_and_varied_without(index):
    same = [[a.word for a in A.anchors(index, rng=random.Random(7))] for _ in range(3)]
    assert same[0] == same[1] == same[2]
    seen = {tuple(a.word for a in A.anchors(index, rng=random.Random(s))) for s in range(20)}
    assert len(seen) > 1


def test_anchors_seed_sets_group_a(index):
    for s in range(5):
        res = A.anchors(index, "AABB", seed="grade", rng=random.Random(s))
        assert res[0].key == res[1].key == keys.tail_key("grade")
        assert "grade" not in {a.word for a in res}


def test_anchors_lane_and_scheme_length(index):
    res = A.anchors(index, "ABAB", lines=4, lane="pop", rng=random.Random(2))
    assert len(res) == 4 and len({a.word for a in res}) == 4
    assert "snimaš" not in {a.word for a in res}


@pytest.mark.parametrize("mode", ["assonance", "consonance"])
def test_anchor_modes_share_their_key(index, mode):
    res = A.anchors(index, "AABB" if mode == "assonance" else "AA", mode=mode, rng=random.Random(3))
    assert res[0].key == res[1].key and all(A.class_key(a.word, mode) == a.key for a in res)


def test_anchors_empty_result_raises_with_reason(index):
    with pytest.raises(A.NoAnchors):
        A.anchors(index, "AABB", artists=("nobody",), rng=random.Random(1))
    with pytest.raises(A.NoAnchors):
        A.anchors(index, "AABB", seed="xyz", rng=random.Random(1))


def test_multi_skeleton_ends_with_target_and_final_is_content(index):
    res = M.multis(index, "da me imaš")
    assert res and all(w.endswith(" snimaš") for w in words(res))
    assert {w.split()[0] for w in words(res)} <= {"sade", "grade", "pade"}
    for s in res:
        assert s.meta["skeleton"].endswith("aeia")
        ws = s.meta["words"]
        assert index.forms[ws[-1]]["upos"] in A.CONTENT_POS
        assert all(w in index.forms for w in ws)               # vocabulary words only
        assert len(ws) <= 3
    assert all(s.candidate.split()[-1] != "imaš" for s in res)


def test_multi_at_most_one_glue_word_never_adjacent(index, monkeypatch):
    monkeypatch.setattr(M, "MAX_PER_FINAL", 99)          # see every combination, not just the capped top
    monkeypatch.setattr(M, "MAX_PER_FIRST", 99)
    res = M.multis(index, "da me imaš", max_results=200)
    assert "da te snimaš" not in words(res)                    # two glue words
    for s in res:
        ws = s.meta["words"]
        assert sum(w in M.GLUE for w in ws) <= 1
        assert not any(a in M.GLUE and b in M.GLUE for a, b in zip(ws, ws[1:]))
    assert any(sum(w in M.GLUE for w in s.meta["words"]) == 1 for s in res)   # one is still fine


def test_multi_final_never_proper_noun_or_artist_name(index):
    res = M.multis(index, "da me imaš")
    assert "melisa" in index.forms and index.forms["melisa"]["upos"] == "PROPN"
    assert "senida" in index.forms and "senida" in index.artist_names
    assert not any(s.meta["words"][-1] in ("melisa", "senida") for s in res)
    assert not any("senida" in s.candidate.split() for s in res)      # also not in other slots


def test_multi_diversity_caps(index, monkeypatch):
    res = M.multis(index, "da me imaš", max_results=50)
    finals = [s.meta["words"][-1] for s in res]
    firsts = [s.meta["words"][0] for s in res]
    assert all(finals.count(f) <= M.MAX_PER_FINAL for f in finals)
    assert all(firsts.count(f) <= M.MAX_PER_FIRST for f in firsts)
    assert (M.MAX_PER_FINAL, M.MAX_PER_FIRST) == (2, 3)
    monkeypatch.setattr(M, "MAX_PER_FINAL", 1)
    monkeypatch.setattr(M, "MAX_PER_FIRST", 1)
    tight = M.multis(index, "da me imaš", max_results=50)
    assert 0 < len(tight) < len(res)
    assert len({s.meta["words"][-1] for s in tight}) == len(tight) == len({s.meta["words"][0] for s in tight})


def test_multi_max_and_lane(index):
    assert len(M.multis(index, "da me imaš", max_results=2)) <= 2
    assert all("snimaš" not in s.candidate for s in M.multis(index, "da me imaš", lane="pop"))
    assert M.multis(index, "xyz") == []


def test_votes_boosts_roundtrip(tmp_path):
    con = votes.connect(tmp_path / "m.db")
    lid = votes.log_shown(con, "rhyme", "imaš", "learned", [("snimaš", 1.0, {}), ("uzimaš", 0.9, {})])
    votes.cast_votes(con, [(2, 1), (2, 1), (1, -1)])
    b = votes.boosts(con)
    assert b["uzimaš"] == (1, 0, 0) and b["snimaš"] == (0, 1, 0)      # latest vote per item counts
    assert lid == 1


@pytest.mark.parametrize("a,b", [("nekad", "ponekad"), ("padnem", "upadnem"), ("nemirna", "mirna"),
                                 ("srolam", "rolam"), ("grabim", "zgrabim")])
def test_conflict_word_and_its_own_extension(a, b):
    assert A.conflict(a, b) and A.conflict(b, a)


def test_no_conflict_for_real_rhymes():
    assert not A.conflict("lava", "spava") and not A.conflict("snimaš", "uzimaš")
    assert A.conflict("lava", "glava")                 # glava ends with lava


def test_anchors_never_pair_a_word_with_its_extension(index):
    for s in range(60):
        res = A.anchors(index, "AABB", rng=random.Random(s))
        for g in "AB":
            w = [a.word for a in res if a.group == g]
            assert not A.conflict(w[0], w[1]), w
        assert not {"nekad", "ponekad"} <= {a.word for a in res}


def test_anchor_seed_with_only_an_extension_class_fails(index):
    with pytest.raises(A.NoAnchors):
        A.anchors(index, "AA", seed="nekad", rng=random.Random(1))       # ponekad is nekad's extension


def test_anchors_min_freq_is_five(index, monkeypatch):
    assert A.MIN_FREQ == 5 and index.forms["trava"]["freq"] == 4
    assert index.forms["lava"]["freq"] > 5
    for s in range(30):
        assert "trava" not in {a.word for a in A.anchors(index, "AABB", rng=random.Random(s))}
    with pytest.raises(A.NoAnchors):     # lava/glava conflict, trava is below the floor
        A.anchors(index, "AA", seed="spava", rng=random.Random(1))
    monkeypatch.setattr(A, "MIN_FREQ", 3)
    res = A.anchors(index, "AA", seed="spava", rng=random.Random(1))
    assert "trava" in {a.word for a in res}


def test_anchors_and_rhymes_exclude_artist_names(index):
    c = ctx(index)
    assert "senida" not in c.vocab()
    assert "senida" not in words(rank.rank("nida", c.vocab(), c))
    for s in range(30):
        assert "senida" not in {a.word for a in A.anchors(index, "AABB", mode="assonance", rng=random.Random(s))}


def test_artist_lens_intersects_lane_in_rank(index):
    lens = ctx(index, "drill", artists=("jala",))
    assert rank.rank("imaš", lens.vocab(), lens) == []                # jala has no drill songs
    both = ctx(index, "all", artists=("jala",))
    got = words(rank.rank("imaš", both.vocab(), both))
    assert got[0] == "uzimaš" and "snimaš" not in got
    dev = ctx(index, "drill", artists=("devito",))
    got = words(rank.rank("imaš", dev.vocab(), dev))
    assert got[0] == "snimaš" and "uzimaš" not in got
