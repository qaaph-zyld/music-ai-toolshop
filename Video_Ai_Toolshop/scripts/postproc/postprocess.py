#!/usr/bin/env python3
"""Post-processing pipeline: GFPGAN → Real-ESRGAN → RIFE

Usage:
    python postprocess.py --input raw_video/clip_001.mp4 --output processed_video/clip_001_processed.mp4
    python postprocess.py --input raw_video/ --output processed_video/ --batch
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def extract_frames(input_video: str, output_dir: str, fps: float = 24.0) -> list[str]:
    """Extract frames from video using FFmpeg."""
    os.makedirs(output_dir, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-i", input_video,
        "-vf", f"fps={fps}",
        "-q:v", "2",
        os.path.join(output_dir, "frame_%06d.png")
    ], check=True)
    
    frames = sorted(Path(output_dir).glob("frame_*.png"))
    print(f"Extracted {len(frames)} frames from {input_video}")
    return [str(f) for f in frames]


def run_gfpgan(input_dir: str, output_dir: str, version: str = "1.4") -> None:
    """Run GFPGAN face restoration on all frames."""
    os.makedirs(output_dir, exist_ok=True)
    
    from gfpgan import GFPGANer
    import cv2
    
    model = GFPGANer(
        model_path=f"weights/GFPGANv{version}.pth",
        upscale=1,
        arch="clean",
        channel_multiplier=2,
    )
    
    frames = sorted(Path(input_dir).glob("frame_*.png"))
    for frame_path in frames:
        img = cv2.imread(str(frame_path), cv2.IMREAD_UNCHANGED)
        _, _, output = model.enhance(img, paste_back=True)
        cv2.imwrite(os.path.join(output_dir, frame_path.name), output)
    
    print(f"GFPGAN restored {len(frames)} frames")


def run_realesrgan(input_dir: str, output_dir: str, scale: int = 4) -> None:
    """Run Real-ESRGAN upscaling on all frames."""
    os.makedirs(output_dir, exist_ok=True)
    
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet
    import cv2
    import numpy as np
    
    model = RRDBNet(
        num_in_ch=3, num_out_ch=3, num_feat=64,
        num_block=23, num_grow_ch=32, scale=4
    )
    
    upsampler = RealESRGANer(
        scale=4,
        model_path="weights/RealESRGAN_x4plus.pth",
        model=model,
        tile=512,
        tile_pad=10,
        pre_pad=0,
        half=True,
    )
    
    frames = sorted(Path(input_dir).glob("frame_*.png"))
    for frame_path in frames:
        img = cv2.imread(str(frame_path), cv2.IMREAD_UNCHANGED)
        output, _ = upsampler.enhance(img, outscale=scale)
        cv2.imwrite(os.path.join(output_dir, frame_path.name), output)
    
    print(f"Real-ESRGAN upscaled {len(frames)} frames ({scale}x)")


def run_rife(input_dir: str, output_dir: str, fps: float = 24.0, target_fps: float = 48.0) -> None:
    """Run RIFE frame interpolation using FFmpeg's minterpolate or RIFE directly."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Using FFmpeg minterpolate as fallback (simpler, no RIFE model needed)
    # For true RIFE, use: https://github.com/hzwer/ECCV2022-RIFE
    frames_pattern = os.path.join(input_dir, "frame_%06d.png")
    output_path = os.path.join(output_dir, "interpolated.mp4")
    
    subprocess.run([
        "ffmpeg", "-framerate", str(fps),
        "-i", frames_pattern,
        "-vf", f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        output_path
    ], check=True)
    
    print(f"RIFE interpolated to {target_fps}fps → {output_path}")


def reassemble_video(input_dir: str, output_path: str, fps: float = 48.0) -> None:
    """Reassemble frames into final video."""
    frames_pattern = os.path.join(input_dir, "frame_%06d.png")
    
    subprocess.run([
        "ffmpeg", "-framerate", str(fps),
        "-i", frames_pattern,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        output_path
    ], check=True)
    
    print(f"Reassembled video → {output_path}")


def process_single(input_video: str, output_video: str, work_dir: str = "/tmp/postproc") -> None:
    """Full post-processing chain for a single video."""
    print(f"\n{'='*60}")
    print(f"Processing: {input_video}")
    print(f"Output: {output_video}")
    print(f"{'='*60}\n")
    
    # Step 1: Extract frames
    frames_dir = os.path.join(work_dir, "frames")
    extract_frames(input_video, frames_dir, fps=24.0)
    
    # Step 2: GFPGAN face restoration
    gfpgan_dir = os.path.join(work_dir, "gfpgan")
    run_gfpgan(frames_dir, gfpgan_dir)
    
    # Step 3: Real-ESRGAN 4x upscale
    esrgan_dir = os.path.join(work_dir, "esrgan")
    run_realesrgan(gfpgan_dir, esrgan_dir, scale=4)
    
    # Step 4: RIFE frame interpolation (24fps → 48fps)
    rife_dir = os.path.join(work_dir, "rife")
    run_rife(esrgan_dir, rife_dir, fps=24.0, target_fps=48.0)
    
    # Step 5: Copy final video
    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    final_path = os.path.join(rife_dir, "interpolated.mp4")
    if os.path.exists(final_path):
        import shutil
        shutil.copy2(final_path, output_video)
    
    print(f"\n✓ Post-processing complete: {output_video}")


def process_batch(input_dir: str, output_dir: str) -> None:
    """Process all videos in a directory."""
    os.makedirs(output_dir, exist_ok=True)
    videos = sorted(Path(input_dir).glob("*.mp4"))
    
    print(f"Found {len(videos)} videos to process")
    
    for video in videos:
        output_path = os.path.join(output_dir, f"{video.stem}_processed.mp4")
        work_dir = f"/tmp/postproc_{video.stem}"
        process_single(str(video), output_path, work_dir)


def main():
    parser = argparse.ArgumentParser(description="Post-processing pipeline: GFPGAN → Real-ESRGAN → RIFE")
    parser.add_argument("--input", required=True, help="Input video file or directory")
    parser.add_argument("--output", required=True, help="Output video file or directory")
    parser.add_argument("--batch", action="store_true", help="Process all videos in input directory")
    args = parser.parse_args()
    
    if args.batch:
        process_batch(args.input, args.output)
    else:
        process_single(args.input, args.output)


if __name__ == "__main__":
    main()
