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
- **Compressor threshold/ratio** -- per-frame RMS-in vs RMS-out (dB), grid
  search over a hinge point, two independent least-squares line fits either
  side of it. `threshold_db` is the hinge x-position; `ratio` is `1/slope`
  of the above-hinge line. This assumes a hard knee (no soft-knee rounding),
  which matches the installed pedalboard_exec (it does not honour
  `Compressor.knee_db` -- see `tests/test_chain_dsl_unwired_params.py`).
- **Compressor makeup gain** -- the median `y_db - x_db` offset for frames
  well below the recovered threshold (where gain should be unity + makeup).
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

    out["clip_drive_db"] = recover_clipper_drive_db(dry, wet).to_dict()

    return out
