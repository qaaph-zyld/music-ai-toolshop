# Audition-review workflow — commented listening pages

**Status:** LIVE (created 2026-10-04, first use = OGCM G3 organ ear test)
**Tool:** `scripts/audition_review.py` (stdlib only, `.venv` Python 3.11.9)
**Log:** `<served-root>/_audition_comments/<page-slug>.jsonl`

---

## What this is

A repeatable way to run ear-test gates: a local server that shows the audition
pages the pack pipelines already produce, with a **verdict select + comment
box beside every player**. Comments persist to a JSONL log that the agent
reads back and records into the lane ledger.

It does NOT replace the `:8777` static server (`python -m http.server 8777`
rooted at `Stemmeca_alatkka/stems`) — that one stays for the pack gates
(`check_audition_serve.py` keeps targeting it). The review server runs
alongside on **`:8778`**, same root, same URLs, plus the comment layer.

## Why serve-time injection

Existing pages must never be rewritten on disk:

- `beats/nachtfahrt_flip/release_manifest.json` sha256-hashes `index.html`.
- `flip_sample/index.html` is agent-curated prose appended per wave
  (no Python writer exists); a scripted rewrite would fight the convention.

So the server injects `<script src="/__audition__/comments.js">` into any
served `.html` **at serve time**. Disks stay byte-identical; manifests stay
valid; agent edits to pages never collide with the tool.

## The workflow

1. **Pack** — put the audio under `Stemmeca_alatkka/stems/<pack>/` (gitignored
   data root). If the pack has no `index.html` yet, generate one:

   ```
   .venv\Scripts\python.exe scripts\audition_review.py page --dir <pack_dir> --title "<name>" [--note "<why these files>"]
   ```

   Never run `page` against agent-curated indexes (`flip_sample/`, the beats
   packs) — it would overwrite them. Curated pages work as-is: the widget
   attaches to every `<audio>` element it finds.

2. **Serve**

   ```
   .venv\Scripts\python.exe scripts\audition_review.py serve --root <stems> --port 8778
   ```

   Background process; leave it running. `127.0.0.1` only, no deps.

3. **Listen** — open `http://127.0.0.1:8778/<pack>/`. Under every player:
   verdict select (`pick` / `ok` / `flag` / `reject`) + comment box + Save.
   Each entry appends `{ts_utc, audio, verdict, comment}` to
   `<stems>/_audition_comments/<page-slug>.jsonl`. Reloading the page
   pre-fills what was already saved.

4. **Review (agent)** — read the log:

   ```
   .venv\Scripts\python.exe scripts\audition_review.py comments --root <stems> [--page <slug>]
   ```

   Dispositions get recorded in the lane ledger by the agent. For a pick-one
   gate (like OGCM G3): the item(s) marked `pick` decide the choice; comments
   become the rationale. The agent records — the ear verdict is the user's.

5. **Gates** — unchanged. `check_audition_serve.py` still validates `:8777`
   static serving; `:8778` is additive and needs no gate.

## Comment log format

One JSON object per line, UTF-8, append-only:

```json
{"ts_utc": "2026-10-03T22:53:35+00:00", "audio": "audition_s6/s6_00_drive_control.wav", "verdict": "pick", "comment": "..."}
```

- `audio` = the player's `src` relative to the page (stable across page edits).
- Latest entry per `audio` wins on read; the file keeps full history.
- Page slug: `/flip_sample/` → `flip_sample`, `/beats/x/` → `beats_x`.

## Failure modes

- Port taken → `serve` prints the OS error; pick another `--port`.
- `verdict` outside the allowed set / empty verdict+comment / body >64 KB → 400.
- A page saved on `:8778` but browsed on `:8777` shows no widgets (static
  server has no injection) — open the same URL on `:8778`.

## Files

- `scripts/audition_review.py` — serve | page | comments
- `tests/test_audition_review.py` — 22 tests (injection, passthrough,
  comment round-trip, page isolation, guards, generator, reader)
- This spec.
