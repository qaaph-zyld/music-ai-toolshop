"""Tests for the DawDreamer evaluation harness.

Unit tests cover the parent's subprocess plumbing and verdict merging with a
faked ``subprocess.run``; the real plugin checks are ``@pytest.mark.slow`` and
excluded from normal runs (same convention as the fx probe suite).
"""

from __future__ import annotations

import json
import subprocess

import pytest

from toolshop.fx import dawdreamer_eval as ev


# ---------------------------------------------------------------------------
# Parent-side plumbing (no real plugins, no real subprocess)
# ---------------------------------------------------------------------------

class FakeCP:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_run_check_parses_last_json_line(monkeypatch):
    payload = {"check": "dry_gate", "verdict": "ok", "evidence": "x"}
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return FakeCP(stdout="noise\n" + json.dumps(payload) + "\n")

    monkeypatch.setattr(ev.subprocess, "run", fake_run)
    result = ev.run_check("dry_gate")
    assert result["verdict"] == "ok"
    assert "--child" in seen["cmd"] and "dry_gate" in seen["cmd"]
    assert "toolshop.fx.dawdreamer_eval" in seen["cmd"]


def test_run_check_timeout_is_verdict(monkeypatch):
    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    monkeypatch.setattr(ev.subprocess, "run", fake_run)
    result = ev.run_check("vst2_fx")
    assert result == {"check": "vst2_fx", "verdict": "timeout",
                      "evidence": f"child exceeded {ev.CHILD_TIMEOUT_S}s",
                      "wall_s": result["wall_s"]}


def test_run_check_crash_captures_stderr(monkeypatch):
    def fake_run(cmd, **kw):
        return FakeCP(stderr="Access violation in Glitch2.dll",
                      returncode=-1073741819)
    monkeypatch.setattr(ev.subprocess, "run", fake_run)
    result = ev.run_check("vst2_fx")
    assert result["verdict"] == "crash"
    assert "Glitch2" in result["evidence"]
    assert result["returncode"] == -1073741819


def test_evaluate_merges_and_summarises(monkeypatch):
    fake = {
        "dry_gate": {"check": "dry_gate", "verdict": "ok"},
        "vst2_fx": {"check": "vst2_fx", "verdict": "ok"},
        "vsti_midi": {"check": "vsti_midi", "verdict": "crash"},
        "automation": {"check": "automation", "verdict": "skipped-missing"},
        "preset": {"check": "preset", "verdict": "skipped-no-preset"},
        "determinism": {"check": "determinism", "verdict": "ok"},
        "parity_perf": {"check": "parity_perf", "verdict": "ok"},
    }
    monkeypatch.setattr(ev, "run_check", lambda c, **kw: fake[c])
    doc = ev.evaluate()
    assert doc["summary"]["checks"] == 7
    assert doc["summary"]["hard_failures"] == 1
    assert doc["summary"]["all_ok_or_skipped"] is False
    assert doc["summary"]["non_ok"] == ["vsti_midi"]
    assert doc["license"] == "GPLv3"


def test_main_writes_eval_json(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "evaluate",
                        lambda checks=None: {"checks": [], "summary": {
                            "checks": 0, "hard_failures": 0,
                            "all_ok_or_skipped": True, "non_ok": []}})
    out = tmp_path / "eval.json"
    rc = ev.main(["--out", str(out)])
    assert rc == 0
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["checks"] == 0


# ---------------------------------------------------------------------------
# Child mode — only exercised when dawdreamer is importable; the real plugin
# checks are slow and hit the machine's installed VSTs.
# ---------------------------------------------------------------------------

def test_child_without_dawdreamer_reports_blocked_env(monkeypatch):
    """run_child must degrade to blocked-env evidence, not raise."""
    real_import = __builtins__["__import__"] if isinstance(
        __builtins__, dict) else __builtins__.__import__

    def fake_import(name, *a, **kw):
        if name == "dawdreamer":
            raise ImportError("No module named 'dawdreamer'")
        return real_import(name, *a, **kw)

    monkeypatch.setitem(__builtins__, "__import__", fake_import) \
        if isinstance(__builtins__, dict) else \
        monkeypatch.setattr("builtins.__import__", fake_import)
    result = ev.run_child("dry_gate", 48000)
    assert result["verdict"] == "blocked-env"
    assert "import failed" in result["evidence"]


@pytest.mark.slow
def test_child_dry_gate_real():
    """Real dawdreamer playback-only render — requires the wheel installed."""
    pytest.importorskip("dawdreamer")
    result = ev.run_child("dry_gate", 48000)
    assert result["verdict"] == "ok", result
    assert result["dawdreamer_version"]


@pytest.mark.slow
@pytest.mark.parametrize("check", ["vst2_fx", "vsti_midi", "automation",
                                   "preset", "determinism", "parity_perf"])
def test_child_real_check(check):
    pytest.importorskip("dawdreamer")
    result = ev.run_child(check, 48000)
    assert result["verdict"] != "error", result
