# Agent H — Complexity & Linting Tool Evaluation (radon, Ruff, pylint)

**Wave**: 4 (Tool Integration)
**Date**: 2026-08-24
**Status**: COMPLETE

## Executive Summary

Evaluated three Python static-analysis tools against `d:\Project\astrology\kundli-ai\src` (30+ Python files). **Ruff** and **radon** approved for runner scripts. **pylint** skipped — W0611 fully overlaps with Ruff F401, and W0612/W0613 don't justify a separate heavy dependency.

## Tool Evaluation Results

### 1. Ruff (F401, F811)

- **Version**: 0.14.14 (already installed)
- **Prevalence**: Dev dependency in `d:\Project\memory-compiler\pyproject.toml` (`ruff>=0.6.0`)
- **Findings**: 110 F401 (unused imports), 0 F811 (redefined-while-unused)
- **Files affected**: 27
- **Execution time**: <2 seconds
- **Unique value vs Vulture**:
  - F401 provides precise column-level location and auto-fix suggestions (safe applicability)
  - F811 detects redefined-while-unused names — Vulture cannot detect this
  - Ruff is significantly faster than Vulture's library API scavenge
  - Ruff is extensible: `--select` can add more rule categories (E, W, I, etc.) without new dependencies
- **Decision**: **APPROVE** — Create runner script

### 2. radon (cyclomatic complexity)

- **Version**: 6.0.1
- **Findings**: 714 blocks analyzed
  - Rank A: 500, B: 121, C: 69, D: 14, E: 8, F: 2
  - 93 blocks at rank C or higher (13% of codebase)
- **Top hotspots**:
  | Rank | CC | Function | File |
  |------|----|----------|------|
  | F | 57 | `JhoraParser._parse_single_grid` | `parse_jhora.py` |
  | F | 54 | `KundliValidator.validate_dasha_forecast` | `validator.py` |
  | E | 39 | `NarrativeGenerator.s11_life_areas` | `narrative_generator.py` |
  | E | 36 | `generate_docx_from_narrative` | `report_generator.py` |
  | E | 35 | `NarrativeGenerator.s2_panchanga` | `narrative_generator.py` |
  | E | 35 | `PrashnaEngine._evaluate_answer` | `prashna_engine.py` |
  | E | 34 | `generate_pdf_from_narrative` | `report_generator.py` |
  | E | 31 | `cmd_process` | `kundli.py` |
  | E | 31 | `NarrativeGenerator.s10_dasha` | `narrative_generator.py` |
  | E | 31 | `generate_transit_report` | `transit_overlay.py` |
- **Unique value vs Vulture**:
  - Quantitative complexity scoring surfaces refactoring targets that file size alone doesn't reveal
  - F-ranked functions (cc>50) are immediate refactoring priorities
  - Rank distribution provides a codebase health metric for Phase 3 (Performance)
  - Complements manual review with objective, reproducible scores
- **Decision**: **APPROVE** — Create runner script

### 3. pylint (W0611, W0612, W0613)

- **Version**: 4.0.7
- **Findings**: 176 total
  - W0611 (unused import): 109
  - W0612 (unused variable): 54
  - W0613 (unused argument): 13
- **Files affected**: 35
- **Execution time**: ~15 seconds (significantly slower than Ruff)
- **Overlap analysis**:
  - W0611 (109) ≈ Ruff F401 (110) — near-perfect overlap, 1 difference likely due to import style detection
  - W0612 (54) — Vulture does not detect local unused variables in loops/comprehensions
  - W0613 (13) — Vulture does not detect unused function arguments
- **Unique value**: Only W0612 + W0613 = 67 findings not covered by Ruff F401
- **Decision**: **SKIP** — W0611 fully overlaps with Ruff. The 67 unique W0612/W0613 findings don't justify adding pylint as a separate heavy dependency (539KB wheel + astroid 276KB). Ruff can be extended with `ARG001` (unused-function-argument) and similar rules to cover W0613 without pylint.

## Overlap Analysis Table

| Finding Type | Vulture | Ruff F401/F811 | pylint W0611/W0612/W0613 | radon cc |
|---|---|---|---|---|
| Unused imports | ✅ (library API) | ✅ (110, faster, auto-fix) | ✅ (109, near-identical) | ❌ |
| Redefined-while-unused | ❌ | ✅ (F811, 0 found) | ❌ | ❌ |
| Unused variables | ❌ (block-level only) | ❌ | ✅ (54) | ❌ |
| Unused arguments | ❌ | ❌ | ✅ (13) | ❌ |
| Cyclomatic complexity | ❌ | ❌ | ❌ | ✅ (714 blocks, ranked) |
| Auto-fix suggestions | ❌ | ✅ (safe fixes) | ❌ | ❌ |
| Execution speed | ~5s (library API) | <2s (CLI) | ~15s (CLI) | <3s (CLI) |

## Deliverables

### Runner Scripts Created

1. **`d:\Project\ai_dev_meta_layer\scripts\run_ruff.py`**
   - Runs `ruff check <project> --select F401,F811 --output-format json`
   - CLI: `python scripts/run_ruff.py <project_dir> [--select RULES] [--exclude PATTERNS] [--dry-run]`
   - Exit codes: 0 (no findings), 1 (error), 3 (findings found)
   - Imports: `framework.tool_utils.{is_python_available, is_python_project, sanitize_project_name}`, `framework.paths.OUTPUT_DIR`
   - Output: `output/ruff_<project>_<timestamp>.json` + `.md`

2. **`d:\Project\ai_dev_meta_layer\scripts\run_radon.py`**
   - Runs `radon cc <project> -j` (cyclomatic complexity in JSON)
   - CLI: `python scripts/run_radon.py <project_dir> [--min-rank C] [--exclude PATTERNS] [--dry-run]`
   - Exit codes: 0 (no hotspots), 1 (error), 3 (hotspots found)
   - Imports: `framework.tool_utils.{is_python_available, is_python_project, parse_json_blob, sanitize_project_name}`, `framework.paths.OUTPUT_DIR`
   - Output: `output/radon_<project>_<timestamp>.json` + `.md`
   - Markdown includes rank distribution and top 15 hotspots

### Test Files Created

1. **`d:\Project\ai_dev_meta_layer\tests\test_run_ruff.py`** — 16 tests
   - `TestDryRun`: 2 tests (no subprocess, markdown written)
   - `TestRunRuff`: 8 tests (findings, JSON file, markdown, empty, parse error, timeout, select, exclude)
   - `TestMain`: 6 tests (exit codes 0/1/3, dry-run, nonexistent, not Python, select flag)

2. **`d:\Project\ai_dev_meta_layer\tests\test_run_radon.py`** — 17 tests
   - `TestDryRun`: 2 tests (no subprocess, markdown written)
   - `TestRunRadon`: 9 tests (data, JSON file, markdown, hotspot filtering C/F, empty, parse error, timeout, exclude)
   - `TestMain`: 6 tests (exit codes 0/1/3, dry-run, nonexistent, not Python, min-rank flag)

### Test Results

```
33 passed in 0.33s
```

### pylint Skip Documentation

**Reason**: pylint W0611 (unused-import) has near-perfect overlap with Ruff F401 (109 vs 110 findings). The 67 unique findings (W0612 unused-variable + W0613 unused-argument) don't justify adding pylint as a 815KB+ dependency when:
1. Ruff can be extended with `ARG001`/`ARG002` rules to cover unused arguments
2. Vulture already covers block-level dead code
3. pylint's execution time (~15s) is 7.5x slower than Ruff (<2s)

**Future consideration**: If naming convention checks (C0103, C0114, etc.) are needed for Phase 1 (Architecture), pylint could be re-evaluated with a broader rule set. For now, Ruff's `N` rules (pep8-naming) can cover naming conventions without pylint.

## Architecture-Check Integration Points

| Phase | Tool | Integration |
|-------|------|-------------|
| Phase 1 (Architecture) | Ruff F401/F811 | Fast pre-pass for unused imports before manual review |
| Phase 3 (Performance) | radon cc | Complexity scoring to identify refactoring hotspots |
| Phase 4 (Optimization) | Ruff F401 | Redundant import detection as part of cleanup recommendations |

## Raw Test Output Files

- `d:\Project\ai_dev_meta_layer\output\radon_test_results.json` — radon cc JSON output
- `d:\Project\ai_dev_meta_layer\output\ruff_test_results.json` — Ruff F401/F811 JSON output
- `d:\Project\ai_dev_meta_layer\output\pylint_test_results.json` — pylint W0611/W0612/W0613 JSON output

## Dependencies Added

- `radon>=6.0.1` (installed via pip)
- `ruff>=0.14.14` (already installed)
- `pylint>=4.0.7` (installed for evaluation, not integrated into framework)

**Note**: `radon` and `ruff` should be added to `scripts/requirements-tools.txt`.

---

*Generated by Agent H — Wave 4 Tool Integration*
