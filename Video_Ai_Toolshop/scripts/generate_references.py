#!/usr/bin/env python3
"""Generate cinematic reference images using SDXL + LoRA.

Usage:
    python generate_references.py --lora models/sdxl_lora/sdxl_lora.safetensors \
        --output output/reference_images/ --scenes scenes.json

    python generate_references.py --lora models/sdxl_lora/sdxl_lora.safetensors \
        --output output/reference_images/ --prompt "ohwx person in neon-lit Tokyo street"
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import torch
from diffusers import StableDiffusionXLPipeline


# Default cinematic scenes (10 scenes × 3-5 images each = 30-50 images)
DEFAULT_SCENES = [
    {
        "name": "neon_tokyo_night",
        "prompt": "ohwx person walking through a neon-lit Tokyo street at night, "
                  "35mm anamorphic lens, shallow depth of field, volumetric fog with god rays from streetlights, "
                  "teal and orange color grade, subtle 35mm film grain, cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 5,
        "lora_scale": 0.9,
    },
    {
        "name": "golden_hour_field",
        "prompt": "ohwx person standing in a golden wheat field at sunset, "
                  "85mm telephoto lens, compressed depth, warm golden hour lighting, "
                  "lens flare from low sun, shallow depth of field, Kodak Portra 400 film stock, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 4,
        "lora_scale": 0.85,
    },
    {
        "name": "rainy_city_umbrella",
        "prompt": "ohwx person holding black umbrella on rainy city street, "
                  "50mm standard lens, natural perspective, rain droplets, reflections on wet pavement, "
                  "moody desaturated palette, cool blue tones, 35mm film grain, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 5,
        "lora_scale": 0.9,
    },
    {
        "name": "studio_portrait_dramatic",
        "prompt": "ohwx person in dramatic studio portrait, Rembrandt lighting, "
                  "135mm telephoto lens, extreme shallow depth of field, black background, "
                  "single key light from left, chiaroscuro, fine film grain, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 4,
        "lora_scale": 1.0,
    },
    {
        "name": "futuristic_corridor",
        "prompt": "ohwx person walking down futuristic corridor with holographic displays, "
                  "24mm wide angle lens, exaggerated depth, blue and purple neon lighting, "
                  "volumetric fog, god rays from ceiling lights, 2.39:1 cinema scope, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 5,
        "lora_scale": 0.9,
    },
    {
        "name": "desert_highway",
        "prompt": "ohwx person standing beside desert highway at dusk, "
                  "35mm anamorphic lens, vast landscape, dusty atmosphere, "
                  "warm orange sky fading to deep blue, heat haze, 35mm film grain, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 4,
        "lora_scale": 0.85,
    },
    {
        "name": "snowy_mountain_peak",
        "prompt": "ohwx person on snowy mountain peak, bright sunlight, "
                  "16mm wide angle lens, expansive sky, snow particles in air, "
                  "cool blue and white palette, crisp sharp detail, 2.39:1 cinema scope, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 3,
        "lora_scale": 0.8,
    },
    {
        "name": "jazz_club_smoky",
        "prompt": "ohwx person in dimly lit jazz club, stage spotlight, "
                  "50mm standard lens, cigarette smoke in air, warm amber lighting, "
                  "bokeh from background lights, muted desaturated palette, 35mm film grain, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 5,
        "lora_scale": 0.95,
    },
    {
        "name": "rooftop_sunrise",
        "prompt": "ohwx person on city rooftop at sunrise, backlit by rising sun, "
                  "35mm anamorphic lens, lens flare, warm morning light, "
                  "city skyline in background, shallow depth of field, Kodak Portra 400, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 4,
        "lora_scale": 0.85,
    },
    {
        "name": "underground_subway",
        "prompt": "ohwx person in underground subway station, fluorescent lighting, "
                  "24mm wide angle lens, motion blur of passing train, "
                  "green and orange color grade, gritty texture, 35mm film grain, "
                  "cinematic lighting, photorealistic, 8k resolution render",
        "num_images": 5,
        "lora_scale": 0.9,
    },
]


def generate_images(
    pipe: FluxPipeline,
    prompt: str,
    num_images: int,
    output_dir: str,
    scene_name: str,
    lora_scale: float = 0.9,
    width: int = 1024,
    height: int = 576,
    steps: int = 30,
    guidance: float = 3.5,
) -> list[dict]:
    """Generate multiple images for a single scene."""
    scene_dir = os.path.join(output_dir, scene_name)
    os.makedirs(scene_dir, exist_ok=True)
    
    metadata = []
    for i in range(num_images):
        seed = torch.randint(0, 2**32, (1,)).item()
        
        image = pipe(
            prompt,
            height=height,
            width=width,
            num_inference_steps=steps,
            guidance_scale=guidance,
            cross_attention_kwargs={"scale": lora_scale},
            generator=torch.Generator("cuda").manual_seed(seed),
        ).images[0]
        
        filename = f"{scene_name}_{i:03d}_seed{seed}.png"
        filepath = os.path.join(scene_dir, filename)
        image.save(filepath)
        
        entry = {
            "filename": filename,
            "filepath": filepath,
            "scene": scene_name,
            "prompt": prompt,
            "seed": seed,
            "lora_scale": lora_scale,
            "steps": steps,
            "guidance": guidance,
            "width": width,
            "height": height,
            "timestamp": datetime.now().isoformat(),
        }
        metadata.append(entry)
        print(f"  [{i+1}/{num_images}] {filename} (seed={seed})")
    
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Generate cinematic reference images with Flux + LoRA")
    parser.add_argument("--lora", required=True, help="Path to Flux LoRA weights (.safetensors)")
    parser.add_argument("--output", default="output/reference_images", help="Output directory")
    parser.add_argument("--model", default="stabilityai/stable-diffusion-xl-base-1.0", help="Base SDXL model")
    parser.add_argument("--scenes", help="JSON file with custom scene definitions")
    parser.add_argument("--prompt", help="Single prompt (overrides scenes)")
    parser.add_argument("--num-images", type=int, default=5, help="Number of images for single prompt mode")
    parser.add_argument("--lora-scale", type=float, default=0.9, help="LoRA scale (0.8-1.2)")
    parser.add_argument("--width", type=int, default=1024, help="Image width")
    parser.add_argument("--height", type=int, default=576, help="Image height (576 for 16:9)")
    parser.add_argument("--steps", type=int, default=30, help="Inference steps")
    parser.add_argument("--guidance", type=float, default=7.0, help="CFG guidance scale (7.0 for SDXL)")
    args = parser.parse_args()
    
    print(f"Loading model: {args.model}")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        args.model,
        torch_dtype=torch.float16,
        variant="fp16"
    ).to("cuda")
    
    print(f"Loading LoRA: {args.lora}")
    pipe.load_lora_weights(args.lora)
    
    os.makedirs(args.output, exist_ok=True)
    all_metadata = []
    
    if args.prompt:
        # Single prompt mode
        print(f"\nGenerating {args.num_images} images for custom prompt...")
        metadata = generate_images(
            pipe, args.prompt, args.num_images,
            args.output, "custom", args.lora_scale,
            args.width, args.height, args.steps, args.guidance
        )
        all_metadata.extend(metadata)
    else:
        # Scene-based mode
        scenes = DEFAULT_SCENES
        if args.scenes:
            with open(args.scenes) as f:
            scenes = json.load(f)
        
        total = sum(s["num_images"] for s in scenes)
        print(f"\nGenerating {total} images across {len(scenes)} scenes...")
        
        for scene in scenes:
            print(f"\n--- Scene: {scene['name']} ({scene['num_images']} images) ---")
            metadata = generate_images(
                pipe, scene["prompt"], scene["num_images"],
                args.output, scene["name"], scene.get("lora_scale", 0.9),
                args.width, args.height, args.steps, args.guidance
            )
            all_metadata.extend(metadata)
    
    # Save metadata
    metadata_path = os.path.join(args.output, "generation_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(all_metadata, f, indent=2)
    
    print(f"\n✓ Generated {len(all_metadata)} images")
    print(f"  Metadata: {metadata_path}")
    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
