# 07 — Decisions (locked v1, 2026-10-06)

Each decision has an id that other documents cite. To change one, append a row to the **Change log** and bump the
README version. A decision is never edited in place.

| ID | Decision | Why | Source |
|---|---|---|---|
| D1 | Home = **Inbox ("waiting on you") + Journal** on one page; Lanes (W3) and Artists (W4) follow | The week's failures all show up in "what needs me / what really happened" | Nikola, 2026-10-06 ("sounds good" to option D, starting with A+B) |
| D2 | It is a **tool**, so it lives in the parent `Music-AI-Toolshop` as subpackage `toolshop/hub/`. Its lane folder is `ORCHESTRATION/hub/` | Rule R1 (three homes) and R3 (lane-local plans); the `toolshop/daw/` subpackage pattern (AGENTS.md § Package layout) | Diagnosis doc R1/R3 |
| D3 | Stack: **Flask 3.1.3 (already installed) + Jinja + vanilla JS + one CSS file**. No npm, no build, no CDN | Ponytail ladder: reuse an installed dependency; works offline; the user's other local tools (audition_review, MAirina API) follow the same shape | `.venv` check 2026-10-06 |
| D4 | `hub.db` is a **rebuildable cache**; `inbox.jsonl` is the **append-only source of truth** in `TOOLSHOP_DATA_DIR/hub/` and gets **backup coverage** | Losing the cache costs nothing; losing answers costs decisions. Append-only gives an audit trail | AGENTS.md "Backups are verified by coverage" |
| D5 | **Read-only toward repos.** The git allow-list has no fetch; the hub writes only its own data dir | Agents and humans own the repos; a dashboard must never be a writer | Lane isolation lessons (memory `lane-isolation`) |
| D6 | The inbox is **structured** (CLI/API asks). Ledgers and handoffs are **not** parsed into inbox items | ≥6 different ledger table shapes, and "Remaining Work" in handoffs is never updated (rule `handoff-freshness`) | `02` S3/S4 evidence |
| D7 | Bind `127.0.0.1:8790` only; Origin guard on POST; `/file` restricted to the workspace root; no auth | Single user, local machine; blocks drive-by POSTs from other browser tabs | `01` Security |
| D8 | Visual tokens = MAirina rimer-ui `index.css:2-48` (light + dark), copied exactly | Nikola's most recently approved UI; one visual language across his local tools | `04` |
| D9 | **Receipts** badge on session and handoff journal rows, computed from git | The 2026-10-05 "fix 3 done" report had no commit; a badge makes that visible without a manual audit | `03` § Receipts |
| D10 | Journal horizon 90 days (config); Home shows the last 7 days, ≤100 rows | Keeps Home fast and readable; the full journal pages through the rest | `04` |
| D11 | CLI is `python -m toolshop.hub …`; **no edit to `toolshop/cli.py`** | Avoids a shared-file edit by the lane (R3) | Lane rules |
| D12 | Build in worktree `D:\Projects\Music-AI-Toolshop-wt-hub` on branch `lane/hub`. Each wave merges to master only after orchestrator verification | R2 (one lane = one branch + one working tree + one agent); the 2026-10-05 Studio collision | Diagnosis doc |
| D13 | The CHANGELOG ID is allocated at merge time, by whoever merges | R3 and the CHANGELOG ID note (IDs ≤ #084 are not unique) | `CHANGELOG.md` top note |
| D14 | Contract checks live in `ORCHESTRATION/hub/checks/contract_checks.py`. They are written by the orchestrator and **never edited by the builder** | Proposer ≠ approver; a builder grading its own work is how "done" reports drifted from reality | `define_visual` adversarial pass |
| D15 | De-esser values are shown as **linear**, never as dB | The schema stores a linear 0–1 envelope despite the `_db` field name (`voice_profiles/schema.json:41`) | Fix 2 / F14 |
| D16 | Times are shown in Europe/Belgrade, 24-hour; English weekday and month names | Nikola's locale; commits carry +0200 | Git logs |

## Open questions for later waves (do not block W0–W2)

| Q | Ask at | Default if unanswered |
|---|---|---|
| Q1 | Phone access over the LAN (bind 0.0.0.0 + token)? | After G2 | No (stays 127.0.0.1) |
| Q2 | Which listening packs belong to which artist (`pack_artist_rules`)? | W4 (builder lists the candidates) | Unassigned packs are shown only on the journal |
| Q3 | Should agents' session_end automatically `ask` its "Remaining Work" items? | After G5 | No; agents ask explicitly |

## Change log

| Version | Date | Change | By |
|---|---|---|---|
| v1 | 2026-10-06 | Initial lock | orchestrator (Claude), approved by Nikola ("lock it in") |
