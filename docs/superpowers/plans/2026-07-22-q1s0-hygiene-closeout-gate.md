# Q1-S0 — Hygiene + Mechanical Close-Out Gate

**Date:** 2026-07-22 · **Author:** orchestrator · **Size:** 1 session
**Why now:** Q1 step 0 in `docs/superpowers/STATUS.md` — blocks every other lane. Three L3 commits
are UNPUSHED (sole copy of flagship lyrics code), 12 junk `pytest_*.txt` dumps sit in the repo
root, and the close-out discipline written into AGENTS.md (`b13cf47`) was violated one commit
later — documentation alone is insufficient; this session makes the gate MECHANICAL.

**Standing context (do not re-derive):**
- Repo: `D:\Projects\Music-AI-Toolshop`, branch master, remote origin (github.com/qaaph-zyld/music-ai-toolshop).
- Env: `.venv` Python 3.11 in repo root — ALL pytest runs inside it.
- CI is **billing-locked** (GitHub Actions do not run). Never claim "CI green"; the gate is LOCAL
  pytest with pasted output. Last verified suite state: green (0 failed).
- Data boundary: nothing under `D:\MusicData\` is touched; never commit lyrics or `.env`.
- Close-out discipline: see AGENTS.md — a session is DONE only with clean tree + pushed + evidence
  pasted in the handoff. This plan's Task 8 IS that gate; do not skip it.

---

## Tasks

### Task 1 — PUSH FIRST (backup before anything else)
`git push origin master` — publishes the 3 unpushed L3 commits (`2318878`, `1ce86cd`, `6f44a3c`).
Do NOT rebase, amend, squash, or force — plain push of existing history.
**Exit evidence:** `git log origin/master..master` output is EMPTY (paste it).

### Task 2 — Baseline test run
`.venv` pytest full run (`-m "not slow"` per convention). Record exact counts
(passed/failed/skipped). This is the no-NEW-failures baseline for Task 8.
**Exit evidence:** pasted tail of pytest output.

### Task 3 — Junk-file cleanup + `.gitignore` globs
1. Delete the untracked run-dumps in repo root: `pytest_all_l3.txt`, `pytest_annotate.txt`,
   `pytest_annotate2.txt`, `pytest_baseline.txt`, `pytest_commit_a.txt`, `pytest_commit_b.txt`,
   `pytest_l3_schema.txt`, `pytest_lexicon.txt`, `pytest_lexicon2.txt`, `pytest_themes.txt`,
   `annotate_run.txt`, `annotate_run2.txt`. Delete ONLY files that `git status` shows as
   untracked (`??`) — nothing tracked gets deleted in this session.
2. `.gitignore`: replace the exact-match `pytest_tail.txt` line with globs: `pytest_*.txt`,
   `annotate_run*.txt`; add `.windsurf/` (see Task 4).
3. Root-clutter AUDIT (no action): list in the handoff every remaining repo-root file that looks
   like run output or one-off scripting (e.g. `output.json`, `output.txt`, `diagnose_voice.*`,
   `pytest_runner.log`, `check_batch_status.py`, `recover_batch_status.py`) with its tracked/
   untracked status — orchestrator decides their fate next review. Do not delete or move them.

### Task 4 — Stray handoff file
`.windsurf/handoffs/2026-07-22_reconcile-m6-t7-records.md` (untracked, inside the repo) belongs
with the framework handoffs. Move it to `D:\Projects\.windsurf\handoffs\` (same filename). With
Task 3's ignore rule, repo-level `.windsurf/` stops appearing in status.

### Task 5 — Diagnose `mastering_tool` submodule state
`git status` shows the submodule as modified. Diagnose precisely (`git -C mastering_tool status`,
`git diff --submodule`): dirty tree inside vs pointer drift. REPORT findings in the handoff with
the exact output. Only commit a pointer bump if the submodule's referenced commit is already
pushed to its remote; if the submodule tree is dirty, report and leave it — do not commit blind.

### Task 6 — `toolshop closeout` command (TDD)
New CLI verb on the existing CLI surface. Behavior:
- Checks, in order: (a) working tree clean — no staged/unstaged changes, no untracked non-ignored
  files; (b) no unpushed commits on the current branch vs its upstream; (c) submodule
  `mastering_tool` clean and its pointer commit present on its remote (best-effort; degrade to a
  warning if the submodule remote is unreachable).
- Prints an EVIDENCE BLOCK: `git status --short`, `git log @{u}..HEAD --oneline`, submodule
  summary — exactly what a handoff must paste.
- Exit code 0 only when all checks pass; nonzero otherwise with a one-line reason per failure.
- Tests first (mock the git calls; cover clean, dirty, unpushed, untracked, submodule-dirty cases).

### Task 7 — Version-controlled git hook + doctor check
1. Create repo-tracked `hooks/pre-push` (POSIX sh, runs on Windows git): blocks the push if the
   working tree contains tracked-pattern junk (`pytest_*.txt`, `annotate_run*.txt` outside
   .gitignore) or staged-but-uncommitted changes; prints how to bypass legitimately
   (`--no-verify` is NOT to be documented as routine — say "fix the tree instead").
2. Activate via `git config core.hooksPath hooks` (local config; document the command in
   AGENTS.md so every clone re-runs it).
3. `toolshop doctor`: add a check that `core.hooksPath` is set to `hooks` (warn if not).
4. AGENTS.md: add a short "Mechanical close-out" subsection — `toolshop closeout` must exit 0
   and its evidence block must be pasted in every handoff; hooksPath setup command.

### Task 8 — Commit wave + CHANGELOG + close-out (the gate, applied to itself)
1. Verify CHANGELOG has Answer entries for the pushed L3 commits; if missing, add
   reconciliation entries (check latest number first — was #020 as of `1d5a8d4`; use next free
   numbers, no collisions).
2. Commit in logical units (suggested): (a) gitignore+cleanup, (b) closeout command + tests,
   (c) hooks + doctor + AGENTS.md, (d) docs wave — `docs/superpowers/STATUS.md` edits, this plan,
   `specs/2026-07-22-longterm-goals-12mo-full-studio.md`,
   `research/2026-07-22-research-brief-full-studio-landscape.md`,
   `research/2026-07-22-full-studio-oss-landscape.md`, `research/2026-07-22-gapfill-report.md`
   — plus (e) CHANGELOG entry for this session.
3. Full pytest run: NO NEW failures vs Task 2 baseline (paste tail).
4. `git push origin master`.
5. Run `toolshop closeout` — must exit 0; paste its evidence block in the handoff.
6. Handoff file to `D:\Projects\.windsurf\handoffs\` (framework convention), containing: commit
   hashes, pytest baseline + final counts, closeout evidence block, submodule diagnosis (Task 5),
   root-clutter audit list (Task 3.3), and any deviations with reasons.

## Out of scope (do NOT do)
- No L3/L4 lyrics work, no new features, no dependency changes, no data-dir writes.
- No deletion/move of tracked files beyond what Tasks 3–4 specify.
- No CHANGELOG renumbering of existing entries.
- No fixing debt 1c (`PauseRemovalStage` min_silence) or any other known bug — tracked separately.

## Exit criteria (orchestrator will verify independently)
1. `git status --short` empty; `git log origin/master..master` empty.
2. `toolshop closeout` exists, tested, exits 0 on the final state.
3. `pytest_*.txt`/`annotate_run*.txt` cannot reappear untracked (globs in .gitignore).
4. Hook active (`git config core.hooksPath` → `hooks`); doctor reports it.
5. Strategy docs (goals v1.0, brief, 2 research reports, STATUS, this plan) committed and pushed.
6. Honest handoff with pasted evidence — claims without pasted output will be treated as unverified.
