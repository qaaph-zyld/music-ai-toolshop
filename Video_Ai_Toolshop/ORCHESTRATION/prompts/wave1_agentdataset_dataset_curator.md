FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Curate 25-30 photos, crop to 1024x576 (16:9) or 1024x1024 (square), write captions with trigger word, package for Google Drive upload" --files "d:/Project/Video_Ai_Toolshop/dataset/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Curate 25-30 photos, crop to 1024x576 (16:9) or 1024x1024 (square), write captions with trigger word, package for Google Drive upload
OPEN FILES: d:/Project/Video_Ai_Toolshop/dataset/

OUTPUT: Write your handoff to: ORCHESTRATION/wave1/dataset_handoff.md

CONSTRAINTS:
- Read-only on research files. Write only to dataset/ directory.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
