---
description: Multi-agent chain with parallel web research — for greenfield projects or tasks that need external investigation before planning.
---

# /orchestrate_with_research — Research-First Multi-Agent Chain

Use this for greenfield projects, competitive analysis, or any task that needs
**external research before planning**. The chain runs parallel web-research
agents, then transitions into the standard orchestrate pipeline.

## Trigger

- Greenfield project (no existing codebase to explore)
- User asks to "research what's out there" before building
- Task needs competitive landscape, technology evaluation, or dataset survey
- User wants parallel research agents with copy-paste bootstrap prompts

## Chain

### Phase 1: Research (Parallel)

The orchestrator identifies N independent research topics and generates a
**copy-paste bootstrap prompt** for each. The user opens N new Cascade threads
and pastes each prompt. Each agent runs the `researcher` role, does web
research, and writes a handoff file.

**Orchestrator responsibilities:**
1. Analyze the user's task and break it into independent research topics
2. Generate a bootstrap prompt for each topic (see template below)
3. Present all prompts to the user in one message
4. Wait for the user to return with handoff file paths

**Research agent responsibilities (in separate threads):**
1. Load the `researcher` SKILL.md
2. Read the task and scope from the bootstrap prompt
3. Use `search_web` + `read_url_content` to investigate
4. Write a structured research report to `.windsurf/handoffs/researcher_<topic>_<stamp>.md`
5. Return the file path + 1-2 sentence summary

### Phase 2: Synthesis (Orchestrator)

The orchestrator reads all research handoffs and:
1. Summarizes key findings across all reports
2. Identifies gaps (topics that need deeper investigation)
3. Decides: dispatch more research agents OR transition to planning
4. If more research is needed, generate new bootstrap prompts (back to Phase 1)

### Phase 3: Plan (Planner)

Consumes synthesized research and drafts an implementation plan.

- No code edits.
- Output: `.windsurf/plans/<plan>.md` with frozen steps + verification criteria.

### [HUMAN APPROVAL GATE]

Do not proceed until the user approves the plan.

### Phase 4: Implement (Implementer)

Executes the approved plan with surgical edits.

- Only touches approved files.
- One concern per edit.
- Keeps tests green after each step.

### Phase 5: Review (Reviewer)

Reads the diff + test evidence and emits blockers + nits.

- No writes except review output.
- If blockers exist, return to implementer; do not claim done.

## Bootstrap Prompt Template

The orchestrator fills in the template for each research topic and presents
it as a copy-paste block for the user:

```text
RESEARCH AGENT — Paste this into a new Cascade thread:

1. Load the researcher skill:
   Read d:\Project\ai_dev_meta_layer\.windsurf\skills\researcher\SKILL.md

2. Your research task:
   TOPIC: {topic}
   QUESTION: {research_question}
   SCOPE: {what_to_include, what_to_exclude}

3. Use search_web and read_url_content to investigate.
   Cite every finding with a URL and access date.

4. Write your report to:
   d:\Project\.windsurf\handoffs\researcher_{topic_slug}_{stamp}.md

5. Return ONLY the file path and a 1-2 sentence summary.
   Do NOT make implementation decisions. Report findings, not conclusions.

6. When done, tell the user to bring the handoff file path back to the
   orchestrator thread.
```

## Commands

```bash
# Phase 1: Generate bootstrap prompts (optional helper)
python d:\Project\ai_dev_meta_layer\scripts\gen_research_prompts.py --config research_topics.json

# Phase 1: Dispatch researcher handoff packet (optional, for file-based dispatch)
python d:\Project\ai_dev_meta_layer\scripts\dispatch_subagent.py researcher \
    --task "describe research task" \
    --output "handoffs/researcher_topic_20260802_200000.md"

# Phase 3: Planner (reads synthesized research)
python d:\Project\ai_dev_meta_layer\scripts\dispatch_subagent.py planner \
    --task "describe task" --scope "files/areas" --execute

# Phase 4: Implementer
python d:\Project\ai_dev_meta_layer\scripts\dispatch_subagent.py implementer \
    --task "approved plan" --scope "files/areas" --execute

# Phase 5: Reviewer
python d:\Project\ai_dev_meta_layer\scripts\dispatch_subagent.py reviewer \
    --task "review the change" --scope "files/areas" --execute
```

## Governance

- The researcher role must NOT grep local files — that's the explorer role.
- The orchestrator must verify URLs in research handoffs are accessible before relying on findings.
- The implementer role must refuse to write until a plan file exists and is approved.
- The reviewer output must include:
  - **Blockers**: anything that prevents shipping.
  - **Nits**: style/simplification suggestions.
  - **Verdict**: `approved` or `needs-fix`.
- No role may skip the approval gate. A chain without an approved plan is invalid.

## Artifacts

- `handoffs/researcher_*.md` — research reports from parallel agents
- `handoffs/orchestrator_synthesis_<task>_<stamp>.md` — synthesis of all research
- `.windsurf/plans/*.md` — implementation plan
- Review output (captured in utilization log or handoff)

## Relationship to /orchestrate

| Aspect | /orchestrate | /orchestrate_with_research |
|--------|-------------|---------------------------|
| **Exploration** | Local codebase grep (explorer) | Web research (researcher) + optional local grep |
| **Parallelism** | Sequential | Phase 1 is parallel (user opens N threads) |
| **Greenfield** | No (assumes codebase) | Yes (no codebase needed) |
| **Bootstrap prompts** | No | Yes (copy-paste for manual thread spawning) |
| **Phases 3-5** | Same | Same (planner → gate → implementer → reviewer) |

For codebase-internal tasks, use `/orchestrate`. For greenfield or
research-heavy tasks, use `/orchestrate_with_research`.

## Related

- `scripts/dispatch_subagent.py`
- `scripts/gen_research_prompts.py`
- `.windsurf/skills/researcher/SKILL.md`
- `.windsurf/skills/explorer/SKILL.md`
- `.windsurf/skills/planner/SKILL.md`
- `.windsurf/skills/implementer/SKILL.md`
- `.windsurf/skills/reviewer/SKILL.md`
