FRAMEWORK BOOTSTRAP (v14.1) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool with task + open files, or run:
   `python scripts/session.py brief "<task>" --files "<open files or omit>"`
5. Read the brief. Load ONLY the KBs it names. Note the "Do NOT load" list.
   Skills auto-activate natively — do not preload.
6. For large tasks, use `/orchestrate` or dispatch a subagent:
   `python scripts/dispatch_subagent.py <role> --task "..." --scope "..." --execute`
7. Draft a plan. Do NOT start coding until the plan is approved.
8. After completion, run `python scripts/session.py end --status completed --duration <min> --helpful <skill>`.
WAIT FOR MY TASK.

MY TASK: lyrics-sr A1a - fix the SR-3 "database is locked" crash, make the annotate status honest and show the MAirina gate, add a build-db reminder, then relaunch SR-3 as a detached overnight batch. PRE-APPROVED (MAirina v3 plan, approved 2026-10-20): skip bootstrap step 7, do not re-plan.

CONTEXT (verified by Claude 2026-10-20, see ORCHESTRATION\lyrics_sr\ledger.md section "Resume 2026-10-20"):
SR-3 died on 2026-10-13 at 00:08, at 2,000/152,588 lines, with sqlite3.OperationalError "database is locked"
(toolshop\annotate.py:256). Cause: run_annotation (annotate.py:389-436) sets no busy_timeout, and the SR-4 rimer
rebuild wrote lyrics.db at the same moment. The status JSON had no error field, so the ledger kept saying RUNNING.
The MAirina finder has been offline since 2026-10-07: genius-pro coverage is 0.4%, lrclib 7.8%, gate 90%.

PRECONDITIONS (STOP and tell Nikola if any fails):
- `git -C D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr status --porcelain` is empty, and the ledger has the "Resume 2026-10-20" section.
- No lyrics.db writer: `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db-journal` does not exist and `lyrics.db-wal` is missing or 0 bytes.
- No live annotate/build-db/rimer python process (check with Get-CimInstance Win32_Process and the CommandLine).
- Record lyrics.db size and LastWriteTime before you start.

BUILD (TDD; mock CLASSLA exactly like tests\test_annotate.py and tests\test_annotate_corpus_scope.py do; tests use tmp DBs only):
1. toolshop\annotate.py:
   a. `run_annotation(..., busy_timeout_ms: int = 60000)`: run `PRAGMA busy_timeout=<ms>` right after sqlite3.connect (the same fix SR-4 made for rimer writes in d4e06c1).
   b. Write preflight, BEFORE loading CLASSLA: refuse if `<db>-journal` exists, or if `BEGIN IMMEDIATE` can't be acquired within the timeout (then ROLLBACK). On refusal: write the status JSON with `finished: false` and `error: "<Type>: <msg>"`, print one clear line, and exit non-zero.
   c. Commit safety: wrap each per-batch commit in a bounded retry for "database is locked" (3 attempts, backoff 5 s / 15 s / 45 s). After the last failure: roll back the uncommitted batch, flush the status JSON with `finished: false`, `error`, `failed_at`, and `lines_done` = lines actually committed, then re-raise (non-zero exit). Committed batches stay, so `--resume` continues from them.
   d. On success, the status JSON gets `finished: true`, `finished_at`, and a `mairina_gate` block. For each scoped corpus: `{"non_empty": n, "annotated": a, "pct": p}`, using MAirina's exact gate semantics (mairina\corpus.py check_annotated): lines with `length(trim(coalesce(text_norm,''))) > 0`, song `corpus = ?` AND `language IN (<scoped languages>)`, annotated = EXISTS a token row. Plus `"pass": every pct >= 90.0`. Do NOT change coverage_summary's existing numbers (it uses text_raw and no language filter); add the gate block next to it.
   e. New tests\test_annotate_locking.py:
      (i) another connection holds BEGIN IMMEDIATE and busy_timeout_ms is small -> preflight refuses, and the status has `error`;
      (ii) the lock is released inside the timeout -> the run completes;
      (iii) a forced commit failure on batch 2 -> status `finished: false`, `error` set, `lines_done` == batch-1 count, and a following resume run skips exactly the committed lines;
      (iv) `mairina_gate` on a fixture db with sr / en / NULL-language songs and empty-text_norm lines matches a hand-computed expectation (en and NULL excluded from both numerator and denominator).
2. Build-db reminder: add `annotate_reminder(db_path) -> str` in toolshop\lyricsdb.py. It returns a note saying MAirina's finder stays offline until the scoped annotate finishes, plus the exact command:
   `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -m toolshop.cli lyrics annotate --db "<db>" --resume --corpus genius-pro --corpus lrclib --language sr`
   Print it at the end of the `build-db` branch in toolshop\cli.py (~line 2289). Test the function (cli.py can't be imported from this worktree: module-level mastering_tool import).
3. Tests: first list every test file that imports toolshop.annotate or toolshop.lyricsdb (Select-String over tests\). Run that set BEFORE your change and AFTER it, with `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -m pytest <files> -q -p no:cacheprovider`. Rule: no new failures, and the new tests pass. Paste both summaries.
4. Commit in three calls with explicit pathspecs (`git -C D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr add <paths>`, then `diff --cached --name-only`, then `commit`). Subject: `fix(lyrics-sr): annotate busy_timeout, write preflight, honest status, MAirina gate block`.

RELAUNCH SR-3 (the only lyrics.db write in this wave):
5. Keep the evidence: rename `.scratch\annotate_sr.log` to `.scratch\annotate_sr_20261013.log` and `.scratch\annotate_sr.err.log` to `.scratch\annotate_sr_20261013.err.log`. COPY `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\_annotate_status_sr.json` to `.scratch\_annotate_status_sr_20261013.json`.
6. Write `.scratch\launch_sr3.ps1` (ASCII only, no non-ASCII bytes; check with a Python byte scan). It must:
   - run `Start-Process` with `-FilePath D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`;
   - pass `-ArgumentList` with `-X utf8 -u "D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr\.scratch\run_annotate_sr.py"`;
   - redirect stdout to `.scratch\annotate_sr.log` and stderr to `.scratch\annotate_sr.err.log` (absolute paths);
   - use `-WindowStyle Hidden -PassThru` and print the PID.

   Run it with `powershell -NoProfile -File <abs path>`. `run_annotate_sr.py` stays as it is; it picks up the new defaults.
7. Liveness, bounded (no unbounded until-loops):
   - read the status JSON and confirm the process is alive (Get-CimInstance by PID) at about +3 min and about +10 min after the start;
   - `lines_done` must grow, `error` must be absent, and `updated` must be recent;
   - compute lines/s and the ETA from the two readings.

   If it dies: paste err.log, do NOT relaunch blindly, and record the failure in the ledger.

LEDGER + STOP:
8. Append an "A1a" entry using the ledger's template (commits, both test summaries, PID, start time, the two readings, lines/s, ETA). Set the A1a row to DONE and the SR-3 row to "RELAUNCHED <ts> PID <n>, ETA <ts>". Commit the ledger by explicit pathspec. `git status --porcelain` must be empty (`.scratch\` is ignored).
9. STOP and tell Nikola: "A1a done - SR-3 running (PID <n>, ETA <ts>). Keep the PC on and awake; nothing else may write lyrics.db until it finishes. Tell Claude when _annotate_status_sr.json shows finished: true (or an error)." Do not start A1b.

READ FIRST: D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr\ORCHESTRATION\lyrics_sr\ledger.md (all of it, including Gotchas), D:\Projects\.workspace_archive\plans\mairina-v3-revive-learn-write-5be0a1.md (Track A1), AGENTS.md.
WORK ONLY in D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr on branch lyrics-sr. Do NOT touch the MAirina worktree D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr-mairina (that is A1b), the main checkout, or any other lane.
DATA: the only real-lyrics.db write allowed is the SR-3 batch itself. Never run build-db, the rimer rebuild, populate_rhymes, or any other writer against the real db. Every DB op passes the explicit path D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db (ledger gotcha: the worktree default would create an empty db). Never delete data.
Python: D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -X utf8 -u. Stdlib + existing deps only (classla is already installed); no installs. Absolute paths. Foreground commands, except the detached batch in step 6. Kill nothing you did not start. No push, no merge, no CHANGELOG id.
END OF WAVE: the ledger entry with raw outputs and exit codes is committed, the worktree status is empty, then STOP as in step 9.
OPEN FILES: toolshop\annotate.py, toolshop\lyricsdb.py, toolshop\cli.py, tests\test_annotate.py, tests\test_annotate_corpus_scope.py, tests\test_annotate_locking.py, .scratch\run_annotate_sr.py, ORCHESTRATION\lyrics_sr\ledger.md
