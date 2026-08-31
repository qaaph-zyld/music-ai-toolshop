"""Time-align a vocal take to an instrumental.

**The problem, honestly stated.** There are two very different cases hiding
behind "align the vocal", and conflating them is how a swap pipeline silently
produces a track that is off by half a bar:

1. **Same-instrumental takes.** The vocal was recorded while listening to this
   instrumental, so the only error is a constant offset (DAW export start, count-in,
   latency). A single lag fixes it, and cross-correlation finds that lag reliably.
2. **Independent performances.** The vocal was recorded to a different tempo or no
   backing at all. No single offset can fix that; it needs stretching at best and
   real warping at worst.

This module solves case 1 properly and **detects** case 2 rather than pretending
to solve it. `estimate_offset` returns a confidence, `tempo_match` reports the
tempo ratio, and the pipeline's `--require-alignment` turns a low-confidence
result into a hard failure instead of a quietly bad mix. Recording which path ran
is necessary but not sufficient - the caller must be able to demand the good one.

**Why onset envelopes and not raw waveforms.** A vocal and an instrumental share
almost no waveform structure; correlating samples finds noise. What they do share
is *rhythm* - the performer lands syllables on the beat. Onset strength envelopes
reduce both signals to that shared structure, which is what makes the correlation
peak meaningful. The envelope is computed at ~86 Hz (hop 512 at 22050), so lag
resolution is ~11.6 ms - well under the ~20 ms at which a listener starts hearing
a vocal as "late".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

#: Analysis sample rate. Alignment works on envelopes, not audio quality, so the
#: cheap rate is the right one - it is ~4x faster than 44100 for identical lags.
ANALYSIS_SR = 22050
#: Hop for the onset envelope; sets lag resolution (512/22050 = 11.6 ms).
HOP_LENGTH = 512

#: Correlation below this is not a real alignment. Calibrated as a floor, not a
#: guarantee: normalised cross-correlation of unrelated envelopes typically peaks
#: around 0.1-0.2, so 0.35 sits clear of noise without demanding a perfect take.
#: NOT YET tuned against a labelled set - treated as a warning threshold, and the
#: measured value is always reported so a caller can judge for itself.
DEFAULT_MIN_CONFIDENCE = 0.35

#: Tempo agreement tolerance in percent, used only as a **fallback** when the
#: track is too short to measure drift directly.
#:
#: MEASURED 2026-08-31: two click trains at exactly 140 and 70 BPM - the same
#: rhythm, one written at half time - were estimated by `librosa.beat.beat_track`
#: as 143.55 and 69.84 BPM. Folded to a common octave that is a **2.7% error on
#: identical material**. A tolerance tighter than the instrument's own error
#: rejects good takes, so this sits at 5.0 and the real verdict comes from
#: `drift_seconds` below, which resolves ~12 ms.
DEFAULT_TEMPO_TOLERANCE_PCT = 5.0

#: Drift between the head and tail alignments, in seconds, beyond which a single
#: offset cannot serve the whole track. ~30 ms is where a vocal begins to sound
#: flammed against a beat; 50 ms leaves room for window noise while staying well
#: inside audible.
DEFAULT_DRIFT_TOLERANCE_S = 0.05

#: Shortest envelope, in seconds, on which head/tail drift is worth measuring.
#: Below this the two windows overlap too much for their lags to be independent.
MIN_DRIFT_ANALYSIS_S = 12.0

#: Head/tail window correlations below this are too weak to base a drift verdict
#: on; the estimator says "unknown" rather than inventing a verdict.
MIN_WINDOW_CONFIDENCE = 0.25

#: Half-width of the neighbourhood suppressed around the winning correlation peak
#: before looking for a rival. Wide enough to cover a peak's own shoulder, far
#: narrower than a beat at any musical tempo (0.1 s = 1/5 beat at 120 BPM).
PEAK_GUARD_S = 0.1

#: Minimum gap between the best peak and the best distinct rival. Below this the
#: offset is ambiguous - typically by whole beats or bars on periodic material.
#: NOT calibrated against a labelled set of real takes; it is a *reporting*
#: threshold, and `peak_margin` is always emitted so a caller can judge directly.
DEFAULT_MIN_PEAK_MARGIN = 0.05

#: Widest offset searched, seconds. Wider than any plausible count-in or export
#: slip; searching the whole track invites a spurious peak from a repeated section.
DEFAULT_MAX_OFFSET_S = 30.0


@dataclass
class AlignmentResult:
    """What alignment concluded, and how much it should be trusted."""

    #: Seconds to delay the vocal by. Negative means the vocal starts late in its
    #: own file and must be trimmed.
    offset_seconds: float
    #: Peak normalised cross-correlation, 0-1. The confidence number.
    confidence: float
    instrumental_tempo: Optional[float]
    vocal_tempo: Optional[float]
    #: vocal_tempo / instrumental_tempo, octave-folded. Informational: it carries
    #: the estimator's own few-percent error and is not the verdict.
    tempo_ratio: Optional[float]
    #: True when a single offset cannot align the whole track (case 2 above).
    tempo_mismatch: bool
    #: "cross_correlation" | "declared" | "none"
    method: str
    notes: str = ""

    #: Seconds the alignment slips between the head and the tail of the track.
    #: None when the track was too short, or the windows too weakly correlated,
    #: to measure it - reported as unknown rather than as zero.
    drift_seconds: Optional[float] = None
    #: Distance between the two window centres the drift was measured across.
    drift_span_seconds: Optional[float] = None
    #: How the mismatch verdict was reached: "drift" | "tempo" | "none".
    mismatch_basis: str = "none"

    #: Gap between the winning correlation peak and the best distinct rival.
    #: Small means several placements fit equally well - usually whole beats or
    #: bars apart on periodic material. See `_normalised_cross_correlation`.
    peak_margin: float = 1.0

    @property
    def ambiguous(self) -> bool:
        """True when a rival placement fits nearly as well as the chosen one."""
        return self.peak_margin < DEFAULT_MIN_PEAK_MARGIN

    @property
    def trustworthy(self) -> bool:
        return (
            self.confidence >= DEFAULT_MIN_CONFIDENCE
            and not self.tempo_mismatch
            and not self.ambiguous
        )

    @property
    def implied_tempo_error_pct(self) -> Optional[float]:
        """Tempo disagreement implied by the drift - the precise version."""
        if self.drift_seconds is None or not self.drift_span_seconds:
            return None
        return (self.drift_seconds / self.drift_span_seconds) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["offset_seconds"] = round(self.offset_seconds, 4)
        data["confidence"] = round(self.confidence, 4)
        data["trustworthy"] = self.trustworthy
        data["ambiguous"] = self.ambiguous
        data["peak_margin"] = round(self.peak_margin, 4)
        error_pct = self.implied_tempo_error_pct
        data["implied_tempo_error_pct"] = (
            round(error_pct, 3) if error_pct is not None else None
        )
        for key in ("instrumental_tempo", "vocal_tempo", "tempo_ratio",
                    "drift_seconds", "drift_span_seconds"):
            if data.get(key) is not None:
                data[key] = round(data[key], 4)
        return data


def _onset_envelope(path: Path, sr: int = ANALYSIS_SR):
    """Load `path` mono and return (onset_envelope, tempo)."""
    import librosa
    import numpy as np

    y, loaded_sr = librosa.load(str(path), sr=sr, mono=True)
    if y.size == 0:
        raise ValueError(f"no audio samples in {path}")
    env = librosa.onset.onset_strength(y=y, sr=loaded_sr, hop_length=HOP_LENGTH)
    tempo = None
    try:
        raw_tempo, _ = librosa.beat.beat_track(
            onset_envelope=env, sr=loaded_sr, hop_length=HOP_LENGTH
        )
        tempo = float(np.atleast_1d(raw_tempo)[0])
    except Exception:  # pragma: no cover - librosa edge cases on very short input
        logger.warning("tempo estimation failed for %s", path, exc_info=True)
    return env, tempo


def _normalised_cross_correlation(a, b, max_lag: int) -> Tuple[int, float, float]:
    """Return (best_lag, peak_correlation, peak_margin) for `b` against `a`.

    Both envelopes are mean-removed and unit-normalised first, so the peak is a
    correlation coefficient in roughly -1..1 and comparable across tracks. Without
    that normalisation the peak scales with signal energy and a loud take looks
    better aligned than a quiet one, which is precisely the wrong bias.

    **`peak_margin` is the number that matters, and it is why this returns three
    values instead of two.** MEASURED 2026-08-31 on a 120 BPM click train against
    a copy displaced by 0.75 s: the correlation peaked at 0.9173 (lag -11 frames),
    0.9135 (-54), 0.9012 (+11) and 0.8972 (-32) - and **-32 was the true offset**.
    The peaks sit one beat apart and the *wrong* one won by 0.02.

    That is not a fixture artefact. Rap instrumentals are strongly periodic at the
    bar, so a lone "confidence" number is actively misleading: it can be 0.92 while
    the offset is a whole bar out, which is the classic way a vocal swap lands
    audibly wrong. The margin between the winning peak and the best *distinct*
    rival exposes it. A small margin means "several placements fit equally well" -
    the caller should declare the offset rather than trust one.
    """
    import numpy as np

    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    a = a - a.mean()
    b = b - b.mean()
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0, 0.0, 0.0
    a = a / a_norm
    b = b / b_norm

    corr = np.correlate(a, b, mode="full")
    zero_lag_index = len(b) - 1
    lo = max(0, zero_lag_index - max_lag)
    hi = min(len(corr), zero_lag_index + max_lag + 1)
    window = np.array(corr[lo:hi], dtype=np.float64)
    if window.size == 0:
        return 0, 0.0, 0.0

    best_local = int(np.argmax(window))
    best_value = float(window[best_local])
    best_lag = (lo + best_local) - zero_lag_index

    # Suppress the winning peak's own shoulder before looking for a rival, or the
    # "second peak" is just the sample next to the first.
    guard = max(1, int(PEAK_GUARD_S * ANALYSIS_SR / HOP_LENGTH))
    masked = window.copy()
    masked[max(0, best_local - guard) : best_local + guard + 1] = -np.inf
    rival = float(np.max(masked)) if np.isfinite(masked).any() else -1.0
    margin = best_value - rival if rival > -1.0 else best_value

    return best_lag, best_value, float(max(0.0, margin))


def _fold_octaves(ratio: float) -> float:
    """Fold a tempo ratio into 0.67..1.5 - 70 and 140 BPM are one performance."""
    folded = ratio
    for _ in range(8):  # bounded: a ratio of 0 or inf must not spin here
        if folded > 1.5:
            folded /= 2.0
        elif folded < 0.67:
            folded *= 2.0
        else:
            break
    return folded


def _measure_drift(instr_env, vocal_env, max_lag: int):
    """Align the head and the tail separately and report how far they disagree.

    This is the precise instrument for "can one offset serve the whole track?".
    A 1% tempo difference moves the alignment by 1% of the elapsed time - over a
    60 s span that is 600 ms, hundreds of times the 12 ms this can resolve, while
    `beat_track` cannot see the same difference at all through its own ~3% error.

    Returns `(drift_seconds, span_seconds, head_conf, tail_conf)`, or None when
    the material is too short or the windows correlate too weakly to say.
    """
    import numpy as np

    frames_per_second = ANALYSIS_SR / HOP_LENGTH
    usable = min(len(instr_env), len(vocal_env))
    if usable / frames_per_second < MIN_DRIFT_ANALYSIS_S:
        return None

    window = usable // 3
    if window < int(2.0 * frames_per_second):
        return None

    # Truncate BOTH envelopes to the common length before slicing. Taking `[-w:]`
    # of envelopes with different lengths compares different absolute time ranges,
    # which manufactures drift proportional to the length difference - a 0.75 s
    # difference showed up as 0.26 s of phantom drift on identical rhythms.
    instr = np.asarray(instr_env[:usable])
    vocal = np.asarray(vocal_env[:usable])

    head_lag, head_conf, _ = _normalised_cross_correlation(
        instr[:window], vocal[:window], max_lag
    )
    tail_lag, tail_conf, _ = _normalised_cross_correlation(
        instr[usable - window : usable], vocal[usable - window : usable], max_lag
    )
    if head_conf < MIN_WINDOW_CONFIDENCE or tail_conf < MIN_WINDOW_CONFIDENCE:
        return None

    drift_frames = tail_lag - head_lag
    # Centres of the two windows: half a window in, and half a window from the end.
    span_frames = (usable - window / 2.0) - (window / 2.0)
    return (
        drift_frames / frames_per_second,
        span_frames / frames_per_second,
        head_conf,
        tail_conf,
    )


def estimate_offset(
    instrumental: Path,
    vocal: Path,
    max_offset_s: float = DEFAULT_MAX_OFFSET_S,
    tempo_tolerance_pct: float = DEFAULT_TEMPO_TOLERANCE_PCT,
    drift_tolerance_s: float = DEFAULT_DRIFT_TOLERANCE_S,
) -> AlignmentResult:
    """Estimate how far the vocal must move to sit on the instrumental."""
    instr_env, instr_tempo = _onset_envelope(Path(instrumental))
    vocal_env, vocal_tempo = _onset_envelope(Path(vocal))

    frames_per_second = ANALYSIS_SR / HOP_LENGTH
    max_lag = int(max_offset_s * frames_per_second)
    lag, confidence, peak_margin = _normalised_cross_correlation(
        instr_env, vocal_env, max_lag
    )
    offset_seconds = lag / frames_per_second

    tempo_ratio = None
    if instr_tempo and vocal_tempo and instr_tempo > 0:
        tempo_ratio = _fold_octaves(vocal_tempo / instr_tempo)

    # Drift is the verdict when it can be measured; tempo is the fallback.
    drift = _measure_drift(instr_env, vocal_env, max_lag)
    drift_seconds = drift_span = None
    if drift is not None:
        drift_seconds, drift_span, _, _ = drift
        tempo_mismatch = abs(drift_seconds) > drift_tolerance_s
        basis = "drift"
    elif tempo_ratio is not None:
        tempo_mismatch = abs(tempo_ratio - 1.0) * 100.0 > tempo_tolerance_pct
        basis = "tempo"
    else:
        tempo_mismatch = False
        basis = "none"

    notes = ""
    if peak_margin < DEFAULT_MIN_PEAK_MARGIN:
        notes = (
            "ambiguous alignment: a rival placement scores within {:.3f} of the "
            "chosen one, so the offset may be a whole beat or bar out. Declare it "
            "with --offset-seconds rather than trusting this."
        ).format(peak_margin)
    elif tempo_mismatch and basis == "drift":
        notes = (
            "alignment drifts {:+.0f} ms across {:.0f} s - a single offset cannot "
            "align the whole track; time-stretch or re-record to the instrumental"
        ).format(drift_seconds * 1000.0, drift_span or 0.0)
    elif tempo_mismatch:
        notes = (
            "tempo disagreement beyond tolerance (estimated, not drift-measured) - "
            "a single offset probably cannot align the whole track"
        )
    elif confidence < DEFAULT_MIN_CONFIDENCE:
        notes = (
            "low correlation - the takes may not share a rhythmic reference; "
            "check the offset by ear before trusting the mix"
        )
    elif basis == "none":
        notes = "drift not measurable on this material; offset unverified across the track"

    return AlignmentResult(
        offset_seconds=offset_seconds,
        confidence=confidence,
        instrumental_tempo=instr_tempo,
        vocal_tempo=vocal_tempo,
        tempo_ratio=tempo_ratio,
        tempo_mismatch=tempo_mismatch,
        method="cross_correlation",
        notes=notes,
        drift_seconds=drift_seconds,
        drift_span_seconds=drift_span,
        mismatch_basis=basis,
        peak_margin=peak_margin,
    )


def declared_offset(offset_seconds: float) -> AlignmentResult:
    """An offset the user supplied. Confidence 1.0 because it is not a guess."""
    return AlignmentResult(
        offset_seconds=float(offset_seconds),
        confidence=1.0,
        instrumental_tempo=None,
        vocal_tempo=None,
        tempo_ratio=None,
        tempo_mismatch=False,
        method="declared",
        notes="offset supplied by the caller; no estimation performed",
    )


def apply_offset(audio, sr: int, offset_seconds: float):
    """Shift `audio` (samples-first, mono or stereo) by `offset_seconds`.

    Positive delays the vocal with leading silence; negative trims from the head.
    Length is not otherwise altered here - the mixer decides the final length, so
    that padding and trimming happen in exactly one place.
    """
    import numpy as np

    audio = np.asarray(audio)
    shift = int(round(offset_seconds * sr))
    if shift == 0:
        return audio
    if audio.ndim == 1:
        pad_shape = (abs(shift),)
    else:
        pad_shape = (abs(shift), audio.shape[1])

    if shift > 0:
        return np.concatenate([np.zeros(pad_shape, dtype=audio.dtype), audio], axis=0)
    return audio[abs(shift) :]


def time_stretch_to(audio, sr: int, ratio: float):
    """Stretch `audio` by `ratio` (vocal_tempo / instrumental_tempo).

    A ratio above 1 means the vocal was performed faster than the instrumental
    and must be slowed. Uses librosa's phase vocoder, which is adequate for
    modest corrections and audibly poor beyond roughly +-6%; the caller is
    expected to have surfaced the ratio to the user before invoking this.
    """
    import librosa
    import numpy as np

    if ratio is None or abs(ratio - 1.0) < 1e-6:
        return audio

    audio = np.asarray(audio)
    if audio.ndim == 1:
        return librosa.effects.time_stretch(y=audio, rate=ratio)
    channels = [
        librosa.effects.time_stretch(y=np.ascontiguousarray(audio[:, c]), rate=ratio)
        for c in range(audio.shape[1])
    ]
    length = min(len(c) for c in channels)
    return np.stack([c[:length] for c in channels], axis=1)
