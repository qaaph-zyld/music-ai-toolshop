# Toolshop Portfolio Status Board

> Orchestrator-owned. Updated at each strategy review. Backlog of record: `specs/2026-07-15-longterm-roadmap-v2.md`;
> 12-month vision layer above it: `specs/2026-07-22-longterm-goals-12mo-full-studio.md` (v1.0).
>
> **Last review: 2026-07-23 (T5-L3 INDEPENDENT VERIFICATION — VERIFIED PASS · #024).**
> All #021 claims independently reproduced from `lyrics.db`: annotation coverage 36,572/36,572
> lines (100%), 282,426 tokens, 6,708 entities — all match. Slang: 6,984 terms, 2,421 drill / 1,741
> pop distinctive, distinctiveness recompute max diff 0.0000 (10-term sample, seed=42). Themes: 84
> topics, 2,283 section_topics, JSD=0.2015 reproduces exactly. Gate: all three conditions PASS
> (slang + strong slang + theme discrimination). Direction consistent with L2.1 (different dominant
> topics, 2/5 overlap in top-5). Report: `lyrics_research/reports/2026-07-23_l3-verification.md`.
> **#021 is now REVIEW-CLEARED.** L4 (fingerprints + gap report vs 2,633 Suno lyrics) is unblocked.
>
> **Prior review: 2026-07-23 (Q1-S0 HYGIENE + CLOSE-OUT GATE — VERIFIED PASS · #023).**
> Orchestrator re-ran everything independently: pytest **429/0** (matches handoff), `toolshop
> closeout` **exit 0 PASS**, origin sync empty, `core.hooksPath=hooks` + doctor OK, `.gitignore`
> globs live, docs wave on origin. The close-out gate is now MECHANICAL (CLI verb + tracked
> pre-push hook + doctor check). First fully honest handoff in the sequence — deviations
> documented, wrong-approach config hack self-corrected and disclosed. **Q1 step 0 DONE.**
> Mystery explained: the plan's premises (3 unpushed commits, 12 junk files) had been consumed by
> a **6th out-of-band L3 session** (`7a93ad7`/`de2a528`/`2893394`, #021 claims "L3 discrimination
> gate PASS") which pushed + cleaned before Q1-S0 ran — benign this time, but **#021 is
> UNREVIEWED → next session = L3 spot-check (Q1 item 1)**. Pending orchestrator decisions
> (root-clutter audit, handoff §6): tracked one-off scripts (`diagnose_voice_analysis.py`,
> `check_batch_status.py`, `recover_batch_status.py`, `generate_crhymetv_catalogue.py`,
> `run_papapedro_pilot.*`) + `.coverage` tracked-though-ignored → keep / scripts-dir / git-rm at
> next consolidation. Minor debt: closeout docstring claims a pointer-on-remote check the code
> doesn't implement; doctor overall FAIL = pre-existing model_cache gap (M2 scope).
>
> **Last review: 2026-07-22 evening (FULL-STUDIO MANDATE adopted + landscape research received).**
> User widened scope to a complete studio toolkit (goals G1–G10, quarters Q1–Q4): new lanes =
> composition/MIDI, synthesis palette, mixing chains, vocal correction; **3-machine fleet**
> (2× i7-4770-class + 1× i5 9th-gen, all 16 GB) enables batch grid + TRUE cross-machine DR;
> stronger machines later → GPU shelf maintained with specs. Research report:
> `research/2026-07-22-full-studio-oss-landscape.md` — verdicts folded into goals §8 as `likely`
> (evidence bar unmet; re-verify at adoption). **Key alerts from the report:**
> (1) pedalboard **VST3-effects-render-dry bug (PR #476, open)** → mandatory test gate in E2;
> (2) sfizz ARCHIVED → FluidSynth is the durable SF2/SFZ path; (3) LSP Windows builds will be
> PAID → free mixing-suite question still open (goals §8.3); (4) `.als` generation has real prior
> art (ableton-set-builder, als-wire, ableton-project-processor) → **E6 substantially de-risked**;
> (5) GPU shelf is cheap now — ACE-Step v1.5 (MIT, SOTA) needs <4 GB offloaded; one used 8–12 GB
> card unlocks nearly everything (G9 spec target). **Discipline flag: 3 L3 commits UNPUSHED
> (`2318878..6f44a3c`) + 12 junk `pytest_*.txt` in repo root — push + cleanup precedes any new lane.**
>
> **Addendum same evening: gap-fill research received + verified** (`research/2026-07-22-gapfill-report.md`
> — this one MET the evidence bar; verdicts folded into goals §8.3). Mixing-suite question RESOLVED:
> Airwindows Consolidated (MIT) + ZL EQ2/Compressor (AGPL) + Dragonfly Reverb (GPL) for free Windows
> VST3. Phantom (`phantom-audio`) = stem-masking analysis INTEGRATE candidate for T8/E-lane.
> Confirmed real gaps: no OSS auto-mixing (diagnose-and-suggest only), no OSS VocAlign-style
> time-warping. Composition v0 stack fully specified (MusicLang + mido/pretty_midi + drum gens +
> FluidSynth/sforzando; miditoolkit SKIP-stale). CC0-first instrument content sourced (VCSL,
> Meadowlark, TR808-fischer, GareBear99 808s). AbletonOSC INTEGRATE (slow but only bridge);
> FL = still a poor generation target → D1 stands. All research now CLOSED except
> groove-extraction prior art (rhythm-lane fold-in).
>
> **Prior review: 2026-07-22 (T5-L2.1 INDEPENDENT VERIFICATION — PASS).** All four verification tasks
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
| T5 Library Intelligence | lyrics.db over **742 songs**; L1.1 + **L2.1 VERIFIED PASS** (independent re-run 2026-07-22, report: `lyrics_research/reports/2026-07-22_l2-1-verification.md`); Cohen's d=1.18, persisted==engine to 0.000000; **L3 VERIFIED PASS** (independent re-run 2026-07-23, report: `lyrics_research/reports/2026-07-23_l3-verification.md`); JSD=0.2015, slang distinctiveness reproduces to 0.0000, 84 topics, 6,708 entities; roadmap `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md` | **L4 NEXT** — fingerprints + gap report on the 2,633 Suno lyrics. #021 review-cleared. |
| T6 Creation Bridge | Corpus = fuel for briefs/rhyme work | Consumes Lyric Intelligence outputs: rimer DB, brief generator, draft scorer (L5) |
| T7 Sample Forge | v1 partial: section-consuming forge + spec-aligned naming shipped; auto-detection deferred to H2 structure detector | H2: automatic section detection; H3: its pedalboard pick promoted to core chains (E2) |
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

## Recommended Sequence — Q1 (Aug–Oct 2026, per goals v1.0 §6)

0. ~~Hygiene FIRST~~ → ✅ **DONE, VERIFIED 2026-07-23** (#022/#023): pushed, junk globs live,
   `toolshop closeout` + pre-push hook + doctor check mechanical
1. ~~**T5-L3 SPOT-CHECK**~~ → ✅ **DONE, VERIFIED 2026-07-23** (#024): all #021 claims reproduced
   from lyrics.db — annotation, slang, themes, JSD, gate all match → then **L4** fingerprints + gap
   report vs the 2,633 Suno lyrics
2. **H1 close:** M2 Demucs e2e · M4 mastering e2e (any evening) · M3 CPU opt (+ museval seed) · M5 reorg
3. **E1 restore diagnose** (plan ready) → **E2 chains core** (⚠ include PR#476 VST3 dry-render test
   gate) → **E3 treat v1**
4. **H2 Dossier v2** milestone chain (K-S key, structure, beats, chords, faster-whisper lyrics)
5. **Fleet pilot (new, G5):** 2-machine shared-folder/SQLite job-queue pilot on the existing batch
   engine + Syncthing/rclone sync + **first true cross-machine backup** (kills the same-box DR caveat)
6. **New-lane opener (research-gated, last):** composition/MIDI v0 — MusicLang + drum-gen +
   wobblemidi + FluidSynth render path (goals §8.1); residual research items per goals §8.3

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
