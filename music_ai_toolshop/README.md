# Music AI Toolshop — Unified Web Launcher

A single Windows executable that starts a Flask dashboard for the six phase tools from the `mastering_tool` + `open_DAW` unified execution plan.

## What it does

Double-click `MusicAIToolshop.exe` in the umbrella repo root:

1. Starts a local Flask server on `http://127.0.0.1:5055`.
2. Opens the dashboard in your default browser.
3. Adds a system tray icon for restart/exit.

From the dashboard you can run:

- **Stem Extractor** — separate a mix into vocal/instrumental stems.
- **Vocal Restore** — run the vocal restoration chain on a vocal stem.
- **CLAP Reference Match** — find the nearest reference masters.
- **Vocal QC** — Whisper-driven transcription confidence diagnostics.
- **Neutone Plugin Preview** and **Master Bus Preview** — launch cards for the `open_DAW` desktop app.

## Requirements

- Windows 10/11
- Python 3.10+ installed and on `PATH`
- The umbrella repo (`d:\Project`) with `mastering_tool/` and `open_DAW/` as sibling directories

## Install

```powershell
python music_ai_toolshop/setup_dev.py
```

## Run in development

```powershell
cd music_ai_toolshop
python server.py
```

Then open `http://127.0.0.1:5055`.

Or use the launcher directly:

```powershell
python launcher.py
```

## Build the EXE

```powershell
cd music_ai_toolshop
build.bat
```

This produces `..\MusicAIToolshop.exe`.

You can also build manually:

```powershell
python -m pip install -r build_requirements.txt
python build_exe.py
```

## Project layout

```
music_ai_toolshop/
├── launcher.py              # tray launcher + browser auto-open
├── server.py                # Flask backend
├── paths.py                 # sibling repo resolver
├── requirements.txt         # runtime dependencies
├── build_requirements.txt   # PyInstaller only
├── build_exe.py             # PyInstaller build script
├── build.bat / run.bat      # Windows shortcuts
├── setup_dev.py             # install runtime deps
├── wrappers/                # tool-specific runners
│   ├── stem_extractor.py
│   ├── vocal_restore.py
│   ├── clap_match.py
│   └── vocal_qc.py
├── templates/               # dashboard HTML
│   └── index.html
├── static/                  # dashboard JS/CSS
│   ├── app.js
│   └── style.css
└── tests/                   # smoke tests
    ├── test_paths.py
    └── test_smoke.py
```

## Environment variables

If the umbrella repos are not in the default sibling layout, set:

- `MASTERING_TOOL_PATH` — path to the `mastering_tool` repo.
- `OPEN_DAW_PATH` — path to the `open_DAW` repo.

## Notes

- The EXE does not bundle Python or the ML models. It expects the system Python interpreter and the runtime dependencies to be installed.
- Heavy ML tools (stem separation, CLAP, Whisper) are dispatched as subprocesses; progress streams back to the browser via SSE.
- Real-time preview tools (Neutone, master bus) still require the `open_DAW` desktop app.
