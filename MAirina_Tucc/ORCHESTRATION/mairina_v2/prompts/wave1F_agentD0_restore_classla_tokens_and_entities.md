FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "MAirina v2 wave 1F D0 - restore lyrics.db tokens and entities via toolshop lyrics annotate" --files "D:/Projects/Music-AI-Toolshop/toolshop/annotate.py, D:/Projects/Music-AI-Toolshop/toolshop/cli.py, D:/Projects/Music-AI-Toolshop/handoffs/orchestration_ledger_lyrics_sources_20260929.md".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. PRE-APPROVED operational task. Skip bootstrap step 5. You change NO code in this task - you only run the existing annotation pipeline and report.
2. Why: the lyrics-sources rebuild of D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db left tokens = 0 and entities = 0 (CLASSLA lemma/POS/NER layer). MAirina's vocabulary, anchors, rhymes, multis, gazetteer, atlas and comparisons all depend on them. The pipeline that fills them is toolshop/annotate.py (classla.Pipeline('sr', type='nonstandard')), exposed as `toolshop lyrics annotate [--db PATH] [--resume] [--limit N] [--fresh]`; it is RESUMABLE (skips lines already in tokens). CLASSLA and the 'sr' models are installed in the toolshop venv.
3. Step 1 - baseline (read-only): record lyrics.db size/mtime, counts of songs, lines, tokens, entities, and lines per corpus. Confirm no other process is writing lyrics.db right now (no lyrics.db-wal / -journal; ask the user if any other lyrics-sources job is running and WAIT for the answer).
4. Step 2 - timing probe: run `& "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -m toolshop.cli lyrics annotate --db "D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db" --resume --limit 300` (adjust the module entry if the CLI is invoked differently - check toolshop/cli.py and pyproject.toml; use the documented entry point). Measure seconds per line; extrapolate total runtime for all remaining lines; TELL THE USER the estimate before continuing.
5. Step 3 - full run: run the same command without --limit in its OWN terminal (it is long-running, CPU only). It is resumable: if interrupted, rerun with --resume. Never use --fresh (it wipes tokens/entities).
6. Step 4 - verify: tokens > 0 for every genius-pro line with text (report annotated/total per corpus), entities > 0, spot-check 5 tokens rows (form, lemma, upos) from genius-pro lines, e.g. forms 'snimaš', 'imaš', 'lava'. Record final lyrics.db mtime.
7. HANDOFF: baseline counts, timing probe numbers, total runtime, final coverage per corpus, spot-check rows, any errors. Reply exactly: 'WAVE 1F D0 DONE - handoff at <path>' and tell the F1 agent/user that live checks may now run.
OPEN FILES: D:/Projects/Music-AI-Toolshop/toolshop/annotate.py, D:/Projects/Music-AI-Toolshop/toolshop/cli.py, D:/Projects/Music-AI-Toolshop/handoffs/orchestration_ledger_lyrics_sources_20260929.md

OUTPUT: Write your handoff to: MAirina_Tucc/ORCHESTRATION/mairina_v2/wave1F/D0_handoff.md

CONSTRAINTS:
- Do NOT modify any code or any file other than lyrics.db (via the annotate command) and your handoff file.
- Never run annotate with --fresh; never delete lyrics.db or its tables; never run build_database / ingest commands.
- Do not touch MAirina_Tucc\data\index_3a770ed6.pre-rebuild-20260930.pkl (backup).
- No git add/commit/checkout/switch/stash/reset. Absolute paths. Long run in its own terminal; do not end your turn claiming done while it is still running - report progress instead.

CONTEXT BUDGET: 120k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
