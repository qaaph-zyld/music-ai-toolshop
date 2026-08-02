# A11: Relationships Domain Fix + Build Script Patch

**Date:** 2026-08-02
**Agent:** A11
**Status:** Completed

## Summary

Fixed non-standard domain names in two knowledge Markdown files and added 11 defensive aliases to `build_kb.py`'s `DOMAIN_ALIASES` dict so future files with these domain variants are normalized to `relationships`.

## Changes Made

### 1. `knowledge/classical/jataka_parijata/relationships.md` — 4 domain fields changed

| Line | Old value | New value |
|------|-----------|-----------|
| 14 | `domain: temporary_friendship` | `domain: relationships` |
| 62 | `domain: compound_friendship` | `domain: relationships` |
| 130 | `domain: graha_drishti` | `domain: relationships` |
| 223 | `domain: rashi_drishti` | `domain: relationships` |

### 2. `knowledge/classical/bphs/aspects.md` — 4 domain fields changed

| Line | Old value | New value |
|------|-----------|-----------|
| 14 | `domain: graha_drishti` | `domain: relationships` |
| 68 | `domain: graha_drishti_fractional` | `domain: relationships` |
| 129 | `domain: graha_drishti_calculation` | `domain: relationships` |
| 163 | `domain: graha_drishti_nodes` | `domain: relationships` |

### 3. `knowledge/build_kb.py` — 11 aliases added to `DOMAIN_ALIASES`

```python
"temporary_friendship": "relationships",
"compound_friendship": "relationships",
"naisargika_maitri": "relationships",
"tatkalika_maitri": "relationships",
"panchadha_maitri": "relationships",
"graha_drishti": "relationships",
"rashi_drishti": "relationships",
"aspects": "relationships",
"graha_drishti_fractional": "relationships",
"graha_drishti_calculation": "relationships",
"graha_drishti_nodes": "relationships",
```

**Total domain field values changed:** 8 (4 in relationships.md + 4 in aspects.md)
**Total aliases added:** 11 (8 user-specified + 3 additional for aspect variants in aspects.md)

## Verification

Ran `python knowledge/build_kb.py --verbose` — exit code 0, build succeeded.

## Known Issue (out of scope)

Both `relationships.md` and `aspects.md` still produce 0 parsed entries because their YAML frontmatter blocks lack a `subject` field, which `_normalize_entry()` requires (build_kb.py line 217: `if not domain or not subject: return None`). The domain fix is correct and necessary, but a follow-up task is needed to add `subject` fields to these YAML blocks so the parser can produce entries.
