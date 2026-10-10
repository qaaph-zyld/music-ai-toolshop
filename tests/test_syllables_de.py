"""German syllable counter (G4 lane).

Approximate counter for ``language='de'`` rows: vowel groups (consecutive
vowel letters = one nucleus) over the German vowel set aeiouy + umlauts
(mapped to base vowels before grouping). Diphthongs (ei, au, eu/äu, ie)
collapse to one nucleus, which is correct for the common cases; trailing
-e stays counted (German -e is a real schwa, unlike English).

It is deliberately approximate — a real German phonemizer (phonemizer-de
or equivalent) is a later lane. The counter exists so ``syllable_count``
on de rows is sane instead of Serbian ``count_line`` garbage.
"""

from __future__ import annotations

from toolshop.syllables import count_line, count_line_de, count_syllables_de


def test_diphthong_ei_one_nucleus():
    assert count_syllables_de("Zeit") == 1


def test_diphthong_au_in_word():
    assert count_syllables_de("Auto") == 2  # au | o


def test_umlaut_o():
    assert count_syllables_de("schön") == 1


def test_umlaut_u():
    assert count_syllables_de("für") == 1


def test_umlaut_a_word():
    assert count_syllables_de("Mädchen") == 2  # ä | e


def test_umlaut_digraph_a_eu():
    assert count_syllables_de("Häuser") == 2  # äu | e


def test_eszett_word():
    assert count_syllables_de("Straße") == 2  # a | e (ß folds to ss)


def test_eszett_upper():
    assert count_syllables_de("STRASSE") == 2


def test_mixed_line():
    # schöne(2) neue(2) Welt(1)
    assert count_line_de("schöne neue Welt") == 5


def test_empty_and_nonalpha():
    assert count_syllables_de("") == 0
    assert count_syllables_de("187") == 0
    assert count_line_de("") == 0
    assert count_line_de("   ") == 0


def test_german_counter_differs_from_serbian_on_diphthong():
    # Serbian counter counts every vowel; German groups diphthongs.
    # "Auto": de = 2 (au | o), sr = 3 (a, u, o).
    assert count_line_de("Auto") == 2
    assert count_line("Auto") == 3


def test_serbian_counter_untouched():
    # Non-regression: Serbian syllabic-r behavior unchanged.
    assert count_line("prva pesma") == 4  # pr+va, pe+sma
