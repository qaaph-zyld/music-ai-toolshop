"""Command line: anchors, rhyme, multi, vote, used, flow, xray, star, stars, unstar, me,
hint-vote, atlas, compare, stats. Never prompts."""

from __future__ import annotations

import argparse
import random
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

from mairina import DATA_DIR, LANES, RANKER_VERSION, anchors as anchors_mod, corpus, devices
from mairina import atlas as atlas_mod, bans, comparisons, dialect as dialect_mod, fingerprint, hints
from mairina import flow as flow_mod, multis as multis_mod, rank, rules, targets
from mairina import used as used_mod, votes

HINT = "Hint: relax --artist, lower --fresh, or try --mode assonance / --lane all."
# compare has no --mode, and --fresh only re-ranks (it never empties a result)
COMPARE_HINT = "Hint: relax --artist or --theme, or try --lane all."
_VOTE = re.compile(r"^(\d+)([+-])$")
_CLIP = 60


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
        sp.add_argument("--dialect", choices=("all", "ekavica"), default="all",
                        help="ekavica drops ijekavian forms from suggestions")
        if rng:
            sp.add_argument("--rng-seed", type=int, default=None)

    a = sub.add_parser("anchors", help="one end-word per line, grouped by rhyme scheme")
    a.add_argument("--scheme", default="AABB")
    a.add_argument("--lines", type=int, default=None)
    a.add_argument("--mode", choices=anchors_mod.MODES, default="rhyme")
    a.add_argument("--seed", default=None, help="word that fixes group A's rhyme class")
    a.add_argument("--lock", action="append", default=[], metavar="G:WORD",
                   help="fix group G's rhyme class with WORD (repeatable; falls back gracefully)")
    a.add_argument("--section", choices=targets.SECTION_TYPES, default="strofa",
                   help="section type for the syllable target range")
    common(a)
    r = sub.add_parser("rhyme", help="ranked rhyme list for a word")
    r.add_argument("word")
    r.add_argument("--max", type=int, default=20)
    r.add_argument("--line", default=None, help="line so far (shapes syllable-fit and sound)")
    r.add_argument("--target", type=int, default=None, help="target syllable count for the line")
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
    x = sub.add_parser("xray", help="compact craft analysis per line (advisory tags only)")
    x.add_argument("file")
    x.add_argument("--lane", choices=LANES, default="all")
    x.add_argument("--section", choices=targets.SECTION_TYPES, default="strofa")
    st = sub.add_parser("star", help="star one of your own lines (use the number xray prints)")
    st.add_argument("file")
    st.add_argument("line_no", type=int, help="lyric-line number as in xray (blank lines and [headers] skipped)")
    st.add_argument("--tag", action="append", default=[], metavar="TAG",
                    help="metaphor | double-meaning | wordplay | punchline | any text; repeatable")
    st.add_argument("--lane", choices=LANES, default="all")
    sl = sub.add_parser("stars", help="list your starred lines")
    sl.add_argument("--lane", choices=LANES, default="all")
    us = sub.add_parser("unstar", help="remove a star by its id")
    us.add_argument("id", type=int)
    me = sub.add_parser("me", help="your fingerprint: starred lines vs the corpus lane")
    me.add_argument("--lane", choices=LANES, default="all")
    hv = sub.add_parser("hint-vote", help="thumbs on an xray hint rule; 3 down and 0 up mutes it")
    hv.add_argument("rule_id")
    hv.add_argument("vote", choices=("+", "-", "reset"))
    at = sub.add_parser("atlas", help="device rates per lane/artist in the corpus (stats only)")
    at.add_argument("--lane", choices=LANES, default="all")
    at.add_argument("--artist", default=None, help="comma-separated target_artist slugs")
    cp = sub.add_parser("compare", help="words that follow simile markers (ko lava -> lava)")
    cp.add_argument("--max", type=int, default=20)
    cp.add_argument("--theme", default=None, help="only comparisons from lines about this word")
    common(cp)
    bn = sub.add_parser("ban", help="never suggest this word again (undo: mt unban)")
    bn.add_argument("word")
    ub = sub.add_parser("unban", help="remove a word ban")
    ub.add_argument("word")
    bs = sub.add_parser("bans", help="list banned words")
    s = sub.add_parser("stats", help="week-1 numbers")
    s.add_argument("--ab", action="store_true", help="learned vs base ranking arms")
    sv = sub.add_parser("serve", help="run the local JSON API for rimer-ui on 127.0.0.1:8000")
    sv.add_argument("--data-dir", default=None,
                    help="mairina.db + cache directory (default MAirina_Tucc\\data)")
    return p


def _artists(args) -> tuple:
    return tuple(x.strip() for x in (args.artist or "").split(",") if x.strip())


def _clip(text: str, n: int = _CLIP) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def _open_app_db(data_dir, write: bool = False):
    """mairina.db only if it already exists (None otherwise): read-only commands
    must not create it. Read-only unless ``write``."""
    path = Path(data_dir) / "mairina.db"
    if not path.is_file():
        return None
    if write:
        return sqlite3.connect(str(path))
    return sqlite3.connect(f"file:{quote(path.resolve().as_posix(), safe='/:')}?mode=ro", uri=True)


def _create_app_db(data_dir):
    """mairina.db with the v1 tables plus stars, hint_votes and word_bans (all IF NOT EXISTS)."""
    con = votes.connect(Path(data_dir) / "mairina.db")
    fingerprint.ensure(con)
    hints.ensure(con)
    bans.ensure(con)
    return con


def _lane_priors(lyrics_db, data_dir, lane):
    """Corpus priors for the fingerprint, or None (with a Note) when the atlas cannot be built."""
    try:
        return atlas_mod.lane_numeric(atlas_mod.load(lyrics_db, data_dir), lane)
    except corpus.DbUnavailable as exc:
        print(f"Note: {exc} - fingerprint without corpus priors (plain means).", file=sys.stderr)
        return None


def _setup(args, lyrics_db, data_dir):
    """index, mairina.db connection, rng, arm, boosts (boosts only in arm learned)."""
    index = corpus.load_index(lyrics_db, data_dir)
    con = votes.connect(Path(data_dir) / "mairina.db")
    rng = random.Random(args.rng_seed)
    arm = votes.assign_arm(random.Random())      # own RNG: --rng-seed never pins the arm
    return index, con, rng, arm, (votes.boosts(con) if arm == "learned" else None)


def _pack(s: rank.Scored):
    return s.candidate, s.score, {"kind": s.kind, "features": s.features, "meta": s.meta}


def _blocked(args, con, index) -> frozenset:
    """User bans plus (dialect=ekavica) every ijekavian corpus form."""
    out = bans.list_bans(con)
    if getattr(args, "dialect", "all") == "ekavica":
        out |= dialect_mod.ijekavian(index.forms).keys()
    return frozenset(out)


def _head(title: str, args, arm: str, list_id: int) -> str:
    return (f"{title}  lane={args.lane} fresh={args.fresh} arm={arm} ranker={RANKER_VERSION} "
            f"list=#{list_id}" + (f" artist={args.artist}" if args.artist else ""))


def _locks(specs) -> dict:
    """--lock G:WORD entries -> {group letter: word}."""
    out = {}
    for spec in specs:
        if ":" not in spec:
            raise votes.VoteError(f"--lock takes G:word (e.g. --lock B:grade), got '{spec}'.")
        g, w = spec.split(":", 1)
        if not g.strip() or not w.strip():
            raise votes.VoteError(f"--lock takes G:word (e.g. --lock B:grade), got '{spec}'.")
        out[g.strip().upper()[:1]] = w.strip()
    return out


def _cmd_anchors(args, lyrics_db, data_dir) -> int:
    index, con, rng, arm, boosts = _setup(args, lyrics_db, data_dir)
    warns: list = []
    try:
        res = anchors_mod.anchors(index, args.scheme, args.lines, args.lane, args.mode, args.seed,
                                  args.fresh, _artists(args), rng, boosts,
                                  blocked=_blocked(args, con, index),
                                  group_seeds=_locks(args.lock), warnings=warns)
    except anchors_mod.NoAnchors as exc:
        print(f"No anchors: {exc}\n{HINT}")
        return 0
    items = [(a.word, a.score, {"kind": f"anchor-{a.mode}", "group": a.group, "key": a.key,
                                "features": a.features, "meta": {"freq": a.freq, "upos": a.upos, "lemma": a.lemma}})
             for a in res]
    lid = votes.log_shown(con, "anchor", f"{args.scheme}/{args.mode}/{args.seed or ''}", arm, items)
    trange = targets.target(args.lane, args.section, lyrics_db, cache_dir=data_dir)
    print(_head(f"Anchors {args.scheme.upper()} ({args.mode})", args, arm, lid))
    print("Write each line so that it ends on its anchor. The tool never writes lines.")
    for w in warns:
        print(f"Note: {w}")
    for a in res:
        print(f"{a.line:>3}. [{a.group}] {a.word:<16} {a.upos:<5} class -{a.key}  freq {a.freq}  "
              f"syl {targets.fmt_range(trange)}")
    return 0


def _cmd_rhyme(args, lyrics_db, data_dir) -> int:
    if args.target is not None and not args.line:
        print("Error: --target needs --line (the target is for the line being written).",
              file=sys.stderr)
        return 1
    index, con, rng, arm, boosts = _setup(args, lyrics_db, data_dir)
    ctx = rank.Ctx(index, args.lane, args.fresh, _artists(args), boosts,
                   args.line, args.target, _blocked(args, con, index))
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
    res = multis_mod.multis(index, args.phrase, args.lane, args.max, args.fresh, _artists(args), boosts,
                            _blocked(args, con, index))
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


def _cmd_xray(args, lyrics_db, data_dir) -> int:
    """One compact advisory row per line: meter, rhyme group, sound, tags, hints."""
    path = Path(args.file)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    lines = fingerprint.lyric_lines(path)
    if not lines:
        print("No lyric lines to analyze.")
        return 0
    gazetteer, trange, index, cons_thr = frozenset(), None, None, None
    try:
        trange = targets.target(args.lane, args.section, lyrics_db, cache_dir=data_dir)
        cons_thr = targets.cons_thresholds(args.lane, lyrics_db, data_dir)
        gazetteer = devices.load_gazetteer(str(lyrics_db or corpus.DEFAULT_LYRICS_DB))
        index = corpus.load_index(lyrics_db, data_dir)      # 'ko = who' + name_drop filter
    except corpus.CorpusNotAnnotated:
        raise                                   # an unannotated corpus must fail, not degrade
    except corpus.DbUnavailable as exc:
        print(f"Note: {exc} — running without lane targets and gazetteer.",
              file=sys.stderr)
    rep = devices.analyze_verse(lines, gazetteer, index)
    app = _open_app_db(data_dir)                     # None until the first star/vote exists
    try:
        muted = hints.muted(app) if app else []
        star_rows = fingerprint.stars(app, args.lane) if app else []
    finally:
        if app:
            app.close()
    fp = None
    if len(star_rows) >= fingerprint.MIN_STARS_FOR_XRAY:
        priors = _lane_priors(lyrics_db, data_dir, args.lane)
        fp = fingerprint.fingerprint(None, args.lane, priors, rows=star_rows)
    line_hints: dict[int, list[str]] = {}
    for h in rules.verse_hints(lines, index=index):
        if h["rule_id"] in muted:
            continue
        line_hints.setdefault(h["line"], []).append(
            rules.SHORT_LABELS.get(h["rule_id"], h["rule_id"]))
    head = f"X-ray {len(rep.lines)} lines  lane={args.lane} section={args.section} (advisory only — you write)"
    if muted:
        head += f"  muted hints: {', '.join(muted)}"
    print(head)
    for lr in rep.lines:
        parts = [str(lr.n),
                 f"syl {lr.syllables}" + (f" ({targets.fmt_range(trange)})" if trange else ""),
                 f"rhyme {lr.rhyme_letter or '-'}",
                 f"cons {devices.gauge(lr.cons_density, cons_thr)}"]
        if "alliteration" in devices.device_kinds(lr.devices):      # strong (same phoneme) only
            parts.append("allit ✓")
        tags = [f"≈{d['kind']}({d['span']})" for d in lr.devices
                if d["kind"] not in ("alliteration", "consonance")]
        parts += tags
        if line_hints.get(lr.n):
            parts.append("hints: " + ", ".join(line_hints[lr.n]))
        if fp:
            parts.append("vs★ " + fingerprint.vs_star_phrase(lr.text, fp))  # raw ★ mean, allit skipped
        print(" | ".join(parts))
    return 0


def _cmd_star(args, lyrics_db, data_dir) -> int:
    path = Path(args.file)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    con = _create_app_db(data_dir)
    rec = fingerprint.star(con, path, args.line_no, args.lane, args.tag, lyrics_db, data_dir)
    tags = f" [{', '.join(rec['tags'])}]" if rec["tags"] else ""
    print(f"★ #{rec['id']}{' (updated)' if rec['updated'] else ''} line {rec['line_no']} "
          f"\"{_clip(rec['text'])}\"{tags} lane={rec['lane']}")
    return 0


def _cmd_stars(args, data_dir) -> int:
    con = _open_app_db(data_dir)
    rows = fingerprint.stars(con, args.lane) if con else []
    if not rows:
        print(f"No stars yet for lane '{args.lane}'. Star a line: mt star <file> <line_no> [--tag T]")
        return 0
    print(f"{len(rows)} star(s)  lane={args.lane}")
    for r in rows:
        tags = f" [{', '.join(r['tags'])}]" if r["tags"] else ""
        print(f"#{r['id']:<3} {r['lane']:<5} {Path(r['file'] or '?').name} line {r['line_no']}: "
              f"\"{_clip(r['text'])}\"{tags}")
    return 0


def _cmd_unstar(args, data_dir) -> int:
    con = _open_app_db(data_dir, write=True)
    if not (con and fingerprint.unstar(con, args.id)):
        raise votes.VoteError(f"No star #{args.id}. List them with: mt stars")
    print(f"Removed ★ #{args.id}.")
    return 0


def _cmd_me(args, lyrics_db, data_dir) -> int:
    con = _open_app_db(data_dir)
    rows = fingerprint.stars(con, args.lane) if con else []
    priors = _lane_priors(lyrics_db, data_dir, args.lane) if rows else None
    print("\n".join(fingerprint.render(
        fingerprint.fingerprint(None, args.lane, priors, rows=rows), args.lane)))
    return 0


def _cmd_hint_vote(args, data_dir) -> int:
    con = _create_app_db(data_dir)
    rid = args.rule_id.strip()
    if args.vote == "reset":                      # any well-formed id: old stray votes can go
        n = hints.reset(con, rid)
        print(f"Reset '{rid}': {n} vote(s) removed; its hints are shown again.")
        return 0
    up, down = hints.vote(con, rid, 1 if args.vote == "+" else -1)
    print(f"Hint '{rid}': {up} up / {down} down.")
    if rid in hints.muted(con):
        print(f"Muted: xray no longer shows '{rid}' (undo: mt hint-vote {rid} reset).")
    return 0


def _cmd_atlas(args, lyrics_db, data_dir) -> int:
    blob = atlas_mod.load(lyrics_db, data_dir)
    print("\n".join(atlas_mod.render(blob, args.lane, _artists(args))))
    return 0


def _cmd_compare(args, lyrics_db, data_dir) -> int:
    theme = None
    if args.theme:
        words = used_mod.tokenize(args.theme)
        if len(words) != 1:
            raise votes.VoteError("--theme takes exactly one word.")
        theme = words[0]
    index, con, rng, arm, boosts = _setup(args, lyrics_db, data_dir)
    blocked = _blocked(args, con, index)
    counts = comparisons.collect(lyrics_db, args.lane, _artists(args), theme, index, blocked)
    res = comparisons.rank_words(counts, index, args.lane, _artists(args), args.fresh,
                                 boosts, blocked)[: args.max]
    if not res:
        print(f"No comparison words found in lane '{args.lane}'"
              + (f" for theme '{theme}'" if theme else "") + f".\n{COMPARE_HINT}")
        return 0
    lid = votes.log_shown(con, "compare", f"lane={args.lane},theme={theme or ''}", arm,
                          [_pack(s) for s in res])
    print(_head("Comparisons (single words after kao/ko/k'o/poput)", args, arm, lid)
          + (f" theme={theme}" if theme else ""))
    for i, s in enumerate(res, 1):
        print(f"{i:>3}. {s.candidate:<16} {s.score:>6.2f}  {s.meta['count']:>3}x  {rank.explain(s)}")
    return 0


def _cmd_ban(args, data_dir) -> int:
    con = _create_app_db(data_dir)
    try:
        w = bans.ban(con, args.word)
    finally:
        con.close()
    print(f"Banned '{w}' — anchors, rhymes, multis and compare skip it. (undo: mt unban {w})")
    return 0


def _cmd_unban(args, data_dir) -> int:
    con = _open_app_db(data_dir, write=True)
    try:
        removed = bool(con) and bans.unban(con, args.word)
    finally:
        if con:
            con.close()
    if not removed:
        print(f"'{args.word}' is not banned. (list: mt bans)")
        return 0
    print(f"Unbanned '{args.word.strip().lower()}'.")
    return 0


def _cmd_bans(args, data_dir) -> int:
    con = _open_app_db(data_dir)
    try:
        items = bans.list_with_ts(con) if con else []
    finally:
        if con:
            con.close()
    if not items:
        print("No banned words. Ban one: mt ban <word>")
        return 0
    print(f"{len(items)} banned word(s):")
    for it in items:
        print(f"  - {it['word']}  ({it['ts'][:10]})")
    return 0


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _cmd_stats(args, data_dir) -> int:
    con = votes.connect(Path(data_dir) / "mairina.db")
    st = votes.stats(con)
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
    if muted := hints.muted(con):
        print(f"Muted hint rules: {', '.join(muted)}  (undo: mt hint-vote <rule_id> reset)")
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
        if args.cmd == "xray":
            return _cmd_xray(args, lyrics_db, data_dir)
        if args.cmd == "star":
            return _cmd_star(args, lyrics_db, data_dir)
        if args.cmd == "stars":
            return _cmd_stars(args, data_dir)
        if args.cmd == "unstar":
            return _cmd_unstar(args, data_dir)
        if args.cmd == "me":
            return _cmd_me(args, lyrics_db, data_dir)
        if args.cmd == "hint-vote":
            return _cmd_hint_vote(args, data_dir)
        if args.cmd == "atlas":
            return _cmd_atlas(args, lyrics_db, data_dir)
        if args.cmd == "compare":
            return _cmd_compare(args, lyrics_db, data_dir)
        if args.cmd == "ban":
            return _cmd_ban(args, data_dir)
        if args.cmd == "unban":
            return _cmd_unban(args, data_dir)
        if args.cmd == "bans":
            return _cmd_bans(args, data_dir)
        if args.cmd == "serve":
            from mairina import api                  # lazy: Flask only loads for `serve`
            return api.run(lyrics_db, Path(args.data_dir) if args.data_dir else data_dir)
        return _cmd_stats(args, data_dir)
    except corpus.DbUnavailable as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except votes.VoteError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
