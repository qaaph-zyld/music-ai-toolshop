# H1-M1b — Make Advanced Backend Permanent, Guard Long Files, Close M1

> **For agentic workers:** One milestone only. Obey `AGENTS.md`. This supersedes "Task 5" of the
> H1-M1 plan and the "Next steps" of handoff `2026-07-15_2149_music-ai-toolshop-h1m1.md`.
> Read the "Context" below — it corrects that handoff.

## Context (verified by strategy review, 2026-07-15 late evening)

1. **Backend regression found & rescued:** the venv could not import `wav_reverse_engineer`
   (adapter silently fell back to `basic_librosa` — no chords/instruments; smoke recipes prove it).
   The first detached batch also **died without traceback** on track #141 (long `[Dokumentation]`
   file, ~4.5 GB RAM; OOM or console/sleep kill). No degraded tracks were committed (still 140/222).
2. **Rescue batch is running/ran** (launched ~23:00 with `PYTHONPATH=projects\05-track-reverse-engineering\track_reverse_engineering`,
   `--no-stems --offset 141`, logs in `results\crhymetv_re\batch_offset141.log/.err`). It processes
   display-tracks #142–#222 (81 tracks) with the ADVANCED backend. Track #141 (the documentary) was
   deliberately skipped and is handled in Task 3 below.
3. Uncommitted work has accumulated (AGENTS.md, plan/spec docs, PS1 + runner edits, CHANGELOG) — Task 6 commits it.

### Task 1: Verify the rescue batch outcome
- [ ] `batch_status.json`: expect completed == 221 (all except idx 140/display #141), errors == [].
      If the rescue died early: check `batch_offset141.err`, fix cause, relaunch same command
      (resume-safe) — with Task 2's guard in place first.
- [ ] Spot-check TWO new tracks (`per_track/<slug>/recipe.md`): `Backend: wav_reverse_engineer`,
      chord progression non-empty, instruments present. If any new track shows `basic_librosa`,
      list them — they must be re-run after Task 4 (delete their per_track dirs is NOT allowed;
      use `--no-resume`? No — instead remove their entries from batch_status via a small script and re-run).

### Task 2: Make the advanced backend import permanent (no more silent fallback)
- [ ] Write `.venv\Lib\site-packages\wav_reverse_engineer.pth` containing one line:
      `d:\Projects\Music-AI-Toolshop\projects\05-track-reverse-engineering\track_reverse_engineering`
- [ ] Also add `$env:PYTHONPATH = ...` (same path) to `run_crhymetv_batch.ps1` as belt-and-braces, and
      set `$NoStems`-adjacent comment noting the advanced-backend requirement.
- [ ] **Anti-silent-fallback guard:** add `--require-advanced` flag to `run_reverse_engineering_batch.py`
      (fail fast at startup if `reverse_engineering_adapter._WAV_RE_AVAILABLE` is False); use it in the PS1. TDD.
- [ ] Verify: `.venv\Scripts\python.exe -c "from toolshop import reverse_engineering_adapter as r; print(r._WAV_RE_AVAILABLE)"`
      → True (fresh shell, no PYTHONPATH). Re-run the previously failing wav_re-dependent tests
      (`test_reverse_engineering_adapter.py`, `test_track_cli.py`) — expect most of those 7 to pass now;
      quote before/after counts.

### Task 3: Long-file guard + the #141 documentary
- [ ] Add `--max-duration <seconds>` to the runner (default 0 = off; PS1 passes 900). Tracks over the
      limit get status `skipped_long` with `duration_seconds` recorded (probe via librosa
      `get_duration(path=...)` or ffprobe — cheap, no full load). Update catalogue generator to count
      completed vs skipped_long separately and list skipped files at the bottom of `catalogue.md`. TDD both.
- [ ] Run the runner once for idx 140 only (`--offset 140 --limit 1 --no-stems --max-duration 900`)
      → documentary becomes `skipped_long` in status. **[USER DECISION]** only if the user wants
      documentaries fully analyzed instead (then run it unguarded overnight, alone, RAM permitting).

### Task 4: Final M1 verification
- [ ] `batch_status.json`: completed + skipped_long == 222, errors == [].
- [ ] Regenerate: `.venv\Scripts\python.exe generate_crhymetv_catalogue.py --results-dir results\crhymetv_re`
- [ ] `catalogue.md`: completed-track count matches; skipped section lists the documentary;
      spot-check one new track section has chords + instruments populated.

### Task 5: Test-debt snapshot (report only, no fixes)
- [ ] Full `pytest -q`; quote tail. Expected: wav_re-dependent failures resolved by Task 2; remaining
      failures should be the ~10 cleaning-pipeline numpy-scalar items + any EOFError fixture debt.
      List them in the handoff as input for a future mini-milestone ("test-debt cleanup").

### Task 6: Commit + docs
- [ ] Commit in logical chunks: (a) `docs: strategy pack` (AGENTS.md, roadmap v2, integration map, H1 plan files),
      (b) `fix(batch): catalogue args, advanced-backend guard, max-duration skip` (PS1 + runner + tests),
      (c) CHANGELOG Answer entry for M1 completion (state 140→222, backend incident + fix, guard added).
- [ ] Handoff `<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m1b.md` per report template; `session_end.py`.

## Verification checklist
- [ ] 222/222 accounted (221 completed + 1 skipped_long, or 222 completed per user decision)
- [ ] New tracks: `Backend: wav_reverse_engineer` with chords/instruments (2 spot-checks quoted)
- [ ] Fresh-shell advanced import True; `--require-advanced` guard tested
- [ ] Catalogue regenerated with skip section; counts quoted
- [ ] pytest before/after counts quoted; residual debt listed
- [ ] All work committed (3 commits); handoff written

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "H1-M1b: advanced-backend permanence + long-file guard + close M1" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m1b-backend-fix-and-close.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-15-h1m1b-backend-fix-and-close.md
exactly as written. Its "Context" section is authoritative and CORRECTS the previous handoff (backend
regression + dead batch were found and a rescue batch was launched by strategy review). Scope = this
milestone only. Use the .venv python. TDD for runner changes. Never delete audio or per_track results.

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m1b.md
with: per-task [x] + evidence, final batch counts (completed/skipped_long/errors), two quoted
"Backend: wav_reverse_engineer" spot-checks, pytest before/after tails, commit hashes, deviations, blockers.
This gets reviewed before H1-M2 is released.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m1b-backend-fix-and-close.md
```
