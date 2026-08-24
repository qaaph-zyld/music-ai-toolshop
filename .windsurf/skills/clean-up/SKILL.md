---
name: clean-up
description: Detailed execution steps for the /clean-up workflow. Checkpoint-safe project clean-up with phased subagent orchestration.
version: 0.1.0
license: Proprietary
author: a265m001-bot
compatibility: windsurf
allowedTools: []
effort: high
trigger: manual
---

# Clean-Up Skill — Detailed Execution

> Reference skill for `/clean-up` workflow (`.windsurf/workflows/clean-up.md`).
> Contains the detailed phase steps, code examples, and orchestration patterns.

---

## Phase 0 — Checkpoint (GitHub save = rollback point)

Mechanical; owned by `scripts/cleanup_checkpoint.py` (never freehand git here).

```powershell
# 1. Inspect the target's repo, remote, and cleanliness.
python ai_dev_meta_layer/scripts/cleanup_checkpoint.py status @Project

# 2. Create the pre-cleanup snapshot: WIP commit + tag + branch (--dry-run to preview).
python ai_dev_meta_layer/scripts/cleanup_checkpoint.py checkpoint @Project --push

# 3. Create the staging area the cleanup will move files into.
python ai_dev_meta_layer/scripts/cleanup_checkpoint.py scaffold @Project
```

- The checkpoint tag is `cleanup-checkpoint-<stamp>`; the branch is `cleanup/<stamp>`.
- **Pushing is outward-facing** → confirm before `--push`. If the user declines,
  keep the checkpoint local (still a valid rollback point).
- If `@Project` is not a git repo, offer to `git init` first — do not proceed
  without a checkpoint.

**Record** the tag name in the phase ledger — it is the rollback contract.

---

## Phase 1 — Discovery (parallel isolated subagents)

Dispatch **read-only `explorer` subagents in parallel**, each scoped to one lens
so no single context loads the whole tree. Each writes a findings file the
organizer will read.

```powershell
python ai_dev_meta_layer/scripts/dispatch_subagent.py explorer `
  --task "Inventory obsolete/generated/stale artifacts: build output, logs, *_output.txt, dist/, caches, dead scripts, orphaned test-output, duplicate handoffs" `
  --scope "Corporate_Projects/<Project>" --execute `
  --output "ai_dev_meta_layer/handoffs/cleanup_explore_artifacts_<stamp>.md"

python ai_dev_meta_layer/scripts/dispatch_subagent.py explorer `
  --task "Map module topology, entry points, import graph, and dead code / unreferenced files" `
  --scope "Corporate_Projects/<Project>" --execute `
  --output "ai_dev_meta_layer/handoffs/cleanup_explore_topology_<stamp>.md"

python ai_dev_meta_layer/scripts/dispatch_subagent.py explorer `
  --task "Find duplicate / near-duplicate files, redundant docs, and consolidation candidates" `
  --scope "Corporate_Projects/<Project>" --execute `
  --output "ai_dev_meta_layer/handoffs/cleanup_explore_duplication_<stamp>.md"
```

The organizer reads the three reports and builds a single **candidate ledger**
(no decisions yet — just evidence).

### Deterministic Pre-Pass (before subagent dispatch)

Run language-appropriate deterministic tools **before** dispatching explorer
subagents. Results feed into subagents as input — they no longer start from
scratch. If a tool is unavailable, the corresponding subagent falls back to
manual discovery; log which tools ran and which were unavailable.

| Project type | Tools |
|--------------|-------|
| **Python** | `run_vulture.py` + `run_import_analyzer.py` + `run_jscpd.py` + `run_ruff.py` + `run_bandit.py` + `run_pip_audit.py` + `run_radon.py` |
| **JS/TS** | `run_fallow.py` + `run_jscpd.py` + `run_bandit.py` (if Python backend exists) |
| **Mixed** | All tools from both rows |

```powershell
python ai_dev_meta_layer/scripts/run_vulture.py --project @Project --json
python ai_dev_meta_layer/scripts/run_import_analyzer.py --project @Project --json
python ai_dev_meta_layer/scripts/run_fallow.py --project @Project --json
python ai_dev_meta_layer/scripts/run_jscpd.py --project @Project --json
python ai_dev_meta_layer/scripts/run_ruff.py --project @Project --json
python ai_dev_meta_layer/scripts/run_bandit.py --project @Project --json
python ai_dev_meta_layer/scripts/run_pip_audit.py --project @Project --json
python ai_dev_meta_layer/scripts/run_radon.py --project @Project --json
```

Save outputs to `ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json` and pass
the file path to each explorer subagent as input.

**Subagent task shift**: With deterministic tool output available, explorer
subagents shift from "find dead code" to **"validate findings, check false
positives, identify items tools missed."** The tools do the mechanical scan;
subagents do the contextual judgment.

---

## Phase 2 — Architecture & Consolidation Analysis

Delegates to other workflows — no clean-up-specific file moves here.

### Architecture Audit
- Run `/architecture-check @Project` (full 5-phase audit).
- **`--light` mode**: Inline checklist — entry points importable, no circular imports, no hardcoded secrets, no broken imports.
- **P0 blockers**: Pause → user decides: fix first / proceed with note / abort. Record in ledger.

### Consolidation Lens
- Apply `/consolidate` *perspective* (not full 9-step workflow) to Phase 1 duplication findings.
- Look for: mergeable duplicates, near-duplicate logic for shared utility, redundant docs.
- Record candidates in phase ledger for Phase 3.

---

## Phase 3 — Plan Manifest Table

The plan MUST contain a **manifest table** classifying every candidate:

| Original Path | Category | Reason (evidence) | Proposed Target |
|---------------|----------|-------------------|-----------------|
| `dist/…` | DELETE | build artifact, regenerated | `to_be_deleted/dist/…` |
| `foo_v2.py`, `foo_v3.py` | CONSOLIDATE | supersede `foo.py`; merge | single `foo.py` |
| `src/*.js` (flat) | RESTRUCTURE | no module boundaries | `src/<domain>/…` |
| `README.md` | KEEP | canonical | — |

Categories: **DELETE** (→ `to_be_deleted/`), **CONSOLIDATE** (merge duplicates),
**RESTRUCTURE** (modular reorg), **KEEP**.

Also include: a proposed target module layout, an ordered execution sequence
(low-risk deletes first, restructuring last), and the rollback tag from Phase 0.

---

## Phase 4 — Execute Details

Order: stage DELETEs → CONSOLIDATE → RESTRUCTURE.

- **Stage deletes** with `git mv` so history is preserved and the move is
  reversible; append a row to `to_be_deleted/manifest.tsv` for each:
  ```powershell
  git -C "<project>" mv "<path>" "to_be_deleted/<path>"
  ```
- **Consolidate**: merge duplicates into the canonical file; stage the losers.
- **Restructure**: move modules into the approved layout; update imports.
- Commit in **small, labelled steps** (`clean-up: stage build artifacts`,
  `clean-up: consolidate foo_v*`, `clean-up: modularize src/`), so any single
  step is independently revertible on top of the checkpoint.
- **Partial cleanliness**: After each commit group, repo is clean and committable. Execution can pause between groups.

---

## Phase 5 — Verify

### Structural Regression Check

After file moves (Phase 4), re-run deterministic tools and compare to the
pre-cleanup baseline from Phase 1.

| Project type | Re-run | Regression signal |
|--------------|--------|-------------------|
| **Python** | `run_vulture.py` + `run_import_analyzer.py` | New unused imports after consolidation = expected. **New circular dependencies = regression.** |
| **JS/TS** | `run_fallow.py --command audit` | Baseline-aware — compares to pre-cleanup state. |
| **All languages** | `run_jscpd.py` | Compare duplication % to pre-cleanup. Increase = regression. |
| **Python** | `run_bandit.py` | New security findings post-cleanup = regression. |
| **Python** | `run_radon.py` | Complexity increase in refactored code = regression. |

```powershell
python ai_dev_meta_layer/scripts/run_vulture.py --project @Project --json --compare ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json
python ai_dev_meta_layer/scripts/run_import_analyzer.py --project @Project --json --compare ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json
python ai_dev_meta_layer/scripts/run_jscpd.py --project @Project --json --compare ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json
python ai_dev_meta_layer/scripts/run_bandit.py --project @Project --json --compare ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json
python ai_dev_meta_layer/scripts/run_radon.py --project @Project --json --compare ai_dev_meta_layer/handoffs/cleanup_tools_<stamp>.json
```

### Standard Verification

- Run `/verify` — evidence-based completion gate.
- Run project test suite; quote exit codes and key output.
- For testless projects: import smoke tests + build checks + diff review.
  Record which verification method was used.

---

## Phase 7 — Report, Persist, Handoff

1. **Write report** to `audit_history/cleanup_report_<project>_<date>.md` —
   includes the candidate ledger, decisions, tool findings before/after, and
   rollback tag.
2. **Persist findings** — write HIGH/MEDIUM findings to
   `<project>_LESSONS.md` for future session reuse.
3. **Run `/handoff`** + `python scripts/session.py end --status completed
   --helpful clean-up` — triggers experience extraction and memory
   verification.
4. **Outcome metrics table** — include in the report:

   | Metric | Value |
   |--------|-------|
   | Files staged (DELETE) | N |
   | Files consolidated | N |
   | Files restructured | N |
   | Files kept | N |
   | Test status | pass/fail (exit code) |
   | Net lines removed | N |
   | Deterministic tool findings (before → after) | vulture: X→Y, import-analyzer: X→Y, jscpd: X%→Y%, ruff: X→Y, bandit: X→Y, pip-audit: X→Y, radon: X→Y |

---

## Rollback, Orchestration & Anti-Patterns

→ **Detail**: [`ORCHESTRATION.md`](ORCHESTRATION.md)
