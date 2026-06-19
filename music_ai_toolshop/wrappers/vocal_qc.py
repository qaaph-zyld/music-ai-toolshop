"""Wrapper for mastering_tool Whisper-driven vocal QC."""
from __future__ import annotations

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
    lyric = params.get("lyric", "")

    python = get_python_exe()
    cmd = [
        python, "-m", "tools.vocal_qc.diagnose",
        str(input_path),
    ]
    if lyric:
        cmd.extend(["--lyric", lyric])

    report_path = output_dir / "vocal_qc_report.md"
    lines: list[str] = []
    def capture(line: str):
        lines.append(line)
        if progress_callback:
            progress_callback(line)

    rc = run_subprocess(cmd, mastering, progress_callback=capture)
    if rc != 0:
        raise RuntimeError(f"Vocal QC exited with code {rc}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return [report_path]
