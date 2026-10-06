# I9 handoff — wave P2-I: incremental build-db × 7 corpora + genius invariant + rimer gate + _release_v1 export

**Date:** 2026-10-05/06 (session ~21:20–00:15)
**Lane:** `lyrics-p2` @ worktree `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2`
**Role:** implementer — wave P2-I of `ORCHESTRATION/lyrics_sources/waves_megaplan_p2.json`, executed per `.workspace_archive/plans/lyrics-p2-tail/window-2.md` bootstrap. No code edits — pure data execution.
**Env on every command:** `TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop`, `PYTHONUNBUFFERED=1`, interpreter `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -X utf8`, console script `D:/Projects/Music-AI-Toolshop/.venv/Scripts/toolshop.exe` (editable install → resolves main-repo code + data dir regardless of cwd).

## Step 2 — incremental ingest per corpus (all `toolshop lyrics build-db --corpus <tag> --incremental`)

| corpus | wall | ingested | already_present | dupes dropped | skipped | lines | rhyme rows | exit |
|---|---|---|---|---|---|---|---|---|
| hymnary | 28s | 2 | 1 | 0 | 0 | 68 | 95 | 0 |
| sacred-texts | 2617s | 254 | 23 | 0 | 0 | 21,629 | 463,941 | 0 |
| ccmixter | 122s | 530 | 17 | 0 | 0 | 15,726 | 41,683 | 0 |
| gutenberg_pd | 296s | 1,303 | 3 | 46 | 0 | 110,228 | 312,097 | 0 |
| mudcat-digitrad | 780s | 7,080 | 25 | 45 | 0 | 258,989 | 835,875 | 0 |
| wikisource_pd | 2673s | 12,538 | 0 | 136 | 0 | 784,454 | 2,090,304 | 0 |
| lrclib | 172s | 862 | 25 | 0 | 0 | 41,060 | 151,897 | 0 |
| **total** | **~98 min** | **22,569** | 94 | 227 | 0 | 1,232,154 | 3,895,892 | — |

Every run printed `Mode: incremental (additive)`; per-corpus `already_present` matched the pilot rows I5 deposited (mudcat 25, sacred-texts 23, ccmixter 17, gutenberg 3, hymnary 1, lrclib 25). Order was smallest→largest inside the PD/CC group (banks single-transaction commits before the two big corpora), lrclib last per spec. jamendo skipped (inert — no key). hymnary included (3-song gated micro-corpus from B6).

## Step 3 — idempotency proof

Re-run `toolshop lyrics build-db --corpus lrclib --incremental` → exit 0, 7s:

```
  Incremental: 887 existing 'lrclib' songs keyed
  Rhymes computed: 0 rhyme rows across 0 songs
  Metrics computed for 0 songs
  Ingested: 0 songs, 0 sections, 41060 lines
  Already present: 887
```

## Step 4 — GENIUS INVARIANT (verbatim, DB-verbatim)

`corpus_inventory.py --corpus genius-pro` after all ingests:

```
Total songs: 1425
  Sections: 10654
  Lines: 65912
  Rhyme rows: 273801
  Song rhyme metrics: 1425
```

→ `1425/10654/65912/273801` — **byte-identical** to wave-5 baseline. Corpus-scoped ingest never touched genius-pro.

## Step 5 — metrics coverage

Read-only query (`mode=ro`): songs per corpus LEFT JOIN `song_metrics` and `song_rhyme_metrics` on `song_id` — **0 missing in all 8 corpora** (24,488 songs: genius-pro 1425, ccmixter 547, gutenberg_pd 1306, hymnary 3, lrclib 887, mudcat-digitrad 7105, sacred-texts 277, wikisource_pd 12538).

## Step 6 — RIMER GATE (measured → presented → user approved)

`populate_rhymes` runs inside `build_database` per new-song id (lyricsdb.py:1165-1170) — the small-corpora ingest IS the pilot:

- hymnary: 28s / 2 songs (warm-up, startup-dominated)
- sacred-texts: **2617s / 254 songs = 10.3 s/song** (121 ms/line; Child ballads — rhyme-densest corpus, ~2,100 rhyme rows/song)

Projection over ~22,300 remaining songs: ~36h (line-weighted) to ~64h (flat per-song). **>8h → presented to user as the spec's USER gate** with the caveat that rhymes are embedded and per-corpus transactions are atomic. **User decision: full run, background batches.** Actual observed cost was far below the projection — sacred-texts was the outlier; real per-corpus rates: ccmixter 0.23, gutenberg 0.23, mudcat 0.11, wikisource 0.21, lrclib 0.20 s/song → total ~98 min. `toolshop lyrics build-rimer` (aggregate `rhyme_pairs` build over `line_rhymes`) not run — not in I9 scope; candidate for P2-V or a follow-up.

## Step 7 — release export v1

`python -X utf8 export_release.py --release-cleared --out .../lyrics/_release_v1 --db .../lyrics/lyrics.db` → **exit 0, 1370s**:

```
mode: release
emitted: 21776 song JSON(s) -> D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\_release_v1
  ccmixter: 547
  gutenberg_pd: 1306
  hymnary: 3
  mudcat-digitrad: 7105
  sacred-texts: 277
  wikisource_pd: 12538
pending_decisions: 0
skipped (missing source): 0
```

- Emit-plan blocker audit passed (no `release_ok != 'yes'` row emitted; exit ≠ 3).
- `RELEASE_MANIFEST.json` parses; `total_emitted: 21776`; `counts_per_corpus` matches the printout; `license_histogram`: `CC-BY-3.0` 518 + `CC-BY-2.5` 16 + `LicenseRef-public-domain` 21,242 = 21,776; `release_ok` in selected scope `{yes: 21776, no: 2312}` (no = genius-pro 1425 + lrclib 887, correctly excluded); `gaps` 0, `skipped_missing_source` 0.
- `CREDITS.md`: 534 cc-by items → 534 TASL lines (518 CC-BY-3.0 + 16 CC-BY-2.5), each with title/creator/source_url/license URL (+ccPlus note where present).

## BEFORE inventory (verbatim — captured pre-ingest ~21:40)

Evidence-file caveat: `.scratch/i9_inventory_before.txt` was **overwritten at 22:03 by a concurrent run of the WORKTREE `corpus_inventory.py`** (traceback: `sqlite3.OperationalError: database is locked` — it hit the main db while sacred-texts held the write txn). A second actor was running this wave's prompt; flagging per one-agent-per-lane rule. The text below is the actual pre-ingest output as captured in-session:

```
=== CORPUS INVENTORY ===

Total songs: 1425

--- Solo songs by artist (1315 total) ---
  [drill_trap] jala 199 / rasta 109 / devito 106 / corona 92 / coby 79 / buba 73 / voyage 67 / tng 40 / jala-buba 20 / indodjija 9 / jala-buba-coby 1
  [pop] maya-berovic 145 / senidah 82 / nikolija 70 / ana-nikolic 68 / relja 59 / henny 44 / breskvica 40 / jala-buba 6 / coby 3 / buba 2 / jala 1

--- Featured songs (110 total) ---  (rasta 24, corona 21, henny 9, voyage 9, devito 7, tng 6, senidah 5, indodjija 4, nikolija 3, relja 3, breskvica 2 [NULL] + cohort-tagged singles)

--- Structural counts ---
  Sections: 10654
  Lines: 65912
  Rhyme rows: 273801
  Song rhyme metrics: 1425

=== corpus: ccmixter ===      Total songs: 17   (Sections 115  Lines 758  Rhyme 2393)
=== corpus: gutenberg_pd ===  Total songs: 3    (Sections 55   Lines 116  Rhyme 309)
=== corpus: hymnary ===       Total songs: 1    (Sections 5    Lines 20   Rhyme 77)
=== corpus: lrclib ===        Total songs: 25   (Sections 169  Lines 1219 Rhyme 4058)
=== corpus: mudcat-digitrad === Total songs: 25 (Sections 341  Lines 893  Rhyme 2713)
=== corpus: sacred-texts ===  Total songs: 23   (Sections 2832 Lines 2832 Rhyme 45767)
(wikisource_pd absent — not yet ingested)

=== LICENSE / RELEASE READINESS ===
  genius-pro study-only/no 1425; ccmixter cc-by/yes 11 + pd/yes 6;
  gutenberg_pd pd/yes 3; hymnary pd/yes 1; lrclib study-only/no 25;
  mudcat-digitrad pd/yes 25; sacred-texts pd/yes 23

--- TASL gaps ---
  genius-pro missing creator=1425 source_url=1425 (of 1425)
  lrclib missing creator=25 (of 25)
  all other corpora: 0 gaps
```

(Compression note: genius-pro artist histograms abbreviated here; the untruncated render matches the AFTER block's genius section byte-for-byte — same corpus, unchanged.)

## AFTER inventory (verbatim)

```
=== corpus: ccmixter ===
Total songs: 547
  Sections: 3010  Lines: 15726  Rhyme rows: 44076  Rhyme metrics: 547
  Categories: acappella-by 534, acappella-pd 13

=== corpus: gutenberg_pd ===
Total songs: 1306
  Sections: 26704  Lines: 110228  Rhyme rows: 312406  Rhyme metrics: 1306
  Categories: child-ballads 1031, elizabethan 18, misc 60, songs-of-the-west 121, yorkshire 76

=== corpus: hymnary ===
Total songs: 3
  Sections: 15  Lines: 68  Rhyme rows: 172  Rhyme metrics: 3

=== corpus: lrclib ===
Total songs: 887
  Sections: 5165  Lines: 41060  Rhyme rows: 155955  Rhyme metrics: 887

=== corpus: mudcat-digitrad ===
Total songs: 7105
  Sections: 92160  Lines: 258989  Rhyme rows: 838588  Rhyme metrics: 7105

=== corpus: sacred-texts ===
Total songs: 277
  Sections: 21629  Lines: 21629  Rhyme rows: 509708  Rhyme metrics: 277

=== corpus: wikisource_pd ===
Total songs: 12538
  Sections: 42095  Lines: 784454  Rhyme rows: 2090304  Rhyme metrics: 12538
  Categories: ballads 67, epske 1906, erlangen 188, folk-songs 36, hymns 268,
              lirske 1176, ostalo 4079, poetry-collections 53, song-books 6,
              vuk-zbirke 42, zenske 4717

=== LICENSE / RELEASE READINESS ===
  genius-pro   study-only release_ok=no  : 1425
  ccmixter     cc-by/yes 534 + pd/yes 13
  gutenberg_pd pd/yes 1306
  hymnary      pd/yes 3
  lrclib       study-only/no 887
  mudcat-digitrad pd/yes 7105
  sacred-texts pd/yes 277
  wikisource_pd pd/yes 12538

--- TASL gaps ---
  genius-pro missing creator=1425 source_url=1425 (of 1425); releasable-with-gaps: 0
  lrclib     missing creator=887 (of 887)
  ALL other corpora: 0 gaps (creator/source_url/license_ref fully populated)

--- derived_from links --- all corpora: 0
```

## Watch-outs / notes for P2-V and downstream

1. **Concurrent-actor incident**: a second session ran worktree `corpus_inventory.py` at ~22:03 against the locked main db (failed, traceback landed in my `.scratch/i9_inventory_before.txt`). One-lane-one-agent was violated; no db corruption observed (all counts verified post-hoc), but P2-V should be aware evidence files can be clobbered.
2. `build_unified_index` rewrote each corpus's `_index.json`/`_dedup_log.json` from song JSONs. wikisource unified index = **12,538 uniques / 136 dupes** vs the adapter's 12,580/94 — the builder's `(title, primary_artist)` key catches a few more collisions than the adapter's fid-based dedup. Consumers reading `_index.json` now see the builder's shape (no `foreign_identifier` in entries — it lives in the song JSONs and made it into the `songs` table via fallback).
3. `data/toolshop/lyrics/wikisource_pd/_index.json` etc. live under the main-repo data dir (gitignored) — corpus data never commits, as designed.
4. lrclib fetched corpus is 863 matched rows; db holds 887 `lrclib` songs (862 new + 25 I5 pilot) — 887 = on-disk `tracks/` JSON count; all `release_ok=no` so none export.
5. Stray `data/toolshop/lyrics/gutenberg_pd/_src/pg47692.txt` exists **in the worktree** data dir (pre-existing, Oct 5 02:18 — not this session). Left in place; worktree `data/` is gitignored.
6. `--incremental` held additive-only semantics on every corpus: `already_present` counts exactly matched pilots; no DELETE path ran (incremental branch never issues one).
7. jamendo absent from db entirely (inert); hymnary at full gated size (3).

## Git evidence

```
$ git -C "D:/Projects/Music-AI-Toolshop-wt-lyrics-p2" log --oneline -3
5ccad47 lyrics-p2: I9 handoff — P2-I incremental ingest 7 corpora (22,569 new songs), genius invariant held, rimer gate measured+user-approved, _release_v1 exported (21,776)
2747a3c lyrics-p2: B7 wikisource handoff — sr 12,220 + en 430 fetched, 0 failed; en dump repaired via curl -C -
cb67372 lyrics-p2: B8 jamendo handoff — inert, JAMENDO_CLIENT_ID not supplied (user gate)
```

`toolshop closeout` — **exit 1, declared** (same pattern as wave-6 V1: multi-lane workspace):

```
--- git status --porcelain ---              (clean)
--- git status --porcelain --ignore-submodules=dirty ---   (clean)
--- git log @{u}..HEAD --oneline ---        WARNING: no upstream configured for 'lyrics-p2' (lane never pushed — push cadence is the user's call)
--- git submodule status ---                all 9 children '-' (uninitialized in this worktree — by design: corpus lane is code+data only, submodules need auth/network and are irrelevant here)
--- verdict --- FAIL (submodule not initialized)
```

Data boundary held: nothing under `data/toolshop/` or `_release_v1/` was committed (all gitignored); lane diff = this handoff only.
