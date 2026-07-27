"""Piano roll note operations — add, clear, get, quantize, transpose, humanize.

Note format: list of dicts with keys:
    - note: int (MIDI note number, 0-127)
    - position: int (step position in pattern, 0-based)
    - length: int (duration in steps)
    - velocity: int (0-127, default 100)

Note names (e.g. "C4", "G#3") are converted to MIDI numbers via :func:`note_name_to_midi`.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Union

from .client import DAWClient

# Note name → semitone offset from C
_NOTE_SEMITONES = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


def note_name_to_midi(name: str) -> int:
    """Convert a note name like ``"C4"`` or ``"G#3"`` to a MIDI note number.

    MIDI note 60 = C4 (middle C in FL Studio convention).
    """
    name = name.strip()
    # Parse note letter + optional accidental + octave
    if len(name) < 2:
        raise ValueError(f"Invalid note name: {name!r}")

    # Find where the octave number starts
    octave_start = 1
    if name[1] in "#b":
        octave_start = 2

    note_part = name[:octave_start]
    octave_str = name[octave_start:]

    if note_part not in _NOTE_SEMITONES:
        raise ValueError(f"Invalid note name: {name!r}")

    try:
        octave = int(octave_str)
    except ValueError:
        raise ValueError(f"Invalid octave in note name: {name!r}")

    return (octave + 1) * 12 + _NOTE_SEMITONES[note_part]


def midi_to_note_name(midi: int) -> str:
    """Convert a MIDI note number to a note name like ``"C4"``."""
    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI note out of range: {midi}")
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi // 12) - 1
    note = note_names[midi % 12]
    return f"{note}{octave}"


def parse_notes(notes_str: str) -> List[int]:
    """Parse a comma-separated list of note names into MIDI numbers.

    Example: ``"C4,E4,G4"`` → ``[60, 64, 67]``
    """
    return [note_name_to_midi(n.strip()) for n in notes_str.split(",") if n.strip()]


def add_notes(
    client: DAWClient,
    pattern: int,
    notes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Add notes to a pattern's piano roll.

    Args:
        pattern: Pattern index.
        notes: List of note dicts with keys ``note``, ``position``, ``length``, ``velocity``.
    """
    return client.call(  # type: ignore[return-value]
        "pianoroll.add_notes", pattern=pattern, notes=notes
    )


def add_notes_simple(
    client: DAWClient,
    pattern: int,
    note_names: Union[str, List[str]],
    position: int = 0,
    length: int = 16,
    velocity: int = 100,
) -> Dict[str, Any]:
    """Add notes from note names to a pattern's piano roll.

    Args:
        pattern: Pattern index.
        note_names: Comma-separated string ``"C4,E4,G4"`` or list of note names.
        position: Step position for all notes (default 0).
        length: Duration in steps (default 16).
        velocity: MIDI velocity 0-127 (default 100).
    """
    if isinstance(note_names, str):
        midi_notes = parse_notes(note_names)
    else:
        midi_notes = [note_name_to_midi(n) for n in note_names]

    notes = [
        {"note": n, "position": position, "length": length, "velocity": velocity}
        for n in midi_notes
    ]
    return add_notes(client, pattern, notes)


def clear_notes(client: DAWClient, pattern: int) -> Dict[str, Any]:
    """Clear all notes from a pattern's piano roll."""
    return client.call("pianoroll.clear_notes", pattern=pattern)  # type: ignore[return-value]


def get_notes(client: DAWClient, pattern: int) -> Dict[str, Any]:
    """Get all notes from a pattern's piano roll."""
    return client.call("pianoroll.get_notes", pattern=pattern)  # type: ignore[return-value]


def quantize(client: DAWClient, pattern: int, grid: int = 16) -> Dict[str, Any]:
    """Quantize all notes in a pattern to the given grid.

    Args:
        pattern: Pattern index.
        grid: Grid resolution (4=quarter, 8=eighth, 16=sixteenth, 32=thirty-second).
    """
    return client.call(  # type: ignore[return-value]
        "pianoroll.quantize", pattern=pattern, grid=grid
    )


def transpose(client: DAWClient, pattern: int, semitones: int) -> Dict[str, Any]:
    """Transpose all notes in a pattern by a number of semitones."""
    return client.call(  # type: ignore[return-value]
        "pianoroll.transpose", pattern=pattern, semitones=semitones
    )


def humanize(
    client: DAWClient, pattern: int, amount: float = 0.3, seed: int = 42
) -> Dict[str, Any]:
    """Humanize note timing and velocity in a pattern.

    Args:
        pattern: Pattern index.
        amount: Humanization amount (0.0-1.0, higher = more variation).
        seed: Random seed for reproducibility.
    """
    return client.call(  # type: ignore[return-value]
        "pianoroll.humanize", pattern=pattern, amount=amount, seed=seed
    )
