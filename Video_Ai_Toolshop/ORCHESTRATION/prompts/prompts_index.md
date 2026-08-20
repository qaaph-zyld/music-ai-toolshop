# Orchestration Prompts Index

**Task**: Cinematic AI Character Video Pipeline
**Project root**: `d:/Project/Video_Ai_Toolshop`
**Orchestration dir**: `ORCHESTRATION`

| Wave | Agent | Role | Name | Prompt File | Output |
|------|-------|------|------|-------------|--------|
| 1 | dataset | preparer | Dataset Curator | `wave1_agentdataset_dataset_curator.md` | `wave1/dataset_handoff.md` |
| 1 | cloud | engineer | Cloud Environment Setup | `wave1_agentcloud_cloud_environment_setup.md` | `wave1/cloud_handoff.md` |
| 1 | comfyui | engineer | ComfyUI Workflow Designer | `wave1_agentcomfyui_comfyui_workflow_designer.md` | `wave1/comfyui_handoff.md` |
| 1 | — | GATE | **Human approval required** | — | — |
| 2 | flux_lora | trainer | Flux LoRA Trainer | `wave2_agentflux_lora_flux_lora_trainer.md` | `wave2/flux_lora_handoff.md` |
| 2 | wan_lora | trainer | Wan 2.2 Video LoRA Trainer | `wave2_agentwan_lora_wan_2_2_video_lora_trainer.md` | `wave2/wan_lora_handoff.md` |
| 2 | — | GATE | **Human approval required** | — | — |
| 3 | ref_images | generator | Cinematic Reference Image Generator | `wave3_agentref_images_cinematic_reference_image_generator.md` | `wave3/ref_images_handoff.md` |
| 3 | — | GATE | **Human approval required** | — | — |
| 4 | video_gen | generator | Video Clip Generator | `wave4_agentvideo_gen_video_clip_generator.md` | `wave4/video_gen_handoff.md` |
| 4 | postproc_setup | engineer | Post-Processing Pipeline Setup | `wave4_agentpostproc_setup_post_processing_pipeline_setup.md` | `wave4/postproc_handoff.md` |
| 4 | — | GATE | **Human approval required** | — | — |
| 5 | postproc | processor | Video Post-Processor | `wave5_agentpostproc_video_post_processor.md` | `wave5/postproc_handoff.md` |
| 5 | assembly | editor | Final Assembly Editor | `wave5_agentassembly_final_assembly_editor.md` | `wave5/assembly_handoff.md` |

## Wave Summary

- **Wave 1**: Parallel Setup (3 agents, parallel + GATE)
- **Wave 2**: LoRA Training (2 agents, parallel + GATE)
- **Wave 3**: Reference Image Generation (1 agents, sequential + GATE)
- **Wave 4**: Video Generation + Post-Processing Setup (2 agents, parallel + GATE)
- **Wave 5**: Post-Processing + Assembly (2 agents, sequential)
