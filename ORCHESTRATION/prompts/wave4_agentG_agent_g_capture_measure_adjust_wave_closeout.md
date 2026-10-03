FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "'daw capture --measure' (premaster report) + '--target-lufs X --apply' one bounded adjust pass via mixer.set_volume/devices.set_param; then wave closeout." --files "toolshop/daw/ + tests + CHANGELOG/README + handoffs".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. measure_loop.py: capture -> premaster.analyze_premaster report (LUFS/TP/PSR) -> if --apply: compute nudge, apply via bridge, re-capture, re-measure, report both.
2. Tests mock capture + client.
3. Closeout checklist per AGENTS.md; paste closeout evidence block in handoff; write .windsurf/handoffs/ + .workspace_archive/handoffs/ entries; update ACTIVE override.
OPEN FILES: toolshop/daw/ + tests + CHANGELOG/README + handoffs

OUTPUT: Write your handoff to: ORCHESTRATION/fx_wave2/wave4/agent_g_handoff.md

CONSTRAINTS:
- ONE bounded adjust pass in v1 — no convergence loop; second pass = re-run.
- Master-track volume uses the shared track=-1 bridge extension.
- Closeout: 'toolshop closeout' exit 0, full pytest, CHANGELOG committed WITH code, handoff + session_end.

CONTEXT BUDGET: 45k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
