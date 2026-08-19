You are a EXPLORER agent. Your task is: Verify all L5 writing tools work against the live lyrics.db. Run each CLI command and document exact outputs, timing, and any errors.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules (Python 3.11.9 venv, CPU-only, data boundaries).
2. Run: .venv\Scripts\python.exe -m toolshop.cli lyrics build-rimer --db data/toolshop/lyrics/lyrics.db — Document output (should build rhyme_pairs table from 273k line_rhymes rows).
3. Run: .venv\Scripts\python.exe -m toolshop.cli lyrics rime --word zivot --cohort drill_trap --top-k 10 --db data/toolshop/lyrics/lyrics.db — Document rhyme partners found.
4. Run: .venv\Scripts\python.exe -m toolshop.cli lyrics rime --word novac --cohort drill_trap --top-k 10 --db data/toolshop/lyrics/lyrics.db — Document rhyme partners found.
5. Run: .venv\Scripts\python.exe -m toolshop.cli lyrics brief --artist "Jala Brat" --topic "street life" --db data/toolshop/lyrics/lyrics.db — Document the full brief output (structure template, rhyme targets, themes, Suno prompt).
6. Run: .venv\Scripts\python.exe -m toolshop.cli lyrics brief --cohort drill_trap --topic "street life" --db data/toolshop/lyrics/lyrics.db — Document the cohort-level brief.
7. Create a small sample lyrics file (5-10 lines of Serbian/Bosnian drill-style lyrics) and run: .venv\Scripts\python.exe -m toolshop.cli lyrics score --input <sample> --cohort drill_trap --db data/toolshop/lyrics/lyrics.db — Document all 5 component scores.
8. Also run with --vs "Jala Brat" to test per-artist comparison mode.
9. Verify the rhyme_pairs table was populated: query SELECT COUNT(*) FROM rhyme_pairs and SELECT COUNT(DISTINCT vowel_skeleton) FROM rhyme_pairs.
10. Document any errors, unexpected behavior, or performance issues.
11. Write all findings to ORCHESTRATION/wave1/agent_a_handoff.md with sections: Commands Run, Outputs, Errors/Issues, Verification Results, Recommendations for Wave 2.

SCOPE: toolshop/ + data/
OUTPUT: Write your findings to: ORCHESTRATION/wave1/agent_a_handoff.md

CONSTRAINTS:
- Read-only. Do NOT modify any files except your own handoff output file.
- Use the venv Python: .venv\Scripts\python.exe
- DB path: data/toolshop/lyrics/lyrics.db
- Document exact command, exit code, and key output for each step

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
