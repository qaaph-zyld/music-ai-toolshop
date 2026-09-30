"""West-coast sample voices — OGCM Suno-sample pivot (post-GATE-F).

The GATE-F build shipped `bed_lanes` placeholder voices (sine+harmonics
"epiano", detuned-saw "pad"); the user verdict was that the result sounded
terrible. This module is the *polished* render path for the new deliverable:
a melodic **sample** (no drums, no vocal) carrying melodies transcribed from
the real OGCM instrumental, voiced for a west-coast / G-funk flavour and
packaged for Suno.

Voices (all stereo `(samples, 2)` float32, 44.1 kHz):

- ``render_rhodes``  — suitcase-EP: fundamental + fast-decay bell partial +
  soft warmth partials, velocity->brightness, stereo tremolo (L/R antiphase),
  ~1.8 s exponential decay.
- ``render_warm_pad`` — three detuned saws + slow detune LFO + one-pole LPF +
  slow attack; stereo width via independent L/R detune.
- ``render_gfunk_lead`` — mono-legato sine+saw lead with per-note portamento
  (~100 ms) and delayed 5.5 Hz vibrato — the G-funk "whine".
- ``render_sub`` — sine + soft 2nd harmonic, tanh-saturated, for derived
  bass roots.

Support functions:

- ``split_registers`` — split a mixed transcription into bass/melody lanes.
- ``derive_chords`` — per-bar diatonic-7th voicings in the landed key,
  inferred from the transcription's own bass + melody content (falls back to
  a canonical i-VI-III-VII cycle when a bar has no usable content).
- ``humanize`` — seeded timing/velocity jitter (deterministic).
- ``west_coast_chain`` — per-lane pedalboard FX (chorus on EP, filter+verb
  on pad, dotted-8th delay on lead, glue compressor on the bus).
- ``fit_loop`` — fold render tails into the head + raised-cosine seam fade
  so the loop wraps seamlessly.

S3 helpers (simple, recognizable motif):

- ``quantize`` — snap onsets/durations to a time grid.
- ``extract_motif`` — pick the most-repeated `motif_bars`-bar cell of the
  top line, simplify it to <=8 grid-quantized diatonic notes.
- ``tile_motif`` — tile the motif verbatim; ``answer_motif`` — an A'
  response variant (last notes resolve to the opening pitch class).
- ``render_simple_lead`` — plain sine+0.15x2nd-harmonic tone voice.

Everything is deterministic: fixed seeds, no randomness outside the seeded
RNG, no model calls.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from toolshop.flip.bed_lanes import BedNote, FELT_BPM, _one_pole_lpf, _saw

BAR_S = 4.0 * 60.0 / FELT_BPM          # one felt bar in seconds (2.6939)
REGISTER_SPLIT_MIDI = 50               # <=50 bass lane, >50 melody lane
SEED = 20260929

# D natural minor: pitch-class set and diatonic 7th-chord spellings.
# pc -> (chord root pc, [chord-tone pcs]) for the 7th chord built on that degree.
D_MINOR_PCS = (2, 4, 5, 7, 9, 10, 0)
_DMINOR_7TH: Dict[int, Tuple[str, Tuple[int, ...]]] = {
    2: ("Dm7", (2, 5, 9, 0)),      # i7
    4: ("Em7b5", (4, 7, 10, 2)),   # ii7b5
    5: ("Fmaj7", (5, 9, 0, 4)),    # IIImaj7
    7: ("Gm7", (7, 10, 2, 5)),     # iv7
    9: ("Am7", (9, 0, 4, 7)),      # v7
    10: ("Bbmaj7", (10, 2, 5, 9)),  # VImaj7
    0: ("C7", (0, 4, 7, 10)),      # VII7
}
# Canonical fallback cycle (i-VI-III-VII) when a bar has no derivable root.
FALLBACK_PROG: Tuple[int, ...] = (2, 10, 5, 0)


def _midi_to_freq(note: float) -> float:
    return 440.0 * 2.0 ** ((note - 69.0) / 12.0)


def _env(n: int, sr: int, attack_ms: float, release_ms: float,
         decay_s: float, velocity: float) -> np.ndarray:
    """Attack / exp-decay / release envelope of n samples."""
    env = np.ones(n, dtype=np.float64)
    a = min(n, max(1, int(attack_ms * sr / 1000.0)))
    env[:a] = np.linspace(0.0, 1.0, a)
    body = np.arange(n - a, dtype=np.float64) / sr
    env[a:] = np.exp(-body / max(decay_s, 0.05))
    r = min(n, max(1, int(release_ms * sr / 1000.0)))
    env[n - r:] *= np.linspace(1.0, 0.0, r)
    return env * velocity


# ---------------------------------------------------------------------------
# Register split + humanize + chord derivation
# ---------------------------------------------------------------------------

def split_registers(notes: Sequence[BedNote],
                    split: int = REGISTER_SPLIT_MIDI
                    ) -> Tuple[List[BedNote], List[BedNote]]:
    """(bass_lane, melody_lane): note <= `split` goes to bass, else melody."""
    bass = [n for n in notes if n.note <= split]
    melody = [n for n in notes if n.note > split]
    bass.sort(key=lambda n: n.start_s)
    melody.sort(key=lambda n: n.start_s)
    return bass, melody


def humanize(notes: Sequence[BedNote], timing_ms: float = 8.0,
             vel_lo: float = 0.85, seed: int = SEED) -> List[BedNote]:
    """Seeded jitter: shift onsets ±`timing_ms` (keeping duration), scale
    velocity into [vel_lo, 1]. Deterministic for a fixed seed + input order."""
    rng = np.random.default_rng(seed)
    out: List[BedNote] = []
    for n in notes:
        shift = float(rng.uniform(-timing_ms, timing_ms)) / 1000.0
        start = max(0.0, n.start_s + shift)
        out.append(BedNote(start_s=start, end_s=start + n.duration_s,
                           note=n.note,
                           velocity=n.velocity * float(rng.uniform(vel_lo, 1.0))))
    return out


def top_line(notes: Sequence[BedNote], cell_s: float = 0.08) -> List[BedNote]:
    """Extract the melodic contour: per `cell_s` time cell keep the
    highest-pitch note (melody = upper contour). The transcription is
    bass-dominated — a fixed register split starves the melody; this adapts.
    """
    if not notes:
        return []
    seq = sorted(notes, key=lambda n: n.start_s)
    cells: Dict[int, BedNote] = {}
    for n in seq:
        cell = int(n.start_s / cell_s)
        cur = cells.get(cell)
        if cur is None or n.note > cur.note:
            cells[cell] = n
    return [cells[k] for k in sorted(cells)]


def legato(notes: Sequence[BedNote], gap_ms: float = 20.0,
           max_s: Optional[float] = None) -> List[BedNote]:
    """Extend each note's end to the next onset minus `gap_ms` — turns a
    stream of short transcription blips into a continuous singable line.
    `max_s` caps a single note's duration (None = uncapped)."""
    seq = sorted(notes, key=lambda n: n.start_s)
    out: List[BedNote] = []
    for i, n in enumerate(seq):
        nxt = seq[i + 1].start_s if i + 1 < len(seq) else n.end_s
        end = max(n.end_s, nxt - gap_ms / 1000.0)
        if max_s is not None:
            end = min(end, n.start_s + max_s)
        out.append(BedNote(start_s=n.start_s, end_s=max(end, n.start_s + 0.03),
                           note=n.note, velocity=n.velocity))
    return out


def tempo_scale(notes: Sequence[BedNote], factor: float) -> List[BedNote]:
    """Scale note times by `factor` (0.95 = ~5% faster). Pure time math."""
    return [BedNote(start_s=n.start_s * factor, end_s=n.end_s * factor,
                    note=n.note, velocity=n.velocity) for n in notes]


def swing(notes: Sequence[BedNote], sixteenth_s: float, amt: float = 0.15
          ) -> List[BedNote]:
    """Swing 16ths: onsets sitting on odd sixteenths (within ±10 ms) get
    delayed by `amt` × a sixteenth. Quantized-grid notes only — off-grid
    onsets are left alone (already human)."""
    out: List[BedNote] = []
    for n in notes:
        cell = n.start_s / sixteenth_s
        if int(round(cell)) % 2 == 1 and abs(cell - round(cell)) < 0.06:
            shift = amt * sixteenth_s
            out.append(BedNote(n.start_s + shift, n.end_s + shift,
                               n.note, n.velocity))
        else:
            out.append(n)
    return out


def octave_double(notes: Sequence[BedNote], up_st: int = 12,
                  vel_scale: float = 0.4) -> List[BedNote]:
    """Return `notes` + a quieter copy transposed `up_st` semitones — the
    G-funk lead octave-double that makes the melody cut."""
    out = list(notes)
    for n in notes:
        out.append(BedNote(n.start_s, n.end_s, n.note + up_st,
                           n.velocity * vel_scale))
    out.sort(key=lambda n: n.start_s)
    return out


# ---------------------------------------------------------------------------
# S3 — simple recognizable motif (quantize / extract / tile / answer)
# ---------------------------------------------------------------------------

GRID_8TH_S = BAR_S / 8.0          # 8th note on the felt grid (~0.337 s)
MOTIF_SELF_SIMILARITY = 0.6       # cells sharing >=60% pitch classes "repeat"


def _snap_to_dm(midi: int) -> int:
    """Nearest midi pitch whose pitch class is in D natural minor."""
    pc = midi % 12
    if pc in D_MINOR_PCS:
        return midi
    best = min(D_MINOR_PCS, key=lambda d: min((pc - d) % 12, (d - pc) % 12))
    return min(range(midi - 6, midi + 7),
               key=lambda m: (m % 12 != best, abs(m - midi)))


def quantize(notes: Sequence[BedNote], grid_s: float = GRID_8TH_S
             ) -> List[BedNote]:
    """Snap onsets and durations to `grid_s` multiples (min duration = one
    grid step). Idempotent."""
    out: List[BedNote] = []
    for n in notes:
        start = round(n.start_s / grid_s) * grid_s
        dur = max(grid_s, round(n.duration_s / grid_s) * grid_s)
        out.append(BedNote(start_s=start, end_s=start + dur,
                           note=n.note, velocity=n.velocity))
    out.sort(key=lambda n: n.start_s)
    return out


def extract_motif(notes: Sequence[BedNote], bar_s: float = BAR_S,
                  motif_bars: int = 2, max_notes: int = 8,
                  grid_s: float = GRID_8TH_S) -> List[BedNote]:
    """Distill a region into its most-repeated melodic cell, simplified.

    Steps: top-line contour -> segment into `motif_bars`-bar cells -> the
    winning cell is the one most other cells resemble (>=60% shared pitch
    classes; tie-break = note density) -> quantize to the 8th grid, keep the
    <=`max_notes` strongest notes (velocity x duration), snap pitches to
    D natural minor, de-overlap. The result is monophonic by construction.
    """
    mel = top_line(notes)
    if not mel:
        return []
    cell_s = motif_bars * bar_s
    cells: Dict[int, List[BedNote]] = {}
    for n in mel:
        cells.setdefault(int(n.start_s / cell_s), []).append(n)
    pcs_of = {k: {n.note % 12 for n in v} for k, v in cells.items()}

    def score(k: int) -> Tuple[int, int]:
        mine = pcs_of[k]
        repeats = sum(
            1 for j, theirs in pcs_of.items()
            if j != k and mine and len(mine & theirs) / len(mine) >= MOTIF_SELF_SIMILARITY)
        return repeats, len(cells[k])           # (self-similarity, density)

    winner = cells[max(cells, key=score)]
    cell_t0 = min(n.start_s for n in winner)
    picked = sorted(winner, key=lambda n: n.velocity * max(n.duration_s, 0.01),
                    reverse=True)[:max_notes]
    picked.sort(key=lambda n: n.start_s)
    q = quantize([BedNote(n.start_s - cell_t0, n.end_s - cell_t0, n.note,
                          n.velocity) for n in picked], grid_s)
    # monophonic: one note per grid slot — the higher pitch wins (the motif
    # is the top line); then clamp each note to the next onset.
    slots: Dict[float, BedNote] = {}
    for n in q:
        cur = slots.get(n.start_s)
        if cur is None or n.note > cur.note:
            slots[n.start_s] = n
    seq = [slots[k] for k in sorted(slots)]
    out: List[BedNote] = []
    for i, n in enumerate(seq):
        nxt = seq[i + 1].start_s if i + 1 < len(seq) else None
        end = min(n.end_s, nxt) if nxt is not None else n.end_s
        if end - n.start_s < 0.03:
            continue                            # degenerate slot, drop it
        out.append(BedNote(start_s=n.start_s, end_s=end,
                           note=_snap_to_dm(n.note), velocity=n.velocity))
    return out


def tile_motif(motif: Sequence[BedNote], motif_s: float,
               n_reps: int) -> List[BedNote]:
    """Repeat `motif` verbatim `n_reps` times, rep k offset by k*motif_s."""
    out: List[BedNote] = []
    for k in range(n_reps):
        off = k * motif_s
        out.extend(BedNote(n.start_s + off, n.end_s + off, n.note, n.velocity)
                   for n in motif)
    out.sort(key=lambda n: n.start_s)
    return out


def answer_motif(motif: Sequence[BedNote], n_tail: int = 2) -> List[BedNote]:
    """A' response: same rhythm; the last `n_tail` notes resolve to the
    motif's opening pitch class (nearest midi, same octave)."""
    out = list(motif)
    if not out:
        return out
    open_pc = out[0].note % 12
    for i in range(len(out) - min(n_tail, len(out)), len(out)):
        n = out[i]
        new_note = min(range(n.note - 6, n.note + 7),
                       key=lambda m: (m % 12 != open_pc, abs(m - n.note)))
        out[i] = BedNote(n.start_s, n.end_s, new_note, n.velocity)
    return out


# ---------------------------------------------------------------------------
# S4 — recognizable riff from the RAW native-key transcription
#
# Root cause of the S3 rejection: the S3 motif was extracted from
# ``region_54_67_cleaned_Dm.mid``, whose pitches ``bed_lanes.cleanup`` had
# scale-locked from F# minor onto D minor (C#->D, F#->F, G#->G, B->Bb),
# rewriting every interval of the riff. S4 instead reads the raw MIDI,
# filters the register, folds octave errors onto the line's median, picks the
# best self-repeating FULL 2-bar cell, and TRANSPOSES it -4 st (F#m -> Dm)
# so every interval is preserved. Nothing is snapped to a scale here.
# ---------------------------------------------------------------------------

GRID_16TH_S = BAR_S / 16.0         # 16th note on the felt grid (~0.168 s)
PC_NAMES = ("C", "C#", "D", "D#", "E", "F",
            "F#", "G", "G#", "A", "A#", "B")

# Krumhansl-Schmuckler key profiles (numpy-only estimate_key).
_KS_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52,
             5.19, 2.39, 3.66, 2.29, 2.88)
_KS_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54,
             4.75, 3.98, 2.69, 3.34, 3.17)


def note_name(midi: int) -> str:
    """MIDI -> name, e.g. 69 -> 'A4'."""
    return f"{PC_NAMES[int(midi) % 12]}{int(midi) // 12 - 1}"


def transpose(notes: Sequence[BedNote], st: int) -> List[BedNote]:
    """Pure pitch shift — every interval preserved, no scale snapping."""
    return [BedNote(n.start_s, n.end_s, n.note + st, n.velocity)
            for n in notes]


def estimate_key(notes: Sequence[BedNote]) -> Tuple[int, str, float]:
    """Duration-weighted pitch-class histogram vs Krumhansl profiles.

    Returns ``(tonic_pc, mode, r)`` for the best-correlating of the 24 keys.
    This is the guard that would have caught the S3 scale_lock snap: it is
    computed on the RAW transcription, before any cleanup. Empty input ->
    ``(0, "unknown", 0.0)``.
    """
    hist = np.zeros(12, dtype=np.float64)
    for n in notes:
        hist[n.note % 12] += max(n.duration_s, 0.0)
    if hist.sum() <= 0.0:
        return 0, "unknown", 0.0
    best: Tuple[int, str, float] = (0, "major", -2.0)
    for root in range(12):
        for mode, prof in (("major", _KS_MAJOR), ("minor", _KS_MINOR)):
            r = float(np.corrcoef(hist, np.roll(prof, root))[0, 1])
            if np.isfinite(r) and r > best[2]:
                best = (root, mode, r)
    return best


def fold_octaves(notes: Sequence[BedNote], max_dist: int = 7
                 ) -> List[BedNote]:
    """Fold transcription octave errors onto the line's median pitch.

    Any note more than ``max_dist`` semitones from the median is shifted by
    +-12 toward it until it is inside the band (an octave-fold always lands
    within 6 st, so this terminates). Kills sub-bass intrusions and 24-st
    leaps while preserving each note's pitch class.
    """
    if not notes:
        return []
    med = float(np.median([n.note for n in notes]))
    out: List[BedNote] = []
    for n in notes:
        m = n.note
        while m - med > max_dist:
            m -= 12
        while med - m > max_dist:
            m += 12
        out.append(BedNote(n.start_s, n.end_s, m, n.velocity))
    return out


def extract_riff(notes: Sequence[BedNote], motif_bars: int = 2,
                 grid_s: float = GRID_16TH_S, min_midi: int = 55,
                 max_notes: int = 16
                 ) -> Tuple[List[BedNote], float]:
    """Extract the recognizable riff from the RAW native-key transcription.

    Returns ``(riff, cell_t0)`` — the riff is monophonic, on the 16th grid,
    legato-filled, RELATIVE to ``cell_t0`` (the winning cell's absolute start
    in the region timeline, so the caller can pull the same window's bass).

    Steps:
      1. register floor (``min_midi``) -> ``top_line`` -> ``fold_octaves``.
      2. Candidates are FULL ``motif_bars``-bar cells only — a partial tail
         cell can no longer win on a small shared pc set.
      3. A cell scores on notes that repeat in OTHER cells at the same
         onset slot (+-1 grid) with the same pitch class; ties break on
         density.
      4. Quantize to 16ths, one top note per onset slot, keep at most
         ``max_notes`` by velocity (no duration bias — S3's velocity*dur
         scoring kept only long notes).
      5. Legato-fill each note to the next onset, capped at one beat; the
         last note runs to the cell end, capped (fixes the 75%-silence loop).
    """
    mel = [n for n in notes if n.note >= min_midi]
    mel = fold_octaves(top_line(mel))
    if not mel:
        return [], 0.0
    cell_s = motif_bars * BAR_S
    mel_end = max(n.end_s for n in mel)
    cells: Dict[int, List[BedNote]] = {}
    for n in mel:
        k = int(n.start_s / cell_s)
        if (k + 1) * cell_s <= mel_end + grid_s:     # full cells only
            cells.setdefault(k, []).append(n)
    if not cells:                                   # region shorter than a cell
        for n in mel:
            cells.setdefault(int(n.start_s / cell_s), []).append(n)

    def _match_count(k: int, j: int) -> int:
        cnt = 0
        for n in cells[k]:
            rel = n.start_s - k * cell_s
            for m in cells[j]:
                if (m.note % 12 == n.note % 12
                        and abs(m.start_s - j * cell_s - rel) <= grid_s + 1e-9):
                    cnt += 1
                    break
        return cnt

    def _score(k: int) -> Tuple[int, int]:
        return (sum(_match_count(k, j) for j in cells if j != k),
                len(cells[k]))

    win_k = max(cells, key=_score)
    cell_t0 = win_k * cell_s
    rel = [BedNote(n.start_s - cell_t0, n.end_s - cell_t0, n.note, n.velocity)
           for n in cells[win_k]]
    q = quantize(rel, grid_s)
    slots: Dict[float, BedNote] = {}
    for n in q:
        if n.start_s >= cell_s - 1e-9:              # quantized past the edge
            continue
        cur = slots.get(n.start_s)
        if cur is None or n.note > cur.note:
            slots[n.start_s] = n
    seq = [slots[k] for k in sorted(slots)]
    if len(seq) > max_notes:
        keep = {id(n) for n in sorted(seq, key=lambda n: n.velocity,
                                      reverse=True)[:max_notes]}
        seq = [n for n in seq if id(n) in keep]
    beat_s = BAR_S / 4.0
    riff: List[BedNote] = []
    for i, n in enumerate(seq):
        limit = seq[i + 1].start_s if i + 1 < len(seq) else cell_s
        end = min(limit, n.start_s + beat_s)
        riff.append(BedNote(start_s=n.start_s,
                            end_s=max(end, n.start_s + 0.03),
                            note=n.note, velocity=n.velocity))
    return riff, cell_t0


def riff_stats(riff: Sequence[BedNote], cell_s: float) -> dict:
    """Density/coverage/leap numbers for O5 (``check_riff.py``)."""
    n = len(riff)
    coverage = sum(x.duration_s for x in riff) / cell_s if cell_s > 0 else 0.0
    leap = max((abs(b.note - a.note) for a, b in zip(riff, riff[1:])),
               default=0)
    return {"n_notes": n,
            "notes_per_s": round(n / cell_s, 3) if cell_s > 0 else 0.0,
            "coverage": round(coverage, 3),
            "max_leap_st": leap}


def _nearest_diatonic_root(pc: int) -> int:
    """Snap a pitch class to the nearest D-natural-minor chord root."""
    return min(D_MINOR_PCS,
               key=lambda d: min((pc - d) % 12, (d - pc) % 12))


def derive_chords(bass: Sequence[BedNote], melody: Sequence[BedNote],
                  n_bars: int, bar_s: float = BAR_S,
                  voicing_lo: int = 57, voicing_hi: int = 72
                  ) -> List[dict]:
    """Per-bar diatonic-7th chords in D minor, derived from the transcription.

    Each bar's root = the strongest bass pitch class (by total on-time),
    snapped to the nearest diatonic degree; melody tones are counted as
    chord-tone evidence. Bars with no bass content fall back to the
    i-VI-III-VII cycle phase-locked to the loop. Returns one dict per bar:
    ``{"bar", "root_pc", "name", "notes": [midi...]}`` voiced inside
    [voicing_lo, voicing_hi] as rootless-ish 3-5-7-9 grips (the sub lane owns
    the actual root).
    """
    chords: List[dict] = []
    for bar in range(n_bars):
        t0, t1 = bar * bar_s, (bar + 1) * bar_s
        pc_time: Dict[int, float] = {}
        for n in bass:
            ov = max(0.0, min(n.end_s, t1) - max(n.start_s, t0))
            if ov > 0:
                pc_time[n.note % 12] = pc_time.get(n.note % 12, 0.0) + ov
        if pc_time:
            root_pc = _nearest_diatonic_root(max(pc_time, key=pc_time.get))
        else:
            root_pc = FALLBACK_PROG[bar % len(FALLBACK_PROG)]
        name, pcs = _DMINOR_7TH[root_pc]
        # voice the 7th chord without the root (sub covers it): 3,5,7,9
        tone_pcs = list(pcs[1:]) + [(root_pc + 2) % 12]
        voiced = sorted(
            min(range(voicing_lo, voicing_hi + 1), key=lambda m: abs(m % 12 - pc))
            for pc in tone_pcs)
        chords.append({"bar": bar, "root_pc": root_pc, "name": name,
                       "notes": voiced})
    return chords


def chord_bednotes(chords: Sequence[dict], bar_s: float = BAR_S,
                   velocity: float = 0.55) -> List[BedNote]:
    """Whole-note chord BedNotes — one sustained grip per bar."""
    out: List[BedNote] = []
    for c in chords:
        t0, t1 = c["bar"] * bar_s, (c["bar"] + 1) * bar_s
        for m in c["notes"]:
            out.append(BedNote(start_s=t0 + 0.02, end_s=t1 - 0.05,
                               note=m, velocity=velocity))
    return out


def bass_root_notes(chords: Sequence[dict], bar_s: float = BAR_S,
                    root_octave: int = 2, velocity: float = 0.9
                    ) -> List[BedNote]:
    """Sub lane: the chord root sustained per bar at `root_octave`."""
    out: List[BedNote] = []
    for c in chords:
        root_midi = c["root_pc"] + 12 * (root_octave + 1)  # pc -> octave 2
        out.append(BedNote(start_s=c["bar"] * bar_s + 0.01,
                           end_s=(c["bar"] + 1) * bar_s - 0.03,
                           note=root_midi, velocity=velocity))
    return out

def _soft_clip(out: np.ndarray, drive: float) -> np.ndarray:
    """tanh soft-clip normalized so |in|<=1 stays <=1, plus a hard peak guard
    (tanh(d*x)/tanh(d) alone can reach 1/tanh(d) > 1 for overdriven input)."""
    y = np.tanh(drive * out) / np.tanh(drive)
    peak = float(np.abs(y).max())
    if peak > 0.99:
        y = y * (0.99 / peak)
    return y.astype(np.float32)


# ---------------------------------------------------------------------------
# Voices — stereo (n, 2) float32
# ---------------------------------------------------------------------------

def _buf_for(notes: Sequence[BedNote], sr: int, tail_s: float = 2.0) -> int:
    if not notes:
        return sr
    end = max(n.start_s + n.duration_s for n in notes)
    return int((end + tail_s) * sr)


def render_rhodes(notes: Sequence[BedNote], sr: int = 44100,
                  decay_s: float = 1.8, trem_hz: float = 4.6,
                  trem_depth: float = 0.45) -> np.ndarray:
    """Suitcase EP: bell partial + warmth partials + stereo tremolo pan."""
    if not notes:
        return np.zeros((sr, 2), dtype=np.float32)
    n_samples = _buf_for(notes, sr)
    out = np.zeros((n_samples, 2), dtype=np.float64)
    for n in notes:
        f = _midi_to_freq(n.note)
        s0 = int(n.start_s * sr)
        s1 = min(n_samples, s0 + int(max(n.duration_s, 0.05) * sr))
        if s1 <= s0:
            continue
        t = np.arange(s1 - s0) / sr
        env = _env(s1 - s0, sr, attack_ms=6.0, release_ms=60.0,
                   decay_s=decay_s, velocity=n.velocity)
        bright = 0.6 + 0.4 * n.velocity  # velocity -> brightness
        bell = np.sin(2 * np.pi * (f * 3.98) * t) * np.exp(-t / 0.35) * 0.35
        osc = (np.sin(2 * np.pi * f * t)
               + 0.4 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.9)
               + 0.18 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.5))
        sig = (osc * bright + bell) * env
        # stereo tremolo: L/R antiphase — classic suitcase pan
        trem = np.sin(2 * np.pi * trem_hz * t)
        out[s0:s1, 0] += sig * (1.0 - trem_depth * 0.5 * (1.0 + trem))
        out[s0:s1, 1] += sig * (1.0 - trem_depth * 0.5 * (1.0 - trem))
    return _soft_clip(out, 1.15)


def render_warm_pad(notes: Sequence[BedNote], sr: int = 44100,
                    detune_cents: float = 10.0, cutoff_hz: float = 1200.0,
                    attack_ms: float = 300.0) -> np.ndarray:
    """Warm pad: 3 detuned saws per channel, independent L/R drift + LPF."""
    if not notes:
        return np.zeros((sr, 2), dtype=np.float32)
    n_samples = _buf_for(notes, sr, tail_s=3.0)
    out = np.zeros((n_samples, 2), dtype=np.float64)
    det = 2.0 ** (detune_cents / 1200.0)
    for n in notes:
        f = _midi_to_freq(n.note)
        s0 = int(n.start_s * sr)
        s1 = min(n_samples, s0 + int(max(n.duration_s, 0.1) * sr))
        if s1 <= s0:
            continue
        t = np.arange(s1 - s0) / sr
        env = _env(s1 - s0, sr, attack_ms=attack_ms, release_ms=400.0,
                   decay_s=8.0, velocity=n.velocity)
        for ch, cents in ((0, det), (1, 1.0 / det)):
            drift = 1.0 + 0.0015 * np.sin(2 * np.pi * 0.4 * t + ch)
            saw = (_saw(f * cents * drift * t)
                   + 0.6 * _saw(f * cents * 0.5 * drift * t)
                   + 0.35 * _saw(f * cents * 2.01 * drift * t)) * (1.0 / 1.95)
            out[s0:s1, ch] += saw * env
    for ch in (0, 1):
        out[:, ch] = _one_pole_lpf(out[:, ch], sr, cutoff_hz)
    return _soft_clip(out, 1.1)


def render_gfunk_lead(notes: Sequence[BedNote], sr: int = 44100,
                      glide_ms: float = 100.0, vib_hz: float = 5.5,
                      vib_delay_ms: float = 180.0,
                      vib_depth_st: float = 0.45) -> np.ndarray:
    """Mono-legato G-funk lead: sine+saw, per-note portamento, delayed vibrato.

    Notes must be sorted by onset; consecutive notes glide `glide_ms` from
    the previous pitch (legato), retriggering when the gap exceeds one
    sixteenth of the felt grid.
    """
    if not notes:
        return np.zeros((sr, 2), dtype=np.float32)
    seq = sorted(notes, key=lambda n: n.start_s)
    n_samples = _buf_for(seq, sr)
    out = np.zeros(n_samples, dtype=np.float64)
    prev_freq: Optional[float] = None
    for n in seq:
        f = _midi_to_freq(n.note)
        s0 = int(n.start_s * sr)
        s1 = min(n_samples, s0 + int(max(n.duration_s, 0.05) * sr))
        if s1 <= s0:
            continue
        t = np.arange(s1 - s0) / sr
        env = _env(s1 - s0, sr, attack_ms=12.0, release_ms=80.0,
                   decay_s=max(n.duration_s, 0.3), velocity=n.velocity)
        if prev_freq is not None and glide_ms > 0:
            g = min(len(t), int(glide_ms * sr / 1000.0))
            ramp = np.ones(len(t))
            ramp[:g] = np.linspace(0.0, 1.0, g)
            freq = prev_freq * (f / prev_freq) ** ramp
        else:
            freq = np.full(len(t), f)
        vib = np.zeros(len(t))
        d = int(vib_delay_ms * sr / 1000.0)
        if len(t) > d:
            vib[d:] = vib_depth_st * np.sin(
                2 * np.pi * vib_hz * (t[d:] - t[d]))
        phase = np.cumsum(freq * 2.0 ** (vib / 12.0)) / sr
        osc = np.sin(2 * np.pi * phase) + 0.35 * _saw(phase)
        out[s0:s1] += osc * env
        prev_freq = f
    out = _soft_clip(out, 1.4)
    return np.stack([out, out], axis=1)


def render_sub(notes: Sequence[BedNote], sr: int = 44100) -> np.ndarray:
    """Sub bass: sine + soft 2nd harmonic, tanh-saturated, mono->stereo."""
    if not notes:
        return np.zeros((sr, 2), dtype=np.float32)
    n_samples = _buf_for(notes, sr)
    out = np.zeros(n_samples, dtype=np.float64)
    for n in notes:
        f = _midi_to_freq(n.note)
        s0 = int(n.start_s * sr)
        s1 = min(n_samples, s0 + int(max(n.duration_s, 0.1) * sr))
        if s1 <= s0:
            continue
        t = np.arange(s1 - s0) / sr
        env = _env(s1 - s0, sr, attack_ms=15.0, release_ms=60.0,
                   decay_s=max(n.duration_s, 0.5), velocity=n.velocity)
        sig = np.sin(2 * np.pi * f * t) + 0.15 * np.sin(2 * np.pi * f * 2 * t)
        out[s0:s1] += sig * env
    out = _soft_clip(out, 1.3)
    return np.stack([out, out], axis=1)


def render_simple_lead(notes: Sequence[BedNote], sr: int = 44100
                       ) -> np.ndarray:
    """Plain tone lead — the "simple MIDI tone": sine + 0.15x2nd harmonic,
    10 ms attack, 100 ms release, flat sustain (no portamento, vibrato,
    detune or FX-osc). Mono -> stereo, peak-guarded."""
    if not notes:
        return np.zeros((sr, 2), dtype=np.float32)
    n_samples = _buf_for(notes, sr)
    out = np.zeros(n_samples, dtype=np.float64)
    for n in notes:
        f = _midi_to_freq(n.note)
        s0 = int(n.start_s * sr)
        s1 = min(n_samples, s0 + int(max(n.duration_s, 0.05) * sr))
        if s1 <= s0:
            continue
        t = np.arange(s1 - s0) / sr
        env = _env(s1 - s0, sr, attack_ms=10.0, release_ms=100.0,
                   decay_s=max(n.duration_s * 4.0, 1.0), velocity=n.velocity)
        sig = np.sin(2 * np.pi * f * t) + 0.15 * np.sin(2 * np.pi * f * 2 * t)
        out[s0:s1] += sig * env
    out = _soft_clip(out, 1.2)
    return np.stack([out, out], axis=1)


# ---------------------------------------------------------------------------
# FX + assembly
# ---------------------------------------------------------------------------

def west_coast_chain(lanes: Dict[str, np.ndarray], sr: int = 44100,
                     ) -> np.ndarray:
    """Per-lane pedalboard FX, then sum to a stereo bus.

    ``lanes`` maps a lane name to stereo audio; FX per lane:
    rhodes: Chorus -> Reverb; pad: LadderFilter LPF -> Reverb;
    lead: dotted-8th-feel Delay -> Reverb; sub/others: dry.
    Final bus: light glue Compressor -> Gain.
    """
    from pedalboard import (Chorus, Compressor, Delay, Gain, LadderFilter,
                            Pedalboard, Reverb)

    def run(x: np.ndarray, board: Pedalboard) -> np.ndarray:
        # pedalboard wants (channels, samples)
        return board(np.ascontiguousarray(x.T), sr).T.astype(np.float32)

    chains = {
        "rhodes": lambda: Pedalboard([
            Chorus(rate_hz=0.9, depth=0.25, mix=0.35),
            Reverb(room_size=0.35, damping=0.6, wet_level=0.18,
                   dry_level=1.0, width=0.9)]),
        "pad": lambda: Pedalboard([
            LadderFilter(mode=LadderFilter.Mode.LPF24, cutoff_hz=3200.0,
                         resonance=0.15, drive=1.2),
            Reverb(room_size=0.5, damping=0.7, wet_level=0.25,
                   dry_level=1.0, width=1.0)]),
        "lead": lambda: Pedalboard([
            Delay(delay_seconds=0.375, feedback=0.28, mix=0.22),
            Reverb(room_size=0.45, damping=0.5, wet_level=0.22,
                   dry_level=1.0, width=0.95)]),
    }
    bus: Optional[np.ndarray] = None
    for name, audio in lanes.items():
        if audio is None or audio.size == 0:
            continue
        fn = chains.get(name)
        wet = run(audio, fn()) if fn else audio.astype(np.float32)
        bus = wet if bus is None else bus[: len(wet)] + wet[: len(bus)]
    if bus is None:
        return np.zeros((sr, 2), dtype=np.float32)
    glue = Pedalboard([
        Compressor(threshold_db=-16.0, ratio=2.0, attack_ms=10.0,
                   release_ms=120.0),
        Gain(gain_db=0.0)])
    return run(bus.astype(np.float32), glue)


def fit_loop(audio: np.ndarray, sr: int, loop_s: float,
             fade_ms: float = 50.0) -> np.ndarray:
    """Fold render tails into the head so the loop wraps seamlessly.

    Material past `loop_s` (reverb/decay tails) is wrapped additively onto the
    head. The last `fade_ms` of the body then crossfades toward the head
    content, so wrapping end->start lands on (nearly) the same waveform and
    does not click. Returns exactly ``int(loop_s*sr)`` samples.
    """
    n = int(loop_s * sr)
    if audio.shape[0] <= n:
        out = np.zeros((n,) + audio.shape[1:], dtype=np.float32)
        out[: audio.shape[0]] = audio
        return out
    body = audio[:n].astype(np.float64).copy()
    tail = audio[n:]
    k = min(len(tail), n)
    body[:k] += tail[:k]
    f = max(1, int(fade_ms * sr / 1000.0))
    w = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, f))
    if audio.ndim == 2:
        w = w[:, None]
    head = body[:f].copy()
    body[-f:] = body[-f:] * (1.0 - w) + head * w
    return body[:n].astype(np.float32)


def mixdown(lanes: Dict[str, np.ndarray],
            gains: Optional[Dict[str, float]] = None) -> np.ndarray:
    """Sum named lanes to the longest buffer; per-lane gains; peak-report."""
    gains = gains or {}
    n = max((a.shape[0] for a in lanes.values() if a is not None), default=0)
    out = np.zeros((n, 2), dtype=np.float64)
    for name, a in lanes.items():
        if a is None or a.size == 0:
            continue
        g = gains.get(name, 1.0)
        m = min(n, a.shape[0])
        out[:m] += a[:m].astype(np.float64) * g
    return out.astype(np.float32)
