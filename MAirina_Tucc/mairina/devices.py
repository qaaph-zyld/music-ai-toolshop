"""Mechanical sound-device and figure detection for a draft verse.

Every tag is a dict ``{kind, span, confidence: high|medium|low, advisory: True}``:
the tool finds and measures, it never judges for real and never writes. The
hard cases (metaphor, wordplay, double meaning, chiasmus, hyperbole,
polyptoton, stress prediction) are deliberately not implemented.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

from toolshop.rhyme_miner import find_internal_rhymes
from toolshop.syllables import count_line

from mairina import ROOT, corpus, keys, phonetics
from mairina.used import token_spans, tokenize

ALLIT_WINDOW = 4          # word-onset window for alliteration
CONS_TAG_LEVEL = 0.6      # consonance density that earns a tag
GAUGE_STEPS = (0.35, 0.6, 1.0)   # cons density -> filled blocks out of 3

SIMILE_RE = re.compile(r"(?<!\w)(ka'o|k'o|kao|poput|ko)(?!\w)")
_AUX_CLITICS = frozenset({"je", "sam", "smo", "su", "si", "ste",
                          "bi", "će", "ću", "ćemo", "ćete", "ćeš"})
_VERBISH_SUFFIX = ("ti", "ći")           # infinitive fallback when no index
_KAO_CONJ = frozenset({"da", "što", "sto"})   # 'kao da/što' is a conjunction, not a simile

# Shared openings made only of these are not anaphora (clitics + function words).
ANAPHORA_STOP = phonetics.CLITICS | frozenset({
    "ja", "ti", "on", "ona", "ono", "mi", "vi", "oni", "one", "ne", "sve",
    "to", "taj", "ta", "ovo", "i", "a", "ali", "pa", "kad", "jer", "da",
})

# Majority-non-PROPN single-token gazetteer entries at or above this frequency
# are ordinary words ('mala', 'niko'), not name drops.
NAME_MIN_FREQ = 20

# Gazetteer noise (CLASSLA NER tags ad-libs and filler repeats as names): an entry
# is dropped when it is shorter than 3 letters in total, is one token repeated
# ('a a a', 'yeah yeah'), or when every token is an interjection (corpus majority
# UPOS INTJ) or in this ad-lib list. Real names and brands never match all three.
ADLIB = frozenset("yeah yea ye aha uh oh ey hey brr skrr ja la na da a e o".split())
MIN_ENTRY_LETTERS = 3


def is_noise_entry(entry: str, forms=None) -> bool:
    """True when a gazetteer entry is ad-lib/filler noise, not a name drop.
    ``forms`` (``Index.forms``) enables the majority-INTJ test; without it only
    the corpus-free rules (length, repeat, ad-lib list) apply."""
    toks = entry.split()
    if not toks or sum(len(t) for t in toks) < MIN_ENTRY_LETTERS:
        return True
    if len(toks) > 1 and len(set(toks)) == 1:
        return True
    return all(t in ADLIB or (forms is not None and (forms.get(t) or {}).get("upos") == "INTJ")
               for t in toks)


def _tag(kind: str, span: str, confidence: str) -> dict:
    return {"kind": kind, "span": span, "confidence": confidence,
            "advisory": True}


@lru_cache(maxsize=1)
def _english_tokens() -> frozenset:
    path = ROOT / "lexicons" / "english_tokens.txt"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        print(f"Note: lexicon file missing: {path} — code_switch tag disabled.",
              file=sys.stderr)
        return frozenset()
    return frozenset(t.strip() for t in text.splitlines()
                     if t.strip() and not t.startswith("#"))


@lru_cache(maxsize=4)
def load_gazetteer(db_path: str | None = None) -> frozenset:
    """Lowercased entity texts (ORG/PER/LOC) and artist names from lyrics.db.

    Multi-word entities stay whole phrases — 'Tabak Mala' must match as
    'tabak mala', never lend 'mala' as a standalone name. Single tokens are
    kept as-is; whether a common word is suppressed is decided at match time
    against corpus UPOS/frequency (see ``_name_drops``). Ad-lib/filler noise
    (``is_noise_entry``) is dropped here and, for interjections, at match time.
    Only CORPORA rows count.
    """
    out: set[str] = set()

    def _add(text: str):
        t = " ".join(tokenize(text))
        if t and not is_noise_entry(t):
            out.add(t)

    con = corpus.open_ro(db_path)
    try:
        for (text,) in con.execute(
                "SELECT DISTINCT e.text FROM entities e "
                "JOIN songs s ON s.id = e.song_id "
                "WHERE e.ner_type IN ('ORG','PER','LOC')" + corpus._corpus_sql("s")):
            if text:
                _add(text)
        for col in ("target_artist", "primary_artist"):
            for (name,) in con.execute(
                    f"SELECT DISTINCT s.{col} FROM songs s WHERE s.{col} IS NOT NULL"
                    + corpus._corpus_sql("s")):
                _add(name)
    finally:
        con.close()
    return frozenset(out)


def _split_gazetteer(gazetteer) -> tuple[set, list]:
    singles, phrases = set(), []
    for entry in gazetteer:
        if " " in entry:
            phrases.append(entry)
        else:
            singles.add(entry)
    return singles, phrases


_PREP: dict = {}        # single-entry memo for _prepared_gazetteer


def _prepared_gazetteer(gazetteer, index):
    """(singles, phrases_by_first_token), memoised on the (gazetteer, index) objects.

    Splitting the gazetteer and filtering it against the index is O(|gazetteer|);
    doing it per line made a whole-corpus scan (the device atlas) take minutes.
    """
    if (_PREP.get("gaz") is gazetteer and _PREP.get("index") is index
            and _PREP.get("n") == len(gazetteer)):
        return _PREP["prep"]
    forms = index.forms if index is not None else None
    singles, phrases = _split_gazetteer(e for e in gazetteer if not is_noise_entry(e, forms))
    if index is not None:
        def _common_word(s: str) -> bool:
            e = index.forms.get(s)
            return bool(e) and e["freq"] >= NAME_MIN_FREQ and e["upos"] != "PROPN"
        singles = {s for s in singles if not _common_word(s)}
    by_first: dict[str, list[str]] = {}
    for p in sorted(phrases):
        by_first.setdefault(p.split(" ", 1)[0], []).append(p)
    _PREP.update(gaz=gazetteer, index=index, n=len(gazetteer), prep=(singles, by_first))
    return _PREP["prep"]


def consonance_density(line: str) -> float:
    """Consonant units whose class repeats >=2x, divided by syllables.

    Clitics carry no stress and are excluded from the numerator AND the
    denominator — counting their syllables would dilute dense lines.
    """
    toks = [t for t in tokenize(line) if t not in phonetics.CLITICS]
    units: list[str] = []
    for t in toks:
        units.extend(phonetics.consonants(t))
    syl = sum(phonetics.syllables(t) for t in toks)
    if not units or not syl:
        return 0.0
    counts = Counter(phonetics.consonant_class(u) for u in units)
    repeated = sum(n for n in counts.values() if n >= 2)
    return repeated / syl


def gauge(density: float, thresholds=None, blocks: int = 3) -> str:
    """'▮▮▯' style gauge. `thresholds` are the lane's corpus quantiles
    (``targets.cons_thresholds``); GAUGE_STEPS is the offline fallback."""
    steps = thresholds or GAUGE_STEPS
    filled = sum(1 for thr in steps[:blocks] if density >= thr)
    return "▮" * filled + "▯" * (blocks - filled)


def _alliteration(tokens: list[str]) -> dict | None:
    """Word onsets in a 4-token window: same phoneme = strong, same class = weak.
    Clitics and 'ne' are measured out — 'se snimaš' is not alliteration."""
    toks = [t for t in tokens if t not in phonetics.CLITICS and t != "ne"]
    onsets = [phonetics.onset(t) for t in toks]
    strong: set[str] = set()
    weak: set[str] = set()
    for i in range(len(onsets)):
        win = [o for o in onsets[i:i + ALLIT_WINDOW] if o]
        seen_ph, seen_cls = set(), set()
        for o in win:
            if o in seen_ph:
                strong.add(o)
            cls = phonetics.consonant_class(o)
            if cls in seen_cls:
                weak.add(o)
            seen_ph.add(o)
            seen_cls.add(cls)
    weak -= strong
    if strong:
        return _tag("alliteration", ",".join(sorted(strong)), "high")
    if weak:
        return _tag("alliteration", ",".join(sorted(weak)), "low")
    return None


def _verbish(token: str, index=None) -> bool:
    """True when the token reads as a verb: aux clitic, -ti/-ći infinitive,
    or VERB/AUX by corpus index majority UPOS."""
    if token in _AUX_CLITICS or token.endswith(_VERBISH_SUFFIX):
        return True
    if index is not None:
        return (index.forms.get(token) or {}).get("upos") in ("VERB", "AUX")
    return False


def _ko_is_who(toks, j: int | None, index) -> bool:
    """'ko' at token position j-1 means 'who' when what follows is verbal:
    'ko je gazda', 'ko me zove' (clitic(s) then a verb), 'ko radi'."""
    if j is None or j >= len(toks):
        return False
    if _verbish(toks[j][0], index):
        return True
    if toks[j][0] in phonetics.CLITICS:
        k = j + 1
        while k < len(toks) and toks[k][0] in phonetics.CLITICS:
            k += 1
        return k < len(toks) and _verbish(toks[k][0], index)
    return False


def simile_scan(line: str, index=None) -> tuple[list[str], list[tuple[str, int, int]]]:
    """(tokens, positions) for the simile markers of a line.

    Tokens are lowercased with the curly ’ folded to ' (so k’o matches). Each
    position is ``(marker, marker_tok_idx, next_tok_idx)``; ``next_tok_idx`` may
    equal ``len(tokens)`` when the marker ends the line. 'ko' read as 'who' (a
    question, or a verb/aux follows, at ANY position) is excluded; 'kao da/što'
    and line-initial 'ko' are kept — ``simile_confidence`` grades them low.
    """
    low = unicodedata.normalize("NFC", line).lower().replace("’", "'")
    spans = token_spans(low)
    toks = [t for t, _s, _e in spans]
    starts = {s: i for i, (_, s, _e) in enumerate(spans)}
    is_question = low.rstrip().endswith("?")
    out = []
    for m in SIMILE_RE.finditer(low):
        marker = m.group(1)
        i = starts.get(m.start())                    # token where the marker starts
        if i is None:
            continue
        j = i + (2 if "'" in marker else 1)
        if marker == "ko" and (is_question or _ko_is_who(spans, j, index)):
            continue                                 # 'ko' = 'who' here
        out.append((marker, i, j))
    return toks, out


def simile_positions(line: str, index=None) -> list[tuple[str, int, int]]:
    """``[(marker, marker_tok_idx, next_tok_idx)]`` — see ``simile_scan``."""
    return simile_scan(line, index)[1]


def simile_confidence(marker: str, nxt: str | None, initial: bool) -> str:
    """kao is high unless a conjunction follows ('kao da/što' -> low); k'o,
    ka'o, poput are high; 'ko' is medium mid-line and low line-initially."""
    if marker == "kao":
        return "low" if nxt in _KAO_CONJ else "high"
    if marker != "ko":
        return "high"
    return "low" if initial else "medium"


def _similes(line: str, index=None) -> list[dict]:
    """kao/k'o/ka'o/poput are similes (curly ’ recognised); 'ko' also means
    'who', checked at ANY position, not only line-initial."""
    toks, positions = simile_scan(line, index)
    return [_tag("simile", marker,
                 simile_confidence(marker, toks[j] if j < len(toks) else None, i == 0))
            for marker, i, j in positions]


def _maximal_internal_rhymes(line: str) -> list:
    """Only the longest repeated skeletons in the line, kept to non-overlapping
    occurrences (shorter matches are echoes and would just add noise)."""
    matches = find_internal_rhymes(line, min_match=2)
    if not matches:
        return []
    longest = max(m.match_length for m in matches)
    out = []
    for m in matches:
        if m.match_length != longest:
            continue
        kept: list[int] = []
        for pos in sorted(m.line_indices):
            if not kept or pos >= kept[-1] + m.match_length:
                kept.append(pos)
        if len(kept) >= 2:
            out.append(m)
    return out


def _epizeuxis(tokens: list[str]) -> list[dict]:
    return [_tag("epizeuxis", t, "high")
            for i, t in enumerate(tokens[1:], 1) if t == tokens[i - 1]]


def _name_drops(line: str, tokens: list[str], gazetteer, index=None) -> list[dict]:
    if not gazetteer:
        return []
    singles, by_first = _prepared_gazetteer(gazetteer, index)
    token_set = set(tokens)
    out = [_tag("name_drop", w, "high") for w in sorted(token_set & singles)]
    joined = " " + " ".join(tokens) + " "
    out += [_tag("name_drop", p, "high")
            for first in sorted(token_set & by_first.keys())
            for p in by_first[first] if f" {p} " in joined]
    return out


def _first_content(tokens: list[str]) -> str | None:
    return next((t for t in tokens if t not in phonetics.CLITICS), None)


def _last_content(tokens: list[str]) -> str | None:
    return next((t for t in reversed(tokens) if t not in phonetics.CLITICS), None)


def analyze_line(line: str, n: int = 1, prev_lines=(),
                 gazetteer=frozenset(), index=None) -> list[dict]:
    """All tags detectable from one line plus its immediate predecessor."""
    tokens = tokenize(line)
    if not tokens:
        return []
    out: list[dict] = []
    if tag := _alliteration(tokens):
        out.append(tag)
    density = consonance_density(line)
    if density >= CONS_TAG_LEVEL:
        out.append(_tag("consonance", f"{density:.2f}/syl", "medium"))
    for m in _maximal_internal_rhymes(line):
        out.append(_tag("internal_rhyme", m.vowel_skeleton,
                        "high" if m.match_length >= 3 else "medium"))
    out += _similes(line, index)
    out += _epizeuxis(tokens)
    drops = _name_drops(line, tokens, gazetteer, index)
    named = {t for d in drops for t in d["span"].split()}
    out += [_tag("code_switch", t, "medium")
            for t in dict.fromkeys(t for t in tokens
                                   if t in _english_tokens() and t not in named)]
    out += drops
    if prev_lines:
        prev = tokenize(prev_lines[-1])
        prev_last, cur_first = _last_content(prev), _first_content(tokens)
        if prev_last and cur_first and prev_last == cur_first:
            out.append(_tag("anadiplosis", cur_first, "high"))
    return out


@dataclass
class LineReport:
    n: int
    text: str
    syllables: int
    cons_density: float
    rhyme_letter: str | None
    devices: list = field(default_factory=list)


@dataclass
class VerseReport:
    lines: list                 # of LineReport
    scheme: str                 # e.g. 'A-A-BB' ('-' = no end-rhyme partner)


def _union_groups(n: int, pairs):
    """Union-find over 0..n-1; returns groups of >=2 members, ordered by first index."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted((g for g in groups.values() if len(g) >= 2), key=min)


def _rhyme_letters(tokens_per_line: list[list[str]]) -> dict[int, str]:
    """Rhyme letters from the LAST WORD's tail keys: two lines share a letter
    when tail_key(., 2) matches, or tail_key(., 1) matches and is >=2 chars
    (vowel + coda, e.g. 'aš' — which is how 'znaš' joins 'imaš'/'snimaš')."""
    lasts = [t[-1] if t else "" for t in tokens_per_line]
    t2 = [keys.tail_key(w, 2) if w else "" for w in lasts]
    t1 = [keys.tail_key(w, 1) if w else "" for w in lasts]
    pairs = [(i, j) for i in range(len(lasts)) for j in range(i + 1, len(lasts))
             if lasts[i] and (t2[i] == t2[j] or (len(t1[i]) >= 2 and t1[i] == t1[j]))]
    letter_of: dict[int, str] = {}
    for gi, group in enumerate(_union_groups(len(lasts), pairs)):
        for idx in group:
            letter_of[idx] = chr(65 + gi)
    return letter_of


def _common_suffix(a: str, b: str) -> str:
    k = 0
    while k < min(len(a), len(b)) and a[-1 - k] == b[-1 - k]:
        k += 1
    return a[len(a) - k:]


def _multi_suffixes(texts: list[str]) -> dict[int, str]:
    """Line -> longest common vowel-skeleton suffix (>=3) it shares with others:
    'imaš'/'snimaš' lines report the full shared tail ('iaeia'), not 3 vowels."""
    skels = [keys.vowel_key(t) for t in texts]
    pairs = [(i, j) for i in range(len(texts)) for j in range(i + 1, len(texts))
             if len(_common_suffix(skels[i], skels[j])) >= 3]
    out: dict[int, str] = {}
    for group in _union_groups(len(texts), pairs):
        common = skels[group[0]]
        for idx in group[1:]:
            common = _common_suffix(common, skels[idx])
        for idx in group:
            out[idx] = common
    return out


def _opening_surface(line: str, n_tokens: int) -> str:
    """The first `n_tokens` tokens with their original casing/punctuation."""
    spans = token_spans(line)
    if len(spans) < n_tokens:
        return " ".join(tokenize(line)[:n_tokens])
    return line[spans[0][1]:spans[n_tokens - 1][2]]


def _common_prefix(a: list[str], b: list[str]) -> int:
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    return k


def anaphora_runs(tokens: list[list[str]]) -> list[tuple[int, int, int]]:
    """``[(first, end, p)]``: lines first..end-1 share an opening of ``p`` tokens
    that holds at least one non-stopword. Shared by ``analyze_verse`` and the
    device atlas so both apply identical rules."""
    out = []
    i = 0
    while i < len(tokens) - 1:
        p = _common_prefix(tokens[i], tokens[i + 1])
        if p and any(t not in ANAPHORA_STOP for t in tokens[i][:p]):
            j = i + 2
            while j < len(tokens) and _common_prefix(tokens[i], tokens[j]) == p:
                j += 1
            out.append((i, j, p))
            i = j
        else:
            i += 1
    return out


# Per-line numeric features shared by the personal fingerprint (stars) and the
# corpus atlas (lane priors): one definition so both measure the same thing.
NUMERIC_FEATURES = ("syllables", "words", "cons_density", "end_tail", "multi_len", "allit")


def device_kinds(tags) -> set[str]:
    """Device kinds on a line for flags, stars and the atlas. Weak (same-class)
    alliteration stays in the tag list as detail but is NOT a kind here: only
    same-phoneme (strong) alliteration counts as 'alliteration'."""
    return {t["kind"] for t in tags
            if not (t["kind"] == "alliteration" and t["confidence"] != "high")}


def has_alliteration(tokens: list[str]) -> bool:
    """Strong alliteration only (>= 2 content-word onsets with the same phoneme
    in the 4-word window)."""
    tag = _alliteration(tokens)
    return tag is not None and tag["confidence"] == "high"


def end_tail_len(tokens: list[str]) -> int:
    """Letters in the 2-nucleus tail of the last content word (0 when none)."""
    w = _last_content(tokens)
    return len(keys.tail_key(w, 2)) if w else 0


def line_features(syllables: int, cons_density: float, tokens: list[str],
                  kinds, multi_len: int = 0) -> dict:
    """Numeric feature snapshot of one line. ``kinds`` = device kinds on the line."""
    return {"syllables": int(syllables), "words": len(tokens),
            "cons_density": float(cons_density), "end_tail": end_tail_len(tokens),
            "multi_len": int(multi_len), "allit": "alliteration" in kinds}


def analyze_verse(lines: list[str], gazetteer=frozenset(), index=None) -> VerseReport:
    """Per-line tags plus the cross-line devices: rhyme scheme, multisyllabic
    rhymes, anaphora, epistrophe, anadiplosis and hook repetition."""
    texts = [l for l in lines]
    tokens = [tokenize(l) for l in texts]
    reports: list[LineReport] = []
    for i, text in enumerate(texts):
        devs = analyze_line(text, i + 1, texts[:i], gazetteer, index)
        reports.append(LineReport(i + 1, text, count_line(text),
                                  consonance_density(text), None, devs))

    letter_of = _rhyme_letters(tokens)
    for i, rep in enumerate(reports):
        rep.rhyme_letter = letter_of.get(i)
    scheme = "".join(rep.rhyme_letter or "-" for rep in reports)

    for idx, suffix in _multi_suffixes(texts).items():
        reports[idx].devices.append(_tag("multisyllabic_rhyme", suffix, "high"))

    # anaphora: >=2 consecutive lines sharing an opening that contains at least
    # one non-stopword. The reported span is the shared opening text itself.
    for first, end, p in anaphora_runs(tokens):
        for k in range(first, end):
            reports[k].devices.append(
                _tag("anaphora", _opening_surface(texts[k], p), "high"))

    lasts = [_last_content(t) for t in tokens]
    i = 0
    while i < len(texts):
        j = i + 1
        while j < len(texts) and lasts[j] and lasts[j] == lasts[i]:
            j += 1
        if j - i >= 2:
            for k in range(i, j):
                reports[k].devices.append(_tag("epistrophe", lasts[i], "high"))
        i = j

    # anadiplosis tags the predecessor line too (analyze_line tagged the latter).
    for i in range(1, len(texts)):
        prev_last = _last_content(tokens[i - 1])
        cur_first = _first_content(tokens[i])
        if prev_last and cur_first and prev_last == cur_first:
            reports[i - 1].devices.append(_tag("anadiplosis", prev_last, "high"))

    counts = Counter(" ".join(t) for t in tokens if t)
    for rep, t in zip(reports, tokens):
        key = " ".join(t)
        if key and counts[key] >= 2:
            rep.devices.append(_tag("hook_repeat", key[:24], "high"))

    return VerseReport(reports, scheme)
