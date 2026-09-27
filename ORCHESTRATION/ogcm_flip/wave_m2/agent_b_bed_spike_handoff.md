# Wave m2 (W1′) — Bed-lane spike → GATE C2 audition pack — Agent B handoff

**Status:** DONE — GATE C2 pack ready; STOPPING for user audition (lane + grid arm + hook pick).
**Plan:** `D:\Projects\.workspace_archive\plans\ogcm-flip-megaplan.md` (sections: The Pivot, Revised Waves > W1′, F8, A22–A25/A28, ADR-009).

## What this wave delivered

Executed wave W1′ of the OGCM flip megaplan: the melodic-bed pivot as a pure-code render path (basic-pitch ONNX → MIDI cleanup → numpy voice render), producing a blind GATE C2 audition pack that lets the user pick the bed lane without committing to the dual-grid build.

### 1. Authorized install + ONNX verification (F8)
- Command: `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -m pip install --no-deps basic-pitch mir_eval`
- **Exit code 0.** Output: `Successfully installed basic-pitch-0.4.0 mir_eval-0.8.2`.
- Rationale (F8): on py3.11 basic-pitch's wheel pulls `tensorflow<2.15.1` as a HARD dep (requires_dist marker `python_version>="3.11"`) and pins `resampy<0.4.3` vs installed 0.4.3 — `--no-deps` avoids both; runtime deps (librosa/pretty_midi/sklearn/scipy/onnxruntime/resampy 0.4.3) already present.
- **ONNX path verified:** `basic_pitch.inference.predict` defaults to the bundled `nmp.onnx` model (TF absent → ONNX auto-selected; the `Model` class tries ONNX when `ONNX_PRESENT` and the path ends `.onnx`). Predicted on a 10 s region (63–73 s) of the v2 `(other)` bed → **67 note events**. No proxy/download failure; resampy stayed at 0.4.3 (no downgrade needed — the spike did not break, per F8 fallback rule).

### 2. Transcription of top GATE-C regions → MIDI
Three regions on the v2 `(other)` bed (`2Pac - Only God Can Judge Me_(other)_..._unwa.wav`, 297.03 s, 44.1 kHz) transcribed via `basic_pitch.inference.predict` (onset_threshold=0.5, frame_threshold=0.3, minimum_note_length=80 ms):

| Region | Clip window | Raw notes | Cleaned (Dm scale-locked) |
|---|---|---|---|
| ~63–66 s | 63–73 s | 67 | 41 |
| ~12.6 s | 12.6–22.6 s | 68 | 43 |
| ~233–258 s | 233–258 s | 170 | 95 |

Raw + cleaned MIDI saved to `Stemmeca_alatkka/stems/flip_bed_lanes/midi/` (6 files: `region_*_raw.mid`, `region_*_cleaned_Dm.mid`).

### 3. New module `toolshop/flip/bed_lanes.py`
Same pure-numpy technique family as `bass808.py`. Provides:
- **MIDI cleanup:** `quantize_to_grid` (89.1 felt grid, configurable subdivision), `prune_low_confidence` (<0.4), `prune_short` (<80 ms), `scale_lock` (snap to landed key, mode preserved), and a `cleanup()` pipeline.
- **Numpy voices:** `render_epiano` (sine + integer overtones + exp decay + tanh), `render_pad` (detuned saws + one-pole LPF + slow attack), `render_pluck` (Karplus-Strong), plus `render_loop` (tile/trim to N felt bars).
- **MIDI I/O:** `events_to_notes`, `notes_to_pretty_midi`, `pretty_midi_to_notes`, `save_midi`, `load_midi` (via pretty_midi).
- **ADR-009 loudness:** `measure_lufs`, `loudness_match_pair`, `loudness_match_many` (pyloudnorm; handles near-silent signals by peak-normalizing first so no lane is left at -inf LUFS).

**Bug caught + fixed during the spike:** basic-pitch returns note events in **descending** start order. An over-defensive "non-decreasing onset" pass in `quantize_to_grid` cascaded every note to the latest onset, rendering Lane B silent (peak 0.0). Fix: sort by `start_s` before quantize; drop the cascade. `events_to_notes` now sorts too. This is the kind of defect the spike exists to catch (A23 — transcription quality on a multi-instrument bed is sketch-grade; the cleanup must not silently eat the output).

### 4. TDD: `tests/test_flip_bed_lanes.py` — 19 tests
Cover: BedNote duration, MIDI round-trip, events→notes (basic-pitch shape), prune_low_confidence, prune_short (boundary inclusive), quantize (snap, order, no-invert), scale_lock (Dm, C#m, in-scale preserved), full cleanup pipeline, epiano/pad/pluck renders (non-zero, right length, pad slow-attack, KS decay), empty-notes silence, render_loop tiling, loudness_match_pair (≤0.3 LU, target ±1.0).
- `pytest tests/test_flip_bed_lanes.py -q` → **19 passed** (exit 0).

### 5. New script `scripts/ogcm_bed_spike.py`
Drives basic-pitch → cleanup → renders → blind pack. Produces:
- **Lane B** (interpolated bed): cleaned notes from regions 233–258 (epiano + pad) and 63–66 (epiano) → 8-bar felt-grid loops.
- **Lane C** (hand-programmed): 3 dark motifs via pretty_midi note lists — `motif_dm_1` (Dm i-VI arpeggio), `motif_dm_2` (Dm minor-9 stabs), `motif_csm_1` (C#m i-VII-VI) — rendered with epiano + pad.
- **Lane A** (existing chops): cand_220 (4bar F#min) + cand_121 (2bar F#min) from `stems/flip_chops_v2/audition/` — tiled to 8 bars + time-stretched (pitch-preserving via librosa) for the 133.65 arm. No new module code (reuse only).
- All lanes × both grid arms (89.1 felt = 178.2 written, and 133.65).

### 6. GATE C2 audition pack (ADR-009)
Location: `Stemmeca_alatkka/stems/flip_bed_lanes/` (gitignored — NOT committed, per task).
- **22 files** in `audition/` (`bed_001.wav` … `bed_022.wav`, opaque names, shuffled with seed 20260927).
- Composition: Lane A ×4, Lane B ×6, Lane C ×12; both grid arms (11 felt_89 + 11 triplet_133).
- Loudness-matched to −18 LUFS; **LU spread 0.0 LU** (≤0.3 tolerance).
- No clipping (max peak 0.771); file/identity bijection OK.
- `manifest.json` — hidden-key mapping (file → lane/arm/voice/source/key); the user should NOT read this before picking.
- `verification.json` — pre-listening check record (lufs_per_file, spread, clipping, bijection, passed=true).
- `GATE_C2.md` — describes the pack (22 files, 8-bar loops, what to choose, how to listen, verification results) **WITHOUT revealing which file is which lane**.
- `midi/` — raw + cleaned MIDI for the 3 regions.

### 7. `pyproject.toml` `[flip]` extra
Added `basic-pitch` (with a comment documenting the required `--no-deps` install per F8), `mir_eval`, `pretty_midi>=0.2.10`, `pyloudnorm>=0.1`.

## Verification (all run this session, exit codes quoted)

| Check | Command | Result |
|---|---|---|
| pip install | `... -m pip install --no-deps basic-pitch mir_eval` | **exit 0** — `Successfully installed basic-pitch-0.4.0 mir_eval-0.8.2` |
| ONNX predict (10 s bed region) | inline `predict(...)` | 67 events; TF absent → ONNX auto-selected |
| bed_lanes tests | `pytest tests/test_flip_bed_lanes.py -q` | **19 passed** (exit 0) |
| full suite | `pytest tests/ -q --ignore=tests/test_chain_dsl_unwired_params.py` | **1347 passed, 2 skipped** (exit 0; ~15:43) |
| spike script | `python scripts/ogcm_bed_spike.py` | **exit 0**; verify: LU spread 0.0 LU (PASS), clipping PASS, bijection PASS, overall PASS |

**Note on the excluded test file:** `tests/test_chain_dsl_unwired_params.py` raises `ModuleNotFoundError: No module named 'mastering_tool'` at collection — a **pre-existing** issue (the `mastering_tool` git submodule is not installed in the venv), unrelated to this wave. It was excluded from the suite run; no other collection errors.

## Files created/modified

**Committed (code):**
- NEW `toolshop/flip/bed_lanes.py` (418 lines)
- NEW `scripts/ogcm_bed_spike.py` (398 lines)
- NEW `tests/test_flip_bed_lanes.py` (227 lines)
- MODIFIED `pyproject.toml` — `[flip]` extra: +basic-pitch, +mir_eval, +pretty_midi, +pyloudnorm (with F8 `--no-deps` comment)
- MODIFIED `CHANGELOG.md` — Answer #060 W1′ entry appended
- MODIFIED `docs/superpowers/STATUS.md` — Flip lane row updated (W1′ done, GATE C2 ready)
- MODIFIED `ORCHESTRATION/ogcm_flip/LEDGER.md` — m2 row → done (pack ready, awaiting user pick)

**NOT committed (gitignored data, per task constraints):**
- `Stemmeca_alatkka/stems/flip_bed_lanes/audition/*.wav` (22 files)
- `Stemmeca_alatkka/stems/flip_bed_lanes/{manifest.json,verification.json,GATE_C2.md}`
- `Stemmeca_alatkka/stems/flip_bed_lanes/midi/*.mid` (6 files)

## Deviations from spec
- **Grid-arm semantics:** the task's "both pitch arms (178.2 written/89.1 felt AND 133.65)" was read as the two **grid/tempo** arms (the dual-grid experiment), not the −1/−4/−5 pitch-shift arms from GATE C. The megaplan W1′ step 5 ("all lanes + pitch arms as 8-bar felt-grid loops") and the dual-grid context confirm this: the −1/−4/−5 pitch arms are a GATE C (chop) axis; at GATE C2 the arm choice is which grid tempo. Lane A's pitch-shift arms remain available via the existing chop pack if the user wants them later.
- **Lane A 133.65 arm:** produced by pitch-preserving time-stretch (librosa) in the spike script, not a new module — consistent with "reuse its audition arms, no new code needed" (no new module; the script does the tiling/stretch).
- **Lane B voice/region choice:** used regions 233–258 (epiano+pad) and 63–66 (epiano) for the main loops; region 12.6 was transcribed + saved to MIDI but not rendered into the pack (the 233–258 region is richest: 170 raw / 95 cleaned notes). All three regions' MIDI are on disk for downstream use.

## Blockers / risks for downstream waves (m3+)
- **GATE C2 is a hard user gate.** m3 (W2+W3 build) is blocked until the user picks lane + grid arm + hook treatment. Do not start drum/808/arrange work before the pick.
- **Transcription quality (A23, PARTIAL):** basic-pitch on the multi-instrument `(other)` bed is sketch-grade — notes cluster, voicings are approximate. The cleanup (conf≥0.4, ≥80 ms, scale-lock to Dm) tames this but the Lane B loops are intentionally synthetic; the GATE_C2.md tells the user to judge contour/sit, not sample quality. If Lane B wins on a thin timbre, the declared upgrade is SF2/FL (A24) — one step, not required.
- **Downbeat phase (0.08):** bar-1 labels may sit a beat off — affects all lanes equally; the ear decides (carried from GATE C).
- **133.65 arrangement cost:** if the 133.65 arm wins, the 3/6/9-written-bar chop spans vs 4-bar drum cycles need the explicit 12-bar supercycle (W3 arrange.py, not yet written — F3 open). Arm-B early-exit is the declared escape.
- **Pre-existing dirty tree (not mine):** `mastering_tool`/`suno_prompter` submodule pointers, `ORCHESTRATION/prompts/*hemija*`, `lyrics_research/documents/`, `prompts_index.md` were dirty before this wave and are left untouched (other sessions' work). Only this wave's code + records were committed.

## STOP
At GATE C2. The deliverable is the pack + `GATE_C2.md`. The user auditions `stems/flip_bed_lanes/audition/` (read `GATE_C2.md` first, NOT `manifest.json`) and picks lane + grid arm + hook treatment. Resume m3 after the pick.
