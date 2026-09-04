"""Differential round-trip recovery: given (dry, wet) can we recover the Chain?

`render_known` renders a dry signal through a known `Chain` (thin wrapper over
`mastering_tool.tools.chain_dsl.executors.pedalboard_exec`). `extract_differential`
takes the resulting (dry, wet) pair and tries to recover each stage's
parameters *without* being told what the chain was.

Every recoverable field is returned as a `Recovery`: a `value`, a `confidence`
in [0, 1] (or `None`), the `method` name, and -- when `value` is `None` -- a
`reason` string explaining why it could not be measured. **Never fabricate a
plausible-looking number.** A parameter this module cannot measure returns
`None` with a reason, not a guess (see CHANGELOG.md's RT60 defect for why that
distinction matters).

Methods, one per stage
-----------------------
- **HPF cutoff** -- H1 transfer-function estimate `H(f) = Pxy(f)/Pxx(f)`
  (Welch-averaged cross/auto spectral density between dry and wet), then the
  frequency where |H| crosses 3 dB below its high-frequency plateau. This is
  well-posed for a first-order filter (pedalboard's `HighpassFilter` *defines*
  its cutoff as the -3dB point, so this measures the same quantity the DSL
  sets, not a proxy for it).
- **EQ band gains** -- the same H(f), sampled (linearly interpolated) at a
  standard set of octave-band centres and reported relative to a flat
  baseline measured >1.5 octaves away from each centre. Reported as a table,
  not tied to any particular chain's actual band frequencies -- this module
  is not told what the chain was.
- **Compressor threshold/ratio (`recover_compressor`)** -- per-frame RMS-in
  vs RMS-out (dB), grid search over a hinge point, two independent
  least-squares line fits either side of it. `threshold_db` is the hinge
  x-position; `ratio` is `1/slope` of the above-hinge line. This assumes a
  hard knee (no soft-knee rounding), which matches the installed
  pedalboard_exec (it does not honour `Compressor.knee_db` -- see
  `tests/test_chain_dsl_unwired_params.py`). It also assumes the input is
  quasi-static within a 100ms frame -- true for a held-level staircase, false
  for a sung vocal (continuous phrasing/vibrato/transients), where it
  recovers ratio/threshold badly (see the Wave 2 D1 handoff's recovery
  table). Kept as-is; superseded for dynamic material by
  `recover_compressor_gain_reduction` below.
- **Compressor makeup gain** -- the median `y_db - x_db` offset for frames
  well below the recovered threshold (where gain should be unity + makeup).
  Stays accurate even on material where `recover_compressor`'s own
  threshold/ratio fail, and is reused by `recover_compressor_gain_reduction`.
- **Compressor threshold/ratio/attack/release (`recover_compressor_gain_reduction`)**
  -- uses the *instantaneous* per-sample gain reduction
  `GR_db(t) = 20*log10(|wet(t)|/|dry(t)|)` (exact for a pure scalar-gain
  stage, no framing/averaging assumption) fit against a one-pole
  attack/release envelope-follower detector level built from `|dry|`,
  instead of block RMS on both axes. `attack_ms`/`release_ms` fall out of a
  grid search over candidate time constants, picking the pair whose envelope
  best explains the measured GR curve; reported `None` when the fit residual
  has no clear minimum across the grid (not identifiable from the data).
  This is the method to use for continuously dynamic material (real vocals);
  `recover_compressor` remains accurate on quasi-static test signals.
- **Clipper drive** -- pedalboard's `Distortion` docs give the exact model:
  `y = tanh(x * db_to_gain(drive_db))`. That is invertible per-sample:
  `g = arctanh(y) / x`, `drive_db = 20*log10(median(g))`. This is an exact
  analytic inversion, not a curve-fit -- but it is only valid when `dry` is
  actually the clipper's input, i.e. no upstream stage (HPF/EQ/comp) altered
  the signal first. In a multi-stage chain with earlier active stages, this
  recovery is unreliable; the confidence score does not detect that case, so
  treat clip_drive_db recovery as floor-only unless the clipper is isolated.

What this module does NOT do: blind extraction (wet signal only, no dry
reference). That is a materially harder, unsolved problem here -- see the D1
handoff for why the differential floor matters before attempting it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
from scipy import signal as sp_signal

from mastering_tool.tools.chain_dsl.executors import pedalboard_exec
from mastering_tool.tools.chain_dsl.schema import Chain

# ---------------------------------------------------------------------------
# Recovery result type
# ---------------------------------------------------------------------------


@dataclass
class Recovery:
    """One recovered (or un-recoverable) parameter."""

    value: Optional[float]
    confidence: Optional[float]
    method: str
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "method": self.method,
            "reason": self.reason,
        }


# Standard octave-band centres (Hz) used to report the EQ transfer curve.
# This module is not told what the chain's actual EQ band frequencies were,
# so it reports a generic band table sampled at these centres rather than
# guessing which frequencies matter.
STANDARD_EQ_BAND_CENTERS_HZ: Tuple[float, ...] = (
    31.5,
    63.0,
    125.0,
    250.0,
    500.0,
    1000.0,
    2000.0,
    4000.0,
    8000.0,
    16000.0,
)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_known(dry: np.ndarray, sr: int, chain: Chain) -> np.ndarray:
    """Render `dry` through a known `Chain`. Thin wrapper over chain_dsl's renderer."""
    return pedalboard_exec.render(chain, dry, sample_rate=sr)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _mono(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x)
    if x.ndim == 2:
        return x.mean(axis=1)
    return x


def _align(dry: np.ndarray, wet: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    d = _mono(dry).astype(np.float64)
    w = _mono(wet).astype(np.float64)
    n = min(len(d), len(w))
    return d[:n], w[:n]


def _transfer_function(
    dry: np.ndarray, wet: np.ndarray, sr: float, nperseg: int = 8192
) -> Tuple[np.ndarray, np.ndarray]:
    """H1 estimator: H(f) = Pxy(f) / Pxx(f), Welch-averaged.

    Pxy is the dry/wet cross power spectral density, Pxx the dry auto power
    spectral density. This is the standard estimator for the frequency
    response of an (approximately) LTI system given input/output pairs.
    """
    d, w = _align(dry, wet)
    n = len(d)
    if n < 64:
        raise ValueError(f"signal too short for a transfer-function estimate ({n} samples)")
    nperseg = int(min(nperseg, n))
    freqs, pxy = sp_signal.csd(d, w, fs=sr, nperseg=nperseg)
    _, pxx = sp_signal.welch(d, fs=sr, nperseg=nperseg)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = pxy / pxx
    return freqs, h


def _frame_rms_db(x: np.ndarray, sr: float, frame_ms: float, floor_db: float = -100.0) -> np.ndarray:
    """Non-overlapping frame RMS envelope in dBFS."""
    x = _mono(x).astype(np.float64)
    frame_len = max(1, int(round(sr * frame_ms / 1000.0)))
    n_frames = max(0, len(x) // frame_len)
    if n_frames == 0:
        return np.zeros(0)
    trimmed = x[: n_frames * frame_len].reshape(n_frames, frame_len)
    rms = np.sqrt(np.mean(trimmed**2, axis=1) + 1e-24)
    floor_lin = 10 ** (floor_db / 20.0)
    return 20.0 * np.log10(np.maximum(rms, floor_lin))


# ---------------------------------------------------------------------------
# HPF cutoff
# ---------------------------------------------------------------------------


def recover_hpf_cutoff_hz(
    dry: np.ndarray,
    wet: np.ndarray,
    sr: float,
    plateau_band_hz: Tuple[float, float] = (2000.0, 15000.0),
    drop_db: float = 3.0,
) -> Recovery:
    """Recover a high-pass cutoff as the -3dB point of the dry->wet transfer function."""
    method = "transfer_function_h1_minus3db"
    try:
        freqs, h = _transfer_function(dry, wet, sr)
    except ValueError as exc:
        return Recovery(None, None, method, reason=str(exc))

    mag_db = 20.0 * np.log10(np.maximum(np.abs(h), 1e-12))
    plateau_mask = (freqs >= plateau_band_hz[0]) & (freqs <= plateau_band_hz[1])
    if not np.any(plateau_mask):
        return Recovery(
            None, None, method, reason="no frequency bins in the plateau reference band at this sample rate"
        )

    plateau_db = float(np.median(mag_db[plateau_mask]))
    if plateau_db < -20.0:
        return Recovery(
            None,
            None,
            method,
            reason=f"transfer function has no usable passband (plateau {plateau_db:.1f}dB) -- likely near-silent wet signal",
        )

    target_db = plateau_db - drop_db
    below = mag_db < target_db
    crossing_idx: Optional[int] = None
    for i in range(len(freqs) - 1):
        if freqs[i] <= 0:
            continue
        if below[i] and not below[i + 1]:
            crossing_idx = i
            break

    if crossing_idx is None:
        return Recovery(
            None,
            None,
            method,
            reason="no -3dB crossing found below the measured plateau -- transfer function is flat (HPF likely bypassed or freq below measurable range)",
        )

    f1, f2 = float(freqs[crossing_idx]), float(freqs[crossing_idx + 1])
    d1, d2 = float(mag_db[crossing_idx]), float(mag_db[crossing_idx + 1])
    if d2 == d1:
        f_cross = f1
    else:
        frac = (target_db - d1) / (d2 - d1)
        f_cross = f1 + frac * (f2 - f1)

    freq_res = float(freqs[1] - freqs[0]) if len(freqs) > 1 else float("inf")
    plateau_std = float(np.std(mag_db[plateau_mask]))
    confidence = float(np.clip(1.0 - (freq_res / max(f_cross, 1.0)) - plateau_std / 10.0, 0.0, 1.0))
    return Recovery(float(f_cross), confidence, method)


# ---------------------------------------------------------------------------
# EQ band gains
# ---------------------------------------------------------------------------


def recover_eq_band_gains(
    dry: np.ndarray,
    wet: np.ndarray,
    sr: float,
    band_centers_hz: Optional[Tuple[float, ...]] = None,
    exclude_octaves: float = 1.5,
) -> Dict[float, Recovery]:
    """Sample the dry->wet transfer function at standard band centres.

    Each band's gain is reported relative to a baseline measured >=
    `exclude_octaves` octaves away, so an overall level offset elsewhere in
    the chain does not get misread as a band gain.
    """
    method = "transfer_function_h1_band_sample"
    centers = band_centers_hz or STANDARD_EQ_BAND_CENTERS_HZ
    nyquist = sr / 2.0
    centers = tuple(f for f in centers if f < nyquist * 0.95)

    try:
        freqs, h = _transfer_function(dry, wet, sr)
    except ValueError as exc:
        return {f: Recovery(None, None, method, reason=str(exc)) for f in centers}

    mag_db = 20.0 * np.log10(np.maximum(np.abs(h), 1e-12))
    valid = freqs > 20.0
    if not np.any(valid):
        return {
            f: Recovery(None, None, method, reason="no usable frequency bins above 20Hz")
            for f in centers
        }

    out: Dict[float, Recovery] = {}
    for f0 in centers:
        ratio = freqs[valid] / f0
        far_mask = (ratio < 2**-exclude_octaves) | (ratio > 2**exclude_octaves)
        if not np.any(far_mask):
            out[f0] = Recovery(None, None, method, reason="no frequency bins far enough away for a baseline")
            continue
        baseline_db = float(np.median(mag_db[valid][far_mask]))
        band_db = float(np.interp(f0, freqs, mag_db))
        gain_est = band_db - baseline_db

        nearest_bin_dist = float(np.min(np.abs(freqs - f0)))
        confidence = float(np.clip(1.0 - nearest_bin_dist / max(f0, 1.0) * 2.0, 0.0, 1.0))
        out[f0] = Recovery(gain_est, confidence, method)
    return out


# ---------------------------------------------------------------------------
# Compressor threshold / ratio / makeup
# ---------------------------------------------------------------------------


def recover_compressor(
    dry: np.ndarray,
    wet: np.ndarray,
    sr: float,
    frame_ms: float = 100.0,
    min_points_per_side: int = 8,
    silence_floor_db: float = -55.0,
) -> Dict[str, Recovery]:
    """Hinge-fit the input/output RMS(dB) curve to recover threshold/ratio/makeup.

    Assumes a hard knee (matches the installed pedalboard_exec, which does
    not honour `Compressor.knee_db`). Frames are per-block RMS, so this needs
    a test signal whose level changes slowly relative to attack/release
    (e.g. a staircase of held levels) to let the envelope settle; a
    continuously-varying signal will blur the hinge and lower confidence.
    """
    keys = ("threshold_db", "ratio", "makeup_db")

    d, w = _align(dry, wet)
    x_db = _frame_rms_db(d, sr, frame_ms)
    y_db = _frame_rms_db(w, sr, frame_ms)
    m = min(len(x_db), len(y_db))
    x_db, y_db = x_db[:m], y_db[:m]

    active = x_db > silence_floor_db
    x_db, y_db = x_db[active], y_db[active]

    if len(x_db) < 2 * min_points_per_side:
        reason = f"only {len(x_db)} non-silent frames -- need >= {2 * min_points_per_side} to fit a two-line hinge"
        return {k: Recovery(None, None, "rms_io_hinge_fit", reason=reason) for k in keys}

    lo, hi = np.percentile(x_db, [5.0, 95.0])
    if hi - lo < 1.0:
        return {
            k: Recovery(None, None, "rms_io_hinge_fit", reason="input level barely varies -- no dynamic range to fit a hinge over")
            for k in keys
        }

    candidates = np.arange(lo, hi, 0.25)
    best: Optional[Tuple[float, float, float, float, float, float]] = None
    for T in candidates:
        below = x_db <= T
        above = ~below
        if np.sum(below) < min_points_per_side or np.sum(above) < min_points_per_side:
            continue
        m1, c1 = np.polyfit(x_db[below], y_db[below], 1)
        m2, c2 = np.polyfit(x_db[above], y_db[above], 1)
        pred = np.where(below, m1 * x_db + c1, m2 * x_db + c2)
        sse = float(np.sum((y_db - pred) ** 2))
        if best is None or sse < best[0]:
            best = (sse, float(T), float(m1), float(c1), float(m2), float(c2))

    if best is None:
        return {
            k: Recovery(
                None,
                None,
                "rms_io_hinge_fit",
                reason="no candidate split had enough frames on both sides (compressor may never have engaged, or threshold is outside the tested level range)",
            )
            for k in keys
        }

    sse, T, m1, c1, m2, c2 = best
    sst = float(np.sum((y_db - np.mean(y_db)) ** 2))
    r2 = float(np.clip(1.0 - sse / sst, 0.0, 1.0)) if sst > 1e-9 else 0.0

    # A hinge only exists if the two fitted lines actually have different
    # slopes. When they don't (the whole curve is one straight line -- e.g.
    # the compressor is bypassed, or the signal never got loud enough to
    # engage it), the least-squares split still "succeeds" numerically for
    # an arbitrary T (any split of a straight line has ~zero residual), which
    # would report a specific-looking threshold_db that is in fact
    # unidentifiable. Refuse it explicitly rather than emit that number.
    MIN_SLOPE_DIFFERENCE = 0.05  # ~5% slope change; below this, no detectable kink
    slope_diff = abs(m2 - m1)
    result: Dict[str, Recovery] = {}
    if slope_diff < MIN_SLOPE_DIFFERENCE:
        result["threshold_db"] = Recovery(
            None,
            None,
            "rms_io_hinge_fit",
            reason=f"input/output curve is linear throughout (|slope_above - slope_below|={slope_diff:.4f} < {MIN_SLOPE_DIFFERENCE}) "
            "-- no detectable hinge, so threshold is unidentifiable; compressor likely bypassed or never engaged in the tested level range",
        )
    else:
        result["threshold_db"] = Recovery(T, r2, "rms_io_hinge_fit")

    if m2 > 1e-3:
        result["ratio"] = Recovery(float(1.0 / m2), r2, "rms_io_hinge_fit_above_slope")
    else:
        result["ratio"] = Recovery(
            None, None, "rms_io_hinge_fit_above_slope", reason=f"fitted above-threshold slope ({m2:.4f}) is not positive"
        )

    deep_mask = x_db < (T - 6.0)
    if np.sum(deep_mask) >= 5:
        offsets = y_db[deep_mask] - x_db[deep_mask]
        makeup_est = float(np.median(offsets))
        makeup_conf = float(np.clip(1.0 - np.std(offsets) / 3.0, 0.0, 1.0))
        result["makeup_db"] = Recovery(makeup_est, makeup_conf, "below_threshold_offset_median")
    else:
        result["makeup_db"] = Recovery(
            None,
            None,
            "below_threshold_offset_median",
            reason="not enough frames >=6dB below the recovered threshold to isolate makeup gain",
        )

    return result


# ---------------------------------------------------------------------------
# Compressor threshold / ratio / attack / release -- gain-reduction method
#
# `recover_compressor` above assumes quasi-static input (block RMS needs the
# envelope to settle within a 100ms frame); a sung vocal violates that
# continuously (phrasing, vibrato, consonant transients), which flattens its
# recovered ratio toward 1 on real material even though it works well on a
# synthetic staircase (see the Wave 2 D1/D2 handoffs). This method sidesteps
# block-RMS averaging entirely by using the *instantaneous* gain applied at
# each sample -- directly observable in differential mode -- fit against a
# proper attack/release envelope detector instead of a fixed analysis window.
# ---------------------------------------------------------------------------

# Detector envelope is computed on `|dry|` decimated to roughly this rate
# before running the one-pole attack/release filter, which is an inherently
# sequential, data-dependent recursion (the coefficient switches per-sample
# based on whether the input is above or below the current envelope) and so
# cannot be vectorized with `scipy.signal.lfilter` (fixed-coefficient LTI
# only). Benchmarked: a plain Python loop processes 7.3M samples (166s of
# audio at 44.1kHz, the real vocal's full length) in ~3.05s; decimating to
# ~6kHz cuts that by the decimation factor before a multi-candidate
# attack/release grid search is run on top. 6kHz still resolves the fastest
# candidate attack (1ms) as ~6 decimated samples -- coarse but sufficient to
# discriminate between grid points that are themselves spaced apart.
_ENVELOPE_DECIMATE_TARGET_HZ = 6000.0

# Candidate grids for the attack/release search. Deliberately coarse (36
# combinations): this is a floor-proving harness, not a production tool, and
# a 166s real file multiplies every combination's cost.
_DEFAULT_ATTACK_CANDIDATES_MS: Tuple[float, ...] = (1.0, 2.0, 5.0, 10.0, 20.0, 40.0)
_DEFAULT_RELEASE_CANDIDATES_MS: Tuple[float, ...] = (10.0, 20.0, 50.0, 80.0, 150.0, 300.0)


def _decimate_for_envelope(x: np.ndarray, sr: float) -> Tuple[np.ndarray, float, int]:
    """Stride-decimate `x` toward `_ENVELOPE_DECIMATE_TARGET_HZ`.

    Plain stride decimation (no anti-alias low-pass) of what will become a
    rectified envelope-follower input -- not the raw waveform used for
    anything spectral -- is the standard cheap approximation real-time
    envelope followers use when running their detector at a reduced control
    rate; the one-pole filter applied afterward smooths whatever aliasing
    this introduces, and the target rate stays well above the 1-300ms time
    constants being searched.
    """
    dec = max(1, int(round(sr / _ENVELOPE_DECIMATE_TARGET_HZ)))
    return x[::dec], sr / dec, dec


def _one_pole_envelope_db(
    x_abs: np.ndarray, sr: float, attack_ms: float, release_ms: float, floor_db: float = -100.0
) -> np.ndarray:
    """Attack/release one-pole peak-envelope follower, in dB.

    `env[n] = a*env[n-1] + (1-a)*x[n]`, with `a` switched per-sample between
    an attack and a release coefficient depending on whether the input is
    above or below the current envelope -- the standard "ballistics" detector
    model used by hardware/software compressors. `a = exp(-1/(sr*t_s))` is the
    standard time-constant-to-coefficient conversion (t_s = attack_ms or
    release_ms in seconds): after `sr*t_s` samples (i.e. `t_s` seconds) the
    envelope has moved ~63% of the way to a step target, matching how
    `attack_ms`/`release_ms` are conventionally defined.

    This is a data-dependent switching recursion, not a fixed-coefficient LTI
    filter, so it cannot be vectorized with `scipy.signal.lfilter`. Written as
    a plain Python loop over a list (faster in practice than repeated numpy
    scalar indexing in a tight loop); callers decimate `x_abs` first to keep
    this affordable on multi-minute audio.
    """
    a_att = float(np.exp(-1.0 / (sr * max(attack_ms, 1e-3) / 1000.0)))
    a_rel = float(np.exp(-1.0 / (sr * max(release_ms, 1e-3) / 1000.0)))
    xl = x_abs.tolist()
    n = len(xl)
    out = [0.0] * n
    e = 0.0
    for i in range(n):
        xi = xl[i]
        if xi > e:
            e = a_att * e + (1.0 - a_att) * xi
        else:
            e = a_rel * e + (1.0 - a_rel) * xi
        out[i] = e
    env = np.asarray(out, dtype=np.float64)
    floor_lin = 10 ** (floor_db / 20.0)
    return 20.0 * np.log10(np.maximum(env, floor_lin))


def _hinge_fit(
    x_db: np.ndarray, y_db: np.ndarray, min_points_per_side: int
) -> Optional[Tuple[float, float, float, float, float, float]]:
    """Grid-search a 2-line hinge fit of `y_db` against `x_db` (0.5dB steps).

    Returns `(sse, T, slope_below, intercept_below, slope_above,
    intercept_above)` for the best split, or `None` if no split had enough
    points on both sides of any candidate.
    """
    lo, hi = np.percentile(x_db, [5.0, 95.0])
    if hi - lo < 1.0:
        return None
    candidates = np.arange(lo, hi, 0.5)
    best: Optional[Tuple[float, float, float, float, float, float]] = None
    for T in candidates:
        below = x_db <= T
        above = ~below
        if np.sum(below) < min_points_per_side or np.sum(above) < min_points_per_side:
            continue
        m1, c1 = np.polyfit(x_db[below], y_db[below], 1)
        m2, c2 = np.polyfit(x_db[above], y_db[above], 1)
        pred = np.where(below, m1 * x_db + c1, m2 * x_db + c2)
        sse = float(np.sum((y_db - pred) ** 2))
        if best is None or sse < best[0]:
            best = (sse, float(T), float(m1), float(c1), float(m2), float(c2))
    return best


def recover_compressor_gain_reduction(
    dry: np.ndarray,
    wet: np.ndarray,
    sr: float,
    attack_candidates_ms: Tuple[float, ...] = _DEFAULT_ATTACK_CANDIDATES_MS,
    release_candidates_ms: Tuple[float, ...] = _DEFAULT_RELEASE_CANDIDATES_MS,
    dry_floor_rel_db: float = -50.0,
    min_points_per_side: int = 200,
    convergence_ratio: float = 0.7,
) -> Dict[str, Recovery]:
    """Recover threshold/ratio/attack/release from instantaneous gain reduction.

    Sidesteps `recover_compressor`'s block-RMS assumption (only valid for
    quasi-static input) by using the directly observable per-sample gain: for
    a pure scalar-gain stage, `wet(t) = gain(t) * dry(t)` exactly, so
    `GR_db(t) = 20*log10(|wet(t)|/|dry(t)|)` *is* the instantaneous gain
    reduction (plus makeup gain, subtracted below) at every sample -- no
    averaging-window assumption required, and no information lost to framing.

    A compressor acts on an envelope follower's output, not the raw sample,
    so `GR_db(t)` is fit against a one-pole attack/release detector level
    built from `|dry|` (`_one_pole_envelope_db`), not against `dry(t)`
    itself. Below threshold the fitted curve should be flat (GR ~ 0dB); above
    it the slope is `1/ratio - 1`; the split point is the threshold -- this
    is the same 2-line hinge-fit shape as `recover_compressor`, just with a
    detector-level x-axis and an exact per-sample y-axis instead of block RMS
    on both axes.

    `attack_ms`/`release_ms` are recovered by grid search: for each candidate
    pair, build the envelope, hinge-fit GR vs envelope-level, and keep the
    pair with the lowest fit residual (SSE). If the SSE has no clear minimum
    across the grid (the best candidate is not meaningfully better than the
    grid's typical residual -- i.e. many different envelope shapes fit about
    equally well), attack/release are reported as unrecoverable. threshold_db
    and ratio may still be reported from the best-SSE candidate even then:
    a hinge's x-position and an above-hinge slope are position/shape
    quantities, materially less sensitive to a somewhat-mismatched envelope
    shape than the envelope shape itself is identifiable.
    """
    keys = ("threshold_db", "ratio", "attack_ms", "release_ms")
    method = "instantaneous_gr_envelope_hinge_fit"

    d, w = _align(dry, wet)
    if len(d) < 64:
        reason = f"signal too short for gain-reduction recovery ({len(d)} samples)"
        return {k: Recovery(None, None, method, reason=reason) for k in keys}

    # Makeup-gain confound: GR as measured below includes makeup gain (the
    # Chain DSL renders makeup as a separate Gain stage after the compressor,
    # so it is added to every sample of `wet` uniformly -- see
    # pedalboard_exec.build_pedalboard). `recover_compressor` already
    # measures makeup independently (median below-threshold y-x offset on
    # block RMS) and that measurement stays accurate even on real material
    # where its own threshold/ratio do not (see the D1 handoff's recovery
    # table) -- so it is reused here rather than re-derived. This subtraction
    # is a constant additive shift of the y-axis: the hinge's x-position
    # (threshold) and the above-hinge slope (ratio) are both invariant to a
    # constant y-offset, so even if makeup recovery had failed, threshold_db
    # and ratio below would be unaffected by falling back to 0.0 -- only the
    # "is the below-threshold segment really flat at 0dB" physical sanity
    # read would be off by the unknown makeup amount.
    makeup_rec = recover_compressor(d, w, sr)["makeup_db"]
    makeup_db = makeup_rec.value if makeup_rec.value is not None else 0.0

    dec_d, sr_d, dec = _decimate_for_envelope(d, sr)
    dec_w = w[::dec]
    n = min(len(dec_d), len(dec_w))
    dec_d, dec_w = dec_d[:n], dec_w[:n]

    dry_abs = np.abs(dec_d)
    peak = float(np.max(dry_abs)) if n > 0 else 0.0
    if peak <= 0.0:
        reason = "dry signal is silent after decimation -- no level to detect against"
        return {k: Recovery(None, None, method, reason=reason) for k in keys}

    floor_lin = peak * (10 ** (dry_floor_rel_db / 20.0))
    valid = dry_abs > floor_lin
    if int(np.sum(valid)) < 2 * min_points_per_side:
        reason = (
            f"only {int(np.sum(valid))} samples above the {dry_floor_rel_db}dB-below-peak floor "
            f"-- need >= {2 * min_points_per_side} to fit a two-line hinge"
        )
        return {k: Recovery(None, None, method, reason=reason) for k in keys}

    with np.errstate(divide="ignore", invalid="ignore"):
        raw_gr_db = 20.0 * np.log10(np.abs(dec_w[valid]) / dry_abs[valid])
    finite = np.isfinite(raw_gr_db)
    raw_gr_db = raw_gr_db[finite]
    if len(raw_gr_db) < 2 * min_points_per_side:
        reason = "too few finite instantaneous gain-reduction samples after masking near-zero/near-silent points"
        return {k: Recovery(None, None, method, reason=reason) for k in keys}
    gr_db = raw_gr_db - makeup_db
    valid_idx = np.flatnonzero(valid)[finite]

    results = []  # (sse, attack_ms, release_ms, T, m1, c1, m2, c2)
    for attack_ms in attack_candidates_ms:
        for release_ms in release_candidates_ms:
            env_db_full = _one_pole_envelope_db(dry_abs, sr_d, attack_ms, release_ms)
            env_db = env_db_full[valid_idx]
            fit = _hinge_fit(env_db, gr_db, min_points_per_side)
            if fit is None:
                continue
            sse, T, m1, c1, m2, c2 = fit
            results.append((sse, attack_ms, release_ms, T, m1, c1, m2, c2))

    if not results:
        reason = (
            "no (attack, release) candidate produced a valid two-line hinge fit -- "
            "input level range or point count insufficient at every candidate"
        )
        return {k: Recovery(None, None, method, reason=reason) for k in keys}

    results.sort(key=lambda r: r[0])
    best_sse, best_attack, best_release, T, m1, c1, m2, c2 = results[0]

    sst = float(np.sum((gr_db - np.mean(gr_db)) ** 2))
    r2 = float(np.clip(1.0 - best_sse / sst, 0.0, 1.0)) if sst > 1e-9 else 0.0

    result: Dict[str, Recovery] = {}

    # Same guard/rationale as recover_compressor: a hinge only exists if the
    # two fitted lines actually have different slopes.
    MIN_SLOPE_DIFFERENCE = 0.05
    slope_diff = abs(m2 - m1)
    if slope_diff < MIN_SLOPE_DIFFERENCE:
        reason = (
            f"best-fit GR/level curve is linear throughout (|slope_above - slope_below|={slope_diff:.4f} "
            f"< {MIN_SLOPE_DIFFERENCE}) at the best-fitting attack/release candidate -- no detectable hinge"
        )
        result["threshold_db"] = Recovery(None, None, method, reason=reason)
        result["ratio"] = Recovery(None, None, method, reason=reason)
    else:
        # Fit-quality guard. When the compressor spends little time engaged, the
        # above-threshold slope is fitted over too short a lever arm, the fit is
        # ill-conditioned, and the ratio collapses toward 1 -- which is
        # indistinguishable from genuine light compression unless something
        # refuses it.
        #
        # Measured on the 166 s real take (set ratio 4.0, att 5 ms, rel 80 ms):
        #   thr -24 -> ratio 3.878 (3% err),  r2 = 0.9951
        #   thr -18 -> ratio 1.543 (61% err), r2 = 0.7168
        # The vocal crosses -18 dB only 0.44% of the time (7.64 dB of span) versus
        # 5.17% and 13.64 dB at -24 dB. 0.90 sits between the two r2 values. It is
        # PROVISIONAL -- calibrated on one take at two thresholds -- and should be
        # revisited once more material has run. Stated plainly so the next reader
        # knows exactly how thin the evidence behind the constant is.
        #
        # A span-above-hinge guard was tried first and DOES NOT WORK: the hinge
        # search relocates the threshold to wherever the data actually is (it put
        # the -18 dB case at -23.1 dB), so the span measured above the *recovered*
        # hinge looks healthy in precisely the cases that failed. It never fired
        # on any of six cells. Recording the refuted approach so it is not retried.
        MIN_FIT_R2 = 0.90
        if r2 < MIN_FIT_R2:
            reason = (
                f"two-line fit quality r2={r2:.4f} is below {MIN_FIT_R2} -- the compressor is "
                "engaged over too little of this signal to constrain the above-threshold slope. "
                "The ratio this would report collapses toward 1, which reads as light "
                "compression rather than as a failed measurement."
            )
            result["threshold_db"] = Recovery(None, None, method, reason=reason)
            result["ratio"] = Recovery(None, None, method, reason=reason)
            result["attack_ms"] = Recovery(None, None, method, reason=reason)
            result["release_ms"] = Recovery(None, None, method, reason=reason)
            return result

        result["threshold_db"] = Recovery(T, r2, method)
        # GR_db = (1/ratio - 1) * (level_db - threshold_db) above threshold,
        # so the fitted slope m2 = 1/ratio - 1  =>  ratio = 1 / (1 + m2).
        denom = 1.0 + m2
        if denom > 1e-3:
            result["ratio"] = Recovery(float(1.0 / denom), r2, method)
        else:
            result["ratio"] = Recovery(
                None, None, method, reason=f"fitted above-threshold slope ({m2:.4f}) implies a non-positive ratio"
            )

    # Attack/release convergence check: is the best-SSE candidate meaningfully
    # better than the grid's typical residual, or is the residual ~flat
    # (many envelope shapes fit about as well, so the specific attack/release
    # pair is not actually identifiable from this data)?
    sses = np.array([r[0] for r in results], dtype=np.float64)
    median_sse = float(np.median(sses))

    # Boundary check, and it must come first. A monotone residual surface passes
    # the convergence test below (best IS meaningfully lower than median) while
    # its argmin sits on the edge of the grid -- which means the real minimum is
    # somewhere outside the grid and these time constants were never located.
    #
    # This is not hypothetical. On the 166 s real take, all six (ratio, threshold)
    # cells returned the exact bottom-left corner, attack=1.0/release=10.0, while
    # the truth was 5.0/80.0 -- both interior points of the candidate lists. Worse,
    # forcing the TRUE pair fit *worse* (ratio 2.817 vs 3.878 against a set 4.0),
    # proving the objective does not identify ballistics at all: fast coefficients
    # merely linearise the GR-vs-level relation better. Reporting the argmin would
    # be a grid artefact wearing the costume of a measurement.
    on_attack_edge = best_attack in (min(attack_candidates_ms), max(attack_candidates_ms))
    on_release_edge = best_release in (min(release_candidates_ms), max(release_candidates_ms))
    if on_attack_edge or on_release_edge:
        edges = []
        if on_attack_edge:
            edges.append(f"attack={best_attack:g}ms")
        if on_release_edge:
            edges.append(f"release={best_release:g}ms")
        reason = (
            f"best-fit ballistics sit on the candidate-grid boundary ({', '.join(edges)}) -- "
            "the residual minimum is outside the searched range, so the time constants are not "
            "located by this fit. Threshold/ratio from this candidate remain usable; the "
            "ballistics do not."
        )
        result["attack_ms"] = Recovery(None, None, method, reason=reason)
        result["release_ms"] = Recovery(None, None, method, reason=reason)
    elif median_sse <= 0.0 or best_sse >= convergence_ratio * median_sse:
        reason = (
            f"fit residual is not meaningfully lower at the best (attack, release) candidate than the grid "
            f"median (best={best_sse:.3f}, median={median_sse:.3f}) -- attack/release are not identifiable "
            "from this GR-vs-level fit"
        )
        result["attack_ms"] = Recovery(None, None, method, reason=reason)
        result["release_ms"] = Recovery(None, None, method, reason=reason)
    else:
        conv_conf = float(np.clip(1.0 - best_sse / (convergence_ratio * median_sse), 0.0, 1.0))
        result["attack_ms"] = Recovery(float(best_attack), conv_conf, method)
        result["release_ms"] = Recovery(float(best_release), conv_conf, method)

    return result


# ---------------------------------------------------------------------------
# Clipper drive
# ---------------------------------------------------------------------------


def recover_clipper_drive_db(
    dry: np.ndarray,
    wet: np.ndarray,
    min_abs_dry: float = 1e-3,
    max_abs_wet: float = 0.995,
    min_samples: int = 200,
) -> Recovery:
    """Invert pedalboard's documented Distortion model y = tanh(x * db_to_gain(drive_db)).

    Exact per-sample inversion: g = arctanh(y)/x, drive_db = 20*log10(median(g)).
    Only valid when `dry` is genuinely the clipper's input (no earlier active
    stage altered the signal first) -- see module docstring.
    """
    method = "tanh_waveshaper_inversion"
    d, w = _align(dry, wet)
    mask = (np.abs(d) > min_abs_dry) & (np.abs(w) < max_abs_wet)
    if int(np.sum(mask)) < min_samples:
        return Recovery(
            None,
            None,
            method,
            reason=f"only {int(np.sum(mask))} samples usable for inversion (need >= {min_samples}); "
            "signal may be too quiet, too heavily saturated, or not exercising the nonlinearity",
        )

    with np.errstate(invalid="ignore", divide="ignore"):
        g = np.arctanh(w[mask]) / d[mask]
    g = g[np.isfinite(g) & (g > 0)]
    if len(g) < min_samples // 4:
        return Recovery(None, None, method, reason="inversion produced too few finite positive gain estimates")

    g_med = float(np.median(g))
    if g_med <= 0:
        return Recovery(None, None, method, reason="median recovered gain is non-positive")

    drive_db = 20.0 * np.log10(g_med)
    mad = float(np.median(np.abs(g - g_med)))
    rel_spread = mad / g_med
    confidence = float(np.clip(1.0 - rel_spread * 5.0, 0.0, 1.0))
    return Recovery(drive_db, confidence, method)


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------


def extract_differential(dry: np.ndarray, wet: np.ndarray, sr: float) -> Dict[str, Any]:
    """Recover what can be recovered from a (dry, wet) pair, per parameter.

    Does not take a `Chain` -- it is blind to which stages were actually
    active. Every field is a `Recovery.to_dict()`; a field the method could
    not measure carries `value: None` and a `reason`, never a guessed number.
    """
    out: Dict[str, Any] = {}

    out["hpf_cutoff_hz"] = recover_hpf_cutoff_hz(dry, wet, sr).to_dict()

    eq_table = recover_eq_band_gains(dry, wet, sr)
    out["eq_band_gains_db"] = {
        f"{freq:g}Hz": rec.to_dict() for freq, rec in sorted(eq_table.items())
    }

    comp = recover_compressor(dry, wet, sr)
    out["comp_threshold_db"] = comp["threshold_db"].to_dict()
    out["comp_ratio"] = comp["ratio"].to_dict()
    out["comp_makeup_db"] = comp["makeup_db"].to_dict()

    # Gain-reduction-based recovery (see recover_compressor_gain_reduction):
    # a second, independent measurement of the same threshold/ratio, plus
    # attack/release which the block-RMS method above cannot reach at all.
    # New keys only -- comp_threshold_db/comp_ratio/comp_makeup_db above are
    # untouched, so this does not change extract_differential's existing
    # output contract.
    comp_gr = recover_compressor_gain_reduction(dry, wet, sr)
    out["comp_threshold_db_gr"] = comp_gr["threshold_db"].to_dict()
    out["comp_ratio_gr"] = comp_gr["ratio"].to_dict()
    out["comp_attack_ms"] = comp_gr["attack_ms"].to_dict()
    out["comp_release_ms"] = comp_gr["release_ms"].to_dict()

    out["clip_drive_db"] = recover_clipper_drive_db(dry, wet).to_dict()

    return out
