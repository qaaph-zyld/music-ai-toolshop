# 08 — Rules for the building agent (Devin)

These rules are binding. They exist because each one was broken at least once in this workspace during
September–October 2026.

## Isolation

1. **Work only in `D:\Projects\Music-AI-Toolshop-wt-hub` on branch `lane/hub`.**
   - Never edit files in the main checkout `D:\Projects\Music-AI-Toolshop`. The exceptions are the
     merge step (W-end, after verification) and the W5 AGENTS.md rule edits listed in `05`.
   - Never edit any submodule except where `05` W4/W5 says so explicitly.
2. **One agent at a time in the worktree.** If you see uncommitted changes you did not make, stop and report
   them in `LEDGER.md`. Do not build on top of them, and do not commit them.
3. **Never touch live-lane files.**
   - Studio: `ORCHESTRATION/ogcj_flip/`, `Only_God_Can_Judge_Me_Flip/` and `data/ogcj_flip/`.
   - Toolshop: `ORCHESTRATION/ogcm_flip/` and `Stemmeca_alatkka/stems/**`.
   - The worktrees `Music-AI-Toolshop-wt-flip`, `-wt-lyrics-p2` and `-wt-audition`, plus any other `-wt-*` not
     named `-wt-hub`.
   - Reading `Stemmeca_alatkka/stems/_audition_comments/` is allowed. Writing is not.
4. **The hub never writes into a repo.** It runs only the git commands on the allow-list in `01`; `fetch` is
   not on it.

## Commits

5. **Explicit pathspecs only.** Never `git add -A` or `git add .`. Stage, run `git diff --cached --name-only`, then
   commit, as three separate calls (rule `run-git-add-git-commit`).
6. **One concern per commit.** Subjects use the form `feat(hub): …`, `test(hub): …` or `docs(hub): …`.
   - No CHANGELOG ID; the ID is allocated at merge (D13).
   - Shared indexes (README, PROJECTS_INDEX, STATUS, the root CHANGELOG) are edited only in the W5 merge commit.
7. **No push without Nikola's explicit OK** in the session. `lane/hub` may stay local until merge.
8. **Never edit `ORCHESTRATION/hub/checks/contract_checks.py`** or any locked plan document (`00`–`07`).
   - If one is wrong, write the problem into `LEDGER.md` under "Plan issues" and stop that task.
   - `LEDGER.md` is the only plan file you write.

## Evidence and close-out

9. **Every wave ends with a `LEDGER.md` entry** containing:
   - the commit hashes (full 7+ chars) on `lane/hub`;
   - the raw output of every `06` check for that wave, with exit codes;
   - `git -C D:\Projects\Music-AI-Toolshop-wt-hub status --porcelain`, which must be empty;
   - deviations from the plan, each with its reason;
   - plan issues found.
10. **Don't claim what you haven't checked.**
    - "Done", "passes" and "works" require the check output in the entry. A summary without output counts as not
      done.
    - Write "not verified" when you didn't run something.
11. **Stop at the gate.** After the ledger entry, end the session. The orchestrator verifies, then merges.
    Don't start the next wave in the same session.
12. **Tests live in `tests/test_hub_*.py`,** where `pytest.ini` collects them. Never weaken an existing test to
    make it pass; report it instead.
13. **No new third-party dependencies** beyond the `hub` extra (`flask>=3.1`). No npm, no CDN.
14. **PowerShell files are ASCII-only.** Verify with the byte check (rule `ascii-only-powershell`).
15. **No lyric writing of any kind.** Standing product rule.
