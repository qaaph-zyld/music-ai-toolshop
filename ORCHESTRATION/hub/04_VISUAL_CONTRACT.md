# 04 — Visual contract (`/define_visual`)

| | |
|---|---|
| Artifact | Music Hub web UI, served by `python -m toolshop.hub serve` |
| Medium | `web` (DOM / selector / computed-style idiom) |
| Source template | `ORCHESTRATION/hub/mockups/home.html` (static mockup, sample data) |
| Token source | `MAirina_Tucc/rimer-ui/src/index.css:2-48`. This is Nikola's most recently approved UI ("design tokens (from the approved mockup)", line 1), with light and dark sets. Copy the values exactly; do not invent new colours. |
| Audience | Nikola, one user, on desktop (≥1280 px) and occasionally phone width (390 px) |
| Primary decision it drives | "What do I need to decide or listen to now, and did the agents really do what they claim?" |

## Rules that apply to every section

- **Every section root carries `data-section="<id>"`** exactly as listed here. The checks key on these anchors, so
  renaming one breaks its gate.
- **Colours only through the CSS custom properties** `--bg --panel --ink --muted --line --accent --accent-ink --ok
  --warn --bad --chip --focus`. Radius is `--radius` (10px); fonts are `--sans` / `--mono`. `hub.css` defines the
  tokens with exactly the values from the token source, including the
  `@media (prefers-color-scheme: dark) { :root:not([data-theme='light']) {…} }` block. No hex colour appears
  anywhere else in `hub.css`.
- **Times show in local time (Europe/Belgrade), 24-hour.** Relative ages read "just now", "N min ago",
  "N h ago", "yesterday", "N days ago".
- **All dynamic text is escaped.** Titles truncate with an ellipsis and keep the full text in `title=""`.
- **Focus is always visible** (`outline: 2px solid var(--focus)`). Every select and input has an `aria-label`.
- **Under 760 px the two columns stack, Inbox first.** The header nav hides.

## Required DOM anchors (the checks read these, so they are part of the contract)

| Element | Required attributes |
|---|---|
| Inbox card (s1a_item) | `data-section="s1a_item" data-id="<inbox id>" data-kind="<kind>" data-blocking="<n>"` |
| Inbox count badge | `data-count="<n>"` inside s1_inbox |
| Journal row (s2c_row) | `data-section="s2c_row" data-id="<event id>" data-ts="<ts_utc ISO>" data-kind data-lane data-repo`; class `muted` on pointer/ledger rows |
| Receipt badge (s2d_receipt) | `data-section="s2d_receipt" data-state="pushed|local|missing|none"` |
| Repo row (s3_repos) | `data-repo` (`Music-AI-Toolshop` for the parent, the `.gitmodules` path for each child, the folder name for a worktree), plus `data-modified data-untracked data-ahead data-behind` |
| Override item (s3a_marker) | `data-section="s3a_override"` per `override:` line |
| Chain map figure (s4c_chainmaps) | `data-section="s4c_map" data-file="<workspace-relative svg path>"` |
| Resolved row on /inbox (s5_inbox_full) | `data-section="s5_resolved_row" data-id` |
| Lane row (s3b_lanes) | `data-lane data-status="active|quiet|dormant" data-last-ts="<ISO>"` |
| Artist card (s4_artist_grid) | `data-section="s4_artist_card" data-artist="<dir name>"` |
| Song row (s4a_songs) | `data-section="s4a_song" data-source-exists="1|0"` |
| Ledger row (s4e_ledgers) | `data-section="s4e_ledger"` per ledger doc |
| Profile card (s4b_profile) | `data-field="<target field name>"` on each value row |

Home shows at most **100** journal rows; `/journal` pages 200 rows at a time.

## Home (`/`, wave W2)

### s0_header: header bar
- **Data:** `meta.indexed_at`, plus counts from `collector_status`.
- **Copy:** title "Music Hub"; nav links "Home", "Journal", and from W3/W4 "Lanes", "Artists". **Only views that
  exist are linked.** The current page has `aria-current="page"`.
- **Visual:** sticky; height 56px; background var(--panel); 1px solid var(--line) bottom border; title 18px/600.
- **States:** always rendered.

### s0a_health: freshness and health
- **Data:**
  - W2: `indexed_at`, ok-source count, total-source count.
  - W3 adds pills: `repos_dirty` (repos with modified+untracked>0), `commits_unpushed` (sum of ahead), and
    `guard_overridden` (the ACTIVE marker has ≥1 `override:` line).
- **Copy:** "Indexed {rel_age} · {ok}/{total} sources"; button "Refresh". Pills read "{n} dirty", "{n} unpushed",
  "guard overridden". A pill is shown only when its value is non-zero / true.
- **Visual:** pills 12px/500 on var(--chip). Dirty and override pills use color var(--warn); unpushed uses
  var(--bad). The Refresh button has background var(--accent) and color var(--accent-ink).
- **States:** while refreshing, the button shows "Indexing…" and is disabled. A failed refresh adds the
  s0b_degraded banner.

### s0b_degraded: degraded sources banner
- **Data:** `collector_status` rows whose status is not 'ok'.
- **Copy:** "{n} source(s) degraded: {name} — {error}" (several sources joined with "; ").
- **Visual:** 1px solid var(--warn) border; color var(--warn); `role="status"`.
- **States:** the `hidden` attribute is set when every collector is ok. It must never block the page.

### s1_inbox: Waiting on you
- **Data:** `inbox` rows with `state='open'`, plus snoozed rows whose `snooze_until` has passed, which count as open.
  Sort by `len(blocking)` descending, then `created_ts` ascending (oldest first). Show the first 6.
- **Copy:** heading "Waiting on you" followed by a count badge with the number of open items. Empty state:
  "Nothing waiting on you." Overflow link: "{n} more · resolved history" to `/inbox`.
- **Visual:** a column panel (var(--panel), 1px var(--line), radius 10px, padding 16px). The count badge has
  background var(--accent).
- **States:** a missing `inbox.jsonl` means the empty state, not an error. Malformed lines are reported in
  s0b_degraded.

### s1a_item: inbox card (repeated)
- **Data:** `kind, title, lane|artist|repo, blocking, links, created_ts, created_by, body`.
- **Copy:**
  - Kind pill: the kind with `_` → space (e.g. "ear test").
  - Context pill: lane, else artist, else repo.
  - "blocks {n} lane(s)" when `blocking` is non-empty.
  - Meta line: "opened {rel_age} by {by}".
  - Body: plain text, first 200 characters.
  - Buttons: "Resolve…" and "Snooze".
- **Visual:** card background var(--bg), 1px var(--line), radius 10px. A blocking card gets
  `border-left: 4px solid var(--accent)`. The kind pill uses var(--mono), 11px, uppercase.
- **Interaction:**
  - **Resolve…** opens an inline form with a textarea labelled "Answer" and the buttons "Save" and "Cancel".
    Save sends `POST /api/inbox/<id>/resolve` with `{answer}` and removes the card on 200.
  - **Snooze** opens a date input (default today+3) and Save, which posts to `POST /api/inbox/<id>/snooze`.
- **States:** a POST error shows inline "Not saved: {error}" in var(--bad), and the card stays.

### s2_journal: Journal
- **Data:** `events` from the last 7 days (Home) or 90 days (`/journal`, 200 rows per page). Sorted by `ts_utc`
  **descending**; ties are broken by id.
- **Copy:** heading "Journal". Footer link "Full journal" to `/journal`. Empty state: "No activity in the last 7 days."
- **Visual:** a column panel like s1_inbox.

### s2a_filters: filter bar
- **Data:** distinct `lane`, `repo` and `kind` values from the displayed events.
- **Copy:** select defaults read "All lanes", "All repos" and "All kinds"; the search placeholder is "Search titles".
- **Behaviour:** filtering happens client-side on Home and server-side (query string) on `/journal`. The choice is
  kept in the URL query (`?lane=&repo=&kind=&q=`).

### s2b_day: day group header
- **Copy:** "Today · {Ddd D Mon}", "Yesterday · {Ddd D Mon}", otherwise "{Ddd D Mon}". English weekday and
  month abbreviations.
- **Visual:** 12px/600, var(--muted), uppercase, 1px var(--line) bottom border.

### s2c_row: journal row (repeated)
- **Data:** `ts_utc` (shown local HH:MM), `kind`, `lane` (or "unassigned"), `title`, `link`, plus `receipt_status`
  for the kinds `session` and `handoff`.
- **Copy:** kind pill labels: commit→"commit", pointer_bump→"pointer", session→"session", handoff→"handoff",
  ledger_update→"ledger", listen_verdict→"listen", inbox_*→"inbox", changelog→"changelog".
- **Visual:** a 4-column grid (time 48px mono 12px var(--muted) | pills | title | receipt). `pointer_bump` and
  `ledger_update` rows get the class `muted` (title in var(--muted)). Rows are separated by 1px var(--line).
- **Links:**
  - `file:` opens `/file?path=…` (read-only text view).
  - `git:` opens `/commit/<repo>/<hash>`, which shows `git show --stat` (read-only allow-list).
  - `http://127.0.0.1:8778/…` opens directly in a new tab.

### s2d_receipt: receipts badge (session and handoff rows only)
- **Copy and class, by state:**

  | State | Class | Copy |
  |---|---|---|
  | `pushed` | `rcpt pushed` | "receipts ✓ {n} pushed" |
  | `local` | `rcpt local` | "receipts: {n} local, not pushed" |
  | `missing` | `rcpt missing` | "receipts ✗ {m} of {n} not found" |
  | `none` | `rcpt none` | "no receipts" |

- **Visual:** pushed var(--ok); local var(--warn); missing var(--bad) at 600 weight; none var(--muted).
- **Tooltip** (`title`): the per-hash list "8a9a5f3 studio pushed; 0a1ece6 studio local …".

### s2e_lastvisit: since your last visit
- **Data:** `localStorage['hub.lastVisit']` (the ISO timestamp of the previous page load; updated on unload).
- **Copy:** "since your last visit". Placed above the first row older than lastVisit.
- **States:** omitted when there is no stored value, or when all rows are newer or all are older. Storage errors
  are caught silently.

## Inbox page (`/inbox`, wave W2)

### s5_inbox_full
- **Data:**
  - **Open list:** the same cards as s1a_item, without the 6-item limit.
  - **History table:** resolved items, newest resolution first, columns Resolved · Title · Answer · By.
- **Copy:** headings "Waiting on you" and "Resolved". Empty history: "Nothing resolved yet."

## Lanes page (`/lanes`, wave W3)

### s3_repos: repo health table
- **Data:** `repo_state` rows, the parent first and then the submodules alphabetically. Linked worktrees are
  indented under their repo.
- **Columns:** Repo · Branch · HEAD · Modified · Untracked · Ahead · Behind · Stashes · Pointer.
- **Copy:**
  - Zero values show as "–".
  - Pointer drift shows "parent pins {a}, child at {b}".
  - The column header tooltip on Ahead/Behind reads "as of last fetch".
- **Visual:** non-zero Modified/Untracked cells in var(--warn); Ahead>0 cells in var(--bad); drift in var(--warn).

### s3a_marker: orchestrator marker
- **Data:** the ACTIVE file's `task:` line and every `override:` line.
- **Copy:** "Orchestrator mode: {task}". Each override is listed. When ≥1 override exists, a warning reads "One
  override suspends the guard for every session (orchestrator-boundary rule)".
- **States:** with no marker file, show "Orchestrator mode: off".

### s3b_lanes: lanes list
- **Data:** per lane, the last event ts, the event count in the last 7 days, open inbox items, and the
  repos touched.
- **Status:** `active` when the lane has events in the last 48 h, `quiet` up to 14 days, otherwise `dormant`.
- **Copy:** status pills "active" / "quiet" / "dormant".

## Artists (`/artists`, `/artists/<name>`, wave W4)

### s4_artist_grid
- **Data:** the `artists` table.
- **Copy:** one card per artist showing its title, the number of songs, profile confidence, the open inbox count,
  and the date of its latest event.

### s4a_songs: songs table (artist page)
- **Data:** `songs` rows.
- **Columns:** Song · Source · Rounds · Status.
- **Source cell:** shows the path in var(--mono) with ✓ in var(--ok) when it exists, or ✗ in var(--bad).

### s4b_profile: voice profile card
- **Data:** `voice_profiles/<name>.json` → `target` fields (f0 range and mean, hpf, sibilance centre and
  bandwidth, de-esser, compressor ratio and threshold), `consequence.snr_db`, and `sources.recording_path`.
- **Confidence:** "low" when `snr_db < 20` or the notes contain "LOW-SNR" / "low-confidence". Otherwise "ok".
- **Copy:** label/value rows with units (Hz, dB). The de-esser shows "linear {v}" and never "dB", because the
  field is linear despite its `_db` name (schema line 41).
- **Caveat line** from `hub_config.json` → `profile_caveats`. Initial caveat: "sibilance measured on fricative
  events; cap ≈ 8.95 kHz (F15)".
- **Visual:** a confidence pill, var(--ok) for "ok" and var(--warn) for "low". Values in var(--mono).
- **States:** no profile file shows "No voice profile measured yet."

### s4c_chainmaps: chain-map gallery
- **Data:** `artists/<name>/**/chain_map*.svg`, newest mtime first.
- **Visual:** each SVG is inlined (sanitised: no `<script>`, no `on*` attributes, no external hrefs) inside a
  panel with `max-width: 100%` and horizontal scroll. Caption: "{round} · {file} · {date}".
- **States:** with no maps, show "No chain map yet — run /mix_svg_tree".

### s4d_packs: listening packs
- **Data:** packs matched through `pack_artist_rules`, with verdict counts from S5.
- **Copy:** "{pack} — {n} verdicts ({picks} pick)". The link goes to :8778.

### s4e_ledgers
- **Data:** `docs` rows for this artist, with title, mtime and excerpt.

## Contract checks

Every check is a command that exits 0 on pass. They are implemented in `ORCHESTRATION/hub/checks/contract_checks.py`
(stdlib only, ASCII literals, written by the orchestrator and **never edited by the builder**).

- **Live checks** need the server running at `HUB_URL` (default `http://127.0.0.1:8790`).
- **Static checks** read files.

```json
{
  "medium": "web",
  "template": "ORCHESTRATION/hub/mockups/home.html",
  "token_source": "MAirina_Tucc/rimer-ui/src/index.css:2-48",
  "checker": "ORCHESTRATION/hub/checks/contract_checks.py",
  "sections": [
    {
      "id": "tokens",
      "wave": "W2",
      "provenance": "file:MAirina_Tucc/rimer-ui/src/index.css:2-48",
      "data": "n/a",
      "copy": "n/a",
      "visual": "hub.css defines the 12 color tokens with the exact light and dark values; no other hex colors in hub.css",
      "states": "n/a",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py tokens"
      ]
    },
    {
      "id": "s0_header",
      "wave": "W2",
      "provenance": "html:mockups/home.html header.hdr",
      "data": "meta.indexed_at",
      "copy": "Music Hub; nav only to existing views",
      "visual": "sticky; height 56px; bg var(--panel); border-bottom 1px var(--line)",
      "states": "always",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s0_header"
      ]
    },
    {
      "id": "s0a_health",
      "wave": "W2 (pills W3)",
      "provenance": "html:mockups/home.html .health",
      "data": "indexed_at, collector_status counts; W3: repos_dirty, commits_unpushed, guard_overridden",
      "copy": "Indexed {rel_age} . {ok}/{total} sources; Refresh",
      "visual": "pills 12px on var(--chip); Refresh bg var(--accent)",
      "states": "Indexing... disabled while refreshing",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s0a_health"
      ]
    },
    {
      "id": "s0b_degraded",
      "wave": "W2",
      "provenance": "html:mockups/home.html .degraded",
      "data": "collector_status != ok",
      "copy": "{n} source(s) degraded: {name} - {error}",
      "visual": "border var(--warn); role=status",
      "states": "hidden when all ok",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s0b_degraded"
      ]
    },
    {
      "id": "s1_inbox",
      "wave": "W2",
      "provenance": "html:mockups/home.html section[data-section=s1_inbox]",
      "data": "inbox open (+expired snoozes), sort blocking desc then created asc, first 6",
      "copy": "Waiting on you + count; empty: Nothing waiting on you.",
      "visual": "panel var(--panel) 1px var(--line) radius 10px; count bg var(--accent)",
      "states": "missing inbox.jsonl -> empty state",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s1_inbox"
      ]
    },
    {
      "id": "s1a_item",
      "wave": "W2",
      "provenance": "html:mockups/home.html article.card",
      "data": "kind,title,lane|artist|repo,blocking,links,created_ts,created_by",
      "copy": "kind pill; blocks {n} lane(s); opened {rel_age} by {by}; Resolve...; Snooze",
      "visual": "blocking card border-left 4px var(--accent); kind pill mono 11px uppercase",
      "states": "POST error -> inline Not saved: {error}",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s1a_item",
        "python ORCHESTRATION/hub/checks/contract_checks.py inbox_roundtrip"
      ]
    },
    {
      "id": "s2_journal",
      "wave": "W2",
      "provenance": "html:mockups/home.html section[data-section=s2_journal]",
      "data": "events last 7 days (home) / 90 days paged (journal), ts desc",
      "copy": "Journal; empty: No activity in the last 7 days.",
      "visual": "panel like s1_inbox",
      "states": "empty",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s2_journal"
      ]
    },
    {
      "id": "s2a_filters",
      "wave": "W2",
      "provenance": "html:mockups/home.html .filters",
      "data": "distinct lane/repo/kind",
      "copy": "All lanes; All repos; All kinds; Search titles",
      "visual": "selects with aria-label",
      "states": "query string persisted",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s2a_filters"
      ]
    },
    {
      "id": "s2c_row",
      "wave": "W2",
      "provenance": "html:mockups/home.html .row",
      "data": "ts local HH:MM, kind, lane|unassigned, title, link",
      "copy": "kind labels per 04 table",
      "visual": "grid 48px|pills|title|receipt; pointer/ledger rows .muted",
      "states": "n/a",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s2c_row"
      ]
    },
    {
      "id": "s2d_receipt",
      "wave": "W2",
      "provenance": "html:mockups/home.html .rcpt",
      "data": "receipt_status + receipt_detail",
      "copy": "four states per 04 table",
      "visual": "pushed var(--ok); local var(--warn); missing var(--bad) 600; none var(--muted)",
      "states": "only on session/handoff rows",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s2d_receipt"
      ]
    },
    {
      "id": "origin_guard",
      "wave": "W2",
      "provenance": "none - new (01_DESIGN Security)",
      "data": "n/a",
      "copy": "n/a",
      "visual": "n/a",
      "states": "POST with foreign Origin -> 403",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py origin_guard"
      ]
    },
    {
      "id": "s3_repos",
      "wave": "W3",
      "provenance": "none - new",
      "data": "repo_state",
      "copy": "columns per 04; zero as en dash",
      "visual": "warn/bad cell colors per 04",
      "states": "per-repo error cell",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s3_repos"
      ]
    },
    {
      "id": "s3a_marker",
      "wave": "W3",
      "provenance": "none - new",
      "data": "ACTIVE task + override lines",
      "copy": "Orchestrator mode: {task}; override warning",
      "visual": "warning in var(--warn)",
      "states": "no file -> Orchestrator mode: off",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s3a_marker"
      ]
    },
    {
      "id": "s4b_profile",
      "wave": "W4",
      "provenance": "none - new",
      "data": "voice_profiles/<name>.json target + snr",
      "copy": "de-esser shown as linear, never dB",
      "visual": "confidence pill ok/warn",
      "states": "no profile -> No voice profile measured yet.",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s4b_profile"
      ]
    },
    {
      "id": "s4c_chainmaps",
      "wave": "W4",
      "provenance": "none - new",
      "data": "artists/<name>/**/chain_map*.svg",
      "copy": "{round} . {file} . {date}",
      "visual": "inline sanitized svg, no script",
      "states": "none -> No chain map yet",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s4c_chainmaps"
      ]
    },
    {
      "id": "s2b_day",
      "wave": "W2",
      "provenance": "html:mockups/home.html .day",
      "data": "local date of each row (Europe/Belgrade)",
      "copy": "Today . Ddd D Mon / Yesterday . Ddd D Mon / Ddd D Mon",
      "visual": "12px 600 var(--muted) uppercase",
      "states": "n/a",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s2b_day"
      ]
    },
    {
      "id": "s2e_lastvisit",
      "wave": "W2",
      "provenance": "html:mockups/home.html .lastvisit",
      "data": "localStorage hub.lastVisit",
      "copy": "since your last visit",
      "visual": "var(--accent) dashed rule",
      "states": "omitted without stored value",
      "checks": [],
      "verify": "browser (orchestrator): depends on client storage, no deterministic server-side check"
    },
    {
      "id": "s5_inbox_full",
      "wave": "W2",
      "provenance": "none - new",
      "data": "inbox state=all",
      "copy": "Waiting on you; Resolved; Nothing resolved yet.",
      "visual": "cards as s1a_item; history table",
      "states": "empty history",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s5_inbox_full"
      ]
    },
    {
      "id": "s3b_lanes",
      "wave": "W3",
      "provenance": "none - new",
      "data": "per-lane last event ts",
      "copy": "active / quiet / dormant",
      "visual": "status pills",
      "states": "n/a",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s3b_lanes"
      ]
    },
    {
      "id": "s4_artist_grid",
      "wave": "W4",
      "provenance": "none - new",
      "data": "artists table",
      "copy": "card per artist",
      "visual": "cards",
      "states": "n/a",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s4_artist_grid"
      ]
    },
    {
      "id": "s4a_songs",
      "wave": "W4",
      "provenance": "file:studio/artists/<name>/ARTIST.md songs table",
      "data": "songs rows",
      "copy": "Song . Source . Rounds . Status",
      "visual": "source mono, exists check ok/bad",
      "states": "n/a",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s4a_songs"
      ]
    },
    {
      "id": "s4d_packs",
      "wave": "W4",
      "provenance": "none - new",
      "data": "packs via pack_artist_rules + S5 verdict counts",
      "copy": "{pack} - {n} verdicts ({picks} pick)",
      "visual": "list",
      "states": "no rules -> none shown",
      "checks": [],
      "verify": "browser (orchestrator) after Nikola confirms pack_artist_rules (07 Q2)"
    },
    {
      "id": "s4e_ledgers",
      "wave": "W4",
      "provenance": "none - new",
      "data": "docs rows for artist",
      "copy": "title, mtime, excerpt",
      "visual": "list",
      "states": "n/a",
      "checks": [
        "python ORCHESTRATION/hub/checks/contract_checks.py s4e_ledgers"
      ]
    }
  ]
}
```
