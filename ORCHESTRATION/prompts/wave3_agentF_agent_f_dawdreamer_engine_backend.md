FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "engine_dd.py + chain schema (engine/preset/automation/instrument+midi) + registry hostable_by + --engine CLI + probe --engine; VST2/VSTi/automation/preset unlock." --files "toolshop/fx/ + tests/test_fx_engine_dd.py + pyproject.toml + requirements.lock.txt + specs + README/CHANGELOG".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. Read megaplan W3 + engine.py + chain.py + registry.py + eval JSON evidence.
2. engine_dd.py: RenderEngine + linear processor graph; params by name; set_automation for 'automation:' stage blocks; load_preset for 'preset:'; assert_wet + tail flush parity.
3. chain.py: 'engine' field (default pedalboard); stage 'preset:', 'automation:' ([{time_beats|time_seconds, value}]), 'instrument: true' + chain 'midi:' (file or inline notes) for VSTi->audio feeding downstream stages.
4. registry.py: 'hostable_by' per entry (vst3->[pedalboard,dawdreamer], vst2->[dawdreamer], vst3-shell->[pedalboard]); version 2; validate(chain, reg) engine-aware.
5. probe_one --engine dawdreamer so VST2 params reach plugin_probes.json.
6. fx_cli: --engine on render/batch/params/probe.
7. pyproject: 'fx' extra [pedalboard>=0.9, dawdreamer==0.9.0, pyyaml, librosa, soundfile, pyloudnorm]; add to 'all'; regen requirements.lock.txt.
8. Spec 2026-10-02 limits amended (VST2/presets/automation/VSTi scope per adopted verdict); README + CHANGELOG #084+.
9. Append evidence-citation block for v2 OSS G1/W4b (music_toolshop_v2/ORCHESTRATION/oss_scout/ledger.md or .workspace_archive/reviews/) — flag the cross-repo write in handoff.
10. tests: importorskip('dawdreamer'); real-plugin tests @pytest.mark.slow; full suite green.
OPEN FILES: toolshop/fx/ + tests/test_fx_engine_dd.py + pyproject.toml + requirements.lock.txt + specs + README/CHANGELOG

OUTPUT: Write your handoff to: ORCHESTRATION/fx_wave2/wave3/agent_f_handoff.md

CONSTRAINTS:
- GATE: only runs after user reviews dawdreamer_eval.json and signs off 'adopt' (scoped or full). If reject: document REAPER (avenue K) fallback note instead — no code.
- chain 'engine:' defaults to pedalboard — backwards compatible; preset/automation/instrument under pedalboard = hard error.
- WaveShell under DawDreamer out of scope.
- dawdreamer==0.9.0 pin + GPLv3 license-ledger row + OSS-map T7 row update.
- Registry version bump 1->2 with load() tolerant of v1.

CONTEXT BUDGET: 110k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
