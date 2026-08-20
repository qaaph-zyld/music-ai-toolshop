# Video AI Toolshop

End-to-end pipeline for generating cinematic AI character videos from your photos using open-source models on cloud GPU.

## Quick Start

1. **Read the plan:** `C:\Users\cc\.windsurf\plans\cinematic-ai-character-video-pipeline-81354c.md`
2. **Read the orchestration ledger:** `ORCHESTRATION/orchestration_ledger.md`
3. **Dispatch Wave 1:** Open the 3 prompt files in `ORCHESTRATION/prompts/wave1_*.md` in separate Cascade threads

## Architecture

```
Photos → Flux LoRA Training → Cinematic Reference Images → Wan 2.2 I2V → Post-Process → Final Video
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
│   ├── flux_lora/         # Trained Flux LoRA weights
│   └── wan_lora/          # Trained Wan 2.2 video LoRA weights
├── output/
│   ├── reference_images/  # Generated cinematic reference images
│   ├── raw_video/         # Raw AI-generated video clips
│   ├── processed_video/   # Post-processed clips (upscaled, interpolated)
│   └── final/             # Final assembled videos
└── scripts/
    └── postproc/          # Post-processing pipeline scripts
```

## Key Models

| Model | Purpose | License | VRAM |
|-------|---------|---------|------|
| Wan 2.2 I2V-A14B | Video generation | Apache 2.0 | 80GB (full) / 24GB (5B) |
| Flux.1-dev | Image generation + LoRA | Non-commercial | 24GB |
| Flux.1-schnell | Image generation (commercial) | Apache 2.0 | 24GB |
| HunyuanVideo 1.5 | Alternative video gen | Tencent (research) | 14GB min |

## Cost Estimate

~$20-30 for 10 cinematic scenes (Track A, including 2-3 LoRA training iterations).
~$10-12/month model storage on RunPod.

## Research Sources

- `research/researcher_sota_video_models_20260820_200000.md`
- `research/researcher_video_lora_consistency_20260820_200000.md`
- `research/researcher_cinematic_control_20260820_200000.md`
- `research/researcher_pipeline_infrastructure_20260820_200000.md`
