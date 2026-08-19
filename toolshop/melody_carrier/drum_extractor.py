"""Drum transcription module for the melody carrier generator.

Transcribes isolated drum stems to MIDI using ADTOF-pytorch (primary)
or librosa onset detection + spectral classification (fallback).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pretty_midi


# MIDI pitch mapping for drum classes (ADTOF 5-class output)
_DRUM_PITCH = {
    "kick": 36,
    "snare": 38,
    "hat": 42,
    "tom": 50,
    "cymbal": 49,
}


def extract_drums(
    drums_wav: Path,
    bpm: float,
) -> pretty_midi.Instrument:
    """Transcribe isolated drum stem to MIDI using ADTOF-pytorch, fallback librosa.

    Primary path (ADTOF-pytorch):
        - from adtof_pytorch import transcribe_to_midi
        - 5-class output: kick (36), snare (38), hat (42), tom (50), cymbal (49)
        - F=0.92 on isolated stems per research

    Fallback path (librosa spectral heuristic, if ADTOF-pytorch not installed):
        - librosa.onset.onset_detect() -> onset times
        - Classify by spectral centroid: <200Hz=kick(36), 200-2000Hz=snare(38), >2000Hz=hat(42)
        - Quantize to BPM grid

    Args:
        drums_wav: Path to isolated drum stem WAV.
        bpm: Detected BPM for quantization grid.

    Returns:
        pretty_midi.Instrument with drum notes (is_drum=True, program 0).
    """
    try:
        from adtof_pytorch import transcribe_to_midi

        instrument = _extract_drums_adtof(drums_wav, bpm, transcribe_to_midi)
    except ImportError:
        instrument = _extract_drums_librosa(drums_wav, bpm)

    return instrument


def _extract_drums_adtof(
    drums_wav: Path,
    bpm: float,
    transcribe_fn,
) -> pretty_midi.Instrument:
    """Extract drums using ADTOF-pytorch."""
    result = transcribe_fn(str(drums_wav))

    instrument = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

    # ADTOF-pytorch returns a list of (time, drum_class) tuples or a pretty_midi object
    if isinstance(result, pretty_midi.Instrument):
        for note in result.notes:
            instrument.notes.append(note)
    elif isinstance(result, list):
        for entry in result:
            if isinstance(entry, dict):
                time = entry.get("time", 0.0)
                drum_class = entry.get("class", "kick")
                pitch = _DRUM_PITCH.get(drum_class, 36)
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                time, drum_class = entry[0], entry[1]
                pitch = _DRUM_PITCH.get(drum_class, 36) if isinstance(drum_class, str) else drum_class
            else:
                continue
            note = pretty_midi.Note(
                velocity=100,
                pitch=pitch,
                start=float(time),
                end=float(time) + 0.1,
            )
            instrument.notes.append(note)
    elif hasattr(result, "notes"):
        for note in result.notes:
            instrument.notes.append(note)

    return instrument


def _extract_drums_librosa(
    drums_wav: Path,
    bpm: float,
) -> pretty_midi.Instrument:
    """Extract drums using librosa onset detection + spectral classification."""
    import librosa

    y, sr = librosa.load(str(drums_wav), sr=22050, mono=True)

    onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    instrument = pretty_midi.Instrument(program=0, is_drum=True, name="drums")

    # Classify each onset by spectral centroid
    for onset_time in onset_times:
        # Get a short window around the onset
        frame_start = int(onset_time * sr)
        frame_length = int(0.05 * sr)  # 50ms window
        frame_end = min(frame_start + frame_length, len(y))

        if frame_end <= frame_start:
            continue

        frame = y[frame_start:frame_end]

        if len(frame) == 0 or np.max(np.abs(frame)) < 1e-6:
            continue

        # Compute spectral centroid
        spectrum = np.abs(np.fft.rfft(frame))
        freqs = np.fft.rfftfreq(len(frame), 1.0 / sr)
        if np.sum(spectrum) == 0:
            centroid = 0.0
        else:
            centroid = float(np.sum(freqs * spectrum) / np.sum(spectrum))

        # Classify by spectral centroid
        if centroid < 200:
            pitch = _DRUM_PITCH["kick"]
        elif centroid < 2000:
            pitch = _DRUM_PITCH["snare"]
        else:
            pitch = _DRUM_PITCH["hat"]

        # Quantize to BPM grid
        beat_duration = 60.0 / bpm if bpm > 0 else 0.5
        quantized_time = round(float(onset_time) / (beat_duration / 4)) * (beat_duration / 4)

        note = pretty_midi.Note(
            velocity=100,
            pitch=pitch,
            start=quantized_time,
            end=quantized_time + 0.1,
        )
        instrument.notes.append(note)

    return instrument
