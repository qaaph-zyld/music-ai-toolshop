"""Bridge helpers for invoking the music-ai-toolshop CLI from a ReaScript.

This module is intentionally free of any Reaper API imports so it can be
unit-tested in isolation. The companion ReaScript files in this directory
import from this module and add the Reaper-specific glue (selecting media
items, writing markers, console output, etc.).

The bridge calls the ``toolshop`` CLI as a subprocess. This mirrors how
the rest of ``music-ai-toolshop`` is consumed and avoids tying the script
to whichever Python interpreter Reaper happens to ship.

Configuration via environment variables:

* ``TOOLSHOP_BIN``  - path or name of the ``toolshop`` entry point.
                       Defaults to ``"toolshop"`` (must be on ``PATH``).
* ``TOOLSHOP_PYTHON`` - if set, the bridge runs ``<python> -m toolshop.cli ...``
                        instead of the bare ``toolshop`` binary. Useful when
                        the CLI lives in a different virtualenv than Reaper's
                        embedded Python.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


class ToolshopError(RuntimeError):
    """Raised when the ``toolshop`` CLI cannot be invoked or returns an error."""


@dataclass(frozen=True)
class BpmKeyResult:
    """Structured result from ``toolshop analyze bpm-key --json``."""

    file: str
    bpm: float
    key: str
    mode: str
    duration_seconds: float
    sample_rate: int

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BpmKeyResult":
        try:
            return cls(
                file=str(payload["file"]),
                bpm=float(payload["bpm"]),
                key=str(payload["key"]),
                mode=str(payload["mode"]),
                duration_seconds=float(payload["duration_seconds"]),
                sample_rate=int(payload["sample_rate"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ToolshopError(
                f"Unexpected payload from toolshop analyze bpm-key: {payload!r}"
            ) from exc

    def summary(self) -> str:
        """One-line human-readable summary suitable for Reaper's console."""
        return (
            f"{Path(self.file).name}: {self.bpm:.2f} BPM, "
            f"{self.key} {self.mode}, {self.duration_seconds:.2f}s"
        )


def resolve_toolshop_command(env: Optional[Dict[str, str]] = None) -> List[str]:
    """Build the argv prefix used to invoke the ``toolshop`` CLI.

    Args:
        env: Mapping to read configuration from. Defaults to ``os.environ``.

    Returns:
        A list suitable to pass as the prefix of ``subprocess.run`` argv.

    Raises:
        ToolshopError: if neither ``TOOLSHOP_PYTHON`` is set nor a ``toolshop``
            binary is discoverable on ``PATH``.
    """
    env = os.environ if env is None else env

    python = env.get("TOOLSHOP_PYTHON")
    if python:
        return [python, "-m", "toolshop.cli"]

    binary = env.get("TOOLSHOP_BIN", "toolshop")
    resolved = shutil.which(binary)
    if not resolved:
        raise ToolshopError(
            "Could not find the 'toolshop' CLI. Either install music-ai-toolshop "
            "(pip install -e .) and ensure 'toolshop' is on PATH, or set the "
            "TOOLSHOP_PYTHON environment variable to a Python interpreter that "
            "has it installed."
        )
    return [resolved]


def _run_toolshop(
    args: Sequence[str],
    env: Optional[Dict[str, str]] = None,
    runner: Any = subprocess.run,
    timeout: Optional[float] = None,
) -> str:
    """Run the toolshop CLI and return stdout. Internal helper.

    The ``runner`` parameter is dependency-injected so tests can replace it
    with a fake without touching ``subprocess`` globally.
    """
    cmd = list(resolve_toolshop_command(env)) + list(args)
    try:
        completed = runner(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ToolshopError(f"Failed to launch toolshop: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolshopError(
            f"toolshop {' '.join(args)} timed out after {timeout}s"
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise ToolshopError(
            f"toolshop {' '.join(args)} exited {completed.returncode}: {stderr}"
        )
    return completed.stdout or ""


def analyze_bpm_key(
    audio_path: Path,
    env: Optional[Dict[str, str]] = None,
    runner: Any = subprocess.run,
    timeout: Optional[float] = 600.0,
) -> BpmKeyResult:
    """Run ``toolshop analyze bpm-key --json`` for a single audio file.

    Args:
        audio_path: Path to the audio file Reaper has selected.
        env: Override environment used for CLI resolution. Defaults to ``os.environ``.
        runner: Subprocess runner; injected for tests.
        timeout: Subprocess timeout in seconds.

    Returns:
        Parsed :class:`BpmKeyResult`.

    Raises:
        FileNotFoundError: if ``audio_path`` does not exist.
        ToolshopError: if the CLI is missing or returns a non-zero exit code,
            or if the JSON payload cannot be parsed.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    stdout = _run_toolshop(
        ["analyze", "bpm-key", str(audio_path), "--json"],
        env=env,
        runner=runner,
        timeout=timeout,
    )

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ToolshopError(
            f"Could not parse JSON from toolshop output: {stdout!r}"
        ) from exc

    return BpmKeyResult.from_dict(payload)
