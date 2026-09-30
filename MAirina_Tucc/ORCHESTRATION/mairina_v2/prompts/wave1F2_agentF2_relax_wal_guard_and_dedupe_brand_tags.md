FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "MAirina v2 wave 1F2 - relax the lyrics.db WAL guard to non-empty WAL only, dedupe brand tags" --files "D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/corpus.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/devices.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/tests/test_live_smoke.py".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. PRE-APPROVED small fix. Skip bootstrap step 5. Context: the orchestrator verified wave 1F on real data - everything passes EXCEPT that the guard in corpus.py build_guarded (~lines 62-80) refuses whenever lyrics.db-wal merely EXISTS. That was the orchestrator's spec error: in WAL mode SQLite leaves a 0-byte -wal/-shm whenever a reader has connected (right now a stale 0-byte lyrics.db-wal from 01:18 exists, no writer process running), so `mt` is unusable and the 2 live smoke tests fail with exit 2.
2. FIX 1 (corpus.py): refuse only if lyrics.db-journal exists OR lyrics.db-wal exists with size > 0. A 0-byte -wal (and any -shm) is NOT a writer signal. Keep the existing mtime+size before/after stability check and single retry unchanged. Update the error text accordingly. Tests: (a) fixture db + 0-byte '-wal' + '-shm' files -> builds fine; (b) '-wal' with >0 bytes -> DbUnavailable 'being written'; (c) '-journal' present -> DbUnavailable. Do NOT create, modify or delete any sidecar next to the REAL lyrics.db - only in tmp fixture dirs.
3. FIX 2 (devices.py): a token tagged name_drop must not also be tagged code_switch (e.g. 'Gucci na meni, BMW ispred kuće' currently yields both code_switch(gucci) and name_drop(gucci)). name_drop wins. Test it.
4. VERIFY (absolute paths): "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q -p no:cacheprovider -> ALL pass, 0 skipped (the live smoke tests must now run and pass against the real lyrics.db, which is annotated: 501,386 genius-pro tokens). Then `mt rhyme imaš --lane drill` (snimaš in top 10) and `mt anchors --scheme AABB --lane drill` via MAirina_Tucc\mt.ps1; afterwards delete MAirina_Tucc\data\mairina.db and any NEW index_*/targets_* cache files your runs created, but NEVER delete index_3a770ed6.pre-rebuild-20260930.pkl. Record lyrics.db mtime+size before/after (must be equal). List MAirina_Tucc\data\ before/after.
5. HANDOFF: the diff summary (file:line), pytest summary line (must show 0 skipped), the two live outputs, data\ listing before/after, lyrics.db mtime+size before/after, git status --short for MAirina_Tucc. Reply exactly: 'WAVE 1F2 DONE - handoff at <path>' plus the pytest summary line.
OPEN FILES: D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/corpus.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/devices.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/tests/test_live_smoke.py

OUTPUT: Write your handoff to: MAirina_Tucc/ORCHESTRATION/mairina_v2/wave1F2/F2_handoff.md

CONSTRAINTS:
- You MAY modify files ONLY under D:\Projects\Music-AI-Toolshop\MAirina_Tucc\ (mairina\corpus.py, mairina\devices.py, tests\, and your handoff).
- Never create, modify or delete lyrics.db or its -wal/-shm/-journal sidecars. lyrics.db opened only via the immutable read-only URI.
- No pip/npm installs. No git add/commit/checkout/switch/stash/reset. Absolute paths; foreground only; CLI never prompts.

CONTEXT BUDGET: 80k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
