"""Tests for toolshop/video_cli.py and cli.py video subcommand."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from toolshop.video_cli import add_parser, run


def _make_args(**kwargs):
    """Create a mock args namespace with video defaults."""
    defaults = {
        "video_command": "features",
        "audio": Path("test.wav"),
        "output": None,
        "stems_dir": None,
        "lyrics": None,
        "lyrics_format": "lrc",
        "features": None,
        "style": "default",
        "background": "showwaves",
        "image": None,
        "stock_query": None,
        "stock_source": "both",
        "stock_limit": 5,
        "stock_out": None,
        "resolution": "1280x720",
        "fps": 30,
        "out": None,
        "json": False,
    }
    defaults.update(kwargs)
    return MagicMock(**defaults)


def test_add_parser_video():
    """Test that add_parser registers the video subcommand."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    add_parser(subparsers)
    args = parser.parse_args(["video", "features", "--audio", "test.wav"])
    assert args.command == "video"
    assert args.video_command == "features"


def test_run_features(tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()
    out = tmp_path / "features.json"

    args = _make_args(video_command="features", audio=audio, output=out)

    with patch("toolshop.video_cli.extract_features") as mock_extract:
        mock_extract.return_value = {"tempo": 128.0, "beats": []}
        code = run(args)

    assert code == 0
    mock_extract.assert_called_once()


def test_run_features_json_output(tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()
    out = tmp_path / "features.json"

    args = _make_args(
        video_command="features", audio=audio, output=out, json=True
    )

    with patch("toolshop.video_cli.extract_features") as mock_extract:
        mock_extract.return_value = {"tempo": 128.0, "beats": [0.5, 1.0]}
        code = run(args)

    assert code == 0


def test_run_generate_basic(tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()
    output = tmp_path / "mv.mp4"
    features = tmp_path / "features.json"
    features.write_text(json.dumps({"tempo": 128.0, "beats": [], "duration": 5.0}), encoding="utf-8")

    args = _make_args(
        video_command="generate",
        audio=audio,
        out=output,
        features=features,
        background="showwaves",
    )

    with patch("toolshop.video_cli.compose_pipeline") as mock_compose:
        mock_compose.return_value = output
        code = run(args)

    assert code == 0
    mock_compose.assert_called_once()


def test_run_generate_with_lyrics(tmp_path):
    audio = tmp_path / "test.wav"
    audio.touch()
    lyrics = tmp_path / "test.lrc"
    lyrics.write_text("[00:01.00]Hello\n[00:03.00]World\n", encoding="utf-8")
    output = tmp_path / "mv.mp4"
    features = tmp_path / "features.json"
    features.write_text(json.dumps({"tempo": 128.0, "beats": [], "duration": 5.0}), encoding="utf-8")

    args = _make_args(
        video_command="generate",
        audio=audio,
        out=output,
        features=features,
        background="showwaves",
        lyrics=lyrics,
        style="neon",
    )

    with patch("toolshop.video_cli.compose_pipeline") as mock_compose, patch(
        "toolshop.video_cli.lrc_to_ass"
    ) as mock_lrc:
        mock_compose.return_value = output
        mock_lrc.return_value = tmp_path / "lyrics.ass"
        code = run(args)

    assert code == 0
    mock_lrc.assert_called_once()


def test_run_generate_no_features(tmp_path):
    """generate should auto-extract features if --features not provided."""
    audio = tmp_path / "test.wav"
    audio.touch()
    output = tmp_path / "mv.mp4"

    args = _make_args(
        video_command="generate",
        audio=audio,
        out=output,
        features=None,
        background="showwaves",
    )

    with patch("toolshop.video_cli.extract_features") as mock_extract, patch(
        "toolshop.video_cli.compose_pipeline"
    ) as mock_compose:
        mock_extract.return_value = {"tempo": 128.0, "beats": [], "duration": 5.0}
        mock_compose.return_value = output
        code = run(args)

    assert code == 0
    mock_extract.assert_called_once()


def test_run_lyrics(tmp_path):
    lrc = tmp_path / "test.lrc"
    lrc.write_text("[00:01.00]Hello\n", encoding="utf-8")
    out = tmp_path / "lyrics.ass"

    args = _make_args(
        video_command="lyrics",
        lyrics=lrc,
        output=out,
        style="minimal",
    )

    with patch("toolshop.video_cli.lrc_to_ass") as mock_lrc:
        mock_lrc.return_value = out
        code = run(args)

    assert code == 0
    mock_lrc.assert_called_once()


def test_run_lyrics_missing_file(tmp_path):
    args = _make_args(
        video_command="lyrics",
        lyrics=Path("nonexistent.lrc"),
        output=tmp_path / "out.ass",
    )

    code = run(args)
    assert code == 1


def test_run_unknown_command():
    args = _make_args(video_command="nonexistent")
    code = run(args)
    assert code == 1
