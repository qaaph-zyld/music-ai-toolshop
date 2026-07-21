# Lyric Intelligence — Multi-Phase Roadmap (post-L2.1)

> **Authored 2026-07-21** by orchestrator after T5-L2.1 passed spot-check. Parent spec:
> `specs/2026-07-17-lyric-intelligence-strategy.md`. This sequences the road from the now-verified
> foundation to the payoff (writing tools). **One tracked plan per phase; review gate between each;
> no out-of-band feature sprawl** (that pattern cost us a defective fingerprint that shipped unreviewed).

## Where we actually are (verified on disk 2026-07-21)

| Asset | State |
|---|---|
| Corpus | 742 songs, 8 target artists + guests, 2 cohorts (drill_trap 387 solo / pop 214), `D:\MusicData` |
| lyrics.db | songs/sections/lines/song_metrics/song_rhyme_metrics + line_rhymes (159k) + views |
| Normalization | Cyrillic/Latin unified (ASCII-fold); `other` sections 0.9% |
| Rhyme fingerprint | **Works & discriminates** — RF pop 0.70–0.76 > drill 0.51–0.66; multis/internal/scheme persisted |
| Syllables | counter with syllabic-r, 0 NULL |

**Verified craft signal already available:** per-artist rhyme_factor separates pop from drill and ranks
within-cohort (Jala densest-varied at 0.57; Buba lowest 0.51; Senidah/Nikolija densest overall 0.74–0.76).
This is the first real "learn from the pros" output — L4 turns it into per-artist fingerprint one-pagers.

## Phase 0 — Hygiene gate (small; do BEFORE or alongside L3)

The assets are now valuable and exposed; the test/CI picture is misreported. Close this so later phases
run on trustworthy ground.
- **M6 backups (RAISED PRIORITY):** 742-song corpus + lyrics.db + catalogue + API tokens have **zero
  backups**. One session: a backup target + `toolshop doctor` disk/backup check. Losing MusicData now =
  losing everything.
- **Test skip-guards:** ~8 `test_remix_adapter`/`test_cli_remix` failures are `MissingDependencyError`
  (`.[remix]`/pedalboard absent) — they should `pytest.importorskip`/skip, not fail. Fix so the suite
  reports true health (target: only the 10 numpy debt + 1 demucs remain, and triage those).
- **CI billing:** GitHub Actions is account-locked → CI cannot run. Decide: resolve billing, or make
  LOCAL `pytest -m "not slow"` the official gate and stop citing CI. Until resolved, every plan says
  "local pytest, no new failures" — never "CI green."
- **Numpy debt (10) + demucs (1):** schedule the long-deferred `test_cleaning_pipeline` fix; triage the
  demucs failure. Flips the real baseline to green-modulo-known.

## Phase L3 — Language & Themes (1–2 sessions) — GATE OPEN

Goal: add *what they rap about* and *how they use language* to the fingerprint.
- CLASSLA annotation (lemma/POS/NER tuned for non-standard internet Serbian) → slang lexicon via OOV
  mining; NER surfaces brands/places/names per artist.
- BERTopic + paraphrase-multilingual-MiniLM themes **per section** (sharper than per-song); per-artist
  and per-cohort theme mix; theme evolution over time.
- New deps: classla, bertopic, sentence-transformers, umap/hdbscan (all CPU, license-ledger entries).
- **Exit:** theme atlas + slang lexicon in lyrics.db; per-cohort theme contrast (does drill theme
  differently from pop?); statistics-only report. Runtime budget respected (CPU; batch, no LLM in loop).
- **Watch:** CLASSLA model download size vs the 41 GB disk (see [[pc-hardware-constraints]]); themes on
  742 songs × sections is the heaviest CPU job yet — time-box and checkpoint.

## Phase L4 — Fingerprints & Gap Report (1 session) — gated on L3

Goal: the deliverable a producer acts on.
- Per-artist one-page fingerprint (rhyme craft from L2 + structure from sections + lexical/NER + themes
  from L3), per cohort. This is Success Criterion #1 from the strategy spec.
- Run the **2,633 Suno lyrics** (own/AI baseline) through the same pipeline → first **gap report**:
  where your/Suno output falls short of each cohort (rhyme_factor, %multis, hook repetition, TTR, themes).
- **Exit:** `reports/pro_fingerprints.md` + `reports/gap_report.md`; ≥3 concrete measured craft
  adjustments (Success Criterion #2).

## Phase L5 — Apply: the writing tools (2 sessions) — gated on L4

Goal: turn knowledge into tools (the actual payoff for Nikola's pen).
- **Rimer DB:** attested pro rhyme pairs ranked by usage → feeds MAirina "Pro Rimer" PRD Phase 1;
  must beat the dictionary version (Success Criterion #3).
- **Brief generator:** structure + rhyme-scheme + theme targets from a chosen fingerprint, formatted
  for Suno.
- **Draft scorer CLI:** `toolshop lyrics score draft.txt --vs jala-brat` incl. **originality check**
  (n-gram overlap vs corpus — learn, never plagiarize).
- **Exit:** write ONE real song with the tools; A/B the fingerprint-built Suno brief vs a naive prompt,
  keep the comparison (Success Criterion #4).

## Phase L6 — Expand (later)

More regional artists; German corpus from the 222 CrhymeTV artists via the proven extractor +
phonemizer-de (German is NOT phonetic — needs real phonemization, unlike Serbian). Ties into the H3 flow
analyzer (whisperX word timings × beat grid) so text craft meets delivery craft. The out-of-band flow
analyzer v1 (commit d868f0d) lands here — review it when L6 opens, not before.

## Sequencing recommendation

1. **Phase 0 hygiene** (esp. M6 backups — do this next; it's one small session and the downside of
   skipping is catastrophic) — can run parallel to L3 planning.
2. **L3 themes** — the next lyric-analysis phase; gate is open.
3. **L4 fingerprints + gap report** — the "am I improving?" instrument.
4. **L5 apply** — rimer/brief/scorer; the tools you write with.
5. **L6 expand** — German + flow; absorbs the out-of-band flow analyzer.

Discipline note: each phase = one tracked plan file + bootstrap prompt + orchestrator spot-check of the
handoff before the next gate opens. No adopting new lanes (T8/T9 production-expansion pack) until L4
ships — finish the thread that's delivering craft value before starting new ones.
