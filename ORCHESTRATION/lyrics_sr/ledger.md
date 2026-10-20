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
| SR-3 overnight batch | **FAILED 2026-10-13 00:08** (corrected by Claude 2026-10-20) | f6fc759 | Launched PID 19096 at 00:02:48 via `.scratch/run_annotate_sr.py` (cli.py unusable from worktree: module-level `mastering_tool` import), 152,588 sr lines. **Died at 2,000/152,588** with `sqlite3.OperationalError: database is locked` (`annotate.py:256`, `.scratch/annotate_sr.err.log`). Status JSON still says `finished: false` and has no error field, which is why this row read RUNNING. Root cause: `run_annotation` sets no `busy_timeout`, and SR-4's rimer rebuild wrote lyrics.db at the same time (db mtime 00:11). Resume plan: A1a below |
| SR-4 rimer rebuild | DONE | d4e06c1 | `build_rimer_db(corpora, languages)` + busy_timeout; rebuilt languages=['sr'] → **252,518 pairs** (13,891 skeletons; drill 17,577/pop 4,211/NULL 230,823 folk-dominated); `populate_rhymes` now skips en+de; slang_terms lineage safe (NULL-cohort + non-sr never reach tokens) |
| SR-5 MAirina wire | PENDING (uncommitted WIP) | — | child-repo branch; NOTE lrclib unique value now only ~45-80 songs (808 cross-corpus dupes). WIP sits uncommitted in the MAirina worktree `.worktrees/lyrics-sr-mairina` (branch `lyrics-sr-lrclib`, base a329774; 5 files: `mairina/corpus.py` CORPORA+LANGUAGES+CACHE_VERSION 5, `tests/conftest.py`, `test_atlas_compare`, `test_keys_corpus`, `test_targets`; mtime 2026-10-13 00:14) |
| SR-V verify | PENDING | — | — |
| MERGE | PENDING | — | CHANGELOG id at merge |

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
| A1a lock fix + gate-equivalent status + build-db warning + relaunch SR-3 | Devin | `prompts/A1a.md` | not started | — |
| A1.3 coverage gate | Claude | — | waits for `finished: true` | — |
| A1b SR-5 commit + SR-V smoke + merge prep | Devin | `prompts/A1b.md` | not started | — |
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
