# H1-M6 — Backups & Data Governance (Tier-1 tonight-capable)

> **Authored 2026-07-17** by orchestrator after gate [D2] resolved (M6 before E1).
> Parent: roadmap v2 H1-M6. Obey `AGENTS.md`. **Read-only toward all existing data** — this session
> COPIES; it never moves, rewrites, or deletes anything under `D:\MusicData` or the repo.

## Why now (facts verified 2026-07-17)

- Irreplaceable, ZERO-backup assets: 222-track dossier catalogue · 749-song lyrics corpus + `lyrics.db`
  (34,598 rhyme rows) · Genius token `.env` · batch status JSONs · mastering references.
- **D: is a 2010-era 640 GB laptop HDD (Seagate ST9640423AS)** — age alone is a failure risk.
- C: (Toshiba DT01ACA050, 75.9 GB free) is a **separate physical disk** → a D→C Tier-1 backup already
  protects against single-disk death. No new hardware needed for Tier 1.
- Also present: unmounted 120 GB Kingston SA400 SSD (disk 0) — status unknown; card-reader slots empty;
  no external drive connected.

## Tier model

| Tier | Contents | Size class | Destination |
|---|---|---|---|
| 1 — irreplaceable, small | lyrics corpus JSON + indices, `lyrics.db`, dossier catalogue + dossiers, batch statuses, model checksum manifests (not weights), gitignored `.env` tokens | ≤ a few GB | `C:\Backups\toolshop\` (cross-disk), rotated |
| 2 — regenerable but expensive | stems (~30 min/track to redo), model weights mirror | tens of GB | external drive — **[USER DECISION]** |
| 3 — source audio | CrhymeTV rips, own recordings, Suno downloads | large | external drive — **[USER DECISION]** |

This session implements Tier 1 end-to-end (incl. restore test + doctor checks). Tiers 2/3 get a decision
recorded and, at most, a `--tier 2` stub — no implementation without a destination drive.

## Tasks

### Task 0: Preflight
- [ ] `.venv`; `python -m toolshop.doctor` captured; `pytest -q -m "not slow"` baseline count captured (no-NEW-failures rule).

### Task 1: Asset inventory (read-only)
- [ ] Enumerate + size every asset class under `D:\MusicData\toolshop\` (lyrics/, catalogue(s), dossiers, models/, stems/, audio).
- [ ] Locate mastering_tool `REFERENCE_LIBRARY`/`CATALOGUE` on disk (WSL path or D:) and the Suno library root; record paths + sizes.
- [ ] Enumerate gitignored secrets (`.env` files) across repo + subprojects.
- [ ] Output: inventory table in the handoff + a `backup_config.json` (paths, tiers) checked into repo (paths only — no secrets in the file).

### Task 2: Tier-1 backup engine (TDD, stdlib-only — no new deps)
- [ ] `toolshop/backup.py`: given `backup_config.json` → copy Tier-1 sets to `C:\Backups\toolshop\<YYYY-MM-DD>\`,
      write `backup_manifest.json` (per-file size + sha256 for DBs/JSON/indices, started/finished timestamps, source paths).
- [ ] Rotation: keep last 7 daily + last 3 monthly; prune only directories that carry a valid manifest (never prune the newest; never touch sources).
- [ ] UTF-8 path safety test (`Täterprofil ćevap`-style name in a temp fixture tree).
- [ ] CLI: `toolshop backup run [--tier 1] [--dry-run]` + `toolshop backup verify` (checks newest manifest checksums).
- [ ] Tests: fixture tree → run → manifest correct; rotation math; verify catches a corrupted byte; dry-run touches nothing.

### Task 3: Doctor integration
- [ ] `backup-age` check: warn > 7 days, fail > 30 days or no backup found.
- [ ] `disk-free` watchdog: warn < 30 GB free on C: or D:.
- [ ] Doctor output captured in handoff showing both checks live.

### Task 4: Restore test (the exit bar — a backup that never restored is a hope, not a backup)
- [ ] Restore newest Tier-1 backup to `%TEMP%\restore_test\`; open restored `lyrics.db` → row counts match live DB; parse one dossier JSON; `toolshop backup verify` green.
- [ ] Quote all outputs in the handoff.

### Task 5: Scheduling — **[USER DECISION]**
- [ ] Default proposal: register Windows Task Scheduler weekly job (Sun 03:00) running `backup run --tier 1`; doctor nags cover missed runs. Alternative: manual habit only.
- [ ] If scheduled: `schtasks` registration command recorded in README + handoff; job runs once as proof.

### Task 6: Tier-2/3 destination — **[USER DECISION]** (decision only, no build)
- [ ] Options: (a) plug/buy an external HDD (≥1 TB) → next mini-session extends `--tier 2/3`;
      (b) mount the idle 120 GB Kingston SSD (too small for audio; could hold stems-only);
      (c) accept documented regenerable-risk for stems/models and irreplaceability risk for source audio.
- [ ] Record the choice in this plan + STATUS debt register.

### Task 7: Close-out gates (all IN-session)
- [ ] README backup section; CHANGELOG Answer entry; PROJECTS_INDEX untouched unless verbs changed.
- [ ] Commit wave + push; CI run URL + "no NEW failures vs baseline" in handoff.
- [ ] Handoff + `python scripts/session_end.py`.

## Exit evidence
1. Tier-1 backup exists on C: with manifest; `backup verify` output.
2. Restore-test outputs (row counts, checksum pass).
3. Doctor showing backup-age + disk-free checks.
4. Scheduled task registered + one proof run (if D5 = schedule).

## Out of scope
Cloud sync, encryption (note: `.env` tokens stay on local disks only until an encryption decision),
Tier-2/3 implementation, any touching of the numpy test debt.

## Bootstrap prompt for the coder session

```
D:\Projects\Music-AI-Toolshop | FRAMEWORK BOOTSTRAP (v11) per D:\Projects\ai_dev_meta_layer\framework_loader.md.
Load AGENTS.md. TASK: Execute plan docs/superpowers/plans/2026-07-17-h1m6-backups-data-governance.md
(H1-M6 Backups & Data Governance — Tier 1 end-to-end + restore test + doctor checks).
Rules that bite: .venv 3.11; COPY-only (never move/delete sources); stdlib-only engine; secrets never
land in committed files; TDD on backup/rotation/verify; close-out gates are Task 7, not optional.
Two [USER DECISION] points (scheduling, Tier-2/3 destination) — present defaults, wait for answer.
Draft your session plan from the doc, wait for approval, then execute task-by-task.
```
