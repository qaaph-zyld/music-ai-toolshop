"""Hybrid sliding-808 voice for the drill flip (wave W2).

**Design** (per R3 research): a synthesized sine/triangle sub voice with
mono legato and exponential portamento — the controllable half of the 808 —
plus an optional mined-kick transient layered on each note attack for the
OGCM fingerprint. Long decay, short release, soft tanh saturation for
phone audibility, and an optional ducking curve around kick events so the
sub does not fight the drum pattern.

Slides are exponential (frequency ratio swept over time) which is how a
real 808's RC glide behaves — a linear-in-Hz ramp sounds wrong in the low
register.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

GLIDE_MS_DEFAULT = 240.0      # drill octave slides sit ~200–300 ms
DECAY_S = 1.6
RELEASE_MS = 40.0
ATTACK_MS = 4.0
DRIVE = 1.6


def midi_to_freq(note: float) -> float:
    return 440.0 * 2.0 ** ((note - 69.0) / 12.0)


@dataclass
class Note808:
    """(start_s, duration_s, midi_note, velocity)."""

    start_s: float
    duration_s: float
    note: float
    velocity: float = 1.0


def _freq_trajectory(notes: Sequence[Note808], n_samples: int, sr: int, glide_s: float) -> np.ndarray:
    """Per-sample frequency under mono-legato exponential glide.

    Between note onsets the frequency approaches the new target as
    ``f(t) = f_t * (f_prev/f_t)^(exp(-t/tau))`` — constant slide *time*
    regardless of interval size, matching 808 RC behaviour.
    """
    freq = np.zeros(n_samples, dtype=np.float64)
    if not notes:
        return freq
    tau = glide_s / 3.0  # ~95% settled after glide_s
    prev_f = midi_to_freq(notes[0].note)
    note_idx = 0
    seg_start = 0
    onsets = sorted(notes, key=lambda n: n.start_s)
    # Build per-segment: [onset_i, onset_{i+1}) glides toward note_i.
    for i, nt in enumerate(onsets):
        start = int(nt.start_s * sr)
        end = int(onsets[i + 1].start_s * sr) if i + 1 < len(onsets) else n_samples
        end = min(end, n_samples)
        if start >= n_samples:
            break
        target = midi_to_freq(nt.note)
        t = np.arange(end - start) / sr
        seg = target * (prev_f / target) ** np.exp(-t / tau)
        freq[start:end] = seg
        prev_f = target
    return freq


def _amp_envelope(notes: Sequence[Note808], n_samples: int, sr: int) -> np.ndarray:
    """Legato amp: per-note attack/decay/release; overlapping notes retrigger
    softly (glide without full re-articulation)."""
    env = np.zeros(n_samples, dtype=np.float64)
    atk = max(1, int(ATTACK_MS * sr / 1000.0))
    rel = max(1, int(RELEASE_MS * sr / 1000.0))
    for nt in sorted(notes, key=lambda n: n.start_s):
        start = int(nt.start_s * sr)
        stop = min(n_samples, int((nt.start_s + nt.duration_s) * sr))
        if stop <= start:
            continue
        # attack
        a_end = min(stop, start + atk)
        env[start:a_end] = np.maximum(env[start:a_end], np.linspace(0, 1, a_end - start) * nt.velocity)
        # sustain+decay body
        body = np.arange(stop - a_end) / sr
        env[a_end:stop] = np.maximum(env[a_end:stop], nt.velocity * np.exp(-body / (DECAY_S / 3.0)))
        # release
        r_end = min(n_samples, stop + rel)
        tail = np.linspace(env[stop - 1] if stop > start else nt.velocity, 0, r_end - stop)
        env[stop:r_end] = np.maximum(env[stop:r_end], tail)
    return env


def render_808(
    notes: Sequence[Note808],
    sr: int,
    glide_ms: float = GLIDE_MS_DEFAULT,
    drive: float = DRIVE,
    transient: Optional[np.ndarray] = None,
    transient_gain: float = 0.6,
    duck_times: Optional[Sequence[float]] = None,
    duck_depth: float = 0.5,
    duck_ms: float = 60.0,
) -> np.ndarray:
    """Render the 808 lane to a mono buffer.

    Args:
        notes: Note808 list (monophonic — overlaps are resolved by sort order).
        sr: Sample rate.
        glide_ms: Portamento time for ~95% pitch convergence (200–300 typical).
        drive: tanh soft-saturation drive (1 = clean).
        transient: Optional mined kick/808 attack buffer layered on each onset
            (the OGCM-fingerprint half of the hybrid).
        transient_gain: Layer level relative to the sub peak.
        duck_times: Kick event times (s) for a simple sidechain-style dip.
        duck_depth: Max attenuation (0–1).
        duck_ms: Dip length.
    """
    if not notes:
        return np.zeros(0, dtype=np.float32)
    n_samples = int((max(n.start_s + n.duration_s for n in notes) + 0.5) * sr) + sr
    freq = _freq_trajectory(notes, n_samples, sr, glide_ms / 1000.0)
    phase = np.cumsum(2.0 * np.pi * freq / sr)
    # triangle blend for upper harmonics: tri = asin(sin) scaled
    tri = (2.0 / np.pi) * np.arcsin(np.clip(np.sin(phase), -1.0, 1.0))
    osc = 0.85 * np.sin(phase) + 0.15 * tri
    env = _amp_envelope(notes, n_samples, sr)
    out = osc * env

    if transient is not None and transient.size:
        t = transient.astype(np.float32)
        t = t / (np.abs(t).max() + 1e-12)
        for nt in notes:
            start = int(nt.start_s * sr)
            seg = t[: max(0, n_samples - start)]
            out[start : start + seg.size] += seg * transient_gain * nt.velocity

    if duck_times:
        dn = int(duck_ms * sr / 1000.0)
        for ts in duck_times:
            s = int(ts * sr)
            e = min(n_samples, s + dn)
            if e > s:
                dip = 1.0 - duck_depth * np.sin(np.linspace(0, np.pi, e - s)) ** 2
                out[s:e] *= dip

    out = np.tanh(drive * out) / np.tanh(drive)
    return out.astype(np.float32)
