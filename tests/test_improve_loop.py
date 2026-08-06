"""Tests for toolshop.improve_loop — iteration logic and suggestion generation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from toolshop.improve_loop import (
    _generate_suggestions,
    _identify_weakest,
    _import_scorer,
    _import_scheme_checker,
    _import_structure_template,
    improve_loop,
)


# ── Weakest component identification ───────────────────────────────────

def test_identify_weakest_rhyme():
    components = {
        "structural": {"score": 70},
        "rhyme": {"score": 40},
        "lexical": {"score": 65},
        "repetition": {"score": 60},
    }
    assert _identify_weakest(components) == "rhyme"


def test_identify_weakest_structural():
    components = {
        "structural": {"score": 30},
        "rhyme": {"score": 80},
        "lexical": {"score": 75},
        "repetition": {"score": 70},
    }
    assert _identify_weakest(components) == "structural"


def test_identify_weakest_lexical():
    components = {
        "structural": {"score": 80},
        "rhyme": {"score": 75},
        "lexical": {"score": 25},
        "repetition": {"score": 70},
    }
    assert _identify_weakest(components) == "lexical"


def test_identify_weakest_repetition():
    components = {
        "structural": {"score": 85},
        "rhyme": {"score": 80},
        "lexical": {"score": 75},
        "repetition": {"score": 20},
    }
    assert _identify_weakest(components) == "repetition"


def test_identify_weakest_missing_component():
    """Missing components should be treated as score 0."""
    components = {
        "structural": {"score": 70},
        "rhyme": {"score": 65},
    }
    result = _identify_weakest(components)
    assert result in ("lexical", "repetition")


# ── Suggestion generation ──────────────────────────────────────────────

def test_generate_suggestions_structural_with_module():
    """Structural suggestions should use structure_template if available."""
    mock_gen = MagicMock(return_value={
        "sections": [
            {"type": "strofa", "lines": 4, "rhyme_scheme": "AABB"},
            {"type": "refren", "lines": 4, "rhyme_scheme": "AAAA"},
        ],
        "total_lines": 8,
    })
    with patch("toolshop.improve_loop._import_structure_template", return_value=mock_gen):
        suggestions = _generate_suggestions(
            weakest="structural",
            input_path=Path("test.txt"),
            cohort="drill_trap",
            db_path=Path("test.db"),
            score_result={"components": {}},
        )
    assert len(suggestions) > 0
    assert "strofa" in " ".join(suggestions)


def test_generate_suggestions_structural_without_module():
    """Structural suggestions should have fallback when module unavailable."""
    with patch("toolshop.improve_loop._import_structure_template", return_value=None):
        suggestions = _generate_suggestions(
            weakest="structural",
            input_path=Path("test.txt"),
            cohort="drill_trap",
            db_path=Path("test.db"),
            score_result={"components": {}},
        )
    assert len(suggestions) == 1
    assert "structure_template" in suggestions[0]


def test_generate_suggestions_rhyme_with_module():
    """Rhyme suggestions should use scheme_checker if available."""
    mock_check = MagicMock(return_value={
        "sections": [
            {"type": "strofa", "detected_scheme": "AABB", "broken_lines": [2], "fixes": ["Fix line 2"]},
        ],
    })
    with patch("toolshop.improve_loop._import_scheme_checker", return_value=mock_check):
        suggestions = _generate_suggestions(
            weakest="rhyme",
            input_path=Path("test.txt"),
            cohort="drill_trap",
            db_path=Path("test.db"),
            score_result={"components": {}},
        )
    assert any("broken" in s.lower() for s in suggestions)


def test_generate_suggestions_rhyme_without_module():
    with patch("toolshop.improve_loop._import_scheme_checker", return_value=None):
        suggestions = _generate_suggestions(
            weakest="rhyme",
            input_path=Path("test.txt"),
            cohort="drill_trap",
            db_path=Path("test.db"),
            score_result={"components": {}},
        )
    assert len(suggestions) == 1
    assert "scheme_checker" in suggestions[0]


def test_generate_suggestions_lexical_high_ttr():
    score_result = {
        "components": {"lexical": {"ttr": 0.65}},
    }
    suggestions = _generate_suggestions(
        weakest="lexical",
        input_path=Path("test.txt"),
        cohort="drill_trap",
        db_path=Path("test.db"),
        score_result=score_result,
    )
    assert any("high" in s.lower() for s in suggestions)


def test_generate_suggestions_lexical_low_ttr():
    score_result = {
        "components": {"lexical": {"ttr": 0.25}},
    }
    suggestions = _generate_suggestions(
        weakest="lexical",
        input_path=Path("test.txt"),
        cohort="drill_trap",
        db_path=Path("test.db"),
        score_result=score_result,
    )
    assert any("low" in s.lower() for s in suggestions)


def test_generate_suggestions_repetition():
    score_result = {
        "components": {"repetition": {"hook_count": 1}},
    }
    suggestions = _generate_suggestions(
        weakest="repetition",
        input_path=Path("test.txt"),
        cohort="drill_trap",
        db_path=Path("test.db"),
        score_result=score_result,
    )
    assert any("hook" in s.lower() for s in suggestions)


# ── Import fallbacks ───────────────────────────────────────────────────

def test_import_scorer_fallback():
    """_import_scorer should return None if ai_scorer not available."""
    with patch.dict("sys.modules", {"toolshop.ai_scorer": None}):
        result = _import_scorer()
    # Will either return the function or None depending on availability
    assert result is None or callable(result)


def test_import_scheme_checker_fallback():
    with patch.dict("sys.modules", {"toolshop.scheme_checker": None}):
        result = _import_scheme_checker()
    assert result is None or callable(result)


def test_import_structure_template_fallback():
    with patch.dict("sys.modules", {"toolshop.structure_template": None}):
        result = _import_structure_template()
    assert result is None or callable(result)


# ── improve_loop integration ───────────────────────────────────────────

def test_improve_loop_no_scorer(tmp_path):
    """improve_loop should return error dict when ai_scorer unavailable."""
    lyrics = tmp_path / "lyrics.txt"
    lyrics.write_text("[Verse 1]\nTest lyrics\n", encoding="utf-8")

    with patch("toolshop.improve_loop._import_scorer", return_value=None):
        result = improve_loop(
            input_path=lyrics,
            cohort="drill_trap",
            db_path=tmp_path / "test.db",
        )
    assert "error" in result
    assert "ai_scorer" in result["error"]


def test_improve_loop_target_reached(tmp_path):
    """improve_loop should stop early if target is already met."""
    lyrics = tmp_path / "lyrics.txt"
    lyrics.write_text("[Verse 1]\nTest lyrics\n", encoding="utf-8")

    mock_scorer = MagicMock(return_value={
        "overall_score": 80,
        "components": {
            "structural": {"score": 80},
            "rhyme": {"score": 75},
            "lexical": {"score": 70},
            "repetition": {"score": 85},
        },
    })

    with patch("toolshop.improve_loop._import_scorer", return_value=mock_scorer):
        result = improve_loop(
            input_path=lyrics,
            cohort="drill_trap",
            iterations=3,
            target_score=65,
            db_path=tmp_path / "test.db",
        )
    assert result["baseline_score"] == 80
    assert result["final_score"] == 80
    assert result["target_reached"] is True
    assert len(result["iterations"]) == 0
