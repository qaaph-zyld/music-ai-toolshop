"""Tests for toolshop.rhyme_miner — vowel-skeleton rhyme engine."""

from __future__ import annotations

import pytest

from toolshop.rhyme_miner import (
    vowel_skeleton,
    extract_end_rhyme,
    find_rhymes,
    find_internal_rhymes,
    rhyme_factor,
    infer_scheme,
    multisyllabic_rhymes,
    RhymeMatch,
)


# ── Vowel skeleton extraction ─────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("da", "a"),
    ("mama", "aa"),
    ("voda", "oa"),
    ("babone", "aoe"),
    ("kamineto", "aieo"),
    ("prst", "r"),           # syllabic r
    ("srce", "re"),          # syllabic r + e
    ("brzo", "ro"),          # syllabic r + o
    ("zdravo", "ao"),        # z-d-r-a-v-o → a, o (r not syllabic, followed by vowel)
    ("ljubav", "ua"),        # l-j-u-b-a-v → u, a
    ("novac", "oa"),         # n-o-v-a-c → o, a
    ("", ""),
    ("123", ""),
    ("BMW", ""),             # no vowels, no syllabic r
    ("da da da", "aaa"),     # three words, one vowel each
    ("novac novac", "oaoa"), # two words
    ("prst prst", "rr"),     # two syllabic-r words
])
def test_vowel_skeleton(text, expected):
    assert vowel_skeleton(text) == expected


# ── End rhyme extraction ──────────────────────────────────────────────

def test_extract_end_rhyme_basic():
    # "babone" → skeleton "aoe", last 2 = "oe"
    assert extract_end_rhyme("babone", n_syllables=2) == "oe"


def test_extract_end_rhyme_full():
    # When n_syllables >= len(skeleton), return full skeleton
    assert extract_end_rhyme("da", n_syllables=2) == "a"


def test_extract_end_rhyme_multiword():
    # "novac babone" → skeleton "oaaoe" (oa + aoe), last 3 = "aoe"
    assert extract_end_rhyme("novac babone", n_syllables=3) == "aoe"


def test_extract_end_rhyme_empty():
    assert extract_end_rhyme("", n_syllables=2) == ""


def test_extract_end_rhyme_syllabic_r():
    # "prst" → skeleton "r", last 1 = "r"
    assert extract_end_rhyme("prst", n_syllables=1) == "r"


# ── End rhyme matching ────────────────────────────────────────────────

def test_find_rhymes_basic():
    lines = ["novac novac", "popac popac", "zdravo svete"]
    matches = find_rhymes(lines, min_match=2)
    # "novac novac" (oaoa) and "popac popac" (oa oa) share end-rhyme "oa"
    assert len(matches) >= 1
    # Check that at least one match group has 2+ lines
    group_sizes = [len(m.line_indices) for m in matches]
    assert any(s >= 2 for s in group_sizes)


def test_find_rhymes_no_match():
    lines = ["da", "ne", "mi"]
    matches = find_rhymes(lines, min_match=2)
    # All have different 1-syllable skeletons, no rhymes with min_match=2
    # But "da"→"a", "ne"→"e", "mi"→"i" — all different
    # With min_match=1 they'd match themselves; with min_match=2 they need 2-syl skeletons
    assert len(matches) == 0


def test_find_rhymes_min_match_filter():
    lines = ["da da", "ne ne"]
    # "da da"→"aa", "ne ne"→"ee" — end-rhyme "aa" vs "ee", no match
    matches = find_rhymes(lines, min_match=2)
    assert len(matches) == 0


def test_find_rhymes_returns_rhyme_match():
    lines = ["babone", "kamineto"]
    # "babone"→"aoe", "kamineto"→"aieo"
    # end-2: "oe" vs "eo" — not quite
    # Let's use lines that definitely rhyme
    lines = ["novac", "popac"]
    # "novac"→"oa", "popac"→"oa" — end-2: "oa" == "oa"
    matches = find_rhymes(lines, min_match=2)
    assert len(matches) == 1
    match = matches[0]
    assert match.vowel_skeleton == "oa"
    assert match.match_length == 2
    assert match.rhyme_type == "end"
    assert set(match.line_indices) == {0, 1}


# ── Internal rhymes ───────────────────────────────────────────────────

def test_find_internal_rhymes_basic():
    # "novac popac" has internal rhyme: "oa" ... "oa"
    line = "novac popac"
    matches = find_internal_rhymes(line, min_match=2)
    assert len(matches) >= 1
    assert matches[0].vowel_skeleton == "oa"
    assert matches[0].rhyme_type == "internal"


def test_find_internal_rhymes_none():
    line = "da ne mi"
    # "a", "e", "i" — no 2-syllable internal rhymes
    matches = find_internal_rhymes(line, min_match=2)
    assert len(matches) == 0


def test_find_internal_rhymes_multisyllabic():
    # "babone kamineto" → "aoe" and "aieo" — no match
    # "babone babone" → "aoe" and "aoe" — match!
    line = "babone babone"
    matches = find_internal_rhymes(line, min_match=3)
    assert len(matches) >= 1
    assert matches[0].vowel_skeleton == "aoe"


# ── Rhyme factor ──────────────────────────────────────────────────────

def test_rhyme_factor_no_rhymes():
    lines = ["da", "ne", "mi"]
    # No rhymes → factor = 0
    factor = rhyme_factor(lines)
    assert factor == 0.0


def test_rhyme_factor_with_rhymes():
    lines = ["novac", "popac", "zdravo"]
    # "novac"→"oa", "popac"→"oa" — rhyme. "zdravo"→"aao" — end-2 "ao" != "oa"
    # Rhymed syllables: 2 (from "oa") × 2 lines = 4? Or just the rhyme portion.
    factor = rhyme_factor(lines)
    assert factor > 0.0


def test_rhyme_factor_all_rhyme():
    lines = ["novac", "popac", "lovac"]
    # All end in "oa" → high rhyme factor
    factor = rhyme_factor(lines)
    assert factor > 0.5


# ── Scheme inference ──────────────────────────────────────────────────

def test_infer_scheme_aabb():
    # 4 lines: 1-2 rhyme, 3-4 rhyme
    groups = [
        RhymeMatch(line_indices=[0, 1], vowel_skeleton="oa", match_length=2, rhyme_type="end"),
        RhymeMatch(line_indices=[2, 3], vowel_skeleton="ie", match_length=2, rhyme_type="end"),
    ]
    scheme = infer_scheme(groups, n_lines=4)
    assert scheme == "AABB"


def test_infer_scheme_abab():
    # 4 lines: 1-3 rhyme, 2-4 rhyme
    groups = [
        RhymeMatch(line_indices=[0, 2], vowel_skeleton="oa", match_length=2, rhyme_type="end"),
        RhymeMatch(line_indices=[1, 3], vowel_skeleton="ie", match_length=2, rhyme_type="end"),
    ]
    scheme = infer_scheme(groups, n_lines=4)
    assert scheme == "ABAB"


def test_infer_scheme_chain():
    # 3 lines all rhyme with each other
    groups = [
        RhymeMatch(line_indices=[0, 1, 2], vowel_skeleton="oa", match_length=2, rhyme_type="end"),
    ]
    scheme = infer_scheme(groups, n_lines=3)
    assert scheme == "AAA"


def test_infer_scheme_free():
    # No rhymes
    scheme = infer_scheme([], n_lines=4)
    assert scheme == "free"


def test_infer_scheme_single_rhyme_pair():
    # 4 lines, only 1-2 rhyme
    groups = [
        RhymeMatch(line_indices=[0, 1], vowel_skeleton="oa", match_length=2, rhyme_type="end"),
    ]
    scheme = infer_scheme(groups, n_lines=4)
    assert scheme == "AABC"


# ── Multisyllabic rhymes ──────────────────────────────────────────────

def test_multisyllabic_rhymes_basic():
    lines = ["babone", "kamineto", "babone"]
    # "babone"→"aoe" (3-syl), "kamineto"→"aieo" (4-syl)
    # "babone" appears twice → 3-syl rhyme
    matches = multisyllabic_rhymes(lines, min_length=3)
    assert len(matches) >= 1
    assert matches[0].match_length >= 3


def test_multisyllabic_rhymes_filter():
    lines = ["novac", "popac"]
    # "novac"→"oa" (2-syl), "popac"→"oa" (2-syl)
    # min_length=3 → no matches
    matches = multisyllabic_rhymes(lines, min_length=3)
    assert len(matches) == 0


# ── espeak-ng validation (slow, requires system install) ──────────────

@pytest.mark.slow
def test_espeak_validation():
    """Validate vowel-skeleton method against espeak-ng phonemes."""
    try:
        from toolshop.rhyme_miner import validate_with_espeak
    except ImportError:
        pytest.skip("espeak-ng not available")
    try:
        result = validate_with_espeak("zdravo")
    except RuntimeError:
        pytest.skip("espeak-ng not installed")
    assert result is not None
    assert len(result) > 0
