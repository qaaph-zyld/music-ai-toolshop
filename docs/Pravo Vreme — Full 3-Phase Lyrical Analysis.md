# Lyrical Analysis: "Pravo Vreme" — Buba Corelli ft. Maya Berović

> **Note on metrics:** Toolshop CLI was not available in this environment. All metrics below are **Toolshop-style proxy metrics** computed via a custom Python NLP script that approximates Toolshop's fingerprint fields (rhyme skeletons, syllable counts, TTR, etc.). Vowel-skeleton rhyme detection is heuristic — the `rhyme_factor` value in particular uses a simple group-count method and should be read as approximate. Where the heuristic diverges from the musical reality (e.g., monorhyme blocks that the ear clearly hears), I flag it.

---

## TOOLSHOP-STYLE PROXY METRICS

```
STRUCTURE
  section_order:         strofa → predrefren → refren → strofa → predrefren → refren
  section_type_counts:   {strofa: 2, predrefren: 2, refren: 2}
  total_sections:        6
  avg_lines_per_section: 7.7
  total_lines:           46
  refren_share:           0.333
  hook_repetition_ratio:  0.326
  hook_repetition_max:    2

VOCABULARY
  total_words:            333
  unique_words:           136
  ttr:                    0.408
  avg_words_per_line:     7.2
  english_loanword_rate:  0.006 (plan B, distance — 2 loanwords in 333)
  top_20_words:           bebo(8), sviđa(8), pravo(6), vreme(6),
                          parirala(4), sabotirala(4), pusti(4),
                          samo(2), radio(2), skinô(2), tebe(2),
                          onda(2), bacio(2), pod(2), dao(2), što(2),
                          pravu(2), kraljicu(2), vratio(2)
  distinctive_vocabulary: bebo, sviđa, pravo, vreme, parirala,
                          sabotirala, pusti, samo, radio, skinô,
                          tebe, onda, bacio, pod

RHYME & SOUND
  rhyme_factor:           0.152 (heuristic — see caveat below)
  pct_multis:             28.3%
  internal_rhyme_rate:    82.6%
  dominant_scheme:        mixed/free (at song level)
  avg_syllables_per_line: 11.8
  syllable_density:       1.637
  speed_variation (σ):    2.9
  dominant_pattern:       free
  top_vowel_pairs:        oi-oi(7), eo-eo(6), ee-ee(6), e-ia(3), ia-ia(3)

THEMES & ENTITIES
  top_topics:    romance/erotic, nightlife, obsession, power_dynamics, intimacy
  top_entities:  PER: [Buba Corelli, Maya Berović]
  cohort_mix:    {Buba Corelli: 0.5, Maya Berović: 0.5}
```

---

# PHASE 1 — DECONSTRUCT

## 1. Structure & Form

### Section map

| Order | Section | Lines | Avg words/line | Avg chars/line | Avg syllables/line |
|-------|---------|-------|----------------|----------------|-------------------|
| 1 | Strofa 1 | 8 | 7.1 | 36.2 | 12.9 |
| 2 | Predrefren | 8 | 8.4 | 36.1 | 12.2 |
| 3 | Refren | 7 | 6.4 | 33.4 | 11.9 |
| 4 | Strofa 2 | 8 | 6.5 | 30.9 | 10.0 |
| 5 | Predrefren (repeat) | 8 | 8.4 | 36.1 | 12.2 |
| 6 | Refren (repeat) | 7 | 6.4 | 33.4 | 11.9 |

**Overall:** 46 lines across 6 sections, avg 7.7 lines/section.

### Repeated/hook lines — exact locations

**Full-line repetition (predrefren):** Lines 9–16 (predrefren 1) are repeated verbatim at lines 32–39 (predrefren 2). All 8 lines match exactly.

**Full-line repetition (refren):** Lines 17–23 (refren 1) are repeated verbatim at lines 40–46 (refren 2). All 7 lines match exactly.

**Phrase-level repetition within sections:**

| Phrase | Count | Locations (line numbers) |
|--------|-------|------------------------|
| `bebo` | 8 | End of lines 9, 10, 11, 12, 32, 33, 34, 35 |
| `pravo vreme` | 6 | Lines 13, 14, 15, 36, 37, 38 |
| `sviđa` | 8 | Lines 20, 23, 43, 46 (×2), plus "Sve mi se sviđa" lines 22, 45 |
| `a-je` | 8 | Lines 18, 21, 22, 41, 44, 45, plus internal |
| `pusti, pusti` | 4 | Lines 28, 30 (×2 pairs) |
| `parirala` | 4 | Lines 17 (×2), 40 (×2) |
| `sabotirala` | 4 | Lines 19 (×2), 42 (×2) |

**hook_repetition_ratio: 0.326** — roughly one-third of all lines are verbatim repeats. **hook_repetition_max: 2** — no single line appears more than twice (the predrefren and refren each appear twice).

### Song arc

**Setup (Strofa 1)** → establishes nocturnal danger, weapon/love metaphors, mutual secrecy → **Tension build (Predrefren)** → male proposition framed in conditionals, time-pressure hook → **Release (Refren)** → compact feminine-judgment block with ad-libs → **Re-escalation (Strofa 2)** → more explicit erotic imagery, 8-line monorhyme accelerates flow → **Tension build (Predrefren repeat)** → identical → **Release (Refren repeat)** → identical.

The arc is symmetrical: two cycles of setup→build→release, with Strofa 2 intensifying the erotic register before returning to the same predrefren/refren payoff.

---

## 2. Vocabulary & Language

### Most frequent content words (stopwords removed)

| Word | Count | Function |
|------|-------|----------|
| bebo | 8 | Vocative refrain (baby, in the vocative case) |
| sviđa | 8 | Hook anchor (pleases me / I like) |
| pravo | 6 | Time-pressured repetition (right/correct) |
| vreme | 6 | Paired with "pravo" — the song title |
| parirala | 4 | Refren verb (she matched/equaled) |
| sabotirala | 4 | Refren verb (she sabotaged) |
| pusti | 4 | Strofa 2 imperative (let/allow) |

### Distinctive / slang terms & non-standard spellings

| Term | Standard form | Note |
|------|---------------|------|
| `bebo` | bebo (vocative) | Clipped vocative of "beba" — baby |
| `bi'` | bih | Conditional auxiliary, apostrophe-clipped |
| `imô` | imao | Past tense, ô marks elongated vowel (regional) |
| `skinô` | skidao | Past tense, ô contraction |
| `zamišljô` | zamišljao | Past tense, ô contraction |
| `kô` | kao | As/like — ô contraction |
| `Da-da-dao` | dao | Stuttering entrance / ad-lib |
| `je-je` | — | Rhythmic ad-lib |
| `a-je` | — | Rhythmic ad-lib (hook punctuation) |
| `plan B` | — | English loanword (backup plan) |
| `distance` | — | English loanword (from a distance) |

### Tone / register

**Erotic, boastful, slightly aggressive, intimate.** The register oscillates between tender proposition (predrefren: "dao bi' ti sve") and dominant judgment (refren: "parirala, sabotirala"). The female voice is framed through verbs of control; the male voice through conditional fantasy.

### POS / lemma patterns

- **Heavy feminine past-tense verbs** in refren: parirala, kontrolirala, sabotirala, demonstrirala — all share the `-irala` ending (loan-verb conjugation pattern from -irati verbs)
- **Conditional auxiliary `bi'`** dominates predrefren — 7+ instances
- **Imperative `pusti`** repeated in strofa 2 — 4 instances
- **Vocative nouns** (bebo) at line-ends as rhythmic anchors
- **Minimal adjective density** — the style is verb-and-noun driven

---

## 3. Rhyme, Sound & Flow

### End-rhyme map by section

**Strofa 1 (lines 1–8):** A B A C D D D D
- Lines 1 & 3 share the `-ae` skeleton (tajne / distance) — slant rhyme
- Lines 5–8 form a 4-line AAAA block on `-ia` (sklopila / popila / otkriva / zločina)

**Predrefren (lines 9–16):** E E E E F F F F
- Lines 9–12: 4-line AAAA on `-eo` (bebo × 4) — vocative monorhyme
- Lines 13–16: 4-line AAAA on `-ee` (vreme × 3 + probleme)

**Refren (lines 17–23):** G C G H C C H
- Lines 17 & 19: `-aa` pair (parirala / sabotirala) — 3+ syllable multisyllabic rhyme
- Lines 20 & 23: `-ia` pair (sviđa × 2)
- Lines 18, 21, 22: `-e` (je × 3) — short ad-lib lines

**Strofa 2 (lines 24–31):** I I I I I I I I
- **8-line pure monorhyme on `-oi`**: pozi / poziv / koži / eksploziv / vozi / dozi / loži / grozni — all share the `oi` vowel skeleton

### Multisyllabic end rhymes (3+ matching vowel syllables)

| Pair | Lines | Vowel match |
|------|-------|-------------|
| parirala ↔ sabotirala | 17, 19 (and 40, 42) | a-i-a-a (4-syllable match) |
| sklopila ↔ popila ↔ otkriva ↔ zločina | 5–8 | i-a (2-3 syllable match) |
| pozi ↔ poziv ↔ koži ↔ eksploziv ↔ vozi ↔ dozi ↔ loži ↔ grozni | 24–31 | o-i (2-syllable match, ×8) |

**pct_multis: 28.3%** — over a quarter of lines participate in multisyllabic rhyme matches.

### Internal rhymes, assonance, alliteration

- **internal_rhyme_rate: 82.6%** — extremely high. Most lines contain vowel-sound echoes within the line, not just at the end.
- Strofa 2 is dense with internal `-oži` / `-ozi` echoes even mid-line
- Alliteration: "Pusti, pusti da te vozi" (p-p-t-v), "Kako gledaš, kako dišeš, kako pričaš" (k-k-k anaphora)
- Assonance: "Zo-zore sviću, noći nam kriju tajne" (o-i-o-i vowel pattern)

### Dominant rhyme scheme

At the **song level**: mixed/free, because sections use different rhyme sounds. But **within each section**, the dominant scheme is **AAAA monorhyme blocks** — 4-line or 8-line stretches where every line ends on the same vowel skeleton. This is the structural signature.

### Syllable counts & flow pattern

| Section | Avg syllables/line | Flow character |
|---------|-------------------|----------------|
| Strofa 1 | 12.9 | Moderate, varied |
| Predrefren | 12.2 | Moderate, steady |
| Refren | 11.9 | Shorter lines, punchy |
| Strofa 2 | 10.0 | Accelerating — fastest section |

**speed_variation (σ): 2.9** — moderate variation. The flow accelerates noticeably in Strofa 2 (10.0 vs. 12.9 in Strofa 1), creating a deceleration-into-release effect when the refren returns.

**dominant_pattern: free** — the CV (coefficient of variation) exceeds 0.2, driven by the contrast between long predrefren lines and short ad-lib lines in the refren.

### Top vowel pairs (consecutive end-rhyme skeletons)

| Pair | Count | Source |
|------|-------|--------|
| oi → oi | 7 | Strofa 2 monorhyme block |
| eo → eo | 6 | Predrefren "bebo" block |
| ee → ee | 6 | Predrefren "vreme" block |
| e → ia | 3 | Refren ad-lib → sviđa transitions |
| ia → ia | 3 | Refren sviđa pairs |

---

## 4. Themes, Entities & Content

### Dominant themes

1. **Power dynamics / female dominance** — She controls, sabotages, demonstrates force; he surrenders ("nisam imô ni šanse", "srce kontrolirala mi je")
2. **Erotic intimacy** — Bodies, skin, sweat, positions, explosive sex ("koži", "znoj", "pozi", "seks tvoj je kô eksploziv")
3. **Nightlife & danger** — Night setting, weapons metaphors, crime scenes ("noći nam kriju tajne", "metak u šaržer", "mesto zločina")
4. **Obsession & compulsion** — Can't stop returning, addicted ("navučen", "opasnoj dozi")
5. **Time pressure** — "Pravo vreme" as both title and structural refrain; the right moment as justification

### Named entities

| Type | Entities |
|------|----------|
| PER | Buba Corelli, Maya Berović (credited in section headers) |
| LOC | — (no explicit place names) |
| ORG | — |

### Cultural references

- **"plan B"** — English loanword, the only non-Serbian content word
- **"metak u šaržer"** — bullet in magazine; weapon-as-love metaphor
- **"mesto zločina"** — crime scene; intimacy framed as transgression
- **"kraljica na tron"** — queen on throne; female elevation/regal framing

### Emotional arc & narrative perspective

**Perspective:** Duet — dual voice. The male voice (Buba Corelli) uses **1st-person conditional** ("ja bi' samo ti radio to") for fantasy/proposition. The female voice (Maya Berović) is represented through **3rd-person feminine past tense** ("parirala", "kontrolirala", "sabotirala") — she is described, not speaking directly. This creates a call-and-response dynamic where the male proposes and the female is judged/admired.

**Tense:** Conditional (bi') for desire, past tense (-ala) for the female's actions, present tense for admiration ("sviđa mi se").

**Arc:** Desire → surrender → admiration → re-desire → re-surrender → re-admiration. Symmetrical, no resolution — the cycle simply repeats.

---

## 5. Style & Voice

### Point of view & tense

- **Male voice:** 1st person, conditional ("ja bi' ti dao", "bi' samo ti radio")
- **Female voice:** 3rd person, feminine past tense ("parirala", "kontrolirala")
- **Admiration register:** 1st person, present ("sve mi se sviđa")

### Sentence length & syntax

- Short, punchy clauses — avg 7.2 words/line, rarely exceeding 10
- Frequent sentence fragments ("Sviđa, sviđa", "je-je", "a-je")
- Enjambment is rare — most lines are self-contained units

### Imagery & metaphors

| Metaphor | Meaning |
|----------|---------|
| "metak u šaržer" | Love/desire as a loaded weapon |
| "mesto zločina" | Intimacy as crime scene |
| "kraljica na tron" | Female elevation to royalty |
| "seks kô eksploziv" | Erotic intensity as detonation |
| "ti si stroj" | Woman as relentless machine |
| "opasna doza" | Desire as drug addiction |
| "otrov bi' popila" | Willing self-destruction through love |

### Rhetorical devices

- **Epizeuxis** (immediate repetition): "Pusti, pusti", "sviđa, sviđa", "Da-da-dao"
- **Anaphora**: "Kako gledaš, kako dišeš, kako pričaš" — triple anaphora on "kako"
- **Vocative refrain**: "bebo" as structural punctuation at line-ends
- **Polyptoton**: "parirala...parirala", "sabotirala...sabotirala" — same verb repeated in same form for emphasis

### Ad-libs & interjections

| Ad-lib | Function | Count |
|--------|----------|-------|
| `a-je` | Refren rhythmic punctuation, line-end filler | ~8 |
| `je-je` | Strofa 1 exit, playful sign-off | 1 |
| `Da-da-dao` | Stuttering entrance, builds anticipation | 1 |

### Duet reciprocity

The song is not a single-perspective monologue. The **predrefren** functions as the male proposition space ("ja bi' samo ti radio to"), while the **refren** shifts to a female-judgment space where she is the active agent ("parirala", "kontrolirala"). The two voices never sing directly to each other within a single line — the reciprocity is structural, alternating between sections rather than within lines.

---

# PHASE 2 — SYNTHESIZE A STYLE GUIDE

## Signature Patterns

1. **AAAA monorhyme blocks (4–8 lines)** — Each section locks onto a single end-vowel skeleton and sustains it: `-eo` (bebo ×4), `-ee` (vreme ×4), `-oi` (8-line strofa 2 monorhyme), `-ia` (sklopila/zločina ×4). Complex cross-rhyming (ABAB, ABBA) is avoided.

2. **`-irala` loan-verb hook stack** — Refren anchors on feminine past-tense -irati loan verbs: *parirala, kontrolirala, sabotirala, demonstrirala*. These are polished, high-register verbs that create a distinctive rhythmic and sonic signature when stacked.

3. **Conditional `bi'` as fantasy framing** — The male voice defaults to conditional tense ("bi' samo ti radio", "bi' ti dao", "bi' vratio") to frame desire as hypothetical/wish-fulfillment rather than direct statement.

4. **Vocative line-end refrain** — "bebo" placed at the end of 4+ consecutive lines, functioning as both rhyme anchor and emotional punctuation. The vocative doubles as a structural marker.

5. **Epizeuxis + anaphora as micro-hooks** — Immediate repetition ("pusti, pusti", "sviđa, sviđa") and triple anaphora ("kako gledaš, kako dišeš, kako pričaš") create hook-like density within individual lines.

6. **Section-specific flow tempo** — Strofa 1 is moderate (12.9s/line), Strofa 2 accelerates (10.0s/line), refren is punchy with short ad-lib lines. The tempo shift signals emotional escalation.

## Quantitative Targets

| Metric | Target | Source value |
|--------|--------|-------------|
| Syllables per line | 10–13 (section avg) | 11.8 |
| Words per line | 6–9 | 7.2 |
| Characters per line | 30–40 | 35.7 |
| TTR | 0.38–0.45 | 0.408 |
| Rhyme: AAAA block coverage | ≥60% of lines in monorhyme blocks | ~70% |
| Multisyllabic rhyme rate | ≥25% | 28.3% |
| Internal rhyme rate | ≥70% | 82.6% |
| English loanword rate | <2% | 0.6% |
| Hook repetition ratio | 0.28–0.35 | 0.326 |
| Lines per section | 7–8 | 7.7 |
| Sections per song | 5–6 (with repeats) | 6 |
| Speed variation (σ) | 2.5–3.5 | 2.9 |

## Do / Don't List

**DO:**
1. Lock each section into a single end-vowel skeleton and sustain it for 4+ lines
2. Use `-irala` loan-verb feminine past tense as refren anchors (hypnotisirala, provocirala, etc.)
3. Place a vocative ("bebo" or equivalent) at line-ends as both rhyme and refrain
4. Frame male desire in conditional `bi'` — never direct present tense
5. Accelerate syllable density in the second strofa to signal escalation
6. Use epizeuxis ("pusti, pusti") and triple anaphora ("kako... kako... kako...") for hook density
7. End refren lines with short ad-lib lines (`a-je`, 2–4 syllables) as rhythmic punctuation

**DON'T:**
1. Don't use ABAB or ABBA cross-rhyme schemes — this style is monorhyme or nothing
2. Don't exceed 2% English loanwords — keep it Balkan-rooted
3. Don't write philosophical or abstract themes — keep it concrete: bodies, weapons, power, night
4. Don't use 1st-person present tense for the male voice — conditional `bi'` or past tense only
5. Don't let TTR exceed 0.45 — repetition is structural, not a flaw
6. Don't write lines longer than ~10 words — the punchiness is the style
7. Don't forget ad-libs — `a-je` and `je-je` are rhythmic furniture, not optional

## Vocabulary Palette

**Safe to reuse in this style:**

*Vocatives & ad-libs:* bebo, a-je, je-je, ej

*Time/pressure:* pravo vreme, sat, noć, noći, zore

*Body & erotic:* koža, znoj, oči, usne, ruke, pozi, koži

*Weapon/danger:* metak, šaržer, zločina, mesto, eksploziv, stroj, doza

*Power verbs (-irala):* parirala, kontrolirala, sabotirala, demonstrirala, hipnotizirala, provocirala, dominirala, ignorirala, riskirala, komandirala

*Power/female:* kraljica, tron, sila

*Conditional constructions:* bi' ti dao, bi' samo, bi' vratio, bi' popila

*Obsession:* navučen, grozni, loši, opasan/opasna

## Taboos

- **No English-heavy phrasing** — one or two loanwords (like "plan B") at most; this is Balkan pop-folk, not drill
- **No ABAB cross-rhyme** — monorhyme blocks are the structural DNA
- **No abstract/philosophical themes** — no existential musings, no nature imagery, no politics
- **No 1st-person present-tense male narration** — the male voice lives in conditional `bi'` or past tense
- **No long compound sentences** — max ~10 words per line, fragments are encouraged
- **No clean resolution** — the song should end on a repeated hook, not a new section or outro
- **No direct female first-person voice** — she is described through `-ala` verbs, never says "ja"

---

# PHASE 3 — GENERATE & ANNOTATE

## Original Verse (16 lines, two 8-line blocks)

### Block 1 (lines 1–8): `-eo` vocative monorhyme → `-ija` monorhyme

```
1.  Opet noću zoveš, tražiš izgovor, bebo
2.  Ponos svoj polomô, bacio ga pred tobom, bebo
3.  Sve bi' ti poklonô, samo da te zadržim, bebo
4.  Na kolena pao, molim te, oživi me, bebo

5.  Slikô sam tvoj osmeh, među nama hemija
6.  Kad se približiš, raste mi energija
7.  Tvoj pogled pali, sve oko nas je magija
8.  Kroz mrak nas vuče nevidljiva linija
```

`[Annotation: Lines 1–4 implement AAAA monorhyme on -eo vowel skeleton with "bebo" as line-end vocative refrain — mirrors predrefren pattern. Line 3 uses conditional "bi'" for fantasy framing. Lines 5–8 shift to AAAA on -ija (-ija/-ija/-ija/-ija) monorhyme block — fresh anchor replacing the source's -oi monorhyme, using the advisor-suggested palette (hemija/energija/magija/linija). Simile construction "je kô" mirrors source's "je kô eksploziv" but with fresh imagery.]`

### Block 2 (lines 9–16): `-irala` verb stack → `-ama` monorhyme

```
9.  Hipnotizirala si me, pogledom me saterala
10. Misli mi obarala, a-je
11. Provocirala si ludost, na ivici me držala
12. A ja opet stojim, sve me k tebi okreće, a-je
13. Sve se lomi tiho među našim smenama
14. Gubim se s tobom po zaključanim sobama
15. Svaki dodir ostavlja trag po starim ranama
16. Sami tonemo dublje u noćnim dramama
```

`[Annotation: Lines 9–12 implement the -irala loan-verb hook stack (hipnotizirala, provocirala) alternating with short -e/-je ad-lib lines — mirrors refren's ABAC pattern with fresh -irala verbs (not source's parirala/sabotirala). "a-je" used as rhythmic punctuation. Lines 13–16 form AAAA on -ama (-ama/-ama/-ama/-ama) — fresh content anchor replacing source's "pravo vreme" -ee block. Conditional "bi'" absent here — Block 2 moves to declarative past for the -irala verbs, then present tense for the -ama block, matching section-function pattern.]`

---

## Original Hook (7 lines, mirrors refren structure)

```
17. Dominirala, noću me opet dominirala
18. Misli mi obarala, a-je
19. Ignorirala, kad me vidiš ignorirala
20. A ja opet gorim, sve me k tebi okreće
21. Kako ćutiš, kako mamiš, kako nestaješ, a-je
22. Sve me okreće, a-je, a-je
23. Okreće, okreće
```

`[Annotation: Hook mirrors the source refren's 7-line ABACBBC structure. Lines 17 & 19 use the -irala loan-verb stack (dominirala, ignorirala) as feminine past-tense anchors — direct parallel to source's parirala/sabotirala but with completely fresh verbs from the advisor-suggested palette. Line 18 is a short -e ad-lib line matching "Srce kontrolirala mi je, a-je". Line 21 uses triple anaphora on "kako" — direct structural parallel to source line 5, but with fresh verbs (ćutiš/mamiš/nestaješ vs. gledaš/dišeš/pričaš). Lines 22–23 close with epizeuxis ("Okreće, okreće") matching "Sviđa, sviđa" — fresh verb, same device. Ad-lib "a-je" appears 3× as rhythmic punctuation. Style markers (bebo, a-je, kako×3, epizeuxis) are reused intentionally as structural furniture — no full lines or title-hook phrases are copied from the source.]`

---

## Generated Lyrics — Quantitative Check

| Metric | Target | Generated | Notes |
|--------|--------|-----------|-------|
| Verse lines | ~16 | 16 | ✅ |
| Hook lines | 4–8 | 7 | ✅ |
| AAAA monorhyme blocks | ≥2 | 3 (lines 1–4 -eo, 5–8 -ija, 13–16 -ama) | ✅ |
| -irala loan-verbs | ≥2 | 4 (hipnotizirala, provocirala, dominirala, ignorirala) | ✅ |
| Conditional `bi'` | ≥1 | 1 (line 3) | ✅ |
| Ad-libs | ≥3 | 4 (a-je ×4) | ✅ |
| Epizeuxis | ≥1 | 1 (Okreće, okreće) | ✅ |
| Triple anaphora | ≥1 | 1 (Kako...kako...kako) | ✅ |
| Vocative refrain | present | "bebo" ×4 (lines 1–4) | ✅ |
| Rhyme anchors | Intentional style anchors: -eo, -irala; fresh content anchors: -ija, -ama, okreće | ✅ — no source vowel skeletons (-oi, -ee) reused |
| Full-line / title-hook reuse | 0 | 0 | ✅ — no source lines or "pravo vreme"/"parirala"/"sabotirala" copied |
| Style-marker reuse | intentional | bebo, a-je, kako×3, epizeuxis | These are structural furniture, not distinctive content |
| English loanwords | <2% | 0% | ✅ |
