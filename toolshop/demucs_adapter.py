"""Demucs backend adapter for `toolshop stems`.

Tries the Python API first (`demucs.api.Separator`) and falls back to a
`python -m demucs.separate` subprocess if the API is unavailable or fails.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import stem_models

logger = logging.getLogger(__name__)

DEMUCS_STEM_NAMES = ["drums", "bass", "other", "vocals", "guitar", "piano"]


def _check_demucs() -> None:
    try:
        import demucs  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("demucs is required for 4stem/6stem presets") from exc


def _normalize_ext(path: Path, output_format: str) -> Path:
    if output_format in ("wav", "flac"):
        return path.with_suffix(f".{output_format}")
    return path


def auto_jobs() -> int:
    """Pick a demucs worker count for this machine.

    MEASURED 2026-08-30 (8 logical cores, CPU-only), **controlled**: warm-up run
    discarded, then jobs=0 / jobs=4 / jobs=0 again to catch drift.

        jobs=0  30.2 s
        jobs=4  24.6 s      <- 1.22x
        jobs=0  29.6 s      <- baseline repeat, 2.0% drift => stable instrument

    **1.22x, not the 2.97x first reported.** The initial sweep ran the baseline
    cold and the variant warm, so it was partly measuring disk warm-up (56.5 s
    cold vs ~30 s warm). The companion claim on the audio-separator side survived
    that confound even less well - see `stem_extractor_adapter.default_mdxc_params`,
    where a clip-measured "1.40x" turned out to be exactly 1.00x on a full track.

    1.22x is small but genuine, free, and the output is equivalent (stem
    correlation 0.986-0.9995 vs jobs=0; the `other` residual stem varies most,
    as expected).

    Capped at 4 because that is the highest value actually measured; halved from
    the core count so demucs' worker processes do not fight torch's own threads.
    The fleet (G5) has different CPUs, so this is computed, never hardcoded.
    """
    cores = os.cpu_count() or 1
    return max(1, min(4, cores // 2))


def _api_separate(
    input_path: Path,
    output_dir: Path,
    model: stem_models.StemModel,
    output_format: str,
    device: str = "cpu",
    jobs: Optional[int] = None,
) -> Dict[str, str]:
    """Use demucs.api.Separator to separate and write stems to output_dir."""
    from demucs.api import Separator  # type: ignore

    if jobs is None:
        jobs = auto_jobs()
    logger.info("demucs: model=%s device=%s jobs=%d", model.model_file, device, jobs)
    sep = Separator(model=model.model_file, device=device, jobs=jobs)
    # separate_audio_file returns (origin, separated) where separated is a dict.
    _, separated = sep.separate_audio_file(str(input_path))

    stems: Dict[str, str] = {}
    for stem_name, tensor in separated.items():
        out_path = _normalize_ext(output_dir / f"{stem_name}", output_format)
        sep.save_audio(tensor, str(out_path))
        stems[stem_name] = str(out_path)
    return stems


def _cli_separate(
    input_path: Path,
    output_dir: Path,
    model: stem_models.StemModel,
    output_format: str,
    device: str = "cpu",
) -> Dict[str, str]:
    """Fallback to `python -m demucs.separate` subprocess."""
    python = sys.executable
    cmd: List[str] = [
        python,
        "-m",
        "demucs.separate",
        "--name",
        model.model_file,
        "--device",
        device,
        "--out",
        str(output_dir),
        str(input_path),
    ]

    # Use a format demucs supports. Default CLI outputs wav.
    if output_format == "mp3":
        cmd.append("--mp3")
    elif output_format == "mp4":
        cmd.append("--mp4")

    logger.info("Running demucs CLI: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"demucs CLI failed (exit {result.returncode}): {result.stderr}"
        )

    # Demucs CLI emits: <out_dir>/<model>/<input_stem>/<stem>.wav
    song_dir = output_dir / model.model_file / input_path.stem
    stems: Dict[str, str] = {}
    for stem_name in DEMUCS_STEM_NAMES:
        candidate = _normalize_ext(song_dir / stem_name, output_format)
        if candidate.exists():
            stems[stem_name] = str(candidate)
    return stems


def separate(
    input_file: Path,
    model_id: str,
    *,
    output_dir: Optional[Path] = None,
    output_format: str = "flac",
    device: str = "cpu",
    jobs: Optional[int] = None,
) -> Dict[str, Any]:
    """Separate an audio file with Demucs.

    Args:
        input_file: Path to input audio.
        model_id: Registry model id (e.g. 'htdemucs' or 'htdemucs_6s').
        output_dir: Destination directory for stems.
        output_format: Output audio format.
        device: 'cpu' or 'cuda'.
        jobs: Demucs worker processes. None picks a measured default for this
            machine via `auto_jobs()` - see its docstring for the 2.97x figure.

    Returns:
        Result dict matching the adapter contract used by `stems_cli`.
    """
    model = stem_models.get_model(model_id)
    if model.backend != "demucs":
        raise ValueError(f"Model {model_id} is not a demucs backend")
    _check_demucs()

    output_dir = output_dir or Path("separated_tracks") / model_id
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()
    try:
        stems = _api_separate(
            input_path=input_file,
            output_dir=output_dir,
            model=model,
            output_format=output_format,
            device=device,
            jobs=jobs,
        )
        backend = "demucs-api"
    except Exception:
        logger.warning("Demucs API failed, falling back to CLI subprocess")
        stems = _cli_separate(
            input_path=input_file,
            output_dir=output_dir,
            model=model,
            output_format=output_format,
            device=device,
        )
        backend = "demucs-cli"

    elapsed = time.time() - start
    return {
        "input_file": str(input_file),
        "output_dir": str(output_dir),
        "preset": model_id,
        "stems": stems,
        "models_used": [model_id],
        "gpu_used": device != "cpu",
        "output_format": output_format,
        "backend": backend,
        "elapsed_seconds": elapsed,
    }
