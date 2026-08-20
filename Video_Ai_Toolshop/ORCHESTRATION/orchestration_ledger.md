# Orchestration Ledger — Cinematic AI Character Video Pipeline

**Task:** Cinematic AI Character Video Pipeline
**Project root:** `d:/Project/Video_Ai_Toolshop`
**Orchestration dir:** `ORCHESTRATION`
**Created:** 2026-08-20

---

## Wave Status

| Wave | Name | Agents | Status | Gate |
|------|------|--------|--------|------|
| 1 | Parallel Setup | 3 (dataset, cloud, comfyui) | COMPLETE | Yes |
| 2 | LoRA Training | 2 (sdxl_lora, hunyuan_lora) | PENDING | Yes |
| 3 | Reference Image Generation | 1 (ref_images) | PENDING | Yes |
| 4 | Video Generation + Post-Processing Setup | 2 (video_gen, postproc_setup) | PENDING | Yes |
| 5 | Post-Processing + Assembly | 2 (postproc, assembly) | PENDING | No |

---

## Agent Handoff Tracking

### Wave 1 — Parallel Setup

| Agent | Role | Prompt File | Handoff File | Status |
|-------|------|-------------|--------------|--------|
| dataset | preparer | `prompts/wave1_agentdataset_dataset_curator.md` | `wave1/dataset_handoff.md` | COMPLETE |
| cloud | engineer | `prompts/wave1_agentcloud_cloud_environment_setup.md` | `wave1/cloud_handoff.md` | COMPLETE |
| comfyui | engineer | `prompts/wave1_agentcomfyui_comfyui_workflow_designer.md` | `wave1/comfyui_handoff.md` | COMPLETE |

### Wave 2 — LoRA Training

| Agent | Role | Prompt File | Handoff File | Status |
|-------|------|-------------|--------------|--------|
| sdxl_lora | trainer | `prompts/wave2_agentsdxl_lora_sdxl_lora_trainer.md` | `wave2/sdxl_lora_handoff.md` | PENDING |
| hunyuan_lora | trainer | `prompts/wave2_agenthunyuan_lora_hunyuanvideo_lora_trainer.md` | `wave2/hunyuan_lora_handoff.md` | PENDING (optional Track B) |

### Wave 3 — Reference Image Generation

| Agent | Role | Prompt File | Handoff File | Status |
|-------|------|-------------|--------------|--------|
| ref_images | generator | `prompts/wave3_agentref_images_cinematic_reference_image_generator.md` | `wave3/ref_images_handoff.md` | PENDING |

### Wave 4 — Video Generation + Post-Processing Setup

| Agent | Role | Prompt File | Handoff File | Status |
|-------|------|-------------|--------------|--------|
| video_gen | generator | `prompts/wave4_agentvideo_gen_video_clip_generator.md` | `wave4/video_gen_handoff.md` | PENDING |
| postproc_setup | engineer | `prompts/wave4_agentpostproc_setup_post_processing_pipeline_setup.md` | `wave4/postproc_handoff.md` | PENDING |

### Wave 5 — Post-Processing + Assembly

| Agent | Role | Prompt File | Handoff File | Status |
|-------|------|-------------|--------------|--------|
| postproc | processor | `prompts/wave5_agentpostproc_video_post_processor.md` | `wave5/postproc_handoff.md` | PENDING |
| assembly | editor | `prompts/wave5_agentassembly_final_assembly_editor.md` | `wave5/assembly_handoff.md` | PENDING |

---

## Wave Synthesis Notes

### Wave 1 Synthesis

All 3 Wave 1 agents completed. Deliverables:

- **Dataset Curator:** Complete curation guide at `dataset/README.md` — photo selection, cropping script (1024×576), captioning guide, Kohya config, validation checklist. Updated for SDXL.
- **Cloud Environment:** Free-tier setup at `infra/free_tier_setup.md` — Kaggle P100 16GB (30h/week), Google Colab T4 16GB, HuggingFace Hub, Google Drive 15GB. $0 total cost.
- **ComfyUI Workflows:** 5 workflow JSON files at `workflows/` — HunyuanVideo 1.5 I2V, LTX-Video 2B fallback, plus legacy Wan 2.2 workflows. ComfyUI pinned to v0.3.22.
- **Notebooks:** `notebooks/kaggle_train_sdxl_lora.ipynb` (training) and `notebooks/colab_generate_video.ipynb` (generation + post-processing).

**Gate Decision:** Wave 1 updated for zero-cost pipeline. Ready to proceed to Wave 2 once user uploads photos to HuggingFace/Google Drive.

### Wave 2 Synthesis
*(To be filled after Wave 2 agents complete)*

### Wave 3 Synthesis
*(To be filled after Wave 3 agents complete)*

### Wave 4 Synthesis
*(To be filled after Wave 4 agents complete)*

### Wave 5 Synthesis
*(To be filled after Wave 5 agents complete)*

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-20 | Wan 2.2 as primary video model | Best open-source cinematic quality, Apache 2.0 |
| 2026-08-20 | Flux.1-dev as image LoRA base | Best photorealism (non-commercial) |
| 2026-08-20 | 5-wave orchestration design | Natural decomposition of pipeline stages |
| 2026-08-20 | Gate after Waves 1-4 | User review checkpoints for quality control |
| 2026-08-20 | **PIVOT: Zero-cost pipeline** | User has GTX 950M (no local GPU). Switched to free-tier: HunyuanVideo 1.5 + SDXL on Kaggle P100 + Colab T4 |
| 2026-08-20 | HunyuanVideo 1.5 replaces Wan 2.2 | 14GB VRAM fits free tier, same ⭐⭐⭐⭐⭐ quality |
| 2026-08-20 | SDXL replaces Flux.1-dev | 8GB VRAM fits free tier, mature LoRA ecosystem |
| 2026-08-20 | LTX-Video 2B as fallback | 8GB VRAM if HunyuanVideo OOMs on 16GB |
