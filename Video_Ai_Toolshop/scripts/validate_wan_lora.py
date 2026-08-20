#!/usr/bin/env python3
"""Validate Wan 2.2 dual-expert LoRA identity preservation.

Generates short test video clips using trained high-noise + low-noise LoRAs,
extracts frames, and computes ArcFace cosine similarity against reference
frames from the dataset.

Usage:
    # Two-stage (default)
    python validate_wan_lora.py \
        --high-noise-lora /workspace/models/wan_lora/high_noise/pytorch_lora_weights.safetensors \
        --low-noise-lora /workspace/models/wan_lora/low_noise/pytorch_lora_weights.safetensors \
        --reference /workspace/dataset/video_clips \
        --output /workspace/output/test_clips

    # Three-stage
    python validate_wan_lora.py \
        --high-noise-lora /workspace/models/wan_lora/high_noise/pytorch_lora_weights.safetensors \
        --mid-noise-lora /workspace/models/wan_lora/mid_noise/pytorch_lora_weights.safetensors \
        --low-noise-lora /workspace/models/wan_lora/low_noise/pytorch_lora_weights.safetensors \
        --reference /workspace/dataset/video_clips \
        --output /workspace/output/test_clips
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def extract_video_frames(video_path: str, output_dir: str, max_frames: int = 5) -> list[str]:
    """Extract frames from a video using ffmpeg."""
    os.makedirs(output_dir, exist_ok=True)
    frames = []
    result = subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", f"select='lt(n,{max_frames})'",
        "-vsync", "vfr",
        "-q:v", "2",
        os.path.join(output_dir, "frame_%04d.png"),
        "-y",
    ], capture_output=True)
    if result.returncode == 0:
        frames = sorted(Path(output_dir).glob("frame_*.png"))
    return [str(f) for f in frames]


def get_face_embedding(image_path: str, app) -> np.ndarray | None:
    """Extract face embedding using InsightFace."""
    img = np.array(Image.open(image_path).convert("RGB"))
    faces = app.get(img)

    if len(faces) == 0:
        return None

    face = max(faces, key=lambda f: f.det_score)
    return face.embedding


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))


def generate_test_clips(args) -> list[str]:
    """Generate test video clips using Wan 2.2 with trained LoRAs."""
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    # Build generation command using musubi-tuner's wan_generate.py
    gen_cmd = [
        "python", "wan_generate.py",
        f"--task={args.task}",
        f"--pretrained_model_name_or_path={args.model}",
        f"--lora_weights={args.high_noise_lora}",
        f"--lora_weights={args.low_noise_lora}",
        f"--lora_scale={args.high_noise_scale}",
        f"--lora_scale={args.low_noise_scale}",
        f"--width={args.width}",
        f"--height={args.height}",
        f"--num_frames={args.num_frames}",
        f"--num_inference_steps={args.steps}",
        f"--guidance_scale={args.guidance_scale}",
        f"--output_dir={output_dir}",
        f"--seed={args.seed}",
    ]

    if args.mid_noise_lora:
        gen_cmd.insert(-2, f"--lora_weights={args.mid_noise_lora}")
        gen_cmd.insert(-2, f"--lora_scale={args.mid_noise_scale}")

    # Use first reference frame as I2V input
    ref_videos = sorted(Path(args.reference).glob("*.mp4"))
    if not ref_videos:
        ref_videos = sorted(Path(args.reference).glob("*.avi"))

    if not ref_videos:
        print("ERROR: No reference videos found for I2V input")
        sys.exit(1)

    # Extract first frame from first video as I2V conditioning image
    ref_frame_dir = os.path.join(output_dir, "ref_frames")
    ref_frames = extract_video_frames(str(ref_videos[0]), ref_frame_dir, max_frames=1)
    if not ref_frames:
        print("ERROR: Could not extract reference frame for I2V generation")
        sys.exit(1)

    gen_cmd.extend([
        f"--image_path={ref_frames[0]}",
        f"--prompt={args.prompt}",
    ])

    print("\n" + "=" * 60)
    print("GENERATING TEST CLIP")
    print("=" * 60)
    print(f"  Model: {args.model}")
    print(f"  High-noise LoRA: {args.high_noise_lora} (scale={args.high_noise_scale})")
    if args.mid_noise_lora:
        print(f"  Mid-noise LoRA: {args.mid_noise_lora} (scale={args.mid_noise_scale})")
    print(f"  Low-noise LoRA: {args.low_noise_lora} (scale={args.low_noise_scale})")
    print(f"  Resolution: {args.width}x{args.height}, {args.num_frames} frames")
    print(f"  Prompt: {args.prompt}")
    print()

    if args.dry_run:
        print("Dry run — not generating")
        return []

    musubi_dir = "/workspace/musubi-tuner"
    result = subprocess.run(gen_cmd, cwd=musubi_dir)

    if result.returncode != 0:
        print(f"Generation failed (exit code {result.returncode})")
        sys.exit(1)

    # Find generated clips
    clips = sorted(Path(output_dir).glob("*.mp4"))
    return [str(c) for c in clips]


def main():
    parser = argparse.ArgumentParser(
        description="Validate Wan 2.2 dual-expert LoRA identity preservation"
    )
    parser.add_argument("--high-noise-lora", required=True,
                        help="Path to high-noise expert LoRA .safetensors")
    parser.add_argument("--mid-noise-lora",
                        help="Path to mid-noise LoRA (three-stage only)")
    parser.add_argument("--low-noise-lora", required=True,
                        help="Path to low-noise expert LoRA .safetensors")
    parser.add_argument("--reference", required=True,
                        help="Directory of reference video clips")
    parser.add_argument("--output", required=True,
                        help="Output directory for test clips and report")
    parser.add_argument("--model", default="/workspace/models/Wan2.2-I2V-A14B",
                        help="Path to Wan 2.2 model")
    parser.add_argument("--task", default="i2v", choices=["i2v", "t2v"])
    parser.add_argument("--width", type=int, default=720, help="Output width")
    parser.add_argument("--height", type=int, default=480, help="Output height")
    parser.add_argument("--num-frames", type=int, default=25,
                        help="Number of frames to generate (2-3s at 24fps)")
    parser.add_argument("--steps", type=int, default=50,
                        help="Inference steps")
    parser.add_argument("--guidance-scale", type=float, default=5.0,
                        help="CFG guidance scale")
    parser.add_argument("--high-noise-scale", type=float, default=1.0,
                        help="LoRA scale for high-noise expert at inference")
    parser.add_argument("--mid-noise-scale", type=float, default=1.0,
                        help="LoRA scale for mid-noise adapter (three-stage)")
    parser.add_argument("--low-noise-scale", type=float, default=1.3,
                        help="LoRA scale for low-noise expert (1.3x boosted for identity)")
    parser.add_argument("--prompt", default="ohwx person, cinematic close-up, neutral expression, soft studio lighting",
                        help="Generation prompt (must include trigger word)")
    parser.add_argument("--threshold", type=float, default=0.7,
                        help="Identity similarity threshold (0.7=good, 0.6=acceptable)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print commands without executing")
    args = parser.parse_args()

    # Generate test clips
    clips = generate_test_clips(args)

    if args.dry_run or not clips:
        return

    # Initialize InsightFace
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name="buffalo_l",
                           providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
    except ImportError:
        print("ERROR: insightface not installed. Run: pip install insightface onnxruntime-gpu")
        sys.exit(1)

    # Extract reference embeddings from dataset video frames
    ref_videos = (
        sorted(Path(args.reference).glob("*.mp4"))
        + sorted(Path(args.reference).glob("*.avi"))
        + sorted(Path(args.reference).glob("*.mov"))
    )
    ref_frame_dir = os.path.join(args.output, "ref_frames_all")
    ref_embeddings = []

    for vidx, vpath in enumerate(ref_videos[:5]):
        clip_frame_dir = os.path.join(ref_frame_dir, f"clip_{vidx:04d}")
        frames = extract_video_frames(str(vpath), clip_frame_dir, max_frames=3)
        for fpath in frames:
            emb = get_face_embedding(fpath, app)
            if emb is not None:
                ref_embeddings.append((Path(vpath).name, emb))

    print(f"Extracted {len(ref_embeddings)} reference face embeddings from {len(ref_videos[:5])} clips")

    if not ref_embeddings:
        print("ERROR: No faces detected in reference video frames")
        sys.exit(1)

    # Extract frames from generated clips and compute identity
    results = []
    total_good = 0
    total_acceptable = 0
    total_failed = 0

    for clip_path in clips:
        clip_name = Path(clip_path).name
        clip_frame_dir = os.path.join(args.output, f"gen_frames_{clip_name}")
        gen_frames = extract_video_frames(clip_path, clip_frame_dir, max_frames=5)

        clip_sims = []
        for fpath in gen_frames:
            gen_emb = get_face_embedding(fpath, app)
            if gen_emb is None:
                results.append({
                    "clip": clip_name,
                    "frame": Path(fpath).name,
                    "status": "no_face",
                    "max_similarity": 0.0,
                })
                total_failed += 1
                continue

            similarities = []
            for ref_name, ref_emb in ref_embeddings:
                sim = cosine_similarity(gen_emb, ref_emb)
                similarities.append((ref_name, sim))

            max_sim = max(s for _, s in similarities)
            best_match = max(similarities, key=lambda x: x[1])
            clip_sims.append(max_sim)

            if max_sim >= args.threshold:
                status = "good"
                total_good += 1
            elif max_sim >= args.threshold - 0.1:
                status = "acceptable"
                total_acceptable += 1
            else:
                status = "failed"
                total_failed += 1

            results.append({
                "clip": clip_name,
                "frame": Path(fpath).name,
                "status": status,
                "max_similarity": max_sim,
                "best_match": best_match[0],
            })

    # Summary
    total = len(results) if results else 1
    avg_sim = float(np.mean([r["max_similarity"] for r in results])) if results else 0.0

    print(f"\n{'='*60}")
    print(f"WAN LoRA IDENTITY VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Generated clips: {len(clips)}")
    print(f"Total frames analyzed: {len(results)}")
    print(f"  Good (≥{args.threshold}):       {total_good} ({100*total_good/total:.1f}%)")
    print(f"  Acceptable (≥{args.threshold-0.1:.1f}): {total_acceptable} ({100*total_acceptable/total:.1f}%)")
    print(f"  Failed (<{args.threshold-0.1:.1f}):      {total_failed} ({100*total_failed/total:.1f}%)")
    print(f"  Average max similarity: {avg_sim:.4f}")
    print(f"{'='*60}")

    if total_good / total > 0.7:
        print("PASS: Wan LoRA identity preservation is good")
    elif (total_good + total_acceptable) / total > 0.5:
        print("MARGINAL: Identity is acceptable but could be improved")
        print("  Consider: more training steps, higher rank, or adjust lora_scale")
    else:
        print("FAIL: Identity preservation is poor")
        print("  Recommended actions:")
        print("  1. Check video clip quality (lighting, face visibility, motion)")
        print("  2. Increase training steps (try 3000-4000)")
        print("  3. Adjust learning rate (try 1e-5 for finer training)")
        print("  4. Increase LoRA rank (try 64)")
        print("  5. Boost low-noise lora_scale at inference (try 1.5)")
        print("  6. Ensure trigger word is in every caption")

    # Save report
    report = {
        "timestamp": str(np.datetime64("now")),
        "threshold": args.threshold,
        "model": args.model,
        "high_noise_lora": args.high_noise_lora,
        "mid_noise_lora": args.mid_noise_lora,
        "low_noise_lora": args.low_noise_lora,
        "high_noise_scale": args.high_noise_scale,
        "mid_noise_scale": args.mid_noise_scale,
        "low_noise_scale": args.low_noise_scale,
        "generated_clips": len(clips),
        "total_frames": len(results),
        "good": total_good,
        "acceptable": total_acceptable,
        "failed": total_failed,
        "average_max_similarity": avg_sim,
        "results": results,
    }

    report_path = os.path.join(args.output, "wan_lora_validation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report: {report_path}")


if __name__ == "__main__":
    main()
