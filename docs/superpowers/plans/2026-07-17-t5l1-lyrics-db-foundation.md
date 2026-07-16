# T5-L1 — Lyric Intelligence Foundation: lyrics.db + Baseline Stats

> **Authored 2026-07-17** by strategy review. Parent spec: `specs/2026-07-17-lyric-intelligence-strategy.md`
> (phase L1). Obey `AGENTS.md`. **GATED ON M1c-final** (`plans/2026-07-16-h1m1c-cleanup-genius-run.md`):
> repo must be clean and the corpus index rebuilt before this session starts. No L2+ scope creep —
> no rhyme mining, no CLASSLA, no BERTopic in this session.

## Context (facts verified against the corpus 2026-07-17)

- Corpus root: `D:\MusicData\toolshop\lyrics\genius\` — **386 unique songs** on disk
  (386 `.json` + 386 `.txt` + `_index.json`/`_summary.md`/`_dedup_log.json` = 775 files).
  Per folder: buba-solo 75 · coby-solo 82 · jala-solo 201 · jala-buba-duo 27 · jala-buba-coby-trio 1.
  The often-quoted "415" is index inflation (28 duplicated keys) — M1c Task 2 fixes the index;
  **the folders are the source of truth either way.**
- One **cross-folder duplicate**: `jala-brat-dandara` exists in two category folders. Loader must
  dedup by normalized `(title, primary_artist)` and record which copy won.
- Song JSON schema (already section-segmented at extraction): `title`, `artist`, `url`, `language`,
  `raw_lyrics`, `clean_lyrics`, `sections: [{label, content}]`. **2,704 sections total; 0 songs
  without sections.**
- **112 songs contain Cyrillic** → script unification via `cyrtranslit` is required, not optional.
- Lyrics are largely **diacritics-stripped Latin** ("Izaci cu" not "Izaći ću"). Serbian diacritics
  sit on consonants only — vowels are unaffected, so syllable counting and later vowel-skeleton
  rhyme work are safe. **Do NOT attempt diacritic restoration in L1.**
- **Category folder ≠ author.** Example: "Brkka — Diskoteka" lives in `jala-solo` because Jala Brat
  is featured; its `primary_artist` is Brkka. Per-artist stats must key on `primary_artist`, never
  the folder. Bonus: section labels carry performer attribution (`[Refren: Peki & Jala Brat]`,
  `[Strofa 1: Peki]`) — parse performers now; L2/L4 fingerprints will attribute craft per section.
- Reuse, don't rewrite: `toolshop/genius_parser.py` (Section/ParsedLyrics), `toolshop/lyrics_analyzer.py`
  (basic stats), `lyrics_research/scripts/analyze_lyrics.py` (pilot metrics: English-loanword heuristic,
  hook/repeated-line detection, top-words).

### Data boundary (hard rules)
- `lyrics.db` is derived from copyrighted material → lives at `D:\MusicData\toolshop\lyrics\lyrics.db`
  (respect `TOOLSHOP_DATA_DIR` env override). **Never inside the repo, never committed.**
- Test fixtures: **synthetic fake lyrics only** — never copy real corpus lines into `tests/`.
- The baseline report contains **statistics only** (counts, ratios, top-word lists are fine;
  no full lyric lines; at most 2 short attributed quotes).

## Tasks

### Task 1: Schema + loader (`toolshop/lyricsdb.py`) — TDD
- [ ] SQLite (stdlib `sqlite3`; Datasette-compatible). Tables:
      - `songs(id, corpus TEXT NOT NULL DEFAULT 'genius-pro', category, title, primary_artist,
        featured_artists JSON, url, language, source_path, ingested_at)` — `corpus` column exists NOW
        so the Suno corpus (L4) needs no migration.
      - `sections(id, song_id, ordinal, type, type_number, label_raw, performers JSON)` — `type`
        normalized to {refren, strofa, bridge, intro, outro, prerefren, hook, other}; map English
        labels too (Verse→strofa, Chorus→refren, Pre-Chorus→prerefren, …).
      - `lines(id, section_id, ordinal, text_raw, text_norm, word_count, syllable_count)`.
- [ ] Normalization for `text_norm`: NFC → cyrtranslit Cyrillic→Latin (only when Cyrillic detected)
      → lowercase. Keep `text_raw` verbatim.
- [ ] Section label parser: `"Refren: Peki & Jala Brat"` → `(type='refren', performers=['Peki','Jala Brat'])`;
      `"Strofa 2"` → `(type='strofa', type_number=2, performers=[])`. Unknown labels → `type='other'`,
      `label_raw` preserved. TDD with a table of real label shapes.
- [ ] Loader: scan `<root>/genius/*/*.json` (folders = truth), join `_index.json` by filename for
      `featured_artists`/`url`/`category`; tolerate a stale/missing index (fields nullable). Note:
      the rebuilt index (385 entries, verified 2026-07-17) stores ABSOLUTE paths — join on basename,
      never trust index paths.
      Dedup by normalized `(title, primary_artist)`; log dropped duplicates. Full rebuild each run
      (drop + recreate — corpus is small); print ingest summary.
- [ ] Fixture mini-corpus (3 fake songs, incl. one Cyrillic, one with performer-attributed labels,
      one duplicate pair) under `tests/fixtures/lyrics_min/`.

### Task 2: Serbian syllable counter (`toolshop/syllables.py`) — TDD
- [ ] Rule: nuclei = vowels `aeiou` + **syllabic r** (an `r` with no adjacent vowel: "prst"→1,
      "srce"→2, "brzo"→2, "vrt"→1). `count_syllables(word)` and `count_line(text)`.
- [ ] Test list of ≥30 hand-checked words including syllabic-r cases, loanwords, and
      diacritics-stripped forms. This counter feeds `lines.syllable_count` at ingest.

### Task 3: Baseline metrics (`toolshop/lyrics_metrics.py`)
- [ ] Per song → `song_metrics` table: total_words, unique_words, TTR, line_count,
      avg_words_per_line, avg_syllables_per_line, hook_repetition (max repeated-line count +
      repeated-line ratio), english_loanword_rate (port the pilot heuristic), section_type_counts JSON.
- [ ] Per artist (GROUP BY `primary_artist`, corpus='genius-pro'): SQL views with means/medians —
      Buba Corelli / Jala Brat / Coby rows are the deliverable; other primary artists appear as-is.

### Task 4: CLI + baseline report
- [ ] `toolshop lyrics build-db [--root PATH] [--db PATH]` and
      `toolshop lyrics stats [--artist NAME] [--json] [--db PATH]` — follow the existing argparse
      subparser pattern in `toolshop/cli.py`.
- [ ] Write `lyrics_research/reports/2026-07-XX_genius_corpus_baseline.md`: corpus inventory,
      per-artist baseline table (the three tracked artists side by side), top-20 words per artist,
      section-type distribution, syllables/line distribution. Statistics only (see data boundary).
- [ ] Verify Datasette browsing works: `pip install datasette` (dev-only, NOT a project dep) →
      `datasette D:\MusicData\toolshop\lyrics\lyrics.db` opens; document the one-liner in README.

### Task 5: Deps, docs, commits
- [ ] New runtime dep: `cyrtranslit` only, under a `lyrics` optional-dependency extra in
      `pyproject.toml` + license-ledger entry per integration-map policy. classla/bertopic are L3 —
      do NOT add them now.
- [ ] CHANGELOG entry; PROJECTS_INDEX lyrics lane refreshed (386-song corrected count).
- [ ] Commits: (a) `feat(lyrics): lyrics.db schema + corpus loader`, (b) `feat(lyrics): Serbian
      syllable counter`, (c) `feat(lyrics): baseline metrics + stats CLI + corpus report`,
      (d) `docs: changelog + index`. Push. **CI reality check (verified 2026-07-17): CI has been red
      since May (pre-existing numpy debt, STATUS debt item 1). The bar for this session is: local
      pytest shows no NEW failures beyond the known 10 `test_cleaning_pipeline.py` ones, and the CI
      run's failure list is unchanged. Paste the CI run URL + conclusion in the handoff — do not
      tick a "green" claim.**

### Task 6: Handoff
- [ ] `d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-t5l1.md`: ingest summary
      (songs/sections/lines counts vs the verified 386/2,704 baseline), dedup log, pytest tail,
      `toolshop lyrics stats` output for the three artists, commit hashes, deviations.

## Verification checklist
- [ ] `toolshop lyrics build-db` ingests **385–386 songs** (386 minus cross-folder dedup), **2,704
      sections** (± documented dedup delta), zero unexplained skips
- [ ] Syllable tests green incl. all syllabic-r cases; fixture ingest test green; no NEW CI failures
      vs the known-red baseline (run URL in handoff)
- [ ] `toolshop lyrics stats` renders per-artist table in <10 s on the full corpus
- [ ] Datasette opens the DB; `songs`, `sections`, `lines`, `song_metrics` all browsable
- [ ] `git grep` spot-check: no real lyric lines anywhere in the repo; lyrics.db only in MusicData
- [ ] Exit criteria from the strategy spec met: stats CLI over the corpus + DB browsable in Datasette

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "T5-L1: lyrics.db foundation (normalize, syllables, baseline stats)" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-17-t5l1-lyrics-db-foundation.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-17-t5l1-lyrics-db-foundation.md
exactly as written. PRECONDITION: M1c-final must be complete (clean git status, rebuilt corpus index) —
if it is not, STOP and report instead of starting. Hard rules: lyrics.db and all derived data live in
D:\MusicData, never in the repo; test fixtures use synthetic fake lyrics only; the baseline report contains
statistics, never lyric dumps; cyrtranslit is the ONLY new dependency (no classla, no bertopic — those are L3).
TDD for the label parser, loader, and syllable counter. No rhyme mining in this session (that is L2).

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-t5l1.md
with ingest counts reconciled against 386 songs / 2,704 sections, dedup evidence, pytest tails, stats output
for Buba Corelli / Jala Brat / Coby, commit hashes, CI status, deviations, blockers. After review, L2
(rhyme miner) is released.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-17-t5l1-lyrics-db-foundation.md
```
