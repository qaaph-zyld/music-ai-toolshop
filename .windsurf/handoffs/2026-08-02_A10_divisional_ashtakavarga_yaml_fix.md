# A10: Divisional Charts & Ashtakavarga YAML Reformatting — Handoff

**Date:** 2026-08-02
**Agent:** A10
**Status:** Completed

## Summary

Reformatted 3 knowledge base Markdown files to add YAML frontmatter blocks compatible with the `build_kb.py` parser regex (` ```yaml\n---\n...\n---\n``` `). The parser requires triple-backtick code fence wrappers around YAML `---` delimiters; bare `---` blocks were not detected.

## Changes by File

### 1. `bphs/divisional_charts.md` — 18 blocks wrapped

All 18 existing bare `---\n...\n---` YAML blocks were wrapped in ` ```yaml ... ``` ` code fences. No content was changed — only the fence wrapper was added.

| # | Subject (chart) | Lines (approx) |
|---|-----------------|-----------------|
| 1 | D-1 (Rashi) | 46-62 |
| 2 | D-2 (Hora) | 85-101 |
| 3 | D-3 (Drekkana) | 129-148 |
| 4 | D-4 (Chaturthamsa) | 175-187 |
| 5 | D-7 (Saptamsa) | 212-228 |
| 6 | D-9 (Navamsa) | 253-275 |
| 7 | D-10 (Dashamsa) | 312-324 |
| 8 | D-12 (Dvadashamsa) | 351-367 |
| 9 | D-16 (Shodashamsa) | 391-403 |
| 10 | D-20 (Vimshamsa) | 431-443 |
| 11 | D-24 (Chaturvimshamsa) | 474-486 |
| 12 | D-27 (Saptavimshamsa) | 511-523 |
| 13 | D-30 (Trimshamsa) | 550-566 |
| 14 | D-40 (Khavedamsa) | 599-611 |
| 15 | D-45 (Akshavedamsa) | 636-648 |
| 16 | D-60 (Shashtyamsa) | 677-689 |
| 17 | Vimsopaka Bala | 730-744 |
| 18 | Vaiseshikamsa | 859-869 |

**New blocks:** 0 | **Wrapped blocks:** 18 | **Total:** 18

### 2. `bphs/ashtakavarga.md` — 7 new + 4 wrapped = 11 blocks

#### New YAML blocks (7):
Added ` ```yaml ` frontmatter blocks before each planet's BAV section heading.

| # | Subject | Chapter | Confidence |
|---|---------|---------|------------|
| 1 | Sun BAV | 66 | high |
| 2 | Moon BAV | 66 | high |
| 3 | Mars BAV | 66 | high |
| 4 | Mercury BAV | 66 | medium |
| 5 | Jupiter BAV | 66 | high |
| 6 | Venus BAV | 66 | medium |
| 7 | Saturn BAV | 66 | high |

#### Wrapped existing blocks (4):
Wrapped bare `---` blocks in ` ```yaml ` fences and added `subject` field.

| # | Subject | Type | Chapter |
|---|---------|------|---------|
| 8 | SAV | SAV | 66 |
| 9 | Sodhya Pinda | sodhya_pinda | 67-69 |
| 10 | Transit Effects | transit_effects | 70 |
| 11 | BAV Effects | bav_effects | 54 (Saravali) |

**New blocks:** 7 | **Wrapped blocks:** 4 | **Total:** 11

### 3. `saravali/divisional_charts.md` — 4 blocks wrapped

Wrapped 4 existing bare `---` blocks in ` ```yaml ` fences and added `subject` field where missing.

| # | Subject | Domain | Chapter |
|---|---------|--------|---------|
| 1 | General Varga Rules | divisional_chart | 3 |
| 2 | D-9 (Navamsa) | divisional_chart | 51 |
| 3 | Ashtakavarga Tables | ashtakavarga | 53 |
| 4 | Ashtakavarga Effects | ashtakavarga | 54 |

**New blocks:** 0 | **Wrapped blocks:** 4 | **Total:** 4

## Grand Total

| File | New | Wrapped | Total |
|------|-----|---------|-------|
| bphs/divisional_charts.md | 0 | 18 | 18 |
| bphs/ashtakavarga.md | 7 | 4 | 11 |
| saravali/divisional_charts.md | 0 | 4 | 4 |
| **Total** | **7** | **26** | **33** |

## Entries with Missing Chapter/Verse Info

- **Sun BAV, Moon BAV, Mars BAV, Mercury BAV, Jupiter BAV, Venus BAV, Saturn BAV** (bphs/ashtakavarga.md): Chapter 66 is specified, but exact verse ranges within the chapter are not provided in the source text. The BPHS chapter numbering varies between editions.
- **Vimsopaka Bala** (bphs/divisional_charts.md): `domain: vimsopaka`, `subject: Vimsopaka Bala` added. This domain is not in the parser's `DOMAINS` list but will be handled by the `by_domain.setdefault()` fallback.
- **Vaiseshikamsa** (bphs/divisional_charts.md): `domain: vaiseshikamsa`, `subject: Vaiseshikamsa` added. Same fallback applies. Confidence is `medium` due to unverified verse numbers.

## Notes

- Existing `domain: divisional_chart` (singular) values were kept as-is — the parser's `DOMAIN_ALIASES` maps them to `divisional_charts`
- No existing prose/content was removed or changed in any file
- The `chart` field in divisional_charts entries serves as the parser's `subject` via fallback logic (`build_kb.py:212`)
- Mercury BAV and Venus BAV confidence set to `medium` due to known arithmetic discrepancies documented in the source text
