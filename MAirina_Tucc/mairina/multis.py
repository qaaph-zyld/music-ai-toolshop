"""Phrase-level multi-syllable rhymes.

Combinations of 1-3 vocabulary words whose concatenated vowel skeleton ends with
the skeleton of the given phrase. Vocabulary words only: never corpus lines.
"""

from __future__ import annotations

import math
from collections import defaultdict

from mairina import keys
from mairina.anchors import CONTENT_POS
from mairina.rank import W_FREQ, Ctx, Scored, features_for

GLUE = frozenset("da se me te je u na sa mi ti ne".split())
MIN_FREQ = 2
PER_SKELETON = 40      # words kept per skeleton
BEAM = 60              # partial combos kept per (remaining, slots)
FINAL_BEAM = 2000      # complete combos kept before the diversity caps
W_EXTRA_WORD = 0.4     # penalty per additional word
MAX_PER_FINAL = 2      # results sharing the same final word
MAX_PER_FIRST = 3      # results sharing the same first word


def _build_pools(ctx: Ctx):
    """skeleton -> [(word, freq, final_ok)] sorted by frequency, capped.

    Any content word or glue word may sit in a non-final slot. The final slot needs
    a content word that is not a proper noun (artist names are already out of the vocab).
    """
    pools = defaultdict(list)
    for w, f in ctx.vocab().items():
        if f < MIN_FREQ or len(w) < 2:
            continue
        skel = keys.vowel_key(w)
        if not skel:
            continue
        upos = ctx.index.forms[w]["upos"]
        content = upos in CONTENT_POS
        if content or w in GLUE:
            pools[skel].append((w, f, content and upos != "PROPN"))
    for skel in pools:
        pools[skel].sort(key=lambda t: (-t[1], t[0]))
        del pools[skel][PER_SKELETON:]
    return pools


def _glue_count(words) -> int:
    return sum(1 for w in words if w in GLUE)


def multis(index, phrase: str, lane: str = "all", max_results: int = 20, fresh: float = 0.5,
           artists=(), boosts: dict | None = None) -> list[Scored]:
    """Ranked multi-syllable rhyme combinations for an ending phrase."""
    ctx = Ctx(index, lane, fresh, tuple(artists or ()), boosts)
    target = keys.vowel_key(phrase)
    if not target:
        return []
    pools = _build_pools(ctx)
    input_words = [keys.normalize(w) for w in phrase.split() if keys.normalize(w)]
    last_lemma = (index.forms.get(input_words[-1]) or {}).get("lemma") if input_words else None
    covers: dict[tuple, list] = {}

    def covering(rem: str, final: bool):
        key = (rem, final)
        if key not in covers:
            found = [t for skel, ws in pools.items() if skel.endswith(rem)
                     for t in ws if t[2] or not final]
            found.sort(key=lambda t: (-t[1], t[0]))
            covers[key] = found[:PER_SKELETON]
        return covers[key]

    memo: dict[tuple, list] = {}

    def gen(rem: str, slots: int, final: bool):
        """[(words, mean log-freq)] whose skeletons end with `rem`, best first."""
        key = (rem, slots, final)
        if key in memo:
            return memo[key]
        out = [([w], math.log1p(f)) for w, f, _ in covering(rem, final)]
        if slots > 1:
            for L in range(1, len(rem)):
                for w, f, final_ok in pools.get(rem[-L:], ()):
                    if final and not final_ok:
                        continue
                    for words, lf in gen(rem[:-L], slots - 1, False):
                        if _glue_count(words) + (w in GLUE) > 1:
                            continue           # at most one glue word per combination
                        n = len(words)
                        out.append((words + [w], (lf * n + math.log1p(f)) / (n + 1)))
        out.sort(key=lambda t: (-(W_FREQ * t[1] - W_EXTRA_WORD * (len(t[0]) - 1)), t[0]))
        memo[key] = out[:FINAL_BEAM if final else BEAM]
        return memo[key]

    results, seen = [], set()
    for words, mean_lf in gen(target, 3, True):
        phrase_s = " ".join(words)
        if phrase_s in seen or words == input_words:
            continue
        if any(a == b for a, b in zip(words, words[1:])):
            continue
        if last_lemma and index.forms[words[-1]]["lemma"] == last_lemma:
            continue
        if input_words and words[-1] == input_words[-1]:
            continue
        seen.add(phrase_s)
        freq = max(1, round(math.expm1(mean_lf)))
        feats = features_for(phrase_s, ctx, {"words": -W_EXTRA_WORD * (len(words) - 1)}, freq)
        results.append(Scored(phrase_s, round(sum(feats.values()), 3), feats, "multi",
                              {"freq": freq, "words": words, "skeleton": "".join(keys.vowel_key(w) for w in words)}))
    results.sort(key=lambda s: (-s.score, s.candidate))
    out, finals, firsts = [], defaultdict(int), defaultdict(int)
    for s in results:                      # diversity caps, best first
        w = s.meta["words"]
        if finals[w[-1]] >= MAX_PER_FINAL or firsts[w[0]] >= MAX_PER_FIRST:
            continue
        finals[w[-1]] += 1
        firsts[w[0]] += 1
        out.append(s)
        if len(out) >= max_results:
            break
    return out
