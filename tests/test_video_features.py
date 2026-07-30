"""Tests for toolshop/video_features.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from toolshop.video_features import (
    extract_features,
    _check_librosa,
    _HAS_LIBROSA,
    STYLE_PRESETS,
)


@pytest.fixture
def mock_librosa():
    with patch("toolshop.video_features.librosa") as mock_lib, patch(
        "toolshop.video_features.np"
    ) as mock_np:
        mock_lib.load.return_value = (MagicMock(), 22050)
        mock_lib.get_duration.return_value = 30.0
        mock_lib.beat.beat_track.return_value = (128.0, None)
        mock_lib.feature.chroma_cqt.return_value = MagicMock()
        mock_lib.onset.onset_detect.return_value = MagicMock()
        mock_lib.onset.onset_strength.return_value = MagicMock()
        mock_lib.feature.rms.return_value = MagicMock()
        mock_lib.feature.spectral_centroid.return_value = MagicMock()
        mock_lib.effects.trim.return_value = (MagicMock(), MagicMock())

        mock_np.atleast_1d.return_value = MagicMock()
        mock_np.atleast_1d.return_value.__getitem__ = lambda self, i: 128.0
        mock_np.mean.return_value = [0.8] * 12
        mock_np.argmax.return_value = 0
        mock_np.linspace.return_value = MagicMock()

        yield mock_lib, mock_np


def test_check_librosa_missing():
    with patch("toolshop.video_features._HAS_LIBROSA", False):
        with pytest.raises(RuntimeError, match="librosa is required"):
            _check_librosa()


def test_extract_features_file_not_found():
    with patch("toolshop.video_features._HAS_LIBROSA", True):
        with pytest.raises(FileNotFoundError):
            extract_features(Path("nonexistent_audio.wav"))


def test_extract_features_basic(mock_librosa, tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()

    with patch("toolshop.video_features._HAS_LIBROSA", True):
        result = extract_features(audio)

    assert "tempo" in result
    assert "beats" in result
    assert "onsets" in result
    assert "rms_env" in result
    assert "spectral_centroid" in result
    assert "chroma_mean" in result
    assert "duration" in result
    assert "key" in result
    assert "mode" in result
    assert "file" in result


def test_extract_features_to_json(mock_librosa, tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()
    out = tmp_path / "features.json"

    with patch("toolshop.video_features._HAS_LIBROSA", True):
        result = extract_features(audio, output_path=out)

    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == result


def test_extract_features_with_stems_dir(mock_librosa, tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()
    (stems_dir / "vocals.wav").touch()
    (stems_dir / "drums.wav").touch()

    with patch("toolshop.video_features._HAS_LIBROSA", True), patch(
        "toolshop.video_features._compute_stem_energies"
    ) as mock_stems:
        mock_stems.return_value = {"vocals": [0.1, 0.2], "drums": [0.3, 0.4]}
        result = extract_features(audio, stems_dir=stems_dir)

    assert "stem_energies" in result
    assert result["stem_energies"]["vocals"] == [0.1, 0.2]


def test_extract_features_no_librosa():
    with patch("toolshop.video_features._HAS_LIBROSA", False):
        with pytest.raises(RuntimeError, match="librosa is required"):
            extract_features(Path("test.wav"))


def test_extract_features_sections(mock_librosa, tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()

    with patch("toolshop.video_features._HAS_LIBROSA", True), patch(
        "toolshop.video_features._detect_sections"
    ) as mock_sections:
        mock_sections.return_value = [
            {"start": 0.0, "end": 15.0, "label": "intro"},
            {"start": 15.0, "end": 30.0, "label": "verse"},
        ]
        result = extract_features(audio)

    assert "sections" in result
    assert len(result["sections"]) == 2
    assert result["sections"][0]["label"] == "intro"
