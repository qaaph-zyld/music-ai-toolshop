"""Nachtfahrt: composition as plain data, lane builders and the dry lane renderer.

Source of truth: .workspace_archive/plans/nachtfahrt-beat-from-scratch.md
(composition section). Pure synthesis, seeded, no file reads. DRY lanes only:
no reverb / delay / sidechain here (mix FX arrive in the mixdown wave).
Bars are 1-indexed in the data, 0-indexed in the time maths.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy import signal

from toolshop.beat import drums_synth
from toolshop.flip import drums as fdrums
from toolshop.flip import sample_voices as sv
from toolshop.flip.bass808 import Note808, render_808
from toolshop.flip.bed_lanes import BedNote, render_pluck

# --------------------------------------------------------------------------
# DATA
# --------------------------------------------------------------------------
BPM = 105
BAR_S = 4 * 60 / BPM
STEP_S = BAR_S / 16
N_BARS = 80
SR = 44100
TAIL_S = 4.0
KEY = "D minor"

VOICINGS: Dict[str, List[int]] = {
    "Dm7": [57, 60, 62, 65],
    "Bbmaj7": [58, 62, 65, 69],
    "Gm7": [58, 62, 65, 67],
    "A7": [57, 61, 64, 67],
    "Cadd9": [60, 62, 64, 67],
    "Fmaj7": [57, 60, 64, 65],
}
CHORD_ROOT = {"Dm7": "D", "Bbmaj7": "Bb", "Gm7": "G", "A7": "A",
              "Cadd9": "C", "Fmaj7": "F"}
ROOT_808 = {"D": 38, "Bb": 34, "G": 31, "A": 33, "C": 36, "F": 29}

ARRANGEMENT: List[Tuple[str, int, int]] = [
    ("intro", 1, 4), ("hook_a", 5, 8), ("verse1", 13, 16), ("hook_b", 29, 8),
    ("verse2", 37, 16), ("hook_c", 53, 8), ("bridge", 61, 8),
    ("hook_d", 69, 8), ("outro", 77, 4),
]
SECTION_KIND = {"intro": "intro", "hook_a": "hook", "verse1": "verse",
                "hook_b": "hook", "verse2": "verse", "hook_c": "hook",
                "bridge": "bridge", "hook_d": "hook", "outro": "outro"}

PROGRESSIONS = {
    "verse": ["Dm7", "Bbmaj7", "Gm7", "A7"],     # intro + verse
    "hook": ["Bbmaj7", "Cadd9", "Dm7", "Dm7"],   # 4 bars, played twice
    "bridge": ["Gm7", "Bbmaj7", "Fmaj7", "A7"],  # twice
    "outro": ["Dm7", "Bbmaj7", "Gm7", "Dm7"],
}

# (bar, 16th step, length in steps, midi); 4-bar pattern played twice per hook
HOOK_MELODY: List[Tuple[int, int, int, int]] = [
    (0, 0, 4, 74), (0, 4, 2, 77), (0, 6, 2, 76), (0, 8, 4, 74), (0, 12, 4, 72),
    (1, 0, 6, 76), (1, 6, 2, 79), (1, 8, 4, 76), (1, 12, 4, 72),
    (2, 0, 4, 77), (2, 4, 2, 76), (2, 6, 2, 74), (2, 8, 8, 69),
    (3, 0, 4, 74), (3, 4, 2, 76), (3, 6, 2, 77), (3, 8, 8, 81),
]
HOOK_RESOLUTION = (3, 8, 8, 74)  # replaces the last note on the repeat (bar 8)
HOOK_MELODY_REPEAT = HOOK_MELODY[:-1] + [HOOK_RESOLUTION]

DRUM_GRIDS = {
    "verse_kick_A": "x.....x...x.....",
    "verse_kick_B": "x..x......x..x..",
    "snare": "....x.......x...",
    "verse_hat": "x.x.x.x.x.x.x.x.",
    "verse_roll_steps": [12, 13, 14, 14.5, 15, 15.5],  # 16ths + 32nd ratchet
    "verse_open_hat_step": 14,
    "hook_kick": "x...x...x...x...",
    "hook_hat_accents": [1.0, 0.6],     # even / odd 16th
    "hook_open_hat": "..x...x...x...x.",
    "hook_crash_bar": 1,                # bar 1 of each hook
}
BRIDGE_DRUMS = {
    "kick_only_bars": [61, 62, 63, 64], "kick_lowpass_hz": 200.0,
    "hook_kick_bars": [65, 66, 67, 68],
    "snare_8ths_bar": 67, "snare_16ths_bar": 68,
    "roll_vel": [0.4, 1.0], "roll_pitch_st": 5.0,
}
RISERS = [(3, 2), (27, 2), (51, 2), (67, 2)]   # (first_bar, n_bars)

DRUM_VEL = {"kick": 1.0, "bridge_kick": 0.9, "verse_snare": 0.9,
            "verse_clap": 0.7, "hook_snare": 1.0, "hook_clap": 0.8,
            "verse_hat": 0.7, "roll_hat": [0.5, 0.9],
            "verse_open": 0.7, "hook_open": 0.8, "hookd_open_db": 2.0,
            "bridge_snare_8th": 0.8, "crash": 0.9, "riser": 0.8}

LEVELS = {
    "pad": {"intro": 0.7, "hook": 0.8, "verse": 0.4, "bridge": 0.7,
            "outro": 0.7},
    "arp": {"intro": 0.6, "hook": 0.6, "verse": 0.35, "bridge": 0.5,
            "outro": 0.6},
    "stab_verse": 0.7, "stab_verse_gate_ms": 200.0,
    "lead": {"hook": 0.9, "bridge": 0.7},
    "lead_double_db": -8.0, "lead_glide_ms": 25.0,
    "bass808": 0.9, "pad_verse2_octave_from_bar": 45,
    "pad_attack_ms": 300.0, "pad_release_ms": 800.0,
    "arp_gate_steps": 1.5,
    "arp_lp_hz": [400.0, 4000.0],
    "arp_lp_ramp_bars": [[1, 4], [77, 80]],
    "lane_peak": 0.95,
}
LANES = ["kick", "snare", "hats", "fx", "bass808", "synthbass", "pad", "arp",
         "stabs", "lead"]
SEED = 20261002


def composition_data() -> dict:
    return {
        "bpm": BPM, "n_bars": N_BARS, "key": KEY, "tail_s": TAIL_S,
        "voicings": VOICINGS, "chord_root": CHORD_ROOT, "root_808": ROOT_808,
        "arrangement": ARRANGEMENT, "section_kind": SECTION_KIND,
        "progressions": PROGRESSIONS, "hook_melody": HOOK_MELODY,
        "hook_resolution": HOOK_RESOLUTION, "drum_grids": DRUM_GRIDS,
        "bridge_drums": BRIDGE_DRUMS, "risers": RISERS, "drum_vel": DRUM_VEL,
        "levels": LEVELS, "lanes": LANES, "seed": SEED,
        "stab_grids": list(sv.STAB_GRIDS),
        "stab_velocities": list(sv.STAB_VELOCITIES),
    }


def composition_hash() -> str:
    blob = json.dumps(composition_data(), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def section_map() -> List[dict]:
    return [{"name": n, "first_bar": b, "n_bars": k,
             "start_s": (b - 1) * BAR_S, "end_s": (b - 1 + k) * BAR_S}
            for n, b, k in ARRANGEMENT]


def section_of(bar: int) -> Tuple[str, int]:
    """(section name, 0-based bar index within the section) for a 1-indexed bar."""
    for n, b, k in ARRANGEMENT:
        if b <= bar < b + k:
            return n, bar - b
    raise ValueError(f"bar {bar} outside the arrangement")


def kind_of(bar: int) -> str:
    return SECTION_KIND[section_of(bar)[0]]


def chord_at(bar: int) -> str:
    name, i = section_of(bar)
    kind = SECTION_KIND[name]
    if kind in ("intro", "verse"):
        return PROGRESSIONS["verse"][i % 4]
    return PROGRESSIONS[kind][i % 4]


def chord_dicts(bars: Sequence[int]) -> List[dict]:
    out = []
    for b in bars:
        c = chord_at(b)
        out.append({"bar": b - 1, "chord": c, "notes": list(VOICINGS[c]),
                    "root_pc": ROOT_808[CHORD_ROOT[c]] % 12})
    return out


def _bars_of(kind: str) -> List[int]:
    return [b for b in range(1, N_BARS + 1) if kind_of(b) == kind]


def _bar_t(bar: int) -> float:
    return (bar - 1) * BAR_S


def _hook_starts() -> List[int]:
    return [b for n, b, k in ARRANGEMENT if SECTION_KIND[n] == "hook"]


# --------------------------------------------------------------------------
# DRUM EVENTS (grid_events: absolute beats, 4 beats per bar)
# --------------------------------------------------------------------------
def _sb(bar: int, step: float) -> float:
    return (bar - 1) * 4 + step / 4.0


def _ev(items: Sequence[Tuple[float, str, float]]):
    return fdrums.grid_events(sorted(items, key=lambda x: (x[0], x[1])), BPM)


def _hits(grid: str) -> List[int]:
    return [i for i, c in enumerate(grid) if c == "x"]


def verse_kick_steps(rel_bar: int) -> List[int]:
    return _hits(DRUM_GRIDS["verse_kick_A" if rel_bar % 2 == 0 else "verse_kick_B"])


def kick_items() -> List[Tuple[float, str, float]]:
    out = []
    for b in range(1, N_BARS + 1):
        name, rel = section_of(b)
        kind = SECTION_KIND[name]
        if kind == "verse":
            for s in verse_kick_steps(rel):
                out.append((_sb(b, s), "kick", DRUM_VEL["kick"]))
        elif kind == "hook":
            for s in _hits(DRUM_GRIDS["hook_kick"]):
                out.append((_sb(b, s), "kick", DRUM_VEL["kick"]))
        elif kind == "bridge":
            if b in BRIDGE_DRUMS["kick_only_bars"]:
                out.append((_sb(b, 0), "kick_lp", DRUM_VEL["bridge_kick"]))
            else:
                for s in _hits(DRUM_GRIDS["hook_kick"]):
                    out.append((_sb(b, s), "kick", DRUM_VEL["kick"]))
    return out
def snare_items() -> List[Tuple[float, str, float]]:
    out = []
    for b in range(1, N_BARS + 1):
        name, rel = section_of(b)
        kind = SECTION_KIND[name]
        if kind in ("verse", "hook"):
            for s in _hits(DRUM_GRIDS["snare"]):
                out.append((_sb(b, s), "snare", DRUM_VEL[kind + "_snare"]))
                out.append((_sb(b, s), "clap", DRUM_VEL[kind + "_clap"]))
        elif b == BRIDGE_DRUMS["snare_8ths_bar"]:
            for s in range(0, 16, 2):
                out.append((_sb(b, s), "snare", DRUM_VEL["bridge_snare_8th"]))
        elif b == BRIDGE_DRUMS["snare_16ths_bar"]:
            lo, hi = BRIDGE_DRUMS["roll_vel"]
            for s in range(16):
                out.append((_sb(b, s), f"snare_r{s}", lo + (hi - lo) * s / 15))
    return out


def hat_items() -> List[Tuple[float, str, float]]:
    out = []
    for b in range(1, N_BARS + 1):
        name, rel = section_of(b)
        kind = SECTION_KIND[name]
        if kind == "verse":
            roll = rel % 4 == 3
            for s in _hits(DRUM_GRIDS["verse_hat"]):
                if roll and s >= 12:
                    continue
                out.append((_sb(b, s), "hat", DRUM_VEL["verse_hat"]))
            if roll:
                steps = DRUM_GRIDS["verse_roll_steps"]
                lo, hi = DRUM_VEL["roll_hat"]
                for j, s in enumerate(steps):
                    out.append((_sb(b, s), "hat",
                                lo + (hi - lo) * j / (len(steps) - 1)))
                out.append((_sb(b, DRUM_GRIDS["verse_open_hat_step"]),
                            "openhat", DRUM_VEL["verse_open"]))
        elif kind == "hook":
            acc = DRUM_GRIDS["hook_hat_accents"]
            for s in range(16):
                out.append((_sb(b, s), "hat", acc[s % 2]))
            ov = DRUM_VEL["hook_open"]
            if name == "hook_d":
                ov *= 10 ** (DRUM_VEL["hookd_open_db"] / 20)
            for s in _hits(DRUM_GRIDS["hook_open_hat"]):
                out.append((_sb(b, s), "openhat", ov))
    return out


def fx_items() -> List[Tuple[float, str, float]]:
    out = []
    for fb in _hook_starts():
        out.append((_sb(fb + DRUM_GRIDS["hook_crash_bar"] - 1, 0), "crash",
                    DRUM_VEL["crash"]))
    for fb, n in RISERS:
        out.append((_sb(fb, 0), "riser", DRUM_VEL["riser"]))
    return out


def kick_events():
    return _ev(kick_items())


def snare_events():
    return _ev(snare_items())


def hat_events():
    return _ev(hat_items())


def fx_events():
    return _ev(fx_items())


# --------------------------------------------------------------------------
# NOTE LISTS
# --------------------------------------------------------------------------
def pad_notes() -> List[BedNote]:
    out = []
    for b in range(1, N_BARS + 1):
        c = VOICINGS[chord_at(b)]
        v = LEVELS["pad"][kind_of(b)]
        s, e = _bar_t(b), _bar_t(b + 1)
        for m in c:
            out.append(BedNote(s, e, m, v))
        name, _ = section_of(b)
        if name == "verse2" and b >= LEVELS["pad_verse2_octave_from_bar"]:
            for m in c:
                out.append(BedNote(s, e, m + 12, v))
    return out


def arp_tones(chord: str) -> List[int]:
    v = VOICINGS[chord]
    return sorted(v + [m + 12 for m in v])


def arp_notes() -> List[BedNote]:
    out = []
    for b in range(1, N_BARS + 1):
        tones = arp_tones(chord_at(b))
        seq = tones + tones[::-1]          # 8 up then 8 down = 16 steps
        v = LEVELS["arp"][kind_of(b)]
        for i, m in enumerate(seq):
            s = _bar_t(b) + i * STEP_S
            out.append(BedNote(s, s + LEVELS["arp_gate_steps"] * STEP_S, m, v))
    return out


def stab_notes() -> List[BedNote]:
    out: List[BedNote] = []
    for hb in _hook_starts():
        out += sv.stab_pattern(chord_dicts(range(hb, hb + 8)), BAR_S)
    for b in range(1, N_BARS + 1):
        name, rel = section_of(b)
        if SECTION_KIND[name] == "verse" and rel % 2 == 0:
            s = _bar_t(b)
            for m in VOICINGS[chord_at(b)]:
                out.append(BedNote(s, s + LEVELS["stab_verse_gate_ms"] / 1000.0,
                                   m, LEVELS["stab_verse"]))
    out.sort(key=lambda n: (n.start_s, n.note))
    return out


def _melody(first_bar: int, rep: int, vel: float, shift: int = 0) -> List[BedNote]:
    mel = HOOK_MELODY if rep == 0 else HOOK_MELODY_REPEAT
    out = []
    for bar, step, ln, midi in mel:
        s = _bar_t(first_bar + rep * 4 + bar) + step * STEP_S
        out.append(BedNote(s, s + ln * STEP_S, midi + shift, vel))
    return out


def lead_notes() -> List[BedNote]:
    out = []
    for hb in _hook_starts():
        for rep in (0, 1):
            out += _melody(hb, rep, LEVELS["lead"]["hook"])
    out += _melody(61, 0, LEVELS["lead"]["bridge"])  # bridge bars 61-64
    return sorted(out, key=lambda n: n.start_s)


def lead_double_notes() -> List[BedNote]:
    """Hook D only: octave-up double (rendered at lead_double_db)."""
    out = []
    for rep in (0, 1):
        out += _melody(69, rep, LEVELS["lead"]["hook"], shift=12)
    return sorted(out, key=lambda n: n.start_s)


def _kick_hits_808() -> List[Tuple[float, int]]:
    """(time_s, bar) of every plain kick hit (verse and bridge 65-68)."""
    out = []
    for e in kick_events():
        if e.piece != "kick":
            continue
        bar = e.bar + 1
        if kind_of(bar) in ("verse", "bridge"):
            out.append((e.time_s, bar))
    return out


def bass808_notes() -> List[Note808]:
    v = LEVELS["bass808"]
    out: List[Note808] = []
    for hb in _hook_starts():          # hooks: root on steps 0 and 8, 8 steps each
        for b in range(hb, hb + 8):
            root = ROOT_808[CHORD_ROOT[chord_at(b)]]
            for s in (0, 8):
                out.append(Note808(_bar_t(b) + s * STEP_S, 8 * STEP_S, root, v))
    for name, first, n in ARRANGEMENT:  # verse / bridge 65-68: root per kick, legato
        kind = SECTION_KIND[name]
        if kind == "verse":
            lo, hi = first, first + n
        elif kind == "bridge":
            lo, hi = 65, first + n
        else:
            continue
        hits = [(t, b) for t, b in _kick_hits_808() if lo <= b < hi]
        end = _bar_t(hi)
        for i, (t, b) in enumerate(hits):
            nxt = hits[i + 1][0] if i + 1 < len(hits) else end
            root = ROOT_808[CHORD_ROOT[chord_at(b)]]
            out.append(Note808(t, nxt - t, root, v))
    out.sort(key=lambda x: x.start_s)
    return out


def split_808_phrases(notes: Sequence[Note808]) -> List[List[Note808]]:
    """Split where the pitch change is not a m3/P4 slide, because render_808
    glides on every pitch change; inside a phrase only 3 or 5 semitones slide."""
    phrases: List[List[Note808]] = []
    for n in sorted(notes, key=lambda x: x.start_s):
        if phrases:
            prev = phrases[-1][-1]
            d = abs(int(n.note) - int(prev.note))
            contiguous = prev.start_s + prev.duration_s >= n.start_s - 1e-6
            if contiguous and (d == 0 or d in (3, 5)):
                phrases[-1].append(n)
                continue
        phrases.append([n])
    return phrases


def synthbass_notes() -> List[BedNote]:
    out: List[BedNote] = []
    for hb in _hook_starts():
        out += sv.driving_bass(chord_dicts(range(hb, hb + 8)), BAR_S,
                               root_octave_low=3)
    return out


# --------------------------------------------------------------------------
# RENDER
# --------------------------------------------------------------------------
def _stereo(x: np.ndarray, n: int) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    out = np.zeros((n, 2), dtype=np.float32)
    m = min(n, x.shape[0])
    out[:m] = x[:m]
    return out


def _guard(x: np.ndarray) -> np.ndarray:
    pk = float(np.abs(x).max()) if x.size else 0.0
    lim = LEVELS["lane_peak"]
    if pk > lim:
        x = x * (lim / pk)
    return x.astype(np.float32)


def _add(lane: np.ndarray, audio: np.ndarray, t0_s: float, sr: int) -> None:
    s0 = int(round(t0_s * sr))
    a = _stereo(audio, np.asarray(audio).shape[0])
    m = min(lane.shape[0] - s0, a.shape[0])
    if m > 0:
        lane[s0:s0 + m] += a[:m]


def _slice_notes(notes, t0, t1):
    out = []
    for nt in notes:
        if t0 - 1e-9 <= nt.start_s < t1 - 1e-9:
            if isinstance(nt, BedNote):
                out.append(dataclasses.replace(nt, start_s=nt.start_s - t0,
                                               end_s=nt.end_s - t0))
            else:
                out.append(dataclasses.replace(nt, start_s=nt.start_s - t0))
    return out


def _slice_events(evs, t0, t1):
    return [dataclasses.replace(e, time_s=e.time_s - t0) for e in evs
            if t0 - 1e-9 <= e.time_s < t1 - 1e-9]


def _pitched(x: np.ndarray, semitones: float) -> np.ndarray:
    r = 2.0 ** (semitones / 12.0)
    idx = np.arange(0, len(x) - 1, r)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


def _shots(sr: int) -> Dict[str, np.ndarray]:
    sh = drums_synth.one_shots(sr)
    sh["riser"] = drums_synth.riser(2 * BAR_S, sr)
    top = BRIDGE_DRUMS["roll_pitch_st"]
    for s in range(16):
        sh[f"snare_r{s}"] = _pitched(sh["snare"], top * s / 15)
    return sh


def _drum_lane(events, shots, sr, n, t_total) -> np.ndarray:
    return _stereo(fdrums.render_drums(events, shots, sr, t_total), n)


def arp_cutoff_hz(t_abs: np.ndarray) -> np.ndarray:
    lo, hi = LEVELS["arp_lp_hz"]
    fc = np.full(np.shape(t_abs), hi, dtype=np.float64)
    t_abs = np.asarray(t_abs, dtype=np.float64)
    (a0, a1), (b0, b1) = LEVELS["arp_lp_ramp_bars"]
    ta, tb = _bar_t(a0), _bar_t(a1 + 1)
    m = t_abs < tb
    fc[m] = lo * (hi / lo) ** np.clip((t_abs[m] - ta) / (tb - ta), 0, 1)
    tc, td = _bar_t(b0), _bar_t(b1 + 1)
    m = t_abs >= tc
    fc[m] = hi * (lo / hi) ** np.clip((t_abs[m] - tc) / (td - tc), 0, 1)
    return fc


def _lp_automated(x: np.ndarray, sr: int, t0_s: float, block: int = 512) -> np.ndarray:
    """Two cascaded one-pole low-passes, cutoff automated block-wise."""
    y = x.astype(np.float64)
    for _ in range(2):
        out = np.zeros_like(y)
        zi = np.zeros(1)
        for a in range(0, len(y), block):
            e = min(len(y), a + block)
            fc = float(arp_cutoff_hz(np.array([t0_s + (a + e) / 2 / sr]))[0])
            c = float(np.exp(-2 * np.pi * min(fc, 0.45 * sr) / sr))
            out[a:e], zi = signal.lfilter([1 - c], [1, -c], y[a:e], zi=zi)
        y = out
    return y


def _render_groups(notes, fn, n, sr, gap_s=0.5 * BAR_S) -> np.ndarray:
    lane = np.zeros((n, 2), dtype=np.float32)
    groups: List[List[BedNote]] = []
    for nt in sorted(notes, key=lambda x: x.start_s):
        if groups and nt.start_s - groups[-1][-1].end_s <= gap_s:
            groups[-1].append(nt)
        else:
            groups.append([nt])
    for g in groups:
        t0 = g[0].start_s
        sh = [dataclasses.replace(x, start_s=x.start_s - t0, end_s=x.end_s - t0)
              for x in g]
        _add(lane, fn(sh), t0, sr)
    return lane


def render_lanes(sr: int = SR, bars: Optional[Tuple[int, int]] = None
                 ) -> Dict[str, np.ndarray]:
    """10 dry stereo lanes. ``bars=(first, last)`` (1-indexed, inclusive) renders
    only that slice (time 0 = start of ``first``, 1 s tail) for tests."""
    if bars is None:
        t0, t1, tail = 0.0, N_BARS * BAR_S, TAIL_S
    else:
        t0, t1, tail = _bar_t(bars[0]), _bar_t(bars[1] + 1), 1.0
    t_total = (t1 - t0) + tail
    n = int(t_total * sr)
    zero = lambda: np.zeros((n, 2), np.float32)
    lanes: Dict[str, np.ndarray] = {}
    shots = _shots(sr)

    ke = _slice_events(kick_events(), t0, t1)
    kick = _drum_lane([e for e in ke if e.piece == "kick"], shots, sr, n, t_total)
    lp = [dataclasses.replace(e, piece="kick") for e in ke if e.piece == "kick_lp"]
    if lp:
        sos = signal.butter(4, BRIDGE_DRUMS["kick_lowpass_hz"], "lowpass",
                            fs=sr, output="sos")
        kick += signal.sosfilt(sos, _drum_lane(lp, shots, sr, n, t_total),
                               axis=0).astype(np.float32)
    lanes["kick"] = kick
    for name, evs in (("snare", snare_events()), ("hats", hat_events()),
                      ("fx", fx_events())):
        lanes[name] = _drum_lane(_slice_events(evs, t0, t1), shots, sr, n, t_total)

    lane = zero()
    for ph in split_808_phrases(_slice_notes(bass808_notes(), t0, t1)):
        p0 = ph[0].start_s
        sh = [dataclasses.replace(x, start_s=x.start_s - p0) for x in ph]
        _add(lane, render_808(sh, sr), p0, sr)
    lanes["bass808"] = lane

    sb = _slice_notes(synthbass_notes(), t0, t1)
    lanes["synthbass"] = _stereo(sv.render_synth_bass(sb, sr), n) if sb else zero()

    pn = _slice_notes(pad_notes(), t0, t1)
    lanes["pad"] = _stereo(sv.render_organ(
        pn, "string", sr, attack_ms=LEVELS["pad_attack_ms"],
        release_ms=LEVELS["pad_release_ms"]), n)

    ar = render_pluck(_slice_notes(arp_notes(), t0, t1), sr=sr).astype(np.float64)
    ar = _lp_automated(ar * (0.9 / (float(np.abs(ar).max()) or 1.0)), sr, t0)
    lanes["arp"] = _stereo(ar, n)

    sn = _slice_notes(stab_notes(), t0, t1)
    lanes["stabs"] = _stereo(sv.render_organ(sn, "drawbar", sr), n) if sn else zero()

    glide = LEVELS["lead_glide_ms"]
    fn = lambda g: sv.render_gfunk_lead(g, sr, glide_ms=glide)
    lead = _render_groups(_slice_notes(lead_notes(), t0, t1), fn, n, sr)
    dbl = _slice_notes(lead_double_notes(), t0, t1)
    if dbl:
        lead += _render_groups(dbl, fn, n, sr) * 10 ** (LEVELS["lead_double_db"] / 20)
    lanes["lead"] = lead

    return {k: _guard(np.nan_to_num(lanes[k])) for k in LANES}
