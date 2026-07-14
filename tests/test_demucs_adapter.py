"""Tests for the Demucs backend adapter.

The demucs package is mocked via sys.modules to avoid heavy dependencies and
model downloads. The adapter module is imported once at import time to avoid
triggering numpy reload issues.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from toolshop import demucs_adapter


@pytest.fixture
def mock_demucs_api():
    """Provide a mocked demucs Python API in sys.modules."""
    demucs_module = MagicMock()
    separator_instance = MagicMock()

    def fake_separate_audio_file(path: str):
        return (None, {
            "drums": "drums_tensor",
            "bass": "bass_tensor",
            "other": "other_tensor",
            "vocals": "vocals_tensor",
        })

    separator_instance.separate_audio_file.side_effect = fake_separate_audio_file
    demucs_module.api.Separator = MagicMock(return_value=separator_instance)

    with patch.dict(
        "sys.modules", {"demucs": demucs_module, "demucs.api": demucs_module.api}
    ):
        yield demucs_adapter, separator_instance


def test_separate_api_creates_stems(mock_demucs_api, tmp_path):
    adapter, sep_instance = mock_demucs_api
    input_file = tmp_path / "song.wav"
    input_file.write_bytes(b"fake wav data")

    result = adapter.separate(
        input_file=input_file,
        model_id="htdemucs",
        output_dir=tmp_path / "out",
        output_format="flac",
        device="cpu",
    )

    assert result["preset"] == "htdemucs"
    assert result["backend"] == "demucs-api"
    assert set(result["stems"].keys()) == {"drums", "bass", "other", "vocals"}
    for stem_path in result["stems"].values():
        assert Path(stem_path).suffix == ".flac"

    sep_instance.save_audio.assert_called()


def test_separate_cli_fallback(mock_demucs_api, tmp_path):
    adapter, sep_instance = mock_demucs_api
    input_file = tmp_path / "song.wav"
    input_file.write_bytes(b"fake wav data")

    # Force the API path to fail.
    sep_instance.separate_audio_file.side_effect = RuntimeError("CUDA unavailable")

    # Mock subprocess CLI path by faking demucs CLI output tree.
    expected_dir = tmp_path / "out" / "htdemucs" / "song"
    expected_dir.mkdir(parents=True)
    (expected_dir / "drums.wav").touch()
    (expected_dir / "bass.wav").touch()
    (expected_dir / "other.wav").touch()
    (expected_dir / "vocals.wav").touch()

    with patch.object(adapter, "_cli_separate") as mock_cli:
        mock_cli.return_value = {
            "drums": str(expected_dir / "drums.wav"),
            "bass": str(expected_dir / "bass.wav"),
            "other": str(expected_dir / "other.wav"),
            "vocals": str(expected_dir / "vocals.wav"),
        }

        result = adapter.separate(
            input_file=input_file,
            model_id="htdemucs",
            output_dir=tmp_path / "out",
            output_format="wav",
            device="cpu",
        )

    assert result["backend"] == "demucs-cli"
    assert set(result["stems"].keys()) == {"drums", "bass", "other", "vocals"}
    mock_cli.assert_called_once()


def test_separate_wrong_backend_raises():
    with pytest.raises(ValueError, match="not a demucs backend"):
        demucs_adapter.separate(
            input_file=Path("x.wav"),
            model_id="uvr-mdx-net-voc-ft",
        )
