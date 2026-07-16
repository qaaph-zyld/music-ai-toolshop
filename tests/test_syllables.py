"""Tests for Serbian syllable counter."""

from __future__ import annotations

import pytest

from toolshop.syllables import count_syllables, count_line


# ── Single-word tests (30+ hand-checked) ──────────────────────────────

@pytest.mark.parametrize("word,expected", [
    # Basic vowel-nucleus words
    ("a", 1),
    ("da", 1),
    ("ma", 1),
    ("ne", 1),
    ("ni", 1),
    ("ko", 1),
    ("su", 1),
    # Two vowels
    ("mama", 2),
    ("voda", 2),
    ("ruka", 2),
    ("noce", 2),  # no diacritics
    # Three+ vowels
    ("patrone", 3),
    ("diskoteka", 4),
    ("fantazije", 4),
    ("ljubav", 2),
    # Syllabic-r cases (r with no adjacent vowel)
    ("prst", 1),
    ("vrt", 1),
    ("trn", 1),
    ("crkva", 2),  # crk-va: syllabic r + a
    ("srce", 2),   # sr-ce: syllabic r + e
    ("brzo", 2),   # br-zo: syllabic r + o
    ("grlo", 2),   # gr-lo: syllabic r + o
    ("drvo", 2),   # dr-vo: syllabic r + o
    ("mrak", 1),   # mr-a-k: syllabic r + a → 2? No: m-r-a-k → r has adjacent a → r not syllabic → a is nucleus → 1
    ("prsti", 2),  # pr-sti: syllabic r + i
    # r NOT syllabic when adjacent to vowel
    ("rad", 1),    # r adjacent to a → a is nucleus, r is consonant
    ("rijeka", 3), # ri-je-ka: r adjacent to i → i is nucleus
    ("ruka", 2),   # r adjacent to u → u is nucleus
    # Loanwords / English
    ("money", 2),  # mo-ney → 2
    ("cash", 1),   # 1
    ("gangsta", 2),
    ("fashion", 3),  # f-a-sh-i-o-n: 3 vowels
    ("bmw", 0),    # no vowels, no syllabic r
    ("lol", 1),    # o is vowel
    # Diacritics-stripped forms (as they appear in corpus)
    ("izaci", 3),  # i-za-ci → 3
    ("cu", 1),     # c + u → 1
    ("nagruvam", 3),  # na-gru-vam → 3
    ("gadjam", 2),    # ga-djam → 2
    ("sve", 1),       # sve → 1
    ("znas", 1),      # znas → 1
    # Edge cases
    ("", 0),
    ("123", 0),
    ("!", 0),
    ("n", 0),       # single consonant
    ("r", 1),       # single r → syllabic
])
def test_count_syllables(word: str, expected: int) -> None:
    assert count_syllables(word) == expected


# ── Line-level tests ──────────────────────────────────────────────────

def test_count_line_simple() -> None:
    # "da da da" → 3 words × 1 syllable = 3
    assert count_line("da da da") == 3


def test_count_line_mixed() -> None:
    # "znas se ko je peka" → 1+1+1+1+2 = 6
    assert count_line("znas se ko je peka") == 6


def test_count_line_empty() -> None:
    assert count_line("") == 0


def test_count_line_with_punctuation() -> None:
    # "Zna se ko je Peka, lomi se diskoteka"
    # Zna(1) se(1) ko(1) je(1) Peka(2) lomi(2) se(1) diskoteka(4) = 13
    assert count_line("Zna se ko je Peka, lomi se diskoteka") == 13


def test_count_line_cyrillic_not_handled_here() -> None:
    # count_line operates on Latin text; Cyrillic transliteration happens upstream
    # Just verify it doesn't crash on non-Latin
    result = count_line("прст")
    assert isinstance(result, int)
