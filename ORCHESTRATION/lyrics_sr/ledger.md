# Orchestration ledger — lyrics-sr (Serbian corpus consolidation + activation)

Lane: `lyrics-sr` | Worktree: `Music-AI-Toolshop/.worktrees/lyrics-sr` | Plan: `~/.devin/plans/plan-26ca8ded2d2b9ff3.md`
Origin: `lyrics-g4` handoff (2026-10-11) carried-forward → user directed: consolidate + actually use the Serbian corpus.

## Verified baseline (2026-10-12, lyrics.db 26,650 songs / 9 corpora)

- Serbian slices: `genius-pro` 2,532 (language NULL), `lrclib` 887 (NULL, ~20% international), `wikisource_pd` 12,108 `sr` (folk — separate register).
- **MAirina dead**: `check_annotated` needs ≥90% CLASSLA coverage on genius-pro; actual coverage = 0/116,658 lines. 89,784 stray tokens sit on EN corpora — a DB-wide annotate run died early (annotate had no corpus scope).
- `rhyme_pairs` 370,144 rows built from ALL corpora — top pair `away/day` (EN). ~22k rows carry drill/pop cohort.
- lrclib cohorts: drill_trap 425 / pop 298 / NULL 164 (NULL ≈ unmapped Serbian artists + international).

## Locked decisions (2026-10-12)

- wikisource folk = separate register (queryable; excluded from pro baselines/MAirina).
- lrclib = verify + tag + consume (audit → 'sr' tag → annotate → MAirina CORPORA + rhyme_pairs).
- `rhyme_pairs` rebuilt scoped `language='sr'` (includes folk pairs, cohort NULL marks register).
- CLASSLA re-annotation = detached overnight resumable batch.

## Waves

| Wave | Status | Commit | Evidence |
|---|---|---|---|
| SR-0 pre | DONE | — | worktree at d896c82; classla 2.2.1; pilot 500 lines/180s ≈ 2.78 l/s |
| SR-2 annotate scope | DONE (code+tests) | — | `--corpus` + `--language` flags (repeatable), `--status` JSON per-500-line flush, per-corpus coverage block; 19 tests green |
| SR-1 audit+tag | DONE | — | 3,390 language tags (gp 2465sr/41en/26NULL, lrclib 853sr/31en/3NULL); cohort fold-fix +73 lrclib; dedup report below |
| SR-3 overnight batch | DONE 2026-10-21 | f6fc759, b3ff8a0 | Finished 03:22:06: 150,588/150,588 lines, 1,125,682 tokens, 25,809 entities, no error, `mairina_gate.pass: true`. Claude's A1.3 gate PASS 19:40: genius-pro 113,890/113,890 + lrclib 39,345/39,345 = **100.00% each** (`language='sr'`); db 598,089,728 B, mtime_ns 1792545761305058900; `PRAGMA quick_check` ok. History: died 2026-10-13 00:08 at 2,000/152,588 (`database is locked`, no busy_timeout + SR-4 writer), relaunched 2026-10-20 21:32 PID 10620 via `.scratch/launch_sr3.ps1`, resume skipped 8,338 done lines |
| SR-4 rimer rebuild | DONE | d4e06c1 | `build_rimer_db(corpora, languages)` + busy_timeout; rebuilt languages=['sr'] → **252,518 pairs** (13,891 skeletons; drill 17,577/pop 4,211/NULL 230,823 folk-dominated); `populate_rhymes` now skips en+de; slang_terms lineage safe (NULL-cohort + non-sr never reach tokens) |
| SR-5 MAirina wire | DONE 2026-10-21 | `5be3276` (MAirina repo, `lyrics-sr-lrclib`) | `mairina/corpus.py` CORPORA=genius-pro+lrclib, LANGUAGES=('sr',), CACHE_VERSION 5, `_corpus_sql` adds language filter; corpus-SQL audit: every lyrics.db query routes through `_corpus_sql()`, no leaks; suite 334 passed/2 skipped; NULL-language + en rows excluded on purpose (SR-1 audit). NOTE lrclib unique value ~45-80 songs (808 cross-corpus dupes) |
| SR-V verify | DONE 2026-10-21 | — | Live smoke 5/5 exit 0 vs real lyrics.db: anchors AABB pop (4 anchors), rhyme noć (9), multi "bez tebe" (20), compare pop (20), xray gold_002 (45 lines). First CACHE_VERSION-5 index build 301.9 s. Raw output in A1b entry + `.scratch/mairina_smoke_out.txt` |
| MERGE | **ready for Claude** | — | CHANGELOG id at merge; Claude merges `lyrics-sr-lrclib`→MAirina main, `lyrics-sr`→master, bumps gitlink, removes worktrees |

## SR-1 evidence (2026-10-12)

- `apply_languages` dry→real: 3,390 updates; verdicts {sr 3318, en 72, ambiguous 29}.
- Cohort: `derive_genre_cohort()` extracted; ASCII-fold on both compare sides (fixes `Maya Berovic`/`CØBY` misses); `backfill_genre_cohort(conn, corpus)` — lrclib +73, genius-pro +0 (already tagged). genius-pro NULL=255 (featured/non-target + unmapped), lrclib NULL=91.
- Dedup (folded artist::title): **808 cross-corpus dup keys**, 1 intra-genius-pro key, 89 same-title/diff-artist-spelling keys (mostly legit different songs or "a & b" formatting). Report-only; nothing quarantined.
- Unmapped sr-verdict artists (306 songs, need user ear-verdict for COHORT_MAP): Rimski (17), Djare 8, Klijent 7, Biba 8, Dizzy (SRB) 6, Zli Toni 5, THCF 4, Faberge 4, 30Zona 3, Nucci 6, Sajfer 3, Vuk Mob 3, Kurtoazija 3, Cvija 3, Elena 3, Furio Djunta 3, In Vivo 3, Relja Torinno 3, Riga Dri 3, Skele (SRB) 3 + long tail.

## Gotchas

- DB ops from this worktree must pass `--db D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db` — `DEFAULT_DB_PATH` resolves `<code-repo>/data/toolshop` and would silently create an empty worktree db.
- `annotate_lines` selected DB-wide pre-lane; `--corpus` is new (lyrics-sr).

## Resume 2026-10-20: MAirina v3, track A1 (Claude orchestrates, Devin builds)

Phase plan: `D:\Projects\.workspace_archive\plans\mairina-v3-revive-learn-write-5be0a1.md`, approved by the user 2026-10-20.

**Measured by Claude 2026-10-20** (read-only probe; same query as `mairina/corpus.py check_annotated`, per corpus):
- genius-pro: 500 / 116,658 non-empty lines annotated (0.4%).
- lrclib: 3,219 / 41,060 (7.8%).
- MAirina gate: 90%, so the MAirina finder is **offline**.
- Language tags: genius-pro sr 2465 / en 41 / NULL 26; lrclib sr 853 / en 31 / NULL 3. rhyme_pairs 252,518.
- lyrics.db 543,211,520 B, mtime 2026-10-13 00:11, no `-journal` / `-wal`. No annotate process alive.

| Step | Owner | Prompt | Status | Evidence |
|---|---|---|---|---|
| A1.0 ledger truth | Claude | — | DONE 2026-10-20 | SR-3 and SR-5 rows corrected above |
| A1a lock fix + gate-equivalent status + build-db warning + relaunch SR-3 | Devin | `prompts/A1a.md` | DONE 2026-10-20 | b3ff8a0; SR-3 PID 10620 running, ETA ~08:20 |
| A1.3 coverage gate | Claude | — | **PASS 2026-10-21 19:40** | genius-pro 113,890/113,890 and lrclib 39,345/39,345 (100.00% each, `language='sr'`); db 598,089,728 B, mtime_ns 1792545761305058900 (2026-10-21 03:22:41); see verdict below |
| A1b SR-5 commit + SR-V smoke + merge prep | Devin | `prompts/A1b.md` | DONE 2026-10-21 | SR-5 = `5be3276` on `lyrics-sr-lrclib`; merge master→lyrics-sr clean (`studio` gitlink only); `0ebfc5b` annotate_reminder sys.executable; smoke 5/5 PASS |
| Merge lyrics-sr -> master, lyrics-sr-lrclib -> MAirina main, pointer bump, worktree removal | Claude | — | not started | — |

### Entry template (builder)

```
### A1<x> - <date> - builder: <session name>
Commits on <branch>: <hash> <subject>, ...
Commands + raw output (exit codes): <paste>
Tests: <file / count / result>
Worktree status: <git -C <worktree> status --porcelain>  (must be empty)
Deviations: <each with reason, or "none">
Not verified: <list, or "none">
```

### A1a - 2026-10-20 - builder: Devin

Commits on lyrics-sr: `b3ff8a0` fix(lyrics-sr): annotate busy_timeout, write preflight, honest status, MAirina gate block

What changed:
- `toolshop/annotate.py`: `run_annotation(..., busy_timeout_ms=60000)` runs `PRAGMA busy_timeout` right after connect; write preflight BEFORE classla load — refuse on `<db>-journal` present, then `PRAGMA journal_mode=WAL` + `BEGIN IMMEDIATE` probe inside the timeout (ROLLBACK after) — refusal writes status `finished:false` + `error:"<Type>: <msg>"` and exits `SystemExit(1)`. Per-batch commits go through `_commit_with_retry` (retries after 5/15/45 s); final failure → rollback pending batch, status `finished:false` + `error` + `failed_at` + `lines_done`=committed-only, re-raise. Success status adds `finished_at` + `mairina_gate` (per scoped corpus `{non_empty, annotated, pct}` using `check_annotated` semantics — `text_norm` non-empty, `corpus=?`, `language IN (...)`, `EXISTS tokens` — plus `"pass"` at >=90). Initial `lines_done:0` status now written at run start.
- `toolshop/lyricsdb.py`: `annotate_reminder(db_path)` returns the offline-until-annotate note + exact resume command.
- `toolshop/cli.py`: build-db prints `annotate_reminder(db_path)` after the Done summary.
- `tests/test_annotate_locking.py`: 5 new tests (preflight refuse, wait+release, forced commit failure + resume-skip, gate fixture, reminder).

Commands + raw output (exit codes):
- Baseline `pytest` (12 files importing toolshop.annotate/toolshop.lyricsdb): `249 passed, 2 skipped in 401.95s` (exit 0)
- After change, same set + test_annotate_locking.py: `254 passed, 2 skipped in 421.65s` (exit 0)
- `git commit` → `[lyrics-sr b3ff8a0] 4 files changed, 410 insertions(+), 6 deletions(-)` (exit 0)
- Evidence preserved: `.scratch/annotate_sr_20261013.log`, `.err.log`, `_annotate_status_sr_20261013.json` (copied from data dir)
- `.scratch/launch_sr3.ps1` byte-scanned ASCII-clean (485 B); `powershell -NoProfile -File launch_sr3.ps1` → `PID 10620` (exit 0)
- Liveness +3min (21:35:38): PID alive; status `updated 21:35:31`, `lines_done 500`, no error
- Liveness +10min (21:42:28): PID alive; status `updated 21:41:59`, `lines_done 2000`, no error; rate 1500 lines / 388 s = **3.87 l/s**; ETA for 148,588 remaining ≈ **2026-10-21 ~08:20** (slower than the plan's 5.7 l/s estimate — measured value)

Tests: tests/test_annotate_locking.py — 5 passed; suite delta 249→254, no new failures.

Worktree status: clean (verified after ledger commit below; `.scratch/` ignored).

Deviations:
- No separate non-empty `-wal` refusal: a committed WAL writer can leave a non-empty `-wal` (checkpoint timing), which would falsely refuse the wait-path the spec's test (ii) requires. The `BEGIN IMMEDIATE` probe inside `busy_timeout` covers both journal modes, so the file check is `-journal` only.
- Added the initial `lines_done:0` status write at run start — otherwise `updated` stays at the crash timestamp until the first 500-line flush (~2–3 min) and the +3 min liveness check would read a stale file as failure.

Not verified: none against spec — preflight/wait/retry/gate all covered by the new tests and confirmed live on the first two flushes of the real run.

### A1a - orchestrator verdict - Claude - 2026-10-20 22:05: PASS

- Commits present on lyrics-sr: b3ff8a0 (fix) and d3a25d9 (ledger). `git status --porcelain` empty.
- Code reviewed (b3ff8a0):
  - busy_timeout is set right after connect.
  - The `-journal` and `BEGIN IMMEDIATE` preflight runs before CLASSLA loads.
  - Bounded commit retry, with rollback, an honest status and a re-raise on final failure.
  - The `mairina_gate` block reproduces `check_annotated` semantics plus the SR-5 language scope.
- **Deviations accepted:** no `-wal` refusal (a non-empty WAL is normal under WAL mode; the probe covers real
  writers), and the start-of-run status write.
- **Nit, not blocking:** `annotate_reminder` hardcodes the venv path (AGENTS "no absolute paths in code"). Prefer `sys.executable`; fold into A1b.
- **Tests (Claude's own run):** `tests/test_annotate_locking.py` + `test_annotate.py` + `test_annotate_corpus_scope.py`
  → `24 passed in 184.47s`, exit 0. Not re-run by Claude: the other 9 of Devin's 12-file set (Devin reports 249 → 254 passed, 2 skipped).
- **Batch liveness (Claude):** PID 10620 alive (python.exe, created 21:32:09, command = `.scratch/run_annotate_sr.py`).
  - Status: `lines_done` 8,500 @ 21:58:24, then 10,000 @ 22:03:05, no `error`.
  - lyrics.db-wal is growing (normal under WAL).
  - Rate since Devin's 21:41:59 reading: 8,000 lines / 1,266 s ≈ 6.3 l/s (5.3 l/s while Claude's pytest shared the CPU).
  - Remaining 140,588 → **revised ETA ≈ 2026-10-21 04:30-05:30**. Devin's 08:20 came from the warm-up window.
- **Next:** A1.3 coverage gate (Claude) once `finished: true`. A1b waits for it.

### A1.3 - orchestrator gate - Claude - 2026-10-21 19:40: PASS

- **Batch finished cleanly.**
  - Status: `finished: true` at 03:22:06, 150,588 / 150,588 lines, 1,125,682 tokens, 25,809 entities, no `error`.
  - `mairina_gate.pass: true`.
- **Processes:** no annotate, build-db or rimer process is alive (19:32). The live python processes are
  audition_review servers and the ai_insta_saved sync loop, and none of them writes lyrics.db.
- **Logs:** `.scratch/annotate_sr.err.log` has 0 lines matching traceback/error (CLASSLA INFO only).
  `annotate_sr.log` ends with `Done: 150588 lines`.
- **Sidecars:** `-wal`, `-shm` and `-journal` are all absent. The connection closed cleanly and the WAL was
  checkpointed, so step K was not needed.
  - The db header bytes 18/19 are 2/2, so **lyrics.db stays in WAL mode** (persistent, set by the A1a preflight).
- **Independent probe** (Claude; read-only `mode=ro&immutable=1`; the same SQL as `check_annotated`, per corpus, `language='sr'`):

  | corpus | annotated / non-empty | coverage |
  |---|---|---|
  | genius-pro | 113,890 / 113,890 | 100.00% |
  | lrclib | 39,345 / 39,345 | 100.00% |
  | aggregate | 153,235 / 153,235 | 100.00% |

  - These numbers equal the status `mairina_gate` block.
  - The coverage queries took 16.1 s on a cold cache.
- **The real gate:** SR-5's `mairina.corpus.check_annotated` (worktree `lyrics-sr-mairina`, CORPORA genius-pro +
  lrclib, LANGUAGES sr, CACHE_VERSION 5) passed in 1.5 s warm.
- **Integrity:** `PRAGMA quick_check` = `ok` (113 s).
- **Post-batch baseline** (also the gold_kb W0 baseline):
  - size **598,089,728 B**;
  - `st_mtime_ns` **1792545761305058900** (2026-10-21 03:22:41 +02:00).
  - The probe left the size, mtime and sidecars unchanged.
- **For the record (not a gate input):** the batch's own unscoped print shows genius-pro 113,890 / 116,658
  (97.6%) and lrclib 40,417 / 41,060 (98.4%). The remainder is the NULL/en lines that SR-1 excluded on purpose.
- **Next:** A1b is unblocked (Devin, `prompts/A1b.md`). No other lyrics.db writer runs until the lane merges.

### A1b - 2026-10-21 - builder: Devin

Commits on `lyrics-sr-lrclib` (MAirina repo): `5be3276` feat(lyrics-sr): MAirina reads genius-pro+lrclib, language sr (CACHE_VERSION 5)
Commits on `lyrics-sr` (parent): merge `master`→`lyrics-sr` (clean, `studio` gitlink only), `0ebfc5b` fix(lyrics-sr): annotate_reminder uses sys.executable

What changed:
- SR-5 review + commit: `mairina/corpus.py` `CORPORA = ("genius-pro", "lrclib")`, `LANGUAGES = ("sr",)`,
  `CACHE_VERSION 5`, `_corpus_sql()` gains `language IN (...)`. Fixtures/tests updated
  (`conftest.py` language column + song 6 = genius-pro/`en` guard case, `test_atlas_compare`,
  `test_keys_corpus` CACHE_VERSION 5 + `test_en_language_rows_excluded`, `test_targets`).
- Corpus-SQL leak audit (`corpus IN` / `FROM|JOIN songs` / `CORPORA` / `execut*` sweep of `mairina/`):
  every lyrics.db query (corpus, targets, flow, devices, comparisons, atlas) routes through
  `corpus._corpus_sql()`; `votes/used/hints/fingerprint/bans` queries hit mairina.db app tables only.
  No leaks — nothing to fix.
- `toolshop/lyricsdb.py` `annotate_reminder` builds the resume command from `sys.executable`
  (was a hardcoded venv path; A1a nit, Claude's verdict). Test `test_annotate_reminder_uses_sys_executable`
  monkeypatches `sys.executable` to `X:\fake\python.exe`, asserts the note contains it and not
  `Music-AI-Toolshop`. Red → fix → green.
- `git merge master` into `lyrics-sr`: clean (ort), only `studio` gitlink changed.

Commands + raw output (exit codes):
- MAirina suite (worktree, `PYTHONPATH=.worktrees/lyrics-sr-mairina`):
  `334 passed, 2 skipped in 371.53s` (exit 0; skips incl. `test_live_smoke` — DEFAULT_LYRICS_DB
  resolves under `.worktrees`)
- Live smoke `.scratch/mairina_smoke.py` (venv python `-X utf8 -u`, temp data_dir, real lyrics.db
  read-only). Output `.scratch/mairina_smoke_out.txt`:
  ```
  First index build (CACHE_VERSION 5): 301.9 s
  mt anchors --scheme AABB --lane pop   exit=0 wall=17.9s result_lines=4  OK   ([A] najgorim, [A] otvorim, [B] bolujem …)
  mt rhyme noć --lane pop               exit=0 wall=0.9s  result_lines=9  OK   (sinoć 3.34, ponoć 3.33, moć 3.27 …)
  mt multi "bez tebe" --lane pop        exit=0 wall=1.2s  result_lines=20 OK   (je remek, je hekler, je nered …)
  mt compare --lane pop                 exit=0 wall=2.1s  result_lines=20 OK   (leptir 16x, led 13x, laž 7x …)
  mt xray <gold_002 fenced, tags out>   exit=0 wall=14.2s result_lines=45 OK   (X-ray 45 lines, advisory)
  SMOKE PASS — 5 commands run
  ```
- SR-5 commit: `[lyrics-sr-lrclib 5be3276] 5 files changed, 43 insertions(+), 23 deletions(-)` (exit 0)
- `git merge master`: `Merge made by the 'ort' strategy. studio | 2 +-` (exit 0)
- reminder tests `-k reminder`: `2 passed` (exit 0); new test was red before the fix.
- A1a rerun (annotate/lyricsdb importers + test_annotate_locking.py, 13 files):
  `255 passed, 2 skipped in 445.18s` (exit 0; 254 → 255 = the new reminder test)

Tests: MAirina suite 334 passed/2 skipped; parent A1a set 255 passed/2 skipped. No new failures.

Worktree status: clean — `git -C .worktrees/lyrics-sr-mairina status --porcelain` empty;
`git -C .worktrees/lyrics-sr status --porcelain` empty (after ledger commit below; `.scratch/` ignored).

Deviations:
- `multi` phrase chosen as `bez tebe` (93 occurrences at line-end in pop cohort, sr — measured).
- Smoke xray argv kept the prompt's exact form (no `--lane`; default `all`/`strofa`).

Not verified:
- Nothing past merge: gitlink pointer deliberately not bumped (step 6); Claude merges.
- Smoke ran through the main checkout's `toolshop` (editable install), same as production `mt`.
