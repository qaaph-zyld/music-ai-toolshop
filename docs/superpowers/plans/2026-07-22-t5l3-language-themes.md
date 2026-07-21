# T5-L3 — Language & Themes (CLASSLA annotation + slang lexicon + BERTopic)

> **Authored 2026-07-22** by orchestrator. Parent: `specs/2026-07-17-lyric-intelligence-strategy.md`
> (phase L3) and `plans/2026-07-21-lyric-intelligence-roadmap-L3-L6.md`. Obey `AGENTS.md`.
> **Adds *what they rap about* + *how they use language* to the fingerprint. No L4/L5 work
> (no gap report, no rimer/scorer) — those consume this.**

## PRECONDITION (verify first — STOP if unmet)
- **Phase 0 is DONE, committed + pushed** (verified 2026-07-22: commits `27cfa35` + reconcile `e293323`;
  origin 0/0). Its CHANGELOG entry is **#019** (renumbered from the earlier #018 collision with the
  Sample Forge series, which keeps #018). So the CHANGELOG through HEAD is: #016 Sample Forge, #017 L2.1,
  #018 T7.1 Sample Forge, #019 Phase 0. **L3 gets CHANGELOG #020.** Confirm `git status` is clean before
  starting; if the tree is dirty with unrelated work, STOP and report.
- lyrics.db present at `D:\MusicData\toolshop\lyrics\lyrics.db` (742 songs / 5,493 sections / 36,572
  lines / song_metrics + song_rhyme_metrics + line_rhymes — verified 2026-07-21).

## Verified facts (2026-07-22)
- Tables in `lyricsdb.py:367-449`: `songs, sections(type,type_number,label_raw,performers),
  lines(text_raw,text_norm,syllable_count), song_metrics, song_rhyme_metrics, line_rhymes`.
  View `v_artist_stats` is in `lyrics_metrics.py:166` (`_ARTIST_VIEW_SQL`), not `lyricsdb.py`.
- Section text = `lines.text_norm` for a `section_id`, ordered by `lines.ordinal`.
- Cohorts live on `songs.genre_cohort` ∈ {drill_trap(387 solo), pop(214 solo), NULL}; `role` ∈
  {solo, featured}. **Baselines use solo + a cohort; featured excluded** (same rule as L1.1/L2.1).
- Disk: D: 263 GB free (torch/CLASSLA models are NOT a constraint; the memory's "41 GB" was stale).
- CPU-only box (GT 640 unusable for ML) — everything here runs CPU; torch CPU wheel. See
  [[pc-hardware-constraints]].
- CLI pattern to extend: `toolshop lyrics <sub>` argparse subparsers in `cli.py:807`
  (`build-db`, `stats --cohort`, `rhymes`, `flow`, `collab`), all with a `--db` default to the
  MusicData path. Dispatch block is `cli.py:1520-1750`. New `annotate`/`lexicon`/`themes`
  subcommands follow the same subparser + dispatch pattern.

## Key design decision — which text feeds CLASSLA (name it, don't paper over it)
`text_norm` is ASCII-folded (č→c, đ→dj) → good for embeddings, **bad for CLASSLA** (its sr model expects
diacritics). `text_raw` keeps original script: Cyrillic for the 112 Cyrillic songs (CLASSLA handles
Cyrillic natively — full accuracy) and **diacritic-stripped Latin** for the rest (Genius stored it that
way; diacritic restoration was forbidden at L1). **Decision:** feed CLASSLA `text_raw`. Document that
the stripped-Latin majority caps lemma/POS/NER below CLASSLA's headline 97.9% — an accepted L3 ceiling,
not a bug. Embeddings (BERTopic) use `text_norm` (MiniLM is diacritic-robust).

## Dependencies (new `lyrics-nlp` extra — keep base `lyrics` light)
- `pyproject.toml`: add extra `lyrics-nlp = ["classla", "bertopic", "sentence-transformers",
  "umap-learn", "hdbscan", "torch"]`. Do NOT add to `lyrics` (build-db/stats/rhymes must stay
  installable without the heavy stack; CI installs `[audio,lyrics]` only). License-ledger entry per dep
  (integration-map policy).
- **torch CPU wheel:** `sentence-transformers` pulls torch transitively, but pip resolves the default
  CUDA wheel (~2.5 GB) on Windows. Install with:
  `pip install torch --index-url https://download.pytorch.org/whl/cpu`
  before installing the `lyrics-nlp` extra, or document this in the one-time setup instructions.
- Model/cache dirs (CLASSLA sr model ~few-hundred-MB; MiniLM ~90 MB) go to
  `D:\MusicData\toolshop\models\` (env `TOOLSHOP_DATA_DIR`-aware), **never the repo**. Document the
  one-time download.
- All L3 tests that import classla/bertopic/torch or need models → `pytest.importorskip` / skip-guard
  (same pattern Phase 0 established for remix), so they stay OUT of the default CI run.

## Task 1 — Schema for annotation + themes (`toolshop/lyricsdb.py`, TDD on schema/inserts)
Add tables (idempotent CREATE; wiped+rebuilt by the L3 commands, not by build-db):
- `tokens(id, line_id, ordinal, form, lemma, upos, feats, is_oov)` — CLASSLA per-token.
- `entities(id, song_id, section_id, line_id, text, ner_type)` — NER (brands/places/persons).
  `line_id` REFERENCES `lines(id)` ON DELETE CASCADE — NER spans are per-line (CLASSLA runs per-line),
  so line provenance must be preserved.
- `slang_terms(id, form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov)` — mined lexicon.
- `topics(topic_id, label, top_terms JSON, size, exemplar_section_id)` — BERTopic topics.
- `section_topics(section_id, topic_id, probability)` — per-section assignment.
Indexes on the FKs. TDD: a synthetic 2-song fixture inserts/reads back cleanly.

## Task 2 — CLASSLA annotation (`toolshop/annotate.py` + `toolshop lyrics annotate`)
- `toolshop lyrics annotate [--db PATH] [--resume] [--limit N]`: run
  `classla.Pipeline('sr', type='nonstandard')` over each line's `text_raw`; populate `tokens`
  (lemma/upos/feats) and `entities` (NER). The `nonstandard` pipeline type handles internet text
  spelling — critical for diacritic-stripped Latin. **Resumable** — skip lines already annotated
  (heaviest CPU job so far; time-box, checkpoint per song).
- Lazy-import classla inside the function (guarded). Print coverage summary (lines annotated, token
  count, %OOV, entity count).
- TDD: the line→CLASSLA-input adapter and the token-row builder (mock CLASSLA output); the live model
  call gets one skip-guarded integration test.

## Task 3 — Slang lexicon via OOV mining (`toolshop/lexicon.py` + `toolshop lyrics lexicon`)
- Mine `tokens.is_oov` (+ low-frequency-lemma heuristic) → `slang_terms`, with per-cohort frequency and
  a **distinctiveness** score (e.g. drill_freq vs pop_freq log-ratio). Solo songs only, cohort-scoped.
- `toolshop lyrics lexicon [--cohort] [--top N] [--json]`: ranked slang; and a drill-vs-pop
  distinctive-terms view.
- TDD: the OOV-selection + distinctiveness ranking on synthetic token tables (deterministic).

## Task 4 — BERTopic themes per section (`toolshop/themes.py` + `toolshop lyrics themes`)
- Assemble per-section docs from `text_norm` (skip sections < `--min-section-lines`, default 2, to cut
  noise). Embed with `paraphrase-multilingual-MiniLM-L12-v2`; fit ONE BERTopic model over ALL sections
  (so topics are comparable across cohorts); populate `topics` + `section_topics`.
- `toolshop lyrics themes [--db] [--min-section-lines N] [--seed 42]` (fix random_state/seed for
  reproducibility). Print topic count + size distribution.
- Aggregate per-artist and **per-cohort theme mix** (share of sections per topic).
- TDD: section-doc assembler + the per-cohort aggregation SQL (synthetic); the fit itself is a
  skip-guarded integration test (assert ≥1 topic on a tiny corpus).

## Task 5 — Report (`lyrics_research/reports/2026-07-22_language_themes.md`) — statistics only
- Slang lexicon: top drill-distinctive vs pop-distinctive terms (short, attributed at most; NO lyric
  dumps). Theme atlas: topic labels + top terms + per-cohort mix. Per-artist NER highlights
  (brands/places counts). Lemma/POS coverage + the diacritic-ceiling caveat stated plainly.

## HARD EXIT GATE — discrimination (mirrors L2.1; do NOT close without it)
The whole point is contrast. The report MUST show, with numbers:
1. **Themes discriminate:** drill_trap and pop have visibly different dominant topics (not the same
   topic mix). If every cohort maps to the same topics, the model isn't discriminating — retune
   (min_topic_size / min-section-lines) or explain, don't ship flat.
2. **Slang discriminates:** a non-trivial list of terms distinctive to drill vs pop (distinctiveness
   above a stated threshold).
3. Annotation coverage reported honestly (lemma/POS % on Cyrillic-source vs stripped-Latin, so the
   ceiling is visible).

## Task 6 — Deps, docs, commits, handoff
- License-ledger entries: classla, bertopic, sentence-transformers, umap-learn, hdbscan, torch.
- CHANGELOG **#020** (last used is #019 = Phase 0); PROJECTS_INDEX; STATUS T5 lane → L3 done, L4 next.
- Commits: (a) `feat(lyrics): annotation/themes schema`, (b) `feat(lyrics): CLASSLA annotate + entities`,
  (c) `feat(lyrics): slang lexicon (OOV + cohort distinctiveness)`, (d) `feat(lyrics): BERTopic themes
  + cohort mix`, (e) `docs: report + changelog + ledger`. Push.
- **CI reality:** account is billing-locked → Actions don't run; gate on LOCAL `pytest -m "not slow"`.
  **The invariant is 0 failed.** Passed/skipped counts vary by which optional extras are installed in the
  venv (observed 349–383 passed, 1–10 skipped, always 0 failed) — do NOT treat a specific passed count as
  the bar; the bar is "0 failed, and NLP tests skip when `lyrics-nlp` is absent." Put the local pytest
  tail in the handoff; do NOT claim "CI green".
- Handoff `d:\Projects\.windsurf\handoffs\<ts>_music-ai-toolshop-t5l3.md`: token/entity/topic counts,
  annotation coverage (Cyrillic vs Latin), the drill-vs-pop theme + slang discrimination evidence,
  runtime, commit hashes, local pytest tail, deviations.

## Verification checklist
- [ ] `tokens`/`entities`/`slang_terms`/`topics`/`section_topics` populated; counts in handoff
- [ ] `annotate` resumable; coverage reported per source-script (ceiling visible)
- [ ] **Themes discriminate drill vs pop; slang distinctive lists non-empty** (the exit gate)
- [ ] Heavy deps in `lyrics-nlp` extra only; models in MusicData not repo; license-ledger updated
- [ ] Local pytest: 0 failed (passed count varies by installed extras; NLP tests skip when deps absent)
- [ ] Report is statistics-only (no lyric dumps); repo clean + pushed

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "T5-L3: language & themes (CLASSLA + slang lexicon + BERTopic)" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-22-t5l3-language-themes.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-22-t5l3-language-themes.md
exactly as written. PRECONDITION: Phase 0 is already committed+pushed (27cfa35/e293323, verified); just
confirm git status is clean before starting, else STOP and report. Last CHANGELOG number is #019 (Phase 0)
— L3 gets CHANGELOG #020. Hard rules: lyrics.db + models
+ all derived data in D:\MusicData, never the repo; heavy NLP deps go in a NEW `lyrics-nlp` extra (not
base `lyrics`); install torch CPU wheel first (`pip install torch --index-url
https://download.pytorch.org/whl/cpu`); NLP tests skip-guarded so they stay out of CI; reports
statistics-only (no lyric dumps); no re-fetch from Genius; NO L4/L5 work. Feed CLASSLA `text_raw` via
`classla.Pipeline('sr', type='nonstandard')` (document the diacritic-stripped-Latin accuracy ceiling
— do not attempt diacritic restoration). CI is billing-locked → gate on LOCAL pytest; the invariant is
0 failed (passed count varies by installed extras), never claim CI green. The session is NOT done until the
report shows,
with numbers, that themes AND slang DISCRIMINATE drill_trap vs pop (flat/identical topic mixes = not done).

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-t5l3.md
with token/entity/topic counts, annotation coverage by source-script, the drill-vs-pop theme + slang
discrimination evidence, runtime, commit hashes, local pytest tail, deviations. After review, L4
(fingerprints + gap report on the 2,633 Suno lyrics) is released.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-22-t5l3-language-themes.md
```
