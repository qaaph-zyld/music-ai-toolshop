#!/usr/bin/env python3
"""Flux.1-dev DreamBooth LoRA training script using Kohya_ss (sd-scripts).

This is a wrapper script that prepares the training command and can be
run on a RunPod A100 instance. The actual training is done by Kohya_ss's
flux_train_network.py.

Usage:
    python train_flux_lora.py --dataset /workspace/dataset/processed --output /workspace/models/flux_lora
    python train_flux_lora.py --dataset /workspace/dataset/processed --output /workspace/models/flux_lora --rank 128 --lr 5e-5 --steps 1500
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def validate_dataset(dataset_dir: str) -> bool:
    """Validate dataset directory structure."""
    images = list(Path(dataset_dir).glob("*.png")) + list(Path(dataset_dir).glob("*.jpg"))
    captions = list(Path(dataset_dir).glob("*.txt"))
    
    if len(images) < 10:
        print(f"ERROR: Need at least 10 images, found {len(images)}")
        return False
    
    if len(captions) < len(images):
        missing = len(images) - len(captions)
        print(f"ERROR: {missing} images missing caption files")
        return False
    
    # Check all captions start with trigger word
    for cap in captions:
        text = cap.read_text().strip().lower()
        if not text.startswith("ohwx person") and not text.startswith("zjk person"):
            print(f"WARNING: Caption {cap.name} doesn't start with expected trigger word")
    
    print(f"Dataset OK: {len(images)} images, {len(captions)} captions")
    return True


def build_training_command(args) -> list[str]:
    """Build the Kohya_ss flux_train_network.py command."""
    cmd = [
        "accelerate", "launch",
        "--mixed_precision=bf16",
        "flux_train_network.py",
        f"--pretrained_model_name_or_path={args.model}",
        f"--train_data_dir={args.dataset}",
        f"--output_dir={args.output}",
        f"--instance_prompt={args.trigger_word}",
        f"--resolution={args.resolution}",
        f"--train_batch_size={args.batch_size}",
        f"--gradient_accumulation_steps={args.grad_accum}",
        f"--learning_rate={args.lr}",
        f"--lr_scheduler={args.lr_scheduler}",
        f"--lr_warmup_steps={args.warmup_steps}",
        f"--max_train_steps={args.steps}",
        f"--save_every_n_epochs=1",
        "--mixed_precision=bf16",
        "--save_model_as=safetensors",
        "--network_module=networks.lora_flux",
        f"--network_dim={args.rank}",
        f"--network_alpha={args.alpha}",
        "--network_train_unet_only",
        "--cache_text_encoder_outputs",
        "--cache_latents",
        f"--seed={args.seed}",
    ]
    
    if args.optimizer == "prodigy":
        cmd.extend([
            "--optimizer_type=Prodigy",
            "--prodigy_safetensors=True",
        ])
    else:
        cmd.extend([
            "--optimizer_type=AdamW",
        ])
    
    return cmd


def main():
    parser = argparse.ArgumentParser(description="Train Flux.1-dev DreamBooth LoRA")
    parser.add_argument("--dataset", required=True, help="Dataset directory with images + captions")
    parser.add_argument("--output", required=True, help="Output directory for LoRA weights")
    parser.add_argument("--model", default="/workspace/models/FLUX.1-dev", help="Path to Flux.1-dev model")
    parser.add_argument("--trigger-word", default="ohwx person", help="Trigger word for LoRA")
    parser.add_argument("--resolution", type=int, default=1024, help="Training resolution")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=str, default="1e-4", help="Learning rate")
    parser.add_argument("--lr-scheduler", default="constant", help="LR scheduler")
    parser.add_argument("--warmup-steps", type=int, default=0, help="LR warmup steps")
    parser.add_argument("--steps", type=int, default=1000, help="Max training steps")
    parser.add_argument("--rank", type=int, default=64, help="LoRA rank (network_dim)")
    parser.add_argument("--alpha", type=int, default=32, help="LoRA alpha (network_alpha)")
    parser.add_argument("--optimizer", choices=["adamw", "prodigy"], default="adamw", help="Optimizer")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--dry-run", action="store_true", help="Print command without executing")
    args = parser.parse_args()
    
    # Validate dataset
    if not validate_dataset(args.dataset):
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Build command
    cmd = build_training_command(args)
    
    print("\n" + "=" * 60)
    print("TRAINING COMMAND")
    print("=" * 60)
    print(" ".join(cmd))
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Model: {args.model}")
    print(f"  Dataset: {args.dataset}")
    print(f"  Output: {args.output}")
    print(f"  Rank: {args.rank} (alpha: {args.alpha})")
    print(f"  LR: {args.lr} ({args.lr_scheduler})")
    print(f"  Steps: {args.steps}")
    print(f"  Optimizer: {args.optimizer}")
    print(f"  Resolution: {args.resolution}")
    print()
    
    if args.dry_run:
        print("Dry run — not executing training")
        return
    
    # Run training
    print("Starting training...")
    result = subprocess.run(cmd, cwd="/workspace/sd-scripts")
    
    if result.returncode == 0:
        print(f"\n✓ Training complete!")
        print(f"  LoRA weights: {args.output}/pytorch_lora_weights.safetensors")
        print(f"\nNext steps:")
        print(f"  1. Validate identity: python /workspace/scripts/validate_identity.py --reference {args.dataset} --generated <test_images> --threshold 0.7")
        print(f"  2. If similarity < 0.7, retry with adjusted hyperparameters")
        print(f"  3. If similarity ≥ 0.7, proceed to reference image generation")
    else:
        print(f"\n✗ Training failed (exit code {result.returncode})")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
