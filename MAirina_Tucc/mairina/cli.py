"""Command line: anchors, rhyme, multi, vote, used, flow, stats. Never prompts."""

from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

from mairina import DATA_DIR, LANES, RANKER_VERSION, anchors as anchors_mod, corpus, flow as flow_mod
from mairina import multis as multis_mod, rank, used as used_mod, votes

HINT = "Hint: relax --artist, lower --fresh, or try --mode assonance / --lane all."
_VOTE = re.compile(r"^(\d+)([+-])$")


def _fresh(s: str) -> float:
    v = float(s)
    if not 0.0 <= v <= 1.0:
        raise argparse.ArgumentTypeError("must be between 0.0 and 1.0")
    return v


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mt", description="MAirina Tucc v1: it finds, you write.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, rng=True):
        sp.add_argument("--lane", choices=LANES, default="all")
        sp.add_argument("--fresh", type=_fresh, default=0.5)
        sp.add_argument("--artist", default=None, help="comma-separated target_artist slugs")
        if rng:
            sp.add_argument("--rng-seed", type=int, default=None)

    a = sub.add_parser("anchors", help="one end-word per line, grouped by rhyme scheme")
    a.add_argument("--scheme", default="AABB")
    a.add_argument("--lines", type=int, default=None)
    a.add_argument("--mode", choices=anchors_mod.MODES, default="rhyme")
    a.add_argument("--seed", default=None, help="word that fixes group A's rhyme class")
    common(a)
    r = sub.add_parser("rhyme", help="ranked rhyme list for a word")
    r.add_argument("word")
    r.add_argument("--max", type=int, default=20)
    common(r)
    m = sub.add_parser("multi", help="multi-syllable rhyme combinations for an ending phrase")
    m.add_argument("phrase")
    m.add_argument("--max", type=int, default=20)
    common(m)
    v = sub.add_parser("vote", help="e.g. vote 3+ 5- 7+")
    v.add_argument("items", nargs="+")
    u = sub.add_parser("used", help="log which shown suggestions appear in your text file")
    u.add_argument("file")
    u.add_argument("--days", type=int, default=14)
    f = sub.add_parser("flow", help="syllables per line vs your median and the lane median")
    f.add_argument("file")
    f.add_argument("--lane", choices=LANES, default="all")
    s = sub.add_parser("stats", help="week-1 numbers")
    s.add_argument("--ab", action="store_true", help="learned vs base ranking arms")
    return p


def _artists(args) -> tuple:
    return tuple(x.strip() for x in (args.artist or "").split(",") if x.strip())


def _setup(args, lyrics_db, data_dir):
    """index, mairina.db connection, rng, arm, boosts (boosts only in arm learned)."""
    index = corpus.load_index(lyrics_db, data_dir)
    con = votes.connect(Path(data_dir) / "mairina.db")
    rng = random.Random(args.rng_seed)
    arm = votes.assign_arm(random.Random())      # own RNG: --rng-seed never pins the arm
    return index, con, rng, arm, (votes.boosts(con) if arm == "learned" else None)


def _pack(s: rank.Scored):
    return s.candidate, s.score, {"kind": s.kind, "features": s.features, "meta": s.meta}


def _head(title: str, args, arm: str, list_id: int) -> str:
    return (f"{title}  lane={args.lane} fresh={args.fresh} arm={arm} ranker={RANKER_VERSION} "
            f"list=#{list_id}" + (f" artist={args.artist}" if args.artist else ""))


def _cmd_anchors(args, lyrics_db, data_dir) -> int:
    index, con, rng, arm, boosts = _setup(args, lyrics_db, data_dir)
    try:
        res = anchors_mod.anchors(index, args.scheme, args.lines, args.lane, args.mode, args.seed,
                                  args.fresh, _artists(args), rng, boosts)
    except anchors_mod.NoAnchors as exc:
        print(f"No anchors: {exc}\n{HINT}")
        return 0
    items = [(a.word, a.score, {"kind": f"anchor-{a.mode}", "group": a.group, "key": a.key,
                                "features": a.features, "meta": {"freq": a.freq, "upos": a.upos, "lemma": a.lemma}})
             for a in res]
    lid = votes.log_shown(con, "anchor", f"{args.scheme}/{args.mode}/{args.seed or ''}", arm, items)
    print(_head(f"Anchors {args.scheme.upper()} ({args.mode})", args, arm, lid))
    print("Write each line so that it ends on its anchor. The tool never writes lines.")
    for a in res:
        print(f"{a.line:>3}. [{a.group}] {a.word:<16} {a.upos:<5} class -{a.key}  freq {a.freq}")
    return 0


def _cmd_rhyme(args, lyrics_db, data_dir) -> int:
    index, con, rng, arm, boosts = _setup(args, lyrics_db, data_dir)
    ctx = rank.Ctx(index, args.lane, args.fresh, _artists(args), boosts)
    res = rank.rank(args.word, ctx.vocab(), ctx)[: args.max]
    if not res:
        print(f"No rhymes found for '{args.word}' in lane '{args.lane}'.\n{HINT}")
        return 0
    lid = votes.log_shown(con, "rhyme", args.word, arm, [_pack(s) for s in res])
    print(_head(f"Rhymes for '{args.word}'", args, arm, lid))
    for i, s in enumerate(res, 1):
        print(f"{i:>3}. {s.candidate:<16} {s.score:>6.2f}  {rank.explain(s)}")
    return 0


def _cmd_multi(args, lyrics_db, data_dir) -> int:
    index, con, rng, arm, boosts = _setup(args, lyrics_db, data_dir)
    res = multis_mod.multis(index, args.phrase, args.lane, args.max, args.fresh, _artists(args), boosts)
    if not res:
        print(f"No multi-syllable rhymes for '{args.phrase}' in lane '{args.lane}'.\n{HINT}")
        return 0
    lid = votes.log_shown(con, "multi", args.phrase, arm, [_pack(s) for s in res])
    print(_head(f"Multis for '{args.phrase}'", args, arm, lid))
    for i, s in enumerate(res, 1):
        print(f"{i:>3}. {s.candidate:<28} {s.score:>6.2f}  {rank.explain(s)}")
    return 0


def _cmd_vote(args, data_dir) -> int:
    pairs = []
    for tok in args.items:
        m = _VOTE.match(tok)
        if not m:
            raise votes.VoteError(f"Cannot read '{tok}'. Use item numbers with + or -, e.g. vote 3+ 5-.")
        pairs.append((int(m.group(1)), 1 if m.group(2) == "+" else -1))
    con = votes.connect(Path(data_dir) / "mairina.db")
    n = votes.cast_votes(con, pairs)
    lid, kind, _ = votes.last_list(con)
    print(f"Saved {n} vote(s) on list #{lid} ({kind}).")
    return 0


def _cmd_used(args, data_dir) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    con = votes.connect(Path(data_dir) / "mairina.db")
    hits = used_mod.scan(path, args.days, con)
    new = [h for h in hits if votes.mark_used(con, h, str(path.resolve()))]
    print(f"{len(hits)} shown suggestion(s) from the last {args.days} days appear in {path.name} "
          f"({len(new)} newly logged).")
    for h in hits:
        print(f"  - {h}")
    return 0


def _cmd_flow(args, lyrics_db) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    print("\n".join(flow_mod.render(flow_mod.flow(path, args.lane, lyrics_db))))
    return 0


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _cmd_stats(args, data_dir) -> int:
    st = votes.stats(votes.connect(Path(data_dir) / "mairina.db"))
    if args.ab:
        print(f"Ranking A/B (votes so far: {st['votes']}, need {votes.AB_MIN_VOTES})")
        if not st["ab_ready"]:
            print("Not enough data yet. Keep voting.")
        for arm, a in st["arms"].items():
            print(f"  arm {arm:<8} lists {a['lists']:>3}  votes {a['votes']:>3}  up-rate {_pct(a['rate'])}")
        if st["ab_ready"]:
            l, b = st["arms"]["learned"]["rate"], st["arms"]["base"]["rate"]
            ok = l is not None and b is not None and l > b
            print("Verdict: learned beats base." if ok else "Verdict: learned does not beat base (yet).")
        return 0
    kinds = ", ".join(f"{k} {v['lists']} lists/{v['items']} items" for k, v in st["by_kind"].items()) or "nothing shown yet"
    print(f"Shown: {kinds}")
    print(f"Votes: {st['votes']} (up {st['up']}, down {st['down']}) up-rate {_pct(st['rate'])}")
    print(f"First 50 votes: {st['first50_votes']}/50 cast, up-rate {_pct(st['first50_rate'])} (pass: 40% or more)")
    print(f"Used: {st['used_candidates']} of {st['shown_candidates']} distinct shown suggestions ({_pct(st['used_rate'])})")
    print(f"Multi lists (first 20): {st['multi_lists']} seen, {st['multi_hits']} with an up-vote or used hit (pass: 10 of 20)")
    print("Run 'stats --ab' for the learned-vs-base test.")
    return 0


def main(argv=None, *, lyrics_db=None, data_dir=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    try:
        if args.cmd == "anchors":
            return _cmd_anchors(args, lyrics_db, data_dir)
        if args.cmd == "rhyme":
            return _cmd_rhyme(args, lyrics_db, data_dir)
        if args.cmd == "multi":
            return _cmd_multi(args, lyrics_db, data_dir)
        if args.cmd == "vote":
            return _cmd_vote(args, data_dir)
        if args.cmd == "used":
            return _cmd_used(args, data_dir)
        if args.cmd == "flow":
            return _cmd_flow(args, lyrics_db)
        return _cmd_stats(args, data_dir)
    except corpus.DbUnavailable as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except votes.VoteError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
