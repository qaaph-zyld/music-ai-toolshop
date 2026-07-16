# Toolshop Portfolio Status Board

> Orchestrator-owned. Updated at each strategy review. Backlog of record: `specs/2026-07-15-longterm-roadmap-v2.md`.
> **Last review: 2026-07-17 (M1c-final closed)** — M1c-final consolidation complete: 6 commits pushed,
> repo clean, submodule committed, index rebuilt (385 unique songs), resume fix tested (11/11 green).
> T5-L1 plan ready: `plans/2026-07-17-t5l1-lyrics-db-foundation.md` — launches next.

## H1 Milestone Board

| Milestone | State | Notes |
|---|---|---|
| M1 CrhymeTV analyze-only | ✅ CLOSED 2026-07-16 | 221 completed + 1 skipped_long, 0 errors; catalogue `Tracks: 222`; advanced-backend incident caught & guarded |
| M1c-final consolidation | ✅ CLOSED 2026-07-17 | 6 commits (ec42fb5..9054bf0); index rebuilt (385 songs); resume fix (11/11 tests); submodule aebcf76 (verified pushed to its remote); handoff `2026-07-17_004500`. **Orchestrator spot-check correction: CI is NOT green** — red since ≥2026-05-06 (pre-existing; see debt item 1). |
| M2 Demucs e2e + model mirror | ⏸ Ready, gated on M1c-final | Plan + prompt embedded |
| M3 Stems CPU optimization | ⬜ Not started | Needs museval eval-harness seed first (integration map §4) |
| M4 Mastering german_drill e2e | ⏸ Ready (unblocked) | Submodule committed (aebcf76); pointer bumped |
| M5 Suite reorg + meta-layer registration | ⬜ Not started | AGENTS.md exists; project not yet in framework project table |
| M6 Backups + doctor disk/backup checks | ⬜ Not started — **PRIORITY RAISED** | Irreplaceable assets now exist: 222-track dossier catalogue, 386-song lyrics corpus, API tokens. Currently ZERO backups. |

## Tool Lanes

| Lane | State | Next meaningful step |
|---|---|---|
| T1 Stems | v0.4 shipped; idle | M2 (models+mirror), then M3 (CPU opt) |
| T2 Dossier/RE | v1 live; **222-track catalogue is the first cross-tool asset** | H2 (Dossier v2) after H1 |
| T3 Mastering | Working daily product; submodule clean (aebcf76) | M4 verification |
| T4 Vocal Lab | Shipped detectors/cleaning; idle | H2 (faster-whisper) |
| T5 Library Intelligence | Assets growing fast: CrhymeTV catalogue + **386-song Buba/Jala/Coby lyrics corpus** (verified on disk 2026-07-17) | **L1 NEXT** — `plans/2026-07-17-t5l1-lyrics-db-foundation.md` (lyrics.db + syllables + baseline stats), gate open; strategy: `specs/2026-07-17-lyric-intelligence-strategy.md` L1–L6 |
| T6 Creation Bridge | Corpus = fuel for briefs/rhyme work | Consumes Lyric Intelligence outputs: rimer DB, brief generator, draft scorer (L5) |
| T7 Sample Forge | — | H3 |
| Parked | open_DAW, Voicebox, ACE-Step local | No investment (roadmap §6) |

## Debt Register (after M1c-final: items 2–6 cleared)

1. ~10 `test_cleaning_pipeline.py` numpy-scalar failures → dedicated mini-session (post-M2). **This is
   what keeps CI red** (workflow runs `pytest tests -m "not slow"`; every visible run since 2026-05-06
   failed) — fixing it flips the badge green, raising its value.
1b. Index paths written absolute (`D:\MusicData\...`) instead of genius-root-relative as specified —
   works today, breaks on any future move. One-line fix; fold into next extractor-touching session.
2. ~~Uncommitted work wave~~ → ✅ cleared (5 commits + plan tick)
3. ~~Resume-status bug~~ → ✅ cleared (11/11 tests green)
4. ~~Extractor index bugs~~ → ✅ cleared (385 entries, 8 rebuild tests)
5. ~~Mastering submodule uncommitted~~ → ✅ cleared (aebcf76)
6. ~~PROJECTS_INDEX stale~~ → ✅ cleared (lyrics lane added)
7. No backups of MusicData/catalogues/tokens → M6

## Recommended Sequence (next ~6 sessions)

1. **T5-L1 lyrics.db foundation** (NEXT — plan ready: `plans/2026-07-17-t5l1-lyrics-db-foundation.md`; gate open)
2. **M6 backups** (small session; assets are now worth protecting)
3. **M2** Demucs/models · then **M4** mastering e2e (independent, any evening)
4. **T5-L2 rhyme miner** (after L1 handoff passes review)
5. **Test-debt mini** (numpy failures)
6. **M3** CPU optimization (with museval seed) → closes H1 → **H2 Dossier v2 begins**

## Standing Observations (orchestrator)

- Coder sessions deliver strong evidence but drift on close-out discipline (commits/CHANGELOG deferred
  3× now). Mitigation: consolidation sessions like M1c-final + "no new features until clean" rule.
- **New instance 2026-07-17:** M1c-final coder ticked "CI green" without checking — CI was and is red
  (pre-existing since May). Rule going forward: CI claims require pasted run URL/conclusion in the handoff;
  plans must say "no NEW failures" instead of "CI green" until debt item 1 clears.
- Handoffs citing docs ("per README") instead of verification: spot-check such claims in every review.
- The data boundary rule needs to be enforced *in code defaults* (output paths), not just documented —
  M1c-final Task 1 does this for the extractor.
