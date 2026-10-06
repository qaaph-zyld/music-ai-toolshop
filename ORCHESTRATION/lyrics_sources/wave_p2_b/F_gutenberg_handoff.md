# F — gutenberg_pd fetch handoff (wave p2_b, run B3)

Executor run of `fetch_lyrics_source.py --source gutenberg_pd`, two steps per
spec: `--catalog-only` (lists all 10 curated WORKS, downloading `pg<n>.txt`
via the robot-sanctioned `aleph.gutenberg.org` hosts into `_src/` — no
`/ebooks/` or `/files/` pages touched), then `--resume` (emits songs).

Working dir for both: `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2/Genious_lyrics_extractor`
Env: `TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop` (passed via
exec env param — catalog/db live in the main repo's data dir, NOT the worktree).
Both commands emitted one benign `RequestsDependencyWarning` (urllib3/chardet
version mismatch). Per adapter docstring: `verify=False` is used ONLY for the
aleph host (corporate TLS interception breaks its cert chain); documented here
as required.

## Commands (verbatim) + exit codes

```
python fetch_lyrics_source.py --source gutenberg_pd --catalog-only
```
**Exit code: 0** (interpreter: `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe`)

```
python fetch_lyrics_source.py --source gutenberg_pd --resume
```
**Exit code: 0**

## Catalog before / after

Before (pilot, verbatim from `_catalog.json`):

```
total entries: 243
status: {'dropped': 25, 'fetched': 3, 'pending': 215}
by prefix: {'pg44969': 125, 'pg27129': 17, 'pg47607': 64, 'pg7535': 37}
```

Step 1 log (verbatim):

```
[gutenberg_pd] listing catalog (limit=None, offset=0) ...
[gutenberg_pd] catalog -> D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\gutenberg_pd\_catalog.json (29 new, 272 total)
[gutenberg_pd] catalog-only: {'dropped': 25, 'fetched': 3, 'pending': 244}
```

After (verbatim):

```
total entries: 272
status: {'dropped': 27, 'fetched': 245}
```

## Step 2 run log — final lines (verbatim)

```
  [243/244] OK (misc): Traditional — The Lye
  [244/244] OK (misc): Traditional — The Ballad Of Reading Gaol
[gutenberg_pd] index: 235 unique songs, 10 intra-corpus dupes
[gutenberg_pd] done: {'fetched': 242, 'failed': 0, 'dropped': 2, 'skipped': 0} (catalog counts: {'dropped': 27, 'fetched': 245})
```

`failed = 0` → no retry pass needed. 244 pending processed; 245 total fetched
(3 pre-existing + 242). On-disk check: `child-ballads/` 100 + `elizabethan/`
18 + `yorkshire/` 84 + `misc/` 43 = **245 `.json` (+ `.txt`)** — matches
`fetched: 245` exactly.

## Work-level breakdown (per ebook)

| ebook | work key | kind | catalog rows | fetched | dropped | index (deduped) |
|------:|----------|------|-------------:|--------:|--------:|----------------:|
| 44969 | child-vol1 | child | 125 | 100 | 25 | 100 |
| 47692 | child-vol2 | child | 0 | 0 | 0 | 0 |
| 62474 | child-vol3 | child | 0 | 0 | 0 | 0 |
| 63116 | child-vol4 | child | 0 | 0 | 0 | 0 |
| 71104 | child-vol5 | child | 0 | 0 | 0 | 0 |
| 56625 | songs-of-the-west | sotw | 0 | 0 | 0 | 0 |
| 27129 | elizabethan | caps | 19 | 18 | 1 | 18 |
| 47607 | yorkshire | caps | 85 | 84 | 1 | 76 |
| 7535 | old-ballads | caps | 43 | 43 | 0 | 41 |
| 2831 | bundle-of-ballads | caps | 0 | 0 | 0 | 0 |
| **Σ** | | | **272** | **245** | **27** | **235** |

Index dedup: 245 fetched → 235 unique (`_dedup_log.json` lists 10 intra-corpus
dupes — repeated boilerplate "songs" like `Footnote:`, `Chorus`, `Viii`,
`Part The First` colliding on slug within yorkshire/misc).

## Drop histogram (all drops; single kind)

```
   27  too-short    (pg44969 ×25, pg27129 ×1, pg47607 ×1)
```

Raw reasons verbatim: `pg44969:{0,1,2,3,4,35..42,113..124}:too-short`,
`pg27129:2:too-short`, `pg47607:0:too-short` (<4 body lines after stanza
extraction — front-matter headings / single-variant stubs).

## Verbatim sample rows (3)

### pg44969:88 — `child-ballads/traditional-babylon-or-the-bonnie-banks-o-fordie-a.json`

```
foreign_identifier: 'pg44969:88'
title: 'Babylon; Or, The Bonnie Banks O Fordie [A]'
primary_artist: 'Traditional'
category: 'child-ballads'  corpus: 'gutenberg_pd'  source: 'gutenberg_pd'
license: 'LicenseRef-public-domain'  license_tier: 'pd'  release_ok: 'yes'
source_url: 'https://www.gutenberg.org/ebooks/44969'  language: 'en'  status: 'completed'
--- lyric head (3 of 55 lines) ---
There were three ladies lived in a bower,
Eh vow bonnie
And they went out to pull a flower.
```

### pg27129:17 — `elizabethan/traditional-a-mourning-song-for-the-death-of-sir-fulke-greville-lord-brooke.json`

```
foreign_identifier: 'pg27129:17'
title: 'A Mourning-Song For The Death Of Sir Fulke Greville, Lord Brooke'
primary_artist: 'Traditional'
category: 'elizabethan'  corpus: 'gutenberg_pd'  source: 'gutenberg_pd'
license: 'LicenseRef-public-domain'  license_tier: 'pd'  release_ok: 'yes'
source_url: 'https://www.gutenberg.org/ebooks/27129'  language: 'en'  status: 'completed'
--- lyric head (3 of 16 lines) ---
Where shall a sorrow great enough be sought
For this sad ruin which the Fates have wrought,
Unless the Fates themselves should weep and wish
```

### pg7535:5 — `misc/traditional-barbara-allens-cruelty.json`

```
foreign_identifier: 'pg7535:5'
title: "Barbara Allen'S Cruelty"
primary_artist: 'Traditional'
category: 'misc'  corpus: 'gutenberg_pd'  source: 'gutenberg_pd'
license: 'LicenseRef-public-domain'  license_tier: 'pd'  release_ok: 'yes'
source_url: 'https://www.gutenberg.org/ebooks/7535'  language: 'en'  status: 'completed'
--- lyric head (3 of 79 lines) ---
In Scarlet towne where I was borne,
There was a faire maid dwellin,
Made every youth crye, Wel-awaye!
```

## Findings / deviations

- **Fetch layer clean:** all 10 `pg<n>.txt` files present in `_src/` (263 KB –
  2.7 MB each, plausible sizes; each contains exactly one `*** START OF` line).
  Zero 4xx/5xx on aleph — the >2-works-fail stop condition was not triggered.
- **6 of 10 works yielded ZERO catalog rows — splitter gap, not a fetch
  failure.** Diagnostic (read-only, no edits): `split_songs` returns `[]` for
  child-vol2/3/4/5 (kind=child), songs-of-the-west (kind=sotw) and
  bundle-of-ballads (kind=caps) despite large parsed bodies (14k–158k lines).
  `iter_catalog` silently `continue`s on empty splits, so these works leave no
  trace in `_catalog.json` — the catalog looks "fully resolved" while covering
  only 4/10 works. **Downstream:** the `child`/`sotw`/`caps` heading patterns
  need work (vol2+ likely use a different ballad-number/heading layout;
  bundle-of-ballads misses the >=5-char-CAPS + 2-indented-lines rule). The 245
  fetched songs are real, but this run is ~half the intended corpus.
- **Catalog grew +29 within pilot works** (pg27129 17→19, pg47607 64→85,
  pg7535 37→43): the current adapter lists more songs per work than the pilot
  snapshot did — expected, merge is idempotent on `foreign_identifier`.
- **Split noise in index:** yorkshire produced roman-numeral/footnote/`Part N`
  pseudo-songs (visible in run log + dedup log); they pass the >=4-line gate
  with boilerplate bodies. Cosmetic — flag for corpus-quality review, not a
  fetch defect.
- Corpus data lives under `D:/Projects/Music-AI-Toolshop/data/toolshop/`
  (outside this worktree) — nothing but this handoff is committed.
