# Flux.1-dev DreamBooth LoRA Training Guide

## Prerequisites

1. **RunPod A100 80GB** instance deployed (see `infra/cloud_setup.md`)
2. **Kohya_ss (sd-scripts)** installed at `/workspace/sd-scripts`
3. **Flux.1-dev** model downloaded to `/workspace/models/FLUX.1-dev`
4. **Dataset** uploaded to `/workspace/dataset/processed/` (25-30 images at 1024×576 + .txt captions, trigger word `ohwx person`)
5. **InsightFace** installed for validation: `pip install insightface onnxruntime-gpu`

## Training Workflow

### Step 1: Train LoRA

```bash
python /workspace/scripts/train_flux_lora.py \
    --dataset /workspace/dataset/processed \
    --output /workspace/models/flux_lora \
    --rank 64 --alpha 32 --lr 1e-4 --steps 1000 \
    --optimizer adamw \
    --dry-run  # remove --dry-run to execute
```

The script auto-generates `dataset_config.toml` from the dataset directory. You can also use a pre-existing TOML with `--dataset-config /workspace/dataset/dataset_config.toml`.

### Step 2: Generate Test Images

```bash
python /workspace/scripts/generate_test_images.py \
    --lora /workspace/models/flux_lora/pytorch_lora_weights.safetensors \
    --output /workspace/output/test_images/ \
    --num-images 8 --lora-scale 0.9
```

### Step 3: Validate Identity

```bash
python /workspace/scripts/validate_identity.py \
    --reference /workspace/dataset/processed \
    --generated /workspace/output/test_images/ \
    --threshold 0.7
```

**Results interpretation:**
- **≥70% images at similarity ≥0.7** → PASS, proceed to Wave 3
- **50-70% at ≥0.6** → MARGINAL, try next iteration
- **<50% at ≥0.6** → FAIL, retry with iteration 2 or 3

## Iteration Guide

Expect 2-3 training iterations. The dataset config TOML stays the same across iterations; only hyperparameters change.

### Iteration 1 — Baseline

| Parameter | Value |
|-----------|-------|
| Rank (network_dim) | 64 |
| Alpha (network_alpha) | 32 |
| Learning rate | 1e-4 |
| LR scheduler | constant |
| Max steps | 1000 |
| Optimizer | AdamW |
| Batch size | 1 (grad_accum 4) |
| Guidance scale | 3.5 |
| Estimated time | ~15-20 min on A100 80GB |

```bash
python /workspace/scripts/train_flux_lora.py \
    --dataset /workspace/dataset/processed \
    --output /workspace/models/flux_lora/iter1 \
    --rank 64 --alpha 32 --lr 1e-4 --steps 1000 --optimizer adamw
```

### Iteration 2 — Higher Capacity + Lower LR

If iteration 1 similarity < 0.7:

| Parameter | Value | Change |
|-----------|-------|--------|
| Rank | 128 | 2× capacity for identity features |
| Alpha | 64 | Maintain alpha:rank ratio |
| Learning rate | 5e-5 | Lower for finer convergence |
| Max steps | 1500 | More steps for larger network |
| Optimizer | Prodigy | Adaptive LR |

```bash
python /workspace/scripts/train_flux_lora.py \
    --dataset /workspace/dataset/processed \
    --output /workspace/models/flux_lora/iter2 \
    --rank 128 --alpha 64 --lr 5e-5 --steps 1500 --optimizer prodigy
```

### Iteration 3 — Maximum Identity Fidelity

If iteration 2 similarity still < 0.7:

| Parameter | Value | Change |
|-----------|-------|--------|
| Rank | 128 | Same as iter 2 |
| Alpha | 128 | Alpha = rank (full strength) |
| Learning rate | 2e-5 | Very low for precise convergence |
| Max steps | 2000 | Extended training |
| Optimizer | Prodigy | Adaptive LR |
| LR scheduler | cosine_with_restarts | Avoid getting stuck |
| Warmup steps | 100 | Smooth start |

```bash
python /workspace/scripts/train_flux_lora.py \
    --dataset /workspace/dataset/processed \
    --output /workspace/models/flux_lora/iter3 \
    --rank 128 --alpha 128 --lr 2e-5 --steps 2000 \
    --optimizer prodigy --lr-scheduler cosine_with_restarts --warmup-steps 100
```

Also edit `dataset_config.toml` to increase `num_repeats` from 10 to 15 for iteration 3.

## Inference: Using the LoRA

**IMPORTANT:** Use inference-time `lora_scale` via `cross_attention_kwargs`. Do NOT use `fuse_lora()` — it permanently modifies model weights and prevents scale adjustment.

### Diffusers (Python)

```python
from diffusers import FluxPipeline
import torch

pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-dev", torch_dtype=torch.bfloat16).to("cuda")
pipe.load_lora_weights("models/flux_lora/pytorch_lora_weights.safetensors")

image = pipe(
    "ohwx person in neon-lit Tokyo street, cinematic, 35mm anamorphic",
    height=576, width=1024,
    num_inference_steps=28,
    guidance_scale=3.5,
    cross_attention_kwargs={"scale": 0.9},  # lora_scale 0.8-1.2
).images[0]
```

### ComfyUI

Use a LoraLoader node with `strength_model` set to 0.8-1.2. This applies the LoRA at inference time without fusing.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| OOM on A100 80GB | Add `--fp8-base` flag, reduce batch size |
| OOM on 24GB VRAM | Use `--fp8-base`, reduce rank to 32, reduce resolution to 768×432 |
| Overfitting (artifacts) | Reduce steps, lower lora_scale at inference to 0.7-0.8 |
| Underfitting (poor likeness) | Increase steps, increase rank, increase num_repeats in TOML |
| No face detected in generated images | Check trigger word in prompts, increase lora_scale to 1.0-1.2 |
| Training crashes | Ensure Kohya_ss is up to date, check CUDA version matches PyTorch |

## Files

| File | Purpose |
|------|---------|
| `training_config.toml` | Kohya dataset config (resolution, repeats, captions) |
| `pytorch_lora_weights.safetensors` | Trained LoRA weights (output, gitignored) |
| `iter1/`, `iter2/`, `iter3/` | Per-iteration weight directories |
