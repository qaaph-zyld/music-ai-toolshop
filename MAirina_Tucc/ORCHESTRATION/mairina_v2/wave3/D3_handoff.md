# Wave 3 — D3: local Flask API over the MAirina engine

Date: 2026-10-01. Baseline: waves 1–2R committed (b1c066b, b33f0fd, 75362fa, 4d227b1,
docs 46155b0, CHANGELOG #077), suite was 220 passed / 0 skipped.

`mairina/api.py` is a thin adapter: request validation → existing engine modules →
JSON shaped exactly to `rimer-ui/src/types.ts`. No lyric generation, no external
services, no CORS, `127.0.0.1:8000` only (any other host/port raises before serving).

## Endpoint table

| Method | Path | Request | Response sample | Error codes |
|--------|------|---------|-----------------|-------------|
| POST | `/api/anchors` | `{scheme,lines,lane,mode,seed,fresh,artist,section}` (all optional → defaults) | `{"list_id":1,"arm":"base","target":{"lo":10,"median":13,"hi":15,"approx":false},"items":[{"n":1,"group":"A","word":"lava","upos":"NOUN","cls":"rhyme","freq":9,"why":"…"}]}` | 400 bad scheme/lane/mode/section/fresh/lines · 503 corpus down |
| POST | `/api/rhyme` | `{word,line?,target?,lane,fresh,artist}` | `{"list_id":2,"arm":"base","query":"lava","items":[{"n":1,"word":"spava","score":2.31,"kind":"perfect-2","why":"…"}]}` | 400 missing word / target w/o line / bad fresh · 503 |
| POST | `/api/multi` | `{phrase,lane}` | `{"list_id":3,"arm":"base","query":"me imaš","items":[{"n":1,"phrase":"…","score":1.8,"why":"…"}]}` | 400 missing phrase · 503 |
| POST | `/api/xray` | `{text,lane,section?}` | `{"lines":[{"n":1,"text":"…","syl":8,"target":{"lo":10,"median":13,"hi":15,"approx":false},"rhyme":"A","cons":0,"cons_density":0.75,"allit":false,"assonance":null,"devices":[{"kind":"simile","span":"ko","confidence":"medium"}],"hints":[],"vs_star":null}]}` | 400 missing/blank text, bad lane/section · 413 >20 000 chars · 503 |
| POST | `/api/vote` | `{list_id,items:[[n,+1|-1]]}` | `{"ok":true}` | 400 bad n/value/shape · 404 unknown list_id |
| POST | `/api/star` | `{text,line_no,tags[],lane,draft_id?}` | `{"id":1,"ts":"…","line_no":1,"text":"lava pada","lane":"all","tags":["punchline"]}` | 400 bad line_no / tags not array · 413 oversized text |
| DELETE | `/api/star/<id>` | — | `{"ok":true}` | 404 unknown id |
| GET | `/api/stars?lane` | — | `{"items":[{"id":1,"ts":"…","line_no":1,"text":"…","lane":"all","tags":[…]}]}` | 400 bad lane |
| GET | `/api/me?lane` | — | `{"n":3,"low_confidence":true,"numeric":{"syl":{"mean":8.7,"shrunk":8.6,"lane_mu":12.0,"lane_sigma":1.9},…},"tag_rates":{"punchline":1.0},"kind_rates":{…}}` | 400 bad lane |
| GET | `/api/atlas?lane&artist` | — | `{"lanes":[{"scope":"lane drill","lines":39052,"simile":5.18,…}],"artists":[{"scope":"devito",…}]}` | 400 bad lane · 503 |
| GET | `/api/compare?lane&artist&theme` | — | `{"list_id":4,"arm":"base","items":[{"n":1,"word":"led","count":12,"score":2.93,"why":"simile-use +2.56 | freq(66) +0.84 | fresh -0.47"}]}` | 400 bad lane / multi-word theme · 503 |
| POST | `/api/hint-vote` | `{rule_id,vote:+1|-1|0}` | `{"rule_id":"cliche","up":0,"down":0,"muted":false}` | 400 unknown rule_id / bad vote |
| POST | `/api/used` | `{text,draft_id?}` | `{"count":2,"hits":["glava","spava"]}` | 400 missing text · 413 |
| GET | `/api/stats` | — | `{"votes":0,"up":0,"down":0,"up_rate":null,"used":0,"lists":0,"arms":{"learned":{"votes":0,"up_rate":null},"base":{"votes":0,"up_rate":null}},"ab":"not enough data (0/100)","muted":[]}` | — |

All errors are `{"error": "…"}` JSON — 4xx validation, 404 unknown ids/routes, 405,
413 oversized text (cap `MAX_TEXT_CHARS = 20_000`), 503 corpus down, generic 500 with
no internals. No HTML bodies anywhere (`werkzeug.HTTPException` is re-rendered as JSON).

## Engine helpers (shared with CLI — CLI behavior unchanged)

- `fingerprint.lyric_lines_from_text(text)` — parse a draft blob into numbered lines,
  no temp file.
- `fingerprint.draft_key(draft_id)` — opaque id → `"draft:<id>"` pseudo-filename;
  never resolved as a path. Missing id → `"<text>"` (unchanged legacy identity).
- `fingerprint.star_text(con, text, line_no, tags, lane, draft_id)` — text-first star;
  `star()` keeps the file-based CLI path and delegates to the shared `_store_star`.
- `fingerprint.vs_star_phrase(text, fp)` — the `vs★` string (raw ★ mean, `(n=…)` when
  `low_confidence`, allit skipped); both cli `_cmd_xray` and the API use it.
- `used.scan_text(con, text, file=None)` — text-first hit scan; `used.scan()` delegates.
- `votes.cast_votes(con, items, list_id=None)` — `None` = latest list (unchanged CLI);
  supplied = that exact list, validated atomically inside one transaction;
  unknown/stale → `VoteError` → 404.
- `devices.gauge_level(d)` — the numeric 0–3 level behind the existing `gauge()`
  ▮▯ bar (cli unchanged, still renders the bar).
- Hint `vote: 0` → `hints.reset(rule_id)` (clears up+down, un-mutes).

## `mt serve`

`cli.py`: `mt serve [--data-dir PATH]` (default `MAirina_Tucc\data`) →
`api.run(lyrics_db, data_dir)` → `create_app` + `app.run(host="127.0.0.1", port=8000)`.
`serve()` raises `ValueError` for any other host/port before Flask starts. Flask is
imported lazily inside the serve branch so all other CLI paths stay identical.

## Files changed

| File | Lines | Change |
|------|------:|--------|
| `mairina/api.py` | 556 new | app factory, 14 endpoints, validators, JSON error handlers, `serve()`/`run()` |
| `mairina/fingerprint.py` | 374 (+86) | `lyric_lines_from_text`, `draft_key`, `_store_star` core, `star_text`, `vs_star_phrase` |
| `mairina/votes.py` | 172 (+27) | optional `list_id` with atomic exact-list validation |
| `mairina/used.py` | 52 (+6) | `scan_text`; `scan` delegates |
| `mairina/devices.py` | 563 (+7) | `gauge_level` |
| `mairina/cli.py` | 474 (+7) | `serve` subcommand; `_cmd_xray` uses `vs_star_phrase` |
| `tests/test_api.py` | 377 new | 24 tests (see below) |

`rimer-ui/` untouched (parallel Claude session owns it).

## Pytest

```
"D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest
  "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q -p no:cacheprovider
244 passed, 1 warning in 333.87s (0:05:33)      # 0 skipped
```

(`test_api.py` alone: 24 passed in 37.66s.) The 1 warning is the pre-existing
`requests`/`urllib3` `RequestsDependencyWarning` — unrelated, present since before
Wave 1.

Test coverage (`tests/test_api.py`): happy path + exact response key sets for all 14
endpoints; ≥1 error path each; malformed JSON; oversized text → 413; injection-shaped
strings in `word`/`artist`/`draft_id`/`theme`; unknown + stale `list_id` (stale list
is still votable — targeted semantics); hint `vote:0` resets up/down/muted;
`draft_id` stable + idempotent (same draft+text+lane → same star id, no new `used`
rows) and stored verbatim, never a path; `CorpusNotAnnotated` → app still boots,
corpus routes 503 while `/api/stats` `/api/stars` `/api/star` keep working; missing
db → same 503/200 split; non-localhost + non-8000 bind refused; no HTML bodies on
400/404/405/413/503; real `MAirina_Tucc\data\` dir untouched; `lyrics.db` mtime+size
unchanged after a full client round-trip.

## Live smoke (mt serve + curl)

Server: `mt.ps1 serve --data-dir C:\Users\015ZCS\AppData\Local\Temp\mairina-api-smoke`
→ `Running on http://127.0.0.1:8000` (index + targets rebuilt into the temp dir).

```
GET /api/stats
{"ab":"not enough data (0/100)","arms":{"base":{"up_rate":null,"votes":0},
 "learned":{"up_rate":null,"votes":0}},"down":0,"lists":0,"muted":[],"up":0,
 "up_rate":null,"used":0,"votes":0}

GET /api/stars
{"items":[]}

GET /api/me
{"kind_rates":{},"low_confidence":true,"n":0,"numeric":{},"tag_rates":{}}

GET /api/compare?lane=drill   → list_id 1, arm "base", top item:
{"n":1,"word":"led","count":12,"score":2.934,
 "why":"simile-use +2.56 | freq(66) +0.84 | fresh -0.47"}

GET /api/atlas?lane=drill → 1 lane row ("lane drill", 39052 lines) + 18 artist rows;
statistics only, no lyric text anywhere in the payload.

POST /api/xray (the 6-line verse) → HTTP 200, 6 lines; "ko lava" tagged simile
(medium), lines 4–5 strong alliteration (n/m), imaš/snimaš share the "iaeia"
multisyllabic-rhyme span, rhyme letters A A A B B B, per-line strofa targets
{lo:10, median:13, hi:15, approx:false}, cons/cons_density both present.
```

## Invariants — before / after the smoke

| | Before | After |
|--|--------|-------|
| `lyrics.db` | 78 524 416 B · 2026-09-30 23:15:43 UTC | identical |
| `lyrics.db-wal` | 0 B | 0 B (read-only honored) |
| `MAirina_Tucc\data\` | `.gitignore`, `index_3a770ed6.pkl`, `index_3a770ed6.pre-rebuild-20260930.pkl`, `targets_3a770ed6.pkl` | identical listing — `mairina.db` went to %TEMP% only |
| `index_…pre-rebuild-20260930.pkl` | 4 548 296 B | untouched |

## Deviations

- `xray` lines carry `assonance: null` when no internal-rhyme/assonance device fires —
  the contract keeps the key, value is the vowel-skeleton string when present
  (e.g. `"ea"`, `"ia"`), else `null`. Same pattern for `vs_star` (null until ≥1 star).
- `anchors` returns `items: []` (HTTP 200) when the engine raises `NoAnchors` —
  the list is still logged so `list_id` stays votable. An empty shelf is a find, not
  an error.
- Votes on a stale-but-existing `list_id` succeed (that is the point of targeted
  voting); only unknown ids → 404.

## Not done

- Nothing in D3 scope. Wave 3 D4 (React UI wiring against this API) is the parallel
  Claude session's work; contract is frozen and verified field-for-field here.
