# Music Hub — master plan

**Status: LOCKED v1 (2026-10-06).**
- Builders follow these documents as written.
- A change needs a new entry in `07_DECISIONS.md` § Change log, plus a version bump here (v1.1 …).
- Never edit a locked rule silently.

**What it is:** a local web app that shows Nikola one screen answering two questions.
1. **What's waiting on me?** That means every decision, ear test, sign-off and input any lane needs from him.
2. **What happened?** That is a journal of activity across all music repos and lanes. Each entry shows a
   **receipts** badge proving whether the work it claims actually landed in git.

Later waves add a **Lanes & repo-health** board and **Artist pages**. Artist pages show songs, voice profiles,
chain-map SVGs and listening packs.

**Why now:** the 2026-10-04/05 workspace clean-up showed the cost of not having it. See the diagnosis doc
`D:\Projects\.workspace_archive\reviews\2026-10-04_music_workspace_diagnosis.md`. The problems were:
- votes and sign-offs buried in ledgers;
- a "done" report with no commit behind it;
- two agents colliding in one working tree;
- dirty and unpushed state spread across 10 repos.

## Documents (read in this order)

| # | File | What it answers |
|---|------|-----------------|
| 00 | `00_VISION.md` | Problem, goals, non-goals, success criteria |
| 01 | `01_DESIGN.md` | Architecture, components, runtime contract, security, error handling |
| 02 | `02_DATA_SOURCES.md` | Every source the hub reads: path, real format (with evidence), collector, attribution rules |
| 03 | `03_DATA_MODEL.md` | SQLite cache schema, inbox JSONL schema, event kinds, receipts algorithm |
| 04 | `04_VISUAL_CONTRACT.md` | `/define_visual` per-section rendering contract (tokens, copy, states, checks) |
| 05 | `05_WAVES.md` | Implementation plan: waves W0–W5, tasks, gates, token budget |
| 06 | `06_EXPECTED_OUTCOMES.md` | `/define_output` spec: deterministic check commands per outcome |
| 07 | `07_DECISIONS.md` | Locked decisions D1–D16 + change log |
| 08 | `08_RULES_FOR_BUILDERS.md` | Lane rules for the building agent (Devin): isolation, commits, receipts, gates |
| — | `LEDGER.md` | Wave ledger. The builder updates it; the orchestrator verifies. |
| — | `seed_inbox.jsonl` | The items waiting on Nikola on 2026-10-06; imported in W2 |
| — | `mockups/home.html` | Static Home mockup; the visual provenance for `04` |
| — | `checks/contract_checks.py` | Independent checker (31 checks, stdlib only), written by the orchestrator. **Builders never edit it** (D14) |
| — | `prompts/W0.md … W5.md` | Paste-ready bootstrap prompt per wave (one fresh session each) |

## How to build

1. Start each wave in a **fresh Devin session** by pasting `prompts/W<N>.md`.
2. The builder works **only** in the worktree `D:\Projects\Music-AI-Toolshop-wt-hub` on branch `lane/hub`
   (created in W0). Never in the main checkout.
3. At the end of each wave the builder writes its handoff into the **worktree copy** of `LEDGER.md`, committed on
   `lane/hub`. The handoff must include commit hashes and the `06` check output, and the builder must **stop**.
4. Nikola asks the orchestrator (Claude) to verify that wave.
5. Only after verification is the wave merged to `master`. The next wave starts from the merged state.

## Where things live

| Thing | Location |
|---|---|
| Code | `Music-AI-Toolshop/toolshop/hub/` (subpackage, the `toolshop/daw/` pattern) |
| Tests | `Music-AI-Toolshop/tests/test_hub_*.py` |
| Run | `python -m toolshop.hub serve` → `http://127.0.0.1:8790/` |
| Cache + inbox data | `TOOLSHOP_DATA_DIR/hub/` (default `Music-AI-Toolshop/data/toolshop/hub/`, git-ignored) |
| Plan, ledger, prompts | this folder |
