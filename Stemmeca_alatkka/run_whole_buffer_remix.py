#!/usr/bin/env python3
"""Run the 2Pac drill flip with whole-buffer time-stretching."""
import sys
sys.path.insert(0, r"D:\Projects\Music-AI-Toolshop")
from pathlib import Path
from toolshop.remix_adapter import create_remix

stems_dir = Path(r"D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\htdemucs_6s\2Pac - Only God Can Judge Me")

result = create_remix(
    input_path=stems_dir / "drums.wav",
    output_path=Path(r"D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\2pac_drill_flip_whole.wav"),
    target_bpm=87.0,
    target_key="Gm",
    mode="remix",
    fx_chain=["reverb", "distortion", "compressor"],
    max_duration=300.0,
    source_bpm=89.1,
    source_key="A",
    output_format="wav",
    stems_dir=stems_dir,
    whole_buffer=True,
)
print(f"Remix created: {result.output_file}")
print(f"  Source BPM: {result.bpm}, Key: {result.key}")
print(f"  Target BPM: {result.target_bpm}, Key: {result.target_key}")
print(f"  FX: {result.fx_chain}")
print(f"  Duration: {result.duration_seconds}s")
print(f"  Manifest: {result.manifest_path}")
