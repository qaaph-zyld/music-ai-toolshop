"""Stem extraction adapter for music-ai-toolshop.

Uses audio-separator to extract instrumentals, main vocals, and backing vocals
from Suno tracks using a two-pass process.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

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


def extract_stems(
    input_file: Path,
    output_dir: Optional[Path] = None,
    use_gpu: bool = True,
    high_quality: bool = True,
) -> Dict[str, Any]:
    """Extract stems from an audio file using two-pass separation.

    Args:
        input_file: Path to input audio file.
        output_dir: Directory for output files (default: ./separated_tracks).
        use_gpu: Whether to use GPU acceleration.
        high_quality: Use Roformer models (slower) vs MDX-Net (faster).

    Returns:
        Dictionary with extracted stem paths and metadata.
    """
    _check_audio_separator()

    if not input_file.exists():
        raise FileNotFoundError(f"Audio file not found: {input_file}")

    output_dir = output_dir or Path("separated_tracks")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Configure models based on quality
    if high_quality:
        model_pass1 = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
        model_pass2 = "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"
    else:
        model_pass1 = "UVR-MDX-NET-Voc_FT.onnx"
        model_pass2 = "UVR-BVE-4B_SN-44100-1.pth"

    # Configure GPU/CPU settings - use_directml for Windows GPU support
    use_directml = use_gpu  # DirectML is the Windows GPU backend

    # Pass 1: Separate instrumental from all vocals
    separator1 = Separator(
        output_dir=output_dir, output_format="wav", use_directml=use_directml
    )
    separator1.load_model(model_pass1)

    logging.info(f"Pass 1: Extracting instrumental from {input_file}")
    outputs1 = separator1.separate(str(input_file))

    # Pass 2: Separate vocals into main and backing
    vocal_file = None
    for output in outputs1:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = output_dir / output_path
        if "vocals" in output.lower():
            vocal_file = output_path
            break

    if not vocal_file:
        raise RuntimeError("Could not find vocal stem from pass 1")

    separator2 = Separator(
        output_dir=output_dir, output_format="wav", use_directml=use_directml
    )
    separator2.load_model(model_pass2)

    logging.info(f"Pass 2: Splitting vocals from {vocal_file}")
    outputs2 = separator2.separate(str(vocal_file))

    # Clean up intermediate vocal file
    vocal_file.unlink(missing_ok=True)

    return {
        "input_file": str(input_file),
        "output_dir": str(output_dir),
        "stems": {
            "instrumental": next(
                (p for p in outputs1 if "instrumental" in p.lower()), None
            ),
            "main_vocals": next((p for p in outputs2 if "vocals" in p.lower()), None),
            "backing_vocals": next(
                (p for p in outputs2 if "backing" in p.lower() or "other" in p.lower()),
                None,
            ),
        },
        "models_used": {"pass1": model_pass1, "pass2": model_pass2},
        "gpu_used": use_gpu,
        "quality_mode": "high" if high_quality else "fast",
    }
