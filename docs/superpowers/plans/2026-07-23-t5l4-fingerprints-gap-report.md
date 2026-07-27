# T5-L4 — Pro Fingerprints + Suno Gap Report

**Date:** 2026-07-23 · **Author:** orchestrator · **Size:** 1–2 sessions (Part A = 1; Part B gated)
**Parent:** `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md` §L4 · Strategy:
`specs/2026-07-17-lyric-intelligence-strategy.md` (Success Criteria #1 and #2)
**Gate state:** L2.1 VERIFIED (#020/#023) + L3 VERIFIED (#024) — L4 is legitimately open.

**Standing context (do not re-derive):**
- lyrics.db (`D:\MusicData\toolshop\lyrics\lyrics.db`): 742 songs / 5,493 sections / 36,572 lines;
  `song_metrics`, `song_rhyme_metrics` (RF/%multis/internal/scheme/top vowel pairs, 159,171
  line_rhymes), `tokens` 282,426 + `entities` 6,708 (CLASSLA), `slang_terms` 6,984,
  `topics` 84 + `section_topics` 2,283 (BERTopic), cohorts `drill_trap` (387 solo) / `pop` (214).
- Verified reference numbers: pop RF median 0.7399 > drill 0.5628 (Cohen's d≈1.18); JSD(drill‖pop
  themes) = 0.2015.
- **Orchestrator caveat (from #024 review):** `slang_terms` is cohort-distinctive VOCABULARY, not
  strictly slang — top entries mix true slang (drip, swag) with common words (ljude, ikad, mirna).
  Fingerprints must filter/re-rank before presenting terms (see Task A2).
- CI billing-locked → gate is local `pytest -m "not slow"`, "no NEW failures" vs your recorded
  baseline. Close-out is MECHANICAL: `toolshop closeout` must exit 0; paste its evidence block.
- Data boundary: no lyric text in reports or repo — statistics and single-word vocabulary items
  only (established L1–L3 convention).

---

## PART A — Per-artist pro fingerprints (UNBLOCKED; do first)

### Task A1 — Fingerprint builder (TDD)
New module `toolshop/fingerprint.py` + CLI verb (`toolshop lyrics fingerprint` or consistent with
existing lyrics CLI surface — follow whatever pattern `l3_report.py` established). For a given
artist (8 targets) and cohort rollup, aggregate FROM PERSISTED DATA ONLY (no recomputation of
rhymes/topics):
- **Rhyme craft:** rhyme_factor (median + IQR), %multis, internal-rhyme rate, dominant schemes,
  top vowel pairs (from `song_rhyme_metrics`).
- **Structure:** section-type distribution, avg sections/song, avg lines/section, refren share,
  hook repetition proxy (refren line-repetition within song).
- **Lexical:** TTR (from `song_metrics`), syllables/line distribution, distinctive-vocabulary
  top-20 — **filtered**: exclude UPOS in {PRON, DET, ADP, CCONJ, SCONJ, AUX, PART} and
  frequency-rank the remainder; label the column "distinctive vocabulary" NOT "slang".
- **Content:** top entities (PER/LOC/ORG separated), top-5 topics with shares.
- Return a dict; renderer separate (A2). Tests: mocked/fixture DB, one golden-artist snapshot.

### Task A2 — Render `lyrics_research/reports/pro_fingerprints.md`
One page per artist (8) + one per cohort (2): the aggregates above, formatted; each page carries
2–3 sentence orchestrator-readable "craft profile" AUTO-DERIVED from the numbers (e.g. "densest
multis in cohort; hook-heavy structure") — rule-based phrasing, no LLM in the loop. Statistics
only; no lyric lines.

### Task A3 — Sanity gate for Part A
Cross-check 3 spot values in the rendered report against direct SQL (e.g. Jala RF median,
Senidah top topic share, Buba %multis) — paste the SQL + values in the handoff. Report must
reproduce the verified L2.1/L3 reference numbers where they overlap.

## PART B — Suno ingestion + gap report (GATED on data location)

**BLOCKER (orchestrator search 2026-07-23):** the 2,633-song Suno library
(`suno_library.db` + per-clip `*_metadata.json` per `toolshop/suno_adapter.py` conventions) was
NOT FOUND on this machine: absent from the repo `projects/` tree, `D:\MusicData`, shallow C:
search; the PC-wide catalogue (88k files) has zero "suno" paths. Likely on another fleet machine
or an unindexed location. **[USER INPUT] required: the library's actual path.** If the task
message does not provide it, DELIVER PART A ONLY and write in the handoff exactly what Part B
needs staged (expected layout, size estimate, where to copy it under `D:\MusicData\toolshop\`).

### Task B1 — Schema: source dimension (migration + regression guard)
Add `songs.source TEXT NOT NULL DEFAULT 'pro'` (values: `pro` | `suno`) via idempotent migration.
REGRESSION GUARD: capture pre-migration baseline (artist stats, RF medians, counts) and prove
identical post-migration; all existing views/queries stay pro-only by default (filter
`source='pro'` where aggregation would mix). Suno-specific metadata (style prompt, model tag,
created date) → new `suno_songs` side table keyed on song_id.

### Task B2 — Suno ingest + metrics batch (resumable)
Ingest Suno lyrics through the IDENTICAL normalization path (ASCII-fold, section parser, syllable
counter) with `source='suno'`. Then compute per-song: song_metrics, rhyme metrics (existing
miner). **Language triage first:** detect language per song (cheap heuristic or langdetect);
gap comparison is Serbian-vs-Serbian — non-Serbian songs get ingested but flagged
(`suno_songs.lang`) and excluded from cohort comparisons; report the language mix as a finding.
**Scope control:** NO CLASSLA annotation and NO slang mining for Suno in this phase (CPU cost);
themes via EXISTING BERTopic model `.transform()` only (no refit). Batch resumable with status
JSON; measure and record min/100-songs.

### Task B3 — `lyrics_research/reports/gap_report.md`
Per target cohort (drill_trap, pop): Suno-corpus distribution vs pro distribution on rhyme_factor,
%multis, internal rate, syllables/line, TTR, hook repetition, section structure, theme mix
(JSD Suno‖cohort). Deltas with effect direction and size. **Exit requirement (Success Criterion
#2): ≥3 concrete, MEASURED craft adjustments** phrased as actionable brief/writing rules (e.g.
"raise multi-syllabic share from X to cohort median Y"). Statistics only.

## Close-out (mechanical — applies to whichever parts ran)
1. CHANGELOG next Answer number; plan checkboxes ticked; STATUS T5 row NOT edited (orchestrator
   owns the board — report, don't self-mark).
2. Local pytest: no NEW failures vs recorded baseline (paste tail).
3. Commit in logical units; push; `toolshop closeout` exit 0 — paste evidence block.
4. Handoff to `D:\Projects\.windsurf\handoffs\` with: A3 sanity SQL + values, runtime
   measurements, Part B blocker status (what's still needed if skipped), deviations with reasons.

## Out of scope
- No L5 work (rimer/brief/scorer), no flow analyzer, no T8/T9 lanes, no new deps beyond an
  optional language detector (ledger it if added), no BERTopic refit, no CLASSLA on Suno corpus,
  no edits to verified L2/L3 pipeline code.
