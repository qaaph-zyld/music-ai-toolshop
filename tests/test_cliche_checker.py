"""Tests for toolshop.cliche_checker — cliché density and audio token detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolshop.cliche_checker import check_cliches


@pytest.fixture
def cliche_file(tmp_path: Path) -> Path:
    """Create a test cliche_list.json."""
    data = {
        "english_cliches": ["neon", "echoes", "shatter", "tapestry", "whisper",
                            "cascade", "embrace", "yearning", "tender",
                            "dance with", "beneath the sky"],
        "english_extended": ["heart", "soul", "fade away", "memories", "tears",
                             "dreams", "forever", "alone", "darkness", "light"],
        "balkan_cliches": ["duša", "srce"],
        "audio_metadata_tokens": ["female", "male", "chorus", "verse", "bass",
                                  "kick", "vox", "bv", "bar", "fx", "db",
                                  "bars", "vocal"],
    }
    p = tmp_path / "cliche_list.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_single_word_cliche_detection(cliche_file):
    """Single-word clichés are detected."""
    text = "neon echoes in the darkness"
    result = check_cliches(text, cliche_file)
    assert result["total_cliches"] >= 3  # neon, echoes, darkness
    assert result["density_pct"] > 0


def test_multi_word_cliche_detection(cliche_file):
    """Multi-word cliché phrases are detected."""
    text = "we dance with the stars beneath the sky"
    result = check_cliches(text, cliche_file)
    # "dance with" and "beneath the sky" should be found
    all_terms = []
    for hit in result["per_line_hits"]:
        all_terms.extend(hit["terms"])
    assert "dance with" in all_terms
    assert "beneath the sky" in all_terms


def test_density_calculation(cliche_file):
    """Density is (cliche tokens / total tokens) * 100."""
    text = "neon heart"
    result = check_cliches(text, cliche_file)
    # 2 cliché tokens / 2 total tokens * 100 = 100.0
    assert result["density_pct"] == 100.0


def test_audio_token_flagging(cliche_file):
    """Audio metadata tokens are counted separately."""
    text = "[female] this is a verse about the heart"
    result = check_cliches(text, cliche_file)
    assert result["audio_token_count"] >= 1  # "verse" at least
    assert 1 in result["audio_token_lines"]


def test_line_number_reporting(cliche_file):
    """Per-line hits include correct 1-indexed line numbers."""
    text = "clean line\nneon and heart\nanother clean line"
    result = check_cliches(text, cliche_file)
    assert len(result["per_line_hits"]) == 1
    assert result["per_line_hits"][0]["line"] == 2


def test_empty_text(cliche_file):
    """Empty text returns zero counts."""
    result = check_cliches("", cliche_file)
    assert result["total_cliches"] == 0
    assert result["density_pct"] == 0.0
    assert result["audio_token_count"] == 0


def test_no_cliches(cliche_file):
    """Text without clichés returns zero."""
    text = "Ovo je pesma o gradu i ljudima"
    result = check_cliches(text, cliche_file)
    assert result["total_cliches"] == 0
    assert result["density_pct"] == 0.0


def test_balkan_cliches(cliche_file):
    """Balkan clichés are detected when include_balkan=True."""
    text = "moja dusa i srce"
    result = check_cliches(text, cliche_file, include_balkan=True)
    # "dusa" (ascii-folded from "duša") and "srce" should be found
    assert result["total_cliches"] >= 2


def test_balkan_not_included_by_default(cliche_file):
    """Balkan clichés are not checked when include_balkan=False."""
    text = "moja dusa i srce"
    result = check_cliches(text, cliche_file, include_balkan=False)
    assert result["total_cliches"] == 0
