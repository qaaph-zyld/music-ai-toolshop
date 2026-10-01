FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "MAirina v2 wave 2 - stars and fingerprint, hint votes, device atlas, comparison finder" --files "D:/Projects/.workspace_archive/plans/mairina-v2-craft-4d7a19.md, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/devices.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/votes.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/cli.py".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. PRE-APPROVED: planned and approved by the user and the orchestrator. Skip bootstrap step 5 and implement directly. Read the plan sections 'Research synthesis' and 'Design' (fingerprint, hints, atlas, comparisons, cli rows) and the wave 1F and 1F2 handoffs MAirina_Tucc\ORCHESTRATION\mairina_v2\wave1F\F1_handoff.md and ...\wave1F2\F2_handoff.md. Wave 1 + fixes are committed (b1c066b); baseline suite = 147 passed, 0 skipped.
2. mairina/fingerprint.py - STARS: `mt star <file> <line_no> [--tag metaphor|double-meaning|wordplay|punchline|<free text>]...` stores the line text, lane, tags, timestamp and a FEATURE SNAPSHOT (syllables, end-rhyme tail length, longest multi length, consonance density, alliteration yes/no, device kinds present, word count) in data\mairina.db (new tables via CREATE TABLE IF NOT EXISTS; never drop/alter existing v1 tables). `mt stars` lists them; `mt unstar <id>`.
3. FINGERPRINT: per numeric feature, shrunk mean = (n * x̄ + k * μ_lane) / (n + k) with k = 8, where μ_lane and σ_lane come from the atlas corpus stats for the same lane; categorical features (tags, device kinds) as rates. `mt me [--lane]` prints the fingerprint with n and 'low confidence (<10 stars)' when n < 10. compare(line): the top-3 largest |z| deviations (z vs your fingerprint using σ_lane) rendered in plain words, e.g. 'shorter than your ★ lines: 6 vs 9 syllables'. `mt xray` gains an optional per-line 'vs ★' column when >= 3 stars exist.
4. mairina/hints.py - HINT VOTES: every xray hint already has a stable rule_id; `mt hint-vote <rule_id> +|-` records a vote. A rule with >= 3 down-votes and 0 up-votes is MUTED for this user: xray omits it, and `mt stats` lists muted rules. `mt hint-vote <rule_id> reset` unmutes.
5. mairina/atlas.py - DEVICE ATLAS: run devices.analyze_line over corpus lines (lines.text_raw joined to sections/songs, restricted to corpus.CORPORA = genius-pro only; use lane + target_artist) and aggregate per lane and per artist: simile rate per 100 lines, anaphora rate, alliteration rate, mean consonance density, internal-rhyme rate, multis share, code-switch rate, name-drop rate, median syllables. Build it through corpus.build_guarded (the wave 1F/1F2 writer guard) and cache with cache_dir (pickle keyed by DB path + mtime + size, like the index cache). Output STATS ONLY - never print, store or return corpus lines. `mt atlas [--lane] [--artist]` prints a compact table.
6. mairina/comparisons.py - COMPARISON FINDER: from corpus lines, collect the first content word (NOUN/ADJ/PROPN by index, not a clitic, not an artist name) after a simile marker (kao/ko/k'o/k’o/ka'o/poput, applying the same 'ko'=who exclusion as devices). Rank by lane frequency with the v1 fresh slider; votes apply (log via votes.log_shown with kind 'compare'). `mt compare [--lane] [--artist] [--theme <word>]` - theme filters to comparison words that co-occur in lines containing the theme lemma. SINGLE WORDS ONLY, never phrases or lines.
7. Tests with fixture words/lines only (no real lyrics): star -> fingerprint -> compare round trip (incl. shrinkage math and low-confidence flag); hint muting at 3 down / 0 up and reset; atlas returns only numbers/strings of stats (assert no fixture line text appears in any output); comparisons return single tokens only; ko-as-who excluded. Tests must not write the real data\ (use tmp dirs) - reuse the wave 1F data-dir guard test.
8. VERIFY (absolute paths): full pytest (-p no:cacheprovider) all pass; live: `mt atlas --lane drill` (paste the table), `mt compare --lane drill` top 10, star 3 lines of the user's verse (temp file outside repo) with tags, then `mt me` and `mt xray` showing the 'vs ★' column, then UNSTAR them and delete data\mairina.db so the user's real stats start clean; lyrics.db mtime+size equal before and after your runs (MAirina never writes it); comparisons/atlas use only corpus.CORPORA (genius-pro); git status --short (your paths only).
9. HANDOFF: files created/changed (line counts), pytest summary, the live outputs above, schema of new tables, deviations, not done. Reply exactly: 'WAVE 2 DONE - handoff at <path>' plus the pytest summary line. Do not start wave 3.
OPEN FILES: D:/Projects/.workspace_archive/plans/mairina-v2-craft-4d7a19.md, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/devices.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/votes.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/cli.py

OUTPUT: Write your handoff to: MAirina_Tucc/ORCHESTRATION/mairina_v2/wave2/D2_handoff.md

CONSTRAINTS:
- You MAY create/modify files, but ONLY under D:\Projects\Music-AI-Toolshop\MAirina_Tucc\. Never touch toolshop\, rimer-ui\, other projects, or other sessions' files.
- Product rule: FIND and ANALYZE only; NEVER write or complete lyric lines. Metaphor/double meaning/wordplay are NEVER auto-detected - only user tags on stars.
- lyrics.db opened ONLY via file:D:/Projects/Music-AI-Toolshop/data/toolshop/lyrics/lyrics.db?mode=ro&immutable=1 (uri=True). Never write to it. Atlas/compare output is statistics or single words only - no corpus lines.
- Standard library + existing toolshop only. No pip/npm installs. No git add/commit/checkout/switch/stash/reset.
- Absolute paths; foreground only; CLI never prompts; UTF-8 safe output. Tests never write the real MAirina_Tucc\data\.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
