# Session Record — MAirina v2 Wave 3 D3: local Flask API over the engine

**Session scope:** implement `mairina/api.py` (Flask app factory, 14 frozen
endpoints), engine helpers (text-first star/used, targeted `list_id` voting,
hint-vote-0 reset), `mt serve`, and `tests/test_api.py`; verify full suite +
live smoke; emit `D3_handoff.md`. ORCH-local record — framework `memory/`
writes barred while `.workspace_archive/orchestration/ACTIVE` exists. The task
itself was a PRE-APPROVED implementer dispatch (D3) under that marker.
Recorded 2026-10-01 23:42; observable events only.

## What happened

- Read the frozen contract field-for-field: `rimer-ui/src/types.ts` + `api.ts`
  (UI owned by a parallel Claude session — read-only for me), the two plans,
  the D3 prompt, and all touched engine modules (fingerprint, used, votes,
  hints, devices, anchors, rank, multis, atlas, comparisons, corpus, cli).
- Implemented engine helpers first, each delegating so CLI paths stay
  byte-identical: `devices.gauge_level` (numeric 0–3 behind `gauge()`),
  `used.scan_text` (no temp lyric file; `scan()` delegates),
  `votes.cast_votes(list_id=None)` (omitted = latest; supplied = exact list,
  validated atomically in one transaction; unknown/stale → `VoteError`),
  `fingerprint.lyric_lines_from_text` / `draft_key` / `star_text` /
  `vs_star_phrase` (cli `_cmd_xray` refactored to call it).
- Wrote `mairina/api.py` (556 lines): `create_app(lyrics_db=None,
  data_dir=None)` loads the corpus index once; `DbUnavailable` /
  `CorpusNotAnnotated` are captured, the app still boots, corpus routes 503
  while stars/stats/me keep working. `serve()` raises `ValueError` for any
  host/port other than `127.0.0.1:8000` before Flask starts. All
  `werkzeug.HTTPException`s re-rendered as `{"error": …}` — no HTML anywhere.
- `cli.py`: `serve` subparser (`--data-dir`, default `MAirina_Tucc\data`);
  Flask imported lazily inside the dispatch branch.
- `tests/test_api.py` (377 lines, 24 tests): every endpoint happy path +
  exact key sets, ≥1 error path each, malformed JSON, >20k text → 413,
  injection strings, stale `list_id` votable while unknown → 404, hint
  `vote:0` reset, `draft_id` idempotence + stored verbatim (`"draft:<id>"`,
  never resolved as a path), `CorpusNotAnnotated` → 503 split, bind refusal,
  no-HTML bodies, real `data/` untouched, `lyrics.db` mtime+size invariant.
- First run: 23/24 — `scheme:""` defaulted leniently to AABB (consistent with
  lane/section/mode null-handling); test fixed to assert a non-alpha scheme →
  400 instead of changing contract. Second run: 24/24.
- Full suite: **244 passed, 1 warning, 0 skipped** in 333.87s.
- Live smoke: `mt.ps1 serve --data-dir %TEMP%\mairina-api-smoke` → all five
  GETs + POST `/api/xray` (6-line verse) correct; simile/allit/multi tags
  present. `lyrics.db` 78 524 416 B @ 23:15:43 UTC identical before/after;
  WAL 0 B; `MAirina_Tucc\data\` listing unchanged.
- `D3_handoff.md` written; required completion line emitted.

## Lessons

- **Read the consumer before the provider.** The single biggest contract
  catch came from `api.ts`, not `types.ts`: optional fields arrive as `null`,
  `draft_id` is browser-stable, and `cons` is the *level* while
  `cons_density` is the raw float — an interface-only read would have missed
  the `approx` fallback marker and the ab-string humanization.
- **Reuse CLI semantics, don't reimplement them.** Every API handler maps to
  an existing CLI function; the only new logic is validation → JSON shaping.
  `vs_star_phrase` extraction kept the `(n=…)`/raw-mean behavior identical
  across both surfaces instead of drifting.
- **`draft_id` stays opaque by construction.** Prefixing to `"draft:<id>"`
  before it reaches the file-column makes "never a path" structural — there
  is no code path that could resolve it.
- **503-degrade is per-route, not per-app.** Capturing the corpus exception
  at factory time lets star/stats/me pass the smoke on a laptop without the
  corpus — the same degradation the CLI already does.

## Decisions

- Empty/`null` optional fields → defaults (lenient), invalid enum values →
  400 (strict). Rejected strictness on empty strings: would diverge from the
  UI's null-heavy request shape.
- `NoAnchors` → `items:[]` + logged `list_id` (200), not 4xx — an empty shelf
  is a find, keeps the list votable.
- Stale-but-existing `list_id` remains votable (the point of targeted
  voting); only unknown ids 404.
- Flask imported lazily in cli dispatch so non-serve CLI paths don't pay the
  import.
- `vs_star`/`assonance` keys always present with `null` when nothing fires —
  the contract key set never shrinks.

## Files Modified

| File | Change |
|---|---|
| `mairina/api.py` | New, 556 lines — app factory, 14 endpoints, JSON error handlers, `serve()`/`run()` |
| `mairina/fingerprint.py` | +86 — text-first star helpers, `draft_key`, `vs_star_phrase` |
| `mairina/votes.py` | +27 — optional `list_id`, atomic exact-list validation |
| `mairina/used.py` | +6 — `scan_text`; `scan` delegates |
| `mairina/devices.py` | +7 — `gauge_level` |
| `mairina/cli.py` | +7 — `serve` subcommand; `_cmd_xray` uses `vs_star_phrase` |
| `tests/test_api.py` | New, 377 lines — 24 tests |
| `ORCHESTRATION/mairina_v2/wave3/D3_handoff.md` | New — endpoint table, verification, invariants |

## Verification

- `python -X utf8 -m pytest MAirina_Tucc\tests -q -p no:cacheprovider` →
  `244 passed, 1 warning in 333.87s` — 0 skipped.
- `mt.ps1 serve --data-dir %TEMP%\mairina-api-smoke` live curls: stats/stars/
  me/atlas?lane=drill/compare?lane=drill + POST xray — all 200, contract-exact.
- `lyrics.db` invariant: 78 524 416 B @ 2026-09-30 23:15:43 UTC before == after.
- `MAirina_Tucc\data\` listing identical; smoke `mairina.db` confined to %TEMP%.
- `git status` scope: only `mairina/` + `tests/` + the wave3 handoff mine;
  `rimer-ui/` modifications belong to the parallel session.
