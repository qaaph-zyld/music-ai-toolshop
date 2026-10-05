# 00 — Vision

## The problem (observed, 2026-10-04 … 10-06)

Nikola runs about 10 music repos: the parent `music-ai-toolshop` plus 9 submodules, among them `studio/`
(artist sessions), `MAirina_Tucc` and `Stemmeca_alatkka`. Several AI lanes work in them at the same time.
Their state lives in five scattered places, and none of them is shaped for a human:

| Where state lives | How much | Problem |
|---|---|---|
| Orchestration ledgers | ≥14 files, ≥6 different table shapes | "Pending G4 vote" is a prose cell in one of them |
| Session records | 292 in `ai_dev_meta_layer/memory/episodic/sessions/` | Two filename schemes, free-form |
| Handoffs | 86 in `.workspace_archive/handoffs/` | "Remaining Work" is never updated |
| Git | 10 repos + worktrees | Dirty/unpushed state is invisible without running commands |
| Listening comments | `Stemmeca_alatkka/stems/_audition_comments/*.jsonl` | Only readable as raw JSON |

These are the concrete failures this caused during the clean-up:
- **Decisions sat unnoticed** in prose. Examples: the OGCJ G4 vote, the W1b sign-off, the W1e "re-bench on a quiet
  machine", and the PE3 raw take.
- **A "fix 3 done" report had no commit behind it.** Only a manual git-log check exposed that.
- **Two agents worked in one Studio working tree** at the same time. Their commits landed on the wrong branch twice.
- **"Closed" lanes were left unmerged,** and their work sat unpushed for days.

## Goal

One local page Nikola opens with his coffee that answers:

1. **What is waiting on me?** That means decisions, ear tests, sign-offs, inputs to provide, and "run when you
   say so" items. Sort them by what blocks the most work, and let him resolve each one in place.
2. **What happened?** A journal across all music repos and lanes, newest first and filterable by lane, repo
   and artist. Each "I did X" record carries a **receipts** badge, which proves from git whether the cited
   commits exist and are pushed.

Then, in later waves:

3. **Is anything unhealthy?** A lanes and repo-health board covering dirty trees, unpushed commits, live
   worktrees, and orchestrator overrides.
4. **Where is each artist and song?** Artist pages built from `studio/artists/*/ARTIST.md` and
   `voice_profiles/*.json`. They show confidence flags, chain-map SVGs (from `/mix_svg_tree`) and listening
   packs with their comment verdicts.

## Non-goals (v1)

- **No git writes from the UI.** No commit, push, merge or branch operations; the hub never mutates a repo.
- **No editing of ledgers, handoffs or session records.** The hub reads them; agents keep writing them.
- **No cloud, auth or multiple users.** It is local, single-user, `127.0.0.1` only.
- **No audio playback engine.** Listening stays on the existing `audition_review` pages (:8778); the hub links to them.
- **No lyric writing of any kind.** This is a standing product rule (memory `ai-finds-never-writes-lyrics`).
- **No parsing of prose ledgers into inbox items.** The inbox is structured on purpose (see `07` D6).

## Success criteria (checked in `06`)

- **Fast:** the Home page renders in under 2 s, and a re-index takes under 30 s on this PC.
- **Correct counts:** journal event counts reconcile with independent counts per source, e.g. `git rev-list --count`
  per repo and the number of session files.
- **Receipts are honest:**
  - a session record citing a commit that exists and is pushed shows **green**;
  - a cited hash that does not exist shows **red**;
  - no cited hash shows **grey "no receipts"**.
- **Inbox round-trip works:** an agent runs `python -m toolshop.hub ask …`, the item appears on Home, Nikola resolves
  it in the UI, the resolution is appended to `inbox.jsonl`, and the agent reads it with
  `python -m toolshop.hub list --resolved-since …`.
- **No repo is mutated** by indexing or serving: `git status --porcelain` is identical before and after a full run.
- **Nikola uses it.** The W2 user gate is a verdict on the real page, not on a screenshot.
