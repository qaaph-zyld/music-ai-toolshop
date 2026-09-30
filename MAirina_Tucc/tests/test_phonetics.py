"""phonetics: Serbian Latin units, consonant classes, voicing, clitics."""

import pytest

from mairina import phonetics as P


def test_digraphs_are_single_units():
    assert P.units("ljubav") == ["lj", "u", "b", "a", "v"]
    assert P.units("džaba") == ["dž", "a", "b", "a"]
    assert P.units("njegov") == ["nj", "e", "g", "o", "v"]
    assert P.units("kavez") == ["k", "a", "v", "e", "z"]          # no false digraph


def test_prefix_boundary_digraphs_stay_two_letters():
    # nad-živeti, in-jekcija, ...: the apparent digraph crosses a morpheme seam
    assert P.units("nadživeti") == ["n", "a", "d", "ž", "i", "v", "e", "t", "i"]
    assert P.units("injekcija") == ["i", "n", "j", "e", "k", "c", "i", "j", "a"]
    assert P.syllables("nadživeti") == 4 and P.syllables("konjunkcija") == 4


def test_syllabic_r_is_nucleus():
    assert P.nuclei("prst") == ["r"]
    assert P.nuclei("trava") == ["a", "a"]      # r next to a vowel is a consonant
    assert P.syllables("krv") == 1
    assert P.syllables("srce") == 2


def test_consonant_classes():
    for u in "ptkbdg":
        assert P.consonant_class(u) == "plosive"
    for u in ("s", "z", "š", "ž", "c", "č", "ć", "dž", "đ"):
        assert P.consonant_class(u) == "sibilant", u
    for u in ("l", "lj", "r"):
        assert P.consonant_class(u) == "liquid"
    for u in ("m", "n", "nj"):
        assert P.consonant_class(u) == "nasal"
    for u in ("f", "h", "v", "j"):
        assert P.consonant_class(u) == "other"
    assert P.consonant_class("a") is None and P.consonant_class("e") is None


def test_voicing_pairs_are_symmetric():
    for voiced, voiceless in (("b", "p"), ("d", "t"), ("g", "k"), ("z", "s"),
                              ("ž", "š"), ("dž", "č"), ("đ", "ć")):
        assert P.voicing_partner(voiced) == voiceless
        assert P.voicing_partner(voiceless) == voiced
    assert P.voicing_partner("m") is None and P.voicing_partner("j") is None


def test_clitics():
    for w in ("je", "se", "me", "da", "na", "su", "ga", "bi", "ću", "će",
              "i", "sa", "za", "od", "po"):
        assert P.is_clitic(w)
    assert not P.is_clitic("lava") and not P.is_clitic("ko")


def test_onset_is_first_consonant_only():
    assert P.onset("krevet") == "k"
    assert P.onset("ljubav") == "lj"
    assert P.onset("džep") == "dž"
    assert P.onset("ime") is None              # vowel onset: not alliteration material


def test_consonant_stream_skips_clitics_and_syllabic_r():
    assert P.consonant_stream("da mi prst") == ["p", "s", "t"]     # da/mi out, r is nucleus
    assert P.consonant_stream("da mi prst", exclude_clitics=False) == ["d", "m", "p", "s", "t"]


def test_dominant_class_deterministic():
    assert P.dominant_class("kučka kuca kroz kapiju") == "plosive"     # k-heavy
    assert P.dominant_class("mama nemirna nina") == "nasal"
    assert P.dominant_class("aeiou") is None
    assert P.dominant_class("da me na") is None                        # all clitics, nothing counted
    assert P.dominant_class("da me na", exclude_clitics=False) == "nasal"
