# F — gutenberg_pd fetch handoff (wave p2_b, run B3-rerun)

Executor re-run of `fetch_lyrics_source.py --source gutenberg_pd`, made
necessary by the G-fix splitter work (commit `442ee51` — `split_songs` now
emits songs for all 10 curated WORKS; run B3 fetched 245 rows from only 4/10
works). Two steps per spec: `--catalog-only` (upserts newly-split rows as
`pending`), then `--resume` (emits them). Fully local pass — all 10
`_src/pg<n>.txt` texts were already cached from B3, so `iter_catalog` /
`fetch_lyrics` served every read from cache (no aleph traffic).

Working dir for both: `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2/Genious_lyrics_extractor`
Env: `TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop` (passed via
exec env param — catalog/db live in the main repo's data dir, NOT the worktree).
Interpreter: `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe`.
Both commands emitted one benign `RequestsDependencyWarning`
(urllib3/chardet version mismatch).

## Commands (verbatim) + exit codes

```
python fetch_lyrics_source.py --source gutenberg_pd --catalog-only
```
**Exit code: 0**

```
python fetch_lyrics_source.py --source gutenberg_pd --resume
```
**Exit code: 0**

## Catalog before / after

Before (verbatim from `_catalog.json`, post-B3 state):

```
total entries: 272
status: {'fetched': 245, 'dropped': 27}
by prefix: {'pg44969': 125, 'pg47607': 85, 'pg7535': 43, 'pg27129': 19}
```

Step 1 log (verbatim):

```
[gutenberg_pd] listing catalog (limit=None, offset=0) ...
[gutenberg_pd] catalog -> D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\gutenberg_pd\_catalog.json (1108 new, 1380 total)
[gutenberg_pd] catalog-only: {'dropped': 27, 'fetched': 245, 'pending': 1108}
```

After (verbatim):

```
total entries: 1380
status: {'fetched': 1352, 'dropped': 28}
```

272 → **1,380** catalog rows (spec estimate ~1,373 — within noise); fetched
245 → **1,352**.

## Step 2 run log — head + tail + final stats (verbatim)

```
[gutenberg_pd] 1108 entries to process (resume=True, corpus=D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\gutenberg_pd)
  [1/1108] OK (child-ballads): Traditional — The Cruel Mother [F]
  [2/1108] OK (child-ballads): Traditional — The Cruel Mother [G]
  [3/1108] OK (child-ballads): Traditional — The Cruel Mother [H]
  ...
  [1106/1108] OK (misc): Traditional — Elfinland Wood
  [1107/1108] OK (misc): Traditional — Casabianca
  [1108/1108] OK (misc): Traditional — Auld Robin Gray
[gutenberg_pd] index: 1307 unique songs, 45 intra-corpus dupes
[gutenberg_pd] done: {'fetched': 1107, 'failed': 0, 'dropped': 1, 'skipped': 0} (catalog counts: {'dropped': 28, 'fetched': 1352})
```

Log counts: `OK` ×1107, `DROP` ×1, `FAIL` ×0, `SKIP` ×0. `failed = 0` → no
retry pass needed. On-disk check: `child-ballads/` 1,055 + `elizabethan/` 18 +
`misc/` 72 + `songs-of-the-west/` 123 + `yorkshire/` 84 = **1,352 `.json`
(+ `.txt`)** — matches `fetched: 1352` exactly.

## Work-level breakdown (per ebook)

| ebook | work key | kind | catalog rows | fetched | dropped |
|------:|----------|------|-------------:|--------:|--------:|
| 44969 | child-vol1 | child | 228 | 202 | 26 |
| 47692 | child-vol2 | child | 294 | 294 | 0 |
| 62474 | child-vol3 | child | 170 | 170 | 0 |
| 63116 | child-vol4 | child | 296 | 296 | 0 |
| 71104 | child-vol5 | child | 93 | 93 | 0 |
| 56625 | songs-of-the-west | sotw | 123 | 123 | 0 |
| 27129 | elizabethan | caps | 19 | 18 | 1 |
| 47607 | yorkshire | caps | 85 | 84 | 1 |
| 7535 | old-ballads | caps | 43 | 43 | 0 |
| 2831 | bundle-of-ballads | caps | 29 | 29 | 0 |
| **Σ** | | | **1,380** | **1,352** | **28** |

All six previously-zero works now emit rows (B3: 0 → this run: vol2 294,
vol3 170, vol4 296, vol5 93, sotw 123, bundle 29). Index dedup: 1,352 fetched
→ **1,307 unique** (`_dedup_log.json`: 45 intra-corpus dupes — same-title
variants colliding on slug within `child-ballads`/`misc`).

## Drop histogram (all drops; single kind)

```
   28  too-short    (pg44969 ×26, pg27129 ×1, pg47607 ×1)
```

Raw reasons verbatim: `pg44969:{0,1,2,3,4,35..42,113..124,227}:too-short`,
`pg27129:2:too-short`, `pg47607:0:too-short` (<4 body lines after stanza
extraction). Only NEW drop vs B3 is `pg44969:227` —
`Young Beichan [N]` (`[103/1108] DROP:` in run log), a single-stanza variant
stub newly surfaced by the vol-1 re-split.

## Verbatim sample rows (3 — headers/fields only, ≤3 lyric lines)

### pg62474:0 — `child-ballads/traditional-johnie-cock-a.json` (NEW work: child-vol3)

```
foreign_identifier: 'pg62474:0'
title: 'Johnie Cock [A]'
primary_artist: 'Traditional'
category: 'child-ballads'  corpus: 'gutenberg_pd'  source: 'gutenberg_pd'
license: 'LicenseRef-public-domain'  license_tier: 'pd'  release_ok: 'yes'
source_url: 'https://www.gutenberg.org/ebooks/62474'  language: 'en'  status: 'fetched'
--- lyric head (3 of 109 lines) ---
Johny he has risen up i the morn,
Calls for water to wash his hands;
But little knew he that his bloody hounds
```

### pg56625:0 — `songs-of-the-west/traditional-by-chance-it-was.json` (NEW work: sotw)

```
foreign_identifier: 'pg56625:0'
title: 'By Chance It Was'
primary_artist: 'Traditional'
category: 'songs-of-the-west'  corpus: 'gutenberg_pd'  source: 'gutenberg_pd'
license: 'LicenseRef-public-domain'  license_tier: 'pd'  release_ok: 'yes'
source_url: 'https://www.gutenberg.org/ebooks/56625'  language: 'en'  status: 'fetched'
--- lyric head (3 of 40 lines) ---
By chance it was I met my love,
It did me much surprise,
Down by a shady myrtle grove,
```

### pg2831:0 — `misc/traditional-chevy-chase-pg28310.json` (NEW work: bundle-of-ballads)

```
foreign_identifier: 'pg2831:0'
title: 'Chevy Chase'
primary_artist: 'Traditional'
category: 'misc'  corpus: 'gutenberg_pd'  source: 'gutenberg_pd'
license: 'LicenseRef-public-domain'  license_tier: 'pd'  release_ok: 'yes'
source_url: 'https://www.gutenberg.org/ebooks/2831'  language: 'en'  status: 'fetched'
--- lyric head (3 of 189 lines) ---
The Percy out of Northumberland, and avow to God made he
That he would hunt in the mountains of Cheviot within days three,
In the maugre of doughty Douglas and all that ever with him be,
```

## Findings / deviations

- **G-fix verified in production:** B3's 6 zero-row works now yield 1,005
  catalog rows (294+170+296+93+123+29) — the `child`, `sotw`, and
  `caps`/`flush_left_heads` splitter paths all emit under real cached input.
  Zero `failed`, zero unexpected drops.
- **child-vol1 grew 125 → 228 rows** (fetched 100 → 202): the same fix also
  recovered ~103 additional vol-1 rows — mostly lettered variants beyond what
  B3's splitter saw (e.g. `The Cruel Mother` now runs to [H]) plus
  `=X.=`/`#X.#`-marked variants and supplement pieces in
  `APPENDIX`/`ADDITIONS AND CORRECTIONS` regions. One new too-short drop
  (`pg44969:227`) came with them — acceptable splitter noise, same class as
  the 25 pre-existing vol-1 drops.
- **Zero network:** all 10 `_src/pg<n>.txt` files were cache hits; the
  ~9 min wall-clock is local parse+write for 1,108 entries (~2/s — the
  splitter re-parses the full work text per entry).
- **Spec estimate vs actual:** spec said ~1,373 expected rows; observed
  1,380 catalog rows / 1,352 fetched / 1,307 unique index entries. Within
  ~0.5% — no discrepancy to chase.
- Corpus data lives under `D:/Projects/Music-AI-Toolshop/data/toolshop/`
  (outside this worktree) — nothing but this handoff is committed.
- Pre-commit `git status --short`: clean (empty output).

## Files

- Created: `ORCHESTRATION/lyrics_sources/wave_p2_b/F_gutenberg2_handoff.md` (this file)
- Modified (outside worktree, NOT committed — corpus data):
  `data/toolshop/lyrics/gutenberg_pd/_catalog.json`, `_index.json`,
  `_dedup_log.json`, `<category>/*.json|.txt` (+1,107 song files)

## Blockers / risks for downstream waves

- None for the corpus itself. The 45 intra-corpus dupes in `_dedup_log.json`
  (variant slugs colliding inside child-ballads/misc) are recorded, not
  merged — downstream consumers should read `_index.json` (1,307 uniques),
  not raw catalog rows, if slug-uniqueness matters.
- The 28 `too-short` drops are all low-information stubs (front-matter or
  single-verse fragments); no recovery action recommended.
