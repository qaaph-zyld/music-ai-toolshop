# Handoff: Music Toolshop v2 — Research Synthesis & Unified Implementation Plan

**Date**: 2026-08-08 20:36
**Project**: `Music_Toolshop_v2`
**Previous Handoff**: None
**Session Record**: `memory/episodic/sessions/2026-08-08_203600_music_toolshop_v2_research_synthesis.md`

---

## Session Summary
Synthesized 5 completed research reports (3,396 lines total) into a unified implementation plan for the Music Toolshop v2 project. The 5 reports covered:

1. **Golden Reference Spectral Curves** (342 lines) — Genre-specific mastering targets from TrackSensei 563-track corpus, Matchering 2025 multi-reference workflow, statistical aggregation methods
2. **Agentic AI for Genre Decisions** (998 lines) — Three-layer closed-loop architecture (Phantom MCP + REAPER MCP + LLM), measurable proxies for subjective qualities (Tech House bass bounce, Drill 808 weight, Hip-Hop vocal presence), convergence criteria
3. **LoRA Fine-Tuning Pipeline** (529 lines + code) — 2-stage curriculum (clean → mastered), MSST YAML config, RTX 3090 feasibility (10–14GB VRAM), loss function combination, data requirements (50–200 tracks), implementation at `ai_modules/lora_finetuning/`
4. **Real-Time Edge Deployment** (588 lines) — ONNX/TensorRT conversion steps, hardware tier benchmarks, WSA + TensorRT blocked (FlexAttention ONNX export not ready), torch.compile fallback (Option B)
5. **Advanced Evaluation Metrics** (939 lines) — Fullness/Bleedless, LogWMSE, MMSNR, Zimtohrli, FAD-CLAP implementations, genre-specific evaluation weights, metric comparison matrix, module structure

The synthesis document was written to `.windsurf/handoffs/orchestrator_synthesis_music_toolshop_v2_20260806.md` (559 lines) with 10 sections: Executive Summary, Genre-Specific Profiles, System Architecture, Training Pipeline, Deployment Pipeline, Evaluation Framework, Implementation Roadmap, Open Questions, Source Index, Next Actions.

Research bootstrap prompts file updated with completion status for all 5 prompts.

Both repos pushed to GitHub:
- Parent repo (`music-ai-toolshop`): commit `5dd96ac`
- Music Toolshop v2 repo: commit `d6d7e33`

---

### Changes
- `.windsurf/handoffs/orchestrator_synthesis_music_toolshop_v2_20260806.md` — NEW: 559-line synthesis document consolidating all 5 research reports`
- `Music_Toolshop_v2/research_bootstrap_prompts.md` — MODIFIED: Added research status table with completion markers for all 5 prompts`

### Verification
- Synthesis document written and committed: `git log --oneline -1` → `5dd96ac` (parent repo)
- Research prompts status updated and committed: `git log --oneline -1` → `d6d7e33` (Music Toolshop v2 repo)
- Both repos pushed to GitHub successfully:
  - Parent: `8ded2de..5dd96ac main -> main`
  - Music Toolshop v2: `2a0c782..d6d7e33 main -> main`
- All 5 research reports confirmed complete with handoff files verified

---

---

## Key Files

| File | Role |
|------|------|
| `.windsurf/handoffs/orchestrator_synthesis_music_toolshop_v2_20260806.md` — NEW: 559-line synthesis document consolidating all 5 research reports` | Modified during session |
| `Music_Toolshop_v2/research_bootstrap_prompts.md` — MODIFIED: Added research status table with completion markers for all 5 prompts` | Modified during session |

---

## Known Issues
1. None

---

## Remaining Work
- Source genre stems, build Golden Reference curves, create genre profiles, begin LoRA training, build evaluation module, deploy agentic system

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v12.0) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run `python scripts/session.py brief "<task>" --files "<open files>"`.
5. Read the brief. Load ONLY the KBs it names. Note the "Do NOT load" list.
   Skills auto-activate natively — do not preload.
6. For large tasks, use `/orchestrate` or dispatch a subagent:
   `python scripts/dispatch_subagent.py <role> --task "..." --scope "..." --execute`
7. Draft a plan. Do NOT start coding until the plan is approved.
8. After completion: `python scripts/session.py end --status completed --duration <min> --helpful <skill>`.
WAIT FOR MY TASK.

MY TASK: Continue from handoff — devise a plan based on .windsurf/handoffs/2026-08-08_203600_music_toolshop_v2_research_synthesis.md
OPEN FILES: .windsurf/handoffs/2026-08-08_203600_music_toolshop_v2_research_synthesis.md
```
