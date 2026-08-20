# Video AI Toolshop

End-to-end pipeline for generating cinematic AI character videos from your photos using open-source models — **100% free** on Kaggle P100 + Google Colab T4.

## Quick Start

1. **Read the free-tier setup:** `infra/free_tier_setup.md`
2. **Read the orchestration ledger:** `ORCHESTRATION/orchestration_ledger.md`
3. **Upload photos** to Google Drive or HuggingFace dataset repo
4. **Open Kaggle notebook:** `notebooks/kaggle_train_sdxl_lora.ipynb` — train LoRA
5. **Open Colab notebook:** `notebooks/colab_generate_video.ipynb` — generate + post-process

## Architecture

```
Photos → SDXL LoRA Training (Kaggle P100) → Cinematic Reference Images (Colab T4) → HunyuanVideo 1.5 I2V (Colab T4) → Post-Process → Final Video
```

**Three tracks:**
- **Track A (Primary):** Image LoRA → I2V generation
- **Track B (Optional):** Direct video LoRA for better temporal identity
- **Track C (Fallback):** Tuning-free identity preservation (HunyuanCustom/ConsisID)
- **Track D (Bonus):** Video-to-video character replacement (Wan-Animate-14B)

## Project Structure

```
Video_Ai_Toolshop/
├── research/              # 4 research handoff documents
├── ORCHESTRATION/         # Wave orchestration
│   ├── waves.json         # Wave definition
│   ├── orchestration_ledger.md
│   ├── prompts/           # Copy-paste bootstrap prompts per agent
│   ├── wave1/             # Wave 1 handoffs
│   ├── wave2/             # Wave 2 handoffs
│   ├── wave3/             # Wave 3 handoffs
│   ├── wave4/             # Wave 4 handoffs
│   └── wave5/             # Wave 5 handoffs
├── dataset/               # Curated photos + captions
├── infra/                 # Cloud environment setup docs
├── workflows/             # ComfyUI workflow JSON files
├── models/
│   ├── sdxl_lora/         # Trained SDXL LoRA weights
│   └── hunyuan_lora/      # Trained HunyuanVideo LoRA weights (optional Track B)
├── notebooks/             # Kaggle + Colab notebooks
├── output/
│   ├── reference_images/  # Generated cinematic reference images
│   ├── raw_video/         # Raw AI-generated video clips
│   ├── processed_video/   # Post-processed clips (upscaled, interpolated)
│   └── final/             # Final assembled videos
└── scripts/
    ├── postproc/          # Post-processing pipeline scripts
    ├── generate_references.py  # SDXL reference image generation
    ├── generate_videos.py      # HunyuanVideo 1.5 clip generation
    ├── train_sdxl_lora.py      # SDXL LoRA training wrapper
    └── validate_identity.py    # ArcFace identity validation
```

## Key Models

| Model | Purpose | License | VRAM | Free Tier |
|-------|---------|---------|------|-----------|
| HunyuanVideo 1.5 | Video generation (primary) | Open weights | 14GB min | ✅ Kaggle P100 / Colab T4 |
| LTX-Video 2B | Video generation (fallback) | Apache 2.0 | 8GB | ✅ Colab T4 |
| SDXL | Image generation + LoRA | CreativeML Open RAIL++-M | 8GB | ✅ Kaggle P100 / Colab T4 |

## Cost

**$0** — entirely free on Kaggle P100 (30h/week) + Google Colab T4 + HuggingFace Hub + Google Drive 15GB.

Quality: ~85-90% of the paid RunPod A100 pipeline. Main tradeoff is speed (2-3x slower) and session management (no persistent storage).

## Research Sources

- `research/researcher_sota_video_models_20260820_200000.md`
- `research/researcher_video_lora_consistency_20260820_200000.md`
- `research/researcher_cinematic_control_20260820_200000.md`
- `research/researcher_pipeline_infrastructure_20260820_200000.md`
