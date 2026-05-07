# 07-reaper-integration

Drive the existing `music-ai-toolshop` adapters from inside
[Reaper](https://www.reaper.fm/) using ReaScript Python.

This project is the post-OpenDAW pivot: rather than build a from-scratch
DAW, we hook the toolshop's analysis/separation/cleaning utilities into a
mature host so they can be used while actually making music.

## Status

**Phase 0 — Skeleton.** One ReaScript action is wired up end-to-end, with
unit tests for the helper bridge. More actions to follow (see "Roadmap").

| Action | ReaScript | Status |
|---|---|---|
| Analyze BPM/Key of selected media item | `reascripts/toolshop_analyze_bpm_key.py` | ✅ Implemented (skeleton) |
| Extract stems from selected media item | _planned_ | ⏳ |
| Detect voice effects on selected take | _planned_ | ⏳ |
| Run cleaning pipeline on selected take | _planned_ | ⏳ |
| Insert YouTube audio as new media item | _planned_ | ⏳ |
| Generate Suno prompt from selection | _planned_ | ⏳ |

## Layout

```
projects/07-reaper-integration/
├── README.md                       (this file)
├── reascripts/
│   ├── _toolshop_bridge.py         Helper module — no Reaper imports, fully testable.
│   └── toolshop_analyze_bpm_key.py ReaScript entry point (uses reaper_python).
├── tests/
│   └── test_toolshop_bridge.py     Pytest suite for the bridge helper.
└── docs/
    └── (TBD)
```

## How it works

ReaScript Python is invoked by Reaper with its embedded interpreter. We
do *not* try to run the heavy `librosa`/`demucs` stack inside Reaper.
Instead, the ReaScript subprocesses out to the regular `toolshop` CLI
(installed via `pip install -e .` in this monorepo's root) and parses the
JSON it produces. This keeps Reaper responsive and lets the analysis
code keep using its preferred Python/conda environment.

## Install

1. **Install music-ai-toolshop and its `audio` extras** in any Python
   environment of your choice:

   ```bash
   pip install -e ".[audio]"
   ```

   Verify the CLI works:

   ```bash
   toolshop analyze bpm-key /path/to/song.wav --json
   ```

2. **Tell Reaper which Python to use** for ReaScript Python:
   *Reaper -> Preferences -> Plug-ins -> ReaScript -> Python*. Point it
   at any modern Python 3 install (does not need to match the toolshop
   environment).

3. **Make the `toolshop` CLI reachable from the script.** Two options:
   - Ensure the `toolshop` entry point is on your `PATH` (works out of
     the box if you `pip install -e .` into the same Python that's on
     `PATH`).
   - Or set the environment variable `TOOLSHOP_PYTHON` to the
     interpreter that has it installed, e.g. on Windows in Reaper's
     environment block:

     ```
     TOOLSHOP_PYTHON=D:\Project\music-ai-toolshop\.venv\Scripts\python.exe
     ```

     The bridge will then run `<that python> -m toolshop.cli ...` instead
     of the bare binary. (Linux/macOS equivalents work the same way.)

   You can also override the binary name with `TOOLSHOP_BIN` if you have
   it aliased.

4. **Register the ReaScript with Reaper:**
   - Copy `reascripts/toolshop_analyze_bpm_key.py` *and*
     `reascripts/_toolshop_bridge.py` into Reaper's `Scripts/` folder
     (or any folder Reaper scans). Both files must live next to each
     other; the entry script imports the bridge module by relative path.
   - In Reaper: *Actions -> Show action list -> ReaScript: Load -> select
     `toolshop_analyze_bpm_key.py`*.
   - Optionally bind a keyboard shortcut.

## Use

1. Select an audio media item in Reaper.
2. Run the action *"Custom: toolshop_analyze_bpm_key.py"*.
3. Watch the console: the script logs the file path, then the analysis
   result (`120.00 BPM, F minor, 234.56s`).
4. Side effects:
   - The item's *Notes* (`P_NOTES`) field is filled with the BPM, key,
     duration, and source path.
   - A project marker is added at the item's start position labelled
     `<bpm> BPM <key> <mode>` so the analysis stays visible on the
     timeline.

## Develop / test

The bridge module has zero Reaper dependencies and is fully unit-tested:

```bash
pip install -e .
pytest projects/07-reaper-integration/tests
```

The tests cover: CLI resolution (`TOOLSHOP_PYTHON`, `TOOLSHOP_BIN`,
`PATH`), happy-path JSON parsing, missing-file, non-zero exit, malformed
JSON, subprocess timeout, and missing binary.

## Roadmap

Short-term (next PR each):

* `toolshop_extract_stems.py` — invokes `toolshop stem extract`, then
  uses `RPR_InsertMedia` to import the four stems as new tracks
  underneath the source.
* `toolshop_voice_analyze.py` — runs `toolshop voice analyze --json` on
  the selected take and writes the detected effects into `P_NOTES`.
* `toolshop_clean_pipeline.py` — runs `toolshop clean pipeline` on the
  selected take and replaces (or duplicates) the source with the
  cleaned output.

Mid-term:

* Real ACE-Step bridge in `toolshop` (currently a stub in the archived
  `06-opendaw/ai_modules/ace_step_bridge`) — once that exists, expose
  it as a "Generate MIDI clip" action.
* Optional small Tk/PyQt panels for the actions that have parameters
  (cleaning thresholds, stem mode, etc.) instead of relying on Reaper's
  built-in input dialog.

## Why this and not 06-opendaw?

See [`../06-opendaw/README.md`](../06-opendaw/README.md) for the full
post-mortem. Short version: building a usable DAW from scratch is a
multi-year solo project, and Reaper already does everything 06-opendaw
was trying to do, better, today. Plugging the toolshop's actually-novel
work (voice-effects detection, BPM/key, stems, cleaning) into a real DAW
gets us a useful tool in weeks rather than years.
