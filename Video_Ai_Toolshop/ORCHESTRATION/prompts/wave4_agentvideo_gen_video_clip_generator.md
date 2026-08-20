FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Generate 5s 720P/24fps cinematic video clips from reference images using HunyuanVideo 1.5 I2V on Google Colab T4 16GB with model offloading. Use anchor-frame workflow: last frame of clip N = first frame of clip N+1. Fallback to LTX-Video 2B if HunyuanVideo OOMs. Save raw clips to Google Drive." --files "d:/Project/Video_Ai_Toolshop/output/raw_video/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Generate 5s 720P/24fps cinematic video clips from reference images using HunyuanVideo 1.5 I2V on Google Colab T4 16GB with model offloading. Use anchor-frame workflow: last frame of clip N = first frame of clip N+1. Fallback to LTX-Video 2B if HunyuanVideo OOMs. Save raw clips to Google Drive.
OPEN FILES: d:/Project/Video_Ai_Toolshop/output/raw_video/

OUTPUT: Write your handoff to: ORCHESTRATION/wave4/video_gen_handoff.md

CONSTRAINTS:
- Depends on Wave 3. 16GB VRAM — use model offloading. Save clips immediately (Colab disconnects).

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
