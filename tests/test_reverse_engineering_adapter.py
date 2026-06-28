import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from toolshop import reverse_engineering_adapter


def test_analyze_track_file_not_found():
    with pytest.raises(FileNotFoundError):
        reverse_engineering_adapter.analyze_track(Path("nonexistent.wav"))


@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
def test_analyze_track_advanced_defaults(mock_feature_extractor, mock_audio_processor, tmp_path):
    mock_audio = MagicMock()
    mock_sr = 22050
    mock_audio_processor.load_audio.return_value = (mock_audio, mock_sr)
    mock_feature_extractor.extract_features.return_value = {
        "duration": 120.5,
        "tempo": 128.0,
        "beat_count": 4,
        "key": "F",
        "mode": "major",
        "spectral_centroid": 2100.0,
        "spectral_bandwidth": 2600.0,
        "harmonic_ratio": 0.75,
        "tuning_offset": 0.0,
        "onset_strength": 0.5,
    }

    test_file = tmp_path / "test.wav"
    test_file.touch()

    result = reverse_engineering_adapter.analyze_track(test_file)

    assert result["file"] == str(test_file)
    assert result["duration_seconds"] == 120.5
    assert result["bpm"] == 128.0
    assert result["key"] == "F"
    assert result["mode"] == "major"
    assert result["analysis_backend"] == "wav_reverse_engineer"
    mock_audio_processor.load_audio.assert_called_once_with(
        str(test_file), target_sr=22050, mono=True
    )
    mock_feature_extractor.extract_features.assert_called_once_with(mock_audio, mock_sr)


@patch("toolshop.reverse_engineering_adapter._WAV_RE_AVAILABLE", False)
@patch("toolshop.reverse_engineering_adapter._basic_analysis")
def test_analyze_track_fallback_when_advanced_unavailable(mock_basic, tmp_path):
    mock_basic.return_value = {"file": "test.wav", "analysis_backend": "basic_librosa"}
    test_file = tmp_path / "test.wav"
    test_file.touch()
    result = reverse_engineering_adapter.analyze_track(test_file)
    assert result["analysis_backend"] == "basic_librosa"
    mock_basic.assert_called_once_with(test_file)


@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
def test_analyze_track_basic_backend(mock_feature_extractor, mock_audio_processor, tmp_path):
    with patch("toolshop.reverse_engineering_adapter._basic_analysis") as mock_basic:
        mock_basic.return_value = {"file": "test.wav", "analysis_backend": "basic_librosa"}
        test_file = tmp_path / "test.wav"
        test_file.touch()
        result = reverse_engineering_adapter.analyze_track(test_file, backend="basic")
        assert result["analysis_backend"] == "basic_librosa"
        mock_basic.assert_called_once_with(test_file)
        mock_audio_processor.load_audio.assert_not_called()


@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
def test_analyze_track_with_chords_and_notes(mock_feature_extractor, mock_audio_processor, tmp_path):
    mock_audio = MagicMock()
    mock_sr = 22050
    mock_audio_processor.load_audio.return_value = (mock_audio, mock_sr)
    mock_feature_extractor.extract_features.return_value = {
        "duration": 60.0,
        "tempo": 120.0,
        "beat_count": 2,
        "key": "C",
        "mode": "major",
        "spectral_centroid": 1500.0,
        "spectral_bandwidth": 2000.0,
        "harmonic_ratio": 0.6,
        "tuning_offset": 0.0,
        "onset_strength": 0.4,
    }
    mock_feature_extractor.summarize_chord_progression.return_value = [
        {"name": "C", "start_time": 0.0, "duration": 1.0}
    ]
    mock_feature_extractor.detect_notes.return_value = [
        {"pitch": "C4", "start_time": 0.0, "confidence": 0.9}
    ]

    test_file = tmp_path / "test.wav"
    test_file.touch()

    result = reverse_engineering_adapter.analyze_track(test_file, chords=True, notes=True)

    assert "chord_progression" in result
    assert result["chord_progression"][0]["name"] == "C"
    assert "notes" in result
    assert result["notes"][0]["pitch"] == "C4"


@patch("toolshop.reverse_engineering_adapter.analyze_effects")
@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
def test_analyze_track_with_effects(
    mock_feature_extractor, mock_audio_processor, mock_analyze_effects, tmp_path
):
    mock_audio = MagicMock()
    mock_sr = 22050
    mock_audio_processor.load_audio.return_value = (mock_audio, mock_sr)
    mock_feature_extractor.extract_features.return_value = {
        "duration": 60.0,
        "tempo": 120.0,
        "beat_count": 2,
        "key": "C",
        "mode": "major",
        "spectral_centroid": 1500.0,
        "spectral_bandwidth": 2000.0,
        "harmonic_ratio": 0.6,
        "tuning_offset": 0.0,
        "onset_strength": 0.4,
    }
    mock_analyze_effects.return_value = {"rt60_seconds": 1.2}

    test_file = tmp_path / "test.wav"
    test_file.touch()

    result = reverse_engineering_adapter.analyze_track(test_file, effects=True)

    assert "effects" in result
    assert result["effects"]["rt60_seconds"] == 1.2
    mock_analyze_effects.assert_called_once_with(mock_audio, mock_sr)


@patch("toolshop.reverse_engineering_adapter.InstrumentRecognizer")
@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
def test_analyze_track_with_instruments(
    mock_feature_extractor, mock_audio_processor, mock_recognizer_class, tmp_path
):
    mock_audio = MagicMock()
    mock_sr = 22050
    mock_audio_processor.load_audio.return_value = (mock_audio, mock_sr)
    mock_feature_extractor.extract_features.return_value = {
        "duration": 60.0,
        "tempo": 120.0,
        "beat_count": 2,
        "key": "C",
        "mode": "major",
        "spectral_centroid": 1500.0,
        "spectral_bandwidth": 2000.0,
        "harmonic_ratio": 0.6,
        "tuning_offset": 0.0,
        "onset_strength": 0.4,
    }
    mock_instance = MagicMock()
    mock_instance.recognize.return_value = [{"label": "drums", "score": 0.8}]
    mock_recognizer_class.return_value = mock_instance

    test_file = tmp_path / "test.wav"
    test_file.touch()

    result = reverse_engineering_adapter.analyze_track(test_file, instruments=True)

    assert "instruments" in result
    assert result["instruments"][0]["label"] == "drums"
    mock_instance.recognize.assert_called_once_with(mock_audio, mock_sr)


@patch("toolshop.reverse_engineering_adapter.separate_hpss")
@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
def test_analyze_track_with_hpss_separation(
    mock_feature_extractor, mock_audio_processor, mock_separate_hpss, tmp_path
):
    mock_audio = MagicMock()
    mock_sr = 22050
    mock_audio_processor.load_audio.return_value = (mock_audio, mock_sr)
    mock_feature_extractor.extract_features.return_value = {
        "duration": 60.0,
        "tempo": 120.0,
        "beat_count": 2,
        "key": "C",
        "mode": "major",
        "spectral_centroid": 1500.0,
        "spectral_bandwidth": 2000.0,
        "harmonic_ratio": 0.6,
        "tuning_offset": 0.0,
        "onset_strength": 0.4,
    }
    mock_separate_hpss.return_value = {"harmonic": MagicMock(), "percussive": MagicMock()}

    test_file = tmp_path / "test.wav"
    test_file.touch()

    result = reverse_engineering_adapter.analyze_track(test_file, separation="hpss")

    assert result["separation"]["method"] == "hpss"
    assert "harmonic" in result["separation"]["stems"]
    mock_separate_hpss.assert_called_once_with(mock_audio)


@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
def test_analyze_track_export_json(mock_feature_extractor, mock_audio_processor, tmp_path):
    mock_audio = MagicMock()
    mock_sr = 22050
    mock_audio_processor.load_audio.return_value = (mock_audio, mock_sr)
    mock_feature_extractor.extract_features.return_value = {
        "duration": 60.0,
        "tempo": 120.0,
        "beat_count": 2,
        "key": "C",
        "mode": "major",
        "spectral_centroid": 1500.0,
        "spectral_bandwidth": 2000.0,
        "harmonic_ratio": 0.6,
        "tuning_offset": 0.0,
        "onset_strength": 0.4,
    }

    test_file = tmp_path / "test.wav"
    test_file.touch()

    result = reverse_engineering_adapter.analyze_track(test_file, export_json=True)

    expected_file = tmp_path / "test_analysis.json"
    assert expected_file.exists()
    with expected_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["file"] == str(test_file)
    assert data["analysis_backend"] == "wav_reverse_engineer"
