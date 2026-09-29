"""Transparent linear ranking. Every term of the score is kept in `features`.

score = match (kind/length) + log-frequency in the lane
        - fresh * overuse of the candidate's rhyme class
        + vote boost + "used" boost   (the last two only in arm `learned`)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from mairina import keys

# All weights live here.
W_LEN = 3.0      # per matched nucleus of a perfect rhyme
W_ASSON = 1.5    # vowel-only match (last two vowels)
W_CONS = 1.0     # consonant-only match
W_FREQ = 0.2     # * log(1 + frequency in lane)
W_FRESH = 2.0    # * fresh slider * class overuse (0..1)
W_VOTE = 2.0     # * ((up+1)/(up+down+2) - 0.5)
W_USED = 1.5     # if the word ended up in the user's own text


@dataclass
class Ctx:
    """Everything a ranking call needs. boosts=None means arm `base`."""

    index: object
    lane: str = "all"
    fresh: float = 0.5
    artists: tuple = ()
    boosts: dict | None = None
    _classes: dict = field(default_factory=dict, repr=False)

    def vocab(self) -> dict[str, int]:
        return self.index.vocab(self.lane, self.artists or None)

    def overuse(self, form: str) -> float:
        """0..1: how overused the form's tail class (2 nuclei) is in the lane."""
        if "totals" not in self._classes:
            totals: dict[str, int] = {}
            for w, f in self.vocab().items():
                k = keys.tail_key(w, 2)
                totals[k] = totals.get(k, 0) + f
            top = math.log1p(max(totals.values())) if totals else 1.0
            self._classes["totals"], self._classes["top"] = totals, top or 1.0
        t = self._classes["totals"].get(keys.tail_key(form, 2), 0)
        return math.log1p(t) / self._classes["top"]


@dataclass
class Scored:
    candidate: str
    score: float
    features: dict
    kind: str
    meta: dict = field(default_factory=dict)


def features_for(cand: str, ctx: Ctx, terms: dict, freq: int) -> dict:
    """Add frequency, fresh, and (arm learned) vote/used terms to `terms`."""
    f = dict(terms)
    f["freq"] = W_FREQ * math.log1p(freq)
    if ctx.fresh:
        f["fresh"] = -ctx.fresh * W_FRESH * ctx.overuse(cand.split()[-1])
    if ctx.boosts is not None:
        up, down, used = ctx.boosts.get(cand, (0, 0, 0))
        if up or down:
            f["votes"] = W_VOTE * ((up + 1) / (up + down + 2) - 0.5)
        if used:
            f["used"] = W_USED
    return {k: round(v, 3) for k, v in f.items()}


def classify(t: dict, cand: str) -> tuple[str, float] | None:
    """Match kind and base score of `cand` against the precomputed target `t`."""
    for n in (3, 2, 1):
        if n <= t["nuc"] and (n > 1 or len(t["tail"][1]) >= 2) and keys.tail_key(cand, n) == t["tail"][n]:
            return f"perfect-{n}", W_LEN * n
    if len(t["vt"]) == 2 and keys.vowel_tail(cand, 2) == t["vt"]:
        return "assonance", W_ASSON
    if len(t["cons"]) >= 2 and keys.consonant_units(cand, 2) == t["cons"]:
        return "consonance", W_CONS
    return None


def prepare_target(word: str) -> dict:
    w = keys.normalize(word)
    return {"word": w, "nuc": keys.nuclei_count(w), "tail": {n: keys.tail_key(w, n) for n in (1, 2, 3)},
            "vt": keys.vowel_tail(w, 2), "cons": keys.consonant_units(w, 2)}


def rank(target: str, candidates, ctx: Ctx) -> list[Scored]:
    """Rank rhyme candidates for `target`. Sorted best first, ties alphabetical."""
    t = prepare_target(target)
    vocab = ctx.vocab()
    tlemma = (ctx.index.forms.get(t["word"]) or {}).get("lemma")
    out = []
    for cand in candidates:
        freq = vocab.get(cand, 0)
        if not freq or cand == t["word"] or len(cand) < 2:
            continue
        info = ctx.index.forms[cand]
        if tlemma and info["lemma"] == tlemma:
            continue
        m = classify(t, cand)
        if m is None:
            continue
        kind, base = m
        feats = features_for(cand, ctx, {kind: base}, freq)
        out.append(Scored(cand, round(sum(feats.values()), 3), feats, kind,
                          {"freq": freq, "upos": info["upos"], "lemma": info["lemma"]}))
    out.sort(key=lambda s: (-s.score, s.candidate))
    return out


def explain(s: Scored) -> str:
    """Short 'why' line: each term's contribution."""
    parts = []
    for k, v in s.features.items():
        if k == "freq":
            parts.append(f"freq({s.meta.get('freq', '?')}) {v:+.2f}")
        elif abs(v) >= 0.005 or k == s.kind:
            parts.append(f"{k} {v:+.2f}")
    return " | ".join(parts)
