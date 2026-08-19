"""Stage 2 renderer for the melody carrier generator.

Loads Stage 1 MIDI files and analysis.json, renders carrier WAVs
(sine-wave always, SoundFont if midirenderer available), generates
Suno cover mode prompts, and writes a README.txt with upload instructions.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List

import pretty_midi

from . import midi_utils
from . import prompt_gen


def render(
    work_dir: Path,
    instruments: str = "",
    fidelity: str = "medium",
) -> Dict:
    """Stage 2: Render carrier WAVs and generate Suno prompts from Stage 1 MIDI.

    Pipeline:
    1. Validate stage1/analysis.json exists (clear error if missing)
    2. Load analysis.json
    3. Validate stage1/midi/melody.mid exists
    4. Print detected instruments
    5. Parse instrument substitutions
    6. Render carrier WAVs (all normalized to -1 dB peak, 44.1kHz/16-bit)
    7. Generate prompts via prompt_gen.generate_prompts()
    8. Write README.txt with upload instructions
    9. Print summary

    Args:
        work_dir: Root working directory containing stage1/ subdirectory.
        instruments: Substitution string "piano:cathedral organ,guitar:synth lead".
                     Empty string = no substitutions.
        fidelity: "low", "medium", or "high" — controls Audio Influence %.

    Returns:
        Dict with keys:
        - "stage2_dir": Path to stage2 output directory
        - "carriers": Dict of carrier name -> Path (carrier_sine.wav, etc.)
        - "prompts": Dict from prompt_gen.generate_prompts()
        - "readme": Path to README.txt
        - "fidelity_pct": int (35/55/70)

    Raises:
        FileNotFoundError: If stage1/analysis.json or stage1/midi/melody.mid missing.
    """
    work_dir = Path(work_dir)
    stage1_dir = work_dir / "stage1"

    # Step 1: Validate analysis.json
    analysis_path = stage1_dir / "analysis.json"
    if not analysis_path.exists():
        raise FileNotFoundError(
            f"Stage 1 analysis.json not found in {stage1_dir}. "
            f"Run 'toolshop melody-carrier extract' first."
        )

    # Step 2: Load analysis
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))

    # Step 3: Validate melody.mid
    midi_dir = stage1_dir / "midi"
    melody_mid = midi_dir / "melody.mid"
    if not melody_mid.exists():
        raise FileNotFoundError(
            f"Required melody.mid not found in {midi_dir}."
        )

    # Step 4: Print detected instruments
    detected = analysis.get("detected_instruments", [])
    print(f"Detected instruments: {', '.join(detected) if detected else 'none'}")

    # Step 5: Parse substitutions
    substitutions = _parse_substitutions(instruments)

    # Step 6: Create stage2 dir and render carriers
    stage2_dir = work_dir / "stage2"
    stage2_dir.mkdir(parents=True, exist_ok=True)
    carriers = _render_carriers(stage1_dir, stage2_dir, substitutions)

    # Step 7: Generate prompts
    prompts = prompt_gen.generate_prompts(
        analysis, substitutions, fidelity, stage2_dir
    )

    # Step 8: Write README
    readme_path = _write_readme(stage2_dir, fidelity, carriers)

    # Step 9: Print summary
    fidelity_pct = prompt_gen._fidelity_to_pct(fidelity)
    carrier_names = ", ".join(sorted(carriers.keys()))
    print(
        f"\n--- Stage 2 complete ---\n"
        f"Output directory: {stage2_dir}\n"
        f"Carriers produced: {carrier_names}\n"
        f"Audio Influence: {fidelity_pct}%\n"
        f"Prompt files: {', '.join(sorted(prompts.keys()))}\n"
        f"README: {readme_path}\n"
    )

    return {
        "stage2_dir": stage2_dir,
        "carriers": carriers,
        "prompts": prompts,
        "readme": readme_path,
        "fidelity_pct": fidelity_pct,
    }


def _parse_substitutions(
    substitutions_str: str,
) -> Dict[str, str]:
    """Parse instrument substitution string into a dict.

    Format: "piano:cathedral organ,guitar:synth lead"
    -> {"piano": "cathedral organ", "guitar": "synth lead"}

    Args:
        substitutions_str: Comma-separated "original:replacement" pairs.
                           Empty string returns empty dict.

    Returns:
        Dict mapping original instrument name to replacement instrument name.
    """
    if not substitutions_str or not substitutions_str.strip():
        return {}

    result: Dict[str, str] = {}
    for entry in substitutions_str.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            print(
                f"Warning: skipping invalid substitution '{entry}' "
                f"(missing colon). Expected format: 'original:replacement'",
                file=sys.stderr,
            )
            continue
        original, replacement = entry.split(":", 1)
        original = original.strip()
        replacement = replacement.strip()
        if original and replacement:
            result[original] = replacement

    return result


def _render_carriers(
    stage1_dir: Path,
    stage2_dir: Path,
    substitutions: Dict[str, str],
) -> Dict[str, Path]:
    """Render all carrier WAV variants from Stage 1 MIDI files.

    Carriers produced (all 44.1kHz/16-bit, normalized to -1 dB peak):
    - carrier_sine.wav: pretty_midi .synthesize() on melody.mid (always produced)
    - carrier_melody_only.wav: midirenderer + SoundFont on melody.mid (if available)
    - carrier_melody_chords.wav: midirenderer on merged melody+chords
    - carrier_melody_chords_bass.wav: midirenderer on merged melody+chords+bass
    - carrier_full_sketch.wav: midirenderer on full_sketch.mid
    - carrier_reference.wav: copy of stage1/stems/other.wav

    If midirenderer not installed: skip SoundFont carriers, still produce sine.
    carrier_sine.wav has zero external dependencies and is always produced.

    Args:
        stage1_dir: Path to stage1 directory with MIDI files.
        stage2_dir: Path to stage2 output directory.
        substitutions: Instrument substitution dict (for future SoundFont selection).

    Returns:
        Dict of carrier name -> Path. Always includes "carrier_sine".
        SoundFont carriers included only if midirenderer available.
    """
    stage1_dir = Path(stage1_dir)
    stage2_dir = Path(stage2_dir)
    midi_dir = stage1_dir / "midi"

    carriers: Dict[str, Path] = {}

    # --- carrier_sine.wav: always produced (zero external deps) ---
    sine_path = stage2_dir / "carrier_sine.wav"
    midi_utils.render_sine(midi_dir / "melody.mid", sine_path)
    carriers["carrier_sine"] = sine_path

    # --- SoundFont carriers via midirenderer (optional) ---
    midirenderer_available = False
    try:
        import midirenderer  # noqa: F401
        midirenderer_available = True
    except ImportError:
        print(
            "Warning: midirenderer not installed — skipping SoundFont carriers. "
            "Only carrier_sine.wav will be produced. "
            "Install midirenderer for higher-quality carriers.",
            file=sys.stderr,
        )

    if midirenderer_available:
        bpm = 120.0
        analysis_path = stage1_dir / "analysis.json"
        if analysis_path.exists():
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            bpm = float(analysis.get("bpm", 120.0))

        # carrier_melody_only.wav
        melody_only_path = stage2_dir / "carrier_melody_only.wav"
        _render_with_midirenderer(midi_dir / "melody.mid", melody_only_path)
        carriers["carrier_melody_only"] = melody_only_path

        # carrier_melody_chords.wav
        mc_mid = stage2_dir / "_merged_melody_chords.mid"
        _merge_midi_files(
            [midi_dir / "melody.mid", midi_dir / "chords.mid"], bpm, mc_mid
        )
        mc_path = stage2_dir / "carrier_melody_chords.wav"
        _render_with_midirenderer(mc_mid, mc_path)
        carriers["carrier_melody_chords"] = mc_path

        # carrier_melody_chords_bass.wav
        mcb_mid = stage2_dir / "_merged_melody_chords_bass.mid"
        _merge_midi_files(
            [midi_dir / "melody.mid", midi_dir / "chords.mid", midi_dir / "bass.mid"],
            bpm,
            mcb_mid,
        )
        mcb_path = stage2_dir / "carrier_melody_chords_bass.wav"
        _render_with_midirenderer(mcb_mid, mcb_path)
        carriers["carrier_melody_chords_bass"] = mcb_path

        # carrier_full_sketch.wav
        full_path = stage2_dir / "carrier_full_sketch.wav"
        _render_with_midirenderer(midi_dir / "full_sketch.mid", full_path)
        carriers["carrier_full_sketch"] = full_path

    # --- carrier_reference.wav: copy of stems/other.wav ---
    other_wav = stage1_dir / "stems" / "other.wav"
    if other_wav.exists():
        ref_path = stage2_dir / "carrier_reference.wav"
        shutil.copy(str(other_wav), str(ref_path))
        carriers["carrier_reference"] = ref_path
    else:
        print(
            f"Warning: {other_wav} not found — skipping carrier_reference.wav",
            file=sys.stderr,
        )

    return carriers


def _render_with_midirenderer(midi_path: Path, output_wav: Path) -> None:
    """Render a MIDI file to WAV using midirenderer + SoundFont.

    This is a thin wrapper that calls midirenderer's render function.
    Normalizes output to -1 dB peak, 44100 Hz, 16-bit.

    Args:
        midi_path: Path to input .mid file.
        output_wav: Path to output .wav file.
    """
    import midirenderer

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    midirenderer.render(str(midi_path), str(output_wav))


def _write_readme(
    stage2_dir: Path,
    fidelity: str,
    carriers: Dict[str, Path],
) -> Path:
    """Write README.txt with Suno upload instructions.

    Content includes:
    - Upload steps (Suno -> Cover mode -> upload carrier -> paste prompt)
    - Recommended carrier (sine first, then piano)
    - Audio Influence percentage
    - Community tips: shorter clips, dry sketches, trim dead air, one slider at a time

    Args:
        stage2_dir: Directory to write README.txt into.
        fidelity: Fidelity level for Audio Influence recommendation.
        carriers: Dict of carrier paths for listing in README.

    Returns:
        Path to written README.txt.
    """
    fidelity_pct = prompt_gen._fidelity_to_pct(fidelity)

    carrier_list = "\n".join(
        f"  - {name}: {path.name}" for name, path in sorted(carriers.items())
    )

    content = f"""\
Suno Cover Mode — Carrier Upload Guide
=======================================

UPLOAD STEPS
------------
1. Go to Suno and select "Cover" mode.
2. Upload one of the carrier WAV files from this directory.
3. Paste the text from one of the suno_prompt_*.txt files into the prompt field.
4. Set the Audio Influence slider to {fidelity_pct}%.
5. Generate and evaluate the result.

RECOMMENDED CARRIER
-------------------
Start with carrier_sine.wav — it contains the pure melody contour and works
reliably with Suno's cover mode. If the result is too sparse, try
carrier_melody_chords.wav or carrier_full_sketch.wav for a richer carrier.

AVAILABLE CARRIERS
------------------
{carrier_list}

AUDIO INFLUENCE
---------------
Audio Influence: {fidelity_pct}%
- low (35%): vague suggestion, Suno takes creative freedom
- medium (55%): where most people land — melody is followed but with room to improvise
- high (70%): melody closely followed by Suno

COMMUNITY TIPS
--------------
- Use shorter clips (30-60s) for better results — Suno handles short carriers better
- Keep carriers dry and simple — reverb and complex arrangements confuse the model
- Trim dead air at the start and end of the carrier
- Change one slider at a time when experimenting — isolate variables
- Cover mode regenerates the entire track — the uploaded audio is NOT in the output
- The carrier provides melodic DNA; the prompt provides style/genre context

PROMPT FILES
------------
- suno_prompt_minimal.txt: genre, bpm, key, instruments, Audio Influence
- suno_prompt_descriptive.txt: adds chord progression, drum style, energy description
- suno_prompt_detailed.txt: adds harmonic structure, tuning offset, spectral profile
"""

    readme_path = Path(stage2_dir) / "README.txt"
    readme_path.write_text(content, encoding="utf-8")
    return readme_path


def _merge_midi_files(
    midi_files: List[Path],
    bpm: float,
    output_mid: Path,
) -> Path:
    """Merge multiple MIDI files into one multi-track MIDI.

    Used for carrier_melody_chords.wav and carrier_melody_chords_bass.wav.

    Args:
        midi_files: List of MIDI file paths to merge (in order).
        bpm: Tempo for output MIDI.
        output_mid: Path to write merged MIDI.

    Returns:
        Path to written merged MIDI file.
    """
    instruments: List[pretty_midi.Instrument] = []

    for midi_path in midi_files:
        midi_obj = pretty_midi.PrettyMIDI(str(midi_path))
        for instr in midi_obj.instruments:
            instruments.append(instr)

    merged = midi_utils.merge_instruments(instruments, bpm)
    midi_utils.save_midi(merged, output_mid)

    return output_mid
