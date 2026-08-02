# Handoff: Dasha System Source Research (A4)

**Date**: 2026-08-02
**Session**: Dasha systems research for Kundli AI v3.0 knowledge base
**Status**: COMPLETE

---

## Summary

Researched Dasha systems from three classical Jyotish sources (BPHS, Jaimini Sutras, Phaladeepika) and produced three structured Markdown knowledge files with YAML frontmatter, calculation methods, interpretation rules, favorability rules, and verse citations. No existing source files were modified.

### Research Sources Used

| Source | Reference | URL/Format |
|--------|-----------|------------|
| BPHS (R. Santanam translation) | Full text | archive.org (BPHS English) |
| BPHS (S.P. Tata) | Chapter excerpts | astrojyoti.com |
| BPHS (vedpuran.net) | PDF with chapter index | vedpuran.net |
| Phaladeepika (V.S. Sastri & Iyer) | Ch.19 & Ch.20 full text | wisdomlib.org |
| Phaladeepika (S.P. Tata) | Ch.19 excerpts | astrojyoti.com |
| Jaimini Sutras (Sanjay Rath) | Narayana, Sudasa, Moola, Chara | srath.com, shreekundli.com |
| Jaimini Chara Dasha (K.N. Rao method) | Calculation method | moonketu.com, astrojyoti.com |
| Crux of Vedic Astrology (Sanjay Rath) | Narayana/Sudasa comparison | archive.org |
| Jaimini Upadesa Sutras (overview) | Chapter structure | astroamerica.com, exoticindiaart.com |

---

## Files Created

| File | Description | Size |
|------|-------------|------|
| `d:\Project\astrology\kundli-ai\knowledge\classical\bphs\dashas.md` | BPHS Dasha systems: Vimshottari, Ashtottari, Kalachakra, other dashas list | ~12KB |
| `d:\Project\astrology\kundli-ai\knowledge\classical\jaimini_sutras\dashas.md` | Jaimini Dasha systems: Narayana, Sudasa, Moola, Chara | ~14KB |
| `d:\Project\astrology\kundli-ai\knowledge\classical\phaladeepika\dashas.md` | Phaladeepika Dasha interpretation: dasha-phala per planet, house lord rules, Yogakaraka, favorability, death timing | ~16KB |

---

## Dasha System Coverage Matrix

| Dasha System | Source | Calculation | Interpretation | Favorability | Confidence | Implementation Ready |
|--------------|--------|-------------|----------------|--------------|------------|---------------------|
| **Vimshottari** | BPHS Ch.46 | Complete (nakshatra-based, balance at birth) | Complete (Ch.48 house lords, Ch.52-60 Antardashas) | Complete (dignity, placement, Kendra-Trikona) | High | Yes |
| **Ashtottari** | BPHS Ch.46 | Complete (Ardra-based, 108yr, 8 planets) | General (same principles as Vimshottari) | Same as Vimshottari | High | Yes |
| **Kalachakra** | BPHS Ch.49 | Partial (structure clear, per-pada details complex) | General (sign as temporary Lagna) | General | Medium | Needs further research |
| **Narayana** | Jaimini 2.4 | Complete (sign-to-lord distance, odd/even) | Complete (Rashi Drishti, Argala, Karakas) | Complete (sign-based assessment) | High | Yes |
| **Sudasa** | Jaimini 2.4 | Partial (Dwara-Bahya rules need more detail) | General (wealth-focused, 2nd/11th houses) | General | Medium | Needs Sanjay Rath book |
| **Moola** | Tradition (srath.com) | Complete (Mulatrikona distance, two cycles) | Complete (D60 correlation, karmic roots) | N/A (karmic, not favorable/unfavorable) | Medium | Yes (with caveats) |
| **Chara** | Jaimini 2.3 | Complete (9th house direction, sign-to-lord) | Complete (house from Lagna, Karakas, Rashi Drishti) | Complete (planets in sign, lord strength) | High | Yes |
| **Phaladeepika Dasha-phala** | PD Ch.19 | N/A (uses Vimshottari) | Complete (per-planet, well/ill-placed) | Complete (Vargottama, transit, Yogakaraka) | High | Yes |
| **Phaladeepika House Lord** | PD Ch.20 | N/A (uses Vimshottari) | Complete (12 house lords, strong/weak) | Complete (Yogakaraka, Kendra dosha, transit) | High | Yes |

---

## Gaps and Uncertainties

### High Confidence (well-established from multiple sources)
- Vimshottari sequence, years, and calculation method -- verified across BPHS, Phaladeepika, and existing `dasha_engine.py`
- Antardasha calculation formula -- confirmed in both BPHS Ch.51 and Phaladeepika Ch.21
- BPHS Ch.48 favorability rules (house lord placement, Kendra-Trikona relationships)
- Phaladeepika per-planet dasha-phala (Ch.19, v.4-26) -- direct verse citations
- Phaladeepika Yogakaraka rules (Ch.20, v.43-51) -- direct verse citations
- Chara Dasha general structure and K.N. Rao calculation method

### Medium Confidence (single source or commentator disagreement)
- **Kalachakra Dasha**: Per-pada year assignments and gati (motion) rules are complex. BPHS Ch.49 spans many verses with commentator disagreements (B.V. Raman vs. Sanjay Rath). The structural principles are sound, but specific numeric assignments need verification against a trusted commentary.
- **Sudasa**: The Dwara-Bahya Rasi rules and the special Saturn/Ketu rule are primarily from Sanjay Rath's commentary. The general principles are clear, but the exact sutra-by-sutra calculation procedure requires reference to Sanjay Rath's "Upadesa Sutras" (1997) book.
- **Moola Dasha**: Not explicitly in extant Jaimini Sutras text. Sanjay Rath states it was "a secret of the tradition of Orissa." Mentioned in Saravali and Varahamihira but without calculation method. The calculation comes from Sanjay Rath's traditional lineage only.
- **Chara Dasha method differences**: K.N. Rao vs. P.V.R. Narasimha Rao methods differ on forward/backward sign grouping and exaltation adjustments. The K.N. Rao method is dominant in modern Indian practice.

### Low Confidence (not found or could not verify)
- **Exact verse numbers for some BPHS passages**: The BPHS chapter/verse numbering varies between the Santanam and Tata translations. Verse ranges are approximate.
- **Ashtottari sub-period calculation**: The "1/4 for malefics, 1/3 for benefics" rule is mentioned but the exact verse could not be precisely cited.
- **Kalachakra gati transition rules**: Could not find a clear, consensus description of when savya/apasavya transitions occur at sign boundaries.

---

## Cross-Source Verification: Vimshottari Sequence and Years

| Planet | BPHS Ch.46 | Phaladeepika Ch.19 | dasha_engine.py | Verified |
|--------|------------|---------------------|-----------------|----------|
| Ketu | 7 | 7 | 7 | Yes |
| Venus | 20 | 20 | 20 | Yes |
| Sun | 6 | 6 | 6 | Yes |
| Moon | 10 | 10 | 10 | Yes |
| Mars | 7 | 7 | 7 | Yes |
| Rahu | 18 | 18 | 18 | Yes |
| Jupiter | 16 | 16 | 16 | Yes |
| Saturn | 19 | 19 | 19 | Yes |
| Mercury | 17 | 17 | 17 | Yes |
| **Total** | **120** | **120** | **120** | **Yes** |

All three sources agree on the Vimshottari sequence and year allocations.

---

## Bootstrap Prompt for Next Session

```
TASK: Continue Dasha system research for Kundli AI v3.0 knowledge base.

PREVIOUS WORK: Three knowledge files were created in the previous session:
- knowledge/classical/bphs/dashas.md (Vimshottari, Ashtottari, Kalachakra)
- knowledge/classical/jaimini_sutras/dashas.md (Narayana, Sudasa, Moola, Chara)
- knowledge/classical/phaladeepika/dashas.md (Dasha-phala, house lord rules, Yogakaraka)

REMAINING GAPS TO ADDRESS:
1. Kalachakra Dasha: Obtain per-pada year assignments and gati transition rules from BPHS Ch.49 full text. Cross-check with B.V. Raman's "How to Judge a Horoscope" and Sanjay Rath's "Crux of Vedic Astrology."
2. Sudasa: Obtain Sanjay Rath's "Upadesa Sutras" (1997) book for complete Dwara-Bahya calculation rules and the special Saturn/Ketu rule.
3. Moola Dasha: Cross-verify the Mulatrikona-based period calculation with additional traditional sources beyond Sanjay Rath.
4. Chara Dasha: Document the P.V.R. Narasimha Rao method as an alternative to the K.N. Rao method, noting specific differences in sign grouping and duration calculation.
5. BPHS verse numbering: Verify exact verse numbers against the Devanagari critical edition (R. Santhanam or V. Iyer editions).

CONSTRAINTS:
- RESEARCH ONLY -- do NOT modify any files in src/
- Do NOT fabricate verses -- mark confidence as "medium" or "low" if exact verse cannot be found
- All output goes to knowledge/classical/ subdirectories only
- Maintain the YAML frontmatter format established in the existing knowledge files

KEY FILES TO REFERENCE:
- d:\Project\astrology\kundli-ai\src\dasha_engine.py (existing Vimshottari implementation)
- d:\Project\astrology\kundli-ai\knowledge\classical\bphs\yogas.md (format template)
- d:\Project\astrology\kundli-ai\knowledge\classical\bphs\dashas.md (BPHS dasha research)
- d:\Project\astrology\kundli-ai\knowledge\classical\jaimini_sutras\dashas.md (Jaimini dasha research)
- d:\Project\astrology\kundli-ai\knowledge\classical\phaladeepika\dashas.md (Phaladeepika dasha research)
```

---

## Implementation Notes for Kundli AI v3.0

The knowledge files are structured to support implementation of dasha calculation and interpretation in the Kundli AI engine:

1. **Vimshottari**: Already partially implemented in `dasha_engine.py`. The research confirms the existing constants and provides the complete calculation method for the initial balance at birth (Moon's nakshatra position).

2. **Ashtottari**: Implementation-ready. The key differences from Vimshottari are: 108-year cycle, 8 planets (no Ketu), Ardra-based nakshatra assignment, different year allocations.

3. **Kalachakra**: NOT implementation-ready without further research. The per-pada year assignments and gati rules need to be resolved.

4. **Narayana Dasha**: Implementation-ready. The sign-to-lord distance calculation with odd/even direction rules is well-defined.

5. **Sudasa**: Partially implementation-ready. The Moon-sign-strength determination and basic period calculation are clear, but the Dwara-Bahya sequence rules need more detail.

6. **Moola Dasha**: Implementation-ready with caveats. The Mulatrikona-based period calculation is well-defined, but the traditional source is single-lineage (Sanjay Rath).

7. **Chara Dasha**: Implementation-ready. The K.N. Rao method is well-documented and widely used in software.

8. **Phaladeepika interpretation rules**: These are interpretive guidelines rather than calculation methods. They can be used to build an interpretation engine that assesses Mahadasha/Antardasha favorability based on the factors described in Ch.20.
