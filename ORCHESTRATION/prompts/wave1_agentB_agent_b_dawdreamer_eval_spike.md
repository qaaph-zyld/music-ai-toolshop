FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Install dawdreamer==0.9.0 into the umbrella .venv, write toolshop/fx/dawdreamer_eval.py (subprocess-isolated checks), run it, emit data/toolshop/fx/dawdreamer_eval.json + verdict summary for the user's adopt/reject gate." --files "toolshop/fx/ + tests/test_fx_dawdreamer_eval.py + .venv install".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. pip install dawdreamer==0.9.0 into .venv; record wheel tag. License GPLv3 — note for ledger.
2. Write toolshop/fx/dawdreamer_eval.py: checks = vst2_fx (Glitch2_64bit render probe signal, pass max|delta|>-80dBFS), vsti (Serum_x64 + 4-bar MIDI clip, pass RMS>-60dBFS), automation (ramped param -> output differs first vs second half), preset (load .fxp/.vstpreset from disk, no error + state delta), determinism (two renders identical), parity_perf (same VST3 via pedalboard vs dawdreamer, warmup + repeated baseline), dry_gate.
3. Eval plugins (from plugin_registry.json): Glitch2 = C:/Program Files/VstPlugins/Glitch2_64bit/Glitch2.dll; Serum_x64 = C:/Program Files/Steinberg/VstPlugins/Serum_x64.dll; VST3 parity arm = first hostable non-shell entry (e.g. Kickstart 2 VST3).
4. Write tests/test_fx_dawdreamer_eval.py — importorskip('dawdreamer'), unit tests for eval harness logic (verdict mapping, JSON schema), real-plugin checks @pytest.mark.slow.
5. Run the eval; write data/toolshop/fx/dawdreamer_eval.json {check, verdict, evidence, wall_s} + printed summary.
6. Handoff: per-check verdicts, wheel tag, timings, recommendation seed (adopt/adopt-scoped/reject) — user makes the call at the gate.
OPEN FILES: toolshop/fx/ + tests/test_fx_dawdreamer_eval.py + .venv install

OUTPUT: Write your handoff to: ORCHESTRATION/fx_wave2/wave1/agent_b_handoff.md

CONSTRAINTS:
- Use the venv Python: .venv\Scripts\python.exe — NEVER global 3.13 (AGENTS.md hard rule). If no cp311 win_amd64 wheel: verdict 'blocked-env', stop, record.
- Every plugin load inside a subprocess (probe.py pattern) with hard timeout — a plugin crash must not kill the eval.
- Measurement discipline: warmup run + baseline repeated at end; >10% baseline drift = 'inconclusive', never a number.
- Do NOT edit chain.py/registry.py/engine.py — eval only, integration is W3 behind the adopt gate.

CONTEXT BUDGET: 75k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
