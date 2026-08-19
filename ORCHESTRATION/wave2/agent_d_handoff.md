# Agent D Handoff — Fingerprint Brief for Jala Brat (drill_trap)

**Date:** 2026-08-09  
**Agent:** Implementer (Agent D)  
**Task:** Generate corpus-informed Suno brief for Jala Brat using L5 writing tools  
**DB:** `data/toolshop/lyrics/lyrics.db` (742 songs, 36,572 lines, 159,171 rhyme rows)  

---

## Brief Generated

**Command:**
```
.venv\Scripts\python.exe -m toolshop.cli lyrics brief --artist "Jala Brat" --topic "street life" --db data/toolshop/lyrics/lyrics.db --output ORCHESTRATION/wave2/brief_fingerprint.md
```

**Output file:** `ORCHESTRATION/wave2/brief_fingerprint.md`

**Baseline:** 169 Jala Brat solo songs in drill_trap cohort.

### Brief contents summary

The brief is a structured writing brief derived from Jala Brat's per-artist fingerprint combined with the drill_trap cohort structure template, top themes, and attested rhyme pairs. It contains:

1. **Structure template** — 6 sections, 57 total lines (see Structure Template section below)
2. **Craft targets** — rhyme factor, multisyllabic %, internal rhyme rate, TTR, syllables/line, dominant schemes
3. **Theme palette** — top-5 cohort themes from BERTopic section_topics
4. **Top rhyme pairs** — 10 most frequent attested rhyme pairs from the rimer DB
5. **Topic hint** — "street life"
6. **Suno prompt hints** — style, language, vocal style

### Craft Targets (from Jala Brat fingerprint)

| Metric | Value |
|--------|-------|
| Rhyme factor (median) | 0.58 |
| Multisyllabic rhymes | 85% of rhymes |
| Internal rhyme rate | 0.91 |
| TTR (type-token ratio) | 0.47 |
| Syllables per line | 12.3 |
| Avg sections per song | 7.24 |
| Avg lines per section | 7.2 |

**Dominant schemes:** Highly varied — Jala Brat uses complex, long-form schemes (50+ letter patterns) rather than simple AABB/ABAB. The top-3 schemes each appear once, indicating no single dominant scheme but high structural diversity.

### Theme Palette (top-5 drill_trap cohort themes)

1. **voli_volim_ljubav_sarajevo** — love, Sarajevo, emotional (80 sections)
2. **oh_hej_tng_wo** — ad-libs, hype, TNG crew references (63 sections)
3. **les_oy_vavoy_pucnjave** — shootings, street life, French/Algerian slang (56 sections)
4. **balkan_limiti_gang_krvavi** — Balkan gang identity, blood, limits (49 sections)
5. **vozilu_svom_pumpam_elegantan** — cars, flexing, elegance (42 sections)

### Top 10 Attested Rhyme Pairs (drill_trap cohort)

| Word A | Word B | Vowel Skeleton | Match Length | Frequency |
|--------|--------|---------------|-------------|-----------|
| smaras | varas | eoaaaa | 6 | 64 |
| cartier | je | iiiiiiaie | 9 | 49 |
| aha | la | aaaaaa | 6 | 40 |
| moja | ona | oaoaoaoa | 8 | 36 |
| nova | odma | eoaoaoa | 7 | 36 |
| koka | opa | oaoaoaoaoa | 10 | 28 |
| ajde | sve | aeaeaeaeaeae | 12 | 18 |
| vozilu | x | uauooiuuauooiu | 14 | 16 |
| bolje | nove | iieaoeiieooe | 12 | 16 |
| ey | ye | eiiiiaeoiee | 11 | 16 |

---

## Suno Prompt

**Output file:** `ORCHESTRATION/wave2/suno_prompt_fingerprint.txt`

**Full Suno prompt:**
```
style: Serbian drill trap, dark piano, 808 bass, fast flow
language: Serbian (Latin)
vocal style: aggressive, rhythmic delivery
structure: tekst(14) → refren(7) → strofa(11) → refren(7) → strofa(11) → refren(7)
rhyme density: 0.58
multis: 85%
topic: street life
```

**Generation method:** Called `format_suno_prompt()` from `toolshop.brief_generator` with the same brief dict. This condenses the full brief into a single paste-ready prompt string for Suno.

---

## Rhyme Partners Found

Five key drill_trap words queried via `toolshop lyrics rime --word <WORD> --cohort drill_trap --db ... --json`. All partners are attested in the corpus (rhyme_pairs table).

### 1. zivot (life)

| Partner | Skeleton | Match Length | Frequency | Distinctiveness |
|---------|----------|-------------|-----------|-----------------|
| krio | io | 2 | 2 | 0.4627 |
| pio | io | 2 | 2 | 0.4627 |
| nismo | io | 2 | 2 | 0.4627 |
| sivo | aaeoeio | 7 | 1 | 0.2903 |
| avion | ioaio | 5 | 1 | 0.2903 |
| ross | eio | 3 | 1 | 0.2903 |
| htio | aio | 3 | 1 | 0.2903 |
| o | aio | 3 | 1 | 0.2903 |
| sony | aio | 3 | 1 | 0.2903 |
| isto | io | 2 | 1 | 0.2903 |

**Key partners:** krio (hid), pio (drank), nismo (we weren't) — all share the -io ending. Multisyllabic: sivo (7-skeleton match), avion (5-skeleton match).

### 2. novac (money)

| Partner | Skeleton | Match Length | Frequency | Distinctiveness |
|---------|----------|-------------|-----------|-----------------|
| daunovac | aoauoa | 6 | 1 | 0.2903 |
| rovac | eaioa | 5 | 1 | 0.2903 |
| borac | eiioa | 5 | 1 | 0.2903 |
| volan | oa | 2 | 1 | 0.2903 |
| poraz | oa | 2 | 1 | 0.2903 |
| kosova | oa | 2 | 1 | 0.2903 |

**Key partners:** daunovac (down payment), rovac (digger), borac (fighter) — 5-6 vowel matches. Shorter: volan, poraz, kosova.

### 3. brat (brother)

| Partner | Skeleton | Match Length | Frequency | Distinctiveness |
|---------|----------|-------------|-----------|-----------------|
| grad | eoa | 3 | 3 | 0.5858 |
| tvorza | oa | 2 | 3 | 0.5858 |
| postar | oa | 2 | 3 | 0.5858 |
| para | aaa | 3 | 2 | 0.4627 |
| sahara | aaa | 3 | 2 | 0.4627 |
| ta | aaa | 3 | 2 | 0.4627 |
| coska | oaoaoa | 6 | 1 | 0.2903 |
| sipa | uaia | 4 | 1 | 0.2903 |
| niagara | iaaa | 4 | 1 | 0.2903 |
| sjajna | aiaa | 4 | 1 | 0.2903 |

**Key partners:** grad (city) ×3, tvorza (creator) ×3, postar (postman) ×3 — highest frequency pair. para (money) ×2, sahara ×2. Multisyllabic: coska (6-match), niagara (4-match).

### 4. grad (city)

| Partner | Skeleton | Match Length | Frequency | Distinctiveness |
|---------|----------|-------------|-----------|-----------------|
| brat | eoa | 3 | 3 | 0.5858 |
| dva | eaa | 3 | 2 | 0.4627 |
| dan | eaa | 3 | 2 | 0.4627 |
| nas | eeuiiaiaoa | 10 | 1 | 0.2903 |
| revija | oaeeia | 6 | 1 | 0.2903 |
| ja | iaoia | 5 | 1 | 0.2903 |
| zaspala | iiaaa | 5 | 1 | 0.2903 |
| sad | eiia | 4 | 1 | 0.2903 |
| kralja | aoaa | 4 | 1 | 0.2903 |
| gram | ieia | 4 | 1 | 0.2903 |

**Key partners:** brat (brother) ×3 — reciprocal pair with highest frequency. dva (two) ×2, dan (day) ×2. Long match: nas (10-skeleton!), revija (6-skeleton).

### 5. problem (problem)

| Partner | Skeleton | Match Length | Frequency | Distinctiveness |
|---------|----------|-------------|-----------|-----------------|
| zoves | eoe | 3 | 2 | 0.4627 |
| recommends | eoe | 3 | 2 | 0.4627 |
| ne | eoe | 3 | 2 | 0.4627 |
| bombe | eoe | 3 | 2 | 0.4627 |
| opet | eoe | 3 | 2 | 0.4627 |
| ove | ioe | 3 | 2 | 0.4627 |
| vole | oe | 2 | 2 | 0.4627 |
| odnose | oe | 2 | 2 | 0.4627 |
| nje | oe | 2 | 2 | 0.4627 |
| satove | ieiaoe | 6 | 1 | 0.2903 |

**Key partners:** zoves (you call), bombe (bombs), opet (again) — all share the -oe ending. satove (hours) has a 6-skeleton match. Note: "recommends" is an English loanword appearing in drill_trap corpus.

### Cross-word observation

**brat ↔ grad** is a reciprocal pair (each appears as the other's top partner, frequency=3, distinctiveness=0.5858). This is the strongest attested pair among the 5 queried words — both are core drill_trap vocabulary (brother + city).

---

## Structure Template

**Output file:** `ORCHESTRATION/wave2/structure_template.json`

**Command:**
```
.venv\Scripts\python.exe -m toolshop.cli lyrics template --cohort drill_trap --db data/toolshop/lyrics/lyrics.db --json
```

**Template (drill_trap cohort):**

| # | Section Type | Lines | Rhyme Scheme |
|---|-------------|-------|-------------|
| 1 | tekst (intro/verse) | 14 | AABB |
| 2 | refren (chorus) | 7 | AABB |
| 3 | strofa (verse) | 11 | AABB |
| 4 | refren (chorus) | 7 | AABB |
| 5 | strofa (verse) | 11 | AABB |
| 6 | refren (chorus) | 7 | AABB |

**Total lines:** 57  
**Cohort:** drill_trap  
**Pattern:** tekst → refren → strofa → refren × 2 → refren (outro)  
**Section count:** 6 (3 verse-type + 3 chorus)  
**Note:** The template uses "tekst" as the opening section type (from Genius section label convention) followed by alternating strofa/refren. All sections default to AABB rhyme scheme at the template level, though the fingerprint shows Jala Brat's actual schemes are far more complex.

---

## Craft Targets Summary

The fingerprint brief encodes the following corpus-derived targets for a Jala Brat-style drill_trap song on "street life":

### Structure
- **6 sections:** tekst(14) → refren(7) → strofa(11) → refren(7) → strofa(11) → refren(7)
- **57 total lines** (vs. AI default of ~80+ — the brief counters structural inflation)
- **AABB template scheme** at section level, but actual Jala Brat schemes are highly varied (50+ letter patterns)

### Rhyme Craft
- **Rhyme factor: 0.58** — target end-rhyme density (Malmi method). This is the drill_trap median; pop median is 0.74.
- **Multisyllabic: 85%** — 85% of rhymes should be 2+ syllable matches. This is Jala Brat's actual multisyllabic rate.
- **Internal rhyme rate: 0.91** — nearly 1 internal rhyme per line. Very dense.
- **Dominant schemes:** No single dominant scheme — Jala Brat uses highly varied long-form schemes. This indicates structural creativity rather than formulaic repetition.

### Lexical
- **TTR: 0.47** — type-token ratio. Lower than pop (0.52), indicating more repetition (consistent with drill's hook-heavy style). AI default is 0.52+ (vocabulary inflation); the brief targets 0.47 to enforce repetition.
- **Syllables per line: 12.3** — moderate density, allowing for fast flow without overcrowding.

### Themes (drill_trap cohort)
- **Top 5 themes:** love/Sarajevo, hype/ad-libs, street life/shootings, Balkan gang identity, cars/flexing
- **Theme distribution:** JSD(drill||pop) = 0.2015 — themes are cohort-discriminating
- **For "street life" topic:** themes 3 (pucnjave/shootings) and 4 (balkan/gang/krvavi) are most relevant

### Slang Density
- The brief does not include an explicit slang density target, but the slang lexicon contains 2,421 drill-distinctive terms. The `slang_injector` module can post-process to achieve target density.
- Key drill-distinctive terms from the lexicon include: braca, gang, geng, bang, pucnjave, limiti, krvavi

### Suno Style Hints
- **Style:** Serbian drill trap, dark piano, 808 bass, fast flow
- **Language:** Serbian (Latin)
- **Vocal style:** Aggressive, rhythmic delivery

### Repetition Pattern
- TTR 0.47 implies ~47% unique tokens — meaning ~53% repetition. This is characteristic of drill_trap's hook-heavy, refrain-driven structure.
- The 3 refren sections (7 lines each, 21 total) provide the repetitive hook anchor.
- Chorus repetition (3× refren) is the primary repetition pattern.

---

## Files Created

| File | Description |
|------|-------------|
| `ORCHESTRATION/wave2/brief_fingerprint.md` | Full text brief (human-readable) |
| `ORCHESTRATION/wave2/suno_prompt_fingerprint.txt` | Condensed Suno paste-ready prompt |
| `ORCHESTRATION/wave2/structure_template.json` | JSON structure template for drill_trap |
| `ORCHESTRATION/wave2/agent_d_handoff.md` | This handoff document |

## Rimer DB Status

Built fresh in this session: **13,036 pairs, 1,632 unique skeletons, 9,333 drill, 2,421 pop**. The `rhyme_pairs` table is populated and ready for all downstream rhyme lookup queries.

## No Source Files Modified

Per instructions, no source files were modified. Only output files in `ORCHESTRATION/wave2/` were created.
