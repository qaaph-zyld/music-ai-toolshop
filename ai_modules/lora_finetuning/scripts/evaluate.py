"""Evaluation and inference launcher for LoRA-adapted BS-RoFormer via MSST.

Wraps the MSST valid.py and inference.py scripts with LoRA checkpoint support.

Usage:
    python -m ai_modules.lora_finetuning.scripts.evaluate --valid-path /path/to/val --lora-checkpoint results/stage2/lora_best.ckpt
    python -m ai_modules.lora_finetuning.scripts.infer --input-folder /path/to/tracks --lora-checkpoint results/stage2/lora_best.ckpt
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
ALL_METRICS = ["sdr", "si_sdr", "log_wmse", "aura_stft", "aura_mrstft", "l1_freq"]


def find_msst_root() -> Path | None:
    """Attempt to locate the MSST repository root."""
    candidates = [
        Path(os.environ.get("MSST_ROOT", "")),
        Path.home() / "Music-Source-Separation-Training",
        Path(__file__).resolve().parent.parent.parent / "Music-Source-Separation-Training",
        Path("D:/Music-Source-Separation-Training"),
    ]
    for c in candidates:
        if c and c.exists() and (c / "valid.py").exists():
            return c
    return None


def run_validation(
    msst_root: Path,
    config_path: Path,
    valid_paths: list[Path],
    base_checkpoint: str,
    lora_checkpoint: str | None,
    store_dir: Path,
    device_ids: str,
    metrics: list[str],
    use_tta: bool = False,
    use_peft: bool = False,
    dry_run: bool = False,
) -> int:
    """Execute MSST valid.py with LoRA checkpoint."""
    cmd = [
        sys.executable, str(msst_root / "valid.py"),
        "--model_type", "bs_roformer",
        "--config_path", str(config_path),
        "--start_check_point", base_checkpoint,
        "--store_dir", str(store_dir),
        "--device_ids", device_ids,
        "--metrics", *metrics,
    ]

    for vp in valid_paths:
        cmd.extend(["--valid_path", str(vp)])

    if lora_checkpoint:
        if use_peft:
            cmd.extend(["--lora_checkpoint_peft", lora_checkpoint])
        else:
            cmd.extend(["--lora_checkpoint_loralib", lora_checkpoint])

    if use_tta:
        cmd.append("--use_tta")

    print("Validation command:")
    print(" ".join(cmd))
    print()

    if dry_run:
        print("DRY RUN — not executing")
        return 0

    env = os.environ.copy()
    env["PYTHONPATH"] = str(msst_root) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(cmd, cwd=str(msst_root), env=env)
    return result.returncode


def run_inference(
    msst_root: Path,
    config_path: Path,
    input_folder: Path,
    base_checkpoint: str,
    lora_checkpoint: str | None,
    store_dir: Path,
    device_ids: str,
    use_peft: bool = False,
    dry_run: bool = False,
) -> int:
    """Execute MSST inference.py with LoRA checkpoint."""
    cmd = [
        sys.executable, str(msst_root / "inference.py"),
        "--model_type", "bs_roformer",
        "--config_path", str(config_path),
        "--start_check_point", base_checkpoint,
        "--store_dir", str(store_dir),
        "--input_folder", str(input_folder),
        "--device_ids", device_ids,
    ]

    if lora_checkpoint:
        if use_peft:
            cmd.extend(["--lora_checkpoint_peft", lora_checkpoint])
        else:
            cmd.append("--lora_checkpoint")
            cmd.append(lora_checkpoint)

    print("Inference command:")
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
    parser = argparse.ArgumentParser(description="Evaluate/infer with LoRA-adapted BS-RoFormer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Validation subcommand
    p_val = subparsers.add_parser("validate", help="Run validation with metrics")
    p_val.add_argument("--valid-path", type=Path, required=True, action="append")
    p_val.add_argument("--base-checkpoint", type=str, default=DEFAULT_BASE_CHECKPOINT)
    p_val.add_argument("--lora-checkpoint", type=str, default=None)
    p_val.add_argument("--store-dir", type=Path, required=True)
    p_val.add_argument("--config", type=Path, default=None)
    p_val.add_argument("--stage", type=int, default=2, choices=[1, 2])
    p_val.add_argument("--msst-root", type=Path, default=None)
    p_val.add_argument("--device-ids", type=str, default="0")
    p_val.add_argument("--metrics", nargs="+", default=ALL_METRICS)
    p_val.add_argument("--use-tta", action="store_true", help="Enable test-time augmentation")
    p_val.add_argument("--use-peft", action="store_true")
    p_val.add_argument("--dry-run", action="store_true")

    # Inference subcommand
    p_inf = subparsers.add_parser("infer", help="Run inference on a folder of audio files")
    p_inf.add_argument("--input-folder", type=Path, required=True)
    p_inf.add_argument("--base-checkpoint", type=str, default=DEFAULT_BASE_CHECKPOINT)
    p_inf.add_argument("--lora-checkpoint", type=str, default=None)
    p_inf.add_argument("--store-dir", type=Path, required=True)
    p_inf.add_argument("--config", type=Path, default=None)
    p_inf.add_argument("--stage", type=int, default=2, choices=[1, 2])
    p_inf.add_argument("--msst-root", type=Path, default=None)
    p_inf.add_argument("--device-ids", type=str, default="0")
    p_inf.add_argument("--use-peft", action="store_true")
    p_inf.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    msst_root = args.msst_root or find_msst_root()
    if msst_root is None or not msst_root.exists():
        print("ERROR: MSST repository not found. Please specify --msst-root or set MSST_ROOT env var.",
              file=sys.stderr)
        sys.exit(1)

    config_path = args.config or CONFIGS[args.stage]

    if args.command == "validate":
        rc = run_validation(
            msst_root=msst_root,
            config_path=config_path,
            valid_paths=args.valid_path,
            base_checkpoint=args.base_checkpoint,
            lora_checkpoint=args.lora_checkpoint,
            store_dir=args.store_dir,
            device_ids=args.device_ids,
            metrics=args.metrics,
            use_tta=args.use_tta,
            use_peft=args.use_peft,
            dry_run=args.dry_run,
        )
    elif args.command == "infer":
        rc = run_inference(
            msst_root=msst_root,
            config_path=config_path,
            input_folder=args.input_folder,
            base_checkpoint=args.base_checkpoint,
            lora_checkpoint=args.lora_checkpoint,
            store_dir=args.store_dir,
            device_ids=args.device_ids,
            use_peft=args.use_peft,
            dry_run=args.dry_run,
        )
    else:
        parser.error("Unknown command")
        rc = 1

    sys.exit(rc)


if __name__ == "__main__":
    main()
