"""Serbian Latin grapheme -> phoneme units and consonant classes.

``lj``, ``nj`` and ``dž`` are single units; a syllabic ``r`` (no adjacent vowel)
is a nucleus, not a consonant. Consonant classes and voicing pairs follow the
Serbo-Croatian phonology used in the v2 research notes. Clitics carry no stress
and are excluded from density/dominance measurements.
"""

from __future__ import annotations

from mairina import keys
from mairina.used import tokenize

VOWELS = keys.VOWELS
DIGRAPHS = frozenset({"lj", "nj", "dž"})

PLOSIVE = frozenset("ptkbdg")
SIBILANT = frozenset({"s", "z", "š", "ž", "c", "č", "ć", "dž", "đ"})
LIQUID = frozenset({"l", "lj", "r"})
NASAL = frozenset({"m", "n", "nj"})
OTHER = frozenset({"f", "h", "v", "j"})
CLASSES = {"plosive": PLOSIVE, "sibilant": SIBILANT, "liquid": LIQUID,
           "nasal": NASAL, "other": OTHER}
_CLASS_OF = {u: name for name, members in CLASSES.items() for u in members}

# Voicing pairs (voiced -> voiceless). Serbian devoices final voiced obstruents.
VOICED_OF = {"p": "b", "t": "d", "k": "g", "s": "z", "š": "ž", "č": "dž", "ć": "đ"}

# Unstressed function words (enclitics/proclitics): de-weighted everywhere.
CLITICS = frozenset({
    "je", "se", "me", "te", "da", "u", "na", "mi", "ti", "si",
    "sam", "smo", "ste", "su", "ga", "mu", "joj", "ih", "im", "li",
    "bi", "ću", "će", "ćeš", "ćemo", "ćete",
    "i", "a", "o", "s", "sa", "k", "ka", "za", "od", "do", "iz", "po",
})


def is_clitic(token: str) -> bool:
    return token in CLITICS


def units(word: str) -> list[str]:
    """Phoneme units of a word, digraphs kept whole. Letters only, lowercase.

    ``keys.NO_DIGRAPH_WORDS`` are prefix-boundary exceptions (nadživeti,
    injekcija) where the apparent digraph is two separate sounds.
    """
    w = keys.normalize(word)
    merge = w not in keys.NO_DIGRAPH_WORDS
    out: list[str] = []
    i = 0
    while i < len(w):
        if merge and w[i:i + 2] in DIGRAPHS:
            out.append(w[i:i + 2])
            i += 2
        else:
            out.append(w[i])
            i += 1
    return out


def _is_nucleus(u: list[str], i: int) -> bool:
    x = u[i]
    if x in VOWELS:
        return True
    if x != "r":
        return False
    left = i > 0 and u[i - 1] in VOWELS
    right = i < len(u) - 1 and u[i + 1] in VOWELS
    return not left and not right


def nuclei(word: str) -> list[str]:
    u = units(word)
    return [x for i, x in enumerate(u) if _is_nucleus(u, i)]


def syllables(word: str) -> int:
    return keys.nuclei_count(word)


def consonants(word: str) -> list[str]:
    """Consonant units of a word (syllabic r excluded: it is a nucleus)."""
    u = units(word)
    return [x for i, x in enumerate(u) if not _is_nucleus(u, i)]


def consonant_class(unit: str) -> str | None:
    """'plosive'|'sibilant'|'liquid'|'nasal'|'other' for a consonant unit."""
    return _CLASS_OF.get(unit)


def voicing_partner(unit: str) -> str | None:
    """The voiced/voiceless counterpart (b<->p, dž<->č, ...), or None."""
    if unit in VOICED_OF:
        return VOICED_OF[unit]
    for voiceless, voiced in VOICED_OF.items():
        if voiced == unit:
            return voiceless
    return None


def onset(word: str) -> str | None:
    """First consonant unit of a word, or None when it starts with a vowel."""
    for u in units(word):
        if u in VOWELS:
            return None
        return u
    return None


def content_tokens(text: str) -> list[str]:
    """Lowercased tokens minus clitics (clitics carry no stress)."""
    return [t for t in tokenize(text) if t not in CLITICS]


def consonant_stream(text: str, exclude_clitics: bool = True) -> list[str]:
    """Consonant units across the text's words, in order."""
    toks = tokenize(text)
    if exclude_clitics:
        toks = [t for t in toks if t not in CLITICS]
    out: list[str] = []
    for t in toks:
        out.extend(consonants(t))
    return out


def dominant_class(text: str, exclude_clitics: bool = True) -> str | None:
    """Most frequent consonant class in the text (ties: class name, deterministic)."""
    counts: dict[str, int] = {}
    for u in consonant_stream(text, exclude_clitics):
        c = _CLASS_OF.get(u)
        if c:
            counts[c] = counts.get(c, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
