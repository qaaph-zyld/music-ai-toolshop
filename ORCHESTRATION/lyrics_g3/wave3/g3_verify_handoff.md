# G3 Wave-3 Verify Handoff — lyrics-g3

**Date:** 2026-10-07
**Verifier:** `reviewer` subagent 411921d3 + orchestrator follow-ups
**Verdict:** **VERIFIED** (minor items resolved by orchestrator; see below)

## Per-check results

| # | Check | Result |
|---|-------|--------|
| 1 | Wave handoffs + ledger claims | DB re-queries match wave-2 handoff exactly |
| 2 | NULL-cohort audit | **PASS** — all 261 genius-pro NULL cohorts are `role='featured'` (93 baseline + 168 new); zero NULL on solo rows |
| 3 | Misattribution | **PASS** — full pass, not samples: every `<artist>-solo` dir has a single `primary_artist` matching the roster artist |
| 4 | Cohort correctness | **PASS** — 8 drill_trap artists solo=drill_trap, 6 pop artists solo=pop; duo/trio dirs drill_trap (all drill_trap-roster combos); `target_artist` matches folder |
| 5 | Release-safety | **PASS** — `corpus='genius-pro' AND release_ok='yes'` = 0/2,531; new rows 25514–26619 all `license_tier='study-only'` + non-null `license_ref`; export path = `Genious_lyrics_extractor/export_release.py` selects only `release_ok IN ('yes','conditional')` and self-audits (`_audit_emit_plan` BLOCKER); `tests/test_export_release.py` 12/12 green incl. `test_v1_db_self_heals_and_emits_nothing_for_genius` |
| 6a | `test_lyrics_genius_roster.py` | **PASS** — 18/18 green (the "26 tests" figure in the session record was stale/miscounted; file has 18 `test_` defs, unmodified since 8a82573) |
| 6b | `-k lyrics` test subset | **PASS** — 561 passed, 2 skipped, 0 failed in 582s (initial reviewer poll stopped at 76% while still running; orchestrator collected the finished run) |
| 7 | Rimer counts | 370,116 pairs / 16,665 skeletons — source: wave-2 handoff, quoted from `build-rimer` output; reviewer did not independently re-query |

## Re-verified DB counts (read-only)

- genius-pro: 2,531 total = drill_trap 1,350 + pop 920 + featured-NULL 261
- New rows: ids 25514–26619 (1,106) = solo drill_trap 542 + solo pop 396 + featured NULL 168
- No rows older than id 25514 carry 2026-10-07 `ingested_at` — consistent with wave-2's 0/1,425 baseline diff
- Library-wide release_ok: yes 21,776 (pd/cc-by corpora), no 3,418 — genius-pro all `no`

## Notes for the record

- Cohort is tagged by `role`, not folder name: `*-featured` dirs on external primaries carry NULL (by design, matching the 93 baseline pattern); `*-duo`/`*-trio` dirs are `role='solo'`.
- `foreign_identifier` is NULL corpus-wide — dedup keyed on normalized (title, artist). Joins must use that key.
- Lacku `5446636` ("Tenzija" slug collision) remains an accepted 1-song gap — documented in wave-1 r2 handoff.
- Reviewer deleted its own scratch file; `.scratch/g3_v_lyrics_tests.log` retained (gitignored).

## Follow-ups

- [ ] Ledger rows G3-DB / G3-V flip to DONE at orchestrator commit time
- [ ] Adversarial review + user merge gate pending
- [ ] Lacku 5446636: accepted gap or targeted refetch (user decision or later lane)
