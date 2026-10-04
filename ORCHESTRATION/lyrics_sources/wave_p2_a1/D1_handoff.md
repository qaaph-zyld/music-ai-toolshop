# D1 handoff — wikisource XML-dump ingestor (wave P2-A, agent D1)

**Branch/commit:** `lyrics-p2` @ `0e60e97` — `feat(lyrics-p2): wikisource XML-dump ingestor (D1)`
**Status:** COMPLETE, committed, tree clean. Live pilot **deferred to B7** (no real dump on disk — see §5).

## 1. Files created / modified (all in commit `0e60e97`, 5 files +1131/−6)

| File | Change |
|---|---|
| `Genious_lyrics_extractor/sources/wikisource_dump.py` | NEW — dump streaming library, no network: `iter_dump_pages` (bz2/gz/plain XML via `ElementTree.iterparse`, `elem.clear()` + parent removal = constant memory), `build_member_cats` (pass 1: ns-14 parent-link graph → per-entry DFS → `{wiki: {member_cat_title: slug}}`), `iter_dump_candidates` (pass 2: ns-0 pages linking a member cat → `CatalogEntry`, `fid={wiki}:{pageid}`, `meta={wiki,pageid,page_title,via:'dump',member_cat}`, raw wikitext on transient `._wt` attr, never serialized) |
| `Genious_lyrics_extractor/wikisource_dump_ingest.py` | NEW — CLI `--dump --wiki {sr,en} [--limit N] [--offset N] [--resume] [--quiet]`. Reuses `wikisource_pd._song_from_wikitext` verbatim; `Catalog.for_corpus` pageid-keyed resume; `pending_slice` parity (skipped/dropped never re-queued, fetched skipped only under `--resume`, failed retried); `write_index` at end |
| `Genious_lyrics_extractor/sources/wikisource_pd.py` | REFACTOR — extracted `_song_from_wikitext(entry, wt, parsed_title=None)`; `fetch_lyrics` now = API fetch + builder call. Identical song shape; 20 existing tests unchanged + green |
| `tests/test_lyrics_sources_dump.py` | NEW — 13 tests covering all spec'd assertions |
| `tests/fixtures/lyrics_sources/wikisource_sample.xml` | NEW — synthetic namespaced export-0.11 dump, 14 pages (6 ns-14 + 8 ns-0), synthetic + PD text only |

## 2. Test results (quoted)

```
$ D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -m pytest \
    tests/test_lyrics_sources_dump.py tests/test_lyrics_sources_wikisource.py -q
33 passed, 3 warnings in 3.00s        # exit 0  (13 new + 20 existing wikisource)

$ pytest tests/test_lyrics_sources_{ccmixter,gutenberg,hymnary,jamendo,lrclib,mudcat,sacred_texts}.py -q
170 passed, 2 skipped, 4 warnings     # exit 0

$ pytest tests/test_lyrics_sources_{dump,wikisource,core,catalog}.py -q
158 passed, 3 warnings                # exit 0
```

Full `pytest tests/` collection hits **pre-existing** worktree errors
(`scripts`, `mastering_tool` modules unresolvable in this worktree) —
unrelated to this change; scoped runs above are green.

## 3. Verbatim emit/drop examples (fixture-driven CLI, real corpus write)

Command (`TOOLSHOP_DATA_DIR` pointed at `.scratch/d1_data`, exit 0):

```
[wikisource_pd] dump pass 1: building member-category set for wiki 'sr' (roots=3, max_depth=8) ...
[wikisource_pd] member categories: 5
  [1] OK (zenske): Narodna pesma — Два бора и јела
  [2] OK (vuk-zbirke): Narodna pesma — Ага Асан-ага
  [3] DROP: Narodna pesma — Злоћудна песма (non-pd-license-template:CC-BY-NC-4.0)
  [4] DROP: Narodna pesma — Списак песама (toc-or-index-page)
  [5] DROP: Narodna pesma — Кратка песма (too-short:2-verse-lines)
  [6] OK (zenske): Narodna pesma — Пример песме
[wikisource_pd] index: 3 unique songs, 0 intra-corpus dupes
[wikisource_pd] done: {'fetched': 3, 'failed': 0, 'dropped': 3, 'offset_skipped': 0,
 'candidates': 6, 'terminal_skipped': 0} (catalog counts: {'fetched': 3, 'dropped': 3})
EXIT=0
```

Emitted song `zenske/narodna-pesma-два-бора-и-јела.json` (page `sr:902` links ONLY the
subcat `Категорија:Женске народне песме` — graph-derived membership, the adversarial case):

```json
{"title":"Два бора и јела","foreign_identifier":"sr:902","category":"zenske",
 "script":"cyrillic-original","license_tier":"pd","release_ok":"yes","language":"sr",
 "meta":{"wiki":"sr","pageid":"902","page_title":"Два бора и јела",
 "license_verdict":"ok","via":"dump",
 "member_cat":"Категорија:Женске народне песме", ...}}
sections: ['Strofa 1','Strofa 2']   raw0: 'Два су бора напоредо расла,'   clean0: 'Dva su bora naporedo rasla,'
```

Resume (`--resume` second run, exit 0): `{'fetched': 0, ... 'terminal_skipped': 6}` —
all 6 catalog rows skipped, zero rewrites.

En run (same corpus, exit 0): `member categories: 6` → `OK (folk-songs): Traditional —
The Riddles Wisely Expounded` → `{'fetched': 1}`.

Parity test asserts dump song == `_song_from_wikitext` output + exactly
`{meta.via, meta.member_cat}` extra keys (write-time `normalise_song` adds the two
sync-field defaults `synced_lyrics`/`lyricsfile` = null — same as API path).

## 4. Design decisions / deviations

- **Membership is graph-derived, not name-matched** (spec delta §2): pass 1 inverts
  child→parent links inside ns-14 wikitext, then DFS per entry root in declared order
  (Vuk → Erlangen → Народне — the "broadest last, dedup-first-wins" intent);
  `_branch_for_cat` refines each edge for sr (en inherits entry slug — its tokens
  never match English names, matching `_walk_en` which applies no refinement).
  Depth bounds mirror the API walk: sr 8, en 2.
- **Fixture is 14 pages, not "~8"**: the spec's page list is a minimum — the
  conditional-verdict, en-root, and non-member assertions each need their own page.
  Every spec'd case is covered (PD Cyrillic via subcat, Vuk-book-cat member, non-PD
  drop, TOC/link-heavy drop, too-short drop, en folk-song, root→subcat ns-14 pair).
- **Catalog flush cadence**: per-item `save_catalog` is O(n²) IO at 10k+ rows —
  marks flush every 25 processed + final flush (`_SAVE_EVERY`). Crash loses <25
  marks; all writes idempotent, `--resume` converges.
- **`._wt` transient attribute**: `iter_dump_candidates` yields spec-shaped
  `CatalogEntry`; raw wikitext rides a non-serialized attribute so `_catalog.json`
  isn't bloated. Ingest reads it via `getattr(entry, "_wt", "")`.
- **License fields on catalog rows** stay registry-PD (API-path parity — the
  per-page verdict lands in the song JSON `meta.license_verdict` + song/index
  license fields, which is where V2 audits).

## 5. Blockers / risks for downstream

- **Live pilot deferred to B7** — `data/toolshop/lyrics/wikisource_pd/_src/` does
  not exist; no `*-pages-articles.xml*` on disk. B7 must download
  `dumps.wikimedia.org/srwikisource/latest/srwikisource-latest-pages-articles.xml.bz2`
  (and `enwikisource`) into `_src/` or pass `--dump` any path, then run:
  `python wikisource_dump_ingest.py --dump <path> --wiki sr --resume`.
- **P2-A1 validation point**: expect ≥2k member cats for sr on the real dump
  (fixture shows 5). If pass-1 returns far fewer, the category graph inside the
  dump is thinner than assumed — inspect before ingesting.
- **Throughput unknown at scale**: iterparse + two sequential decompress passes;
  single-threaded. Overnight-capable per megaplan; measure pass-1 wall time on the
  real .bz2 first.
- en ingest currently reads the en entries even when handed an sr dump — pass
  `--wiki` correctly (CLI requires it; en roots on an sr dump just yield ~0
  members → the zero-member guard exits 2).
- `RequestsDependencyWarning` (urllib3/chardet mismatch) is pre-existing venv
  noise, not from this change.
```
