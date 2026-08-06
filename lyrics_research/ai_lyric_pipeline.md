# AI Lyric Improvement Pipeline

**Author:** Implementation Planner Agent  
**Date:** 2026-08-07  
**Sources:** 5 research handoffs (`researcher_*_20260806.md`), `suno_gap_report.md`, existing toolshop modules  
**Companion files:** `craft_implementation_plan.md`, `data/cliche_list.json`

---

## 1. Prompt Engineering Playbook

15 techniques for improving AI-generated lyrics, with Balkan-specific examples where applicable.

### Structural Techniques

**T1. Section Template Injection**  
Provide the AI with an explicit section structure before generation.  
*Example:* "Write lyrics with this structure: [Intro: 2 lines] [Verse 1: 8 lines] [Chorus: 4 lines] [Verse 2: 8 lines] [Chorus: 4 lines] [Outro: 2 lines]. Total: 28 lines."  
*Balkan:* Use drill_trap templates (verse-dominant, 6-7 sections) or pop templates (hook-forward, chorus by section 2).

**T2. Line Count Constraints**  
Mandate exact line counts per section to prevent structural inflation (Suno averages 12.5 sections vs 6-7 professional).  
*Example:* "Each verse must be exactly 8 lines. Each chorus must be exactly 4 lines. Do not add extra sections."

**T3. Repetition Mandate**  
Force chorus repetition and hook callbacks.  
*Example:* "The chorus must appear 3 times, verbatim. Add a pre-chorus of 2 lines that appears twice."

### Style Transfer Techniques

**T4. Artist Style Mimicry**  
Specify a target artist's style traits.  
*Example:* "Write in the style of Buba Corei: short punchy lines, aggressive delivery, street slang, BMW/brand references, multisyllabic end rhymes."

**T5. Genre Convention Lock**  
Constrain vocabulary and themes to genre norms.  
*Balkan drill_trap:* "Use street vocabulary, neighborhood references, loyalty/betrayal themes. Avoid poetic metaphors."

**T6. Vocabulary Restriction (TTR Control)**  
Limit vocabulary diversity to prevent AI vocabulary inflation (Suno TTR 0.52 vs 0.07-0.15 professional).  
*Example:* "Use a limited vocabulary. Repeat key words intentionally. Target TTR of 0.10-0.15. Do not use synonyms for words that appear in the chorus."

### Constraint-Based Techniques

**T7. Rhyme Scheme Enforcement**  
Specify exact rhyme scheme per section.  
*Example:* "Verse 1: AABBCCDD rhyme scheme. Chorus: ABAB. Use multisyllabic rhymes (2+ syllables matching) for at least 50% of end rhymes."

**T8. Syllable Budget**  
Constrain syllables per line to match genre norms.  
*Balkan drill_trap:* "7-9 syllables per verse line. 5-7 syllables per chorus line."  
*Balkan pop:* "6-8 syllables per verse line. 4-6 syllables per chorus line."

**T9. Cliché Blacklist**  
Provide the AI with a list of forbidden words/phrases.  
*Example:* "Do NOT use these words: neon, echoes, shatter, tapestry, whisper, cascade, embrace, yearning, tender, dance with, beneath the sky. Do NOT use these audio tokens: female, male, chorus, verse, bass, kick, vox."

**T10. Slang Injection Quota**  
Require a minimum density of genre-specific slang.  
*Balkan drill_trap:* "Include at least 5 drill-specific slang terms from this list: [bro, brate, kvart, beton, ulica, kinta, fora, ...]. Slang density should be ~5% of total words."

### Iterative Techniques

**T11. Chain-of-Thought Revision**  
Ask the AI to critique its own output before revising.  
*Example:* "First, analyze these lyrics: [paste lyrics]. Identify: (1) lines that sound AI-generated, (2) cliché usage, (3) rhyme scheme breaks, (4) vocabulary inflation. Then rewrite addressing each issue."

**T12. Few-Shot Professional Examples**  
Provide professional lyrics as exemplars before generation.  
*Example:* "Here are professional Balkan drill lyrics by [artist]: [4-8 lines]. Write new lyrics in a similar style, matching the rhyme density, vocabulary level, and slang usage."

**T13. Line-by-Line Replacement**  
Replace AI lines one at a time while preserving structure.  
*Example:* "Keep the structure and rhyme scheme. Replace line 3 with something more specific and less generic. Replace line 7 with a line that uses a concrete image instead of an abstract emotion."

### Evaluation-Guided Techniques

**T14. Score-Targeted Rewriting**  
Use the automated quality score to guide revisions.  
*Example:* "These lyrics scored 42/100. The weakest component is Rhyme (28/100). Rewrite focusing on: increasing multisyllabic rhyme density from 30% to 60%, adding internal rhymes, and enforcing AABB scheme in verses."

**T15. Theme Alignment**  
Compare AI lyrics' theme distribution to genre baseline and redirect.  
*Example:* "Your lyrics over-represent 'love/longing' themes (40% vs 8% genre average) and under-represent 'street life/status' themes (5% vs 35% genre average). Rewrite to shift theme distribution closer to the genre baseline."

---

## 2. Automated Quality Score (4-Component, 0-100 Scale)

Each component is normalized to 0-100 where **50 = genre average** (z-score mapped linearly: score = 50 + z × 20, clamped to [0, 100]). Overall = weighted sum.

### Structural Score (25%)

| Metric | Source | Weight |
|--------|--------|--------|
| Sections/song | `lyricsdb` section count | 30% |
| Lines/song | `lyricsdb` line count | 30% |
| Lines/section (avg) | `lyricsdb` | 20% |
| Section type diversity | `lyrics_metrics.section_type_counts` | 20% |

**Baselines (from `suno_gap_report.md`):**
- drill_trap: 6.5 sections, 42 lines, 6.5 lines/section
- pop: 6.8 sections, 38 lines, 5.6 lines/section
- Suno (problematic): 12.5 sections, 72 lines → score ~15-20

### Rhyme Score (25%)

| Metric | Source | Weight |
|--------|--------|--------|
| Rhyme Factor (end-rhyme density) | `rhyme_miner.rhyme_factor()` | 35% |
| Multisyllabic rhyme % | `rhyme_miner.multisyllabic_rhymes()` | 25% |
| Internal rhyme rate | `rhyme_miner.find_internal_rhymes()` | 25% |
| Scheme consistency | `rhyme_miner.infer_scheme()` | 15% |

**Baselines:**
- drill_trap: RF 0.65, 55% multisyllabic, 0.15 internal rate
- pop: RF 0.55, 35% multisyllabic, 0.08 internal rate
- Suno: RF 0.50, 20% multisyllabic, 0.05 internal rate → score ~30-35

### Lexical Score (25%)

| Metric | Source | Weight |
|--------|--------|--------|
| TTR (type-token ratio) | `lyrics_metrics.compute_song_metrics()` | 40% |
| Avg syllables/line | `syllables.count_syllables()` | 30% |
| Cliché density | `cliche_checker.check_cliches()` | 20% |
| Audio token contamination | `cliche_checker.check_cliches()` | 10% |

**Baselines:**
- drill_trap: TTR 0.12, 8.2 syl/line, ~0% clichés, 0% audio tokens
- pop: TTR 0.15, 6.8 syl/line, ~0% clichés, 0% audio tokens
- Suno: TTR 0.52, 7.5 syl/line, ~3% clichés, ~2% audio tokens → score ~20-30

**Note:** Lower TTR = higher score for rap genres (repetition is craft, not poverty). For pop, optimal TTR window is 0.12-0.20.

### Repetition Score (25%)

| Metric | Source | Weight |
|--------|--------|--------|
| Hook repetition ratio | `lyrics_metrics.compute_song_metrics()` (`hook_repetition_ratio`) | 40% |
| Chorus recurrence | Section type count (chorus appears ≥2×) | 30% |
| Phrase callback count | N-gram repetition analysis | 30% |

**Baselines:**
- drill_trap: hook_ratio 0.15, chorus 2×, 3-4 phrase callbacks
- pop: hook_ratio 0.25, chorus 3×, 5-6 phrase callbacks
- Suno: hook_ratio 0.05, chorus 1×, 0-1 callbacks → score ~20-25

### Score Interpretation

| Score Range | Quality Level | Action |
|-------------|---------------|--------|
| 0-29 | Poor | Major rewrite needed. Use T1-T3, T7, T9 |
| 30-49 | Below average | Targeted fixes. Use T11, T14 on weakest component |
| 50-64 | Average | Minor polish. Use T13, T10 |
| 65-79 | Good | Fine-tuning. Use T6, T8 |
| 80-100 | Excellent | Production-ready. Human review for authenticity only |

---

## 3. 5-Step Human-AI Workflow

### Step 1: Generate with Structure (AI)
- Human provides: genre, topic, target artist style, section template
- AI generates first draft using T1 (Section Template Injection) + T4 (Artist Style Mimicry)
- Human does NOT accept the first draft as final

### Step 2: Clean and Score (Automated)
- Run `toolshop lyrics clean-tokens --input draft.txt` to remove audio metadata contamination
- Run `toolshop lyrics score-ai --input draft.txt --cohort drill_trap` to get baseline quality score
- Run `toolshop lyrics cliches --input draft.txt` to identify cliché usage
- Review the 4-component score breakdown

### Step 3: Targeted Revision (AI + Human)
- Identify weakest score component
- Apply corresponding prompt technique:
  - Structural weak → T1, T2 (template + line count)
  - Rhyme weak → T7 (scheme enforcement), T12 (few-shot rhyme examples)
  - Lexical weak → T6 (vocabulary restriction), T9 (cliché blacklist)
  - Repetition weak → T3 (repetition mandate)
- AI generates revised draft; human reviews for authenticity and emotional truth

### Step 4: Slang and Style Injection (Automated + Human)
- Run `toolshop lyrics inject-slang --input revised.txt --cohort drill_trap --density 0.05`
- Run `toolshop lyrics check-scheme --input revised.txt` to verify rhyme scheme integrity
- Human reviews slang injection for contextual appropriateness (automated injection can be tone-deaf)
- Human makes final manual edits for authenticity — the "cost question" (what did this cost the narrator?)

### Step 5: Final Validation (Automated)
- Run `toolshop lyrics score-ai --input final.txt --cohort drill_trap` — confirm score ≥65
- Run `toolshop lyrics theme-match --input final.txt --cohort drill_trap` — confirm theme distribution is within genre norms (JSD < 0.3)
- Run `toolshop lyrics retrieve-similar --input final.txt --cohort drill_trap --top-k 3` — check that similar professional songs exist (if no matches >0.3, lyrics may be too unusual)
- Human gives final approval

---

## 4. Collaboration Mode Recommendations

### AI-as-Assistant (Recommended)

**Mode:** Human writes the core lyrics (theme, story, key phrases). AI assists with technical craft: rhyme scheme, syllable count, slang suggestions, structure templates.

**Why preferred:**
- RCT evidence (n=112, ACL 2025): Sequential AI collaboration (AI-first or AI-follow) significantly impairs narrative creativity vs human-only
- AI lyrics fail the "cost question": they describe feelings without documenting what they cost the narrator
- LLM judges unreliable for creative writing: Claude-3.7-Sonnet only 73% agreement with human preferences (LitBench, EACL 2026)
- Creativity judgments are hierarchical: initial impressions dominated by emotional resonance (human strength), reflective evaluation shifts to novelty (AI can help here)

**Best for:** Balkan drill/rap where authenticity and street credibility are paramount. Slang usage, neighborhood references, and personal narrative cannot be AI-generated convincingly.

### AI-as-Ghostwriter (Use with Caution)

**Mode:** AI generates full lyrics. Human edits and curates.

**When acceptable:**
- Pop hooks where catchiness > authenticity
- Draft generation when suffering from writer's block
- Generating multiple variants to choose from

**Required safeguards:**
- Always run through the 5-step workflow above
- Mandatory cliché check (B2) and audio token cleaning (B4)
- Slang injection (B5) must be human-reviewed
- Final score must reach ≥65 before consideration

**Why caution:** AI lyrics have an authenticity gap that automated metrics cannot fully detect. The 4-component score measures craft, not emotional truth. A song can score 80/100 and still feel hollow.

---

## 5. Balkan-Specific Cliché List

See `lyrics_research/data/cliche_list.json` for the full data file.

**English AI clichés (SongForgeAI 11):** neon, echoes, shatter, tapestry, whisper, cascade, embrace, yearning, tender, dance with, beneath the sky

**English extended:** heart, soul, fade away, memories, tears, dreams, forever, alone, darkness, light

**Audio metadata tokens (Suno leakage):** female, male, chorus, verse, bass, kick, vox, bv, bar, fx, db, bars, vocal

**Balkan clichés:** To be populated from systematic analysis of Suno corpus top-50 vocabulary. Candidates from `suno_gap_report.md`: words that appear frequently in AI lyrics but rarely in professional Balkan lyrics. Initial observations suggest over-use of abstract emotional terms (ljubav, bol, duša, srce) and calque translations of English AI clichés.

---

## 6. Suno Gap Summary

Four quantifiable gaps between Suno AI lyrics and professional Balkan lyrics (from `suno_gap_report.md`):

### Gap 1: Structural Inflation
- **Suno:** 12.5 sections/song, 72 lines/song
- **Professional:** 6-7 sections/song, 38-42 lines/song
- **Delta:** ~2× inflation
- **Addressable by:** T1 (template injection), T2 (line count constraints), B3 (structure template generator), B1 (structural score component)

### Gap 2: Rhyme Craft Deficit
- **Suno:** RF 0.50, 20% multisyllabic, 5% internal rhyme rate
- **Professional drill_trap:** RF 0.65, 55% multisyllabic, 15% internal rate
- **Professional pop:** RF 0.55, 35% multisyllabic, 8% internal rate
- **Delta:** RF -0.10 to -0.15, multisyllabic -20 to -35%, internal -5 to -10%
- **Addressable by:** T7 (scheme enforcement), T12 (few-shot examples), B6 (scheme checker), B1 (rhyme score component)

### Gap 3: Vocabulary Inflation
- **Suno:** TTR 0.52 (high diversity, low repetition)
- **Professional:** TTR 0.07-0.15 (intentional repetition, limited vocabulary)
- **Delta:** 3-7× over-diversification
- **Addressable by:** T6 (vocabulary restriction), T3 (repetition mandate), B1 (lexical score component), B9 (improve-loop targeting lexical weakness)

### Gap 4: Authenticity Gap (Slang & Theme)
- **Suno:** 8.9% slang overlap with professional lexicon, theme distribution skewed toward generic "love/longing"
- **Professional:** 100% slang overlap (by definition), themes aligned to genre norms (drill: street life/status; pop: romance/party)
- **Delta:** -91% slang overlap, JSD 0.20+ theme divergence
- **Addressable by:** T10 (slang injection quota), T15 (theme alignment), B5 (slang injector), B8 (theme comparator), B7 (few-shot retriever for style transfer)

---

## 7. Toolshop Integration Map

Which features (B1-B10) address which Suno gaps:

| Feature | Gap 1: Structural | Gap 2: Rhyme | Gap 3: Vocabulary | Gap 4: Authenticity |
|---------|:-:|:-:|:-:|:-:|
| **B1: score-ai** | ✓ (Structural 25%) | ✓ (Rhyme 25%) | ✓ (Lexical 25%) | ✓ (Repetition 25%) |
| **B2: cliches** | | | ✓ (cliché density) | ✓ (audio token detection) |
| **B3: template** | ✓ (structure generation) | | | |
| **B4: clean-tokens** | | | | ✓ (audio token removal) |
| **B5: inject-slang** | | | | ✓ (slang density) |
| **B6: check-scheme** | | ✓ (scheme enforcement) | | |
| **B7: retrieve-similar** | | ✓ (few-shot rhyme examples) | ✓ (vocabulary matching) | ✓ (style transfer) |
| **B8: theme-match** | | | | ✓ (theme distribution) |
| **B9: improve-loop** | ✓ (iterative structural fix) | ✓ (iterative rhyme fix) | ✓ (iterative lexical fix) | ✓ (iterative repetition fix) |
| **B10: centaur** | ✓ (real-time scoring) | ✓ (scheme visualization) | ✓ (cliché highlighting) | ✓ (slang injection UI) |

**Coverage:** All 4 gaps are addressed by at least 3 features. Gap 4 (Authenticity) has the most coverage (7 features) because it is the hardest gap to close automatically and requires multiple complementary approaches.
