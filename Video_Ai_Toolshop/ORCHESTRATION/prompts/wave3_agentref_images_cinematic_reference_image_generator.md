FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Generate 3-5 cinematic reference images per target scene (10 scenes = 30-50 images) using SDXL + LoRA + Five Pillars prompt framework on Google Colab T4. Output at 1024x576 (16:9) to match HunyuanVideo 1.5 input. Use lora_scale 0.8-1.2 at inference (NOT fuse_lora). Save to Google Drive with metadata." --files "d:/Project/Video_Ai_Toolshop/output/reference_images/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Generate 3-5 cinematic reference images per target scene (10 scenes = 30-50 images) using SDXL + LoRA + Five Pillars prompt framework on Google Colab T4. Output at 1024x576 (16:9) to match HunyuanVideo 1.5 input. Use lora_scale 0.8-1.2 at inference (NOT fuse_lora). Save to Google Drive with metadata.
OPEN FILES: d:/Project/Video_Ai_Toolshop/output/reference_images/

OUTPUT: Write your handoff to: ORCHESTRATION/wave3/ref_images_handoff.md

CONSTRAINTS:
- Depends on Wave 2 sdxl_lora. Generate at HunyuanVideo 1.5 aspect ratio.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
