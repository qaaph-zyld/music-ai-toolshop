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

MY TASK: lyrics-sr A1b - commit SR-5 (MAirina reads genius-pro + lrclib, language sr), prove the MAirina finder is alive with a live smoke run, and prepare the lane for Claude's merge (SR-V). PRE-APPROVED (MAirina v3 plan, approved 2026-10-20): skip bootstrap step 7, do not re-plan.

PRECONDITIONS (STOP and tell Nikola if any fails):
- ledger.md: the "A1.3 coverage gate" row shows Claude's PASS, with genius-pro and lrclib (language sr) >= 90% each and the post-batch lyrics.db size/mtime recorded.
- `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\_annotate_status_sr.json` has `finished: true`, no `error`, and `mairina_gate.pass: true`.
- No annotate/build-db/rimer process is alive, and no `lyrics.db-journal` exists.
- `lyrics.db-wal` is absent or 0 bytes. lyrics.db is in WAL mode since A1a, and MAirina (`corpus.build_guarded`) refuses to build while the `-wal` is non-empty. A non-empty `-wal` with no writer alive needs a checkpoint, which only Nikola may approve.
- `git -C D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr status --porcelain` is empty.

STEPS:
1. Review the SR-5 work in progress, uncommitted in the MAirina worktree D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr-mairina (branch lyrics-sr-lrclib, base a329774). It touches 5 files: mairina\corpus.py (CORPORA = genius-pro + lrclib, LANGUAGES = sr, CACHE_VERSION 5, _corpus_sql adds the language filter), tests\conftest.py, tests\test_atlas_compare.py, tests\test_keys_corpus.py, tests\test_targets.py.
   - Confirm it matches the ledger's locked decisions. NULL-language and en songs are excluded on purpose (SR-1 audit).
   - Grep mairina\ for every corpus-scoped SQL (`corpus IN`, `FROM songs`, `JOIN songs`, `CORPORA`). Every query must go through `corpus._corpus_sql()`. Any query that bypasses it is a leak: fix it, with a test.
2. Run the MAirina suite from that worktree: `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -m pytest "D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr-mairina\tests" -q -p no:cacheprovider`, with `PYTHONPATH=D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr-mairina`. Paste the summary. test_live_smoke skips there, because DEFAULT_LYRICS_DB resolves under .worktrees; step 3 covers it.
3. Live smoke. Write `D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr\.scratch\mairina_smoke.py`:
   - It puts the MAirina worktree first on sys.path and creates a temp data_dir (`tempfile.mkdtemp()`), so no cache or app db lands in a repo.
   - It calls `mairina.cli.main(argv, lyrics_db=r"D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db", data_dir=<tmp>)` for each of:
     - `["anchors", "--scheme", "AABB", "--lane", "pop"]`
     - `["rhyme", "noc", "--lane", "pop"]`, with the word written as the real `noć` via `\u0107`
     - `["multi", "<a two-word ending of your choice from the corpus>", "--lane", "pop"]`
     - `["compare", "--lane", "pop"]`
     - `["xray", <temp .txt holding the fenced block of D:\Projects\Music-AI-Toolshop\MAirina_Tucc\lyrics_popper\gold\gold_002\lyrics.md, tag lines removed>]`
   - It records the exit code, the first 5 output lines and the wall time of each, plus the time of the first index build (CACHE_VERSION 5).
   - Every command must exit 0 with non-empty results.
   - Run it with the venv python, `-X utf8 -u`.
   - Check each command's flags against `--help` first, and adjust argv (not the code) if a flag differs.
4. Commit SR-5 in three calls with explicit pathspecs: `git -C D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr-mairina add <paths>`, then `diff --cached --name-only`, then `commit`. Subject: `feat(lyrics-sr): MAirina reads genius-pro+lrclib, language sr (CACHE_VERSION 5)`. That worktree's status must then be empty.
5. SR-V in the parent lane:
   - `git -C D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr merge master`. Resolve conflicts if any; only unrelated files are expected.
   - A1a nit (Claude's verdict): `toolshop/lyricsdb.py` `annotate_reminder` hardcodes the venv path (AGENTS: no absolute paths in code). Build the command from `sys.executable` instead. Add a test that monkeypatches `sys.executable` to a fake path (e.g. `X:\\fake\\python.exe`) and asserts the note contains that fake path and does not contain `Music-AI-Toolshop`. Test first, then the fix; commit it separately by explicit pathspec (`fix(lyrics-sr): annotate_reminder uses sys.executable`).
   - Then rerun the A1a test set (the annotate/lyricsdb importers + test_annotate_locking.py). No new failures.
   - Update the ledger rows:
     - SR-3: DONE, citing Claude's A1.3 numbers;
     - SR-5: DONE, with the MAirina commit hash;
     - SR-V: DONE, with the pasted smoke output;
     - MERGE: "ready for Claude".
   - Append an "A1b" entry using the template. Commit the ledger by explicit pathspec. Both worktrees' status must be empty.
6. Do NOT bump the MAirina gitlink in the parent and do NOT merge anything into master or MAirina main. Claude merges lyrics-sr-lrclib into MAirina main, then lyrics-sr into master (CHANGELOG id at merge), bumps the pointer, and removes the worktrees.
7. STOP and tell Nikola: "A1b done - MAirina finder alive (smoke 5/5), lane ready for Claude's merge."

READ FIRST: D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr\ORCHESTRATION\lyrics_sr\ledger.md, D:\Projects\.workspace_archive\plans\mairina-v3-revive-learn-write-5be0a1.md (Track A1), D:\Projects\Music-AI-Toolshop\MAirina_Tucc\AGENTS.md.
WORK ONLY in D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr-mairina (MAirina, branch lyrics-sr-lrclib) and D:\Projects\Music-AI-Toolshop\.worktrees\lyrics-sr (parent, branch lyrics-sr: ledger, .scratch, merge from master). Never edit the main checkouts, the gold_kb files (MAirina ORCHESTRATION\gold_kb, lyrics_popper\gold) or other lanes.
DATA: this wave never writes lyrics.db; all access is read-only, which MAirina already does through its immutable URI. Caches and the app db go to the temp data_dir only.
PRODUCT RULE: MAirina finds and analyses; it never writes lyric lines. The smoke inputs are existing user-provided text, and outputs are words, rhymes and tags.
Python: D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -X utf8 -u. No installs. Absolute paths. Foreground only. No push, no merge into master/main, no CHANGELOG id.
END OF WAVE: ledger entry committed, both worktrees clean, then STOP as in step 7.
OPEN FILES: (MAirina worktree) mairina\corpus.py, mairina\devices.py, mairina\targets.py, mairina\atlas.py, tests\conftest.py, tests\test_keys_corpus.py; (parent worktree) ORCHESTRATION\lyrics_sr\ledger.md, .scratch\mairina_smoke.py
