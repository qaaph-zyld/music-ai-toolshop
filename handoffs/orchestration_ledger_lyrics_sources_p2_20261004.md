# Orchestration ledger · lyrics-sources P2 megaplan · 2026-10-04

- **Plan:** `D:\Projects\.workspace_archive\plans\lyrics-sources-p2-megaplan.md` (adversarially reviewed 2026-10-04, verdict approved-with-fixes — all folded in)
- **Waves:** `ORCHESTRATION/lyrics_sources/waves_megaplan_p2.json` (agent task prompts embedded)
- **Mode:** waves sequential; P2-A agents parallel-OK; P2-B runs strictly sequential in listed order; gates are USER gates (GATE P2 = megaplan approval; jamendo sub-gate = key; rimer sub-gate = measured pilot)
- **Lane:** `lyrics-p2` branch on worktree `D:\Projects\Music-AI-Toolshop-wt-lyrics-p2`; every data command exports `TOOLSHOP_DATA_DIR=D:\Projects\Music-AI-Toolshop\data\toolshop` (worktree `data/` is empty — gitignored)
- **Python:** `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe` only
- **Prior phase:** ledger `orchestration_ledger_lyrics_sources_20260929.md` — phase-1 closed APPROVED (wave_6/V1)

| Wave | Agent(s) | Status | Handoff | Notes |
|---|---|---|---|---|
| **GATE P2** | user | ✅ **PASSED** — plan approved 2026-10-04 | — | scope: full ingest + synced lyrics; all gated sources with workarounds |
| P2-pre | orchestrator | ✅ **DONE** — worktree `Music-AI-Toolshop-wt-lyrics-p2` @ `2cae51a` (branch `lyrics-p2`); test comment committed `2cae51a`; `TOOLSHOP_DATA_DIR` → `corpus_root` verified resolving to canonical `data/toolshop/lyrics/`; no concurrent writers | — | — |
| P2-A | D1 `0dea85f9` · S1 `7b615658` | ✅ **DONE** — S1 `eddbc3c`+`c86afb0`; D1 `0e60e97`+`faf084f`; gate-check: worktree clean, 170+158 lyrics-sources tests green, adversarial subcat case proven | `wave_p2_a1/D1_handoff.md`, `wave_p2_a2/S1_handoff.md` | D1: two-pass ns-14 category-graph dump ingestor (live pilot → B7); S1: `_seed.json` 1,425 rows, all `release_ok=no` |
| P2-B1 | mudcat-digitrad `--resume` | ✅ **DONE** — exit 0, ~70 min local; fetched 7,125/7,125, failed 0; catalog 7,150 fetched / 1,830 dropped / 0 pending; `b939083` | `wave_p2_b/F_mudcat_handoff.md` | drops: 1,649 copyright-flagged, 158 parser-rejected; 38 intra-corpus dupes |
| P2-B2 | sacred-texts `--resume` | ✅ **DONE** — exit 0; fetched 277/305, dropped 28 (all `no-ballad-text`), failed 0; `d28479e` | `wave_p2_b/F_sacred_handoff.md` | NOTE: `` mojibake in lyric text (upstream legacy charset) — cleanup pass candidate before NLP consumers |
| P2-B3 | gutenberg_pd `--catalog-only`→`--resume` | ✅ **DONE** — catalog 243→272 (+29), fetched 245, dropped 27 (`too-short`), failed 0; `7df7403` | `wave_p2_b/F_gutenberg_handoff.md` | ⚠ finding: `split_songs` returns [] for 6/10 works (child-vol2-5, songs-of-the-west, bundle-of-ballads) — splitter coverage gap, fix dispatched in parallel (G-fix) then re-catalog |
| P2-B4 | ccmixter `--catalog-only`→`--resume` | ✅ **DONE** — fetched 547, dropped 959 (`no-lyric-text`), failed 0; yield 36.3%; cc-by 534 + pd 13, study-only fetched 0; `1a4619a` | `wave_p2_b/F_ccmixter_handoff.md` | yield below est. — remix-event upload descriptions lack lyric headers; drops correctly reasoned |
| P2-B3-fix | gutenberg splitter coverage (G-fix) | ✅ **DONE** — `442ee51`; all 6 silent works now split (child-vol2 294, vol3 170, vol4 296, vol5 93, sotw 123, bundle 29); also fixed treble-spacing orphan bug (sotw all-empty) + PART/FYTTE class fix; 28 tests green | `wave_p2_b/G_fix_handoff.md` | side-effects: child-vol1 125→228, yorkshire 85→81, old-ballads 43→40 — net corpus ~1,373 vs 245 |
| P2-B3-rerun | gutenberg re-catalog + `--resume` (post-fix) | ✅ **DONE** — catalog 272→1,380; fetched 1,352 (all 10 works emit; vol1 100→202); 28 `too-short`; ~9 min local; `fb4ce99` | `wave_p2_b/F_gutenberg2_handoff.md` | 45 slug-collision dupes in `_dedup_log.json` — consumers use `_index.json` (1,307 uniques) |
| P2-B5 | lrclib `--catalog-only`→`--resume` | ✅ **DONE** — 863/1,425 matched (60.6%, all search); synced_lyrics 610 (68.8%), lyricsfile 887/887; misses 559 not-found + 3 instrumental; 0 failed, 0×429, ~36 min; `52b817e` | `wave_p2_b/F_lrclib_handoff.md` | `release_ok=no` held on all 1,450 rows; P2-A4 answered: worthwhile ex-YU coverage |
| P2-B6 | hymnary bounded retry | ✅ **DONE — deferred-with-evidence** — probe 23/25 → 403 (Bunny challenge persists); 3 fetched all ≤1930-verified; 524 rows stay `--resume`-retryable; `c9a6941` | `wave_p2_b/F_hymnary_handoff.md` | adapter enforces Crawl-delay 5s; grinding a challenged host risks hard block — correct defer per SPEC §9 |
| P2-B7 | wikisource_pd via D1 dump (sr→en) | ✅ **DONE** — catalog 14,943 rows fully resolved: sr 12,220 fetched / 1,555 dropped + en 430 fetched / 738 dropped, 0 failed; en member-cats 24, all rows `pd`/`release_ok=yes`, 0 conditional; index 12,580 uniques (94 sr dupes); `2747a3c` | `wave_p2_b/F_wikisource_handoff.md` | en dump arrived truncated (1.77/3.43 GB) → EOFError pass 1 → `curl -C -` resumed to byte-exact remote size, re-run exit 0 (~57 min); en yield 36.8% inside ~300-500 est |
| P2-B8 | jamendo | ✅ **DONE — inert** — user gate: `JAMENDO_CLIENT_ID` not supplied → recorded inert, no catalog created, exit clean; `cb67372` | `wave_p2_b/F_jamendo_handoff.md` | can be revived any time by supplying the key (catalog-only → `--resume` path still in adapter) |
| P2-I | I9 implementer | ✅ **DONE** — 7 corpora ingested additive-only (~98 min): +22,569 songs → db 24,088 (I9 handoff's '24,488' = transposition, V2-corrected); lrclib idempotency `Ingested: 0`; genius invariant **1425/10654/65912/273801** byte-identical; 0 songs missing song_metrics/song_rhyme_metrics; rimer pilot 10.3 s/song on sacred-texts → proj ~36-64h → **user gated: approved full run** (actual ~0.11-0.23 s/song on big corpora); `_release_v1` export 21,776 emitted / 0 pending / 0 skipped, CREDITS TASL ×534 cc-by; `f41eb3c` | `wave_p2_5/I9_handoff.md` | jamendo skipped (inert); concurrent-actor incident: worktree corpus_inventory run clobbered before-snapshot file at 22:03 (locked-db traceback, no harm) |
| P2-V | V2 reviewer | ✅ **DONE — approved-with-fixes** — all 10 gates run live: idempotency `Ingested:0`, genius invariant byte-identical, license audit 93/0 mismatches (+live parity sr:42408), fresh release smoke 21,776 all `yes` no genius/lrclib dirs, policy invariants 4/4, lrclib 887/887 `no`, seed 10/10, dump 20/20; 166 tests green; `closeout` exit 1 declared (worktree submodules uninitialized); 8 findings all low (3 open routed: `24,488` typo fix applied here, `build-rimer` aggregate → merge checklist, synced_lyrics DB columns → future schema lane) | `wave_p2_6/V2_handoff.md` | review `.workspace_archive/reviews/2026-10-06_0146_lyrics-sources-p2-impl.md`; merge `lyrics-p2→master` = separate user-gated session |

## Invariants checked at each wave boundary
- `lyrics.db` genius-pro counts unchanged (1425/10654/65912/273801 — DB-verbatim, not handoff-relayed)
- no corpus/lyric data committed (`git ls-files` under `data/toolshop/lyrics/` stays empty)
- no `import toolshop` inside `Genious_lyrics_extractor/sources/` or folder scripts
- no fetch path exists for `catalog-only`/`manual`/`uncleared` sources
- lrclib `release_ok='no'` forever — a `yes` row is a release blocker
- `TOOLSHOP_DATA_DIR` set for every data command in the worktree

## Volume expectations (verified against on-disk catalogs 2026-10-04)

| Source | Pending | Expected fetched |
|---|---|---|
| mudcat-digitrad | 7,125 | ~7,100 |
| wikisource_pd | ~10k+ sr / ~300-500 en | ~8-10k |
| ccmixter | 1,481 | ~650-900 |
| gutenberg_pd | 215→(full list) | ~600-1k |
| sacred-texts | 280 | ~280 |
| hymnary | 522 | 0-500 (retry-or-defer) |
| lrclib | ~1,425 seeds | hit-rate TBD |
| jamendo | — | key-gated |
| **release-cleared total** | | **~17-19k** (from 69 today) |
