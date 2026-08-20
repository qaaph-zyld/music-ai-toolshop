#!/usr/bin/env python3
"""Wan 2.2 I2V dual-expert LoRA training script using musubi-tuner.

Trains two LoRAs matching Wan 2.2's Mixture-of-Experts architecture:
  - High-noise expert (timestep > 0.9): composition/motion
  - Low-noise expert (timestep < 0.9): texture/identity

Both LoRAs are saved as .safetensors and loaded together at inference.

Optionally supports three-stage training (high/mid/low noise) via --stages 3.

Usage:
    # Two-stage (default, matches MoE architecture)
    python train_wan_lora.py --dataset /workspace/dataset/video_clips --output /workspace/models/wan_lora

    # Three-stage (advanced, adds mid-noise motion refinement)
    python train_wan_lora.py --dataset /workspace/dataset/video_clips --output /workspace/models/wan_lora --stages 3

    # Budget GPU (5B model on RTX 4090)
    python train_wan_lora.py --dataset /workspace/dataset/video_clips --output /workspace/models/wan_lora --model /workspace/models/Wan2.2-TI2V-5B --fp8
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# Wan 2.2 MoE timestep boundaries
# I2V: high-noise expert active for t > 0.9, low-noise for t < 0.9
# Three-stage splits low-noise into mid (0.5-0.9) and low (0.0-0.5)
TWO_STAGE_BOUNDARIES = {
    "high": (0.9, 1.0),
    "low": (0.0, 0.9),
}

THREE_STAGE_BOUNDARIES = {
    "high": (0.9, 1.0),
    "mid": (0.5, 0.9),
    "low": (0.0, 0.5),
}

EXPERT_DESCRIPTIONS = {
    "high": "composition/motion (high-noise expert)",
    "mid": "motion refinement (mid-noise adapter)",
    "low": "texture/identity (low-noise expert)",
}


def generate_toml(
    dataset_dir: str,
    output_path: str,
    resolution: list[int] = [480, 720],
    frame_count: int = 12,
    batch_size: int = 1,
    num_repeats: int = 10,
) -> str:
    """Generate musubi-tuner dataset config TOML from video clip directory."""
    toml_content = f"""[general]
resolution = {resolution}
frame_bucket = {frame_count}
shuffle_caption = true
keep_tokens = 1

[[datasets]]
batch_size = {batch_size}
enable_bucket = false

  [[datasets.subsets]]
  image_dir = "{dataset_dir}"
  caption_extension = ".txt"
  num_repeats = {num_repeats}
"""
    with open(output_path, "w") as f:
        f.write(toml_content)
    print(f"Generated dataset config: {output_path}")
    return output_path


def validate_dataset(dataset_dir: str) -> bool:
    """Validate video clip dataset directory structure."""
    videos = (
        list(Path(dataset_dir).glob("*.mp4"))
        + list(Path(dataset_dir).glob("*.avi"))
        + list(Path(dataset_dir).glob("*.mov"))
        + list(Path(dataset_dir).glob("*.mkv"))
    )
    captions = list(Path(dataset_dir).glob("*.txt"))

    if len(videos) < 10:
        print(f"ERROR: Need at least 10 video clips, found {len(videos)}")
        print("  For character LoRA, 10-20 clips of 2-5 seconds each is recommended.")
        print("  See models/wan_lora/README.md for dataset preparation guide.")
        return False

    if len(captions) < len(videos):
        missing = len(videos) - len(captions)
        print(f"ERROR: {missing} video clips missing caption files")
        print("  Each video needs a .txt file with the same basename.")
        return False

    for cap in captions:
        text = cap.read_text().strip().lower()
        if not text.startswith("ohwx person") and not text.startswith("zjk person"):
            print(f"WARNING: Caption {cap.name} doesn't start with expected trigger word")

    print(f"Dataset OK: {len(videos)} video clips, {len(captions)} captions")
    return True


def build_training_command(
    args,
    expert_name: str,
    t_min: float,
    t_max: float,
    output_subdir: str,
) -> list[str]:
    """Build musubi-tuner wan_train_network.py command for one expert."""
    cmd = [
        "accelerate", "launch",
        "--mixed_precision=bf16",
        "wan_train_network.py",
        f"--task={args.task}",
        f"--pretrained_model_name_or_path={args.model}",
        f"--dataset_config={args.dataset_config}",
        f"--output_dir={output_subdir}",
        f"--train_batch_size={args.batch_size}",
        f"--gradient_accumulation_steps={args.grad_accum}",
        f"--learning_rate={args.lr}",
        f"--lr_scheduler={args.lr_scheduler}",
        f"--lr_warmup_steps={args.warmup_steps}",
        f"--max_train_steps={args.steps}",
        "--save_model_as=safetensors",
        "--save_precision=bf16",
        f"--network_dim={args.rank}",
        f"--network_alpha={args.alpha}",
        "--network_train_unet_only",
        "--cache_text_encoder_outputs",
        "--cache_latents",
        f"--timestep_sampling={args.timestep_sampling}",
        f"--min_timestep={int(t_min * 1000)}",
        f"--max_timestep={int(t_max * 1000)}",
        f"--seed={args.seed}",
        f"--frame_sample_count={args.frames}",
    ]

    if args.fp8:
        cmd.append("--fp8")
        cmd.append(f"--blocks_to_swap={args.blocks_swap}")

    if args.optimizer == "came":
        cmd.extend([
            "--optimizer_type=CAME",
            "--lora_plus_lr_ratio=4",
        ])
    elif args.optimizer == "adamw8bit":
        cmd.extend([
            "--optimizer_type=AdamW8bit",
        ])
    else:
        cmd.extend([
            "--optimizer_type=AdamW",
        ])

    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Train Wan 2.2 I2V dual-expert LoRA using musubi-tuner"
    )
    parser.add_argument("--dataset", help="Video clips directory with .mp4 + .txt captions")
    parser.add_argument("--dataset-config", help="Path to existing musubi-tuner dataset TOML")
    parser.add_argument("--output", required=True, help="Output directory for LoRA weights")
    parser.add_argument("--model", default="/workspace/models/Wan2.2-I2V-A14B",
                        help="Path to Wan 2.2 model (A14B or 5B)")
    parser.add_argument("--task", default="i2v", choices=["i2v", "t2v"],
                        help="Wan task type")
    parser.add_argument("--stages", type=int, default=2, choices=[2, 3],
                        help="Training stages: 2 (dual-expert, default) or 3 (high/mid/low)")
    parser.add_argument("--resolution", type=int, nargs=2, default=[480, 720],
                        help="Training resolution (height width)")
    parser.add_argument("--frames", type=int, default=12,
                        help="Frames per training sample (8-16, 12 recommended)")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=str, default="2e-5",
                        help="Learning rate (2e-5 recommended for Wan)")
    parser.add_argument("--lr-scheduler", default="cosine_with_restarts",
                        help="LR scheduler")
    parser.add_argument("--warmup-steps", type=int, default=200, help="LR warmup steps")
    parser.add_argument("--steps", type=int, default=2000, help="Max training steps per expert")
    parser.add_argument("--rank", type=int, default=32,
                        help="LoRA rank (32-64 for characters)")
    parser.add_argument("--alpha", type=int, default=16,
                        help="LoRA alpha (rank//2 or rank)")
    parser.add_argument("--optimizer", choices=["came", "adamw", "adamw8bit"],
                        default="came",
                        help="Optimizer (CAME + LoRAPlus recommended for Wan)")
    parser.add_argument("--timestep-sampling", default="logit-normal",
                        help="Timestep sampling strategy")
    parser.add_argument("--fp8", action="store_true",
                        help="Use FP8 weights + block swap (for 24GB VRAM)")
    parser.add_argument("--blocks-swap", type=int, default=20,
                        help="Number of blocks to swap to CPU when --fp8 (20 for 24GB)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without executing")
    args = parser.parse_args()

    if not args.dataset and not args.dataset_config:
        parser.error("Either --dataset or --dataset-config is required")

    # Resolve dataset config
    if args.dataset_config:
        args.dataset_config = os.path.abspath(args.dataset_config)
        if not os.path.exists(args.dataset_config):
            print(f"ERROR: Dataset config not found: {args.dataset_config}")
            sys.exit(1)
    else:
        if not validate_dataset(args.dataset):
            sys.exit(1)
        toml_path = os.path.join(args.dataset, "wan_dataset_config.toml")
        generate_toml(args.dataset, toml_path, args.resolution, args.frames,
                      args.batch_size)
        args.dataset_config = toml_path

    os.makedirs(args.output, exist_ok=True)

    # Determine stage boundaries
    if args.stages == 2:
        boundaries = TWO_STAGE_BOUNDARIES
    else:
        boundaries = THREE_STAGE_BOUNDARIES

    # Build commands for each expert stage
    commands = []
    for expert_name, (t_min, t_max) in boundaries.items():
        output_subdir = os.path.join(args.output, f"{expert_name}_noise")
        os.makedirs(output_subdir, exist_ok=True)
        cmd = build_training_command(args, expert_name, t_min, t_max, output_subdir)
        commands.append((expert_name, cmd, output_subdir))

    # Print summary
    print("\n" + "=" * 60)
    print(f"WAN 2.2 DUAL-EXPERT LoRA TRAINING ({args.stages}-stage)")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Model: {args.model}")
    print(f"  Task: {args.task}")
    print(f"  Dataset config: {args.dataset_config}")
    print(f"  Output: {args.output}")
    print(f"  Resolution: {args.resolution[0]}x{args.resolution[1]}")
    print(f"  Frames per sample: {args.frames}")
    print(f"  Rank: {args.rank} (alpha: {args.alpha})")
    print(f"  LR: {args.lr} ({args.lr_scheduler})")
    print(f"  Steps per expert: {args.steps}")
    print(f"  Optimizer: {args.optimizer}")
    print(f"  FP8: {args.fp8}" + (f" (blocks_swap={args.blocks_swap})" if args.fp8 else ""))
    print(f"  Stages: {args.stages}")
    print()

    for expert_name, cmd, output_subdir in commands:
        t_min, t_max = boundaries[expert_name]
        print(f"  [{expert_name.upper}] t=[{t_min:.2f}, {t_max:.2f}] — {EXPERT_DESCRIPTIONS[expert_name]}")
        print(f"    Output: {output_subdir}/pytorch_lora_weights.safetensors")
        print(f"    Command: {' '.join(cmd)}")
        print()

    if args.dry_run:
        print("Dry run — not executing training")
        return

    # Execute training for each expert sequentially
    musubi_dir = "/workspace/musubi-tuner"
    if not os.path.exists(musubi_dir):
        print(f"ERROR: musubi-tuner not found at {musubi_dir}")
        print("Install it with:")
        print("  cd /workspace && git clone https://github.com/kohya-ss/musubi-tuner.git")
        print("  cd musubi-tuner && pip install -r requirements.txt")
        sys.exit(1)

    failed = False
    for expert_name, cmd, output_subdir in commands:
        t_min, t_max = boundaries[expert_name]
        print("\n" + "=" * 60)
        print(f"TRAINING: {expert_name.upper()} NOISE EXPERT")
        print(f"  Timestep range: [{t_min:.2f}, {t_max:.2f}]")
        print(f"  {EXPERT_DESCRIPTIONS[expert_name]}")
        print("=" * 60)

        result = subprocess.run(cmd, cwd=musubi_dir)

        if result.returncode == 0:
            lora_path = os.path.join(output_subdir, "pytorch_lora_weights.safetensors")
            print(f"\n  {expert_name.upper()} expert training complete!")
            print(f"  LoRA weights: {lora_path}")
        else:
            print(f"\n  {expert_name.upper()} expert training FAILED (exit code {result.returncode})")
            failed = True
            break

    if failed:
        print("\nTraining aborted due to failure. See logs above.")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    print("ALL EXPERTS TRAINED SUCCESSFULLY")
    print("=" * 60)
    for expert_name, _, output_subdir in commands:
        lora_path = os.path.join(output_subdir, "pytorch_lora_weights.safetensors")
        print(f"  {expert_name}: {lora_path}")

    print(f"\nNext steps:")
    print(f"  1. Validate: python /workspace/scripts/validate_wan_lora.py \\")
    print(f"       --high-noise-lora {os.path.join(commands[0][2], 'pytorch_lora_weights.safetensors')} \\")
    if args.stages == 2:
        print(f"       --low-noise-lora {os.path.join(commands[1][2], 'pytorch_lora_weights.safetensors')} \\")
    else:
        print(f"       --mid-noise-lora {os.path.join(commands[1][2], 'pytorch_lora_weights.safetensors')} \\")
        print(f"       --low-noise-lora {os.path.join(commands[2][2], 'pytorch_lora_weights.safetensors')} \\")
    print(f"       --reference /workspace/dataset/video_clips --output /workspace/output/test_clips")
    print(f"  2. If identity similarity < 0.7, adjust hyperparameters (see models/wan_lora/README.md)")
    print(f"  3. If similarity >= 0.7, load both LoRAs at inference for video generation")


if __name__ == "__main__":
    main()
