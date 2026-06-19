"""Wrapper for open_DAW stem_extractor CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from paths import resolve_open_daw
from wrappers._common import get_python_exe, run_subprocess


def run(
    input_path: Path,
    output_dir: Path,
    params: dict[str, str],
    progress_callback: Callable[[str], None] | None = None,
) -> list[Path]:
    open_daw = resolve_open_daw()
    backend = params.get("backend", "roformer")
    stem = params.get("stem", "vocals,instrumental")

    python = get_python_exe()
    cmd = [
        python, "-m", "ai_modules.stem_extractor.cli", "separate",
        str(input_path),
        "--backend", backend,
        "--stem", stem,
    ]

    rc = run_subprocess(cmd, open_daw, progress_callback=progress_callback)
    if rc != 0:
        raise RuntimeError(f"Stem extractor exited with code {rc}")

    # The CLI prints stem paths to stdout; the wrapper will have seen them.
    # We cannot reliably parse them back from the callback, so return an empty
    # list here. The server currently falls back to scanning the output dir.
    return []
