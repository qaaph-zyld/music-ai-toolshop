```text
You are a senior Python engineer. Build a FREE + OPEN-SOURCE Windows desktop app (simple GUI) that takes MP3/WAV and outputs high-quality stems using Demucs (MIT-licensed). Name the app: “StemSlicer”.

GOALS
- Windows 10/11
- Simple GUI (no web UI)
- Input: MP3 + WAV (also allow FLAC/M4A if available via ffmpeg)
- Output: separate stems into folders per track
- Must feel “pro”: stable, cancellable, batch-capable, clear logs, no UI freezing

TECH STACK (REQUIRED)
- Python 3.10+ (target 3.11)
- PySide6 (Qt for Python) for GUI
- Demucs as backend (installed via pip)
- FFmpeg required (for decoding MP3/M4A/etc)
- Use ONLY open-source dependencies

BACKEND CHOICE (IMPORTANT)
- Call Demucs via subprocess using the installed `demucs` CLI (easiest cancellation).
- Do NOT rely on any undocumented flags. Assume only these flags are definitely available:
  - model select: `-n <model>` (default: `htdemucs_ft`)
  - device: `-d cpu` or `-d cuda` (auto if possible)
  - quality-related: `--shifts N` (GPU only; 0 on CPU), `--overlap X`, `--segment S`, `-j N`
  - karaoke/two stems: `--two-stems vocals` (optional mode)
- To control output directory WITHOUT relying on a specific demucs “-o/--out” flag:
  - run Demucs with subprocess `cwd=<chosen_output_dir>`, so its default output folder goes inside that directory.
  - After run finishes, locate the created output under `<output_dir>/separated/<model>/<trackname>/` and show it to the user.

DEFAULTS (SANE)
- Default model: `htdemucs_ft` (best general 4-stem)
- Optional model: `htdemucs_6s` (6-stem: vocals, drums, bass, other, guitar, piano)
- Default device: Auto (cuda if torch cuda available, else cpu)
- Default shifts:
  - CPU: 0
  - CUDA: 1 (“Balanced”), with presets:
    - Fast: shifts 0, overlap 0.10
    - Balanced: shifts 1, overlap 0.25
    - High: shifts 2, overlap 0.25
    - Ultra: shifts 4, overlap 0.25
- Default jobs: 1 (show tooltip: higher uses more RAM)

GUI SPEC (SIMPLE, CLEAN)
Main window layout:
1) File picker area
   - “Add Files…” (multi-select)
   - “Add Folder…” (adds audio files found inside)
   - List widget showing queued files with status (Queued / Running / Done / Failed / Canceled)
   - “Remove Selected”, “Clear”
2) Output settings
   - Output folder picker
   - Checkbox: “Open output folder when done”
3) Separation settings
   - Model dropdown: [htdemucs_ft, htdemucs, htdemucs_6s]
   - Mode dropdown: [Stems (default), Karaoke (2-stem vocals/instrumental)]
   - Device dropdown: [Auto, CPU, CUDA]
   - Quality preset dropdown: [Fast, Balanced, High, Ultra] (disable High/Ultra if CPU)
   - Advanced collapsible section:
     - overlap (float input)
     - segment (int input; tooltip explains GPU memory tradeoff)
     - jobs (int spinbox)
4) Controls
   - “Start”
   - “Cancel Current”
   - “Pause” is optional; if too hard, skip (don’t fake it)
   - Progress bar (overall) + “Now processing: <filename>”
5) Log panel
   - Text area with live subprocess stdout/stderr (streamed)
   - “Copy Log” button

RUNTIME BEHAVIOR
- Dependency check at startup:
  - Verify ffmpeg exists: run `ffmpeg -version`
  - Verify demucs exists: run `demucs -h`
  - If missing, show a friendly dialog with exact commands for Windows installation:
    - Option A (recommended): Anaconda prompt → `conda install -c conda-forge ffmpeg`
    - Then: `python -m pip install -U demucs SoundFile pyside6`
  - App should still open even if missing; but “Start” should be blocked with a clear message.
- Batch processing:
  - Process queue sequentially (simple + stable)
  - Each file gets its own output folder (based on sanitized filename)
- Cancellation:
  - Cancel kills the running subprocess cleanly (terminate, then kill if needed)
  - Mark file as “Canceled” and continue (or stop, user’s choice; default stop)
- Robustness:
  - Handle paths with spaces
  - Ensure output folder exists
  - Avoid overwriting by creating unique run folder if target already exists (e.g., append timestamp)
  - Write a small `run.json` manifest per track (input path, model, settings, start/end time, status)

PROJECT STRUCTURE (GENERATE ALL FILES)
- stemslicer/
  - README.md  (how to install ffmpeg + run app, plus troubleshooting)
  - pyproject.toml  (or requirements.txt if simpler)
  - src/stemslicer/
    - __init__.py
    - main.py          (app entry)
    - ui_main.py       (widgets/layout; no Qt Designer required)
    - worker.py        (QThread / QObject worker that runs subprocess, streams logs)
    - demucs_runner.py (builds command line, validates settings, finds outputs)
    - utils.py         (file scanning, sanitizing, time helpers)
  - LICENSE (MIT for our code)

PACKAGING (OPTIONAL BUT NICE)
- Provide PyInstaller instructions in README for creating a Windows executable:
  - Prefer “onedir” build (torch makes onefile painful)
  - Include ffmpeg note (user must have it in PATH OR bundle it only if license allows; do NOT bundle proprietary builds)

ACCEPTANCE TESTS (YOU MUST MEET THESE)
1) Launch app on Windows, add an MP3, choose output folder, click Start → produces stems folder under output directory.
2) UI remains responsive while running.
3) Log panel updates live.
4) Cancel stops the current file and marks it canceled.
5) Batch of 3 files runs sequentially and marks each status correctly.
6) Missing ffmpeg/demucs shows clear install instructions and blocks Start.

DELIVERABLE
- Output the complete code for all files exactly in the project structure above.
- Keep code clean, typed where reasonable, and heavily commented only where it matters.
- No placeholders like “TODO”; implement fully.

REFERENCE FACTS TO EMBED IN README (DO NOT LINK, JUST STATE)
- Demucs model `htdemucs_ft` is the fine-tuned Hybrid Transformer model; `htdemucs_6s` is experimental 6-source.
- `--two-stems vocals`, `--shifts`, `--overlap`, `-j`, `-d cpu/cuda`, `--segment` exist and are common tuning knobs.
- On Windows, ffmpeg is commonly installed via conda-forge in Anaconda prompt.

Now generate the full repository.
```

Sources used for the technical constraints above: Demucs models + flags + Python-call example + MIT license. ([PyPI][1])
Windows-side install guidance for Demucs (ffmpeg via conda-forge + pip install demucs/SoundFile). ([GitHub][2])

[1]: https://pypi.org/project/demucs/ "demucs · PyPI"
[2]: https://github.com/facebookresearch/demucs/blob/main/docs/windows.md?plain=1&utm_source=chatgpt.com "demucs/docs/windows.md at main"
