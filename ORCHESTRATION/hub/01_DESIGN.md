# 01 — Design

## Architecture (one process, three layers)

```
 sources (read-only)            toolshop/hub/                         browser (127.0.0.1:8790)
 ───────────────────            ─────────────                         ───────────────────────
 git repos + worktrees ─┐
 session records ───────┤   collectors/*.py ──► index.py ──► hub.db (SQLite cache, rebuildable)
 handoffs, ledgers ─────┤        (one per source,      atomic rebuild        │
 audition comments ─────┤         pure: read → Events)                       ▼
 ARTIST.md, profiles ───┘                                  app.py (Flask) ──► Jinja templates + hub.css + hub.js
                                                              ▲   │
 inbox.jsonl (append-only, SOURCE OF TRUTH) ◄── store.py ◄────┘   └── /api/* JSON
        ▲
        └── CLI: python -m toolshop.hub ask | resolve | list   (agents + user)
```

- **Collectors** read one source each and yield `Event` / `Doc` / `RepoState` / `Artist` records
  (`03_DATA_MODEL.md`). They never write anything.
- **Index** runs all collectors, writes a fresh SQLite file to `hub.db.tmp`, and then atomically replaces
  `hub.db` with it. The cache is always rebuildable, and deleting it is safe.
- **Store** owns `inbox.jsonl`. It is the only file the hub writes besides `hub.db` and `hub.log`. It is
  append-only: every change is a new line, and current state is the fold of all lines.
- **App** is a Flask app factory. It serves server-rendered pages (Jinja, autoescape on) plus a small vanilla JS file
  for filters, the refresh button and inline resolve forms. There is no build step, no npm and no CDN; it works offline.

## Package layout (`toolshop/hub/`, the `toolshop/daw/` subpackage pattern, AGENTS.md § Package layout)

```
toolshop/hub/
  __init__.py
  __main__.py          # CLI: serve | index | ask | resolve | snooze | list | selfcheck | import-seed
  config.py            # loads hub_config.json, resolves paths relative to workspace root
  hub_config.json      # tracked: repos, source globs, lane rules, horizon (no absolute paths)
  models.py            # dataclasses: Event, Doc, RepoState, InboxItem, Artist, Song, Receipt
  collectors/
    __init__.py        # registry + CollectorResult(status, records, error)
    git_log.py         # commits per repo (W1)
    sessions.py        # session records (W1)
    handoffs.py        # workspace handoffs (W1)
    ledgers.py         # ledgers as Docs + last-activity events (W1)
    audition.py        # listening-page comments (W1)
    inbox.py           # inbox.jsonl -> events (W1, via store)
    repo_state.py      # status/ahead/behind/worktrees/ACTIVE marker (W3)
    artists.py         # ARTIST.md + voice_profiles + chain maps + packs (W4)
  receipts.py          # commit-hash extraction + resolution (W1)
  index.py             # run collectors -> hub.db (atomic)
  store.py             # inbox.jsonl append/fold/validate
  app.py               # Flask factory, routes, Origin check
  templates/           # base.html, home.html, inbox.html, journal.html, lanes.html, artists.html, artist.html
  static/hub.css       # tokens + components (04 contract)
  static/hub.js        # filters, refresh, resolve forms, last-visit marker
scripts/hub.ps1        # ASCII-only launcher: starts serve, opens browser, appends launch line to hub.log
tests/test_hub_*.py    # inside tests/ so pytest.ini testpaths collects them (AGENTS.md lane discipline)
```

## HTTP surface (all on 127.0.0.1:8790)

| Method + path | Returns | Wave |
|---|---|---|
| `GET /` | Home (Inbox + Journal, last 7 days, ≤100 rows) | W2 |
| `GET /inbox` | All open items + resolved history | W2 |
| `GET /journal?days=90&lane=&repo=&kind=&q=&page=` | Paged journal (200/page) | W2 |
| `GET /file?path=<workspace-relative>` | Read-only text view; 404 outside workspace root | W2 |
| `GET /commit/<repo>/<hash>` | `git show --stat` text (allow-list) | W2 |
| `GET /lanes` | Lanes & repo health | W3 |
| `GET /artists`, `GET /artists/<name>` | Artist grid / artist page | W4 |
| `GET /api/health` | `{"indexed_at": ISO, "collectors": [{"name","status","records","error"}], "version"}` | W1 |
| `GET /api/events?days=&lane=&repo=&kind=&limit=` | `[{id, ts_utc, kind, repo, lane, artist, title, link, receipt_status, receipt_detail}]`, newest first. `days` omitted means everything indexed (the 90-day horizon); `limit` defaults to 500 | W1 |
| `GET /api/inbox?state=open\|resolved\|all` | folded inbox items (03 schema) | W2 |
| `POST /api/inbox` | ask (same fields as CLI `ask`) → `{"id"}` | W2 |
| `POST /api/inbox/<id>/resolve` `{answer}` · `/snooze` `{until}` · `/reopen` `{note}` | `{"ok": true}` | W2 |
| `POST /api/refresh` | re-index; `{"ok": true, "indexed_at"}` | W1 |
| `GET /api/repos` | `repo_state` rows | W3 |
| `GET /api/artists`, `GET /api/artists/<name>` | artist + songs + profile + maps | W4 |

All POSTs: Origin guard (Security below); JSON body; 400 on validation error with `{"error": "..."}`.

## Runtime contract (`deployed-runtime-verification` rule)

| Item | Value |
|---|---|
| Machine | Nikola's home PC only (Windows 10, D: HDD) |
| Interpreter | `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`, Python 3.11.9 |
| Third-party deps | Flask 3.1.3 (already installed). Declare the extra `hub = ["flask>=3.1"]` in `pyproject.toml` (W0) |
| External tools | `git` on PATH (read-only subcommands only, see allow-list below) |
| Network | none (bind `127.0.0.1`; no CDN, no external fetch) |
| Data dir | `toolshop.paths.subdir("hub", create=True)`, i.e. `TOOLSHOP_DATA_DIR/hub/` |
| Workspace root | parent of the Toolshop repo root (`D:\Projects`), overridable with env `HUB_WORKSPACE_ROOT` |
| Timezone | `zoneinfo.ZoneInfo("Europe/Belgrade")` (needs `tzdata`, which is present in the venv on 2026-10-06; selfcheck must load it) |
| Port | 8790 (free on 2026-10-06; the ports in use are 8777/8778 audition, 5174 MAirina, 5040). Use `--port` to override |

`python -m toolshop.hub selfcheck` must check every item above. It exits non-zero and prints the
failing item when any check fails.

## Git access: read-only allow-list

The git collectors may run only these commands, through one helper `_git(repo, *args, timeout=10)`:
- `log`
- `rev-list`
- `status --porcelain`
- `worktree list --porcelain`
- `cat-file -e`
- `branch -r --contains`
- `for-each-ref`
- `rev-parse`
- `stash list`

A unit test asserts that the helper refuses anything else, e.g. `commit`, `push`, `checkout`, `fetch` and `gc`.
The helper must not run `fetch` either: ahead/behind is measured against the last-fetched remote refs, and the UI
says "as of last fetch".

## Security

- Bind `127.0.0.1` only, never `0.0.0.0`.
- **Origin guard on every POST.** Reject the request (403) unless its `Origin` header (or its `Referer` when
  `Origin` is absent) is `http://127.0.0.1:<port>` or `http://localhost:<port>`. This blocks drive-by POSTs
  from other sites open in the browser.
- **Escape everything.** Jinja autoescape stays on. Bodies from markdown sources render as **plain text** with URLs
  linkified by a safe helper; raw HTML from sources is never rendered.
- **Path safety.** File links open only through `/file?path=…`, and only for paths that resolve inside the
  workspace root. Text files show read-only; SVGs are inlined only from the `artists/` tree.

## Error handling (the page never goes blank)

- **One collector failing never breaks the index.** Each collector runs inside try/except. A failure becomes a
  `collector_status` row (`ok | degraded | failed`, plus the error text), and the other collectors still run.
- **Visible but not blocking.** Home shows a degraded banner listing the failed sources (contract
  `s0b_degraded`). The rest of the page renders from the data that did index.
- **Missing source paths** count as `degraded` with the message "path not found: …", not as a crash.
- **Git timeouts** (10 s per call) mark only that repo as degraded.
- **A corrupt `inbox.jsonl` line** is skipped and reported (line number). It is never rewritten: the
  file is append-only and the hub repairs nothing silently.
- **Run log.** `scripts/hub.ps1` appends `timestamp | user@host | launch | outcome` to `hub.log` before starting
  Python (`run-logging-deployed-tools` rule). `serve` and `index` append their own lines.
  `hub.log` lives in the data dir, which is git-ignored.

## Refresh model

- **Index on serve start,** and again on `POST /api/refresh` (the header button).
- **No background watcher in v1.**
- **Fast re-index.** Collectors cache by file mtime and git HEAD inside `hub.db`, so an unchanged source is skipped.
- **Freshness** shows in the header as "indexed N min ago".

## Testing strategy

- **Fixture workspace.** `tests/hub_fixtures.py` builds a temporary workspace containing two tiny git repos
  (commits with `feat(mairina): …`, `docs(beat-flip): …` and `submodule: x -> y` subjects, plus one unpushed
  commit through a bare "origin"), session records in both filename schemes, a handoff, two ledgers of different
  shapes, an audition JSONL and an inbox JSONL.
- **Unit tests** cover each collector, receipts (exists+pushed / exists-local / missing / none-cited), the inbox
  fold (open→resolve→reopen), the git allow-list, config path resolution and the Origin guard.
- **Route tests** use the Flask test client and assert the `04` section anchors (`data-section="…"`) plus the copy
  strings. Every `06` check is a pytest node or a stdlib one-liner.
- **Non-mutation test.** Snapshot `git status --porcelain` of the fixture repos, run index and serve, assert they
  are identical.
- **Browser check (orchestrator, at each UI gate).** Home is rendered in a real browser, in light and dark mode at
  1280 px and 390 px, and screenshots go into the ledger.
