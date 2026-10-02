"""Batch tests — resumable fx rendering over a directory of wavs."""

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

pytest.importorskip("pedalboard")

from toolshop.fx.batch_fx import run_fx_batch
from toolshop.fx.chain import FXChain, FXStage

SR = 48000


def _write_tone(path: Path, freq=440.0, sr=SR):
    t = np.arange(int(sr * 0.5)) / sr
    x = np.sin(2 * np.pi * freq * t) * 0.25
    sf.write(str(path), np.stack([x, x], 1).astype(np.float32), sr)


def _chain():
    return FXChain(name="t", sample_rate=SR, stages=[
        FXStage(builtin="hpf", params={"freq": 200.0}),
    ])


def test_batch_renders_all_files(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for i in range(3):
        _write_tone(src / f"track_{i}.wav")
    out = tmp_path / "out"
    status = run_fx_batch(_chain(), {"plugins": []}, src, out)
    assert len(status["tracks"]) == 3
    assert all(t["status"] == "completed" for t in status["tracks"])
    assert len(list(out.glob("*.wav"))) == 3
    assert (out / "batch_status.json").exists()


def test_batch_resume_skips_completed(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    for i in range(3):
        _write_tone(src / f"track_{i}.wav")
    out = tmp_path / "out"

    run_fx_batch(_chain(), {"plugins": []}, src, out)
    # Simulate interruption: mark the third file incomplete in status.
    status_path = out / "batch_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["tracks"][-1]["status"] = "pending"
    status_path.write_text(json.dumps(status), encoding="utf-8")

    calls = []
    import toolshop.fx.engine as engine
    orig = engine.render_file
    engine.render_file = lambda *a, **kw: (calls.append(1), orig(*a, **kw))[1]
    try:
        run_fx_batch(_chain(), {"plugins": []}, src, out)
    finally:
        engine.render_file = orig
    assert len(calls) == 1  # only the interrupted file re-rendered


def test_batch_failure_recorded_and_retried(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    _write_tone(src / "ok.wav")
    _write_tone(src / "bad.wav")
    out = tmp_path / "out"

    import toolshop.fx.engine as engine
    orig = engine.render_file

    def fail_once(chain, reg, inp, outp, **kw):
        if "bad" in str(inp):
            raise RuntimeError("boom")
        return orig(chain, reg, inp, outp, **kw)

    engine.render_file = fail_once
    try:
        status = run_fx_batch(_chain(), {"plugins": []}, src, out)
    finally:
        engine.render_file = orig

    statuses = {Path(t["source"]).stem: t["status"] for t in status["tracks"]}
    assert statuses["ok"] == "completed"
    assert statuses["bad"] == "failed"
    assert "boom" in next(
        t["error"] for t in status["tracks"] if Path(t["source"]).stem == "bad")
