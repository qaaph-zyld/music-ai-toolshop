"""Melodic-bed lanes for the OGCM drill flip (wave W1' — bed-lane spike).

Pure-code render path for the melodic-bed pivot (megaplan A22–A25/A28, F8):
basic-pitch ONNX transcription -> MIDI cleanup -> numpy voice render. No DAW
required; same technique family as `bass808.py` (deterministic, testable,
zero new runtime deps beyond pretty_midi which is already installed).

Three lanes feed the GATE C2 blind audition:
- **Lane A** — existing chop pack (`stems/flip_chops_v2`); no new code here.
- **Lane B** — interpolated bed: basic-pitch on the top GATE-C regions of the
  v2 `(other)` bed -> MIDI cleanup -> numpy voice render -> 8-bar felt loop.
- **Lane C** — hand-programmed 2–3 bar dark Dm/C#m motifs via pretty_midi ->
  same numpy voices.

MIDI cleanup (per megaplan W1' step 3):
- quantize onsets to the 89.1 felt grid (configurable subdivision),
- prune notes with confidence < 0.4 and duration < 80 ms,
- scale-lock to the landed key (snap out-of-scale pitches to the nearest
  scale degree, mode preserved).

Numpy voices (per megaplan research synthesis):
- epiano: sine + integer overtones + exp decay + tanh saturation,
- pad: detuned saws + one-pole LPF + slow attack,
- pluck: Karplus-Strong (optional).

pretty_midi handles MIDI I/O. Loudness matching uses pyloudnorm (already a
flip-extra dep) for the ADR-009 blind-pack contract (<=0.3 LU).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
import pretty_midi

# Felt-grid default (megaplan: 178.2 written / 89.1 felt).
FELT_BPM = 89.1
# Cleanup defaults (megaplan W1' step 3).
MIN_CONFIDENCE = 0.4
MIN_NOTE_MS = 80.0
# Scale pitch-class sets by mode.
_SCALE_INTERVALS = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),  # natural minor
}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _note_to_pc(name: str) -> int:
    return NOTE_NAMES.index(name)


# ---------------------------------------------------------------------------
# Note model
# ---------------------------------------------------------------------------

@dataclass
class BedNote:
    """One bed note: (start_s, end_s, midi_note, velocity/confidence 0-1)."""

    start_s: float
    end_s: float
    note: int
    velocity: float = 0.8

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_s - self.start_s)


# ---------------------------------------------------------------------------
# MIDI I/O (pretty_midi)
# ---------------------------------------------------------------------------

def events_to_notes(events: Sequence[Tuple]) -> List[BedNote]:
    """Convert basic-pitch note events to BedNote list.

    basic-pitch event tuple = ``(start_s, end_s, midi_note, velocity, pitch_bends)``.
    """
    out: List[BedNote] = []
    for ev in events:
        start, end, note, vel = ev[0], ev[1], int(ev[2]), float(ev[3])
        out.append(BedNote(start_s=float(start), end_s=float(end),
                            note=note, velocity=max(0.0, min(1.0, vel))))
    out.sort(key=lambda n: n.start_s)
    return out


def notes_to_pretty_midi(notes: Sequence[BedNote], bpm: float = FELT_BPM,
                         program: int = 0) -> pretty_midi.PrettyMIDI:
    """Render BedNotes to a single-instrument PrettyMIDI object."""
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=program, is_drum=False)
    for n in notes:
        start = max(0.0, float(n.start_s))
        end = max(start + 1e-3, float(n.end_s))
        vel = int(round(max(0.0, min(1.0, n.velocity)) * 127))
        inst.notes.append(pretty_midi.Note(velocity=max(1, vel),
                                            pitch=int(n.note),
                                            start=start, end=end))
    pm.instruments.append(inst)
    return pm


def pretty_midi_to_notes(pm: pretty_midi.PrettyMIDI) -> List[BedNote]:
    """Flatten a PrettyMIDI object's instruments to BedNotes."""
    out: List[BedNote] = []
    for inst in pm.instruments:
        for nt in inst.notes:
            out.append(BedNote(start_s=nt.start, end_s=nt.end,
                                note=nt.pitch, velocity=nt.velocity / 127.0))
    out.sort(key=lambda n: n.start_s)
    return out


def save_midi(path: Union[str, Path], pm: pretty_midi.PrettyMIDI) -> None:
    pm.write(str(path))


def load_midi(path: Union[str, Path]) -> pretty_midi.PrettyMIDI:
    return pretty_midi.PrettyMIDI(str(path))


# ---------------------------------------------------------------------------
# Cleanup: prune low-confidence + short notes
# ---------------------------------------------------------------------------

def prune_low_confidence(notes: Sequence[BedNote],
                         min_conf: float = MIN_CONFIDENCE) -> List[BedNote]:
    return [n for n in notes if n.velocity >= min_conf]


def prune_short(notes: Sequence[BedNote],
                min_ms: float = MIN_NOTE_MS) -> List[BedNote]:
    min_s = min_ms / 1000.0
    return [n for n in notes if n.duration_s + 1e-9 >= min_s]


# ---------------------------------------------------------------------------
# Cleanup: quantize to the felt grid
# ---------------------------------------------------------------------------

def quantize_to_grid(notes: Sequence[BedNote], bpm: float = FELT_BPM,
                     subdivision: int = 16) -> List[BedNote]:
    """Snap note onsets/offsets to the nearest grid step.

    `subdivision` = steps per beat (4 = sixteenth notes, 16 = 32nd notes).
    Durations are preserved; only start/end are snapped. Notes are sorted by
    onset first (basic-pitch returns events in descending-start order; without
    sorting, a defensive non-decreasing pass would cascade every note to the
    latest onset).
    """
    step = (60.0 / bpm) / subdivision
    ordered = sorted(notes, key=lambda n: n.start_s)
    out: List[BedNote] = []
    for n in ordered:
        start = round(n.start_s / step) * step
        dur = n.duration_s
        end = round((start + dur) / step) * step
        if end <= start:
            end = start + step
        out.append(BedNote(start_s=start, end_s=end, note=n.note,
                           velocity=n.velocity))
    return out


# ---------------------------------------------------------------------------
# Cleanup: scale-lock to landed key
# ---------------------------------------------------------------------------

def _scale_pcs(root: str, mode: str) -> List[int]:
    root_pc = _note_to_pc(root)
    intervals = _SCALE_INTERVALS.get(mode, _SCALE_INTERVALS["minor"])
    return [(root_pc + iv) % 12 for iv in intervals]


def _snap_to_scale(pitch: int, scale_pcs: Sequence[int]) -> int:
    """Snap a MIDI pitch to the nearest in-scale pitch (octave preserved)."""
    pc = pitch % 12
    if pc in scale_pcs:
        return pitch
    # search outward by semitone for the nearest in-scale pitch class
    best = None
    best_dist = 99
    for cand_pc in scale_pcs:
        # distance in pitch-class space, but we keep the octave of the original
        delta = (cand_pc - pc) % 12
        if delta > 6:
            delta = delta - 12
        if abs(delta) < best_dist:
            best_dist = abs(delta)
            best = pitch + delta
    return best if best is not None else pitch


def scale_lock(notes: Sequence[BedNote], root: str,
               mode: str = "minor") -> List[BedNote]:
    """Snap each note's pitch to the nearest scale degree (mode preserved)."""
    scale_pcs = _scale_pcs(root, mode)
    return [BedNote(start_s=n.start_s, end_s=n.end_s,
                    note=_snap_to_scale(n.note, scale_pcs),
                    velocity=n.velocity) for n in notes]


# ---------------------------------------------------------------------------
# Full cleanup pipeline
# ---------------------------------------------------------------------------

def cleanup(notes: Sequence[BedNote], bpm: float = FELT_BPM,
            subdivision: int = 16, min_conf: float = MIN_CONFIDENCE,
            min_ms: float = MIN_NOTE_MS, root: Optional[str] = None,
            mode: str = "minor") -> List[BedNote]:
    """Run the full MIDI cleanup: prune conf + prune short + quantize + scale-lock.

    Scale-lock is applied only when `root` is given.
    """
    out = prune_low_confidence(notes, min_conf=min_conf)
    out = prune_short(out, min_ms=min_ms)
    out = quantize_to_grid(out, bpm=bpm, subdivision=subdivision)
    if root is not None:
        out = scale_lock(out, root=root, mode=mode)
    return out


# ---------------------------------------------------------------------------
# Numpy voices
# ---------------------------------------------------------------------------

def _midi_to_freq(note: float) -> float:
    return 440.0 * 2.0 ** ((note - 69.0) / 12.0)


def _note_envelope(start_s: float, dur_s: float, n_samples: int, sr: int,
                   attack_ms: float, release_ms: float, decay_s: float,
                   velocity: float) -> Tuple[int, int, np.ndarray]:
    """Per-note ADSR window over its sample span. Returns (start, stop, env)."""
    start = int(start_s * sr)
    stop = min(n_samples, int((start_s + dur_s) * sr))
    if stop <= start:
        return start, stop, np.zeros(0)
    atk = max(1, int(attack_ms * sr / 1000.0))
    rel = max(1, int(release_ms * sr / 1000.0))
    a_end = min(stop, start + atk)
    body_len = max(0, stop - a_end)
    env = np.zeros(stop - start, dtype=np.float64)
    # attack
    env[: a_end - start] = np.linspace(0, velocity, a_end - start)
    # decay/sustain body
    if body_len > 0:
        body = np.arange(body_len) / sr
        env[a_end - start:] = velocity * np.exp(-body / (decay_s / 3.0))
    # release tail (overlaps into the next region; caller maxes)
    return start, stop, env


def render_epiano(notes: Sequence[BedNote], sr: int = 22050,
                  decay_s: float = 1.2, drive: float = 1.4) -> np.ndarray:
    """E-piano voice: sine + integer overtones + exp decay + tanh saturation."""
    if not notes:
        return np.zeros(0, dtype=np.float32)
    n_samples = int((max(n.start_s + n.duration_s for n in notes) + 0.5) * sr) + sr
    out = np.zeros(n_samples, dtype=np.float64)
    # overtone series (fundamental + 2nd + 3rd + 4th, decaying)
    harms = [(1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12)]
    for n in notes:
        f = _midi_to_freq(n.note)
        start, stop, env = _note_envelope(n.start_s, n.duration_s, n_samples, sr,
                                          attack_ms=4.0, release_ms=40.0,
                                          decay_s=decay_s, velocity=n.velocity)
        if stop <= start:
            continue
        t = np.arange(stop - start) / sr
        osc = np.zeros(stop - start, dtype=np.float64)
        for mult, amp in harms:
            osc += amp * np.sin(2.0 * np.pi * f * mult * t)
        out[start:stop] += osc * env
    out = np.tanh(drive * out) / np.tanh(drive)
    return out.astype(np.float32)


def lowpass(x: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    """Public one-pole LPF — used by `arrange` for filtered intro beds."""
    return _one_pole_lpf(x, sr, cutoff_hz).astype(np.float32)


def _one_pole_lpf(x: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    """One-pole low-pass filter (RC), vectorised via lfilter-equivalent recursion."""
    if cutoff_hz <= 0 or cutoff_hz >= sr / 2.0:
        return x.astype(np.float64)
    dt = 1.0 / sr
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    a = dt / (rc + dt)
    y = np.zeros_like(x, dtype=np.float64)
    prev = 0.0
    for i, v in enumerate(x):
        prev = prev + a * (v - prev)
        y[i] = prev
    return y


def _saw(phase: np.ndarray) -> np.ndarray:
    return 2.0 * (phase - np.floor(phase + 0.5))


def render_pad(notes: Sequence[BedNote], sr: int = 22050,
               detune_cents: float = 8.0, cutoff_hz: float = 1800.0,
               attack_ms: float = 120.0) -> np.ndarray:
    """Pad voice: detuned saws + one-pole LPF + slow attack."""
    if not notes:
        return np.zeros(0, dtype=np.float32)
    n_samples = int((max(n.start_s + n.duration_s for n in notes) + 0.5) * sr) + sr
    raw = np.zeros(n_samples, dtype=np.float64)
    detune = 2.0 ** (detune_cents / 1200.0)
    for n in notes:
        f = _midi_to_freq(n.note)
        start, stop, env = _note_envelope(n.start_s, n.duration_s, n_samples, sr,
                                          attack_ms=attack_ms, release_ms=200.0,
                                          decay_s=4.0, velocity=n.velocity)
        if stop <= start:
            continue
        t = np.arange(stop - start) / sr
        # two detuned saws
        saw = (_saw(f * detune * t) + _saw(f / detune * t)) * 0.5
        raw[start:stop] += saw * env
    raw = _one_pole_lpf(raw, sr, cutoff_hz)
    raw = np.tanh(1.3 * raw) / np.tanh(1.3)
    return raw.astype(np.float32)


def render_pluck(notes: Sequence[BedNote], sr: int = 22050,
                 decay: float = 0.996) -> np.ndarray:
    """Pluck voice: Karplus-Strong (optional). Excitation = noise burst."""
    if not notes:
        return np.zeros(0, dtype=np.float32)
    n_samples = int((max(n.start_s + n.duration_s for n in notes) + 0.5) * sr) + sr
    out = np.zeros(n_samples, dtype=np.float64)
    rng = np.random.default_rng(42)
    for n in notes:
        f = _midi_to_freq(n.note)
        start = int(n.start_s * sr)
        dur = int(n.duration_s * sr)
        if start >= n_samples or dur <= 0:
            continue
        L = max(2, int(sr / max(1.0, f)))
        # excitation: short noise burst of length L
        buf = rng.standard_normal(L) * n.velocity
        # KS: y[t] = buf[t] for t<L, else decay*0.5*(y[t-L]+y[t-L+1])
        ks = np.zeros(dur, dtype=np.float64)
        ks[: min(L, dur)] = buf[: min(L, dur)]
        for t in range(L, dur):
            ks[t] = decay * 0.5 * (ks[t - L] + ks[t - L + 1])
        end = min(n_samples, start + dur)
        out[start:end] += ks[: end - start]
    return out.astype(np.float32)


VOICES = {"epiano": render_epiano, "pad": render_pad, "pluck": render_pluck}


def render_voice(notes: Sequence[BedNote], voice: str, sr: int = 22050) -> np.ndarray:
    fn = VOICES.get(voice)
    if fn is None:
        raise ValueError(f"unknown voice {voice!r}; choose from {list(VOICES)}")
    return fn(notes, sr=sr)


def render_loop(notes: Sequence[BedNote], voice: str, bars: int = 8,
                bpm: float = FELT_BPM, sr: int = 22050) -> np.ndarray:
    """Render a voice and tile/trim to exactly `bars` felt bars."""
    audio = render_voice(notes, voice, sr=sr)
    target = int(bars * 4 * 60.0 / bpm * sr)
    if audio.size == 0:
        return np.zeros(target, dtype=np.float32)
    if audio.size < target:
        reps = math.ceil(target / audio.size)
        audio = np.tile(audio, reps)
    return audio[:target].astype(np.float32)


# ---------------------------------------------------------------------------
# Loudness (ADR-009 blind-pack helper)
# ---------------------------------------------------------------------------

def measure_lufs(audio: np.ndarray, sr: int) -> float:
    """Measure integrated LUFS via pyloudnorm (already a flip-extra dep)."""
    import pyloudnorm as pyln
    if audio.ndim == 1:
        y = audio.reshape(-1, 1)
    else:
        y = audio
    y = y.astype(np.float64)
    if y.size < int(sr * 0.4):
        return -70.0
    meter = pyln.Meter(sr)
    try:
        return float(meter.integrated_loudness(y))
    except Exception:
        return -70.0


def _gain_to_lufs(audio: np.ndarray, sr: int, target_lufs: float) -> np.ndarray:
    a = audio.astype(np.float64)
    cur = measure_lufs(a, sr)
    # pyloudnorm returns -inf / -70 for near-silent signals. Peak-normalize
    # into a measurable range first, then measure, so the blind pack does not
    # leave a lane at -inf LUFS (ADR-009 spread contract).
    if not np.isfinite(cur) or cur <= -69.0:
        peak = float(np.abs(a).max())
        if peak <= 1e-9:
            return np.zeros_like(audio, dtype=np.float32)
        a = a * (0.5 / peak)
        cur = measure_lufs(a, sr)
        if not np.isfinite(cur) or cur <= -69.0:
            # still unmeasurable (e.g. pure DC) — fall back to RMS heuristic
            rms = float(np.sqrt(np.mean(a ** 2)) + 1e-12)
            cur = 20.0 * np.log10(rms + 1e-12) - 0.691
    delta = target_lufs - cur
    gain = 10.0 ** (delta / 20.0)
    out = (a * gain).astype(np.float32)
    # clip guard
    peak = float(np.abs(out).max())
    if peak > 0.99:
        out = (out * (0.99 / peak)).astype(np.float32)
    return out


def loudness_match_pair(a: np.ndarray, b: np.ndarray, sr: int,
                        target_lufs: float = -18.0) -> Tuple[np.ndarray, np.ndarray]:
    """Normalize both signals to the same target LUFS (ADR-009 <=0.3 LU)."""
    return _gain_to_lufs(a, sr, target_lufs), _gain_to_lufs(b, sr, target_lufs)


def loudness_match_many(signals: Sequence[np.ndarray], sr: int,
                        target_lufs: float = -18.0) -> List[np.ndarray]:
    return [_gain_to_lufs(s, sr, target_lufs) for s in signals]
