"""Common subprocess runner for tool wrappers."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


def run_subprocess(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> int:
    """Run a subprocess, streaming stdout/stderr to the callback. Returns exit code."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )

    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if progress_callback:
                progress_callback(line)
    except Exception:
        proc.kill()
        raise

    proc.wait()
    return proc.returncode


def get_python_exe() -> str:
    """Return the Python interpreter to use for subprocess calls."""
    if getattr(sys, 'frozen', False):
        for name in ("python", "python3", "py"):
            path = shutil.which(name)
            if path:
                return path
        raise RuntimeError("Cannot find python executable for subprocess tools.")
    return sys.executable
