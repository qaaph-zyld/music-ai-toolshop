# Wave 3S - S3 handoff (API security / robustness fixes)

Implementer: S3. Method per finding: failing test first, then fix, then green. All 14 findings
reproduced except where marked "did NOT reproduce" (those tests are pins; no code was "fixed").

Result: `pytest MAirina_Tucc\tests -q -p no:cacheprovider` -> **321 passed, 0 skipped** (baseline 244;
+77 new tests, all in `tests/test_api_hardening.py` incl. parametrized cases; plus 1 test rewritten in `tests/test_api.py`).

Changed files (only `MAirina_Tucc\mairina\` and `MAirina_Tucc\tests\`, plus this handoff):
`mairina/api.py`, `mairina/votes.py`, `mairina/atlas.py`, `mairina/rank.py`,
`tests/test_api.py` (client fixture waits for the atlas; vote test made discriminating),
`tests/test_api_hardening.py` (new). No change to `devices.py`, `multis.py`, `corpus.py`, `cli.py`.
Line numbers below refer to the files after the change.

## Per finding

### H1 DNS rebinding / cross-site - reproduced: YES
- Failing before: `test_h1_foreign_host_header_is_rejected_with_json[evil.test:8000 | evil.test |
  127.0.0.1.evil.test:8000 | localhost.evil.test]` -> `GET /api/stats` with `Host: evil.test:8000`
  answered **200** with the stats JSON; `test_h1_cross_site_fetch_metadata_is_forbidden` -> 200 not 403.
- Fix: `api.py:330` `app.config["TRUSTED_HOSTS"] = ["127.0.0.1", "localhost"]` (Werkzeug ignores the
  port); `api.py:355-360` `before_request` -> 403 JSON on `Sec-Fetch-Site: cross-site`, plus a
  `SecurityError` handler (`api.py:362`) -> 403 JSON (the untrusted-Host exception is raised while the request
  context is built; Flask stores it as a routing exception, so the JSON handler catches it - no HTML).
- Green: all four Host variants + cross-site -> 403 JSON, and a rejected call logs nothing.
  Pins (passed before and after): Host `127.0.0.1[:8000]` / `localhost[:8000]` served;
  `Sec-Fetch-Site` same-origin / same-site / none / missing pass; Vite-proxy-style request
  (`Host: 127.0.0.1:8000`, `Origin: http://localhost:5173`, json body) still 200.
- Note: Werkzeug does not lowercase the Host, so `LOCALHOST:8000` is refused (fails closed; browsers
  send lowercase hosts). I did not pin that either way.
- Live: `curl -H "Host: evil.test:8000" /api/stats` -> `403 {"error":"Host header not allowed: ..."}`.

### H2 input caps - reproduced: YES
- Failing before: `test_h2_word_phrase_seed_cap_200_chars`, `test_h2_rhyme_line_cap_500_chars`,
  `test_h2_artists_tags_caps`, `test_h2_text_line_count_cap_300[xray|star|used]` (301 lines -> 200).
  Timing on the old code (fixture corpus, `/api/xray`): 2000 x `a\n` -> 3.41 s (quadratic, so
  10000 lines extrapolates to ~85 s; I did not run the full 10000 on the old code).
- **Extra finding while measuring:** ONE line of 19,999 chars (inside the 20k char cap, 1 line) took
  **29.9 s** in `/api/xray` (22 s in `/api/star`). The line-count cap does not touch that, so I added a
  per-line cap: any draft line > 500 chars -> 413 (same number as the rhyme `line` cap).
  RED: `test_h2_single_very_long_line_is_refused_not_ground_through[xray|star|used]`.
- Fix (`api.py`): constants 38-49; `_req_text` 108-117 (20k chars, 300 lines via `splitlines()`, 500 chars
  per line -> 413, all before any analysis); `_req_str/_opt_str` caps (word/phrase/seed 200, rhyme
  `line` 500 -> 413) at 396, 427-428, 450; `_artists` 185-199 (> 20 names -> 400); `_tags` 127-140
  (> 20 -> 400, each > 64 chars -> 413). Additions beyond the brief: artist name <= 64 chars (413, every
  distinct artist set caches a whole vocabulary) and compare `theme` <= 200 (413).
- Pairwise passes (`devices._rhyme_letters`, `_multi_suffixes`) and the multis loop: NOT rewritten.
  The skeleton/tail keys were already computed once, and with the three caps the pairwise work is
  bounded. Worst admitted inputs measured after the fix: 300 identical 66-char lines -> xray 0.91 s /
  star 2.23 s (star includes the sqlite commit); 300 vowel-heavy lines 1.3 s; 40 x 492-char lines 0.4 s.
  Multis with a 200-char phrase on the REAL corpus index: 0.45-0.59 s (while the atlas was building).
- `rank.features_for` recomputation FIXED: `rank.py:51-60` `Ctx.line_syllables()/line_dominant()`
  (cached per Ctx = per request), used at `rank.py:92, 97, 132`. Measured, 5 candidates, HEAD vs new:
  `count_line(line)` 6 calls -> 1, `dominant_class(line)` 5 calls -> 1. Test:
  `test_h2_rhyme_line_level_values_are_computed_once_per_request`.
- Green: `'a\n' * 10000` -> 413 in < 2 s on all three endpoints (assertion in the test).

### H3 atlas cold build inside a request - reproduced: YES
- Failing before: `test_h3_atlas_load_concurrent_callers_scan_once` (5 concurrent `atlas.load` = 5 scans),
  `test_h3_atlas_warms_in_background_503_then_200_exactly_one_build` (requests blocked on the build /
  500s after the 10 s gate), `test_h3_a_failed_warmup_degrades_then_retries`.
- Fix: `atlas.py:161-175` module-level `_LOAD_LOCK` around the whole of `load()` (second caller waits,
  then hits the cache the first wrote). `api.py:229-293` `_AtlasWarmup` (single-flight, daemon thread
  `mairina-atlas-warmup`, status warming / ready / failed / disabled), started in `create_app`
  (`api.py:352`) only when the corpus index loaded. `/api/me` and `/api/atlas` -> 503
  `Corpus atlas is warming up (first run ~20 s) - retry shortly` while warming; `/api/xray`
  skips the fingerprint (`vs_star` null) while warming and never blocks (`api.py:489`).
- Green: with a gated fake `atlas.load`: startup < 5 s, 9 concurrent me/atlas/xray calls all return
  promptly (503 / 200 with null vs_star), exactly ONE build on the warm-up thread; after release
  me/atlas 200, vs_star filled again, still one build.
- Decisions to review: (1) `/api/me` 503s while warming even with zero stars (as specified).
  (2) A failed warm-up (e.g. `-journal` present) degrades: `/api/me` 200 with plain means,
  `/api/atlas` 503 with the scrubbed engine message; a request retries the build (single-flight) once
  30 s have passed (`ATLAS_RETRY_SECS`, `retry_after` on the object) - added so a transient writer
  lock needs no restart. (3) The atlas is now a startup snapshot (before: per-request mtime check),
  like the index already was; restart `mt serve` after lyrics.db changes.
- Live (real corpus, cold atlas, new temp data dir): `/api/atlas` 503 warming -> 200 after ~13 s;
  `/api/me` 200 afterwards.

### M1 serve() - reproduced: YES
- Failing before: `test_m1_serve_disables_debugger_even_with_flask_debug_env` (with `FLASK_DEBUG=1`
  Werkzeug `run_simple` received `use_debugger=True`), `test_m1_serve_passes_explicit_safe_run_options`.
- Fix: `api.py:737` `app.run(host, port, debug=False, use_debugger=False, use_reloader=False,
  load_dotenv=False, threaded=True)`.
- Green: both tests. Live with `FLASK_DEBUG=1` in the server's env: `GET /console` -> 404 JSON (no
  debugger console).

### M2 list_id race / empty lists - reproduced: YES
- Failing before: `test_m2_concurrent_log_shown_gets_distinct_ids` (forced interleave -> both threads
  got the same list_id), `test_m2_many_threads_log_distinct_lists`,
  `test_m2_empty_list_id_is_never_reused` (an empty anchors list's id was handed to the NEXT list),
  `test_m2_empty_list_survives_for_later_lists_in_the_cli_numbering`.
- Fix (`votes.py`): new `lists(list_id PK, ts, kind, arm, query)` table (line 22, `IF NOT EXISTS`, picked up
  by every `connect()`); `log_shown` 55-95: module `threading.Lock` + `BEGIN IMMEDIATE`, id =
  `MAX(max(shown.list_id), max(lists.list_id)) + 1`, header row always inserted (even for empty
  lists), items inserted in the same transaction, rollback on error (the lock serialises threads,
  BEGIN IMMEDIATE serialises processes, e.g. CLI + API). `list_rows` 98-107 returns `(id, kind, [])`
  for a header-only list; `cast_votes` 125 -> `VoteError` "List #N is empty..." -> API **400** JSON.
- Green: distinct ids under forced interleave and under 5 threads x 6 lists (each list keeps its own 2
  rows); empty list id not reused; vote on the empty list -> 400 and zero vote rows. Pin (passed
  before and after): a pre-3S db (shown rows, no `lists` table) keeps counting up (7 -> 8).
- Not changed on purpose: `stats()` / `last_list` still read `shown` only, so an empty list does not
  count in `lists` stats and `mt vote` (no list id) still targets the newest list WITH items.

### M3 GET /api/compare writes `shown` rows - reproduced: YES
- Failing before: `test_m3_cross_site_get_compare_writes_nothing` (cross-site GET -> 200 and a list logged).
- Fix: the H1 `Sec-Fetch-Site` guard. Green: 403 JSON, nothing logged; same-origin GET -> 200 and logged.
  (The design smell - a GET that writes - is left as is; out of scope.)

### M4 tests
- `tests/test_api.py::test_vote_targets_the_exact_list` rewritten: two DIFFERENT lists (rhyme vs multi,
  no shared candidate); vote on list 1 item 1; asserts the vote row is `(list_id=1's id, rank 1,
  list 1's candidate, +1)` straight from sqlite. Mutation check: with `votes.cast_votes` patched to
  ignore `list_id` (vote lands on the newest list) the OLD test still passes (non-discriminating)
  and the NEW test fails (`[(2, 1, 'ekipa', 1)] != [(1, 1, 'glava', 1)]`).
- Duplicate vote items: reproduced (`[[1,1],[1,-1]]` -> 200, two vote rows). Fix `api.py:527-538` ->
  400, nothing written. `test_m4_duplicate_vote_items_are_rejected_without_writing`.
- **Did NOT reproduce (already correct; tests are pins that passed on the pre-fix code):**
  `text/plain` POST -> 400 with no side effects (8 endpoints); JSON `[]`/`null`/`[1,2]`/`"str"`/`42`/
  `true` bodies -> 400; `NaN`/`Infinity`/`-Infinity`/out-of-range `fresh` -> 400, nothing logged;
  forced engine exception (`rank.rank` / `devices.analyze_verse` raising with a `D:\` path in the
  message) -> 500 JSON `{"error": "internal server error"}` with no `Traceback`, `D:\`, message text or
  `File "` in the body.

### L1 absolute paths in 503 bodies - reproduced: YES
- Failing before: `test_l1_503_bodies_carry_no_absolute_paths` (body `lyrics.db not found. Expected at:
  C:\Users\...\gone\lyrics.db`), `test_l1_other_dbunavailable_messages_are_scrubbed_too`.
- Fix: `api.py:210-226` `_scrub()/_clean()` (drops the `Expected at:` clause, replaces the known db/data
  paths, then any drive-letter / UNC path with `<path>`); applied to the startup `corpus_error`, the
  `DbUnavailable` handler (request-time raises from targets/comparisons/atlas) and the atlas 503. CLI
  output unchanged. Green: six corpus routes -> 503 with `lyrics.db not found.` and no `X:\`.

### L2 absurd ids / nesting - reproduced: YES
- Failing before: `DELETE /api/star/10**30` and `/2**63` -> 500 (sqlite OverflowError);
  `2**63-1` -> already 404 (did not reproduce, kept as a pin). Deeply nested JSON (`[`*200000,
  `{"a":`*100000, balanced) -> 500 (RecursionError is not a ValueError, so `get_json(silent=True)`
  does not swallow it).
- Fix: `api.py:571` ids above SQLite's INTEGER -> 404 JSON; `api.py:77-84` `_body()` catches
  `RecursionError` -> 400 JSON. Green: all variants.

### L3 draft_id / tags must be strings - reproduced: YES
- Failing before: `draft_id` 123 / 1.5 / true / ["a"] / {"a":1} accepted (stored as `draft:123`...) on
  `/api/star` and `/api/used`; tags `[1]`, `[None]`, `[["a"]]`, `[{"a":1}]`, `["ok", 2]`, `[true]` were
  coerced with `str()`.
- Fix: `api.py:120-140` `_draft_id`, `_tags`; used by `api_star` and `api_used`. Green: 400 each, no star
  stored; string tags / draft_id still 200.

### L4 startup sqlite3.Error / OSError - reproduced: YES
- Failing before: a garbage `lyrics.db`, and `load_index` raising `sqlite3.OperationalError`,
  `sqlite3.DatabaseError`, `PermissionError`, `FileNotFoundError` (also `load_gazetteer` raising)
  -> `create_app` itself raised.
- Fix: `api.py:342-345` catches `(sqlite3.Error, OSError)` next to `DbUnavailable`: app starts, corpus
  routes 503 with a scrubbed message `lyrics.db could not be read (<ExcName>: ...)`; stats/stars/me
  still work. Green: all five variants (no path in the body).

## Verification
- Pre-fix RED run of the new tests (fast subset, old code): 42 failed / 28 passed; slow subset: 4 + 3
  failed (`h2_single` x3, `h3_atlas_warms`, `h2_text_line` x3). Passing-on-old tests are the pins named above.
- Final: `"D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q -p no:cacheprovider`
  -> `321 passed, 1 warning in 262.10s`, 0 skipped. Concurrency tests (m2/h3/l4/m1) re-run 3x: 16 passed each time.
- Live smoke (the ONE port-8000 bind that counts; `mt.ps1 serve --data-dir %TEMP%\s3_smoke_ae702b75`, index/targets
  pickles copied into that folder, `FLASK_DEBUG=1` in env, then killed with `taskkill /T /F`; port 8000
  confirmed free afterwards): `/api/stats` 200; `Host: evil.test:8000` -> 403 JSON; `Sec-Fetch-Site: cross-site`
  -> 403 JSON; `/api/atlas` 503 warming then 200 after ~13 s; `/api/me` 200; `/console` 404 JSON.
  Disclosure: an earlier launch of the same smoke script aborted within a second (a PowerShell
  `curl` alias clash in my script, no request reached the API, the server was killed in `finally`);
  I fixed the script and ran it once more - that is the run above. The smoke's `POST /api/rhyme`
  line returned 400 only because PowerShell 5.1 strips the double quotes of curl's `-d` body (a script
  artifact); the JSON POST path is covered by `test_h1_vite_proxy_style_request_still_works`.
- Invariants: `lyrics.db` (78,524,416 bytes, mtime_ns 1790810143258653900) and every file in
  `MAirina_Tucc\data\` (names, sizes, mtimes; `index_3a770ed6.pre-rebuild-20260930.pkl` untouched) are
  byte-for-byte identical before and after (diff of a before/after snapshot = empty), after the full
  suite AND the live smoke. Tests use tmp data dirs only. No git add/commit/checkout/stash/reset. No
  `rimer-ui\`, `toolshop\` or lyrics.db writes.

## For the orchestrator
- Contract: `/api/atlas` rows' `med_syl` may be `null` (lane/artist with no lines) - API unchanged;
  update `rimer-ui\src\types.ts` (`med_syl: number | null`).
- New response cases the UI should tolerate: `/api/me` and `/api/atlas` may answer 503 `Corpus atlas is
  warming up (first run ~20 s) - retry shortly` right after `mt serve` starts (cache miss: ~13-20 s;
  cache hit: well under a second); `/api/xray` `vs_star` is null during that window; 413 for oversize
  input, 403 for a foreign Host / cross-site fetch, 400 for duplicate vote items and non-string tags/draft_id.
  Vite proxy (`changeOrigin: true` -> Host `127.0.0.1:8000`) keeps working.
- Out of scope, noticed: `/api/compare` runs `comparisons.collect` (a full corpus pass) in EVERY request,
  and `targets.target` builds its pickle cache inside the first request on a cold data dir - the same
  cold-work-in-request pattern as H3, not changed.
- Leftover scratch dirs `%TEMP%\s3\`, `%TEMP%\s3_smoke_*`, `%TEMP%\s3real_*`, `%TEMP%\s3t_*` (mine, harmless).
