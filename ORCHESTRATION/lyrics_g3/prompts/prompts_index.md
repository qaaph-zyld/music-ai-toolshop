# Subagent Dispatch Index

**Task**: Lyrics G3 — Genius roster expansion: post-fetch ingest + verification waves
**Orchestrator model**: SWE-2 Max
**Subagent model**: swe-2-max (default)

| Wave | Agent | Profile | Model | Background | Output |
|------|-------|---------|-------|------------|--------|
| 1 | 1a | `wave-explorer` | swe-2-max | False | `wave1/g3_fetch_audit_handoff.md` |
| 1 | — | GATE | **Human approval required** | — | — |
| 2 | 2a | `wave-implementer` | swe-2-max | False | `wave2/g3_db_ingest_handoff.md` |
| 2 | — | GATE | **Human approval required** | — | — |
| 3 | 3a | `reviewer` | swe-2-max | False | `wave3/g3_verify_handoff.md` |
