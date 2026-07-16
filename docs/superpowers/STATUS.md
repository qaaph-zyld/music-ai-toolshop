# Toolshop Portfolio Status Board

> Orchestrator-owned. Updated at each strategy review. Backlog of record: `specs/2026-07-15-longterm-roadmap-v2.md`.
> **Last review: 2026-07-17** — corpus re-verified: **386 unique songs** on disk (415 was index
> inflation from the known dedup bug); index paths stale after the MusicData move (noted in M1c plan);
> T5-L1 plan finalized: `plans/2026-07-17-t5l1-lyrics-db-foundation.md`.

## H1 Milestone Board

| Milestone | State | Notes |
|---|---|---|
| M1 CrhymeTV analyze-only | ✅ CLOSED 2026-07-16 | 221 completed + 1 skipped_long, 0 errors; catalogue `Tracks: 222`; advanced-backend incident caught & guarded |
| M1c-final consolidation | 🔴 **NEXT SESSION** | Revised plan `plans/2026-07-16-h1m1c-cleanup-genius-run.md`: commit debt (3 sessions old), lyrics data boundary, extractor index bugs, resume fix, submodule hygiene |
| M2 Demucs e2e + model mirror | ⏸ Ready, gated on M1c-final | Plan + prompt embedded |
| M3 Stems CPU optimization | ⬜ Not started | Needs museval eval-harness seed first (integration map §4) |
| M4 Mastering german_drill e2e | ⏸ Ready, gated on M1c-final Task 4 | Submodule must be committed first |
| M5 Suite reorg + meta-layer registration | ⬜ Not started | AGENTS.md exists; project not yet in framework project table |
| M6 Backups + doctor disk/backup checks | ⬜ Not started — **PRIORITY RAISED** | Irreplaceable assets now exist: 222-track dossier catalogue, 415-song lyrics corpus, API tokens. Currently ZERO backups. |

## Tool Lanes

| Lane | State | Next meaningful step |
|---|---|---|
| T1 Stems | v0.4 shipped; idle | M2 (models+mirror), then M3 (CPU opt) |
| T2 Dossier/RE | v1 live; **222-track catalogue is the first cross-tool asset** | H2 (Dossier v2) after H1 |
| T3 Mastering | Working daily product; dirty submodule | M1c-final Task 4 → M4 verification |
| T4 Vocal Lab | Shipped detectors/cleaning; idle | H2 (faster-whisper) |
| T5 Library Intelligence | Assets growing fast: CrhymeTV catalogue + **386-song Buba/Jala/Coby lyrics corpus** (verified on disk 2026-07-17) | **L1 plan READY** — `plans/2026-07-17-t5l1-lyrics-db-foundation.md` (lyrics.db + syllables + baseline stats), gated on M1c-final; strategy: `specs/2026-07-17-lyric-intelligence-strategy.md` L1–L6 |
| T6 Creation Bridge | Corpus = fuel for briefs/rhyme work | Consumes Lyric Intelligence outputs: rimer DB, brief generator, draft scorer (L5) |
| T7 Sample Forge | — | H3 |
| Parked | open_DAW, Voicebox, ACE-Step local | No investment (roadmap §6) |

## Debt Register (after M1c-final should shrink to item 1)

1. ~10 `test_cleaning_pipeline.py` numpy-scalar failures → dedicated mini-session (post-M2)
2. Uncommitted work wave (genius code, cli/pyproject mods, plans, junk files) → M1c-final Task 5
3. Resume-status bug (skipped_long/failed lost on resume) → M1c-final Task 3
4. Extractor index bugs (duplicate counting, empty `file` fields, other-collab=0) → M1c-final Task 2
5. Mastering submodule uncommitted CRLF/path fixes → M1c-final Task 4
6. PROJECTS_INDEX stale (no lyrics lane) → M1c-final Task 5
7. No backups of MusicData/catalogues/tokens → M6

## Recommended Sequence (next ~6 sessions)

1. **M1c-final** (consolidation — everything gates on this)
2. **M6 backups** (small session; assets are now worth protecting)
3. **M2** Demucs/models · then **M4** mastering e2e (independent, any evening)
4. **T5-L1 lyrics.db foundation** (plan ready: `plans/2026-07-17-t5l1-lyrics-db-foundation.md` — this IS the lyrics quick win, now specced)
5. **Test-debt mini** (numpy failures)
6. **M3** CPU optimization (with museval seed) → closes H1 → **H2 Dossier v2 begins**

## Standing Observations (orchestrator)

- Coder sessions deliver strong evidence but drift on close-out discipline (commits/CHANGELOG deferred
  3× now). Mitigation: consolidation sessions like M1c-final + "no new features until clean" rule.
- Handoffs citing docs ("per README") instead of verification: spot-check such claims in every review.
- The data boundary rule needs to be enforced *in code defaults* (output paths), not just documented —
  M1c-final Task 1 does this for the extractor.
