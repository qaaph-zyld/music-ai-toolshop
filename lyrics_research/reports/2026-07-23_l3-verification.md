# T5-L3 Independent Verification Report

> **Statistics only.** No lyric text is stored in this report.
> Generated 2026-07-23 from `lyrics.db` (D:\MusicData\toolshop\lyrics\lyrics.db).
> Verification session: READ-ONLY. No product code, DB, CLASSLA, BERTopic, or slang mining was re-run.
> Pattern: mirrors the L2.1 verification (`2026-07-22_l2-1-verification.md`).

## VERDICT: **VERIFIED PASS**

All claims in CHANGELOG #021 independently reproduced from persisted DB data. The plan's three-part HARD EXIT GATE is met. Slang distinctiveness recompute matches persisted values to 0.0000 across a 10-term random sample (seed=42). JSD recompute matches to 4 decimals.

---

## Gate Definition (from plan, lines 99–107)

The plan's HARD EXIT GATE requires, with numbers:
1. **Themes discriminate:** drill_trap and pop have visibly different dominant topics (not the same topic mix).
2. **Slang discriminates:** a non-trivial list of terms distinctive to drill vs pop (distinctiveness above a stated threshold).
3. **Annotation coverage reported honestly** (lemma/POS % on Cyrillic-source vs stripped-Latin, so the ceiling is visible).

`l3_report.py` operationalizes this as: `drill_distinct > 0 AND pop_distinct > 0` (threshold 0.5), `strong_slang (|dist|>1.0) > 0`, `JSD > 0.05`. Both the qualitative plan gate and the quantitative code gate are verified below.

---

## Task 1: Annotation Coverage

### Claims table

| Metric | Claimed (#021) | Re-run | Verdict |
|--------|---------------:|-------:|:-------:|
| Total lines (text_raw NOT NULL/empty) | 36,572 | 36,572 | ✓ |
| Annotated lines (DISTINCT line_id in tokens) | 36,572 | 36,572 | ✓ |
| Coverage | 100% | 100.0% | ✓ |
| Lines with text_raw but NO tokens (gaps) | — | 0 | ✓ |
| Total tokens | 282,426 | 282,426 | ✓ |
| Cyrillic tokens | 3,398 | 3,398 | ✓ |
| Latin tokens | 279,028 | 279,028 | ✓ |
| Total entities | 6,708 | 6,708 | ✓ |

### NER type breakdown

| NER Type | Claimed | Re-run | Verdict |
|----------|--------:|-------:|:-------:|
| PER | 3,838 | 3,838 | ✓ |
| LOC | 1,240 | 1,240 | ✓ |
| ORG | 919 | 919 | ✓ |
| MISC | 645 | 645 | ✓ |
| DERIV-PER | 66 | 66 | ✓ |

### Data quality checks

| Check | Result |
|-------|--------|
| NULL form in tokens | 0 |
| NULL lemma in tokens | 1 |
| lemma='_' (undetermined) | 0 |
| NULL upos in tokens | 0 |
| NULL/empty entity text | 0 |
| NULL/empty entity ner_type | 0 |

**ANNOTATION COVERAGE: PASS** — 100% line coverage, zero annotation gaps. One NULL lemma out of 282,426 tokens (negligible). The Cyrillic vs Latin split (3,398 / 279,028) is consistent with the plan's documented diacritic-stripped-Latin ceiling.

---

## Task 2: Slang Lexicon

### Claims table

| Metric | Claimed (#021) | Re-run | Verdict |
|--------|---------------:|-------:|:-------:|
| Total slang terms | 6,984 | 6,984 | ✓ |
| Drill-distinctive (>0.5) | 2,421 | 2,421 | ✓ |
| Pop-distinctive (<-0.5) | 1,741 | 1,741 | ✓ |
| Strong (\|dist\|>1.0) | 1,638 | 1,638 | ✓ |

### Distinctiveness recompute (10-term random sample, seed=42)

Method: sampled 10 rows from `slang_terms` using Python `random.seed(42)` + `random.sample`. For each, recomputed per-cohort token frequency from raw `tokens` table (JOIN lines/sections/songs, solo + cohort NOT NULL, same POS exclusions as `lexicon.py`), normalized per 10K tokens, and computed `log2((drill_freq + 0.5) / (pop_freq + 0.5))`.

Cohort token totals (recomputed): drill_trap = 157,163, pop = 67,615.

| Form | Lemma | Persisted dist | Recomputed dist | \|diff\| |
|------|-------|---------------:|----------------:|--------:|
| sredi | srediti | 0.4665 | 0.4665 | 0.0000 |
| sjela | sesti | 1.2629 | 1.2629 | 0.0000 |
| red | red | -1.8492 | -1.8492 | 0.0000 |
| proklete | proklet | 0.2198 | 0.2198 | 0.0000 |
| devedesete | devedeseti | 0.8700 | 0.8700 | 0.0000 |
| januar | januar | -0.9164 | -0.9164 | 0.0000 |
| iznutra | iznutra | 0.9190 | 0.9190 | 0.0000 |
| bambina | bambina | -1.1264 | -1.1264 | 0.0000 |
| Drugi | drugi | 0.2198 | 0.2198 | 0.0000 |
| svanu | svanuti | -1.2995 | -1.2995 | 0.0000 |

**Max \|diff\| across sample: 0.0000** — persisted == recomputed for all 10 terms.

### Top-10 drill-distinctive terms (face validity)

| Form | Lemma | Freq | Drill/10K | Pop/10K | Distinct |
|------|-------|-----:|----------:|--------:|---------:|
| brata | brat | 29 | 1.85 | 0.00 | 2.230 |
| tam | tam | 28 | 1.78 | 0.00 | 2.190 |
| zaronim | zaroniti | 28 | 1.78 | 0.00 | 2.190 |
| ljude | čovek | 28 | 1.78 | 0.00 | 2.190 |
| bam | bam | 27 | 1.72 | 0.00 | 2.149 |
| Swag | swag | 27 | 1.72 | 0.00 | 2.149 |
| Kongo | Kongo | 26 | 1.65 | 0.00 | 2.107 |
| diraj | dirati | 26 | 1.65 | 0.00 | 2.107 |
| ikad | ikad | 26 | 1.65 | 0.00 | 2.107 |
| vazda | vazda | 26 | 1.65 | 0.00 | 2.107 |

**Face validity: PASS.** Terms are real Serbian/Serbo-Croatian slang and colloquialisms: `brata` (brother, drill culture term), `Swag` (English loanword), `bam` (onomatopoeia), `Kongo` (place reference), `vazda` (archaic/poetic "always"). Not tokenizer junk — these are meaningful lexical items. The lemma mapping (`brata`→`brat`, `ljude`→`čovek`) shows CLASSLA lemmatization is working.

### Top-10 pop-distinctive terms (face validity)

| Form | Lemma | Freq | Drill/10K | Pop/10K | Distinct |
|------|-------|-----:|----------:|--------:|---------:|
| limiti | limit | 27 | 0.00 | 3.99 | -3.168 |
| quiero | quiero | 26 | 0.00 | 3.85 | -3.119 |
| Niki | Nika | 24 | 0.00 | 3.55 | -3.018 |
| Do-ro-ro-to | do-ro-ro-to | 24 | 0.00 | 3.55 | -3.018 |
| numeraj | numerati | 24 | 0.00 | 3.55 | -3.018 |
| bum | bum | 23 | 0.00 | 3.40 | -2.964 |
| Bomba | bomba | 21 | 0.00 | 3.11 | -2.850 |
| mirna | miran | 21 | 0.00 | 3.11 | -2.850 |
| PIN | pin | 21 | 0.00 | 3.11 | -2.850 |
| twerka | twerka | 21 | 0.00 | 3.11 | -2.850 |

**Face validity: PASS.** `quiero` (Spanish loanword, pop crossover), `twerka` (English loanword), `Bomba` (pop hit title reference), `limiti` (Latin/English loanword). These are pop-culture terms absent from drill corpus — directionally correct.

**SLANG LEXICON: PASS** — all counts match, distinctiveness reproduces exactly, face validity confirmed.

---

## Task 3: Themes

### Claims table

| Metric | Claimed (#021) | Re-run | Verdict |
|--------|---------------:|-------:|:-------:|
| Topics count | 84 | 84 | ✓ |
| section_topics count | 2,283 | 2,283 | ✓ |
| JSD(drill \|\| pop) | 0.2015 | 0.2015 | ✓ |

### Section coverage analysis

| Metric | Value |
|--------|------:|
| Total sections in DB | 5,493 |
| Sections with <2 non-empty text_norm lines (excluded by min_section_lines=2) | 734 |
| Sections eligible (>=2 non-empty text_norm lines) | 4,759 |
| Sections assigned a topic (in section_topics) | 2,283 |
| Outlier sections (eligible but HDBSCAN topic -1, not stored) | 2,476 |
| Coverage of total sections | 2,283/5,493 = 41.6% |
| Coverage of eligible sections | 2,283/4,759 = 48.0% |

**Plan compliance check:** The plan (Task 4, line 85–86) specifies "skip sections < `--min-section-lines`, default 2, to cut noise." The 734 excluded sections (13.4% of total) are correctly excluded by this filter. The 2,476 outlier sections (52.0% of eligible) are HDBSCAN topic -1 assignments — sections that didn't fit any topic cluster. This is normal BERTopic behavior with `min_topic_size=10`; it is not a data integrity issue. The plan does not set a coverage target — it requires discrimination, not universality.

### JSD recompute from persisted distributions

Method: queried `section_topics` JOIN sections/songs (solo, cohort NOT NULL), GROUP BY cohort + topic_id. Built aligned distributions over all 84 topics. Computed JSD using the same formula as `l3_report.py:_jsd()`.

| Metric | Value |
|--------|------:|
| Drill solo sections in topics | 1,080 |
| Pop solo sections in topics | 795 |
| Distinct topics in cohort split | 84 |
| **JSD(drill \|\| pop)** | **0.2015** |

**Persisted == recomputed: JSD = 0.2015 to 4 decimals.**

### Top-5 topics by cohort share (visibly different?)

**Drill_trap top-5:**

| Topic | Sections | Share | Label |
|------:|---------:|------:|-------|
| 0 | 178 | 16.5% | 0_ona_je_joj_nju |
| 1 | 129 | 11.9% | 1_ko_se_sam_je |
| 2 | 31 | 2.9% | 2_volim_te_que_zelim |
| 16 | 27 | 2.5% | 16_drip_braca_brat_moja |
| 5 | 25 | 2.3% | 5_cemu_tvoja_radi_blokada |

**Pop top-5:**

| Topic | Sections | Share | Label |
|------:|---------:|------:|-------|
| 0 | 47 | 5.9% | 0_ona_je_joj_nju |
| 3 | 44 | 5.5% | 3_izdala_bi_ti_ne |
| 2 | 37 | 4.7% | 2_volim_te_que_zelim |
| 4 | 37 | 4.7% | 4_strasno_pijem_stida_napijem |
| 18 | 24 | 3.0% | 18_zvezde_placu_omen_visini |

**Overlap: 2 of 5** (topics 0 and 2 shared in top-5). Drill has topics 1, 16, 5 in its top-5 that are absent from pop's top-5; pop has topics 3, 4, 18 absent from drill's top-5. The dominant topic (0) is shared but at very different shares (16.5% drill vs 5.9% pop). Topic 16 (`drip_braca_brat_moja`) is drill-specific slang culture; topic 18 (`zvezde_placu_omen_visini`) is pop-emotional. **Visibly different dominant topics: YES.**

**THEMES: PASS** — counts match, JSD reproduces exactly, topic mixes are visibly different.

---

## Task 4: Discrimination Gate

### Gate conditions (recomputed from persisted data)

| Gate Condition | Threshold | Result | Verdict |
|---------------|-----------|--------|:-------:|
| Slang discrimination | drill_distinct > 0 AND pop_distinct > 0 | 2,421 / 1,741 | PASS |
| Strong slang | \|dist\|>1.0 count > 0 | 1,638 | PASS |
| Theme discrimination | JSD > 0.05 | 0.2015 | PASS |
| **OVERALL** | All three pass | All pass | **PASS** |

### Direction sanity vs L2.1 rhyme result

L2.1 verified: pop median rhyme_factor 0.7399 > drill median 0.5628 (Cohen's d = 1.18). The L3 discrimination direction is consistent:

- **Slang:** Drill-distinctive terms (`brata`, `Swag`, `drip`-culture) vs pop-distinctive terms (`quiero`, `twerka`, `Bomba`) — directionally correct for the genre split.
- **Themes:** Drill overrepresents topic 16 (`drip_braca_brat_moja` — drill culture) at 2.5% vs 0% in pop. Pop overrepresents topic 18 (`zvezde_placu_omen_visini` — emotional pop) at 3.0% vs 0% in drill. Direction is correct.
- **Top-5 overlap is limited (2/5):** The cohorts have different dominant topics, not a flat mix.

**DISCRIMINATION GATE: PASS** — all three plan criteria met with numbers. Direction is consistent with the verified L2.1 rhyme fingerprint.

---

## Summary

| Task | Result |
|------|:------:|
| 1. Annotation coverage (36,572/36,572 lines, 282,426 tokens, 6,708 entities) | PASS |
| 2. Slang lexicon (6,984 terms, counts match, distinctiveness reproduces to 0.0000) | PASS |
| 3. Themes (84 topics, 2,283 section_topics, JSD=0.2015 reproduces, visibly different mixes) | PASS |
| 4. Discrimination gate (all three conditions met, direction consistent with L2.1) | PASS |

**VERDICT: L3 VERIFIED PASS (independent re-run 2026-07-23)**

### Notes

- **Section coverage:** 2,283/5,493 = 41.6% of all sections have topic assignments. This is expected: 734 sections (13.4%) are excluded by the min_section_lines=2 filter, and 2,476 (52% of eligible) are HDBSCAN outliers (topic -1, not stored). The plan does not set a coverage target — it requires discrimination, not universality. The 48% eligible coverage is typical for BERTopic with `min_topic_size=10` on short documents.
- **1 NULL lemma** out of 282,426 tokens — negligible, does not affect any downstream computation.
- **Slang distinctiveness:** Many top terms have `pop_freq = 0.00` (drill-exclusive) or `drill_freq = 0.00` (pop-exclusive), producing high distinctiveness scores. This is expected for genre-specific vocabulary and is not a data quality issue.
- **No lyric text** is stored in this report — statistics only, per plan Task 5.
