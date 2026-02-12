"""Voice effects detection adapter.

Analyzes an audio file to detect what vocal effects and processing
were likely applied. Uses only free/open-source libraries:
  - librosa (spectral analysis, MFCCs, pitch)
  - numpy / scipy (signal processing, stats)
  - parselmouth (Praat wrapper - formant analysis, voice quality)
  - crepe (neural pitch detection - optional, enhances pitch-shift detection)

All detectors are heuristic/statistical — no ML training required.
Missing optional deps degrade gracefully (detector is skipped).
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
try:
    import librosa
    import numpy as np
    from scipy import signal as scipy_signal
    from scipy.stats import kurtosis as scipy_kurtosis

    _HAS_LIBROSA = True
except ImportError:
    _HAS_LIBROSA = False

try:
    import parselmouth
    from parselmouth.praat import call as praat_call

    _HAS_PARSELMOUTH = True
except ImportError:
    _HAS_PARSELMOUTH = False

try:
    import crepe

    _HAS_CREPE = True
except ImportError:
    _HAS_CREPE = False


def _require_librosa() -> None:
    if not _HAS_LIBROSA:
        raise RuntimeError(
            "librosa, numpy, and scipy are required for voice analysis. "
            "Install with: pip install librosa numpy scipy"
        )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _load_audio(path: Path, sr: int = 22050) -> Tuple[Any, int]:
    """Load audio as mono float32 via librosa."""
    _require_librosa()
    y, sr_out = librosa.load(str(path), sr=sr, mono=True)
    return y, sr_out


def _rms_envelope(y: Any, frame_length: int = 2048, hop_length: int = 512) -> Any:
    """Compute RMS energy envelope."""
    return librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]


def _db(x: float, ref: float = 1.0) -> float:
    """Convert amplitude ratio to dB."""
    return 20.0 * np.log10(max(x, 1e-10) / ref)


# ---------------------------------------------------------------------------
# Individual effect detectors
# ---------------------------------------------------------------------------

def detect_reverb(y: Any, sr: int) -> Dict[str, Any]:
    """Detect reverb by analysing energy decay and spectral smearing.

    Approach:
      1. Compute energy decay curve from the tail of the signal.
      2. Estimate RT60 (time for 60dB decay) from the slope.
      3. Measure spectral temporal smearing via autocorrelation width.
    """
    result: Dict[str, Any] = {"effect": "reverb", "confidence": 0.0, "params": {}, "evidence": []}

    # Energy envelope
    rms = _rms_envelope(y, frame_length=2048, hop_length=512)
    rms_db = 20.0 * np.log10(rms + 1e-10)

    # Find the last loud segment and measure its decay
    threshold = np.max(rms_db) - 10  # 10dB below peak
    loud_frames = np.where(rms_db > threshold)[0]
    if len(loud_frames) == 0:
        return result

    last_loud = loud_frames[-1]
    decay_region = rms_db[last_loud:]
    if len(decay_region) < 10:
        # Try a different approach: look at average decay after transients
        # Segment the signal into chunks and measure average decay tails
        chunk_size = sr  # 1 second chunks
        hop = sr // 2
        decay_times = []
        for start in range(0, len(y) - chunk_size, hop):
            chunk = y[start : start + chunk_size]
            chunk_rms = _rms_envelope(chunk, frame_length=512, hop_length=128)
            chunk_db = 20.0 * np.log10(chunk_rms + 1e-10)
            peak_idx = np.argmax(chunk_db)
            tail = chunk_db[peak_idx:]
            if len(tail) > 5:
                # Linear fit to decay
                x_axis = np.arange(len(tail))
                if np.std(tail) > 0:
                    coeffs = np.polyfit(x_axis, tail, 1)
                    slope = coeffs[0]  # dB per frame
                    if slope < -0.01:
                        frames_per_sec = sr / 128
                        rt60_est = -60.0 / (slope * frames_per_sec)
                        if 0.05 < rt60_est < 10.0:
                            decay_times.append(rt60_est)
        if decay_times:
            median_rt60 = float(np.median(decay_times))
            result["params"]["estimated_rt60_seconds"] = round(median_rt60, 3)
            if median_rt60 > 0.5:
                result["confidence"] = min(0.95, 0.4 + median_rt60 * 0.3)
                result["evidence"].append(
                    f"Median RT60 estimate: {median_rt60:.2f}s across {len(decay_times)} segments"
                )
            elif median_rt60 > 0.15:
                result["confidence"] = 0.3
                result["evidence"].append(f"Short reverb tail: {median_rt60:.2f}s")
        return result

    # Linear regression on decay curve
    x_axis = np.arange(len(decay_region))
    coeffs = np.polyfit(x_axis, decay_region, 1)
    slope = coeffs[0]  # dB per frame

    frames_per_sec = sr / 512
    if slope < -0.001:
        rt60 = -60.0 / (slope * frames_per_sec)
        rt60 = max(0.0, min(rt60, 15.0))  # Clamp
        result["params"]["estimated_rt60_seconds"] = round(rt60, 3)

        if rt60 > 1.5:
            result["confidence"] = min(0.95, 0.5 + (rt60 - 1.5) * 0.15)
            result["params"]["type"] = "hall" if rt60 > 3.0 else "room"
            result["evidence"].append(f"Energy decay RT60 ~ {rt60:.2f}s")
        elif rt60 > 0.5:
            result["confidence"] = 0.3 + (rt60 - 0.5) * 0.2
            result["params"]["type"] = "room"
            result["evidence"].append(f"Moderate energy decay: RT60 ~ {rt60:.2f}s")
        else:
            result["confidence"] = max(0.1, rt60 * 0.4)
            result["evidence"].append(f"Minimal decay tail: RT60 ~ {rt60:.2f}s")

    # Spectral smearing: compare spectral flux in high freqs
    S = np.abs(librosa.stft(y))
    high_band = S[S.shape[0] // 2 :, :]  # Upper half of spectrum
    spectral_flux = np.mean(np.diff(high_band, axis=1) ** 2)
    if spectral_flux < 0.001:
        result["confidence"] = min(1.0, result["confidence"] + 0.15)
        result["evidence"].append("Low spectral flux in high frequencies (smearing)")

    return result


def detect_pitch_shift(y: Any, sr: int) -> Dict[str, Any]:
    """Detect pitch shifting by comparing F0 with formant positions.

    Natural voice: formants scale with vocal tract length, not with pitch.
    Pitch-shifted voice: F0 moves but formants either stay (PSOLA) or
    shift together (naive resampling).
    """
    result: Dict[str, Any] = {"effect": "pitch_shift", "confidence": 0.0, "params": {}, "evidence": []}

    # Get F0 via crepe (preferred) or librosa
    if _HAS_CREPE:
        try:
            import soundfile as sf
            # crepe needs the raw audio at original SR
            y_22k = y
            sr_crepe = sr
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _, frequency, confidence, _ = crepe.predict(
                    y_22k, sr_crepe, viterbi=True, step_size=10
                )
            # Filter low-confidence frames
            mask = confidence > 0.5
            if np.sum(mask) < 5:
                return result
            f0_values = frequency[mask]
            f0_median = float(np.median(f0_values))
        except Exception:
            f0_median = _librosa_f0(y, sr)
    else:
        f0_median = _librosa_f0(y, sr)

    if f0_median is None or f0_median < 50:
        return result

    result["params"]["detected_f0_hz"] = round(f0_median, 1)

    # Get formants via parselmouth
    if _HAS_PARSELMOUTH:
        formants = _get_formants_parselmouth(y, sr)
        if formants and formants.get("F1") and formants.get("F2"):
            f1 = formants["F1"]
            f2 = formants["F2"]
            result["params"]["formants"] = formants

            # Expected F0 range based on formant spacing
            # Male: F1~500-700, F2~1000-1400, F0~85-180
            # Female: F1~600-900, F2~1200-1800, F0~165-255
            # If F0 is way outside expected range for the formant pattern, likely shifted
            expected_f0_low, expected_f0_high = _estimate_f0_range_from_formants(f1, f2)
            result["params"]["expected_f0_range"] = [round(expected_f0_low, 1), round(expected_f0_high, 1)]

            if f0_median < expected_f0_low * 0.75:
                shift_semitones = 12 * np.log2(expected_f0_low / f0_median)
                result["confidence"] = min(0.95, 0.5 + shift_semitones * 0.08)
                result["params"]["estimated_semitones"] = f"-{round(shift_semitones, 1)}"
                result["evidence"].append(
                    f"F0 ({f0_median:.0f}Hz) below expected range "
                    f"({expected_f0_low:.0f}-{expected_f0_high:.0f}Hz) for detected formants"
                )
            elif f0_median > expected_f0_high * 1.25:
                shift_semitones = 12 * np.log2(f0_median / expected_f0_high)
                result["confidence"] = min(0.95, 0.5 + shift_semitones * 0.08)
                result["params"]["estimated_semitones"] = f"+{round(shift_semitones, 1)}"
                result["evidence"].append(
                    f"F0 ({f0_median:.0f}Hz) above expected range "
                    f"({expected_f0_low:.0f}-{expected_f0_high:.0f}Hz) for detected formants"
                )
            else:
                result["confidence"] = 0.05
                result["evidence"].append("F0-formant relationship appears natural")
    else:
        result["evidence"].append("parselmouth not installed — formant comparison skipped")

    return result


def _librosa_f0(y: Any, sr: int) -> Optional[float]:
    """Estimate median F0 using librosa's pyin."""
    try:
        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=50, fmax=600, sr=sr
        )
        voiced = f0[voiced_flag]
        if len(voiced) < 5:
            return None
        return float(np.median(voiced))
    except Exception:
        return None


def _get_formants_parselmouth(y: Any, sr: int) -> Dict[str, float]:
    """Extract median formant frequencies using parselmouth (Praat)."""
    try:
        snd = parselmouth.Sound(y, sampling_frequency=sr)
        formant = praat_call(snd, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
        n_frames = praat_call(formant, "Get number of frames")

        f1_vals, f2_vals, f3_vals = [], [], []
        for i in range(1, int(n_frames) + 1):
            f1 = praat_call(formant, "Get value at time", 1, praat_call(formant, "Get time from frame number", i), "hertz", "Linear")
            f2 = praat_call(formant, "Get value at time", 2, praat_call(formant, "Get time from frame number", i), "hertz", "Linear")
            f3 = praat_call(formant, "Get value at time", 3, praat_call(formant, "Get time from frame number", i), "hertz", "Linear")
            if f1 and not np.isnan(f1) and 200 < f1 < 1200:
                f1_vals.append(f1)
            if f2 and not np.isnan(f2) and 600 < f2 < 3500:
                f2_vals.append(f2)
            if f3 and not np.isnan(f3) and 1500 < f3 < 5000:
                f3_vals.append(f3)

        result = {}
        if f1_vals:
            result["F1"] = round(float(np.median(f1_vals)), 1)
        if f2_vals:
            result["F2"] = round(float(np.median(f2_vals)), 1)
        if f3_vals:
            result["F3"] = round(float(np.median(f3_vals)), 1)
        return result
    except Exception:
        return {}


def _estimate_f0_range_from_formants(f1: float, f2: float) -> Tuple[float, float]:
    """Heuristic: estimate plausible F0 range from formant positions.

    Lower formants → larger vocal tract → lower expected F0.
    """
    # Rough mapping based on vocal tract length estimation
    # vtl ~ c / (4 * F1) where c ~ 34000 cm/s
    vtl_estimate = 34000 / (4 * f1)  # cm

    # Male vtl ~17cm (F0 85-180), Female vtl ~14cm (F0 165-255), Child ~10cm
    if vtl_estimate > 16:
        return (75.0, 190.0)
    elif vtl_estimate > 13:
        return (150.0, 270.0)
    else:
        return (200.0, 400.0)


def detect_formant_shift(y: Any, sr: int) -> Dict[str, Any]:
    """Detect formant shifting — formants moved independently of pitch.

    Formant-shifted voice has formant ratios that deviate from natural
    F1/F2/F3 spacing patterns.
    """
    result: Dict[str, Any] = {"effect": "formant_shift", "confidence": 0.0, "params": {}, "evidence": []}

    if not _HAS_PARSELMOUTH:
        result["evidence"].append("parselmouth not installed — cannot detect formant shift")
        return result

    formants = _get_formants_parselmouth(y, sr)
    if not formants.get("F1") or not formants.get("F2"):
        result["evidence"].append("Could not extract formants reliably")
        return result

    f1, f2 = formants["F1"], formants["F2"]
    f3 = formants.get("F3")

    # Natural F2/F1 ratio typically 1.5-2.5 for speech vowels
    ratio_f2_f1 = f2 / f1
    result["params"]["F2_F1_ratio"] = round(ratio_f2_f1, 2)

    anomaly_score = 0.0
    if ratio_f2_f1 < 1.2 or ratio_f2_f1 > 3.2:
        anomaly_score += 0.4
        result["evidence"].append(f"Unusual F2/F1 ratio: {ratio_f2_f1:.2f} (normal: 1.5-2.5)")

    if f3:
        ratio_f3_f2 = f3 / f2
        result["params"]["F3_F2_ratio"] = round(ratio_f3_f2, 2)
        # Natural F3/F2 ratio typically 1.2-1.8
        if ratio_f3_f2 < 1.0 or ratio_f3_f2 > 2.2:
            anomaly_score += 0.3
            result["evidence"].append(f"Unusual F3/F2 ratio: {ratio_f3_f2:.2f} (normal: 1.2-1.8)")

    # Check if formants are unnaturally uniform across time
    try:
        snd = parselmouth.Sound(y, sampling_frequency=sr)
        formant_obj = praat_call(snd, "To Formant (burg)", 0.0, 5, 5500, 0.025, 50)
        n_frames = praat_call(formant_obj, "Get number of frames")

        f1_series = []
        for i in range(1, min(int(n_frames) + 1, 200)):
            t = praat_call(formant_obj, "Get time from frame number", i)
            val = praat_call(formant_obj, "Get value at time", 1, t, "hertz", "Linear")
            if val and not np.isnan(val) and 200 < val < 1200:
                f1_series.append(val)

        if len(f1_series) > 10:
            f1_cv = np.std(f1_series) / np.mean(f1_series)  # Coefficient of variation
            result["params"]["F1_variability_cv"] = round(float(f1_cv), 4)
            # Very low variability can indicate processing
            if f1_cv < 0.03:
                anomaly_score += 0.2
                result["evidence"].append(f"Unusually stable F1 (CV={f1_cv:.4f})")
    except Exception:
        pass

    result["confidence"] = min(0.95, anomaly_score)
    if not result["evidence"]:
        result["evidence"].append("Formant ratios appear within normal range")

    return result


def detect_compression(y: Any, sr: int) -> Dict[str, Any]:
    """Detect dynamic range compression via crest factor and RMS analysis."""
    result: Dict[str, Any] = {"effect": "compression", "confidence": 0.0, "params": {}, "evidence": []}

    rms = _rms_envelope(y, frame_length=2048, hop_length=512)

    # Crest factor: peak / RMS (lower = more compressed)
    peak = float(np.max(np.abs(y)))
    rms_global = float(np.sqrt(np.mean(y ** 2)))
    if rms_global < 1e-10:
        return result

    crest_factor = peak / rms_global
    crest_factor_db = _db(crest_factor)
    result["params"]["crest_factor_db"] = round(crest_factor_db, 2)
    result["params"]["peak_amplitude"] = round(peak, 4)
    result["params"]["rms_amplitude"] = round(rms_global, 4)

    # Dynamic range: difference between loud and quiet sections
    rms_db = 20.0 * np.log10(rms + 1e-10)
    # Exclude silence
    non_silent = rms_db[rms_db > np.max(rms_db) - 60]
    if len(non_silent) > 10:
        dynamic_range = float(np.percentile(non_silent, 95) - np.percentile(non_silent, 5))
        result["params"]["dynamic_range_db"] = round(dynamic_range, 2)

        # RMS envelope variance (low = heavily compressed)
        rms_variance = float(np.var(non_silent))
        result["params"]["rms_variance_db2"] = round(rms_variance, 2)

    # Scoring
    confidence = 0.0

    # Crest factor: natural speech ~12-18dB, compressed ~3-8dB
    if crest_factor_db < 6:
        confidence += 0.5
        result["params"]["estimated_ratio"] = "8:1+"
        result["evidence"].append(f"Very low crest factor: {crest_factor_db:.1f}dB (heavy compression)")
    elif crest_factor_db < 10:
        confidence += 0.3
        result["params"]["estimated_ratio"] = "4:1"
        result["evidence"].append(f"Low crest factor: {crest_factor_db:.1f}dB (moderate compression)")
    elif crest_factor_db < 14:
        confidence += 0.1
        result["params"]["estimated_ratio"] = "2:1"
        result["evidence"].append(f"Mild crest factor: {crest_factor_db:.1f}dB (light compression)")

    if "dynamic_range_db" in result["params"]:
        dr = result["params"]["dynamic_range_db"]
        if dr < 6:
            confidence += 0.3
            result["evidence"].append(f"Very narrow dynamic range: {dr:.1f}dB")
        elif dr < 12:
            confidence += 0.15
            result["evidence"].append(f"Reduced dynamic range: {dr:.1f}dB")

    result["confidence"] = min(0.95, confidence)
    return result


def detect_eq(y: Any, sr: int) -> Dict[str, Any]:
    """Detect EQ / filtering by comparing spectral shape to natural voice reference."""
    result: Dict[str, Any] = {"effect": "eq_filtering", "confidence": 0.0, "params": {}, "evidence": []}

    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)

    # Average spectral magnitude per frequency bin
    avg_spectrum = np.mean(S, axis=1)
    avg_spectrum_db = 20.0 * np.log10(avg_spectrum + 1e-10)

    # Natural voice reference: roughly -3dB/octave rolloff above ~1kHz
    # Check for anomalous peaks or notches
    spectral_centroid = float(np.sum(freqs * avg_spectrum) / (np.sum(avg_spectrum) + 1e-10))
    spectral_rolloff = float(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85).mean())

    result["params"]["spectral_centroid_hz"] = round(spectral_centroid, 1)
    result["params"]["spectral_rolloff_hz"] = round(spectral_rolloff, 1)

    # Check for high-pass filter (missing low frequencies)
    low_band_energy = float(np.mean(avg_spectrum_db[freqs < 150]))
    mid_band_energy = float(np.mean(avg_spectrum_db[(freqs > 300) & (freqs < 3000)]))

    hp_diff = mid_band_energy - low_band_energy
    if hp_diff > 20:
        result["confidence"] += 0.3
        result["params"]["high_pass_detected"] = True
        result["params"]["hp_cutoff_estimate_hz"] = "~150Hz"
        result["evidence"].append(f"Steep low-frequency rolloff: {hp_diff:.1f}dB below midrange")

    # Check for low-pass filter (missing highs)
    high_band_energy = float(np.mean(avg_spectrum_db[freqs > 8000]))
    lp_diff = mid_band_energy - high_band_energy
    # Natural voice drops off, but >30dB is suspicious
    if lp_diff > 35:
        result["confidence"] += 0.2
        result["params"]["low_pass_detected"] = True
        result["evidence"].append(f"Steep high-frequency rolloff: {lp_diff:.1f}dB below midrange")

    # Check for presence boost (2-5kHz boost common in vocal processing)
    presence_band = avg_spectrum_db[(freqs > 2000) & (freqs < 5000)]
    surrounding = np.concatenate([
        avg_spectrum_db[(freqs > 1000) & (freqs < 2000)],
        avg_spectrum_db[(freqs > 5000) & (freqs < 8000)],
    ])
    if len(presence_band) > 0 and len(surrounding) > 0:
        presence_boost = float(np.mean(presence_band) - np.mean(surrounding))
        if presence_boost > 5:
            result["confidence"] += 0.2
            result["params"]["presence_boost_db"] = round(presence_boost, 1)
            result["evidence"].append(f"Presence boost: +{presence_boost:.1f}dB in 2-5kHz range")

    # Spectral flatness — very flat spectrum suggests heavy EQ or processing
    flatness = float(librosa.feature.spectral_flatness(y=y).mean())
    result["params"]["spectral_flatness"] = round(flatness, 4)

    result["confidence"] = min(0.95, result["confidence"])
    if not result["evidence"]:
        result["evidence"].append("Spectral shape appears within normal range")

    return result


def detect_distortion(y: Any, sr: int) -> Dict[str, Any]:
    """Detect distortion/saturation via harmonic analysis and THD."""
    result: Dict[str, Any] = {"effect": "distortion", "confidence": 0.0, "params": {}, "evidence": []}

    # Total Harmonic Distortion estimation
    S = np.abs(librosa.stft(y, n_fft=4096))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    avg_spectrum = np.mean(S, axis=1)

    # Find fundamental
    # Focus on voice range 80-400Hz
    voice_range = (freqs > 80) & (freqs < 400)
    if not np.any(voice_range):
        return result

    fund_idx = np.argmax(avg_spectrum[voice_range])
    fund_freq = freqs[voice_range][fund_idx]
    fund_amp = avg_spectrum[voice_range][fund_idx]

    if fund_amp < 1e-10:
        return result

    result["params"]["fundamental_hz"] = round(float(fund_freq), 1)

    # Measure harmonics
    harmonic_amps = []
    for n in range(2, 9):  # 2nd through 8th harmonic
        harm_freq = fund_freq * n
        if harm_freq > sr / 2:
            break
        harm_idx = np.argmin(np.abs(freqs - harm_freq))
        # Search small window around expected position
        window = 3
        start = max(0, harm_idx - window)
        end = min(len(avg_spectrum), harm_idx + window + 1)
        harm_amp = float(np.max(avg_spectrum[start:end]))
        harmonic_amps.append(harm_amp)

    if harmonic_amps:
        # THD = sqrt(sum(harmonics^2)) / fundamental
        thd = float(np.sqrt(np.sum(np.array(harmonic_amps) ** 2)) / fund_amp)
        thd_percent = thd * 100
        result["params"]["thd_percent"] = round(thd_percent, 2)

        # Odd vs even harmonic ratio (tube saturation → even harmonics)
        odd_amps = [harmonic_amps[i] for i in range(0, len(harmonic_amps), 2)]  # 2nd,4th,6th = even
        even_amps = [harmonic_amps[i] for i in range(1, len(harmonic_amps), 2)]  # 3rd,5th,7th = odd
        if odd_amps and even_amps:
            even_odd_ratio = float(np.mean(odd_amps)) / (float(np.mean(even_amps)) + 1e-10)
            result["params"]["even_odd_harmonic_ratio"] = round(even_odd_ratio, 2)

        if thd_percent > 15:
            result["confidence"] = min(0.95, 0.5 + (thd_percent - 15) * 0.01)
            result["evidence"].append(f"High THD: {thd_percent:.1f}% (heavy distortion/saturation)")
        elif thd_percent > 5:
            result["confidence"] = 0.3 + (thd_percent - 5) * 0.02
            result["evidence"].append(f"Moderate THD: {thd_percent:.1f}% (mild saturation)")
        elif thd_percent > 2:
            result["confidence"] = 0.1
            result["evidence"].append(f"Low THD: {thd_percent:.1f}% (minimal distortion)")

    # Clipping detection
    clip_threshold = 0.99
    clipped_samples = np.sum(np.abs(y) > clip_threshold)
    clip_ratio = clipped_samples / len(y)
    if clip_ratio > 0.001:
        result["confidence"] = min(0.95, result["confidence"] + 0.3)
        result["params"]["clipped_sample_ratio"] = round(float(clip_ratio), 6)
        result["evidence"].append(f"Digital clipping detected: {clip_ratio * 100:.3f}% of samples")

    if not result["evidence"]:
        result["evidence"].append("No significant distortion detected")

    return result


def detect_chorus(y: Any, sr: int) -> Dict[str, Any]:
    """Detect chorus/doubling via phase coherence and spectral width modulation."""
    result: Dict[str, Any] = {"effect": "chorus_doubling", "confidence": 0.0, "params": {}, "evidence": []}

    # STFT for phase analysis
    D = librosa.stft(y)
    S = np.abs(D)
    phase = np.angle(D)

    # Phase coherence: chorus introduces phase decorrelation
    phase_diff = np.diff(phase, axis=1)
    phase_coherence = float(np.mean(np.abs(np.cos(phase_diff))))
    result["params"]["phase_coherence"] = round(phase_coherence, 4)

    # Spectral width modulation: chorus causes periodic spectral broadening
    spectral_bw = librosa.feature.spectral_bandwidth(S=S, sr=sr)[0]
    bw_std = float(np.std(spectral_bw))
    bw_mean = float(np.mean(spectral_bw))
    bw_cv = bw_std / (bw_mean + 1e-10)
    result["params"]["bandwidth_cv"] = round(bw_cv, 4)

    # Chorus typically has LFO modulation (0.1-5Hz)
    if len(spectral_bw) > 20:
        # Check for periodic modulation in bandwidth
        bw_centered = spectral_bw - np.mean(spectral_bw)
        autocorr = np.correlate(bw_centered, bw_centered, mode='full')
        autocorr = autocorr[len(autocorr) // 2:]
        if len(autocorr) > 1:
            autocorr = autocorr / (autocorr[0] + 1e-10)
            # Look for peaks indicating periodic modulation
            peaks = []
            for i in range(2, min(len(autocorr) - 1, 100)):
                if autocorr[i] > autocorr[i - 1] and autocorr[i] > autocorr[i + 1] and autocorr[i] > 0.3:
                    peaks.append(i)
            if peaks:
                result["confidence"] += 0.3
                result["evidence"].append(f"Periodic bandwidth modulation detected ({len(peaks)} peaks)")

    if phase_coherence < 0.7:
        result["confidence"] += 0.3
        result["evidence"].append(f"Low phase coherence: {phase_coherence:.3f} (typical of chorus)")
    elif phase_coherence < 0.85:
        result["confidence"] += 0.1
        result["evidence"].append(f"Slightly reduced phase coherence: {phase_coherence:.3f}")

    result["confidence"] = min(0.95, result["confidence"])
    if not result["evidence"]:
        result["evidence"].append("No chorus/doubling indicators found")

    return result


def detect_autotune(y: Any, sr: int) -> Dict[str, Any]:
    """Detect auto-tune / pitch correction by analyzing F0 contour smoothness.

    Auto-tuned vocals have unnaturally stable/quantized pitch contours
    with fast transitions between notes.
    """
    result: Dict[str, Any] = {"effect": "autotune_pitch_correction", "confidence": 0.0, "params": {}, "evidence": []}

    # Get F0 contour
    try:
        f0, voiced_flag, _ = librosa.pyin(y, fmin=50, fmax=600, sr=sr)
    except Exception:
        result["evidence"].append("Could not extract pitch contour")
        return result

    voiced = f0[voiced_flag]
    if len(voiced) < 20:
        result["evidence"].append("Insufficient voiced frames for analysis")
        return result

    # Convert to cents (semitone = 100 cents)
    cents = 1200 * np.log2(voiced / (voiced[0] + 1e-10) + 1e-10)

    # 1. Pitch stability: how close are values to nearest semitone?
    nearest_semitone = np.round(cents / 100) * 100
    deviation_from_semitone = np.abs(cents - nearest_semitone)
    mean_deviation = float(np.mean(deviation_from_semitone))
    result["params"]["mean_pitch_deviation_cents"] = round(mean_deviation, 2)

    # Natural voice: 15-40 cents mean deviation
    # Auto-tuned: < 10 cents
    if mean_deviation < 8:
        result["confidence"] += 0.5
        result["evidence"].append(f"Unnaturally precise pitch: {mean_deviation:.1f} cents mean deviation")
    elif mean_deviation < 15:
        result["confidence"] += 0.25
        result["evidence"].append(f"Very stable pitch: {mean_deviation:.1f} cents mean deviation")

    # 2. Pitch transition speed: auto-tune creates fast jumps
    pitch_diff = np.abs(np.diff(cents))
    large_jumps = pitch_diff[pitch_diff > 50]  # Jumps > 50 cents
    if len(large_jumps) > 0:
        # In auto-tune, large jumps are instantaneous (1-2 frames)
        jump_count = len(large_jumps)
        total_frames = len(pitch_diff)
        jump_ratio = jump_count / total_frames
        result["params"]["pitch_jump_ratio"] = round(float(jump_ratio), 4)

        # Check if jumps are clean (single-frame) vs gradual
        clean_jumps = 0
        for i in range(1, len(pitch_diff) - 1):
            if pitch_diff[i] > 50 and pitch_diff[i - 1] < 20 and pitch_diff[i + 1] < 20:
                clean_jumps += 1
        if jump_count > 0:
            clean_ratio = clean_jumps / jump_count
            result["params"]["clean_jump_ratio"] = round(float(clean_ratio), 3)
            if clean_ratio > 0.6:
                result["confidence"] += 0.25
                result["evidence"].append(
                    f"Sharp pitch transitions: {clean_ratio:.0%} of jumps are single-frame"
                )

    # 3. Pitch histogram: auto-tune creates peaks at semitone intervals
    cents_mod = cents % 100  # Position within semitone
    hist, _ = np.histogram(cents_mod, bins=20, range=(0, 100))
    hist_normalized = hist / (np.sum(hist) + 1e-10)
    peak_concentration = float(np.max(hist_normalized))
    result["params"]["pitch_histogram_peak"] = round(peak_concentration, 3)

    if peak_concentration > 0.3:
        result["confidence"] += 0.2
        result["evidence"].append(f"Pitch concentrated at semitone centers ({peak_concentration:.0%} peak)")

    result["confidence"] = min(0.95, result["confidence"])
    if not result["evidence"]:
        result["evidence"].append("Pitch contour appears natural")

    return result


def detect_deessing(y: Any, sr: int) -> Dict[str, Any]:
    """Detect de-essing by looking for energy dips in sibilant frequency range."""
    result: Dict[str, Any] = {"effect": "de_essing", "confidence": 0.0, "params": {}, "evidence": []}

    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)

    # Sibilant range: ~4-9kHz
    sibilant_mask = (freqs > 4000) & (freqs < 9000)
    below_mask = (freqs > 2000) & (freqs < 4000)
    above_mask = (freqs > 9000) & (freqs < 11000)

    sib_energy = float(np.mean(S[sibilant_mask, :]))
    below_energy = float(np.mean(S[below_mask, :]))
    above_energy = float(np.mean(S[above_mask, :]))

    if below_energy < 1e-10:
        return result

    # Natural voice: sibilant region has similar or higher energy than surroundings
    # De-essed: notch or dip in sibilant region
    sib_ratio = sib_energy / below_energy
    result["params"]["sibilant_ratio"] = round(float(sib_ratio), 3)

    if sib_ratio < 0.3:
        result["confidence"] = 0.5
        result["evidence"].append(f"Strong dip in sibilant range: ratio {sib_ratio:.2f}")
    elif sib_ratio < 0.6:
        result["confidence"] = 0.25
        result["evidence"].append(f"Moderate sibilant reduction: ratio {sib_ratio:.2f}")

    # Check for dynamic de-essing: sibilant energy that's unnaturally consistent
    sib_envelope = np.mean(S[sibilant_mask, :], axis=0)
    if len(sib_envelope) > 10:
        sib_cv = float(np.std(sib_envelope) / (np.mean(sib_envelope) + 1e-10))
        result["params"]["sibilant_variability_cv"] = round(sib_cv, 4)
        if sib_cv < 0.3:
            result["confidence"] += 0.15
            result["evidence"].append(f"Unnaturally consistent sibilant level (CV={sib_cv:.3f})")

    result["confidence"] = min(0.95, result["confidence"])
    if not result["evidence"]:
        result["evidence"].append("No significant de-essing detected")

    return result


def detect_vocoder(y: Any, sr: int) -> Dict[str, Any]:
    """Detect vocoder processing via spectral envelope regularity."""
    result: Dict[str, Any] = {"effect": "vocoder", "confidence": 0.0, "params": {}, "evidence": []}

    # MFCCs — vocoded voice has very regular/artificial MFCC patterns
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)

    # Check MFCC temporal variance — vocoders create very uniform textures
    mfcc_var = np.var(mfccs, axis=1)
    mean_mfcc_var = float(np.mean(mfcc_var[1:]))  # Skip DC component
    result["params"]["mfcc_temporal_variance"] = round(mean_mfcc_var, 4)

    # Check for carrier signal: vocoders often use sawtooth/synth carriers
    # which create very regular harmonic spacing
    S = np.abs(librosa.stft(y, n_fft=4096))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    avg_spectrum = np.mean(S, axis=1)

    # Measure harmonic regularity
    peaks_idx = scipy_signal.find_peaks(avg_spectrum, height=np.max(avg_spectrum) * 0.05, distance=5)[0]
    if len(peaks_idx) > 3:
        peak_freqs = freqs[peaks_idx]
        peak_diffs = np.diff(peak_freqs)
        if len(peak_diffs) > 2:
            spacing_cv = float(np.std(peak_diffs) / (np.mean(peak_diffs) + 1e-10))
            result["params"]["harmonic_spacing_cv"] = round(spacing_cv, 4)

            # Very regular spacing = synthetic carrier
            if spacing_cv < 0.1:
                result["confidence"] += 0.4
                result["evidence"].append(
                    f"Extremely regular harmonic spacing (CV={spacing_cv:.3f}) — synthetic carrier likely"
                )
            elif spacing_cv < 0.2:
                result["confidence"] += 0.15
                result["evidence"].append(f"Regular harmonic spacing (CV={spacing_cv:.3f})")

    # Very low MFCC variance suggests artificial sound
    if mean_mfcc_var < 5:
        result["confidence"] += 0.3
        result["evidence"].append(f"Low MFCC variance: {mean_mfcc_var:.2f} (artificial texture)")

    result["confidence"] = min(0.95, result["confidence"])
    if not result["evidence"]:
        result["evidence"].append("No vocoder indicators found")

    return result


def detect_noise_gate(y: Any, sr: int) -> Dict[str, Any]:
    """Detect noise gating via abrupt silence transitions."""
    result: Dict[str, Any] = {"effect": "noise_gate", "confidence": 0.0, "params": {}, "evidence": []}

    rms = _rms_envelope(y, frame_length=1024, hop_length=256)
    rms_db = 20.0 * np.log10(rms + 1e-10)

    # Find transitions from silence to sound
    threshold = np.max(rms_db) - 40
    is_silent = rms_db < threshold

    # Measure transition sharpness
    transitions = np.diff(is_silent.astype(int))
    onset_indices = np.where(transitions == -1)[0]  # silence → sound
    offset_indices = np.where(transitions == 1)[0]   # sound → silence

    sharp_onsets = 0
    sharp_offsets = 0
    total_transitions = len(onset_indices) + len(offset_indices)

    for idx in onset_indices:
        if idx > 0 and idx < len(rms_db) - 1:
            jump = rms_db[idx + 1] - rms_db[idx]
            if jump > 15:  # > 15dB in one frame = unnaturally sharp
                sharp_onsets += 1

    for idx in offset_indices:
        if idx > 0 and idx < len(rms_db) - 1:
            drop = rms_db[idx] - rms_db[idx + 1]
            if drop > 15:
                sharp_offsets += 1

    total_sharp = sharp_onsets + sharp_offsets
    result["params"]["total_transitions"] = total_transitions
    result["params"]["sharp_transitions"] = total_sharp

    if total_transitions > 0:
        sharp_ratio = total_sharp / total_transitions
        result["params"]["sharp_ratio"] = round(float(sharp_ratio), 3)

        if sharp_ratio > 0.5 and total_sharp > 3:
            result["confidence"] = min(0.9, 0.3 + sharp_ratio * 0.4)
            result["evidence"].append(
                f"{total_sharp}/{total_transitions} transitions are unnaturally sharp (>15dB/frame)"
            )
        elif sharp_ratio > 0.2:
            result["confidence"] = 0.2
            result["evidence"].append(f"Some sharp transitions: {sharp_ratio:.0%}")

    # Check noise floor consistency in "silent" regions
    silent_regions = rms_db[is_silent]
    if len(silent_regions) > 10:
        noise_floor_var = float(np.var(silent_regions))
        result["params"]["noise_floor_variance_db2"] = round(noise_floor_var, 2)
        # Very uniform noise floor suggests gating
        if noise_floor_var < 1.0 and np.mean(silent_regions) < -60:
            result["confidence"] += 0.2
            result["evidence"].append("Very uniform/deep silence floor (digital noise gate)")

    result["confidence"] = min(0.95, result["confidence"])
    if not result["evidence"]:
        result["evidence"].append("No noise gate indicators found")

    return result


def detect_delay(y: Any, sr: int) -> Dict[str, Any]:
    """Detect delay/echo via autocorrelation peaks."""
    result: Dict[str, Any] = {"effect": "delay_echo", "confidence": 0.0, "params": {}, "evidence": []}

    # Use energy envelope for autocorrelation (more robust than raw signal)
    rms = _rms_envelope(y, frame_length=2048, hop_length=512)
    rms_centered = rms - np.mean(rms)

    if np.std(rms_centered) < 1e-10:
        return result

    autocorr = np.correlate(rms_centered, rms_centered, mode='full')
    autocorr = autocorr[len(autocorr) // 2:]
    autocorr = autocorr / (autocorr[0] + 1e-10)

    # Look for peaks in delay range (50ms - 1s)
    frames_per_sec = sr / 512
    min_delay_frames = int(0.05 * frames_per_sec)  # 50ms
    max_delay_frames = int(1.0 * frames_per_sec)   # 1s

    search_region = autocorr[min_delay_frames:min(max_delay_frames, len(autocorr))]
    if len(search_region) < 5:
        return result

    peaks_idx = scipy_signal.find_peaks(search_region, height=0.15, distance=5)[0]

    if len(peaks_idx) > 0:
        strongest_peak_idx = peaks_idx[np.argmax(search_region[peaks_idx])]
        actual_idx = strongest_peak_idx + min_delay_frames
        delay_seconds = actual_idx / frames_per_sec
        peak_height = float(autocorr[actual_idx])

        result["params"]["delay_time_seconds"] = round(delay_seconds, 3)
        result["params"]["delay_time_ms"] = round(delay_seconds * 1000, 1)
        result["params"]["correlation_strength"] = round(peak_height, 3)

        if peak_height > 0.4:
            result["confidence"] = min(0.9, 0.4 + peak_height * 0.5)
            result["evidence"].append(
                f"Strong echo at {delay_seconds * 1000:.0f}ms (correlation: {peak_height:.2f})"
            )
        elif peak_height > 0.2:
            result["confidence"] = 0.2 + peak_height * 0.3
            result["evidence"].append(
                f"Possible echo at {delay_seconds * 1000:.0f}ms (correlation: {peak_height:.2f})"
            )

        # Check for multiple echoes (feedback delay)
        if len(peaks_idx) > 1:
            result["params"]["echo_count"] = len(peaks_idx)
            result["evidence"].append(f"Multiple echo peaks detected ({len(peaks_idx)})")
            result["confidence"] = min(0.95, result["confidence"] + 0.1)

    if not result["evidence"]:
        result["evidence"].append("No delay/echo detected")

    return result


# ---------------------------------------------------------------------------
# Main analysis entry point
# ---------------------------------------------------------------------------

def analyze_voice(
    path: Path,
    export_json: bool = False,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Analyze a voice audio file for applied effects and processing.

    Args:
        path: Path to audio file.
        export_json: If True, export results to JSON.
        output_dir: Directory for JSON output (default: same as audio file).

    Returns:
        Dict with full analysis results including detected effects.
    """
    _require_librosa()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    print(f"Loading audio: {path.name}...")
    y, sr = _load_audio(path, sr=22050)
    duration = librosa.get_duration(y=y, sr=sr)

    print(f"  Duration: {duration:.1f}s | Sample rate: {sr}Hz")
    print(f"  Dependencies: librosa=YES, parselmouth={'YES' if _HAS_PARSELMOUTH else 'NO'}, crepe={'YES' if _HAS_CREPE else 'NO'}")

    # Basic voice detection: check if there's pitched content in voice range
    f0_median = _librosa_f0(y, sr)
    voice_detected = f0_median is not None and 50 < f0_median < 600

    result: Dict[str, Any] = {
        "file": str(path),
        "filename": path.name,
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
        "voice_detected": voice_detected,
        "fundamental_frequency_hz": round(f0_median, 1) if f0_median else None,
        "dependencies_available": {
            "librosa": True,
            "parselmouth": _HAS_PARSELMOUTH,
            "crepe": _HAS_CREPE,
        },
        "effects_detected": [],
        "spectral_profile": {},
    }

    # Spectral profile
    spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    spectral_bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
    spectral_rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
    spectral_flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))

    result["spectral_profile"] = {
        "centroid_hz": round(spectral_centroid, 1),
        "bandwidth_hz": round(spectral_bandwidth, 1),
        "rolloff_hz": round(spectral_rolloff, 1),
        "flatness": round(spectral_flatness, 4),
    }

    # Run all detectors
    detectors = [
        ("Reverb", detect_reverb),
        ("Pitch shift", detect_pitch_shift),
        ("Formant shift", detect_formant_shift),
        ("Compression", detect_compression),
        ("EQ/Filtering", detect_eq),
        ("Distortion", detect_distortion),
        ("Chorus/Doubling", detect_chorus),
        ("Auto-tune", detect_autotune),
        ("De-essing", detect_deessing),
        ("Vocoder", detect_vocoder),
        ("Noise gate", detect_noise_gate),
        ("Delay/Echo", detect_delay),
    ]

    for name, detector_fn in detectors:
        print(f"  Analyzing: {name}...")
        try:
            effect_result = detector_fn(y, sr)
            result["effects_detected"].append(effect_result)
        except Exception as e:
            result["effects_detected"].append({
                "effect": name.lower().replace("/", "_").replace(" ", "_"),
                "confidence": 0.0,
                "params": {},
                "evidence": [f"Error during analysis: {e}"],
            })

    # Sort by confidence descending
    result["effects_detected"].sort(key=lambda x: x.get("confidence", 0), reverse=True)

    # Export JSON if requested
    if export_json:
        if output_dir is None:
            output_dir = path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{path.stem}_voice_analysis.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\nAnalysis saved to {json_path}")

    return result


def print_voice_summary(result: Dict[str, Any]) -> None:
    """Print a human-readable summary of voice effects analysis."""
    print("\n" + "=" * 60)
    print("  VOICE EFFECTS ANALYSIS REPORT")
    print("=" * 60)
    print(f"  File:       {result.get('filename', result.get('file'))}")
    print(f"  Duration:   {result.get('duration_seconds')}s")
    print(f"  Voice:      {'Detected' if result.get('voice_detected') else 'Not detected'}")
    if result.get("fundamental_frequency_hz"):
        print(f"  F0:         {result['fundamental_frequency_hz']}Hz")
    print()

    # Spectral profile
    sp = result.get("spectral_profile", {})
    if sp:
        print("  Spectral Profile:")
        print(f"    Centroid:   {sp.get('centroid_hz', '?')}Hz")
        print(f"    Bandwidth:  {sp.get('bandwidth_hz', '?')}Hz")
        print(f"    Rolloff:    {sp.get('rolloff_hz', '?')}Hz")
        print(f"    Flatness:   {sp.get('flatness', '?')}")
        print()

    # Effects
    effects = result.get("effects_detected", [])
    if not effects:
        print("  No effects analysis available.")
        return

    # Split into detected and not detected
    detected = [e for e in effects if e.get("confidence", 0) >= 0.2]
    low = [e for e in effects if e.get("confidence", 0) < 0.2]

    if detected:
        print("  DETECTED EFFECTS:")
        print("  " + "-" * 56)
        for e in detected:
            conf = e.get("confidence", 0)
            name = e.get("effect", "unknown").replace("_", " ").title()
            bar = "#" * int(conf * 20)
            print(f"  [{conf:.0%}] {bar:<20} {name}")

            for ev in e.get("evidence", []):
                print(f"        > {ev}")

            params = e.get("params", {})
            if params:
                param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                # Wrap long param strings
                if len(param_str) > 70:
                    print(f"        Params:")
                    for k, v in params.items():
                        print(f"          {k}: {v}")
                else:
                    print(f"        Params: {param_str}")
            print()

    if low:
        print("  NOT DETECTED / LOW CONFIDENCE:")
        print("  " + "-" * 56)
        for e in low:
            name = e.get("effect", "unknown").replace("_", " ").title()
            conf = e.get("confidence", 0)
            print(f"  [{conf:.0%}] {name}")
        print()

    # Dependencies note
    deps = result.get("dependencies_available", {})
    missing = [k for k, v in deps.items() if not v]
    if missing:
        print(f"  NOTE: Some detectors limited — install missing: {', '.join(missing)}")
        print()

    print("=" * 60)
