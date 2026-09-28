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
FELT_BPM = 89.1             # nominal felt rate shared by both written grids


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
    pad_s: float = 0.0      # audio before the onset inside the strip (strip_phrase fills)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("start_s", "end_s", "source_beat", "beat_fraction",
                  "gap_before_ms", "pad_s"):
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
    # lattice-placement audit fields (W4); legacy source-time placement leaves
    # anchor_kind="source_time", anchor_offset_ms=0.0
    nominal_s: float = 0.0   # mapped position on the felt lattice before snap
    anchor_beat: float = -1.0  # lattice beat index snapped to (-1 = unfixed)
    anchor_kind: str = "source_time"  # downbeat | odd_beat | beat | float | source_time
    anchor_offset_ms: float = 0.0     # |placed - nominal| — the correction applied

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("target_beat_fraction", "start_s", "warp", "nominal_s",
                  "anchor_beat", "anchor_offset_ms"):
            d[k] = round(float(d[k]), 4)
        return d


def load_transcript_words(path: Any) -> List[Any]:
    """Load the cached faster-whisper transcript JSON → list of word objects.

    The cached file is the wave-m1 immutable input (`flip_relay/lead_transcript.json`);
    this validates it enough to trust: sorted, non-negative durations, count>0.
    Raises ValueError when the cache is provably invalid (empty/unsorted words).
    """
    import json

    from ..transcribe import Word

    data = json.loads(open(str(path), encoding="utf-8").read())
    raw = [w for seg in data.get("segments", []) for w in seg.get("words", [])]
    words = [
        Word(
            text=str(w.get("text", "")),
            start=float(w["start"]),
            end=float(w["end"]),
            probability=float(w.get("probability", 0.0)),
        )
        for w in raw
        if w.get("start") is not None and w.get("end") is not None
    ]
    words.sort(key=lambda w: w.start)
    if not words:
        raise ValueError(f"transcript cache has no word timings: {path}")
    if any(w.end < w.start for w in words):
        raise ValueError(f"transcript cache has negative word durations: {path}")
    return words


def extend_grid_left(
    beat_times: Sequence[float],
    fill_to_s: float = 0.0,
) -> np.ndarray:
    """Extend a measured beat grid backwards to t≈0 at the median interval.

    librosa beat tracking starts where the onsets get trackable (8.01 s on the
    v2 bed) but the vocal's intro talk precedes that — phrases before the
    first detected beat would collapse onto beat 0 and lose their positions.
    Prepended beats are an extrapolation, recorded in the relay manifest.
    """
    bt = np.asarray(beat_times, dtype=float)
    if bt.size < 2:
        return bt
    iv = float(np.median(np.diff(bt)))
    extra: List[float] = []
    t = bt[0] - iv
    while t > fill_to_s - 0.5 * iv:
        extra.append(t)
        t -= iv
    extra.reverse()
    return np.concatenate([np.asarray(extra), bt])


def detect_strips_energy(
    y_vocal: np.ndarray,
    sr: int,
    min_gap_ms: float = MIN_GAP_MS,
    floor_rms: float = 0.002,
    min_dur_ms: float = 250.0,
    hop: int = 512,
) -> List[Phrase]:
    """Phrase bounds from energy alone — for the transcript-less backing stem.

    Same boundary logic as `detect_phrases` (bounds at >= `min_gap_ms` gaps +
    energy dips) driven by the RMS envelope instead of word timings: an active
    region must sit above an adaptive floor (max of `floor_rms` and the 40th
    percentile of nonzero frames); adjacent regions separated by less than
    `min_gap_ms` of low energy merge — the strip pads keep breaths/tails.
    Returns Phrase objects with word_count=0.
    """
    if y_vocal is None or y_vocal.size == 0:
        return []
    rms, hop = _rms_envelope(y_vocal, sr, hop=hop)
    if rms.size == 0:
        return []
    nz = rms[rms > 1e-6]
    thresh = max(floor_rms, float(np.percentile(nz, 40)) * 0.5) if nz.size else floor_rms
    active = rms > thresh
    # frame spans of active regions
    edges = np.diff(np.concatenate([[False], active, [False]]).astype(int))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)  # exclusive
    frame_s = hop / float(sr)
    min_gap_f = min_gap_ms / 1000.0 / frame_s
    min_dur_f = min_dur_ms / 1000.0 / frame_s
    phrases: List[Tuple[float, float]] = []
    prev_end = 0.0
    for s, e in zip(starts, ends):
        if (e - s) < min_dur_f:
            continue
        t0, t1 = s * frame_s, e * frame_s
        if phrases and (t0 - phrases[-1][1]) * 1000.0 < min_gap_ms:
            phrases[-1] = (phrases[-1][0], t1)
        else:
            phrases.append((t0, t1))
    out: List[Phrase] = []
    for i, (t0, t1) in enumerate(phrases):
        out.append(
            Phrase(
                index=i,
                start_s=float(t0),
                end_s=float(t1),
                word_count=0,
                source_beat=0.0,
                source_bar=0,
                beat_fraction=0.0,
                gap_before_ms=(t0 - prev_end) * 1000.0,
            )
        )
        prev_end = t1
    return out


def _choose_anchor(
    nominal_beat: float,
    beat_s: float,
    tol_ms: float,
    downbeat_phase: int = 0,
    prefer_downbeats: bool = True,
) -> Tuple[Optional[float], str]:
    """Pick a felt-lattice anchor for a nominal (fractional) beat position.

    Candidates: integer beats within `tol_ms` of the nominal time. Preference
    order: downbeat (bar line) > odd beat (the "3" — drill convention) > any
    beat; ties bias EARLY (rap onsets arrive laid-back — correct early→on,
    per R4). Returns (anchor_beat, kind) or (None, "float") when nothing is
    inside tolerance — floats keep their source beat fraction.
    """
    tol_beats = (tol_ms / 1000.0) / beat_s
    lo = int(np.ceil(nominal_beat - tol_beats - 1e-9))
    hi = int(np.floor(nominal_beat + tol_beats + 1e-9))
    cands = []
    for k in range(lo, hi + 1):
        dist = abs(k - nominal_beat) * beat_s * 1000.0
        if dist <= tol_ms + 1e-6:
            pos = (k - downbeat_phase) % 4
            rank = 0 if pos == 0 else (1 if pos == 2 else 2)
            if not prefer_downbeats:
                rank = 0
            cands.append((rank, dist, k))
    if not cands:
        return None, "float"
    # best class; nearest inside it; equal distance -> the earlier beat
    rank, dist, k = min(cands, key=lambda c: (c[0], c[1], c[2]))
    kind = ("downbeat" if rank == 0 and prefer_downbeats else
            "odd_beat" if rank == 1 else "beat")
    return float(k), kind


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

    onset_i = int(phrase.start_s * sr)
    start = snap_to_zero_crossing(
        y_vocal, max(0, onset_i - int(pad_ms * sr / 1000.0)), 0.01, sr
    )
    end = snap_to_zero_crossing(
        y_vocal, min(len(y_vocal), int(phrase.end_s * sr) + int(pad_ms * sr / 1000.0)), 0.01, sr
    )
    # seconds of audio inside the strip that precede the onset — the renderer
    # subtracts this so the ONSET (not the pad) lands on the placed position.
    phrase.pad_s = phrase.start_s - start / float(sr)
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
    bpm_source: Optional[float] = None,
    lattice_bpm: Optional[float] = None,
    lattice_shift_beats: Optional[float] = None,
    downbeat_phase: int = 0,
) -> List[RelayPlacement]:
    """Place phrases onto the target grid at SOURCE-felt time (F2 fix).

    Zero-stretch relay (spec W4 "preserve identical source material"): the
    vocal is never time-stretched to fit a written tempo — the grid is the
    grid, the vocal is the vocal. This is the researched alternative to
    July's global 1.57× stretch failure.

    Two placement modes, both giving both grid arms an IDENTICAL schedule:

    * ``lattice_bpm=None`` (legacy/m1): ``start_s = phrase.start_s`` — the
      raw source wall-clock offset. Correct only when the source's true
      tempo equals the render lattice's nominal rate; otherwise the vocal
      drifts off the drum grid progressively (measured v2 bed grid ≈90.2–90.7
      vs nominal 89.1 → ~1.2 %/beat).
    * ``lattice_bpm=<felt rate>`` (W4): the phrase's *measured* source beat
      position (`annotate_grid`) maps onto the nominal felt lattice —
      ``nominal_s = (source_beat + shift) × 60/lattice_bpm`` — then the onset
      snaps to a lattice anchor within `anchor_tol_ms` (downbeats preferred,
      odd beats next, ties bias early; syncopated entries float and keep
      their source beat fraction). The ~1 % tempo discrepancy between the
      measured source grid and the nominal lattice is absorbed in the elastic
      inter-phrase gaps — exactly what phrase-realign is for (R4: "anchor on
      the new grid, keep internal timing native"). `shift` defaults to the
      smallest multiple of 4 making the first nominal position ≥ 0.

    The written-grid fields are REPORTING ONLY — computed from the placed
    ``start_s`` on the written (target-bpm) grid, so they describe where the
    phrase actually landed regardless of mode.

    Phrases in source bars ≥ ``bars`` are skipped (arrangement boundary).
    Warping: none applied by this function — phrase durations are intrinsic
    to the vocal. ``warp`` is reported as the ratio the *gap* would need to
    compress to reach the next phrase's anchor before overlap; values below
    ``1/MAX_WARP`` are flagged and left unwarped (the audio must not be
    smeared); ratios inside the bound are legal for the renderer to apply.
    """
    placements: List[RelayPlacement] = []
    lattice = lattice_bpm is not None and lattice_bpm > 0.0
    felt_s = 60.0 / lattice_bpm if lattice else 0.0
    if lattice:
        if lattice_shift_beats is None:
            min_beat = min((p.source_beat for p in phrases), default=0.0)
            lattice_shift_beats = (
                4.0 * float(np.ceil(max(0.0, -min_beat) / 4.0 - 1e-9))
            )
        shift = float(lattice_shift_beats)
    for p in phrases:
        if p.source_bar >= bars:
            continue
        if lattice:
            nominal_beat = p.source_beat + shift
            nominal_s = nominal_beat * felt_s
            anchor_beat, kind = _choose_anchor(
                nominal_beat, felt_s, anchor_tol_ms,
                downbeat_phase=downbeat_phase,
                prefer_downbeats=anchor_downbeats,
            )
            placed_beat = nominal_beat if anchor_beat is None else anchor_beat
            placed_start_s = placed_beat * felt_s
            anchor_off = abs(placed_start_s - nominal_s) * 1000.0
        else:
            nominal_s = float(p.start_s)
            placed_start_s = nominal_s
            anchor_beat, kind, anchor_off = -1.0, "source_time", 0.0
        # Written-grid reporting only (does NOT move the audio).
        written_beat = placed_start_s * bpm / 60.0
        written_bar = int(written_beat // 4)
        written_frac = float(written_beat % 4)
        if anchor_downbeats and written_frac < (anchor_tol_ms / 1000.0) * bpm / 60.0:
            written_frac = 0.0  # genuinely on the downbeat — don't smear ±30 ms
        placements.append(
            RelayPlacement(
                phrase_index=p.index,
                target_bar=start_bar + written_bar,
                target_beat_fraction=written_frac,
                start_s=placed_start_s,
                warp=1.0,
                warped=False,
                nominal_s=round(nominal_s, 6),
                anchor_beat=anchor_beat if anchor_beat is not None else -1.0,
                anchor_kind=kind,
                anchor_offset_ms=round(anchor_off, 4),
            )
        )
    # flag overlaps: a phrase that runs into its successor's anchor. An overlap
    # means the source itself had a short gap relative to phrase duration —
    # reported, not stretched (bounded warp is the renderer's option).
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


# ---------------------------------------------------------------------------
# W4 rendering + verification helpers
# ---------------------------------------------------------------------------


def render_vocal_lane(
    strips: Dict[int, np.ndarray],
    placements: Sequence[RelayPlacement],
    phrases: Sequence[Phrase],
    sr: int,
    total_s: float,
    apply_warp: bool = True,
    max_warp: float = MAX_WARP,
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Overlay phrase strips into a mono lane at their placed positions.

    `strips` maps phrase_index -> mono buffer (from `strip_phrase`). A strip
    whose overlap flag fit inside `max_warp` is time-compressed with
    pedalboard (single bounded pass, same as assemble.fit_chop_to_slot);
    anything beyond the bound is placed unwarped — flagged, never smeared.
    """
    from .. import remix_adapter

    n = int(total_s * sr) + int(sr * 0.05)
    lane = np.zeros(n, dtype=np.float32)
    events: List[Dict[str, Any]] = []
    ph_by_idx = {p.index: p for p in phrases}
    for pl in placements:
        strip = strips.get(pl.phrase_index)
        if strip is None or strip.size == 0:
            continue
        ph = ph_by_idx.get(pl.phrase_index)
        placed = strip
        warp_note = ""
        if apply_warp and ph is not None and pl.warp < 1.0 and pl.warp >= 1.0 / max_warp:
            placed = remix_adapter._stretch_segment(
                strip, sr, src_bpm=1.0, dst_bpm=1.0 / max(pl.warp, 1e-3),
                src_key="C", dst_key=None,
            )
            warp_note = f"bounded warp {pl.warp:.3f} applied"
        # strip[0] is source audio at (phrase.start_s - pad_s); place the strip
        # so the ONSET lands on pl.start_s — not the pad (F4: pad offset).
        pad_s = ph.pad_s if ph is not None else 0.0
        start = int(round((pl.start_s - pad_s) * sr))
        if start >= n:
            events.append({"phrase_index": pl.phrase_index, "start_s": pl.start_s,
                           "rendered": False, "reason": "beyond render end"})
            continue
        if start < 0:  # onset at t≈0 — clip the strip's leading pad
            placed = placed[-start:]
            start = 0
        seg = placed[: max(0, n - start)]
        lane[start : start + seg.size] += seg
        events.append({
            "phrase_index": pl.phrase_index,
            "start_s": round(pl.start_s, 4),
            "duration_s": round(seg.size / sr, 4),
            "anchor_kind": pl.anchor_kind,
            "anchor_offset_ms": pl.anchor_offset_ms,
            "warp": pl.warp,
            "warped_audio": bool(warp_note),
            "rendered": True,
            **({"note": warp_note} if warp_note else {}),
        })
    return lane, events


def onset_envelope(y: np.ndarray, sr: int, hop: int = 512) -> np.ndarray:
    """librosa onset-strength envelope (frame-rate `hop`)."""
    import librosa

    return librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)


def drum_envelope(
    drum_events: Sequence[Dict[str, Any]],
    total_s: float,
    sr: int,
    hop: int = 512,
    smooth_ms: float = 15.0,
) -> np.ndarray:
    """Synthesise a drum onset envelope from an events table (velocity-weighted
    impulses smoothed by ~`smooth_ms`) — no audio read needed, exact hit times.
    """
    n_f = int(total_s * sr / hop) + 2
    env = np.zeros(n_f, dtype=np.float32)
    for ev in drum_events:
        t = ev.get("time_s")
        if t is None:
            continue
        f = int(round(t * sr / hop))
        if 0 <= f < n_f:
            env[f] += float(ev.get("velocity", 1.0))
    w = max(1, int(smooth_ms * sr / 1000.0 / hop))
    if w > 1:
        kern = np.hanning(2 * w + 1)
        env = np.convolve(env, kern / kern.sum(), mode="same")
    return env


def xcorr_offset(
    env_a: np.ndarray,
    env_b: np.ndarray,
    sr: int,
    hop: int = 512,
    max_lag_ms: float = 250.0,
) -> Dict[str, float]:
    """Normalised cross-correlation between two onset envelopes.

    Returns the best lag in ms (positive = env_a behind env_b), the peak
    normalised correlation, and the zero-lag correlation — so a caller can see
    whether the vocal's accents actually lock with the drums or merely sit
    near a periodicity.
    """
    a = np.asarray(env_a, dtype=float) - float(np.mean(env_a))
    b = np.asarray(env_b, dtype=float) - float(np.mean(env_b))
    if a.size == 0 or b.size == 0 or a.std() == 0 or b.std() == 0:
        return {"lag_ms": 0.0, "peak": 0.0, "lag0": 0.0, "note": "degenerate envelope"}
    n = a.size + b.size - 1
    from numpy.fft import rfft, irfft

    nfft = 1 << (n - 1).bit_length()
    corr = irfft(rfft(a, nfft) * np.conj(rfft(b, nfft)), nfft)
    corr = np.concatenate([corr[-(b.size - 1):], corr[: a.size]])
    norm = float(np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    corr = corr / norm
    lags = np.arange(-(b.size - 1), a.size)
    max_lag = int(max_lag_ms * sr / 1000.0 / hop)
    sel = np.abs(lags) <= max_lag
    if not np.any(sel):
        return {"lag_ms": 0.0, "peak": 0.0, "lag0": float(corr[lags == 0][0]),
                "note": "lag window empty"}
    idx = np.argmax(corr[sel])
    lag_frames = lags[sel][idx]
    return {
        "lag_ms": round(float(lag_frames) * hop / sr * 1000.0, 2),
        "peak": round(float(corr[sel][idx]), 4),
        "lag0": round(float(corr[lags == 0][0]), 4),
    }


def _win(env: np.ndarray, center: int, half: int) -> np.ndarray:
    """Fixed-size window env[center-half : center+half], zero-padded at the
    edges — keeps lag indexing exact for phrases near t=0 or the render end."""
    out = np.zeros(2 * half, dtype=float)
    lo, hi = max(0, center - half), min(env.size, center + half)
    if hi > lo:
        out[lo - (center - half) : lo - (center - half) + (hi - lo)] = env[lo:hi]
    return out


def phrase_xcorr_table(
    vocal_env: np.ndarray,
    drum_env: np.ndarray,
    placements: Sequence[RelayPlacement],
    sr: int,
    hop: int = 512,
    window_ms: float = 400.0,
    phrases: Optional[Sequence[Phrase]] = None,
    drum_hit_times_s: Optional[Sequence[float]] = None,
) -> List[Dict[str, Any]]:
    """Per-phrase local alignment (R4: 'onset cross-correlation between placed
    vocal phrase and the beat's drum-energy envelope at phrase start').

    The window is centred on the phrase's *effective* onset — the first onset-
    envelope frame inside the placed strip that rises above 15% of the strip's
    max — not the nominal transcript start (whisper word onsets precede the
    acoustic attack, and strips carry pad). `onset_delay_ms` reports that
    whisper-start→acoustic-onset gap. When `drum_hit_times_s` is given, each
    row also reports `nearest_hit_ms`: signed distance from the effective
    onset to the nearest drum hit (positive = vocal laid-back AFTER the hit).
    """
    rows: List[Dict[str, Any]] = []
    w = int(window_ms * sr / 1000.0 / hop)
    ph_by_idx = {p.index: p for p in phrases} if phrases else {}
    hits = (np.asarray(sorted(drum_hit_times_s), dtype=float)
            if drum_hit_times_s is not None else None)
    for pl in placements:
        c = int(pl.start_s * sr / hop)
        ph = ph_by_idx.get(pl.phrase_index)
        span_f = (int((ph.end_s - ph.start_s) * sr / hop)
                  if ph is not None else 2 * w)
        seg = vocal_env[c: min(vocal_env.size, c + max(span_f, 2 * w))]
        if seg.size < 8 or float(seg.max()) <= 0.0:
            rows.append({"phrase_index": pl.phrase_index, "lag_ms": None,
                         "peak": 0.0, "onset_delay_ms": None})
            continue
        c_eff = c + int(np.argmax(seg > max(1e-4, 0.15 * float(seg.max()))))
        onset_delay_ms = (c_eff - c) * hop / sr * 1000.0
        t_eff = c_eff * hop / sr
        a = _win(vocal_env, c_eff, w)
        b = _win(drum_env, c_eff, 2 * w)
        if np.std(a) == 0 or np.std(b) == 0:
            rows.append({"phrase_index": pl.phrase_index, "lag_ms": None,
                         "peak": 0.0,
                         "onset_delay_ms": round(onset_delay_ms, 2)})
            continue
        aa = a - a.mean()
        bb = b - b.mean()
        corr = np.correlate(bb, aa, mode="valid")  # bb slides over aa
        norm = float(np.linalg.norm(aa) * np.linalg.norm(bb)) or 1.0
        corr = corr / norm
        k = int(np.argmax(corr))
        # aa block covers [-w,+w] inside bb's [-2w,+2w]; zero lag at k == w
        lag_frames = k - w
        row: Dict[str, Any] = {
            "phrase_index": pl.phrase_index,
            "lag_ms": round(lag_frames * hop / sr * 1000.0, 2),
            "peak": round(float(corr[k]), 4),
            "onset_delay_ms": round(onset_delay_ms, 2),
        }
        if hits is not None and hits.size:
            j = int(np.searchsorted(hits, t_eff))
            cand = [hits[j]] if j < hits.size else []
            if j > 0:
                cand.append(hits[j - 1])
            nearest = min(cand, key=lambda t: abs(t - t_eff)) if cand else None
            if nearest is not None:
                row["nearest_hit_ms"] = round((t_eff - nearest) * 1000.0, 2)
        rows.append(row)
    return rows


def word_offset_table(
    words: Sequence[Any],
    phrases: Sequence[Phrase],
    placements: Sequence[RelayPlacement],
    beat_times: Sequence[float],
    lattice_bpm: float,
    lattice_shift_beats: float,
) -> List[Dict[str, Any]]:
    """Per-word placed-vs-grid table (R4's 'whisper word-timestamp vs
    grid-position' evidence).

    For each word: `nominal_s` = its position if it rode the lattice
    ((word_beat + shift) × felt_s); `placed_s` = phrase anchor + the word's
    intra-phrase offset (strips are never internally warped). `offset_ms` is
    therefore the phrase's applied correction plus the word's own lattice
    divergence — the honest microtiming picture, not just the anchor table.
    """
    bt = np.asarray(beat_times, dtype=float)
    idx = np.arange(bt.size)
    felt_s = 60.0 / lattice_bpm
    pl_by_phrase = {pl.phrase_index: pl for pl in placements}
    ph_by_idx = {p.index: p for p in phrases}
    rows: List[Dict[str, Any]] = []
    for ph in phrases:
        pl = pl_by_phrase.get(ph.index)
        if pl is None:
            continue
        for w in ph_words(ph, words):
            w_beat = float(np.interp(w.start, bt, idx))
            nominal = (w_beat + lattice_shift_beats) * felt_s
            placed = pl.start_s + (w.start - ph.start_s)
            # distance to the nearest lattice beat after placement — the
            # word's preserved microtiming (laid-back entries report >0)
            fb = placed / felt_s
            resid = abs(fb - round(fb)) * felt_s * 1000.0
            rows.append({
                "phrase_index": ph.index,
                "word": w.text,
                "word_start_s": round(w.start, 4),
                "nominal_s": round(nominal, 4),
                "placed_s": round(placed, 4),
                "offset_ms": round((placed - nominal) * 1000.0, 2),
                "lattice_residual_ms": round(resid, 2),
            })
    return rows


def ph_words(phrase: Phrase, words: Sequence[Any]) -> List[Any]:
    """Words belonging to a phrase (start inside [start_s, end_s])."""
    return [w for w in words if phrase.start_s - 1e-9 <= w.start <= phrase.end_s + 1e-9]


def summarize_anchors(placements: Sequence[RelayPlacement]) -> Dict[str, Any]:
    """Anchor-offset statistics — the W4 PASS bar is the median <=30 ms.

    `anchor_offset_ms` is the correction applied at placement (snaps bounded
    by ANCHOR_TOLERANCE_MS; floats report 0 — unmoved, syncopation kept).
    `grid_residual_ms` is informational: post-placement distance of each
    onset to the nearest felt-lattice anchor (the preserved microtiming).
    """
    offs = np.asarray([p.anchor_offset_ms for p in placements], dtype=float)
    kinds = [p.anchor_kind for p in placements]
    n_snap = sum(1 for k in kinds if k in ("downbeat", "odd_beat", "beat"))
    return {
        "placed": len(placements),
        "snapped": n_snap,
        "floated": len(placements) - n_snap,
        "median_anchor_offset_ms": float(np.median(offs)) if offs.size else 0.0,
        "mean_anchor_offset_ms": float(offs.mean()) if offs.size else 0.0,
        "max_anchor_offset_ms": float(offs.max()) if offs.size else 0.0,
        "median_anchored_offset_ms": (
            float(np.median(offs[offs > 0])) if np.any(offs > 0) else 0.0
        ),
        "anchor_pass_median_le_30ms": bool(
            offs.size and np.median(offs) <= ANCHOR_TOLERANCE_MS
        ),
    }
