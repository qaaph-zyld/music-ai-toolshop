# Handoff: A6 — Knowledge Base Architecture & Schema Design

**Date:** 2026-08-02
**Agent:** A6 (Architecture & Schema Design)
**Status:** Completed
**Project:** Kundli AI v3.0 — Knowledge Base Infrastructure

---

## Summary of Architecture Decisions

### Three-Layer Architecture

1. **Markdown (source of truth):** Human-readable `.md` files with YAML metadata, stored in `knowledge/classical/`, `knowledge/modern/`, `knowledge/cross_ref/`. Git-diffable, editable by research agents.
2. **JSON (runtime):** Machine-readable exports in `knowledge/dist/`, one file per domain. Loaded lazily by `src/kb_loader.py` with in-memory caching.
3. **SQLite (query):** `knowledge/kundli_kb.db` with `sources`, `entries`, `cross_refs` tables for complex cross-reference queries and full-text search.

### Dual YAML Parsing

The build script supports both:
- **Top-of-file frontmatter** (`---\n...\n---\n` at file start) — one entry per file
- **Embedded YAML blocks** (` ```yaml\n---\n...\n---\n``` ` within body) — multiple entries per file

This preserves the existing file format (embedded blocks) while supporting the simpler one-entry-per-file approach for new content.

### Domain Normalization

Singular domain names (e.g., `dasha`, `dignity`, `yoga`) are automatically normalized to canonical plural forms (`dashas`, `dignities`, `yogas`) via a `DOMAIN_ALIASES` mapping. This handles existing files that use singular forms.

### Graceful Degradation

- Build script handles empty directories without errors (produces empty JSON files with `{"domain": "...", "entries": []}`)
- Query API returns empty dict/list if dist files or SQLite DB don't exist
- Missing domains don't crash the loader — they return empty results

### Custom JSON Encoder

YAML parser produces `date`/`datetime` objects for date-like values. A custom JSON encoder (`_json_default`) converts these to ISO format strings during serialization.

---

## Files Created

| File | Purpose |
|---|---|
| `knowledge/build_kb.py` | Build script: Markdown → JSON + SQLite |
| `src/kb_loader.py` | Query API with 8 query functions + SQLite-backed search |
| `knowledge/sources/source_registry.yaml` | 15 pre-registered classical and modern sources |
| `knowledge/README.md` | Full documentation for the KB system |
| `knowledge/modern/` | Directory for modern commentary files (empty) |
| `knowledge/cross_ref/` | Directory for cross-reference files (has 1 file) |
| `knowledge/dist/` | Generated JSON output directory |
| `knowledge/sources/` | Source registry directory |

**Modified files:**
| File | Change |
|---|---|
| `requirements.txt` | Added `pyyaml>=6.0` |

**No existing source files were modified.**

---

## Schema Specification

### YAML Frontmatter Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `domain` | string | yes | One of: `nakshatras`, `yogas`, `dignities`, `relationships`, `dashas`, `divisional_charts`, `ashtakavarga` (singular forms auto-normalized) |
| `subject` | string | yes | Entity name (e.g., `"Ruchaka"`, `"Sun"`, `"Ashwini"`) |
| `source` | string | yes | Source ID from `source_registry.yaml` |
| `chapter` | string/int | no | Chapter number |
| `verse_range` | string | no | Verse range (e.g., `"1-7"`) |
| `tradition` | string | no | Parashari, Jaimini, etc. |
| `confidence` | string | no | high, medium, low |
| `cross_refs` | list | no | List of `{source, chapter, verse_range}` |
| *(domain-specific)* | any | no | All other fields go into `data` object |

### SQLite Table Schemas

```sql
CREATE TABLE sources (
    id        TEXT PRIMARY KEY,
    name      TEXT,
    full_name TEXT,
    author    TEXT,
    era       TEXT,
    language  TEXT,
    tradition TEXT,
    url       TEXT,
    notes     TEXT
);

CREATE TABLE entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    domain       TEXT NOT NULL,
    subject      TEXT NOT NULL,
    source_id    TEXT,
    chapter      TEXT,
    verse_range  TEXT,
    tradition    TEXT,
    confidence   TEXT,
    content_md   TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE cross_refs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id        INTEGER,
    ref_source      TEXT,
    ref_chapter     TEXT,
    ref_verse_range TEXT,
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_entries_domain_subject ON entries(domain, subject);
CREATE INDEX idx_entries_source ON entries(source_id);
CREATE INDEX idx_cross_refs_entry ON cross_refs(entry_id);
```

### JSON Dist Format

```json
{
  "domain": "yogas",
  "entries": [
    {
      "subject": "Ruchaka",
      "data": { "type": "mahapurusha", "planet": "Mars", ... },
      "sources": [
        { "source_id": "BPHS", "chapter": "75", "verse_range": "1-7", "confidence": "high" }
      ],
      "cross_refs": [
        { "source": "phaladeepika", "chapter": "6", "verse_range": "1-2" }
      ],
      "content_md": "#### Formation Rules\n..."
    }
  ]
}
```

---

## Build Results (from existing content)

| Domain | Entries | Sources |
|---|---|---|
| yogas | 108 (JSON) / 134 (SQLite) | BPHS, phaladeepika, saravali |
| dignities | 9 | BPHS |
| dashas | 14 | BPHS, phaladeepika, jaimini_sutras |
| nakshatras | 0 | (not yet populated) |
| relationships | 0 | (not yet populated) |
| divisional_charts | 0 | (not yet populated) |
| ashtakavarga | 0 | (not yet populated) |
| cross_reference | 1 | (Swiss Ephemeris API ref) |

**Note:** SQLite has more entries than JSON for yogas because SQLite stores one row per source-entry pair, while JSON merges entries with the same subject (combining sources). This is by design.

---

## Query API Functions

| Function | Signature | Description |
|---|---|---|
| `get_nakshatra(name)` | `str -> dict` | Nakshatra data with all sources |
| `get_yoga(name)` | `str -> dict` | Yoga data with all sources |
| `get_dignity(planet)` | `str -> dict` | Planetary dignity data |
| `get_dasha_rules(system)` | `str -> dict` | Dasha system rules |
| `get_divisional_chart(chart_id)` | `str -> dict` | Divisional chart data |
| `get_ashtakavarga_rules()` | `-> dict` | Ashtakavarga rules |
| `search(query)` | `str -> list[dict]` | Full-text search across all entries |
| `get_citations(domain, subject)` | `str, str -> list[dict]` | Source citations for a subject |

All functions available as module-level convenience (uses singleton) or via `KnowledgeBase` class.

---

## Integration Plan for Existing Source Files

The following files contain hardcoded knowledge data that should be refactored to use the KB:

| File | Current Data | KB Domain | Migration Approach |
|---|---|---|---|
| `src/narrative_generator.py` | `NAKSHATRA_DATA` dict (27 nakshatras, ~500 lines) | `nakshatras` | Replace with `get_nakshatra()` calls; keep hardcoded as fallback |
| `src/yoga_validator.py` | `EXALTATION`, `DEBILITATION`, `MOOLATRIKONA` dicts | `dignities`, `yogas` | Replace with `get_dignity()` / `get_yoga()` |
| `src/dasha_engine.py` | `VIM_SEQUENCE`, `VIM_YEARS`, `RULER`, `EXALT`, `DEBIL` | `dashas`, `dignities` | Replace with `get_dasha_rules()` / `get_dignity()` |
| `src/validator.py` | `EXPECTED_VARGAS`, `SAV_SEVEN_PLANET_TOTAL` | `divisional_charts`, `ashtakavarga` | Replace with `get_divisional_chart()` / `get_ashtakavarga_rules()` |

**Migration strategy:** Use KB data when available, fall back to hardcoded values when KB is not built. This ensures backward compatibility during the transition. Example pattern:

```python
from src.kb_loader import get_dignity

def get_exaltation_sign(planet: str) -> str:
    kb_data = get_dignity(planet)
    if kb_data and "exaltation_sign" in kb_data.get("data", {}):
        return kb_data["data"]["exaltation_sign"]
    # Fallback to hardcoded
    return EXALT.get(planet, "")
```

---

## Bootstrap Prompt for Next Session

```text
FRAMEWORK BOOTSTRAP (v12) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.

MY TASK: Continue Kundli AI v3.0 knowledge base development. The infrastructure is complete:
- `knowledge/build_kb.py` — build script (Markdown → JSON + SQLite)
- `src/kb_loader.py` — query API (8 functions + SQLite search)
- `knowledge/sources/source_registry.yaml` — 15 sources registered
- `knowledge/README.md` — full documentation

Current state: 158 entries parsed from existing files (yogas: 108, dignities: 9, dashas: 14, cross_ref: 1).
Empty domains needing content: nakshatras, relationships, divisional_charts, ashtakavarga.

Next steps:
1. Populate empty domains with content from classical sources
2. Refactor existing src/ files to use kb_loader (see integration plan in handoff)
3. Add tests for build_kb.py and kb_loader.py
4. Verify all 27 nakshatras have complete data in the KB

OPEN FILES: d:\Project\astrology\kundli-ai\src\kb_loader.py, d:\Project\astrology\kundli-ai\knowledge\build_kb.py
```
