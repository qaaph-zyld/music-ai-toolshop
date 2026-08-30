"""Premaster acceptance profile (H2-M4, CHANGELOG #050).

Measures a track against `mastering_tool/PREMASTER_ACCEPTANCE_SPEC.md` v1.0 and
reports PASS / FLAG / FAIL per gate, so the dossier can say whether material is
fit to master *before* the irreversible loudness stage.

**Why this lives in the dossier.** The spec's own premise is that the largest
measurable gap to commercial releases is not in the mastering chain but in the
material arriving at it — phase coherence and micro-dynamics are mix properties
that mastering can attenuate but never restore. The dossier previously carried
only `spectral_centroid`, `spectral_bandwidth` and `harmonic_ratio`: none of the
six measurable gates.

**Measurement honesty.**

* Gates 1-2 need **stereo**. On a mono file they are reported ``None`` with a
  reason, never silently passed — a mono file has no phase relationship to fail.
* **True peak is approximated** by 4x polyphase upsampling. That is the standard
  cheap approximation, not a certified ITU-R BS.1770-4 TP meter, and the field is
  named and documented accordingly.
* Gate 7 (declared provenance) is a manual/lossless-ancestry check with no signal
  correlate. It is reported as ``manual`` rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

PASS = "PASS"
FLAG = "FLAG"
FAIL = "FAIL"
NOT_MEASURED = "NOT_MEASURED"

#: Low-band split for the bass mono-coherence gate.
LOW_BAND_HZ = 120.0
#: Oversampling factor for the true-peak approximation.
TP_OVERSAMPLE = 4


@dataclass
class GateResult:
    """One gate from the acceptance spec."""

    number: int
    name: str
    value: Optional[float]
    verdict: str
    threshold: str
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate": self.number,
            "name": self.name,
            "value": None if self.value is None else round(float(self.value), 4),
            "verdict": self.verdict,
            "threshold": self.threshold,
            "note": self.note,
        }


def _grade(value: float, pass_at: float, fail_at: float, higher_is_better: bool) -> str:
    """PASS / FLAG / FAIL against the spec's two thresholds."""
    if higher_is_better:
        if value >= pass_at:
            return PASS
        return FLAG if value >= fail_at else FAIL
    if value <= pass_at:
        return PASS
    return FLAG if value <= fail_at else FAIL


def _windowed_correlation(left: np.ndarray, right: np.ndarray, sr: int, window_s: float = 0.4):
    """L/R correlation per window. Returns an array of coefficients."""
    n = max(1, int(sr * window_s))
    out: List[float] = []
    for start in range(0, min(len(left), len(right)) - n + 1, n):
        a = left[start : start + n]
        b = right[start : start + n]
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        out.append(float(np.dot(a, b) / denom) if denom > 0 else 0.0)
    return np.asarray(out) if out else np.asarray([0.0])


def _lowpass(x: np.ndarray, sr: int, cutoff: float = LOW_BAND_HZ) -> np.ndarray:
    from scipy.signal import butter, sosfiltfilt

    sos = butter(4, cutoff / (sr / 2.0), btype="low", output="sos")
    return sosfiltfilt(sos, x)


def true_peak_dbfs(y: np.ndarray, oversample: int = TP_OVERSAMPLE) -> float:
    """Approximate true peak in dBFS via polyphase upsampling.

    Not a certified BS.1770-4 meter — an inter-sample-peak estimate, which is why
    the output field is called ``true_peak_dbfs_approx``.
    """
    from scipy.signal import resample_poly

    if y.size == 0:
        return -np.inf
    up = resample_poly(y, oversample, 1)
    peak = float(np.max(np.abs(up)))
    return 20.0 * np.log10(peak) if peak > 0 else -np.inf


def analyze_premaster(path: Path) -> Dict[str, Any]:
    """Measure a file against the premaster acceptance gates."""
    import soundfile as sf
    import pyloudnorm as pyln

    path = Path(path)
    data, sr = sf.read(str(path), always_2d=True)
    n_channels = data.shape[1]
    mono = data.mean(axis=1)

    gates: List[GateResult] = []

    # --- Gates 1 & 2: phase coherence (stereo only) -------------------------
    if n_channels >= 2:
        left, right = data[:, 0], data[:, 1]
        full = _windowed_correlation(left, right, sr)
        corr_min = float(full.min())
        gates.append(GateResult(
            1, "full_band_corr_min", corr_min,
            _grade(corr_min, -0.20, -0.50, higher_is_better=True),
            ">= -0.20 pass, -0.50..-0.20 flag, < -0.50 fail",
        ))
        low = _windowed_correlation(_lowpass(left, sr), _lowpass(right, sr), sr)
        low_mean = float(low.mean())
        gates.append(GateResult(
            2, "low_band_corr_mean", low_mean,
            _grade(low_mean, 0.70, 0.40, higher_is_better=True),
            ">= +0.70 pass, +0.40..+0.70 flag, < +0.40 fail",
            note=f"<{LOW_BAND_HZ:.0f} Hz",
        ))
    else:
        for num, name in ((1, "full_band_corr_min"), (2, "low_band_corr_mean")):
            gates.append(GateResult(
                num, name, None, NOT_MEASURED, "stereo required",
                note="mono input has no L/R phase relationship to measure",
            ))

    # --- Gate 3: sample peak headroom ---------------------------------------
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    peak_dbfs = 20.0 * np.log10(peak) if peak > 0 else -np.inf
    gates.append(GateResult(
        3, "sample_peak_dbfs", peak_dbfs,
        _grade(peak_dbfs, -3.0, 0.0, higher_is_better=False),
        "<= -3.0 dBFS pass, -3.0..0 flag, >= 0 fail (clipped)",
    ))

    # --- Gate 4: crest factor (peak - RMS) ----------------------------------
    rms = float(np.sqrt(np.mean(mono**2))) if mono.size else 0.0
    rms_db = 20.0 * np.log10(rms) if rms > 0 else -np.inf
    crest = peak_dbfs - rms_db if np.isfinite(peak_dbfs) and np.isfinite(rms_db) else 0.0
    gates.append(GateResult(
        4, "crest_factor_db", crest,
        _grade(crest, 12.0, 9.0, higher_is_better=True),
        ">= 12 dB pass, 9..12 flag, < 9 fail",
    ))

    # --- Gate 5: PSR = true peak - max short-term loudness -------------------
    meter = pyln.Meter(sr)
    integrated = float(meter.integrated_loudness(data if n_channels > 1 else mono))
    tp = true_peak_dbfs(mono)

    # Max short-term (3 s windows, 1 s hop) per BS.1770 short-term convention.
    win, hop = int(sr * 3.0), int(sr * 1.0)
    st_values: List[float] = []
    if mono.size >= win:
        for start in range(0, mono.size - win + 1, hop):
            block = data[start : start + win] if n_channels > 1 else mono[start : start + win]
            try:
                val = float(meter.integrated_loudness(block))
                if np.isfinite(val):
                    st_values.append(val)
            except Exception:
                continue
    max_st = max(st_values) if st_values else integrated
    psr = tp - max_st if np.isfinite(tp) and np.isfinite(max_st) else 0.0
    gates.append(GateResult(
        5, "psr_db", psr,
        _grade(psr, 11.0, 8.0, higher_is_better=True),
        ">= 11 dB pass, 8..11 flag, < 8 fail",
        note="true peak approximated by 4x oversampling",
    ))

    # --- Gate 6: DC offset ---------------------------------------------------
    dc = float(np.abs(np.mean(mono))) if mono.size else 0.0
    gates.append(GateResult(
        6, "dc_offset", dc,
        _grade(dc, 0.001, 0.005, higher_is_better=False),
        "< 0.001 pass, 0.001..0.005 flag, >= 0.005 fail",
    ))

    # --- Gate 7: provenance (manual) ----------------------------------------
    gates.append(GateResult(
        7, "declared_provenance", None, NOT_MEASURED,
        "sr/bits stated, lossless ancestry",
        note="manual check - no signal correlate; verify the file's ancestry by hand",
    ))

    measured = [g for g in gates if g.verdict in (PASS, FLAG, FAIL)]
    fails = [g for g in measured if g.verdict == FAIL]
    flags = [g for g in measured if g.verdict == FLAG]
    overall = FAIL if fails else (FLAG if flags else PASS)

    return {
        "file": str(path),
        "sample_rate": sr,
        "channels": n_channels,
        "integrated_lufs": round(integrated, 2) if np.isfinite(integrated) else None,
        "true_peak_dbfs_approx": round(tp, 2) if np.isfinite(tp) else None,
        "max_short_term_lufs": round(max_st, 2) if np.isfinite(max_st) else None,
        "gates": [g.to_dict() for g in gates],
        "verdict": overall,
        "failing_gates": [g.name for g in fails],
        "flagged_gates": [g.name for g in flags],
        "spec": "mastering_tool/PREMASTER_ACCEPTANCE_SPEC.md v1.0",
    }
