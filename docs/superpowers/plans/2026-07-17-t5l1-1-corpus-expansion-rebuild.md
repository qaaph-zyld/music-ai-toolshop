# T5-L1.1 — Corpus Expansion + Normalization/Parser Fixes (rebuild over 749)

> **Authored 2026-07-17** by orchestrator after the T5-L1 spot-check + batch-2 extraction.
> Parent spec: `specs/2026-07-17-lyric-intelligence-strategy.md`. Supersedes the L1 DB snapshot.
> Obey `AGENTS.md`. Consolidation + fix pass — **no rhyme mining (that is L2)**.

## Why this session exists

1. **Corpus doubled out of band.** Batch 2 added 5 artists → **749 songs on disk** (was 386). The
   lyrics.db from L1 covers only 385 (**51% stale**). Every L1 stat/report describes half the corpus.
2. **Two L1 defects surfaced in the orchestrator spot-check** (L1 otherwise passed — see §"L1 verdict").
3. **User decision 2026-07-17:** the reference splits into **two explicit genre cohorts**
   (drill/trap vs pop) — needs a genre label per artist and cohort-aware reports.

### T5-L1 verdict (for the record) — CONDITIONAL PASS
Verified good: DB at `D:\MusicData\toolshop\lyrics\lyrics.db`; tables `songs`(385)/`sections`(2701)/
`lines`(19780)/`song_metrics`(385) + `v_artist_stats`; **0 NULL `syllable_count`**; cyrtranslit in
`lyrics` extra + license-ledger entry present; report is statistics-only; CI honestly reported
(same known 10 failures, run URL given); 80 new tests green; no lyric lines leaked to the repo.
Two defects (below) must be fixed before L2 builds token/section analysis on this data.

## Corpus facts (verified on disk 2026-07-17)

- **749 JSON songs** across 15 folders. Batch-1: buba-solo 75, coby-solo 82, jala-solo 201,
  jala-buba-duo 27, jala-buba-coby-trio 1. Batch-2 solo: corona 92, senidah 83, nikolija 71,
  relja 62, indodjija 9. Batch-2 featured: corona 23, senidah 7, nikolija 7, relja 5, indodjija 4.
- **`-featured` folders are folder≠author, always.** e.g. `corona-featured/amna-fantomi.json` has
  `primary_artist = "Amna"` (Corona only guests). The real primary artists there (Amna, Tanja Savić, …)
  are NOT study targets — the target artist appears only inside section performers.
- **Two fragmented indices:** `_index.json` (385, batch 1, absolute paths) + `_index_batch2.json`
  (363, batch 2). No cross-batch dedup was done. `extract_batch2.py` is uncommitted in the repo.
- Corrected total: **749**, not the handoff's "778" (that reused the inflated 415 batch-1 figure).

## Genre cohort mapping (user-editable — confirm by ear before committing)

| Artist (primary) | Cohort | Note |
|---|---|---|
| Buba Corelli, Jala Brat, Coby | `drill_trap` | original reference |
| Nikolija, Senidah, Relja | `pop` | pop / dance-pop / pop-rap |
| Corona, Indodjija | `pop` (PROVISIONAL) | **verify** — reassign to `drill_trap` if they rap |
| any primary from a `-featured` folder (Amna, Tanja Savić, …) | `NULL` | non-target; excluded from cohort baselines |

## Tasks

### Task 1: Fix script-unification normalization (TDD) — DEFECT 1
- [ ] Root cause: Latin source is diacritic-stripped ("izaci cu"), but `cyrtranslit.to_latin(sr)`
      emits diacritics for the 112 Cyrillic songs ("izaći ću") → **same word, two `text_norm` forms**,
      corrupting TTR/top-words for ~29% of batch-1 and all future token/rhyme matching.
- [ ] Fix: after transliteration, **ASCII-fold to match the stripped Latin corpus**
      (č→c, ć→c, š→s, ž→z, đ→dj) so both scripts unify DOWN. Keep `text_raw` verbatim; only `text_norm`
      folds. (Plan forbade diacritic *restoration*; folding is the consistent alternative. Serbian
      diacritics sit on consonants only → vowel skeletons for L2 are unaffected.)
- [ ] Regression test: Cyrillic `"Изаћи ћу"` and Latin `"Izaci cu"` → identical `text_norm`.

### Task 2: Expand section-label parser (TDD) — DEFECT 2
- [ ] L1 left **1030/2701 (38%) sections as `other`**; the top "other" labels are standard, not exotic:
      `Uvod`→intro, `Završetak`→outro, `Prelaz`→bridge, `Pred-Refren`/`Predrefren`/`Prerefren`→prerefren,
      `Refren:` (trailing colon / empty performer)→refren, `Refrain`→refren,
      `Post-Refren`/`Postrefren`/`Post-Chorus`→**new type `postrefren`**, `Izgovoreno`→**new type `spoken`**.
- [ ] Normalize label (strip trailing `:`, fold diacritics, collapse hyphen/space) BEFORE matching.
- [ ] Target: **`other` < 10%** of sections. Test table covers every variant above.

### Task 3: Genre-cohort + role schema
- [ ] `songs`: add `role TEXT` ({solo, featured} from folder suffix), `target_artist TEXT`
      (the folder's artist), `genre_cohort TEXT` ({drill_trap, pop, NULL}).
- [ ] `artists`/cohort mapping from the table above as an editable dict in code (single source).
- [ ] **`role='featured'` rows are EXCLUDED from per-artist and cohort baselines** (they're by
      non-target primaries; reserved for L4 guest-verse section attribution). Document this rule.

### Task 4: Unified loader over all 749
- [ ] Folders-as-truth over **all 15 folders** incl `-featured`. Regenerate ONE unified
      `_index.json` from disk with **basename-relative paths** (fixes carried debt 1b); retire/merge
      `_index_batch2.json`. NO re-fetch from Genius.
- [ ] **Cross-batch dedup** via normalized `(title, primary_artist)` (catches any batch-2 song that
      duplicates batch-1); log drops to `_dedup_log.json`.

### Task 5: Rebuild + cohort-aware report
- [ ] `toolshop lyrics build-db` over the full corpus; `stats` gains `--cohort {drill_trap,pop}`.
- [ ] Regenerate `lyrics_research/reports/2026-07-17_genius_corpus_baseline.md` (overwrite) with:
      corpus inventory (15 folders, role split), **two cohort tables** (drill/trap vs pop, per-artist
      within each), featured-song count shown separately and flagged excluded-from-baseline.
      Statistics only.

### Task 6: Deps, docs, commits, handoff
- [ ] **No new dependencies.** Commit `extract_batch2.py` (or gitignore it) — no more uncommitted scripts.
- [ ] CHANGELOG + PROJECTS_INDEX (749-song corrected count, 2 cohorts). STATUS board.
- [ ] Commits: (a) `fix(lyrics): unify Cyrillic/Latin normalization (ASCII-fold)`,
      (b) `fix(lyrics): expand section-label parser (<10% other)`,
      (c) `feat(lyrics): genre cohorts + role schema + unified 749 rebuild`,
      (d) `docs: changelog + index + status`. Push.
- [ ] **CI:** known-red baseline (numpy debt) — bar is NO NEW failures; paste run URL in handoff,
      never claim "green".
- [ ] Handoff `d:\Projects\.windsurf\handoffs\<ts>_music-ai-toolshop-t5l1-1.md`: ingest count vs 749,
      cross-batch dedup log, `other`-section % before/after, normalization regression evidence,
      per-cohort stats, commit hashes, CI URL, deviations.

## Verification checklist
- [ ] DB ingests **≈749 songs** minus any cross-batch dups (all skips explained); role/cohort populated
- [ ] `other` sections **< 10%**; normalization regression test green (Cyrillic == Latin `text_norm`)
- [ ] `stats --cohort drill_trap` and `--cohort pop` both render; featured songs excluded from baselines
- [ ] No new CI failures vs the known 10 (run URL in handoff); repo clean; no lyric lines in repo
- [ ] Baseline report regenerated with two cohort tables

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "T5-L1.1: corpus expansion rebuild (normalization + parser fixes, genre cohorts, 749 songs)" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-17-t5l1-1-corpus-expansion-rebuild.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-17-t5l1-1-corpus-expansion-rebuild.md
exactly as written. Hard rules unchanged: lyrics.db + all derived data in D:\MusicData, never the repo;
synthetic test fixtures only; report is statistics-only; NO new dependencies; NO rhyme mining (that is L2);
NO re-fetch from Genius (rebuild indices from disk). TDD for the normalization fix and the section parser.
Confirm the genre-cohort mapping by ear before committing (reassign Corona/Indodjija if they rap). CI is
known-red (numpy debt): bar is NO NEW failures, paste the CI run URL in the handoff — never claim green.

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-t5l1-1.md
with ingest count reconciled against 749, cross-batch dedup evidence, other-section % before/after,
normalization regression proof, per-cohort stats, commit hashes, CI URL, deviations. After review, L2
(rhyme miner) is released — scoped to the drill/trap cohort first.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-17-t5l1-1-corpus-expansion-rebuild.md
```
