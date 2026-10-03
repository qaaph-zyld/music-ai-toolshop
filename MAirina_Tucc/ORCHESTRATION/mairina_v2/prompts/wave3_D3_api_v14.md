FRAMEWORK BOOTSTRAP (v14.1) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool with task + open files, or run:
   `python scripts/session.py brief "<task>" --files "<open files or omit>"`
5. Read the brief. Load ONLY the KBs it names. Note the "Do NOT load" list.
   The brief may surface `domain_topic` wiki articles (compiled domain
   knowledge) — treat them as citable facts. Skills auto-activate natively —
   do not preload.
6. For large tasks, use `/orchestrate` or dispatch a subagent:
   `python scripts/dispatch_subagent.py <role> --task "..." --scope "..." --execute`
7. Draft a plan. Do NOT start coding until the plan is approved.
8. After completion, run `python scripts/session.py end --status completed --duration <min> --helpful <skill>`.
WAIT FOR MY TASK.

MY TASK: MAirina v2 wave 3 D3 — local Flask API over the MAirina engine. PRE-APPROVED by the user and the Claude orchestrator (skip step 7 plan approval; implement). Plans: D:\Projects\.workspace_archive\plans\mairina-v2-api-ui-15383c.md (sections "Frozen HTTP contract", "D3 — Flask API", "Acceptance criteria" 2–4, and the final "Reassessment" addendum, which wins on conflicts) and D:\Projects\.workspace_archive\plans\mairina-v2-craft-4d7a19.md. Baseline: MAirina waves 1–2R committed (b1c066b, b33f0fd, 75362fa, 4d227b1; docs 46155b0, CHANGELOG #077); suite 220 passed, 0 skipped. Note from 2R: stars default to lane 'all' and count in every lane view; hint-vote accepts only known rule ids (rules.py); vs★ phrases quote the raw star mean + (n=…). The React UI (rimer-ui) is being built IN PARALLEL by the Claude session — do NOT touch rimer-ui\.

BUILD (D:\Projects\Music-AI-Toolshop\MAirina_Tucc\ only):
1. mairina/api.py — Flask (already installed in the toolshop venv; install nothing). App factory `create_app(lyrics_db=None, data_dir=None)`; load the corpus index once at startup; if corpus init fails (DbUnavailable / CorpusNotAnnotated) the app still starts and corpus routes return HTTP 503 `{error}`. Bind ONLY 127.0.0.1:8000; refuse any other host (raise before serving). No CORS (Vite proxies /api same-origin). JSON errors everywhere (4xx validation, 404 unknown ids, 503 corpus, generic 500 without internals/tracebacks); register handlers so Flask never returns HTML.
2. The 14 endpoints of the frozen contract: POST anchors {scheme,lines,lane,mode,seed,fresh,artist,section}; POST rhyme {word,line?,target?,lane,fresh,artist}; POST multi {phrase,lane}; POST xray {text,lane,section?} → per line {n,syl,target,rhyme,cons,allit,assonance,devices[],hints[{rule_id,label}],vs_star?}; POST vote {list_id,items:[[n,+1|-1]]}; POST star {text,line_no,tags[],lane,draft_id?}; DELETE star/<id>; GET stars; GET me?lane; GET atlas?lane&artist; GET compare?lane&artist&theme; POST hint-vote {rule_id,vote:+1|-1|0}; POST used {text,draft_id?}; GET stats. List responses: {list_id, arm, items:[{... , why}]}. Atlas/compare: statistics / single words only — never corpus lines.
2b. EXACT RESPONSE/REQUEST SHAPES (shared with the UI — must match field-for-field): READ (do not edit) D:\Projects\Music-AI-Toolshop\MAirina_Tucc\rimer-ui\src\types.ts (every response interface: AnchorsResponse, RhymeResponse, MultiResponse, CompareResponse, XrayResponse/XrayLine/TargetRange/DeviceTag/HintTag, Star/StarsResponse, MeResponse/FingerprintFeature, AtlasResponse/AtlasRow, HintVoteResponse, UsedResponse, StatsResponse/ArmStats, ApiErrorBody) and D:\Projects\Music-AI-Toolshop\MAirina_Tucc\rimer-ui\src\api.ts (exact request bodies and query params; optional fields arrive as null). Notes: anchors response carries `target` (TargetRange|null) once, not per item; xray `cons` is the 0..3 gauge level and `cons_density` the raw value; TargetRange.approx = the n<30 fallback marker; stats.ab is a human string (e.g. "not enough data (12/100)"). Add a contract test per endpoint asserting the exact key sets. If a shape is impossible to produce from the engine, keep the key and return null, and list it under deviations.
3. Engine helpers (share logic with existing CLI paths; CLI behavior must stay identical): text-first star/used helpers in fingerprint.py and used.py (no temp lyric files; optional opaque `draft_id` — never used as a path); votes.cast_votes optional list_id (omitted = latest list, as today; supplied = vote that exact list atomically; unknown/stale list_id → JSON 4xx); hint-vote 0 → hints.reset.
4. cli.py: `mt serve [--data-dir PATH]` (default MAirina_Tucc\data) runs the app on 127.0.0.1:8000.
5. tests/test_api.py with Flask test_client on the fixture corpus + tmp_path data dir: every endpoint happy path + one error path; malformed JSON; oversized text (define a sane max, e.g. 20k chars → 413/400 JSON); injection-shaped strings in query fields; stale list_id; hint reset via 0; draft_id stable/idempotent; CorpusNotAnnotated → 503; non-localhost bind refused; no HTML error bodies; tests never write the real MAirina_Tucc\data\ (reuse the data-dir guard pattern).

HARD RULES: only MAirina_Tucc\ (mairina\, tests\, your handoff); never rimer-ui\, toolshop\, other sessions' files, the ACTIVE marker, framework scripts. Product rule: finds/analyzes, never writes lyric lines; no external services/LLMs/API keys. lyrics.db only via the existing read-only guards (corpus.open_ro / build_guarded); never write it or its sidecars. Parameterized SQL only. Standard library + toolshop + Flask only; no pip/npm. No git add/commit/checkout/switch/stash/reset — the orchestrator commits. Absolute paths; foreground only; never delete MAirina_Tucc\data\index_3a770ed6.pre-rebuild-20260930.pkl.

VERIFY: (1) "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q -p no:cacheprovider → all pass, 0 skipped (quote it). (2) In its own terminal: `MAirina_Tucc\mt.ps1 serve --data-dir <new folder under %TEMP%>`; from another terminal curl GET /api/stats, /api/stars, /api/me, /api/atlas?lane=drill, /api/compare?lane=drill and POST /api/xray with the verse below; then stop the server. (3) lyrics.db mtime+size and the MAirina_Tucc\data\ listing identical before/after. Verse:
Usne crvene ko lava –
s tobom uvek ludilo
(niko ne pomisli da spava)
Separe je naš, najluđi smo – znaš
Mala, mogla si da me imaš,
u Panameri da se snimaš

HANDOFF: D:\Projects\Music-AI-Toolshop\MAirina_Tucc\ORCHESTRATION\mairina_v2\wave3\D3_handoff.md — endpoint table (method, path, request, response sample, error codes), files changed with line counts, pytest summary, curl outputs, invariants before/after, deviations, not done. Reply exactly: "WAVE 3 API DONE - handoff at <path>" plus the pytest summary line.

OPEN FILES: D:\Projects\Music-AI-Toolshop\MAirina_Tucc\rimer-ui\src\types.ts, D:\Projects\Music-AI-Toolshop\MAirina_Tucc\rimer-ui\src\api.ts, D:\Projects\.workspace_archive\plans\mairina-v2-api-ui-15383c.md, D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mairina\cli.py, D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mairina\votes.py, D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mairina\fingerprint.py, D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mairina\used.py
