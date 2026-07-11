# Phase 1 Implementation Plan — Stem Tool v1.0 ("any wav/mp3 in, stems out")

> **For agentic workers:** Execute task-by-task with checkbox tracking. TDD required — write/extend
> tests in `tests/` before modifying adapters. All work in the Phase-0 venv. CPU is the default
> device on this machine; never assume GPU. Parent strategy:
> `docs/superpowers/specs/2026-07-11-strategic-roadmap-v1.md`. Prerequisite: Phase 0 complete.

**Goal:** One command turns any wav/mp3 (or a folder of them) into correctly-named stems with a
manifest, using CPU-realistic presets. Fix known separation bugs.

---

### Task 1: Fix fast-mode stem mapping bug (defect #1)

- [ ] **Step 1:** Reproduce: run `extract_stems(..., high_quality=False)` on a short fixture; observe `backing_vocals: None` and verify which file `main_vocals` actually points to.
- [ ] **Step 2:** Root cause: pass-2 (UVR-BVE) output names contain `_(Vocals)_` / `_(Instrumental)_`, not `backing`/`other`. Map by the model's documented output semantics per registry entry (see Task 2), not substring guessing. Handle Roformer-karaoke naming (`_(Vocals)_mel_band_roformer_karaoke...`) the same way.
- [ ] **Step 3:** Tests: mock `Separator.separate` returning realistic filenames for BOTH quality modes; assert all three stems resolve to existing paths. Extend `tests/test_stem_extractor_adapter.py`.

### Task 2: Model registry

- [ ] **Step 1:** New `toolshop/stem_models.py`: registry of models with fields — id, backend (`audio-separator`|`demucs`), stems produced, output-name mapping, quality tier, ~CPU min/track (fill after Task 6), VRAM needs, license/source.
- [ ] **Step 2:** Seed entries: `UVR-MDX-NET-Voc_FT` (2-stem fast), `model_bs_roformer_ep_317` (2-stem HQ), `mel_band_roformer_karaoke_aufr33_viperx` (karaoke split), `UVR-BVE-4B_SN-44100-1` (backing-vocal split), `htdemucs` (4-stem), `htdemucs_6s` (6-stem).
- [ ] **Step 3:** Presets composing registry entries: `karaoke` (vocals/instrumental fast), `vocals-hq` (Roformer), `full-vocals` (2-pass main+backing), `4stem` (drums/bass/other/vocals), `6stem` (+guitar/piano). Config-driven, no hardcoding.

### Task 3: Demucs backend

- [ ] **Step 1:** `pip install demucs` into venv (torch 2.x CPU already available); lock file update. If demucs wheels fight py3.11, fall back to `python -m demucs` subprocess wrapper — adapter API must hide the difference.
- [ ] **Step 2:** New `toolshop/demucs_adapter.py` implementing the same return contract as `stem_extractor_adapter` (`{"stems": {...}, "models_used": ..., ...}`); `--two-stems` passthrough option.
- [ ] **Step 3:** Salvage anything useful from `Stemmeca_alatkka/src/stemslicer/demucs_runner.py`, then mark stemslicer deprecated in its README.
- [ ] **Step 4:** Tests with mocked subprocess/module calls; integration test behind `@pytest.mark.slow`.

### Task 4: Unified `toolshop stems` command (new UX, keep `stem extract` as alias)

- [ ] **Step 1:** CLI: `toolshop stems <path> [--preset karaoke|vocals-hq|full-vocals|4stem|6stem] [--out DIR] [--format flac|wav] [--device cpu|gpu] [--json]`. `<path>` = file OR directory (batch).
- [ ] **Step 2:** Output convention: `<data-root>/stems/<track-slug>/<stem>.<ext>` + `manifest.json` (source path+hash, preset, models, durations, timings, toolshop version). Slugs UTF-8-safe (reuse batch runner's `safe_slug`).
- [ ] **Step 3:** FLAC default via soundfile (halves disk vs WAV, lossless). `--format wav` for DAW-direct use.
- [ ] **Step 4:** Batch mode: reuse the proven resumable pattern (`batch_status.json`, `--limit/--offset`, skip-completed, UTF-8 console guards) — extract that logic from `run_reverse_engineering_batch.py` into `toolshop/batch.py` so both pipelines share it.
- [ ] **Step 5:** Device default CPU; `--device gpu` prints an honest warning on this hardware (GT 640 unsupported).

### Task 5: Model cache management

- [ ] **Step 1:** Pin audio-separator/demucs model download dir to `<data-root>/models/` (env-var or Separator arg), so C: doesn't silently fill and `doctor` can report it.
- [ ] **Step 2:** `toolshop stems --list-models` prints registry with install state + disk usage.

### Task 6: Benchmark + docs

- [ ] **Step 1:** Benchmark each preset on one fixed ~3.5-min track on this CPU; record min/track + peak RAM into the registry and a README table.
- [ ] **Step 2:** README "Stems" section rewrite: presets table, batch example, manifest description, honest CPU-time expectations.
- [ ] **Step 3:** CHANGELOG entry; version bump to 0.4.0.

---

## Verification Checklist
- [ ] `toolshop stems song.mp3 --preset karaoke` → 2 correctly-named FLAC stems + manifest
- [ ] `toolshop stems song.wav --preset full-vocals` → instrumental + main + backing, none None
- [ ] `toolshop stems ./folder --preset 4stem` → resumable batch over folder
- [ ] Non-ASCII filename (e.g. `Täterprofil ćevap.mp3`) round-trips without mojibake
- [ ] All new code TDD-covered; `pytest` green; slow tests pass locally at least once
- [ ] Benchmark table committed
