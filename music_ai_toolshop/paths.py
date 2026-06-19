"""Sibling-repo resolver for the umbrella Music AI Toolshop launcher.

Supports three discovery methods, in order:
1. Environment variables MASTERING_TOOL_PATH and OPEN_DAW_PATH.
2. The directory containing the .exe / script (PROJECT_ROOT) and its sibling dirs.
3. Hard-coded fallback to d:\Project layout.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _project_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent.resolve()
    return Path(__file__).parent.parent.resolve()


PROJECT_ROOT = _project_root()


def resolve_mastering_tool() -> Path:
    env = os.environ.get("MASTERING_TOOL_PATH")
    if env:
        p = Path(env).resolve()
        if p.exists():
            return p
    candidates = [
        PROJECT_ROOT / "mastering_tool",
        PROJECT_ROOT.parent / "mastering_tool",
        Path("d:/Project/mastering_tool"),
    ]
    for c in candidates:
        if c.exists() and (c / "tools" / "vocal_restore" / "restore.py").exists():
            return c
    raise FileNotFoundError(
        "Could not find mastering_tool repo. "
        "Set MASTERING_TOOL_PATH or place it as a sibling to the umbrella project."
    )


def resolve_open_daw() -> Path:
    env = os.environ.get("OPEN_DAW_PATH")
    if env:
        p = Path(env).resolve()
        if p.exists():
            return p
    candidates = [
        PROJECT_ROOT / "open_DAW",
        PROJECT_ROOT.parent / "open_DAW",
        Path("d:/Project/open_DAW"),
    ]
    for c in candidates:
        if c.exists() and (c / "ai_modules" / "stem_extractor" / "cli.py").exists():
            return c
    raise FileNotFoundError(
        "Could not find open_DAW repo. "
        "Set OPEN_DAW_PATH or place it as a sibling to the umbrella project."
    )


def get_repo_paths() -> dict[str, Path]:
    return {
        "umbrella": PROJECT_ROOT,
        "mastering_tool": resolve_mastering_tool(),
        "open_daw": resolve_open_daw(),
    }
