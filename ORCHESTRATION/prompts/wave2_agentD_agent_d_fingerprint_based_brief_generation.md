You are a IMPLEMENTER agent. Your task is: Generate a corpus-informed Suno brief for Jala Brat (drill_trap) using the L5 writing tools. This is the 'fingerprint' side of the A/B comparison.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules.
2. Ensure rimer DB is built: .venv\Scripts\python.exe -m toolshop.cli lyrics build-rimer --db data/toolshop/lyrics/lyrics.db
3. Generate the brief: .venv\Scripts\python.exe -m toolshop.cli lyrics brief --artist "Jala Brat" --topic "street life" --db data/toolshop/lyrics/lyrics.db --output ORCHESTRATION/wave2/brief_fingerprint.md
4. Also generate the Suno prompt format: run with --json and extract the Suno prompt, or use the format_suno_prompt() function. Save to ORCHESTRATION/wave2/suno_prompt_fingerprint.txt
5. Query 5 key rhyme words and document their attested partners: .venv\Scripts\python.exe -m toolshop.cli lyrics rime --word zivot --cohort drill_trap --db data/toolshop/lyrics/lyrics.db --json
6. Repeat for: novac, brat, grad, problem — save all results.
7. Also run the structure template: .venv\Scripts\python.exe -m toolshop.cli lyrics template --cohort drill_trap --db data/toolshop/lyrics/lyrics.db --json — save to ORCHESTRATION/wave2/structure_template.json
8. Document what the fingerprint brief contains: structure template (section types, counts), rhyme scheme targets, theme distribution, slang density target, TTR target, repetition pattern, Suno style hints.
9. Write findings to ORCHESTRATION/wave2/agent_d_handoff.md with sections: Brief Generated, Suno Prompt, Rhyme Partners Found, Structure Template, Craft Targets Summary.

SCOPE: toolshop/ + data/ + ORCHESTRATION/wave2/
OUTPUT: Write your findings to: ORCHESTRATION/wave2/agent_d_handoff.md

CONSTRAINTS:
- Use the venv Python: .venv\Scripts\python.exe
- DB path: data/toolshop/lyrics/lyrics.db
- Do NOT modify any source files. Only create output files in ORCHESTRATION/wave2/.
- If build-rimer has not been run yet, run it first.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
