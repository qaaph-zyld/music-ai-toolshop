# fx_wave2 W1B handoff — DawDreamer eval spike

**Date:** 2026-10-03 · **Agent:** Devin session (window 1) · **State:** evidence produced — **USER VERDICT GATE OPEN**

## Installed

`dawdreamer-0.9.0-cp311-cp311-win_amd64.whl` → `.venv` (Python 3.11.9). **GPLv3**. Not added to pyproject/lockfile — that is deliberate, pending adopt sign-off (W3).

## Verdicts (7/7 pass, 0 hard failures)

`data/toolshop/fx/dawdreamer_eval.json`:

| Check | Verdict | Evidence |
|---|---|---|
| dry_gate | ok | playback-only graph bit-exact (-240 dBFS) |
| vst2_fx | ok | Glitch2 x64 VST2 renders wet (max\|Δ\| 0.5 dBFS, 3.9s) |
| vsti_midi | ok | Serum_x64 + 4-bar MIDI arp → -17.5 dBFS |
| automation | ok | set_automation forced 0.0 vs 1.0 → renders differ |
| preset | ok | load_preset(.fxp) loads + mutates render |
| determinism | ok | bit-identical renders |
| parity_perf | ok | pedalboard 1.2ms vs DD ~5-7ms median (≈5x slower), outputs bit-identical (Kickstart ducks probe to silence in BOTH engines) |

## API gotchas discovered (W3 must know)

- `load_graph` takes `(processor, [input_name_strings])` — names via `get_name()`, not objects.
- `load_midi(path, clear_previous, beats, all_events)` — no `convert_to_seconds`.
- `set_automation(index:int, float32 ndarray, ppqn=0)` — constant-value arrays are the unambiguous test; PPQN indexing semantics need care in W3.
- `load_preset(path)` — documented `.fxp` only; `.vstpreset` unsupported by this call.
- `get_plugin_parameters_description()` (plural) → list[dict] with `index,name,isAutomatable,min/max` **as strings**, `defaultValue` float. Kickstart reports 2093 params (many "X (Reserved)").
- VST2 shell init is async — `get_plugin_parameters_description` can race ("Please load the plugin first!"); retry loop (`_wait_ready`) needed.
- No `RenderEngine.reset`; `render()` repeats cleanly (advances transport).
- `engine.get_audio()` returns `(channels, samples)` — transpose vs pedalboard convention.

## Recommendation seed → adopt

All target capabilities verified on real installed plugins: VST2 fx (Glitch2), VSTi+MIDI (Serum), automation lanes, .fxp presets, deterministic renders, subprocess-isolated safety. Cost: ~5x slower than pedalboard per render on a light VST3, GPLv3, `.vstpreset` gap.

**User call required:** adopt / adopt-scoped (VST2+VSTi only) / reject (→ avenue K REAPER note). W3 agent F is gated on this.
