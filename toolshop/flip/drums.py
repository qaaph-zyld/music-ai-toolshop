"""Drum one-shot mining and drill-pattern event generation (wave W2).

**Two acquisition paths.** The preferred path is DrumSep output — the
`ogcm-drumsep` preset splits `drums.wav` into kick/snare/hat/cymbals/toms
stems, and `mine_one_shots` can then pull clean hits per stem. The fallback
path (`classify_hit`) mines a *mixed* drum stem and labels each onset by
spectral features — documented as a heuristic, not a substitute for real
separation. Callers that require separated stems should check for the
DrumSep output files first and refuse rather than silently classify a mix
(lane rule: fallback paths must be declarable).

**Drill grammar** (per R3 research + spec): half-time snare on beat 3,
optional ghost snare on the "and" of 4, syncopated kicks on a 3+3+2 accent
skeleton, hats alternating straight 1/16 with triplet bursts, and deliberate
gaps — hesitation over constant rolls. `drill_pattern` returns bar-relative
event lists; `render_drums` places mined one-shot buffers onto the grid.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

#: One-shot slicing bounds.
MAX_ONESHOT_MS = 500.0
MIN_ONESHOT_MS = 30.0
ONESHOT_FADE_MS = 5.0

#: Fallback-classifier spectral-centroid bounds (Hz). Calibrated for a mixed
#: drum stem at 44.1 kHz; deliberately conservative — ambiguous hits get
#: labelled "other" rather than guessed.
CENTROID_KICK_MAX = 900.0
CENTROID_HAT_MIN = 5500.0
SUB_BAND = (30.0, 110.0)
SNARE_BAND = (1500.0, 8000.0)

PIECE_ORDER = ("kick", "snare", "hat", "openhat", "cymbal", "tom", "other")


@dataclass
class OneShot:
    """A mined drum hit."""

    piece: str
    onset_s: float
    duration_s: float
    start_sample: int
    end_sample: int
    peak: float
    centroid_hz: float
    sub_ratio: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("onset_s", "duration_s", "peak", "centroid_hz", "sub_ratio", "confidence"):
            d[k] = round(float(d[k]), 4)
        return d


@dataclass
class DrumEvent:
    """A scheduled hit on the target grid."""

    bar: int
    beat: float            # position within the bar, in beats (0-based)
    time_s: float          # absolute position in the rendered grid
    piece: str
    velocity: float

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["time_s"] = round(float(d["time_s"]), 4)
        d["beat"] = round(float(d["beat"]), 4)
        return d


def _spectral_features(chunk: np.ndarray, sr: int) -> Tuple[float, float]:
    """(spectral centroid Hz, sub-band energy ratio) for a mono hit."""
    if chunk.size < 64:
        return 0.0, 0.0
    import librosa

    mag = np.abs(librosa.stft(chunk.astype(np.float32), n_fft=1024, hop_length=256))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
    total = mag.sum() + 1e-12
    centroid = float((mag.sum(axis=1) * freqs).sum() / total)
    sub = float(mag[(freqs >= SUB_BAND[0]) & (freqs < SUB_BAND[1])].sum() / total)
    return centroid, sub


def classify_hit(chunk: np.ndarray, sr: int) -> Tuple[str, float]:
    """Fallback spectral classifier for a mixed drum stem.

    Returns ``(piece, confidence)``. Deliberately emits ``"other"`` when the
    evidence is ambiguous — a wrong label on a mined kit is worse than an
    unused hit. Documented fallback: prefer DrumSep stems when available.
    """
    centroid, sub = _spectral_features(chunk, sr)
    if centroid <= 0:
        return "other", 0.0
    if centroid < CENTROID_KICK_MAX and sub > 0.35:
        return "kick", float(min(1.0, sub * 2))
    if centroid >= CENTROID_HAT_MIN:
        return "hat", float(min(1.0, centroid / 9000.0))
    if CENTROID_KICK_MAX <= centroid < CENTROID_HAT_MIN:
        # Mid-band: snare if there's real broadband energy, else tom/other.
        return "snare", 0.5
    return "other", 0.2


def mine_one_shots(
    y: np.ndarray,
    sr: int,
    piece_hint: Optional[str] = None,
    max_shots: int = 64,
    min_gap_ms: float = 60.0,
) -> List[OneShot]:
    """Extract drum one-shots from a (separated) drum stem.

    Args:
        y: Mono audio — ideally a single-kit-piece stem from DrumSep; on a
            mixed stem, `classify_hit` labels each onset.
        sr: Sample rate.
        piece_hint: If given (e.g. "kick" for a kick stem), every mined shot
            inherits that piece label and the classifier is skipped.
        max_shots: Cap on returned shots (strongest first).
        min_gap_ms: Onsets closer than this are merged (keeps the stronger).

    Returns:
        OneShot list sorted by onset time; audio slices are NOT stored —
        use `slice_one_shot` per event.
    """
    import librosa

    if y.ndim != 1:
        y = y.mean(axis=1)
    onset_frames = librosa.onset.onset_detect(
        y=y, sr=sr, units="frames", backtrack=True,
        pre_max=int(0.01 * sr / 512), post_max=int(0.01 * sr / 512) + 1,
    )
    onset_samples = librosa.frames_to_samples(onset_frames)
    if onset_samples.size == 0:
        return []

    # merge too-close onsets
    min_gap = int(min_gap_ms * sr / 1000.0)
    merged = [int(onset_samples[0])]
    for s in onset_samples[1:]:
        if s - merged[-1] >= min_gap:
            merged.append(int(s))
        elif abs(y[s]) > abs(y[merged[-1]]):
            merged[-1] = int(s)

    shots: List[OneShot] = []
    for i, start in enumerate(merged):
        end = merged[i + 1] if i + 1 < len(merged) else min(len(y), start + int(MAX_ONESHOT_MS * sr / 1000.0))
        end = min(end, start + int(MAX_ONESHOT_MS * sr / 1000.0))
        if end - start < int(MIN_ONESHOT_MS * sr / 1000.0):
            end = min(len(y), start + int(MIN_ONESHOT_MS * sr / 1000.0))
        chunk = y[start:end]
        if chunk.size == 0:
            continue
        centroid, sub = _spectral_features(chunk, sr)
        if piece_hint:
            piece, conf = piece_hint, 1.0
        else:
            piece, conf = classify_hit(chunk, sr)
        shots.append(
            OneShot(
                piece=piece,
                onset_s=start / sr,
                duration_s=(end - start) / sr,
                start_sample=start,
                end_sample=end,
                peak=float(np.abs(chunk).max()),
                centroid_hz=centroid,
                sub_ratio=sub,
                confidence=conf,
            )
        )

    shots.sort(key=lambda s: s.peak * s.confidence, reverse=True)
    shots = shots[:max_shots]
    shots.sort(key=lambda s: s.onset_s)
    return shots


def slice_one_shot(y: np.ndarray, shot: OneShot, sr: int, fade_ms: float = ONESHOT_FADE_MS) -> np.ndarray:
    """Cut a mined hit with a click-free release fade."""
    chunk = np.array(y[shot.start_sample : shot.end_sample], copy=True)
    n = int(sr * fade_ms / 1000.0)
    if chunk.size > 2 * n and n >= 2:
        t = np.linspace(0.0, np.pi / 2.0, n, dtype=np.float32)
        chunk[-n:] *= (np.sin(t) ** 2)[::-1]
    return chunk


# ---------------------------------------------------------------------------
# Drill grammar
# ---------------------------------------------------------------------------

def drill_pattern(bars: int = 4, ghost_snare: bool = True, hat_mode: str = "mix") -> List[Tuple[float, str, float]]:
    """Bar-relative drill events as ``(beat_in_bar, piece, velocity)``.

    Skeleton: half-time snare on beat 3; ghost on "and" of 4 (optional);
    kicks on a rotating 3+3+2 accent pattern; hats on 1/16 with a triplet
    burst in the last bar and periodic gaps.
    """
    events: List[Tuple[float, str, float]] = []
    # 3+3+2 kick accents across two bars (in sixteenth-note steps).
    kick_steps_cycle = (0, 3, 6, 8, 11, 14)
    for bar in range(bars):
        # snare — half-time on beat 3 (beat index 2), ghost on and-of-4 (3.5)
        events.append((bar * 4 + 2.0, "snare", 1.0))
        if ghost_snare and bar % 2 == 1:
            events.append((bar * 4 + 3.5, "snare", 0.45))
        # kicks — 3+3+2 accents, offset per bar cycle
        for step in kick_steps_cycle:
            events.append((bar * 4 + step / 4.0, "kick", 0.95 if step == 0 else 0.85))
        # hats
        for step in range(16):
            if hat_mode == "mix" and bar == bars - 1 and 8 <= step < 12:
                continue  # gap before the triplet burst
            vel = 0.8 if step % 4 == 0 else 0.55
            events.append((bar * 4 + step / 4.0, "hat", vel))
        if hat_mode == "mix" and bar == bars - 1:
            # triplet burst on the last beat of the last bar
            for k in range(6):
                events.append((bar * 4 + 3.0 + k / 6.0, "hat", 0.7))
        # open hat on the offbeat of 2 every other bar
        if bar % 2 == 0:
            events.append((bar * 4 + 1.5, "openhat", 0.6))
    events.sort(key=lambda e: e[0])
    return events


def grid_events(
    pattern: Sequence[Tuple[float, str, float]],
    bpm: float,
    start_beat: float = 0.0,
) -> List[DrumEvent]:
    """Project bar-relative pattern events onto an absolute timeline at `bpm`."""
    beat_s = 60.0 / bpm
    events = []
    for beat_in_pattern, piece, vel in pattern:
        abs_beat = start_beat + beat_in_pattern
        events.append(
            DrumEvent(
                bar=int(abs_beat // 4),
                beat=abs_beat % 4,
                time_s=abs_beat * beat_s,
                piece=piece,
                velocity=vel,
            )
        )
    return events


def render_drums(
    events: Sequence[DrumEvent],
    one_shots: Dict[str, np.ndarray],
    sr: int,
    total_s: float,
) -> np.ndarray:
    """Place one-shot buffers at event times into a mono buffer.

    `one_shots` maps piece name → audio (mono np.ndarray). Missing pieces are
    skipped, not synthesized — caller chooses the fallback policy.
    """
    n = int(total_s * sr) + sr
    out = np.zeros(n, dtype=np.float32)
    for ev in events:
        buf = one_shots.get(ev.piece)
        if buf is None:
            continue
        start = int(ev.time_s * sr)
        seg = buf[: max(1, n - start)]
        out[start : start + seg.size] += (seg * ev.velocity).astype(np.float32)
    return out
