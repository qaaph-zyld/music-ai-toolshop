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
| P2-pre | orchestrator | ⬜ pending | — | create `lyrics-p2` worktree; commit dangling `tests/test_lyrics_sources_core.py` comment; verify TOOLSHOP_DATA_DIR resolves corpora on main data dir |
| P2-A | D1 dump ingestor · S1 lrclib seed | ⬜ pending | `wave_p2_a1/D1_handoff.md`, `wave_p2_a2/S1_handoff.md` | D1: two-pass ns-14 category-graph dump ingestor (API path 429'd — dumps are the sanctioned bulk channel); S1: genius-pro → `_seed.json` |
| P2-B1 | mudcat-digitrad `--resume` | ⬜ pending | `wave_p2_b/F_mudcat_handoff.md` | 7,125 pending — local parse, no network |
| P2-B2 | sacred-texts `--resume` | ⬜ pending | `wave_p2_b/F_sacred_handoff.md` | 280 pending |
| P2-B3 | gutenberg_pd `--catalog-only`→`--resume` | ⬜ pending | `wave_p2_b/F_gutenberg_handoff.md` | catalog pass IS the download stage (10 works) |
| P2-B4 | ccmixter `--catalog-only`→`--resume` | ⬜ pending | `wave_p2_b/F_ccmixter_handoff.md` | 1,481 pending, all `release_ok=yes`; expect ~45-60% lyric yield |
| P2-B5 | lrclib `--catalog-only`→`--resume` | ⬜ pending | `wave_p2_b/F_lrclib_handoff.md` | ~1,425 lookups; **deliverable = hit-rate report**; `release_ok=no` invariant |
| P2-B6 | hymnary bounded retry | ⬜ pending | `wave_p2_b/F_hymnary_handoff.md` | verify post-quarantine catalog (522) → `--resume --limit 25` probe → resume or defer-with-evidence |
| P2-B7 | wikisource_pd via D1 dump (sr→en) | ⬜ pending | `wave_p2_b/F_wikisource_handoff.md` | ~10k+ sr / ~300-500 en; overnight-capable; dump download may go user-run if proxy blocks |
| P2-B8 | jamendo | ⬜ pending | `wave_p2_b/F_jamendo_handoff.md` | **sub-gate: user supplies `JAMENDO_CLIENT_ID`** (stored-credential rule); else inert |
| P2-I | I9 implementer | ⬜ pending | `wave_p2_5/I9_handoff.md` | `--incremental` per corpus; genius invariant verbatim; metrics coverage; **rimer pilot → user gate**; `_release_v1` export |
| P2-V | V2 reviewer | ⬜ pending | `wave_p2_6/V2_handoff.md` | refutation mandate; review → `.workspace_archive/reviews/<stamp>_lyrics-sources-p2-impl.md`; STATUS/CHANGELOG; `toolshop closeout` |

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
