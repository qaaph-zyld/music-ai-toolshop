"""Suno cover mode prompt generator for the melody carrier generator.

Generates three tiers of Suno cover mode prompts (minimal, descriptive, detailed)
from track analysis data, instrument substitutions, and fidelity level.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


_FIDELITY_MAP = {
    "low": 35,
    "medium": 55,
    "high": 70,
}


def generate_prompts(
    analysis: Dict,
    substitutions: Dict[str, str],
    fidelity: str,
    output_dir: Path,
) -> Dict[str, Path]:
    """Generate three Suno cover mode prompt files (minimal, descriptive, detailed).

    Args:
        analysis: Analysis dict from extractor (bpm, key, mode, genre,
                  spectral_centroid, spectral_bandwidth, harmonic_ratio,
                  onset_strength, chord_progression, detected_instruments,
                  tuning_offset, drum_pattern).
        substitutions: Dict mapping original instrument -> replacement instrument
                       (e.g., {"piano": "cathedral organ"}). Empty dict = no subs.
        fidelity: "low", "medium", or "high" — controls Audio Influence %.
        output_dir: Directory to write prompt files into. Created if needed.

    Returns:
        Dict with keys "minimal", "descriptive", "detailed" mapping to Path
        objects for the three written files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fidelity_pct = _fidelity_to_pct(fidelity)

    genre = analysis.get("genre", "unknown")
    bpm = analysis.get("bpm", 120.0)
    key = analysis.get("key", "C")
    mode = analysis.get("mode", "major")

    detected_instruments = analysis.get("detected_instruments", [])
    chord_prog = analysis.get("chord_progression", [])
    onset_strength = analysis.get("onset_strength", 0.5)
    harmonic_ratio = analysis.get("harmonic_ratio", 0.5)
    spectral_centroid = analysis.get("spectral_centroid", 0.0)
    spectral_bandwidth = analysis.get("spectral_bandwidth", 0.0)
    tuning_offset = analysis.get("tuning_offset", 0.0)
    drum_pattern = analysis.get("drum_pattern", {})

    # Build instrument list with substitutions applied
    instrument_list = _build_instrument_list(detected_instruments, substitutions)

    # Build substitution description strings
    sub_desc_minimal = _substitution_description_minimal(substitutions)
    sub_desc_detailed = _substitution_description_detailed(substitutions)

    energy_desc = _energy_description(onset_strength, harmonic_ratio)
    drum_desc = _drum_description(drum_pattern)
    chord_compact = _format_chord_progression(chord_prog, compact=True)
    chord_full = _format_chord_progression(chord_prog, compact=False)

    # --- Minimal prompt ---
    minimal_text = (
        f"{genre} instrumental, {bpm} bpm, {key} {mode}\n"
        f"Instruments: {sub_desc_minimal}\n"
        f"Audio Influence: {fidelity_pct}%\n"
    )

    # --- Descriptive prompt ---
    descriptive_text = (
        f"{genre} instrumental, {bpm} bpm, {key} {mode}\n"
        f"{energy_desc} arrangement with {instrument_list}\n"
        f"Chord progression: {chord_compact}\n"
        f"Instrument substitutions: {sub_desc_detailed}\n"
        f"Drum style: {drum_desc}\n"
        f"Audio Influence: {fidelity_pct}%\n"
    )

    # --- Detailed prompt ---
    best_carrier = _best_carrier_recommendation(energy_desc, drum_desc)

    detailed_text = (
        f"{genre} instrumental cover, {bpm} bpm, {key} {mode}\n"
        f"{energy_desc} with {instrument_list}\n"
        f"\n"
        f"Harmonic structure:\n"
        f"- Key: {key} {mode}\n"
        f"- Chord progression: {chord_full}\n"
        f"- Tuning offset: {tuning_offset} cents\n"
        f"\n"
        f"Instrument substitutions:\n"
        f"{_per_instrument_rationale(substitutions, detected_instruments)}\n"
        f"\n"
        f"Arrangement notes:\n"
        f"- Drum pattern: {drum_desc}\n"
        f"- Spectral profile: centroid {spectral_centroid}Hz, bandwidth {spectral_bandwidth}Hz\n"
        f"- Harmonic ratio: {harmonic_ratio}\n"
        f"\n"
        f"Audio Influence: {fidelity_pct}% (melody contour preservation)\n"
        f"\n"
        f"Recommended carrier: {best_carrier}\n"
    )

    paths = {}
    for name, text in (
        ("minimal", minimal_text),
        ("descriptive", descriptive_text),
        ("detailed", detailed_text),
    ):
        p = output_dir / f"suno_prompt_{name}.txt"
        p.write_text(text, encoding="utf-8")
        paths[name] = p

    return paths


def _energy_description(onset_strength: float, harmonic_ratio: float) -> str:
    """Derive energy description from spectral features.

    Args:
        onset_strength: Onset strength from analysis (higher = more percussive).
        harmonic_ratio: Harmonic ratio from analysis (higher = more tonal).

    Returns:
        String like "high-energy percussive" or "laid-back atmospheric".
    """
    if onset_strength > 0.6 and harmonic_ratio < 0.7:
        return "high-energy percussive"
    if onset_strength < 0.5 and harmonic_ratio > 0.6:
        return "laid-back atmospheric"
    if onset_strength > 0.6:
        return "high-energy percussive"
    return "laid-back atmospheric"


def _drum_description(drum_pattern: Dict) -> str:
    """Derive drum style description from drum pattern data.

    Args:
        drum_pattern: Dict with drum pattern summary (kick_density, snare_density,
                      hat_density, pattern_type).

    Returns:
        String like "trap hi-hats with deep kick" or "four-on-the-floor".
    """
    if not drum_pattern:
        return "no drums detected"

    hat_density = drum_pattern.get("hat_density", 0.0)
    kick_density = drum_pattern.get("kick_density", 0.0)
    pattern_type = drum_pattern.get("pattern_type", "")

    if pattern_type == "trap" or hat_density >= 3.0:
        return "trap hi-hats with deep kick"
    if kick_density > 0 and kick_density <= 2.0 and hat_density < 3.0:
        return "four-on-the-floor"
    if hat_density >= 3.0:
        return "trap hi-hats with deep kick"
    if kick_density > 0:
        return "four-on-the-floor"
    return "no drums detected"


def _format_chord_progression(
    chord_prog: List[Dict],
    compact: bool = False,
) -> str:
    """Format chord progression for prompt inclusion.

    Args:
        chord_prog: List of dicts with "chord", "start", "end" keys.
        compact: If True, return short form "Am - F - C - G".
                 If False, return long form with timings.

    Returns:
        Formatted chord progression string.
    """
    if not chord_prog:
        return "N/A"

    if compact:
        return " - ".join(entry["chord"] for entry in chord_prog)

    parts = []
    for entry in chord_prog:
        chord = entry["chord"]
        start = entry.get("start", 0.0)
        end = entry.get("end", 0.0)
        parts.append(f"{chord} ({start:.1f}s-{end:.1f}s)")
    return ", ".join(parts)


def _fidelity_to_pct(fidelity: str) -> int:
    """Map fidelity level to Suno Audio Influence percentage.

    Args:
        fidelity: "low", "medium", or "high".

    Returns:
        Integer percentage for Audio Influence slider.

    Raises:
        ValueError: If fidelity is not one of the three valid values.
    """
    if fidelity not in _FIDELITY_MAP:
        raise ValueError(
            f"Invalid fidelity '{fidelity}'. Must be one of: {', '.join(_FIDELITY_MAP.keys())}"
        )
    return _FIDELITY_MAP[fidelity]


def _build_instrument_list(
    detected_instruments: List[str],
    substitutions: Dict[str, str],
) -> str:
    """Build the instrument list string with substitutions applied."""
    if not detected_instruments:
        return "instruments not specified"

    instruments = []
    for inst in detected_instruments:
        instruments.append(substitutions.get(inst, inst))

    if len(instruments) == 1:
        return instruments[0]
    if len(instruments) == 2:
        return f"{instruments[0]} and {instruments[1]}"
    return ", ".join(instruments[:-1]) + f", and {instruments[-1]}"


def _substitution_description_minimal(substitutions: Dict[str, str]) -> str:
    """Build a minimal instrument/substitution description."""
    if not substitutions:
        return "as detected"
    parts = [f"{replacement}" for original, replacement in substitutions.items()]
    return ", ".join(parts)


def _substitution_description_detailed(substitutions: Dict[str, str]) -> str:
    """Build a detailed substitution description."""
    if not substitutions:
        return "none"
    parts = [f"{original} -> {replacement}" for original, replacement in substitutions.items()]
    return ", ".join(parts)


def _per_instrument_rationale(
    substitutions: Dict[str, str],
    detected_instruments: List[str],
) -> str:
    """Build per-instrument rationale text for the detailed prompt."""
    if not substitutions:
        return "none"
    lines = []
    for original, replacement in substitutions.items():
        lines.append(f"- {original} replaced with {replacement}")
    return "\n".join(lines)


def _best_carrier_recommendation(energy_desc: str, drum_desc: str) -> str:
    """Recommend the best carrier type based on energy and drum descriptions."""
    if "percussive" in energy_desc:
        return "sine-wave MIDI carrier with strong rhythmic content"
    if "atmospheric" in energy_desc:
        return "sine-wave MIDI carrier with sustained pad textures"
    return "sine-wave MIDI carrier"
