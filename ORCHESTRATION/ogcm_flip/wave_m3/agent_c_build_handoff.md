# Wave m3 (W2 + W3) — Kit audit, 808 retune, arrange.py, dual-grid renders — Agent C handoff

**Status:** DONE — both grid arms rendered and verified; no arm-B early-exit needed.
**Wave:** m3 (W2 kit audit + 808 retune; W3 arrange.py + dual-grid renders) of the OGCM flip megaplan.
**Repo:** `d:/Projects/Music-AI-Toolshop` · **Commit:** `150db80` — `feat(#060): ogcm flip m3 - W2 kit audit + 808 retune, W3 arrange.py + dual-grid renders`
**Python:** `.venv/Scripts/python.exe` (3.11.9), CPU-only, no installs this wave.

## GATE C2 pick applied (user audition 2026-09-28, hidden-manifest resolution)

- **Arm `felt_89`** (178.2 written / 89.1 felt): **Lane B** interpolated bed — `stems/flip_bed_lanes/midi/region_63_66_cleaned_Dm.mid` → `bed_lanes` epiano voice, D minor.
- **Arm `triplet_133`** (133.65): **Lane C** programmed motifs as section alternates — `motif_dm_1` (pad, D minor) on verse blocks, `motif_csm_1` (epiano, C# minor) on hook blocks.
- **Lane A (chops): not used.** Hook = `backing_vocals`-driven; arrangements reserve hook sections (thinned bed + mute-drop) — vocal placement is m4's job.

## Task 1 — Kit audit (A29)

New `drums.audit_kit_manifest` checks every piece's kept reps against `MIN_ONESHOT_PEAK=0.01` / `USABLE_ONESHOT_PEAK=0.05` plus file existence → written to `Stemmeca_alatkka/stems/flip_kit/kit_audit.json` (gitignored data).

```
$ python -c "... audit_kit_manifest(manifest, kit_dir=kit) ..."
cymbal  weak  max_peak=0.0263  files_exist=True  src_rms=0.000299
hat     pass  max_peak=0.7316  files_exist=True  src_rms=0.027906
kick    pass  max_peak=0.7145  files_exist=True  src_rms=0.09732
openhat pass  max_peak=0.104   files_exist=True  src_rms=0.000766
snare   pass  max_peak=0.7925  files_exist=True  src_rms=0.031198
tom     pass  max_peak=0.4932  files_exist=True  src_rms=0.005548
ok= True  weak= ['cymbal']  failed= []          (exit code 0)
```

- All 6 pieces kept hits ≥ MIN_PEAK — **no re-mining, no fallback invoked** (m1's spot-check confirmed programmatically, file existence added).
- `cymbal` (crash stem, src_rms 0.0003 — near noise floor) flagged **weak**: best rep 0.0263 is thin. Declared mitigation in `kit_audit.json` + code: crash is used only as a section-downbeat accent; `openhat` (ride, 0.104) carries sustained cymbal duties. The heuristic `classify_hit` remains the **declared-only** fallback (`drums.CLASSIFIER_FALLBACK`, "must be requested explicitly — never auto-selected") per the lane rule.
- Kit loading helper `drums.load_kit_buffers(kit_dir, manifest, rep=1)` → piece→buffer for the render layer.

## Task 2 — `bass808.py` retune

- Glide window tightened to the drill spec: `GLIDE_MS_MIN=90 / GLIDE_MS_MAX=200`, `GLIDE_MS_DEFAULT 240→140 ms`; `render_arm` refuses glide values outside the window (tested).
- New `plan_808_line(kick_times, bpm, root_note, ...)`: one mono-legato note per kick (strictly increasing onsets); per 4-bar block it raises the note preceding 2 (or 3) evenly-spread target kicks by m3/P4 (`SLIDE_INTERVALS_ST=(3,5)`) so the slide **lands on the kick**; collision-guarded so adjacent targets can't corrupt each other's interval; returns `(notes, slide_events)` for the event JSON.
- Section roots = landed key: D2 (38) on Dm sections, C#2 (37) on C#m hook sections (`arrange.ROOT_MIDI`).

## Task 3 — `drums.drill_pattern`: F5 fixed in behavior

Kick row is now a **true 2-bar cycle**: bar A = `(0,3,6,8,11,14)` (3+3+2), bar B = `(0,6,8,11,13,14)` (drops the "a"-of-1, adds "e"-of-4 pickup). Ghost snare/openhat still alternate on the same parity. Test asserts bar0≠bar1, bar0==bar2, bar1==bar3.

## Task 3 (cont.) — NEW `toolshop/flip/arrange.py` (F3)

- **Span math:** `felt_span_written_bars(felt_bars, written_bpm)` — 4 felt bars → 8 written @178.2 / 6 @133.65; `supercycle_bars` = lcm(span, 4-bar drum group) → **8** (arm A) and **12** (arm B, the megaplan's LCM-12 supercycle — covers both 6-bar spans and 3-bar motif reps).
- **Arc:** `Section`/`ArmPlan` — `intro` (sparse kick+hat drums, bed LPF'd @1100 Hz, no 808) → `verse` (full) → `hook` (bed_gain 0.62 + mute-drop last 2 bars, reserved for `backing_vocals`) → `verse2` → `outro`. Arm A = 48 written bars / 65.6 s; arm B = 72 / 130.3 s (same 5-section shape, 12-bar supercycles).
- `plan_drum_events` (per-section density + mute-drops + section crash accents), `plan_bass` (per-section root, muted bars excluded → 808 drops with the kit), `build_bed_lane` (tiles rendered motif/region segments per section w/ gain + filter), `render_arm` → delegates the mix to `assemble.render_beat` via new **`bed_lane`** param (Lane B/C beds aren't manifest chops).
- `verify_render`: clip count, grid adherence (every drum event on the 1/24-beat lattice within 1 sample), mono<120 Hz (stereo side/mid sub-band ratio; mono input trivially passes).
- Motif library mirrored from `ogcm_bed_spike.py` (`motif_notes`/`motif_meta`/`write_motif_midi`) — the picked motifs were spike-script note lists, now also materialised as `midi/motif_dm_1.mid` + `midi/motif_csm_1.mid`.

## Task 4 — Renders (`Stemmeca_alatkka/stems/flip_renders/`, gitignored)

```
$ python scripts/ogcm_render_arms.py        (exit code 0)
kit audit: {cymbal: weak, hat/kick/openhat/snare/tom: pass} | weak: ['cymbal'] | ok: True
motif MIDIs: [midi\motif_dm_1.mid, midi\motif_csm_1.mid]
felt_89:     65.646s  peak=0.9373  clips=0  grid=True  mono120=True  PASS=True
triplet_133: 130.293s peak=0.9035  clips=0  grid=True  mono120=True  PASS=True
```

| Arm | Written bars | Supercycle | Duration | Drum events | 808 notes | Slides | Peak | Clips | Grid | Mono<120 Hz |
|---|---|---|---|---|---|---|---|---|---|---|
| felt_89 | 48 | 8 | 65.65 s | 1105 | 180 | 16 | 0.937 | **0** | PASS | PASS |
| triplet_133 | 72 | 12 | 130.29 s | 1665 | 276 | 24 | 0.904 | **0** | PASS | PASS |

No normaliser rescue on the final render (headroom-first mix levels `bed 0.42 / drums 0.28 / 808 0.28`; earlier 0.5/0.45/0.45 peaked 1.37). The 133.65 supercycle arrangement **reads clean** — no arm-B early-exit declared.

Per-render evidence: `beat_<arm>_events.json` (sections w/ bar+second bounds, all drum events, 808 notes, slide table with landing kick times, `hook_sections` + `hook_reserved_for="backing_vocals"`, embedded `verification` block); `renders_manifest.json` records the GATE C2 pick + audit pointer.

## Task 6 — Tests (TDD, all inside `tests/` where pytest.ini collects)

```
$ .venv/Scripts/python.exe -m pytest tests/test_flip_arrange.py tests/test_flip_drums.py \
      tests/test_flip_assemble.py -x -q
43 passed, 1 warning in 16.46s          (exit code 0)

$ .venv/Scripts/python.exe -m pytest tests/test_flip_*.py -q   (all 6 flip files)
80 passed, 1 warning in 31.39s          (exit code 0)
```

New coverage: `test_flip_arrange.py` (14) — span math, supercycle LCM, plan shapes both arms, motif alternation (Dm↔C#m), hook space+mute-drop, 2-bar cycle, sparse/mute filtering, crash accents, grid adherence, slide-counts-in-window, per-section 808 roots, mute-silences-808, bed tile+filter, end-to-end render verify, glide-window rejection, clip/mono helpers, motif MIDI roundtrip. `test_flip_drums.py` (+5) — true 2-bar cycle, audit verdicts pass/weak/fail + files-exist, declared fallback path, 90–200 ms glide window, mono-legato overlap convergence, `plan_808_line` spec (mono onsets on kicks, m3/P4, landing-on-kick, density bounds, rejection of out-of-spec density). `test_flip_assemble.py` (+1) — bed_lane mix + gain-0 silence.

## Files created/modified (all committed in `150db80`)

| Path | Action |
|---|---|
| `toolshop/flip/arrange.py` | NEW — arrangement layer |
| `toolshop/flip/drums.py` | MOD — 2-bar kick cycle, `audit_kit_manifest`, `load_kit_buffers`, classifier constants |
| `toolshop/flip/bass808.py` | MOD — 90–200 ms glide constants, `plan_808_line` |
| `toolshop/flip/assemble.py` | MOD — `bed_lane` param, `"bed"` mix key |
| `toolshop/flip/bed_lanes.py` | MOD — public `lowpass` wrapper |
| `scripts/ogcm_render_arms.py` | NEW — dual-grid render driver |
| `tests/test_flip_arrange.py` | NEW (14 tests) |
| `tests/test_flip_drums.py` | MOD (+5 tests) |
| `tests/test_flip_assemble.py` | MOD (+1 test) |
| `CHANGELOG.md` | MOD — Answer #060 m3 entry |
| `ORCHESTRATION/ogcm_flip/LEDGER.md` | MOD — m3 row → done (also commits the orchestrator's GATE C2 pick row that was already in the file) |

NOT committed (gitignored `Stemmeca_alatkka/stems/`): `flip_renders/*` (2 WAV + 2 event JSON + manifest), `flip_kit/kit_audit.json`, `flip_bed_lanes/midi/motif_{dm_1,csm_1}.mid`.

## Deviations from the task spec

- **Motif "MIDI sources"**: the pick describes motif MIDI "in the same midi/ dir" — they actually existed only as note lists inside `scripts/ogcm_bed_spike.py`. I mirrored them into `arrange._MOTIF_DEFS` (same note data, verified: `motif_dm_1` head note 62/D4) and had the render script materialise `midi/motif_dm_1.mid` + `midi/motif_csm_1.mid` so the declared source paths now exist for reproducibility.
- **Slides-per-4-bars**: used 2/4 bars (inside the 2–3 window) for all sections — deterministic spread at block fractions (0.375, 0.875); dense blocks yield exactly 2, collision-guard can reduce sparse blocks below 2 (accepted; spec floor applies to programming intent).
- **Mix levels**: default levels chosen so assemble's normaliser is never needed (evidence cleaner); levels remain a `render_arm` parameter.
- **LEDGER commit**: the file already contained the orchestrator's uncommitted GATE-C2-pick row; my m3-row update committed both hunks (m2 wave did likewise for its row).

## Blockers / risks for downstream waves (m4/m5)

- **`felt_89` is 65.6 s / `triplet_133` is 130.3 s** — arm B is 2× arm A in wall-clock (72 vs 48 written bars). If W4 wants matched durations per arm, the plan section counts are the knob (`build_plan` section list), not the renderer.
- **Hook reservation semantics**: `hook_sections` in each events JSON carry start_bar/bars/start_s/end_s; `backing_vocals` hook should be placed there (mute-drops at the tail of each hook/outro — low-end intentionally absent).
- **Relay placements**: `map_phrases` (m1) places at source-time; the render grids are 178.2/133.65 written — W4 must still pass `bpm_source` for written-grid reporting per m1 handoff.
- **Arm-B runtime**: render is pure-numpy ~seconds; no perf risk. Transcription/Lane-A paths untouched.
- **cymbal weak flag**: if the crash accents read too thin on audition, the declared escalation is `openhat` for accents or a re-mine with different rep selection — not silent classifier use.
- **Full suite not re-run** (80 flip tests + 43 targeted pass; m1's full-suite exclusion for `test_chain_dsl_unwired_params.py` / uninitialized `mastering_tool` submodule still applies — run before closeout at m5).

## Close-out evidence (`toolshop closeout`, exit 1 — expected)

FAIL on two pre-existing grounds, identical to m2's wave: (1) dirty paths are all other sessions'/orchestrator's (`M wave_m2 handoff` pick annotation, `M prompts_index.md`, `M mastering_tool`/`suno_prompter` submodule pointers, `??` prompt/dispatch/hemija/lyrics detritus, `?? wave_m1/`, `?? waves_megaplan.json`, and now `?? wave_m3/` — this file); (2) unpushed commits — push is W5's gate, not this wave's. All m3 code is committed in `150db80`; `git status` shows no m3 paths dirty.

Pre-commit hook note: the harness hook false-positived "no staged changes in D:/Projects" (parent repo); `git -C "D:/Projects/Music-AI-Toolshop" commit` resolved it, same as m2. No `--no-verify` used.
