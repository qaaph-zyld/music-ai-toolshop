"""Make the repo root importable under bare `pytest` in any worktree.

`python -m pytest` puts cwd on sys.path; bare `pytest` does not, and the
editable install only exposes declared packages (toolshop) — never `scripts/`.
Without this file a lane's tests would import the MAIN checkout's scripts/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
