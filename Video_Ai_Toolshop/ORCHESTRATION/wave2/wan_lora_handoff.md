# Wave 2 — Wan 2.2 Video LoRA Trainer Handoff

**Agent:** wan_lora
**Wave:** 2
**Status:** COMPLETE (scripts ready, Track B optional)
**Date:** 2026-08-20

## Deliverables

- `scripts/train_wan_lora.py` — Dual-expert LoRA training orchestration script:
  - Calls musubi-tuner `wan_train_network.py` twice (high-noise + low-noise experts)
  - Two-stage (default, matches Wan 2.2 MoE architecture) or three-stage (optional)
  - CLI args for all hyperparameters (rank, lr, steps, optimizer, model path)
  - fp8 + block swap support for 24GB VRAM (5B model)
  - Auto-generates musubi-tuner dataset TOML from video clip directory
  - Validates dataset (min 10 clips, caption files present, trigger word check)

- `scripts/validate_wan_lora.py` — Identity validation script:
  - Generates test clips using both trained LoRAs via musubi-tuner
  - Extracts frames from generated + reference clips via ffmpeg
  - Computes ArcFace cosine similarity (InsightFace `buffalo_l`)
  - Boosted low-noise scale (1.3x default) for sharper identity
  - Saves JSON report with per-frame similarity scores
  - Supports two-stage and three-stage validation

- `models/wan_lora/training_config.toml` — musubi-tuner dataset config:
  - Resolution 480x720, 12 frames per sample, batch_size 1
  - `keep_tokens=1`, `shuffle_caption=true`, `num_repeats=10`
  - Video clip dir `/workspace/dataset/video_clips`, caption extension `.txt`

- `models/wan_lora/README.md` — Complete training guide:
  - Prerequisites (RunPod, musubi-tuner, model weights)
  - Dataset preparation (10-20 clips, 2-5s, captioning, directory structure)
  - Two-stage training workflow (primary, matching MoE)
  - Three-stage training (optional advanced, mid-noise refinement)
  - A14B vs 5B hyperparameter comparison
  - Budget GPU config (5B + fp8 + block swap on RTX 4090)
  - Inference guidance (load both LoRAs, lora_scale tuning)
  - 3-iteration strategy table
  - Troubleshooting table (OOM, identity drift, motion artifacts)
  - Cost estimate table

- `infra/cloud_setup.md` — **Updated** with musubi-tuner installation:
  - Added `git clone https://github.com/kohya-ss/musubi-tuner.git` + `pip install`
  - Positioned as primary Wan 2.2 trainer, finetrainers as fallback

## Key Decisions

- **musubi-tuner as primary:** Most mature Wan 2.2 support, native fp8/block swap, dual-expert timestep control, best community documentation. Finetrainers remains installed as fallback.
- **Two-stage matches MoE:** Wan 2.2 I2V uses timestep boundary 0.9 — high-noise expert (t>0.9) for composition/motion, low-noise expert (t<0.9) for texture/identity. Training one LoRA per expert is the native approach.
- **Three-stage optional:** Splits low-noise into mid (0.5-0.9) and low (0.0-0.5) for finer motion control. Documented but not default — departs from native MoE boundary.
- **CAME optimizer + LoRAPlus (ratio 4):** Research shows this outperforms AdamW for Wan character LoRA. Lower learning rates (2e-5) consistently beat community defaults (1e-4+).
- **Low-noise scale 1.3x at inference:** Boosted from 1.0 for sharper identity. Research recommends up to 1.5x if drift persists.
- **A14B primary, 5B fallback:** A14B on A100 80GB for best quality ($1.39/hr), 5B on RTX 4090 with fp8 for budget ($0.69/hr). Both already in cloud setup download script.
- **Track B is optional:** Scripts and docs are ready. User activates Track B only if identity drift is observed with Track A (Flux LoRA → Wan I2V).

## Validation Workflow

```bash
# 1. Train dual-expert LoRAs (A100 80GB)
python /workspace/scripts/train_wan_lora.py \
    --dataset /workspace/dataset/video_clips \
    --output /workspace/models/wan_lora \
    --model /workspace/models/Wan2.2-I2V-A14B \
    --rank 32 --lr 2e-5 --steps 2000 --optimizer came

# 2. Validate identity
python /workspace/scripts/validate_wan_lora.py \
    --high-noise-lora /workspace/models/wan_lora/high_noise/pytorch_lora_weights.safetensors \
    --low-noise-lora /workspace/models/wan_lora/low_noise/pytorch_lora_weights.safetensors \
    --reference /workspace/dataset/video_clips \
    --output /workspace/output/test_clips \
    --low-noise-scale 1.3

# 3. If similarity < 0.7, iterate (see models/wan_lora/README.md)
# 4. If similarity >= 0.7, load both LoRAs at inference for video generation
```

## Cost Estimate

| Config | GPU | Time | Cost |
|--------|-----|------|------|
| A14B, 2-stage, 2000 steps | A100 80GB | ~60-90 min | ~$1.40-$2.10 |
| A14B, 3-stage, 2000 steps | A100 80GB | ~90-120 min | ~$2.10-$2.80 |
| 5B, 2-stage, 2000 steps (fp8) | RTX 4090 | ~30-50 min | ~$0.35-$0.58 |

## Next Steps (Wave 4)

When Track B is activated and LoRAs are trained:
1. Load both `.safetensors` in ComfyUI WanVideoWrapper node
2. Set `strength_model = 1.0` for high-noise, `1.3` for low-noise
3. Generate video clips using reference images from Wave 3
4. Compare identity consistency vs Track A (Flux LoRA only)
5. If Track B shows clear improvement, use as primary generation path
