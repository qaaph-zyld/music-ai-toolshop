"""Training launcher for LoRA fine-tuning of BS-RoFormer via MSST.

Wraps the MSST train.py script with genre-specific defaults and convenience options.
Requires MSST to be cloned and installed separately.

Usage:
    python -m ai_modules.lora_finetuning.scripts.train --stage 1 --data-path /path/to/dataset
    python -m ai_modules.lora_finetuning.scripts.train --stage 2 --data-path /path/to/mastered --lora-checkpoint results/stage1/lora_best.ckpt
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

CONFIGS = {
    1: Path(__file__).resolve().parent.parent / "configs" / "stage1_genre_clean.yaml",
    2: Path(__file__).resolve().parent.parent / "configs" / "stage2_mastered.yaml",
}

DEFAULT_BASE_CHECKPOINT = "weights/model_bs_roformer_ep_17_sdr_9.6568.ckpt"
DEFAULT_METRICS = ["sdr", "si_sdr", "log_wmse"]
DEFAULT_DEVICE = "0"


def find_msst_root() -> Path | None:
    """Attempt to locate the MSST repository root."""
    candidates = [
        Path(os.environ.get("MSST_ROOT", "")),
        Path.home() / "Music-Source-Separation-Training",
        Path(__file__).resolve().parent.parent.parent / "Music-Source-Separation-Training",
        Path("D:/Music-Source-Separation-Training"),
    ]
    for c in candidates:
        if c and c.exists() and (c / "train.py").exists():
            return c
    return None


def build_train_command(
    msst_root: Path,
    config_path: Path,
    data_paths: list[Path],
    valid_paths: list[Path],
    base_checkpoint: str,
    results_path: Path,
    device_ids: str,
    metrics: list[str],
    metric_for_scheduler: str,
    lora_checkpoint: str | None = None,
    use_peft: bool = False,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build the MSST train.py command line."""
    cmd = [
        sys.executable, str(msst_root / "train.py"),
        "--model_type", "bs_roformer",
        "--config_path", str(config_path),
        "--start_check_point", base_checkpoint,
        "--results_path", str(results_path),
        "--device_ids", device_ids,
        "--metrics", *metrics,
        "--metric_for_scheduler", metric_for_scheduler,
    ]

    for dp in data_paths:
        cmd.extend(["--data_path", str(dp)])
    for vp in valid_paths:
        cmd.extend(["--valid_path", str(vp)])

    if use_peft:
        cmd.append("--train_lora_peft")
    else:
        cmd.append("--train_lora")

    if lora_checkpoint:
        if use_peft:
            cmd.extend(["--lora_checkpoint_peft", lora_checkpoint])
        else:
            cmd.extend(["--lora_checkpoint_loralib", lora_checkpoint])

    if extra_args:
        cmd.extend(extra_args)

    return cmd


def run_training(
    msst_root: Path,
    config_path: Path,
    data_paths: list[Path],
    valid_paths: list[Path],
    base_checkpoint: str,
    results_path: Path,
    device_ids: str,
    metrics: list[str],
    metric_for_scheduler: str,
    lora_checkpoint: str | None = None,
    use_peft: bool = False,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
) -> int:
    """Execute the MSST training command."""
    cmd = build_train_command(
        msst_root, config_path, data_paths, valid_paths,
        base_checkpoint, results_path, device_ids,
        metrics, metric_for_scheduler,
        lora_checkpoint, use_peft, extra_args,
    )

    print("Training command:")
    print(" ".join(cmd))
    print()

    if dry_run:
        print("DRY RUN — not executing")
        return 0

    env = os.environ.copy()
    env["PYTHONPATH"] = str(msst_root) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(cmd, cwd=str(msst_root), env=env)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Launch LoRA fine-tuning via MSST")
    parser.add_argument("--stage", type=int, required=True, choices=[1, 2],
                        help="Training stage: 1=clean genre adaptation, 2=mastered audio adaptation")
    parser.add_argument("--data-path", type=Path, required=True, action="append",
                        help="Path to training dataset (can be specified multiple times)")
    parser.add_argument("--valid-path", type=Path, required=True, action="append",
                        help="Path to validation dataset (can be specified multiple times)")
    parser.add_argument("--base-checkpoint", type=str, default=DEFAULT_BASE_CHECKPOINT,
                        help="Path to pretrained BS-RoFormer checkpoint")
    parser.add_argument("--results-path", type=Path, required=True,
                        help="Directory to store training results")
    parser.add_argument("--lora-checkpoint", type=str, default=None,
                        help="Path to LoRA checkpoint from previous stage (Stage 2)")
    parser.add_argument("--msst-root", type=Path, default=None,
                        help="Path to MSST repository root (auto-detected if not specified)")
    parser.add_argument("--config", type=Path, default=None,
                        help="Override config path (defaults to stage-specific config)")
    parser.add_argument("--device-ids", type=str, default=DEFAULT_DEVICE,
                        help="GPU device IDs (e.g., '0' or '0,1')")
    parser.add_argument("--metrics", nargs="+", default=DEFAULT_METRICS,
                        help="Evaluation metrics")
    parser.add_argument("--metric-for-scheduler", type=str, default="sdr",
                        help="Metric used for learning rate scheduler")
    parser.add_argument("--use-peft", action="store_true",
                        help="Use HuggingFace PEFT LoRA backend instead of loralib")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print command without executing")
    parser.add_argument("--extra-args", nargs=argparse.REMAINDER,
                        help="Extra arguments to pass to MSST train.py")

    args = parser.parse_args()

    msst_root = args.msst_root or find_msst_root()
    if msst_root is None or not msst_root.exists():
        print("ERROR: MSST repository not found. Please specify --msst-root or set MSST_ROOT env var.",
              file=sys.stderr)
        print("Clone MSST: git clone https://github.com/ZFTurbo/Music-Source-Separation-Training.git",
              file=sys.stderr)
        sys.exit(1)

    config_path = args.config or CONFIGS[args.stage]

    if args.stage == 2 and not args.lora_checkpoint:
        print("WARNING: Stage 2 without --lora-checkpoint will start from base model only.", file=sys.stderr)

    rc = run_training(
        msst_root=msst_root,
        config_path=config_path,
        data_paths=args.data_path,
        valid_paths=args.valid_path,
        base_checkpoint=args.base_checkpoint,
        results_path=args.results_path,
        device_ids=args.device_ids,
        metrics=args.metrics,
        metric_for_scheduler=args.metric_for_scheduler,
        lora_checkpoint=args.lora_checkpoint,
        use_peft=args.use_peft,
        extra_args=args.extra_args,
        dry_run=args.dry_run,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
