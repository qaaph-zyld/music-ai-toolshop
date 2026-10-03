FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Persist 'fx params' live-load fallback dumps into plugin_probes.json so a plugin is probed once and cached forever." --files "toolshop/fx/fx_cli.py + probe.py + tests".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. In fx_cli.py params fallback: after live-load dump, merge a minimal probe record {name,path,format,parameters,verdict:'params-only'} via probe.save_probe_db / merge_probe_into_registry.
2. Test: params command writes probe record; second call reads cache without loading plugin (mock engine.load_plugin_stage).
3. Handoff with before/after probe-db evidence.
OPEN FILES: toolshop/fx/fx_cli.py + probe.py + tests

OUTPUT: Write your handoff to: ORCHESTRATION/fx_wave2/wave2/agent_e_handoff.md

CONSTRAINTS:
- Optional lane — skip if wave budget tight.
- Only the params fallback path; do not trigger a corpus-wide probe.

CONTEXT BUDGET: 30k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
