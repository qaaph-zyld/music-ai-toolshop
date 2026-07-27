"""Music theory engine and high-level musical generators.

Provides one-call generators for drum patterns, chord progressions, basslines,
melodies, and arpeggios.  Uses the piano_roll and channels wrapper modules
to write notes to the DAW via the TCP bridge.

Music theory core:
    - NOTE_NAMES: chromatic scale names
    - NOTE_TO_MIDI: note name → MIDI number
    - SCALE_INTERVALS: interval patterns for common scales
    - CHORD_SHAPES: interval patterns for common chords
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from .client import DAWClient
from . import piano_roll as pr
from . import channels as ch


# ---------------------------------------------------------------------------
# Music theory constants
# ---------------------------------------------------------------------------

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SCALE_INTERVALS: Dict[str, List[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}

CHORD_SHAPES: Dict[str, List[int]] = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "7": [0, 4, 7, 10],
    "m7": [0, 3, 7, 10],
    "maj7": [0, 4, 7, 11],
    "dim7": [0, 3, 6, 9],
    "m7b5": [0, 3, 6, 10],
}

# Common chord progressions (scale-degree based, 0-indexed)
PROGRESSIONS: Dict[str, List[List[int]]] = {
    # Minor key progressions (drill/trap)
    "i-VI-III-VII": [0, 5, 2, 6],
    "i-VII-VI-V": [0, 6, 5, 4],
    "i-iv-VI-V": [0, 3, 5, 4],
    "i-VI-iv-V": [0, 5, 3, 4],
    # Major key progressions (pop)
    "vi-IV-I-V": [5, 3, 0, 4],
    "I-V-vi-IV": [0, 4, 5, 3],
    "I-IV-V-I": [0, 3, 4, 0],
    "ii-V-I": [1, 4, 0],
}


# ---------------------------------------------------------------------------
# Music theory functions
# ---------------------------------------------------------------------------

def key_to_root(key: str) -> int:
    """Convert a key name like ``"Gm"`` or ``"C"`` to the root MIDI note (octave 4).

    ``"Gm"`` → G4 = 67, ``"C"`` → C4 = 60, ``"Bb"`` → Bb4 = 70.
    """
    key = key.strip()
    # Parse note name + optional "m" for minor
    note_part = key
    if key.endswith("m") and len(key) > 1:
        note_part = key[:-1]

    return pr.note_name_to_midi(note_part + "4")


def scale_notes(key: str, scale: str = "minor", octave: int = 4) -> List[int]:
    """Return MIDI notes for a scale starting at the given key.

    Args:
        key: Root note name, e.g. ``"G"`` or ``"Gm"``.
        scale: Scale name from :data:`SCALE_INTERVALS`.
        octave: Starting octave (default 4).
    """
    if scale not in SCALE_INTERVALS:
        raise ValueError(f"Unknown scale: {scale!r}. Available: {list(SCALE_INTERVALS.keys())}")

    root = key_to_root(key)
    return [root + interval for interval in SCALE_INTERVALS[scale]]


def chord_notes(
    key: str, scale_degree: int, scale: str = "minor", chord_type: str = "", octave: int = 4
) -> List[int]:
    """Return MIDI notes for a chord at a scale degree.

    Auto-detects chord quality from scale if ``chord_type`` is empty.

    Args:
        key: Root note name.
        scale_degree: 0-indexed scale degree (0=I, 1=ii, 2=iii, ...).
        scale: Scale name.
        chord_type: Override chord type (e.g. ``"min"``, ``"maj"``). Auto-detected if empty.
        octave: Starting octave.
    """
    notes = scale_notes(key, scale, octave)
    root = notes[scale_degree % len(notes)]

    if not chord_type:
        # Auto-detect from scale: use stacked thirds (scale degrees +2 and +4)
        intervals = SCALE_INTERVALS[scale]
        root_pc = intervals[scale_degree % 7]
        third_pc = intervals[(scale_degree + 2) % 7]
        fifth_pc = intervals[(scale_degree + 4) % 7]
        third_interval = (third_pc - root_pc) % 12
        fifth_interval = (fifth_pc - root_pc) % 12
        if third_interval == 3:
            chord_type = "min"
        elif third_interval == 4:
            chord_type = "maj"
        else:
            chord_type = "dim"
        # Override for diminished fifth
        if fifth_interval == 6 and chord_type == "dim":
            chord_type = "dim"

    shape = CHORD_SHAPES.get(chord_type, CHORD_SHAPES["min"])
    return [root + interval for interval in shape]


def parse_progression(progression: str) -> List[int]:
    """Parse a progression string into scale-degree indices.

    Supports roman numeral notation: ``"i-VI-III-VII"`` → ``[0, 5, 2, 6]``.
    Also supports direct lookup from :data:`PROGRESSIONS`.
    """
    if progression in PROGRESSIONS:
        return PROGRESSIONS[progression]

    # Parse roman numerals
    roman_map = {
        "i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6,
        "I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6,
    }
    parts = progression.split("-")
    degrees = []
    for p in parts:
        p = p.strip()
        if p in roman_map:
            degrees.append(roman_map[p])
        else:
            raise ValueError(f"Unknown progression part: {p!r}")
    return degrees


# ---------------------------------------------------------------------------
# Drum pattern presets
# ---------------------------------------------------------------------------

# 16-step patterns. Each list has 16 booleans (True = hit).
DRUM_PRESETS: Dict[str, Dict[str, List[bool]]] = {
    "drill": {
        "kick":  [True, False, False, False, False, False, False, True,
                  False, False, False, False, False, False, False, False],
        "snare": [False, False, False, False, True, False, False, False,
                  False, False, False, False, True, False, False, False],
        "hat":   [True, False, True, False, True, False, True, False,
                  True, False, True, False, True, False, True, False],
    },
    "trap": {
        "kick":  [True, False, False, False, False, True, False, False,
                  False, False, True, False, False, False, False, False],
        "snare": [False, False, False, False, True, False, False, False,
                  False, False, False, False, True, False, False, False],
        "hat":   [True, True, True, True, True, True, True, True,
                  True, True, True, True, True, True, True, True],
    },
    "pop": {
        "kick":  [True, False, False, False, True, False, False, False,
                  True, False, False, False, True, False, False, False],
        "snare": [False, False, False, False, True, False, False, False,
                  False, False, False, False, True, False, False, False],
        "hat":   [False, False, True, False, False, False, True, False,
                  False, False, True, False, False, False, True, False],
    },
    "boom_bap": {
        "kick":  [True, False, False, False, False, False, True, False,
                  False, False, True, False, False, False, False, False],
        "snare": [False, False, False, False, True, False, False, False,
                  False, False, False, False, True, False, False, False],
        "hat":   [True, False, True, False, True, False, True, False,
                  True, False, True, False, True, False, True, False],
    },
}


def get_drum_preset(genre: str) -> Dict[str, List[bool]]:
    """Get the 16-step drum pattern for a genre.

    Returns dict with ``"kick"``, ``"snare"``, ``"hat"`` keys.
    """
    genre = genre.lower().replace("-", "_").replace(" ", "_")
    if genre not in DRUM_PRESETS:
        raise ValueError(
            f"Unknown genre: {genre!r}. Available: {list(DRUM_PRESETS.keys())}"
        )
    return DRUM_PRESETS[genre]


# ---------------------------------------------------------------------------
# Generators — write to DAW
# ---------------------------------------------------------------------------

def gen_drum_pattern(
    client: DAWClient,
    genre: str = "drill",
    bars: int = 4,
    channel_kick: int = 0,
    channel_snare: int = 1,
    channel_hat: int = 2,
) -> Dict[str, Any]:
    """Generate a drum pattern in the step sequencer.

    Args:
        genre: ``"drill"``, ``"trap"``, ``"pop"``, or ``"boom_bap"``.
        bars: Number of bars (each bar = 16 steps).
        channel_kick: Channel index for kick.
        channel_snare: Channel index for snare.
        channel_hat: Channel index for hi-hat.
    """
    preset = get_drum_preset(genre)
    steps_per_bar = 16

    kick_steps = preset["kick"] * bars
    snare_steps = preset["snare"] * bars
    hat_steps = preset["hat"] * bars

    # Write to step sequencer
    ch.set_step_pattern(client, channel_kick, kick_steps)
    ch.set_step_pattern(client, channel_snare, snare_steps)
    ch.set_step_pattern(client, channel_hat, hat_steps)

    return {
        "genre": genre,
        "bars": bars,
        "total_steps": bars * steps_per_bar,
        "channels": {"kick": channel_kick, "snare": channel_snare, "hat": channel_hat},
    }


def gen_chord_progression(
    client: DAWClient,
    pattern: int,
    key: str = "Gm",
    scale: str = "minor",
    progression: str = "i-VI-III-VII",
    bars: int = 8,
    chord_length: int = 16,
) -> Dict[str, Any]:
    """Generate a chord progression in the piano roll.

    Args:
        pattern: Pattern index to write to.
        key: Root key (e.g. ``"Gm"``, ``"C"``).
        scale: Scale name (``"minor"``, ``"major"``, etc.).
        progression: Progression string (e.g. ``"i-VI-III-VII"``).
        bars: Total number of bars.
        chord_length: Length of each chord in steps.
    """
    degrees = parse_progression(progression)
    steps_per_bar = 16
    total_steps = bars * steps_per_bar
    chords_per_progression = len(degrees)
    chord_spacing = total_steps // (chords_per_progression * (bars // chords_per_progression if bars >= chords_per_progression else 1))

    all_notes: List[Dict[str, Any]] = []
    pos = 0
    while pos < total_steps:
        for degree in degrees:
            if pos >= total_steps:
                break
            notes = chord_notes(key, degree, scale)
            for n in notes:
                all_notes.append({
                    "note": n,
                    "position": pos,
                    "length": chord_length,
                    "velocity": 80,
                })
            pos += chord_length

    pr.add_notes(client, pattern, all_notes)

    return {
        "key": key,
        "scale": scale,
        "progression": progression,
        "bars": bars,
        "chords_written": len(all_notes) // 3,  # approximate (triads)
        "notes_written": len(all_notes),
    }


def gen_bassline(
    client: DAWClient,
    pattern: int,
    key: str = "Gm",
    scale: str = "minor",
    bars: int = 8,
    style: str = "root",
    note_length: int = 8,
) -> Dict[str, Any]:
    """Generate a bassline in the piano roll.

    Args:
        pattern: Pattern index to write to.
        key: Root key.
        scale: Scale name.
        bars: Total bars.
        style: ``"root"`` (root notes), ``"octaves"`` (root + octave), ``"walking"`` (scale walk).
        note_length: Length of each note in steps.
    """
    root = key_to_root(key)
    bass_root = root - 12  # One octave below
    scale_n = scale_notes(key, scale, 3)  # Octave 3 for bass
    steps_per_bar = 16
    total_steps = bars * steps_per_bar

    all_notes: List[Dict[str, Any]] = []
    pos = 0

    if style == "root":
        while pos < total_steps:
            all_notes.append({
                "note": bass_root, "position": pos,
                "length": note_length, "velocity": 100,
            })
            pos += note_length

    elif style == "octaves":
        while pos < total_steps:
            all_notes.append({
                "note": bass_root, "position": pos,
                "length": note_length, "velocity": 100,
            })
            all_notes.append({
                "note": bass_root + 12, "position": pos + note_length // 2,
                "length": note_length // 2, "velocity": 90,
            })
            pos += note_length

    elif style == "walking":
        degree = 0
        while pos < total_steps:
            note = scale_n[degree % len(scale_n)]
            all_notes.append({
                "note": note, "position": pos,
                "length": note_length, "velocity": 95,
            })
            degree += 1
            pos += note_length

    else:
        raise ValueError(f"Unknown bass style: {style!r}. Use 'root', 'octaves', or 'walking'.")

    pr.add_notes(client, pattern, all_notes)

    return {
        "key": key, "scale": scale, "style": style,
        "bars": bars, "notes_written": len(all_notes),
    }


def gen_melody(
    client: DAWClient,
    pattern: int,
    key: str = "Gm",
    scale: str = "minor",
    bars: int = 4,
    density: float = 0.5,
    seed: int = 42,
) -> Dict[str, Any]:
    """Generate a melodic line using scale degrees.

    Args:
        pattern: Pattern index.
        key: Root key.
        scale: Scale name.
        bars: Total bars.
        density: Note density 0.0-1.0 (higher = more notes).
        seed: Random seed for reproducibility.
    """
    rng = random.Random(seed)
    scale_n = scale_notes(key, scale, 5)  # Octave 5 for melody
    steps_per_bar = 16
    total_steps = bars * steps_per_bar

    all_notes: List[Dict[str, Any]] = []
    pos = 0
    step_size = 4  # 16th notes

    while pos < total_steps:
        if rng.random() < density:
            degree = rng.randint(0, len(scale_n) - 1)
            note = scale_n[degree]
            length = step_size * rng.choice([1, 1, 1, 2, 2, 4])
            velocity = rng.randint(70, 110)
            all_notes.append({
                "note": note, "position": pos,
                "length": min(length, total_steps - pos),
                "velocity": velocity,
            })
        pos += step_size

    pr.add_notes(client, pattern, all_notes)

    return {
        "key": key, "scale": scale, "bars": bars,
        "density": density, "seed": seed,
        "notes_written": len(all_notes),
    }


def gen_arpeggio(
    client: DAWClient,
    pattern: int,
    chords: str = "Gm,Bb,Dm",
    pattern_type: str = "up",
    bars: int = 4,
    note_length: int = 2,
    octave: int = 4,
) -> Dict[str, Any]:
    """Generate an arpeggio pattern from a chord list.

    Args:
        pattern: Pattern index.
        chords: Comma-separated chord root names (e.g. ``"Gm,Bb,Dm"``).
        pattern_type: ``"up"``, ``"down"``, ``"updown"``, ``"random"``.
        bars: Total bars.
        note_length: Length of each arpeggio note in steps.
        octave: Starting octave.
    """
    rng = random.Random(42)
    chord_roots = [c.strip() for c in chords.split(",")]
    steps_per_bar = 16
    total_steps = bars * steps_per_bar

    # Build note lists for each chord (triad)
    # Strip trailing "m" from chord root names (e.g. "Gm" → "G")
    chord_note_lists: List[List[int]] = []
    for cr in chord_roots:
        note_name = cr[:-1] if cr.endswith("m") and len(cr) > 1 else cr
        root = pr.note_name_to_midi(note_name + str(octave))
        chord_note_lists.append([root, root + 7, root + 12])  # root-fifth-octave

    all_notes: List[Dict[str, Any]] = []
    pos = 0
    chord_idx = 0
    note_idx = 0
    direction = 1  # 1=up, -1=down

    while pos < total_steps:
        current_chord = chord_note_lists[chord_idx % len(chord_note_lists)]
        num_notes = len(current_chord)

        if pattern_type == "up":
            note = current_chord[note_idx % num_notes]
        elif pattern_type == "down":
            note = current_chord[(num_notes - 1 - (note_idx % num_notes))]
        elif pattern_type == "updown":
            note = current_chord[note_idx % num_notes]
        elif pattern_type == "random":
            note = rng.choice(current_chord)
        else:
            raise ValueError(f"Unknown arpeggio pattern: {pattern_type!r}")

        all_notes.append({
            "note": note, "position": pos,
            "length": note_length, "velocity": 90,
        })

        pos += note_length
        note_idx += 1

        # Advance chord every bar
        if pos % steps_per_bar == 0:
            chord_idx += 1
            note_idx = 0

    pr.add_notes(client, pattern, all_notes)

    return {
        "chords": chords, "pattern_type": pattern_type,
        "bars": bars, "notes_written": len(all_notes),
    }
