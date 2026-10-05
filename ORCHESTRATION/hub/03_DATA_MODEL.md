# 03 — Data model

## hub.db (SQLite cache, rebuildable; `TOOLSHOP_DATA_DIR/hub/hub.db`)

```sql
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);           -- indexed_at, horizon_days, config_hash, hub_version
CREATE TABLE collector_status (
  name TEXT PRIMARY KEY, status TEXT CHECK (status IN ('ok','degraded','failed')),
  records INTEGER, error TEXT, duration_ms INTEGER, ran_at TEXT);
CREATE TABLE events (
  id TEXT PRIMARY KEY,            -- stable: '<kind>:<source-key>' e.g. 'commit:<fullhash>', 'session:<filename>'
  ts_utc TEXT NOT NULL,           -- ISO-8601 Z
  ts_approx INTEGER DEFAULT 0,    -- 1 when time came from mtime (scheme-B session records)
  kind TEXT NOT NULL,             -- see Event kinds
  source TEXT NOT NULL,           -- collector name
  repo TEXT, lane TEXT, artist TEXT,
  title TEXT NOT NULL,
  excerpt TEXT,                   -- plain text, <= 300 chars
  link TEXT,                      -- 'file:<workspace-relative path>' | 'git:<repo>@<hash>' | 'http://127.0.0.1:8778/...'
  receipt_status TEXT,            -- NULL | 'pushed' | 'local' | 'missing' | 'none'
  receipt_detail TEXT             -- JSON: [{"hash":"8a9a5f3","repo":"studio","state":"pushed"}, ...]
);
CREATE INDEX events_ts ON events(ts_utc DESC);
CREATE INDEX events_lane ON events(lane, ts_utc DESC);
CREATE TABLE docs (path TEXT PRIMARY KEY, kind TEXT, lane TEXT, artist TEXT, title TEXT,
  mtime TEXT, excerpt TEXT, spent_by TEXT);                      -- ledgers + handoffs (spent_by = consuming record)
CREATE TABLE repo_state (repo TEXT PRIMARY KEY, path TEXT, branch TEXT, head TEXT,
  modified INTEGER, untracked INTEGER, ahead INTEGER, behind INTEGER, stashes INTEGER,
  pointer_drift TEXT, worktree_of TEXT, last_commit_ts TEXT, error TEXT);  -- W3
CREATE TABLE artists (name TEXT PRIMARY KEY, title TEXT, profile_json TEXT, profile_confidence TEXT,
  chain_maps TEXT, packs TEXT, ledgers TEXT);                    -- W4 (JSON arrays)
CREATE TABLE songs (artist TEXT, song TEXT, source TEXT, source_exists INTEGER, rounds TEXT, status TEXT,
  PRIMARY KEY (artist, song));                                   -- W4
CREATE TABLE inbox (id TEXT PRIMARY KEY, state TEXT, kind TEXT, title TEXT, lane TEXT, artist TEXT,
  repo TEXT, blocking TEXT, links TEXT, body TEXT, created_ts TEXT, created_by TEXT,
  resolved_ts TEXT, resolution TEXT, snooze_until TEXT);         -- folded view of inbox.jsonl
```

Rebuild is atomic: build `hub.db.tmp`, run `PRAGMA integrity_check`, then `os.replace` it over `hub.db`.

## Event kinds

| kind | source | receipts? | shown on Home journal by default |
|---|---|---|---|
| `commit` | S1 | — | yes |
| `pointer_bump` | S1 | — | yes (muted) |
| `session` | S2 | **yes** | yes |
| `handoff` | S3 | **yes** | yes |
| `ledger_update` | S4 | — | yes (muted) |
| `listen_verdict` | S5 | — | yes (grouped per page per minute) |
| `inbox_opened` / `inbox_resolved` / `inbox_reopened` | S6 | — | yes |
| `changelog` | S9 | — | no (journal page filter only) |

## Inbox (`TOOLSHOP_DATA_DIR/hub/inbox.jsonl`, append-only source of truth)

One JSON object per line. Every line is an **operation**, and the current state is the fold of all operations
in file order.

```json
{"op":"open","id":"inb_20261006_ogcj_g4","ts_utc":"2026-10-06T09:00:00Z","by":"orchestrator",
 "kind":"ear_test","title":"OGCJ G4: pick the blind Suno-flip master",
 "lane":"ogcj","artist":null,"repo":"studio","blocking":["ogcj"],
 "links":[{"label":"Blind pack","href":"http://127.0.0.1:8778/beats/ogcj_suno/"}],
 "body":"Two masters A/B. Pick one; the lane closes out after your pick."}
{"op":"resolve","id":"inb_20261006_ogcj_g4","ts_utc":"…","by":"user","answer":"B"}
{"op":"snooze","id":"…","ts_utc":"…","by":"user","until":"2026-10-10"}
{"op":"reopen","id":"…","ts_utc":"…","by":"user","note":"wrong pick"}
{"op":"note","id":"…","ts_utc":"…","by":"agent:devin-x","text":"pack re-rendered, please re-listen"}
```

| Field | Rule |
|---|---|
| `id` | `inb_<YYYYMMDD>_<slug>`, unique. `ask` derives it from the title and refuses duplicates of open items. |
| `kind` | one of `decision`, `ear_test`, `sign_off`, `provide_input`, `run_on_signal`, `review` |
| `lane`, `artist`, `repo` | Optional, but at least one is required. The values match attribution names from `02`. |
| `blocking` | List of lanes that cannot proceed until this is resolved. The count drives sort order on Home. |
| `links` | `[{label, href}]`. `href` is `http://127.0.0.1:*`, a `file:` path inside the workspace, or `git:<repo>@<hash>` |
| `by` | `user`, `orchestrator`, or `agent:<session-or-name>` |
| States | `open` → `resolved` (with `answer`) or `snoozed` (with `until`, which reverts to open after that date) → `open` again on `reopen` |

**Validation** (`store.validate`) runs on append. An unknown `op`, a resolve on an unknown id, or a missing title
on `open` is rejected with exit code 2, and nothing is written. On read, a malformed line is skipped and
counted in `collector_status`. The file is never rewritten.

**CLI** (`python -m toolshop.hub …`):
- `ask --title T --kind K [--lane L] [--artist A] [--repo R] [--blocking L1,L2] [--link "label=href"]… [--body B] [--by agent:X]`
  prints the id.
- `resolve ID --answer TEXT [--by user]`
- `snooze ID --until YYYY-MM-DD`
- `reopen ID [--note TEXT]`
- `note ID --text TEXT`
- `list [--open] [--resolved-since ISO] [--lane L] [--json]` is how agents read their answers at session start.
  `--json` prints a list of folded items:
  `{id, state, kind, title, lane, artist, repo, blocking, links, body, created_ts, created_by, resolved_ts, answer, snooze_until}`,
  with `answer` at the top level.
- `import-seed PATH` appends `open` lines for ids not present yet (idempotent).

## Receipts (`receipts.py`)

**Purpose:** make "done" claims checkable. This is the 2026-10-05 lesson: a "fix 3 done" report had no
commit behind it.

1. **Extract candidates** from the session or handoff text. A candidate is a token matching
   `(?<![0-9a-fA-F])[0-9a-f]{7,12}(?![0-9a-fA-F])` that contains at least one digit **and** at least one of
   `a-f`. That excludes plain numbers, plain words like `facade` and the 64-hex sha256 values that appear in
   manifests.
2. **Resolve** each candidate with `git cat-file -e <cand>^{commit}` in the journal repos **plus**
   `hub_config.json` → `receipt_extra_repos`, which defaults to `["ai_dev_meta_layer", "."]` (the framework
   repo and the workspace repo). Session records often cite framework commits, and without these repos those
   would show as red. Stop at the first repo where the commit exists.
   - A candidate that resolves in no repo is **ignored** when the document never wrote it in backticks or after
     the words commit/merged/pushed/hash. Otherwise it counts as `missing`.
3. **Pushed check** (resolved hashes only): `git branch -r --contains <hash>` non-empty means `pushed`, empty means
   `local`.
4. **Document status** is the worst status across its counted hashes, in the order `missing` > `local` > `pushed`.
   A document with no counted hash gets `none`.
5. **Cache.** Results are cached per (hash, repo HEAD) in `hub.db`, so a re-index doesn't re-run git for
   unchanged repos.

**Badge copy** (contract `s2c_receipt`):
- `pushed` → "receipts ✓ N pushed"
- `local` → "receipts: N local, not pushed"
- `missing` → "receipts ✗ M of N not found"
- `none` → "no receipts"

The receipts test fixture must cover all four states.
