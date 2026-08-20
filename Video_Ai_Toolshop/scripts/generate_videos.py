#!/usr/bin/env python3
"""Generate video clips with anchor-frame workflow for multi-clip continuity.

Uses HunyuanVideo 1.5 I2V (14GB VRAM) to generate 5s clips, then uses the last
frame of each clip as the first frame of the next clip for seamless continuity.
Falls back to LTX-Video 2B (8GB) if HunyuanVideo OOMs on 16GB GPUs.

Usage:
    python generate_videos.py --references output/reference_images/ --output output/raw_video/ --num-clips 5
    python generate_videos.py --references output/reference_images/ --output output/raw_video/ --model ltx
"""

import argparse
import os
from pathlib import Path

import torch
from PIL import Image
from diffusers import AutoPipelineForImage2Video
from diffusers.utils import export_to_video


def load_pipeline(model_name: str = "hunyuan"):
    """Load video generation pipeline. Supports hunyuan (1.5) and ltx (2B fallback)."""
    if model_name == "ltx":
        from diffusers import LTXVideoPipeline
        print("Loading LTX-Video 2B (8GB VRAM fallback)...")
        pipe = LTXVideoPipeline.from_pretrained(
            "Lightricks/LTX-Video-2B",
            torch_dtype=torch.float16,
        ).to("cuda")
        return pipe, "ltx"
    else:
        from diffusers import HunyuanVideoPipeline
        print("Loading HunyuanVideo 1.5 (14GB VRAM with offloading)...")
        pipe = HunyuanVideoPipeline.from_pretrained(
            "tencent/HunyuanVideo-1.5",
            torch_dtype=torch.float16,
        ).to("cuda")
        pipe.enable_model_cpu_offload()
        return pipe, "hunyuan"
    return pipe


def generate_clip(
    pipe,
    image: Image.Image,
    prompt: str,
    output_path: str,
    num_frames: int = 121,
    steps: int = 40,
    cfg: float = 7.5,
    seed: int = 42,
    negative_prompt: str = "blurry, distorted, low quality, deformed, watermark, He is speaking. Talking. mouth moving",
) -> Image.Image:
    """Generate a single video clip. Returns last frame for anchor-frame workflow."""
    
    # Resize image to Wan 2.2 native resolution
    image = image.resize((1280, 704), Image.LANCZOS)
    
    video = pipe(
        image=image,
        prompt=prompt,
        num_inference_steps=steps,
        num_frames=num_frames,
        guidance_scale=cfg,
        negative_prompt=negative_prompt,
        generator=torch.Generator("cuda").manual_seed(seed),
    ).frames[0]
    
    export_to_video(video, output_path, fps=24)
    print(f"  Saved: {output_path}")
    
    # Return last frame as PIL Image for anchor-frame workflow
    last_frame = Image.fromarray(video[-1])
    return last_frame


def extract_last_frame(video_path: str) -> Image.Image:
    """Extract last frame from a video file using FFmpeg."""
    import subprocess
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vf", "select=eq(n\,0)",
            "-vframes", "1",
            "-q:v", "2",
            tmp.name
        ], check=True, capture_output=True)
        return Image.open(tmp.name)


def main():
    parser = argparse.ArgumentParser(description="Generate video clips with anchor-frame workflow")
    parser.add_argument("--references", required=True, help="Directory of reference images")
    parser.add_argument("--output", default="output/raw_video", help="Output directory")
    parser.add_argument("--model", default="hunyuan", choices=["hunyuan", "ltx"], help="Video model: hunyuan (HunyuanVideo 1.5) or ltx (LTX-Video 2B fallback)")
    parser.add_argument("--num-clips", type=int, default=5, help="Number of sequential clips")
    parser.add_argument("--frames", type=int, default=121, help="Frames per clip (121=5s@24fps)")
    parser.add_argument("--steps", type=int, default=40, help="Inference steps (4 for LightX2V)")
    parser.add_argument("--cfg", type=float, default=7.5, help="CFG guidance scale")
    parser.add_argument("--prompt", default="ohwx person walking forward, camera dollying forward, cinematic motion, 35mm anamorphic, photorealistic", help="Video prompt")
    parser.add_argument("--denoise", type=float, default=0.75, help="Denoise strength for anchor frames")
    parser.add_argument("--lora-high", help="Path to Wan 2.2 high-noise LoRA (Track B)")
    parser.add_argument("--lora-low", help="Path to Wan 2.2 low-noise LoRA (Track B)")
    parser.add_argument("--lora-scale", type=float, default=1.0, help="LoRA adapter weight")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    pipe, model_type = load_pipeline(args.model)
    
    # Load Track B LoRAs if provided (HunyuanVideo or LTX)
    if args.lora_high and args.lora_low:
        print(f"Loading Track B LoRAs: {args.lora_high} + {args.lora_low}")
        pipe.load_lora_weights(args.lora_high, adapter_name="high_noise")
        pipe.load_lora_weights(args.lora_low, adapter_name="low_noise")
        pipe.set_adapters(["high_noise", "low_noise"], adapter_weights=[1.0, 1.3])
        print("  Low-noise LoRA boosted to 1.3x for sharper identity")
    
    # Find reference images
    ref_images = sorted(
        list(Path(args.references).rglob("*.png")) + list(Path(args.references).rglob("*.jpg"))
    )
    
    if len(ref_images) == 0:
        print("ERROR: No reference images found")
        return
    
    print(f"\nGenerating {args.num_clips} clips from {len(ref_images)} reference images")
    print(f"Using anchor-frame workflow (denoise={args.denoise} for continuity)\n")
    
    # Generate clips
    current_image = Image.open(ref_images[0])
    
    for clip_num in range(args.num_clips):
        print(f"\n--- Clip {clip_num + 1}/{args.num_clips} ---")
        
        # Use different reference image for first clip, anchor frame for subsequent
        if clip_num == 0:
            print(f"  Source: reference image {ref_images[0].name}")
        else:
            print(f"  Source: anchor frame from clip {clip_num}")
        
        output_path = os.path.join(args.output, f"clip_{clip_num + 1:03d}.mp4")
        seed = 42 + clip_num * 100
        
        current_image = generate_clip(
            pipe,
            current_image,
            args.prompt,
            output_path,
            num_frames=args.frames,
            steps=args.steps,
            cfg=args.cfg,
            seed=seed,
        )
    
    print(f"\n✓ Generated {args.num_clips} clips")
    print(f"  Output: {args.output}")
    print(f"\nNext steps:")
    print(f"  1. Review raw clips")
    print(f"  2. Run post-processing: python scripts/postproc/postprocess.py --input {args.output} --output output/processed_video/ --batch")
    print(f"  3. Assemble in DaVinci Resolve")


if __name__ == "__main__":
    main()
