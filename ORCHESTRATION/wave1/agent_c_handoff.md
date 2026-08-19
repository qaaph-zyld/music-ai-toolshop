# Agent C — Flow Analyzer v1 Audit & v2 Requirements

**Date:** 2026-08-08  
**Scope:** `toolshop/flow_analyzer.py` + research docs + tool availability checks  
**Mode:** Read-only audit (no files modified except this handoff)

---

## 1. v1 Capabilities

**File:** `toolshop/flow_analyzer.py` (283 lines, commit `d868f0d`)

### Data Structures
- `SectionFlow` dataclass: section_type, section_number, line_count, avg_syllables, syllable_counts, pattern
- `FlowProfile` dataclass: song_id, title, artist, avg_syllables_per_line, syllable_density, speed_variation, pattern, sections[]

### Functions
1. **`detect_patterns(syllable_counts: List[int]) -> str`** — Classifies a sequence of per-line syllable counts into one of 5 patterns:
   - `uniform`: all lines within ±1 of mean
   - `alternating`: even/odd indexed lines form two groups with means ≥3 apart, each within ±2 of group mean (requires ≥4 lines)
   - `accelerating`: consecutive diffs all ≥-1 and total increase ≥ len(counts)
   - `decelerating`: consecutive diffs all ≤1 and total decrease ≤ -len(counts)
   - `free`: no clear pattern

2. **`section_flow(conn, section_id) -> SectionFlow`** — Queries `lines.syllable_count` joined to `sections` table, computes avg syllables and pattern per section.

3. **`flow_profile(conn, song_id) -> Dict`** — Full song profile:
   - `avg_syllables_per_line`: mean of all line syllable counts
   - `syllable_density`: avg_syllables / avg_words_per_line (ratio from `lines` table)
   - `speed_variation`: coefficient of variation (stdev/mean) of syllable counts
   - `pattern`: overall pattern from `detect_patterns`
   - `sections`: list of per-section flow dicts

4. **`artist_flow_summary(conn, artist=None) -> List[Dict]`** — Aggregates per-artist stats via SQL: song_count, avg_syllables_per_line, avg_density. **Stubbed**: `avg_speed_variation` hardcoded to 0, `dominant_pattern` hardcoded to `'free'` — these are not actually computed.

### Data Sources
- `lines.syllable_count` — from `syllables.py` counting
- `lines.word_count` — from text parsing
- `sections.type`, `sections.type_number` — from section label parser
- `songs.primary_artist`, `songs.title` — metadata

### v1 Limitations
1. **No timing data**: operates entirely on syllable counts per line — no word-level timestamps, no beat grid, no audio
2. **No microtiming analysis**: cannot detect laid-back vs eager delivery
3. **No triplet flow detection**: cannot identify 3-against-4 rhythmic patterns
4. **No tension-relaxation pacing**: cannot track rhyme pacing variation across a verse
5. **No rhyme integration**: flow is analyzed in isolation from rhyme placement
6. **`artist_flow_summary` is partially stubbed**: speed_variation and dominant_pattern are hardcoded placeholders
7. **Pattern detection is coarse**: only 5 categories based on syllable count trends, no rhythmic subdivision analysis
8. **No per-word or per-syllable granularity**: smallest unit is a line

---

## 2. v2 Requirements (from Research Reports)

### From Rhyme/Flow Craft Research (`researcher_rhyme_flow_craft_20260806.md`)

**Kendrick Tension-Relaxation Model** (§1, Technique #6):
- Faster rhyme pacing = tension; slower pacing = relaxation
- Four formal verse roles: Verse-Rhyming Block (stable rhymes on beats 2&4), Verse-Excursion (irregular off-beat), Verse-Crisis (intensifying syllables, shortening inter-rhyme intervals), Parenthetical Chorus (rhymes on beats 1&3)
- **v2 requirement**: Track rhyme frequency over time within a verse; detect inter-rhyme interval shortening (crisis) vs lengthening (relaxation)

**Migos Triplet Flow** (§6, Technique #14):
- Three syllables over one beat in cascading cadence
- Three types: mixed (interspersed), phrasal (triplet groups = phrases), total (entire verse)
- **v2 requirement**: Detect 3-against-4 rhythmic patterns from word-level timing; classify triplet density per section

**Microtiming: Laid-Back vs Eager** (§5, Technique #16-17):
- Laid-back: syllables systematically behind the beat (Snoop Dogg)
- Eager: syllables ahead of the beat (Lil B, Blueface)
- These are aesthetic choices, not errors
- **v2 requirement**: Compute per-word deviation from beat grid; positive deviation = laid-back, negative = eager; aggregate per-artist and per-section

**DOOM Time-Shifted Rhyme Placement** (§1, Technique #5):
- Second rhyme of a pair deliberately placed off-beat, spilling into next bar
- **v2 requirement**: Map rhyme landing positions to beat positions; detect off-beat rhyme placement

**Syncopation as Multi-Layer Interaction** (§5):
- Syncopation emerges from conflict between lyrics stress, delivery accents, and beat metric accents
- **v2 requirement**: Cross-reference word stress patterns with beat positions

### From AI Lyric Improvement Research (`researcher_ai_lyric_improvement_20260806.md`)

**Flow/Delivery Evaluation Findings**:
- PLOS One study: authentic lyrics have higher rhyme density (LO 0.25) and vowel harmony/assonance (LO 1.06); AI overfits on alliteration (LO -0.32) and word repetition (LO -0.83)
- Violet Recording's workflow step: "Sing the line as a placeholder melody and notice which words land on the strong beats" — this is exactly what word-level timing × beat grid alignment enables
- **v2 requirement**: Flow fingerprint per artist/section for comparing pro vs AI delivery patterns

### From Roadmap L6 (`2026-07-21-lyric-intelligence-roadmap-L3-L6.md:73-78`)
> "Ties into the H3 flow analyzer (whisperX word timings × beat grid) so text craft meets delivery craft."
> "The out-of-band flow analyzer v1 (commit d868f0d) lands here — review it when L6 opens, not before."

### From OSS Integration Map (`2026-07-15-oss-integration-map.md:74`)
> **Flow analyzer** — 🔨 BUILD (flagship). No OSS does this: whisperX word timings × beat_this grid → syllables/bar, on/off-beat placement, rhyme-scheme density, flow fingerprint per artist/section. Uniquely ours.

### From Longterm Roadmap (`2026-07-15-longterm-roadmap-v2.md:77-81`)
- T4 Vocal Lab v1 (H2): `toolshop voice transcribe` via faster-whisper (model size configurable, int8 default); timed-lyrics artifact shared with T2
- T4 Vocal Lab v1.1 (H3): lyrics↔beat-grid alignment (bars/phrases); vocal QC bridge to mastering_tool

---

## 3. Available Tools: whisperX vs faster-whisper

### whisperX
- **Status:** NOT INSTALLED in `.venv` (ModuleNotFoundError confirmed)
- **Purpose:** Forced alignment — takes audio + transcript text, produces word-level timestamps with high precision
- **CPU viability:** Possible but slow; designed for GPU. Uses pyannote for diarization (needs HF token)
- **Deps:** Pulls heavy dependencies (pyannote, torch, torchaudio)
- **Risk noted in OSS map:** "whisperX/pyannote pulls heavy deps; pyannote needs HF token — Use alignment-only path (no diarization) unless needed; pin versions in lock"
- **License:** BSD

### faster-whisper
- **Status:** NOT INSTALLED in `.venv` (ModuleNotFoundError confirmed)
- **Purpose:** CTranslate2-based Whisper inference; provides word-level timestamps natively via `transcribe(word_timestamps=True)`
- **CPU viability:** Yes — CTranslate2 int8 quantization is designed for CPU inference. Documented path in OSS map: "CPU int8 documented path; <100 ms word timestamps"
- **Deps:** CTranslate2 (lighter than torch/pyannote)
- **License:** MIT
- **Roadmap plan:** T4 Vocal Lab v1 uses faster-whisper as the transcription tool (H2 milestone)

### Recommendation
**faster-whisper is the primary path** for v2:
1. CPU-viable with int8 quantization (matches locked CPU-only constraint)
2. Provides word-level timestamps natively without forced alignment
3. Lighter dependency tree than whisperX
4. Already planned in roadmap (T4 v1, H2)
5. MIT license

**whisperX as optional enhancement** for higher-precision alignment if needed later (alignment-only path, no diarization, to avoid pyannote HF token dependency).

---

## 4. v2 Architecture Proposal

### Pipeline Overview
```
Audio (vocal stem) → faster-whisper (int8) → word-level timestamps
                                              ↓
Audio (full mix)  → beat_this/librosa      → beat grid (BPM, downbeats)
                                              ↓
                                    Alignment: word start/end → beat position
                                              ↓
                                    ┌─────────────────────┐
                                    │ Microtiming Analysis │  (deviation from grid)
                                    │ Triplet Detection    │  (3-against-4 patterns)
                                    │ Tension-Relaxation   │  (rhyme pacing over verse)
                                    │ Flow Fingerprint     │  (per artist/section)
                                    └─────────────────────┘
```

### Component Details

**1. Word-Level Timings (faster-whisper, int8)**
- Input: vocal stem (from existing stem separation pipeline)
- Output: list of `{word, start_time, end_time, confidence}` per line
- Model: `large-v3` int8 (multilingual — German strong, Serbian usable per OSS map)
- CPU budget: <100ms word timestamps claimed; measure per-track on this machine
- Adapter: `toolshop/whisper_adapter.py` (following existing adapter pattern)

**2. Beat Grid (from T2 Dossier)**
- Source: `beat_this` ONNX model (ISMIR-2024, planned H2) or librosa fallback (already in `bpm_adapter.py`)
- Output: `{bpm, downbeat_positions, beat_positions}` as time array
- Existing: `bpm_adapter.py` already computes BPM via librosa; beat_this adds downbeat detection
- No beat grid table exists in lyrics.db yet

**3. Alignment: Word → Beat Position**
- For each word with `start_time` and `end_time`:
  - Map to nearest beat position in beat grid
  - Compute `beat_position` (e.g., beat 2.5 of bar 4)
  - Compute `deviation_ms` = word_start - nearest_beat_time
- Output: aligned `{word, beat_bar, beat_position_in_bar, deviation_ms, on_beat: bool}`

**4. Microtiming Analysis**
- Per-word deviation from beat grid:
  - Positive deviation = laid-back (behind the beat)
  - Negative deviation = eager (ahead of the beat)
  - |deviation| < threshold (e.g., 30ms) = on-beat
- Per-section aggregation: mean deviation, std, % laid-back vs eager vs on-beat
- Per-artist signature: distribution of deviations across all songs

**5. Tension-Relaxation Pacing**
- Track rhyme landing positions over verse timeline
- Inter-rhyme interval (IRI): time (or beats) between consecutive rhyme landings
- Decreasing IRI = tension (Verse-Crisis pattern)
- Increasing IRI = relaxation
- Correlate with syllable density acceleration/deceleration (already in v1)
- Output: pacing curve per verse, classified into Kendrick's 4 formal roles

**6. Triplet Flow Detection**
- From word-level timings: compute syllables-per-beat ratio
- 3 syllables in 1 beat = triplet
- Classify sections: mixed (<30% triplets), phrasal (30-70%, grouped), total (>70%)
- Output: triplet density per section, triplet type classification

**7. Flow Fingerprint**
- Combine: avg syllables/bar, microtiming signature, triplet density, rhyme pacing curve, on-beat ratio
- Per-artist and per-section fingerprint vector
- Enables: artist comparison (like rhyme fingerprint in L2.1), pro vs AI delivery comparison

### DB Schema Additions (proposed)
```sql
CREATE TABLE IF NOT EXISTS word_timings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id     INTEGER NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    ordinal     INTEGER NOT NULL,
    word        TEXT,
    start_time  REAL,   -- seconds
    end_time    REAL,
    confidence  REAL
);

CREATE TABLE IF NOT EXISTS beat_grids (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id     INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    bpm         REAL,
    beat_times  TEXT,   -- JSON array of beat timestamps
    downbeat_times TEXT, -- JSON array of downbeat timestamps
    source      TEXT    -- 'beat_this' or 'librosa'
);

CREATE TABLE IF NOT EXISTS word_beat_alignment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    word_timing_id  INTEGER NOT NULL REFERENCES word_timings(id) ON DELETE CASCADE,
    beat_grid_id    INTEGER NOT NULL REFERENCES beat_grids(id) ON DELETE CASCADE,
    bar_number      INTEGER,
    beat_in_bar     REAL,   -- e.g., 1.0, 2.5 (off-beat)
    deviation_ms    REAL,   -- positive = laid-back, negative = eager
    on_beat         INTEGER -- 0 or 1
);
```

---

## 5. Data Gaps

### What's Already in lyrics.db (usable for v2 without whisperX)

| Table | Fields Available | v2 Use |
|-------|-----------------|--------|
| `lines` | `syllable_count`, `word_count`, `text_norm` | Syllable density (v1 baseline), word-level text for alignment |
| `sections` | `type`, `type_number`, `ordinal`, `performers` | Section-level flow profiles, collab attribution |
| `songs` | `primary_artist`, `genre_cohort` | Per-artist and per-cohort flow comparison |
| `song_metrics` | `avg_syllables_per_line`, `ttr`, `line_count` | Song-level aggregates |
| `line_rhymes` | `line_id`, `rhyme_type`, `match_length`, `skeleton` | Rhyme placement for tension-relaxation pacing |
| `song_rhyme_metrics` | `rhyme_factor`, `pct_multis`, `internal_rhyme_count` | Rhyme density per song |

### What's Missing (requires new data collection)

| Gap | What's Needed | Source |
|-----|--------------|--------|
| **Word-level timestamps** | Per-word start/end times | faster-whisper on vocal stems |
| **Beat grid** | BPM + beat/downbeat positions | beat_this ONNX or librosa `beat_track` |
| **Audio files for corpus** | Vocal stems for 742 Genius lyrics songs | NOT in corpus — Genius lyrics are text-only, no audio |
| **Word-beat alignment** | Mapping words to beat positions | Computed from timestamps × beat grid |
| **Microtiming data** | Per-word deviation from beat | Computed from alignment |
| **BPM per song** | Tempo for each song in lyrics corpus | `bpm_adapter.py` exists but lyrics.db has no BPM column — audio files not available for Genius corpus |

### Critical Gap: No Audio for Genius Corpus
The 742-song Genius lyrics corpus is **text-only** — there are no audio files to run transcription or beat detection on. This means:
- v2's full pipeline (word timings × beat grid) requires audio that doesn't exist for the lyrics corpus
- v2 can only be applied to tracks where we have audio (CrhymeTV batch, Suno downloads, own releases)
- For the Genius corpus, v2 can only use text-based proxies (syllable density patterns, rhyme spacing from `line_rhymes`)

### What v2 Can Do Without Audio (text-only path)
Using existing `line_rhymes` + `lines` + `sections` data:
1. **Rhyme pacing proxy**: inter-rhyme interval in *lines* (not beats) — decreasing line-interval = tension
2. **Syllable acceleration** (already in v1): accelerating pattern = tension, decelerating = relaxation
3. **Rhyme placement density**: rhymes per line per section — correlates with tension-relaxation
4. **Triplet proxy**: high syllable_count + high internal_rhyme_count per line may indicate triplet-style delivery

---

## 6. Dependencies & Risks

### Dependencies
| Dependency | Status | Install Needed | Notes |
|-----------|--------|---------------|-------|
| faster-whisper | NOT installed | `pip install faster-whisper` | MIT, CTranslate2 int8, CPU-viable |
| CTranslate2 | NOT installed | (comes with faster-whisper) | Inference engine |
| beat_this (CPJKU) | NOT installed | Separate integration (H2) | ONNX model, onnxruntime |
| onnxruntime | Unknown | Check if already present | For beat_this |
| librosa | Installed | — | Already in `bpm_adapter.py` as fallback |
| Audio files | Missing for Genius corpus | — | Critical gap for full v2 |

### Risks
1. **No audio for Genius corpus**: The 742-song lyrics database has no corresponding audio. Full v2 (word timings × beat grid) can only run on tracks with audio (CrhymeTV, Suno, own releases). Text-only v2 features are limited to proxies.
2. **CPU cost unknown**: faster-whisper int8 on CPU for a 3-4 min track — needs measurement before committing to batch processing. OSS map says "<100ms word timestamps" but full transcription time per track is unspecified.
3. **Serbian transcription quality**: faster-whisper multilingual model — German strong, Serbian "usable" per OSS map. Quality of word-level timestamps for Serbian/Bosnian vocals is untested.
4. **beat_this integration is H2 milestone**: Beat grid with downbeats requires beat_this ONNX model which is planned for H2. v2 flow analyzer is H3. Sequencing: beat_this must land first.
5. **whisperX heavy deps**: If higher-precision alignment is needed later, whisperX pulls pyannote (HF token required), torch, torchaudio. Use alignment-only path to minimize deps.
6. **Corpus mismatch**: v1 operates on text-only Genius corpus (742 songs). v2 full pipeline operates on audio corpus (different songs). Bridging the two requires either (a) obtaining audio for Genius corpus songs, or (b) building a separate audio-based flow corpus.
7. **AGENTS.md constraint**: "Do not introduce new third-party audio/ML deps outside that map without user sign-off." faster-whisper and beat_this are both in the OSS map, so no blocker — but installation requires explicit authorization.

### Sequencing Recommendation
1. **Phase 1 (text-only v2 enhancements)**: Implement tension-relaxation pacing proxy and rhyme placement density using existing `line_rhymes` data — no new deps, no audio needed
2. **Phase 2 (after H2 faster-whisper integration)**: Add word-level timestamps for tracks with audio; implement microtiming analysis
3. **Phase 3 (after H2 beat_this integration)**: Add beat grid alignment; implement triplet flow detection and full flow fingerprint
4. **Phase 4**: Cross-corpus analysis: compare text-based flow proxies (Genius) with audio-based flow metrics (CrhymeTV/Suno)

---

## Summary

Flow analyzer v1 is a text-only syllable-count pattern detector with 5 coarse categories. v2 requires word-level timestamps (faster-whisper, not installed, CPU-viable) and beat grids (beat_this, H2 milestone) to unlock microtiming analysis, triplet flow detection, and tension-relaxation pacing. The critical gap is that the 742-song Genius lyrics corpus has no audio — full v2 can only run on tracks with audio files. A phased approach is recommended: text-only v2 enhancements first (using existing rhyme data), then audio-based features after H2 dependencies land.
