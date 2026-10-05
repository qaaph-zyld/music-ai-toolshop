# F — wikisource_pd dump-ingest executor handoff (run B7)

**Date:** 2026-10-05 (session clock ~19:30–20:40; sr pass ran in prior session ~02:50–03:10)
**Lane:** `lyrics-p2` @ worktree `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2`
**Role:** fetch executor — no code edits made.
**Source:** Wikimedia `pages-articles` XML dumps only (no API, no scraping).

## Commands (verbatim, as run)

Environment on every invocation: `TOOLSHOP_DATA_DIR=D:\Projects\Music-AI-Toolshop\data\toolshop`,
interpreter `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -X utf8`, `PYTHONUNBUFFERED=1`.

**sr pass** (prior session; agent record vanished — stats below reconstructed from catalog, all verified this session):

```
python -X utf8 Genious_lyrics_extractor/wikisource_dump_ingest.py \
  --dump data/toolshop/lyrics/wikisource_pd/_src/srwikisource-latest-pages-articles.xml.bz2 \
  --wiki sr --resume
```

**en pass — attempt 1** (this session, ~19:36, background shell): same flags with `--dump .../enwikisource-latest-pages-articles.xml.bz2 --wiki en`.

**Exit: FAILED** — `EOFError: Compressed file ended before the end-of-stream marker was reached` in pass 1 (`bz2` stream ended mid-decompress while building the category graph). Cause: **the local dump was truncated** — 1,772,580,864 B on disk vs remote `Content-Length: 3,428,152,987` (last-modified 2026-10-01). The prior session's download never completed. No catalog writes occurred before the failure (crash was pre-pass-2), so sr data was untouched.

**Dump repair** (this session): remote `Accept-Ranges: bytes`; verified same dump revision via a 256-byte `Range` fetch at offset 900 MB compared to the local file (identical), then:

```
curl -C - -o enwikisource-latest-pages-articles.xml.bz2 \
  https://dumps.wikimedia.org/enwikisource/latest/enwikisource-latest-pages-articles.xml.bz2
```

Resumed ~1.66 GB tail; final size **3,428,152,987 B = remote Content-Length exactly**. Egress to dumps.wikimedia.org was NOT corp-blocked — no user-run needed.

**en pass — attempt 2** (~19:36–20:33, ~57 min wall): identical ingest command.

**Exit code: 0.**

```
[wikisource_pd] dump pass 1: building member-category set for wiki 'en' (roots=6, max_depth=2) ...
[wikisource_pd] member categories: 24
[wikisource_pd] index: 12580 unique songs, 94 intra-corpus dupes
[wikisource_pd] done: {'fetched': 430, 'failed': 0, 'dropped': 738, 'offset_skipped': 0, 'candidates': 1168, 'terminal_skipped': 0} (catalog counts: {'fetched': 12650, 'dropped': 2293})
```

Entry roots used (unchanged from adapter): `Category:Folk songs`, `Category:Ballads`, `Category:Traditional ballads`, `Category:Song books`, `Category:Hymns`, `Category:Collections of poetry`.

## Counts — combined catalog (post-run, `_catalog.json` verified this session)

| Wiki | Catalog rows | fetched | dropped | failed | member cats (pass 1 / distinct in rows) |
|---|---|---|---|---|---|
| sr | 13,775 | 12,220 | 1,555 | 0 | not preserved (agent record lost) / **118** |
| en | 1,168 | 430 | 738 | 0 | **24** / **21** |
| **total** | **14,943** | **12,650** | **2,293** | **0** | — |

- sr rows **byte-stable**: fetched 12,220 / dropped 1,555 matches the pre-run baseline exactly; every sr row still `meta.via='dump'`; en rows appended cleanly — **zero `foreign_identifier`/wiki mismatches** across all 14,943 rows.
- `_index.json` rebuilt: **12,580 unique songs**, 94 intra-corpus dupes — all 94 are sr-side title collisions (e.g. `Бој на салашу` variants); all 430 en fetched rows indexed.
- `_catalog.json.tmp` from the vanished session is gone — the successful run's atomic write cleaned it. Corpus artifacts remain under the main-repo data dir only (gitignored); nothing corpus-related touched the worktree.

## License verdict distribution (all fetched rows)

| Wiki | license | license_tier | release_ok |
|---|---|---|---|
| sr (12,220) | `LicenseRef-public-domain` 100% | `pd` 100% | `yes` 100% |
| en (430) | `LicenseRef-public-domain` 100% | `pd` 100% | `yes` 100% |

**Conditional / CC-BY-SA rows: 0** — no `pending_decisions` contribution from this source. (Wikisource pages in scope carried PD markers only; dump `meta.license_templates` carried no conditional licenses.)

## Drop-reason histogram

sr (1,555):
```
{'too-short:2-verse-lines': 1228, 'too-short:3-verse-lines': 302,
 'too-short:1-verse-lines': 11, 'too-short:0-verse-lines': 11,
 'toc-or-index-page': 3}
```
en (738):
```
{'too-short:0-verse-lines': 427, 'too-short:2-verse-lines': 191,
 'too-short:3-verse-lines': 60, 'too-short:1-verse-lines': 59,
 'toc-or-index-page': 1}
```

en drops are dominated by collection/anthology landing pages and stub pages carrying no extractable verse lines — consistent with the poetry-collections/song-books roots. en fetch yield 430/1,168 = **36.8%**, inside the spec's ~300–500 expectation.

## Catalog status histogram (whole catalog)

```
{'fetched': 12650, 'dropped': 2293}
```
(0 pending, 0 failed, 0 skipped — fully resolved.)

## Category histograms (fetched rows)

sr: `zenske` 4,804 · `ostalo` 4,097 · `epske` 1,910 · `lirske` 1,179 · `erlangen` 188 · `vuk-zbirke` 42
en: `hymns` 268 · `ballads` 67 · `poetry-collections` 53 · `folk-songs` 36 · `song-books` 6

## 3 emitted en song headers (from `_index.json`)

```json
{"foreign_identifier": "en:233892", "title": "A Ballad of Ducks", "primary_artist": "Traditional", "category": "ballads", "license_tier": "pd", "release_ok": "yes", "language": "en"}
{"foreign_identifier": "en:116813", "title": "A Ballad of Trees and the Master", "primary_artist": "Traditional", "category": "ballads", "license_tier": "pd", "release_ok": "yes", "language": "en"}
{"foreign_identifier": "en:121103", "title": "A Ballade of Theatricals", "primary_artist": "Traditional", "category": "ballads", "license_tier": "pd", "release_ok": "yes", "language": "en"}
```

## Git evidence (worktree, pre-commit)

```
$ git -C "D:/Projects/Music-AI-Toolshop-wt-lyrics-p2" status --short
(clean — nothing but this handoff added)

$ git -C "D:/Projects/Music-AI-Toolshop-wt-lyrics-p2" log --oneline -3
cb67372 lyrics-p2: B8 jamendo handoff — inert, JAMENDO_CLIENT_ID not supplied (user gate)
52b817e lyrics-p2: F handoff — lrclib run B5 (863/1425 fetched, 60.6% hit, release_ok=no x1450)
c9a6941 lyrics-p2: B6 hymnary fetch probe handoff — deferred-with-evidence (23/25 403, Bunny challenge persists; 2/25 fetched, <=1930 gate held)
```

## Risks / notes for downstream waves

1. **en dump was truncated on arrival** (48%) — any future `latest`-dump re-fetch must verify `Content-Length` vs on-disk size before ingest; `curl -C -` resume worked cleanly.
2. **en yield is modest (430)** — the 6 roots with max_depth=2 mostly surface hymn/psalm stubs and anthology landing pages. If more en volume is ever wanted, the lever is deeper `max_depth` or additional roots, not a re-run (`--resume` is a no-op now: catalog fully resolved).
3. **94 sr intra-corpus dupes** collapsed in `_index.json` — consumers must read the index, not the catalog, for unique songs (same caveat as gutenberg's 45 dupes).
4. sr `meta.member_cat` spans **118** real subcategories — good provenance granularity for downstream slicing; en spans **21**.
5. Runtime observation only: pass 1 (~20 min) + pass 2 (~37 min) decompress/parse the full 3.4 GB twice — expected cost, not a defect. A ~15 min candidate-free stretch near EOF is normal.
6. No failures, no network use in the ingest path itself, no license ambiguity — **this source is done**.
