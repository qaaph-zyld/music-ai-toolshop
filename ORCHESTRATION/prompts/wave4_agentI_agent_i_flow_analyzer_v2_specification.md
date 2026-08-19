You are a IMPLEMENTER agent. Your task is: Design the flow analyzer v2 architecture specification. Do NOT implement — spec only.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules.
2. Read the full flow analyzer v1: d:\Projects\Music-AI-Toolshop\toolshop\flow_analyzer.py (283 lines) — document all dataclasses, functions, and current limitations.
3. Read the rhyme/flow research report: d:\Projects\.windsurf\handoffs\researcher_rhyme_flow_craft_20260806.md — extract v2-relevant techniques: (1) Kendrick tension-relaxation model (faster rhyme pacing = tension, slower = relaxation), (2) Migos triplet flow (3 types: mixed, phrasal, total), (3) microtiming (laid-back vs eager as systematic deviation), (4) DOOM time-shifted rhyme placement, (5) Eminem syllable-series stacking.
4. Read the roadmap L6 section: d:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-21-lyric-intelligence-roadmap-L3-L6.md lines 73-78.
5. Read the longterm roadmap T4 section: d:\Projects\Music-AI-Toolshop\docs\superpowers\specs\2026-07-15-longterm-roadmap-v2.md lines 77-81 — faster-whisper is the planned transcription tool (CPU-viable, CTranslate2 int8).
6. Read the existing lyrics DB schema: d:\Projects\Music-AI-Toolshop\toolshop\lyricsdb.py — understand what tables exist (songs, sections, lines, song_metrics, line_rhymes, etc.) and what data is available for flow analysis.
7. Write the v2 specification to ORCHESTRATION/wave4/flow_v2_spec.md with sections:
8.   1. Overview — what v2 adds over v1 (word-level timings, beat grid alignment, microtiming, tension-relaxation, triplet detection)
9.   2. Data Requirements — what inputs are needed (faster-whisper word timings, beat grid from T2 dossier, existing syllable counts from lines table)
10.   3. Architecture — module structure, dataclasses, functions, DB schema additions (new tables/columns for word timings, beat_alignment, microtiming)
11.   4. Algorithm Specifications — (a) word-to-beat alignment, (b) microtiming deviation computation (laid-back = positive offset, eager = negative), (c) tension-relaxation pacing (rhyme density over verse timeline), (d) triplet flow detection (3-against-4 pattern in syllable timing), (e) flow pattern classification extending v1's uniform/alternating/accelerating/decelerating/free
12.   5. CPU Feasibility — all computation must be CPU-only per AGENTS.md. faster-whisper int8 is CPU-viable. Beat grid from existing T2 analysis. No GPU dependencies.
13.   6. Integration Points — how v2 connects to T2 (dossier beat grid), T4 (vocal transcription), T5 (lyrics.db), and the L5 writing tools (flow targets in briefs)
14.   7. Implementation Phases — phase 1 (word timings ingest + basic alignment), phase 2 (microtiming analysis), phase 3 (tension-relaxation + triplet detection), phase 4 (integration with brief generator)
15.   8. Test Plan — unit tests with synthetic timing data, integration tests with real audio
16. Write findings to ORCHESTRATION/wave4/agent_i_handoff.md with sections: Spec Written, Key Design Decisions, Dependencies, Implementation Phases, Risks.

SCOPE: toolshop/flow_analyzer.py + research docs
OUTPUT: Write your findings to: ORCHESTRATION/wave4/agent_i_handoff.md

CONSTRAINTS:
- Do NOT implement any code. Spec document only.
- Do NOT modify any existing source files.
- Read-only except for the spec file and handoff.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
