"""MAirina Tucc v1: anchor sets and a rhyme finder that learns.

Product rule: the tool finds, it never writes.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # .../MAirina_Tucc
REPO = ROOT.parent                                     # .../Music-AI-Toolshop
DATA_DIR = ROOT / "data"
DEFAULT_LYRICS_DB = REPO / "data" / "toolshop" / "lyrics" / "lyrics.db"
RANKER_VERSION = "v1"

# `toolshop` is normally importable from the venv; fall back to the repo root.
try:
    import toolshop  # noqa: F401
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(REPO))

LANES = ("drill", "pop", "all")
