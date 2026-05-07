"""Tests for the ReaScript -> toolshop bridge helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# The bridge module lives outside the standard ``toolshop`` package so the
# tests add its directory to ``sys.path``.
_BRIDGE_DIR = Path(__file__).resolve().parent.parent / "reascripts"
if str(_BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_DIR))

from _toolshop_bridge import (  # noqa: E402  (sys.path tweak above)
    BpmKeyResult,
    ToolshopError,
    analyze_bpm_key,
    resolve_toolshop_command,
)


def _ok_payload(file: str = "song.wav") -> dict:
    return {
        "file": file,
        "bpm": 128.0,
        "key": "F",
        "mode": "minor",
        "duration_seconds": 234.56,
        "sample_rate": 44100,
    }


class TestResolveToolshopCommand:
    def test_uses_python_module_when_python_env_set(self):
        cmd = resolve_toolshop_command(env={"TOOLSHOP_PYTHON": "/opt/venv/bin/python"})
        assert cmd == ["/opt/venv/bin/python", "-m", "toolshop.cli"]

    def test_uses_resolved_binary_when_on_path(self, monkeypatch):
        monkeypatch.setattr(
            "_toolshop_bridge.shutil.which",
            lambda name: f"/usr/bin/{name}" if name == "toolshop" else None,
        )
        cmd = resolve_toolshop_command(env={})
        assert cmd == ["/usr/bin/toolshop"]

    def test_honors_toolshop_bin_override(self, monkeypatch):
        monkeypatch.setattr(
            "_toolshop_bridge.shutil.which",
            lambda name: f"/custom/{name}" if name == "ts" else None,
        )
        cmd = resolve_toolshop_command(env={"TOOLSHOP_BIN": "ts"})
        assert cmd == ["/custom/ts"]

    def test_raises_when_binary_missing(self, monkeypatch):
        monkeypatch.setattr("_toolshop_bridge.shutil.which", lambda name: None)
        with pytest.raises(ToolshopError, match="Could not find the 'toolshop' CLI"):
            resolve_toolshop_command(env={})


class TestBpmKeyResult:
    def test_from_dict_round_trips_known_payload(self):
        r = BpmKeyResult.from_dict(_ok_payload())
        assert r.bpm == 128.0
        assert r.key == "F"
        assert r.mode == "minor"

    def test_from_dict_raises_on_missing_field(self):
        bad = _ok_payload()
        del bad["bpm"]
        with pytest.raises(ToolshopError, match="Unexpected payload"):
            BpmKeyResult.from_dict(bad)

    def test_summary_includes_bpm_and_key(self):
        r = BpmKeyResult.from_dict(_ok_payload(file="/tmp/foo/bar.wav"))
        s = r.summary()
        assert "bar.wav" in s
        assert "128.00 BPM" in s
        assert "F minor" in s


class TestAnalyzeBpmKey:
    def test_happy_path_parses_json_output(self, tmp_path, monkeypatch):
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"")  # Just needs to exist; we mock the runner.
        monkeypatch.setattr(
            "_toolshop_bridge.shutil.which",
            lambda name: "/usr/bin/toolshop",
        )

        runner = MagicMock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout=json.dumps(_ok_payload(file=str(audio))),
                stderr="",
            )
        )

        result = analyze_bpm_key(audio, env={}, runner=runner)

        assert result.bpm == 128.0
        assert result.key == "F"
        # Confirm the CLI was invoked with the expected args.
        runner.assert_called_once()
        cmd = runner.call_args.args[0]
        assert cmd[:2] == ["/usr/bin/toolshop", "analyze"]
        assert "bpm-key" in cmd
        assert "--json" in cmd
        assert str(audio) in cmd

    def test_missing_audio_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            analyze_bpm_key(tmp_path / "does-not-exist.wav")

    def test_non_zero_exit_raises_toolshop_error(self, tmp_path, monkeypatch):
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"")
        monkeypatch.setattr(
            "_toolshop_bridge.shutil.which",
            lambda name: "/usr/bin/toolshop",
        )
        runner = MagicMock(
            return_value=SimpleNamespace(returncode=2, stdout="", stderr="boom")
        )
        with pytest.raises(ToolshopError, match="exited 2"):
            analyze_bpm_key(audio, env={}, runner=runner)

    def test_invalid_json_raises_toolshop_error(self, tmp_path, monkeypatch):
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"")
        monkeypatch.setattr(
            "_toolshop_bridge.shutil.which",
            lambda name: "/usr/bin/toolshop",
        )
        runner = MagicMock(
            return_value=SimpleNamespace(
                returncode=0, stdout="not json at all", stderr=""
            )
        )
        with pytest.raises(ToolshopError, match="Could not parse JSON"):
            analyze_bpm_key(audio, env={}, runner=runner)

    def test_subprocess_timeout_raises_toolshop_error(self, tmp_path, monkeypatch):
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"")
        monkeypatch.setattr(
            "_toolshop_bridge.shutil.which",
            lambda name: "/usr/bin/toolshop",
        )

        def boom(*_a, **_kw):
            raise subprocess.TimeoutExpired(cmd=["toolshop"], timeout=1.0)

        with pytest.raises(ToolshopError, match="timed out"):
            analyze_bpm_key(audio, env={}, runner=boom, timeout=1.0)

    def test_missing_binary_raises_toolshop_error(self, tmp_path, monkeypatch):
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"")
        monkeypatch.setattr("_toolshop_bridge.shutil.which", lambda name: None)
        with pytest.raises(ToolshopError, match="Could not find"):
            analyze_bpm_key(audio, env={})
