# Orchestration Prompts Index

**Task**: Plugin-Arsenal-FX Wave 2 — Ableton bridge (full F) + session->chain (B) + DawDreamer eval/integration (E)
**Project root**: `d:/Projects/Music-AI-Toolshop`
**Orchestration dir**: `ORCHESTRATION`

| Wave | Agent | Role | Name | Prompt File | Output |
|------|-------|------|------|-------------|--------|
| 1 | A | implementer | Agent A: Live bridge parity fix + install + verify | `wave1_agentA_agent_a_live_bridge_parity_fix_install_verify.md` | `fx_wave2/wave1/agent_a_handoff.md` |
| 1 | B | implementer | Agent B: DawDreamer eval spike | `wave1_agentB_agent_b_dawdreamer_eval_spike.md` | `fx_wave2/wave1/agent_b_handoff.md` |
| 1 | — | GATE | **Human approval required** | — | — |
| 2 | C | implementer | Agent C: daw export-chain (Live session -> fx YAML) | `wave2_agentC_agent_c_daw_export_chain_live_session_fx_yaml.md` | `fx_wave2/wave2/agent_c_handoff.md` |
| 2 | D | implementer | Agent D: loopback capture module | `wave2_agentD_agent_d_loopback_capture_module.md` | `fx_wave2/wave2/agent_d_handoff.md` |
| 2 | E | implementer | Agent E (optional): lazy-probe persistence | `wave2_agentE_agent_e_optional_lazy_probe_persistence.md` | `fx_wave2/wave2/agent_e_handoff.md` |
| 2 | — | GATE | **Human approval required** | — | — |
| 3 | F | implementer | Agent F: DawDreamer engine backend | `wave3_agentF_agent_f_dawdreamer_engine_backend.md` | `fx_wave2/wave3/agent_f_handoff.md` |
| 3 | — | GATE | **Human approval required** | — | — |
| 4 | G | implementer | Agent G: capture->measure->adjust + wave closeout | `wave4_agentG_agent_g_capture_measure_adjust_wave_closeout.md` | `fx_wave2/wave4/agent_g_handoff.md` |
| 4 | — | GATE | **Human approval required** | — | — |

## Wave Summary

- **Wave 1**: Bridge install + DawDreamer eval spike (2 agents, parallel + GATE)
- **Wave 2**: Extraction + loopback capture (3 agents, parallel + GATE)
- **Wave 3**: DawDreamer engine integration (gated on adopt verdict) (1 agents, sequential + GATE)
- **Wave 4**: Measure->adjust loop + closeout (1 agents, sequential + GATE)
