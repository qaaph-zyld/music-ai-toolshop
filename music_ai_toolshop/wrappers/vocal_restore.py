"""Wrapper for mastering_tool vocal_restore helper."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from paths import resolve_mastering_tool
from wrappers._common import get_python_exe, run_subprocess


def run(
    input_path: Path,
    output_dir: Path,
    params: dict[str, str],
    progress_callback: Callable[[str], None] | None = None,
) -> list[Path]:
    mastering = resolve_mastering_tool()
    stage = params.get("stage", "all")
    output_path = output_dir / "vocal_restored.wav"

    # Prefer the Python helper so we can control the output path directly.
    helper = mastering / "tools" / "vocal_restore" / "restore.py"
    if helper.exists():
        python = get_python_exe()
        cmd = [
            python, str(helper),
            "--input", str(input_path),
            "--output", str(output_path),
            "--stage", stage,
        ]
        rc = run_subprocess(cmd, mastering, progress_callback=progress_callback)
        if rc != 0:
            raise RuntimeError(f"Vocal restore exited with code {rc}")
        if output_path.exists():
            return [output_path]
        return []

    # Fallback to the shell orchestrator.
    script = mastering / "vocal_restore.sh"
    if script.exists():
        fallback = output_dir / "restored_full_mix.wav"
        cmd = ["bash", str(script), str(input_path), str(fallback)]
        rc = run_subprocess(cmd, mastering, progress_callback=progress_callback)
        if rc != 0:
            raise RuntimeError(f"vocal_restore.sh exited with code {rc}")
        if fallback.exists():
            return [fallback]
        return []

    raise FileNotFoundError("No vocal_restore implementation found in mastering_tool.")
