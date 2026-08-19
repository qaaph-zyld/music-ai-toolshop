You are a IMPLEMENTER agent. Your task is: Create a naive/generic Suno prompt for the same target (Jala Brat drill trap, street life theme) — no corpus data, just generic instructions. Document what the naive prompt lacks vs the fingerprint brief.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Create a naive Suno prompt for a drill trap song in Serbian/Bosnian about street life. Write it to ORCHESTRATION/wave2/suno_prompt_naive.txt. The prompt should include: genre (drill trap), language (Serbian/Bosnian), topic (street life), BPM (around 120-140), mood (dark, aggressive), and generic structure (verse-chorus-verse-chorus). Do NOT include: specific rhyme targets, corpus-attested rhyme pairs, theme distribution data, slang density targets, TTR targets, or structure templates from the corpus.
2. Create a document comparing what the naive prompt lacks vs what a fingerprint-based prompt would contain. Write to ORCHESTRATION/wave2/naive_vs_fingerprint_gap.md with sections: What the Naive Prompt Has, What It Lacks (structure template, rhyme targets, theme distribution, slang density, TTR target, repetition pattern, Suno style hints), Expected Impact on Output Quality.
3. Write findings to ORCHESTRATION/wave2/agent_e_handoff.md with sections: Naive Prompt Created, Gap Analysis, Expected Quality Difference.

SCOPE: ORCHESTRATION/wave2/
OUTPUT: Write your findings to: ORCHESTRATION/wave2/agent_e_handoff.md

CONSTRAINTS:
- Do NOT use any toolshop CLI commands or corpus data.
- Do NOT modify any source files. Only create output files in ORCHESTRATION/wave2/.
- The naive prompt should be what a user would write WITHOUT the toolshop — just generic Suno instructions.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
