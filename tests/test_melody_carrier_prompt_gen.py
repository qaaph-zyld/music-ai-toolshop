"""Tests for toolshop.melody_carrier.prompt_gen — Suno cover mode prompt generation.

All tests use pure Python string formatting (no external deps).
Uses tmp_path for output directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from toolshop.melody_carrier.prompt_gen import (
    generate_prompts,
    _energy_description,
    _drum_description,
    _format_chord_progression,
    _fidelity_to_pct,
)


TEST_ANALYSIS = {
    "bpm": 140.0,
    "key": "C#",
    "mode": "minor",
    "genre": "drill",
    "spectral_centroid": 2500.0,
    "spectral_bandwidth": 1800.0,
    "harmonic_ratio": 0.65,
    "onset_strength": 0.8,
    "tuning_offset": 5.0,
    "chord_progression": [
        {"chord": "C#:min", "start": 0.0, "end": 2.0},
        {"chord": "F:min", "start": 2.0, "end": 4.0},
    ],
    "detected_instruments": ["piano", "acoustic guitar", "synth pad"],
    "drum_pattern": {
        "kick_density": 2.0,
        "snare_density": 1.0,
        "hat_density": 4.0,
        "pattern_type": "trap",
    },
}


# ---------------------------------------------------------------------------
# generate_prompts
# ---------------------------------------------------------------------------

class TestGeneratePrompts:
    def test_generate_prompts_creates_three_files(self, tmp_path):
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", tmp_path)
        assert (tmp_path / "suno_prompt_minimal.txt").exists()
        assert (tmp_path / "suno_prompt_descriptive.txt").exists()
        assert (tmp_path / "suno_prompt_detailed.txt").exists()

    def test_generate_prompts_contains_genre(self, tmp_path):
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", tmp_path)
        for name, path in result.items():
            text = path.read_text(encoding="utf-8")
            assert "drill" in text, f"{name} prompt missing genre"

    def test_generate_prompts_contains_bpm_key(self, tmp_path):
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", tmp_path)
        for name, path in result.items():
            text = path.read_text(encoding="utf-8")
            assert "140.0" in text, f"{name} prompt missing bpm"
            assert "C#" in text, f"{name} prompt missing key"

    def test_descriptive_prompt_contains_chords(self, tmp_path):
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", tmp_path)
        desc_text = result["descriptive"].read_text(encoding="utf-8")
        assert "C#:min" in desc_text
        assert "F:min" in desc_text

    def test_generate_prompts_contains_audio_influence(self, tmp_path):
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", tmp_path)
        for name, path in result.items():
            text = path.read_text(encoding="utf-8")
            assert "Audio Influence: 55%" in text, f"{name} prompt missing Audio Influence"

    def test_generate_prompts_fidelity_values(self, tmp_path):
        for fidelity, expected_pct in [("low", 35), ("medium", 55), ("high", 70)]:
            result = generate_prompts(TEST_ANALYSIS, {}, fidelity, tmp_path / fidelity)
            text = result["minimal"].read_text(encoding="utf-8")
            assert f"Audio Influence: {expected_pct}%" in text

    def test_generate_prompts_no_substitutions(self, tmp_path):
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", tmp_path)
        detailed_text = result["detailed"].read_text(encoding="utf-8")
        # Should mention detected instruments
        assert "piano" in detailed_text
        assert "acoustic guitar" in detailed_text
        assert "synth pad" in detailed_text

    def test_generate_prompts_with_substitutions(self, tmp_path):
        subs = {"piano": "cathedral organ"}
        result = generate_prompts(TEST_ANALYSIS, subs, "medium", tmp_path)
        detailed_text = result["detailed"].read_text(encoding="utf-8")
        assert "cathedral organ" in detailed_text

    def test_generate_prompts_creates_output_dir(self, tmp_path):
        output = tmp_path / "nested" / "prompts"
        assert not output.exists()
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", output)
        assert output.exists()
        assert (output / "suno_prompt_minimal.txt").exists()

    def test_generate_prompts_returns_paths(self, tmp_path):
        result = generate_prompts(TEST_ANALYSIS, {}, "medium", tmp_path)
        assert set(result.keys()) == {"minimal", "descriptive", "detailed"}
        for name, path in result.items():
            assert isinstance(path, Path)
            assert path.exists()


# ---------------------------------------------------------------------------
# _energy_description
# ---------------------------------------------------------------------------

class TestEnergyDescription:
    def test_energy_high_percussive(self):
        result = _energy_description(onset_strength=0.8, harmonic_ratio=0.4)
        assert result == "high-energy percussive"

    def test_energy_laid_back(self):
        result = _energy_description(onset_strength=0.3, harmonic_ratio=0.8)
        assert result == "laid-back atmospheric"


# ---------------------------------------------------------------------------
# _drum_description
# ---------------------------------------------------------------------------

class TestDrumDescription:
    def test_drum_trap(self):
        drum_pattern = {"hat_density": 4.0, "kick_density": 2.0, "pattern_type": "trap"}
        result = _drum_description(drum_pattern)
        assert "trap hi-hats" in result

    def test_drum_four_floor(self):
        drum_pattern = {"hat_density": 1.0, "kick_density": 1.0, "pattern_type": "four_floor"}
        result = _drum_description(drum_pattern)
        assert "four-on-the-floor" in result

    def test_drum_empty(self):
        result = _drum_description({})
        assert "no drums detected" in result


# ---------------------------------------------------------------------------
# _format_chord_progression
# ---------------------------------------------------------------------------

class TestFormatChordProgression:
    def test_chord_compact(self):
        chord_prog = [
            {"chord": "Am", "start": 0.0, "end": 2.0},
            {"chord": "F", "start": 2.0, "end": 4.0},
            {"chord": "C", "start": 4.0, "end": 6.0},
            {"chord": "G", "start": 6.0, "end": 8.0},
        ]
        result = _format_chord_progression(chord_prog, compact=True)
        assert result == "Am - F - C - G"

    def test_chord_full(self):
        chord_prog = [
            {"chord": "Am", "start": 0.0, "end": 2.0},
            {"chord": "F", "start": 2.0, "end": 4.0},
        ]
        result = _format_chord_progression(chord_prog, compact=False)
        assert "0.0s-2.0s" in result
        assert "2.0s-4.0s" in result
        assert "Am" in result
        assert "F" in result

    def test_chord_empty(self):
        result = _format_chord_progression([], compact=True)
        assert result == "N/A"


# ---------------------------------------------------------------------------
# _fidelity_to_pct
# ---------------------------------------------------------------------------

class TestFidelityToPct:
    def test_fidelity_low(self):
        assert _fidelity_to_pct("low") == 35

    def test_fidelity_medium(self):
        assert _fidelity_to_pct("medium") == 55

    def test_fidelity_high(self):
        assert _fidelity_to_pct("high") == 70

    def test_fidelity_invalid(self):
        with pytest.raises(ValueError, match="Invalid fidelity"):
            _fidelity_to_pct("ultra")
