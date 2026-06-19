#!/usr/bin/env python3
"""One-shot dev environment setup for Music AI Toolshop."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).parent.resolve()
    req = root / "requirements.txt"
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)], check=True)

    import flask, pystray, PIL, requests  # noqa: F401
    print("Dependencies OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
