"""Arrangement layer for the OGCM drill flip (wave W3 — finding F3).

The spec requires an intro→verse→chorus arc with mute-drops and per-arm
span math; none of that existed (`assemble.render_beat` only mixes a fixed
event list). This module owns the *plan*: which sections exist, which bed
segment plays where, which drum pieces are active, where the 808 sits and
where it drops — then delegates the actual buffer math to `drums`,
`bass808`, `bed_lanes` and `assemble`.

**Per-arm span math.** Bed material is authored on the 89.1 *felt* grid
(motifs and the cleaned MIDI are all in felt-time seconds). A `felt_bars`
span occupies ``felt_bars * written_bpm / felt_bpm`` written bars:

- arm ``felt_89``  (178.2 written): 4 felt bars -> 8 written bars;
  supercycle = lcm(8, 4-bar drum group) = **8 written bars**.
- arm ``triplet_133`` (133.65 written): 4 felt bars -> 6 written bars
  (a 2-felt-bar motif = 3 written bars); supercycle = lcm(3 or 6, 4) =
  **12 written bars** — the LCM-12 supercycle the megaplan asks for.

**Drum foundation (F5 fixed properly).** `drums.drill_pattern` now emits a
true 2-bar kick cycle; this module groups those into 4-bar blocks (the
triplet-burst bar) and layers mute-drops on top.

**Hook space.** Sections of kind ``hook`` lower the bed gain and are
reported in the event JSON's ``hook_sections`` — the structure reserves
room for the backing-vocal-driven hook that wave m4 places.

Verification: `verify_render` emits the per-render evidence (clip count —
must be 0; grid adherence of every emitted event; mono<120 Hz check).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import assemble, bass808, drums

FELT_BPM = 89.1
ARM_BPM = {"felt_89": 178.2, "triplet_133": 133.65}
DRUM_CYCLE_BARS = 4        # drill_pattern's triplet-burst group
FOUNDATION_BARS = 2        # true 2-bar kick cycle (F5)
MONO_SUB_HZ = 120.0        # spec: mono below 120 Hz
CLIP_THRESH = 0.999        # samples at/above this count as clipped
GRID_SUBDIV = 24           # 1/24-beat grid covers 16ths AND triplet eighths

#: Pieces muted during a mute-drop (the low-end + backbeat drop; hats ride on).
MUTE_DROP_PIECES = frozenset({"kick", "snare", "openhat", "cymbal", "tom"})
#: Sparse-section drum set (intro/outro).
SPARSE_PIECES = frozenset({"kick", "hat"})

#: MIDI root notes for the 808 (D2 = 73.4 Hz, C#2 = 69.3 Hz — sub range
#: that stays audible on small speakers once driven).
ROOT_MIDI = {"D": 38.0, "C#": 37.0}
ROOT_OF_KEY = {"D minor": "D", "C# minor": "C#"}


# ---------------------------------------------------------------------------
# Span math
# ---------------------------------------------------------------------------

def felt_span_written_bars(felt_bars: float, written_bpm: float,
                           felt_bpm: float = FELT_BPM) -> float:
    """Written bars occupied by a felt-grid span at `written_bpm`."""
    return felt_bars * written_bpm / felt_bpm


def supercycle_bars(bed_written_bars: int,
                    drum_cycle_bars: int = DRUM_CYCLE_BARS) -> int:
    """LCM written-bar supercycle so bed spans and drum cycles close together."""
    return math.lcm(int(bed_written_bars), int(drum_cycle_bars))


# ---------------------------------------------------------------------------
# Motif library (Lane C — hand-programmed dark motifs; mirrored from
# scripts/ogcm_bed_spike.py so the arrange layer can render + re-export them
# to stems/flip_bed_lanes/midi/ without importing the spike script).
# ---------------------------------------------------------------------------

def _motif_dm_1() -> List[Tuple[float, float, int]]:
    """Dark Dm motif: i-VI arpeggio, 2 felt bars @89.1 (16th grid)."""
    seq = [
        (0, 0.5, 62), (0.5, 1.0, 65), (1.0, 1.5, 69),   # D F A
        (2.0, 2.5, 58), (2.5, 3.0, 62), (3.0, 3.5, 65),  # Bb D F
        (4.0, 4.5, 65), (4.5, 5.0, 69), (5.0, 5.5, 72),  # F A C
        (6.0, 7.0, 62),                                    # D sustain
    ]
    return [(s, e, n) for s, e, n in seq]


def _motif_csm_1() -> List[Tuple[float, float, int]]:
    """Dark C#m motif: i-VII-VI arpeggio, 2 felt bars @89.1."""
    seq = [
        (0, 0.5, 61), (0.5, 1.0, 64), (1.0, 1.5, 68),
        (2.0, 2.5, 59), (2.5, 3.0, 63), (3.0, 3.5, 66),
        (4.0, 4.5, 57), (4.5, 5.0, 61), (5.0, 5.5, 64),
        (6.0, 7.0, 61),
    ]
    return [(s, e, n) for s, e, n in seq]


_MOTIF_DEFS = {
    "motif_dm_1": {"root": "D", "mode": "minor", "voice": "pad",
                   "key": "D minor", "felt_bars": 2, "seq": _motif_dm_1},
    "motif_csm_1": {"root": "C#", "mode": "minor", "voice": "epiano",
                    "key": "C# minor", "felt_bars": 2, "seq": _motif_csm_1},
}


def motif_notes(name: str) -> List[Any]:
    """BedNote list for a programmed motif (felt-time seconds @89.1)."""
    from . import bed_lanes

    meta = _MOTIF_DEFS[name]
    beat = 60.0 / FELT_BPM
    six = beat / 4.0
    return [bed_lanes.BedNote(s * six, e * six, n, 0.85) for s, e, n in meta["seq"]()]


def motif_meta(name: str) -> Dict[str, Any]:
    """Public copy of a motif's metadata (root/mode/voice/felt_bars)."""
    return {k: v for k, v in _MOTIF_DEFS[name].items() if k != "seq"}


def write_motif_midi(path: Path, name: str) -> Path:
    """Materialise a programmed motif as a .mid file (for the midi/ dir)."""
    from . import bed_lanes

    notes = motif_notes(name)
    pm = bed_lanes.notes_to_pretty_midi(notes, bpm=FELT_BPM)
    bed_lanes.save_midi(path, pm)
    return Path(path)


# ---------------------------------------------------------------------------
# Sections + arrangement plan
# ---------------------------------------------------------------------------

@dataclass
class Section:
    """One arrangement block on the written grid."""

    name: str
    kind: str                 # intro | verse | hook | outro
    start_bar: int            # written bars
    bars: int
    motif: Optional[str]      # bed segment key (None = no bed)
    voice: str = "epiano"
    root: Optional[str] = None        # 808 root key ("D"/"C#"), None = no 808
    drum_mode: str = "full"           # full | sparse | off
    bed_gain: float = 1.0
    bed_filter_hz: Optional[float] = None   # one-pole LPF on this section's bed
    mute_bars: Tuple[int, ...] = ()   # absolute written bars that mute-drop

    def to_dict(self, bpm: float) -> Dict[str, Any]:
        beat_s = 60.0 / bpm
        return {
            "name": self.name, "kind": self.kind,
            "start_bar": self.start_bar, "bars": self.bars,
            "start_s": round(self.start_bar * 4 * beat_s, 4),
            "end_s": round((self.start_bar + self.bars) * 4 * beat_s, 4),
            "motif": self.motif, "voice": self.voice, "root": self.root,
            "drum_mode": self.drum_mode, "bed_gain": self.bed_gain,
            "bed_filter_hz": self.bed_filter_hz,
            "mute_bars": list(self.mute_bars),
        }


@dataclass
class ArmPlan:
    arm: str
    bpm: float
    felt_bpm: float
    supercycle_bars: int
    sections: List[Section]

    @property
    def total_bars(self) -> int:
        return max((s.start_bar + s.bars for s in self.sections), default=0)

    @property
    def total_s(self) -> float:
        return self.total_bars * 4 * 60.0 / self.bpm

    @property
    def hook_sections(self) -> List[Section]:
        return [s for s in self.sections if s.kind == "hook"]


def build_plan(arm: str) -> ArmPlan:
    """The GATE-C2-picked arrangement for a grid arm.

    felt_89: Lane B interpolated bed (region_63_66 cleaned Dm, epiano) —
    4-felt-bar loop = 8-written-bar supercycle.
    triplet_133: Lane C programmed motifs as section alternates —
    motif_dm_1 (pad, Dm) for verse blocks, motif_csm_1 (epiano, C#m) for
    hook blocks; 12-written-bar supercycle sections.
    """
    if arm == "felt_89":
        bpm = ARM_BPM[arm]
        sc = supercycle_bars(int(felt_span_written_bars(4, bpm)))  # = 8
        sec = [
            Section("intro", "intro", 0, sc, "region_63_66", voice="epiano",
                    root=None, drum_mode="sparse", bed_gain=0.55,
                    bed_filter_hz=1100.0),
            Section("verse1", "verse", sc, 2 * sc, "region_63_66",
                    voice="epiano", root="D"),
            Section("hook", "hook", 3 * sc, sc, "region_63_66",
                    voice="epiano", root="D", bed_gain=0.62,
                    mute_bars=(3 * sc + sc - 2, 3 * sc + sc - 1)),
            Section("verse2", "verse", 4 * sc, sc, "region_63_66",
                    voice="epiano", root="D"),
            Section("outro", "outro", 5 * sc, sc, "region_63_66",
                    voice="epiano", root=None, drum_mode="sparse",
                    bed_gain=0.55, bed_filter_hz=1100.0,
                    mute_bars=(6 * sc - 2, 6 * sc - 1)),
        ]
        return ArmPlan(arm=arm, bpm=bpm, felt_bpm=FELT_BPM,
                       supercycle_bars=sc, sections=sec)
    if arm == "triplet_133":
        bpm = ARM_BPM[arm]
        sc = supercycle_bars(int(felt_span_written_bars(2, bpm)))  # lcm(3,4)=12
        sec = [
            Section("intro", "intro", 0, sc, "motif_dm_1", voice="pad",
                    root=None, drum_mode="sparse", bed_gain=0.55,
                    bed_filter_hz=1100.0),
            Section("verse1", "verse", sc, 2 * sc, "motif_dm_1", voice="pad",
                    root="D"),
            Section("hook", "hook", 3 * sc, sc, "motif_csm_1", voice="epiano",
                    root="C#", bed_gain=0.62,
                    mute_bars=(4 * sc - 2, 4 * sc - 1)),
            Section("verse2", "verse", 4 * sc, sc, "motif_dm_1", voice="pad",
                    root="D"),
            Section("outro", "outro", 5 * sc, sc, "motif_csm_1",
                    voice="epiano", root=None, drum_mode="sparse",
                    bed_gain=0.55, bed_filter_hz=1100.0,
                    mute_bars=(6 * sc - 2, 6 * sc - 1)),
        ]
        return ArmPlan(arm=arm, bpm=bpm, felt_bpm=FELT_BPM,
                       supercycle_bars=sc, sections=sec)
    raise ValueError(f"unknown arm {arm!r}; choose from {list(ARM_BPM)}")


# ---------------------------------------------------------------------------
# Drum + 808 planning
# ---------------------------------------------------------------------------

def plan_drum_events(plan: ArmPlan) -> List[drums.DrumEvent]:
    """Sectioned drill events: per-section density + mute-drops + section
    crash accents. `drill_pattern`'s 2-bar kick cycle is the foundation."""
    beat_s = 60.0 / plan.bpm
    events: List[drums.DrumEvent] = []
    for sec in plan.sections:
        if sec.drum_mode == "off":
            continue
        pat = drums.drill_pattern(bars=sec.bars, ghost_snare=True,
                                  hat_mode="mix")
        for ev in drums.grid_events(pat, bpm=plan.bpm,
                                    start_beat=sec.start_bar * 4):
            abs_bar = ev.bar
            if sec.drum_mode == "sparse" and ev.piece not in SPARSE_PIECES:
                continue
            if abs_bar in sec.mute_bars and ev.piece in MUTE_DROP_PIECES:
                continue
            events.append(ev)
        # crash accent on each full-density section downbeat
        if sec.drum_mode == "full":
            events.append(drums.DrumEvent(
                bar=sec.start_bar, beat=0.0,
                time_s=sec.start_bar * 4 * beat_s,
                piece="cymbal", velocity=0.7))
    events.sort(key=lambda e: (e.time_s, e.piece))
    return events


def plan_bass(
    plan: ArmPlan,
    drum_events: Sequence[drums.DrumEvent],
) -> Tuple[List[bass808.Note808], List[dict]]:
    """808 line per section, root = section's landed key; slides on kicks.

    Kicks inside mute-drop bars are excluded so the 808 drops with them.
    """
    beat_s = 60.0 / plan.bpm
    all_notes: List[bass808.Note808] = []
    all_slides: List[dict] = []
    kicks = sorted(e.time_s for e in drum_events if e.piece == "kick")
    for sec in plan.sections:
        if sec.root is None:
            continue
        s0 = sec.start_bar * 4 * beat_s
        s1 = (sec.start_bar + sec.bars) * 4 * beat_s
        sec_kicks = [t for t in kicks
                     if s0 <= t < s1
                     and int(t / (4 * beat_s)) not in sec.mute_bars]
        notes, slides = bass808.plan_808_line(
            sec_kicks, bpm=plan.bpm, root_note=ROOT_MIDI[sec.root],
            total_s=s1, slides_per_4bars=2)
        all_notes.extend(notes)
        for sl in slides:
            sl = dict(sl)
            sl["section"] = sec.name
            sl["root"] = sec.root
            all_slides.append(sl)
    all_notes.sort(key=lambda n: n.start_s)
    return all_notes, all_slides


# ---------------------------------------------------------------------------
# Bed lane assembly
# ---------------------------------------------------------------------------

def build_bed_lane(
    plan: ArmPlan,
    bed_segments: Dict[str, np.ndarray],
    sr: int,
) -> Tuple[np.ndarray, List[dict]]:
    """Tile each section's bed segment across its written-bar span.

    `bed_segments` maps motif/segment key -> rendered audio (native felt
    timing). Per-section gain and the optional one-pole LPF ("filtered
    intro") are applied to a copy — the source segments are not mutated.
    """
    from . import bed_lanes

    beat_s = 60.0 / plan.bpm
    n = int(plan.total_s * sr) + sr
    lane = np.zeros(n, dtype=np.float32)
    placements: List[dict] = []
    for sec in plan.sections:
        if not sec.motif:
            continue
        seg = bed_segments.get(sec.motif)
        if seg is None or seg.size == 0:
            continue
        seg = seg.astype(np.float32)
        if sec.bed_filter_hz:
            seg = bed_lanes.lowpass(seg, sr, sec.bed_filter_hz)
        start = int(sec.start_bar * 4 * beat_s * sr)
        span = int(sec.bars * 4 * beat_s * sr)
        if seg.size < span:
            seg = np.tile(seg, math.ceil(span / seg.size))
        end = min(n, start + span)
        lane[start:end] += seg[: end - start] * sec.bed_gain
        placements.append({
            "type": "bed", "section": sec.name, "motif": sec.motif,
            "voice": sec.voice, "start_bar": sec.start_bar,
            "start_s": round(start / sr, 4), "span_s": round(span / sr, 4),
            "gain": sec.bed_gain, "filter_hz": sec.bed_filter_hz,
        })
    return lane, placements


# ---------------------------------------------------------------------------
# Render + verification
# ---------------------------------------------------------------------------

def render_arm(
    plan: ArmPlan,
    bed_segments: Dict[str, np.ndarray],
    one_shots: Dict[str, np.ndarray],
    sr: int = 44100,
    mix_levels: Optional[Dict[str, float]] = None,
    glide_ms: float = bass808.GLIDE_MS_DEFAULT,
) -> Dict[str, Any]:
    """Render a full grid arm: bed lane + drums + 808 via assemble.

    Returns ``{"audio", "sr", "bpm", "events", "verification",
    "warnings"}`` — `events` is the per-render JSON body (sections, drum
    hits, bed placements, 808 notes, slides, hook reservations).
    """
    if not (bass808.GLIDE_MS_MIN <= glide_ms <= bass808.GLIDE_MS_MAX):
        raise ValueError(
            f"glide_ms {glide_ms} outside drill window "
            f"{bass808.GLIDE_MS_MIN}-{bass808.GLIDE_MS_MAX}")
    drum_events = plan_drum_events(plan)
    notes808, slides = plan_bass(plan, drum_events)
    kick_times = [e.time_s for e in drum_events if e.piece == "kick"]
    transient = one_shots.get("kick")
    sub = bass808.render_808(notes808, sr=sr, glide_ms=glide_ms,
                             transient=transient, transient_gain=0.35,
                             duck_times=kick_times,
                             duck_depth=0.4, duck_ms=50.0)
    bed_lane, bed_placements = build_bed_lane(plan, bed_segments, sr)

    res = assemble.render_beat(
        np.zeros(1, dtype=np.float32), sr,
        {"grid": {"tempo": plan.bpm}, "candidates": []}, [],
        bpm=plan.bpm,
        drum_events=drum_events, one_shots=one_shots,
        bass808_audio=sub, bed_lane=bed_lane,
        total_beats=plan.total_bars * 4.0,
        # headroom-first defaults: kick+808+crash coincident peaks must stay
        # below 1.0 without assemble's normaliser having to rescue the mix
        mix_levels=mix_levels or {"bed": 0.42, "drums": 0.28, "808": 0.28},
    )

    events: Dict[str, Any] = {
        "arm": plan.arm,
        "bpm_written": plan.bpm,
        "bpm_felt": plan.felt_bpm,
        "supercycle_bars": plan.supercycle_bars,
        "total_bars": plan.total_bars,
        "total_s": round(plan.total_s, 4),
        "sr": sr,
        "sections": [s.to_dict(plan.bpm) for s in plan.sections],
        "hook_sections": [s.to_dict(plan.bpm) for s in plan.hook_sections],
        "hook_reserved_for": "backing_vocals (wave m4 places the hook)",
        "bed_placements": bed_placements,
        "drum_events": [e.to_dict() for e in drum_events],
        "bass808_notes": [
            {"start_s": round(n.start_s, 4), "duration_s": round(n.duration_s, 4),
             "note": n.note, "velocity": n.velocity} for n in notes808
        ],
        "bass808_slides": slides,
        "glide_ms": glide_ms,
        "warnings": res.warnings,
    }
    verification = verify_render(res.audio, sr, drum_events, plan.bpm)
    return {"audio": res.audio, "sr": sr, "bpm": plan.bpm,
            "events": events, "verification": verification,
            "warnings": res.warnings}


def clip_count(audio: np.ndarray, thresh: float = CLIP_THRESH) -> int:
    """Samples sitting at/above full-scale — spec requires 0."""
    return int(np.sum(np.abs(audio) >= thresh))


def grid_adherence(drum_events: Sequence[drums.DrumEvent], bpm: float,
                   sr: int = 44100, tol_samples: float = 1.0) -> Dict[str, Any]:
    """Every drum event must sit on the 1/24-beat grid AND land within
    `tol_samples` of its ideal sample position."""
    beat_s = 60.0 / bpm
    checked = 0
    worst_beat_err = 0.0
    worst_sample_err = 0.0
    for e in drum_events:
        grid_pos = e.bar * 4 + e.beat
        # on the 1/24-beat lattice (16ths = 6/24, triplet eighths = 8/24)
        lattice = grid_pos * GRID_SUBDIV
        beat_err = abs(lattice - round(lattice)) / GRID_SUBDIV
        worst_beat_err = max(worst_beat_err, beat_err)
        ideal_s = grid_pos * beat_s
        sample_err = abs(e.time_s - ideal_s) * sr
        worst_sample_err = max(worst_sample_err, sample_err)
        checked += 1
    return {
        "checked": checked,
        "max_grid_beat_err": round(worst_beat_err, 6),
        "max_sample_err": round(worst_sample_err, 3),
        "tol_samples": tol_samples,
        "pass": bool(worst_beat_err < 1e-3 and worst_sample_err <= tol_samples),
    }


def mono_below_120hz(audio: np.ndarray, sr: int) -> Dict[str, Any]:
    """Verify the sub band is mono.

    Mono input trivially passes (and is reported as such). For stereo,
    compares mid vs side energy below `MONO_SUB_HZ` — a flip render must
    keep kick+808 centred (side/mid energy ratio < 0.01).
    """
    if audio.ndim == 1 or audio.shape[1] == 1:
        return {"mono_input": True, "pass": True,
                "note": "single-channel render — sub band is mono by construction"}
    import scipy.signal as sig

    mid = 0.5 * (audio[:, 0] + audio[:, 1])
    side = 0.5 * (audio[:, 0] - audio[:, 1])
    sos = sig.butter(4, MONO_SUB_HZ, "lowpass", fs=sr, output="sos")
    e_mid = float(np.sum(sig.sosfilt(sos, mid) ** 2))
    e_side = float(np.sum(sig.sosfilt(sos, side) ** 2))
    ratio = e_side / (e_mid + 1e-12)
    return {"mono_input": False, "side_mid_ratio": round(ratio, 6),
            "pass": bool(ratio < 0.01)}


def verify_render(
    audio: np.ndarray,
    sr: int,
    drum_events: Sequence[drums.DrumEvent],
    bpm: float,
) -> Dict[str, Any]:
    """The per-render evidence block: clips, grid, mono<120 Hz."""
    clips = clip_count(audio)
    grid = grid_adherence(drum_events, bpm, sr=sr)
    mono = mono_below_120hz(audio, sr)
    return {
        "clip_count": clips,
        "clip_pass": clips == 0,
        "peak": round(float(np.abs(audio).max()), 4) if audio.size else 0.0,
        "grid_adherence": grid,
        "mono_below_120hz": mono,
        "pass": bool(clips == 0 and grid["pass"] and mono["pass"]),
    }
