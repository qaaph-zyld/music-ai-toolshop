# F — sacred_texts fetch executor handoff (run B2)

**Date:** 2026-11-27 (session clock ~01:41–01:50)
**Lane:** `lyrics-p2` @ worktree `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2`
**Role:** fetch executor — no code edits made.

## Command (verbatim, as run)

Canonical spec command:

```
TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe fetch_lyrics_source.py --source sacred_texts --resume
```

Executed from `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2/Genious_lyrics_extractor`
via the exec tool's `env` parameter (`{"TOOLSHOP_DATA_DIR": "D:/Projects/Music-AI-Toolshop/data/toolshop"}`)
— the inline `VAR=val cmd` form was denied by sandbox; semantics identical.

## Result

**Exit code: 0** — run completed, no failure storm (0 failed).

Terminal output verbatim (tail):

```
[sacred_texts] 280 entries to process (resume=True, corpus=D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\sacred-texts)
  [1/280] DROP: Traditional — Child ballad 26 (no-ballad-text)
  ...
  [280/280] OK (child-ballads): Traditional — Child ballad 305
[sacred_texts] index: 277 unique songs, 0 intra-corpus dupes
[sacred_texts] done: {'fetched': 254, 'failed': 0, 'dropped': 26, 'skipped': 0} (catalog counts: {'fetched': 277, 'dropped': 28})
```

Startup emitted two benign warnings only:

```
RequestsDependencyWarning: urllib3 (2.7.0) or chardet (None)/charset_normalizer (2.0.12) doesn't match a supported version!
FutureWarning: The 'strict' parameter is no longer needed on Python 3+.
```

## Counts

| State | Pre-run | This run | Post-run (catalog) |
|---|---|---|---|
| pending | 280 | — | 0 |
| fetched | 23 | +254 | 277 |
| dropped | 2 | +26 | 28 |
| failed | 0 | 0 | 0 |

- `_index.json`: **277 unique songs, 0 intra-corpus dupes**
- `child-ballads/`: 554 files on disk (277 `.json` + 277 `.txt`)
- Catalog: 305 total entries, all resolved (fetched or dropped)

## Drop histogram (whole catalog)

```
{'no-ballad-text': 28}
```

Single drop reason — pages in the Child index that carry no ballad text (scans/commentary stubs). 28/305 = 9.2%.

## 3 verbatim `_index.json` rows

```json
{"title": "A True Tale of Robin Hood", "primary_artist": "Traditional", "featured_artists": [], "category": "child-ballads", "url": "https://sacred-texts.com/neu/eng/child/ch154.htm", "status": "completed", "json_path": "child-ballads/traditional-a-true-tale-of-robin-hood.json", "txt_path": "child-ballads/traditional-a-true-tale-of-robin-hood.txt", "corpus": "sacred-texts", "source": "sacred_texts", "foreign_identifier": "child-154", "source_url": "https://sacred-texts.com/neu/eng/child/ch154.htm", "creator": "Traditional", "creator_url": null, "copyright_notice": "Ballads originally transcribed by Cathy Lynn Preston. HTML Formatting at sacred-texts.com. This text is in the public domain. These files may be used for any non-commercial purpose, provided this notice of attribution is left intact.", "modified_note": null, "license": "LicenseRef-public-domain", "license_url": "https://creativecommons.org/publicdomain/mark/1.0/", "license_tier": "pd", "release_ok": "yes", "derived_from": null, "script": "latin", "language": "en"}

{"title": "Adam Bell, Clim of the Clough and William of Cloudesly", "primary_artist": "Traditional", "featured_artists": [], "category": "child-ballads", "url": "https://sacred-texts.com/neu/eng/child/ch116.htm", "status": "completed", "json_path": "child-ballads/traditional-adam-bell-clim-of-the-clough-and-william-of-cloudesly.json", "txt_path": "child-ballads/traditional-adam-bell-clim-of-the-clough-and-william-of-cloudesly.txt", "corpus": "sacred-texts", "source": "sacred_texts", "foreign_identifier": "child-116", "source_url": "https://sacred-texts.com/neu/eng/child/ch116.htm", "creator": "Traditional", "creator_url": null, "copyright_notice": "Ballads originally transcribed by Cathy Lynn Preston. HTML Formatting at sacred-texts.com. This text is in the public domain. These files may be used for any non-commercial purpose, provided this notice of attribution is left intact.", "modified_note": null, "license": "LicenseRef-public-domain", "license_url": "https://creativecommons.org/publicdomain/mark/1.0/", "license_tier": "pd", "release_ok": "yes", "derived_from": null, "script": "latin", "language": "en"}

{"title": "Alison and Willie", "primary_artist": "Traditional", "featured_artists": [], "category": "child-ballads", "url": "https://sacred-texts.com/neu/eng/child/ch256.htm", "status": "completed", "json_path": "child-ballads/traditional-alison-and-willie.json", "txt_path": "child-ballads/traditional-alison-and-willie.txt", "corpus": "sacred-texts", "source": "sacred_texts", "foreign_identifier": "child-256", "source_url": "https://sacred-texts.com/neu/eng/child/ch256.htm", "creator": "Traditional", "creator_url": null, "copyright_notice": "Ballads originally transcribed by Cathy Lynn Preston. HTML Formatting at sacred-texts.com. This text is in the public domain. These files may be used for any non-commercial purpose, provided this notice of attribution is left intact.", "modified_note": null, "license": "LicenseRef-public-domain", "license_url": "https://creativecommons.org/publicdomain/mark/1.0/", "license_tier": "pd", "release_ok": "yes", "derived_from": null, "script": "latin", "language": "en"}
```

Spot-check of `traditional-alison-and-willie.json`: `raw_lyrics` 1406 chars, `clean_lyrics` 1344 chars, `sections` populated (10 stanza entries `256A.1`–`256A.10`), sibling `.txt` 1344 chars. Content is real ballad text, not boilerplate.

## Timing

~8–9 min wall clock for 280 items (background shell `5e2fc8`; progress tracked via `_catalog.json` flush-per-item: 89 fetched at ~3.5 min, 182 at ~6 min, done ~9 min). Effective throughput well above the nominal ≥1.5 s/page spacing — spacing is evidently enforced only on network hits that need it, or the adapter's delay is lower-bound; no 403/429s observed either way.

## Git evidence (worktree, pre-commit)

```
$ git -C "D:/Projects/Music-AI-Toolshop-wt-lyrics-p2" status --short
(clean — nothing but this handoff added)

$ git -C "D:/Projects/Music-AI-Toolshop-wt-lyrics-p2" log --oneline -3
b939083 lyrics-p2: B1 mudcat_digitrad fetch handoff — 7,125 fetched, 0 failed, catalog fully resolved
faf084f docs(lyrics-p2): P2-A/D1 handoff — dump ingestor committed, tests green, live pilot deferred to B7
0e60e97 feat(lyrics-p2): wikisource XML-dump ingestor (D1) — two-pass category-graph bulk ingest replacing 429'd API walk
```

Corpus artifacts live under `D:/Projects/Music-AI-Toolshop/data/toolshop/` (main repo data dir, gitignored) — nothing corpus-related touched the worktree.

## Risks / notes for downstream waves

1. **Encoding mojibake in section content.** `sections[].content` and `clean_lyrics` contain ``-style artifacts (e.g. `MY luve she lives`) — sacred-texts.com serves legacy charset pages and smart-quotes survive as U+FFFD/mis-decoded bytes. Lyrics are usable but a charset-cleanup pass may be wanted before corpus consumers treat text as clean. Fielded for a future adapter/data pass — executor role, no fix applied.
2. **Stanza labels are Child-numbered** (`256A.1`, …) — sections carry structural metadata, good for downstream stanza-aware use.
3. **Corpus complete for this source:** catalog fully resolved; any re-run with `--resume` is a no-op (280→0 pending). The 28 `no-ballad-text` drops are permanent unless the adapter's text extraction is improved.
4. No failures, no rate-limiting, no auth issues — sacred-texts.com tolerated the serial polite crawl fine.
