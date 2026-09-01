"""Provider registry for optional backends.
Backends are optional and loaded lazily.

This module exposes small helpers to detect whether optional components are
available at runtime. Use these to toggle UI options or choose fallbacks.
"""

from __future__ import annotations

from typing import Optional
import shutil


def has_chordino() -> bool:
    """Return True if Sonic Annotator (Chordino Vamp) is likely available."""
    return shutil.which('sonic-annotator') is not None


def has_torchcrepe() -> bool:
    try:
        import torch  # noqa: F401
        import torchcrepe  # noqa: F401
        return True
    except Exception:
        return False


def has_demucs() -> bool:
    try:
        import torch  # noqa: F401
        import demucs  # noqa: F401
        return True
    except Exception:
        return False


def has_essentia() -> bool:
    try:
        import essentia.standard  # noqa: F401
        return True
    except Exception:
        return False


def has_panns() -> bool:
    try:
        import torch  # noqa: F401
        import panns_inference  # noqa: F401
        return True
    except Exception:
        return False


def has_spleeter() -> bool:
    try:
        import spleeter  # noqa: F401
        return True
    except Exception:
        return False


def has_madmom() -> bool:
    try:
        import madmom  # noqa: F401
        return True
    except Exception:
        return False

