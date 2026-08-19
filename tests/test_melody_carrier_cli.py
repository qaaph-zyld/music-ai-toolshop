"""Tests for the `toolshop melody-carrier` CLI module."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from toolshop.melody_carrier import melody_cli
from toolshop.melody_carrier.melody_cli import (
    add_parser,
    run,
    _cmd_extract,
    _cmd_render,
)
from toolshop.melody_carrier import extractor
from toolshop.melody_carrier import renderer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Build a top-level parser with melody-carrier registered."""
    parser = argparse.ArgumentParser(prog="toolshop")
    subparsers = parser.add_subparsers(dest="command")
    add_parser(subparsers)
    return parser


# ---------------------------------------------------------------------------
# Parser structure tests
# ---------------------------------------------------------------------------

class TestAddParser:
    def test_add_parser_creates_subcommand(self):
        parser = _build_parser()
        actions = [a for a in parser._actions if hasattr(a, "choices") and a.choices]
        assert "melody-carrier" in parser._subparsers._group_actions[0].choices

    def test_add_parser_has_extract(self):
        parser = _build_parser()
        mc_parser = parser._subparsers._group_actions[0].choices["melody-carrier"]
        mc_sub = mc_parser._subparsers._group_actions[0]
        assert "extract" in mc_sub.choices

    def test_add_parser_has_render(self):
        parser = _build_parser()
        mc_parser = parser._subparsers._group_actions[0].choices["melody-carrier"]
        mc_sub = mc_parser._subparsers._group_actions[0]
        assert "render" in mc_sub.choices


# ---------------------------------------------------------------------------
# Required argument tests
# ---------------------------------------------------------------------------

class TestRequiredArguments:
    def test_extract_requires_genre(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "melody-carrier", "extract",
                "input.wav",
                "--output", "out",
            ])

    def test_extract_requires_output(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "melody-carrier", "extract",
                "input.wav",
                "--genre", "drill",
            ])

    def test_render_fidelity_choices(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "melody-carrier", "render",
                "workdir",
                "--fidelity", "ultra",
            ])

    def test_extract_preset_choices(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([
                "melody-carrier", "extract",
                "input.wav",
                "--output", "out",
                "--genre", "drill",
                "--preset", "8stem",
            ])


# ---------------------------------------------------------------------------
# run() dispatch tests
# ---------------------------------------------------------------------------

class TestRunDispatch:
    @patch.object(extractor, "extract")
    def test_run_extract(self, mock_extract, tmp_path):
        mock_extract.return_value = {
            "stage1_dir": tmp_path / "stage1",
            "midi_files": {"melody": tmp_path / "melody.mid"},
        }
        args = argparse.Namespace(
            mc_command="extract",
            input=tmp_path / "input.wav",
            output=tmp_path / "output",
            genre="drill",
            preset="4stem",
        )
        result = run(args)
        assert result == 0
        mock_extract.assert_called_once()

    @patch.object(renderer, "render")
    def test_run_render(self, mock_render, tmp_path):
        mock_render.return_value = {
            "stage2_dir": tmp_path / "stage2",
            "carriers": {"carrier_sine": tmp_path / "carrier_sine.wav"},
            "prompts": {"minimal": tmp_path / "suno_prompt_minimal.txt"},
            "readme": tmp_path / "README.txt",
            "fidelity_pct": 55,
        }
        args = argparse.Namespace(
            mc_command="render",
            dir=tmp_path / "workdir",
            instruments="",
            fidelity="medium",
        )
        result = run(args)
        assert result == 0
        mock_render.assert_called_once()

    def test_run_unknown_subcommand(self, capsys):
        args = argparse.Namespace(mc_command="bogus")
        result = run(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown" in captured.err


# ---------------------------------------------------------------------------
# _cmd_extract tests
# ---------------------------------------------------------------------------

class TestCmdExtract:
    @patch.object(extractor, "extract")
    def test_cmd_extract_success(self, mock_extract, tmp_path, capsys):
        mock_extract.return_value = {
            "stage1_dir": tmp_path / "stage1",
            "midi_files": {
                "melody": tmp_path / "melody.mid",
                "chords": tmp_path / "chords.mid",
                "bass": tmp_path / "bass.mid",
                "drums": tmp_path / "drums.mid",
                "full_sketch": tmp_path / "full_sketch.mid",
            },
            "analysis": {"bpm": 140.0},
            "stems_dir": tmp_path / "stems",
        }
        args = argparse.Namespace(
            mc_command="extract",
            input=tmp_path / "input.wav",
            output=tmp_path / "output",
            genre="drill",
            preset="4stem",
        )
        result = _cmd_extract(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Stage 1 extraction complete" in captured.out
        assert "MIDI files created" in captured.out

    @patch.object(extractor, "extract")
    def test_cmd_extract_file_not_found(self, mock_extract, tmp_path, capsys):
        mock_extract.side_effect = FileNotFoundError("Input WAV not found")
        args = argparse.Namespace(
            mc_command="extract",
            input=tmp_path / "missing.wav",
            output=tmp_path / "output",
            genre="drill",
            preset="4stem",
        )
        result = _cmd_extract(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Input WAV not found" in captured.err

    @patch.object(extractor, "extract")
    def test_cmd_extract_generic_exception(self, mock_extract, tmp_path, capsys):
        mock_extract.side_effect = RuntimeError("Something went wrong")
        args = argparse.Namespace(
            mc_command="extract",
            input=tmp_path / "input.wav",
            output=tmp_path / "output",
            genre="drill",
            preset="4stem",
        )
        result = _cmd_extract(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.err


# ---------------------------------------------------------------------------
# _cmd_render tests
# ---------------------------------------------------------------------------

class TestCmdRender:
    @patch.object(renderer, "render")
    def test_cmd_render_success(self, mock_render, tmp_path, capsys):
        mock_render.return_value = {
            "stage2_dir": tmp_path / "stage2",
            "carriers": {
                "carrier_sine": tmp_path / "carrier_sine.wav",
                "carrier_reference": tmp_path / "carrier_reference.wav",
            },
            "prompts": {
                "minimal": tmp_path / "suno_prompt_minimal.txt",
                "descriptive": tmp_path / "suno_prompt_descriptive.txt",
                "detailed": tmp_path / "suno_prompt_detailed.txt",
            },
            "readme": tmp_path / "README.txt",
            "fidelity_pct": 55,
        }
        args = argparse.Namespace(
            mc_command="render",
            dir=tmp_path / "workdir",
            instruments="",
            fidelity="medium",
        )
        result = _cmd_render(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Stage 2 rendering complete" in captured.out
        assert "Carriers created: 2" in captured.out
        assert "Fidelity: 55%" in captured.out

    @patch.object(renderer, "render")
    def test_cmd_render_missing_analysis(self, mock_render, tmp_path, capsys):
        mock_render.side_effect = FileNotFoundError("analysis.json not found")
        args = argparse.Namespace(
            mc_command="render",
            dir=tmp_path / "workdir",
            instruments="",
            fidelity="medium",
        )
        result = _cmd_render(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "analysis.json not found" in captured.err

    @patch.object(renderer, "render")
    def test_cmd_render_generic_exception(self, mock_render, tmp_path, capsys):
        mock_render.side_effect = RuntimeError("Render failed")
        args = argparse.Namespace(
            mc_command="render",
            dir=tmp_path / "workdir",
            instruments="",
            fidelity="medium",
        )
        result = _cmd_render(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Render failed" in captured.err


# ---------------------------------------------------------------------------
# CLI help tests (subprocess — uses .venv Python)
# ---------------------------------------------------------------------------

_PYTHON = sys.executable


class TestCLIHelp:
    def test_cli_melody_carrier_help(self):
        result = subprocess.run(
            [_PYTHON, "-m", "toolshop.cli", "melody-carrier", "--help"],
            capture_output=True,
            text=True,
            cwd=r"d:\Projects\Music-AI-Toolshop",
        )
        assert result.returncode == 0
        assert "melody-carrier" in result.stdout

    def test_cli_melody_carrier_extract_help(self):
        result = subprocess.run(
            [_PYTHON, "-m", "toolshop.cli", "melody-carrier", "extract", "--help"],
            capture_output=True,
            text=True,
            cwd=r"d:\Projects\Music-AI-Toolshop",
        )
        assert result.returncode == 0
        assert "extract" in result.stdout

    def test_cli_melody_carrier_render_help(self):
        result = subprocess.run(
            [_PYTHON, "-m", "toolshop.cli", "melody-carrier", "render", "--help"],
            capture_output=True,
            text=True,
            cwd=r"d:\Projects\Music-AI-Toolshop",
        )
        assert result.returncode == 0
        assert "render" in result.stdout


# ---------------------------------------------------------------------------
# --require-advanced guard (assessment F3, governance rule 9)
#
# The extractor already records which backend each stage used. That is necessary
# but not sufficient: the user must be able to *demand* the primary path and get a
# hard failure rather than a quiet downgrade to the librosa heuristics.
# ---------------------------------------------------------------------------

class TestRequireAdvanced:
    def test_flag_defaults_to_false(self):
        parser = _build_parser()
        args = parser.parse_args(
            ["melody-carrier", "extract", "in.wav", "--output", "out", "--genre", "drill"]
        )
        assert args.require_advanced is False

    def test_flag_parses(self):
        parser = _build_parser()
        args = parser.parse_args(
            [
                "melody-carrier", "extract", "in.wav",
                "--output", "out", "--genre", "drill", "--require-advanced",
            ]
        )
        assert args.require_advanced is True

    def test_missing_backends_reported_by_stage(self):
        missing = melody_cli.missing_advanced_backends()
        # Every reported stage must be one the extractor actually has a backend for.
        assert set(missing).issubset(set(melody_cli.ADVANCED_BACKENDS))
        for stage, pip_name in missing.items():
            assert pip_name == melody_cli.ADVANCED_BACKENDS[stage][1]

    def test_preflight_fails_before_extraction(self, tmp_path, capsys):
        """A missing backend must abort *before* stem separation burns minutes."""
        args = argparse.Namespace(
            input=tmp_path / "in.wav",
            output=tmp_path / "out",
            genre="drill",
            preset="4stem",
            require_advanced=True,
        )
        with patch.object(
            melody_cli, "missing_advanced_backends", return_value={"melody": "basic-pitch"}
        ):
            with patch.object(extractor, "extract") as fake_extract:
                assert _cmd_extract(args) == 1
                fake_extract.assert_not_called()
        err = capsys.readouterr().err
        assert "basic-pitch" in err
        assert ".[melody]" in err

    def test_runtime_fallback_is_rejected(self, tmp_path, capsys):
        """A backend can import and still fail at runtime — trust the record."""
        args = argparse.Namespace(
            input=tmp_path / "in.wav",
            output=tmp_path / "out",
            genre="drill",
            preset="4stem",
            require_advanced=True,
        )
        result = {
            "stage1_dir": tmp_path / "out" / "stage1",
            "midi_files": {},
            "analysis": {
                "extraction_tools": {
                    "melody": "pyin_fallback",
                    "chords": "autochord",
                    "bass": "skipped",
                    "drums": "adtof",
                }
            },
        }
        with patch.object(melody_cli, "missing_advanced_backends", return_value={}):
            with patch.object(extractor, "extract", return_value=result):
                assert _cmd_extract(args) == 1
        err = capsys.readouterr().err
        assert "pyin_fallback" in err

    def test_fallback_allowed_without_the_flag(self, tmp_path, capsys):
        """Default behaviour is unchanged: fall back, but say so."""
        args = argparse.Namespace(
            input=tmp_path / "in.wav",
            output=tmp_path / "out",
            genre="drill",
            preset="4stem",
            require_advanced=False,
        )
        result = {
            "stage1_dir": tmp_path / "out" / "stage1",
            "midi_files": {"melody": tmp_path / "melody.mid"},
            "analysis": {"extraction_tools": {"melody": "pyin_fallback"}},
        }
        with patch.object(extractor, "extract", return_value=result):
            assert _cmd_extract(args) == 0
        out = capsys.readouterr().out
        assert "pyin_fallback" in out
        assert "(fallback)" in out
