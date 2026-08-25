---
name: architecture-analysis
description: Deep, phased architecture and code-health analysis of a project. Use when user requests /architecture_check or a comprehensive structural audit.
version: 0.1.0
license: Proprietary
author: a265m001-bot
compatibility: windsurf
allowedTools: []
effort: high
trigger: manual
---

# Architecture Analysis Skill

> Perform a meticulous, no-guesswork structural audit of a codebase.
> Every finding must cite a specific file path + line range or be flagged `LOW` confidence.

---

## Trigger

- User invokes `/architecture_check @ProjectName`
- User asks for "comprehensive code audit", "architecture review", or "find all bugs/security/performance issues"
- Preparing for a major refactor or release

---

## Prerequisites

1. **Detect project**: Use `scripts/knowledge_router.py "[task text]" --files "[open files]"` to identify the active project.
2. **Load project context**: Read the project's `AGENTS.md` and semantic KB (`memory/semantic/projects/<name>.md`, `<name>_LESSONS.md`).
3. **Load framework context**: Read `memory/system/core_memories.md` and `memory/system/soul.md` for universal guardrails.

---

## Phase 0 — Deep Structural Pass

Goal: Build a mental model of the entire project before drilling into specific concerns.

### Steps
1. **Directory topology**: List top-level folders and understand module boundaries.
2. **Entry points**: Identify main entry files (`index.js`, `main.py`, `App.tsx`, server start, CLI scripts).
3. **Import graph**: Trace key imports to detect circular dependencies and coupling.

### Deterministic Import Graph
For Python projects, run `python "d:/Project/ai_dev_meta_layer/scripts/run_import_analyzer.py" <target>` to generate a deterministic import graph with circular dependency detection. Use this as the basis for the manual import tracing step — the tool finds transitive cycles that manual tracing misses.

4. **Configuration scan**: Review `.env` templates, config files, and hardcoded constants.
5. **Data flow**: Map how data moves from DB → API → UI (or equivalent pipeline).
6. **External dependencies**: Flag outdated, unused, or duplicated dependencies.

### Output
- `report_0_structure.md`: Summary of topology, entry points, and any structural red flags (e.g., "`backend/` and `frontend/` share a `package.json` — potential dependency leakage").

---

## Phase 1 — Architecture

### Checks
- **Layering**: Business logic isolated from UI/transport layers. No DB queries in controllers/components.
- **Coupling**: Modules depend on abstractions, not concrete implementations.
- **Cohesion**: Files/classes have single, well-defined responsibilities.
- **Interface contracts**: Public APIs/modules have stable, documented interfaces.
- **Dead code**: Functions, imports, or files that are never referenced.

### Deterministic Dead Code
For Python projects, run `python "d:/Project/ai_dev_meta_layer/scripts/run_vulture.py" <target>` for confidence-scored dead code findings. Cite findings with the tool's confidence level. For JS/TS projects, use `python "d:/Project/ai_dev_meta_layer/scripts/run_fallow.py" <target> --command dead-code`.

### Deterministic Fast Lint
For Python projects, run `python "d:/Project/ai_dev_meta_layer/scripts/run_ruff.py" <target>` as a fast pre-pass before Vulture. Ruff detects F401 (unused imports) and F811 (redefined-while-unused) in milliseconds. Ruff is faster than Vulture and supports auto-fix (`--fix` flag). Use Ruff for quick scans; use Vulture for confidence-scored deep analysis. Cite Ruff findings with the rule code (F401, F811).

- **Naming conventions**: Consistent with project `AGENTS.md` and language idioms.

### Confidence Scoring
- `HIGH`: Layer violation is visible in a specific import statement or function body.
- `MEDIUM`: Pattern suggests tight coupling but may be justified.
- `LOW`: Smell detected but needs human validation.

### Output
- `report_1_architecture.md`: Each finding with file citation, evidence, impact, and fix recommendation.

---

## Phase 2 — Security

### Checks
- **Secrets**: No hardcoded API keys, passwords, tokens, or connection strings in source.
- **Injection risks**: SQL uses parameterized queries; no string concatenation in query builders.
- **Unsafe execution**: No `eval()`, `new Function()`, `exec()`, or equivalent.
- **Input validation**: All external inputs (HTTP params, file uploads, env vars) validated before use.
- **Auth/authorization**: Authentication enforced on sensitive endpoints; role checks present.
- **Dependencies**: Known vulnerabilities in `package.json`/`requirements.txt` (flag for user to run `npm audit` / `pip-audit`).

### Deterministic Security Scan
For Python projects, run `python "d:/Project/ai_dev_meta_layer/scripts/run_pip_audit.py" <target>` for dependency CVE checking. pip-audit checks all packages in `requirements.txt` against the PyPI vulnerability database. Any vulnerability → architecture-check HIGH.

Then run `python "d:/Project/ai_dev_meta_layer/scripts/run_bandit.py" <target>` for code-level security vulnerabilities. Bandit detects XSS (B701), hardcoded passwords (B105), try/except/pass (B110), assert statements (B101), XML attacks (B405). Severity mapping: bandit HIGH → architecture-check CRITICAL, bandit MEDIUM → HIGH, bandit LOW → MEDIUM (informational).

Run order: pip-audit first (dependency vulnerabilities are higher risk), then bandit (code-level issues). These tools find issues the LLM-only review cannot: CVE database lookups, pattern-based vulnerability detection.

### Output
- `report_2_security.md`: Confidence-scored findings with evidence and remediation steps.

---

## Phase 3 — Performance

### Checks
- **N+1 queries**: Loops that trigger repeated DB/network calls.
- **Unbounded operations**: Queries without `LIMIT`, full table scans, loading entire datasets into memory.
- **Inefficient algorithms**: `O(n^2)` nested loops where indexing or hash maps would suffice.
- **Memory leaks**: Event listeners not removed, closures holding large objects, uncapped caches.
- **Rendering**: React components with unnecessary re-renders, missing `useMemo`/`useCallback`.

### Deterministic Complexity Analysis
For Python projects, run `python "d:/Project/ai_dev_meta_layer/scripts/run_radon.py" <target>` for cyclomatic complexity scoring. radon ranks functions from A (simple) to F (unmaintainable). Flag C+ rank (cc>10) as MEDIUM finding — candidate for refactoring. Flag F rank (cc>50) as HIGH finding — must refactor. Complexity hotspots directly identify performance and maintainability risks.

### Output
- `report_3_performance.md`: Confidence-scored findings with evidence and optimization suggestions.

---

## Phase 4 — Optimization

### Checks
- **Redundancy**: Duplicate logic that could be extracted into a shared utility.

### Deterministic Duplication
Run `python "d:/Project/ai_dev_meta_layer/scripts/run_jscpd.py" <target>` for all languages. The `--summary` flag ranks top files by duplication share — directly identifies consolidation candidates.

- **Over-engineering**: Abstraction layers that add complexity without value.
- **Missed simplification**: Complex conditionals that could be lookup tables or pattern matching.
- **Modern language features**: Opportunities to use newer, safer APIs (e.g., `??` instead of `||` for nullish, optional chaining).
- **Documentation gaps**: Public functions missing JSDoc/docstrings; complex algorithms without comments.

### Output
- `report_4_optimization.md`: Confidence-scored findings with evidence and refactoring suggestions.

---

## Report Aggregation, Confidence Scores, Anti-Patterns & Session References

→ **Detail**: [`REPORTING.md`](REPORTING.md)

---

## Persistence, Presentation, Orchestration, Verification & Notes

→ **Detail**: [`PERSISTENCE.md`](PERSISTENCE.md)
