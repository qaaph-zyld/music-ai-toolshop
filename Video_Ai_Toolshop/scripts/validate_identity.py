#!/usr/bin/env python3
"""Validate LoRA identity preservation using ArcFace cosine similarity.

Compares generated images against original reference photos to verify
the LoRA has learned the subject's identity.

Usage:
    python validate_identity.py --reference dataset/processed/ --generated output/reference_images/ --threshold 0.7
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def get_face_embedding(image_path: str, app) -> np.ndarray | None:
    """Extract face embedding using InsightFace."""
    img = np.array(Image.open(image_path).convert("RGB"))
    faces = app.get(img)
    
    if len(faces) == 0:
        print(f"  WARNING: No face detected in {image_path}")
        return None
    
    # Use the largest face (highest detection score)
    face = max(faces, key=lambda f: f.det_score)
    return face.embedding


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))


def main():
    parser = argparse.ArgumentParser(description="Validate LoRA identity with ArcFace cosine similarity")
    parser.add_argument("--reference", required=True, help="Directory of original reference photos")
    parser.add_argument("--generated", required=True, help="Directory of generated images")
    parser.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0.7=good, 0.6=acceptable)")
    parser.add_argument("--output", default="identity_validation_report.json", help="Output report file")
    args = parser.parse_args()
    
    # Initialize InsightFace
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
    except ImportError:
        print("ERROR: insightface not installed. Run: pip install insightface onnxruntime-gpu")
        sys.exit(1)
    
    # Get reference embeddings
    ref_images = list(Path(args.reference).glob("*.png")) + list(Path(args.reference).glob("*.jpg"))
    print(f"Found {len(ref_images)} reference images")
    
    ref_embeddings = []
    for img_path in ref_images:
        emb = get_face_embedding(str(img_path), app)
        if emb is not None:
            ref_embeddings.append((img_path.name, emb))
    
    print(f"Extracted {len(ref_embeddings)} reference face embeddings")
    
    if len(ref_embeddings) == 0:
        print("ERROR: No faces detected in reference images")
        sys.exit(1)
    
    # Get generated embeddings
    gen_images = list(Path(args.generated).rglob("*.png")) + list(Path(args.generated).rglob("*.jpg"))
    print(f"Found {len(gen_images)} generated images")
    
    results = []
    total_good = 0
    total_acceptable = 0
    total_failed = 0
    
    for img_path in gen_images:
        gen_emb = get_face_embedding(str(img_path), app)
        
        if gen_emb is None:
            results.append({
                "image": str(img_path),
                "status": "no_face",
                "max_similarity": 0.0,
            })
            total_failed += 1
            continue
        
        # Compare against all reference embeddings
        similarities = []
        for ref_name, ref_emb in ref_embeddings:
            sim = cosine_similarity(gen_emb, ref_emb)
            similarities.append((ref_name, sim))
        
        max_sim = max(s for _, s in similarities)
        best_match = max(similarities, key=lambda x: x[1])
        
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
            "image": str(img_path),
            "status": status,
            "max_similarity": max_sim,
            "best_match": best_match[0],
            "all_similarities": {name: sim for name, sim in similarities},
        })
    
    # Summary
    total = len(gen_images)
    print(f"\n{'='*60}")
    print(f"IDENTITY VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Total generated images: {total}")
    print(f"  Good (≥{args.threshold}):       {total_good} ({100*total_good/total:.1f}%)")
    print(f"  Acceptable (≥{args.threshold-0.1:.1f}): {total_acceptable} ({100*total_acceptable/total:.1f}%)")
    print(f"  Failed (<{args.threshold-0.1:.1f}):      {total_failed} ({100*total_failed/total:.1f}%)")
    print(f"  Average max similarity: {np.mean([r['max_similarity'] for r in results]):.4f}")
    print(f"{'='*60}")
    
    if total_good / total > 0.7:
        print("✓ PASS: LoRA identity preservation is good")
    elif (total_good + total_acceptable) / total > 0.5:
        print("⚠ MARGINAL: LoRA identity is acceptable but could be improved")
        print("  Consider: more training steps, higher rank, or better dataset")
    else:
        print("✗ FAIL: LoRA identity preservation is poor")
        print("  Recommended actions:")
        print("  1. Check dataset quality (lighting, angles, face visibility)")
        print("  2. Increase training steps (try 1500-2000)")
        print("  3. Adjust learning rate (try 5e-5)")
        print("  4. Increase LoRA rank (try 128)")
        print("  5. Ensure trigger word is in every caption")
    
    # Save report
    report = {
        "timestamp": str(np.datetime64('now')),
        "threshold": args.threshold,
        "reference_images": len(ref_images),
        "generated_images": total,
        "good": total_good,
        "acceptable": total_acceptable,
        "failed": total_failed,
        "average_max_similarity": float(np.mean([r['max_similarity'] for r in results])),
        "results": results,
    }
    
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report: {args.output}")


if __name__ == "__main__":
    main()
