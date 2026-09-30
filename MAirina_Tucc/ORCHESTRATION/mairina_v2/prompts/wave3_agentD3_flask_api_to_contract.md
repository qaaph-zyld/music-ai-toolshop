FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "MAirina v2 wave 3 - local Flask API wrapping the mairina engine" --files "D:/Projects/.workspace_archive/plans/mairina-v2-craft-4d7a19.md, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/cli.py".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. PRE-APPROVED: planned and approved. Skip bootstrap step 5 and implement directly. Read the plan's 'API contract' paragraph and the wave 2 handoff MAirina_Tucc\ORCHESTRATION\mairina_v2\wave2\D2_handoff.md.
2. Create mairina/api.py (Flask, already installed in the toolshop venv - do not install anything). Run with `python -m mairina.api` and add `mt serve`; bind ONLY to 127.0.0.1, port 8000 (matches the rimer-ui Vite proxy). Load the corpus index once at startup.
3. FROZEN CONTRACT - JSON under /api/: POST anchors {scheme,lines,lane,mode,seed,fresh,artist,section}; POST rhyme {word,line?,target?,lane,fresh,artist}; POST multi {phrase,lane}; POST xray {text,lane,section?} -> per line {n,syl,target,rhyme,cons,allit,assonance,devices[],hints[{rule_id,label}],vs_star?}; POST vote {list_id,items:[[n,+1|-1]]}; POST star {text,line_no,tags[],lane}; DELETE star/<id>; GET stars; GET me?lane; GET atlas?lane&artist; GET compare?lane&artist&theme; POST hint-vote {rule_id,vote:+1|-1|0}; POST used {text}; GET stats. Every list response includes list_id, arm, items[] with a 'why' string. Errors: HTTP 4xx/5xx with {error: <message>} - never an HTML error page.
4. The API only calls existing engine functions; put any glue in api.py, do not change engine behavior. Same arm/vote logging as the CLI.
5. Tests: tests/test_api.py using Flask test_client against the fixture corpus and a tmp data dir - one test per endpoint (happy path + one error path), plus a test that the app refuses a non-localhost bind config.
6. VERIFY: full pytest (-p no:cacheprovider) passes; start `mt serve` in the foreground in a SEPARATE terminal, then curl each GET endpoint and POST xray with the user's verse from another command; stop the server; delete data\mairina.db created by the smoke test; lyrics.db mtime+size equal before and after your runs; if the engine raises CorpusNotAnnotated the API must return HTTP 503 {error} with that message (add a test); git status --short (your paths only).
7. HANDOFF: endpoints table (method, path, request, response sample), pytest summary, curl outputs, deviations. Reply exactly: 'WAVE 3 API DONE - handoff at <path>' plus the pytest summary line.
OPEN FILES: D:/Projects/.workspace_archive/plans/mairina-v2-craft-4d7a19.md, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/cli.py

OUTPUT: Write your handoff to: MAirina_Tucc/ORCHESTRATION/mairina_v2/wave3/D3_handoff.md

CONSTRAINTS:
- You MAY create/modify files ONLY under D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mairina\ and MAirina_Tucc\tests\ (plus your handoff). Do NOT touch rimer-ui\ (another agent owns it this wave).
- Bind to 127.0.0.1 only. No auth needed (local single user). No pip installs - Flask is already present.
- lyrics.db read-only via the immutable URI. No git add/commit/checkout/switch/stash/reset.
- Product rule: FIND and ANALYZE only; never write lyric lines. Absolute paths; foreground only.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
