# F — mudcat_digitrad fetch handoff (wave p2_b, run B1)

Executor run of `fetch_lyrics_source.py --source mudcat_digitrad --resume`
against the complete pre-built catalog (8,980 rows). Fully local parse of the
cached `DTSpring2002MSDOS.zip` in `<corpus>/_src/` — no network observed.

## Command (verbatim)

Working dir: `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2/Genious_lyrics_extractor`

```
TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe fetch_lyrics_source.py --source mudcat_digitrad --resume
```

(Executed via shell `env`/`workdir` params; env var set for the process.
Emitted one benign `RequestsDependencyWarning` about urllib3/chardet versions.)

**Exit code: 0**

## Pre-run catalog state

```
total: 8980
{'fetched': 25, 'dropped': 1830, 'pending': 7125}
```

## Run log — final lines (verbatim)

```
  [7124/7125] OK (dt): Traditional — ZULEIKA
  [7125/7125] OK (dt): Traditional — THE ZULU KING
[mudcat_digitrad] index: 7112 unique songs, 38 intra-corpus dupes
[mudcat_digitrad] done: {'fetched': 7125, 'failed': 0, 'dropped': 0, 'skipped': 0} (catalog counts: {'fetched': 7150, 'dropped': 1830})
```

- Final stats: `{fetched: 7125, failed: 0, dropped: 0, skipped: 0}`
- `failed = 0` → **no second `--resume` pass run** (per retry rule — stop and report).
- Wall time ≈ 70 min (~100 items/min; per-item catalog flush is the bottleneck).

## Post-run catalog counts (verbatim, from `_catalog.json`)

```
TOTAL 8980
STATUS {'fetched': 7150, 'dropped': 1830}
```

0 pending / 0 failed / 0 skipped remain. Catalog is fully resolved.
On-disk check: `dt/` holds 7,150 `.json` + 7,150 `.txt` = 14,300 files —
matches `fetched: 7150` exactly. Index reports 7,112 unique songs,
38 intra-corpus dupes (see `_dedup_log.json`).

## Drop-reason histogram (all 8 kinds; top 5 = required)

```
   1270  copyright-flagged:copyright-word
    296  copyright-flagged:copyright-sign
    108  title-unresolved
     55  copyright-flagged:prev-record-trailer
     50  no-lyric-text
     33  copyright-flagged:c-paren-year
     17  copyright-flagged:c-paren-name
      1  copyright-flagged:permission-grant
```

1,830 dropped total: 1,649 copyright-flagged (conservative §9 gate —
incl. 55 propagated from previous-record trailers), 158 parser-rejected
(title-unresolved / no-lyric-text).

## Verbatim catalog rows

### fetched (processed this run — `[1/7125]`)

```json
{"artist": "Traditional", "category": "dt", "copyright_notice": null, "creator": "Traditional", "creator_url": null, "drop_reason": null, "external_id": "ACAPGLD", "fetched": true, "foreign_identifier": "ACAPGLD", "json_path": "dt/traditional-acapulco-gold.json", "license": "LicenseRef-public-domain", "license_ref": "LicenseRef-public-domain", "license_tier": "pd", "license_url": "https://creativecommons.org/publicdomain/mark/1.0/", "meta": {"charter_note": "Digital Tradition not-for-profit charter item; no copyright/� marker found in the source record (Spring 2002 askSam snapshot).", "copyright_flagged": false, "dt_filename": "ACAPGLD", "tags": [], "title_verified": true, "transcriber": "MC"}, "release_ok": "yes", "source": "mudcat_digitrad", "source_url": "https://mudcat.org/download.cfm", "status": "fetched", "title": "ACAPULCO GOLD", "url": "https://mudcat.org/download.cfm"}
```

### dropped-with-reason

```json
{"artist": "Tim Woodson", "category": "dt", "copyright_notice": null, "creator": "Tim Woodson", "creator_url": null, "drop_reason": "copyright-flagged:c-paren-year", "external_id": "FISHFRY", "fetched": false, "foreign_identifier": "FISHFRY", "license": null, "license_ref": null, "license_tier": "pd", "license_url": null, "meta": {"charter_note": "Digital Tradition not-for-profit charter item; no copyright/� marker found in the source record (Spring 2002 askSam snapshot).", "copyright_flagged": true, "copyright_marker": "c-paren-year", "copyright_snippet": "Tim Woodson, Music Tim Woodson, Rob Compton, Pat Stevenson (c) 1995. @fishing @food JD July01 �. �+", "dt_date": "July01", "dt_filename": "FISHFRY", "source_line": "Recorded by Wildhorse Creek | Lyrics Tim Woodson, Music Tim Woodson, Rob Compton, Pat Stevenson (c) 1995.", "subtitle": "Tim Woodson", "tags": ["fishing", "food"], "title_verified": true, "transcriber": "JD"}, "release_ok": null, "source": "mudcat_digitrad", "source_url": "https://mudcat.org/download.cfm", "status": "dropped", "title": "(I'VE GOT) BIGGER FISH TO FRY", "url": "https://mudcat.org/download.cfm"}
```

### failed

**None — `FAILED_COUNT 0` in `_catalog.json`.** No row exists to quote.

## Notes for downstream waves

- Executor role: no code edits made; run was not interrupted.
- Parse-error rate 0% — nowhere near the 10% stop threshold; parser is healthy.
- All 7,150 fetched items are `license_tier: pd`, `license:
  LicenseRef-public-domain`, `release_ok: yes`, carrying the charter
  `modified_note` required by GATE 0 Q4.
- 38 intra-corpus dupes were folded in `_index.json` (7,150 fetched →
  7,112 unique); audit `_dedup_log.json` if a stricter count is needed.
- Worktree tree was clean before this handoff; only this file is added.
