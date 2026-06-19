# Workspace Structure

**Repository:** `qaaph-zyld/music-ai-toolshop` (umbrella)
**Last updated:** 2026-06-19

## Top-level layout

```
d:\Project/
├── music_ai_toolshop/       # New: unified Windows web launcher
├── mastering_tool/          # FFmpeg mastering pipelines + QC tools
├── open_DAW/                # Rust audio engine + Python AI modules
├── docs/                    # Project documentation
├── project_catalogues/      # Per-project catalogues
├── Tools/                   # Utility tools
├── Websites/                # Web projects
├── Apps_Projects/           # App projects
├── CHANGELOG.md             # Project changelog
├── README.md                # Root project README
├── workspace_structure.md   # This file
└── .gitignore
```

## New: `music_ai_toolshop/`

```
music_ai_toolshop/
├── launcher.py              # Tray launcher + browser auto-open
├── server.py                # Flask backend + SSE endpoints
├── paths.py                 # Sibling repo resolver
├── requirements.txt         # Runtime dependencies
├── build_requirements.txt   # PyInstaller build dependency
├── build_exe.py             # PyInstaller build script
├── build.bat                # Windows build shortcut
├── run.bat                  # Windows dev run shortcut
├── setup_dev.py             # One-shot dev dependency install
├── README.md                # Tool documentation
├── icon.png                 # Generated tray icon
├── templates/
│   └── index.html           # Dashboard UI
├── static/
│   ├── app.js               # Dashboard logic
│   └── style.css            # Dashboard styling
├── wrappers/
│   ├── __init__.py
│   ├── _common.py           # Subprocess runner
│   ├── stem_extractor.py    # open_DAW stem extractor wrapper
│   ├── vocal_restore.py     # mastering_tool vocal restore wrapper
│   ├── clap_match.py        # CLAP reference matcher wrapper
│   └── vocal_qc.py          # Whisper vocal QC wrapper
└── tests/
    ├── __init__.py
    ├── test_paths.py        # Repo resolver tests
    └── test_smoke.py        # Flask server smoke tests
```

## Output artifact

- `d:\Project\MusicAIToolshop.exe` — generated Windows executable (ignored by git)

## Notes

- `music_ai_toolshop/` is the new unified entry point for the six phase tools.
- Real-time preview tools (Neutone, master bus) remain in the `open_DAW` desktop app.
- `MusicAIToolshop.exe` expects Python 3.10+ and the runtime dependencies to be installed.
