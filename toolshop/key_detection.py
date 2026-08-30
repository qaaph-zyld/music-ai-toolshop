"""Krumhansl-Schmuckler key and mode detection.

Replaces two separate broken implementations (H2-M1, CHANGELOG #047).

**What was wrong.** `bpm_adapter` picked the key as ``argmax(mean_chroma)`` — the
loudest pitch class, which is the tonic only by coincidence — and decided mode with
``mean_chroma[key] > 0.5``. Modality is a *relationship* between scale degrees,
above all the third; that expression tests how loud one bin is. Measured over 8
real tracks it returned ``major`` for **7 of 8**, the lone ``minor`` being a track
whose peak happened to fall under the threshold. It was not a detector; it was
"major unless the peak is low". For a catalogue that is overwhelmingly drill and
trap — near-universally minor — it was wrong in the worst direction.

`cleaning_stages._detect_key` was a second, independent implementation. Its mode
logic at least compared the minor third against the major third, which is
musically meaningful. Both now call in here: one detector, not three.

**The method.** Krumhansl-Schmuckler correlates the chroma vector against 24
rotated key profiles (12 major, 12 minor) derived from listener probe-tone ratings,
and takes the highest correlation. It is a standard, well-understood baseline.

**Honest about its weakness.** K-S confuses relative major and minor (C major and
A minor share a pitch-class set), so the two best correlations are often close. The
runner-up and the margin are returned rather than hidden — a narrow margin is real
information about the estimate, and the roadmap asks dossiers to carry confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Kessler probe-tone profiles.
KS_MAJOR = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
KS_MINOR = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)


@dataclass
class KeyEstimate:
    """A key estimate with the evidence behind it."""

    key: str
    mode: str
    confidence: float
    #: Runner-up, usually the relative major/minor. Often nearly as good.
    alternate_key: Optional[str] = None
    alternate_mode: Optional[str] = None
    #: Gap between best and runner-up correlation. Small = genuinely ambiguous.
    margin: float = 0.0

    @property
    def label(self) -> str:
        """``"G major"`` / ``"G minor"`` — the historical string form."""
        return f"{self.key} {self.mode}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "mode": self.mode,
            "confidence": round(float(self.confidence), 4),
            "alternate_key": self.alternate_key,
            "alternate_mode": self.alternate_mode,
            "margin": round(float(self.margin), 4),
            "method": "krumhansl-schmuckler",
        }


def _correlate(chroma: np.ndarray, profile: np.ndarray) -> float:
    """Pearson correlation between a chroma vector and a key profile."""
    c = chroma - chroma.mean()
    p = profile - profile.mean()
    denom = np.linalg.norm(c) * np.linalg.norm(p)
    if denom == 0:
        return 0.0
    return float(np.dot(c, p) / denom)


def detect_key_from_chroma(chroma_mean: np.ndarray) -> KeyEstimate:
    """Estimate key and mode from a 12-bin mean chroma vector.

    Args:
        chroma_mean: 12 values, one per pitch class, C first.

    Returns:
        The best-correlating key, with confidence and the runner-up.
    """
    chroma_mean = np.asarray(chroma_mean, dtype=float).reshape(-1)
    if chroma_mean.shape[0] != 12:
        raise ValueError(f"expected 12 chroma bins, got {chroma_mean.shape[0]}")

    scored: list[tuple[float, str, str]] = []
    for tonic in range(12):
        rotated = np.roll(chroma_mean, -tonic)
        scored.append((_correlate(rotated, KS_MAJOR), PITCH_CLASSES[tonic], "major"))
        scored.append((_correlate(rotated, KS_MINOR), PITCH_CLASSES[tonic], "minor"))

    scored.sort(key=lambda t: t[0], reverse=True)
    best, runner_up = scored[0], scored[1]

    return KeyEstimate(
        key=best[1],
        mode=best[2],
        confidence=best[0],
        alternate_key=runner_up[1],
        alternate_mode=runner_up[2],
        margin=best[0] - runner_up[0],
    )


def detect_key_from_audio(y: np.ndarray, sr: int) -> KeyEstimate:
    """Estimate key from an audio signal.

    Uses CQT chroma, which is better pitch-resolved than STFT chroma for this.
    """
    import librosa

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    return detect_key_from_chroma(chroma.mean(axis=1))
