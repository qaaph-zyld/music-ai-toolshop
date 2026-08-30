# AGENTS.md — Music-AI-Toolshop

> Project rules for AI agents. Loaded at session start per framework bootstrap.
> Strategy: `docs/superpowers/specs/2026-07-15-longterm-roadmap-v2.md` (roadmap v2, the backlog of record).
> Tech choices: `docs/superpowers/specs/2026-07-15-oss-integration-map.md` (which OSS to integrate per tool; adapter/WSL-sidecar/model-mirror policies). Do not introduce new third-party audio/ML deps outside that map without user sign-off.

## What this repo is
Monorepo tool suite ("The Toolshop") for music deconstruction/reconstruction:
core platform + stem tool + reverse-engineering (dossier) tool + remastering tool
(`mastering_tool/` git submodule with tray EXE) + vocal lab + library intelligence +
creation bridge + sample forge. CLI-first (`toolshop` entrypoint), adapters stay pure,
CLI/scripts orchestrate.

## Hard rules
- **Python:** ALWAYS use `.venv` (Python 3.11.9): `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`. Never the global 3.13.
- **Compute is CPU-only** (locked decision 2026-07-15, roadmap §0). GT 640 GPU is unusable for ML. No feature merges without a measured min/track number on this machine. Heavy work (>15 min) must be a resumable overnight batch.
- **Data boundary:** code in repo; audio/models/artifacts under `data/toolshop/` (`TOOLSHOP_DATA_DIR`, defaults to `<repo>/data/toolshop`). Never commit audio, stems, model weights, or results. Never DELETE audio/data — move/quarantine only.
- **UTF-8 everywhere:** reconfigure stdout/stderr on entry (see `run_reverse_engineering_batch.py`); `encoding="utf-8"` on every file read/write; test filenames like `Täterprofil ćevap.mp3`.
- **TDD:** extend `tests/` before modifying adapters. Mock model calls; real-model tests get `@pytest.mark.slow` and are excluded from CI.
- **Batch jobs:** must use the shared resumable pattern (`toolshop/batch.py`): status JSON flushed per item, `--limit/--offset`, skip-completed resume.
- **Verification before assertion:** run pytest + the relevant CLI command; quote output in the handoff.

## Close-out discipline (enforced — repeated out-of-band failure mode)
Caught by orchestrator spot-check 3+ sessions running: uncommitted work left in the tree, records describing code that isn't committed, and "done/spotless/PASS" handoffs that don't match reality.
- **Clean tree or declared.** A session is not done until `git status` is clean, OR the handoff lists every still-dirty path and why. A "spotless" claim must be backed by the actual `git status` pasted in the handoff.
- **No record ahead of code.** No CHANGELOG/STATUS entry may describe code that isn't committed in the same wave. Answer-numbers are unique — check the latest entry before assigning (two sessions once collided on #018).
- **Verified verdicts only.** Quality verdicts (PASS / "discriminates" / "works") enter STATUS or CHANGELOG only after the asserting session re-ran the check itself. Numbers relayed from another doc must be tagged `unverified — source: <path>`, never stated as fact. (The L2 fingerprint defect was caught only by running the actual query, not by trusting the handoff.)
- **Commit before you claim.** Never carry a tested deliverable uncommitted across sessions — it risks the work and tangles the next commit. Commit code with, or before, its record.
- **Handoff = final truth.** Commit hashes, push status, and test counts in the handoff reflect the pushed final state, not a mid-run baseline.

## Lane discipline (added 2026-08-19 — each rule is written against a failure that happened)

- **Commit messages must describe their contents.** Commit `31224e5` shipped a 6,390-line new
  top-level package under the subject *"chore: update mastering_tool submodule"*. No automated gate
  can catch this — `closeout` and the pre-push hook both pass on a clean, pushed tree. So: a
  lane-sized diff (>500 lines, or any new top-level package) must carry its CHANGELOG number in the
  commit subject.
- **New top-level packages are lanes, not files.** A new directory at the repo root, or a new
  `toolshop/` subpackage, needs a plan, a STATUS row, a dependency extra, and **its tests inside
  `tests/`** where `pytest.ini`'s `testpaths` will collect them. `ai_modules/` shipped 1,440 lines
  of tests that have never once run.
- **Fallback paths must be declarable.** Any module with a primary ML backend and a heuristic
  fallback needs a `--require-advanced` guard (see `toolshop melody-carrier extract`, and the
  reverse-engineering backend that caught the original silent-fallback incident). Recording which
  path ran is necessary but not sufficient — the user must be able to *demand* the good path.
- **Backups are verified by coverage, not by exit code.** `backup.py` verified clean for a month
  while collecting zero Suno data. When adding an asset class, add a test that asserts it appears in
  the manifest.

## Package layout (D12, 2026-08-30 — replaces H1-M5's big-bang reorg)

`toolshop/` is deliberately mostly flat. The wholesale core/tool reorganisation was **descoped**: its
own success criterion was "imports/CLI unchanged", so it could not deliver anything observable, and a
55-module move behind re-export shims is exactly where a passing suite stops being evidence.

**The rule instead:** when a lane is next touched *substantially*, move its modules into a subpackage
**then**, with that lane's own tests as the safety net. `toolshop/daw/` and `toolshop/melody_carrier/`
were built this way and are the pattern. Never a repo-wide move as its own task.

## Measurement discipline (added 2026-08-30 — earned the hard way)

- **Warm up before you measure, and repeat the baseline.** An M3 sweep ran each baseline cold and
  every variant warm, so it measured 609 MB of disk read and called it compute. It reported a 2.97x
  and a 1.40x speedup; controlled re-runs gave 1.22x and **1.00x**. Any timing comparison needs a
  discarded warm-up run and the baseline repeated at the end — if the two baselines disagree by more
  than ~10%, the machine is not a stable instrument and no conclusion holds.
- **Verify at the scope of the claim.** Debt 13b was patched in one test file, checked in that one
  file, and recorded as fixed — while five other modules still had the bug. If the claim is "the
  suite leaves a clean tree", the check is the *suite*, not a file. The narrow check passes honestly
  and the broad conclusion is still false, which is worse than an outright error because the evidence
  looks real.
- **Fix the class, not the instance.** When a second occurrence of a bug turns up, centralise the fix
  so a third cannot appear (see `tests/_fixture_support.py`). Patching occurrence #2 just schedules
  occurrence #3.
- **Validate a clip result on a full input before shipping it.** The 1.40x survived a 30 s clip and
  died on a 3 min track. Short-input measurements exaggerate anything with fixed overhead.
- **Kill the watcher with the process it watches.** Stopping a long job while leaving an
  `until <cond>; do sleep; done` loop polling for output that will now never appear leaks a shell
  that spins for the rest of the session. Three were leaked in one session before a user noticed.
  Prefer bounded polling (`for i in $(seq 1 N)`) over unbounded `until`.

## Mechanical close-out (enforced by tooling)
- **`toolshop closeout`** must exit 0 at session end. Its evidence block (git status, git log, submodule summary) must be pasted in every handoff.
- **Pre-push hook** (`hooks/pre-push`, version-controlled): blocks pushes when the working tree has tracked junk files (`pytest_*.txt`, `annotate_run*.txt`) or staged-but-uncommitted changes. Bypass with `--no-verify` is for emergencies only — fix the tree instead.
- **Hook setup:** every clone must run `git config core.hooksPath hooks` (local config). `toolshop doctor` checks this automatically.

## Key commands
```powershell
# tests
D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -m pytest -q
# environment/model-cache health
D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -m toolshop.doctor
# stems (presets: karaoke | vocals-hq | full-vocals | full-vocals-hq | 4stem | 6stem)
D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -m toolshop.cli stems <path> --preset karaoke
# reverse-engineering batch (CrhymeTV pattern)
& D:\Projects\Music-AI-Toolshop\run_crhymetv_batch.ps1
```

## mastering_tool submodule
Separate product (tray EXE + WSL bash pipeline). Do not refactor casually; it is in
daily use. Shell scripts are LF-only (`.gitattributes` enforced). WSL path:
`/mnt/d/Projects/Music-AI-Toolshop/mastering_tool`. Rebuild EXE per its TRAY_LAUNCHER.md.
Commit submodule pointer bumps deliberately, never accidentally.

## Documentation conventions
- Designs → `docs/superpowers/specs/`, executable plans → `docs/superpowers/plans/` (checkbox format, `[USER DECISION]` markers for destructive/ambiguous steps).
- CHANGELOG.md uses the Answer-format (timestamp, previous/current state, files affected).
- Update README + PROJECTS_INDEX in the same session as the behavior change.
- End sessions with a handoff in `D:\Projects\.windsurf\handoffs\` + `python scripts/session_end.py`.

## Known context (verify before relying)
- CrhymeTV batch: 140/222 with stems; remainder runs analyze-only (`--no-stems`, roadmap H1-M1).
- Stems CPU cost: ~30 min/track default MDX preset (10 s synthetic: karaoke ≈26.5 s, full-vocals ≈70.8 s).
- Model cache incomplete: only `UVR-MDX-NET-Voc_FT.onnx` + `UVR-BVE-4B_SN-44100-1.pth` present; Roformer/Demucs download on first use.
- Parked (no investment without user sign-off): open_DAW, Voicebox (archive pending), ACE-Step local generation.
