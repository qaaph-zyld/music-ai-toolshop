# H1-M1 — Finish CrhymeTV Batch Analyze-Only (222/222)

> **For agentic workers:** Execute task-by-task with checkboxes. ONE milestone only — do NOT start
> H1-M2 or other work after this. Obey `AGENTS.md` (venv python, UTF-8, never delete data).
> Parent: `docs/superpowers/specs/2026-07-15-longterm-roadmap-v2.md` §H1-M1.

**Goal:** All 222 CrhymeTV tracks analyzed (BPM/key/chords/effects/recipe), catalogue regenerated.
The 82 remaining tracks run WITHOUT stem separation (CPU-prohibitive; stems backfill later).

**Verified starting state (2026-07-15):**
- `--no-stems` is ALREADY implemented in `run_reverse_engineering_batch.py` (argparse ~line 320,
  `process_track(no_stems=...)` ~line 173) and tested in `tests/test_run_reverse_engineering_batch.py`.
  **Do not re-implement it.**
- `run_crhymetv_batch.ps1` already sets `$NoStems = $true` and uses the venv python.
- `results/crhymetv_re/batch_status.json`: 140/222 completed (with stems), 0 failed. Resume-safe.
- **KNOWN BUG (fix in Task 1):** the PS1 catalogue step calls
  `generate_crhymetv_catalogue.py --status-file <...> --output-dir <...>`, but that script's argparse
  only accepts `--results-dir` → the post-batch catalogue regen exits with an argparse error.

### Task 1: Fix PS1 ↔ catalogue-generator argument mismatch
- [ ] In `run_crhymetv_batch.ps1`, replace the `$CatalogueArgs` block's `--status-file`/`--output-dir`
      pair with a single `--results-dir $ResultsDir`.
- [ ] Regression-verify the generator standalone against current data:
      `.venv\Scripts\python.exe generate_crhymetv_catalogue.py --results-dir results\crhymetv_re`
      → exit 0, prints "Generated catalogue for 140 completed tracks".

### Task 2: Baseline tests
- [ ] `.venv\Scripts\python.exe -m pytest -q` → all green. Quote the tail in the handoff.

### Task 3: Analyze-only smoke (do NOT touch production status file)
- [ ] Run 2 tracks into a scratch dir:
      `.venv\Scripts\python.exe run_reverse_engineering_batch.py --input-dir "d:\Projects\Tools\yt_extractor\downloads\CrhymeTV" --output-dir results\smoke_nostems --limit 2 --no-stems --no-resume`
- [ ] Verify per track: `per_track/<slug>/recipe.md` + `<name>_analysis.json` + `<name>_voice_analysis.json`
      exist; NO `stems/` directory; recipe renders a sensible "stems skipped" line (fix rendering only if
      it prints raw `None`). Record min/track (expect ~2–4 min).

### Task 4: Launch the full batch (detached, resumable)
- [ ] Launch: `Start-Process powershell -ArgumentList '-File','d:\Projects\Music-AI-Toolshop\run_crhymetv_batch.ps1'`
- [ ] Confirm liveness: within ~10 min, `batch_status.json` gains track #141 as completed and
      `results\crhymetv_re\batch.log` advances. Quote the `[141/222]` log line.
- [ ] ETA note for handoff: 82 × ~2–4 min ≈ 3–5.5 h. The run is resume-safe; if interrupted, re-run the PS1.

### Task 5: Post-batch verification (same session if time allows, else next session picks up here)
- [ ] `batch_status.json`: completed == 222, `errors` empty (investigate any failure; the runner
      continues past failures, so list them in the handoff rather than re-running blindly).
- [ ] Catalogue auto-regen ran (PS1 does it on exit 0) — else run Task-1 command manually.
- [ ] `catalogue.md` header shows `Tracks: 222`; spot-check one NEW track's section (BPM/key/chords present, stems absent).

### Task 6: Documentation + handoff
- [ ] CHANGELOG.md Answer-format entry (state 140→222, analyze-only mode, PS1 catalogue fix).
- [ ] Write handoff `d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m1.md` per the
      report template in the bootstrap prompt below. Run `python scripts/session_end.py` from `ai_dev_meta_layer`.

## Verification checklist
- [ ] PS1 catalogue step fixed and proven against real data
- [ ] pytest green (quoted)
- [ ] Smoke: 2 tracks analyze-only, timings recorded
- [ ] Full batch launched with liveness evidence (or completed: 222/222, catalogue `Tracks: 222`)
- [ ] CHANGELOG + handoff written

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "H1-M1: finish CrhymeTV batch analyze-only" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m1-crhymetv-analyze-only.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-15-h1m1-crhymetv-analyze-only.md
exactly as written. Scope = this milestone ONLY; do not start other roadmap items. Use the .venv python for
everything. Never delete audio or results. The plan's "Verified starting state" is authoritative — re-verify,
don't re-implement.

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m1.md
containing: (1) each plan task with [x]/[ ] and one-line evidence, (2) pytest tail quoted, (3) smoke timings
(min/track), (4) batch launch evidence ([141/222] log line) or final counts (completed=222, errors=0) and
catalogue "Tracks: 222" line, (5) files changed, (6) deviations from plan + why, (7) open blockers.
I will paste that handoff to my strategy reviewer for verification before the next milestone is released.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m1-crhymetv-analyze-only.md
```
