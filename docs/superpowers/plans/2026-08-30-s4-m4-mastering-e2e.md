# S4 — M4: Mastering end-to-end (`german_drill`)

**Date:** 2026-08-30 · **Author:** orchestrator · **Size:** 1 session
**Goal:** G1 · third P1 milestone. Supersedes `plans/2026-07-15-h1m4-mastering-e2e-german-drill.md`,
whose premises have gone stale.
> **OUTCOME (CHANGELOG #043): pipeline VERIFIED.** Two runs, both exit 0, deliverables complete,
> 2-pass auto-gain confirmed, independent ebur128 matched the tool exactly. Two findings surfaced:
> auto-gain pass 1 is systematically ~4.2 dB biased (constant across sources 9 dB apart), and the
> PSR >= 8 gate is unreachable at the -8.0 LUFS german_drill target — a control run disproved the
> "quiet source" explanation. Neither fixed: verification run, daily-use product.

**Why now:** M4 is the last H1 milestone that is a *verification*, not a build. It closes the pending
item from 2026-07-13 (the stage-E soft-clip fix was only ever verified in isolation) and it exercises
the 2-pass auto-gain fix that landed in the submodule on 2026-08-18 but has never been run end to end
from this repo.

> **`mastering_tool/` is a production tool in daily use.** This is a verification run. Touch its code
> only to fix what actually blocks the run, minimally, and commit inside the submodule before bumping
> the pointer (AGENTS.md).

---

## What changed since the July plan

| July plan assumed | Reality on 2026-08-30 |
|---|---|
| Premasters in `D:\MusicData\toolshop\Distro Kidea\non-mastered\` | **That path no longer exists** — `D:\MusicData` was retired in #030. Source picked from `Distro_Kidea/` instead. |
| Drive the tray EXE (`dist\Mastering_Toolshop.exe`) | The EXE exists (28.1 MB) but is a **GUI**. The engine underneath is `master_pipeline_v3.sh`, which takes a clean CLI. Driving the script is scriptable, reproducible, and tests the same chain — a GUI click-through would verify less and prove it worse. |
| `scripts/session_end.py` at close | Does not exist in this repo (AGENTS.md already records this). |

**Source chosen:** `Distro_Kidea/Brat za Brata - MixAll.wav` — 123 s, measured **−23.1 LUFS**.
Most WAVs in that folder are `*_MASTER_32f.wav`, i.e. already-mastered outputs; the `MixAll` files
are the actual premasters. At −23.1 LUFS the `german_drill` target of **−8.0 LUFS** needs ~15 dB of
gain, which is precisely the auto-gain path the recent submodule fix touched. A quieter source is the
better test here, not a worse one.

---

## Tasks

### Task 1 — Preflight *(done during scoping)*

- [x] WSL Ubuntu reachable (`uname -sr` → Linux 6.18.33.2-microsoft-standard-WSL2). Note: it prints a
      benign `systemd user session` warning on entry; not a failure.
- [x] `german_drill` profile present in `family_policy.sh` → `-8.0 LUFS / -0.8 dBTP`.
- [x] Premaster staged into `data/toolshop/m4_verify/` (gitignored — never commit audio) and visible
      from WSL under `/mnt/d/...`.

### Task 2 — End-to-end run

`bash master_pipeline_v3.sh <source.wav> <name> <project_dir> german_drill`

Stages A→F plus QC verify + translation matrix + audio MD5. If a stage hangs or fails, capture stderr
(the 2026-07-13 handoff notes some stages swallow it with `2>/dev/null`), diagnose, apply the
**minimal** fix, re-run, and document the root cause.

**Exit evidence:** pipeline exit code and the stage progression.

### Task 3 — Verify deliverables

- `master/` and `verification/` populated.
- Loudness verification reports **`[COMPLIANT]`** against −8.0 LUFS / −0.8 dBTP — quote the lines.
- Confirm the **−0.8 dBTP ceiling path** is genuinely exercised (that is the bit the July plan
  singled out).
- Sanity-check the master's measured LUFS/TP independently with `ffmpeg ebur128`, rather than
  trusting the pipeline's own report. A tool grading its own homework is how the backup passed for a
  month while holding the wrong files.

### Task 4 — Close out

CHANGELOG **#043**, STATUS, plan outcome banner. If anything under `mastering_tool/` changed: commit
**inside the submodule first**, then bump the pointer deliberately. Note the submodule already has
pre-existing untracked files — do not sweep them in.

Then: full suite (bar: no new failures against **991 passed / 2 skipped / 0 failed**), `doctor`
**Overall: PASS**, `closeout` exit 0, push.

---

## Out of scope

- Any refactor of `mastering_tool/` — verification only
- The tray EXE's GUI behaviour (the engine is what is under test)
- M5, Dossier v2, `ai_modules/` (D6 still deferred)

## Risks

| Risk | Handling |
|---|---|
| LV2 plugins missing in WSL | Stages D/E depend on them. If absent, that IS the finding — report it rather than stubbing stages out. |
| Auto-gain overshoots from a −23.1 LUFS source | Exactly what this run is testing. Independent `ebur128` check catches it if the pipeline's own report is wrong. |
| Output is large | Written under gitignored `data/`; never committed. |
