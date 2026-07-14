"""Stem extraction adapter for music-ai-toolshop.

Uses audio-separator to extract instrumentals, vocals, and backing vocals from
audio files. Model choices and filename-to-stem mappings are driven by the
stem model registry in `toolshop.stem_models` so the code no longer has to
guess filenames from substrings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from . import stem_models

try:
    from audio_separator.separator import Separator

    _HAS_AUDIO_SEPARATOR = True
except ImportError:
    _HAS_AUDIO_SEPARATOR = False


def _check_audio_separator() -> None:
    if not _HAS_AUDIO_SEPARATOR:
        raise RuntimeError(
            "audio-separator is required for stem extraction. "
            "Install with: pip install audio-separator"
        )


def _default_model_dir() -> Path:
    """Persistent directory for downloaded separation models."""
    return Path.home() / ".cache" / "toolshop-models"


def _run_audio_separator(
    input_path: Path,
    model: stem_models.StemModel,
    output_dir: Path,
    use_gpu: bool = False,
    output_format: str = "wav",
    model_file_dir: Optional[Path] = None,
) -> Dict[str, str]:
    """Run one audio-separator model and return canonical stem paths."""
    _check_audio_separator()

    model_file_dir = model_file_dir or _default_model_dir()
    model_file_dir.mkdir(parents=True, exist_ok=True)

    use_directml = use_gpu  # DirectML is the Windows GPU backend
    separator = Separator(
        output_dir=str(output_dir),
        output_format=output_format,
        use_directml=use_directml,
        model_file_dir=str(model_file_dir),
    )
    separator.load_model(model.model_file)

    logging.info("Running %s on %s", model.id, input_path)
    raw_outputs = separator.separate(str(input_path))
    resolved = stem_models.resolve_outputs(raw_outputs, model)

    # Convert relative paths to absolute paths.
    absolute: Dict[str, str] = {}
    for stem, raw in resolved.items():
        raw_path = Path(raw)
        if not raw_path.is_absolute():
            raw_path = output_dir / raw_path
        absolute[stem] = str(raw_path)

    return absolute


def extract_stems_preset(
    input_file: Path,
    preset_id: str = "full-vocals",
    output_dir: Optional[Path] = None,
    use_gpu: bool = False,
    output_format: Optional[str] = None,
    model_file_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Extract stems using a named preset from the registry.

    Args:
        input_file: Path to input audio file.
        preset_id: One of the presets in stem_models.PRESETS.
        output_dir: Directory for output files. Defaults to
            ./separated_tracks/<preset_id>.
        use_gpu: Whether to use GPU acceleration (default: CPU).
        output_format: Audio format written by the backend. Defaults to the
            preset's configured format.
        model_file_dir: Directory where audio-separator caches downloaded models.

    Returns:
        Dictionary with extracted stem paths, metadata, and timing info.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Audio file not found: {input_file}")

    preset = stem_models.get_preset(preset_id)
    output_dir = output_dir or Path("separated_tracks") / preset_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_format = output_format or preset.output_format

    intermediate: Dict[str, str] = {"source": str(input_file)}
    final_stems: Dict[str, str] = {}
    models_used: list[str] = []

    for step_index, step in enumerate(preset.steps):
        model = stem_models.get_model(step.model_id)
        if model.backend != "audio-separator":
            raise RuntimeError(
                f"Preset {preset_id} step {model.id} uses unsupported backend "
                f"{model.backend} in this adapter; use the demucs adapter instead."
            )

        input_key = step.input
        if input_key == "source":
            input_path = input_file
        else:
            if input_key not in intermediate:
                raise RuntimeError(
                    f"Preset {preset_id} step {model.id} needs intermediate stem "
                    f"'{input_key}' but it was not produced by a previous step."
                )
            input_path = Path(intermediate[input_key])

        resolved = _run_audio_separator(
            input_path=input_path,
            model=model,
            output_dir=output_dir,
            use_gpu=use_gpu,
            output_format=output_format,
            model_file_dir=model_file_dir,
        )

        # Apply preset-level aliases (e.g. map model's "vocals" to "main_vocals").
        if step.aliases:
            aliased: Dict[str, str] = {}
            for raw_stem, path in resolved.items():
                canonical = step.aliases.get(raw_stem, raw_stem)
                aliased[canonical] = path
            resolved = aliased

        # Keep every output as a possible input for later steps; overwrite so
        # later passes (e.g. refined main_vocals) replace earlier intermediates.
        for stem, path in resolved.items():
            intermediate[stem] = path

        models_used.append(model.id)

        # An output is final if it is declared by this step and not consumed as
        # an input by any later step.
        remaining_steps = preset.steps[step_index + 1 :]
        for stem in step.outputs:
            if stem in resolved and not any(s.input == stem for s in remaining_steps):
                final_stems[stem] = intermediate[stem]

        # Clean up intermediate stems that are not final outputs and not needed
        # by later steps.
        for stem, path in list(intermediate.items()):
            if stem in ("source", *final_stems):
                continue
            needed_later = any(s.input == stem for s in remaining_steps)
            if not needed_later:
                Path(path).unlink(missing_ok=True)
                del intermediate[stem]

    return {
        "input_file": str(input_file),
        "output_dir": str(output_dir),
        "preset": preset_id,
        "stems": final_stems,
        "models_used": models_used,
        "gpu_used": use_gpu,
        "output_format": output_format,
    }


def extract_stems(
    input_file: Path,
    output_dir: Optional[Path] = None,
    use_gpu: bool = True,
    high_quality: bool = True,
) -> Dict[str, Any]:
    """Legacy two-pass stem extraction.

    Preserves the old CLI/contract by mapping the boolean quality flag to a
    registry preset.
    """
    preset_id = "full-vocals-hq" if high_quality else "full-vocals"
    result = extract_stems_preset(
        input_file=input_file,
        preset_id=preset_id,
        output_dir=output_dir,
        use_gpu=use_gpu,
        output_format="wav",
    )
    # Maintain the old return keys for callers that expect them.
    result["quality_mode"] = "high" if high_quality else "fast"
    return result
