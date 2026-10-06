# F — LRCLIB fetch handoff (wave P2-B, run B5)

Executor run of `fetch_lyrics_source.py --source lrclib` (catalog + resume).
Date: 2026-10-05. Worktree `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2` (branch `lyrics-p2`),
cwd `Genious_lyrics_extractor/`, Python `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe`,
`TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop` (passed via exec env — inline
`VAR=val` prefix is sandbox-denied in this environment).

## Prerequisite check

`D:/Projects/Music-AI-Toolshop/data/toolshop/lyrics/lrclib/_seed.json` present
(99,634 bytes, mtime 2026-10-05T00:19). Shape: `{"entries": [...]}` — **1,425 rows**,
all `{artist, title}` only (no album/duration) → every lookup takes the
`/api/search` path (1 request/row) per adapter `_lookup()`.

## Commands + exit codes (verbatim)

```
$ D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe fetch_lyrics_source.py --source lrclib --catalog-only
[lrclib] listing catalog (limit=None, offset=0) ...
[lrclib] catalog -> D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lrclib\_catalog.json (1425 new, 1450 total)
[lrclib] catalog-only: {'fetched': 25, 'pending': 1425}
exit code: 0
```

```
$ D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe fetch_lyrics_source.py --source lrclib --resume
[lrclib] 1425 entries to process (resume=True, corpus=D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lrclib)
  [1/1425] DROP: Afer — Rep i grad (not-found)
  [2/1425] OK (tracks): Alen Sakić — Jugoslavija
  ... (1,425 per-item OK/DROP lines — 863 OK, 562 DROP) ...
  [1425/1425] DROP: “Me And My Girl The Musical” Ensemble — ”This song… is for the most beautiful girl in my life… (not-found)
[lrclib] index: 887 unique songs, 0 intra-corpus dupes
[lrclib] done: {'fetched': 863, 'failed': 0, 'dropped': 562, 'skipped': 0} (catalog counts: {'fetched': 888, 'dropped': 562})
exit code: 0
```

Stderr carried only cosmetic warnings (`RequestsDependencyWarning` urllib3/chardet
version skew; `FutureWarning` urllib3 'strict' param). No 429s / Retry-After
events observed — no `failed` rows at any checkpoint.

## Catalog before → after

| metric | before | after |
|---|---|---|
| total entries | 25 (Sep-30 pilot seed) | 1,450 (1,425 current-seed + 25 pilot remnants) |
| fetched | 25 | 888 |
| dropped | 0 | 562 |
| pending | 0 (before merge) | 0 |
| failed | 0 | 0 |
| skipped | 0 | 0 |
| release_ok=yes | 0 | **0 — invariant held, all 1,450 rows `release_ok='no'`** |

Note: the 25 pilot rows carry `seed:` fids that differ from every current-seed fid,
so `--catalog-only` added all 1,425 rows as new (1,450 total). The 25 stayed
`fetched` under `--resume` and were not reprocessed; 15 of them have album+duration
in meta (old seed shape) → `matched_via='get'`, the other 10 → `search`.

## Hit-rate report (the deliverable)

| measure | count | % |
|---|---|---|
| total seed rows (current `_seed.json`) | 1,425 | — |
| matched (fetched) this run | 863 | **60.6%** of seeds |
| — via `search` | 863 | 100% of this-run matches |
| — via `get` | 0 | (only the 15 pilot rows with full signature) |
| — via `get-cached` | 0 | — |
| misses (dropped) this run | 562 | 39.4% |
| — `not-found` | 559 | |
| — `instrumental` | 3 | (Rasta — 5 Minuta; TNG — Future; one more) |
| — `no-lyrics` | 0 | |
| failed / skipped | 0 / 0 | |

Catalog-wide totals incl. the 25 pilot rows: fetched 888 (search 873, get 15,
get-cached 0), dropped 562 → 61.2%.

**Capture quality over the 887 emitted song JSONs (`tracks/*.json`):**

| field | non-null | % |
|---|---|---|
| `raw_lyrics` (plain text) | 887 | 100.0% |
| `lyricsfile` (YAML per-line ms) | 887 | **100.0%** |
| `synced_lyrics` (LRC) | 610 | **68.8%** |
| `meta.hasWordSync` true | 0 | 0% |

Misses are Balkan-pop/rap catalogue gaps in LRCLIB, not adapter faults — drop
reasons are specific (`not-found`, `instrumental`) and the instrumental flag is
honored upstream. No `no-lyrics` drops occurred.

## Verbatim catalog rows (5)

Fetched, new-seed shape (`search` path):

```json
{"artist": "Breskvica", "category": "tracks", "copyright_notice": null,
 "creator": "Breskvica", "creator_url": null, "drop_reason": null,
 "external_id": "seed:breskvica:gnezdo-orlovo:unknown", "fetched": true,
 "foreign_identifier": "seed:breskvica:gnezdo-orlovo:unknown",
 "json_path": "tracks/breskvica-gnezdo-orlovo.json", "license": "proprietary",
 "license_ref": "proprietary", "license_tier": "study-only", "license_url": null,
 "meta": {"album": null, "duration": null, "lrclib_id": 6662772,
          "matched_via": "search"},
 "release_ok": "no", "source": "lrclib", "source_url": null, "status": "fetched",
 "title": "Gnezdo orlovo",
 "url": "https://lrclib.net/api/search?track_name=Gnezdo+orlovo&artist_name=Breskvica"}
```

```json
{"artist": "Maya Berović", "title": "Ko sam ja", "status": "fetched",
 "foreign_identifier": "seed:maya-berović:ko-sam-ja:unknown",
 "json_path": "tracks/maya-berovic-ko-sam-ja.json",
 "meta": {"album": null, "duration": null, "lrclib_id": 5985227, "matched_via": "search"},
 "license": "proprietary", "license_tier": "study-only", "release_ok": "no",
 "url": "https://lrclib.net/api/search?track_name=Ko+sam+ja&artist_name=Maya+Berovi%C4%87"}
```

Fetched, pilot-seed shape (full signature → `get` path):

```json
{"artist": "Daft Punk", "title": "One More Time", "status": "fetched",
 "foreign_identifier": "seed:daft-punk:one-more-time:discovery:320",
 "json_path": "tracks/daft-punk-one-more-time.json",
 "meta": {"album": "Discovery", "duration": 320.0, "lrclib_id": 250327,
          "matched_via": "get"},
 "license": "proprietary", "license_tier": "study-only", "release_ok": "no",
 "url": "https://lrclib.net/api/get?track_name=One+More+Time&artist_name=Daft+Punk&album_name=Discovery&duration=320"}
```

Dropped `not-found`:

```json
{"artist": "Afer", "title": "Rep i grad", "status": "dropped",
 "drop_reason": "not-found", "fetched": false,
 "foreign_identifier": "seed:afer:rep-i-grad:unknown",
 "meta": {"album": null, "duration": null},
 "license": "proprietary", "license_tier": "study-only", "release_ok": "no",
 "url": ""}
```

Dropped `instrumental`:

```json
{"artist": "Rasta", "title": "5 Minuta", "status": "dropped",
 "drop_reason": "instrumental", "fetched": false,
 "foreign_identifier": "seed:rasta:5-minuta:unknown",
 "meta": {"album": null, "duration": null},
 "license": "proprietary", "license_tier": "study-only", "release_ok": "no",
 "url": ""}
```

`synced_lyrics` first-3-LRC-lines sample (`tracks/a-ha-take-on-me.json`):

```
[00:34.13] We're talking away
[00:36.92] I don't know what I'm to say
[00:39.54] I'll say it anyway
```

`lyricsfile` YAML head (structure only — same file): `version: '1.0'` +
`metadata:` {title, artist, album, duration_ms: 225000, instrumental: false} +
`lines:` — per-line timing records.

## Timing

- `--catalog-only`: ~2 s (local seed read, no network).
- `--resume`: **~35.9 min wall** — first song JSON written 2026-10-05T02:10:17,
  last 02:46:10; final catalog flush 02:46:29; index rebuild done 02:46:40.
  ≈1.51 s/row, matching the ≥1.5 s shared pacing floor (adapter `MIN_INTERVAL_S=1.5`
  overrides the registry's 0.5 s note) — no bypass observed, no 429s raised.

## Files on disk (under `D:/Projects/Music-AI-Toolshop/data/toolshop/lyrics/lrclib/`)

- `tracks/`: 887 `.json` + 887 `.txt`
- `_index.json`: 887 unique songs, `_dedup_log.json`: 0 entries
- `_catalog.json`: 1,450 rows — fetched 888 / dropped 562 / pending 0 / failed 0
- `_seed.json`: 1,425 rows (input, unchanged)

888 fetched rows → 887 files: one slug collision — `seed:relja:omađijala:unknown`
("Omađijala") and `seed:relja:omađijala-aleksa-remix:unknown` ("Omađijala (Aleksa
Remix)") both resolved to the same LRCLIB record → one shared
`tracks/devito-relja-aleksa-omađijala-aleksa-remix.json` (862 files written
today + 25 pilot files = 887).

## Notes / deviations

- Hit rate 60.6% — misses are genuine LRCLIB catalogue gaps for Balkan artists
  (Voyage, TNG, Zli Toni tails are heavily `not-found`); spec'd "search path =
  1 call/row" held since no seed row carries album/duration.
- `get-cached` was never exercised: it requires the full signature
  (album+duration), which only pilot rows have and those already hit via `get`
  in the pilot run. Expected given seed shape, not a defect.
- Invariant verified programmatically: `Counter(release_ok)` over all 1,450 rows
  = `{'no': 1450}` — zero `release_ok='yes'` rows, no blocker.
- 0 failed / 0 skipped rows; nothing to retry. Resumability not exercised
  (single uninterrupted run).
- No code changes made — executor role. No corpus data committed.
- Still-dirty at handoff commit time (pre-existing, NOT from this run):
  `M Genious_lyrics_extractor/sources/gutenberg_pd.py` — parallel agent's
  Child-ballad splitter work. Left uncommitted per executor scope.
