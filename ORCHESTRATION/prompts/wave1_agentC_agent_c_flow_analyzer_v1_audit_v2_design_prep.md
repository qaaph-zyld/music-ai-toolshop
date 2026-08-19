You are a EXPLORER agent. Your task is: Audit the current flow analyzer v1, identify v2 requirements, and check whisperX/faster-whisper availability for word-level timing analysis.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules.
2. Read the full flow analyzer v1: d:\Projects\Music-AI-Toolshop\toolshop\flow_analyzer.py (283 lines) — document all current capabilities (syllable density, pattern detection, section flow profiles).
3. Read the rhyme/flow research report: d:\Projects\.windsurf\handoffs\researcher_rhyme_flow_craft_20260806.md — extract the v2-relevant findings: Kendrick tension-relaxation model, Migos triplet flow types, microtiming (laid-back vs eager), DOOM time-shifted rhyme placement.
4. Read the AI lyric improvement research: d:\Projects\.windsurf\handoffs\researcher_ai_lyric_improvement_20260806.md — check for any flow/delivery evaluation findings.
5. Read the roadmap L6 section: d:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-21-lyric-intelligence-roadmap-L3-L6.md lines 73-78 — 'Ties into the H3 flow analyzer (whisperX word timings × beat grid) so text craft meets delivery craft.'
6. Check if whisperX is installed: run .venv\Scripts\python.exe -c "import whisperx; print(whisperx.__version__)" — document result (expected: not installed, CPU-only constraint).
7. Check if faster-whisper is installed: run .venv\Scripts\python.exe -c "import faster_whisper; print('available')" — document result.
8. Check the longterm roadmap for T4 Vocal Lab v1 plans: d:\Projects\Music-AI-Toolshop\docs\superpowers\specs\2026-07-15-longterm-roadmap-v2.md lines 77-81 — faster-whisper is the planned transcription tool.
9. Document v2 architecture proposal: (1) word-level timings from faster-whisper (CPU-viable, CTranslate2 int8), (2) beat grid from T2 dossier, (3) alignment: each word's start/end time mapped to beat position, (4) microtiming analysis: deviation from grid (laid-back = positive, eager = negative), (5) tension-relaxation pacing: rhyme pacing over verse, (6) triplet flow detection: 3-against-4 rhythm patterns.
10. Identify what data is already in lyrics.db that could support v2 without whisperX: the lines table has syllable counts, the song_metrics table has BPM. What's missing?
11. Write all findings to ORCHESTRATION/wave1/agent_c_handoff.md with sections: v1 Capabilities, v2 Requirements, Available Tools (whisperX vs faster-whisper), v2 Architecture Proposal, Data Gaps, Dependencies & Risks.

SCOPE: toolshop/flow_analyzer.py + research docs
OUTPUT: Write your findings to: ORCHESTRATION/wave1/agent_c_handoff.md

CONSTRAINTS:
- Read-only. Do NOT modify any files except your own handoff output file.
- Do NOT install any packages.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
