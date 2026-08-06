"""Tests for toolshop.scheme_checker — rhyme scheme detection and enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from toolshop.scheme_checker import check_scheme


# ── Test fixtures ─────────────────────────────────────────────────────

_AABB_LYRICS = """\
[Verse 1]
novac novac svuda novac
popac popac svuda popac
zdravo svete kako si
prijatelju moj ti

[Chorus]
babone babone
popac popac
babone babone
popac popac
"""

_ABAB_LYRICS = """\
[Verse 1]
novac novac svuda zdravo
popac popac svuda svete
novac novac svuda zdravo
popac popac svuda svete
"""


# ── Scheme detection (no expected scheme) ─────────────────────────────

def test_scheme_detection_no_expected(tmp_path: Path):
    """Without expected_scheme, reports detected scheme per section."""
    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_AABB_LYRICS, encoding="utf-8")

    result = check_scheme(lyrics_file)

    assert "sections" in result
    assert len(result["sections"]) >= 2
    for section in result["sections"]:
        assert "detected_scheme" in section
        assert "expected_scheme" in section
        assert section["expected_scheme"] is None
        assert "rhyme_factor" in section
        assert "match_pct" in section
        assert section["match_pct"] == 100.0
        assert "broken_lines" in section
        assert section["broken_lines"] == []


# ── Expected scheme comparison ────────────────────────────────────────

def test_expected_scheme_match(tmp_path: Path):
    """When detected matches expected, match_pct is 100 and no broken lines."""
    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_AABB_LYRICS, encoding="utf-8")

    result = check_scheme(lyrics_file, expected_scheme="AABB")

    # The verse section should be AABB (lines 0,1 share "oa", lines 2,3 share "oi")
    verse_sections = [s for s in result["sections"] if s["type"] == "strofa"]
    assert len(verse_sections) >= 1
    verse = verse_sections[0]
    assert verse["expected_scheme"] == "AABB"
    assert verse["line_count"] == 4
    assert verse["match_pct"] == 100.0
    assert verse["broken_lines"] == []


def test_expected_scheme_mismatch(tmp_path: Path):
    """When detected doesn't match expected, broken lines are reported."""
    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_AABB_LYRICS, encoding="utf-8")

    # Force a mismatch: expect ABAB for AABB content
    result = check_scheme(lyrics_file, expected_scheme="ABAB")

    # At least one section should have broken lines
    has_broken = any(s["broken_lines"] for s in result["sections"])
    assert has_broken, "Expected at least one section with broken lines"


# ── Fix suggestions ───────────────────────────────────────────────────

def test_fix_suggestions_for_broken_lines(tmp_path: Path):
    """Fix suggestions are generated for broken lines."""
    lyrics_file = tmp_path / "lyrics.txt"
    lyrics_file.write_text(_AABB_LYRICS, encoding="utf-8")

    result = check_scheme(lyrics_file, expected_scheme="ABAB")

    for section in result["sections"]:
        if section["broken_lines"]:
            assert len(section["fixes"]) > 0
            for fix in section["fixes"]:
                assert "line" in fix
                assert "word" in fix
                assert "expected_letter" in fix
                assert "candidates" in fix


# ── Empty / edge cases ────────────────────────────────────────────────

def test_empty_file(tmp_path: Path):
    """Empty file produces empty sections list."""
    lyrics_file = tmp_path / "empty.txt"
    lyrics_file.write_text("", encoding="utf-8")

    result = check_scheme(lyrics_file)
    assert result["sections"] == []


def test_no_section_labels(tmp_path: Path):
    """Lines without section labels are grouped as intro."""
    lyrics_file = tmp_path / "plain.txt"
    lyrics_file.write_text("novac novac\npopac popac\nzdravo svete\n", encoding="utf-8")

    result = check_scheme(lyrics_file)
    assert len(result["sections"]) == 1
    assert result["sections"][0]["type"] == "intro"
