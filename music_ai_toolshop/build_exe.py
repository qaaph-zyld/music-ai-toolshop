#!/usr/bin/env python3
"""Build a single-file Windows EXE for the Music AI Toolshop launcher."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).parent.resolve()
    umbrella = root.parent
    launcher = root / "launcher.py"
    spec = root / "build" / "launcher.spec"

    # Clean previous build artifacts.
    for d in (root / "build", root / "dist"):
        if d.exists():
            shutil.rmtree(d)
    exe = umbrella / "MusicAIToolshop.exe"
    if exe.exists():
        exe.unlink()

    # Run PyInstaller from the umbrella repo so relative paths resolve correctly.
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "MusicAIToolshop",
        "--distpath", str(umbrella),
        "--workpath", str(root / "build"),
        "--specpath", str(root / "build"),
        "--add-data", f"{root / 'icon.png'};.",
        str(launcher),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(umbrella))
    if result.returncode != 0:
        return result.returncode

    # Move the EXE to the umbrella root.
    built = umbrella / "MusicAIToolshop.exe"
    if built.exists():
        print(f"Built: {built}")
    else:
        print("ERROR: EXE not found after build.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
