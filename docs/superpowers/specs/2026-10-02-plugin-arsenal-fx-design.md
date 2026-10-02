# Plugin Arsenal FX — `toolshop fx` + Ableton Live bridge

**Date:** 2026-10-02
**Status:** Implemented (Answer #082)
**Plan:** `.workspace_archive/plans/` — megaplan `plugin-arsenal-fx`

## Problem

The machine has ~570 plugins installed (full FabFilter, Ozone 10, RX 10,
Auto-Tune Pro + AVOX, Valhalla suite, Waves V14, Slate, UAD 1176, Kickstart 2,
Glitch2) plus FL Studio 21 and Ableton Live 12 Suite — but the toolshop could
only reach them *live* inside a running FL session (`toolshop daw`), and the
offline Chain DSL only rendered pedalboard's stock effects. No way to batch a
directory of studio audio through the real arsenal.

## Design

Two lanes, one approved decision set: headless VST3 (third-party arsenal),
YAML chains, files + directories, new `toolshop fx` command group, and an
Ableton twin of the FL TCP bridge.

### Lane A — `toolshop/fx/` (headless render)

| Module | Responsibility |
|---|---|
| `registry.py` | Pure-filesystem scan of the shared plugin roots (`daw.plugins.plugin_directories()`) + Waves `Plug-Ins V14/*.bundle` enumeration → `plugin_registry.json`. **Never loads a plugin** — WaveShell bare-load was measured to hang >210 s, so shell members resolve to `path=WaveShell` + `plugin_name=<bundle>` at render time. |
| `probe_one.py` / `probe.py` | Per-plugin capability audit in a **subprocess** (crash isolation) with hard timeouts (60 s, 120 s for shells). Renders a level-staircase + impulse + noise probe signal; verdicts `ok` / `dry` / `load-failed` / `render-failed` / `timeout` / `crash` / `needs-ui`, with full parameter dumps. |
| `chain.py` | `FXChain` YAML schema: ordered `stages`, each `{plugin: name, params: {…}}` or `{builtin: hpf|eq|comp|deesser|clip|limit}` (existing Chain DSL field names). `validate()` resolves plugins via the registry, fails loud on unknown/unhostable. |
| `engine.py` | pedalboard hosting: resample input to chain SR, param-by-name set (unknown name → error, never silent), 4 s tail flush, `assert_wet` guard (max\|Δ\| ≤ −80 dBFS → `DryRenderError`), optional per-chain/plugin instance cache unless `stateful: true`. |
| `batch_fx.py` | Resumable directory render — thin adapter over shared `toolshop.batch` (`discover_files`, status JSON, limit/offset). |
| `fx_cli.py` | `toolshop fx scan · probe · params · chains · render · batch · measure` — measure reuses `premaster.analyze_premaster` (LUFS / TP / PSR deltas). |

Artifacts live under `data/toolshop/fx/` (gitignored data boundary).

### Lane B — Ableton Live bridge

`toolshop/daw/live_bridge_script.py` — a Live 12 Remote Script
(`_Framework.ControlSurface`) running the **same** length-prefixed JSON-RPC 2.0
protocol as the FL bridge, on port **9878**. `DAWClient(port=9878)` works
unmodified. Commands queue from the accept thread and drain on Live's main
thread via `schedule_message` (LOM is not thread-safe — mirrors the FL
`OnIdle` pattern).

Method names match FL where semantics match (`system.*`, `transport.*`,
`mixer.*`, `plugins.*`→device aliases) plus Live-only `tracks.list`,
`scenes.list/fire`, `clips.list/fire/stop`, `devices.list/get_params/set_param`
(by index or name).

Install: copy the file as `__init__.py` into
`%APPDATA%\Ableton\Live 12.x\Preferences\User Remote Scripts\ToolshopLive\`,
pick `ToolshopLive` as a Control Surface in Live's Link/Tempo/MIDI prefs.

## Explicit limits (by design)

- FL/Ableton **native** devices can't render headless — third-party VST3 only.
- **VST2** (Glitch2, 208 entries) is marked `hostable: false`; a VST2 host
  (DawDreamer) is a new dependency requiring OSS-map sign-off — deferred.
- No `.vstpreset` loading — params are YAML name/value; dump names via
  `fx params` (probe DB or live load fallback).
- Probe verdict `dry` means "this signal didn't move" — frequency-selective
  processors (de-essers) legitimately score dry; it is a flag, not a failure.
- Param capture *from* live DAW sessions and ARA workflows are deferred.

## Verification

- 26 fx tests + 13 live-bridge tests (incl. real TCP roundtrip through
  `DAWClient`); `test_daw.py` 143/143 unchanged.
- `fx scan` on the real machine: 571 entries, 355 hostable (227 Waves members
  enumerated from bundles, zero shell loads).
- End-to-end: `fx render`/`measure`/`params`/`probe --only` all run.
