#!/usr/bin/env python3
"""Generate quick test images with a trained Flux LoRA for identity validation.

Produces a small set of images (default 8) at 1024x576 using the trained LoRA
with inference-time lora_scale (NOT fuse_lora). These images are then fed to
validate_identity.py for ArcFace cosine similarity scoring.

Usage:
    python generate_test_images.py --lora /workspace/models/flux_lora/pytorch_lora_weights.safetensors
    python generate_test_images.py --lora models/flux_lora/pytorch_lora_weights.safetensors --output output/test_images/ --num-images 10 --lora-scale 0.9
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import torch
from diffusers import FluxPipeline


TEST_PROMPTS = [
    "ohwx person, front-facing portrait, neutral expression, wearing plain white t-shirt, in studio with gray backdrop, soft even lighting",
    "ohwx person, 3/4 angle view, slight smile, wearing blue denim jacket, in coffee shop, warm natural lighting from window",
    "ohwx person, side profile, serious expression, wearing black turtleneck, in dimly lit room, dramatic side lighting",
    "ohwx person, looking at camera, relaxed expression, wearing casual hoodie, outdoors in park, overcast diffused lighting",
    "ohwx person, front-facing, surprised expression, wearing formal suit, in modern office, fluorescent overhead lighting",
    "ohwx person, 3/4 angle, thoughtful expression, wearing leather jacket, on city street at dusk, mixed neon and streetlight",
    "ohwx person, looking slightly up, calm expression, wearing white shirt, in gallery with white walls, bright artificial lighting",
    "ohwx person, front-facing, broad smile, wearing red sweater, in cozy living room, warm lamp lighting",
]


def main():
    parser = argparse.ArgumentParser(description="Generate test images with trained Flux LoRA for identity validation")
    parser.add_argument("--lora", required=True, help="Path to trained Flux LoRA weights (.safetensors)")
    parser.add_argument("--output", default="output/test_images", help="Output directory for test images")
    parser.add_argument("--model", default="/workspace/models/FLUX.1-dev", help="Path to Flux.1-dev model")
    parser.add_argument("--num-images", type=int, default=8, help="Number of test images to generate")
    parser.add_argument("--lora-scale", type=float, default=0.9, help="LoRA scale at inference (0.8-1.2)")
    parser.add_argument("--width", type=int, default=1024, help="Image width")
    parser.add_argument("--height", type=int, default=576, help="Image height (576 for 16:9)")
    parser.add_argument("--steps", type=int, default=28, help="Inference steps")
    parser.add_argument("--guidance", type=float, default=3.5, help="CFG guidance scale")
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed for reproducibility (default: random)")
    args = parser.parse_args()

    print(f"Loading model: {args.model}")
    pipe = FluxPipeline.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16
    ).to("cuda")

    print(f"Loading LoRA: {args.lora}")
    pipe.load_lora_weights(args.lora)

    os.makedirs(args.output, exist_ok=True)

    num_prompts = min(args.num_images, len(TEST_PROMPTS))
    metadata = []

    for i in range(args.num_images):
        prompt = TEST_PROMPTS[i % len(TEST_PROMPTS)]
        seed = args.seed if args.seed is not None else torch.randint(0, 2**32, (1,)).item()

        image = pipe(
            prompt,
            height=args.height,
            width=args.width,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            cross_attention_kwargs={"scale": args.lora_scale},
            generator=torch.Generator("cuda").manual_seed(seed),
        ).images[0]

        filename = f"test_{i:03d}_seed{seed}.png"
        filepath = os.path.join(args.output, filename)
        image.save(filepath)

        entry = {
            "filename": filename,
            "filepath": filepath,
            "prompt": prompt,
            "seed": seed,
            "lora_scale": args.lora_scale,
            "steps": args.steps,
            "guidance": args.guidance,
            "width": args.width,
            "height": args.height,
            "timestamp": datetime.now().isoformat(),
        }
        metadata.append(entry)
        print(f"  [{i+1}/{args.num_images}] {filename} (seed={seed})")

    metadata_path = os.path.join(args.output, "test_images_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nGenerated {len(metadata)} test images")
    print(f"  Metadata: {metadata_path}")
    print(f"  Output: {args.output}")
    print(f"\nNext step: python /workspace/scripts/validate_identity.py --reference /workspace/dataset/processed --generated {args.output} --threshold 0.7")


if __name__ == "__main__":
    main()
