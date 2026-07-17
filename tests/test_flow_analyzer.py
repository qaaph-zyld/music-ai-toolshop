"""Tests for toolshop.flow_analyzer — syllable density, pattern detection."""

from __future__ import annotations

import pytest

from toolshop.flow_analyzer import (
    flow_profile,
    detect_patterns,
    section_flow,
    FlowProfile,
    SectionFlow,
)


# ── Pattern detection ─────────────────────────────────────────────────

def test_detect_patterns_uniform():
    # All lines have same syllable count → "uniform"
    syl_counts = [8, 8, 8, 8]
    pattern = detect_patterns(syl_counts)
    assert pattern == "uniform"


def test_detect_patterns_alternating():
    # Alternating long/short → "alternating"
    syl_counts = [10, 4, 10, 4, 10, 4]
    pattern = detect_patterns(syl_counts)
    assert pattern == "alternating"


def test_detect_patterns_accelerating():
    # Increasing syllable counts → "accelerating"
    syl_counts = [4, 6, 8, 10, 12]
    pattern = detect_patterns(syl_counts)
    assert pattern == "accelerating"


def test_detect_patterns_decelerating():
    # Decreasing syllable counts → "decelerating"
    syl_counts = [12, 10, 8, 6, 4]
    pattern = detect_patterns(syl_counts)
    assert pattern == "decelerating"


def test_detect_patterns_free():
    # No clear pattern → "free"
    syl_counts = [7, 3, 12, 5, 9, 2, 11, 4]
    pattern = detect_patterns(syl_counts)
    assert pattern == "free"


def test_detect_patterns_empty():
    pattern = detect_patterns([])
    assert pattern == "free"


def test_detect_patterns_single():
    pattern = detect_patterns([8])
    assert pattern == "uniform"


# ── Section flow ──────────────────────────────────────────────────────

def test_section_flow_basic():
    """SectionFlow dataclass holds expected fields."""
    sf = SectionFlow(
        section_type="strofa",
        section_number=1,
        line_count=8,
        avg_syllables=7.5,
        syllable_counts=[8, 7, 8, 7, 8, 7, 8, 7],
        pattern="alternating",
    )
    assert sf.section_type == "strofa"
    assert sf.line_count == 8
    assert sf.avg_syllables == 7.5
    assert sf.pattern == "alternating"


# ── Flow profile ──────────────────────────────────────────────────────

def test_flow_profile_dataclass():
    """FlowProfile dataclass holds expected fields."""
    fp = FlowProfile(
        song_id=1,
        title="Test Song",
        artist="Test Artist",
        avg_syllables_per_line=7.5,
        syllable_density=0.75,
        speed_variation=0.15,
        pattern="alternating",
        sections=[],
    )
    assert fp.song_id == 1
    assert fp.avg_syllables_per_line == 7.5
    assert fp.pattern == "alternating"
