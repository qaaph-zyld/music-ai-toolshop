FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Train SDXL DreamBooth LoRA on curated dataset using Kohya_ss on Kaggle P100 16GB. Use fp16 + gradient checkpointing to fit 16GB VRAM. Validate identity with ArcFace cosine similarity (>0.7 = good). Upload LoRA weights to HuggingFace Hub." --files "d:/Project/Video_Ai_Toolshop/models/sdxl_lora/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Train SDXL DreamBooth LoRA on curated dataset using Kohya_ss on Kaggle P100 16GB. Use fp16 + gradient checkpointing to fit 16GB VRAM. Validate identity with ArcFace cosine similarity (>0.7 = good). Upload LoRA weights to HuggingFace Hub.
OPEN FILES: d:/Project/Video_Ai_Toolshop/models/sdxl_lora/

OUTPUT: Write your handoff to: ORCHESTRATION/wave2/sdxl_lora_handoff.md

CONSTRAINTS:
- Use inference-time lora_scale, NOT fuse_lora(). Expect 2-3 iterations. Kaggle 30h/week limit.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
