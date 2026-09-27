"""Buffer-based beat assembly for the dual-grid renders (wave W3).

**Why buffers, not MIDI.** Both R2 research reports converged on placing
audio directly into NumPy buffers on the target grid — no DAW roundtrip, no
MIDI/SF2 detour, every event auditable in the manifest. A chop is triggered
like a sampler note: slice → optional bounded stretch to fit the slot →
optional pitch shift to the shift arm → zero-cross-snapped, microfaded
placement at an absolute grid time.

**Bounded per-chop stretch.** Whole-file stretching is explicitly rejected
by the spec (July failure). Each chop may be stretched only to fill its slot
when `fit_slot=True`, and the caller must accept the implied ratio —
`max_stretch` (default 1.25, the spec's per-phrase ceiling) refuses and
returns the unfitted chop so the arrangement can choose a different slot.

**Dual grid.** `render_beat` is grid-agnostic: the caller passes `bpm` and
the same arrangement for 178.2-written/89.1-felt and 133.65 renders. Nothing
in this module knows which grid is "the winner" — that is the W5 blind A/B.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import chops as _chops

MAX_STRETCH = 1.25


@dataclass
class Placement:
    """One chop trigger: candidate audio placed at a grid beat."""

    candidate_id: str
    start_beat: float          # position on the target grid (beats from 0)
    length_beats: float        # slot length on the target grid
    semitones: float = 0.0     # UK-dark arm: negative = pitch down
    gain: float = 1.0
    fit_slot: bool = False     # bounded-stretch the chop to fill the slot


@dataclass
class RenderResult:
    audio: np.ndarray
    sr: int
    bpm: float
    events: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def fit_chop_to_slot(
    chunk: np.ndarray,
    sr: int,
    src_bpm: float,
    slot_beats: float,
    src_span_beats: float,
    dst_bpm: float,
    semitones: float = 0.0,
    max_stretch: float = MAX_STRETCH,
) -> Tuple[np.ndarray, float, bool]:
    """Bounded per-chop stretch + pitch shift to land a chop in its slot.

    The implied stretch is `slot_seconds / chop_seconds` where chop_seconds is
    derived from its span on the *source* grid. Returns
    ``(audio, applied_ratio, fitted)``; when the ratio would exceed
    `max_stretch` the chop is returned pitch-shifted but unstretched and
    `fitted=False` — the arrangement, not the stretcher, absorbs the
    difference.
    """
    from .. import remix_adapter

    slot_s = slot_beats * 60.0 / dst_bpm
    chop_s = src_span_beats * 60.0 / src_bpm
    # `dur_ratio` is the duration multiplier (target/source); pedalboard's
    # stretch_factor is the inverse (a tempo multiplier, out_len = in/factor).
    dur_ratio = slot_s / chop_s if chop_s > 0 else 1.0
    if abs(dur_ratio - 1.0) > (max_stretch - 1.0) + 1e-9:
        fitted = False
        stretch_factor = 1.0
    else:
        fitted = True
        stretch_factor = 1.0 / dur_ratio
    # Single pedalboard pass: pitch_shift_in_semitones rides the same call —
    # two passes would double the phase-vocoder artifacts the spec rejects.
    out = remix_adapter._stretch_segment(
        chunk,
        sr,
        src_bpm=1.0,
        dst_bpm=stretch_factor,
        src_key="C",
        dst_key=_name_for_shift(semitones) if abs(semitones) > 1e-6 else None,
    )
    return out, float(dur_ratio if fitted else 1.0), fitted


def _name_for_shift(semitones: float) -> str:
    """_stretch_segment takes key names; we only need a semitone distance, so
    express the shift as C→(C+st) major."""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    pc = int(round(semitones)) % 12
    return names[pc]


def render_beat(
    bed: np.ndarray,
    sr: int,
    manifest: Dict[str, Any],
    placements: Sequence[Placement],
    bpm: float,
    drum_events: Optional[Sequence[Any]] = None,
    one_shots: Optional[Dict[str, np.ndarray]] = None,
    bass808_audio: Optional[np.ndarray] = None,
    src_bpm: Optional[float] = None,
    total_beats: Optional[float] = None,
    mix_levels: Optional[Dict[str, float]] = None,
) -> RenderResult:
    """Assemble chops + drums + 808 onto the grid at `bpm`.

    Args:
        bed: Source instrumental mono buffer (candidates are sliced from it).
        sr: Sample rate.
        manifest: `find_candidates` output (candidates carry sample positions
            + span metadata).
        placements: Chop triggers on the target grid.
        bpm: Target grid BPM.
        drum_events: `drums.grid_events` output.
        one_shots: piece→buffer map for `drums.render_drums`.
        bass808_audio: pre-rendered 808 lane (from `bass808.render_808`),
            aligned to the same t=0.
        src_bpm: Source tempo for slot-fitting math (default: manifest grid).
        total_beats: Render length; default = end of last placement + 1 bar.
        mix_levels: {"chop": g, "drums": g, "808": g} gains.
    """
    levels = {"chop": 1.0, "drums": 1.0, "808": 1.0, **(mix_levels or {})}
    src_bpm = src_bpm or float(manifest.get("grid", {}).get("tempo", 89.1))
    cand_by_id = {c["id"]: c for c in manifest.get("candidates", [])}

    beat_s = 60.0 / bpm
    if total_beats is None:
        last = max((p.start_beat + p.length_beats for p in placements), default=0.0)
        total_beats = last + 4.0
    total_s = total_beats * beat_s
    n = int(total_s * sr) + sr
    chop_lane = np.zeros(n, dtype=np.float32)
    warnings: List[str] = []
    events: List[Dict[str, Any]] = []

    for p in placements:
        cand = cand_by_id.get(p.candidate_id)
        if cand is None:
            warnings.append(f"unknown candidate {p.candidate_id}; skipped")
            continue
        chunk = _chops.slice_candidate(bed, sr, cand)
        src_span_beats = cand["bars"] * 4.0
        placed = chunk
        ratio, fitted = 1.0, True
        if p.fit_slot:
            placed, ratio, fitted = fit_chop_to_slot(
                chunk, sr, src_bpm, p.length_beats, src_span_beats, bpm,
                semitones=p.semitones,
            )
            if not fitted:
                warnings.append(
                    f"{p.candidate_id}: implied stretch {ratio:.2f} exceeds "
                    f"{MAX_STRETCH}; placed unfitted"
                )
        elif abs(p.semitones) > 1e-6:
            placed, _, _ = fit_chop_to_slot(
                chunk, sr, src_bpm, p.length_beats, src_span_beats, bpm,
                semitones=p.semitones, max_stretch=1.0,
            )
        start = int(p.start_beat * beat_s * sr)
        seg = placed[: max(1, n - start)]
        chop_lane[start : start + seg.size] += (seg * p.gain * levels["chop"]).astype(np.float32)
        events.append(
            {
                "candidate_id": p.candidate_id,
                "start_beat": p.start_beat,
                "time_s": round(start / sr, 4),
                "semitones": p.semitones,
                "stretch": round(ratio, 4),
                "fitted": fitted,
            }
        )

    drums_lane = np.zeros(n, dtype=np.float32)
    if drum_events and one_shots:
        from . import drums as _drums

        drums_lane[:n] = _drums.render_drums(drum_events, one_shots, sr, total_s)[:n]
        drums_lane *= levels["drums"]

    sub_lane = np.zeros(n, dtype=np.float32)
    if bass808_audio is not None and bass808_audio.size:
        m = min(n, bass808_audio.size)
        sub_lane[:m] = bass808_audio[:m] * levels["808"]

    mix = chop_lane + drums_lane + sub_lane
    peak = float(np.abs(mix).max())
    if peak > 0.99:
        mix *= 0.99 / peak
        warnings.append(f"mix peaked {peak:.2f}; gain-normalised")
    return RenderResult(audio=mix, sr=sr, bpm=bpm, events=events, warnings=warnings)
