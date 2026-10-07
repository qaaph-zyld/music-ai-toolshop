# G3 Fetch Audit — Wave 1 Re-Audit (r2) Handoff

**Audit time:** 2026-10-07 ~19:45 CEST | **Auditor:** wave subagent (read-only)
**Corpus:** `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\genius\` (shared canonical)
**Status file:** `data/toolshop/lyrics/genius/_fetch_status_g3.json` | **Summary:** `genius/_summary_g3.md` (exists, dated 19:18)
**Fetcher log:** `D:\Projects\Music-AI-Toolshop-wt-lyrics-g3\.scratch_fetch_g3.log` — ends cleanly with `Summary saved` (last entry arafat [56/56]); no traceback.
**Supersedes:** `g3_fetch_audit_handoff.md` (run-1, verdict FETCH INCOMPLETE / fetcher dead). Both run-1 blockers now resolved: fetcher ran to completion (18:18 detached relaunch), zera re-fetched with populated ids.

## VERDICT: INGEST READY

All 16 artists `status=done`, all `genius_artist_id` pinned and matching `roster_g3.json`, **zero** null `genius_song_id` on disk, zero empty `sections[]`, zero folder-name or cross-cohort anomalies. One flagged non-blocking gap below (lacku 5446636).

## Per-artist status (16/16 done — attributed song counts)

| Artist (folder) | id | songs | | Artist (folder) | id | songs |
|---|---|---|---|---|---|---|
| zera | 2625064 | 21 | | bulevar | 369563 | 2 |
| mimi-mercedez | 220572 | 112 | | teodora | 1093106 | 53 |
| surreal | 4181 | 88 | | jelena-karleusa | 377401 | 150 |
| fox | 13438 | 174 | | aleksandra-prijovic | 623022 | 46 |
| crni-cerak | 2448528 | 29 | | dara-bubamara | 453327 | 139 |
| lacku | 991333 | 108 | | zoi | 1584694 | 28 |
| 2bona | 1588704 | 81 | | pajak | 2220922 | 33 |
| marlon-brutal | 182579 | 32 | | arafat | 182228 | 56 |

**Attributed total (sum of status `total_songs`/`done_song_ids`): 1152.** No `in_progress`/`error`/`resolve_mismatch` entries.

## New G3 dirs (38 dirs — `*.json` excl. `_index/_dedup_log/_fetch_status`, `.txt` sidecars excluded)

| Dir | n | Dir | n | Dir | n |
|---|---|---|---|---|---|
| zera-solo | 19 | 2bona-solo | 70 | dara-bubamara-solo | 137 |
| zera-featured | 2 | 2bona-featured | 10 | dara-bubamara-featured | 2 |
| mimi-mercedez-solo | 88 | marlon-brutal-solo | 22 | zoi-solo | 26 |
| mimi-mercedez-featured | 21 | marlon-brutal-featured | 7 | zoi-featured | 2 |
| surreal-solo | 68 | bulevar-solo | 2 | pajak-solo | 33 |
| surreal-featured | 17 | teodora-solo | 44 | arafat-solo | 42 |
| fox-solo | 104 | teodora-featured | 9 | arafat-featured | 10 |
| fox-featured | 66 | jelena-karleusa-solo | 146 | 2bona-crni-cerak-lacku-trio | 1 |
| crni-cerak-solo | 25 | jelena-karleusa-featured | 4 | arafat-lacku-duo | 1 |
| crni-cerak-featured | 2 | aleksandra-prijovic-solo | 45 | arafat-marlon-brutal-duo | 2 |
| lacku-solo | 66 | aleksandra-prijovic-featured | 1 | arafat-surreal-duo | 1 |
| lacku-featured | 38 | fox-mimi-mercedez-duo | 2 | crni-cerak-lacku-duo | 1 |
| | | fox-surreal-duo | 2 | marlon-brutal-mimi-mercedez-duo | 1 |

**Unique files on disk: 1139** (1134 distinct `genius_song_id`s — see flags). Reconciles: 1139 files + 10 duo + 2 trio + 5 cross-dir dup = 1156 file-attribution instances = 1152 status attributions − 1 missing file (lacku) − 4 over-count... precisely: 1128 single-dir files×1 + 10 duo×2 + 1 trio×3 = 1151 = 1152 − 1 missing. ✓

## Full-corpus sweeps (all 1139 files parsed, not sampled)

- `genius_song_id` null/missing: **0** — zera healed (e.g. `zera-baraba` id=8311571; status entry now id=2625064 + 21 done ids).
- `sections[]` empty or all-blank content: **0**. `artist_config` ≠ containing dir: **0**. Dir-named roster artist absent from `primary_artist`/`featured_artists`: **0**.
- Spot-check (seeded random, 3/cohort) — drill_trap: `fox-solo/fox-z-dilerima-rasto` (id 13210114, 7 sec), `crni-cerak-solo/...na-granici` (8648248, 10), `lacku-solo/lacku-mlada` (11346142, 9); pop: `jelena-karleusa-solo/...žena-zmija` (5842766, 7), `aleksandra-prijovic-solo/...opa-cupa` (13727545, 7), `...telo` (5906643, 5). All `primary_artist` correct, sections non-empty.
- Cross-cohort collab dirs: **none** — all 8 collab dirs are intra-drill_trap. No `other-collab` dirs. All dir names map to roster folders.

## FLAGS (non-blocking)

1. **1 status id has no file:** lacku `genius_song_id=5446636` — absent from entire corpus (grep). Cause: slug collision — two distinct songs both titled "Tenzija" logged OK at `[92/108]` and `[93/108]` → same `lacku-tenzija.json` filename, second overwrote first. Loss = 1/1152 attributions. Optional targeted re-fetch or record as accepted gap.
2. **5 song-ids stored twice** (external-primary collabs landed in both artists' `-featured` dirs): 2414649 (arafat+fox), 433668 (arafat+marlon-brutal), 10681080 (fox+surreal), 4181036 (jelena-karleusa+surreal), 5056769 (lacku+mimi-mercedez). **DB ingest must dedup/key on `genius_song_id`.**
3. `_summary_g3.md` "Categories this run" counts are save-events, not unique files (`arafat-marlon-brutal-duo: 4` vs 2 files — each song re-saved during both artists' fetches). Cosmetic only.
4. Ledger line 11 stale: says "RUNNING … 6/16 done" — actual state is 16/16 done (last status write 19:18:36).

## Recommendations for wave 2 (G3-DB ingest)

1. Proceed — dedup on `genius_song_id`; expect ≤1134 unique new songs (1139 files, 5 dup ids, minus none — all files ingestible).
2. Decide lacku 5446636: patch/re-fetch single song (title "Tenzija", id pinned in status) or accept 1-song gap.
3. Correct ledger G3-B row to DONE before/within the ingest commit.
4. Note `language: null` observed on samples — ingest should tolerate null language.
