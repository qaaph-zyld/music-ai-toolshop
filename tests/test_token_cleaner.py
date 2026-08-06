"""Tests for toolshop.token_cleaner — audio metadata token removal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolshop.token_cleaner import clean_tokens


@pytest.fixture
def cliche_file(tmp_path: Path) -> Path:
    """Create a minimal cliche_list.json for testing."""
    data = {
        "audio_metadata_tokens": ["female", "male", "chorus", "verse", "bass",
                                  "kick", "vox", "bv", "bar", "fx", "db",
                                  "bars", "vocal"],
    }
    p = tmp_path / "cliche_list.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_bracketed_removal(cliche_file):
    """Bracketed [female], [male] tokens are removed."""
    text = "[female] Ovo je tekst\n[male] Druga linija"
    cleaned, report = clean_tokens(text, cliche_file)
    assert "[female]" not in cleaned
    assert "[male]" not in cleaned
    assert "Ovo je tekst" in cleaned
    assert "Druga linija" in cleaned
    assert report["removed_count"] == 2


def test_unbracketed_removal(cliche_file):
    """Unbracketed standalone tokens are removed."""
    text = "female Ovo je tekst\nDruga bass linija"
    cleaned, report = clean_tokens(text, cliche_file)
    assert "female" not in cleaned.lower().split()
    # "bass" should be removed but "linija" preserved
    assert "linija" in cleaned
    assert report["removed_count"] == 2


def test_lines_affected(cliche_file):
    """Report lists 1-indexed line numbers that had removals."""
    text = "Ovo je cisto\n[female] Ovo ima token\nI ovo je cisto"
    cleaned, report = clean_tokens(text, cliche_file)
    assert report["lines_affected"] == [2]


def test_per_token_counter(cliche_file):
    """Per-token Counter tracks removal frequency."""
    text = "[female] [female] [male] tekst"
    cleaned, report = clean_tokens(text, cliche_file)
    assert report["per_token"]["female"] == 2
    assert report["per_token"]["male"] == 1


def test_empty_line_cleanup(cliche_file):
    """Lines that become empty after removal are stripped."""
    text = "Prva linija\n[female]\nTreca linija"
    cleaned, report = clean_tokens(text, cliche_file)
    lines = [l for l in cleaned.split("\n") if l.strip()]
    assert len(lines) == 2
    assert "Prva linija" in cleaned
    assert "Treca linija" in cleaned


def test_no_false_positives(cliche_file):
    """Tokens embedded in words are not removed."""
    text = "Ovo je vocaloid pesma sa bassline melodijom"
    cleaned, report = clean_tokens(text, cliche_file)
    # "vocaloid" contains "vocal" but should not be stripped
    assert "vocaloid" in cleaned
    # "bassline" contains "bass" but should not be stripped
    assert "bassline" in cleaned
    assert report["removed_count"] == 0


def test_clean_text_no_tokens(cliche_file):
    """Text without any audio tokens is returned unchanged."""
    text = "Ovo je pesma\nBez meta tokena\nSve cisto"
    cleaned, report = clean_tokens(text, cliche_file)
    assert cleaned == text
    assert report["removed_count"] == 0
    assert report["lines_affected"] == []


def test_bars_before_bar(cliche_file):
    """'bars' should match before 'bar' (longest-first)."""
    text = "[bars] neki tekst"
    cleaned, report = clean_tokens(text, cliche_file)
    assert "[bars]" not in cleaned
    assert report["per_token"]["bars"] == 1
    assert report["per_token"].get("bar", 0) == 0
