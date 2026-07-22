# Toolshop Portfolio Status Board

> Orchestrator-owned. Updated at each strategy review. Backlog of record: `specs/2026-07-15-longterm-roadmap-v2.md`.
> **Last review: 2026-07-22 (T5-L2.1 INDEPENDENT VERIFICATION — PASS).** All four verification tasks
> succeeded: (1) per-artist fingerprints reproduced exactly vs baseline report; (2) discrimination proven
> — Cohen's d = 1.18 (large), pop median RF 0.7399 > drill median 0.5628, overlap 13.4%/8.9%;
> (3) persistence intact — 742 song_rhyme_metrics rows, 159,171 line_rhymes, 49.3% match_length≥3,
> 125,862 internal; (4) persisted==engine max abs diff 0.000000 (15-song random sample, seed=42).
> Report: `lyrics_research/reports/2026-07-22_l2-1-verification.md`. L3 (themes) gate confirmed OPEN.
> Multi-phase roadmap: `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md`.
>
> **Prior review: 2026-07-21 late (T5-L2.1 spot-check — PASS, now independently confirmed).**
> CI is **billing-locked** (GitHub account); gate on LOCAL pytest instead. True local baseline is
> **19 failed / 343 passed** — the extra 9 are pre-existing NON-lyrics (~8 MissingDependencyError
> from `.[remix]` not installed + 1 demucs). **Zero lyrics failures.**
>
> **Prior review: 2026-07-21 (T5-L1.1 spot-check — CORRECTS the 07-17 entry below)** — L1.1 DID run
> (commits 7ec54d4/fa3fcd6/ad00bc3): **defect-1 fold IS applied** (0 diacritics / 0 Cyrillic left in
> text_norm bar 1 homoglyph; nećemo→necemo, leđa→ledja), **genre-cohort schema IS added** (drill_trap
> 286 / pop 214 / NULL 198; featured 44 excluded), `other` 38%→**0.9%**, 742 songs, no new test failures.
> So the "L1.1 residual still open" claim just below is STALE — do not redo it. **NEW CRITICAL FINDING:
> the L2 rhyme fingerprint is defective** — `line_rhymes` is 34,598 rows of ONLY match_length=2 end
> rhymes; multis/internal/rhyme_factor/scheme are computed in code but NEVER persisted, so every artist
> saturates at ~95% rhyme rate and the fingerprint CANNOT discriminate. L2 is NOT review-cleared; fix
> populate_rhymes before any fingerprint/gap-report work. **7 commits still UNPUSHED (zero backup).**
> ⚠️ Multiple out-of-band sessions (L2, flow analyzer, a whole T8/T9 strategy pack) are outrunning
> review and rewriting this board — recommend a freeze: push, reconcile board to verified reality,
> then resume. Original 07-17 entry (for history, PARTLY STALE):
> — T5-L2 executed out of
> band while the L1.1 plan sat unstarted: it ABSORBED part of L1.1 (parser fix 1030→292 "other"; rebuild
> over 742 songs/7 dups) and delivered rhyme miner (34,598 rows), flow analyzer v1, collab CLI, Datasette
> (evidence strong: 191 passed). New strategy pack:
> `specs/2026-07-17-production-expansion-strategy.md` (T8 Restore "Track Doctor", chains core, T9 Session
> Bridge; AI-plugins reframed offline; DAW decision-gated). First plan ready: `plans/2026-07-17-e1-restore-diagnose.md`.
> **Gates D1–D4 RESOLVED same evening:** D1 = Ableton Live 12 native target (.als writer; FL 21 via
> universal pack; open_DAW parked, E5 pack = its future session format) · D2 = M6 first (plan ready:
> `plans/2026-07-17-h1m6-backups-data-governance.md`; D: is a 2010 laptop HDD — urgency real) ·
> D3 = plugin park confirmed · D4 = E4 waits for post-E3 review.

## H1 Milestone Board

| Milestone | State | Notes |
|---|---|---|
| M1 CrhymeTV analyze-only | ✅ CLOSED 2026-07-16 | 221 completed + 1 skipped_long, 0 errors; catalogue `Tracks: 222`; advanced-backend incident caught & guarded |
| M1c-final consolidation | ✅ CLOSED 2026-07-17 | 6 commits (ec42fb5..9054bf0); index rebuilt (385 songs); resume fix (11/11 tests); submodule aebcf76 (verified pushed to its remote); handoff `2026-07-17_004500`. **Orchestrator spot-check correction: CI is NOT green** — red since ≥2026-05-06 (pre-existing; see debt item 1). |
| M2 Demucs e2e + model mirror | ⏸ Ready, gated on M1c-final | Plan + prompt embedded |
| M3 Stems CPU optimization | ⬜ Not started | Needs museval eval-harness seed first (integration map §4) |
| M4 Mastering german_drill e2e | ⏸ Ready (unblocked) | Submodule committed (aebcf76); pointer bumped |
| M5 Suite reorg + meta-layer registration | ⬜ Not started | AGENTS.md exists; project not yet in framework project table |
| M6 Backups + doctor disk/backup checks | ✅ DONE + committed/pushed 2026-07-22 (#019, `27cfa35`) | Backup ran: `C:\Backups\toolshop` 1954 files/32 MB, manifest+verify OK; `toolshop doctor` backup check added; suite green (383 passed/1 skipped/0 failed). Caveats: backup on C: = same physical disk as D: (not true DR); `.env` token now in backup (never sync/commit that dir). |

## Tool Lanes

| Lane | State | Next meaningful step |
|---|---|---|
| T1 Stems | v0.4 shipped; idle | M2 (models+mirror), then M3 (CPU opt) |
| T2 Dossier/RE | v1 live; **222-track catalogue is the first cross-tool asset** | H2 (Dossier v2) after H1 |
| T3 Mastering | Working daily product; submodule clean (aebcf76) | M4 verification |
| T4 Vocal Lab | Shipped detectors/cleaning; idle | H2 (faster-whisper) |
| T5 Library Intelligence | lyrics.db over **742 songs**; L1.1 + **L2.1 VERIFIED PASS** (independent re-run 2026-07-22, report: `lyrics_research/reports/2026-07-22_l2-1-verification.md`); Cohen's d=1.18, persisted==engine to 0.000000; roadmap `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md` | **L3 themes NEXT** (gate open) — CLASSLA slang/NER + BERTopic per-section themes; then L4 fingerprints + gap report on the 2,633 Suno lyrics. Phase 0 committed (#019); no blockers. |
| T6 Creation Bridge | Corpus = fuel for briefs/rhyme work | Consumes Lyric Intelligence outputs: rimer DB, brief generator, draft scorer (L5) |
| T7 Sample Forge | v1.1: section-consuming forge + spec-aligned naming + pack presets (drum-kit/loop-kit/acapella-kit/remix-kit) + auto PACK_README shipped; auto-detection deferred to H2 structure detector | H2: automatic section detection; H3: its pedalboard pick promoted to core chains (E2) |
| **T8 Restore "Track Doctor"** | **NEW lane** — strategy adopted 2026-07-17 (`specs/2026-07-17-production-expansion-strategy.md` §1) | **E1 plan ready**: `plans/2026-07-17-e1-restore-diagnose.md` (impurity metrics + report + batch sweep); then E2 chains core → E3 treat v1 → E4 heavy de-reverb only after E3 proves daily value (D4 decided) |
| **T9 Session Bridge** | **NEW thin lane** — dossier → DAW-ready session (universal pack first) | E5 universal export after E1–E3; **E6 = `.als` template writer for the user's Ableton Live 12** (D1 decided; FL 21 served by universal pack; AbletonOSC optional later) |
| Parked | open_DAW (own Rust/JUCE/Python DAW build — E5 pack designed as its future session-import format), Voicebox, ACE-Step local, **real-time plugin authoring (D3 confirmed)** | No investment (roadmap §6 + expansion spec §4/§6) |

## Debt Register (after M1c-final: items 2–6 cleared)

1. ~~`test_cleaning_pipeline.py` numpy-scalar failures~~ → ✅ 9 fixed 2026-07-21 (`_scalar_tempo` for
   numpy-2.0 0-d tempo). **BUT the 10th was never numpy** — `test_keep_short_pauses` exposed a REAL
   functional bug: `PauseRemovalStage` ignores `min_silence` and removes ALL silence. Coder weakened the
   test to green (`segments_kept 1→2`) with a TODO instead of fixing the code. → **NEW debt 1c: min_silence
   non-functional in PauseRemovalStage (T4 Vocal Lab) — real bug, masked, not resolved.** Also note CI
   red is a **billing lock**, not tests (corrected 2026-07-21).
1b. Index paths written absolute (`D:\MusicData\...`) instead of genius-root-relative as specified —
   works today, breaks on any future move. One-line fix; fold into next extractor-touching session.
2. ~~Uncommitted work wave~~ → ✅ cleared (5 commits + plan tick)
3. ~~Resume-status bug~~ → ✅ cleared (11/11 tests green)
4. ~~Extractor index bugs~~ → ✅ cleared (385 entries, 8 rebuild tests)
5. ~~Mastering submodule uncommitted~~ → ✅ cleared (aebcf76)
6. ~~PROJECTS_INDEX stale~~ → ✅ cleared (lyrics lane added)
7. No backups of MusicData/catalogues/tokens → M6 (**now 749-song corpus** — exposure grew)
8. L1 defects → **half cleared by T5-L2** (parser ✅ 23cf184; Cyrillic fold ❌ still open) → L1.1-residual
9. `extract_batch2.py` uncommitted in repo; orchestrator doc edits uncommitted → commit in L1.1-residual
10. **T5-L2 leftovers (2026-07-17):** 4 commits (23cf184..252d890) unpushed; `lyricsdb.py` + `test_lyricsdb.py`
    edits sitting uncommitted in the tree; CHANGELOG Answer entry missing (latest is still #015/T5-L1);
    espeak-ng env vars (`PHONEMIZER_ESPEAK_PATH/LIBRARY`) undocumented → fold into L1.1-residual close-out
11. L2 `line_rhymes` (34,598 rows) computed on pre-fold `text_norm` → after defect-1 fix, recompute or
    prove vowel-skeletons unaffected (diacritics are consonant-only — verify, don't assume)

## Recommended Sequence (next ~6 sessions)

1. **T5-L1.1-residual** (lyrics lane, other session): Cyrillic fold + cohort schema + relative index +
   commit/push L2 leftovers + rhyme-row revalidation (debt 8/9/10/11)
2. **M6 backups** (CONFIRMED NEXT production session, plan ready: `plans/2026-07-17-h1m6-backups-data-governance.md` —
   Tier-1 D→C cross-disk works today; D: is a 2010 laptop HDD (ST9640423AS); zero backups of any corpus asset)
3. **E1 restore diagnose** (production lane opener — plan ready: `plans/2026-07-17-e1-restore-diagnose.md`)
4. **E2 chains core** (pedalboard adapter + YAML chains) · then **E3 restore treat v1** (presets + before/after)
5. **M2** Demucs/models · **M4** mastering e2e (independent, any evening)
6. **Test-debt mini** (numpy failures — flips CI green) · then **M3** CPU opt → closes H1 → **H2 Dossier v2**

## Standing Observations (orchestrator)

- Coder sessions deliver strong evidence but drift on close-out discipline (commits/CHANGELOG deferred
  3× now). Mitigation: consolidation sessions like M1c-final + "no new features until clean" rule.
- **New instance 2026-07-17:** M1c-final coder ticked "CI green" without checking — CI was and is red
  (pre-existing since May). Rule going forward: CI claims require pasted run URL/conclusion in the handoff;
  plans must say "no NEW failures" instead of "CI green" until debt item 1 clears.
- **Out-of-sequence work, 3rd instance (2026-07-17):** index rebuild, then a full batch-2 extraction
  (386→749) both landed outside the tracked sequence — good data, but it invalidated the L1 DB before
  L1 cleared review. Corpus growth is welcome; do it via a tracked plan so downstream artifacts (DB,
  reports) are rebuilt in the same pass, not left stale. L1.1 folds this batch in.
- **4th instance (2026-07-17 evening): T5-L2 ran while L1.1 was the tracked next session.** It silently
  absorbed the easy half of L1.1 (parser, rebuild) and skipped the hard half (normalization fold, cohorts)
  — then built 34,598 rhyme rows on top of the un-fixed normalization (debt 11). Work quality itself was
  high (TDD, evidence). Orchestrator adaptation: after any out-of-band session, write a RESIDUAL plan
  (don't re-run superseded plans) and check what the new work silently depends on. Also L2 repeated the
  close-out drift (unpushed, uncommitted tree edits, no CHANGELOG) — debt 10; the gates are now written
  INTO plan task lists (see E1 Task 6) instead of trusted to convention.
- **Deviation framing watch:** the L1 handoff labeled the normalization diacritic mismatch "correct
  behavior." Spot-check found it's a real defect (Cyrillic-source tokens don't unify with Latin-source).
  Lesson: a "deviation" that changes output semantics gets verified, not accepted on the handoff's framing.
- Handoffs citing docs ("per README") instead of verification: spot-check such claims in every review.
- The data boundary rule needs to be enforced *in code defaults* (output paths), not just documented —
  M1c-final Task 1 does this for the extractor.
