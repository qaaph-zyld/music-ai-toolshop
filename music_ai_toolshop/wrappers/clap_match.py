"""Wrapper for mastering_tool CLAP reference matcher."""
from __future__ import annotations

import re
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
    k = params.get("k", "5")
    genre = params.get("genre", "")

    python = get_python_exe()
    cmd = [
        python, "-m", "tools.clap_match.match",
        str(input_path),
        "--k", k,
    ]
    if genre:
        cmd.extend(["--genre", genre])

    report_path = output_dir / "clap_match_report.txt"
    lines: list[str] = []
    def capture(line: str):
        lines.append(line)
        if progress_callback:
            progress_callback(line)

    rc = run_subprocess(cmd, mastering, progress_callback=capture)
    if rc != 0:
        raise RuntimeError(f"CLAP matcher exited with code {rc}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return [report_path]
