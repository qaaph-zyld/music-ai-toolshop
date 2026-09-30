# Orchestration Prompts Index

**Task**: MAirina Tucc v2 - line craft beyond rhyme (Devin executes, Claude verifies each gate)
**Project root**: `D:/Projects/Music-AI-Toolshop`
**Orchestration dir**: `MAirina_Tucc/ORCHESTRATION/mairina_v2`

| Wave | Agent | Role | Name | Prompt File | Output |
|------|-------|------|------|-------------|--------|
| 1F | D0 | implementer | Restore CLASSLA tokens and entities | `wave1F_agentD0_restore_classla_tokens_and_entities.md` | `wave1F/D0_handoff.md` |
| 1F | F1 | implementer | Fix W1 craft engine findings | `wave1F_agentF1_fix_w1_craft_engine_findings.md` | `wave1F/F1_handoff.md` |
| 1F | — | GATE | **Human approval required** | — | — |
| 1F2 | F2 | implementer | Relax WAL guard and dedupe brand tags | `wave1F2_agentF2_relax_wal_guard_and_dedupe_brand_tags.md` | `wave1F2/F2_handoff.md` |
| 1F2 | — | GATE | **Human approval required** | — | — |
| 2 | D2 | implementer | Stars fingerprint hints atlas compare | `wave2_agentD2_stars_fingerprint_hints_atlas_compare.md` | `wave2/D2_handoff.md` |
| 2 | — | GATE | **Human approval required** | — | — |
| 3 | D3 | implementer | Flask API to contract | `wave3_agentD3_flask_api_to_contract.md` | `wave3/D3_handoff.md` |
| 3 | D4 | implementer | rimer-ui songwriting screen | `wave3_agentD4_rimer_ui_songwriting_screen.md` | `wave3/D4_handoff.md` |
| 3 | — | GATE | **Human approval required** | — | — |

## Wave Summary

- **Wave 1F**: Restore corpus annotation (D0) + W1 fixes (F1), parallel; F1 live checks wait for D0 (2 agents, parallel + GATE)
- **Wave 1F2**: WAL-guard correction (orchestrator spec error) + brand double-tag (1 agents, sequential + GATE)
- **Wave 2**: Learning and reference (1 agents, sequential + GATE)
- **Wave 3**: API and UI (parallel, frozen contract) (2 agents, parallel + GATE)
