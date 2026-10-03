FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "New toolshop/daw/export_chain.py + 'daw export-chain --track N [--master]' subcommand: devices.list + devices.get_params -> FXChain YAML with unresolved-device bypass stages + x_devices/x_unresolved/x_range_warnings metadata." --files "toolshop/daw/ + toolshop/fx/chain.py read-only + tests/test_daw_export_chain.py".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. Read megaplan W2C + toolshop/fx/chain.py + toolshop/daw/daw_cli.py + tests/test_live_bridge.py fakes.
2. export_chain.py: normalize device names (strip '(VST3)/(VST2)/(AU)', '.vst3', trim) -> registry.find_plugin; unresolved -> bypass:true stage + x_unresolved entry; params {name:value} for enabled params; x_devices holds per-device {value,min,max} capture + class_name; instruments -> x_instrument + bypassed stage.
3. daw_cli.py: 'export-chain --track N [--master] [-o out] [--name x]' writing FXChain YAML (chains dir default).
4. tests/test_daw_export_chain.py: canned devices.list/get_params payloads, golden YAML, unresolved handling, Device-On->bypass, master mapping, range warnings. No Live needed.
5. pytest the new file + test_daw.py + test_live_bridge.py regression.
6. If the W1A user gate passed and Live is up: export a real track chain, run 'fx render' + 'fx measure' on a short wav, quote deltas in handoff. Otherwise mark live-proof as pending.
OPEN FILES: toolshop/daw/ + toolshop/fx/chain.py read-only + tests/test_daw_export_chain.py

OUTPUT: Write your handoff to: ORCHESTRATION/fx_wave2/wave2/agent_c_handoff.md

CONSTRAINTS:
- Live-only — no FL support (FL bridge lacks slot enumeration).
- FXChain.from_dict folds unknown STAGE keys into params — metadata must be TOP-LEVEL keys only (x_source, x_devices, x_unresolved).
- param index 0 'Device On' -> stage bypass (not a param).
- bridge master-track support: extend _track() so track=-1 -> song.master_track (shared with W4).

CONTEXT BUDGET: 90k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
