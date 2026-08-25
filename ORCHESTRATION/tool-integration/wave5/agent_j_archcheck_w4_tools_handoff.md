# Agent J — Wire bandit/pip-audit/Ruff/radon into architecture-analysis SKILL.md

**Date:** 2026-08-25
**Agent:** Agent J (Architecture-Check Tool Integration)
**Scope:** Integrate four Wave 4–evaluated deterministic tools into the architecture-analysis SKILL.md
**Target file:** `d:/Project/.windsurf/skills/architecture-analysis/SKILL.md`
**Mode:** Edit SKILL.md only + handoff

---

## Executive Summary

Three new deterministic tool subsections were added to the architecture-analysis SKILL.md, wiring Ruff (Phase 1), bandit + pip-audit (Phase 2), and radon (Phase 3) into the workflow. All four runner scripts were verified to exist. Health check ran successfully — pre-existing issues only, none caused by these changes.

---

## Changes Made

### Edit 1 — Phase 1: "### Deterministic Fast Lint" (lines 69–70)

**Before:** The "### Deterministic Dead Code" subsection (Vulture) was immediately followed by "- **Naming conventions**".

**After:** New "### Deterministic Fast Lint" subsection inserted between them.

**Content:** Ruff as a fast pre-pass before Vulture. Detects F401 (unused imports) and F811 (redefined-while-unused) in milliseconds. Supports `--fix` flag for auto-fix. Use Ruff for quick scans; Vulture for confidence-scored deep analysis. Cite findings with rule code (F401, F811).

**Command:** `python "d:/Project/ai_dev_meta_layer/scripts/run_ruff.py" <target>`

### Edit 2 — Phase 2: "### Deterministic Security Scan" (lines 94–99)

**Before:** The "- **Dependencies**" check item was immediately followed by "### Output".

**After:** New "### Deterministic Security Scan" subsection inserted between them.

**Content:**
- pip-audit: dependency CVE checking against PyPI vulnerability database. Any vulnerability → architecture-check HIGH.
- bandit: code-level security vulnerabilities (B701 XSS, B105 hardcoded passwords, B110 try/except/pass, B101 assert, B405 XML attacks). Severity mapping: bandit HIGH → CRITICAL, MEDIUM → HIGH, LOW → MEDIUM (informational).
- Run order: pip-audit first (dependency vulnerabilities higher risk), then bandit.

**Commands:**
- `python "d:/Project/ai_dev_meta_layer/scripts/run_pip_audit.py" <target>`
- `python "d:/Project/ai_dev_meta_layer/scripts/run_bandit.py" <target>`

### Edit 3 — Phase 3: "### Deterministic Complexity Analysis" (lines 115–116)

**Before:** The "- **Rendering**" check item was immediately followed by "### Output".

**After:** New "### Deterministic Complexity Analysis" subsection inserted between them.

**Content:** radon cyclomatic complexity scoring. A (simple) to F (unmaintainable) ranking. C+ rank (cc>10) → MEDIUM finding (refactoring candidate). F rank (cc>50) → HIGH finding (must refactor). Complexity hotspots identify performance and maintainability risks.

**Command:** `python "d:/Project/ai_dev_meta_layer/scripts/run_radon.py" <target>`

---

## Runner Scripts Verified

| Script | Path | Status |
|--------|------|--------|
| `run_ruff.py` | `d:/Project/ai_dev_meta_layer/scripts/run_ruff.py` | Exists |
| `run_bandit.py` | `d:/Project/ai_dev_meta_layer/scripts/run_bandit.py` | Exists |
| `run_pip_audit.py` | `d:/Project/ai_dev_meta_layer/scripts/run_pip_audit.py` | Exists |
| `run_radon.py` | `d:/Project/ai_dev_meta_layer/scripts/run_radon.py` | Exists |

---

## Tools NOT Referenced (per constraints)

- **pylint** — Evaluated and skipped (W0611 fully overlaps with Ruff F401: 109 vs 110 findings; 67 W0612/W0613 findings don't justify a separate heavy dependency).
- **knip** — Not evaluated for this workflow.
- **duplicate-code-detection** — Not used; jscpd already integrated in Phase 4.

---

## Health Check Result

**Command:** `python "d:/Project/ai_dev_meta_layer/scripts/daily_health_check.py"`
**Exit code:** 1 (overall status: broken)
**Assessment:** All issues are pre-existing — missing AGENTS.md files in 15 projects, unresolved INDEX.md routes in workspace_network, token budget overage in harness/INDEX.md. **No issues caused by the SKILL.md edits.**
**Dashboard:** `d:/Project/ai_dev_meta_layer/audit_history/health_dashboard_2026-08-25_012117.md`

---

## Handoff

**Report file:** `ORCHESTRATION/tool-integration/wave5/agent_j_archcheck_w4_tools_handoff.md`
**Summary:** Wired Ruff (Phase 1 fast lint), bandit + pip-audit (Phase 2 security scan), and radon (Phase 3 complexity analysis) into the architecture-analysis SKILL.md with three new deterministic subsections. All four runner scripts verified present. Health check confirmed no new issues from the changes.
