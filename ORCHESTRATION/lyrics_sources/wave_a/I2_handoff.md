# I2 handoff — wave A: ccMixter adapter (`sources/ccmixter.py`)

**Agent:** I2 (lyrics-sources megaplan, wave A) · **Session:** 2026-10-01 ·
**Lane scope:** `sources/ccmixter.py`, `tests/test_lyrics_sources_ccmixter.py` +
fixtures, `data/toolshop/lyrics/ccmixter/` (uncommitted), this handoff.

## Delivered

- `Genious_lyrics_extractor/sources/ccmixter.py` (~740 lines) — full SPEC §6.3
  contract for a `fetch_policy='auto'` source: `SOURCE_ID`, `iter_catalog`,
  `license_of`, `fetch_lyrics`, plus public `extract_lyrics`.
- `tests/test_lyrics_sources_ccmixter.py` — 38 tests, all fixture-driven
  except one `@pytest.mark.slow` live smoke that `pytest.skip`s offline.
- `tests/fixtures/lyrics_sources/ccmixter_query_page.json` — real Query API
  `f=json&dataview=default` rows: 5 cleared uploads (CC-BY-3.0 / CC0-1.0 —
  TASL recorded in `CREDITS.md`) + 5 synthetic metadata-only rows
  (`meta_fixture: true`, self-authored text) covering nc/sa/sampling+/unknown
  license mapping.
- Pilot corpus under `data/toolshop/lyrics/ccmixter/` — gitignored,
  uncommitted per data-boundary rule (`git check-ignore` verified:
  `.gitignore:47 data/`).
- CHANGELOG Answer **#065** (commits `c72b2ee` code+entry; handoff commit below).

## Verification (exit codes + key output, run this session)

- `pytest tests/test_lyrics_sources_ccmixter.py -q` → **38 passed**, exit 0
  (includes the slow live smoke — network was reachable this session).
- `pytest tests/test_lyrics_sources_ccmixter.py tests/test_lyrics_sources_core.py -m "not slow" -q`
  → **89 passed + 1 deselected**, exit 0 at handoff state. (Mid-session I saw
  2 transient failures in the *core* file — `len(sources)==20` stale asserts —
  caused by I3's in-flight `wikisource_pd` registry merge; that lane fixed the
  second assert while I was working. Not my file; final state green.)
- `python fetch_lyrics_source.py --source ccmixter --limit 25 --resume` →
  **exit 0**:

  ```
  [ccmixter] catalog -> ...\lyrics\ccmixter\_catalog.json (1506 new, 1506 total)
  [ccmixter] 25 entries to process (resume=True, ...)
    [1/25] OK (acappella-by): coruscate — Geppetto V4 (Pell + Stems)
    ...
  [ccmixter] index: 17 unique songs, 0 intra-corpus dupes
  [ccmixter] done: {'fetched': 17, 'failed': 0, 'dropped': 8, 'skipped': 0}
    (catalog counts: {'fetched': 17, 'dropped': 8, 'pending': 1481})
  ```

  **Yield 17/25 = 68%** — at/above R1's 45-60% estimate (recent-upload slice is
  lyric-rich, matching R1's "recent 40-60% / event-era 80%" spread).

## License-tier histogram (pilot, fetched items only)

| license | tier | release_ok | count | category dir |
|---|---|---|---|---|
| CC-BY-3.0 | cc-by | yes | 9 | acappella-by |
| CC-BY-2.5 | cc-by | yes | 2 | acappella-by |
| CC0-1.0 | cc0 | yes | 6 | acappella-pd |

Catalog-wide (1,506 rows): `pending` 1,481, `fetched` 17, `dropped` 8
(all `drop_reason='no-lyric-text'`), `failed` 0. Catalog was built with ~16
requests total (~25 s at the 1.5 s pace); descriptions ride `meta`, so all 25
fetches needed **zero additional requests**.

### 3 catalog rows verbatim (per task text)

```jsonc
{"source":"ccmixter","external_id":"70553","title":"Geppetto V4 (Pell + Stems)",
 "artist":"coruscate","url":"https://ccmixter.org/files/Coruscate/70553",
 "license_tier":"cc-by","license_ref":"CC-BY-2.5","release_ok":"yes",
 "license_url":"http://creativecommons.org/licenses/by/2.5/",
 "copyright_notice":"ccPlus commercial license also available via ccMixter/tunetrack",
 "category":"acappella-by","status":"fetched",
 "json_path":"acappella-by/coruscate-geppetto-v4-pell-stems.json"}   // meta elided
{"source":"ccmixter","external_id":"62648","title":"Les mauvaises & le Reve",
 "artist":"MalreDeszik","license_tier":"cc0","license_ref":"CC0-1.0",
 "release_ok":"yes","license_url":"http://creativecommons.org/publicdomain/zero/1.0/",
 "category":"acappella-pd","status":"dropped","drop_reason":"no-lyric-text"}
{"source":"ccmixter","external_id":"60474","title":"LI Bai – A Homesick Night(vocals)",
 "artist":"Moon Of Magick","license_tier":"cc0","license_ref":"CC0-1.0",
 "release_ok":"yes","category":"acappella-pd","status":"fetched",
 "json_path":"acappella-pd/moon-of-magick-li-bai-a-homesick-nightvocals.json"}
   // note: mojibake 'â\x80\x93' in the raw upload_name repaired to '–'
```

## GATE R robots/API conflict — documented per task

`ccmixter.org/robots.txt` has `Disallow: /api/` for `User-agent: *` (+ full
`MLBot` ban), while http://t.ccmixter.org/about declares the Query API "an
open, publicly available interface … for public use" (R1 §1/§4). GATE R
(user decision, recorded in SPEC §2.1 roster + §9) resolved this as **polite
auto-fetch**: the adapter calls `polite_get` WITHOUT `robots=` for the API
path only (a robots=auto check would block the sanctioned endpoint),
registry-paced at ≥1.5 s/request, descriptive contact UA
(`toolshop-lyrics/1.0 (+contact: {contact})`, `TOOLSHOP_CONTACT` env).
`MLBot` is never spoofed. This is a legal-policy posture, not a nicety — if
the open-API statement is ever withdrawn, downgrade the row to
`catalog-only` (R1 §4 fallback).

## Deviations / decisions vs task text & SPEC

1. **`langdetect` not used** — megaplan task text said "language field via
   langdetect" but the package is NOT installed and pip installs are
   disallowed ("no new third-party deps beyond `[lyrics]` extra"). Replaced
   with a deterministic ~7-language stopword vote (`_guess_language`), default
   `en` on ambiguity; `None` under 8 tokens. Field is advisory-only.
2. **`lic=pd` items carry CC0 deed URLs** — all 24 pd-lane items observed
   have `license_url=…/publicdomain/zero/1.0/` → `CC0-1.0`/tier `cc0`/`yes`
   (category `acappella-pd`), NOT `LicenseRef-public-domain` as the task text
   predicted (R1 asserted "ccMixter has no CC0" — empirically wrong).
   `LicenseRef-public-domain` still resolves automatically for
   `publicdomain/mark/*` items should any appear. Same release-safety, honest
   SPDX. Flagged for W6 review.
3. **`X-JSON` header quirk** — ccHost echoes the whole JSON body in a single
   `X-JSON` response header; `dataview=default` pages exceed Python's
   `http.client._MAXLINE` (64 KiB) → `LineTooLong` on every call.
   `_raise_http_header_limit()` bumps it to 1 MiB inside the adapter —
   documented in the module docstring.
4. **Descriptions ride `catalog meta`** — `iter_catalog` stores
   `upload_description_plain` per row so `fetch_lyrics` needs no per-item
   request (halves the politeness budget: full catalog = ~16 requests).
   `_catalog.json` is ~5 MB under gitignored `data/`. `fetch_lyrics` still
   has an `ids=<fid>` single-item refetch fallback for hand-built catalogs.
5. **Round-robin lane interleave** — `iter_catalog` interleaves `lic=` lanes
   so a `--limit N` pilot spans license classes (else the 24-item pd lane
   would finish invisibly or the by lane would dominate). Deterministic;
   catalog is a full listing regardless.
6. **Extraction = header OR longest verse-run** — R1's informal headers
   (`Lyrics:`, `WORDS`, `LYRICS/SPOKEN WORD:`) handled, plus header-less
   lyric pells (verses before/after prose, separator-delimited). Gates:
   ≥4 lines + ≥120 chars (header) / ≥140 chars (verse-run) → `DropItem(
   'no-lyric-text')`. Signature/footers/`____` separators stripped;
   latin-1→utf-8 + cp1252→utf-8 mojibake repair and U+FFFD/C1 scrub on
   `clean_lyrics` only (`raw_lyrics` keeps the verbatim block).
7. **wikimedia_commons NOT built** — GATE R cut it (R1 §6: ~134 files, no
   lyric text); registry `cut` section already records why. Done per task.

## Files committed this session

- `c72b2ee` `feat(#065)`: `sources/ccmixter.py`, `tests/test_lyrics_sources_ccmixter.py`,
  `tests/fixtures/lyrics_sources/ccmixter_query_page.json`, `CHANGELOG.md`.
- `CREDITS.md` fixture-provenance row was swept into I4's `471cdf7`
  (uncommitted shared file at their commit time) — verified present in HEAD.
- Handoff commit: appended below at write time.
- NOT committed: `data/toolshop/lyrics/ccmixter/` corpus (gitignored),
  `_probe*.json`/`_fixture_real.json` scratch files in data (gitignored).

## Risks / notes for downstream waves

- **W5 ingest:** corpus at `data/toolshop/lyrics/ccmixter/` →
  `build_database(corpus='ccmixter', incremental=)`. `primary_artist` =
  uploader (`NOT NULL` contract honoured). `license`→`license_ref` mapping is
  handled by `_insert_song` per SPEC §4.1.
- **Study lanes:** `CCMIXTER_LANES=nc,sa` (or extend default) adds ~4.2k NC +
  SA items for the study corpus — release layout stays clean via the
  license-classed categories.
- **Catalog staleness:** `_catalog.json` is a point-in-time listing;
  `iter_catalog` re-runs merge via upsert (terminal statuses preserved).
- **Concurrency note:** this lane ran alongside I3/I4 in the same tree —
  registry row count is now **19** (wikisource merge); core test asserts were
  updated by I3. My commit contains ONLY my four files.
- **closeout:** `toolshop closeout` result pasted at bottom.

## `toolshop closeout` evidence

(to be filled after final commit)
