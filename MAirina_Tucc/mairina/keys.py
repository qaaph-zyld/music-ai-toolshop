"""Rhyme keys for Serbian/Balkan Latin text (diacritics kept).

A word is split into sound units: ``lj``, ``nj`` and ``dž`` are single sounds.
Nuclei are the vowels ``aeiou`` plus a syllabic ``r`` (an ``r`` with no
adjacent vowel), mirroring ``toolshop.syllables``.
"""

from __future__ import annotations

from toolshop.rhyme_miner import vowel_skeleton

VOWELS = frozenset("aeiou")
_DIGRAPHS = frozenset({"lj", "nj", "dž"})


def normalize(word: str) -> str:
    """Lowercase and keep letters only."""
    return "".join(c for c in (word or "").lower() if c.isalpha())


def _units(word: str) -> list[tuple[str, bool]]:
    """Split a word into (unit, is_nucleus) pairs."""
    w = normalize(word)
    out: list[tuple[str, bool]] = []
    i = 0
    while i < len(w):
        ch = w[i]
        if ch in VOWELS:
            out.append((ch, True))
        elif ch == "r":
            left = i > 0 and w[i - 1] in VOWELS
            right = i < len(w) - 1 and w[i + 1] in VOWELS
            out.append((ch, not left and not right))
        elif w[i:i + 2] in _DIGRAPHS:
            out.append((w[i:i + 2], False))
            i += 1
        else:
            out.append((ch, False))
        i += 1
    return out


def nuclei_count(word: str) -> int:
    return sum(1 for _, nuc in _units(word) if nuc)


def _tail_units(word: str, n: int) -> list[tuple[str, bool]]:
    units = _units(word)
    idx = [i for i, (_, nuc) in enumerate(units) if nuc]
    if n <= 0 or len(idx) < n:
        return units
    return units[idx[-n]:]


def tail_key(word: str, n: int = 2) -> str:
    """Everything from the n-th nucleus from the end: imaš/snimaš -> 'imaš'."""
    return "".join(u for u, _ in _tail_units(word, n))


def consonant_units(word: str, n: int = 2) -> list[str]:
    """Consonant sounds of the tail, in order, digraphs kept whole."""
    return [u for u, nuc in _tail_units(word, n) if not nuc]


def consonant_key(word: str, n: int = 2) -> str:
    """Consonants of ``tail_key`` without vowels: snimaš -> 'mš'."""
    return "".join(consonant_units(word, n))


def vowel_key(text: str) -> str:
    """Vowel skeleton via toolshop: 'da me imaš' -> 'aeia'."""
    return vowel_skeleton(text)


def vowel_tail(text: str, k: int = 2) -> str:
    return vowel_key(text)[-k:]
