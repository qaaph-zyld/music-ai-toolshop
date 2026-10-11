FRAMEWORK BOOTSTRAP — Execute in order:
1. Read `D:\Projects\ai_dev_meta_layer\framework_loader.md`; load `D:\Projects\Music-AI-Toolshop\AGENTS.md` (lane rules, close-out discipline).
2. Draft a short plan (checklist below is the scope). Do not start coding until the plan is written into the lane folder.
3. When done: handoff + git evidence (section "Close-out"), then STOP. Do not merge to master.

MY TASK: Overwrite the `/audition_review` workflow (the user calls it `/audition-review`; same workflow, KEEP the
filename `audition_review.md`) with the listening-page workflow we used on Moj Grad, generalised so every song
gets the same page. Reference page, live: http://127.0.0.1:8778/mojgrad_khansovac_122/ . Reference
implementation of the page decoration: `D:\Projects\Music-AI-Toolshop\.scratch\mojgrad_sync\build_page.py`
(read it first: GROUPS, TODO, STYLE, LEGEND, SCRIPT are exactly what the tool must produce).

## Where to work (lane rules: one lane = one branch + one worktree)

- Base branch: `audition-autosave` (2 commits NOT on master: 21f3336 Range support, 26dd87c autosave on change/blur).
- Create: `git -C D:\Projects\Music-AI-Toolshop worktree add D:\Projects\Music-AI-Toolshop-wt-audition-v2 -b lane/audition-review-v2 audition-autosave`
- Do NOT touch: master's working tree (its `scripts/audition_review.py` + tests carry old uncommitted dirt that
  21f3336 supersedes), `D:\Projects\Music-AI-Toolshop-wt-audition`, `toolshop/hub/`, `ORCHESTRATION/hub/`.
- Do NOT stop or restart the user's server on :8778. Test your build on **port 8781**.
- Python: `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`. Run everything with cwd = the worktree root;
  first prove the import resolves to the worktree:
  `python -c "import scripts.audition_review as m; print(m.__file__)"` must print a `...wt-audition-v2...` path.

## Hard constraints

- **Comment log contract is frozen**: `_audition_comments/<slug>.jsonl` under the serve root, the `_slug()`
  function, the JSONL fields (`ts_utc, audio, verdict, comment`), and `GET /__audition__/comments?page=` output
  must not change. The Music Hub (W1 `collectors/audition.py`, see `ORCHESTRATION/hub/05_WAVES.md`
  `audition_comments_dir` / `audition_base_url`) reads them.
- Stdlib only, no new dependencies. Audio never in git. Commit by explicit pathspec, never `git add -A`.
- Backward compatible: a pack WITHOUT `audition.json` renders exactly as today; curated pages (e.g. the
  stems-root `index.html` "GATE F", `beats/*/index.html`) are never overwritten.
- TDD: extend `tests/test_audition_review.py` first (32 tests today on the base branch; all must still pass).

## Build (tool: `scripts/audition_review.py`)

1. **Per-pack config `<pack>/audition.json`** (one pack = one song review):
   ```json
   {"title": "Moj Grad khansovac — review", "artist": "MixAll", "song": "Moj Grad",
    "todo": "<html: what to listen to NOW, what to compare, where to listen hardest>",
    "groups": [
      {"prefix": "_PREV_beatfit_", "state": "listen", "label": "LISTEN NOW - your tempo: your vocal untouched, beat adapted"},
      {"prefix": "_PREV_song_",    "state": "heard",  "label": "listened - whole song v3 (your vocal warped to the beat)"},
      {"prefix": "_PREV_wsync_",   "state": "heard",  "label": "done - section v2 (final rendered)"},
      {"prefix": "_PREV_v",        "state": "rej",    "label": "rejected - constant-stretch round"},
      {"prefix": "",               "state": "ref",    "label": "source / reference"}]}
   ```
   States and colours exactly as build_page.py: `listen` green #3ccf5a, `heard` yellow #e6c229,
   `rej` red #e04848 + row opacity .55, `ref` grey #555; row background tints and the 8 px left border; the
   label shown as a small tag above the filename (`data-tag` + `::before`). First matching prefix wins.
2. **`page` with a config** renders: title, legend (4 colour chips), the green-bordered "Listen now" TODO box,
   then the table with rows **ordered by group order** (listen groups on top; alphabetical inside a group). Our
   interim page relied on alphabetical luck; the tool must not.
3. **Live state in the browser** (same rules as build_page.py's SCRIPT): a saved `reject` → red "rejected by
   you"; any saved verdict/comment, or the file played past 50% (localStorage key
   `played:<location.pathname><src>`, every access in try/catch) → yellow "listened - <verdict>"; groups whose
   state is `rej` stay red. With autosave there is no save click any more: make WIDGET_JS dispatch
   `document.dispatchEvent(new CustomEvent("audition:saved", {detail: {audio, verdict}}))` after a successful
   POST, and have the page re-fetch comments and repaint on that event.
4. **`round` subcommand**: the "mark the last batch yellow, new batch green" operation:
   `audition_review.py round --dir <pack> --prefix _PREV_<round>_ --label "<LISTEN NOW - ...>" --todo "<html>"`
   inserts the new group first with state `listen`, flips every previous `listen` group to `heard` (labels:
   "listened - ..."), writes `audition.json`, regenerates the page. **Refuse** (non-zero exit) a prefix that
   already matches existing files from an earlier round. A reused prefix once made a check pass with zero new
   work: `_PREV_v2_` matched an old rejected file.
5. **Song list**: `GET /__audition__/songs` lists every pack under the root that has an `audition.json`: title,
   artist, link, number of `listen` files, latest verdict time from its JSONL. It must not touch `/` (the root
   has a curated index.html).
6. **`check` subcommand**: `audition_review.py check --page <slug> [--port 8778]` → GET the page (expect 200)
   and a `Range: bytes=0-99` GET for every `<audio src>` in the listen groups (expect 206); print each; exit
   non-zero on any failure. Reason: on 2026-10-06 the long-running :8778 server returned an empty reply (curl 000)
   for every file while its comment endpoints still answered 200; only a per-file probe catches that.

## Overwrite the workflow (framework repo, separate git repo!)

Canonical: `D:\Projects\ai_dev_meta_layer\.windsurf\workflows\audition_review.md`; mirrors must end
byte-identical: `D:\Projects\.windsurf\workflows\audition_review.md`, `D:\Projects\.devin\workflows\audition_review.md`
(all three are identical today, sha256 prefix 428b916f9270). Keep the frontmatter `description:` line format.
Then regenerate the index (`python ai_dev_meta_layer/scripts/gen_index.py`, cwd `D:\Projects`).
New workflow content, phases in this order:

0. **One pack per song**: `Stemmeca_alatkka/stems/<artist>_<song>[_<variant>]/` + `audition.json`. Do NOT move
   packs into the Studio repo yet: the per-song workspace location is still being designed.
1. **Render a round**: files `_PREV_<round>_<n>_<label>.mp3`, a round prefix never reused. Every round has
   1-4 green files: one reference row (the track or source as it is now) and variants that differ in ONE
   variable. Labels state the value actually applied AND its reference (e.g. "lead +7.5 dB over original
   vocal"). If a ceiling or cap changed it, label the real value (a "+10 dB" file once really was +8.3).
   Loudness-match previews to -16 LUFS by static gain, peak <= -1 dBFS, never a limiter, mp3 192k/48k. Never
   delete earlier rounds.
2. **Publish**: `round ...`, then `check --page <slug>` must exit 0, and every listen file's mtime must be
   newer than the inputs it was rendered from (freshness bound).
3. **Serve**: the USER starts the server in their own terminal (give them the exact command). An agent's
   background job is killed at its 2 h limit, observed 2026-10-06. The agent only runs `check`.
4. **Human gate**: in chat, tell the user exactly what to listen to: which green rows, what to compare, the
   timestamps to listen hardest at, and "pick ONE and the dropdown saves". The ear verdict is the user's.
5. **Readback before any final**: `audition_review.py comments --page <slug>`. If no pick is logged, ask. Never
   assume a pick: a pick was lost on 2026-10-05 because the old widget needed a save click. Comments can carry
   new requests ("mix my a cappella completely…"), so read them in full.
6. **Final**: render only the picked variant, then either open the next round (`round`) or mark the song done
   (all groups `heard`/`rej`).

Keep the existing rules: 127.0.0.1 only; serve-time injection never rewrites files on disk; the agent never picks.

## Acceptance (paste every output into the handoff)

- A1 `pytest D:\Projects\Music-AI-Toolshop-wt-audition-v2\tests\test_audition_review.py -q` → all pass, count
  > 32. New tests at least cover: config ordering + states in HTML, no-config output unchanged, `round` flips
  listen→heard and refuses a reused prefix, `/__audition__/songs` lists only packs with config, `check` exits
  non-zero on a missing file, WIDGET_JS dispatches `audition:saved`, JSONL schema unchanged.
- A2 Migrate the reference pack: write `Stemmeca_alatkka/stems/mojgrad_khansovac_122/audition.json` reproducing
  build_page.py's GROUPS/TODO exactly; run `page`; serve on **8781**; in a browser, the row states must match the
  live :8778 page: 2 green (beatfit 1, 2), 14 yellow, 4 red, 5 grey (total 25) — report the counts from the DOM.
  Note: the regenerated index.html is shared with :8778 (same files); that is intended.
- A3 `check --page mojgrad_khansovac_122 --port 8781` → exit 0, every listen file 206.
- A4 `GET http://127.0.0.1:8781/__audition__/songs` lists mojgrad_khansovac_122 (and nothing without config).
- A5 sha256 of `_audition_comments/mojgrad_khansovac_122.jsonl` identical before and after your whole run
  (tests must use tmp dirs).
- A6 the three workflow copies hash-identical; gen_index route count printed.
- A7 stop the :8781 server you started; leave :8778 alone.

## Close-out (then STOP)

- Commits: (1) Toolshop lane `lane/audition-review-v2`: code + tests, subject `feat(audition-review-v2): ...`;
  (2) `ai_dev_meta_layer` repo: workflow + mirrors + regenerated index, explicit pathspecs. Run
  `git rev-parse --show-toplevel` before each commit; `git add` and `git commit` as separate calls.
- Handoff: `D:\Projects\.workspace_archive\handoffs\<YYYY-MM-DD_HHMM>_audition_review_v2.md` with A1-A7 outputs,
  `git status --porcelain` + `git log -3` for both repos, and every still-dirty path named with the reason.
- Do not merge to master, do not delete branches, do not push unless the user says so. Claude verifies A1-A7
  independently before any merge.
