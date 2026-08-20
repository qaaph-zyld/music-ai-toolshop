FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Train HunyuanVideo 1.5 I2V LoRA using official Muon optimizer training code on Kaggle P100 16GB. 10-15 images sufficient for human characters. Upload LoRA weights to HuggingFace Hub." --files "d:/Project/Video_Ai_Toolshop/models/hunyuan_lora/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Train HunyuanVideo 1.5 I2V LoRA using official Muon optimizer training code on Kaggle P100 16GB. 10-15 images sufficient for human characters. Upload LoRA weights to HuggingFace Hub.
OPEN FILES: d:/Project/Video_Ai_Toolshop/models/hunyuan_lora/

OUTPUT: Write your handoff to: ORCHESTRATION/wave2/hunyuan_lora_handoff.md

CONSTRAINTS:
- Optional — Track B. Requires video clips. 14GB VRAM min with offloading.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
