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


# ------------------------------------------------------------------ M3: jobs
#
# The adapter passed no tuning parameters at all, so demucs ran at jobs=0 on an
# 8-core machine. CONTROLLED measurement 2026-08-30 (warm-up discarded, baseline
# repeated to check drift): 30.2 s -> 24.6 s on a 30 s clip = 1.22x, with 2.0%
# baseline drift. An earlier uncontrolled sweep reported 2.97x; that was largely
# cold-cache warm-up, not compute.

from unittest.mock import MagicMock, patch

from toolshop import demucs_adapter as _da


def test_auto_jobs_scales_with_cores_and_is_capped():
    for cores, expected in [(1, 1), (2, 1), (4, 2), (8, 4), (16, 4), (64, 4)]:
        with patch.object(_da.os, "cpu_count", return_value=cores):
            assert _da.auto_jobs() == expected, f"{cores} cores"


def test_auto_jobs_survives_unknown_core_count():
    with patch.object(_da.os, "cpu_count", return_value=None):
        assert _da.auto_jobs() == 1


def test_api_separate_passes_jobs_to_demucs():
    """The whole point of M3: the parameter must actually reach the library."""
    fake_sep = MagicMock()
    fake_sep.separate_audio_file.return_value = (None, {})
    fake_module = MagicMock(Separator=MagicMock(return_value=fake_sep))

    with patch.dict("sys.modules", {"demucs.api": fake_module}):
        _da._api_separate(
            input_path=Path("in.wav"),
            output_dir=Path("out"),
            model=_da.stem_models.MODELS["htdemucs"],
            output_format="wav",
            device="cpu",
            jobs=3,
        )
    assert fake_module.Separator.call_args.kwargs["jobs"] == 3


def test_api_separate_defaults_to_auto_jobs():
    fake_sep = MagicMock()
    fake_sep.separate_audio_file.return_value = (None, {})
    fake_module = MagicMock(Separator=MagicMock(return_value=fake_sep))

    with patch.dict("sys.modules", {"demucs.api": fake_module}):
        with patch.object(_da, "auto_jobs", return_value=7):
            _da._api_separate(
                input_path=Path("in.wav"),
                output_dir=Path("out"),
                model=_da.stem_models.MODELS["htdemucs"],
                output_format="wav",
                device="cpu",
            )
    assert fake_module.Separator.call_args.kwargs["jobs"] == 7
