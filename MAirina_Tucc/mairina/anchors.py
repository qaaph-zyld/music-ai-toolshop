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
MODES = ("rhyme", "assonance", "consonance")
MIN_FREQ = 5
MIN_LEN = 3


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
        if info["upos"] not in CONTENT_POS or f < MIN_FREQ or len(w) < MIN_LEN:
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
            artists=(), rng: random.Random | None = None, boosts: dict | None = None) -> list[Anchor]:
    """Pick one end-word per line. Deterministic for a fixed `rng` (--rng-seed)."""
    rng = rng or random.Random()
    ctx = Ctx(index, lane, fresh, tuple(artists or ()), boosts)
    letters = parse_scheme(scheme, lines)
    groups: dict[str, int] = {}
    for g in letters:
        groups[g] = groups.get(g, 0) + 1
    classes = _classes(ctx, mode)
    seed_n = keys.normalize(seed) if seed else None
    seed_lemma = (index.forms.get(seed_n) or {}).get("lemma") if seed_n else None
    used_classes: set[str] = set()
    used_words: set[str] = set()
    used_lemmas: set[str] = set()
    picks: dict[str, list[Anchor]] = {}
    for gi, (g, k) in enumerate(groups.items()):
        def members(cls):
            return {lem: v for lem, v in classes.get(cls, {}).items()
                    if lem not in used_lemmas and v[0] not in used_words
                    and v[0] != seed_n and lem != seed_lemma
                    and not (gi == 0 and seed_n and conflict(v[0], seed_n))}
        def try_class(cls):
            mem = members(cls)
            lemmas = sorted(mem)
            feats = {lem: features_for(mem[lem][0], ctx, {}, mem[lem][1]) for lem in lemmas}
            scores = {lem: sum(feats[lem].values()) for lem in lemmas}
            forms = {lem: mem[lem][0] for lem in lemmas}
            chosen = _weighted_sample(rng, lemmas, [math.exp(scores[lem]) for lem in lemmas], k, forms)
            return mem, feats, scores, chosen

        if gi == 0 and seed_n:
            cls = class_key(seed_n, mode)
            res = try_class(cls) if cls is not None else None
            if res is None or len(res[3]) < k:
                raise NoAnchors(f"Seed '{seed}' has no usable {mode} class with {k} distinct, non-identical words in this lane.")
        else:
            pool = [c for c in sorted(classes) if c not in used_classes and len(members(c)) >= k]
            res = None
            while pool and res is None:
                weights = []
                for c in pool:
                    mem = members(c)
                    top = max(mem.values(), key=lambda v: v[1])
                    total = sum(v[1] for v in mem.values())
                    weights.append(math.sqrt(total) * max(0.05, 1 - fresh * ctx.overuse(top[0])))
                cls = rng.choices(pool, weights=weights)[0]
                cand = try_class(cls)
                if len(cand[3]) >= k:
                    res = cand
                else:
                    pool.remove(cls)          # class only has near-identical words
            if res is None:
                raise NoAnchors(f"No {mode} class with {k} distinct, non-identical words fits this lane/artist.")
        mem, feats, scores, chosen = res
        picks[g] = [Anchor(0, g, mem[lem][0], lem, mem[lem][2], mem[lem][1], cls, mode,
                           round(scores[lem], 3), feats[lem]) for lem in chosen]
        used_classes.add(cls)
        used_words.update(a.word for a in picks[g])
        used_lemmas.update(a.lemma for a in picks[g])
    out, counters = [], {g: 0 for g in groups}
    for i, g in enumerate(letters, 1):
        a = picks[g][counters[g]]
        counters[g] += 1
        a.line = i
        out.append(a)
    return out
