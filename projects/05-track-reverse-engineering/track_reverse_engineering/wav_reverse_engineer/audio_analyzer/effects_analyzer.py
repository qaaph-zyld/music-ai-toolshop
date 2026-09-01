import os
import numpy as np
import librosa
from typing import Dict, Any
from scipy.signal import find_peaks

try:
    import pyloudnorm as pyln
except Exception:
    pyln = None


def _short_term_rms(x: np.ndarray, frame_samples: int, hop_samples: int) -> np.ndarray:
    if len(x) < frame_samples:
        return np.array([])
    frames = []
    for i in range(0, len(x) - frame_samples + 1, hop_samples):
        frames.append(np.sqrt(np.mean(x[i:i+frame_samples] ** 2)))
    return np.asarray(frames)


# --- RT60 ---------------------------------------------------------------------
#
# WHAT WAS WRONG (fixed 2026-09-01, CHANGELOG #056, JOURNAL.md J-063).
#
# The previous implementation ran Schroeder backward-integration over the WHOLE
# TRACK. Schroeder's method measures the decay of an impulse response; a song is
# not one. On continuous audio the energy-decay curve is dominated by "how much
# of the file is left", so the fitted slope is set by the file's DURATION and the
# result is a fixed multiple of it.
#
# Measured on the 221-dossier corpus: `rt60_seconds` correlated **r = 0.946**
# with `duration_seconds`, median **200.1 s** and median ratio **1.18x**. A
# reverb tail longer than the song is not a marginal error.
#
# Minimal reproduction - steady white noise, which has no reverb whatsoever:
#     10 s -> 14.78 s     20 s -> 29.40 s     40 s -> 58.85 s   (ratio 1.47x)
#
# It survived because the only test asserted `'rt60_seconds' in res` - a presence
# check that passes on any number - and it lived outside `pytest.ini`'s
# `testpaths`, so it never ran either.
#
# WHAT IT DOES NOW. RT60 is only meaningful where something actually decays, so
# it is measured on short windows following onsets and refused when no window
# qualifies. `None` means "not measurable here", which is the honest answer for
# a dense mix - the same convention `toolshop/premaster.py` uses for gates it
# cannot measure.

#: Plausible band for a musical reverb tail. Outside it, the fit is measuring
#: something other than a room.
MIN_RT60_SECONDS = 0.05
MAX_RT60_SECONDS = 3.0

#: Decay windows needed before a median is reported. One clean decay in a whole
#: track is as likely to be an artefact as a measurement.
MIN_DECAY_WINDOWS = 4

#: Schroeder fit range. Narrower than the classic -5..-35 dB because these are
#: short post-onset windows inside music, not an anechoic impulse response.
_FIT_LO_DB = -5.0
_FIT_HI_DB = -25.0

#: The fit must finish comfortably before the window ends. If the -25 dB
#: crossing only happens in the last tenth, the "decay" being measured is the
#: window running out of samples - which is the original bug in miniature.
_MAX_FIT_END_FRACTION = 0.9

#: A true Schroeder decay is close to a straight line in dB. Non-decaying audio
#: gives a curve, so goodness-of-fit is what separates them.
_MIN_FIT_R2 = 0.98


def _schroeder_rt60(segment: np.ndarray, sr: int) -> float:
    """RT60 for one candidate decay window, or `nan` if it does not decay."""
    if segment.size < int(0.05 * sr):
        return float("nan")

    energy = np.asarray(segment, dtype=np.float64) ** 2
    edc = np.flip(np.cumsum(np.flip(energy)))
    if edc[0] <= 0.0:
        return float("nan")

    edc_db = 10.0 * np.log10(edc + 1e-20)
    edc_db -= edc_db[0]

    lo = np.flatnonzero(edc_db <= _FIT_LO_DB)
    hi = np.flatnonzero(edc_db <= _FIT_HI_DB)
    if lo.size == 0 or hi.size == 0:
        return float("nan")

    i0, i1 = int(lo[0]), int(hi[0])
    if i1 - i0 < int(0.01 * sr):
        return float("nan")
    if i1 > _MAX_FIT_END_FRACTION * segment.size:
        # Truncation, not decay. This is the guard the old code lacked.
        return float("nan")

    x = np.arange(i0, i1, dtype=np.float64) / sr
    y_db = edc_db[i0:i1]
    m, c = np.polyfit(x, y_db, 1)
    if m >= 0.0:
        return float("nan")

    residual = y_db - (m * x + c)
    ss_res = float(np.sum(residual ** 2))
    ss_tot = float(np.sum((y_db - np.mean(y_db)) ** 2))
    if ss_tot <= 0.0 or (1.0 - ss_res / ss_tot) < _MIN_FIT_R2:
        return float("nan")

    return float(-60.0 / m)


def estimate_rt60_detailed(audio: np.ndarray, sr: int) -> Dict[str, Any]:
    """Reverb decay from post-onset windows, with the evidence behind it.

    Returns `rt60_seconds=None` and a `reason` when the signal offers nothing to
    measure, rather than returning a number that is really the track length.
    """
    y = np.asarray(audio, dtype=np.float64)
    if y.size < sr // 2:
        return {"rt60_seconds": None, "rt60_windows": 0,
                "rt60_reason": "signal shorter than 0.5 s"}
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    if peak <= 0.0:
        return {"rt60_seconds": None, "rt60_windows": 0,
                "rt60_reason": "silent signal"}
    y = y / peak

    try:
        onsets = librosa.onset.onset_detect(
            y=y.astype(np.float32), sr=sr, units="samples", backtrack=True
        )
    except Exception:
        onsets = np.array([], dtype=int)
    if len(onsets) < 2:
        return {"rt60_seconds": None, "rt60_windows": 0,
                "rt60_reason": "no onsets to measure a decay from"}

    max_window = int(1.5 * sr)
    estimates = []
    for start, nxt in zip(onsets[:-1], onsets[1:]):
        end = min(int(start) + max_window, int(nxt))
        rt = _schroeder_rt60(y[int(start):end], sr)
        if np.isfinite(rt) and MIN_RT60_SECONDS <= rt <= MAX_RT60_SECONDS:
            estimates.append(rt)

    if len(estimates) < MIN_DECAY_WINDOWS:
        return {
            "rt60_seconds": None,
            "rt60_windows": len(estimates),
            "rt60_reason": (
                f"only {len(estimates)} usable decay window(s); "
                f"{MIN_DECAY_WINDOWS} required. Dense or heavily compressed "
                f"material often never decays far enough to measure."
            ),
        }

    return {
        "rt60_seconds": float(np.median(estimates)),
        "rt60_windows": len(estimates),
        "rt60_reason": "median of post-onset Schroeder fits",
    }


def estimate_rt60(audio: np.ndarray, sr: int) -> Any:
    """Reverb decay in seconds, or **None** when it cannot be measured.

    Returns `None` rather than `0.0` for the unmeasurable case: 0.0 is a
    plausible-looking value that a caller will happily average.
    """
    return estimate_rt60_detailed(audio, sr)["rt60_seconds"]


def spectral_tilt(audio: np.ndarray, sr: int) -> float:
    S = np.abs(librosa.stft(audio, n_fft=4096, hop_length=1024))
    mag = np.mean(S, axis=1) + 1e-12
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    x = np.log10(freqs[1:])
    y = 20 * np.log10(mag[1:])
    A = np.vstack([x, np.ones_like(x)]).T
    m, _ = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(m)


def harmonic_distortion(audio: np.ndarray, sr: int) -> float:
    S = np.abs(librosa.stft(audio, n_fft=8192, hop_length=2048))
    spec = np.mean(S, axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=8192)
    idx_peak = np.argmax(spec[1:]) + 1
    f0 = freqs[idx_peak]
    if f0 <= 20:
        return 0.0
    harmonics = []
    for k in [2, 3, 4, 5]:
        fk = k * f0
        if fk >= sr / 2:
            break
        idx = np.argmin(np.abs(freqs - fk))
        harmonics.append(spec[idx])
    if not harmonics:
        return 0.0
    thd = np.sqrt(np.sum(np.square(harmonics))) / (spec[idx_peak] + 1e-9)
    return float(thd)


def compression_index(audio: np.ndarray, sr: int) -> float:
    frame = int(0.1 * sr)
    hop = int(0.05 * sr)
    rms = _short_term_rms(audio, frame, hop)
    if rms.size == 0:
        return 0.0
    peak = np.max(np.abs(audio)) + 1e-9
    crest = peak / (np.mean(rms) + 1e-9)
    var = float(np.var(rms))
    idx = float(1.0 / (crest + 1e-9)) * (1.0 / (var + 1e-6))
    return idx


def loudness_metrics(audio: np.ndarray, sr: int) -> Dict[str, float]:
    if pyln is None:
        return {}
    # Ensure correct dtype for pyloudnorm
    y = np.asarray(audio, dtype=np.float64)
    meter = pyln.Meter(sr)
    loudness = float(meter.integrated_loudness(y))
    lra = None
    # Some pyloudnorm versions don't expose Meter.loudness_range
    if hasattr(meter, "loudness_range"):
        try:
            lra = float(meter.loudness_range(y))
        except Exception:
            lra = None
    # Try module-level loudness_range/lra if available
    if lra is None:
        try:
            from pyloudnorm import loudness as _pln_loud
            if hasattr(_pln_loud, "loudness_range"):
                lra = float(_pln_loud.loudness_range(y, sr))
            elif hasattr(_pln_loud, "lra"):
                lra = float(_pln_loud.lra(y, sr))
        except Exception:
            lra = None
    # Fallback: approximate LRA from short-term RMS distribution (3s windows)
    if lra is None:
        win = int(3.0 * sr)
        hop = int(1.0 * sr)
        st_rms = _short_term_rms(y, win, hop)
        if st_rms.size > 0:
            st_db = 20.0 * np.log10(st_rms + 1e-12)
            p95 = float(np.percentile(st_db, 95))
            p10 = float(np.percentile(st_db, 10))
            lra = max(p95 - p10, 0.0)
        else:
            lra = 0.0
    return {"loudness_lufs": loudness, "loudness_range": float(lra)}


def analyze_effects(audio: np.ndarray, sr: int) -> Dict[str, Any]:
    rt60 = estimate_rt60_detailed(audio, sr)
    tilt = spectral_tilt(audio, sr)
    thd = harmonic_distortion(audio, sr)
    comp = compression_index(audio, sr)
    loud = loudness_metrics(audio, sr)
    out = {
        # `rt60_seconds` may be None - see the RT60 section above. The window
        # count and reason travel with it so a reader can tell "no reverb
        # measurable" from "not attempted", which a bare number cannot express.
        "spectral_tilt_db_per_decade": tilt,
        "thd_ratio": thd,
        "compression_index": comp,
    }
    out.update(rt60)
    out.update(loud)
    return out
