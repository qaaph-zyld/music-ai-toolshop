FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Set up free-tier cloud environment: Kaggle P100 16GB for training, Google Colab T4 16GB for generation, HuggingFace Hub for model storage, Google Drive 15GB for dataset/outputs. Document notebook setup and session management strategy." --files "d:/Project/Video_Ai_Toolshop/infra/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Set up free-tier cloud environment: Kaggle P100 16GB for training, Google Colab T4 16GB for generation, HuggingFace Hub for model storage, Google Drive 15GB for dataset/outputs. Document notebook setup and session management strategy.
OPEN FILES: d:/Project/Video_Ai_Toolshop/infra/

OUTPUT: Write your handoff to: ORCHESTRATION/wave1/cloud_handoff.md

CONSTRAINTS:
- Read-only. Document setup steps only — do not rent GPUs.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
