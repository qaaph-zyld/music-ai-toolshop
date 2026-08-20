FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Design ComfyUI workflow JSON for HunyuanVideo 1.5 I2V (14GB VRAM) with camera control and ControlNet stacking. Also design LTX-Video 2B (8GB) fallback workflow. Pin ComfyUI version. Validate against /object_info endpoint." --files "d:/Project/Video_Ai_Toolshop/workflows/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Design ComfyUI workflow JSON for HunyuanVideo 1.5 I2V (14GB VRAM) with camera control and ControlNet stacking. Also design LTX-Video 2B (8GB) fallback workflow. Pin ComfyUI version. Validate against /object_info endpoint.
OPEN FILES: d:/Project/Video_Ai_Toolshop/workflows/

OUTPUT: Write your handoff to: ORCHESTRATION/wave1/comfyui_handoff.md

CONSTRAINTS:
- Read-only. Design workflows only — do not execute.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
