# Orchestration Prompts Index

**Task**: L5 Exit + L6 Prep — Wave-Orchestrated Plan
**Project root**: `d:/Projects/Music-AI-Toolshop`
**Orchestration dir**: `ORCHESTRATION`

| Wave | Agent | Role | Name | Prompt File | Output |
|------|-------|------|------|-------------|--------|
| 1 | A | explorer | Agent A: L5 Tools Live Verification | `wave1_agentA_agent_a_l5_tools_live_verification.md` | `wave1/agent_a_handoff.md` |
| 1 | B | explorer | Agent B: German Corpus Discovery | `wave1_agentB_agent_b_german_corpus_discovery.md` | `wave1/agent_b_handoff.md` |
| 1 | C | explorer | Agent C: Flow Analyzer v1 Audit & v2 Design Prep | `wave1_agentC_agent_c_flow_analyzer_v1_audit_v2_design_prep.md` | `wave1/agent_c_handoff.md` |
| 1 | — | GATE | **Human approval required** | — | — |
| 2 | D | implementer | Agent D: Fingerprint-Based Brief Generation | `wave2_agentD_agent_d_fingerprint_based_brief_generation.md` | `wave2/agent_d_handoff.md` |
| 2 | E | implementer | Agent E: Naive Prompt Generation | `wave2_agentE_agent_e_naive_prompt_generation.md` | `wave2/agent_e_handoff.md` |
| 2 | — | GATE | **Human approval required** | — | — |
| 3 | F | implementer | Agent F: Draft Scoring & A/B Report | `wave3_agentF_agent_f_draft_scoring_a_b_report.md` | `wave3/agent_f_handoff.md` |
| 3 | — | GATE | **Human approval required** | — | — |
| 4 | G | implementer | Agent G: German Corpus Extraction | `wave4_agentG_agent_g_german_corpus_extraction.md` | `wave4/agent_g_handoff.md` |
| 4 | H | implementer | Agent H: phonemizer-de Setup & Wrapper | `wave4_agentH_agent_h_phonemizer_de_setup_wrapper.md` | `wave4/agent_h_handoff.md` |
| 4 | I | implementer | Agent I: Flow Analyzer v2 Specification | `wave4_agentI_agent_i_flow_analyzer_v2_specification.md` | `wave4/agent_i_handoff.md` |
| 4 | — | GATE | **Human approval required** | — | — |

## Wave Summary

- **Wave 1**: Discovery & Verification (3 agents, parallel + GATE)
- **Wave 2**: A/B Brief Generation (2 agents, parallel + GATE)
- **Wave 3**: Scoring & A/B Comparison (1 agents, sequential + GATE)
- **Wave 4**: L6 Prep (3 agents, parallel + GATE)
