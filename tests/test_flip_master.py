"""Tests for toolshop.flip.master — W5 mastering stage (F9)."""

import numpy as np
import pytest

from toolshop.flip import master


SR = 44100


def _tone(freq=220.0, dur=4.0, amp=0.1, sr=SR, stereo=True):
    t = np.arange(int(dur * sr)) / sr
    y = amp * np.sin(2 * np.pi * freq * t)
    if stereo:
        return np.stack([y, y], axis=1).astype(np.float32)
    return y.astype(np.float32)


# ---------------------------------------------------------------------------
# mix_lanes
# ---------------------------------------------------------------------------

def test_mix_lanes_sums_and_pads_tail():
    beat = np.full((1000, 2), 0.25, dtype=np.float32)
    vocal = np.full((1200, 2), 0.1, dtype=np.float32)
    mix, info = master.mix_lanes(beat, vocal)
    assert mix.shape == (1200, 2)
    assert mix[500, 0] == pytest.approx(0.35, abs=1e-4)
    assert mix[1100, 0] == pytest.approx(0.1, abs=1e-4)   # beat zero-padded tail
    assert info["clip_guard_fired"] is False
    assert info["pre_guard_peak"] == pytest.approx(0.35, abs=1e-3)


def test_mix_lanes_clip_guard_records_pre_peak():
    beat = np.full((500, 2), 0.9, dtype=np.float32)
    vocal = np.full((500, 2), 0.5, dtype=np.float32)
    mix, info = master.mix_lanes(beat, vocal)
    assert info["clip_guard_fired"] is True
    assert info["pre_guard_peak"] == pytest.approx(1.4, abs=1e-3)
    assert np.abs(mix).max() == pytest.approx(master.MIX_CLIP_GUARD, abs=1e-3)


def test_mix_lanes_gains_applied():
    beat = np.full((400, 1), 1.0, dtype=np.float32)
    vocal = np.full((400, 1), 1.0, dtype=np.float32)
    mix, info = master.mix_lanes(beat, vocal, beat_gain=0.5, vocal_gain=0.25)
    assert mix[:, 0].max() == pytest.approx(0.75, abs=1e-4)
    assert info["beat_gain"] == 0.5 and info["vocal_gain"] == 0.25


# ---------------------------------------------------------------------------
# meters
# ---------------------------------------------------------------------------

def test_true_peak_and_lufs_on_known_signal():
    y = _tone(amp=0.5)
    tp = master.true_peak_dbfs(y, SR)
    lufs = master.integrated_lufs(y, SR)
    assert tp == pytest.approx(-6.02, abs=0.3)      # 0.5 peak
    assert -20.0 < lufs < -5.0                       # sane BS.1770 reading


# ---------------------------------------------------------------------------
# master_audio
# ---------------------------------------------------------------------------

def test_master_hits_lufs_and_tp_spec():
    y = _tone(amp=0.05)                              # quiet input -> real gain
    out, rep = master.master_audio(y, SR)
    assert rep["passed"] is True
    assert rep["final_lufs"] == pytest.approx(master.TARGET_LUFS, abs=0.3)
    assert rep["final_true_peak_dbtp"] <= master.TP_CEILING_DBTP + 0.05
    assert np.abs(out).max() <= 1.0


def test_master_limits_hot_signal():
    y = _tone(amp=0.95)                              # hot input -> real limiting
    out, rep = master.master_audio(y, SR)
    assert rep["final_true_peak_dbtp"] <= master.TP_CEILING_DBTP + 0.05
    assert rep["final_lufs"] == pytest.approx(master.TARGET_LUFS, abs=0.3)
    assert rep["passed"] is True


def test_master_club_arm_target():
    y = _tone(amp=0.1)
    out, rep = master.master_audio(y, SR, target_lufs=master.CLUB_LUFS)
    assert rep["final_lufs"] == pytest.approx(master.CLUB_LUFS, abs=0.3)
    assert rep["final_true_peak_dbtp"] <= master.TP_CEILING_DBTP + 0.05
    assert rep["passed"] is True


def test_master_is_deterministic():
    y = _tone(freq=330.0, amp=0.08)
    a, ra = master.master_audio(y, SR)
    b, rb = master.master_audio(y.copy(), SR)
    np.testing.assert_allclose(a, b, atol=1e-6)
    assert ra["final_lufs"] == rb["final_lufs"]


def test_master_gain_cap_on_unmeasurable_input():
    y = np.zeros((int(0.5 * SR), 2), dtype=np.float32)
    y[::1000, 0] = 1e-6                              # near-silent
    out, rep = master.master_audio(y, SR)
    assert np.isfinite(out).all()
    assert rep["gain_capped"] is True


def test_master_file_roundtrip(tmp_path):
    import soundfile as sf
    src = tmp_path / "in.wav"
    dst = tmp_path / "out.wav"
    sf.write(str(src), _tone(), SR)
    rep = master.master_file(src, dst)
    assert dst.exists()
    y, sr = sf.read(str(dst), always_2d=True)
    assert sr == SR
    assert master.integrated_lufs(y, sr) == pytest.approx(-14.0, abs=0.3)
    assert master.true_peak_dbfs(y, sr) <= master.TP_CEILING_DBTP + 0.05
    assert rep["passed"] is True
