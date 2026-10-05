# 05 — Waves (implementation plan)

How each wave runs:
- **One wave = one fresh Devin session** started from `prompts/W<N>.md`.
- Every wave ends with:
  1. the builder's handoff entry in `LEDGER.md`;
  2. the builder **stopping**;
  3. orchestrator verification;
  4. the merge to `master`.
- **Checks:** `06_EXPECTED_OUTCOMES.md` lists the outcome ids per wave, and the wave's gate requires all of them
  to pass. Builders run the checks and paste the raw output. They never edit `checks/contract_checks.py`.
- **Paths:** all commands use absolute paths. While building, the repo root is the worktree
  `D:\Projects\Music-AI-Toolshop-wt-hub`; after merge it is `D:\Projects\Music-AI-Toolshop`.

## W0 — Lane setup + skeleton (≈40k tokens)

- [ ] **Preflight.**
  - `git -C D:\Projects\Music-AI-Toolshop status --porcelain` shows only other lanes' known dirt; record it in the
    ledger.
  - `git -C D:\Projects\Music-AI-Toolshop log -1` is noted as the base.
- [ ] **Create the lane.** Run
  `git -C D:\Projects\Music-AI-Toolshop worktree add D:\Projects\Music-AI-Toolshop-wt-hub -b lane/hub master`.
  - All work from here on happens in that folder.
  - Use the parent's `.venv` python. It is installed editable, so `toolshop` resolves to the **parent**
    checkout, not the worktree. To test the worktree code, run pytest with `cwd` = the worktree and
    `PYTHONPATH=D:\Projects\Music-AI-Toolshop-wt-hub`.
  - Verify with `python -c "import toolshop.hub,sys;print(toolshop.hub.__file__)"` and paste the output.
  - **Don't init submodules in the worktree.** The hub reads its data from the main checkout
    (`hub_config.json` → `parent_repo`), so the worktree only carries code.
  - The ledger you write is the **worktree copy** `D:\Projects\Music-AI-Toolshop-wt-hub\ORCHESTRATION\hub\LEDGER.md`,
    committed on `lane/hub`. It reaches master with the merge.
  - Run checks with the worktree's copy of `checks/contract_checks.py`. It tests the code beside it and the data in
    the main checkout.
- [ ] **Package skeleton.** Create `toolshop/hub/` with `__init__.py`, `__main__.py`, `config.py` and
  `hub_config.json` (initial content below), plus `models.py`, an empty `collectors/__init__.py` registry,
  `app.py` (factory + `GET /api/health` returning collectors=[]) and `templates/base.html`.
  - `static/hub.css` holds the token block copied **exactly** from `MAirina_Tucc/rimer-ui/src/index.css:2-48`,
    including the dark blocks.
- [ ] **CLI.**
  - `serve` (port 8790, host 127.0.0.1, refuses any other host) and `selfcheck`, which checks every
    runtime-contract item in `01`.
  - The other subcommands exist as stubs that exit 2 with "not implemented in W0".
- [ ] **Dependency extra.** Add `hub = ["flask>=3.1"]` to `pyproject.toml` `[project.optional-dependencies]`.
  Don't reinstall anything; Flask 3.1.3 is already in the venv.
- [ ] **Launcher.** Write `scripts/hub.ps1`, ASCII-only, verified with the ascii-only-powershell rule's byte check.
  - It appends `timestamp | user@host | launch | start` to `<data>/hub/hub.log`, starts `serve` and opens the browser.
- [ ] **Tests.**
  - `tests/hub_fixtures.py` builds the fixture workspace described in `01` § Testing strategy.
  - `tests/test_hub_skeleton.py` covers selfcheck, health, host refusal and config path resolution.
- [ ] **Gate G0:** outcomes **O0.1–O0.4** in `06`. Commit with explicit pathspecs. Ledger entry. STOP.

Initial `toolshop/hub/hub_config.json`. Paths are relative to the workspace root (`D:\Projects`):

```json
{
  "parent_repo": "Music-AI-Toolshop",
  "extra_repos": [],
  "receipt_extra_repos": ["ai_dev_meta_layer", "."],
  "horizon_days": 90,
  "sessions_glob": "ai_dev_meta_layer/memory/episodic/sessions/*.md",
  "handoffs_glob": ".workspace_archive/handoffs/*.md",
  "ledger_globs": [
    "Music-AI-Toolshop/ORCHESTRATION/*/LEDGER.md",
    "Music-AI-Toolshop/ORCHESTRATION/*/ledger.md",
    "Music-AI-Toolshop/handoffs/*.md",
    "Music-AI-Toolshop/studio/artists/*/ledgers/*.md",
    "Music-AI-Toolshop/studio/handoffs/*.md",
    "Music-AI-Toolshop/studio/ORCHESTRATION/*/ledger.md"
  ],
  "audition_comments_dir": "Music-AI-Toolshop/Stemmeca_alatkka/stems/_audition_comments",
  "audition_base_url": "http://127.0.0.1:8778",
  "active_marker": ".workspace_archive/orchestration/ACTIVE",
  "music_keywords": ["Music-AI-Toolshop", "music_toolshop_v2", "studio", "MAirina", "Tale", "Zeldi", "MixAll",
                     "PE3", "Arpino", "OGCM", "OGCJ", "Nachtfahrt", "lyrics", "Stemmeca", "Stemecca", "suno",
                     "audition", "mastering", "vocal chain", "voice profile", "beat"],
  "lane_rules": [
    {"repo": "studio", "path_regex": "^artists/([^/]+)/", "lane": "$1", "artist": "$1"},
    {"repo": "*", "path_regex": "^ORCHESTRATION/([^/]+)/", "lane": "$1"},
    {"repo": "studio", "path_regex": "^(analysis|pipeline|evaluation|tools|voice_profiles|genre_profiles)/", "lane": "studio-engine"},
    {"repo": "Music-AI-Toolshop", "path_regex": "^toolshop/hub/", "lane": "hub"},
    {"repo": "Music-AI-Toolshop", "path_regex": "^MAirina_Tucc$", "lane": "mairina"},
    {"repo": "Music-AI-Toolshop", "path_regex": "^studio$", "lane": "studio"}
  ],
  "lane_aliases": {"beat-flip": "nachtfahrt", "beat": "nachtfahrt", "ogcm": "ogcm", "ogcj": "ogcj",
                   "lyrics": "lyrics", "mairina": "mairina", "vocal-chain": "studio-engine",
                   "engine": "studio-engine", "hub": "hub", "remix": "sample-forge"},
  "pack_artist_rules": [],
  "profile_caveats": {"*": "sibilance measured on fricative events; cap ~8.95 kHz (F15)"},
  "timezone": "Europe/Belgrade",
  "port": 8790
}
```

## W1 — Data spine (≈120k tokens)

- [ ] **`models.py`.** Write the dataclasses from `03`.
- [ ] **`collectors/__init__.py`.** Registry plus `CollectorResult(status, records, error, duration_ms)`.
  - Each collector runs isolated, per the `01` error-handling rules.
- [ ] **`_git` helper.** Applies the read-only allow-list from `01`, with a 10 s timeout. Unit-test that it refuses
  `commit`, `push`, `checkout`, `fetch` and `gc`.
- [ ] **`collectors/git_log.py` (S1).**
  - Repo discovery: parent, `.gitmodules` paths and worktrees.
  - Dedupe by hash.
  - Lane/artist attribution per `02` S1 (the order is **tested**).
  - `pointer_bump` detection.
- [ ] **`collectors/sessions.py` (S2).**
  - Handles both filename schemes and `ts_approx`.
  - Applies the music filter.
  - Excerpt rules as in `02`.
- [ ] **`collectors/handoffs.py` (S3).** Includes the spent flag (cited by a newer session record).
- [ ] **`collectors/ledgers.py` (S4).**
  - Ledgers are Docs plus `ledger_update` events.
  - No cell-to-state parsing.
- [ ] **`collectors/audition.py` (S5).**
  - Emits `listen_verdict` events.
  - Builds page links from the slug.
  - Malformed lines are skipped and counted.
- [ ] **`store.py` + `collectors/inbox.py` (S6).**
  - Append, validate and fold. The file is never rewritten.
  - Exit code 2 on invalid ops.
- [ ] **`receipts.py`.** Implements `03` § Receipts exactly, including `receipt_extra_repos`, and caches per
  (hash, repo HEAD).
- [ ] **`index.py`.**
  - Atomic rebuild (`hub.db.tmp`, then integrity check, then `os.replace`).
  - Writes `collector_status`.
  - Skips sources whose mtime/HEAD is unchanged.
- [ ] **CLI `index` and the JSON API.**
  - CLI: `index` prints a per-collector summary table.
  - API: `GET /api/health`, `GET /api/events`, `POST /api/refresh`, with the Origin guard on POST.
- [ ] **Tests** (`tests/test_hub_collectors.py`, `test_hub_receipts.py`, `test_hub_store.py`, `test_hub_index.py`).
  - All four receipt states must be covered, plus both session filename schemes and every ledger shape listed
    in `02`.
  - Add a **non-mutation** test over the fixture repos.
- [ ] **Real-workspace dry run.**
  - Run `python -m toolshop.hub index` against `D:\Projects` and paste the summary.
  - Note any collector that is not `ok`.
- [ ] **Gate G1:** outcomes **O1.1–O1.6**. In addition, the orchestrator reconciles the counts independently.
  Commit. Ledger entry. STOP.

## W2 — Home: Inbox + Journal UI (≈120k tokens)

- [ ] **Templates.**
  - `base.html` (header s0_header/s0a_health/s0b_degraded, nav linking only existing views).
  - `home.html` (s1_inbox, s1a_item, s2_journal, s2a_filters, s2b_day, s2c_row, s2d_receipt, s2e_lastvisit).
  - `inbox.html` (s5_inbox_full) and `journal.html` (paged).
  - Follow `04` exactly: copy strings, data-* anchors and states.
- [ ] **`static/hub.css`.** Components use only the tokens, and **no hex outside the token block**.
  - Responsive rules: stack below 760 px, Inbox first, nav hidden.
- [ ] **`static/hub.js`** (vanilla, no build):
  - client-side filters plus query-string sync;
  - Refresh button showing "Indexing…" while disabled;
  - inline Resolve and Snooze forms (POST, inline error);
  - the last-visit marker (`localStorage`, try/catch).
- [ ] **Inbox write paths.**
  - CLI `ask/resolve/snooze/reopen/note/list/import-seed` per `03`.
  - API `GET /api/inbox`, `POST /api/inbox`, and `/resolve`, `/snooze`, `/reopen`.
- [ ] **Read-only pages.** `/file?path=` (only inside the workspace root, else 404) and `/commit/<repo>/<hash>`
  (`git show --stat` via the allow-list).
- [ ] **Seed the real inbox.** Run `python -m toolshop.hub import-seed D:\Projects\Music-AI-Toolshop\ORCHESTRATION\hub\seed_inbox.jsonl`
  and paste the resulting ids.
- [ ] **Tests.** `tests/test_hub_routes.py` uses the Flask test client: section anchors, copy strings, Origin guard,
  path traversal refused, and journal sort.
- [ ] **Gate G2:** outcomes **O2.1–O2.8**.
  - The orchestrator then runs a browser verification in light and dark mode, at 1280 px and 390 px.
  - Then comes the **USER GATE**: Nikola uses the real page for a day and gives a verdict in `LEDGER.md`.
  - Commit. STOP.

## W3 — Lanes & repo health (≈70k tokens)

- [ ] **`collectors/repo_state.py` (S7).** Covers branch, HEAD, modified/untracked, ahead/behind ("as of last
  fetch", **no fetch**), stashes, pointer drift, worktrees and the ACTIVE marker.
- [ ] **Health pills.** Fill the `s0a_health` pills: dirty, unpushed, guard overridden.
- [ ] **`/lanes` page.**
  - `s3_repos` table with the required anchors.
  - `s3a_marker`, with an `s3a_override` element per line.
  - `s3b_lanes`, with activity status active/quiet/dormant.
- [ ] **Optional S9 changelog collector.** Its kind is shown only via the journal filter.
- [ ] **Tests.** A fixture with a dirty repo, an ahead commit, a drifted pointer and a marker with 2 overrides.
- [ ] **Gate G3:** outcomes **O3.1–O3.4**. Commit. STOP.

## W4 — Artists (≈110k tokens)

- [ ] **`collectors/artists.py` (S8).** Covers the ARTIST.md songs table, voice profile (confidence rule from `04`),
  chain maps, packs (`pack_artist_rules`) and ledgers.
- [ ] **Pages.**
  - `/artists` grid (s4_artist_grid).
  - `/artists/<name>` with s4a_songs, s4b_profile (de-esser shown as **linear**), s4c_chainmaps (inline SVG
    **sanitised**: strip `<script>`, `on*` attributes and external hrefs; unit-test the sanitiser), s4d_packs
    and s4e_ledgers.
- [ ] **Fill `pack_artist_rules`** in `hub_config.json` from the real `Stemmeca_alatkka/stems/**/index.html` packs.
  List them in the ledger for Nikola to confirm.
- [ ] **Update `/mix_svg_tree`.** Change the SKILL text from `ORCHESTRATION/<song>/` to
  `artists/<name>/rounds/<round>/`.
  - The canonical copy is `D:\Projects\ai_dev_meta_layer\.windsurf\skills\mix_svg_tree\SKILL.md`, in a
    **separate repo**. Make a separate commit there, then run `python scripts/sync_windsurf.py` from the framework
    root.
  - Paste the diff and the commit hash.
- [ ] **Tests.** A fixture artist with a profile (normal + low-SNR), an SVG that contains a `<script>`, and a
  songs table with an existing and a missing source.
- [ ] **Gate G4:** outcomes **O4.1–O4.5**. Commit. STOP.

## W5 — Agent integration + hardening (≈60k tokens)

- [ ] **AGENTS rules.** Add one rule to the "Boundaries & lanes" section of `Music-AI-Toolshop/AGENTS.md`,
  `studio/AGENTS.md` and `MAirina_Tucc/AGENTS.md`. Each is a small edit and a separate commit per repo; submodule
  commits come first and the parent pointer bump last. The rule:

  > **When you need Nikola** (a decision, ear test, sign-off or input), run
  > `python -m toolshop.hub ask …` instead of burying it in a ledger. At session start, run
  > `python -m toolshop.hub list --resolved-since <last session>` to read the answers.
- [ ] **Backup coverage.**
  - Add `TOOLSHOP_DATA_DIR/hub/inbox.jsonl` to `toolshop/backup.py`.
  - Add a test asserting it appears in the backup manifest (AGENTS.md "Backups are verified by coverage").
- [ ] **Run log.** `serve` and `index` append lines to `hub.log`. Test that a launch line appears.
- [ ] **Docs.**
  - Add a PROJECTS_INDEX row for `hub` and a README "Music Hub" paragraph, both in the merge commit (rule R3).
  - Add a CHANGELOG entry, with its ID allocated at merge.
- [ ] **Final gate G5:** outcomes **O5.1–O5.5**.
  - O5.4 runs **all** contract checks.
  - Full Toolshop pytest: no new failures against the W1 baseline (1,965 passed / 1 skipped / 21 deselected on
    2026-10-05).
  - `toolshop closeout` clean.
- [ ] **Ledger.** Write the final ledger entry. The orchestrator performs the final adversarial verification. Then
  merge and remove the worktree (`git worktree remove`).

## Token budget

| Wave | Main cost | Estimate |
|---|---|---|
| W0 | skeleton, config, selfcheck, launcher | ~40k |
| W1 | 7 collectors + receipts + index + tests | ~120k |
| W2 | 4 templates, css, js, inbox API/CLI, route tests | ~120k |
| W3 | repo_state + lanes page | ~70k |
| W4 | artists collector + pages + sanitiser + skill update | ~110k |
| W5 | rules in 3 repos, backup coverage, docs, final gate | ~60k |

Every wave is ≤200k, so each runs in its own window (the `plan-token-budget` rule). Bootstrap prompts are in
`prompts/`.
