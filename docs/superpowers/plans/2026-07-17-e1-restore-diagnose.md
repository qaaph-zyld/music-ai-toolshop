# E1 — Restore Diagnose: the Track Doctor report (T8 v0.1)

> **Authored 2026-07-17** by orchestrator at the production-expansion strategy review.
> Parent spec: `specs/2026-07-17-production-expansion-strategy.md` §1 (T8 RESTORE).
> Obey `AGENTS.md`. Analysis only — **no audio is modified in this session** (treatment is E3).
> Close-out gates are part of the plan (Task 6); do not defer commits/CHANGELOG to "later".

## Why this session exists

The user wants "automatic cleaning of tracks of any impurities". Per the eval-first policy we never
clean blind: E1 builds the **diagnosis layer** — measurable impurity metrics per track, a severity-graded
report, and a resumable batch sweep — so E3's treatment chains act on data and can prove before/after
deltas. The sweep also creates a new library-wide data asset (impurity tables, queryable in Datasette).

## Constraints (from AGENTS.md — non-negotiable)

- `.venv` Python 3.11.9 only. CPU-only; report measured sec/track in the handoff.
- Data boundary: outputs under `D:\MusicData\toolshop\restore\` (via `TOOLSHOP_DATA_DIR`), never in repo.
- Audio is read-only this session. Never delete/move source audio.
- UTF-8 everywhere; test with a `Täterprofil ćevap.mp3`-style filename.
- TDD: metric functions get synthetic-fixture tests BEFORE wiring CLI.
- Batch = shared resumable pattern (`toolshop/batch.py`): status JSON per item, `--limit/--offset`, skip-completed.
- Test suite: **no NEW failures** (the ~10 known `test_cleaning_pipeline.py` numpy failures are pre-existing debt — do not touch that file here). CI claims require the run URL in the handoff.

## Tasks

### Task 0: Preflight
- [ ] `.venv` active; `python -m toolshop.doctor` output captured.
- [ ] `pytest -q -m "not slow"` baseline captured (expect only the known cleaning-pipeline failures; record the exact count for the no-NEW-failures comparison).
- [ ] Confirm ffmpeg at `D:\Projects\ffmpeg_portable` reachable from config.

### Task 1: Metric engine — `toolshop/restore_metrics.py` (TDD)
Pure functions over `(samples: np.ndarray, sr: int)` returning dataclasses; no I/O inside metric code.
- [ ] `clipping`: clipped-sample ratio + longest consecutive clip run (threshold ≥0.999 FS, documented constant).
- [ ] `dc_offset`: per-channel mean.
- [ ] `spectral_cutoff_hz`: codec-shelf detector (high-band energy drop vs full-band; identifies ~16/19.2 kHz lossy provenance).
- [ ] `hum`: score at 50/100/150 Hz (and 60 Hz family) — Welch PSD peak vs local neighborhood.
- [ ] `noise_floor_db`: low-percentile frame RMS on quiet frames.
- [ ] `clicks`: sample-derivative outlier count per minute.
- [ ] `sibilance_ratio`: 5–9 kHz band energy vs mid band.
- [ ] `mud_ratio`: 200–500 Hz vs broadband balance.
- [ ] `stereo`: L/R correlation, side/mid energy ratio, mono-fold cancellation estimate.
- [ ] `silence_map`: leading/trailing silence + internal dropout gaps (list of ranges).
- [ ] `loudness`: LUFS-I, LRA, sample peak, PLR via **pyloudnorm** (MIT — new dep, verify wheel on adoption, add to `pyproject.toml` extra `restore` + license ledger). Fallback if wheel friction: parse ffmpeg `ebur128`.
- [ ] Tests `tests/test_restore_metrics.py`: synthetic fixtures generated in-test (clean sine; clipped sine; sine+DC; sine+50 Hz hum; sine+white noise floor; lowpassed noise for cutoff; click train; silence-gapped signal). Each metric detects its defect AND stays quiet on the clean fixture. Include one UTF-8 filename round-trip test via a tiny temp WAV.

### Task 2: Report layer — `toolshop/restore_report.py` (TDD)
- [ ] Severity grading per metric: `ok | warn | bad` with named threshold constants (documented in module docstring; conservative defaults).
- [ ] Treatment suggestion table: metric+severity → named future E3 chain stage (`dehum`, `declip`, `denoise-light`, `deess`, …) — suggestions only, nothing executes.
- [ ] Renderers: `impurities.json` (schema versioned `restore_diagnose_v1`) + human `report.md` per track.
- [ ] Tests: grading boundaries, JSON schema stability, report renders for a fully-clean and a multi-defect synthetic case.

### Task 3: CLI + batch — `toolshop restore diagnose <file|folder>`
- [ ] New `restore` command group in `toolshop/cli.py` with `diagnose` subcommand; `--out` (default `%TOOLSHOP_DATA_DIR%\restore\diagnose\`), `--limit/--offset`.
- [ ] Folder mode runs through the shared batch engine (resumable status JSON, skip-completed).
- [ ] Decode via existing audio-loading path (ffmpeg/librosa — reuse whatever `cleaning_pipeline_adapter`/stem tooling already uses; do not introduce a new loader).
- [ ] Mocked CLI test (no real decode) + one tiny real-WAV end-to-end test marked fast.

### Task 4: Pilot run + CPU measurement
- [ ] **[USER DECISION]** Pilot set — default proposal: PapaPedro folder + 20 CrhymeTV tracks (`--limit 20`) + 10 Suno masters. Adjust if the user replies; otherwise run the default.
- [ ] Record sec/track (mean + worst) in the handoff; if >15 min total for the pilot, stop and reassess (should be seconds/track — if not, something is wrong).
- [ ] Skim 3 reports manually; sanity-check gradings against listening reality; note misfires as threshold-tuning candidates (do not endlessly tune in-session).

### Task 5: Catalogue hook
- [ ] Append per-track impurity summary rows to the toolshop catalogue store (follow the existing dossier/catalogue pattern — summary numbers + severity flags + path to full JSON; do NOT invent a new DB).
- [ ] Verify the table is browsable via Datasette (installed 2026-07-17): one screenshot or query output in the handoff.

### Task 6: Close-out (gates — all checked IN this session)
- [ ] README: `restore diagnose` verb documented. PROJECTS_INDEX: T8 lane line added.
- [ ] CHANGELOG Answer-format entry (previous/current state, files affected).
- [ ] Commit wave with conventional messages; push; CI run URL + conclusion pasted in handoff ("no NEW failures" comparison vs Task 0 baseline).
- [ ] Handoff in `D:\Projects\.windsurf\handoffs\` + `python scripts/session_end.py --status completed ...`.
- [ ] **[USER DECISION]** Kick off the full-library overnight sweep (2,633 Suno + 222 CrhymeTV) now, or wait for E3 so treat-priorities are actionable? Default: kick it off — it is read-only, resumable, and the impurity distribution informs E3 preset design.

## Exit evidence
1. `pytest` — new tests green, no NEW failures vs baseline (counts quoted).
2. `toolshop restore diagnose` output for the pilot set with measured sec/track.
3. One `report.md` pasted into the handoff.
4. Catalogue rows queryable (Datasette or SQL output shown).

## Out of scope (do not drift)
- Any audio modification (E3), pedalboard/chains (E2), UVR de-reverb models (E4), DAW export (E5/E6).
- Touching `test_cleaning_pipeline.py` / the numpy debt (its own mini-session).
- Threshold perfectionism — defaults + notes beat a tuning rabbit hole.

## Bootstrap prompt for the coder session

```
D:\Projects\Music-AI-Toolshop | FRAMEWORK BOOTSTRAP (v11) per D:\Projects\ai_dev_meta_layer\framework_loader.md.
Load AGENTS.md. TASK: Execute plan docs/superpowers/plans/2026-07-17-e1-restore-diagnose.md
(E1 Restore Diagnose — T8 Track Doctor v0.1). Parent spec:
docs/superpowers/specs/2026-07-17-production-expansion-strategy.md §1.
Rules that bite: .venv 3.11 only; analysis-only (no audio modified); outputs to TOOLSHOP_DATA_DIR\restore\;
TDD with synthetic fixtures before CLI; shared batch.py pattern; no NEW test failures (baseline in Task 0);
close-out gates (commits+CHANGELOG+push+CI URL) are Task 6 of the plan, not optional.
Draft your session plan from the doc, wait for approval, then execute task-by-task.
```
