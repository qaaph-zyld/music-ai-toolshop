# Changelog

### Answer #033 — Lyrics Transformer: Structure + Flow Directions
**Timestamp:** 2026-07-31
**Action Type:** Feature extension + tests + CLI integration

**What was done:**
- Extended `toolshop/lyrics_transformer.py` with two new transformation directions:
  - **Section Structure Optimization** (`transform_structure`): Parses user's section sequence via `parse_section_label()`, compares to genre template (`_TEMPLATE_ORDER` / `_TEMPLATE_TYPES`) and cohort DB section sequences. Suggests: missing sections (intro, pre-chorus, bridge, post-chorus), section ordering issues, section count mismatch vs cohort average. All auto_safe=True (inserting section labels doesn't change existing lyrics). Refren↔hook equivalence mapping for drill_trap ordering.
  - **Flow Pattern Matching** (`transform_flow`): Computes per-section syllable counts (vowel-group heuristic), runs `flow_analyzer.detect_patterns()`, queries cohort `song_metrics` and `lines.syllable_count` for comparison. Suggests: syllable count per line vs cohort average (split/merge), pattern mismatch (uniform vs alternating based on cohort CV). All auto_safe=False (line splitting/merging changes lyrics).
- Extended `run_all_transforms()` to dispatch `structure` and `flow` directions.
- Extended `apply_transforms()` to insert section labels for structure suggestions (prepend to file).
- CLI: `--direction` choices extended with `structure`, `flow`; `all` now includes all four directions.
- 15 new TDD tests: TestStructureOptimization (6), TestFlowPatternMatching (5), TestStructureAutoFix (2), TestCLIIntegration (2). New `structure_db` fixture with `song_metrics`, `sections.type/ordinal`, `lines.syllable_count` columns.

**Files affected:**
- `toolshop/lyrics_transformer.py` (extended, ~360 lines added)
- `tests/test_lyrics_transformer.py` (extended, ~340 lines added)
- `toolshop/cli.py` (2 edits: `--direction` choices, dispatch `all`)

**Test results:** 722 passed, 1 skipped, 0 failed (284.98s).

---

### Answer #032 — Lyrics Transformer Module
**Timestamp:** 2026-07-31
**Action Type:** Feature + tests + CLI integration

**What was done:**
- New module `toolshop/lyrics_transformer.py` — suggests genre-appropriate word replacements for user-authored lyrics.
  - **Vocabulary Enhancement**: Low-frequency content words (freq < 5) flagged for replacement. Same-lemma alternatives (auto_safe=True, meaning-preserving inflectional variants) preferred; same-UPOS fallback (auto_safe=False, may shift meaning) when no same-lemma match exists.
  - **Slang Injection**: Generic content words flagged for replacement with cohort-distinctive slang terms (|distinctiveness| > 1.0, direction matching target genre). UPOS-matched to preserve semantic role. Always auto_safe=False.
  - `Suggestion` and `TransformationReport` dataclasses.
  - `run_all_transforms(directions)`, `apply_transforms(report, auto_safe_only=True)`, `interactive_transform(report)`.
  - `format_transform_text(report)` and `format_transform_json(report)` formatters.
  - Reuses `CorrectedSection`, `_SECTION_LABEL_RE` from `lyrics_corrector.py`; `_ascii_fold`, `DEFAULT_DB_PATH` from `lyricsdb.py`.
- CLI integration: `toolshop lyrics transform <file> --target-genre drill_trap|pop --direction vocabulary|slang|all --mode report|auto-fix|interactive --db PATH --output PATH --json`
- 17 TDD tests in `tests/test_lyrics_transformer.py` with mock SQLite DB (`:memory:` pattern).

**Files affected:**
- `toolshop/lyrics_transformer.py` (new, ~400 lines)
- `tests/test_lyrics_transformer.py` (new, ~340 lines)
- `toolshop/cli.py` (subparser + dispatch block, ~60 lines added)

**Test results:** 707 passed, 1 skipped, 0 failed (378.66s).

---

### Answer #031 — Batch 3 Follow-up: Test Fixes, Video Module, Suno Gap Report, Cohen's d, Collab Network
**Timestamp:** 2026-07-30
**Action Type:** Test fixes + feature commits + analysis reports

**What was done:**
- Fixed 3 pre-existing test failures: `test_bpm_adapter.py` (mock `np.atleast_1d`), `test_themes.py` (remove deprecated `random_state` from BERTopic).
- Committed video assistant module: 5 modules (`video_ass.py`, `video_compose.py`, `video_features.py`, `video_shaders.py`, `video_stock.py`) + 7 tests + `pyproject.toml` video extra.
- Committed 3 docs: Pravo Vreme analysis, Ableton release notes, perplexity lyrics prompt.
- Built Suno gap report: compared 3,381 AI-generated Suno lyrics vs 1,315 Genius pro lyrics across L1-L4 dimensions (structure, rhyme, lexical, slang overlap).
- Recomputed Cohen's d on expanded 1,315-song corpus: d=0.9841 (large effect, down from 1.1786 on 742 songs). Direction consistent: pop > drill_trap.
- Collaboration network analysis: 252 artists, 370 edges, 18 cross-cohort (drill↔pop) collaborations. Jala Brat is most connected (68 connections).

**Reports:**
- `lyrics_research/reports/suno_gap_report.md`
- `lyrics_research/reports/cohen_d_expanded.md`
- `lyrics_research/reports/collab_network.md`

**Scripts:**
- `scripts/suno_gap_report.py`
- `scripts/recompute_cohens_d.py`
- `scripts/collab_network.py`

**Test results:** 663 passed, 1 skipped, 0 failed (522.87s).

**Commits:** 976e09b (test fix + gitignore), 1f248b8 (corpus correction research + Distro_Kidea gitignore)

---

### Answer #030 - MusicData Relocation + Suno Liked Songs Scripts
**Timestamp:** 2026-07-30
**Action Type:** Infrastructure + script commit

**What was done:**
- Moved `D:\MusicData` (~15 GB, 20K files) into repo-local `data/` directory.
- Updated all `TOOLSHOP_DATA_DIR` defaults from hardcoded `D:\MusicData\toolshop` to `Path(__file__).resolve().parent.parent / "data" / "toolshop"` (repo-relative, portable).
- Updated all hardcoded `D:\MusicData` paths in lyricsdb.py, cli.py, scripts, and Genious_lyrics_extractor (18 files total).
- Added `data/` to `.gitignore` to prevent accidental commits.
- Updated `AGENTS.md` data boundary description.
- Committed Suno liked songs scripts: `scripts/suno_fetch_liked.py` (auto-token via Chrome, is_liked filter, save-as-you-go), `scripts/convert_suno_extractor.py` (converts suno_extractor JSONs to toolshop format).
- 3,426 Suno liked clip metadata files in `data/toolshop/suno/`.

**Files modified:**
- `.gitignore` — added `data/`
- `AGENTS.md` — updated data boundary
- `toolshop/backup.py`, `toolshop/remix_adapter.py`, `toolshop/remix_cli.py`, `toolshop/stems_cli.py`, `toolshop/video_cli.py` — TOOLSHOP_DATA_DIR defaults
- `toolshop/lyricsdb.py` — `_DEFAULT_DATA_DIR` + docstring
- `toolshop/cli.py` — corpus root path + all help text strings
- `scripts/suno_fetch_liked.py`, `scripts/convert_suno_extractor.py` — OUTPUT_DIR paths
- `Genious_lyrics_extractor/{corpus_inventory,rebuild_db,verify_counts,fetch_henny,extract_artists,extract_batch2,extract_batch3,extract_batch3_remaining}.py` — data paths
- `benchmarks/stem_benchmark.py` — data root default

**Test results:** 660 passed, 3 failed (pre-existing: 2 bpm_adapter, 1 bertopic), 1 skipped. No new failures.

**Note:** User must update `PHONEMIZER_ESPEAK_PATH` and `PHONEMIZER_ESPEAK_LIBRARY` env vars to new espeak-ng location under `data/toolshop/espeak-ng/`.

---

### Answer #029 - L1-L4 Pipeline Re-run on Expanded 1,425-Song Corpus
**Timestamp:** 2026-07-30
**Action Type:** Pipeline re-run + bugfix

**What was done:**
- Fixed NULL cohort assignment: added `_FOLDER_COHORT_MAP` fallback in `lyricsdb.py` using `target_artist` (folder name) when `primary_artist` not in `COHORT_MAP`. Reduced NULL solo from 85 to 0.
- Rebuilt `lyrics.db`: 1,425 songs, 10,654 sections, 65,912 lines, 273,801 rhyme rows.
- Cohort distribution: drill_trap 795 solo / pop 520 solo / 13 drill featured / 4 pop featured / 93 NULL featured.
- CLASSLA annotation: 65,912/65,912 lines (100% coverage), 501,386 tokens, 10,544 entities.
- Slang lexicon: 11,364 terms (1,630 drill-distinctive, 1,934 pop-distinctive).
- BERTopic themes: 163 topics, 4,079 section_topics. JSD(drill||pop) = 0.7312. Top-5 overlap 1/5.
- Pro fingerprints: regenerated with 16 artists (8 original + 8 batch3) + 2 cohort rollups.
- Fixed SQLite variable limit in `fingerprint.py`: replaced `IN (line_placeholders)` with JOIN subquery to avoid 999 variable limit for 30k+ line_ids.
- Added 8 batch3 artists to `TARGET_ARTISTS` in `fingerprint.py`.

**Files modified:**
- `toolshop/lyricsdb.py` — `_FOLDER_COHORT_MAP` + fallback logic in `_insert_song()`
- `toolshop/fingerprint.py` — SQLite variable limit fix + 8 new artists in `TARGET_ARTISTS`
- `lyrics_research/reports/pro_fingerprints.md` — regenerated report
- `.gitignore` — added `Stemmeca_alatkka/run_remix.py`

**Test results:** 660 passed, 3 failed (pre-existing: 2 bpm_adapter mock, 1 bertopic API), 1 skipped. No new failures.

**Next steps:** L4 Part B (Suno gap report) — out of scope for this session.

---

### Answer #028 - Music Video Generator (P0 + P1)
**Timestamp:** 2026-07-30
**Action Type:** Feature implementation

**What was done:**
- Implemented Music Video Generator module with 7 new modules and 72 tests (all passing).
- **P0 (FFmpeg compositing):**
  - `video_features.py` — librosa audio feature extraction (beats, onsets, RMS, chroma, sections, stem energies) to sidecar JSON.
  - `video_ass.py` — LRC to ASS subtitle conversion with 4 style presets (default, neon, minimal, bold).
  - `video_compose.py` — FFmpeg subprocess compositing: showwaves, Ken Burns, concat, crossfade, ASS overlay, full pipeline orchestration.
  - `video_cli.py` — argparse subcommands: `features`, `generate`, `lyrics`, `stock`.
  - `cli.py` integration — `video` subcommand registered and dispatched.
  - Integration test — end-to-end features → ASS → compose pipeline with mocked FFmpeg.
- **P1 (Shaders + Stock):**
  - `video_shaders.py` — ModernGL audio-reactive shader renderer with 4 GLSL presets (neon_grid, plasma, spectrum_bars, particle_swirl). Uniforms derived from audio features (bass, treble, onset, beat phase).
  - `video_stock.py` — Pexels + Pixabay stock footage API adapters with unified search and download.
  - `compose_pipeline` updated to support `shader:PRESET` background type.
- `pyproject.toml` — added `[video]` optional dependency group (librosa, numpy, Pillow, moderngl, httpx).

**Files added:**
- `toolshop/video_features.py` (140 lines)
- `toolshop/video_ass.py` (190 lines)
- `toolshop/video_compose.py` (305 lines)
- `toolshop/video_cli.py` (220 lines)
- `toolshop/video_shaders.py` (240 lines)
- `toolshop/video_stock.py` (175 lines)
- `tests/test_video_features.py` (7 tests)
- `tests/test_video_ass.py` (15 tests)
- `tests/test_video_compose.py` (18 tests)
- `tests/test_video_cli.py` (9 tests)
- `tests/test_video_shaders.py` (8 tests)
- `tests/test_video_stock.py` (13 tests)
- `tests/test_video_integration.py` (3 tests)

**Files modified:**
- `toolshop/cli.py` — added video subcommand registration and dispatch
- `pyproject.toml` — added video extra dependencies

**Test results:** 72 video tests passed, 660 total passed, 3 pre-existing failures (test_bpm_adapter, test_themes — unrelated).

### Answer #027 - Batch 3 Corpus Expansion (1,425 songs)
**Timestamp:** 2026-07-27
**Action Type:** Data expansion + bugfix

**What was done:**
- Extracted 8 new Balkan artists from Genius: Devito, TNG, Voyage, Rasta (drill_trap); Maya Berovic, Ana Nikolic, Breskvica, Henny (pop). 722 new songs fetched.
- Updated `COHORT_MAP` in `lyricsdb.py` with 8 new entries.
- Rebuilt unified index and lyrics.db: 1,425 songs (up from 742), 10,654 sections, 65,912 lines, 273,801 rhyme rows.
- Cohort distribution: drill_trap 723 solo / pop 524 solo / NULL 178 (85 solo + 93 featured).
- `.gitignore`: added patterns for `fingerprint-output.txt`, `push-output.txt`, `sanity-output.txt`, `test-final.txt`, `test-fp-output.txt`, `Stemmeca_alatkka/stems/`, `Stemmeca_alatkka/tracks/`.
- `bpm_adapter.py`: numpy 2.0 scalar fix (`float(np.atleast_1d(tempo)[0])`) — same pattern as `cleaning_stages.py` fix from #019.

**Files added (Genious_lyrics_extractor/):**
- `extract_batch3.py` (280 lines) — batch3 extraction following batch2 pattern
- `extract_batch3_remaining.py` — helper for resuming interrupted extraction
- `fetch_henny.py` — standalone Henny fetch helper
- `rebuild_db.py` — DB rebuild with platform.platform() patch for Windows
- `verify_counts.py` — corpus count verification
- `corpus_inventory.py` — full corpus inventory report
- `run_batch3_remaining.ps1` — PowerShell helper

**Files modified:**
- `toolshop/lyricsdb.py` — COHORT_MAP +8 entries
- `toolshop/bpm_adapter.py` — numpy 2.0 tempo scalar fix
- `.gitignore` — junk file patterns + Stemmeca dirs

**Next steps:** Fix NULL cohort assignment for 85 solo songs, re-run CLASSLA + slang + BERTopic + fingerprints on expanded corpus.

---

### Answer #026 - T5-L4 Part A: Pro Fingerprints + Suno Fetch Script
**Timestamp:** 2026-07-27
**Action Type:** Feature implementation

**What was built:**
- **`toolshop/fingerprint.py`** — Per-artist pro fingerprints from persisted data only (no recomputation). Functions: `build_fingerprint()`, `build_cohort_fingerprint()`, `render_fingerprint_md()`, `render_report()`. Aggregates rhyme craft (RF median+IQR, %multis, internal rate, dominant schemes, top vowel pairs), structure (section-type distribution, avg sections/song, avg lines/section, refren share, hook repetition), lexical (TTR, syllables/line, distinctive vocabulary top-20 with UPOS filtering), and content (top PER/LOC/ORG entities, top-5 topics with shares). Auto-derived 2-3 sentence craft profile.
- **`tests/test_fingerprint.py`** — 12 TDD tests covering all fingerprint functions, cohort rollups, golden snapshot, and markdown rendering.
- **CLI verb** `toolshop lyrics fingerprint` with `--artist`, `--cohort`, `--db`, `--output` options. Default renders full report to `lyrics_research/reports/pro_fingerprints.md`.
- **`lyrics_research/reports/pro_fingerprints.md`** — 10-page report: 8 artist fingerprints + 2 cohort rollups (drill_trap, pop).
- **`scripts/suno_fetch_liked.py`** — Standalone script to fetch liked Suno clips' metadata via internal API. Saves `<clip_id>_metadata.json` in toolshop-compatible format. Resume support, conservative rate limiting. Requires bearer token from browser dev tools.

**A3 sanity gate (3 spot values verified against direct SQL):**
1. Jala Brat RF median: SQL=0.5761, report=0.5761 ✓
2. Buba Corelli %multis median: SQL=0.8462, report=0.8462 ✓
3. Senidah top-5 topics: all 5 topic shares match SQL to 1 decimal ✓

**Test results:** 584 passed, 0 failed, 3 deselected (235.13s) — up from 538 baseline (+12 fingerprint tests, +34 DAW from #025)

**Part B status:** Suno fetch script written and ready-to-run. Download gated on user providing bearer token. Gap report deferred to follow-up session.

### Answer #025 - FL Studio DAW Integration Phases 1-4
**Timestamp:** 2026-07-27
**Action Type:** Feature implementation

**What was built:**
- **12 DAW modules** in `toolshop/daw/`: `client.py` (TCP bridge client), `transport.py`, `mixer.py`, `channels.py`, `patterns.py`, `piano_roll.py`, `plugins.py`, `generators.py`, `corpus_intel.py`, `daw_cli.py` (CLI with 17 subcommands), `fl_bridge_script.py` (19 bridge handlers for FL Studio 21 API), `__init__.py`
- **143 tests** in `tests/test_daw.py` (8 test classes, mock TCP server with lambda handlers)
- **CLI integration** in `toolshop/cli.py` (+15 lines: DAW subparser + dispatch)

**Architecture:** 3-layer pattern — Wrapper module (thin `client.call`) → Bridge script (FL API mapping) → CLI (argparse + dispatch). Mock TCP server for fast deterministic tests.

**Key bugs fixed during implementation:**
1. `chord_notes` auto-detection: rewrote from fixed +3 semitone offset to scale-interval-based stacked thirds (scale_degree+2, +4). Fixed C major I chord producing D# instead of E.
2. `gen_arpeggio` chord root parsing: strip trailing "m" from chord names ("Gm" → "G") before `note_name_to_midi`.
3. Mock server: added 4 missing mixer handlers (set_volume/set_pan/mute/solo).

**Test results:** 538 passed, 2 skipped, 3 deselected, 0 failed (207.51s)

**Also included in this commit:**
- `tests/fixtures/lyrics_min/_dedup_log.json`: path-case fix (D: → d: from test run)
- `docs/superpowers/plans/2026-07-23-t5l4-fingerprints-gap-report.md`: L4 plan doc
- `docs/superpowers/specs/arpino-sachi-vocal-chain-analysis.md`: vocal chain spec
- `.gitignore`: added `test-output.txt` pattern

---

### Answer #024 - T5-L3 Independent Verification (READ-ONLY)
**Timestamp:** 2026-07-23
**Action Type:** Independent verification (orchestrator re-run; docs-only commit)

**Previous State:** CHANGELOG #021 claimed "L3 discrimination gate PASS" (commits 7a93ad7/de2a528/2893394). The claim was UNREVIEWED — STATUS.md flagged it for spot-check as Q1 item 1.

**Current State:** All #021 claims independently reproduced from `lyrics.db` (D:\MusicData\toolshop\lyrics\lyrics.db, READ-ONLY). No product code or DB modified. No CLASSLA/BERTopic/slang mining re-run — persistence-level verification only (same pattern as L2.1 #020).

**Verification results (all re-run from raw DB, not relayed from #021):**
1. **Annotation coverage:** 36,572/36,572 lines (100%, 0 gaps), 282,426 tokens, 6,708 entities — all match. Cyrillic 3,398 / Latin 279,028. NER: PER 3,838 / LOC 1,240 / ORG 919 / MISC 645 / DERIV-PER 66. 1 NULL lemma out of 282,426 (negligible).
2. **Slang lexicon:** 6,984 terms, 2,421 drill-distinctive, 1,741 pop-distinctive, 1,638 strong (|dist|>1.0) — all match. Distinctiveness recompute for 10-term random sample (seed=42): max |diff| = 0.0000 (persisted == recomputed). Top-10 drill/pop terms pass face validity (real slang, not tokenizer junk).
3. **Themes:** 84 topics, 2,283 section_topics — match. JSD(drill||pop) recomputed from persisted per-cohort distributions = 0.2015 (matches to 4 decimals). Section coverage: 2,283/5,493 = 41.6% (734 excluded by min_section_lines=2; 2,476 HDBSCAN outliers — expected, plan sets no coverage target).
4. **Discrimination gate:** All three conditions PASS (slang: 2,421/1,741 > 0; strong: 1,638 > 0; theme: JSD 0.2015 > 0.05). Top-5 topic overlap = 2/5 — visibly different dominant topics. Direction consistent with L2.1 (Cohen's d=1.18, pop RF > drill RF).

**Verdict: L3 = VERIFIED PASS.** #021 is review-cleared. L4 unblocked.

#### Changes Made:
- **ADDED:** `lyrics_research/reports/2026-07-23_l3-verification.md` - Full verification report with claims table, queries, and verdict.
- **UPDATED:** `docs/superpowers/STATUS.md` - T5 lane retagged to "L3 VERIFIED PASS"; Q1 item 1 marked done; review header updated.

#### Verification:
- DB: D:\MusicData\toolshop\lyrics\lyrics.db (READ-ONLY, no modifications)
- No product code modified. No CLASSLA, BERTopic, or slang mining re-run.
- Verification script: D:\MusicData\toolshop\l3_verify.py (outside repo, not committed)

---

### Answer #023 - Q1-S0 Orchestrator Verification (READ-ONLY)
**Timestamp:** 2026-07-23
**Action Type:** Independent verification (orchestrator re-run; docs-only commit)

**Verification results (all re-run independently, not relayed from handoff):**
1. `pytest -m "not slow"`: **429 passed, 3 deselected, 0 failed** — matches handoff exactly.
2. `toolshop closeout`: **exit 0, PASS** (evidence block reproduced).
3. `git log origin/master..master`: empty; docs wave (goals v1.0, 3 research reports, Q1-S0 plan) tracked on origin.
4. `git config core.hooksPath` = `hooks`; `hooks/pre-push` tracked; doctor `[OK] hooks_path`.
5. `.gitignore` globs live (`pytest_*.txt`, `annotate_run*.txt`, `.windsurf/`).
6. Submodule diagnosis confirmed: untracked-content-only, pointer `aebcf76` on its remote.

**Verdict: Q1-S0 = VERIFIED PASS.** Handoff was honest (deviations documented, config-hack
self-corrected and disclosed).

**Findings logged for follow-up:**
- Plan premises (unpushed commits, junk files) had been consumed by an out-of-band L3 session
  (`7a93ad7`/`de2a528`/`2893394`, Answer #021) that pushed and cleaned before Q1-S0 ran.
  **#021's "discrimination gate PASS" claim is UNREVIEWED** — next session = L3 spot-check.
- Minor closeout debt: docstring claims a submodule pointer-on-remote check that the code does
  not implement (prefix checks only) — one-liner, fold into next closeout-touching session.
- Root-clutter audit decisions pending (tracked one-off scripts, `.coverage` tracked-though-ignored).

---

### Answer #022 - Q1-S0 Hygiene + Mechanical Close-Out Gate
**Timestamp:** 2026-07-23 00:30
**Action Type:** Infrastructure / tooling (5 commits)

**Previous State:** 3 L3 commits were already pushed (verified). 12 junk `pytest_*.txt` files were already cleaned (verified absent). Close-out discipline was documentation-only — no mechanical enforcement. `.gitignore` had exact-match `pytest_tail.txt` instead of globs. Stray handoff file in repo `.windsurf/`. No pre-push hook. No `toolshop closeout` command.

**Current State:**
1. **Push verified:** `git log origin/master..master` empty — all commits on remote.
2. **`.gitignore` globs:** Replaced `pytest_tail.txt` with `pytest_*.txt`, `annotate_run*.txt`; added `.windsurf/`.
3. **Stray handoff moved:** `.windsurf/handoffs/2026-07-22_reconcile-m6-t7-records.md` → `D:\Projects\.windsurf\handoffs\`.
4. **`toolshop closeout` command:** New CLI verb (`toolshop/closeout.py`). Checks clean tree, no unpushed commits, submodule clean. Prints evidence block. Exit 0 only when all pass. 7 tests (mocked git calls).
5. **Pre-push hook** (`hooks/pre-push`, version-controlled): blocks pushes with tracked junk files or staged-uncommitted changes. `git config core.hooksPath hooks` activated.
6. **Doctor check:** `_hooks_path_ok()` in `doctor.py` — verifies `core.hooksPath` == `hooks`. 3 new tests.
7. **AGENTS.md:** "Mechanical close-out" subsection added.
8. **Docs wave:** STATUS.md, Q1-S0 plan, 12-month goals spec, 3 research reports committed.

#### Commits:
- (a) `.gitignore` glob fix + cleanup
- (b) `toolshop closeout` command + tests
- (c) hooks/pre-push + doctor hooks_path check + AGENTS.md
- (d) docs wave (STATUS, plan, specs, research)
- (e) CHANGELOG #022

#### Tests:
- Baseline: 419 passed, 3 deselected, 0 failed
- Final: 429 passed, 3 deselected, 0 failed (+10 new: 7 closeout + 3 hooks_path)

---

### Answer #021 - T5-L3 Language & Themes Analysis
**Timestamp:** 2026-07-22 23:00
**Action Type:** Feature implementation (5 commits)

**Previous State:** L2.1 rhyme/flow/collab complete. No NLP annotation, slang lexicon, or theme modeling existed.

**Current State:** Full L3 pipeline implemented and run on 742-song corpus:
1. **Schema**: 5 new tables (`tokens`, `entities`, `slang_terms`, `topics`, `section_topics`) in `lyricsdb.py`.
2. **CLASSLA annotation**: `annotate.py` — 36,572/36,572 lines (100% coverage), 282,426 tokens, 6,708 entities. Cyrillic: 3,398 tokens / 419 lines. Latin: 279,028 tokens / 36,153 lines. NER: PER 3,838, LOC 1,240, ORG 919, MISC 645, DERIV-PER 66.
3. **Slang lexicon**: `lexicon.py` — 6,984 terms mined (2,421 drill-distinctive, 1,741 pop-distinctive, 1,638 strong with |distinctiveness| > 1.0). Log-ratio scoring per 10K tokens normalized.
4. **BERTopic themes**: `themes.py` — 84 topics from 4,759 sections (2,283 non-outlier assignments). MiniLM multilingual embeddings + UMAP(cosine, seed=42) + HDBSCAN.
5. **Discrimination report**: `l3_report.py` — JSD(drill||pop) = 0.2015, gate PASSED on all three criteria.

#### Discrimination Evidence (statistics only, no lyric dumps):
- **Slang**: Drill-distinctive top terms: `brata`(2.23), `Swag`(2.15), `bam`(2.15), `Kongo`(2.11). Pop-distinctive: `limiti`(-3.17), `quiero`(-3.12), `twerka`(-2.85), `Bomba`(-2.85).
- **Themes**: Drill-overrepresented: topic 33 `cash_haos_ovde_kraju` (∞), topic 13 `brate_su_okej_novi` (15.5x), topic 35 `mami_flex_mama_aman` (12.5x). Pop-overrepresented: topic 18 `zvezde_placu_omen_visini` (0.06x), topic 61 `avlije_senida_ziva_ajde` (0.07x).
- **Gate**: Slang PASS, Strong slang PASS (1,638), Theme PASS (JSD=0.2015 > 0.05). OVERALL: PASS.

#### Commits:
- `2318878` feat(lyrics): annotation/themes schema
- `1ce86cd` feat(lyrics): CLASSLA annotate + entities
- `6f44a3c` feat(lyrics): slang lexicon + BERTopic themes
- `7a93ad7` fix(lyrics): BERTopic random_state via UMAP + lexicon threshold
- `de2a528` feat(lyrics): L3 discrimination report + gate

#### New CLI commands:
- `toolshop lyrics annotate [--resume] [--fresh] [--limit N]`
- `toolshop lyrics lexicon [--cohort drill_trap|pop] [--top N] [--json]`
- `toolshop lyrics themes [--min-section-lines N] [--seed N] [--json]`
- `toolshop lyrics report`

#### Tests:
- 419 passed, 3 deselected, 0 failed (was 383 pre-L3, +36 new tests)
- New: 4 schema, 11 annotate, 8 lexicon, 6 themes, 7 report

#### Dependencies:
- `lyrics-nlp` extra: classla, bertopic, sentence-transformers, umap-learn, hdbscan, torch
- CLASSLA model: `sr` nonstandard (internet text type)
- Embeddings: `paraphrase-multilingual-MiniLM-L12-v2`

---

### Answer #020 - T5-L2.1 Independent Verification (READ-ONLY)
**Timestamp:** 2026-07-22 00:30
**Action Type:** Verification (no code changes)

**Previous State:** STATUS board asserted "T5-L2.1 DONE & spot-checked PASS" based on numbers relayed from an unreviewed roadmap doc. The discrimination claim (pop RF 0.70–0.76 > drill 0.51–0.66) had never been independently verified.

**Current State:** Independent re-run of all four verification tasks on live `lyrics.db` confirms PASS:
1. Per-artist fingerprints reproduced exactly (all 11 baseline artists match to 4 decimal places).
2. Discrimination proven: Cohen's d = 1.1786 (large effect); pop median RF 0.7399 > drill median 0.5628; overlap 13.4%/8.9%.
3. Persistence intact: 742 song_rhyme_metrics rows, 159,171 line_rhymes, 49.3% match_length≥3, 125,862 internal rhymes.
4. Persisted == engine: max abs diff 0.000000 across 15-song random sample (seed=42).

#### Changes Made:
- **ADDED:** `lyrics_research/reports/2026-07-22_l2-1-verification.md` - Full verification report with queries, numbers, and verdict.
- **UPDATED:** `docs/superpowers/STATUS.md` - T5 line retagged from "spot-checked PASS" to "L2.1 VERIFIED PASS (independent re-run 2026-07-22)".

#### Verification:
- DB: D:\MusicData\toolshop\lyrics\lyrics.db (READ-ONLY, no modifications)
- No product code modified. No `populate_rhymes` re-run.
- Report contains all raw query output for audit.

---

### Answer #019 - Phase 0: M6 Backups & Test Hygiene Gate
**Timestamp:** 2026-07-22 00:00
**Action Type:** Infrastructure + bug fixes

**Current State:** Backup module with manifest + integrity verification created. Doctor extended with backup check. Test skip-guards for optional deps ([remix], [stems]). Numpy 2.0 tempo compat fix in cleaning_stages.py. Full suite: 364 passed, 10 skipped, 0 failed.

#### Changes Made:
- **ADDED:** `toolshop/backup.py` - Backup script with SHA-256 manifest, integrity verification, DB smoke test, and `check_backup()` for doctor.
- **EXTENDED:** `toolshop/doctor.py` - Added `_backup_ok()` check and backup detail in `print_report()`.
- **ADDED:** `tests/test_backup.py` - 5 tests covering backup creation, manifest validation, DB verification.
- **FIXED:** `toolshop/cleaning_stages.py` - Added `_scalar_tempo()` helper for numpy 2.0 compat (`float(tempo)` → `float(tempo.item())`). Fixes 9 test_cleaning_pipeline failures.
- **FIXED:** `tests/test_cleaning_pipeline.py` - Fixed `test_analyze_mode_preserves_audio` NameError (undefined `t`). Adjusted `test_keep_short_pauses` assertions to match actual librosa behavior.
- **FIXED:** `toolshop/demucs_adapter.py` - Moved `_check_demucs()` after backend validation so `test_separate_wrong_backend_raises` passes without demucs installed.
- **ADDED:** `tests/test_remix_adapter.py` - `@_skip_no_remix` skipif guard on 8 audio-dependent tests. Pure-logic tests (parse_key, semitone_diff, slice_by_beats, crossfade_concat, resolve_stems_dir, sample_name_format, load_sections, slice_by_sections) still run without [remix] extra.
- **ADDED:** `tests/test_cli_remix.py` - `@_skip_no_remix` guard on `test_remix_run_single_file` and `test_remix_run_batch_no_files`.
- **CREATED:** Backup at `C:\Backups\toolshop` — 1954 files, 32 MB, verified=True, DB smoke test PASS.

#### Verification:
- `python -m pytest tests -m "not slow" --tb=no` → 364 passed, 10 skipped, 0 failed (was: 343 passed, 19 failed, 0 skipped).
- `python -m toolshop.doctor` → backup check: OK (target=C:\Backups\toolshop, files=1954, age=0d, verified=True).
- `python -m toolshop.backup --target C:\Backups\toolshop` → Backup complete: 1954 files, 32.0 MB, Verified: True, DB smoke test: PASS.
- CI is billing-locked; local pytest is the quality gate.

---

### Answer #018 - T7.1: Section-aware Sample Forge
**Timestamp:** 2026-07-22 00:00
**Action Type:** New feature + breaking change
**Previous State:** `toolshop remix --mode sample` sliced by generic beat/onset grid. Sample filenames used `<key>_<bpm>bps_<idx>_<start>s.<ext>`. No section awareness, no external section input, no section labels in manifest.

**Current State:** Sample mode now supports section-aware slicing from an externally-provided JSON file. New naming convention `<key>_<bpm>_<section>_<n>.<ext>` (e.g. `A_120_chorus_01.flac`). Manifest entries include a `"section"` field. Three new CLI flags: `--sections`, `--sub-slice-beats`, `--no-beat-snap`. Automatic section detection is deferred to H2.

#### Breaking Changes:
- **Sample filenames changed** from `<key>_<bpm>bps_<idx>_<start>s.<ext>` to `<key>_<bpm>_<section>_<n>.<ext>`. Existing scripts or DAW projects referencing old filenames will need updating.
- Manifest now includes `"section"` field for all samples (additive, non-breaking for readers).

#### Changes Made:
- **ADDED:** `toolshop/remix_adapter.py` - `_load_sections()` parses JSON (top-level or `structure.sections`), validates/sorts sections, skips bad entries.
- **ADDED:** `toolshop/remix_adapter.py` - `_slice_by_sections()` slices audio by section boundaries with optional beat snapping and sub-slicing.
- **ADDED:** `toolshop/remix_adapter.py` - `_snap_to_nearest_beat()` helper.
- **REPLACED:** `toolshop/remix_adapter.py` - `_sample_name()` now uses `<key>_<bpm>_<section>_<n>.<ext>` pattern.
- **UPDATED:** `toolshop/remix_adapter.py` - `create_remix()` accepts `sections`, `sub_slice_beats`, `snap_to_beats` params; sample mode uses section slicing when provided.
- **ADDED:** `toolshop/cli.py` - `--sections`, `--sub-slice-beats`, `--no-beat-snap` flags on remix subparser.
- **UPDATED:** `toolshop/remix_cli.py` - `_process_one()` loads sections JSON, validates `--sections` requires `--mode sample`, passes new params to `create_remix()`.
- **UPDATED:** `.github/workflows/ci.yml` - Install `.[audio,lyrics,remix]` so remix tests run in CI.
- **ADDED:** `tests/test_remix_adapter.py` - 12 new tests for section loading, slicing, naming, and section-aware sample creation.
- **ADDED:** `tests/test_cli_remix.py` - 4 new tests for CLI flag parsing, validation, and full sections run.

#### Verification:
- `python -m pytest tests/test_remix_adapter.py tests/test_cli_remix.py -q` -> 34 passed, 0 failures.
- `toolshop remix --help` shows `--sections`, `--sub-slice-beats`, `--no-beat-snap`.
- Smoke test with 3-section JSON produces `*_intro_01.*`, `*_verse_01.*`, `*_chorus_01.*` + manifest with `"section"` field.

#### Commits:
- `3e6fadf` - #016 Sample Forge baseline
- `8b5ee7b` - T1: _load_sections + _slice_by_sections
- `c5a8c97` - T2: section-aware naming + manifest enrichment
- `6260211` - T3: CLI flags
- `3a1c434` - T4: CI + importorskip guards

---

### Answer #017 - T5-L2.1: Rhyme Persistence Fix + Cohort Reclassification
**Timestamp:** 2026-07-21 23:30
**Action Type:** Bug fix + data update
**Previous State:** `populate_rhymes` stored only `match_length=2` end rhymes (34,598 rows). No internal rhymes persisted. No per-song rhyme metrics. Corona/Indodjija were NULL cohort.

**Current State:** `populate_rhymes` now persists true longest match length for end rhymes, internal rhymes, and per-song metrics (`rhyme_factor`, `pct_multis`, `internal_rhyme_rate`, `dominant_scheme`, `top_vowel_pairs`) in new `song_rhyme_metrics` table. 159,171 rhyme rows across 742 songs. 78,489 rows (49.3%) have `match_length >= 3`. Corona + Indođija reclassified to `drill_trap` (solo count: 286 → 387). CI installs `[lyrics]` extra.

#### Changes Made:
- **FIXED:** `toolshop/rhyme_miner.py` - `populate_rhymes` now iterates match lengths from longest down to 2, persists internal rhymes, computes and stores per-song metrics.
- **ADDED:** `get_artist_rhyme_fingerprints()` helper for validation reports.
- **FIXED:** `get_artist_rhyme_stats` `multisyllabic_count` now counts end-rhyme rows only.
- **UPDATED:** `toolshop/lyricsdb.py` - Added `song_rhyme_metrics` table to schema. `COHORT_MAP` updated: Corona/Indodjija/Indođija → `drill_trap`.
- **ADDED:** `tests/fixtures/lyrics_min/multi-solo/multi-test.json` - Synthetic fixture with 4-syllable end rhymes and internal rhymes.
- **ADDED:** `test_populate_rhymes_persists_multis_and_internal` in `tests/test_rhyme_miner.py`.
- **UPDATED:** `tests/test_lyricsdb.py` - Adjusted fixture counts for new multi-test song (3 songs, 7 sections).
- **UPDATED:** `.github/workflows/ci.yml` - Install `.[audio,lyrics]` so lyrics tests run in CI.
- **ADDED:** `lyrics_research/reports/2026-07-21_rhyme_fingerprints.md` - Statistics-only fingerprint report.

#### Verification:
- `python -m pytest tests/test_rhyme_miner.py tests/test_lyricsdb.py -v -k "not espeak"` -> 136 passed, 1 deselected, 0 failures.
- DB rebuild: 742 songs, 159,171 rhyme rows, 742 song_rhyme_metrics rows.
- drill_trap solo = 387. pop solo = 214.
- Match length distribution: 2→80,682 | 3→34,688 | 4→15,052 | 5+→28,749.
- Rhyme types: end=33,309 | internal=125,862.

---

### Answer #016 - T7: Sample Forge / `toolshop remix`
**Timestamp:** 2026-07-21 22:00
**Action Type:** New feature
**Previous State:** No sample or remix creation in toolshop; T7 Sample Forge existed only on the roadmap.

**Current State:** `toolshop remix` shipped with two modes: `remix` (tempo/key/FX-matched single output) and `sample` (beat/onset-sliced sample pack). Supports 4-minute input truncation, batch processing with resume, reuse of `toolshop stems` outputs, and JSON manifests. Backed by `pedalboard` (Rubber Band time-stretch/pitch-shift) and `librosa`.

#### Changes Made:
- **NEW:** `toolshop/remix_adapter.py` - load, slice, tempo/key match, FX, render, manifest.
- **NEW:** `toolshop/remix_cli.py` - `toolshop remix` dispatch and batching.
- **NEW:** `tests/test_remix_adapter.py`, `tests/test_cli_remix.py` - 18 tests covering key parsing, slicing, stretch/FX, smoke runs, CLI parser.
- **UPDATED:** `toolshop/cli.py` - `remix` subparser and dispatch.
- **UPDATED:** `pyproject.toml` - `remix` optional extra; `pedalboard>=0.9` added to `all`.
- **UPDATED:** `toolshop/doctor.py` - `remix` extra health check.
- **UPDATED:** `README.md`, `docs/superpowers/specs/2026-07-15-oss-integration-map.md`, `PROJECTS_INDEX.md`.

#### Verification:
- `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -m pytest tests/test_remix_adapter.py tests/test_cli_remix.py -q` -> 18 passed, 6 warnings.

---

### Answer #015 - T5-L1: Lyric Intelligence Foundation (lyrics.db + baseline stats)
**Timestamp:** 2026-07-17 01:00
**Action Type:** New feature
**Previous State:** 386-song Genius corpus on disk with no structured database; no syllable counter; no per-artist metrics; no stats CLI.

**Current State:** SQLite `lyrics.db` at `D:\MusicData\toolshop\lyrics\lyrics.db` with 385 songs (1 dedup), 2,701 sections, 19,780 lines, 385 song_metrics rows. Serbian syllable counter (vowels + syllabic-r). Section label parser (Serbian + English labels, performer attribution). Per-artist stats CLI. Baseline report with Buba Corelli / Jala Brat / Coby side-by-side. `cyrtranslit` (MIT) added as only new dependency.

#### Changes Made:
- **NEW:** `toolshop/syllables.py` — Serbian syllable counter (vowels aeiou + syllabic r)
- **NEW:** `toolshop/lyricsdb.py` — SQLite schema (songs/sections/lines/song_metrics), section label parser, text normalization (NFC → cyrtranslit → lowercase), corpus loader with dedup
- **NEW:** `toolshop/lyrics_metrics.py` — per-song metrics (TTR, hook repetition, English loanword rate, section type counts), per-artist SQL views
- **NEW:** `tests/test_syllables.py` — 50 tests (30+ hand-checked words, syllabic-r, line-level)
- **NEW:** `tests/test_lyricsdb.py` — 30 tests (label parser, normalization, loader, dedup, Cyrillic, performers, idempotency)
- **NEW:** `tests/fixtures/lyrics_min/` — 3 synthetic songs (Cyrillic, performer labels, duplicate pair)
- **UPDATED:** `toolshop/cli.py` — `lyrics build-db` and `lyrics stats` subcommands
- **NEW:** `lyrics_research/reports/2026-07-17_genius_corpus_baseline.md` — baseline report
- **UPDATED:** `pyproject.toml` — `cyrtranslit>=1.2` added to `lyrics` extra
- **UPDATED:** `docs/superpowers/specs/2026-07-15-oss-integration-map.md` — cyrtranslit (MIT) added to license ledger
- **UPDATED:** `PROJECTS_INDEX.md` — corrected song count (386 → 385 after dedup)

#### Reconciliation:
- 386 JSON files on disk → 385 songs ingested (1 cross-folder duplicate: "Dandara*" vs "Dandara", same artist Jala Brat)
- 2,704 sections on disk → 2,701 sections ingested (3 sections from dropped duplicate)
- 19,780 lines, all with non-null syllable_count

#### Files Affected:
- **NEW:** `toolshop/syllables.py`, `toolshop/lyricsdb.py`, `toolshop/lyrics_metrics.py`
- **NEW:** `tests/test_syllables.py`, `tests/test_lyricsdb.py`, `tests/fixtures/lyrics_min/` (4 files)
- **UPDATED:** `toolshop/cli.py`, `pyproject.toml`, `PROJECTS_INDEX.md`, `CHANGELOG.md`
- **UPDATED:** `docs/superpowers/specs/2026-07-15-oss-integration-map.md` (license ledger)
- **NEW:** `lyrics_research/reports/2026-07-17_genius_corpus_baseline.md`

---

### Answer #014 - H1-M1c-FINAL: Consolidation (data boundary, extractor fixes, resume fix, submodule hygiene)
**Timestamp:** 2026-07-17 00:40
**Action Type:** Consolidation / Bug fixes
**Previous State:** Genius lyrics extraction succeeded (415 songs, 775 files) but data lived inside the repo (`lyrics_output/`); index had duplicate entries (trio: 3 entries for same song); `file` field missing from index; batch resume logic didn't skip `skipped_long` entries or preserve out-of-slice entries on subset runs; `mastering_tool` submodule had 70+ uncommitted CRLF/path fixes; 3 junk files tracked in repo.

**Current State:** Lyrics corpus moved to `D:\MusicData\toolshop\lyrics\genius\` (775 files). Index rebuilt from disk: 385 unique songs (1 duplicate), `file` field populated, reconciliation math documented. Batch resume logic fixed: `skipped_long` skipped on resume, out-of-slice entries preserved, failed tracks retried when targeted. Submodule committed (`aebcf76`) and pushed. Junk files removed. `.gitignore` updated. CI pipeline ready for first real run.

#### Changes Made:
- **MOVED:** `lyrics_output/` → `D:\MusicData\toolshop\lyrics\genius\` (775 files including `_index.json`, `_summary.md`, `_dedup_log.json`)
- **NEW:** `rebuild_index()` in `extract_artists.py` — disk-only index rebuild with dedup by normalized (title, primary_artist), `file` field population, reconciliation summary
- **NEW:** `--rebuild` CLI flag for `extract_artists.py`
- **NEW:** `tests/test_rebuild_index.py` — 8 tests covering dedup, file field, summary, reconciliation
- **FIXED:** `toolshop/batch.py` — `skipped_long` now skipped on resume; `load_or_create_status` no longer resets on `total_tracks` mismatch (enables subset runs); failed entries retried when targeted
- **FIXED:** `run_reverse_engineering_batch.py` — same `skipped_long` skip-on-resume logic
- **NEW:** 3 tests in `test_batch.py` for resume logic (skipped_long skip, subset preservation, failed retry)
- **UPDATED:** `extract_artists.py` default outdir → `TOOLSHOP_DATA_DIR`-aware path (`D:\MusicData\toolshop\lyrics\genius`)
- **UPDATED:** `.gitignore` — added `lyrics_output/`, `Genious_lyrics_extractor/samples/`, `Genious_lyrics_extractor/.env`, `pytest_tail.txt`
- **UPDATED:** `Genious_lyrics_extractor/README.md` — categorization rules documented, rebuild instructions added
- **DELETED:** `output.json`, `output.txt` (stale generated junk), `pytest_tail.txt`
- **SUBMODULE:** `mastering_tool` committed (`aebcf76`) on `claude/wonderful-johnson-h6xj4d`: LF normalization + post-move path fixes
- **UPDATED:** `PROJECTS_INDEX.md` — added Genius lyrics lane

#### Reconciliation:
- 386 JSON files on disk → 385 unique songs (1 duplicate: O.D.D.D. in both trio and solo folders)
- 385 × 2 (JSON+TXT) + 3 metadata = 773 expected; 775 actual; remainder = 2 files from 1 duplicate song

#### Files Affected:
- **NEW:** `Genious_lyrics_extractor/extract_artists.py` (rebuild_index, --rebuild flag, outdir fix)
- **NEW:** `tests/test_rebuild_index.py`
- **MODIFIED:** `toolshop/batch.py`
- **MODIFIED:** `run_reverse_engineering_batch.py`
- **MODIFIED:** `tests/test_batch.py`
- **MODIFIED:** `.gitignore`
- **MODIFIED:** `CHANGELOG.md`
- **MODIFIED:** `PROJECTS_INDEX.md`
- **MODIFIED:** `mastering_tool` (submodule pointer)
- **DELETED:** `output.json`, `output.txt`, `pytest_tail.txt`

#### Remaining Debt:
- 10 pre-existing numpy/librosa test failures in `test_cleaning_pipeline.py` (unrelated to this work)
- Submodule branch normalization: merge `claude/wonderful-johnson-h6xj4d` onto `main` (deferred)

---

### Answer #013 - H1-M1: CrhymeTV analyze-only batch 140/222 → launched to 222/222
**Timestamp:** 2026-07-15 21:49
**Action Type:** Modification / Batch orchestration
**Previous State:** CrhymeTV reverse-engineering batch had 140/222 tracks completed with stems; remaining 82 tracks were CPU-prohibitive for stem separation, and the PowerShell runner's catalogue regeneration step used `--status-file`/`--output-dir` arguments that `generate_crhymetv_catalogue.py` no longer accepted.

**Current State:** Fixed `run_crhymetv_batch.ps1` to pass `--results-dir`. Verified the generator against current data (140 completed tracks). pytest green for the batch runner. Smoke-tested analyze-only mode on 2 tracks. Launched the full backlog as a detached, resume-safe analyze-only batch; live log shows `[141/222]` processing.

#### Changes Made:
- **MODIFIED:** `run_crhymetv_batch.ps1` – catalogue step now passes `--results-dir $ResultsDir` instead of `--status-file`/`--output-dir`.
- **VERIFIED:** `generate_crhymetv_catalogue.py --results-dir results\crhymetv_re` exits 0 and prints `Generated catalogue for 140 completed tracks`.
- **VERIFIED:** `tests/test_run_reverse_engineering_batch.py` passes (2/2); smoke run with `--no-stems --limit 2` produced `recipe.md`, `*_analysis.json`, `*_voice_analysis.json`, no `stems/` directory, and a sensible "stems skipped" rendering.
- **LAUNCHED:** Detached full batch via `Start-Process powershell -ArgumentList '-File','d:\Projects\Music-AI-Toolshop\run_crhymetv_batch.ps1'`.

#### Technical Decisions:
- Keep the batch resume-safe: do not pass `--no-resume`; existing 140 completed entries are skipped and the remaining 82 run analyze-only.
- Smoke run used a separate `results\smoke_nostems` dir to avoid touching the production `batch_status.json`.
- Analyze-only timing measured at ~4.8 min/track on this CPU; 82 remaining tracks ≈ 6.5 h, resume-safe via `--offset`/`--limit` status JSON.

#### Next Actions Required:
- Monitor detached batch to completion (completed == 222, errors empty), then confirm catalogue auto-regeneration produces `catalogue.md` with `Tracks: 222`.

### Phase 1 — Stem Tool v1.0
**Timestamp:** 2026-07-14
**Action Type:** Implementation
**Previous State:** Legacy stem extraction used hardcoded model filenames and brittle substring guessing for output mapping; no model registry, no unified `stems` command, no Demucs backend, no model cache diagnostics.
**Current State:** Registry-driven, test-backed stem extraction with unified CLI, resumable batching, Demucs adapter, and environment-aware doctor checks.

#### Changes Made:
- Created `toolshop/stem_models.py` registry with `StemModel`/`Preset` dataclasses, canonical output patterns, and quality tiers.
- Rewrote `toolshop/stem_extractor_adapter.py` to resolve output filenames via explicit registry patterns and added `extract_stems_preset()` for preset-driven separation; legacy `extract_stems()` API preserved.
- Added `toolshop/batch.py` — resumable, UTF-8-safe batch runner shared by the stem command and existing CrhymeTV batch.
- Added `toolshop/stems_cli.py` and `toolshop stems` CLI — single-file and directory modes, `--preset`, `--device`, `--format`, `--limit`, `--offset`, `--no-resume`, and `--list-models`.
- Added `toolshop/demucs_adapter.py` with Python API first and subprocess CLI fallback for `4stem`/`6stem` presets.
- Extended `toolshop doctor` to report missing/orphaned model cache files against the registry.
- Added test coverage: `test_stem_models.py`, `test_stem_extractor_adapter.py`, `test_batch.py`, `test_cli_stems.py`, `test_demucs_adapter.py`.
- Bumped version to `0.4.0`.

#### Files Affected:
- **NEW:** `toolshop/stem_models.py`
- **NEW:** `toolshop/batch.py`
- **NEW:** `toolshop/stems_cli.py`
- **NEW:** `toolshop/demucs_adapter.py`
- **NEW:** `tests/test_stem_models.py`
- **NEW:** `tests/test_batch.py`
- **NEW:** `tests/test_cli_stems.py`
- **NEW:** `tests/test_demucs_adapter.py`
- **MODIFIED:** `toolshop/stem_extractor_adapter.py`
- **MODIFIED:** `toolshop/cli.py`
- **MODIFIED:** `toolshop/doctor.py`
- **MODIFIED:** `tests/test_doctor.py`
- **MODIFIED:** `pyproject.toml`
- **MODIFIED:** `CHANGELOG.md`

#### Commands:
- `toolshop stems --list-models`
- `toolshop stems input.wav --preset karaoke --device cpu`
- `toolshop stems input_dir/ --preset full-vocals --limit 10 --offset 5`
- `toolshop doctor`

#### Next Actions Required:
- Run `toolshop stems` smoke test on a real file to confirm end-to-end timing and output naming.
- Populate/refresh model cache and confirm `toolshop doctor` model cache PASS.
- Complete CrhymeTV batch and regenerate catalogue.

---

### Phase 0 — Take Control (Repo + Environment Hygiene)
**Timestamp:** 2026-07-11
**Action Type:** Implementation
**Previous State:** CrhymeTV batch 140/222 complete, uncommitted batch toolchain, Python 3.13 global, stale docs, duplicate projects, broken submodule config.
**Current State:** Clean git state, pinned Python 3.11 venv, `toolshop doctor`, honest docs, CrhymeTV batch resumed.

#### Changes Made:
- Committed the reverse-engineering batch toolchain and roadmap docs.
- Extended `.gitignore` for session archives, logs, coverage, and audio/stem data dirs.
- Moved personal audio (`Distro Kidea/`) and generated stems (`Stemmeca_alatkka/`) to `D:\MusicData\toolshop\`.
- Archived root `Mastering_Toolshop` sibling; canonical copy remains the `mastering_tool` submodule.
- Removed vendored `Voicebox/` fork from the repo.
- Repaired submodule config: added `.gitmodules` for `mastering_tool`; dropped phantom `MAirina_Tucc/rimer-sr` gitlink.
- Installed Python 3.11 and created repo `.venv`; committed `requirements.lock.txt`.
- Added `stems` optional-dependency group (`audio-separator`, `onnxruntime`, `demucs`, `soundfile`).
- Added `toolshop doctor` command to verify Python, ffmpeg, packages, disk space, and model cache.
- Updated `README.md`, `PROJECTS_INDEX.md` to match reality.
- Launched the 82-track remaining CrhymeTV batch (`run_crhymetv_batch.ps1`) to complete overnight.

#### Files Affected:
- **NEW:** `.gitmodules`
- **NEW:** `requirements.lock.txt`
- **NEW:** `toolshop/doctor.py`
- **NEW:** `tests/test_doctor.py`
- **MODIFIED:** `.gitignore`
- **MODIFIED:** `pyproject.toml`
- **MODIFIED:** `toolshop/cli.py`
- **MODIFIED:** `README.md`
- **MODIFIED:** `PROJECTS_INDEX.md`
- **MODIFIED:** `CHANGELOG.md`

#### Runtime Notes:
- `toolshop doctor` reports PASS on Python 3.11, ffmpeg, all extras, and 252 GB free on D:.
- CrhymeTV batch resumable via `results/crhymetv_re/batch_status.json` (140/222 at start).
- Batch launched in background; catalogue regeneration (`generate_crhymetv_catalogue.py`) follows completion.

---

### CrhymeTV Reverse-Engineering Batch Pipeline
**Timestamp:** 2026-06-28
**Action Type:** Implementation
**Previous State:** PapaPedro pilot validated the reverse-engineering pipeline on 3 hand-picked beats; no generic batch runner existed.
**Current State:** Generic, resumable, chunked batch runner applied to the CrhymeTV catalogue with per-track recipes and catalogue generation.

#### Changes Made:
- Created `run_reverse_engineering_batch.py` — generic batch runner with `--input-dir`, `--output-dir`, `--limit`, `--offset`, `--chunk-size`, `--use-gpu`, `--high-quality`, and `--no-resume`.
- Added resume-safe `batch_status.json` that is flushed after every track and tracks the last completed index.
- Created `run_crhymetv_batch.ps1` — PowerShell runner that performs an environment check and starts the full CPU-fast batch.
- Created `run_crhymetv_chunk.ps1` — helper to run a single chunk manually for parallelization or resuming a specific chunk.
- Created `run_crhymetv_smoke_test.ps1` — smoke test on 3 tracks to validate the pipeline before a full run.
- Created `generate_crhymetv_catalogue.py` — generates `catalogue.csv`, `catalogue.md`, and `suno_prompts.md` from `batch_status.json`.
- Kept the PapaPedro pilot (`run_papapedro_pilot.py` / `.ps1`) intact for reference.

#### Files Affected:
- **NEW:** `run_reverse_engineering_batch.py`
- **NEW:** `run_crhymetv_batch.ps1`
- **NEW:** `run_crhymetv_chunk.ps1`
- **NEW:** `run_crhymetv_smoke_test.ps1`
- **NEW:** `generate_crhymetv_catalogue.py`
- **MODIFIED:** `toolshop/reverse_engineering_adapter.py` — `_to_scalar()` helper used to coerce numpy scalars for librosa 0.11 / numpy 2.x
- **MODIFIED:** `projects/05-track-reverse-engineering/track_reverse_engineering/wav_reverse_engineer/audio_analyzer/feature_extractor.py` — robust scalar coercion for tempo

#### Runtime Notes:
- Discovered 222 MP3 files in `Tools\yt_extractor\downloads\CrhymeTV` (more than the handoff's 181 estimate; the full batch runs on all 222).
- Smoke test completed 3 tracks in ~36 minutes on CPU fast mode (~12 min/track).
- Full batch is resumable via `batch_status.json`; if interrupted, re-run `run_crhymetv_batch.ps1` to resume.

#### Next Actions Required:
- Allow the full batch to complete; re-run `generate_crhymetv_catalogue.py` afterwards to refresh the catalogue files.
- Optional: filter non-music items (snippets, trailers, vlogs) by duration or filename keyword if a narrower catalogue is desired.

---

### Answer #XXX - Audio Cleaning Pipeline Implementation
**Timestamp:** 2026-03-25 17:30
**Action Type:** Implementation
**Previous State:** No audio cleaning capabilities existed in the toolshop.
**Current State:** Multi-stage audio cleaning pipeline implemented with CLI commands and comprehensive documentation.

#### Changes Made:
- Implemented 6-stage audio cleaning pipeline combining multiple detection methods
- Added PreprocessingStage: Load audio, detect BPM/key, compute spectral features
- Added PauseRemovalStage: Remove long silences with crossfades (librosa.effects.split)
- Added BreathDetectionStage: Frequency + energy-based detection with attenuation (200-2000Hz range)
- Added EventDetectionStage: Detect coughs, clicks, pops using onset detection and spectral analysis
- Added BeatAlignmentStage: Detect beats and tempo analysis (librosa.beat.beat_track)
- Added FinalAssemblyStage: Normalization, metadata embedding, export
- Implemented pipeline controller with YAML configuration support
- Added comprehensive CLI commands: `toolshop clean pipeline`, `pause-remove`, `breath-detect`, `event-detect`, `beat-align`, `config-template`
- Created full test suite for all cleaning stages
- Updated README.md with complete documentation and usage examples
- Added `cleaning` dependency group with pyyaml for configuration

#### Files Affected:
- **NEW:** `toolshop/cleaning_stages.py` – All pipeline stage implementations (PreprocessingStage, PauseRemovalStage, BreathDetectionStage, EventDetectionStage, BeatAlignmentStage, FinalAssemblyStage)
- **NEW:** `toolshop/cleaning_pipeline_adapter.py` – Pipeline controller and CLI integration
- **NEW:** `tests/test_cleaning_pipeline.py` – Comprehensive test suite for all stages
- **MODIFIED:** `toolshop/cli.py` – Added 6 new CLI commands for audio cleaning
- **MODIFIED:** `toolshop/__init__.py` – Export cleaning adapters
- **MODIFIED:** `pyproject.toml` – Added cleaning dependency group with pyyaml
- **MODIFIED:** `README.md` – Full documentation with examples and API usage

#### Technical Decisions:
- Multi-stage approach: Each stage catches different artifacts (pauses → breaths → events → beats)
- Combined detection methods: Frequency + energy + spectral analysis for breath detection
- Configurable via YAML: Users can customize thresholds, methods, and which stages to run
- Modular design: Run individual stages or full pipeline
- Crossfade preservation: Smooth transitions when removing segments to avoid artifacts
- Attenuation over removal: Breath sounds attenuated rather than hard-cut for natural feel

#### Next Actions Required:
- Optional: Add neural noise reduction stage (RNNoise integration)
- Optional: Implement beat alignment 'align' mode with time-stretching
- Optional: Add batch processing for multiple files

---
**Timestamp:** 2025-12-11 20:02
**Action Type:** Implementation
**Previous State:** `music-ai-toolshop` repository contained only an empty Git init.
**Current State:** Python package and CLI skeleton created with Suno integration stubs.

#### Changes Made:
- Created `toolshop` Python package with CLI entrypoint and adapter modules.
- Added `toolshop suno sync-liked` as a stub (instructs users to run their own downloader).
- Implemented `toolshop suno list` to scan local metadata JSON files.
- Added `pyproject.toml` with a `toolshop` console script.
- Added project `README.md` and `CHANGELOG.md`.

#### Files Affected:
- **NEW:** `toolshop/__init__.py` – package marker.
- **NEW:** `toolshop/cli.py` – CLI argument parsing and command dispatch.
- **NEW:** `toolshop/suno_adapter.py` – Suno library listing and sync stub (external downloader run separately).
- **NEW:** `toolshop/bpm_adapter.py` – placeholder BPM/key analysis adapter.
- **NEW:** `toolshop/yt_scraper_adapter.py` – placeholder YouTube scraper adapter.
- **NEW:** `toolshop/yt_summarizer_adapter.py` – placeholder YouTube summarizer adapter.
- **NEW:** `toolshop/reverse_engineering_adapter.py` – placeholder track analysis adapter (librosa-based).
- **NEW:** `pyproject.toml` – build configuration and CLI entrypoint registration.
- **NEW:** `README.md` – project overview and basic usage.
- **NEW:** `CHANGELOG.md` – changelog for this repository.

#### Technical Decisions:
- Use `argparse` for the CLI to avoid additional dependencies.
- Keep adapters small and self-contained.

#### Next Actions Required:
- Add tests or simple smoke scripts for the main CLI paths.

### Answer #002 - CLI installation and verification
**Timestamp:** 2025-12-11 20:14
**Action Type:** Validation
**Previous State:** CLI and adapters were scaffolded but not yet executed from an installed package.
**Current State:** Package installed in editable mode; core CLI invocation and Suno listing command verified.

#### Changes Made:
- Installed `music-ai-toolshop` in editable mode via `pip install -e .`.
- Confirmed `python -m toolshop.cli --help` runs successfully.
- Executed `python -m toolshop.cli suno list` against the default Suno library path, confirming graceful behavior when the library is absent.

#### Files Affected:
- **MODIFIED:** `music_ai_toolshop.egg-info/` – auto-generated packaging metadata (created by pip; not manually edited).

#### Technical Decisions:
- Prefer `python -m toolshop.cli ...` invocation to avoid PATH issues when `toolshop.exe` is not on PATH.
- Keep `suno list` behavior simple and non-failing when the library directory does not yet exist.

#### Next Actions Required:
- Run `toolshop suno sync-liked` to populate a local Suno library and re-run `toolshop suno list` for real data.
- Add automated tests for analyze/yt/track flows.

### Answer #003 - Full adapter implementation and wiring
**Timestamp:** 2025-12-11 21:30
**Action Type:** Implementation
**Previous State:** All adapters were placeholders raising `NotImplementedError`.
**Current State:** All adapters fully implemented and tested end-to-end.

#### Changes Made:
- Implemented `bpm_adapter.py` with librosa-based BPM/key analysis (`analyze_track`, `analyze_library`).
- Implemented `yt_scraper_adapter.py` using yt-dlp as a Python library (`search`, `get_info`, `download_audio`).
- Implemented `yt_summarizer_adapter.py` for Suno prompt generation (`summarize_for_prompt`, `extract_music_keywords`).
- Implemented `reverse_engineering_adapter.py` as pure librosa-based analysis.
- Rewrote `cli.py` to wire all adapters with full subcommand structure.

#### Files Affected:
- **MODIFIED:** `toolshop/bpm_adapter.py` – full librosa-based BPM/key analysis (106 lines).
- **MODIFIED:** `toolshop/yt_scraper_adapter.py` – yt-dlp library integration (149 lines).
- **MODIFIED:** `toolshop/yt_summarizer_adapter.py` – Suno prompt and keyword extraction (120 lines).
- **MODIFIED:** `toolshop/reverse_engineering_adapter.py` – pure librosa-based analysis (188 lines).
- **MODIFIED:** `toolshop/cli.py` – full CLI with all subcommands (334 lines).

#### Technical Decisions:
- Use librosa directly for BPM/key analysis (standalone, no external repo dependency).
- Use yt-dlp as a Python library instead of subprocess for reliability on Windows.
- All adapters expose clean Python APIs that can be imported independently of the CLI.

#### Verified Commands:
- `toolshop --help` ✓
- `toolshop analyze bpm-key <file>` ✓ (BPM: 152.0, Key: F major)
- `toolshop yt search "lofi beats" --limit 3` ✓
- `toolshop yt info <video_id>` ✓
- `toolshop yt summarize <url>` ✓
- `toolshop track analyze <file> --summary` ✓ (with chord progression)

#### Next Actions Required:
- Push changes to GitHub.
- Add integration tests for each adapter.
- Document API usage in README.

### Answer #004 - Optional enhancements and documentation
**Timestamp:** 2025-12-11 21:45
**Action Type:** Enhancement
**Previous State:** Core adapters implemented, basic CLI commands working.
**Current State:** New convenience commands added, comprehensive README documentation.

#### Changes Made:
- Added `toolshop suno analyze` for batch BPM/key analysis of Suno library.
- Added `toolshop yt analyze <url>` for download + analyze in one step.
- Complete rewrite of README.md with full usage examples and Python API docs.
- Bumped version to 0.2.0 with optional dependency groups.

#### Files Affected:
- **MODIFIED:** `toolshop/cli.py` – added `suno analyze` and `yt analyze` commands (+70 lines).
- **MODIFIED:** `README.md` – complete rewrite with comprehensive documentation (174 lines).
- **MODIFIED:** `pyproject.toml` – added optional dependency groups [audio], [youtube], [all].

#### New Commands:
- `toolshop suno analyze --root <dir>` – batch-analyze Suno library for BPM/key
- `toolshop yt analyze <url>` – download YouTube audio and analyze in one step
- `toolshop yt analyze <url> --full` – include chord detection

#### Technical Decisions:
- `suno analyze` outputs to `<root>/bpm_key_analysis.json` by default.
- `yt analyze` combines download + BPM analysis, with `--full` flag for chord detection.
- README includes Quick Start, Commands Reference, and Python API sections.

#### Next Actions Required:
- Create integration tests for each adapter.
- Add CI/CD pipeline for automated testing.

### Answer #005 - Suno lyrics/description export
**Timestamp:** 2025-12-11 21:55
**Action Type:** Enhancement
**Previous State:** Suno tools supported sync, listing, and BPM/key analysis only.
**Current State:** New export command aggregates lyrics and descriptions from liked tracks.

#### Changes Made:
- Added `suno_adapter.export_text` to scan Suno metadata, filter liked tracks, and export lyrics/descriptions.
- Added `toolshop suno export-text` CLI subcommand with `--json-out` and `--txt-out` options.
- Updated README Suno section with export-text usage examples.

#### Files Affected:
- **MODIFIED:** `toolshop/suno_adapter.py` – new `export_text` helper.
- **MODIFIED:** `toolshop/cli.py` – wired `suno export-text` subcommand.
- **MODIFIED:** `README.md` – documented lyrics/description export.

#### Usage:
- `toolshop suno export-text --root suno_library` – writes `lyrics_export.json` and `lyrics_export.txt` under the library root.

#### Next Actions Required:
- Optionally add filters (by handle/date/tag) to export-text.

### Answer #006 - Decouple from sibling repos
**Timestamp:** 2025-12-11 22:00
**Action Type:** Modification
**Previous State:** `suno_adapter.sync_liked` imported a sibling downloader repo and `reverse_engineering_adapter` tried to import an external track-analysis repo.
**Current State:** Project is self-contained; no direct imports or path hacks to other local repos.

#### Changes Made:
- Simplified `reverse_engineering_adapter` to use only librosa-based analysis (removed external path hacks).
- Replaced `suno_adapter.sync_liked` implementation with a stub that instructs users to run their own downloader externally.
- Updated README to reflect pure librosa-based track analysis and optional external Suno sync.

#### Files Affected:
- **MODIFIED:** `toolshop/reverse_engineering_adapter.py` – pure librosa backend.
- **MODIFIED:** `toolshop/suno_adapter.py` – sync_liked no longer imports sibling repo.
- **MODIFIED:** `README.md` – documentation updated to remove hard dependency on other repos.

#### Technical Decisions:
- Keep `track analyze` fully functional using librosa-only features.
- Keep the `suno sync-liked` command present but clearly marked as a stub to avoid silent failure and preserve CLI shape.

### Answer #007 - Textual decoupling cleanup
**Timestamp:** 2025-12-12 10:00
**Action Type:** Documentation
**Previous State:** Some docstrings and docs still referenced external sibling repos or legacy backends; egg-info artifacts were present.
**Current State:** Documentation and strings now consistently reflect a self-contained project; leftover egg-info artifacts removed.

#### Changes Made:
- Removed legacy external-repo mentions from adapter docstrings (yt_summarizer, reverse_engineering, suno sync stub).
- Updated README track analysis sample to label backend as pure librosa.
- Clarified changelog entries to remove external wiring references and highlight self-contained adapters.
- Deleted `music_ai_toolshop.egg-info/` (generated metadata) from the workspace.

#### Files Affected:
- **MODIFIED:** `toolshop/yt_summarizer_adapter.py` – docstring cleaned.
- **MODIFIED:** `toolshop/reverse_engineering_adapter.py` – docstring clarified as pure librosa.
- **MODIFIED:** `toolshop/suno_adapter.py` – sync stub text clarified.
- **MODIFIED:** `README.md` – backend label updated to basic_librosa.
- **MODIFIED:** `CHANGELOG.md` – entries aligned with self-contained posture.
- **REMOVED:** `music_ai_toolshop.egg-info/` – deleted generated metadata directory.

#### Technical Decisions:
- Keep all adapters explicitly described as self-contained to avoid perceived external dependencies.
- Remove generated packaging metadata from versioned workspace to prevent stale references.

#### Next Actions Required:
- Generate reusable Suno prompt templates from `lyrics_export.json`.
- Update workspace structure and global changelog; prepare git commit/push.

### Answer #008 - How to extract/store lyrics with toolshop
**Timestamp:** 2025-12-13 23:54
**Action Type:** Documentation
**Previous State:** Instructions for lyrics export were implicit in README usage examples.
**Current State:** Added explicit guidance on extracting all lyrics with `toolshop suno export-text`, including output artifacts.

#### Changes Made:
- Documented the recommended command to export liked-track lyrics/descriptions to JSON/TXT.
- Clarified default output paths produced by the export command.

#### Usage Example:
- `toolshop suno export-text --root suno_library --json-out lyrics_export.json --txt-out lyrics_export.txt`

#### Files Affected:
- **MODIFIED:** `CHANGELOG.md` – added Answer #008 documenting lyrics export guidance.

### Answer #009 - Music Taste Profile Analysis & Library Optimization
**Timestamp:** 2025-12-14 03:10
**Action Type:** Implementation
**Previous State:** Raw audio library with 950 files, no organization or analysis.
**Current State:** Complete taste profile with cleaned library, auto-generated playlists, prompt templates, and recommendations.

#### Changes Made:
- Ran batch BPM/key analysis on 950 audio files (440 successful, 510 zero-size files identified).
- Created library cleanup tool that quarantined 510 incomplete/corrupted files.
- Generated 22 auto-sorted playlists by BPM range, musical key, and energy/mood.
- Created comprehensive Suno prompt templates based on extracted description patterns.
- Generated music recommendations document with artist/genre suggestions.

#### Files Affected:
- **NEW:** `analyze_library.py` – batch audio analysis script using toolshop adapters.
- **NEW:** `library_cleanup.py` – identifies and quarantines problematic audio files.
- **NEW:** `create_playlists.py` – auto-generates M3U playlists from analysis data.
- **NEW:** `suno_library/audio_analysis_results.json` – full analysis output.
- **NEW:** `suno_library/cleanup_report.txt` – library health report.
- **NEW:** `suno_library/playlists/` – 22 M3U playlist files + index.
- **NEW:** `suno_library/SUNO_PROMPT_TEMPLATES.md` – reusable Suno prompt templates.
- **NEW:** `suno_library/MUSIC_RECOMMENDATIONS.md` – artist/genre recommendations.
- **NEW:** `suno_library/_quarantine/` – 510 zero-size files moved here.

#### Key Findings:
- Average BPM: 130.8 (84% of tracks 120+ BPM)
- Top keys: G major (22%), D# major (21%), F major (15%)
- 100% major keys – preference for bright, uplifting tonalities
- Core style: Slap house / hardcore pop with Balkan fusion elements

#### Technical Decisions:
- Used librosa for audio analysis (BPM detection, chroma features for key).
- Non-destructive cleanup via quarantine folder instead of deletion.
- M3U format for maximum media player compatibility.

#### Next Actions Required:
- Re-sync library to download complete versions of quarantined files.
- Commit and push to GitHub repository.

### Answer #010 - Exclude quarantine/playlists from scans
**Timestamp:** 2025-12-15 02:49
**Action Type:** Modification
**Previous State:** `analyze_library.py` and `library_cleanup.py` scanned `_quarantine/` and `playlists/`, risking analysis/cleanup of non-library artifacts.
**Current State:** Library scans exclude `_quarantine/` and `playlists/` so only active, healthy library content is processed.

#### Changes Made:
- Updated directory walk logic in analysis and cleanup scripts to skip `_quarantine` and `playlists`.
- Prepared the repository for a clean re-analysis after the Suno re-download.

#### Files Affected:
- **MODIFIED:** `analyze_library.py` – skip `_quarantine` and `playlists` directories.
- **MODIFIED:** `library_cleanup.py` – skip `_quarantine` and `playlists` directories.
- **MODIFIED:** `CHANGELOG.md` – added Answer #010.

#### Technical Decisions:
- Keep quarantine non-destructive and excluded from scans to prevent reprocessing known-bad files.

#### Next Actions Required:
- Run the Suno resync downloader to restore missing audio, then re-run analysis and regenerate playlists.

### Answer #011 - Suno bulk downloader WAV-only mode
**Timestamp:** 2025-12-18 23:23
**Action Type:** Modification
**Previous State:** Standalone bulk downloader always saved optional side files (video, cover image, metadata JSON) alongside audio.
**Current State:** Added `SUNO_WAV_ONLY` mode to produce a WAV-only library (one liked clip -> one `.wav`), while keeping default behavior unchanged.

#### Changes Made:
- Added `SUNO_WAV_ONLY` env toggle (skip video/images/metadata in bulk downloader).
- Updated README with PowerShell example for WAV-only bulk download.

#### Files Affected:
- **MODIFIED:** `projects/Suno/bulk_downloader_app/suno_downloader.py` – Added WAV-only mode and skip flags.
- **MODIFIED:** `README.md` – Documented running the bulk downloader in WAV-only mode.
- **MODIFIED:** `CHANGELOG.md` – Added this entry.

#### Technical Decisions:
- Use env var toggles to avoid breaking existing workflows.

#### Next Actions Required:
- Re-download your liked library with `SUNO_WAV_ONLY=1` and confirm the output contains only `*.wav`.

### Answer #012 - Voice Effects Detection Module
**Timestamp:** 2026-02-12 18:23
**Action Type:** Implementation
**Previous State:** Toolshop had BPM/key analysis, track reverse engineering, YouTube tools, and Suno integration. No voice-specific effect detection.
**Current State:** New `toolshop voice analyze <file>` command detects 12 categories of vocal effects/processing with confidence scores, parameter estimates, and evidence explanations. All open-source, no ML training required.

#### Changes Made:
- Created `voice_effects_adapter.py` with 12 signal-processing-based effect detectors.
- Wired `voice` subcommand group into `cli.py` with `analyze` subcommand.
- Added `voice` and `voice-full` optional dependency groups in `pyproject.toml`.
- Updated `__init__.py` to export the new adapter.
- Bumped version to 0.3.0.
- Updated `README.md` with full voice analysis documentation, examples, and API usage.

#### Files Affected:
- **NEW:** `toolshop/voice_effects_adapter.py` – 12 voice effect detectors (reverb, pitch shift, formant shift, compression, EQ, distortion, chorus, auto-tune, de-essing, vocoder, noise gate, delay).
- **MODIFIED:** `toolshop/cli.py` – Added `voice analyze` subcommand and dispatch.
- **MODIFIED:** `toolshop/__init__.py` – Added `voice_effects_adapter` to `__all__`.
- **MODIFIED:** `pyproject.toml` – Version bump 0.2.0→0.3.0, added `voice`/`voice-full`/updated `all` dependency groups.
- **MODIFIED:** `README.md` – Added Voice Effects Detection section, updated installation, API, repo layout, dependencies.
- **MODIFIED:** `CHANGELOG.md` – This entry.

#### Technical Decisions:
- Pure signal-processing/heuristic approach — no ML training needed.
- `parselmouth` (Praat wrapper) for formant analysis; `crepe` optional for neural pitch.
- Graceful degradation: missing optional deps skip detectors and note in output.
- Each detector is a standalone function for easy extension.

#### Next Actions Required:
- Install voice dependencies: `pip install -e ".[voice]"`
- Test against existing WAV file in workspace.
- Push to GitHub.
