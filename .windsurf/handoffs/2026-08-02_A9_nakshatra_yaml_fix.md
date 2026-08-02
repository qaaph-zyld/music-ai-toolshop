# Handoff: Nakshatra YAML Frontmatter Fix (A9)

**Date:** 2026-08-02
**Task:** Insert YAML frontmatter blocks into 3 nakshatra knowledge files for `build_kb.py` parser compatibility
**Status:** Completed

## Summary

The Kundli AI v3.0 knowledge base build script (`knowledge/build_kb.py`) was producing 0 entries for the nakshatras domain because the 3 nakshatra Markdown files used plain `## NakshatraName` headings with no YAML metadata blocks. This fix inserts properly formatted ```` ```yaml ```` blocks (with `---` delimiters inside triple-backtick code fences) before each of the 27 nakshatra headings in each file, matching the format already used in `bphs/yogas.md`.

## Changes Made

### Files Modified

1. **`knowledge/classical/bphs/nakshatras.md`** — 27 YAML blocks inserted
   - source: BPHS, source_full: "Brihat Parashara Hora Shastra"
   - chapter: 6, verse_range: "24-26", confidence: high
   - cross_refs: Brihat Jataka ch.16 (sloka varies 1-14), Phaladeepika ch.26 "35-40"

2. **`knowledge/classical/brihat_jataka/nakshatras.md`** — 27 YAML blocks inserted
   - source: Brihat Jataka, source_full: "Brihat Jataka"
   - chapter: 16, verse_range: per-nakshatra (sloka 1-14), confidence: high
   - cross_refs: BPHS ch.6 "24-26", Phaladeepika ch.26 "35-40"
   - Gandanta nakshatras (Ashlesha, Magha, Jyeshtha, Mula, Revati) also cross-ref BPHS ch.9 "1-4"

3. **`knowledge/classical/phaladeepika/nakshatras.md`** — 27 YAML blocks inserted
   - source: Phaladeepika, source_full: "Phaladeepika"
   - chapter: 26, verse_range: "35-40", confidence: medium
   - cross_refs: BPHS ch.6 "24-26", Brihat Jataka ch.16 (sloka varies 1-14)
   - Gandanta nakshatras also cross-ref BPHS ch.9 "1-4"

### Files Created

- **`knowledge/insert_nakshatra_yaml.py`** — Utility script that performed the insertions (one-time use)

## YAML Blocks Added Per File

| File | Blocks Added |
|------|-------------|
| bphs/nakshatras.md | 27 |
| brihat_jataka/nakshatras.md | 27 |
| phaladeepika/nakshatras.md | 27 |
| **Total** | **81** |

## Verification

```
python knowledge/build_kb.py --domain nakshatras --verbose
```

Result:
- `bphs/nakshatras.md` → 27 entries parsed
- `brihat_jataka/nakshatras.md` → 27 entries parsed
- `phaladeepika/nakshatras.md` → 27 entries parsed
- **Total: 81 entries found for domain 'nakshatras'**
- JSON output: 27 merged entries (merged by subject across sources)
- SQLite: 81 entries inserted

## Entries with Missing Chapter/Verse Info

**None.** All 81 entries have complete chapter and verse_range values:
- BPHS: all ch.6, "24-26"
- Brihat Jataka: all ch.16, sloka 1-14 (varies per nakshatra pair)
- Phaladeepika: all ch.26, "35-40"

## Gandanta Nakshatra Cross-References

The following 6 nakshatras are Gandanta junction points and received additional BPHS ch.9 "1-4" cross-references in the Brihat Jataka and Phaladeepika files (BPHS file uses ch.6 as primary, ch.9 info is in the content body):

- Ashwini (index 0)
- Ashlesha (index 8)
- Magha (index 9)
- Jyeshtha (index 17)
- Mula (index 18)
- Revati (index 26)

## Brihat Jataka Sloka Mapping

Each nakshatra pair shares a sloka in Brihat Jataka ch.16:

| Sloka | Nakshatras |
|-------|-----------|
| 1 | Ashwini, Bharani |
| 2 | Krittika, Rohini |
| 3 | Mrigashira, Ardra |
| 4 | Punarvasu |
| 5 | Pushya, Ashlesha |
| 6 | Magha, Purva Phalguni |
| 7 | Uttara Phalguni, Hasta |
| 8 | Chitra, Swati |
| 9 | Vishakha, Anuradha |
| 10 | Jyeshtha, Mula |
| 11 | Purva Ashadha, Uttara Ashadha |
| 12 | Shravana, Dhanishta |
| 13 | Shatabhisha, Purva Bhadrapada |
| 14 | Uttara Bhadrapada, Revati |
