"""Vocal phrase re-lay onto the new grid (wave W4).

**Why not a global stretch.** July's failure mode was stretching the acapella
1.57× to hit the target tempo — the flow smears and nothing lands on the
grid. The researched alternative treats the vocal as *phrases*: detect the
gaps the rapper already leaves, cut there, and re-anchor each phrase onset
on the target grid while preserving its internal timing. Per-phrase warping
is bounded (≤1.25× by spec) — a phrase that needs more than that to reach
the next downbeat is placed un-stretched and flagged in the manifest.

**Anchoring — beat fraction, not downbeat-or-bust.** Rap entries are often
syncopated (the "and" of 4, the "a" of 1). Blindly snapping every phrase to
a bar downbeat quantizes that swing away. `source_beat_fraction` records
where in the source bar the phrase starts (0.0–3.999 beats into the bar);
`map_phrases` lands it at the same fraction of a *target* bar. Downbeat
entries (fraction ≈ 0.0) stay on downbeats; syncopated entries stay
syncopated.

**Jitter-robust boundaries.** faster-whisper word timings vary run-to-run
(this repo's transcribe.py documents 154 vs 194 words back-to-back on the
same file). A single 300 ms gap threshold would be brittle, so a phrase
boundary requires BOTH a word gap ≥ `min_gap_ms` AND a local energy dip in
the vocal — either alone can be a transcription artifact.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

MIN_GAP_MS = 300.0
PAD_MS = 60.0
MAX_WARP = 1.25
ANCHOR_TOLERANCE_MS = 30.0


@dataclass
class Phrase:
    """A contiguous run of words bounded by real silence."""

    index: int
    start_s: float          # first word onset
    end_s: float            # last word offset
    word_count: int
    source_beat: float      # absolute beat position on the source grid
    source_bar: int         # source bar index
    beat_fraction: float    # position within the source bar (0–3.999)
    gap_before_ms: float    # silence preceding this phrase

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("start_s", "end_s", "source_beat", "beat_fraction", "gap_before_ms"):
            d[k] = round(float(d[k]), 4)
        return d


@dataclass
class RelayPlacement:
    """Where one phrase lands on the target grid."""

    phrase_index: int
    target_bar: int
    target_beat_fraction: float
    start_s: float          # absolute time on the target grid
    warp: float             # applied duration ratio (1.0 = none)
    warped: bool
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("target_beat_fraction", "start_s", "warp"):
            d[k] = round(float(d[k]), 4)
        return d


def _rms_envelope(y: np.ndarray, sr: int, hop: int = 512) -> Tuple[np.ndarray, int]:
    import librosa

    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    return rms, hop


def _energy_dip(rms: np.ndarray, sr: int, hop: int, t_s: float, window_ms: float = 200.0) -> bool:
    """True if RMS at t_s sits in the lower third of its ±window_ms context —
    a relative dip, robust to overall loudness drift."""
    if rms.size < 5:
        return False
    center = int(t_s * sr / hop)
    half = max(1, int(window_ms * sr / 1000.0 / hop))
    lo, hi = max(0, center - half), min(rms.size, center + half + 1)
    window = rms[lo:hi]
    if window.size < 3:
        return False
    return rms[min(center, rms.size - 1)] <= np.percentile(window, 35)


def detect_phrases(
    words: Sequence[Any],
    y_vocal: Optional[np.ndarray],
    sr: int,
    min_gap_ms: float = MIN_GAP_MS,
) -> List[Phrase]:
    """Group transcript words into phrases at confirmed silences.

    A boundary needs a word gap ≥ `min_gap_ms`; when a vocal buffer is
    provided the gap must ALSO coincide with an energy dip. Without audio,
    the gap alone decides (documented degradation — jitter can split a
    phrase).
    """
    if not words:
        return []
    rms, hop = _rms_envelope(y_vocal, sr) if y_vocal is not None else (None, sr)
    sorted_words = sorted(words, key=lambda w: w.start)
    phrases: List[List[Any]] = [[sorted_words[0]]]
    for w in sorted_words[1:]:
        gap_ms = (w.start - phrases[-1][-1].end) * 1000.0
        boundary = gap_ms >= min_gap_ms
        if boundary and rms is not None:
            # Probe the gap midpoint — the phrase end still carries the
            # decaying tail of the last word.
            mid_s = (phrases[-1][-1].end + w.start) / 2.0
            boundary = _energy_dip(rms, sr, hop, mid_s)
        if boundary:
            phrases.append([w])
        else:
            phrases[-1].append(w)

    out: List[Phrase] = []
    prev_end = 0.0
    for i, grp in enumerate(phrases):
        out.append(
            Phrase(
                index=i,
                start_s=float(grp[0].start),
                end_s=float(grp[-1].end),
                word_count=len(grp),
                source_beat=0.0,   # filled by annotate_grid
                source_bar=0,
                beat_fraction=0.0,
                gap_before_ms=(grp[0].start - prev_end) * 1000.0,
            )
        )
        prev_end = grp[-1].end
    return out


def annotate_grid(
    phrases: List[Phrase],
    beat_times: Sequence[float],
    beats_per_bar: int = 4,
) -> List[Phrase]:
    """Fill each phrase's source_beat/source_bar/beat_fraction from the
    source track's beat grid (interpolation between detected beats)."""
    bt = np.asarray(beat_times, dtype=float)
    if bt.size < 2:
        return phrases
    beat_index = np.arange(bt.size)
    for p in phrases:
        # interpolate fractional beat position at phrase start
        pos = np.interp(p.start_s, bt, beat_index)
        p.source_beat = float(pos)
        p.source_bar = int(pos // beats_per_bar)
        p.beat_fraction = float(pos % beats_per_bar)
    return phrases


def strip_phrase(
    y_vocal: np.ndarray,
    sr: int,
    phrase: Phrase,
    pad_ms: float = PAD_MS,
) -> np.ndarray:
    """Extract one phrase with a small pad + microfade — the bleed between
    phrases stays in the source buffer."""
    from .chops import apply_microfade, snap_to_zero_crossing

    start = snap_to_zero_crossing(
        y_vocal, max(0, int(phrase.start_s * sr) - int(pad_ms * sr / 1000.0)), 0.01, sr
    )
    end = snap_to_zero_crossing(
        y_vocal, min(len(y_vocal), int(phrase.end_s * sr) + int(pad_ms * sr / 1000.0)), 0.01, sr
    )
    chunk = np.array(y_vocal[start:end], copy=True)
    apply_microfade(chunk, sr)
    return chunk


def map_phrases(
    phrases: Sequence[Phrase],
    bpm: float,
    bars: int,
    start_bar: int = 0,
    preserve_fraction: bool = True,
    anchor_downbeats: bool = True,
    anchor_tol_ms: float = ANCHOR_TOLERANCE_MS,
) -> List[RelayPlacement]:
    """Place phrases onto the target grid.

    Each source bar maps 1:1 to a target bar (`start_bar + source_bar`);
    the phrase's within-bar position is preserved as `beat_fraction` when
    `preserve_fraction` is set, else quantized to the bar downbeat.
    Phrases in source bars ≥ `bars` are skipped (arrangement boundary).

    Warping: none here — phrase durations are intrinsic to the vocal. The
    *gap* between successive phrases is what compresses/expands. `warp` is
    reported as the ratio needed to reach the next phrase's anchor before
    overlap; > MAX_WARP is flagged and left unwarped (the arrangement must
    re-seat it, the audio must not be smeared).
    """
    beat_s = 60.0 / bpm
    placements: List[RelayPlacement] = []
    for p in phrases:
        if p.source_bar >= bars:
            continue
        frac = p.beat_fraction if preserve_fraction else 0.0
        if anchor_downbeats and frac < (anchor_tol_ms / 1000.0) / beat_s:
            frac = 0.0  # genuinely on the downbeat — don't smear ±30 ms of noise
        target_beat = (start_bar + p.source_bar) * 4.0 + frac
        placements.append(
            RelayPlacement(
                phrase_index=p.index,
                target_bar=start_bar + p.source_bar,
                target_beat_fraction=frac,
                start_s=target_beat * beat_s,
                warp=1.0,
                warped=False,
            )
        )
    # flag overlaps: a phrase that runs into its successor's anchor
    for i in range(len(placements) - 1):
        cur, nxt = placements[i], placements[i + 1]
        ph = phrases[cur.phrase_index]
        dur = ph.end_s - ph.start_s
        needed = (nxt.start_s - cur.start_s) / max(dur, 1e-6)
        if needed < 1.0:
            cur.warp = round(max(needed, 0.5), 4)
            cur.warped = needed >= 1.0 / MAX_WARP and needed != 1.0
            if not cur.warped:
                cur.notes.append(
                    f"overlap: needs {needed:.2f}× (> {MAX_WARP}× bound); unwarped"
                )
    return placements


def relay_manifest(
    phrases: Sequence[Phrase],
    placements: Sequence[RelayPlacement],
    bpm: float,
    source_path: str,
) -> Dict[str, Any]:
    """Deterministic relay evidence: which phrase went where and how much
    the timing had to bend to get there."""
    return {
        "bpm": bpm,
        "source": source_path,
        "phrase_count": len(phrases),
        "placed": len(placements),
        "phrases": [p.to_dict() for p in phrases],
        "placements": [p.to_dict() for p in placements],
        "warped_count": sum(1 for p in placements if p.warped),
    }
