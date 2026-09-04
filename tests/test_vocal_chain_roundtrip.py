"""Tests for the differential round-trip recovery harness (toolshop/vocal_chain).

Question under test: given a dry vocal and the same vocal rendered through a
*known* Chain, can we recover the chain's parameters? This is the
differential floor -- both signals are known. Every synthetic test sets a
ground-truth value, renders, extracts, and asserts the recovered value
against that ground truth within a named, commented tolerance -- never just
`assertIn('key', result)`, which a constant-returning stub could pass.

Sweeps use >= 3 distinct values per parameter so a stub cannot fake recovery.

Tolerances were derived empirically (see ORCHESTRATION/wave_vc1/agent_d1_handoff.md
for the full recovery table) and are named constants with a reasoning comment
each, per AGENTS.md measurement discipline.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from mastering_tool.tools.chain_dsl.schema import Chain, Clipper, Compressor, EQ, EQBand, HPF

from toolshop.vocal_chain.roundtrip import (
    extract_differential,
    recover_clipper_drive_db,
    recover_compressor,
    recover_eq_band_gains,
    recover_hpf_cutoff_hz,
    render_known,
)
from toolshop.paths import subdir

SR = 48000

# ---------------------------------------------------------------------------
# Tolerances (named constants, each with a reasoning comment; see the D1
# handoff's recovery table for the measured errors these were sized against).
# ---------------------------------------------------------------------------

# H1 transfer-function frequency resolution at nperseg=8192, sr=48000 is
# 48000/8192 ~= 5.86Hz. The -3dB crossing is linearly interpolated between
# bins so measured error was < 1Hz in probing; this tolerance is ~1 bin of
# headroom above that.
HPF_FREQ_TOLERANCE_HZ = 6.0

# Peak-filter center-frequency gain measured via the same H1 estimator was
# accurate to < 0.05dB in probing (5s white noise, nperseg=8192). 1dB gives
# generous headroom for shorter or noisier real-world material.
EQ_GAIN_TOLERANCE_DB = 1.0

# The hinge-fit slope above threshold recovers the ratio to < 1% error on
# clean synthetic staircases. 5% leaves headroom while still discriminating
# ratio=2 from 4 from 8.
COMP_RATIO_REL_TOLERANCE = 0.05

# The below-threshold y-x offset recovers makeup gain to < 0.001dB error on
# clean synthetic staircases (it's a direct median measurement, not a fit).
COMP_MAKEUP_TOLERANCE_DB = 0.5

# Pairwise deltas between recovered thresholds, from renders of the *same*
# dry staircase (only comp params change), cancel both the grid-search
# quantization (0.25dB step) and a systematic detector-reference bias
# documented below -- observed delta error was ~0 in probing. 0.5dB covers
# one grid step of slack either side.
COMP_THRESHOLD_DELTA_TOLERANCE_DB = 0.5

# Absolute threshold_db carries a reproducible ~3.8dB offset from nominal
# for Gaussian white-noise material: block-RMS-in-dB (this module's x-axis)
# is not the same detector pedalboard.Compressor uses internally, and the
# offset was stable within 0.05dB across frame_ms in {10..300} and across
# every threshold/ratio combination tried -- so it is a real, reproducible
# calibration difference, not fit noise. It is NOT baked into the recovery
# function: hard-coding a white-noise-specific correction would silently
# mis-calibrate on any other signal (e.g. a real vocal's different crest
# factor implies a different offset). This tolerance is sized to accept that
# known, characterized bias while still catching a genuinely wrong recovery
# (sign flip, wrong stage, etc).
COMP_THRESHOLD_ABS_TOLERANCE_DB = 6.0

# Pedalboard's Distortion is documented as y = tanh(x * db_to_gain(drive_db)),
# which recover_clipper_drive_db inverts exactly per-sample. Measured error
# in probing was ~3e-6dB (floating point noise). 0.2dB leaves large headroom.
CLIP_DRIVE_TOLERANCE_DB = 0.2


# ---------------------------------------------------------------------------
# Synthetic signal generators (truth is known analytically for all of these)
# ---------------------------------------------------------------------------


def _white_noise(seconds: float, sr: int = SR, seed: int = 0, amp: float = 0.2) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(sr * seconds)
    return (rng.standard_normal(n).astype(np.float32) * amp)


def _sine_sweep(seconds: float, sr: int = SR, f0: float = 40.0, f1: float = 12000.0, amp: float = 0.3) -> np.ndarray:
    """Linear chirp from f0 to f1 -- exercises the nonlinearity across many frequencies."""
    t = np.arange(int(sr * seconds)) / sr
    k = (f1 - f0) / seconds
    phase = 2 * np.pi * (f0 * t + 0.5 * k * t**2)
    return (amp * np.sin(phase)).astype(np.float32)


def _click_train(seconds: float, sr: int = SR, click_hz: float = 25.0, jitter_frac: float = 0.35, seed: int = 5) -> np.ndarray:
    """Jittered impulse train: broadband like noise (a perfectly periodic train
    would concentrate energy in narrow combs, leaving the H1 estimator dividing
    near-zero by near-zero between harmonics)."""
    rng = np.random.default_rng(seed)
    n = int(sr * seconds)
    x = np.zeros(n, dtype=np.float32)
    nominal_period = sr / click_hz
    t = 0.0
    while True:
        jitter = rng.uniform(-jitter_frac, jitter_frac) * nominal_period
        idx = int(round(t + jitter))
        if idx >= n:
            break
        if idx >= 0:
            x[idx] = 0.9
        t += nominal_period
    return x


def _staircase(levels_db, sr: int = SR, hold_s: float = 1.2, seed: int = 3) -> np.ndarray:
    """Blocks of white noise held at fixed RMS levels -- the standard method for
    measuring a compressor's I/O characteristic curve. Each block must be held
    much longer than attack_ms/release_ms so the envelope settles."""
    rng = np.random.default_rng(seed)
    chunk = int(sr * hold_s)
    parts = [rng.standard_normal(chunk).astype(np.float32) * (10 ** (db / 20.0)) for db in levels_db]
    return np.concatenate(parts)


_STAIRCASE_LEVELS_DB = [-40, -34, -28, -22, -16, -10, -6, -3, -1]


# ---------------------------------------------------------------------------
# HPF cutoff
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("freq_hz", [60.0, 90.0, 120.0])
def test_hpf_cutoff_recovery_white_noise(freq_hz):
    dry = _white_noise(5.0, seed=1)
    chain = Chain(sample_rate=SR, hpf=HPF(freq=freq_hz, bypass=False))
    wet = render_known(dry, SR, chain)

    rec = recover_hpf_cutoff_hz(dry, wet, SR)

    assert rec.value is not None, rec.reason
    assert abs(rec.value - freq_hz) <= HPF_FREQ_TOLERANCE_HZ
    assert rec.confidence is not None and rec.confidence > 0.5


@pytest.mark.parametrize("freq_hz", [60.0, 90.0, 120.0])
def test_hpf_cutoff_recovery_click_train(freq_hz):
    """Cross-check on a structurally different broadband source: recovery
    should not depend on the excitation being Gaussian noise specifically."""
    dry = _click_train(6.0, seed=5)
    chain = Chain(sample_rate=SR, hpf=HPF(freq=freq_hz, bypass=False))
    wet = render_known(dry, SR, chain)

    rec = recover_hpf_cutoff_hz(dry, wet, SR)

    assert rec.value is not None, rec.reason
    assert abs(rec.value - freq_hz) <= HPF_FREQ_TOLERANCE_HZ


def test_hpf_bypassed_chain_returns_none_with_reason():
    """A test that cannot fail is worse than no test: this asserts the honest
    non-recovery path fires (value None + a reason), not just that *some*
    dict key exists."""
    dry = _white_noise(5.0, seed=9)
    chain = Chain(sample_rate=SR)  # everything bypassed
    wet = render_known(dry, SR, chain)
    assert np.array_equal(dry, wet)  # sanity: bypass really is a no-op

    rec = recover_hpf_cutoff_hz(dry, wet, SR)

    assert rec.value is None
    assert rec.reason is not None and len(rec.reason) > 0


# ---------------------------------------------------------------------------
# EQ band gains
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("gain_db", [-8.0, 4.0, 10.0])
def test_eq_band_gain_recovery(gain_db):
    dry = _white_noise(5.0, seed=2)
    chain = Chain(sample_rate=SR, eq=EQ(bands=[EQBand(freq=1000.0, gain=gain_db, q=1.0)], bypass=False))
    wet = render_known(dry, SR, chain)

    table = recover_eq_band_gains(dry, wet, SR)
    rec = table[1000.0]

    assert rec.value is not None, rec.reason
    assert abs(rec.value - gain_db) <= EQ_GAIN_TOLERANCE_DB

    # A stub returning a fixed table would fail here too: neighbouring bands
    # (2+ octaves from 1000Hz) must show much smaller measured gain than the
    # band actually touched.
    far_bands = [f for f in table if f <= 250.0 or f >= 4000.0]
    for f in far_bands:
        far_rec = table[f]
        if far_rec.value is not None:
            assert abs(far_rec.value) < abs(gain_db) * 0.5 + 1.0


# ---------------------------------------------------------------------------
# Compressor: ratio, threshold, makeup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ratio", [2.0, 4.0, 8.0])
def test_compressor_ratio_recovery(ratio):
    dry = _staircase(_STAIRCASE_LEVELS_DB)
    chain = Chain(
        sample_rate=SR,
        comp=Compressor(threshold_db=-18.0, ratio=ratio, attack_ms=5.0, release_ms=80.0, makeup_db=0.0, bypass=False),
    )
    wet = render_known(dry, SR, chain)

    comp = recover_compressor(dry, wet, SR)
    rec = comp["ratio"]

    assert rec.value is not None, rec.reason
    assert abs(rec.value - ratio) <= ratio * COMP_RATIO_REL_TOLERANCE


@pytest.mark.parametrize("makeup_db", [0.0, 6.0, 12.0])
def test_compressor_makeup_recovery(makeup_db):
    dry = _staircase(_STAIRCASE_LEVELS_DB)
    chain = Chain(
        sample_rate=SR,
        comp=Compressor(threshold_db=-18.0, ratio=4.0, attack_ms=5.0, release_ms=80.0, makeup_db=makeup_db, bypass=False),
    )
    wet = render_known(dry, SR, chain)

    comp = recover_compressor(dry, wet, SR)
    rec = comp["makeup_db"]

    assert rec.value is not None, rec.reason
    assert abs(rec.value - makeup_db) <= COMP_MAKEUP_TOLERANCE_DB


def test_compressor_threshold_recovery_absolute_and_relative():
    """Absolute recovery carries a documented ~3.8dB detector-reference bias
    (see COMP_THRESHOLD_ABS_TOLERANCE_DB) -- so this asserts BOTH the loose
    bias-inclusive absolute bound AND a tight relative bound on the deltas
    between sweep values, which a constant-returning stub cannot satisfy."""
    thresholds = [-24.0, -18.0, -12.0]
    recovered = {}
    for thr in thresholds:
        dry = _staircase(_STAIRCASE_LEVELS_DB)  # same signal (fixed seed) every time
        chain = Chain(
            sample_rate=SR,
            comp=Compressor(threshold_db=thr, ratio=4.0, attack_ms=5.0, release_ms=80.0, makeup_db=6.0, bypass=False),
        )
        wet = render_known(dry, SR, chain)
        comp = recover_compressor(dry, wet, SR)
        rec = comp["threshold_db"]
        assert rec.value is not None, rec.reason
        recovered[thr] = rec.value
        assert abs(rec.value - thr) <= COMP_THRESHOLD_ABS_TOLERANCE_DB

    delta_true = thresholds[2] - thresholds[0]
    delta_recovered = recovered[thresholds[2]] - recovered[thresholds[0]]
    assert abs(delta_recovered - delta_true) <= COMP_THRESHOLD_DELTA_TOLERANCE_DB


def test_compressor_bypassed_chain_returns_none_threshold_with_reason():
    dry = _staircase(_STAIRCASE_LEVELS_DB)
    chain = Chain(sample_rate=SR)  # everything bypassed
    wet = render_known(dry, SR, chain)

    comp = recover_compressor(dry, wet, SR)
    thr_rec = comp["threshold_db"]

    assert thr_rec.value is None
    assert thr_rec.reason is not None and len(thr_rec.reason) > 0
    # ratio correctly reads as "no compression" (~1.0) even though threshold
    # is unidentifiable -- these are independently meaningful, not coupled.
    assert comp["ratio"].value is not None
    assert abs(comp["ratio"].value - 1.0) < 0.05


# ---------------------------------------------------------------------------
# Clipper drive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("drive_db", [6.0, 15.0, 24.0])
def test_clipper_drive_recovery_sine_sweep(drive_db):
    dry = _sine_sweep(2.0, amp=0.3)
    chain = Chain(sample_rate=SR, clip=Clipper(drive_db=drive_db, bypass=False))
    wet = render_known(dry, SR, chain)

    rec = recover_clipper_drive_db(dry, wet)

    assert rec.value is not None, rec.reason
    assert abs(rec.value - drive_db) <= CLIP_DRIVE_TOLERANCE_DB
    assert rec.confidence is not None and rec.confidence > 0.9


# ---------------------------------------------------------------------------
# extract_differential: end-to-end, chain-blind entry point
# ---------------------------------------------------------------------------


def test_extract_differential_recovers_active_hpf_and_reports_dict_shape():
    dry = _white_noise(5.0, seed=11)
    chain = Chain(sample_rate=SR, hpf=HPF(freq=100.0, bypass=False))
    wet = render_known(dry, SR, chain)

    result = extract_differential(dry, wet, SR)

    for key in ("hpf_cutoff_hz", "eq_band_gains_db", "comp_threshold_db", "comp_ratio", "comp_makeup_db", "clip_drive_db"):
        assert key in result

    hpf_field = result["hpf_cutoff_hz"]
    assert hpf_field["value"] is not None
    assert abs(hpf_field["value"] - 100.0) <= HPF_FREQ_TOLERANCE_HZ
    # extract_differential is blind to the chain: it must NOT have recovered
    # a plausible-looking compressor threshold from a signal with no
    # compressor active.
    assert result["comp_threshold_db"]["value"] is None
    assert result["comp_threshold_db"]["reason"] is not None


# ---------------------------------------------------------------------------
# Real audio: same single-stage-isolated protocol as the synthetic tests,
# applied to an actual dry vocal take, to see whether recovery on real
# material matches recovery on synthetic (AGENTS.md: validate on a full
# take, not a clip -- a clip result has bitten this repo before).
# ---------------------------------------------------------------------------

_REAL_VOCAL_DIR = Path(
    r"D:\Projects\music_toolshop_v2\data\ZELDI x ZA OVAJ GRAD\record 1 Project\Samples\Recorded"
)
_REAL_VOCAL_FILE = _REAL_VOCAL_DIR / "Main Vokal 0001 [2026-08-26 223320].wav"


@pytest.mark.slow
def test_real_vocal_hpf_and_clip_recovery():
    if not _REAL_VOCAL_FILE.exists():
        pytest.skip(f"real dry vocal not available at {_REAL_VOCAL_FILE}")

    import soundfile as sf

    dry, file_sr = sf.read(str(_REAL_VOCAL_FILE), dtype="float32")
    assert dry.ndim == 1, "expected mono take"

    out_dir = subdir("vocal_chain", "roundtrip_real", create=True)

    # HPF isolated at 90Hz
    hpf_chain = Chain(sample_rate=float(file_sr), hpf=HPF(freq=90.0, bypass=False))
    hpf_wet = render_known(dry, file_sr, hpf_chain)
    sf.write(str(out_dir / "real_hpf90_wet.wav"), hpf_wet, file_sr)
    hpf_rec = recover_hpf_cutoff_hz(dry, hpf_wet, file_sr)

    # Clipper isolated at 15dB drive
    clip_chain = Chain(sample_rate=float(file_sr), clip=Clipper(drive_db=15.0, bypass=False))
    clip_wet = render_known(dry, file_sr, clip_chain)
    sf.write(str(out_dir / "real_clip15_wet.wav"), clip_wet, file_sr)
    clip_rec = recover_clipper_drive_db(dry, clip_wet)

    # Real material has an uneven, non-flat natural spectrum (unlike white
    # noise) so this uses a looser tolerance than the synthetic sweep, but it
    # must still land in the right neighbourhood -- not just "a number".
    if hpf_rec.value is not None:
        assert abs(hpf_rec.value - 90.0) <= 25.0
    else:
        # Honest non-recovery is an acceptable outcome to report, not a
        # test failure by itself -- but it must carry a reason.
        assert hpf_rec.reason

    if clip_rec.value is not None:
        assert abs(clip_rec.value - 15.0) <= 3.0
    else:
        assert clip_rec.reason
