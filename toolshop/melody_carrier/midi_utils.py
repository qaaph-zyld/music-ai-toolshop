"""MIDI utility functions for the melody carrier generator.

Provides helpers to create, populate, merge, save, and render MIDI files,
plus audio normalization for Suno upload compliance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pretty_midi
from scipy.io import wavfile


def create_midi(bpm: float, key: str, mode: str) -> pretty_midi.PrettyMIDI:
    """Create a PrettyMIDI object with correct tempo and time signature.

    Args:
        bpm: Tempo in beats per minute.
        key: Root note name (e.g., "C", "C#", "D", ... "B").
        mode: "major" or "minor".

    Returns:
        pretty_midi.PrettyMIDI with tempo set to bpm (not default 120).
    """
    midi = pretty_midi.PrettyMIDI(
        initial_tempo=bpm,
        resolution=480,
    )
    # Set time signature to 4/4
    midi.time_signature_changes.append(
        pretty_midi.TimeSignature(numerator=4, denominator=4, time=0)
    )
    # Set key signature
    key_map_major = {
        "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
        "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11,
    }
    key_map_minor = {
        "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
        "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11,
    }
    key_num = (key_map_major if mode == "major" else key_map_minor).get(key, 0)
    if mode == "minor":
        key_num += 12
    midi.key_signature_changes.append(
        pretty_midi.KeySignature(key_number=key_num, time=0)
    )
    return midi


def f0_to_notes(
    f0: np.ndarray,
    times: np.ndarray,
    sr: int,
    min_duration_ms: int = 50,
    max_gap_ms: int = 100,
) -> List[pretty_midi.Note]:
    """Quantize an F0 contour to MIDI notes.

    Used for bass extraction (monophonic). Melody uses Basic Pitch (polyphonic).

    Args:
        f0: Array of fundamental frequencies (Hz). NaN = unvoiced.
        times: Array of time stamps (seconds) matching f0 length.
        sr: Sample rate of the analysis (for frame duration calculation).
        min_duration_ms: Minimum note duration in milliseconds. Shorter notes discarded.
        max_gap_ms: Maximum gap between voiced frames to merge into one note.

    Returns:
        List of pretty_midi.Note objects with pitch, start, end set.
    """
    if len(f0) == 0:
        return []

    min_duration_s = min_duration_ms / 1000.0
    max_gap_s = max_gap_ms / 1000.0

    # Identify voiced frames (non-NaN, positive frequency)
    voiced = ~np.isnan(f0) & (f0 > 0)

    # Find contiguous voiced segments
    notes: List[pretty_midi.Note] = []
    in_segment = False
    seg_start_idx = 0

    for i in range(len(f0)):
        if voiced[i] and not in_segment:
            # Start of a new voiced segment
            in_segment = True
            seg_start_idx = i
        elif not voiced[i] and in_segment:
            # End of voiced segment — check if gap is small enough to continue
            # Look ahead to see if voicing resumes within max_gap_s
            gap_end = i
            resume_idx = None
            for j in range(i, len(f0)):
                if voiced[j]:
                    # Check if the gap is within max_gap_s
                    gap_duration = times[j] - times[gap_end - 1]
                    if gap_duration <= max_gap_s:
                        resume_idx = j
                    break
            if resume_idx is not None:
                # Gap is small — keep the segment going, skip to resume point
                continue
            else:
                # Gap too large or end of array — finalize segment
                in_segment = False
                _finalize_segment(
                    f0, times, seg_start_idx, i - 1, min_duration_s, notes
                )

    # Finalize last segment if still in one
    if in_segment:
        _finalize_segment(
            f0, times, seg_start_idx, len(f0) - 1, min_duration_s, notes
        )

    return notes


def _finalize_segment(
    f0: np.ndarray,
    times: np.ndarray,
    start_idx: int,
    end_idx: int,
    min_duration_s: float,
    notes: List[pretty_midi.Note],
) -> None:
    """Convert a voiced segment to a Note if it meets minimum duration."""
    duration = times[end_idx] - times[start_idx]
    if duration < min_duration_s:
        return
    # Use median frequency to determine pitch
    voiced_freqs = f0[start_idx:end_idx + 1]
    voiced_freqs = voiced_freqs[~np.isnan(voiced_freqs) & (voiced_freqs > 0)]
    if len(voiced_freqs) == 0:
        return
    median_freq = float(np.median(voiced_freqs))
    pitch = int(round(69 + 12 * np.log2(median_freq / 440.0)))
    note = pretty_midi.Note(
        velocity=100,
        pitch=pitch,
        start=float(times[start_idx]),
        end=float(times[end_idx]),
    )
    notes.append(note)


def chords_to_midi(
    chord_prog: List[Dict],
    midi: pretty_midi.PrettyMIDI,
) -> pretty_midi.Instrument:
    """Convert a chord progression to block chords on a pad instrument.

    Args:
        chord_prog: List of dicts, each with keys "chord" (str, e.g., "C:maj"),
                    "start" (float, seconds), "end" (float, seconds).
        midi: PrettyMIDI object to add the instrument track to.

    Returns:
        pretty_midi.Instrument with block chord notes (program 0, piano/pad).
    """
    instrument = pretty_midi.Instrument(program=0, name="chords")

    for chord_entry in chord_prog:
        chord_name = chord_entry["chord"]
        start = float(chord_entry["start"])
        end = float(chord_entry["end"])

        pitches = _chord_name_to_pitches(chord_name)
        for pitch in pitches:
            note = pretty_midi.Note(
                velocity=80,
                pitch=pitch,
                start=start,
                end=end,
            )
            instrument.notes.append(note)

    midi.instruments.append(instrument)
    return instrument


def _chord_name_to_pitches(chord_name: str) -> List[int]:
    """Parse a chord name like 'C:maj' or 'Am' to MIDI pitch numbers."""
    # Root note mapping
    note_to_semitone = {
        "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
        "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
    }

    # Parse root note
    root_str = chord_name[0]
    idx = 1
    if idx < len(chord_name) and chord_name[idx] in ("#", "b"):
        root_str += chord_name[idx]
        idx += 1

    root_pc = note_to_semitone.get(root_str, 0)

    # Parse chord quality
    rest = chord_name[idx:]
    # Remove ":maj" or ":min" style qualifiers
    if ":" in rest:
        rest = rest.split(":", 1)[1]

    # Determine intervals based on chord quality
    if rest in ("", "maj", "major", "M"):
        intervals = [0, 4, 7]
    elif rest in ("m", "min", "minor"):
        intervals = [0, 3, 7]
    elif rest in ("7", "dom7", "dominant7"):
        intervals = [0, 4, 7, 10]
    elif rest in ("maj7", "M7", "major7"):
        intervals = [0, 4, 7, 11]
    elif rest in ("m7", "min7", "minor7"):
        intervals = [0, 3, 7, 10]
    elif rest in ("dim", "diminished"):
        intervals = [0, 3, 6]
    elif rest in ("aug", "augmented"):
        intervals = [0, 4, 8]
    elif rest in ("sus2",):
        intervals = [0, 2, 7]
    elif rest in ("sus4", "sus"):
        intervals = [0, 5, 7]
    else:
        intervals = [0, 4, 7]  # default to major triad

    # Place around octave 4 (MIDI 60 = C4)
    base = 60 + root_pc
    return [base + iv for iv in intervals]


def merge_instruments(
    instruments: List[pretty_midi.Instrument],
    bpm: float,
) -> pretty_midi.PrettyMIDI:
    """Create a multi-track MIDI from multiple instruments.

    Args:
        instruments: List of pretty_midi.Instrument objects (melody, chords, bass, drums).
        bpm: Tempo for the output MIDI.

    Returns:
        pretty_midi.PrettyMIDI with each instrument on a separate track.
    """
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm, resolution=480)
    midi.time_signature_changes.append(
        pretty_midi.TimeSignature(numerator=4, denominator=4, time=0)
    )
    for instr in instruments:
        midi.instruments.append(instr)
    return midi


def save_midi(midi: pretty_midi.PrettyMIDI, path: Path) -> None:
    """Write a PrettyMIDI object to a .mid file with tempo metadata.

    Args:
        midi: PrettyMIDI object to write.
        path: Output file path. Parent directory created if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(path))


def normalize_audio(
    audio: np.ndarray,
    target_peak_db: float = -1.0,
) -> np.ndarray:
    """Normalize audio to a target peak level in dB.

    Suno upload requirement: peak normalized to -1 dB, no clipping.

    Args:
        audio: 1D or 2D numpy array of audio samples.
        target_peak_db: Target peak level in dB (default: -1.0).

    Returns:
        Normalized audio array with peak at target_peak_db.
    """
    current_peak = np.max(np.abs(audio))
    if current_peak == 0:
        return np.zeros_like(audio)

    target_peak = 10 ** (target_peak_db / 20.0)
    gain = target_peak / current_peak
    return (audio * gain).astype(audio.dtype)


def render_sine(
    midi_path: Path,
    output_wav: Path,
    sr: int = 44100,
) -> None:
    """Render a MIDI file to a sine-wave WAV using pretty_midi.synthesize().

    Uses pretty_midi.PrettyMIDI.synthesize(wave=np.sin) for exact pitch/timing.
    Normalizes output to -1 dB peak. Writes 16-bit WAV at sr Hz.

    Note: pretty_midi .synthesize() ignores drum tracks (is_drum=True instruments).
    This is expected behavior — drum tracks produce no audio in sine rendering.

    Args:
        midi_path: Path to input .mid file.
        output_wav: Path to output .wav file. Parent directory created if needed.
        sr: Sample rate for output WAV (default: 44100, Suno requirement).
    """
    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    midi = pretty_midi.PrettyMIDI(str(midi_path))
    audio = midi.synthesize(fs=sr, wave=np.sin)

    # Normalize to -1 dB peak
    audio = normalize_audio(audio.astype(np.float64), target_peak_db=-1.0)

    # Convert to 16-bit
    audio_int16 = (audio * 32767).astype(np.int16)
    wavfile.write(str(output_wav), sr, audio_int16)
