"""Serbian syllable counter.

Rule: nuclei = vowels ``aeiou`` + syllabic **r** (an ``r`` with no adjacent
vowel).  Designed for diacritics-stripped Latin text as found in the Genius
corpus.  ``count_syllables`` works on a single word; ``count_line`` sums
across all words in a line.
"""

from __future__ import annotations

import re

_VOWELS = frozenset("aeiou")

# Pre-compiled word tokenizer — matches alphabetic runs (Latin only).
_WORD_RE = re.compile(r"[a-zA-Z]+")


def count_syllables(word: str) -> int:
    """Count syllables in a single word.

    Nuclei = vowels ``aeiou`` + syllabic **r** (``r`` with no adjacent vowel).
    """
    if not word:
        return 0

    # Work on lowercase for uniformity.
    w = word.lower()
    # Strip to alpha-only — numbers/punctuation contribute nothing.
    letters = [c for c in w if c.isalpha()]
    if not letters:
        return 0

    count = 0
    for i, ch in enumerate(letters):
        if ch in _VOWELS:
            count += 1
        elif ch == "r":
            # Syllabic r: no adjacent vowel (left or right).
            left_is_vowel = i > 0 and letters[i - 1] in _VOWELS
            right_is_vowel = i < len(letters) - 1 and letters[i + 1] in _VOWELS
            if not left_is_vowel and not right_is_vowel:
                count += 1
    return count


def count_line(text: str) -> int:
    """Count total syllables across all words in a line of text."""
    if not text or not text.strip():
        return 0
    return sum(count_syllables(m.group()) for m in _WORD_RE.finditer(text))


# ── German counter (lane lyrics-g4) ─────────────────────────────────
# Approximate: nuclei = vowel groups over aeiouy; umlauts map to base
# vowels, ß folds to ss. Consecutive vowels form one group, which makes
# diphthongs (ei, au, eu/äu, ie) count as one nucleus — right for the
# common cases. One exception modeled: a multi-vowel group ending the
# word on 'e' splits the trailing schwa into its own nucleus
# ("neue" -> eu|e, "Aue" -> au|e). Other hiatus cases are not modeled.
# Approximation only — a real German phonemizer is a separate lane.

_DE_CHAR_MAP = str.maketrans({
    "ä": "a", "ö": "o", "ü": "u",
    "Ä": "a", "Ö": "o", "Ü": "u",
    "ß": "ss", "ẞ": "ss",
})
_DE_VOWELS = frozenset("aeiouy")
_DE_WORD_RE = re.compile(r"[a-zA-ZäöüÄÖÜß]+")


def count_syllables_de(word: str) -> int:
    """Approximate syllable count for a single German word (vowel groups)."""
    if not word:
        return 0
    letters = [c for c in word.translate(_DE_CHAR_MAP).lower() if c.isalpha()]
    if not letters:
        return 0
    count = 0
    prev_vowel = False
    group_len = 0
    for ch in letters:
        is_vowel = ch in _DE_VOWELS
        if is_vowel:
            if not prev_vowel:
                count += 1
                group_len = 1
            else:
                group_len += 1
        prev_vowel = is_vowel
    # Word-final schwa: 'e' closing a multi-vowel group is its own nucleus.
    if group_len >= 2 and letters[-1] == "e":
        count += 1
    return count


def count_line_de(text: str) -> int:
    """Approximate syllable count across a German lyric line."""
    if not text or not text.strip():
        return 0
    return sum(count_syllables_de(m.group()) for m in _DE_WORD_RE.finditer(text))
