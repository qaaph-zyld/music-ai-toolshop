"""Comparison finder: the single words that follow simile markers in the corpus.

``ko lava`` -> ``lava``. For every corpus line (``corpus.CORPORA``, lane and
artist filtered) the simile markers of ``devices`` are located with the very
same ``ko`` = "who" exclusion; the first NOUN/ADJ/PROPN within three tokens
after the marker (not a clitic, not an artist-name token) is counted. Output is
a ranked list of SINGLE WORDS with counts: no line, phrase or song is ever
returned. Pronouns, determiners and pronoun-like adjectives (``STOPWORDS``) are
never comparison words, nor are fragments (under 3 letters, or no vowel; a syllabic
r counts as one). Low-confidence markers ('kao da/što', a line-initial 'ko') are not
comparisons and are skipped.

Identical lines inside one song (refrains) count once, so a repeated chorus
does not drown a word. The scan is uncached: one guarded read-only pass.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

from mairina import corpus, devices, phonetics, rank
from mairina.used import tokenize

CONTENT_UPOS = frozenset({"NOUN", "ADJ", "PROPN"})
# Pronouns/determiners (by corpus majority UPOS) and pronoun-like adjectives are
# function words, not things a line can be compared to. CLASSLA tags many of them
# ADJ ('kao sve', 'ko nijedna'), hence the explicit stoplist (matched on the form
# and on the lemma, so 'mojih' goes with 'moj').
STOP_UPOS = frozenset({"DET", "PRON"})
STOPWORDS = frozenset("""sve svi svaki svaka svako nijedna nijedan nijedno takav takva taj ta to
    ovaj ova ovo onaj ona neki neka svoj svoja moj moja tvoj tvoja isti ista sam sama ceo cela
    celi""".split())
MIN_WORD_LETTERS = 3             # 'la', 'ap' are fragments, not things to compare to
LOOKAHEAD = 3                    # tokens scanned after the marker
W_SIMILE = 1.0                   # * log(1 + times seen after a simile marker)
# Cheap SQL superset of the SIMILE_RE markers (the regex does the exact work).
_PREFILTER = ("%ko%", "%kao%", "%k'o%", "%k’o%", "%ka'o%", "%ka’o%", "%poput%")


def theme_lemma(theme: str, index) -> str:
    """Majority lemma of the theme word from the index, else the normalised word."""
    word = " ".join(tokenize(theme))
    entry = index.forms.get(word) if index is not None else None
    return (entry["lemma"] if entry else word).lower()


def _query(lane: str, artists, lemma: str | None) -> tuple[str, list]:
    sql = ("SELECT s.id, l.text_raw FROM lines l JOIN sections sec ON sec.id = l.section_id "
           "JOIN songs s ON s.id = sec.song_id WHERE length(trim(l.text_raw)) > 0"
           + corpus._corpus_sql("s")
           + " AND (" + " OR ".join("l.text_raw LIKE ?" for _ in _PREFILTER) + ")")
    args: list = list(_PREFILTER)
    cohorts = corpus.LANE_COHORTS[lane]
    if cohorts:
        sql += f" AND s.genre_cohort IN ({','.join('?' * len(cohorts))})"
        args += list(cohorts)
    if artists:
        sql += f" AND s.target_artist IN ({','.join('?' * len(artists))})"
        args += list(artists)
    if lemma:
        sql += " AND l.id IN (SELECT t.line_id FROM tokens t WHERE lower(t.lemma) = ?)"
        args.append(lemma)
    return sql, args


def _comparison_word(tok: str, index, skip_lemma: str | None,
                     blocked: frozenset = frozenset()) -> str | None:
    """The token if it can be a comparison word, else None. Fragments are out: fewer
    than 3 letters, or no vowel at all ('gt'; a syllabic r still counts as one, so
    'krv' and 'prst' stay)."""
    if len(tok) < MIN_WORD_LETTERS or not phonetics.syllables(tok):
        return None
    if tok in blocked or tok in phonetics.CLITICS or tok in index.artist_names:
        return None
    entry = index.forms.get(tok)
    if not entry or entry["upos"] in STOP_UPOS or entry["upos"] not in CONTENT_UPOS:
        return None
    if tok in STOPWORDS or entry["lemma"].lower() in STOPWORDS:
        return None
    if skip_lemma and entry["lemma"].lower() == skip_lemma:
        return None                              # the theme word itself is no comparison
    return tok


def collect(db_path, lane: str, artists, theme: str | None, index,
            blocked: frozenset = frozenset()) -> Counter:
    """``Counter({word: n})`` of comparison words, under ``corpus.build_guarded``."""
    path = Path(db_path or corpus.DEFAULT_LYRICS_DB)
    if not path.is_file():
        raise corpus.DbUnavailable(f"lyrics.db not found. Expected at: {path}")
    lemma = theme_lemma(theme, index) if theme else None
    sql, args = _query(lane, tuple(artists or ()), lemma)

    def _work():
        counts: Counter = Counter()
        seen: set = set()                                  # (song, line) pairs: refrains once
        con = corpus.open_ro(path)
        try:
            for sid, text in con.execute(sql, args):
                key = (sid, " ".join(tokenize(text)))
                if key in seen:
                    continue
                seen.add(key)
                toks, positions = devices.simile_scan(text, index)
                for marker, i, j in positions:
                    nxt = toks[j] if j < len(toks) else None
                    if devices.simile_confidence(marker, nxt, i == 0) == "low":
                        continue
                    for tok in toks[j:j + LOOKAHEAD]:
                        if word := _comparison_word(tok, index, lemma, blocked):
                            counts[word] += 1
                            break
        finally:
            con.close()
        return counts

    return corpus.build_guarded(path, _work)


def rank_words(counts: Counter, index, lane: str = "all", artists=(), fresh: float = 0.5,
               boosts: dict | None = None, blocked: frozenset = frozenset()) -> list[rank.Scored]:
    """Rank comparison words: simile use first, then lane frequency, the fresh slider
    and (arm learned) vote/used boosts, exactly like the other lists."""
    ctx = rank.Ctx(index, lane, fresh, tuple(artists or ()), boosts, blocked=blocked)
    out = []
    for word, n in counts.items():
        info = index.forms[word]
        freq = index.freq(word, lane, tuple(artists or ()) or None)
        feats = rank.features_for(word, ctx, {"simile-use": W_SIMILE * math.log1p(n)}, freq)
        out.append(rank.Scored(word, round(sum(feats.values()), 3), feats, "compare",
                               {"count": n, "freq": freq, "upos": info["upos"],
                                "lemma": info["lemma"]}))
    out.sort(key=lambda s: (-s.score, s.candidate))
    return out
