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
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Drill-spec retune (megaplan W2 + research synthesis): slide *approach*
# intervals are a minor 3rd or perfect 4th, and the glide window is
# 90–200 ms (the earlier 240 ms default was the generic-808 figure).
GLIDE_MS_MIN = 90.0
GLIDE_MS_MAX = 200.0
GLIDE_MS_DEFAULT = 140.0     # mid-window; drill slide approaches
SLIDE_INTERVALS_ST = (3, 5)  # m3 / P4 — the only sanctioned slide sizes
SLIDES_PER_4BARS = (2, 3)    # 2–3 slides per 4 written bars, landing on kicks
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


# ---------------------------------------------------------------------------
# Drill 808 line programming (megaplan W2 retune)
# ---------------------------------------------------------------------------

def plan_808_line(
    kick_times: Sequence[float],
    bpm: float,
    root_note: float,
    total_s: Optional[float] = None,
    slides_per_4bars: int = 2,
    slide_intervals: Sequence[int] = SLIDE_INTERVALS_ST,
) -> Tuple[List[Note808], List[dict]]:
    """Program a mono-legato 808 line locked to the kick pattern.

    One 808 note per kick onset (kick+808 = one low-end system). Most notes
    sit on `root_note`; before each *slide target* kick the previous note is
    raised by a m3/P4 (`slide_intervals`), so the note whose onset lands ON
    the target kick glides down into the root — a drill slide that lands on
    the kick. `slides_per_4bars` controls how many target kicks per 4
    written bars are chosen (spec window: 2–3, evenly distributed).

    Args:
        kick_times: sorted kick onset times (s) the 808 should follow.
        bpm: written-grid tempo (defines the 4-bar block = 16 beats).
        root_note: MIDI note for the section root (landed key root).
        total_s: render horizon; last note is held to this if given.
        slides_per_4bars: slides per 4 written bars (2 or 3).
        slide_intervals: allowed approach intervals in semitones (m3/P4).

    Returns:
        ``(notes, slide_events)`` — notes for `render_808` (monophonic:
        strictly increasing onsets, each ending at the next onset + a small
        legato overlap) and a slide table ``[{time_s, interval_st, block}]``
        where each entry's `time_s` is exactly a kick onset.
    """
    if slides_per_4bars not in SLIDES_PER_4BARS:
        raise ValueError(
            f"slides_per_4bars must be one of {SLIDES_PER_4BARS} "
            f"(drill spec: 2-3 slides per 4 bars), got {slides_per_4bars}"
        )
    kicks = sorted(float(t) for t in kick_times)
    if not kicks:
        return [], []
    beat_s = 60.0 / bpm
    block_s = 16.0 * beat_s  # 4 written bars

    # Choose slide-target kicks per 4-bar block: the kicks nearest to evenly
    # spaced fractions of the block — deterministic, spread across the block.
    fracs = {2: (0.375, 0.875), 3: (0.25, 0.625, 0.875)}[slides_per_4bars]
    candidate_targets = sorted({
        min(members, key=lambda i: (abs(kicks[i] - want), i))
        for blk in sorted({int(t / block_s) for t in kicks})
        for members in [[i for i, t in enumerate(kicks) if int(t / block_s) == blk]]
        for want in [blk * block_s + f * block_s for f in fracs]
    })

    # Slide approach: raise the pitch of the note PRECEDING each target kick
    # by an alternating m3/P4, so the target (root) onset slides down in.
    # `used` guards collisions: a raised approach note or a landing target
    # may not serve as another target's approach (that would corrupt the
    # interval that actually lands on the kick).
    raised: Dict[int, int] = {}
    slides: List[dict] = []
    used: set = set()
    n_slides = 0
    for idx in candidate_targets:
        prev = idx - 1
        if idx == 0 or prev in used or idx in used:
            continue
        interval = int(slide_intervals[n_slides % len(slide_intervals)])
        raised[prev] = interval
        used.add(prev)
        used.add(idx)
        slides.append({
            "time_s": round(kicks[idx], 4),
            "interval_st": interval,
            "block": int(kicks[idx] / block_s),
        })
        n_slides += 1

    notes: List[Note808] = []
    for i, t in enumerate(kicks):
        nxt = kicks[i + 1] if i + 1 < len(kicks) else (total_s or t + 4 * beat_s)
        dur = max(0.05, nxt - t + 0.02)  # small legato overlap
        note = root_note + raised.get(i, 0)
        notes.append(Note808(start_s=t, duration_s=dur, note=float(note), velocity=0.9))
    slides.sort(key=lambda s: s["time_s"])
    return notes, slides
