# Naive vs Fingerprint Prompt — Gap Analysis

**Date:** 2026-08-09
**Naive prompt:** `ORCHESTRATION/wave2/suno_prompt_naive.txt`
**Fingerprint prompt:** `ORCHESTRATION/wave2/suno_prompt_fingerprint.txt`
**Fingerprint brief:** `ORCHESTRATION/wave2/brief_fingerprint.md`

---

## What the Naive Prompt Has

| Element | Naive Value | Source |
|---------|-------------|--------|
| Genre | drill trap | User knowledge |
| Language | Serbian/Bosnian | User knowledge |
| Topic | street life, hustle, loyalty, survival | User knowledge |
| BPM | 130 | User guess (generic trap range) |
| Mood | dark, aggressive, energetic | User knowledge |
| Vocal style | deep male voice, aggressive delivery, fast flow | User knowledge |
| Structure | verse - chorus - verse - chorus - bridge - chorus | Generic song structure |
| Instrumentation | 808 bass, dark piano, trap drums, hi-hats | User knowledge |

All values are generic — derived from the user's general knowledge of drill trap music, not from any corpus analysis.

---

## What It Lacks

### 1. Structure Template (Corpus-Derived)

**Naive:** Generic verse-chorus-verse-chorus-bridge-chorus — a Western pop convention.

**Fingerprint:** `tekst(14) → refren(7) → strofa(11) → refren(7) → strofa(11) → refren(7)` — 6 sections, 57 total lines, derived from the drill_trap cohort's actual section patterns. Uses Serbian section labels (tekst/strofa/refren) matching Genius corpus conventions. No bridge section — drill_trap doesn't use one. Specific line counts per section (14/7/11/7/11/7) match Jala Brat's actual song structures.

**Impact:** Suno will generate a Western-structure song with a bridge that drill_trap songs don't have. Section lengths will be generic (likely 8-16 bars each) rather than matching the 7-line chorus / 11-line verse pattern that characterizes Jala Brat's output.

### 2. Rhyme Targets

**Naive:** No rhyme density, multisyllabic percentage, or internal rhyme rate specified.

**Fingerprint:**
- Rhyme factor: 0.58 (Malmi method — drill_trap median)
- Multisyllabic: 85% of rhymes (2+ syllable matches)
- Internal rhyme rate: 0.91 (nearly 1 per line)
- 10 attested rhyme pairs (e.g., smaras→varas ×64, cartier→je ×49, moja→ona ×36)

**Impact:** Suno will default to simple end-rhymes (AABB with 1-syllable matches). The 85% multisyllabic target is critical — without it, Suno produces monosyllabic cat/hat-style rhymes rather than the vowel-skeleton-matched multisyllabic rhymes that define Jala Brat's craft. The internal rhyme rate (0.91) is almost entirely absent from AI-generated lyrics.

### 3. Theme Distribution

**Naive:** Single topic keyword "street life" with no theme palette.

**Fingerprint:** Top-5 cohort themes from BERTopic section_topics:
1. voli_volim_ljubav_sarajevo (love/Sarajevo — 80 sections)
2. oh_hej_tng_wo (ad-libs/hype/TNG crew — 63 sections)
3. les_oy_vavoy_pucnjave (shootings/street/French-Algerian slang — 56 sections)
4. balkan_limiti_gang_krvavi (Balkan gang identity/blood — 49 sections)
5. vozilu_svom_pumpam_elegantan (cars/flexing — 42 sections)

JSD(drill||pop) = 0.2015 — themes are cohort-discriminating.

**Impact:** Suno will produce generic "street life" lyrics without the specific thematic mix that characterizes Balkan drill. The fingerprint brief shows that "street life" in Jala Brat's corpus is actually a blend of love/Sarajevo nostalgia, crew hype, shooting references, gang identity, and car flexing — not just generic gangster tropes. Suno will miss the Sarajevo-specific and TNG crew references entirely.

### 4. Slang Density

**Naive:** No slang density target or slang lexicon.

**Fingerprint:** The slang lexicon contains 2,421 drill-distinctive terms. Key drill-distinctive terms: braca, gang, geng, bang, pucnjave, limiti, krvavi. The `slang_injector` module can post-process to achieve target density.

**Impact:** Suno will use generic English-translated street slang or none at all. The corpus-attested Balkan slang terms (TNG, vavoy, pucnjave, limiti) that give Jala Brat's lyrics their authentic regional flavor will be absent. Slang density directly affects the "authenticity" perception — research shows AI lyrics have only 8.9% slang overlap with cohort-specific language.

### 5. TTR Target (Repetition Pattern)

**Naive:** No TTR target — Suno defaults to high TTR (0.52+), meaning vocabulary inflation.

**Fingerprint:** TTR 0.47 — meaning ~53% token repetition. This is lower than pop (0.52) and much lower than AI default (0.52+). The repetition is characteristic of drill_trap's hook-heavy, refrain-driven structure. Three refren sections (7 lines each, 21 total) provide the repetitive hook anchor.

**Impact:** Suno will produce vocabulary-inflated lyrics with too many unique words. Research identifies vocabulary inflation (TTR 0.52 vs 0.07 in real lyrics) as a key AI lyric weakness. Without the 0.47 target, Suno generates "word salad" verses instead of the hypnotic, repetitive flow that defines drill_trap.

### 6. Repetition Pattern

**Naive:** No repetition pattern specified.

**Fingerprint:** The 3× refren repetition (7 lines each) is the primary repetition anchor. TTR 0.47 implies ~53% repetition. The structure template encodes this: 3 chorus sections out of 6 total.

**Impact:** Suno may vary the chorus lyrics on each repetition (a common AI behavior) rather than keeping them identical. The fingerprint structure template enforces 3 identical refren sections, which is how Jala Brat actually structures songs.

### 7. Suno Style Hints (Specific vs Generic)

**Naive:** "808 bass, dark piano, trap drums, hi-hats" — generic trap instrumentation.

**Fingerprint:** "Serbian drill trap, dark piano, 808 bass, fast flow" + "aggressive, rhythmic delivery" — corpus-derived style that matches Jala Brat's actual production. The "fast flow" hint is critical — it maps to the 12.3 syllables/line target and the aggressive delivery style.

**Impact:** Without "fast flow" and the syllable density target, Suno may produce mid-tempo delivery. The "Serbian drill trap" genre label is more specific than just "drill trap" — it signals Balkan harmonic conventions and Serbian-language cadence.

---

## Expected Impact on Output Quality

| Dimension | Naive Prompt | Fingerprint Prompt | Expected Gap |
|-----------|-------------|-------------------|-------------|
| **Structure** | Generic verse-chorus-bridge (Western) | 6-section Serbian template, 57 lines | High — wrong structure, wrong section count, phantom bridge |
| **Rhyme density** | Default (low, monosyllabic) | 0.58 RF, 85% multisyllabic | Critical — defines the genre's sound |
| **Internal rhymes** | None expected | 0.91 per line | Critical — absent in AI default |
| **Vocabulary** | Inflated (TTR ~0.52+) | Controlled (TTR 0.47) | High — vocabulary inflation is top AI lyric weakness |
| **Thematic content** | Generic "street life" | 5-theme palette with Sarajevo/TNG/gang specifics | High — missing regional and crew identity |
| **Slang** | Generic or English | 2,421 drill-distinctive Balkan terms | High — authenticity gap |
| **Chorus repetition** | May vary choruses | 3× identical refren (7 lines) | Medium — structural consistency |
| **Syllable density** | Uncontrolled | 12.3 syllables/line | Medium — affects flow speed |
| **Production style** | Generic trap | Serbian drill trap, dark piano, fast flow | Medium — more specific genre signal |

### Summary

The naive prompt provides Suno with enough information to generate a *recognizable* drill trap song in Serbian/Bosnian about street life. However, it will lack every corpus-attested craft dimension that makes Jala Brat's output distinctive: the specific structure, the multisyllabic rhyme density, the internal rhyme complexity, the controlled repetition, the regional slang, and the thematic palette. The output will sound like "generic drill trap in Serbian" rather than "Jala Brat-style drill trap."

The fingerprint prompt encodes **7 corpus-derived craft dimensions** that the naive prompt cannot provide from general knowledge alone. The most critical gaps are rhyme density/multisyllabic targets and internal rhyme rate — these are the craft features that most distinguish professional drill lyrics from AI-generated ones, according to the AI lyric improvement research.
