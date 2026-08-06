# Craft Implementation Plan — 10 New `toolshop lyrics` CLI Subcommands

**Author:** Implementation Planner Agent  
**Date:** 2026-08-07  
**Source reports:** 5 research handoffs in `.windsurf/handoffs/researcher_*_20260806.md`  
**Existing CLI:** `toolshop/cli.py` lines 826-983 (subparser definitions), 1757-2131 (dispatch)  
**Existing modules:** `rhyme_miner.py`, `lyricsdb.py`, `lyrics_metrics.py`, `lexicon.py`, `themes.py`, `flow_analyzer.py`, `lyrics_analyzer.py`, `syllables.py`, `fingerprint.py`

---

## Priority 1 — Build First (Uses Existing Infrastructure)

### B1. AI Lyric Quality Dashboard (`score-ai`)

**Command:** `toolshop lyrics score-ai --input <txt> [--cohort drill_trap|pop] [--json]`  
**Input flags:**
- `--input` (Path, required): Plain-text AI-generated lyrics
- `--cohort` (str, default `drill_trap`): Genre baseline for scoring
- `--json` (flag): JSON output instead of table

**Logic:**
1. Read input text, normalize via `lyricsdb.normalize_text()` (ASCII-fold + Cyrillic transliteration)
2. Parse sections using `lyricsdb.parse_section_label()` to detect `[Verse]`, `[Chorus]`, etc.
3. Compute structural metrics: sections/song, lines/song, lines/section — compare to cohort baseline from `song_metrics` table
4. Compute rhyme metrics: call `rhyme_miner.find_rhymes()` per section, `rhyme_miner.rhyme_factor()`, `rhyme_miner.multisyllabic_rhymes()`, `rhyme_miner.find_internal_rhymes()` — compare to cohort baseline from `song_rhyme_metrics` table
5. Compute lexical metrics: TTR via `lyrics_metrics.compute_song_metrics()` logic (tokenize, unique/total), avg syllables/line via `syllables.count_syllables()`
6. Compute repetition metrics: hook_repetition_ratio from line duplication counts
7. Normalize each component to 0-100 scale where 50 = genre average (z-score → linear map)
8. Weighted sum: Structural 25% + Rhyme 25% + Lexical 25% + Repetition 25%

**Output format:** Table with 4 component scores, overall score, and per-metric comparison to baseline (delta). JSON mode outputs full metric breakdown.

**New module:** `toolshop/ai_scorer.py` (~180 lines)  
**CLI integration:** Add `score-ai` subparser to `lyrics_subparsers` (after `collab`, ~line 983). Dispatch in `args.lyrics_command` if-elif chain (~line 1978).  
**Test file:** `tests/test_ai_scorer.py`  
**Dependencies:** Existing only — `rhyme_miner`, `lyricsdb`, `lyrics_metrics`, `syllables`, `sqlite3`

---

### B2. Cliché Density Checker (`cliches`)

**Command:** `toolshop lyrics cliches --input <txt> [--json]`  
**Input flags:**
- `--input` (Path, required): Plain-text lyrics file
- `--json` (flag): JSON output

**Logic:**
1. Read input text, normalize via `lyricsdb.normalize_text()`
2. Tokenize via `lyrics_analyzer._tokenize()` (lowercase word tokens)
3. Load cliché list from `lyrics_research/data/cliche_list.json`
4. Scan for English clichés (`english_cliches` + `english_extended`) and audio metadata tokens (`audio_metadata_tokens`) in token stream
5. Compute cliché density = (cliché token count / total tokens) × 100
6. Flag lines containing ≥1 cliché with line number and matched terms
7. Report audio token contamination separately (tokens like "female", "male", "chorus", "verse" that indicate Suno metadata leakage)

**Output format:** Table showing total cliché count, density %, per-line hits, audio token contamination count. JSON mode outputs structured per-line matches.

**New module:** `toolshop/cliche_checker.py` (~120 lines)  
**CLI integration:** Add `cliches` subparser to `lyrics_subparsers`. Dispatch in if-elif chain.  
**Test file:** `tests/test_cliche_checker.py`  
**Dependencies:** Existing only — `lyricsdb.normalize_text`, `lyrics_analyzer._tokenize`, `json`, `pathlib`

---

### B3. Structure Template Generator (`template`)

**Command:** `toolshop lyrics template --cohort drill_trap|pop [--sections N] [--json]`  
**Input flags:**
- `--cohort` (str, required, choices: `drill_trap`, `pop`): Genre template
- `--sections` (int, default 6): Target section count
- `--json` (flag): JSON output

**Logic:**
1. Query `lyrics.db` for cohort-specific section type distribution: `SELECT type, count(*) FROM sections JOIN songs ON sections.song_id = songs.id WHERE songs.genre_cohort = ? GROUP BY type`
2. Query average lines/section per type for the cohort
3. Query section ordering patterns: `SELECT group_concat(type, ' → ') FROM sections JOIN songs ... GROUP BY song_id` to find common progressions
4. Generate a template: section sequence (e.g., Intro → Verse → Chorus → Verse → Chorus → Outro), with target line counts per section
5. For pop cohort: enforce hook placement in first 30 seconds (Chorus by section 2)
6. For drill_trap cohort: allow longer intros, verse-dominant structure

**Output format:** Text template with section labels, target line counts, and notes. JSON mode outputs structured template array.

**New module:** `toolshop/structure_template.py` (~140 lines)  
**CLI integration:** Add `template` subparser to `lyrics_subparsers`. Dispatch in if-elif chain.  
**Test file:** `tests/test_structure_template.py`  
**Dependencies:** Existing only — `lyricsdb.DEFAULT_DB_PATH`, `sqlite3`

---

### B4. Audio Token Filter (`clean-tokens`)

**Command:** `toolshop lyrics clean-tokens --input <txt> [--output <txt>]`  
**Input flags:**
- `--input` (Path, required): Plain-text lyrics with audio metadata contamination
- `--output` (Path, default: stdout): Cleaned output path

**Logic:**
1. Read input text
2. Load audio metadata tokens from `lyrics_research/data/cliche_list.json` (`audio_metadata_tokens` list)
3. Scan each line for standalone audio tokens (e.g., `[female]`, `[male]`, `[chorus]`, `[verse]`, `[bass]`, `[kick]`, `[vox]`, `[bv]`, `[bar]`, `[fx]`, `[db]`, `[bars]`, `[vocal]`)
4. Remove bracketed and unbracketed token occurrences that match the audio token list
5. Remove empty lines left after token removal
6. Report removed tokens with line numbers

**Output format:** Cleaned lyrics text + summary of removed tokens (count, per-token frequency). If `--output` specified, write cleaned text to file and print summary.

**New module:** `toolshop/token_cleaner.py` (~90 lines)  
**CLI integration:** Add `clean-tokens` subparser to `lyrics_subparsers`. Dispatch in if-elif chain.  
**Test file:** `tests/test_token_cleaner.py`  
**Dependencies:** Existing only — `json`, `pathlib`, `re`

---

## Priority 2 — Requires New Logic

### B5. Slang Injection Post-Processor (`inject-slang`)

**Command:** `toolshop lyrics inject-slang --input <txt> --cohort drill_trap|pop [--density 0.05] [--json]`  
**Input flags:**
- `--input` (Path, required): Plain-text AI-generated lyrics
- `--cohort` (str, required, choices: `drill_trap`, `pop`): Target genre slang
- `--density` (float, default 0.05): Target slang token ratio (slang tokens / total tokens)
- `--json` (flag): JSON output with injection log

**Logic:**
1. Read input text, normalize via `lyricsdb.normalize_text()`
2. Query `slang_terms` table for cohort-distinctive terms: `SELECT term, distinctiveness FROM slang_terms WHERE cohort = ? ORDER BY distinctiveness DESC LIMIT 50`
3. Tokenize input, identify generic/high-frequency words that are NOT already slang
4. Replace candidate words with slang equivalents using a synonym mapping built from the slang lexicon (match by POS proximity — simplified: match by word length and position)
5. Track all replacements (original → slang term, line number)
6. Ensure final slang density approaches `--density` target
7. Output modified lyrics + injection log

**Output format:** Modified lyrics text + summary (injections made, final density, terms used). JSON mode outputs full injection log.

**New module:** `toolshop/slang_injector.py` (~200 lines)  
**CLI integration:** Add `inject-slang` subparser to `lyrics_subparsers`. Dispatch in if-elif chain.  
**Test file:** `tests/test_slang_injector.py`  
**Dependencies:** Existing only — `lyricsdb.normalize_text`, `lyrics_analyzer._tokenize`, `sqlite3`

---

### B6. Rhyme Scheme Enforcer (`check-scheme`)

**Command:** `toolshop lyrics check-scheme --input <txt> [--scheme AABB|ABAB|AABBCC] [--json]`  
**Input flags:**
- `--input` (Path, required): Plain-text lyrics
- `--scheme` (str, default None): Expected rhyme scheme pattern
- `--json` (flag): JSON output

**Logic:**
1. Read input text, normalize via `lyricsdb.normalize_text()`
2. Parse into sections using `lyricsdb.parse_section_label()`
3. For each section: call `rhyme_miner.find_rhymes()` to get end-rhyme pairs, then `rhyme_miner.infer_scheme()` to detect actual scheme
4. If `--scheme` provided: compare detected scheme to expected scheme, report mismatches per line (which lines break the pattern)
5. If no `--scheme`: report detected scheme per section with confidence score
6. Compute rhyme factor per section via `rhyme_miner.rhyme_factor()`
7. Suggest fixes for broken lines: show the rhyming word that breaks pattern + candidate words from same vowel skeleton (`rhyme_miner.vowel_skeleton()`)

**Output format:** Per-section table with detected scheme, expected scheme (if provided), match %, broken lines, and fix suggestions. JSON mode outputs structured per-section analysis.

**New module:** `toolshop/scheme_checker.py` (~160 lines)  
**CLI integration:** Add `check-scheme` subparser to `lyrics_subparsers`. Dispatch in if-elif chain.  
**Test file:** `tests/test_scheme_checker.py`  
**Dependencies:** Existing only — `rhyme_miner.find_rhymes`, `rhyme_miner.infer_scheme`, `rhyme_miner.rhyme_factor`, `rhyme_miner.vowel_skeleton`, `lyricsdb.parse_section_label`, `lyricsdb.normalize_text`

---

### B7. Few-Shot Example Retriever (`retrieve-similar`)

**Command:** `toolshop lyrics retrieve-similar --input <txt> --cohort drill_trap|pop [--top-k 5] [--json]`  
**Input flags:**
- `--input` (Path, required): Plain-text lyrics (AI-generated or draft)
- `--cohort` (str, required, choices: `drill_trap`, `pop`): Search within this genre
- `--top-k` (int, default 5): Number of similar songs to return
- `--json` (flag): JSON output

**Logic:**
1. Read input text, normalize via `lyricsdb.normalize_text()`
2. Build TF-IDF vector for input text using `sklearn.feature_extraction.text.TfidfVectorizer`
3. Query all song lyrics from `lyrics.db` for the specified cohort: join `songs → sections → lines`, concatenate `text_norm` per song
4. Build TF-IDF matrix for all cohort songs
5. Compute cosine similarity between input vector and all song vectors
6. Return top-K most similar songs with similarity score, artist name, song title, and a representative excerpt (first 4 lines of most similar section)
7. Format as few-shot prompt examples: "Here are professional lyrics in a similar style: ..."

**Output format:** Table with rank, artist, title, similarity score, excerpt. JSON mode outputs full few-shot prompt blocks ready for LLM input.

**New module:** `toolshop/similarity_retriever.py` (~170 lines)  
**CLI integration:** Add `retrieve-similar` subparser to `lyrics_subparsers`. Dispatch in if-elif chain.  
**Test file:** `tests/test_similarity_retriever.py`  
**Dependencies:** **NEW** — `scikit-learn` (TfidfVectorizer, cosine_similarity). Existing: `lyricsdb`, `sqlite3`

---

## Priority 3 — Research / Evaluation

### B8. Theme Distribution Comparator (`themes`)

**Command:** `toolshop lyrics themes --input <txt> --cohort drill_trap|pop [--json]`  
**Input flags:**
- `--input` (Path, required): Plain-text AI-generated lyrics
- `--cohort` (str, required, choices: `drill_trap`, `pop`): Compare against this cohort
- `--json` (flag): JSON output

**Logic:**
1. Read input text, normalize via `lyricsdb.normalize_text()`
2. Parse into sections using `lyricsdb.parse_section_label()`
3. Assemble per-section documents (same format as `themes.assemble_section_docs()`)
4. Load existing BERTopic model from `lyrics.db` (topics table) — use the model's transform method to predict topics for input sections
5. Compute input song's theme distribution (topic proportions)
6. Query cohort theme distribution from `section_topics` table: `SELECT topic_id, count(*) FROM section_topics JOIN sections ON section_topics.section_id = sections.id JOIN songs ON sections.song_id = songs.id WHERE songs.genre_cohort = ? GROUP BY topic_id`
7. Compute Jensen-Shannon Divergence between input distribution and cohort distribution
8. Report over-represented and under-represented themes vs cohort baseline

**Output format:** Table with JSD score, top-5 over-represented themes, top-5 under-represented themes. JSON mode outputs full topic distribution comparison.

**New module:** `toolshop/theme_comparator.py` (~150 lines)  
**CLI integration:** Add `themes` subparser to `lyrics_subparsers` (note: existing `themes` command at cli.py:2031 is `lyrics themes` for DB theme analysis — this new command needs a different name to avoid collision). **Use `theme-match` as the command name.** Dispatch in if-elif chain.  
**Test file:** `tests/test_theme_comparator.py`  
**Dependencies:** **NEW** — `bertopic`, `sentence-transformers` (already in `lyrics-nlp` extras). Existing: `themes.assemble_section_docs`, `lyricsdb`, `sqlite3`, `scipy` (for JSD)

---

### B9. Iterative Improvement Loop (`improve-loop`)

**Command:** `toolshop lyrics improve-loop --input <txt> --cohort drill_trap|pop [--iterations 3] [--target-score 65] [--json]`  
**Input flags:**
- `--input` (Path, required): Initial AI-generated lyrics
- `--cohort` (str, required, choices: `drill_trap`, `pop`): Genre target
- `--iterations` (int, default 3): Max improvement iterations
- `--target-score` (int, default 65): Stop when overall quality score reaches this
- `--json` (flag): JSON output with per-iteration metrics

**Logic:**
1. Run `ai_scorer.score_lyrics()` on input → baseline score
2. For each iteration (up to `--iterations`):
   a. Identify weakest component (Structural, Rhyme, Lexical, or Repetition)
   b. Generate improvement suggestions based on weakest component:
      - Structural: suggest section count adjustment via `structure_template.generate_template()`
      - Rhyme: suggest rhyme fixes via `scheme_checker.check_scheme()` broken-line suggestions
      - Lexical: suggest TTR adjustment (reduce repetition if TTR too low, add variety if too high)
      - Repetition: suggest hook placement changes
   c. Print suggestions for human review
   d. Accept revised input (either re-run with `--input` pointing to revised file, or interactive prompt for revised text)
   e. Re-score revised lyrics
   f. Track score delta per iteration
3. Stop when `--target-score` reached or `--iterations` exhausted
4. Report iteration history with score progression

**Output format:** Per-iteration table with component scores, overall score, weakest component, suggestions. JSON mode outputs full iteration log.

**New module:** `toolshop/improve_loop.py` (~180 lines)  
**CLI integration:** Add `improve-loop` subparser to `lyrics_subparsers`. Dispatch in if-elif chain.  
**Test file:** `tests/test_improve_loop.py`  
**Dependencies:** Existing (internal) — `ai_scorer.score_lyrics`, `structure_template.generate_template`, `scheme_checker.check_scheme`. No new external deps.

---

### B10. Centaur Co-Write Interface (Streamlit)

**Command:** `toolshop lyrics centaur [--port 8501]`  
**Input flags:**
- `--port` (int, default 8501): Streamlit port

**Logic:**
1. Launch a Streamlit app that provides an interactive co-writing interface
2. Left panel: lyrics text editor with real-time quality scoring (calls `ai_scorer.score_lyrics()` on each edit)
3. Right panel: quality dashboard with 4 component scores (radar chart), cliché highlights (calls `cliche_checker.check_cliches()`), rhyme scheme visualization (calls `scheme_checker.check_scheme()`)
4. Bottom panel: few-shot example retriever (calls `similarity_retriever.retrieve_similar()`) — displays professional lyrics in similar style
5. Slang injection button (calls `slang_injector.inject_slang()`) with adjustable density slider
6. Theme distribution comparison (calls `theme_comparator.compare_themes()`)
7. Export button: save current lyrics + quality report as JSON

**Output format:** Streamlit web app (interactive). No CLI text output beyond launch confirmation.

**New module:** `toolshop/centaur_app.py` (~250 lines)  
**CLI integration:** Add `centaur` subparser to `lyrics_subparsers`. Dispatch launches `streamlit run` subprocess.  
**Test file:** `tests/test_centaur_app.py` (smoke test: import + function existence)  
**Dependencies:** **NEW** — `streamlit`. Existing (internal): all P1/P2 modules, `plotly` (for radar chart — already available via `matplotlib` but `plotly` preferred for Streamlit)

---

## File Change Summary

| File | Type | Est. Lines | Description |
|------|------|-----------|-------------|
| `toolshop/cli.py` | **MODIFY** | +~200 | Add 10 subparsers (lines ~983+) + 10 dispatch blocks (lines ~1978+) |
| `toolshop/ai_scorer.py` | NEW | ~180 | B1: 4-component quality score |
| `toolshop/cliche_checker.py` | NEW | ~120 | B2: Cliché density checker |
| `toolshop/structure_template.py` | NEW | ~140 | B3: Structure template generator |
| `toolshop/token_cleaner.py` | NEW | ~90 | B4: Audio token filter |
| `toolshop/slang_injector.py` | NEW | ~200 | B5: Slang injection post-processor |
| `toolshop/scheme_checker.py` | NEW | ~160 | B6: Rhyme scheme enforcer |
| `toolshop/similarity_retriever.py` | NEW | ~170 | B7: Few-shot example retriever |
| `toolshop/theme_comparator.py` | NEW | ~150 | B8: Theme distribution comparator |
| `toolshop/improve_loop.py` | NEW | ~180 | B9: Iterative improvement loop |
| `toolshop/centaur_app.py` | NEW | ~250 | B10: Streamlit co-write interface |
| `tests/test_ai_scorer.py` | NEW | ~80 | B1 tests |
| `tests/test_cliche_checker.py` | NEW | ~60 | B2 tests |
| `tests/test_structure_template.py` | NEW | ~70 | B3 tests |
| `tests/test_token_cleaner.py` | NEW | ~50 | B4 tests |
| `tests/test_slang_injector.py` | NEW | ~80 | B5 tests |
| `tests/test_scheme_checker.py` | NEW | ~70 | B6 tests |
| `tests/test_similarity_retriever.py` | NEW | ~70 | B7 tests |
| `tests/test_theme_comparator.py` | NEW | ~60 | B8 tests |
| `tests/test_improve_loop.py` | NEW | ~80 | B9 tests |
| `tests/test_centaur_app.py` | NEW | ~40 | B10 smoke tests |
| `lyrics_research/data/cliche_list.json` | NEW | ~30 | Cliché data file (created separately) |

**Total new code:** ~1,690 lines across 10 new modules  
**Total new tests:** ~660 lines across 10 test files  
**Modified existing files:** 1 (`cli.py`)

---

## Dependency Check

### Already Installed (in `pyproject.toml` extras)

| Package | Extra | Used by |
|---------|-------|---------|
| `sqlite3` | stdlib | B1, B3, B5, B7, B8 |
| `requests` | `lyrics` | (existing) |
| `beautifulsoup4` | `lyrics` | (existing) |
| `cyrtranslit` | `lyrics` | B1, B5, B6 (via `lyricsdb.normalize_text`) |
| `langdetect` | `lyrics` | (existing) |
| `numpy` | `audio` | B1 (z-score normalization) |
| `scipy` | `audio` | B8 (JSD computation) |
| `matplotlib` | `track` | (existing, optional for B10) |
| `bertopic` | `lyrics-nlp` | B8 |
| `sentence-transformers` | `lyrics-nlp` | B8 |
| `umap-learn` | `lyrics-nlp` | B8 (via BERTopic) |
| `hdbscan` | `lyrics-nlp` | B8 (via BERTopic) |
| `torch` | `lyrics-nlp` | B8 (via sentence-transformers) |

### NOT Installed — Required by New Features

| Package | Used by | Install command |
|---------|---------|----------------|
| `scikit-learn` | B7 (`TfidfVectorizer`, `cosine_similarity`) | `pip install scikit-learn` |
| `streamlit` | B10 (Centaur co-write UI) | `pip install streamlit` |
| `plotly` | B10 (radar chart in Streamlit) | `pip install plotly` |

**Recommendation:** Add new `pyproject.toml` extra:
```toml
lyrics-craft = ["scikit-learn>=1.3", "streamlit>=1.30", "plotly>=5.18"]
```

---

## CLI Integration Pattern

All 10 new subparsers follow the existing pattern in `cli.py`:

```python
# Parser definition (after line 983, before end of lyrics_subparsers block)
lyrics_score_ai_parser = lyrics_subparsers.add_parser(
    "score-ai", help="Score AI-generated lyrics against genre baselines"
)
lyrics_score_ai_parser.add_argument("--input", type=Path, required=True, ...)
lyrics_score_ai_parser.add_argument("--cohort", type=str, default="drill_trap", ...)
lyrics_score_ai_parser.add_argument("--json", action="store_true", ...)

# Dispatch (in the args.lyrics_command if-elif chain, after line 1978)
elif args.lyrics_command == "score-ai":
    from toolshop.ai_scorer import score_lyrics
    result = score_lyrics(args.input, cohort=args.cohort)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_score_table(result)
```

**Note on `themes` collision:** The existing `lyrics themes` command (cli.py:2031) runs DB theme analysis. B8 uses `theme-match` as the command name to avoid collision.

---

## Build Order

1. **Phase 1 (P1):** B4 `clean-tokens` → B2 `cliches` → B3 `template` → B1 `score-ai`  
   (B4 and B2 first because they're simplest and validate the cliché data file; B1 last because it's the most complex P1 feature)

2. **Phase 2 (P2):** B6 `check-scheme` → B5 `inject-slang` → B7 `retrieve-similar`  
   (B6 first because it's pure rhyme_miner integration; B7 last because it needs scikit-learn)

3. **Phase 3 (P3):** B8 `theme-match` → B9 `improve-loop` → B10 `centaur`  
   (B9 depends on B1+B3+B6; B10 depends on all prior features)
