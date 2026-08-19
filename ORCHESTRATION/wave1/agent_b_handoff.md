# Agent B — German Corpus Expansion Feasibility Assessment

**Date:** 2026-08-08  
**Scope:** CrhymeTV catalogue analysis, lyricsgenius extractor compatibility, phonemizer-de requirements  
**Mode:** Read-only exploration. No files modified except this handoff.

---

## 1. CrhymeTV German Artists Found

### Catalogue Overview

The CrhymeTV catalogue is **100% German-language**. The `generate_crhymetv_catalogue.py` script hardcodes `"German rap / hip-hop"` in every Suno prompt (`build_suno_prompt()`, line 74). There is no language metadata field — language is implicit.

- **Total tracks:** 222 (221 completed + 1 skipped long)
- **Year range:** 2010–2026
- **BPM range:** 69.84 – 184.57
- **No language field** in catalogue CSV or batch_status.json — artist names and track titles are the only metadata

### All Unique Artists (from catalogue.csv)

The raw CSV contains ~110 unique "artist" strings, but many are collaboration variants (e.g., "BONEZ MC & RAF CAMORA feat. GZUZ" is a collab track, not a distinct artist). Below are the **core solo artists and groups** identified, normalized from the raw list:

| Artist | Solo Tracks (approx) | Notes |
|--------|---------------------|-------|
| **Bonez MC** | 14 + many collabs | Top artist; 187 Strassenbande member |
| **LX** | 12 + many collabs | 187 Strassenbande member |
| **GZUZ** | 8 + many collabs | 187 Strassenbande member |
| **Sa4** | 8 + collabs | 187 Strassenbande member |
| **Maxwell** | 6 + many collabs | 187 Strassenbande member |
| **RAF Camora** | 6+ (mostly collabs with Bonez MC) | Frequent collaborator, not 187SB member |
| **187 Strassenbande** | 9 (group tracks) | Hamburg rap crew/label |
| **Capuz** | 3+ | Early CrhymeTV artist |
| **Faruk111** | 3 | Early era |
| **111er** | 1 | — |
| **129ers** | 1 | — |
| **Nate57** | 1 (collab with Bonez MC) | — |

### Featured/Collaborator Artists (appear on tracks but not as primary)

Extracted from collab artist strings in the catalogue:

- Ufo361, Trettmann, Frauenarzt, Hanybal, Olexesh, Veysel, The Cratez (producers), Kwam.E, LAYÉ, Nizi19, Young Dolph, Estikay, Malik Montana, Ciiio, Koushino, Silva, Gallo Nero, Graci113, Hasan.K, Gringo, Caney030, Crackaveli, Alkar, VOLO, Addikt102, Stacks102, DJ Mac, Camaeleon, Driess, LEF

### Key Observation

The CrhymeTV catalogue is **entirely German drill/trap** centered on the 187 Strassenbande crew (Bonez MC, LX, GZUZ, Sa4, Maxwell) and their collaborators (especially RAF Camora). This is not a mixed-language catalogue — it is a dedicated German rap channel. All 222 tracks are German-language candidates for corpus expansion.

---

## 2. Extractor Compatibility Assessment

### Current Pattern (lyricsgenius extractor)

The extractor scripts follow a clean, repeatable pattern:

1. **`extract_artists.py`** (Batch 1): Defines `ARTISTS` list, `*_VARIANTS` sets, `categorize_song()` function, `save_song()` (shared), `fetch_artist_songs()` (shared). Uses `lyricsgenius.Genius.search_artist(name, max_songs=1000, sort="title", include_features=True, max_pages=50)`.

2. **`extract_batch2.py`** (Batch 2): Imports shared functions from batch 1. Uses dict-based artist config: `{"name": ..., "folder": ..., "variants": {...}}`. Categorizes as `{folder}-solo` or `{folder}-featured`.

3. **`extract_batch3.py`** (Batch 3): Identical pattern to batch 2. Adds Balkan artists (Devito, TNG, Voyage, Rasta, Maya Berović, Ana Nikolić, Breskvica, Henny).

### What Would Change for German Artists

**Minimal changes required.** The extractor is language-agnostic — it searches Genius by artist name and fetches whatever lyrics exist. Specific adjustments:

1. **Artist config entries**: Add German artists to the `ARTISTS` list in a new `extract_batch4_german.py`:
   ```python
   ARTISTS = [
       {"name": "Bonez MC", "folder": "bonez-mc", "variants": {"bonez mc", "bonez", "johannes"}},
       {"name": "RAF Camora", "folder": "raf-camora", "variants": {"raf camora", "raf camora 207", "raphael ragucci"}},
       {"name": "GZUZ", "folder": "gzuz", "variants": {"gzuz", "jonas glage"}},
       # ... etc.
   ]
   ```

2. **Name variants**: German artists have **fewer diacritic issues** than Serbian. Only ä/ö/ü/ß need variant handling:
   - "ä" → "ae" (e.g., "Hänel" → "Haenel")
   - "ö" → "oe" (e.g., "Grönland" → "Groenland")  
   - "ü" → "ue" (e.g., "Müller" → "Mueller")
   - "ß" → "ss" (e.g., "Straße" → "Strasse")
   - Most German rap artist names use ASCII-only stage names (Bonez MC, GZUZ, LX, Sa4, RAF Camora, Maxwell)

3. **`slugify()` function**: Already uses `[^\w\s-]` regex with `re.sub` — in Python 3, `\w` matches Unicode word characters, so ä/ö/ü/ß are preserved in slugs. No change needed.

4. **Section label parsing**: German Genius lyrics use `[Intro]`, `[Verse 1]`, `[Hook]`, `[Refrain]`, `[Bridge]` — same bracket format as English/Serbian. The existing parser in `save_song()` handles this generically.

5. **`normalize_text()` in lyricsdb.py**: Currently does Cyrillic transliteration + ASCII-fold. For German, this would **destroy umlauts** (ä→a, ö→o, ü→u). A German-specific normalization path is needed that:
   - Preserves umlauts OR converts them to digraphs (ä→ae, ö→oe, ü→ue, ß→ss)
   - Does NOT apply Cyrillic transliteration
   - The `_DIACRITIC_MAP` in `rhyme_miner.py:42-50` already maps ä→a, ö→o, ü→u — this is fine for vowel skeleton extraction but would need to be reviewed for other text processing

6. **Cohort assignment**: `COHORT_MAP` in `lyricsdb.py` would need a new cohort (e.g., `german_drill`) for the German artists.

7. **Output directory**: Same `data/toolshop/lyrics/genius/` with new subfolders (`bonez-mc-solo/`, `lx-solo/`, etc.)

### Verdict: HIGH COMPATIBILITY

The extractor pattern requires only a new batch script (`extract_batch4_german.py`) with artist config entries. No structural code changes. The `save_song()`, `fetch_artist_songs()`, `slugify()`, and `load_token()` functions are language-agnostic and reusable as-is.

---

## 3. phonemizer-de Requirements

### Why Vowel Skeletons Won't Work for German

The current `rhyme_miner.py` uses a **vowel-skeleton approach** (Malmi's Raplyzer method):

- Extracts vowels (a, e, i, o, u) + syllabic r from normalized Latin text
- Matches identical vowel sequences to detect rhymes
- Works because **Serbian orthography is nearly phonetic** — one letter ≈ one sound

**German is NOT phonetic.** Key problems:

| German spelling | Phonetic value | Skeleton extracts | Problem |
|----------------|---------------|-------------------|---------|
| `ei` | [aɪ] (diphthong) | `ei` (2 vowels) | Should be 1 rhyme unit; `ei` ≠ `ai` but both sound [aɪ] |
| `eu` | [ɔɪ] (diphthong) | `eu` (2 vowels) | `eu` ≠ `oi` but both can sound similar |
| `ie` | [iː] (long vowel) | `ie` (2 vowels) | Should be 1 rhyme unit; `ie` ≠ `ih` but both [iː] |
| `v` | [f] in "Vater", "viel" | — (consonant) | Consonant mismatch not captured |
| `s` before consonant | [ʃ] in "Stadt", "Spiel" | — (consonant) | Not captured |
| `sch` | [ʃ] | — (consonant) | Not captured |
| `ch` | [ç] or [x] | — (consonant) | Not captured |
| `ä` | [ɛ] or [eː] | `a` (via diacritic map) | `ä` ≠ `e` in skeleton but they rhyme |
| `ö` | [œ] or [øː] | `o` (via diacritic map) | `ö` ≠ `e` but can rhyme |
| `ü` | [ʏ] or [yː] | `u` (via diacritic map) | `ü` ≠ `i` but can rhyme in some dialects |
| `ß` | [s] | — (consonant) | Not a vowel issue, but normalization needs handling |

**Example failure**: "Zeit" (time, [tsaɪt]) and "leid" (sorry, [laɪt]) rhyme perfectly in German. Vowel skeletons: `ei` vs `ei` — this happens to work. But "Haus" ([haʊs]) and "Maus" ([maʊs]) → `au` vs `au` — also works. The real problem is **cross-spelling rhymes**: "rief" ([ʁiːf]) and "lieb" ([liːp]) → `ie` vs `ie` — works. But "wahr" ([vaːʁ]) and "Haar" ([haːɐ̯]) → `a` vs `aa` — mismatch in skeleton length despite perfect rhyme.

**More critical failure**: Assonance rhymes (common in German rap) like "Messer" and "fesser" → `ee` vs `ee` — works. But "Messer" and "Berg" → `ee` vs `e` — mismatch despite assonance. The skeleton approach cannot handle German's complex vowel-to-sound mapping.

### What German Needs: Real Phonemization

German requires **espeak-ng phonemization** to convert text to IPA/phoneme strings, then rhyme matching on phoneme sequences rather than vowel skeletons.

### espeak-ng German Voice Data: AVAILABLE

The existing espeak-ng installation at `data/toolshop/espeak-ng/` **already includes German support**:

- `espeak-ng-data/de_dict` — 68,276 bytes (German pronunciation dictionary)
- `espeak-ng-data/lang/gmw/de` — 42 bytes (German voice definition, West Germanic branch)

This means `phonemizer` can process German text with:
```python
from phonemizer import phonemize
from phonemizer.backend import EspeakBackend
backend = EspeakBackend('de')
phonemes = backend.phonemize(text)
```

The environment variables `PHONEMIZER_ESPEAK_PATH` and `PHONEMIZER_ESPEAK_LIBRARY` (already configured for Serbian espeak-ng) will work for German without any changes — espeak-ng supports all installed languages from a single binary.

### Implementation Path for German Rhyme Mining

1. **New module**: `rhyme_miner_de.py` (or language-parameterized `rhyme_miner.py`)
2. **Phoneme-based matching**: Use espeak-ng to convert text to IPA, then match rhyme units by phoneme similarity (not just identity)
3. **Diphthong handling**: German diphthongs (ei, eu, au) must be treated as single rhyme units in phoneme space
4. **Umlaut equivalence**: ä≈e, ö≈e (in certain contexts), ü≈i (in certain contexts) — phoneme-based matching handles this naturally
5. **Optional**: Slant rhyme detection via phoneme distance metrics (Steriade psychoacoustic model, per the rhyme/flow research report)

---

## 4. Recommended German Artist List

### Tier 1: CrhymeTV Catalogue Artists (confirmed German, already in catalogue)

These are the artists whose tracks are already reverse-engineered in the CrhymeTV batch. Extracting their Genius lyrics would provide text for the audio already analyzed:

| Artist | Genius Search Name | Folder | Variants |
|--------|-------------------|--------|----------|
| Bonez MC | "Bonez MC" | `bonez-mc` | `bonez mc`, `bonez` |
| RAF Camora | "RAF Camora" | `raf-camora` | `raf camora`, `raf camora 207` |
| GZUZ | "GZUZ" | `gzuz` | `gzuz`, `gzuz aka` |
| LX | "LX" | `lx` | `lx`, `lx 88` |
| Sa4 | "Sa4" | `sa4` | `sa4` |
| Maxwell | "Maxwell" | `maxwell` | `maxwell`, `maxwell 187` |
| 187 Strassenbande | "187 Strassenbande" | `187-strassenbande` | `187 strassenbande`, `187sb` |
| Capuz | "Capuz" | `capuz` | `capuz`, `capuz 16er` |

**Estimated yield**: 8 artists × ~50-150 songs each = ~400-800 songs (based on Genius catalog sizes for German rap artists)

### Tier 2: Known German Drill/Trap Artists (not in CrhymeTV, but genre-adjacent)

These artists are prominent in German rap/drill and would expand the corpus beyond the 187 Strassenbande circle:

| Artist | Why Include |
|--------|-------------|
| Apache 207 | Mainstream German rap star, huge Genius catalog |
| Capital Bra | Prolific (200+ songs on Genius), chart-dominant |
| Shirin David | Female German rapper, large catalog |
| SSIO | Underground respect, distinct style |
| Kollegah | Technical rap, complex rhyme schemes — benchmark for rhyme density |
| Farid Bang | Kollegah's frequent collaborator, battle rap background |
| Ufo361 | Already featured on CrhymeTV tracks, has solo catalog |
| Trettmann | Already featured on CrhymeTV tracks |
| Olexesh | Already featured on CrhymeTV tracks |
| Veysel | Already featured on CrhymeTV tracks |
| Hanybal | Already featured on CrhymeTV tracks, 187SB affiliate |
| Frauenarzt | Already featured on CrhymeTV tracks |

**Estimated yield**: 12 artists × ~50-200 songs = ~600-2000 songs

### Tier 3: Broader German Rap (for cross-cohort comparison)

| Artist | Why Include |
|--------|-------------|
| Trettmann | German reggae/dancehall-rap crossover |
| Bushido | German rap pioneer, large catalog |
| Shindy | Mainstream German rap |
| KC Rebell | German rap, Kurdish-German perspective |
| Summer Cem | KC Rebell collaborator |
| Mero | German rap, Turkish-German perspective |
| Samra | German rap, Berlin scene |
| Apache 207 | (already listed Tier 2) |

---

## 5. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Vowel skeleton approach fails for German** | HIGH | Must implement phoneme-based rhyme matching via espeak-ng before running rhyme analysis on German lyrics. Do NOT use `rhyme_miner.py` as-is on German text. |
| **`normalize_text()` destroys German umlauts** | HIGH | Add a German-specific normalization path in `lyricsdb.py` that converts ä→ae, ö→oe, ü→ue, ß→ss instead of stripping diacritics. Or skip normalization for German and let espeak-ng handle raw text. |
| **Genius API rate limits** | MEDIUM | Use `--delay 1.5` (existing default). 20 artists × ~100 songs = ~2000 requests at 1.5s = ~50 min. Token may expire mid-run — pre-validate. |
| **Artist name collisions on Genius** | LOW | "LX" is a common abbreviation; "Maxwell" could match other artists. Use `get_full_info=True` and verify primary artist matches via variants set. The existing `categorize_song()` pattern handles this. |
| **German lyrics with mixed language** (Turkish-German, English hooks) | LOW | Genius stores lyrics as-is; mixed-language content is natural in German rap. Rhyme analysis should focus on German-language sections. Consider language detection per line. |
| **espeak-ng phonemization quality for German rap** | MEDIUM | espeak-ng uses standard German pronunciation. Rap may use dialectal pronunciations (Hamburg slang, Berlin dialect). Phoneme output will be approximate but sufficient for rhyme detection. |
| **COHORT_MAP expansion** | LOW | Add `german_drill` cohort to `COHORT_MAP` in `lyricsdb.py`. Existing substring matching for duo/trio categorization will work for German collab tracks (e.g., "Bonez MC & RAF Camora"). |
| **Corpus size explosion** | LOW | 742 Balkan songs → +1000-2000 German songs. SQLite handles this fine. BERTopic and CLASSLA are Serbian-specific — German theme analysis would need a separate NLP pipeline (spaCy de, or GermaBERT). |
| **Section label language** | LOW | German Genius lyrics use English labels (Verse, Chorus, Hook) mixed with German (Refrain, Strophe). The existing `_TYPE_MAP` in `lyricsdb.py` may need a few additions (`refrain` → `chorus`, `strophe` → `verse`). |

---

## Summary

The CrhymeTV catalogue is **entirely German-language** — 222 tracks, all German rap/hip-hop, centered on 187 Strassenbande (Bonez MC, LX, GZUZ, Sa4, Maxwell) and RAF Camora. The lyricsgenius extractor is **highly compatible** — a new `extract_batch4_german.py` following the batch 2/3 pattern would work with minimal changes (artist config entries + German umlaut variant handling). The **critical blocker** is rhyme analysis: the vowel-skeleton approach in `rhyme_miner.py` cannot handle German's non-phonetic orthography. espeak-ng German voice data is already installed and ready. Implementation requires a phoneme-based rhyme miner for German before any rhyme density analysis can run.
