# Handoff: Divisional Charts & Ashtakavarga Source Research

**Date:** 2026-08-02
**Session:** A5 — Divisional Charts and Ashtakavarga Source Research
**Project:** Kundli AI v3.0
**Status:** Complete

---

## Summary

Researched divisional charts (D-1 through D-60) and Ashtakavarga from classical Jyotish sources (BPHS, Saravali) and created Markdown knowledge files for the Kundli AI v3.0 knowledge base. All work is research-only — no source code files were modified.

### Sources Consulted

1. **BPHS Chapter 6** ("The Sixteen Divisions of a Rashi") — Full English translation from divyachadhava.com
2. **BPHS Chapter 7** ("Divisional Considerations") — Full English translation from divyachadhava.com
3. **BPHS Chapters 66-72** (Ashtakavarga) — Referenced via vedastro.org, dekhopanchang.com, tempora.ltd, astrobix.com, jyotishvidya.com
4. **Saravali Chapters 3, 51, 53-54** — Full text from archive.org public domain edition
5. **Saravali Varga Viswa** — saravali.github.io
6. **VedAstro Ashtakavarga Guide** — vedastro.org (for BAV table verification)
7. **Existing code:** `varga_matrix.py`, `parse_jhora.py` (for code convention cross-referencing)

---

## Files Created

| # | File | Size | Content |
|---|------|------|---------|
| 1 | `knowledge/classical/bphs/divisional_charts.md` | ~25KB | All 16 Shodasavarga charts with YAML frontmatter, calculation methods, significance, interpretation rules, source text. Vimsopaka Bala (4 schemes). Vaiseshikamsa. General interpretation rules. Code cross-references. |
| 2 | `knowledge/classical/bphs/ashtakavarga.md` | ~20KB | Complete BAV benefic place tables for all 7 planets. SAV calculation and interpretation. Sodhya Pinda (Rashi/Graha Gunakar, Trikona/Ekadhipatya Shodhana). Score interpretation ranges (BAV 0-8, SAV 0-56). Per-planet BAV effects (Saravali Ch.54). Kakshya system. Code cross-references. |
| 3 | `knowledge/classical/saravali/divisional_charts.md` | ~22KB | Source-faithful: General varga rules (Ch.3), Navamsa effects for all 108 Navamsas (Ch.51), Ashtakavarga tables (Ch.53), Ashtakavarga effects (Ch.54). Explicit gap documentation for uncovered charts. |
| 4 | `.windsurf/handoffs/2026-08-02_A5_divisional_ashtakavarga_sources.md` | This file | Handoff document with coverage matrix and bootstrap prompt |

---

## Divisional Chart Coverage Matrix

| Chart | BPHS Calculation | BPHS Significance | BPHS Interpretation | Saravali Calculation | Saravali Effects | Vimsopaka Weight |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| D-1 (Rashi) | ✅ | ✅ | ✅ | ✅ | — | 3.5 (Shodasa) |
| D-2 (Hora) | ✅ | ✅ | ✅ | ✅ | — | 1 (Shodasa) |
| D-3 (Drekkana) | ✅ | ✅ | ✅ | ✅ | — (Ch.50 separate) | 1 (Shodasa) |
| D-4 (Chaturthamsa) | ✅ | ✅ | ✅ | — | — | 0.5 (Shodasa) |
| D-7 (Saptamsa) | ✅ | ✅ | ✅ | ✅ | — (fallback) | 0.5 (Shodasa) |
| D-9 (Navamsa) | ✅ | ✅ | ✅ | ✅ | ✅ (108 Navamsas) | 3 (Shodasa) |
| D-10 (Dashamsa) | ✅ | ✅ | ✅ | — | — | 0.5 (Shodasa) |
| D-12 (Dvadashamsa) | ✅ | ✅ | ✅ | ✅ | — (per 51.110) | 0.5 (Shodasa) |
| D-16 (Shodashamsa) | ✅ | ✅ | ✅ | — | — | 2 (Shodasa) |
| D-20 (Vimshamsa) | ✅ | ✅ | ✅ | — | — | 0.5 (Shodasa) |
| D-24 (Chaturvimshamsa) | ✅ | ✅ | ✅ | — | — | 0.5 (Shodasa) |
| D-27 (Saptavimshamsa) | ✅ | ✅ | ✅ | — | — | 0.5 (Shodasa) |
| D-30 (Trimshamsa) | ✅ | ✅ | ✅ | ✅ | — | 1 (Shodasa) |
| D-40 (Khavedamsa) | ✅ | ✅ | ✅ | — | — | 0.5 (Shodasa) |
| D-45 (Akshavedamsa) | ✅ | ✅ | ✅ | — | — | 0.5 (Shodasa) |
| D-60 (Shashtyamsa) | ✅ | ✅ | ✅ | — | — | 4 (Shodasa) |

**Legend:** ✅ = covered, — = not covered in that source

### Vimsopaka Bala Coverage

| Scheme | Divisions | Total Points | Covered |
|--------|-----------|-------------|---------|
| Shad Varga | 6 (D-1, D-2, D-3, D-9, D-12, D-30) | 20 | ✅ |
| Sapta Varga | 7 (Shad + D-7) | 20 | ✅ |
| Dasa Varga | 10 (Sapta + D-4, D-10, D-16, D-60) | 20 | ✅ |
| Shodasa Varga | 16 (all) | 20 | ✅ |

### Ashtakavarga Coverage

| Topic | BPHS | Saravali | Covered |
|-------|:---:|:---:|:---:|
| BAV benefic place tables (7 planets) | ✅ | ✅ | ✅ |
| SAV calculation (337 constant) | ✅ | — | ✅ |
| BAV score interpretation (0-8) | ✅ | ✅ | ✅ |
| SAV score interpretation (0-56) | ✅ | — | ✅ |
| Trikona Shodhana | ✅ (Ch.67) | — | ✅ |
| Ekadhipatya Shodhana | ✅ (Ch.68) | — | ✅ |
| Sodhya Pinda (Rashi + Graha Pinda) | ✅ (Ch.69) | — | ✅ |
| Rashi Gunakar table | ✅ | — | ✅ |
| Graha Gunakar table | ✅ | — | ✅ |
| Per-planet BAV effects | — | ✅ (Ch.54) | ✅ |
| Transit effectiveness by sign position | — | ✅ (Ch.53.9-10) | ✅ |
| Kakshya system | — | — | ✅ (documented) |
| Vaiseshikamsa | ✅ (Ch.7) | — | ✅ (medium confidence) |

---

## Gaps and Uncertainties

### High-Priority Gaps

1. **Mercury BAV table discrepancy:** Arithmetic sum of listed benefic places = 55, but traditional total = 54. Saravali Ch.53.5 groups Mars and Saturn together ("from Mars and Saturn in similar Signs"), which may resolve this — if Mars and Saturn share the same benefic places for Mercury (8 places each = 16, not 8+8=16 separately), the total works out differently. Requires verification against primary Sanskrit text.

2. **Venus BAV table discrepancy:** Arithmetic sum = 51, but traditional total = 52. One benefic place may be missing from the contributor lists. Requires verification against primary Sanskrit text.

3. **Graha Gunakar for Mars:** BPHS Ch.69 states "3 for Mangal" in one reading, while the variant (Grahman Chakr) gives 8. Both documented; the widely-used value is 8.

4. **Rashi Gunakar for Virgo:** BPHS Ch.69 states "6 for Kanya", while some later texts use 5. BPHS value (6) documented as primary.

5. **Vaiseshikamsa classifications:** The exact classification names (e.g., Gopura) and their criteria could not be fully verified from available translations. Marked as confidence: medium. The existing `parse_jhora.py` code expects `dasa_varga` and `shodasa_varga` fields with format like "4-Gopura", suggesting a count-based classification system.

### Lower-Priority Gaps

6. **Saravali Ch.50 (Drekkana effects):** Not included in this research — Saravali Ch.50 covers all 36 Drekkanas for lost horoscopy. Could be added as a separate knowledge file if needed.

7. **Phaladeepika Ashtakavarga:** Referenced in the task description but not deeply researched. Phaladeepika Ch.13 extends Ashtakavarga with practical interpretive rules. Could be a future research deliverable.

8. **Exact BPHS verse numbering:** Chapter numbering varies between editions (e.g., some editions combine Ch.66-68 differently). Content is consistent but verse numbers may differ by edition.

9. **D-5, D-6, D-8, D-11:** The existing `varga_matrix.py` includes these in VARGA_ORDER but they are NOT part of the classical Shodasavarga. They may come from Jaimini or other traditions. Not covered in this research.

---

## Code Convention Cross-References

The research files cross-reference the existing codebase in the following ways:

| Code Element | File | Cross-Reference |
|-------------|------|----------------|
| `VARGA_ORDER` | `varga_matrix.py:31-35` | D-1 through D-60 order; note extra D-5, D-6, D-8, D-11 |
| `vargas: Dict[str, Dict[str, str]]` | `parse_jhora.py:142` | D-n → {body → signCode} structure |
| `VimsopakaEntry` | `parse_jhora.py:90-96` | dasa_varga, shodasa_varga, sapta_varga, shad_varga |
| `VaiseshikamsaEntry` | `parse_jhora.py:99-104` | dasa_varga, shodasa_varga (e.g., "4-Gopura") |
| `ashtakavarga: Dict[str, List[int]]` | `parse_jhora.py:142` | planet → [12 bindu counts] |
| `sav: List[int]` | `parse_jhora.py:143` | [12 SAV totals] |
| `_parse_ashtakavarga()` | `parse_jhora.py:516` | Parses BAV from "Ashtakavarga of Rasi Chart" |
| `_parse_sav()` | `parse_jhora.py:554` | Parses SAV or computes from BAV |
| `_parse_vimsopaka()` | `parse_jhora.py:863` | Parses Vimsopaka table with 4 schemes |
| `_parse_vaiseshikamsa()` | `parse_jhora.py:920` | Parses Vaiseshikamsa table |

---

## Bootstrap Prompt for Next Session

If further work is needed on this topic, use the following prompt:

```
TASK: Continue divisional charts and Ashtakavarga research for Kundli AI v3.0.

PREVIOUS WORK: Session A5 (2026-08-02) created 3 knowledge files:
- knowledge/classical/bphs/divisional_charts.md (16 Shodasavarga + Vimsopaka + Vaiseshikamsa)
- knowledge/classical/bphs/ashtakavarga.md (BAV tables, SAV, Sodhya Pinda, score ranges)
- knowledge/classical/saravali/divisional_charts.md (Navamsa effects, varga rules, Ashtakavarga)

PENDING GAPS TO ADDRESS:
1. Verify Mercury BAV table (sum=55 vs traditional 54) against primary BPHS Sanskrit text
2. Verify Venus BAV table (sum=51 vs traditional 52) against primary BPHS Sanskrit text
3. Research Vaiseshikamsa classification names and criteria (e.g., "Gopura") from BPHS
4. Add Saravali Ch.50 (36 Drekkana effects) as separate knowledge file if needed
5. Research Phaladeepika Ch.13 Ashtakavarga application rules
6. Verify Graha Gunakar for Mars (BPHS says 3, variant says 8) and Rashi Gunakar for Virgo (BPHS says 6, variant says 5)

KEY FILES:
- Knowledge output: d:\Project\astrology\kundli-ai\knowledge\classical\
- Existing code (READ ONLY): d:\Project\astrology\kundli-ai\src\varga_matrix.py, parse_jhora.py
- Handoff: d:\Project\.windsurf\handoffs\2026-08-02_A5_divisional_ashtakavarga_sources.md

CONSTRAINTS:
- Do NOT modify any files in src/
- Do NOT fabricate verses — mark confidence as medium/low when uncertain
- Research output goes only in knowledge/
- Use web search to find public domain translations for verification
```

---

## Verification Checklist

- [x] All 16 Shodasavarga charts documented in BPHS divisional_charts.md
- [x] Each chart has: calculation method, significance, interpretation rules, source text
- [x] Vimsopaka Bala documented for all 4 schemes (Shad, Sapta, Dasa, Shodasa)
- [x] Vaiseshikamsa documented (medium confidence)
- [x] BAV benefic place tables for all 7 planets
- [x] SAV calculation and interpretation documented
- [x] Sodhya Pinda calculation with Rashi/Graha Gunakar tables
- [x] Score interpretation ranges (BAV 0-8, SAV 0-56) verified against multiple sources
- [x] Saravali Navamsa effects for all 108 Navamsas summarized
- [x] Saravali Ashtakavarga tables and effects documented
- [x] Cross-references to existing code conventions included
- [x] Gaps and uncertainties explicitly documented
- [x] No source code files modified
- [x] No fabricated verses (confidence marked where uncertain)
