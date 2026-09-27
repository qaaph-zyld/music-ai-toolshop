"""Bar-aligned loop-chop candidate extraction for the OGCM drill flip (wave W1).

**Why this module exists.** July's remix stretched the whole instrumental
buffer to a target BPM; the fix direction (spec: `.workspace_archive/plans/
ogcm-flip.spec.md`) is chop-and-rebuild — pick *phrase/bar-level* melodic
regions, retrigger them on a new grid, and never force a global stretch.

Candidate finding rides the same CPU-cheap machinery as `structure.py`:
beat-synchronous chroma, an affinity self-similarity matrix enhanced along the
time-lag diagonal, and the track's repetition classes. A candidate is a span of
N bars anchored on a downbeat; each is scored for loopability (seam similarity),
repetition (does the material recur — a one-off bridge is not a flip loop),
boundary proximity (section edges cut cleaner), and a duration prior that
prefers 2–4 bar loops. Vocal bleed in the bed is penalised when a vocal stem is
available for comparison.

**On tonal centers — an estimate, labelled as one.** A simple Krumhansl-style
template correlation on span-mean chroma reports the most probable pitch class
and mode plus a confidence. When a shift arm is applied the manifest reports
the resulting key name so GATE C knows what each (chop, shift) pair lands on —
whether that is a canonical minor depends on the *content* of the chop, not on
the source track's nominal key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

#: Candidate lengths in bars that get scored.
CANDIDATE_BAR_LENGTHS = (1, 2, 4, 8)
#: Score weights — seam and repetition carry the pick; boundary proximity and
#: duration prior are tiebreakers, bleed is a penalty.
W_SEAM = 0.4
W_SEQ = 0.6
W_BOUNDARY = 0.15
W_DURATION = 0.1
W_BLEED = 0.5
#: Shift arms offered at GATE C (UK-dark direction: pitch down).
PITCH_ARMS = (-1, -4, -5)
#: Microfade length applied at slice boundaries (ms).
MICROFADE_MS = 8.0
#: Search radius when snapping a cut to a zero crossing (ms).
ZERO_CROSS_SNAP_MS = 10.0

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Schmuckler templates (major / natural minor).
_KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass
class ChopCandidate:
    """One scored, bar-aligned loop candidate."""

    id: str
    start_s: float
    end_s: float
    start_sample: int
    end_sample: int
    bars: int
    segment_class: str
    repetitions: int
    seam_score: float
    seq_score: float
    boundary_score: float
    duration_score: float
    bleed_penalty: float
    score: float
    tonal_center: str
    tonal_mode: str
    tonal_confidence: float
    shift_keys: Dict[int, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("start_s", "end_s", "seam_score", "seq_score", "boundary_score",
                  "duration_score", "bleed_penalty", "score", "tonal_confidence"):
            d[k] = round(float(d[k]), 4)
        return d


def _pitch_class_name(pc: int) -> str:
    return NOTE_NAMES[pc % 12]


def estimate_tonal_center(chroma_mean: np.ndarray) -> Tuple[str, str, float]:
    """Estimate pitch class + mode from mean chroma via Krumhansl templates.

    Returns ``(root_name, mode, confidence)`` where mode is ``major`` or
    ``minor`` and confidence is the normalised margin over the runner-up
    key (0 = tie, i.e. distrust the label).
    """
    if chroma_mean.size != 12 or not np.isfinite(chroma_mean).all() or chroma_mean.max() <= 0:
        return "C", "major", 0.0
    x = chroma_mean.astype(float)
    x = x - x.mean()
    norm = np.linalg.norm(x)
    if norm <= 0:
        return "C", "major", 0.0
    x = x / norm
    scores = []
    for pc in range(12):
        for mode, tpl in (("major", _KS_MAJOR), ("minor", _KS_MINOR)):
            t = np.roll(tpl, pc).astype(float)
            t = t - t.mean()
            t = t / (np.linalg.norm(t) + 1e-12)
            scores.append((float(np.dot(x, t)), pc, mode))
    scores.sort(reverse=True)
    (s1, pc1, m1), (s2, _, _) = scores[0], scores[1]
    conf = (s1 - s2) / (abs(s1) + 1e-12)
    return _pitch_class_name(pc1), m1, float(np.clip(conf, 0.0, 1.0))


def shift_key(root: str, mode: str, semitones: int) -> str:
    """Key name after transposing `root` by `semitones` (mode preserved)."""
    try:
        pc = NOTE_NAMES.index(root)
    except ValueError:
        return f"{root}{mode}?"
    shifted = _pitch_class_name(pc + semitones)
    return f"{shifted} minor" if mode == "minor" else f"{shifted} major"


def snap_to_zero_crossing(y_mono: np.ndarray, sample: int, radius_s: float, sr: int) -> int:
    """Move a cut point to the nearest zero crossing within `radius_s`."""
    radius = int(radius_s * sr)
    lo = max(0, sample - radius)
    hi = min(len(y_mono), sample + radius + 1)
    if hi - lo < 2:
        return sample
    window = y_mono[lo:hi]
    sign = np.signbit(window)
    crossings = np.flatnonzero(sign[1:] != sign[:-1]) + lo + 1
    if crossings.size == 0:
        return sample
    return int(crossings[np.argmin(np.abs(crossings - sample))])


def apply_microfade(chunk: np.ndarray, sr: int, fade_ms: float = MICROFADE_MS) -> np.ndarray:
    """Raised-cosine fade in/out on a slice, in place. Works on (n,) or (n, ch)."""
    n = int(sr * fade_ms / 1000.0)
    if n < 2 or chunk.shape[0] < 2 * n:
        return chunk
    t = np.linspace(0.0, np.pi / 2.0, n, dtype=np.float32)
    fade_in = np.sin(t) ** 2
    fade_out = fade_in[::-1]
    if chunk.ndim == 1:
        chunk[:n] *= fade_in
        chunk[-n:] *= fade_out
    else:
        chunk[:n, :] *= fade_in[:, None]
        chunk[-n:, :] *= fade_out[:, None]
    return chunk


def _seam_score(sync_chroma: np.ndarray, start_col: int, end_col: int) -> float:
    """Cosine similarity between the last beat's chroma and the first beat's —
    a high score means the span loops back onto itself cleanly."""
    if end_col <= start_col or end_col >= sync_chroma.shape[1]:
        return 0.0
    a = sync_chroma[:, end_col]
    b = sync_chroma[:, start_col]
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))


def _repetition_score(
    lag: Optional[np.ndarray], ssm: np.ndarray, start_col: int, end_col: int
) -> float:
    """How strongly the span's material repeats *elsewhere* in the track.

    In lag coordinates column j = offset of j beats, so "repeats one span
    later" lives at lag ≈ span length. We take the mean over lag columns at
    and beyond the span length (lag-0 self-similarity is meaningless here).
    Falls back to the raw SSM's off-diagonal mean if the lag transform failed.
    """
    n = ssm.shape[0]
    if end_col > n or start_col >= n:
        return 0.0
    span = end_col - start_col
    if lag is not None and lag.shape[0] == n and lag.shape[1] > span:
        block = lag[start_col:end_col, span:]
        return float(np.clip(np.mean(np.clip(block, 0, None)), 0.0, 1.0)) if block.size else 0.0
    block = ssm[start_col:end_col]
    mask = np.ones_like(block, dtype=bool)
    mask[:, start_col:end_col] = False
    vals = block[:, mask.any(axis=1)] if mask.any() else block
    return float(np.clip(np.mean(np.clip(vals, 0, None)), 0.0, 1.0)) if vals.size else 0.0


def _boundary_score(novelty: np.ndarray, start_col: int, radius: int = 4) -> float:
    """Normalised novelty near the span start — candidates sitting on a section
    boundary cut cleaner."""
    if novelty.size == 0 or start_col >= novelty.size:
        return 0.0
    lo = max(0, start_col - radius)
    hi = min(novelty.size, start_col + radius + 1)
    return float(novelty[lo:hi].max())


def _duration_score(bars: int) -> float:
    """2–4 bar loops are the flip norm; 1-bar chops and 8-bar sections read less
    like a loop and more like a slice/arrangement."""
    return {1: 0.4, 2: 0.9, 4: 1.0, 8: 0.6}.get(bars, 0.3)


def _bleed_penalty(bed_env: np.ndarray, vocal_env: Optional[np.ndarray], start_col: int, end_col: int) -> float:
    """Residual-vocal estimate for the span: correlation between the bed's
    mid-band envelope and the vocal stem's envelope over the same columns.
    No vocal stem → 0 (unmeasured, not zero-risk)."""
    if vocal_env is None or vocal_env.size == 0:
        return 0.0
    n = min(bed_env.size, vocal_env.size)
    lo = min(start_col, n - 1)
    hi = min(end_col, n)
    if hi - lo < 4:
        return 0.0
    a = bed_env[lo:hi] - bed_env[lo:hi].mean()
    b = vocal_env[lo:hi] - vocal_env[lo:hi].mean()
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.clip(np.dot(a, b) / denom, 0.0, 1.0))


def find_candidates(
    y: np.ndarray,
    sr: int,
    y_vocal: Optional[np.ndarray] = None,
    bar_lengths: Sequence[int] = CANDIDATE_BAR_LENGTHS,
    top_n: int = 24,
) -> Dict[str, Any]:
    """Rank bar-aligned loop candidates in an instrumental bed.

    Args:
        y: Mono audio of the bed (caller's job to downmix).
        sr: Sample rate.
        y_vocal: Optional mono audio of the separated vocal stem (same
            timeline/sr as the bed). Its beat-synchronous RMS envelope is
            used to penalise residual bleed. None = unmeasured.
        bar_lengths: Candidate span lengths in bars.
        top_n: Manifest size cap.

    Returns:
        ``{"candidates": [...], "grid": {...}, "segments": [...], "method": ...}``
    """
    import librosa

    from .. import beatgrid as bg
    from .. import structure

    grid = bg.analyze_beats(y, sr)
    duration = len(y) / sr
    if not grid.beat_times or not grid.downbeat_times:
        return {
            "candidates": [],
            "grid": grid.to_dict(),
            "segments": [],
            "duration": round(duration, 3),
            "method": "no usable beat grid",
        }

    beat_times = np.asarray(grid.beat_times)
    downbeats = np.asarray(grid.downbeat_times)
    beat_frames = librosa.time_to_frames(beat_times, sr=sr)
    beat_frames = np.clip(beat_frames, 0, librosa.time_to_frames(duration, sr=sr) - 1)

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median) if beat_frames.size >= 2 else chroma

    vocal_env = None
    if y_vocal is not None and y_vocal.size:
        rms = librosa.feature.rms(y=y_vocal)[0]
        vocal_env = (
            librosa.util.sync(rms.reshape(1, -1), beat_frames, aggregate=np.mean)[0]
            if beat_frames.size >= 2
            else rms
        )

    ssm = librosa.segment.recurrence_matrix(sync, mode="affinity", width=3, sym=True)
    # Diagonal enhancement in the lag domain: median-filtering along the lag
    # axis turns sustained repetition into ridges instead of isolated dots.
    # In lag coordinates LAG[t, j] ≈ similarity(t, t+j), so a span whose
    # material recurs one span-length later shows a ridge at j == span length.
    try:
        from scipy.ndimage import median_filter

        lag = librosa.segment.timelag_filter(
            lambda m: median_filter(m, size=(1, 9)), pad=True
        )(ssm)
    except Exception:
        lag = None

    # Foote checkerboard novelty on the SSM for boundary proximity scoring.
    ksize = min(8, ssm.shape[0] // 4) if ssm.shape[0] >= 8 else 2
    kernel = np.ones((ksize, ksize))
    checker = np.block([[kernel, -kernel], [-kernel, kernel]])
    novelty = np.zeros(ssm.shape[0])
    for i in range(ksize, ssm.shape[0] - ksize):
        patch = ssm[i - ksize : i + ksize, i - ksize : i + ksize]
        novelty[i] = float((patch * checker).sum())
    if novelty.size and novelty.max() > 0:
        novelty = novelty / novelty.max()

    segs = structure.segment_track(y, sr)
    segments = segs.get("segments", [])

    # Map each downbeat to a beat-sync column index (downbeats are a subset of
    # beat_times by construction).
    beat_to_col = {round(float(t), 4): i for i, t in enumerate(beat_times)}
    down_cols = [beat_to_col.get(round(float(t), 4)) for t in downbeats]
    down_cols = [c for c in down_cols if c is not None]

    candidates: List[ChopCandidate] = []
    n_beats = sync.shape[1]
    for bars in bar_lengths:
        for i, start_col in enumerate(down_cols):
            end_beat_idx = i * grid.beats_per_bar + bars * grid.beats_per_bar
            if end_beat_idx >= len(beat_times):
                continue
            end_col = int(end_beat_idx)
            if end_col >= n_beats:
                end_col = n_beats - 1
            start_s = float(downbeats[i])
            end_s = float(beat_times[end_beat_idx]) if end_beat_idx < len(beat_times) else duration
            if end_s <= start_s:
                continue

            seg = next((s for s in segments if s["start"] <= start_s < s["end"]), None)
            seg_class = seg["segment_class"] if seg else "?"
            reps = seg["repetitions"] if seg else 1

            chroma_mean = sync[:, start_col:end_col].mean(axis=1) if end_col > start_col else sync[:, start_col]
            root, mode, conf = estimate_tonal_center(chroma_mean)

            seam = _seam_score(sync, start_col, end_col)
            rep = _repetition_score(lag, ssm, start_col, end_col)
            bound = _boundary_score(novelty, start_col)
            dur = _duration_score(bars)
            bleed = _bleed_penalty(
                np.asarray(sync.mean(axis=0)) if sync.ndim == 2 else np.zeros(n_beats),
                vocal_env, start_col, end_col,
            )

            score = (
                W_SEAM * seam
                + W_SEQ * rep
                + W_BOUNDARY * bound
                + W_DURATION * dur
                - W_BLEED * bleed
            )
            candidates.append(
                ChopCandidate(
                    id=f"cand_{len(candidates):03d}",
                    start_s=start_s,
                    end_s=end_s,
                    start_sample=int(start_s * sr),
                    end_sample=int(end_s * sr),
                    bars=bars,
                    segment_class=seg_class,
                    repetitions=reps,
                    seam_score=seam,
                    seq_score=rep,
                    boundary_score=bound,
                    duration_score=dur,
                    bleed_penalty=bleed,
                    score=score,
                    tonal_center=root,
                    tonal_mode=mode,
                    tonal_confidence=conf,
                    shift_keys={s: shift_key(root, mode, s) for s in PITCH_ARMS},
                )
            )

    candidates.sort(key=lambda c: c.score, reverse=True)
    top = candidates[:top_n]

    return {
        "candidates": [c.to_dict() for c in top],
        "grid": grid.to_dict(),
        "segments": segments,
        "duration": round(duration, 3),
        "method": "beat-sync chroma SSM + laplacian classes + seam/repetition/novelty scoring",
    }


def slice_candidate(
    audio: np.ndarray,
    sr: int,
    cand: Dict[str, Any],
    snap_ms: float = ZERO_CROSS_SNAP_MS,
    fade_ms: float = MICROFADE_MS,
) -> np.ndarray:
    """Cut a candidate out of full audio (mono or (n, ch)), snapped to zero
    crossings with microfades — click-free boundaries."""
    mono = audio if audio.ndim == 1 else audio.mean(axis=1)
    start = snap_to_zero_crossing(mono, int(cand["start_sample"]), snap_ms / 1000.0, sr)
    end = snap_to_zero_crossing(mono, int(cand["end_sample"]), snap_ms / 1000.0, sr)
    chunk = np.array(audio[start:end], copy=True)
    apply_microfade(chunk, sr, fade_ms)
    return chunk


def write_audition_pack(
    audio: np.ndarray,
    sr: int,
    manifest: Dict[str, Any],
    out_dir: Path,
    loops: int = 2,
) -> List[str]:
    """Render each candidate looped `loops` times to `out_dir` for GATE C."""
    import soundfile as sf

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for cand in manifest.get("candidates", []):
        chunk = slice_candidate(audio, sr, cand)
        rendered = np.tile(chunk, loops) if chunk.ndim == 1 else np.tile(chunk, (loops, 1))
        name = f"{cand['id']}_{cand['bars']}bar_{cand['tonal_center']}{cand['tonal_mode'][:3]}_score{cand['score']:.2f}.wav"
        sf.write(str(out_dir / name), rendered, sr)
        written.append(str(out_dir / name))
    return written


def write_manifest(manifest: Dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path
