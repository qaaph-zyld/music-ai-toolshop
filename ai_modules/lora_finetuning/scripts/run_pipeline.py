"""Full pipeline runner for 2-stage LoRA fine-tuning of BS-RoFormer.

Orchestrates:
1. Dataset preparation (organize + master)
2. Stage 1 training (clean genre adaptation)
3. Stage 2 training (mastered audio adaptation)
4. Evaluation
5. Inference

Usage:
    python -m ai_modules.lora_finetuning.scripts.run_pipeline --source-dir /raw/stems --input-folder /tracks/to/separate
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .prepare_dataset import organize_to_type1, prepare_mastered_dataset, validate_dataset
from .train import run_training, find_msst_root, CONFIGS as TRAIN_CONFIGS, DEFAULT_BASE_CHECKPOINT, DEFAULT_METRICS
from .evaluate import run_validation, run_inference, CONFIGS as EVAL_CONFIGS, ALL_METRICS


def main():
    parser = argparse.ArgumentParser(description="Run full 2-stage LoRA fine-tuning pipeline")
    parser.add_argument("--source-dir", type=Path, required=True,
                        help="Directory with raw track folders containing stem WAVs")
    parser.add_argument("--work-dir", type=Path, required=True,
                        help="Working directory for all pipeline outputs")
    parser.add_argument("--base-checkpoint", type=str, default=DEFAULT_BASE_CHECKPOINT)
    parser.add_argument("--msst-root", type=Path, default=None)
    parser.add_argument("--device-ids", type=str, default="0")
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-stage1", action="store_true")
    parser.add_argument("--skip-stage2", action="store_true")
    parser.add_argument("--skip-eval", action="store_true")
    parser.add_argument("--input-folder", type=Path, default=None,
                        help="Folder of audio files to separate after training")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = args.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    log = {"timestamp": timestamp, "steps": []}

    # Step 1: Organize raw stems into Type 1 dataset
    print("=" * 60)
    print("STEP 1: Organize raw stems into Type 1 dataset")
    print("=" * 60)
    clean_dataset = work_dir / "dataset_clean"
    result = organize_to_type1(args.source_dir, clean_dataset, args.train_split, args.seed)
    log["steps"].append({"step": "organize", "result": result})

    # Validate clean dataset
    if not validate_dataset(clean_dataset, dataset_type=1):
        print("ERROR: Clean dataset validation failed", file=sys.stderr)
        sys.exit(1)

    # Step 2: Prepare mastered dataset
    print("\n" + "=" * 60)
    print("STEP 2: Prepare mastered dataset (Stage 2 training data)")
    print("=" * 60)
    mastered_dataset = work_dir / "dataset_mastered"
    result = prepare_mastered_dataset(clean_dataset, mastered_dataset, args.train_split, args.seed)
    log["steps"].append({"step": "master", "result": result})

    if not validate_dataset(mastered_dataset, dataset_type=6):
        print("ERROR: Mastered dataset validation failed", file=sys.stderr)
        sys.exit(1)

    msst_root = args.msst_root or find_msst_root()
    if msst_root is None:
        print("ERROR: MSST repository not found. Set --msst-root or MSST_ROOT env var.", file=sys.stderr)
        sys.exit(1)

    # Step 3: Stage 1 training
    stage1_results = work_dir / "results_stage1"
    if not args.skip_stage1:
        print("\n" + "=" * 60)
        print("STEP 3: Stage 1 — General genre adaptation (clean stems)")
        print("=" * 60)
        rc = run_training(
            msst_root=msst_root,
            config_path=TRAIN_CONFIGS[1],
            data_paths=[clean_dataset / "train"],
            valid_paths=[clean_dataset / "val"],
            base_checkpoint=args.base_checkpoint,
            results_path=stage1_results,
            device_ids=args.device_ids,
            metrics=DEFAULT_METRICS,
            metric_for_scheduler="sdr",
            dry_run=args.dry_run,
        )
        log["steps"].append({"step": "stage1_train", "return_code": rc})
        if rc != 0:
            print(f"ERROR: Stage 1 training failed with code {rc}", file=sys.stderr)
            sys.exit(rc)
    else:
        print("\nSkipping Stage 1 (--skip-stage1)")
        log["steps"].append({"step": "stage1_train", "skipped": True})

    # Find LoRA checkpoint from Stage 1
    lora_ckpt = None
    if stage1_results.exists():
        lora_files = sorted(stage1_results.glob("lora_*.ckpt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if lora_files:
            lora_ckpt = str(lora_files[0])
            print(f"Found Stage 1 LoRA checkpoint: {lora_ckpt}")

    # Step 4: Stage 2 training
    stage2_results = work_dir / "results_stage2"
    if not args.skip_stage2:
        print("\n" + "=" * 60)
        print("STEP 4: Stage 2 — Mastered audio adaptation")
        print("=" * 60)
        rc = run_training(
            msst_root=msst_root,
            config_path=TRAIN_CONFIGS[2],
            data_paths=[mastered_dataset / "train"],
            valid_paths=[mastered_dataset / "val"],
            base_checkpoint=args.base_checkpoint,
            results_path=stage2_results,
            device_ids=args.device_ids,
            metrics=DEFAULT_METRICS,
            metric_for_scheduler="sdr",
            lora_checkpoint=lora_ckpt,
            dry_run=args.dry_run,
        )
        log["steps"].append({"step": "stage2_train", "return_code": rc})
        if rc != 0:
            print(f"ERROR: Stage 2 training failed with code {rc}", file=sys.stderr)
            sys.exit(rc)
    else:
        print("\nSkipping Stage 2 (--skip-stage2)")
        log["steps"].append({"step": "stage2_train", "skipped": True})

    # Find LoRA checkpoint from Stage 2
    final_lora_ckpt = None
    if stage2_results.exists():
        lora_files = sorted(stage2_results.glob("lora_*.ckpt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if lora_files:
            final_lora_ckpt = str(lora_files[0])
    elif lora_ckpt:
        final_lora_ckpt = lora_ckpt

    # Step 5: Evaluation
    if not args.skip_eval:
        print("\n" + "=" * 60)
        print("STEP 5: Evaluation")
        print("=" * 60)
        eval_store = work_dir / "evaluation_results"
        rc = run_validation(
            msst_root=msst_root,
            config_path=EVAL_CONFIGS[2],
            valid_paths=[mastered_dataset / "val"],
            base_checkpoint=args.base_checkpoint,
            lora_checkpoint=final_lora_ckpt,
            store_dir=eval_store,
            device_ids=args.device_ids,
            metrics=ALL_METRICS,
            use_tta=True,
            dry_run=args.dry_run,
        )
        log["steps"].append({"step": "evaluate", "return_code": rc})

    # Step 6: Inference
    if args.input_folder:
        print("\n" + "=" * 60)
        print("STEP 6: Inference")
        print("=" * 60)
        infer_store = work_dir / "inference_results"
        rc = run_inference(
            msst_root=msst_root,
            config_path=EVAL_CONFIGS[2],
            input_folder=args.input_folder,
            base_checkpoint=args.base_checkpoint,
            lora_checkpoint=final_lora_ckpt,
            store_dir=infer_store,
            device_ids=args.device_ids,
            dry_run=args.dry_run,
        )
        log["steps"].append({"step": "infer", "return_code": rc})

    # Save pipeline log
    log_path = work_dir / f"pipeline_log_{timestamp}.json"
    log_path.write_text(json.dumps(log, indent=2, default=str))
    print(f"\nPipeline log saved to: {log_path}")
    print("\nPipeline complete!")


if __name__ == "__main__":
    main()
