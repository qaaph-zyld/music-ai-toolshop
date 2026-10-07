# G3 DB Ingest — Wave 2 Handoff

**Run time:** 2026-10-07 ~19:40–19:57 CEST (ingested_at UTC `2026-10-07T17:*`) | **Agent:** wave-2 subagent
**DB:** `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db` (canonical, 543 MB post-ingest)
**Code:** lane worktree `D:\Projects\Music-AI-Toolshop-wt-lyrics-g3` (G3 `COHORT_MAP` + `_FOLDER_COHORT_MAP` — verified `import toolshop` resolved to worktree, `'Zera' in COHORT_MAP → True`, `_FOLDER_COHORT_MAP['zera'] → 'drill_trap'`)

## VERDICT: INGEST CLEAN

All invariants hold: baseline unchanged (0/1425 rows touched), expected ≤1134 new songs reconciled exactly (1106 + 28 already-present + 5 dups = 1139 files), all new rows `study-only`/`release_ok=no`, zero new solo-role NULL cohorts, rimer grew monotonically, `PRAGMA integrity_check` = ok, FK check clean.

## Environment deviation (required to run the exact command)

The specified CLI command fails in the lane worktree out of the box:
`ModuleNotFoundError: No module named 'mastering_tool.tools'` — `toolshop/cli.py:29` imports `mastering_tool.tools.vocal_doctor` at top level and **all 9 submodules are uninitialized in this worktree** (`git submodule status` shows `-` on every row).

Resolution (no files modified, no submodule init — avoids touching shared `.git/modules` config): the **exact specified command** was run with `PYTHONPATH=D:\Projects\Music-AI-Toolshop` prepended, so submodule imports resolve from the main repo's existing checkouts (mastering_tool @ 9bddc72 = the pinned gitlink) while `import toolshop` still resolves from the worktree cwd. Verified: `toolshop.__file__` → worktree; `vocal_doctor.__file__` → main repo. `cli.py` build-db handler is a thin pass-through to `build_database(root, db_path, corpus, incremental)` (cli.py:2293-2300), so behavior is identical.

## 1. Baseline (pre-ingest, `mode=ro`)

- `total_songs` = **24,088**; `genius-pro` = **1,425** ✓ (expected)
- genius-pro cohorts: `drill_trap` 808 | `pop` 524 | `NULL` 93 (all 93 are `role='featured'`)
- license: all 1,425 = `study-only` / `release_ok=no`; `foreign_identifier` all NULL
- Snapshot: `.scratch\g3_baseline_genius_pro.json` (1,425 rows, ids ≤ 2850)

## 2. Ingest run (log: `.scratch\g3_ingest.log`)

```
Unified index: ...\_index.json (2531 entries)
Dedup log: ...\_dedup_log.json (78 duplicates)
Incremental: 1425 existing 'genius-pro' songs keyed
Rhymes computed: 216071 rhyme rows across 1106 songs
Metrics computed for 1106 songs
Ingested: 1106 songs, 7863 sections, 116606 lines
Duplicates dropped: 5 | Already present: 1498 | Skipped: 0
```

Index artifacts rebuilt at corpus root: `_index.json` (2,531 entries, 1,734,379 B, mtime 19:40:24), `_dedup_log.json` (78 entries; 22 G3-dir / 56 old-dir source paths).

## 3. Post-ingest verify (`mode=ro`)

| Metric | Before | After | Δ |
|---|---|---|---|
| total_songs | 24,088 | 25,194 | +1,106 |
| genius-pro | 1,425 | **2,531** | +1,106 |
| drill_trap | 808 | 1,350 | +542 |
| pop | 524 | 920 | +396 |
| genre_cohort NULL | 93 | 261 | +168 |

- genius-pro count (2,531) **equals the unified-index unique count exactly** — corpus disk state and DB are 1:1.
- New rows: ids **25514–26619** (contiguous), `ingested_at` 2026-10-07T17:* UTC, spanning **38 categories** (= all 38 G3 dirs), 7,863 sections.
- **Baseline diff: 0 missing / 0 extra / 0 changed** of 1,425 rows (full-row field comparison vs snapshot).
- Other corpora untouched: ccmixter 547, gutenberg_pd 1306, hymnary 3, lrclib 887, mudcat-digitrad 7105, sacred-texts 277, wikisource_pd 12538 — identical to baseline.
- License invariant: **all 2,531 genius-pro rows** `license_tier='study-only'`, `release_ok='no'`; `release_ok='yes'` count = **0** (new rows too).
- Per-row completeness: 1106/1106 new songs have sections, `song_metrics`, `song_rhyme_metrics`; 216,071 `line_rhymes` rows written for them.
- `PRAGMA integrity_check` → `ok`; `PRAGMA foreign_key_check` → empty; WAL checkpointed (`lyrics.db-wal` = 0 B).

### NULL-cohort analysis (by-design, not a defect)

All **168** new NULLs are `role='featured'` in `*-featured` dirs whose `primary_artist` is a **non-target external artist** (Djare ×8, Dizzy (SRB) ×6, 30Zona/Biba/Faberge/Gajs/Gudroslav/In Vivo/KUKU$/Ludi Srbi ×3, …). Identical pattern to the 93 baseline NULLs (all `featured`). **Zero** new `solo`/duo/trio rows have NULL cohort — the G3 COHORT_MAP + folder fallback applied to every target song. This matches established corpus semantics ("featured-folder primaries are non-target → NULL", lyricsdb.py:40 comment); the +168 is expected, distinguished from baseline.

### Reconciliation vs audit expectation (≤1134)

1139 new-dir files = **1106 ingested + 28 already_present + 5 duplicates_dropped**
- 5 dropped = audit flag #2's five song-ids stored twice across dirs.
- 28 already-present = G3-dir files whose normalized `(title, primary_artist)` keys were already in the DB from earlier batches (e.g., Corona/Devito/TNG/Nikolija-primaried songs re-fetched into `fox-featured` etc. — audit's "may already exist" caveat). Cross-check: `_index.json` holds 1,117 G3-dir entries = 1106 ingested + 11 already-present-but-first-in-scan.
- Net new songs = 1106 vs 1134 distinct new `genius_song_id`s → 28 overlapped pre-existing keys. Fully reconciled.

## 4. Rimer (log: `.scratch\g3_rimer.log`)

```
Rimer DB built: 370116 pairs, 16665 unique skeletons, 17802 drill, 4100 pop
```

| Metric | Before | After | Δ |
|---|---|---|---|
| rhyme_pairs | 358,862 | 370,116 | +11,254 |
| vowel_skeletons | 16,148 | 16,665 | +517 |

Pre-rimer baseline re-measured in-session: 358,862 / 16,148 (matches task-stated baseline).

## Files created/modified

- `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\genius\_index.json` (rebuilt, 2,531 entries)
- `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\genius\_dedup_log.json` (rebuilt, 78 entries)
- `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db` (+1,106 genius-pro rows, +sections/lines/metrics/rhymes, +rimer rows)
- `.scratch\g3_baseline_genius_pro.json`, `.scratch\g3_ingest.log`, `.scratch\g3_rimer.log` (evidence)
- This handoff. **No git commits made** (orchestrator owns). No other repo files touched.

## Notes for downstream

1. lacku `genius_song_id=5446636` ("Tenzija") remains absent — known accepted 1-song gap (wave-1 audit flag 1); fetch-side decision pending.
2. The 168 featured-role NULL cohorts are intentional corpus semantics. If a downstream wave wants folder-cohort on featured rows, that's a policy change to `_insert_song` — out of scope here.
3. Ledger (`ORCHESTRATION/lyrics_g3/ledger.md`) G3-B row still reads RUNNING (audit flag 4) — outside my modify-scope; orchestrator to flip to DONE at commit time.
4. `foreign_identifier` is NULL on all genius-pro rows (old and new — the song JSONs don't carry it); dedup is `(title, primary_artist)`-keyed. Don't rely on fid for joins.

## Worktree state at close-out (declared, not committed by me)

- `M ORCHESTRATION/lyrics_g3/ledger.md` — pre-existing wave-1 edit, untouched by this wave.
- `?? ORCHESTRATION/lyrics_g3/wave1/g3_fetch_audit_handoff_r2.md` — wave-1 handoff (untracked).
- `?? ORCHESTRATION/lyrics_g3/wave2/g3_db_ingest_handoff.md` — this file (untracked).
- `.scratch/` — gitignored scratch evidence.
- Canonical corpus `_index.json`/`_dedup_log.json` and `lyrics.db` live outside the repo (data boundary) — the DB is the commit.
