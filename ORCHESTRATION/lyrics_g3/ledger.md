# Orchestration ledger — lyrics-g3 (P3 genius-pro roster expansion)

Lane: `lyrics-g3` | Worktree: `Music-AI-Toolshop-wt-lyrics-g3` | Megaplan: `.workspace_archive/plans/lyrics-genius-expansion-megaplan.md`
GATE P3: approved 2026-10-06 — all roster artists with researched cohort tags.

| Wave | Status | Commit | Evidence |
|---|---|---|---|
| G3-pre | DONE | — | worktree at `44888ed`; ACTIVE override scoped to lane |
| G3-I | DONE | `1700720`, `8a82573` | `extract_roster.py` + `roster_g3.json` (16 artists, pinned ids) + `COHORT_MAP`/`_FOLDER_COHORT_MAP` + `tests/test_lyrics_genius_roster.py` — 18/18 green; `8a82573` fixed lyricsgenius 3.x `.id`→`_body` (corpus-wide `genius_song_id=null` bug) |
| Dry-run resolve | DONE | — | 14/16 clean OK; Fox+Zoi top-hit wrong → pinned ids (13438, 1584694); song-probe verified all pins |
| G3-B fetch | DONE | — | 16/16 artists done, clean exit 19:18 (`Summary saved`). 1152 status-attributed / 1139 unique files / 1134 distinct ids across 38 new dirs. Relaunches: ~01:35 bg exec (died ~02:14 host sleep); 18:18 detached `Start-Process` via `.scratch/run_fetch_g3.cmd` — survived to completion |
| Wave-1 re-audit | DONE | agent 5f48e82b | `wave1/g3_fetch_audit_handoff_r2.md` — **INGEST READY**: zero null ids, zero empty sections, no folder anomalies. Non-blocking: lacku id 5446636 lost to slug collision (1 song, "Tenzija"×2); 5 dup-id files across `-featured` dirs → dedup on `genius_song_id` |
| G3-DB ingest | DONE | agent 87958cc0 | `wave2/g3_db_ingest_handoff.md` — **INGEST CLEAN**: genius-pro 1,425→2,531 (+1,106 new; 28 already-present by key + 5 dup-ids reconcile vs 1,139 files); baseline diff 0/1,425 rows changed; drill_trap +542 / pop +396 / featured-NULL +168 (by design); all study-only/release_ok=no; rimer 358,862→370,116 pairs, 16,148→16,665 skeletons. Env note: exact cmd needed `PYTHONPATH=main-repo` (worktree submodules uninit; lane code still resolved for toolshop+COHORT_MAP) |
| G3-V review | DONE | agent 411921d3 | `wave3/g3_verify_handoff.md` — **VERIFIED**: 0 solo NULL cohorts; full-pass attribution clean; cohorts match roster; `release_ok='yes'` 0/2,531; roster tests 18/18; `-k lyrics` subset 561p/2s/0f (582s); `test_export_release.py` 12/12 incl. genius self-heal test |
| Adversarial review | DONE | agent c0eb047a | **MERGE-READY (conditional)** — no blockers. Known deltas to record: (1) full `--rebuild` would re-cohort 8 baseline rows (7 featured NULL→cohort, 1 drill→pop flip id 2220) — incremental ingest leaves baseline stale by design; (2) 2nd dedup loss: Lacku "Južni Vetar" id 11679713 collapsed vs baseline same-key row — total G3 loss = 2 songs (Tenzija slug collision + this); (3) index/DB source_path drift on 11 baseline songs (cosmetic); (4) substring fallback risk on short keys Fox/Zoi/Zera (future artists only, clean today); (5) silent slug overwrite in `save_song` — add id-suffix collision guard before future roster runs. Confirmed: 1,135 status ids fully accounted (1,117 indexed + 17 baseline-dup files + 1 missing) — no other silent losses |
| **MERGE** | DONE | — | user approved gate → `git merge --no-ff lyrics-g3` clean (ort, 13 files +1,400, 0 conflicts); Answer **#086** allocated (CHANGELOG + STATUS T5 + this row in allocation commit); db totals verified live post-merge: 25,194 total / genius-pro 2,531 / line_rhymes 4,441,081 / rhyme_pairs 370,116; lane `lyrics-g3` tip `e5e8daf` reachable from master — lane can be retired |

## Roster (FINAL — pinned)

See megaplan Roster table. 16 artists; all `genius_artist_id` pinned after
song-probe verification. `Bulevar` = YU new-wave band (id 369563, ~2 songs,
cohort provisional `pop`).

## /claude:orchestrate-waves dispatch wiring (commit 3c52e2f)

- Command already registered: `.claude/commands/orchestrate-waves.md` exists at workspace root; `.devin/config.json` has `read_config_from.claude=true` — resolves as `/claude:orchestrate-waves`. Mirrors: `.devin/workflows/orchestrate-waves.md`, `.windsurf/workflows/orchestrate-waves.md` (generated from `.windsurf/skills/orchestrate-waves/SKILL.md`).
- Missing link was lane-side: no `waves.json` existed. Created `ORCHESTRATION/lyrics_g3/waves.json` — 3 sequential waves (G3-fetch-audit gate, G3-db-ingest gate, G3-verify).
- Generated `prompts/subagent_dispatch.json` via `gen_orchestration_prompts.py --mode subagent`. Profiles resolved: wave-1 -> wave-explorer, wave-2 -> wave-implementer, wave-3 -> reviewer (explicit subagent_profile).
- Dispatched wave 1 (agent_id=63b0b646, background): fetch audit. Expected verdict FETCH INCOMPLETE since fetch still running (4/16 artists done in status, Crni Cerak resolving).
- Dispatch-failure fallback per command doc: orchestrator self-execution needs scoped `override:` in ACTIVE (marker currently absent); else paste mode.

## Wave-1 audit result (agent 63b0b646) + remediation

- Verdict FETCH INCOMPLETE + fetcher found DEAD (no extract_roster.py process; log stalled 82+ min at Crni Cerak banner).
- Reconciled: zera 21 / mimi 112 / surreal 88 / fox 174 = 391 files across 12 new G3 dirs; all clean (ids, primary_artist, sections).
- Flag: zera files have genius_song_id=null (pre-8a82573 artifact) — flipped zera status to pending so --resume refetches + overwrites with populated ids.
- Fetcher relaunched background (shell 4e9bf8) with --resume; re-audit (wave-1 rerun) when it completes, then wave-2 gate.
