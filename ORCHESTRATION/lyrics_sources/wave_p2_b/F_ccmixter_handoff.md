# F — ccMixter fetch handoff (wave P2-B, run B4)

Executor run of `fetch_lyrics_source.py --source ccmixter` (catalog + resume).
Date: 2026-10-05. Worktree `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2` (branch `lyrics-p2`),
cwd `Genious_lyrics_extractor/`, Python `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe`,
`TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop` (passed via exec env — inline
`VAR=val` prefix is sandbox-denied in this environment).

## Commands + exit codes (verbatim)

```
$ D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe fetch_lyrics_source.py --source ccmixter --catalog-only
[ccmixter] listing catalog (limit=None, offset=0) ...
[ccmixter] catalog -> D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\ccmixter\_catalog.json (0 new, 1506 total)
[ccmixter] catalog-only: {'fetched': 17, 'dropped': 8, 'pending': 1481}
exit code: 0
```

```
$ D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe fetch_lyrics_source.py --source ccmixter --resume
[ccmixter] 1481 entries to process (resume=True, corpus=D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\ccmixter)
  ... (1,481 per-item OK/DROP lines) ...
[ccmixter] index: 547 unique songs, 0 intra-corpus dupes
[ccmixter] done: {'fetched': 530, 'failed': 0, 'dropped': 951, 'skipped': 0} (catalog counts: {'fetched': 547, 'dropped': 959})
exit code: 0
```

## Catalog before → after

| metric | before | after |
|---|---|---|
| total entries | 1,506 | 1,506 (0 new from --catalog-only) |
| fetched | 17 | 547 |
| dropped | 8 | 959 |
| pending | 1,481 | 0 |
| failed | 0 | 0 |
| release_ok=yes | 1,506 | 1,506 (all rows) |

This run processed all 1,481 pending rows: 530 fetched, 951 dropped, 0 failed, 0 skipped.

## Lyric yield

- All 959 drops are `drop_reason='no-lyric-text'` (no other drop reasons observed).
- Yield = fetched / (fetched + dropped no-lyric-text) = **547 / 1,506 = 36.3%** overall.
- This-run slice only: 530 / 1,481 = 35.8%.
- Below the 45–60% estimate. Cause: long runs of remix-event pells whose upload
  descriptions carry no `lyrics`/`words` header block — notably the "Out of It"
  event (~60 consecutive drops, rows 1174–1245), MommaLuv, Ms.Vybe, brad sucks,
  and Colin Mutchler sections at the tail of the queue.

## License-tier distribution of fetched rows (547)

| license_tier | license (SPDX map) | count |
|---|---|---|
| cc-by | CC-BY-3.0 | 518 |
| cc-by | CC-BY-2.5 | 16 |
| pd | LicenseRef-public-domain | 13 |

- Categories: `acappella-by` 534, `acappella-pd` 13.
- **sampling+/study-only rows fetched: 0** — every fetched row is `release_ok=yes`;
  the by+pd lane held as expected.
- All 534 cc-by fetched rows are TASL-complete (title + creator + creator_url +
  source_url + license + license_url populated).

## Verbatim catalog rows (3)

TASL-complete CC-BY row:

```json
{"title": "Geppetto V4 (Pell + Stems)", "creator": "coruscate",
 "creator_url": "https://ccmixter.org/people/Coruscate",
 "source_url": "https://ccmixter.org/files/Coruscate/70553",
 "license": "CC-BY-2.5", "license_url": "http://creativecommons.org/licenses/by/2.5/",
 "license_tier": "cc-by", "release_ok": "yes", "category": "acappella-by",
 "copyright_notice": "ccPlus commercial license also available via ccMixter/tunetrack",
 "status": "fetched"}
```

CC-BY-3.0 row:

```json
{"title": "The Homeless Man", "creator": "coruscate",
 "creator_url": "https://ccmixter.org/people/Coruscate",
 "source_url": "https://ccmixter.org/files/Coruscate/68853",
 "license": "CC-BY-3.0", "license_url": "http://creativecommons.org/licenses/by/3.0/",
 "license_tier": "cc-by", "release_ok": "yes", "category": "acappella-by",
 "status": "fetched"}
```

Public-domain row:

```json
{"title": "LI Bai A Homesick Night(vocals)", "creator": "Moon Of Magick",
 "creator_url": "https://ccmixter.org/people/moonofmagick",
 "source_url": "https://ccmixter.org/files/moonofmagick/60474",
 "license": "LicenseRef-public-domain",
 "license_url": "https://creativecommons.org/publicdomain/mark/1.0/",
 "license_tier": "pd", "release_ok": "yes", "category": "acappella-pd",
 "status": "fetched"}
```

(The `` in the PD row title is verbatim from the catalog — an upstream mojibake
en-dash in the source upload title, not a local encoding bug.)

## Timing

- `--catalog-only`: ~10 s (0 new rows — the by+pd lane was already fully enumerated).
- `--resume`: ~11 min wall (first song file 01:59:15, last 02:05:30, catalog flush
  02:05:37). Much faster than the 45+ min estimate because the ccMixter Query API
  returns `upload_description_*` inline in catalog pages — lyric extraction for most
  entries needs no additional HTTP request; ≥1.5 s `polite_get` pacing applies at
  the request layer and was not bypassed.

## Files on disk

- `lyrics/ccmixter/acappella-by/`: 534 `.json` + 534 `.txt`
- `lyrics/ccmixter/acappella-pd/`: 13 `.json` + 13 `.txt`
- `_index.json`: 547 unique songs, 0 intra-corpus dupes
- `_catalog.json`: updated 2026-10-05T02:05:37

## Notes / deviations

- Yield 36.3% vs the 45–60% estimate — documented above; not an adapter fault
  (drops carry the correct `no-lyric-text` reason).
- 0 failed rows; nothing to retry.
- One catalog title carries an upstream mojibake character (shown verbatim above).
- No code changes made — executor role. No corpus data committed.
- Still-dirty at handoff commit time (pre-existing, NOT from this run):
  `M Genious_lyrics_extractor/sources/gutenberg_pd.py` (+39/−3 — Child-ballad
  splitter work, consistent with the B3 "splitter gap flagged" note). Left
  uncommitted per executor scope; flag to wave owner.
