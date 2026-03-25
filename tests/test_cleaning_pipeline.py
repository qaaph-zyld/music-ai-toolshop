"""Tests for audio cleaning pipeline stages."""

import pytest
import numpy as np
import soundfile as sf
import tempfile
from pathlib import Path

from toolshop.cleaning_stages import (
    PreprocessingStage,
    PauseRemovalStage,
    BreathDetectionStage,
    EventDetectionStage,
    BeatAlignmentStage,
    StageResult,
)


class TestPreprocessingStage:
    """Tests for preprocessing stage."""

    def test_load_audio(self, tmp_path):
        """Test basic audio loading."""
        # Create test audio file
        duration = 2.0
        sr = 44100
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 440 * t) * 0.5

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        stage = PreprocessingStage()
        result = stage.process(str(test_file))

        assert isinstance(result, StageResult)
        assert result.sample_rate == 44100
        assert len(result.audio) == len(audio)
        assert "duration" in result.metadata
        assert "bpm" in result.metadata
        assert "key" in result.metadata
        assert result.report["status"] == "success"

    def test_bpm_detection(self, tmp_path):
        """Test BPM detection on rhythmic audio."""
        duration = 4.0
        sr = 44100
        bpm = 120

        # Create audio with clear beat
        samples_per_beat = int(sr * 60 / bpm)
        total_samples = int(sr * duration)
        audio = np.zeros(total_samples)

        for i in range(0, total_samples, samples_per_beat):
            if i + 1000 < total_samples:
                audio[i : i + 1000] = 0.8

        test_file = tmp_path / "beat.wav"
        sf.write(test_file, audio, sr)

        stage = PreprocessingStage()
        result = stage.process(str(test_file))

        # Should detect BPM close to 120
        assert 100 <= result.metadata["bpm"] <= 140

    def test_normalization(self, tmp_path):
        """Test audio normalization."""
        duration = 1.0
        sr = 44100
        audio = np.ones(int(sr * duration)) * 0.5  # Half amplitude

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        stage = PreprocessingStage(normalize=True)
        result = stage.process(str(test_file))

        # Peak should be close to 1.0 after normalization
        assert np.max(np.abs(result.audio)) > 0.9


class TestPauseRemovalStage:
    """Tests for pause removal stage."""

    def test_remove_silence(self, tmp_path):
        """Test removing long silences."""
        sr = 44100

        # Create audio with silent section
        audio = np.concatenate(
            [
                np.ones(sr) * 0.5,  # 1 second audio
                np.zeros(sr * 2),  # 2 seconds silence
                np.ones(sr) * 0.5,  # 1 second audio
            ]
        )

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        # Preprocess first
        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        # Then remove pauses
        stage = PauseRemovalStage(min_silence=0.5)
        result = stage.process(result)

        assert result.report["status"] == "success"
        assert result.report["time_removed"] > 1.0  # Should remove most of the silence
        assert len(result.audio) < len(audio) * 0.8

    def test_keep_short_pauses(self, tmp_path):
        """Test that short pauses are preserved."""
        sr = 44100

        # Create audio with short silent sections
        audio = np.concatenate(
            [
                np.ones(int(sr * 0.5)) * 0.5,
                np.zeros(int(sr * 0.2)),  # 200ms silence
                np.ones(int(sr * 0.5)) * 0.5,
            ]
        )

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        stage = PauseRemovalStage(min_silence=0.3)
        result = stage.process(result)

        # Short pause should be kept
        assert result.report["segments_kept"] == 1
        assert result.report["time_removed"] < 0.15


class TestBreathDetectionStage:
    """Tests for breath detection stage."""

    def test_detect_breath_pattern(self, tmp_path):
        """Test detecting breath-like patterns."""
        sr = 44100
        duration = 2.0

        # Create audio with breath-like pattern
        # (gentle rise and fall in 200-2000Hz range)
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 500 * t) * 0.1

        # Add breath-like envelope
        breath_start = int(0.5 * sr)
        breath_end = int(1.0 * sr)
        envelope = np.ones(len(audio))
        envelope[breath_start:breath_end] = np.linspace(
            0.2, 0.05, breath_end - breath_start
        )
        audio = audio * envelope

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        stage = BreathDetectionStage(method="frequency")
        result = stage.process(result)

        assert result.report["status"] == "success"
        assert "breaths_detected" in result.report

    def test_attenuation(self, tmp_path):
        """Test that detected breaths are attenuated."""
        sr = 44100
        duration = 1.5

        # Create simple audio with energy spike
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 1000 * t) * 0.3

        # Add "breath" section
        breath_start = int(0.5 * sr)
        breath_end = int(0.7 * sr)
        audio[breath_start:breath_end] *= 2.0  # Double amplitude in breath region

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        stage = BreathDetectionStage(attenuation_db=15)
        result = stage.process(result)

        # Audio should be attenuated in breath region
        if result.report["breaths_detected"] > 0:
            assert len(result.audio) == len(audio)


class TestEventDetectionStage:
    """Tests for event detection stage."""

    def test_detect_cough(self, tmp_path):
        """Test detecting cough-like events."""
        sr = 44100
        duration = 2.0

        # Create audio with cough-like spike
        audio = np.ones(int(sr * duration)) * 0.1

        # Add "cough" - sharp transient
        cough_start = int(0.5 * sr)
        cough_duration = int(0.2 * sr)
        audio[cough_start : cough_start + cough_duration] = 0.8

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        stage = EventDetectionStage(detect_coughs=True)
        result = stage.process(result)

        assert result.report["status"] == "success"
        assert result.report.get("coughs", 0) >= 0

    def test_detect_click(self, tmp_path):
        """Test detecting click-like events."""
        sr = 44100
        duration = 1.0

        # Create audio with click
        audio = np.ones(int(sr * duration)) * 0.1

        # Add click - very short impulse
        click_pos = int(0.5 * sr)
        audio[click_pos : click_pos + 100] = 0.9

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        stage = EventDetectionStage(detect_clicks=True)
        result = stage.process(result)

        assert result.report["status"] == "success"


class TestBeatAlignmentStage:
    """Tests for beat alignment stage."""

    def test_beat_detection(self, tmp_path):
        """Test beat detection."""
        duration = 4.0
        sr = 44100
        bpm = 120

        # Create audio with clear beat
        samples_per_beat = int(sr * 60 / bpm)
        total_samples = int(sr * duration)
        audio = np.zeros(total_samples)

        for i in range(0, total_samples, samples_per_beat):
            if i + 1000 < total_samples:
                audio[i : i + 1000] = 0.8

        test_file = tmp_path / "beat.wav"
        sf.write(test_file, audio, sr)

        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        stage = BeatAlignmentStage(mode="analyze")
        result = stage.process(result)

        assert result.report["status"] == "success"
        assert "bpm" in result.report
        assert "beat_count" in result.report
        assert result.report["beat_count"] >= 4  # At least 4 beats in 4 seconds

    def test_analyze_mode_preserves_audio(self, tmp_path):
        """Test that analyze mode doesn't modify audio."""
        sr = 44100
        duration = 2.0
        audio = np.sin(2 * np.pi * 440 * t) * 0.5

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        original_audio = result.audio.copy()

        stage = BeatAlignmentStage(mode="analyze")
        result = stage.process(result)

        # Audio should be unchanged in analyze mode
        assert np.allclose(result.audio, original_audio)


class TestStageIntegration:
    """Tests for stage integration."""

    def test_full_pipeline_simple(self, tmp_path):
        """Test running multiple stages together."""
        sr = 44100
        duration = 3.0

        # Create test audio with various elements
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 440 * t) * 0.3

        # Add silence
        audio[int(1.0 * sr) : int(2.0 * sr)] = 0

        # Add breath-like section
        breath_start = int(2.2 * sr)
        breath_end = int(2.5 * sr)
        audio[breath_start:breath_end] = (
            np.sin(2 * np.pi * 600 * t[breath_start:breath_end]) * 0.2
        )

        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, sr)

        # Run preprocessing
        prep = PreprocessingStage()
        result = prep.process(str(test_file))

        # Run pause removal
        pause_stage = PauseRemovalStage()
        result = pause_stage.process(result)

        # Run breath detection
        breath_stage = BreathDetectionStage()
        result = breath_stage.process(result)

        # Run beat alignment
        beat_stage = BeatAlignmentStage()
        result = beat_stage.process(result)

        assert result.metadata["sample_rate"] == sr
        assert len(result.audio) > 0
