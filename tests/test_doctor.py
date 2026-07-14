"""Tests for toolshop doctor diagnostics."""

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

from toolshop import doctor


def test_python_version_ok_when_expected():
    with mock.patch.object(sys, "version_info", (3, 11, 9, "final", 0)):
        result = doctor._python_version_ok()
    assert result["ok"] is True
    assert result["actual"] == "3.11"


def test_python_version_fails_when_wrong():
    with mock.patch.object(sys, "version_info", (3, 13, 5, "final", 0)):
        result = doctor._python_version_ok()
    assert result["ok"] is False
    assert result["actual"] == "3.13"


def test_ffmpeg_ok_found(monkeypatch, tmp_path):
    fake_ffmpeg = tmp_path / "ffmpeg.exe"
    fake_ffmpeg.write_text("fake")
    monkeypatch.setenv("TOOLSHOP_FFMPEG", str(fake_ffmpeg))

    with mock.patch.object(doctor.subprocess, "run") as mock_run:
        mock_run.return_value.stdout = "ffmpeg version 6.0\n"
        mock_run.return_value.stderr = ""
        result = doctor._ffmpeg_ok()

    assert result["ok"] is True
    assert "ffmpeg version 6.0" in result["version"]


def test_ffmpeg_ok_missing():
    with mock.patch.object(doctor.shutil, "which", return_value=None):
        with mock.patch.dict("os.environ", {"TOOLSHOP_FFMPEG": ""}, clear=True):
            with mock.patch.object(Path, "exists", return_value=False):
                result = doctor._ffmpeg_ok()
    assert result["ok"] is False
    assert result["path"] is None


def test_packages_ok_all_present():
    with mock.patch.object(doctor.importlib, "import_module") as mock_import:
        result = doctor._packages_ok("audio")
    assert result["ok"] is True
    assert result["missing"] == []
    assert mock_import.call_count == 3


def test_packages_ok_missing():
    def fake_import(name):
        if name == "librosa":
            raise ImportError("not installed")
        return mock.Mock()

    with mock.patch.object(doctor.importlib, "import_module", side_effect=fake_import):
        result = doctor._packages_ok("audio")

    assert result["ok"] is False
    assert result["missing"] == ["librosa"]


def test_disk_ok_enough_space(monkeypatch):
    fake_usage = mock.Mock(free=50 * 1024**3)
    with mock.patch.object(doctor.shutil, "disk_usage", return_value=fake_usage):
        result = doctor._disk_ok()
    assert result["ok"] is True
    assert result["free_gb"] == 50.0


def test_disk_ok_not_enough_space(monkeypatch):
    fake_usage = mock.Mock(free=5 * 1024**3)
    with mock.patch.object(doctor.shutil, "disk_usage", return_value=fake_usage):
        result = doctor._disk_ok()
    assert result["ok"] is False


def test_model_cache_ok(tmp_path, monkeypatch):
    cache = tmp_path / "models"
    cache.mkdir()
    for name in doctor.stem_models.expected_model_files():
        (cache / name).touch()
    monkeypatch.setenv("TOOLSHOP_MODEL_DIR", str(cache))
    result = doctor._model_cache_ok()
    assert result["ok"] is True
    assert result["path"] == str(cache)
    assert result["missing"] == []


def test_model_cache_missing(tmp_path, monkeypatch):
    cache = tmp_path / "models"
    cache.mkdir()
    monkeypatch.setenv("TOOLSHOP_MODEL_DIR", str(cache))
    result = doctor._model_cache_ok()
    assert result["ok"] is False
    assert result["missing"]


def test_run_checks_aggregates_ok():
    report = doctor.run_checks()
    assert "ok" in report
    assert "checks" in report
    assert "python" in report


def test_print_report_output(capsys):
    report = {"ok": True, "python": sys.executable, "checks": []}
    doctor.print_report(report)
    captured = capsys.readouterr()
    assert "toolshop doctor" in captured.out
    assert "PASS" in captured.out


def test_main_json_output(tmp_path):
    out = tmp_path / "doctor.json"
    with mock.patch.object(doctor, "run_checks", return_value={"ok": True, "python": "x", "checks": []}):
        code = doctor.main(["--json", str(out)])
    assert code == 0
    assert json.loads(out.read_text())["ok"] is True


def test_main_returns_nonzero_on_failure():
    with mock.patch.object(doctor, "run_checks", return_value={"ok": False, "python": "x", "checks": []}):
        code = doctor.main([])
    assert code == 1
