# Wave 2 — Flux LoRA Trainer Handoff

**Agent:** flux_lora
**Wave:** 2
**Status:** COMPLETE
**Date:** 2026-08-20

## Deliverables

- `scripts/train_flux_lora.py` — **Refactored** to hybrid TOML+CLI approach:
  - Removed `--instance_prompt`, `--resolution`, `--train_data_dir` from Kohya command (SD DreamBooth args, not for Flux)
  - Added `--dataset_config` CLI arg pointing to TOML file
  - Added `generate_toml()` function that auto-creates `dataset_config.toml` from dataset directory
  - Added Flux-specific Kohya flags: `--save_precision=bf16`, `--guidance_scale=3.5`
  - Added `--fp8-base` flag for 24GB VRAM fallback
  - Kept hyperparameters as CLI args: `--network_dim`, `--network_alpha`, `--learning_rate`, `--max_train_steps`, `--optimizer_type`

- `scripts/validate_identity.py` — **Fixed** `import sys` bug (was in `__main__` block, moved to top-level imports)

- `scripts/generate_test_images.py` — **New** script for quick identity validation:
  - Generates 8 test images at 1024×576 with trained LoRA
  - Uses `cross_attention_kwargs={"scale": lora_scale}` (inference-time, NOT fuse_lora)
  - 8 diverse test prompts (front-facing, 3/4, side profile, varied expressions/lighting)
  - Saves metadata JSON alongside images

- `models/flux_lora/training_config.toml` — Kohya dataset config:
  - Resolution 1024×576, `keep_tokens=1`, `shuffle_caption=true`
  - `num_repeats=10`, `batch_size=1`, `enable_bucket=false`
  - Image dir `/workspace/dataset/processed`, caption extension `.txt`

- `models/flux_lora/README.md` — Complete training & iteration guide:
  - Prerequisites, step-by-step workflow
  - 3-iteration hyperparameter table (baseline → high capacity → max fidelity)
  - Inference guidance (lora_scale 0.8-1.2, NOT fuse_lora)
  - Troubleshooting table

## Key Decisions

- **Hybrid TOML+CLI:** Dataset config in TOML (stable across iterations), hyperparameters as CLI args (change per iteration). Standard Kohya_ss method for Flux.
- **Inference-time lora_scale only:** `cross_attention_kwargs={"scale": X}` in diffusers, `strength_model` in ComfyUI. Never `fuse_lora()` — it permanently modifies weights and prevents scale adjustment.
- **3-iteration strategy:** Iteration 1 (rank 64, lr 1e-4, 1000 steps, AdamW) → Iteration 2 (rank 128, lr 5e-5, 1500 steps, Prodigy) → Iteration 3 (rank 128, alpha 128, lr 2e-5, 2000 steps, Prodigy + cosine_with_restarts).
- **Validation: ArcFace cosine similarity** via InsightFace `buffalo_l` model. Threshold ≥0.7 = good, ≥0.6 = acceptable.
- **Guidance scale 3.5:** Flux.1-dev default, used both in training and inference.

## Validation Workflow

```bash
# 1. Train
python /workspace/scripts/train_flux_lora.py \
    --dataset /workspace/dataset/processed \
    --output /workspace/models/flux_lora/iter1 \
    --rank 64 --alpha 32 --lr 1e-4 --steps 1000 --optimizer adamw

# 2. Generate test images
python /workspace/scripts/generate_test_images.py \
    --lora /workspace/models/flux_lora/iter1/pytorch_lora_weights.safetensors \
    --output /workspace/output/test_images/ --num-images 8 --lora-scale 0.9

# 3. Validate identity
python /workspace/scripts/validate_identity.py \
    --reference /workspace/dataset/processed \
    --generated /workspace/output/test_images/ --threshold 0.7

# 4. If <0.7, retry with iteration 2 or 3 (see models/flux_lora/README.md)
```

## Next Steps (Wave 3)

Wave 3 (Cinematic Reference Image Generator) depends on this LoRA:
1. Copy best `pytorch_lora_weights.safetensors` to `models/flux_lora/`
2. Run `scripts/generate_references.py` with `--lora models/flux_lora/pytorch_lora_weights.safetensors`
3. Generate 30-50 cinematic reference images at 1024×576 across 10 scenes
4. Use `lora_scale` 0.8-1.2 at inference (NOT fuse_lora)
