# Clean-Up Skill — Rollback & Orchestration

> Reference for `clean-up/SKILL.md`.
> Contains rollback, context budget, and anti-patterns.

---

## Rollback

Any point after Phase 0, one command restores the pre-cleanup state:

```powershell
python ai_dev_meta_layer/scripts/cleanup_checkpoint.py rollback @Project --tag cleanup-checkpoint-<stamp> --yes
# equivalent to: git -C "<project>" reset --hard cleanup-checkpoint-<stamp>
```

To restore a single staged file instead of everything:
`git -C "<project>" mv to_be_deleted/<path> <path>`.

---

## `to_be_deleted/` Lifecycle

- **Created**: Phase 0 scaffold (`cleanup_checkpoint.py scaffold`).
- **Populated**: Phase 4 (via `git mv`, each row appended to `manifest.tsv`).
- **Aging**: `/consolidate` report flags items >90 days for human review.
- **Emptied**: Human-approved `rm -rf to_be_deleted/` + commit.
- **Never**: Emptied during the same clean-up run that created it.

---

## Orchestration & Context Budget

Agent context windows (~200–262k tokens) cannot hold a large project *and* seven
phases of analysis. This workflow is built so the **organizer never has to**:

- **Organizer (parent)** holds only: the phase ledger, the checkpoint tag, and
  the *summaries* of each subagent report. It decides and coordinates.
- **Workers (subagents)** do the token-heavy reading in **isolated `fork`
  contexts** and hand back a **file** (`handoffs/…`, `.windsurf/plans/…`). Per
  `.windsurf/skills/ROLES.md`: subagents report, the parent decides; subagents
  never talk to each other — all state flows through files.
- **Phase ledger** — maintain `ai_dev_meta_layer/handoffs/cleanup_ledger_<project>_<stamp>.md`:

  | Phase | Status | Artifact | Notes |
  |-------|--------|----------|-------|
  | 0 Checkpoint | ✅ | tag `cleanup-checkpoint-…` | pushed |
  | 1 Discovery | ✅ | `explorer_*_…md` | 3 reports |
  | 2 Audit | ⬜ | `architecture_report_…md` | |
  | … | | | |

  If the session is compacted or handed off mid-run, the ledger + the report
  files are sufficient to resume without re-reading the codebase.
- **Parallelism**: Phase 1 explorers and independent audit lenses run
  concurrently (independent scopes), then the organizer synthesizes.

This is the same file-native, isolated-context pattern the harness uses
elsewhere. See `.windsurf/skills/ROLES.md` § Context Budget & Ledger for the
canonical convention.

**P0 blocker handling**: If Phase 2 audit finds P0 blockers, the organizer
pauses, presents to user, and records the decision in the ledger. Cleanup
does not auto-proceed past P0 blockers.

**Testless projects**: For projects with zero tests, Phase 5 uses import
smoke tests + build checks + diff review. The organizer records which
verification method was used.

**`--light` mode**: Skips Phase 2 full audit and Phase 6 adversarial review.
Context budget is ~60% lower. Suitable for projects <50 files where a full
5-phase audit is disproportionate.

**Deterministic tools in `--light` mode**: Vulture, jscpd, and Fallow runners
still execute — they are fast, read-only, and substitute for the skipped full
audit. `import-analyzer-py` is skipped (import graph analysis is part of the
full architecture audit). This gives `--light` mode deterministic dead code +
duplication coverage without the LLM audit cost.

Additional `--light` mode tools: Ruff (fast lint, milliseconds), bandit (security
scan, 3-21s), and radon (complexity, 5-10s) are fast enough for `--light` mode.
pip-audit is skipped in `--light` mode (dependency audit is full-architecture
scope). This gives `--light` mode deterministic dead code + duplication +
security + complexity coverage without the LLM audit cost.

---

## Anti-Patterns

- **Do not** `rm` / hard-delete anything — always `git mv` into `to_be_deleted/`.
- **Do not** skip Phase 0 — no cleanup without a rollback point.
- **Do not** move files before the plan is approved.
- **Do not** load the whole project into the organizer — dispatch subagents.
- **Do not** claim done without `/verify` evidence.
- **Do not** empty `to_be_deleted/` in the same run — that is a later human step.
