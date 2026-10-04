"""Anchor sets: one end-word per line, grouped by rhyme scheme.

The tool only picks words that belong together; the user writes every line.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from mairina import keys
from mairina.rank import Ctx, features_for

CONTENT_POS = frozenset({"NOUN", "VERB", "ADJ", "PROPN", "ADV"})
ANCHOR_POS = CONTENT_POS - {"PROPN"}       # anchors are common words, not names
MODES = ("rhyme", "assonance", "consonance")
MIN_FREQ = 5
MIN_LEN = 3
SAMPLE_TRIES = 12


class NoAnchors(Exception):
    """No rhyme class can satisfy the request (CLI prints reason + hint, exit 0)."""


@dataclass
class Anchor:
    line: int
    group: str
    word: str
    lemma: str
    upos: str
    freq: int
    key: str
    mode: str
    score: float = 0.0
    features: dict = field(default_factory=dict)
    locked: bool = False            # the user's own written end-word, not a suggestion


def class_key(word: str, mode: str) -> str | None:
    """Rhyme class of a word for the given mode, or None if it has no class."""
    if mode == "rhyme":
        return keys.tail_key(word, 2) if keys.nuclei_count(word) >= 2 else None
    if mode == "assonance":
        vt = keys.vowel_tail(word, 2)
        return vt if len(vt) == 2 else None
    units = keys.consonant_units(word, 2)
    return "".join(units) if len(units) >= 2 else None


def parse_scheme(scheme: str, lines: int | None = None) -> list[str]:
    """'AABB' -> ['A','A','B','B']. If `lines` differs, cycle with fresh letters."""
    letters = [c for c in scheme.upper() if c.isalpha()]
    if not letters:
        raise NoAnchors("Empty rhyme scheme. Try --scheme AABB.")
    order = {}
    canon = [order.setdefault(c, len(order)) for c in letters]
    n, u = len(canon), len(order)
    total = lines or n
    ids = [canon[i % n] + (i // n) * u for i in range(total)]
    return [_letter(i) for i in ids]


def _letter(i: int) -> str:
    return chr(65 + i) if i < 26 else f"{chr(65 + i % 26)}{i // 26}"


def _classes(ctx: Ctx, mode: str) -> dict[str, dict[str, tuple]]:
    """class -> {lemma: (form, freq, upos)} using the most frequent form per lemma."""
    out: dict[str, dict[str, tuple]] = {}
    for w, f in ctx.vocab().items():
        info = ctx.index.forms[w]
        if info["upos"] not in ANCHOR_POS or f < MIN_FREQ or len(w) < MIN_LEN:
            continue
        if not keys.is_serbian_orthography(w):
            continue
        k = class_key(w, mode)
        if k is None:
            continue
        cur = out.setdefault(k, {}).get(info["lemma"])
        if cur is None or (f, w) > (cur[1], cur[0]):
            out[k][info["lemma"]] = (w, f, info["upos"])
    return out


def conflict(a: str, b: str) -> bool:
    """True if two words would make an identical rhyme (a word and its own extension)."""
    if a.endswith(b) or b.endswith(a):
        return True
    ta, tb = keys.tail_key(a, 2), keys.tail_key(b, 2)
    return ta == tb and a[:len(a) - len(ta)] == b[:len(b) - len(tb)]


def _weighted_sample(rng, items, weights, k, forms):
    """Sample up to k items without replacement; drop items that conflict with a pick."""
    items, weights, picked = list(items), list(weights), []
    while items and len(picked) < k:
        i = rng.choices(range(len(items)), weights=weights)[0]
        item = items.pop(i)
        weights.pop(i)
        picked.append(item)
        keep = [j for j, other in enumerate(items) if not conflict(forms[item], forms[other])]
        items, weights = [items[j] for j in keep], [weights[j] for j in keep]
    return picked


def anchors(index, scheme: str = "AABB", lines: int | None = None, lane: str = "all",
            mode: str = "rhyme", seed: str | None = None, fresh: float = 0.5,
            artists=(), rng: random.Random | None = None, boosts: dict | None = None,
            blocked: frozenset = frozenset(), exclude: frozenset = frozenset(),
            group_seeds: dict | None = None, warnings: list | None = None,
            locked_lines: frozenset = frozenset()) -> list[Anchor]:
    """Pick one end-word per line. Deterministic for a fixed `rng` (--rng-seed).

    ``blocked`` removes words from the whole vocabulary (bans + dialect).
    ``exclude`` additionally keeps specific words out of the picks (the user's
    own written end-words). ``group_seeds`` {group letter: word} seeds a group
    from a written line: its class chain is tried ``mode`` -> assonance ->
    consonance, then a fresh class as last resort — each fallback adds a
    ``warnings`` entry. ``locked_lines`` (1-based) are written rows: they get
    no generated anchor and don't count toward their group's pick quota.
    ``seed`` (CLI --seed) stays strict: group A only, and NoAnchors when its
    class is thin.
    """
    rng = rng or random.Random()
    ctx = Ctx(index, lane, fresh, tuple(artists or ()), boosts, blocked=blocked)
    warnings = warnings if warnings is not None else []
    letters = parse_scheme(scheme, lines)
    groups: dict[str, int] = {}
    for i, g in enumerate(letters, 1):
        if i not in locked_lines:
            groups[g] = groups.get(g, 0) + 1
    class_maps = {mode: _classes(ctx, mode)}
    seed_n = keys.normalize(seed) if seed else None
    seeded = {g: keys.normalize(w) for g, w in (group_seeds or {}).items() if keys.normalize(w)}
    used_classes: set[str] = set()
    used_words: set[str] = set(exclude)
    used_lemmas: set[str] = set()
    picks: dict[str, list[Anchor]] = {}
    for g in letters:
        if g not in groups:
            picks.setdefault(g, [])
    for gi, (g, k) in enumerate(groups.items()):
        strict_seed = gi == 0 and seed_n is not None
        gseed = seed_n if strict_seed else seeded.get(g)
        gseed_lemma = (index.forms.get(gseed) or {}).get("lemma") if gseed else None

        def members(cls, cls_map):
            return {lem: v for lem, v in cls_map.get(cls, {}).items()
                    if lem not in used_lemmas and v[0] not in used_words
                    and v[0] != gseed and lem != gseed_lemma
                    and not (gseed and conflict(v[0], gseed))}

        def try_class(cls, cls_map):
            mem = members(cls, cls_map)
            lemmas = sorted(mem)
            feats = {lem: features_for(mem[lem][0], ctx, {}, mem[lem][1]) for lem in lemmas}
            scores = {lem: sum(feats[lem].values()) for lem in lemmas}
            forms = {lem: mem[lem][0] for lem in lemmas}
            weights = [math.exp(scores[lem]) for lem in lemmas]
            for _ in range(SAMPLE_TRIES):        # greedy picks can dead-end on a conflict: retry
                chosen = _weighted_sample(rng, lemmas, weights, k, forms)
                if len(chosen) >= k:
                    break
            return mem, feats, scores, chosen

        def fresh_pick():
            pool = [c for c in sorted(class_maps[mode])
                    if c not in used_classes and len(members(c, class_maps[mode])) >= k]
            while pool:
                weights = []
                for c in pool:
                    mem = members(c, class_maps[mode])
                    top = max(mem.values(), key=lambda v: v[1])
                    total = sum(v[1] for v in mem.values())
                    weights.append(math.sqrt(total) * max(0.05, 1 - fresh * ctx.overuse(top[0])))
                cls = rng.choices(pool, weights=weights)[0]
                cand = try_class(cls, class_maps[mode])
                if len(cand[3]) >= k:
                    return cls, cand
                pool.remove(cls)              # class only has near-identical words
            return None

        res = None                            # (cls, cand, mode_used)
        if gseed:
            chain = [mode] if strict_seed else [mode] + [m for m in MODES if m != mode]
            for mi, m2 in enumerate(chain):
                cls = class_key(gseed, m2)
                if cls is None:
                    continue
                cand = try_class(cls, class_maps.setdefault(m2, _classes(ctx, m2)))
                if len(cand[3]) >= k:
                    res = (cls, cand, m2)
                    if mi:
                        warnings.append(f"{g}: '{gseed}' has no {mode} partners — matched on {m2} instead.")
                    break
            if res is None:
                if strict_seed:
                    raise NoAnchors(f"Seed '{seed}' has no usable {mode} class with {k} distinct, non-identical words in this lane.")
                fp = fresh_pick()
                if fp is None:
                    raise NoAnchors(f"No {mode} class with {k} distinct, non-identical words fits this lane/artist.")
                res = (*fp, mode)
                warnings.append(f"{g}: '{gseed}' has no rhyme family — re-rolled a fresh class.")
        else:
            if fp := fresh_pick():
                res = (*fp, mode)
            else:
                raise NoAnchors(f"No {mode} class with {k} distinct, non-identical words fits this lane/artist.")
        cls, (mem, feats, scores, chosen), mode_used = res
        picks[g] = [Anchor(0, g, mem[lem][0], lem, mem[lem][2], mem[lem][1], cls, mode_used,
                           round(scores[lem], 3), feats[lem]) for lem in chosen]
        used_classes.add(cls)
        used_words.update(a.word for a in picks[g])
        used_lemmas.update(a.lemma for a in picks[g])
    out, counters = [], {g: 0 for g in groups}
    for i, g in enumerate(letters, 1):
        if i in locked_lines:
            continue
        a = picks[g][counters[g]]
        counters[g] += 1
        a.line = i
        out.append(a)
    return out


def swap(index, cls: str, mode: str, lane: str = "all", fresh: float = 0.5,
         artists=(), exclude: frozenset = frozenset(), rng: random.Random | None = None,
         boosts: dict | None = None, blocked: frozenset = frozenset()) -> Anchor | None:
    """A different same-class member (different lemma), or None when the class
    is exhausted — used by the swap action on an anchor chip."""
    rng = rng or random.Random()
    ctx = Ctx(index, lane, fresh, tuple(artists or ()), boosts, blocked=blocked)
    mem = {lem: v for lem, v in _classes(ctx, mode).get(cls, {}).items()
           if v[0] not in exclude}
    if not mem:
        return None
    lemmas = sorted(mem)
    feats = {lem: features_for(mem[lem][0], ctx, {}, mem[lem][1]) for lem in lemmas}
    scores = {lem: sum(feats[lem].values()) for lem in lemmas}
    weights = [math.exp(scores[lem]) for lem in lemmas]
    lem = rng.choices(lemmas, weights=weights)[0]
    w, f, upos = mem[lem]
    return Anchor(0, "", w, lem, upos, f, cls, mode, round(scores[lem], 3), feats[lem])
