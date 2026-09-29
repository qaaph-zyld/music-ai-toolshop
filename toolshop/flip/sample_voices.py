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
