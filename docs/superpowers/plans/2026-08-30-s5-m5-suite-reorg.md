# S5 — M5: Suite reorganisation + meta-layer registration

**Date:** 2026-08-30 · **Author:** orchestrator · **Size:** 1 session
**Goal:** G1 · last H1 milestone
**Roadmap definition (v2 §H1):** *"Suite reorganization: core/tool package layout, AGENTS.md,
register project in meta-layer project table + KB entry"* · exit: *"imports/CLI unchanged (tests
green); AGENTS.md live; session_brief detects project"*

---

## Scoping — what is actually left

M5 is three separate things. Two are nearly done; one should not be done at all right now.

| Part | State (verified 2026-08-30) |
|---|---|
| **AGENTS.md live** | ✅ **Done.** Exists and has grown substantially — close-out discipline, lane discipline, measurement discipline. |
| **Meta-layer KB entry** | ✅ **Done.** `ai_dev_meta_layer/memory/semantic/projects/Music-AI-Toolshop_LESSONS.md` exists, 902 lines. |
| **Meta-layer project table** | ❌ **Missing.** `framework/project_inventory.py::CANONICAL_PROJECTS` has 30+ entries; none is this project. |
| **core/tool package layout** | ⚠️ **Recommend descoping — see below.** |
| **Voicebox archived (roadmap §G3, "in H1-M5")** | 🟡 **Half done.** Untracked from git in P0 (D9, 410 files), but the ADR + upstream link the roadmap asks for was never written. |
| **Repo-root one-off scripts** | 🟡 Deferred from P0 Task 6; genuinely "suite reorganisation" work. |

---

## [USER DECISION D12] — descope the package reorg

**Recommendation: do not do the flat→nested move, now or as a single change.**

`toolshop/` currently holds **55 flat modules** plus two subpackages (`daw/`, `melody_carrier/`), and
**63 test files** import from it. The reasons to decline:

1. **Its own exit criterion is "imports/CLI unchanged".** A refactor whose success condition is that
   nothing observable changes delivers no user-visible value. It buys internal tidiness only.
2. **The roadmap already warns against it as a single move** — "the package reorganization is
   gradual (H1-M5), never a big-bang rewrite" (§ line 43) and risk row "Tests-first, alias old verbs,
   no big-bang moves". Doing it in one session is what the roadmap tells us not to do.
3. **It is exactly where a green suite can lie.** Moving modules behind re-export shims keeps tests
   passing while the real structure is wrong. This session has already produced two
   verification-scope errors (#042 cold-cache, #044 debt-13b); a 55-module move is the worst possible
   place to trust "tests green" as proof.
4. **It is not the bottleneck.** H2 Dossier v2 is what the creation loop has been waiting on since
   July. Spending a session rearranging files ahead of it is motion, not progress.

**What to do instead:** treat package layout as an *opportunistic* rule rather than a milestone — when
a lane is next touched substantially, its modules move into a subpackage then, with that lane's tests
as the safety net. `daw/` and `melody_carrier/` already demonstrate the pattern working.

**If the user wants M5's reorg done properly**, it deserves its own multi-session plan with a
module-by-module sequence, not a tick inside a milestone that is otherwise administrative.

**Consequence for H1:** with the reorg descoped, M5's remaining work is small and H1 closes on
M2 ✅ / M3 ✅ / M4 ✅ / M5 (this) / M6 ✅ — with M1 long closed.

---

## Tasks

### Task 1 — Register in the meta-layer project table

`ai_dev_meta_layer` is a **separate git repo** (branch `main`, clean at session start). Add
`Music-AI-Toolshop` to `CANONICAL_PROJECTS` in `framework/project_inventory.py`.

Note every existing entry is nested under `Corporate_Projects/` or `Tools/`; this project sits at the
`D:\Projects` root, so verify the resolved path is correct rather than assuming the pattern.

**Exit evidence:** `project_inventory` resolves the project root; its own tests still pass.

**Do not push the meta-layer repo** — committing to a second repo is the user's call, not a
side effect of this session.

### Task 2 — Verify detection actually works

The roadmap's exit criterion is *"session_brief detects project"*. Run it and show the detection,
rather than asserting registration equals detection. (Registering a name in a dict and having the
tool find the project are two different claims — see #044.)

### Task 3 — Voicebox ADR

Roadmap §G3 asks for Voicebox archived out of the repo **with an ADR + upstream link**. The removal
happened in P0; write the missing ADR: what it was, why it left, where upstream lives, and the
condition for re-adopting it (the GPU gate).

### Task 4 — Repo-root one-off scripts

Deferred from P0 Task 6 because every candidate has a live importer or doc reference. Either move
them with imports updated and the suite green, or record explicitly why they stay. **A decision
either way — not a third deferral.**

### Task 5 — Close out

CHANGELOG **#045**, STATUS, H1 status updated. Suite (bar: no new failures against **991 passed /
2 skipped / 0 failed**), `doctor` **Overall: PASS**, `closeout`.

Note: `closeout` will likely still report a dirty tree — another session has been writing untracked
files into this repo (`lyrics_research/documents/`, `ORCHESTRATION/prompts/*hemija*`). Those are not
this session's and must not be committed; declare them per the AGENTS.md "clean tree or declared" rule.

---

## Out of scope

- The flat→nested package move (D12 above)
- `ai_modules/` — D6 still deferred
- Pushing the `ai_dev_meta_layer` repo
