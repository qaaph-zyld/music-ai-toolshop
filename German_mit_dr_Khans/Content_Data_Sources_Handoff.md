# Content & Data Sources Handoff

> **Research deliverable for the German learning desktop app (Tauri 2 + React + TS)**
> Generated: 2026-08-02
> Companion to: `existing_apps_analysis_and_gap_handoff.md`

---

## Table of Contents

1. [Vocabulary Datasets — Deep Evaluation](#1-vocabulary-datasets--deep-evaluation)
2. [Recommended Primary Datasets (Ranked)](#2-recommended-primary-datasets-ranked)
3. [Grammar Content Sources](#3-grammar-content-sources)
4. [Audio Sources & Strategy](#4-audio-sources--strategy)
5. [Reading Content Sources](#5-reading-content-sources)
6. [Listening Content Sources](#6-listening-content-sources)
7. [Complete Licensing Analysis](#7-complete-licensing-analysis)
8. [Content Integration Strategy](#8-content-integration-strategy)
9. [Data Pipeline Architecture](#9-data-pipeline-architecture)
10. [Estimated Bundled Content Size](#10-estimated-bundled-content-size)
11. [Next Steps for Orchestrator](#11-next-steps-for-orchestrator)

---

## 1. Vocabulary Datasets — Deep Evaluation

### 1.1 German Language Community Dataset

| Attribute | Detail |
|---|---|
| **Source** | [github.com/IamHamud/German-Language-Community](https://github.com/IamHamud/German-Language-Community) |
| **Size** | 8,242 words, 365 grammar rules, 2,300 sentences, 43 alphabet entries |
| **CEFR Coverage** | A1 (834), A2 (1,408), B1 (2,000), B2 (2,000), C1 (2,000) |
| **Data Format** | JSONL (one JSON object per line), organized by CEFR level in separate files |
| **License** | CC BY-SA 4.0 (vocabulary, from Wiktionary), CC BY 2.0 FR (sentences, from Tatoeba) |
| **Quality** | Community-maintained by a single learner (self-admitted possible inaccuracies). Vocabulary imported from Wiktionary, sentences from Tatoeba, grammar rules written manually |
| **Completeness** | Each vocab entry: german, english, gender, pos, example_de, example_en. Grammar: rule_id, category, rule, explanation, examples. Sentences: sentence_de, sentence_en, cefr_level, word_count, grammar_features |
| **How to Obtain** | Clone GitHub repo. Data in `data/` as `.jsonl` files. Also via REST API (unreliable for bulk) |
| **Strengths** | Pre-tagged CEFR, includes grammar + sentences, JSONL easy to parse |
| **Weaknesses** | Single-author quality, no IPA, no plurals, no conjugations, no audio, C1/C2 thin |

### 1.2 Grundwortschatz-voc-de

| Attribute | Detail |
|---|---|
| **Source** | [HuggingFace: cstr/grundwortschatz-voc-de](https://huggingface.co/datasets/cstr/grundwortschatz-voc-de) |
| **Size** | 10,450 lemmas (13k words, 27.6k translations, 24.5k examples) |
| **CEFR Coverage** | No explicit CEFR. grade_level 1–6 (NRW Grundwortschatz). Grade 1–2≈A1, 3–4≈A2, 5–6≈B1 |
| **Data Format** | SQLite (`grundwortschatz.db.gz`, ~19 MB compressed, ~122 MB uncompressed). Parquet export available |
| **License** | GPL-3.0 (re-distribution of CC BY-SA Wiktionary data) |
| **Quality** | High — curated from ~100k Wiktionary lemmas, filtered through multi-corpus intersection. Enriched with spaCy POS, IPA, inflections, synonyms, OpenThesaurus, ConceptNet, spelling patterns |
| **Completeness** | Per-word: word, lemma, article, genus, word_type, grade_level, audio_path, frequency_json, enrichment_json (IPA, examples, inflections, syn/ant, hyper/hypo), metadata_json |
| **How to Obtain** | Download from HuggingFace, decompress gzip, open with SQLite |
| **Strengths** | Richest per-word annotation. SQLite native. Frequency data from multiple corpora. IPA, inflections, synonyms included |
| **Weaknesses** | GPL-3.0 (copyleft). No explicit CEFR tags. Primary-school focus, may lack C1–C2. Audio paths may be empty |

### 1.3 DAFlex (CEFRLex)

| Attribute | Detail |
|---|---|
| **Source** | [cental.uclouvain.be/cefrlex/daflex/](https://cental.uclouvain.be/cefrlex/daflex/) |
| **Size** | 41,646 entries (lemma + POS pairs) |
| **CEFR Coverage** | **A1 through C2** — the only source with full C2 coverage |
| **Data Format** | Online query interface + downloadable. Fields: lemma, POS, level_freq (per 1M words per CEFR level), total_freq, nb_doc |
| **License** | Academic resource (CENTAL, UCLouvain). License not explicitly stated — contact authors for redistribution |
| **Quality** | High — built from CEFR-labeled textbook corpus. Robust frequency estimation with dispersion index. Manual postprocessing |
| **Completeness** | Lemma + POS + per-level frequency only. No translations, IPA, examples, gender, inflections |
| **How to Obtain** | Query online or contact authors for bulk download |
| **Strengths** | Only A1–C2 source. Frequency-based CEFR assignment. Academic quality |
| **Weaknesses** | No enrichment data. License unclear for redistribution. No bulk download link. Receptive vocabulary only |

### 1.4 DWDS Goethe Word Lists

| Attribute | Detail |
|---|---|
| **Source** | [DWDS](https://www.dwds.de/lemma/wortschatz-goethe-zertifikat) — A1, A2, B1 |
| **Size** | A1: ~650, A2: ~1,200, B1: ~2,000 entries |
| **CEFR Coverage** | A1, A2, B1 only |
| **Data Format** | CSV/JSON via DWDS API. Goethe-Institut PDFs also available |
| **License** | **Goethe-Institut copyrighted** — explicitly stated on DWDS |
| **Quality** | Authoritative — official Goethe-Institut exam vocabulary |
| **How to Obtain** | DWDS API or Goethe-Institut PDFs |
| **Strengths** | Gold-standard CEFR vocabulary, machine-readable via DWDS API |
| **Weaknesses** | **Cannot bundle** (copyrighted). Only A1–B1. No translations or enrichment |

### 1.5 Wiktionary German

| Attribute | Detail |
|---|---|
| **Source** | [kaikki.org/dictionary/German/](https://kaikki.org/dictionary/German/) (pre-extracted) + [dumps.wikimedia.org/dewiktionary/](https://dumps.wikimedia.org/dewiktionary/latest/) (raw) |
| **Size** | English edition: 628,954 senses, ~1 GB JSONL. German edition: 2.8 GB JSONL (~286 MB compressed) |
| **CEFR Coverage** | None — covers all German words |
| **Data Format** | Pre-extracted JSONL via [wiktextract](https://github.com/tatuylonen/wiktextract) or [wiktionary-de-parser](https://github.com/gambolputty/wiktionary-de-parser). Extracts: IPA, inflections, POS, definitions, translations, audio links, synonyms, antonyms, examples |
| **License** | CC BY-SA 3.0 |
| **Quality** | Very high for linguistic data (IPA, inflections). Variable for definitions |
| **How to Obtain** | Download pre-extracted JSONL from kaikki.org (easiest) or parse raw XML dumps |
| **Strengths** | Largest free German lexical resource. IPA, inflections, audio links, definitions, translations. Pre-extracted data saves parsing. CC BY-SA bundleable |
| **Weaknesses** | No CEFR levels. Large volume (needs filtering). German edition has German glosses |

### 1.6 FreeDict German-English

| Attribute | Detail |
|---|---|
| **Source** | [freedict.org/downloads/](https://freedict.org/downloads/) |
| **Size** | German→English: 517,534 headwords |
| **Data Format** | TEI XML (structured, convertible to dictd/slob) |
| **License** | GPL (majority) — check TEI header per dictionary |
| **Quality** | Mixed — some hand-crafted, some imported. No IPA, no inflections, no examples |
| **How to Obtain** | Download TEI XML from freedict.org |
| **Strengths** | Very large (517k). Well-structured TEI XML. Good for word lookup |
| **Weaknesses** | GPL (copyleft). No linguistic enrichment. No CEFR. Translation-only |

### 1.7 Wikimedia Commons / Lingua Libre Audio

| Attribute | Detail |
|---|---|
| **Source** | [Commons: Lingua Libre pronunciation-deu](https://commons.wikimedia.org/wiki/Category:Lingua_Libre_pronunciation-deu) |
| **Size** | 25,431 German pronunciation files |
| **Data Format** | OGG/WAV/MP3/FLAC on Wikimedia Commons |
| **License** | CC BY-SA 4.0 (most files) |
| **How to Obtain** | Bulk download via Lingua Libre datasets page or Petscan + Wikiget (~15k files/hour) |
| **Strengths** | Human recordings. CC BY-SA. Free |
| **Weaknesses** | Incomplete (25k vs 100k+ words). Variable quality. OGG format. No CEFR tags |

### 1.8 Other Sources

| Source | Description | License |
|---|---|---|
| **Tatoeba** | ~331,266 German-English sentence pairs | CC BY 2.0 FR |
| **OpenSubtitles frequency** | German word frequency from subtitles | CC BY-SA |
| **LibriVox** | Public domain German audiobooks | Public domain / CC BY |

---

## 2. Recommended Primary Datasets (Ranked)

| Rank | Dataset | Role | Justification |
|---|---|---|---|
| **1** | **Wiktionary (kaikki.org)** | **Master lexical DB** | Largest free German lexical resource (628k senses). IPA, inflections, definitions, translations, audio links. CC BY-SA 3.0. Pre-extracted JSONL eliminates parsing effort |
| **2** | **Grundwortschatz-voc-de** | **Enriched vocab core** | 10,450 curated lemmas with richest annotation: IPA, inflections, frequency, synonyms, OpenThesaurus. SQLite native. Grade level ≈ CEFR proxy |
| **3** | **German Language Community** | **CEFR starter + grammar** | Pre-tagged A1–C1. 8,242 words + 365 grammar rules + 2,300 sentences. JSONL. Use as initial CEFR import and grammar source |
| **4** | **DAFlex (CEFRLex)** | **CEFR assignment engine** | Only A1–C2 frequency data. 41,646 entries. Use to assign/validate CEFR for all other sources. Contact authors for bulk access |
| **5** | **Tatoeba** | **Sentence bank** | ~331k German-English pairs. CC BY 2.0 FR. Use for cloze exercises, reading practice, examples |
| **6** | **Lingua Libre / Commons** | **Human pronunciation audio** | 25,431 files. CC BY-SA. Primary audio for common words; TTS fallback for rest |
| **7** | **FreeDict German-English** | **Translation lookup** | 517k headwords. For in-app word lookup when reading. GPL — check implications |
| **8** | **DWDS Goethe Word Lists** | **CEFR validation reference** | Official A1–B1. **Cannot bundle** (copyrighted). Use for development validation only |

### Recommended Data Stack

```
Layer 1: Master Lexical DB     → Wiktionary (kaikki.org) — all German words
Layer 2: Curated Core Vocab    → Grundwortschatz (10,450 enriched lemmas)
Layer 3: CEFR Tagging          → DAFlex (A1–C2) + GLC (A1–C1)
Layer 4: Grammar Rules         → German Language Community (365 rules)
Layer 5: Sentence Bank         → Tatoeba (331k pairs)
Layer 6: Audio (human)         → Lingua Libre / Commons (25k files)
Layer 7: Audio (TTS fallback)  → Piper TTS / Edge-TTS
Layer 8: Translation Lookup    → FreeDict (517k headwords)
```

---

## 3. Grammar Content Sources

### 3.1 German Language Community Grammar Rules

- **365 rules** across 31 categories (nouns, verbs, cases, declensions, tenses, word order, conjunctions, etc.)
- Format: JSONL `{rule_id, category, rule, explanation, examples[]}`
- License: CC BY-SA 4.0 (original work by author)
- **Verdict**: Use as grammar rule reference and exercise seed. Explanations too brief for standalone lessons — need expansion into full lesson content

### 3.2 Structured Grammar Exercise Datasets

No large, freely licensed, structured German grammar exercise dataset exists. Available projects:

| Source | Type | License | Notes |
|---|---|---|---|
| tdidierjean/german-grammar-trainer | Programmatic exercise generator | Unstated | Generates random exercises. Inspire generation logic |
| korjavin/german-conjuctions-trainer | Conjunction exercises (B1) | Unstated | AI-dependent. Not directly usable |
| saeub/dwlg | DW Top-Thema scraper | Unstated | DW content cannot be redistributed |

**Conclusion**: Must generate exercises programmatically from rules + vocabulary + sentence bank.

### 3.3 Goethe-Institut / Telc / Grammar Websites

| Source | License | Can Bundle? |
|---|---|---|
| Goethe-Institut word lists / practice exams | Copyrighted | No — personal use only |
| Telc materials | Copyrighted, purchase required | No |
| deutsch.lingolia.com | Proprietary | No |
| deutsche-welle.de | DW copyright | No — private use only |
| mein-deutschbuch.de | Proprietary | No |
| yourdailygerman.com | Proprietary | No |

**Conclusion**: No major German grammar website allows content reuse. Must write original grammar lesson content.

### 3.4 Programmatic Exercise Generation

| Exercise Type | Source Data | Generation Method |
|---|---|---|
| Fill-in-blank (article) | Nouns with gender + Tatoeba sentences | Blank the article, user selects der/die/das |
| Fill-in-blank (case) | Sentences with case-marked articles | Blank declined article, user fills correct case |
| Fill-in-blank (verb conjugation) | Verbs with inflection tables | Blank the verb, user fills conjugation |
| Word order arrangement | Tatoeba sentences | Scramble word order, user arranges |
| Multiple-choice (grammar rule) | GLC grammar rules + examples | Present sentence, ask which rule applies |
| Cloze deletion | Tatoeba sentences + grammar features | Remove grammar-critical word |
| Translation | Tatoeba German-English pairs | Show German, user types English |

**Pipeline**: Filter Tatoeba by CEFR → parse grammar features → generate templates → store as JSON in SQLite → bundle with app.

---

## 4. Audio Sources & Strategy

### 4.1 Source Comparison

| Source | Quality | Coverage | License | Offline | Cost |
|---|---|---|---|---|---|
| Lingua Libre / Commons | Variable (human) | ~25k words | CC BY-SA 4.0 | Yes (download) | Free |
| Piper TTS (de_DE-thorsten) | Good (neural) | Unlimited | MIT/GPL + voice-specific | Yes (fully local) | Free |
| Edge-TTS (de-DE-KatjaNeural) | Very good (Microsoft) | Unlimited | Personal use OK, not commercial | Pre-generate + bundle | Free |
| Google Cloud TTS | Excellent | Unlimited | Commercial license required | No (cloud) | Paid |
| Forvo API | Variable (user) | 6M+ | **No caching allowed**, links expire 2h | No | $2–29/mo |

### 4.2 Piper TTS Details

- German voices: de_DE-thorsten (high), de_DE-ramona-low, de_DE-kerstin-low, de_DE-karlsson-low, de_DE-eva_k-low
- VITS neural architecture, optimized for CPU, sub-real-time latency
- Models: 15–100 MB ONNX files
- Engine: MIT (original) / GPL-3.0 (piper1-gpl). Voice models: check MODEL_CARD (CC BY 4.0 voices OK)
- **Best for runtime on-demand generation** (user-imported text, dynamic content)

### 4.3 Edge-TTS Details

- German voices: de-DE-KatjaNeural, de-DE-ConradNeural, de-AT-IngridNeural, de-CH-JanNeural
- Uses Microsoft Edge's read-aloud service (not official API)
- "Intended for personal use only" — not for commercial use
- **Best for pre-generation at build time** (superior quality to Piper)

### 4.4 Forvo — Not Suitable

- API terms: **"It is not allowed to cache audio pronunciations."** Links expire in 2 hours. Each play = 1 request.
- Makes offline bundling impossible. Skip entirely.

### 4.5 Recommended Audio Strategy

**Two-tier approach + runtime fallback:**

```
Tier 1: Human recordings (Lingua Libre)
  → Download 25,431 files, convert OGG→MP3, use for common words
  → License: CC BY-SA 4.0

Tier 2: TTS pre-generation (Edge-TTS at build time)
  → Generate MP3 for all words NOT in Tier 1
  → Voice: de-DE-KatjaNeural. Format: MP3 48kbps mono
  → Personal use acceptable

Tier 3 (runtime): Piper TTS (de_DE-thorsten-high)
  → Bundle ~60 MB ONNX model for on-demand generation
  → For user-imported text, custom vocabulary, reading passages
  → Fully offline, no licensing concerns
```

**Audio format**: MP3, 48kbps mono (~15 KB per word, ~30 KB per sentence)

---

## 5. Reading Content Sources

### 5.1 Deutsche Welle

- Content: Top-Thema (B1), Langsam Gesprochene Nachrichten (B2), Nicos Weg (A1–B1)
- License: **DW copyright — strictly private use. No redistribution, no bundling.**
- Can link to from app. DWLG dataset (saeub/dwlg) format useful as structural reference only.

### 5.2 Tatoeba

- ~331k German-English sentence pairs. CC BY 2.0 FR. **Bundleable with attribution.**
- Some sentences have community audio. Use for short reading exercises, cloze deletion.

### 5.3 Project Gutenberg German

- Hundreds of public domain German books (EPUB, text, HTML)
- Most texts 19th–early 20th century → B2–C2 level
- **Bundleable** (public domain). Check EU copyright (life + 70 years).
- Best for advanced reading. Not suitable for A1–B1.

### 5.4 Simple Language News

| Source | CEFR | License | Can Bundle? |
|---|---|---|---|
| nachrichtenleicht.de | A2–B1 | Deutschlandfunk copyright | No |
| DW Simple News | B2 | DW copyright | No |

### 5.5 User PDF/EPUB Import

- PDF: `pdfplumber` (Python) or `pdf-extract` (Rust), OCR fallback (tesseract)
- EPUB: XHTML-based, standard XML parser
- Word lookup: tap word → FreeDict/Wiktionary lookup → add to SRS
- CEFR estimation: DAFlex word frequency analysis

### 5.6 Recommended Reading Strategy

```
Tier 1: Tatoeba sentences (A1–B1) — CC BY 2.0, bundleable
Tier 2: Curated original passages (A2–B2) — 50–100 passages, MIT (ours)
Tier 3: Project Gutenberg (B2–C2) — 20–30 public domain texts
Tier 4: User import (any level) — PDF/EPUB with word lookup
```

---

## 6. Listening Content Sources

### 6.1 Source Evaluation

| Source | CEFR | Transcript | License | Can Bundle? |
|---|---|---|---|---|
| DW Langsam Gesprochene Nachrichten | B2 | Yes | DW copyright | No |
| DW Top-Thema | B1 | Yes | DW copyright | No |
| Slow German (slowgerman.com) | B1+ | Yes (PDF) | Copyrighted (Annik Rubens) | No |
| Easy German (YouTube) | A2–C1 | Members only | YouTube/membership | No |
| Tatoeba (with audio) | Various | Yes | CC BY 2.0 | **Yes** |
| Our TTS audio | A1–C2 | Yes | Personal use | **Yes** |
| LibriVox | B2–C2 | Yes | Public domain/CC BY | **Yes** |

### 6.2 Recommended Listening Strategy

Since most authentic listening content **cannot be bundled**:

```
Tier 1: TTS-generated listening (A1–B2)
  → Take Tatoeba sentences + curated passages
  → Generate audio with Edge-TTS at build time
  → Bundle audio + transcript + comprehension questions

Tier 2: Public domain audiobooks (B2–C2)
  → LibriVox German audiobooks (public domain / CC BY)
  → Bundle shorter works with transcripts

Tier 3: External links (all levels)
  → Link to DW podcasts, Slow German, Easy German YouTube
  → "Discover" links, not bundled content

Tier 4: User import
  → Import any audio file + transcript text
  → App provides transcript display + word lookup
```

---

## 7. Complete Licensing Analysis

### 7.1 License Summary Table

| Source | License | Can Bundle? | Attribution | Share-Alike | Notes |
|---|---|---|---|---|---|
| Wiktionary (kaikki.org) | CC BY-SA 3.0 | Yes | Yes — "Wiktionary contributors" | Yes | Modified data must stay CC BY-SA |
| Grundwortschatz-voc-de | GPL-3.0 | Yes (personal) | Yes | Yes (copyleft) | Data must remain GPL if distributed |
| German Language Community | CC BY-SA 4.0 + CC BY 2.0 FR | Yes | Yes | Vocab: yes, Sentences: no | Mixed license per data type |
| DAFlex (CEFRLex) | Unclear (academic) | Uncertain | Likely yes | Unknown | Contact UCLouvain for permission |
| DWDS Goethe Word Lists | Goethe-Institut copyrighted | **No** | N/A | N/A | Development validation only |
| Tatoeba | CC BY 2.0 FR | Yes | Yes — tatoeba.org + authors | No | Include sentence IDs + author names |
| FreeDict German-English | GPL | Yes (personal) | Yes | Yes (copyleft) | Check TEI header per dictionary |
| Lingua Libre / Commons | CC BY-SA 4.0 | Yes | Yes — creator + Commons | Yes | Check individual file licenses |
| Edge-TTS audio | Unclear (personal use) | Likely OK (personal) | N/A | N/A | Not official API. Use Azure TTS if distributing |
| Piper TTS | MIT / GPL-3.0 + voice-specific | Yes | Check MODEL_CARD | Varies | CC BY 4.0 voices OK. espeak-ng is GPL |
| Project Gutenberg | Public domain (USA) | Yes | Not required | No | Check EU copyright (life + 70 years) |
| LibriVox | Public domain / CC BY 2.0 | Yes | Yes (for CC BY) | No | Check individual recording license |
| Deutsche Welle | DW copyright | **No** | N/A | N/A | Private use only. Linking/embedding OK |
| Slow German | Copyrighted | **No** | N/A | N/A | Personal use only |
| Easy German | YouTube/membership | **No** | N/A | N/A | YouTube terms prohibit downloading |
| nachrichtenleicht.de | Deutschlandfunk copyright | **No** | N/A | N/A | No reuse license stated |
| Our original content | MIT (our choice) | Yes | N/A | No | We own this |

### 7.2 Key License Implications

**CC BY-SA (Wiktionary, Lingua Libre)**: Attribution + share-alike. If we modify data, must distribute under same license. For personal app: include attribution in Credits page. If distributed: data layer must be CC BY-SA.

**CC BY 2.0 FR (Tatoeba)**: Attribution only. No share-alike. Can use in any project. Include tatoeba.org + sentence author attribution.

**GPL-3.0 (Grundwortschatz, FreeDict)**: Copyleft. If distributed, data must remain GPL. App code can be different license. Data as separate file (SQLite) can be GPL while app code is MIT. Personal use: minimal requirements.

**§5 UrhG (German Official Works)**: Laws, regulations, official decrees, court decisions are **not copyright-protected** in Germany. Other official works published for general knowledge are also free, with restrictions (no alteration, source citation). **Does NOT apply to**: Deutsche Welle, Deutschlandfunk, Goethe-Institut, or educational content. **Does apply to**: German government texts (bund.de, etc.) — but not useful for language learning.

**Edge-TTS**: Not an official Microsoft API. "Intended for personal use only." Pre-generating and bundling for personal use is low-risk. For distribution: use Piper TTS (MIT/GPL) or Azure TTS (official, paid).

### 7.3 Licensing Strategy

```
App code (Rust + TS):             MIT
Original content (lessons):       MIT
Wiktionary data:                  CC BY-SA 3.0 (attribution + share-alike)
Grundwortschatz data:             GPL-3.0 (attribution + copyleft)
Tatoeba sentences:                CC BY 2.0 FR (attribution)
Lingua Libre audio:               CC BY-SA 4.0 (attribution + share-alike)
Edge-TTS audio:                   Personal use (no formal license)
Piper TTS:                        MIT/GPL + voice-specific

NOTICES file:
  - "Lexical data from Wiktionary (CC BY-SA 3.0)"
  - "Vocabulary data from Grundwortschatz (GPL-3.0)"
  - "Sentence data from Tatoeba (CC BY 2.0 FR)"
  - "Pronunciation audio from Lingua Libre / Wikimedia Commons (CC BY-SA 4.0)"
  - "Some audio generated with Edge-TTS (personal use)"
  - "Some audio generated with Piper TTS (MIT/GPL)"
```

---

## 8. Content Integration Strategy

### 8.1 Merging Multiple Sources

```
Step 1: Load Wiktionary (kaikki.org) → master table (all German words)
Step 2: Load Grundwortschatz → enrichment overlay (10,450 curated lemmas)
Step 3: Load DAFlex → CEFR level assignment (41,646 entries)
Step 4: Load GLC → CEFR validation + grammar rules + sentences
Step 5: Load Tatoeba → sentence bank (filtered by length + CEFR)
Step 6: Load FreeDict → translation lookup table (top 50k by frequency)
```

### 8.2 Deduplication

| Challenge | Solution |
|---|---|
| Same word, different POS | Keep separate entries keyed by (lemma, POS) |
| Inflected forms vs lemmas | Store lemma as primary, inflected forms as references |
| Different translations across sources | Prefer Grundwortschatz → Wiktionary → FreeDict |
| Same sentence across sources | Hash text, deduplicate by hash, keep first with attribution |
| Spelling variants (Straße/Strasse) | Normalize to modern orthography, store variants as aliases |

### 8.3 CEFR Mapping for Non-CEFR Sources

| Source | Mapping |
|---|---|
| Grundwortschatz grade_level 1–6 | Grade 1–2→A1, 3–4→A2, 5–6→B1 |
| DAFlex | Direct A1–C2 (primary assignment) |
| Wiktionary | Assign via DAFlex lookup (lemma + POS) |
| Tatoeba sentences | Average DAFlex level of words + sentence length + grammar complexity |
| GLC | Use pre-tagged A1–C1 for validation |

**Assignment algorithm for untagged words**:
1. If in DAFlex: first CEFR level where level_freq > 10 per 1M words
2. If in Grundwortschatz: map grade_level → CEFR
3. If in GLC: use GLC tag
4. Else: frequency rank <1000→A1, <3000→A2, <8000→B1, <20000→B2, <50000→C1, else→C2

### 8.4 Unified SQLite Schema

```sql
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    lemma TEXT NOT NULL, word TEXT NOT NULL, pos TEXT, gender TEXT,
    ipa TEXT, plural TEXT, cefr_level TEXT, cefr_source TEXT,
    grade_level INTEGER, frequency_rank INTEGER,
    definition_de TEXT, definition_en TEXT, translation_en TEXT,
    inflections TEXT, synonyms TEXT, antonyms TEXT,
    example_sentences TEXT, audio_path TEXT, audio_source TEXT,
    source_attribution TEXT
);
CREATE TABLE sentences (
    id INTEGER PRIMARY KEY, sentence_de TEXT NOT NULL, sentence_en TEXT,
    cefr_level TEXT, word_count INTEGER, grammar_features TEXT,
    source TEXT, source_attribution TEXT, audio_path TEXT
);
CREATE TABLE grammar_rules (
    id INTEGER PRIMARY KEY, rule_id TEXT UNIQUE, category TEXT,
    cefr_level TEXT, rule TEXT NOT NULL, explanation TEXT, examples TEXT
);
CREATE TABLE grammar_lessons (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, cefr_level TEXT,
    category TEXT, content_markdown TEXT, exercise_ids TEXT, order_index INTEGER
);
CREATE TABLE exercises (
    id INTEGER PRIMARY KEY, type TEXT, cefr_level TEXT,
    grammar_rule_id TEXT, prompt TEXT, answer TEXT, options TEXT,
    sentence_id INTEGER, explanation TEXT
);
CREATE TABLE reading_passages (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, cefr_level TEXT,
    content TEXT NOT NULL, word_count INTEGER, source TEXT,
    source_attribution TEXT, audio_path TEXT, comprehension_questions TEXT
);
```

---

## 9. Data Pipeline Architecture

### 9.1 Pipeline Overview

```
SOURCES                    TRANSFORM (Python)              BUNDLE
───────                    ──────────────────              ──────
Wiktionary ──→ 1_parse_wiktionary.py ──→ words_raw.jsonl ─┐
Grundwort.  ──→ 2_parse_grundwort.py  ──→ enrichment.jsonl─┤
DAFlex     ──→ 3_parse_daflex.py     ──→ cefr_levels.jsonl┤
GLC        ──→ 4_parse_glc.py        ──→ glc_*.jsonl     ─┤
Tatoeba    ──→ 5_parse_tatoeba.py    ──→ sentences.jsonl ─┤
FreeDict   ──→ 6_parse_freedict.py   ──→ translations.json┤
                                                           │
                    7_merge_deduplicate.py ──→ unified.jsonl
                    8_assign_cefr.py      ──→ unified_cefr.jsonl
                    9_generate_exercises.py──→ exercises.jsonl
                    10_build_sqlite.py     ──→ german_learning.db
                                                           │
AUDIO PIPELINE                                             │
Lingua Libre → 1_download_lingua_libre.py → human_audio/   │
All words    → 2_generate_edge_tts.py    → tts_audio/      │
Both         → 3_convert_to_mp3.py       → audio/          │
DB           → 4_link_audio_to_db.py     → update DB       │
                                                           │
                                          ┌────────────────┘
                                          ▼
                          src-tauri/resources/
                            german_learning.db
                            audio/*.mp3
                            grammar_lessons/*.md
                            reading_passages/*
                            NOTICE
```

### 9.2 Pipeline Scripts

| Script | Input | Output | Description |
|---|---|---|---|
| `1_parse_wiktionary.py` | kaikki.org JSONL (1 GB) | words_raw.jsonl (~50 MB) | Extract lemma, pos, ipa, inflections, definitions, translations, audio_links |
| `2_parse_grundwortschatz.py` | grundwortschatz.db (122 MB) | enrichment.jsonl (~20 MB) | Extract lemma, grade_level, frequency, enrichment data |
| `3_parse_daflex.py` | DAFlex data | cefr_levels.jsonl (~5 MB) | Extract lemma, pos, per-level frequencies, CEFR level |
| `4_parse_glc.py` | GLC data/*.jsonl | glc_*.jsonl (~15 MB) | Extract vocab, grammar rules, sentences |
| `5_parse_tatoeba.py` | deu-eng.tsv (~10 MB) | sentences.jsonl (~15 MB) | Filter to 3–30 word sentences with attribution |
| `6_parse_freedict.py` | deu-eng.tei (~50 MB) | translations.jsonl (~10 MB) | Parse TEI XML, filter to top 50k by frequency |
| `7_merge_deduplicate.py` | All previous | unified.jsonl (~40 MB) | Merge, deduplicate by (lemma, POS), resolve conflicts |
| `8_assign_cefr.py` | unified.jsonl + cefr_levels | unified_cefr.jsonl (~40 MB) | Assign CEFR using algorithm in §8.3 |
| `9_generate_exercises.py` | unified_cefr + sentences + grammar | exercises.jsonl (~20 MB) | Generate fill-blank, cloze, word order, translation exercises |
| `10_build_sqlite.py` | All JSONL | german_learning.db (~80 MB) | Create SQLite with schema §8.4, import all data, create indexes |

### 9.3 Audio Pipeline

| Script | Input | Output | Description |
|---|---|---|---|
| `1_download_lingua_libre.py` | Commons category | human_audio/*.ogg (~2.5 GB) | Batch download 25,431 files |
| `2_generate_edge_tts.py` | Words without human audio | tts_audio/*.mp3 (~1.5 GB) | Edge-TTS de-DE-KatjaNeural, MP3 48kbps mono |
| `3_convert_to_mp3.py` | human_audio/*.ogg | audio/*.mp3 | Convert OGG→MP3 with ffmpeg |
| `4_link_audio_to_db.py` | german_learning.db | Updated DB | Set audio_path + audio_source for each word |

---

## 10. Estimated Bundled Content Size

### 10.1 Database

| Component | Estimated Size |
|---|---|
| Words table (~50k entries with full enrichment) | ~30 MB |
| Sentences table (~100k filtered Tatoeba + GLC) | ~15 MB |
| Grammar rules (365) + lessons (~100 original) | ~2 MB |
| Exercises (~10k generated) | ~10 MB |
| Reading passages (~150 curated + Gutenberg excerpts) | ~5 MB |
| Translations (FreeDict top 50k) | ~5 MB |
| Indexes | ~13 MB |
| **Total SQLite DB** | **~80 MB** |

### 10.2 Audio

| Component | Count | Per-file | Total |
|---|---|---|---|
| Lingua Libre human audio (MP3) | 25,431 | ~15 KB | ~380 MB |
| Edge-TTS generated audio (MP3) | ~24,569 | ~15 KB | ~370 MB |
| Sentence audio (TTS, top 10k sentences) | 10,000 | ~30 KB | ~300 MB |
| Piper TTS voice model (de_DE-thorsten-high) | 1 | ~60 MB | ~60 MB |
| **Total Audio** | | | **~1.1 GB** |

### 10.3 Reading Content

| Component | Estimated Size |
|---|---|
| Curated reading passages (150 × ~300 words) | ~2 MB |
| Project Gutenberg texts (20 short works) | ~10 MB |
| LibriVox audiobooks (5 short works) | ~200 MB |
| **Total Reading + Listening** | **~212 MB** |

### 10.4 Grand Total

| Component | Size |
|---|---|
| SQLite database | ~80 MB |
| Audio (vocab + sentences) | ~1.1 GB |
| Piper TTS model | ~60 MB |
| Reading texts + audiobooks | ~212 MB |
| Grammar lessons (markdown) | ~2 MB |
| NOTICE / attribution files | ~1 MB |
| **Total bundled content** | **~1.5 GB** |

**Optimization options**:
- Reduce audio coverage to A1–B1 only (top 10k words): saves ~500 MB
- Skip sentence audio (generate on-demand with Piper): saves ~300 MB
- Skip LibriVox audiobooks (link instead): saves ~200 MB
- Use Opus instead of MP3 (better compression): saves ~30%
- **Optimized total**: ~700 MB–1 GB

---

## 11. Next Steps for Orchestrator

### Content Decisions Required

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | **Primary vocab source** | Wiktionary+Grundwortschatz / GLC only / Grundwortschatz only | Wiktionary as master + Grundwortschatz as curated core (richest data) |
| 2 | **CEFR assignment method** | DAFlex / GLC tags / frequency-based heuristic | DAFlex primary, GLC validation, frequency heuristic fallback. Contact UCLouvain for bulk DAFlex access |
| 3 | **Audio strategy** | Edge-TTS only / Lingua Libre + Edge-TTS / Piper TTS only / All three | Lingua Libre (human) + Edge-TTS (pre-gen) + Piper (runtime fallback). Best quality + coverage + offline |
| 4 | **Grammar lesson authoring** | Expand GLC 365 rules / Write from scratch / Hybrid | Hybrid: use GLC rules as outline, write full lessons expanding each rule with examples and exercises |
| 5 | **Reading content** | Tatoeba only / Tatoeba + curated / + Gutenberg / + user import | Tatoeba (A1–B1) + curated original (A2–B2) + Gutenberg (B2–C2) + user import (any) |
| 6 | **Listening content** | TTS-only / TTS + LibriVox / + external links | TTS-generated (A1–B2) + LibriVox (B2–C2) + external links to DW/Slow German |
| 7 | **FreeDict inclusion** | Include full 517k / Top 50k filtered / Skip | Top 50k filtered by frequency — sufficient for reading lookup, keeps size manageable |
| 8 | **DAFlex bulk access** | Contact UCLouvain / Use GLC tags only / Use frequency heuristic | Contact UCLouvain for bulk data. If unavailable, fall back to GLC + frequency heuristic |
| 9 | **Audio format** | MP3 48kbps / MP3 64kbps / Opus 32kbps | MP3 48kbps mono for compatibility. Consider Opus if size is critical |
| 10 | **Bundled content size target** | Full (~1.5 GB) / Optimized (~700 MB) / Minimal (~300 MB) | Optimized (~700 MB): A1–B2 audio + DB + reading. Add B2–C2 content as optional download |
| 11 | **Exercise generation scope** | All types / Core types only / Manual only | Core types: fill-blank (article, case, verb), cloze, translation. Add word order + MC in Phase 2 |
| 12 | **Public domain texts selection** | Which Gutenberg titles / How many / What length | 20 short works (short stories, poetry, novellas) at B2–C2 level. Prioritize readable 19th century prose |
| 13 | **License for our original content** | MIT / CC BY-SA 4.0 / CC0 | MIT — most permissive, consistent with app code license |
| 14 | **DAFlex license clearance** | Accept academic use / Get written permission / Skip DAFlex | Get written permission from Thomas François (UCLouvain) for bulk data use in personal app |

### Implementation Priority

| Priority | Task | Dependency |
|---|---|---|
| P0 | Download + parse Wiktionary (kaikki.org) and Grundwortschatz | None — start immediately |
| P0 | Download + parse GLC and Tatoeba | None — start immediately |
| P1 | Contact UCLouvain for DAFlex bulk data | None — send email |
| P1 | Download Lingua Libre audio (25k files, ~2.5 GB, ~2 hours) | None — start immediately |
| P1 | Set up Edge-TTS pre-generation pipeline | Python + edge-tts package |
| P2 | Write merge/dedup/CEFR assignment scripts | P0 data downloaded |
| P2 | Build SQLite database | P2 scripts complete |
| P2 | Generate exercises | SQLite built + Tatoeba parsed |
| P3 | Write grammar lessons (expand GLC rules) | GLC rules parsed |
| P3 | Curate reading passages | Tatoeba filtered + Gutenberg downloaded |
| P3 | Generate sentence audio with Edge-TTS | Sentence bank finalized |
| P4 | Bundle Piper TTS model for runtime fallback | Piper voice downloaded |
| P4 | Create NOTICE/attribution file | All sources identified |

### Open Questions

1. **DAFlex access**: Can we get bulk download? What are the licensing terms for use in a personal (non-commercial, non-distributed) app?
2. **Edge-TTS longevity**: Will Microsoft change the endpoint? Should we pre-generate all audio now while it works, or invest in Piper TTS as primary?
3. **Grundwortschatz GPL**: If the app is ever shared with friends/family (not public distribution), does GPL still apply? (Likely yes — GPL applies to any distribution)
4. **Project Gutenberg EU copyright**: Which titles are public domain in Germany (life + 70 years)? Need to verify per-title.
5. **Content update strategy**: How to handle Wiktionary/Tatoeba updates after initial bundling? Periodic re-build + DB migration?

---

*End of document. Research conducted 2026-08-02. Verify all licenses and data availability before implementation.*
