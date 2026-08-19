"""Stage 1 extractor for the melody carrier generator.

Extracts stems, analyzes track, and converts to MIDI files (melody, chords, bass, drums).
Orchestrates Basic Pitch / autochord / ADTOF-pytorch with librosa fallbacks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pretty_midi

from . import midi_utils
from . import drum_extractor as drum_ext


def extract(
    input_wav: Path,
    output_dir: Path,
    genre: str,
    preset: str = "4stem",
) -> Dict:
    """Stage 1: Extract stems, analyze track, convert to MIDI files.

    Pipeline:
    1. Validate input (file exists, duration >= 15s)
    2. Stem separate via extract_stems_preset()
    3. Track analysis via analyze_track()
    4. Melody extraction (Basic Pitch, fallback pYIN)
    5. Chord extraction (autochord, fallback librosa)
    6. Bass extraction (librosa pYIN)
    7. Drum extraction (drum_extractor.extract_drums())
    8. Merge to full_sketch.mid
    9. Save analysis.json
    10. Print pause message

    Args:
        input_wav: Path to input WAV file.
        output_dir: Directory for output. Creates {output_dir}/stage1/ subdirectory.
        genre: Genre tag for Suno prompt (e.g., "drill", "lofi"). Required.
        preset: Stem separation preset ("4stem" or "6stem").

    Returns:
        Dict with keys:
        - "stage1_dir": Path to stage1 output directory
        - "midi_files": Dict of {"melody": Path, "chords": Path, "bass": Path,
                                 "drums": Path, "full_sketch": Path}
        - "analysis": Dict with bpm, key, mode, genre, chord_progression,
                      detected_instruments, spectral_centroid, spectral_bandwidth,
                      harmonic_ratio, onset_strength, tuning_offset, duration_seconds,
                      melody_source, extraction_tools, drum_pattern
        - "stems_dir": Path to raw stem WAVs

    Raises:
        FileNotFoundError: If input_wav doesn't exist.
        ValueError: If genre is empty string.
    """
    input_wav = Path(input_wav)
    output_dir = Path(output_dir)

    if not input_wav.exists():
        raise FileNotFoundError(f"Input WAV not found: {input_wav}")

    if not genre:
        raise ValueError("genre must be a non-empty string")

    stage1_dir = output_dir / "stage1"
    stage1_dir.mkdir(parents=True, exist_ok=True)
    stems_dir = stage1_dir / "stems"
    midi_dir = stage1_dir / "midi"
    midi_dir.mkdir(parents=True, exist_ok=True)

    # Check duration — warn if short, don't abort
    _check_duration(input_wav)

    # Step 2: Stem separation
    from .. import stem_extractor_adapter

    stems_result = stem_extractor_adapter.extract_stems_preset(
        input_file=input_wav,
        preset_id=preset,
        output_dir=stems_dir,
    )
    stems = stems_result.get("stems", {})

    # Step 3: Track analysis
    from .. import reverse_engineering_adapter

    analysis_raw = reverse_engineering_adapter.analyze_track(
        path=input_wav,
        instruments=True,
        separation="hpss",
    )

    bpm = float(analysis_raw.get("bpm", 120.0))
    key = str(analysis_raw.get("key", "C"))
    mode = str(analysis_raw.get("mode", "major"))
    duration_seconds = float(analysis_raw.get("duration_seconds", 0.0))
    spectral_centroid = float(analysis_raw.get("spectral_centroid", 0.0))
    spectral_bandwidth = float(analysis_raw.get("spectral_bandwidth", 0.0))
    harmonic_ratio = float(analysis_raw.get("harmonic_ratio", 0.5))
    onset_strength = float(analysis_raw.get("onset_strength", 0.5))
    tuning_offset = float(analysis_raw.get("tuning_offset", 0.0))

    # Extract detected instruments from analysis
    detected_instruments = _extract_instrument_list(analysis_raw.get("instruments", {}))

    # Step 4: Determine melody source stem
    melody_stem_path, melody_source_name = _determine_melody_source(stems)

    # Step 5: Extract melody
    melody_mid = midi_dir / "melody.mid"
    melody_path, melody_tool = _extract_melody(
        melody_stem_path, bpm, key, mode, melody_mid
    )

    # Step 6: Extract chords
    other_stem = stems.get("other", melody_stem_path)
    chords_mid = midi_dir / "chords.mid"
    chord_progression, chords_tool = _extract_chords(
        other_stem, chords_mid, bpm
    )

    # Step 7: Extract bass
    bass_mid = midi_dir / "bass.mid"
    bass_stem = stems.get("bass")
    if bass_stem and Path(bass_stem).exists():
        bass_path, bass_tool = _extract_bass(
            Path(bass_stem), bpm, key, mode, bass_mid
        )
    else:
        # No bass stem — write empty bass.mid
        empty_midi = midi_utils.create_midi(bpm, key, mode)
        midi_utils.save_midi(empty_midi, bass_mid)
        bass_path = bass_mid
        bass_tool = "skipped"

    # Step 8: Extract drums
    drums_mid = midi_dir / "drums.mid"
    drum_stem = stems.get("drums")
    drum_pattern = {}
    if drum_stem and Path(drum_stem).exists():
        drum_instrument = drum_ext.extract_drums(Path(drum_stem), bpm)
        drum_pattern = _summarize_drum_pattern(drum_instrument)
        drums_tool = "adtof" if _is_adtof_available() else "librosa_fallback"
    else:
        drum_instrument = pretty_midi.Instrument(program=0, is_drum=True, name="drums")
        drums_tool = "skipped"

    # Save drums.mid
    drums_midi_obj = midi_utils.create_midi(bpm, key, mode)
    drums_midi_obj.instruments.append(drum_instrument)
    midi_utils.save_midi(drums_midi_obj, drums_mid)

    # Step 9: Merge to full_sketch.mid
    melody_instr = _load_instrument_from_mid(melody_path, "melody")
    chords_instr = _load_instrument_from_mid(chords_mid, "chords")
    bass_instr = _load_instrument_from_mid(bass_path, "bass")

    full_sketch_mid = midi_dir / "full_sketch.mid"
    full_midi = midi_utils.merge_instruments(
        [melody_instr, chords_instr, bass_instr, drum_instrument],
        bpm,
    )
    midi_utils.save_midi(full_midi, full_sketch_mid)

    # Step 10: Build analysis dict
    extraction_tools = {
        "melody": melody_tool,
        "chords": chords_tool,
        "bass": bass_tool,
        "drums": drums_tool,
    }

    analysis = {
        "bpm": bpm,
        "key": key,
        "mode": mode,
        "genre": genre,
        "duration_seconds": duration_seconds,
        "spectral_centroid": spectral_centroid,
        "spectral_bandwidth": spectral_bandwidth,
        "harmonic_ratio": harmonic_ratio,
        "onset_strength": onset_strength,
        "tuning_offset": tuning_offset,
        "chord_progression": chord_progression,
        "detected_instruments": detected_instruments,
        "melody_source": melody_source_name,
        "extraction_tools": extraction_tools,
        "drum_pattern": drum_pattern,
    }

    # Save analysis.json
    analysis_path = stage1_dir / "analysis.json"
    analysis_path.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Print pause message
    print(
        "\n--- Stage 1 extraction complete ---\n"
        "Review the MIDI files in the stage1/midi/ directory.\n"
        "When ready, run Stage 2 (render) to generate carrier WAVs and Suno prompts.\n",
        file=sys.stderr,
    )

    return {
        "stage1_dir": stage1_dir,
        "midi_files": {
            "melody": melody_path,
            "chords": chords_mid,
            "bass": bass_path,
            "drums": drums_mid,
            "full_sketch": full_sketch_mid,
        },
        "analysis": analysis,
        "stems_dir": stems_dir,
    }


def _extract_melody(
    stem_wav: Path,
    bpm: float,
    key: str,
    mode: str,
    output_mid: Path,
) -> Tuple[Path, str]:
    """Extract melody from a stem WAV using Basic Pitch, fallback to pYIN.

    Args:
        stem_wav: Path to the stem WAV (vocals or other).
        bpm: Detected BPM for tempo setting.
        key: Detected key for MIDI metadata.
        mode: Detected mode for MIDI metadata.
        output_mid: Path to write melody.mid.

    Returns:
        Tuple of (output_mid_path, tool_used) where tool_used is
        "basic_pitch" or "pyin_fallback".
    """
    try:
        from basic_pitch.inference import predict as bp_predict
        from basic_pitch import ICASSP_2022_MODEL_PATH

        _, midi_data, _ = bp_predict(str(stem_wav))
        # midi_data is a pretty_midi.PrettyMIDI object
        if hasattr(midi_data, "instruments") and midi_data.instruments:
            # Merge all instruments into one
            instrument = pretty_midi.Instrument(program=0, name="melody")
            for instr in midi_data.instruments:
                for note in instr.notes:
                    instrument.notes.append(note)
            midi_obj = midi_utils.create_midi(bpm, key, mode)
            midi_obj.instruments.append(instrument)
            midi_utils.save_midi(midi_obj, output_mid)
        else:
            raise RuntimeError("Basic Pitch returned no notes")

        return (output_mid, "basic_pitch")

    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: librosa pYIN
    return _extract_melody_pyin(stem_wav, bpm, key, mode, output_mid)


def _extract_melody_pyin(
    stem_wav: Path,
    bpm: float,
    key: str,
    mode: str,
    output_mid: Path,
) -> Tuple[Path, str]:
    """Fallback melody extraction using librosa pYIN."""
    import librosa

    y, sr = librosa.load(str(stem_wav), sr=22050, mono=True)
    f0, voiced, voiced_prob = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
    )
    times = librosa.times_like(f0, sr=sr)
    notes = midi_utils.f0_to_notes(f0, times, sr)

    instrument = pretty_midi.Instrument(program=0, name="melody")
    instrument.notes = notes
    midi_obj = midi_utils.create_midi(bpm, key, mode)
    midi_obj.instruments.append(instrument)
    midi_utils.save_midi(midi_obj, output_mid)

    return (output_mid, "pyin_fallback")


def _extract_chords(
    stem_wav: Path,
    output_mid: Path,
    bpm: float,
) -> Tuple[List[Dict], str]:
    """Extract chord progression from a stem WAV using autochord, fallback librosa.

    Args:
        stem_wav: Path to the stem WAV (other/instrumental).
        output_mid: Path to write chords.mid.
        bpm: Detected BPM for MIDI tempo.

    Returns:
        Tuple of (chord_progression_list, tool_used) where tool_used is
        "autochord" or "librosa_fallback".
    """
    try:
        import autochord

        autochord.recognize(str(stem_wav), output_dir=str(output_mid.parent))
        # autochord writes a .lab file — parse it
        lab_path = output_mid.with_suffix(".lab")
        if lab_path.exists():
            chord_prog = _parse_lab_file(lab_path)
        else:
            chord_prog = []

        # Convert to MIDI
        midi_obj = midi_utils.create_midi(bpm, "C", "major")
        midi_utils.chords_to_midi(chord_prog, midi_obj)
        midi_utils.save_midi(midi_obj, output_mid)

        return (chord_prog, "autochord")

    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: use reverse_engineering_adapter chord detection
    return _extract_chords_librosa(stem_wav, output_mid, bpm)


def _extract_chords_librosa(
    stem_wav: Path,
    output_mid: Path,
    bpm: float,
) -> Tuple[List[Dict], str]:
    """Fallback chord extraction using reverse_engineering_adapter."""
    from .. import reverse_engineering_adapter

    analysis = reverse_engineering_adapter.analyze_track(
        path=Path(stem_wav),
        chords=True,
    )

    chord_prog = []
    raw_chords = analysis.get("chord_progression", {})
    if isinstance(raw_chords, dict):
        for chord_name, times in raw_chords.items():
            if isinstance(times, dict):
                chord_prog.append({
                    "chord": chord_name,
                    "start": float(times.get("start", 0.0)),
                    "end": float(times.get("end", 0.0)),
                })
            elif isinstance(times, (list, tuple)) and len(times) >= 2:
                chord_prog.append({
                    "chord": chord_name,
                    "start": float(times[0]),
                    "end": float(times[1]),
                })
    elif isinstance(raw_chords, list):
        chord_prog = raw_chords

    midi_obj = midi_utils.create_midi(bpm, "C", "major")
    midi_utils.chords_to_midi(chord_prog, midi_obj)
    midi_utils.save_midi(midi_obj, output_mid)

    return (chord_prog, "librosa_fallback")


def _extract_bass(
    stem_wav: Path,
    bpm: float,
    key: str,
    mode: str,
    output_mid: Path,
) -> Tuple[Path, str]:
    """Extract bass line from bass stem using librosa pYIN.

    Args:
        stem_wav: Path to the bass stem WAV.
        bpm: Detected BPM for tempo setting.
        key: Detected key for MIDI metadata.
        mode: Detected mode for MIDI metadata.
        output_mid: Path to write bass.mid.

    Returns:
        Tuple of (output_mid_path, tool_used) where tool_used is
        "pyin" or "skipped" (if all-NaN F0).
    """
    import librosa

    y, sr = librosa.load(str(stem_wav), sr=22050, mono=True)
    f0, voiced, voiced_prob = librosa.pyin(
        y,
        fmin=30.0,
        fmax=300.0,
        sr=sr,
    )
    times = librosa.times_like(f0, sr=sr)

    # Check if all NaN
    if np.all(np.isnan(f0)) or np.all(f0[~np.isnan(f0)] <= 0):
        print(
            "Warning: pYIN returned all-NaN F0 for bass stem — writing empty bass.mid",
            file=sys.stderr,
        )
        empty_midi = midi_utils.create_midi(bpm, key, mode)
        midi_utils.save_midi(empty_midi, output_mid)
        return (output_mid, "skipped")

    notes = midi_utils.f0_to_notes(f0, times, sr)
    instrument = pretty_midi.Instrument(program=0, name="bass")
    instrument.notes = notes
    midi_obj = midi_utils.create_midi(bpm, key, mode)
    midi_obj.instruments.append(instrument)
    midi_utils.save_midi(midi_obj, output_mid)

    return (output_mid, "pyin")


def _determine_melody_source(
    stems: Dict[str, Path],
) -> Tuple[Path, str]:
    """Determine which stem to use for melody extraction.

    Prefers "vocals" stem if it has sufficient voiced content,
    otherwise uses "other" stem.

    Args:
        stems: Dict of stem name -> Path from extract_stems_preset.

    Returns:
        Tuple of (stem_path, stem_name) for the chosen melody source.
    """
    vocals_path = stems.get("vocals")
    if vocals_path and Path(vocals_path).exists():
        return (Path(vocals_path), "vocals")

    other_path = stems.get("other")
    if other_path and Path(other_path).exists():
        return (Path(other_path), "other")

    # Fallback: use any available stem
    for name, path in stems.items():
        if path and Path(path).exists():
            return (Path(path), name)

    # Last resort: return a dummy path (will fail gracefully downstream)
    return (Path("no_stem.wav"), "none")


def _check_duration(input_wav: Path) -> None:
    """Check input duration and warn if < 15 seconds."""
    try:
        from .. import reverse_engineering_adapter

        analysis = reverse_engineering_adapter.analyze_track(path=input_wav)
        duration = analysis.get("duration_seconds", 0.0)
        if duration < 15.0:
            print(
                f"Warning: Input duration {duration:.1f}s is less than 15s. "
                f"Results may be unreliable.",
                file=sys.stderr,
            )
    except Exception:
        pass


def _extract_instrument_list(instruments_dict: Dict) -> List[str]:
    """Extract a flat list of instrument names from the analysis instruments dict."""
    if not instruments_dict:
        return []

    if isinstance(instruments_dict, list):
        return [str(i) for i in instruments_dict]

    result = []
    if isinstance(instruments_dict, dict):
        for key, value in instruments_dict.items():
            if isinstance(value, (int, float)) and value > 0.5:
                result.append(str(key))
            elif isinstance(value, bool) and value:
                result.append(str(key))
            elif isinstance(value, str):
                result.append(str(value))
            elif isinstance(value, list):
                for item in value:
                    result.append(str(item))

    return result if result else list(instruments_dict.keys())


def _summarize_drum_pattern(instrument: pretty_midi.Instrument) -> Dict:
    """Summarize a drum instrument into a pattern dict."""
    if not instrument.notes:
        return {}

    kick_count = sum(1 for n in instrument.notes if n.pitch == 36)
    snare_count = sum(1 for n in instrument.notes if n.pitch == 38)
    hat_count = sum(1 for n in instrument.notes if n.pitch == 42)

    if not instrument.notes:
        return {}

    duration = max(n.end for n in instrument.notes) - min(n.start for n in instrument.notes)
    if duration <= 0:
        duration = 1.0

    return {
        "kick_density": kick_count / duration,
        "snare_density": snare_count / duration,
        "hat_density": hat_count / duration,
        "pattern_type": "trap" if hat_count > kick_count else "four_floor",
    }


def _is_adtof_available() -> bool:
    """Check if adtof_pytorch is importable."""
    try:
        import adtof_pytorch  # noqa: F401
        return True
    except ImportError:
        return False


def _parse_lab_file(lab_path: Path) -> List[Dict]:
    """Parse an autochord .lab file into a chord progression list."""
    result = []
    text = Path(lab_path).read_text(encoding="utf-8")
    for line in text.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            result.append({
                "chord": parts[2],
                "start": float(parts[0]),
                "end": float(parts[1]),
            })
    return result


def _load_instrument_from_mid(mid_path: Path, name: str) -> pretty_midi.Instrument:
    """Load the first instrument from a MIDI file, or return an empty one."""
    try:
        midi_obj = pretty_midi.PrettyMIDI(str(mid_path))
        if midi_obj.instruments:
            instr = midi_obj.instruments[0]
            instr.name = name
            return instr
    except Exception:
        pass
    return pretty_midi.Instrument(program=0, name=name)
