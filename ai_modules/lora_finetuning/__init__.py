"""LoRA Fine-Tuning Pipeline for BS-RoFormer / Demucs on Mastered Commercial Audio.

Provides dataset preparation, training configuration, and evaluation utilities
for genre-specific LoRA adaptation of music source separation models via MSST.
"""

from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent
CONFIGS_DIR = PIPELINE_ROOT / "configs"
SCRIPTS_DIR = PIPELINE_ROOT / "scripts"

__all__ = ["PIPELINE_ROOT", "CONFIGS_DIR", "SCRIPTS_DIR"]
