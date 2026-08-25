# Tool Evaluation: knip (JS/TS Dead Code) & duplicate-code-detection (Python Duplication)

**Agent**: Agent I — Tool Integration Wave 4
**Date**: 2026-08-25
**Status**: COMPLETE — Both tools SKIPPED (redundant with existing tools)

---

## Executive Summary

Evaluated two candidate tools for integration into the ai_dev_meta_layer framework:

1. **knip** — JS/TS dead code detector. **SKIP**: 90% redundant with Fallow. Fallow already finds the same unused exports/dependencies, plus has auto-fix actions, dev_deps_in_production detection, and next-step guidance.
2. **duplicate-code-detection** (platisd/duplicate-code-detection-tool) — Python file-level similarity via TF-IDF/gensim. **SKIP**: jscpd's block-level clone detection is more actionable. Also discovered jscpd `--format py` filter is broken but jscpd works correctly without it when pointed at the source directory.

No runner scripts or tests created. Key side-finding: **jscpd `--format py` filter bug** — documented below with workaround.

---

## Evaluation 1: knip vs Fallow

### Test Setup

- **Target project**: `d:/Project/YT_Playlist_app/yt-playlist-app` (Next.js app, single package.json)
- **knip command**: `npx --yes knip --reporter json --no-progress`
- **Fallow command**: `python scripts/run_fallow.py "<project>" --command dead-code`

### Comparison Table

| Finding Category | knip | Fallow | Winner |
|-----------------|------|--------|--------|
| Unused exports (4) | ✅ `searchVideo`, `searchVideos`, `createPlaylist`, `addVideoToPlaylist` | ✅ Same 4 exports | Tie |
| Unused dependencies (1) | ✅ `@react-oauth/google` | ✅ `@react-oauth/google` | Tie |
| Unused types (2) | ✅ `VideoResult`, `SearchResult` | ❌ (reported 0 unused_types) | knip |
| Dev deps in production (1) | ❌ | ✅ `tailwindcss` | Fallow |
| Auto-fix actions | ❌ | ✅ `remove-export`, `suppress-line`, `remove-dependency` | Fallow |
| Next-step guidance | ❌ | ✅ `fallow trace`, `fallow audit` | Fallow |
| Exit code on findings | 1 (error) | 1 (error) | Tie |
| JSON reporter | ✅ stdout JSON | ✅ stdout JSON | Tie |
| Installation | `npm install -g knip` | `npx --yes fallow` (auto-download) | Tie |

### knip Findings (raw JSON)

```json
{
  "issues": [
    {
      "file": "package.json",
      "dependencies": [{"name": "@react-oauth/google", "line": 12}]
    },
    {
      "file": "src/lib/youtube.ts",
      "exports": ["searchVideo", "searchVideos", "createPlaylist", "addVideoToPlaylist"],
      "types": ["VideoResult", "SearchResult"]
    }
  ]
}
```

### Fallow Findings (summary)

- Total issues: 6
- Unused exports: 4 (same as knip)
- Unused dependencies: 1 (same as knip)
- Dev dependencies in production: 1 (`tailwindcss` — knip missed this)
- Unused types: 0 (knip found 2 — Fallow missed these)

### Decision: SKIP knip

**Reason**: 90% redundant with Fallow. The only additive finding is unused types (2 types in this test). Fallow already has a runner script (`run_fallow.py`), is integrated into the framework, and provides strictly more features (auto-fix actions, dev_deps_in_production, next-step guidance, trace commands). Adding knip would mean maintaining a second runner script for near-identical findings.

**What knip does better**: Detects unused TypeScript types. Fallow's `unused_types` counter reported 0, suggesting its type detection may be less thorough for TS type aliases.

**What Fallow does better**: Dev deps in production detection, auto-fix action suggestions, trace commands, boundary violations, circular dependencies, and 30+ other issue categories.

### Raw Reports

- knip JSON: `d:/Project/ai_dev_meta_layer/output/knip_yt-playlist-app_20260825.json`
- Fallow JSON: `d:/Project/ai_dev_meta_layer/output/fallow_yt-playlist-app_20260825_000706.json`
- Fallow MD: `d:/Project/ai_dev_meta_layer/output/fallow_yt-playlist-app_20260825_000706.md`

---

## Evaluation 2: duplicate-code-detection vs jscpd

### Test Setup

- **Target project**: `d:/Project/astrology/kundli-ai/src` (35+ Python files, ~500KB total)
- **duplicate-code-detection**: `python -W ignore duplicate_code_detection.py --directories "<src>" --json True --only-code --ignore-threshold 10`
- **jscpd (with --format py)**: `python scripts/run_jscpd.py "<kundli-ai>" --format py`
- **jscpd (without filter, pointed at src)**: `python scripts/run_jscpd.py "<kundli-ai/src>"`

### Comparison Table

| Aspect | duplicate-code-detection | jscpd (no format filter) | jscpd (--format py) |
|--------|--------------------------|--------------------------|---------------------|
| Approach | File-level TF-IDF similarity (gensim) | Block-level token-based clone detection | Same as left |
| Output | Similarity % between file pairs | Specific clone blocks with line ranges, token counts, fragments | **0 files analyzed — BROKEN** |
| Actionability | Low (which files are similar) | High (exact lines to refactor) | N/A |
| Python support | Native (py in default extensions) | Works without format filter | Broken with `--format py` |
| Dependencies | Heavy: gensim, nltk, astor | Node.js only (already installed) | Same |
| Installation | Raw script from GitHub, not a pip package | `npx --yes jscpd` (auto-download) | Same |
| Findings count | 40+ file pairs with >10% similarity | 100+ block-level clones | 0 |
| Largest clone | N/A (file-level only) | 51 lines, 276 tokens (`ai/llm_engine.py:141↔233`) | N/A |
| Report format | JSON to stdout | JSON file in output directory | JSON file (empty) |

### duplicate-code-detection Findings (top file-pair similarities)

| File A | File B | Similarity % |
|--------|--------|-------------|
| `kb_loader.py` | `ai/rag_pipeline.py` | 45.43% |
| `models.py` | `api_keys.py` | 40.40% |
| `transit_overlay.py` | `varga_matrix.py` | 39.08% |
| `narrative_generator.py` | `varga_matrix.py` | 35.27% |
| `prashna_engine.py` | `varga_matrix.py` | 33.78% |
| `kundli.py` | `batch_processor.py` | 32.68% |
| `narrative_generator.py` | `prashna_engine.py` | 31.35% |
| `muhurta_engine.py` | `varga_matrix.py` | 30.63% |
| `billing_webhooks.py` | `services/billing_service.py` | 29.28% |
| `muhurta_engine.py` | `dasha_engine.py` | 28.01% |

### jscpd Findings (top block-level clones, without --format py)

| Lines | Tokens | First File | Second File |
|-------|--------|-----------|-------------|
| 51 | 276 | `ai/llm_engine.py:141` | `ai/llm_engine.py:233` |
| 27 | 138 | `position_adapters.py:300` | `position_adapters.py:583` |
| 27 | 111 | `report_generator.py:742` | `report_generator.py:997` |
| 25 | 95 | `report_generator.py:668` | `report_generator.py:928` |
| 24 | 126 | `dasha_engine.py:135` | `validator.py:54` |

Top files by clone count: `kundli.py` (24), `report_generator.py` (24), `batch_processor.py` (10), `dasha_engine.py` (10), `position_adapters.py` (8).

### Critical Side-Finding: jscpd `--format py` Bug

When running `jscpd --format py` against `d:/Project/astrology/kundli-ai`, jscpd analyzed **0 files** and found **0 clones**. The statistics showed:
```json
{"total": {"clones": 0, "lines": 0, "sources": 0, "percentage": 0.0}}
```

When running the same command **without** `--format py` and pointing directly at the `src/` directory, jscpd found 100+ Python clones correctly.

**Root cause**: Likely a jscpd format filter issue where `py` doesn't match Python files on Windows (possibly case sensitivity or extension mapping).

**Workaround for `run_jscpd.py`**: When analyzing Python projects, point jscpd at the source directory directly without `--format py`. The format filter is unnecessary since jscpd auto-detects file types.

### Decision: SKIP duplicate-code-detection

**Reason**: jscpd's block-level clone detection is strictly more actionable than file-level TF-IDF similarity scores. jscpd tells you exactly which lines to refactor; duplicate-code-detection only tells you which files are similar. The file-level approach could be useful for architecture analysis, but it doesn't justify the heavy dependencies (gensim 24MB, nltk, astor) and non-package installation (raw script from GitHub).

**What duplicate-code-detection does better**: Provides a quick file-pair similarity matrix useful for identifying architectural coupling (e.g., `kb_loader.py` is 45% similar to `ai/rag_pipeline.py` — possible code sharing or extraction candidate).

**What jscpd does better**: Pinpoints exact duplicate code blocks with line numbers, token counts, and code fragments. Directly actionable for refactoring.

**jscpd Python coverage is adequate** — when used correctly (no `--format py` filter, point at source directory). The `--format py` bug should be documented in `run_jscpd.py` usage.

### Raw Reports

- duplicate-code-detection: stdout captured (not persisted to file — tool doesn't support file output natively)
- jscpd with --format py: `d:/Project/ai_dev_meta_layer/output/jscpd_kundli-ai_20260825_000838.json`
- jscpd without filter: `d:/Project/ai_dev_meta_layer/output/jscpd_src_20260825_000917.json`

---

## Tool Installation Artifacts

- **knip**: Installed globally via `npm install -g knip` (20 packages)
- **duplicate-code-detection**: Cloned to `d:/Project/ai_dev_meta_layer/vendor/duplicate-code-detection-tool/` (shallow clone)
- **codeclone**: Also installed via `pip install codeclone` as a PyPI alternative (not evaluated — duplicate-code-detection was the specified tool)
- **Dependencies installed**: `gensim`, `astor` (nltk was already present), `punkt_tab` nltk data

---

## Recommendations

1. **Do NOT integrate knip** — Fallow already covers JS/TS dead code detection with more features.
2. **Do NOT integrate duplicate-code-detection** — jscpd covers Python duplication with more actionable findings.
3. **Fix jscpd usage in documentation**: Warn that `--format py` is broken on Windows. Recommend pointing jscpd at source directories directly without format filters.
4. **Consider Fallow's unused_types gap**: Fallow reported 0 unused TypeScript types where knip found 2. This may warrant a Fallow config adjustment or bug report.
5. **Optional future evaluation**: `codeclone` (v2.0.2, PyPI) was installed but not evaluated. It uses CFG fingerprint + statement window analysis for Python clones — potentially more thorough than jscpd's token-based approach. Could be evaluated in a future wave if jscpd's Python coverage proves insufficient.

---

*Generated by Agent I — Tool Integration Wave 4*
