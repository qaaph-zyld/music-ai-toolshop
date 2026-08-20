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
| 2 | LoRA Training | 2 (flux_lora, wan_lora) | PENDING | Yes |
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
| flux_lora | trainer | `prompts/wave2_agentflux_lora_flux_lora_trainer.md` | `wave2/flux_lora_handoff.md` | COMPLETE |
| wan_lora | trainer | `prompts/wave2_agentwan_lora_wan_2_2_video_lora_trainer.md` | `wave2/wan_lora_handoff.md` | PENDING (optional) |

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

- **Dataset Curator:** Complete curation guide at `dataset/README.md` — photo selection, cropping script (1024×576), captioning guide, Kohya config, validation checklist.
- **Cloud Environment:** Complete RunPod setup at `infra/cloud_setup.md` — template config, install script, model downloads, storage strategy ($10-12/mo), GPU guide, verification commands.
- **ComfyUI Workflows:** 3 workflow JSON files at `workflows/` — basic I2V, camera control (dolly_forward), ControlNet stacking (Depth + OpenPose). ComfyUI pinned to v0.3.22.

**Gate Decision:** Wave 1 outputs are documentation and workflow templates — no GPU execution needed. Ready to proceed to Wave 2 once user provides photos and deploys RunPod instance.

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
