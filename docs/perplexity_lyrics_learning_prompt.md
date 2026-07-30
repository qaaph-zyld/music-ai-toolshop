# Perplexity Lyrics Learning Prompt

Copy and paste the block below into Perplexity. Replace `[PASTE LYRICS OR METRICS HERE]` with the lyrics text, a single section, a full song, or a snippet of Toolshop metrics/fingerprints.

```text
You are a lyrical analyst and creative coach. I will provide lyrics (and optionally some computed metrics from my Toolshop lyrics database). Work in three clear phases: deconstruct the text, synthesize a style guide, and generate new, original lyrics that follow the guide. Be specific, cite line numbers or examples, and quantify patterns wherever you can.

---

PHASE 1 — DECONSTRUCT

1. Structure & form
   - Identify every section (intro, verse, strofa, refren/chorus, hook, bridge, outro, etc.) and the order they appear in.
   - Count lines per section and report average line length in words and characters.
   - Find repeated/hook lines: which lines repeat, how many times, and where.
   - Describe the overall song arc (setup → tension → release → outro).
   - If you have Toolshop metrics, use: section_type_counts, refren_share, avg_sections_per_song, avg_lines_per_section, hook_repetition_ratio, hook_repetition_max, line_count.

2. Vocabulary & language
   - List the most frequent content words (skip stopwords, pronouns, determiners, prepositions).
   - Identify distinctive/slang terms, English loanwords, neologisms, abbreviations, and non-standard spellings.
   - Describe the tone/register (aggressive, boastful, introspective, romantic, party, melancholic, etc.).
   - Note any patterns in POS/lemma usage (heavy nouns, imperative verbs, etc.).
   - If you have Toolshop metrics, use: total_words, unique_words, ttr (type-token ratio), avg_words_per_line, english_loanword_rate, top_20_words, distinctive_vocabulary.

3. Rhyme, sound & flow
   - Map end-rhyme pairs and mark multisyllabic end rhymes (3+ matching vowel syllables).
   - Find internal rhymes, assonance, alliteration, and consonance.
   - Infer the dominant rhyme scheme (AABB, ABAB, AAA, free, etc.).
   - Count syllables per line and classify the flow pattern as uniform, alternating, accelerating, decelerating, or free.
   - If you have Toolshop metrics, use: rhyme_factor, pct_multis, internal_rhyme_rate, dominant_scheme, top_vowel_pairs, avg_syllables_per_line, syllable_density, speed_variation, pattern (flow/dominant_pattern).

4. Themes, entities & content
   - List the 3-5 dominant themes or motifs.
   - Identify named people, places, brands, organizations, and cultural references.
   - Describe the emotional arc and narrative perspective (1st/3rd person, past/present, real/imagined).
   - If you have Toolshop metrics, use: top_entities (PER/LOC/ORG), top_topics, cohort_mix, artist_mix.

5. Style & voice
   - Note point of view, tense, sentence length, syntax patterns, imagery, metaphors, similes, and rhetorical devices.
   - Highlight call-and-response, ad-libs, exclamations, and any repeated interjections (oh, yeah, ajde, etc.).

---

PHASE 2 — SYNTHESIZE A STYLE GUIDE

Produce a concise “Style Guide” for this artist/cohort:

- Signature patterns: 3-5 bullet points (e.g., “end rhymes land on 2-syllable vowel skeletons,” “hooks are 4-line micro-choruses repeated 3×,” “heavy use of 1st-person present-tense bragging,” etc.).
- Quantitative targets: concrete numbers to aim for (syllables/line, rhyme_factor, % multisyllabic rhymes, TTR, English loanword rate, hook repetition ratio, etc.).
- Do / Don’t list: at least 5 writing rules that capture what makes this style sound like itself.
- Vocabulary palette: 10-20 words, phrases, or constructions that are safe to reuse in the same style.
- Taboos: words, structures, or themes that would break the illusion.

---

PHASE 3 — GENERATE & ANNOTATE

Write an original verse (about 16 lines) + hook (4-8 lines) in the same style.

- Follow the Style Guide quantitatively as closely as possible.
- After each section, add a short annotation block `[Annotation: ...]` that explains which 1-2 patterns from the Style Guide the lines implement.
- Keep the lyrics original (do not copy the source text) but convincingly in the analyzed style.

---

INPUT TO ANALYZE

[PASTE LYRICS OR METRICS HERE]
```

## Optional: add Toolshop metrics alongside lyrics

If you want Perplexity to ground its analysis in computed numbers, paste a short block like this after the lyrics:

```text
TOOLSHOP METRICS (optional)
- rhyme_factor: <value>
- pct_multis: <value>
- internal_rhyme_rate: <value>
- dominant_scheme: <value>
- avg_syllables_per_line: <value>
- avg_words_per_line: <value>
- ttr: <value>
- english_loanword_rate: <value>
- hook_repetition_ratio: <value>
- top_topics: <list>
- distinctive_vocabulary: <list>
- top_entities: <PER/LOC/ORG>
```

Replace the placeholders with values from `toolshop lyrics fingerprint --artist <name>` or a `pro_fingerprints.md` report.
