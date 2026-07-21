"""Tests for toolshop/remix_cli.py."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from toolshop import remix_cli
from toolshop.cli import build_parser


def _sine_wave(duration: float, sr: int = 22050) -> np.ndarray:
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    return np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)


def _write_wav(path: Path, audio: np.ndarray, sr: int = 22050) -> None:
    sf.write(str(path), audio, sr)


@pytest.fixture
def mock_create_remix():
    def side_effect(*args, **kwargs):
        from toolshop import remix_adapter

        return remix_adapter.RemixResult(
            output_file=kwargs.get("output_path", Path("out.wav")),
            source=kwargs.get("input_path", Path("in.wav")),
            source_hash="deadbeef",
            bpm=kwargs.get("source_bpm") or 120.0,
            key=kwargs.get("source_key") or "C",
            mode="major",
            target_bpm=kwargs.get("target_bpm"),
            target_key=kwargs.get("target_key"),
            fx_chain=kwargs.get("fx_chain"),
            duration_seconds=2.0,
            output_format=kwargs.get("output_format", "wav"),
        )

    with patch.object(remix_cli.remix_adapter, "create_remix") as mock:
        mock.side_effect = side_effect
        yield mock


def test_remix_parser_basic():
    parser = build_parser()
    args = parser.parse_args(
        ["remix", "song.wav", "--target-bpm", "95", "--target-key", "Gm", "--mode", "sample"]
    )
    assert args.command == "remix"
    assert args.path == Path("song.wav")
    assert args.target_bpm == 95.0
    assert args.target_key == "Gm"
    assert args.mode == "sample"


def test_remix_parser_fx():
    parser = build_parser()
    args = parser.parse_args(
        ["remix", "song.wav", "--fx", "reverb", "delay", "--mode", "remix"]
    )
    assert args.fx == ["reverb", "delay"]


def test_remix_run_single_file(mock_create_remix, tmp_path):
    audio = _sine_wave(0.5)
    wav = tmp_path / "src.wav"
    _write_wav(wav, audio)

    parser = build_parser()
    args = parser.parse_args(
        ["remix", str(wav), "--target-bpm", "90", "--output", str(tmp_path / "remix.wav")]
    )
    assert remix_cli.run(args) == 0
    mock_create_remix.assert_called_once()


def test_remix_run_batch_no_files(tmp_path):
    parser = build_parser()
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    args = parser.parse_args(
        ["remix", str(empty_dir), "--mode", "sample", "--output-dir", str(tmp_path / "out")]
    )
    assert remix_cli.run(args) == 1


def test_resolve_output_path_defaults(tmp_path):
    class Args:
        mode = "remix"
        output = None
        output_dir = None
        format = None

    result = remix_cli._resolve_output_path(tmp_path / "My Song.wav", Args())
    assert result.suffix == ".wav"
    assert "my_song_unknown_remix" in result.name.lower()


def test_resolve_output_path_sample_dir(tmp_path):
    class Args:
        mode = "sample"
        output = None
        output_dir = str(tmp_path / "pack")
        format = None

    result = remix_cli._resolve_output_path(tmp_path / "My Song.wav", Args())
    assert result == tmp_path / "pack"
