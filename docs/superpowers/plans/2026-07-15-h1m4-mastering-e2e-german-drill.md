# H1-M4 — Mastering Tool E2E Verification (german_drill via tray EXE)

> **For agentic workers:** One milestone only. This is a VERIFICATION run, not a refactor — touch
> `mastering_tool/` code only to fix what blocks the run, minimally. It is a daily-use product.
> Parent: roadmap v2 §H1-M4; open item from handoff `2026-07-13_2020_mastering_toolshop.md`.

**Goal:** One full `german_drill` pipeline run from `mastering_tool\dist\Mastering_Toolshop.exe`
producing complete `master/` + `verification/` deliverables, closing the 2026-07-13 pending item
(stage E soft-clip fix was verified in isolation only).

### Task 1: Preflight
- [ ] `wsl -d Ubuntu bash -c "echo ok"` works; `mastering_tool\dist\Mastering_Toolshop.exe` exists.
- [ ] Pick input premaster: a WAV from `D:\MusicData\toolshop\Distro Kidea\non-mastered\`
      (list candidates, pick the first, note the choice in the handoff). **[USER DECISION]** only if
      the directory is empty — then ask which track to use.

### Task 2: End-to-end run
- [ ] Launch the EXE, run profile `german_drill` on the chosen premaster. Monitor stage progression.
- [ ] If any stage hangs/fails: capture stderr by temporarily removing `2>/dev/null` from that stage
      script (tip from 2026-07-13 handoff), diagnose, apply the MINIMAL fix, re-run. Document root cause.

### Task 3: Verify deliverables
- [ ] `master/` + `verification/` outputs exist for the track; loudness verification reports
      `[COMPLIANT]` (LUFS + true-peak vs the german_drill targets; TP ceiling −0.8 dBTP path exercised).
- [ ] Spot-listen start/middle/end of the master for gross artifacts (clipping, dropouts).

### Task 4: Close out
- [ ] Record results in `mastering_tool` docs (short E2E_VERIFICATION note) + repo CHANGELOG entry.
- [ ] If mastering_tool files changed: commit inside the submodule first, then bump the submodule
      pointer in the parent repo deliberately (see AGENTS.md).
- [ ] Handoff per template; `session_end.py`.

## Verification checklist
- [ ] Full pipeline exit 0 from the EXE; deliverables present
- [ ] `[COMPLIANT]` loudness/TP evidence quoted
- [ ] Any fix: root cause documented, minimal diff, submodule committed properly
- [ ] Handoff written

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "H1-M4: mastering german_drill e2e via tray EXE" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m4-mastering-e2e-german-drill.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-15-h1m4-mastering-e2e-german-drill.md
exactly as written. Verification run — minimal fixes only, mastering_tool is a production tool in daily use.
Submodule commits per AGENTS.md.

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m4.md
with: per-task [x] + evidence, the [COMPLIANT] verification lines quoted, root cause of any fix + diff summary,
files changed (submodule vs parent), deviations, blockers. This gets reviewed before the next milestone.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-15-h1m4-mastering-e2e-german-drill.md
```
