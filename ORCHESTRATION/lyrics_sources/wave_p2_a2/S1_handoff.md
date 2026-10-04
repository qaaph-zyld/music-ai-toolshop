# S1 handoff — wave P2-A: lrclib seed generator + real `_seed.json`

Lane `lyrics-p2`, worktree `Music-AI-Toolshop-wt-lyrics-p2`, agent S1 (seed).
Scope: `Genious_lyrics_extractor/make_lrclib_seed.py` + `tests/test_lrclib_seed.py`
+ generated `data/toolshop/lyrics/lrclib/_seed.json` (canonical data dir —
uncommitted by design, data boundary).

## Deliverables

| Artifact | Path | State |
|---|---|---|
| Seed generator | `Genious_lyrics_extractor/make_lrclib_seed.py` | committed `eddbc3c` |
| Tests | `tests/test_lrclib_seed.py` | committed `eddbc3c` (13 tests) |
| Real seed | `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lrclib\_seed.json` | written, **uncommitted** (data/ boundary — outside this worktree) |

## Contract implemented (per task spec + `sources/lrclib.py` seed contract)

- **db resolution order**: `--db` flag > `TOOLSHOP_DATA_DIR` env +
  `/lyrics/lyrics.db` > `<repo>/data/toolshop/lyrics/lyrics.db`. sqlite3 stdlib
  only, read-only `mode=ro` URI connection — **never `import toolshop`**.
- **Query**: `SELECT title, primary_artist, foreign_identifier FROM songs
  WHERE corpus = ? ORDER BY foreign_identifier` — default `genius-pro`,
  `--corpus` override for future corpora.
- **Output**: `<lrclib corpus root>/_seed.json` =
  `<data>/lyrics/lrclib/_seed.json`, shape
  `{"entries": [{"artist": ..., "title": ...}, ...]}`. No album/duration keys
  (genius lacks them) → adapter's `_lookup` takes the `/api/search` branch
  (1 call/row), verified via `iter_catalog` meta `{album: None, duration: None}`.
- **Dedup**: normalized `(artist, title)` — lowercase + strip + collapse
  whitespace; empty title/artist rows skipped; first row in fid order wins.
- **Idempotent**: entries sorted by normalized `(artist,title)` (+ raw-value
  tiebreak); `json.dumps(ensure_ascii=False, indent=2)` + `\n`, LF newlines →
  byte-identical rewrite.
- **`--dry-run`**: prints the count only (`1425`), writes nothing.
- Exit codes: `0` ok/dry-run, `2` db not found.

## Verification (all run this session, `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`)

### Tests — `tests/test_lrclib_seed.py`

```
D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -X utf8 -m pytest
  tests/test_lrclib_seed.py -v
→ 13 passed, 1 warning in 17.48s          (exit 0)
```

Fixture: temp sqlite `songs` table — 3 genius-pro + 1 case-variant dup +
1 `other-corpus` + 1 empty-title row → exactly 3 entries; corpus filter,
dedup, sort/idempotence, dry-run, TOOLSHOP_DATA_DIR resolution, and an
adapter round-trip (`sources.lrclib.iter_catalog` consumes the emitted file).

### Lane-scope suite

```
pytest -q -m "not slow" tests/test_lrclib_seed.py test_lyrics_sources_lrclib.py
  test_lyrics_sources_core.py test_lyrics_sources_catalog.py
  test_lyricsdb.py test_lyricsdb_multicorpus.py
→ 2 failed, 271 passed, 1 deselected in 135.11s   (exit 1)
```

The 2 failures (`test_named_adapters_resolve_or_defer`,
`test_every_shipped_adapter_matches_policy`) hit while the **parallel D1
agent's `wikisource_pd.py` edit was mid-write** (`fetch_lyrics` momentarily
absent). Re-run after D1's write settled:

```
→ 2 passed in 0.22s                         (exit 0)
```

Full-suite `pytest -q -m "not slow"` additionally fails **collection** on 5
modules needing `mastering_tool.tools` — all nine submodules are
uninitialized in this worktree (`git submodule status` → all `-` prefixed).
Environmental, pre-existing, unrelated to this wave. Declared, not fixed
(private-submodule checkout is a worktree-setup concern, not S1 scope).

### Real seed generation (TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop)

```
--dry-run → "1425"                        (exit 0)

make_lrclib_seed: corpus=genius-pro
  db=D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db
make_lrclib_seed: wrote D:\Projects\Music-AI-Toolshop\data\toolshop\
  lyrics\lrclib\_seed.json — 1425 entries (artist+title only;
  adapter routes to /api/search)            (exit 0)
```

**Seed row count: 1,425** — exactly the genius-pro invariant (1425 songs);
source db verified pre-run: 0 rows with empty title/artist, 0 normalized
duplicates → no dedup/skips fired on real data (all exercised in fixtures).

Idempotence: re-run after write →
`sha256 39f7d3405a58f5fc9487e426d0d9b7959814de6385d2905e6217135f795565af`
before AND after (byte-identical, 99,634 bytes).

Adapter smoke (stdlib import of `sources.lrclib`, no network):
`seed_path()` resolves the written file; `_load_seed` → 1425 rows;
`iter_catalog` → 1425 entries, all `release_ok='no'` (locked invariant),
`meta={album: None, duration: None}` → `/api/search` route;
fids stable (`seed:afer:rep-i-grad:unknown`, …).

### 3 verbatim seed rows (head of `_seed.json`)

```json
{"artist": "Afer", "title": "Rep i grad"}
{"artist": "Alen Sakić", "title": "Jugoslavija"}
{"artist": "Amna", "title": "Fantomi"}
```

## Commits (branch `lyrics-p2`; CHANGELOG ID deferred to merge per lane rules)

```
eddbc3c feat(lyrics-p2): P2-A/S1 lrclib seed generator —
        make_lrclib_seed.py + tests   (2 files, +357)
```

## Tree state at handoff (verbatim `git status --short`)

```
 M Genious_lyrics_extractor/sources/wikisource_pd.py      ← D1 agent (parallel wave), NOT S1
?? Genious_lyrics_extractor/sources/wikisource_dump.py    ← D1 agent
?? Genious_lyrics_extractor/wikisource_dump_ingest.py     ← D1 agent
?? tests/fixtures/lyrics_sources/wikisource_sample.xml    ← D1 agent
?? tests/test_lyrics_sources_dump.py                      ← D1 agent
```

All S1 files are committed (`eddbc3c`). The dirty paths belong to the
concurrent D1 implementer sharing this worktree — declared per close-out
discipline; S1 touched none of them.

## Deviations from task spec

1. **`--out` flag added** (not in spec): optional output-path override used by
   tests so they don't need env manipulation; default path resolution is
   unchanged (`<data>/lyrics/lrclib/_seed.json`). Harmless extension.
2. **`toolshop closeout` not runnable** in this worktree: `toolshop.cli`
   imports `mastering_tool.tools` and all submodules are uninitialized here
   → exit 1 `ModuleNotFoundError`. Declared per "exit 0 or declared";
   substitute evidence = the `git status`/`git log` block above.
3. Test file named `tests/test_lrclib_seed.py` per spec (not the
   `test_lyrics_sources_*` convention — spec wins).

## Blockers / risks for downstream waves

- **B5 (lrclib fetch)**: 1,425 rows × ≥1.5 s pacing ≈ **36 min** floor —
  plan accordingly. Every row takes the `/api/search` branch (no
  album/duration) → exactly 1 call/row, ≤20 results/call, hit picked by
  `_pick_search_hit` (exact title+artist preferred).
- **Hit-rate unknown** (megaplan assumption P2-A4): LRCLIB coverage of the
  ex-YU-heavy genius corpus is unmeasured — B5 must produce the hit-rate
  report (`matched_via`/`not-found`/`instrumental`/`no-lyrics` drop counts).
- `instrumental`/`no-lyrics` drops are expected for intros/beats in the
  corpus — not a seed defect.
- Re-running `make_lrclib_seed.py` after future `lyrics.db` ingests is safe
  (read-only, byte-identical unless the corpus actually changed; seed fids
  are content-derived so `Catalog.upsert` never dupes on relist).
- `LRCLIB_SEED` env var or `--out` can repoint a *consumer*/generator at a
  scratch seed for probes — don't point B5's real run anywhere but the
  canonical corpus root.
