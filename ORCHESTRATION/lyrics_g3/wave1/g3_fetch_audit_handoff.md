# G3 Fetch Audit — Wave 1 Handoff

**Audit time:** 2026-10-07 ~01:30 CEST | **Auditor:** wave subagent (read-only)
**Corpus:** `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\genius\` (shared canonical)
**Status file:** `data/toolshop/lyrics/genius/_fetch_status_g3.json`
**Fetcher log:** `D:\Projects\Music-AI-Toolshop-wt-lyrics-g3\.scratch_fetch_g3.log`

## VERDICT: FETCH INCOMPLETE — and the fetcher process is DEAD (not running)

Ledger row "G3-B fetch | RUNNING" is stale. Evidence:
- `.scratch_fetch_g3.log` last write **00:08:27**, ends at banner `Fetching: Crni Cerak (cohort=drill_trap)` — no lines after.
- `_fetch_status_g3.json` last write **00:08:27** (fox done). No `in_progress` entry for crni-cerak — per `extract_roster.py:320-323`, in_progress is written immediately after resolve returns, so the process died/hung *inside* `fetch_artist_songs_resolving` (or was killed).
- No dir/file write anywhere in the corpus since 00:08:27 (dir mtime scan).
- `tasklist`/`Get-CimInstance` process scan: **no `extract_roster.py` python process exists**. 8 python processes alive, all unrelated (audition_review, mojgrad_mix w3/w4 scripts).

**Action needed:** restart `extract_roster.py --resume --delay 1.5` (resume-safe per done-gates at `extract_roster.py:296-298`).

## Roster verification (16 artists, pins OK)

`Genious_lyrics_extractor/roster_g3.json` — 16 artists, all `genius_artist_id` pinned. Folders: zera, mimi-mercedez, surreal, fox, crni-cerak, lacku, 2bona, marlon-brutal, bulevar, teodora, jelena-karleusa, aleksandra-prijovic, dara-bubamara, zoi, pajak, arafat.

## Fetch status (done artists)

| Artist (folder) | status | total_songs | genius_artist_id | done_song_ids |
|---|---|---|---|---|
| zera | done | 21 | **null ⚠** | **empty [] ⚠** |
| mimi-mercedez | done | 112 | 220572 ✓ | 112 ids |
| surreal | done | 88 | 4181 ✓ | 88 ids |
| fox | done | 174 | 13438 ✓ | 174 ids |

**Pending (12 — never started, not merely in-flight):** crni-cerak, lacku, 2bona, marlon-brutal¹, bulevar, teodora, jelena-karleusa, aleksandra-prijovic, dara-bubamara, zoi, pajak, arafat¹.
¹ arafat / marlon-brutal have pre-created duo dirs as collab side-products of the surreal/mimi fetches; their own artist fetches have not run.

## Corpus tree — new G3 dirs (12 dirs, 391 song JSONs; `*.json` excl. `_index/_dedup_log`)

| Dir | JSONs | | Dir | JSONs |
|---|---|---|---|---|
| zera-solo | 19 | | fox-solo | 104 |
| zera-featured | 2 | | fox-featured | 66 |
| mimi-mercedez-solo | 88 | | fox-mimi-mercedez-duo | 2 |
| mimi-mercedez-featured | 21 | | fox-surreal-duo | 2 |
| surreal-solo | 68 | | arafat-surreal-duo | 1 |
| surreal-featured | 17 | | marlon-brutal-mimi-mercedez-duo | 1 |

Reconciles exactly with status totals (duo files count toward both artists):
zera 19+2=**21** ✓ · mimi 88+21+2+1=**112** ✓ · surreal 68+17+2+1=**88** ✓ · fox 104+66+2+2=**174** ✓.
No G3 trio or `other-collab` dirs yet. All other dirs in the tree are pre-existing G1/G2 batches (ana-nikolic, breskvica, jala-*, tng, voyage, …).

## Spot-check results (3 files/dir, all 12 dirs + full null-id sweep of all 391)

- `primary_artist` correct in every sample; `-featured` dirs carry the external primary + roster artist in `featured_artists` (e.g. `juice-mala-ima-kasko`: primary Juice, feat Mimi ✓).
- `sections[]` non-empty with non-empty content in **all 391 files**.
- Duo dirs correctly pair the two named roster artists (each file: one primary, other featured).
- **`genius_song_id` populated in 370/391 files. ALL 21 zera files are `null`.**

## FLAGS

1. **Zera batch is a pre-fix artifact (remediation required before ingest).** All 21 zera JSONs have `genius_song_id: null`; status entry shows `genius_artist_id: null` + `done_song_ids: []`. Consistent with zera having been fetched under pre-`8a82573` code (lyricsgenius 3.x `.id`→`_body` bug at `extract_roster.py:109-115`), then frozen by `--resume`'s done-gate (`:296`). **Resume will never heal zera** — the status entry must be reset (or files patched) deliberately.
2. **Fetcher dead mid-resolve on crni-cerak** — see verdict. Log ends at the banner; no traceback captured (kill-silent or hang-then-death).
3. **No folder-name anomalies:** all 12 new dirs are `<roster>-solo|featured` or `<roster>-<roster>-duo` — all names map to roster folders.
4. **No cross-cohort collab dirs — by design.** `categorize_song` (`extract_roster.py:84-106`) only creates duo/trio dirs between **G3-roster** artists; G3×G1/G2 collabs land in `-featured` (observed: `tng-hoću-još` → mimi-mercedez-featured, `dj-architect-ko-će-pre` feat Fox+Surreal → surreal-featured). All 4 existing duo dirs are intra-G3 pairs. Downstream DB ingest must not expect cross-batch duo folders.
5. Minor: `.txt` sidecars written beside each `.json` (by `save_song`) — informational only; index builders already ignore them.

## Recommendations for next waves

1. **Before restarting fetch:** decide zera remediation — cleanest is deleting zera's status entry (+ its 21 json/txt) so `--resume` re-fetches with the fixed code; alternative is an id-patch script keyed on the stored `url` field.
2. **Restart command:** `python extract_roster.py --resume --delay 1.5` from `Genious_lyrics_extractor/`, logging to `.scratch_fetch_g3.log` (append). Remaining ~12 artists at ledger's ~9 songs/min ⇒ still hours.
3. **Do NOT run G3-DB ingest** until (a) all 16 artists `status=done`, (b) zera ids are non-null (or an explicit null-tolerance decision is recorded — `build_unified_index` dedup/keying likely depends on it).
4. Ledger line 11 should be corrected: fetch is not "RUNNING" — it has been dead since 00:08.

## Grand total so far

**391 song JSONs on disk across 12 new G3 dirs** (attributed: zera 21 + mimi 112 + surreal 88 + fox 174; unique files 391 — duo songs stored once, counted in both artists' status totals).
