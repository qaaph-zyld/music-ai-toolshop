# Agent K — Clean-Up Skill: Wave 4 Tool Integration

**Date:** 2026-08-25
**Agent:** Agent K (Clean-Up Tool Wiring)
**Scope:** Wire bandit, pip-audit, Ruff, and radon into clean-up SKILL.md and ORCHESTRATION.md
**Mode:** Read-only evaluation + targeted edits to 2 skill files

---

## Executive Summary

Integrated 4 Wave 4 approved tools (bandit, pip-audit, Ruff, radon) into the clean-up workflow's deterministic pre-pass, regression checks, metrics reporting, and `--light` mode. All edits confined to `SKILL.md` and `ORCHESTRATION.md` in the clean-up skill directory. Health check confirms no new issues introduced.

---

## Source Evaluations

### bandit + pip-audit (Agent G, Wave 4)
- **Handoff:** `ORCHESTRATION/tool-integration/wave4/agent_g_security_tools_handoff.md`
- **bandit:** 21 findings (1 HIGH: Jinja2 XSS B701), 3-21s runtime, JSON output. Runner: `scripts/run_bandit.py`
- **pip-audit:** 0 vulnerabilities across 40+ dependencies, ~15s runtime, JSON output. Runner: `scripts/run_pip_audit.py`
- **Decision:** Both APPROVED — bandit catches code-level security issues LLM misses; pip-audit checks CVE database impossible for LLMs.

### Ruff + radon (Agent H, Wave 4)
- **Handoff:** `ORCHESTRATION/tool-integration/wave4/agent_h_complexity_linting_handoff.md`
- **Ruff:** 110 F401 (unused imports), 0 F811, milliseconds runtime, auto-fix capable. Runner: `scripts/run_ruff.py`
- **radon:** 714 blocks, 93 C+ complexity hotspots, 2 F-ranked (cc>50), 5-10s runtime. Runner: `scripts/run_radon.py`
- **Decision:** Both APPROVED — Ruff is fast and provides auto-fix; radon surfaces refactoring targets.
- **pylint:** SKIPPED — 109 W0611 findings fully overlap with Ruff F401; 67 W0612/W0613 don't justify separate dependency.

---

## Changes Made

### File 1: `d:/Project/.windsurf/skills/clean-up/SKILL.md`

#### Edit 1 — Phase 1 tool table (lines 78-82)
**Before:**
```markdown
| **Python** | `run_vulture.py` + `run_import_analyzer.py` + `run_jscpd.py` |
| **JS/TS** | `run_fallow.py` + `run_jscpd.py` |
| **Mixed** | All four: `run_vulture.py` + `run_import_analyzer.py` + `run_fallow.py` + `run_jscpd.py` |
```
**After:**
```markdown
| **Python** | `run_vulture.py` + `run_import_analyzer.py` + `run_jscpd.py` + `run_ruff.py` + `run_bandit.py` + `run_pip_audit.py` + `run_radon.py` |
| **JS/TS** | `run_fallow.py` + `run_jscpd.py` + `run_bandit.py` (if Python backend exists) |
| **Mixed** | All tools from both rows |
```
**Summary:** Added 4 new tools to Python row; added bandit to JS/TS row (conditional on Python backend); simplified Mixed row to "All tools from both rows".

#### Edit 2 — Phase 1 command examples (lines 84-92)
**Before:** 4 command lines (vulture, import_analyzer, fallow, jscpd).
**After:** 8 command lines — added `run_ruff.py`, `run_bandit.py`, `run_pip_audit.py`, `run_radon.py` with `--project @Project --json` flags.

#### Edit 3 — Phase 5 regression table (lines 169-171)
**Before:** 3 rows (Python vulture+import_analyzer, JS/TS fallow, All languages jscpd).
**After:** Added 2 rows:
```markdown
| **Python** | `run_bandit.py` | New security findings post-cleanup = regression. |
| **Python** | `run_radon.py` | Complexity increase in refactored code = regression. |
```
**Summary:** bandit and radon added as regression signals. pip-audit excluded (dependency-level, not affected by file cleanup). Ruff excluded (findings expected to decrease post-cleanup, not a regression signal).

#### Edit 4 — Phase 5 regression commands (lines 176-178)
**Before:** 3 `--compare` commands (vulture, import_analyzer, jscpd).
**After:** Added 2 `--compare` commands:
```powershell
python ai_dev_meta_layer/scripts/run_bandit.py --project @Project --json --compare ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json
python ai_dev_meta_layer/scripts/run_radon.py --project @Project --json --compare ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json
```

#### Edit 5 — Phase 7 metrics table (line 210)
**Before:**
```markdown
| Deterministic tool findings (before → after) | vulture: X→Y, import-analyzer: X→Y, jscpd: X%→Y% |
```
**After:**
```markdown
| Deterministic tool findings (before → after) | vulture: X→Y, import-analyzer: X→Y, jscpd: X%→Y%, ruff: X→Y, bandit: X→Y, pip-audit: X→Y, radon: X→Y |
```
**Summary:** All 7 deterministic tools now tracked in the outcome metrics table.

### File 2: `d:/Project/.windsurf/skills/clean-up/ORCHESTRATION.md`

#### Edit 6 — `--light` mode paragraph (after line 77)
**Before:** Existing paragraph covering Vulture, jscpd, Fallow in `--light` mode; import-analyzer-py skipped.
**After:** Added new paragraph:
```markdown
Additional `--light` mode tools: Ruff (fast lint, milliseconds), bandit (security
scan, 3-21s), and radon (complexity, 5-10s) are fast enough for `--light` mode.
pip-audit is skipped in `--light` mode (dependency audit is full-architecture
scope). This gives `--light` mode deterministic dead code + duplication +
security + complexity coverage without the LLM audit cost.
```
**Summary:** Ruff, bandit, radon added to `--light` mode (all fast enough). pip-audit skipped in `--light` mode (full-architecture scope).

---

## Tools NOT Referenced

Per constraints, the following evaluated-and-skipped tools are NOT referenced in any edit:
- **pylint** — skipped by Agent H (overlaps with Ruff F401)
- **knip** — not evaluated for clean-up
- **duplicate-code-detection** — not evaluated (jscpd covers duplication)

---

## Health Check Result

**Command:** `python "d:/Project/ai_dev_meta_layer/scripts/daily_health_check.py"`
**Exit code:** 1
**Overall status:** broken (pre-existing, not caused by our edits)

Pre-existing issues unrelated to this task:
- **Encoding:** `cutman_brief_check.json` has UTF-16 BOM
- **Project Skills:** 98 issues across 48 skills (missing referenced files in other project skills, not clean-up)
- **Project Agents:** 24 projects with missing AGENTS.md references
- **Index Token Budgets:** 33 routes with unresolved paths in workspace_network

The clean-up skill itself is not flagged in any health check category. No new issues were introduced by our edits.

---

## Runner Scripts Verified

All 4 runner scripts exist at expected paths:
- `d:/Project/ai_dev_meta_layer/scripts/run_bandit.py`
- `d:/Project/ai_dev_meta_layer/scripts/run_pip_audit.py`
- `d:/Project/ai_dev_meta_layer/scripts/run_ruff.py`
- `d:/Project/ai_dev_meta_layer/scripts/run_radon.py`

---

## Handoff

**Report file:** `ORCHESTRATION/tool-integration/wave5/agent_k_cleanup_w4_tools_handoff.md`
**Summary:** Wired bandit, pip-audit, Ruff, and radon into clean-up SKILL.md (tool table, command examples, regression checks, metrics) and ORCHESTRATION.md (--light mode). 6 edits across 2 files. Health check confirms no new issues. No references to skipped tools (pylint, knip, duplicate-code-detection).
