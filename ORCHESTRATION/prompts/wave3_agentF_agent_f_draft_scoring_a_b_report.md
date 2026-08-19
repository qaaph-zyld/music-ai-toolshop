You are a IMPLEMENTER agent. Your task is: Score both draft lyrics files (fingerprint-based and naive) with the 5-component draft scorer and produce the A/B comparison report. This is the L5 exit criterion deliverable.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules.
2. Score the fingerprint draft: .venv\Scripts\python.exe -m toolshop.cli lyrics score --input ORCHESTRATION/wave2/draft_fingerprint.txt --cohort drill_trap --db data/toolshop/lyrics/lyrics.db --json — save JSON output to ORCHESTRATION/wave3/scores_fingerprint.json
3. Score the naive draft: .venv\Scripts\python.exe -m toolshop.cli lyrics score --input ORCHESTRATION/wave2/draft_naive.txt --cohort drill_trap --db data/toolshop/lyrics/lyrics.db --json — save JSON output to ORCHESTRATION/wave3/scores_naive.json
4. Also score both with per-artist comparison: add --vs "Jala Brat" to both commands. Save to ORCHESTRATION/wave3/scores_fingerprint_vs_jala.json and ORCHESTRATION/wave3/scores_naive_vs_jala.json
5. Run additional craft module checks on both drafts for richer comparison:
6.   - .venv\Scripts\python.exe -m toolshop.cli lyrics clean-tokens --input <draft> --json (Suno token contamination)
7.   - .venv\Scripts\python.exe -m toolshop.cli lyrics cliches --input <draft> --include-balkan --json (cliche density)
8.   - .venv\Scripts\python.exe -m toolshop.cli lyrics check-scheme --input <draft> --db data/toolshop/lyrics/lyrics.db --json (rhyme scheme)
9.   - .venv\Scripts\python.exe -m toolshop.cli lyrics theme-match --input <draft> --cohort drill_trap --db data/toolshop/lyrics/lyrics.db --json (theme distribution)
10. Produce the A/B comparison report at ORCHESTRATION/wave3/ab_comparison_report.md with sections:
11.   1. Executive Summary — which draft scored higher, by how much, on which components
12.   2. Side-by-Side 5-Component Scores table (structural, rhyme, lexical, repetition, originality, overall)
13.   3. Per-Artist Comparison (vs Jala Brat) — how close each draft is to Jala's fingerprint
14.   4. Craft Module Analysis — cliche density, token contamination, scheme adherence, theme match
15.   5. Qualitative Analysis — where the fingerprint brief helped vs where it didn't
16.   6. L5 Exit Criterion Evaluation — does the fingerprint draft score >= naive on >=3 of 5 components?
17.   7. Recommendations — what to improve for the next iteration
18. Write findings to ORCHESTRATION/wave3/agent_f_handoff.md with sections: Scores Computed, A/B Verdict, L5 Exit Status.

SCOPE: toolshop/ + data/ + ORCHESTRATION/wave2/ + ORCHESTRATION/wave3/
OUTPUT: Write your findings to: ORCHESTRATION/wave3/agent_f_handoff.md

CONSTRAINTS:
- Use the venv Python: .venv\Scripts\python.exe
- DB path: data/toolshop/lyrics/lyrics.db
- Do NOT modify any source files. Only create output files in ORCHESTRATION/wave3/.
- Both draft files must exist at ORCHESTRATION/wave2/draft_fingerprint.txt and ORCHESTRATION/wave2/draft_naive.txt before starting.
- If either draft file is missing, document the gap and score whichever is available.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
