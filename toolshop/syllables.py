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
