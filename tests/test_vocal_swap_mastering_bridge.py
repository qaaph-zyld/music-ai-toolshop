"""Mastering-bridge tests. The chain itself is mocked; the boundary is not.

Path translation and the "exited 0 but produced nothing" case are the two ways
this bridge can fail silently, so both are tested directly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from toolshop.vocal_swap import mastering_bridge as bridge


class TestToWslPath:
    @pytest.mark.parametrize(
        "windows,expected",
        [
            (r"D:\Projects\Music-AI-Toolshop", "/mnt/d/Projects/Music-AI-Toolshop"),
            (r"C:\Users\x\a b.wav", "/mnt/c/Users/x/a b.wav"),
            (r"E:\x", "/mnt/e/x"),
        ],
    )
    def test_drive_letters_are_translated(self, windows, expected):
        assert bridge.to_wsl_path(Path(windows)) == expected

    def test_posix_paths_pass_through(self):
        assert bridge.to_wsl_path(Path("/mnt/d/already")) == "/mnt/d/already"

    def test_translation_is_idempotent(self):
        once = bridge.to_wsl_path(Path(r"D:\Projects\x.wav"))
        assert bridge.to_wsl_path(Path(once)) == once


class TestProfiles:
    def test_known_profile_returns_targets(self):
        targets = bridge.resolve_profile("serbian_drill")
        assert targets["lufs"] == -8.5
        assert targets["tp_dbtp"] == -1.0

    def test_unknown_profile_lists_the_valid_ones(self):
        with pytest.raises(ValueError) as exc:
            bridge.resolve_profile("nonesuch")
        assert "german_drill" in str(exc.value)

    def test_default_profile_is_valid(self):
        assert bridge.DEFAULT_PROFILE in bridge.PROFILE_TARGETS


def _write_tone(path: Path, lufs_target: float, seconds: float = 5.0, sr: int = 44100):
    """Write a tone roughly at a target loudness, for verdict tests."""
    import pyloudnorm as pyln

    t = np.arange(int(seconds * sr)) / sr
    wave = 0.2 * np.sin(2 * np.pi * 220 * t)
    audio = np.stack([wave, wave], axis=1)
    meter = pyln.Meter(sr)
    current = meter.integrated_loudness(audio)
    audio = audio * (10 ** ((lufs_target - current) / 20.0))
    sf.write(str(path), audio, sr)
    return path


class TestVerifyMaster:
    def _result(self, path: Path, target_lufs: float, target_tp: float = -1.0):
        return bridge.MasterResult(
            profile="serbian_drill", project_dir=str(path.parent), name="x",
            master_32f=None, master_16=str(path), master_mp3=None,
            target_lufs=target_lufs, target_tp_dbtp=target_tp,
        )

    def test_on_target_passes(self, tmp_path):
        path = _write_tone(tmp_path / "m.wav", -8.5)
        out = bridge.verify_master(self._result(path, -8.5, target_tp=0.0))
        assert out.verdict == "pass"
        assert out.measured_lufs == pytest.approx(-8.5, abs=0.3)

    def test_moderately_off_target_flags(self, tmp_path):
        path = _write_tone(tmp_path / "m.wav", -10.0)
        out = bridge.verify_master(self._result(path, -8.5, target_tp=0.0))
        assert out.verdict == "flag"

    def test_far_off_target_fails(self, tmp_path):
        path = _write_tone(tmp_path / "m.wav", -14.0)
        out = bridge.verify_master(self._result(path, -8.5, target_tp=0.0))
        assert out.verdict == "fail"
        assert out.lufs_delta < -2.0

    def test_true_peak_over_ceiling_fails_even_when_loudness_is_right(self, tmp_path):
        """Loudness on target is not enough; the ceiling is a hard limit."""
        path = _write_tone(tmp_path / "m.wav", -8.5)
        out = bridge.verify_master(self._result(path, -8.5, target_tp=-20.0))
        assert out.verdict == "fail"

    def test_missing_deliverable_is_not_verified(self, tmp_path):
        out = bridge.verify_master(self._result(tmp_path / "absent.wav", -8.5))
        assert out.verdict == "not_verified"


class TestMasterInvocation:
    def _ok_env(self, monkeypatch):
        monkeypatch.setattr(bridge, "check_environment", lambda *a, **k: {"ok": True, "errors": []})

    def test_missing_source_raises_before_anything_runs(self, tmp_path, monkeypatch):
        called = []
        monkeypatch.setattr(bridge, "run_in_wsl", lambda *a, **k: called.append(a))
        with pytest.raises(FileNotFoundError):
            bridge.master(tmp_path / "nope.wav", "x", tmp_path, profile="club")
        assert not called, "no subprocess may start for a missing source"

    def test_unusable_environment_raises_masteringunavailable(self, tmp_path, monkeypatch):
        source = _write_tone(tmp_path / "s.wav", -12.0)
        monkeypatch.setattr(
            bridge, "check_environment",
            lambda *a, **k: {"ok": False, "errors": ["ffmpeg is not installed inside WSL"]},
        )
        with pytest.raises(bridge.MasteringUnavailable) as exc:
            bridge.master(source, "x", tmp_path, profile="club")
        assert "ffmpeg" in str(exc.value)

    def test_nonzero_exit_raises_with_the_log_tail(self, tmp_path, monkeypatch):
        source = _write_tone(tmp_path / "s.wav", -12.0)
        self._ok_env(monkeypatch)
        monkeypatch.setattr(
            bridge, "run_in_wsl",
            lambda *a, **k: subprocess.CompletedProcess(
                a, 1, stdout="[A] Headroom\n", stderr="ffmpeg: Invalid data\n"
            ),
        )
        with pytest.raises(bridge.MasteringFailed) as exc:
            bridge.master(source, "x", tmp_path, profile="club")
        assert "Invalid data" in str(exc.value)

    def test_zero_exit_with_no_deliverable_is_a_failure(self, tmp_path, monkeypatch):
        """The dangerous case: the chain 'succeeds' and produces nothing."""
        source = _write_tone(tmp_path / "s.wav", -12.0)
        self._ok_env(monkeypatch)
        monkeypatch.setattr(
            bridge, "run_in_wsl",
            lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="done\n", stderr=""),
        )
        with pytest.raises(bridge.MasteringFailed) as exc:
            bridge.master(source, "x", tmp_path / "proj", profile="club")
        assert "no deliverable" in str(exc.value)

    def test_successful_run_reports_the_deliverables(self, tmp_path, monkeypatch):
        source = _write_tone(tmp_path / "s.wav", -12.0)
        project = tmp_path / "proj"
        self._ok_env(monkeypatch)

        def fake_run(command, timeout=0):
            out = project / "master"
            out.mkdir(parents=True, exist_ok=True)
            _write_tone(out / "song_MASTER_16.wav", -8.5)
            _write_tone(out / "song_MASTER_32f.wav", -8.5)
            return subprocess.CompletedProcess(command, 0, stdout="[F] Deliverables\n", stderr="")

        monkeypatch.setattr(bridge, "run_in_wsl", fake_run)
        result = bridge.master(source, "song", project, profile="serbian_drill")

        assert result.master_16 and Path(result.master_16).exists()
        assert result.target_lufs == -8.5
        assert result.elapsed_seconds >= 0

    def test_timeout_is_reported_as_incomplete_intermediates(self, tmp_path, monkeypatch):
        source = _write_tone(tmp_path / "s.wav", -12.0)
        self._ok_env(monkeypatch)

        def boom(command, timeout=0):
            raise subprocess.TimeoutExpired(command, timeout)

        monkeypatch.setattr(bridge, "run_in_wsl", boom)
        with pytest.raises(bridge.MasteringFailed) as exc:
            bridge.master(source, "x", tmp_path, profile="club", timeout=5)
        assert "intermediate" in str(exc.value)

    def test_env_overrides_are_quoted_into_the_command(self, tmp_path, monkeypatch):
        """EQ_CHAIN contains '=' and ':' and must survive the shell intact."""
        source = _write_tone(tmp_path / "s.wav", -12.0)
        project = tmp_path / "proj"
        self._ok_env(monkeypatch)
        seen = {}

        def fake_run(command, timeout=0):
            seen["command"] = command
            out = project / "master"
            out.mkdir(parents=True, exist_ok=True)
            _write_tone(out / "song_MASTER_16.wav", -8.5)
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        monkeypatch.setattr(bridge, "run_in_wsl", fake_run)
        bridge.master(source, "song", project, profile="club",
                      env_overrides={"EQ_CHAIN": "equalizer=f=200:t=q:g=-1.5"})

        assert "EQ_CHAIN='equalizer=f=200:t=q:g=-1.5'" in seen["command"]
        assert "/mnt/" in seen["command"], "paths must be translated for WSL"
