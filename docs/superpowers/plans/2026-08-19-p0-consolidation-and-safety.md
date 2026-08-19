# P0 — Consolidation + Safety

**Date:** 2026-08-19 · **Author:** orchestrator · **Size:** 1-2 sessions
**Goal:** G0 (consolidated, honest baseline) in `specs/2026-08-19-goals-v2.md`
**Why now:** The backup is **28 days stale** on a destination with **14 GB free (98% full)** while the
corpus it protects nearly doubled. An entire lane (`toolshop/melody_carrier/`, 2,043 LOC + 5 test
files + edits to tracked `cli.py`) sits uncommitted. A second lane (`ai_modules/`, 6,390 LOC) was
committed under a commit message describing a submodule chore, with no CHANGELOG, no STATUS row, no
plan, and its tests outside `pytest.ini`'s collection path. Nothing else in the roadmap starts until
this is true again. Full findings: `specs/2026-08-19-state-of-project-assessment.md`.

**Standing context (do not re-derive):**
- Repo: `D:\Projects\Music-AI-Toolshop`, branch `master`, remote `github.com/qaaph-zyld/music-ai-toolshop`.
- Env: `.venv` Python 3.11 in repo root — ALL pytest runs inside it.
- CI is **billing-locked** (GitHub Actions do not run). Never claim "CI green"; the gate is LOCAL
  pytest with pasted output.
- **Verified baseline 2026-08-19: `963 passed, 2 skipped, 0 failed` in 689.20s.** That is the
  no-NEW-failures bar for this session.
- Data boundary: code in repo, data under `data/` (gitignored). Never commit lyrics, `.env`, or `.db`.
- Close-out discipline: AGENTS.md. Task 9 IS the gate; do not skip it.
- `git status` at plan time: 3 modified (`tests/fixtures/lyrics_min/_dedup_log.json`,
  `toolshop/__init__.py`, `toolshop/cli.py`), 26 untracked. Zero unpushed commits.

---

## Tasks

### Task 1 — BACKUP FIRST (the whole point of this session)

Nothing else runs before the corpus is safe.

1. **Destination — DECIDED (D7 REVISED by user, 2026-08-19): a path on D:, the workspace drive.**
   D: has ~148 GB free, so headroom is a non-issue and no drive needs mounting. C: is abandoned as a
   target (14 GB free, 98% full).
   - **Be honest about what this buys.** A copy on D: protects against accidental deletion, a bad
     script, and working-copy corruption. It does **not** protect against the disk dying — and D: is
     the 2010 Seagate ST9640423AS that holds everything. This is Tier-1 convenience, not DR.
     Record it in the handoff as such; do not let `doctor` returning OK imply DR exists.
   - Second-copy-on-another-disk stays an open item (G5), not a blocker for this session.
   - Set `TOOLSHOP_BACKUP_DIR` to the chosen D: path and persist it as a user env var so future
     sessions and scheduled runs inherit it rather than re-deciding.
2. **FIRST fix what the backup actually covers — see Task 1b. Do not run the backup until it does.**
3. Run the backup: `.venv\Scripts\python.exe -m toolshop.backup --target <D: path>`.
4. Run the verify pass and confirm the manifest covers `data/toolshop/lyrics/lyrics.db`
   (expect ~67 MB, 1,425 songs) **and** the Suno assets added in Task 1b.
5. `toolshop doctor` — the `backup` check must flip from FAIL to OK.

**Exit evidence:** paste the backup summary (file count, bytes, verified=True), the destination path,
free space remaining, and the `doctor` backup line.

**Note:** the backup contains the Genius token from `.env`. Never sync, share, or commit that directory.

---

### Task 1b — CRITICAL: the backup does not cover Suno at all

**Verified 2026-08-19.** `_discover_assets()` in `toolshop/backup.py` collects only:
`lyrics/genius/**/*.json`, `lyrics/genius/**/*.txt`, `lyrics/lyrics.db`, and `espeak-ng/**`.
`_discover_repo_assets()` adds `.env`, `lyrics_research/reports/*.md`, and three
`results/crhymetv_re/` files.

**Nothing Suno is in either list.** The 2026-07-21 backup that "succeeded" contains **zero Suno
data**. Re-running it on a schedule would not have protected a single track. This is a coverage bug,
not a scheduling bug, and it is the reason this task blocks Task 1.

Add to the backup's asset discovery:

1. `data/toolshop/suno/**/*.json` — **3,426 metadata records**. These are small, irreplaceable, and
   they are the only index of what exists. Each holds `id`, `title`, `created_at`, `model_name`,
   tags/lyrics under `metadata`, and the CDN `audio_url`. **Losing these loses the ability to
   re-fetch anything.** Highest value-per-byte in the whole project.
2. `D:\Projects\suno_extractor\suno_downloads\` — **37 mp3 files, 211 MB**: the entire downloaded
   Suno audio collection. Note this lives **outside the toolshop repo**, so it needs an explicit
   source root rather than falling out of `source_root`/`repo_root`.
3. `D:\Projects\suno_extractor\suno_songs\*.{json,csv,md}` — the older liked-song exports
   (16 JSON, 20–46 records each, Oct–Nov 2025). Small; keep for provenance.

**Write a test** that asserts a Suno metadata file and a Suno mp3 appear in the manifest. The whole
point of this task is that the absence was invisible for a month.

**Exit evidence:** the `backup.py` diff, the new test passing, and a manifest excerpt showing Suno
entries by name.

---

### Task 1c — Flag the CDN exposure (report only, no downloads)

The 3,426 metadata records point at `https://cdn1.suno.ai/<id>.mp3`. **Those tracks are not on this
machine.** They are not a backup problem — no backup can protect a file that was never downloaded.
If the links expire or the Suno account lapses, they are unrecoverable.

Estimated local footprint if fetched: roughly **13–15 GB** at ~4 MB/track — comfortable against D:'s
148 GB.

**This task does not download anything.** Bulk-fetching 3,426 files from an external service is a
separate, user-authorised action with its own plan (rate limits, resume, dedup against the 37 already
present, integrity checks). Record the exposure in STATUS and stop.

**Exit evidence:** a STATUS line stating the count, the estimated size, and that the fetch is
un-started and un-authorised.

---

### Task 2 — Commit the melody-carrier lane

The lane is tested and working; it is simply unsaved. Commit it **before** touching anything else in
the tree, so a mistake later cannot lose it.

1. Review what is being committed: `toolshop/melody_carrier/` (6 modules), the 5
   `tests/test_melody_carrier_*.py` files, and the `toolshop/cli.py` + `toolshop/__init__.py` edits
   that register the `melody-carrier` command group.
2. Do **not** commit the `tests/fixtures/lyrics_min/_dedup_log.json` change yet — diagnose it first
   (Task 6) and commit it separately with an explanation.
3. Commit as **CHANGELOG #038** with a subject that names the lane (governance rule 7).

**Exit evidence:** `git show --stat` of the commit; confirmation that the 5 test files are included.

---

### Task 3 — Make melody-carrier's primary path actually reachable

Verified today: `basic_pitch`, `autochord`, and `adtof_pytorch` are all **absent from the venv**, so
every run silently takes the librosa/pYIN/spectral fallback.

1. **Lift the obsolete platform marker.** `pyproject.toml` `track-full` contains
   `"basic-pitch; platform_system!='Windows'"`. Research verdict R4 (2026-08-19): basic-pitch
   installs on Windows and ships ONNX Runtime there by default. Remove the marker.
2. **Add a `melody` extra** declaring the lane's dependencies (`pretty_midi`, `mido`, `basic-pitch`,
   plus `autochord`/ADTOF as clearly-optional if they do not install cleanly — do not force them).
3. **Install it** in the venv and record which of the three backends actually import.
4. **Add a `--require-advanced` guard** to `toolshop melody-carrier`, mirroring the
   reverse-engineering backend guard. Governance rule 9: recording which path ran is necessary but
   not sufficient — the user must be able to *demand* the primary path and get a hard failure instead
   of a quiet downgrade.
5. Run the lane once on a real track both ways and record the measured difference.

**Exit evidence:** the `pyproject.toml` diff, import check output per backend, and the two runs' tool
attribution (`"basic_pitch"` vs `"pyin_fallback"`).

**If `autochord` or ADTOF-pytorch will not install on Windows:** do not fight it. Record the failure,
leave the fallback wired, and open a research item — they have never been evaluated (assessment §6).

---

### Task 4 — `ai_modules/`: RECORD ONLY, do not touch · **D6 DEFERRED**

**Decision D6 is deferred at the user's request (2026-08-19) — they are reviewing the code first.**

**Do not delete, move, shelve, refactor, or "tidy" anything under `ai_modules/` in this session.**
The recommended ledger sits in `specs/2026-08-19-state-of-project-assessment.md` §7 and waits for the
user's review. That review may well overturn it.

The only thing this task does is stop the *record* from lying. Add to `STATUS.md` (Task 7) an honest
row stating:

- `ai_modules/` exists: 40 files, ~6,390 LOC, committed 2026-08-18 in `31224e5`;
- its 7 test files (~1,440 LOC) are **not collected** — they sit outside `pytest.ini`'s
  `testpaths = tests`, so this code is effectively untested by the suite;
- **disposition pending (D6)** — the ledger is a recommendation, not a decision.

**Exit evidence:** the STATUS diff, plus `git status` confirming `ai_modules/` is byte-identical to
where the session started.

---

### Task 5 — Commit the untracked documentation and orchestration content

All currently untracked and all wanted:

- `ORCHESTRATION/` — the wave harness (`waves.json`, 10 prompts, waves 1-2 handoffs). Waves 3-4 never
  ran; note that in the commit so the gap is on record (assessment F10).
- `docs/lyrics/` — 15 craft/lyric documents relocated from `D:\Projects\to_be_moved`.
  **Check first:** these are lyric/craft docs, not corpus data. If any file contains actual song
  lyrics from the Genius corpus, it stays out per the data boundary.
- `docs/Music Video Generator Tech Survey.md`, `docs/song-to-video-ai-genertor.txt`,
  `docs/извештај-дубинског-истраживања.md` — research inputs.
- **Not** `docs/Loznički Podcast THEME.mp3` (639 KB audio) — that belongs under `data/`.

**Exit evidence:** the commit stat, plus confirmation that no lyrics corpus content was committed.

---

### Task 6 — Root clutter and tracking hygiene

1. Delete the untracked run dumps in the repo root: `cli-help-*.txt` (4), `mc-*.txt` (3),
   `test-output-*.txt` (6), `test-renderer-output.txt`. Delete **only** files `git status` shows as
   untracked (`??`).
2. `.gitignore`: add globs that would have caught them — `cli-help-*.txt`, `mc-*.txt`,
   `test-output*.txt`, `*-output.txt`.
3. `git rm --cached .coverage` — tracked though gitignored.
4. **[USER DECISION D9]** `git rm -r --cached Voicebox/` — 410 tracked files for a parked lane that
   `PROJECTS_INDEX.md` already describes as removed. Recommended: untrack, re-clone at the GPU gate.
5. **[USER DECISION]** The 8 tracked repo-root one-offs (`check_batch_status.py`,
   `diagnose_voice_analysis.py`, `generate_crhymetv_catalogue.py`, `recover_batch_status.py`,
   `run_papapedro_pilot.*`, `run_crhymetv_*.ps1`, `run_reverse_engineering_batch.py`) — pending since
   2026-07-23. Recommended: move to `scripts/`. Note `generate_crhymetv_catalogue.py` and
   `run_reverse_engineering_batch.py` have tests in `tests/` — update imports if they move.
6. Diagnose the `tests/fixtures/lyrics_min/_dedup_log.json` modification and commit it with an
   explanation, or revert it if it is incidental run output.

**Exit evidence:** `git status` before and after; the suite re-run after any file moves.

---

### Task 7 — Reconcile the records

1. **CHANGELOG:** #038 melody-carrier (Task 2), #039 hygiene + records (Tasks 5-7).
   Check the latest entry before assigning numbers — collisions have happened twice.
2. **STATUS.md:** add rows for the two undocumented lanes; add a Video lane note; update the debt
   register (1c still open, 7 backup now resolved, add F2/F3/F5 as new items); record the verified
   `963 passed / 2 skipped / 0 failed` baseline and the 1,425-song DB counts.
3. **PROJECTS_INDEX.md:** it currently claims a **742-song corpus at `D:\MusicData\...`** — both wrong.
   Correct to 1,425 songs at `data/toolshop/lyrics/`. Add melody-carrier, video, daw, ai_modules.
   Fix or remove the Voicebox line to match Task 6.4.
4. **README.md:** last touched 2026-07-21. Add the `daw`, `video`, `melody-carrier` command groups
   and the L5 writing tools.
5. **AGENTS.md:** add governance rules 7-9 from `specs/2026-08-19-goals-v2.md` §7.

**Exit evidence:** diffs for each file; confirm no record describes uncommitted code.

---

### Task 8 — Full suite re-run

`.venv\Scripts\python.exe -m pytest -q`. Bar: **no new failures against 963 passed / 2 skipped / 0
failed**. Expect the count to *rise* by roughly the melody-carrier tests committed in Task 2, and to
shift if Task 6 moves files. Explain any delta; do not weaken a test to make it pass (this happened with `test_keep_short_pauses` and
became debt 1c).

**Exit evidence:** pasted tail of pytest output with the timing line.

---

### Task 9 — CLOSE-OUT GATE (do not skip)

1. `.venv\Scripts\python.exe -m toolshop.cli closeout` — must exit 0.
2. `.venv\Scripts\python.exe -m toolshop.cli doctor` — `backup` OK. `model_cache` will still FAIL;
   that is M2 and it is **out of scope here** (it is session S3). State this explicitly rather than
   letting it look like an unnoticed failure.
3. `git push origin master`.
4. Handoff must paste: the closeout evidence block, the doctor output, the pytest tail, the full
   commit list with hashes, and every `[USER DECISION]` as the user actually answered it.

**Exit evidence:** closeout exit code, empty `git log origin/master..master`, pushed hashes.

---

## Out of scope for this session

Named explicitly so they do not get absorbed the way L1.1's hard half once was:

- M2 model cache (session S2) · M3 stems ONNX (session S3) · M4/M5 · Dossier v2
- **Anything at all under `ai_modules/`** beyond the STATUS row (D6 deferred — user is reviewing)
- Orchestration waves 3-4, L6, German corpus
- Any new lane, any new feature, any research dispatch

**If you find yourself writing new capability in this session, stop — that is the exact pattern this
plan exists to interrupt.**
