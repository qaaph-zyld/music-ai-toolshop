"""Dataset preparation utilities for LoRA fine-tuning pipeline.

Organizes genre-specific tracks with stems into MSST-compatible directory structures:
- Type 1 (MUSDB format): per-song folders with stem WAVs + mixture.wav
- Type 6 (MUSDB Aligned + Explicit Mixture): same but with explicit mixture.wav

Also provides a mastering degradation pipeline for generating Stage 2 training data.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

STEM_NAMES = ["vocals", "drums", "bass", "other"]
SAMPLE_RATE = 44100


def organize_to_type1(
    source_dir: Path,
    output_dir: Path,
    train_split: float = 0.8,
    seed: int = 42,
) -> dict:
    """Organize raw stem files into MSST Type 1 (MUSDB) format.

    Expects source_dir to contain subdirectories per track, each with
    stem WAV files named {stem}.wav (e.g., vocals.wav, drums.wav, ...).

    Produces output_dir/train/ and output_dir/val/ with per-song folders
    containing stem WAVs + a computed mixture.wav.
    """
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    track_dirs = sorted([
        d for d in source_dir.iterdir()
        if d.is_dir() and any(d.glob(f"{s}.wav") for s in STEM_NAMES)
    ])

    if not track_dirs:
        print(f"No valid track directories found in {source_dir}", file=sys.stderr)
        return {"train": 0, "val": 0}

    random.shuffle(track_dirs)
    split_idx = int(len(track_dirs) * train_split)
    train_dirs = track_dirs[:split_idx]
    val_dirs = track_dirs[split_idx:]

    for split_name, dirs in [("train", train_dirs), ("val", val_dirs)]:
        split_dir = output_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        for track_dir in dirs:
            dest = split_dir / track_dir.name
            dest.mkdir(parents=True, exist_ok=True)

            stems = {}
            for stem_name in STEM_NAMES:
                src = track_dir / f"{stem_name}.wav"
                if src.exists():
                    dst = dest / f"{stem_name}.wav"
                    shutil.copy2(src, dst)
                    audio, sr = sf.read(str(dst), dtype="float32")
                    if sr != SAMPLE_RATE:
                        print(f"WARNING: {src} has SR={sr}, expected {SAMPLE_RATE}", file=sys.stderr)
                    stems[stem_name] = audio

            if stems:
                min_len = min(a.shape[0] for a in stems.values())
                mixture = np.zeros((min_len, 2) if stems[list(stems.keys())[0]].ndim == 2 else (min_len,), dtype="float32")
                for audio in stems.values():
                    mixture[:min_len] += audio[:min_len]
                sf.write(str(dest / "mixture.wav"), mixture, SAMPLE_RATE)

    print(f"Organized {len(train_dirs)} train / {len(val_dirs)} val tracks into {output_dir}")
    return {"train": len(train_dirs), "val": len(val_dirs)}


def apply_mastering_degradation(
    input_path: Path,
    output_path: Path,
    sr: int = SAMPLE_RATE,
) -> None:
    """Apply a simulated mastering chain to a stem file using pedalboard.

    Chain: EQ -> Compression -> Saturation -> Stereo Width -> Limiter
    """
    try:
        from pedalboard import (
            Pedalboard,
            HighpassFilter,
            Compressor,
            Gain,
            Limiter,
        )
    except ImportError:
        print("pedalboard not installed — copying file without degradation", file=sys.stderr)
        shutil.copy2(input_path, output_path)
        return

    audio, file_sr = sf.read(str(input_path), dtype="float32")
    if file_sr != sr:
        print(f"WARNING: {input_path} has SR={file_sr}, expected {sr}", file=sys.stderr)

    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)

    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=30.0),
        Compressor(threshold_db=-12.0, ratio=3.0, attack_ms=5.0, release_ms=100.0),
        Gain(gain_db=2.0),
        Limiter(threshold_db=-1.0, release_ms=50.0),
    ])

    processed = board(audio, sr)
    sf.write(str(output_path), processed, sr)


def prepare_mastered_dataset(
    clean_dataset_dir: Path,
    output_dir: Path,
    train_split: float = 0.8,
    seed: int = 42,
) -> dict:
    """Prepare a mastered dataset from clean stems for Stage 2 training.

    Takes a Type 1 dataset (clean stems), applies per-stem mastering degradation,
    and creates a Type 6 dataset with explicit mixture.wav (the mastered mix).

    The mastered mixture is created by summing the degraded stems (not the clean stems),
    simulating real-world mastering where the mix differs from sum(clean stems).
    """
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    for split_name in ["train", "val"]:
        split_src = clean_dataset_dir / split_name
        if not split_src.exists():
            continue

        split_dst = output_dir / split_name
        split_dst.mkdir(parents=True, exist_ok=True)

        track_dirs = sorted([d for d in split_src.iterdir() if d.is_dir()])

        for track_dir in track_dirs:
            dest = split_dst / track_dir.name
            dest.mkdir(parents=True, exist_ok=True)

            degraded_stems = {}
            for stem_name in STEM_NAMES:
                src = track_dir / f"{stem_name}.wav"
                if src.exists():
                    dst = dest / f"{stem_name}.wav"
                    apply_mastering_degradation(src, dst, SAMPLE_RATE)
                    degraded_stems[stem_name] = dst

            if degraded_stems:
                stems_audio = []
                for stem_name in STEM_NAMES:
                    stem_path = dest / f"{stem_name}.wav"
                    if stem_path.exists():
                        audio, _ = sf.read(str(stem_path), dtype="float32")
                        if audio.ndim == 1:
                            audio = np.stack([audio, audio], axis=1)
                        stems_audio.append(audio)

                min_len = min(a.shape[0] for a in stems_audio)
                mastered_mix = np.zeros((min_len, 2), dtype="float32")
                for audio in stems_audio:
                    mastered_mix[:min_len] += audio[:min_len]

                sf.write(str(dest / "mixture.wav"), mastered_mix, SAMPLE_RATE)

    train_count = len(list((output_dir / "train").iterdir())) if (output_dir / "train").exists() else 0
    val_count = len(list((output_dir / "val").iterdir())) if (output_dir / "val").exists() else 0
    print(f"Prepared mastered dataset: {train_count} train / {val_count} val tracks")
    return {"train": train_count, "val": val_count}


def validate_dataset(dataset_dir: Path, dataset_type: int = 1) -> bool:
    """Validate that a dataset directory conforms to MSST Type 1 or Type 6 format.

    Type 1: per-song folders with stem WAVs + mixture.wav
    Type 6: same as Type 1 but mixture.wav is required (not computed)
    """
    issues = []
    for split_name in ["train", "val"]:
        split_dir = dataset_dir / split_name
        if not split_dir.exists():
            issues.append(f"Missing {split_name}/ directory")
            continue

        track_dirs = [d for d in split_dir.iterdir() if d.is_dir()]
        if not track_dirs:
            issues.append(f"No track directories in {split_name}/")
            continue

        for track_dir in track_dirs:
            for stem_name in STEM_NAMES:
                stem_path = track_dir / f"{stem_name}.wav"
                if not stem_path.exists():
                    issues.append(f"Missing {stem_name}.wav in {track_dir.name}")

            mix_path = track_dir / "mixture.wav"
            if dataset_type == 6 and not mix_path.exists():
                issues.append(f"Missing mixture.wav in {track_dir.name} (required for Type 6)")

            if mix_path.exists():
                _, sr = sf.read(str(mix_path))
                if sr != SAMPLE_RATE:
                    issues.append(f"{track_dir.name}/mixture.wav has SR={sr}, expected {SAMPLE_RATE}")

    if issues:
        print(f"Dataset validation FAILED with {len(issues)} issues:", file=sys.stderr)
        for issue in issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more", file=sys.stderr)
        return False

    print("Dataset validation PASSED")
    return True


def main():
    parser = argparse.ArgumentParser(description="Prepare datasets for LoRA fine-tuning")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_organize = subparsers.add_parser("organize", help="Organize raw stems into Type 1 format")
    p_organize.add_argument("--source", type=Path, required=True, help="Source directory with raw track folders")
    p_organize.add_argument("--output", type=Path, required=True, help="Output directory for Type 1 dataset")
    p_organize.add_argument("--train-split", type=float, default=0.8)
    p_organize.add_argument("--seed", type=int, default=42)

    p_master = subparsers.add_parser("master", help="Create mastered dataset from clean Type 1 dataset")
    p_master.add_argument("--clean-dir", type=Path, required=True, help="Clean Type 1 dataset directory")
    p_master.add_argument("--output", type=Path, required=True, help="Output directory for mastered dataset")
    p_master.add_argument("--train-split", type=float, default=0.8)
    p_master.add_argument("--seed", type=int, default=42)

    p_validate = subparsers.add_parser("validate", help="Validate dataset format")
    p_validate.add_argument("--dataset-dir", type=Path, required=True)
    p_validate.add_argument("--type", type=int, default=1, choices=[1, 6])

    args = parser.parse_args()

    if args.command == "organize":
        result = organize_to_type1(args.source, args.output, args.train_split, args.seed)
        print(json.dumps(result, indent=2))
    elif args.command == "master":
        result = prepare_mastered_dataset(args.clean_dir, args.output, args.train_split, args.seed)
        print(json.dumps(result, indent=2))
    elif args.command == "validate":
        success = validate_dataset(args.dataset_dir, args.type)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
