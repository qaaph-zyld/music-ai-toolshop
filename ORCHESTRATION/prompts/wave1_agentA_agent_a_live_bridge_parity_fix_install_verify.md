FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Fix plugins.* FL-parity in live_bridge_script.py (param_index kwarg + get_param_name), add 'daw bridge-install' subcommand, copy script to Live 12.1.11 User Remote Scripts, run bridge tests, hand user the Control-Surface prefs gate, verify 'daw --port 9878 status'." --files "toolshop/daw/ + tests/test_live_bridge.py + %APPDATA%/Ableton".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. Read AGENTS.md (repo root) + megaplan section W1A.
2. In live_bridge_script.py: rename _plugins_get_param/_plugins_set_param kwarg 'param' -> 'param_index'; add 'plugins.get_param_name' handler returning {'name': p.name, 'param': idx} via _device(track, slot).parameters[param_index].
3. Extend tests/test_live_bridge.py: fake-tree roundtrip covering plugins.get_param / get_param_name / set_param with param_index kwargs (the exact kwargs toolshop/daw/plugins.py sends).
4. Add 'bridge-install' subcommand in daw_cli.py: copy live_bridge_script.py -> %APPDATA%/Ableton/Live 12.1.11/Preferences/User Remote Scripts/ToolshopLive/__init__.py AND Live 12.2 path; report installed/updated/stale-diff; print manual prefs steps.
5. Run: .venv\Scripts\python.exe -m pytest tests/test_live_bridge.py -v
6. Run install, then hand the user the prefs gate; after user confirms, run: .venv\Scripts\python.exe -m toolshop.cli daw --port 9878 status + tracks.list smoke.
7. Write handoff with exact commands, exit codes, outputs, and whether the user gate is open/passed.
OPEN FILES: toolshop/daw/ + tests/test_live_bridge.py + %APPDATA%/Ableton

OUTPUT: Write your handoff to: ORCHESTRATION/fx_wave2/wave1/agent_a_handoff.md

CONSTRAINTS:
- Use the venv Python: .venv\Scripts\python.exe (3.11.9).
- Stage only lane-owned paths; ~51 foreign dirty paths exist — never stage/clean/reset them.
- USER GATE: Control Surface selection in Live prefs is manual — agent verifies afterward, cannot do it.
- Do NOT commit — ledger records state; commits happen at wave gates.

CONTEXT BUDGET: 75k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
