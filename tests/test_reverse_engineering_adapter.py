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


# --- _basic_analysis error handlers (JOURNAL.md J-006) -----------------------
#
# Every test above mocks `_basic_analysis` out, so its body had never executed.
# It guards its three most valuable field-groups - beat grid, structure and
# premaster, the whole of H2-M1..M4 - behind `except` handlers that called an
# undefined `logger`. A stage failure therefore raised NameError from inside the
# handler meant to absorb it. These tests run the real function.

import logging
import math
import wave

import pytest


def _tone_wav(path, seconds=1.0, sr=22050, freq=220.0):
    """A real, readable wav. `_basic_analysis` loads from disk, so it needs one."""
    frames = bytearray()
    for i in range(int(sr * seconds)):
        v = int(20000 * math.sin(2 * math.pi * freq * i / sr))
        frames += int(v).to_bytes(2, "little", signed=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))
    return path


@pytest.mark.parametrize(
    "target",
    [
        "toolshop.reverse_engineering_adapter.beatgrid.analyze_beats",
        "toolshop.reverse_engineering_adapter.structure.segment_track",
        "toolshop.reverse_engineering_adapter.premaster.analyze_premaster",
    ],
)
def test_basic_analysis_degrades_instead_of_raising(target, tmp_path):
    """A failing stage must be absorbed, not converted into NameError."""
    from toolshop import reverse_engineering_adapter as rea

    wav = _tone_wav(tmp_path / "tone.wav")
    with patch(target, side_effect=RuntimeError("stage exploded")):
        result = rea._basic_analysis(wav)

    assert result["analysis_backend"] == "basic_librosa"
    assert result["file"] == str(wav)


def test_basic_analysis_logger_is_defined():
    """The regression itself: the handlers referenced a name that did not exist."""
    from toolshop import reverse_engineering_adapter as rea

    assert isinstance(getattr(rea, "logger", None), logging.Logger)


def test_basic_analysis_emits_the_four_m6_fields(tmp_path):
    """M6 depends on these coming from _basic_analysis; nothing asserted it did."""
    from toolshop import reverse_engineering_adapter as rea

    result = rea._basic_analysis(_tone_wav(tmp_path / "tone.wav"))
    for field in ("beat_grid", "structure", "premaster", "key"):
        assert field in result, f"{field} missing from _basic_analysis output"


# --- the four M6 field-groups reach BOTH backends (CHANGELOG #054, J-024) ----
#
# beat_grid, structure, premaster and the K-S key block were emitted only by
# _basic_analysis, while the corpus batch hard-coded backend="advanced". All 222
# corpus dossiers therefore carry none of them, and M6's "just re-run the corpus"
# would have added nothing while its count check reported 222 in / 222 out.


@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
def test_advanced_analysis_emits_the_four_m6_fields(mock_ap, mock_fe, tmp_path):
    from toolshop import reverse_engineering_adapter as rea

    mock_ap.load_audio.return_value = (MagicMock(), 22050)
    mock_fe.extract_features.return_value = {
        "duration": 10.0, "tempo": 120.0, "beat_count": 20,
        "key": "C", "mode": "major", "spectral_centroid": 1.0,
        "spectral_bandwidth": 1.0, "harmonic_ratio": 0.5,
    }
    fake_m6 = {
        "beat_grid": {"tempo": 87.3}, "structure": [{"label": "verse"}],
        "premaster": {"verdict": "FLAG"}, "key": "G", "mode": "minor",
        "key_confidence": 0.71, "key_alternate": "Bb major", "key_margin": 0.08,
        "bpm": 87.3, "beat_count": 999,
    }
    with patch.object(rea, "_m6_fields", return_value=fake_m6):
        result = rea._advanced_analysis(tmp_path / "t.wav")

    for field in ("beat_grid", "structure", "premaster", "key_confidence"):
        assert field in result, f"{field} missing from the advanced backend"


@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
def test_ks_key_overrides_the_threshold_mode(mock_ap, mock_fe, tmp_path):
    """feature_extractor.py:190 is `chroma_vals[key_idx] > 0.5` -> 215 major / 7
    minor across the corpus, contradicted by the same backend's own chords on
    170 of 212 tracks. K-S must win."""
    from toolshop import reverse_engineering_adapter as rea

    mock_ap.load_audio.return_value = (MagicMock(), 22050)
    mock_fe.extract_features.return_value = {
        "duration": 10.0, "tempo": 120.0, "beat_count": 20,
        "key": "C", "mode": "major", "spectral_centroid": 1.0,
        "spectral_bandwidth": 1.0, "harmonic_ratio": 0.5,
    }
    with patch.object(rea, "_m6_fields", return_value={"key": "G", "mode": "minor"}):
        result = rea._advanced_analysis(tmp_path / "t.wav")

    assert result["mode"] == "minor", "the threshold mode survived K-S"
    assert result["key"] == "G"


@patch("toolshop.reverse_engineering_adapter.FeatureExtractor")
@patch("toolshop.reverse_engineering_adapter.AudioProcessor")
def test_advanced_keeps_its_own_tempo(mock_ap, mock_fe, tmp_path):
    """The grid must not silently replace the tempo every other field was
    computed against."""
    from toolshop import reverse_engineering_adapter as rea

    mock_ap.load_audio.return_value = (MagicMock(), 22050)
    mock_fe.extract_features.return_value = {
        "duration": 10.0, "tempo": 120.0, "beat_count": 20,
        "key": "C", "mode": "major", "spectral_centroid": 1.0,
        "spectral_bandwidth": 1.0, "harmonic_ratio": 0.5,
    }
    with patch.object(rea, "_m6_fields", return_value={"bpm": 87.3, "beat_count": 999}):
        result = rea._advanced_analysis(tmp_path / "t.wav")

    assert result["bpm"] == 120.0
    assert result["beat_count"] == 20


def test_m6_fields_degrade_independently(tmp_path):
    """One group failing must not take the others with it."""
    from toolshop import reverse_engineering_adapter as rea
    import librosa

    wav = _tone_wav(tmp_path / "tone.wav")
    y, sr = librosa.load(str(wav), sr=22050, mono=True)
    with patch.object(rea.structure, "segment_track", side_effect=RuntimeError("boom")):
        out = rea._m6_fields(y, sr, wav)

    assert out["structure"] is None
    assert out["premaster"] is not None or "premaster" in out
    assert "key" in out, "a structure failure took the key block with it"
