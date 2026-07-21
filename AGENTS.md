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
- **Data boundary:** code in repo; audio/models/artifacts under `D:\MusicData\toolshop\` (`TOOLSHOP_DATA_DIR`). Never commit audio, stems, model weights, or results. Never DELETE audio/data — move/quarantine only.
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
