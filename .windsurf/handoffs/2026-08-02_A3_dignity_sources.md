# Handoff: A3 — Planetary Dignity & Relationship Source Research

**Date:** 2026-08-02
**Agent:** A3
**Task:** Research planetary dignities, relationships, aspects, and combustion rules from classical Jyotish sources for Kundli AI v3.0
**Status:** Completed

---

## Summary

Researched and documented planetary dignities, relationships (natural/temporary/compound), aspects (Graha Drishti and Rashi Drishti), combustion rules, retrograde rules, and Vargottama definition from four classical Jyotish sources: BPHS, Brihat Jataka, Jataka Parijata, and Saravali. All entries include source verse citations, YAML frontmatter metadata, machine-readable structured data, and cross-reference notes documenting where sources disagree.

---

## Files Created

| # | File Path | Content | Lines |
|---|-----------|---------|-------|
| 1 | `knowledge/classical/bphs/dignities.md` | BPHS dignities (7 planets + Rahu/Ketu), combustion, retrograde, vargottama, benefic/malefic, ratio of effects | ~380 |
| 2 | `knowledge/classical/brihat_jataka/dignities.md` | Brihat Jataka dignity table, Naisargika Maitri (natural friendship), Tatkalika Maitri, Panchadha Maitri | ~230 |
| 3 | `knowledge/classical/jataka_parijata/relationships.md` | Tatkalika/Panchadha Maitri, Graha Drishti, Rashi Drishti (Jaimini), comparison table | ~280 |
| 4 | `knowledge/classical/bphs/aspects.md` | BPHS Graha Drishti rules, fractional aspects, mathematical calculation, Rahu/Ketu aspect debate (5 traditions) | ~290 |

**Total:** 4 knowledge files, ~1,180 lines of documented source material.

**No source code files were modified.** All output is in `knowledge/classical/` directory only.

---

## Dignity/Relationship Coverage Matrix

| Topic | BPHS | Brihat Jataka | Jataka Parijata | Saravali | Coverage |
|-------|------|---------------|-----------------|----------|----------|
| Exaltation signs & degrees | ✅ Ch.3 vv.49-50 | ✅ Ch.2 | — | ✅ Ch.3 vv.35-36 | Complete |
| Debilitation signs & degrees | ✅ Ch.3 vv.49-50 | ✅ Ch.2 | — | ✅ Ch.3 vv.35-36 | Complete |
| Moolatrikona ranges | ✅ Ch.3 vv.51-54 | — | — | ✅ Ch.3 vv.21-24 | Complete |
| Own signs | ✅ Ch.3 vv.51-54 | — | — | ✅ Ch.3 vv.21-24 | Complete |
| Rahu/Ketu dignities | ⚠️ Ch.47 (debated) | ❌ Silent | — | ❌ Silent | Partial — 3 traditions documented |
| Natural benefic/malefic | ✅ Ch.3 | ✅ Ch.2 | — | ✅ Ch.4 | Complete |
| Combustion (Asta) degrees | ✅ Ch.7/28 vv.28-29 | — | ✅ Contextual | ✅ Ch.4 (Vikalavastha) | Complete |
| Retrograde rules | ✅ Ch.3 vv.21-25 | — | — | ✅ Ch.4 vv.14-15 | Complete |
| Vargottama | ⚠️ Distributed | — | — | — | Medium — defined in Horaratnam/commentaries |
| Natural friendship (Naisargika) | ✅ Ch.3 v.55 | ✅ Ch.2 vv.15,17 | ✅ Ch.1 | ✅ Same as BPHS | Complete |
| Temporary friendship (Tatkalika) | ✅ Ch.3 v.56 | ✅ Ch.2 v.18 | ✅ Ch.1 | — | Complete |
| Compound friendship (Panchadha) | ✅ Ch.3 vv.57-58 | ✅ Ch.2 v.18 | ✅ Ch.1 | — | Complete |
| Graha Drishti (general 7th) | ✅ vv.2-5 | ✅ Ch.2 | ✅ Ch.1 | ✅ | Complete |
| Graha Drishti (special aspects) | ✅ vv.2-5 | ✅ Ch.2 | ✅ Ch.1 | ✅ | Complete |
| Graha Drishti (fractional) | ✅ vv.2-5 | — | — | — | Complete |
| Graha Drishti (mathematical) | ✅ vv.6-12 | — | — | — | Complete |
| Rahu/Ketu aspects | ❌ Silent | ❌ Silent | — | — | Documented — 5 traditions |
| Rashi Drishti (Jaimini) | ⚠️ Early chapters | — | ✅ | — | Complete |
| Ratio of effects by dignity | ✅ Ch.3 vv.59-60 | ✅ Ch.2 | — | ✅ Ch.3 vv.25-26 | Complete |

**Legend:** ✅ = Documented with verse citations | ⚠️ = Present but with caveats | ❌ = Silent/not mentioned | — = Not covered in this source

---

## Gaps and Disagreements Between Sources

### 1. Rahu/Ketu Dignities (Major Disagreement)

**BPHS Ch.3 is silent** on Rahu/Ketu exaltation, debilitation, and Moolatrikona. Three traditions exist:
- **Tradition A:** Rahu exalted in Taurus, Ketu in Scorpio (Sarvartha Chintamani, BPHS Ch.47)
- **Tradition B:** Rahu exalted in Gemini, Ketu in Sagittarius (Jaimini, Northern India)
- **Tradition C:** Rahu exalted in Scorpio, debilitated in Taurus (Veemesaram, Southern India)

**Recommendation:** Implement as configurable, default to Tradition A. Judge by sign lord and nakshatra rather than dignity alone.

### 2. Rahu/Ketu Aspects (Major Disagreement)

**BPHS does not explicitly mention** Rahu/Ketu aspects. Five traditions documented:
- 5th/7th/9th (most common, like Jupiter)
- 7th only (conservative)
- 3rd/7th/10th (like Saturn, some South Indian)
- No aspects (Adityaguruji)
- 5th/7th/9th/2nd (Parasara.net extended)

**Recommendation:** Default to 5th/7th/9th (Tradition 1), allow configuration.

### 3. Venus Moolatrikona Range (Minor Disagreement)

- **BPHS:** Libra 0°–15° (first half)
- **Saravali:** Libra 0°–5° (first 5 degrees only)

**Recommendation:** Follow BPHS (0°–15°) as primary; note Saravali's variant.

### 4. Saturn Combustion Orb (Minor Disagreement)

- **Most sources (BPHS, Phaladeepika):** 15°
- **One modern implementation (vedaksha crate):** 16°

**Recommendation:** Use 15° (standard BPHS value).

### 5. Combustion Chapter Number (Citation Uncertainty)

- **Vedaksha crate:** BPHS Ch.7 vv.28-29
- **Some web sources:** BPHS Ch.28
- Different editions of BPHS have different chapter numbering.

**Recommendation:** Cite as "BPHS, combustion chapter (number varies by edition), vv.28-29."

### 6. Vargottama Source (Citation Gap)

BPHS does not have a single dedicated verse defining Vargottama. The concept is distributed across commentaries (Horaratnam, Bala Bhadra). 

**Recommendation:** Cite as "BPHS tradition / Horaratnam" with confidence: medium.

### 7. Aspect Strength — Fractional vs Full (Interpretive Disagreement)

- **Standard interpretation:** All planets full on 7th; Mars/Jupiter/Saturn full on special houses.
- **Pathak/Shastri edition:** Mars 1/4 on 7th, Jupiter 1/2 on 7th, Saturn 3/4 on 7th (not full).

**Recommendation:** Use standard (full 7th for all) for interpretation; use fractional for Shadbala/Drig Bala.

### 8. Jataka Parijata Direct Verse Citations (Availability Gap)

Jataka Parijata's full text with verse numbers is less available online than BPHS or Brihat Jataka. The rules are confirmed through multiple secondary sources but exact verse numbers are less certain.

**Recommendation:** Confidence marked as "medium-high" for Jataka Parijata entries. Chapter/section cited rather than exact verse numbers where uncertain.

---

## Bootstrap Prompt for Next Session

If more work is needed on this knowledge base, use the following prompt:

```text
FRAMEWORK BOOTSTRAP (v12) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.

MY TASK: Continue building the Kundli AI v3.0 classical knowledge base. 
The following files have been created by Agent A3:
- knowledge/classical/bphs/dignities.md — BPHS dignities, combustion, retrograde, vargottama
- knowledge/classical/brihat_jataka/dignities.md — Brihat Jataka dignity + friendship tables
- knowledge/classical/jataka_parijata/relationships.md — relationships, Graha/Rashi Drishti
- knowledge/classical/bphs/aspects.md — BPHS aspects + Rahu/Ketu debate

GAPS TO ADDRESS (from handoff 2026-08-02_A3_dignity_sources.md):
1. Jataka Parijata direct verse citations need verification (medium confidence)
2. Saravali needs its own knowledge file for dignity/combustion/retrograde data
3. Phaladeepika yoga-related aspect rules not yet documented
4. Jaimini Sutras Rashi Drishti needs dedicated file with verse citations
5. BPHS Shadbala chapter (Drig Bala) fractional aspect calculations need dedicated file
6. Rahu/Ketu dignity traditions need deeper research into primary sources

OPEN FILES: d:\Project\astrology\kundli-ai\knowledge\classical\bphs\dignities.md
```

---

## Research Sources Consulted

| Source | URL | Content Retrieved |
|--------|-----|-------------------|
| Divyachadhava BPHS Ch.3 | divyachadhava.com | Full verse text vv.45-65 |
| WisdomLib Brihat Jataka Ch.2 | wisdomlib.org | Verse 2.15, 2.17 word-for-word |
| Siva.sh Brihat Jataka | siva.sh | Verse 2.18 full text |
| Astrojyoti BPHS | astrojyoti.com | Aspect verses vv.2-12 |
| Astrojyoti Saravali | astrojyoti.com | Ch.3 vv.35-36, Ch.4 vv.14-15 |
| Archive.org Saravali | archive.org | Full text search |
| Vedaksha Rust crate | github.com | Combustion implementation (BPHS Ch.7 vv.28-29) |
| PanchangBodh | panchangbodh.com | Combustion orb verification |
| Moonketu | moonketu.com | Tatkalika Maitri, Rashi Drishti rules |
| Parasara.net | parasara.net | Graha Drishti, Rahu/Ketu aspects |
| Sushmajee | sushmajee.com | BPHS Ch.3 vv.55-58 relationships |
| AstroSight | astrosight.ai | Graha vs Rashi Drishti comparison |
| OurNakshatra | ournakshatra.com | Combustion, aspect strengths |
| Bhrigu Ashram | bhriguashram.org | Vargottama definition |
| Sri Garuda (Visti Larsen) | srigaruda.com | Vargottama extended definition |
| Horaratnam (astrojyoti) | astrojyoti.com | Vargottama, dignity effects |
