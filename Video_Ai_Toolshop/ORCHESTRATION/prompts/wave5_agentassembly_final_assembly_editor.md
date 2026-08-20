FRAMEWORK BOOTSTRAP (v12) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Assemble processed clips in DaVinci Resolve 21. Add audio (ElevenLabs for TTS, Suno/Udio for music, Freesound for SFX). Color grade with Shot Match + cinematic LUTs. Export 4K master + vertical social cuts." --files "d:/Project/Video_Ai_Toolshop/output/final/".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: Assemble processed clips in DaVinci Resolve 21. Add audio (ElevenLabs for TTS, Suno/Udio for music, Freesound for SFX). Color grade with Shot Match + cinematic LUTs. Export 4K master + vertical social cuts.
OPEN FILES: d:/Project/Video_Ai_Toolshop/output/final/

OUTPUT: Write your handoff to: ORCHESTRATION/wave5/assembly_handoff.md

CONSTRAINTS:
- Depends on postproc. Manual editing in DaVinci Resolve.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
