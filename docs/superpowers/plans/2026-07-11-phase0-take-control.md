# Phase 0 Implementation Plan — Take Control (Repo + Environment Hygiene)

> **For agentic workers:** Execute task-by-task with checkbox (`- [ ]`) tracking. Tasks marked
> **[USER DECISION]** must not be executed until the user confirms in-session. Never delete audio
> or result data — move/quarantine only. Parent strategy: `docs/superpowers/specs/2026-07-11-strategic-roadmap-v1.md`.

**Goal:** Clean git state, reproducible pinned environment, honest documentation, CrhymeTV batch finished.
**Repo:** `D:\Projects\Music-AI-Toolshop` (remote: github.com/qaaph-zyld/music-ai-toolshop)

---

### Task 1: Snapshot current work (safety first)

- [ ] **Step 1:** `git status` — inventory modified + untracked. Expected (as of 2026-07-11): modified `CHANGELOG.md`, `mastering_tool` (submodule ref); untracked: `.session_archive/`, `Distro Kidea/`, `open_DAW/`, batch runner scripts, diagnose files, `lyrics_research/.session_archive/`.
- [ ] **Step 2:** Commit the batch-runner toolchain (it is proven production code):
  `check_batch_status.py`, `recover_batch_status.py`, `run_reverse_engineering_batch.py`, `generate_crhymetv_catalogue.py`, `run_crhymetv_*.ps1`, `diagnose_voice_analysis.py`, CHANGELOG.
  Commit: `feat: reverse-engineering batch toolchain (CrhymeTV pipeline)`
- [ ] **Step 3:** Do NOT commit: `.session_archive/`, `Distro Kidea/`, `output.json`, `output.txt`, `diagnose_voice.log/.err`, `.coverage` — handled in Task 2.

### Task 2: Draw the data/code boundary

- [ ] **Step 1:** Extend `.gitignore`: `results/`, `Stemmeca_alatkka/separated_stems/`, `Stemmeca_alatkka/toolshop_stems*/`, `.session_archive/`, `*.session_archive/`, `Distro Kidea/`, `output.json`, `output.txt`, `*.log`, `*.err`, `.coverage`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`
- [ ] **Step 2 [USER DECISION]:** Personal audio in `Stemmeca_alatkka/` and `Distro Kidea/` — propose moving to `D:\MusicData\` (outside repo). Present sizes first (`Get-ChildItem -Recurse | Measure-Object Length -Sum`).
- [ ] **Step 3:** Document the convention in README: code lives in repo; audio inputs/outputs live under a data root (default `D:\MusicData\toolshop\`), configurable via `TOOLSHOP_DATA_DIR` env var.

### Task 3: Resolve duplicates

- [ ] **Step 1:** Diff `D:\Projects\Mastering_Toolshop` (root sibling) vs `mastering_tool/` submodule — file inventory + git remotes. Report which is canonical (hypothesis: submodule is canonical; root sibling is the original working copy with extra `music_tracks/`, `build/`, `dist/`).
- [ ] **Step 2 [USER DECISION]:** Propose: keep submodule canonical; root sibling's unique data (music_tracks, masters) → `D:\MusicData\`; then archive root sibling.
- [ ] **Step 3:** Same exercise for `open_DAW/` (untracked, newer per commits) vs `projects/06-opendaw/` (tracked). Hypothesis: `open_DAW/` is live, `projects/06-opendaw/` is a stale copy. Keep one, note in PROJECTS_INDEX.
- [ ] **Step 4 [USER DECISION]:** `Voicebox/` is a vendored external fork — propose removing from this repo (re-clone separately when the GPU gate opens).

### Task 4: Reproducible environment

- [ ] **Step 1:** Create `.venv` on Python 3.11 (install via `winget install Python.Python.3.11` if absent). Rationale: madmom/essentia/basic-pitch/spleeter ecosystem does not support 3.13.
- [ ] **Step 2:** `pip install -e ".[audio,youtube,voice,cleaning,stems]"` + `pip install audio-separator demucs soundfile` — then `pip freeze > requirements.lock.txt`. Add `stems` extra to pyproject if missing (audio-separator, onnxruntime).
- [ ] **Step 3:** Verify ffmpeg: prefer existing `D:\Projects\ffmpeg_portable` — add discovery to config (PATH or `TOOLSHOP_FFMPEG` env var).
- [ ] **Step 4:** New command `toolshop doctor`: checks python version, ffmpeg, required packages per extra, model cache dir + free disk space, writes report. TDD: `tests/test_doctor.py` first.
- [ ] **Step 5:** Run full `pytest` in the venv; fix any 3.11/3.13 drift. Expected: all green.

### Task 5: Finish the CrhymeTV batch (runs overnight, unattended)

- [ ] **Step 1:** Preflight: `python check_batch_status.py` → expect 140/222 completed, 0 failed.
- [ ] **Step 2:** Confirm ≥15 GB free on D: (82 tracks × ~150 MB stems). If tight, pause for Task 2 data moves first.
- [ ] **Step 3:** Launch `run_crhymetv_batch.ps1` (resume mode). ~82 tracks × 12 min ≈ 16 h — schedule overnight.
- [ ] **Step 4:** After completion: `python generate_crhymetv_catalogue.py` → refresh `catalogue.csv/md`, `suno_prompts.md`.

### Task 6: Honest documentation

- [ ] **Step 1:** Update `PROJECTS_INDEX.md`: stem-extractor = ✅ Active (shipped in toolshop core); add 06-opendaw, mastering_tool, Voicebox/MAirina rows with real statuses; link the new roadmap spec.
- [ ] **Step 2:** README: add "Hardware profile" note (CPU-only defaults, GT 640 unusable for ML, `--fast` recommended), correct stem docs to match actual behavior, document data-dir convention.
- [ ] **Step 3:** CHANGELOG entry for Phase 0 in the established Answer-format.

### Task 7: CI smoke (GitHub Actions)

- [ ] **Step 1:** Workflow: py3.11, `pip install -e .[audio] pytest`, run unit tests only (mark model-download/integration tests `@pytest.mark.slow` and exclude in CI).
- [ ] **Step 2:** Badge in README. Push and verify green.

---

## Verification Checklist
- [ ] `git status` clean (data dirs ignored, code committed)
- [ ] `.venv` (py3.11) + `requirements.lock.txt` committed
- [ ] `toolshop doctor` passes on this machine
- [ ] `pytest` green locally and in CI
- [ ] CrhymeTV `batch_status.json`: 222/222 completed, catalogue regenerated
- [ ] PROJECTS_INDEX/README/CHANGELOG match reality
