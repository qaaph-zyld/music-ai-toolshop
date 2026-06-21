---
generated_at: 2026-06-22_0103
source_workspace: d:\Project
project: music-ai-toolshop umbrella / open_DAW / mastering_tool
---

# Handoff: Test all utilities properly

## Context

- Previous session was lost due to a PC crash. No recovery artifacts available.
- Per user direction: **assume all utilities do not work** and must be tested from scratch.
- **This session is for handoff only** — no coding changes were made here.

## Scope to test

### `open_DAW`

1. `cargo test` in `d:\Project\open_DAW\daw-engine`
   - `plugin_slot` tests
   - `master_bus` tests
   - Full suite
2. `cargo build` for the daw-engine crate
3. JUCE UI components (if build environment is available)
   - `ui/src/Plugins/NeutoneHost.{h,cpp}`
   - `ui/src/MasterBus/MasterBusPanel.{h,cpp}`
4. `ai_modules/stem_extractor/`
   - `python -m ai_modules.stem_extractor.cli` on a real MP3/WAV
   - `pytest` in `ai_modules/stem_extractor/tests/`
5. `ai_modules/neutone_bridge/`
   - `python -m ai_modules.neutone_bridge.pretrained`
   - JSON export path

### `mastering_tool`

1. `vocal_restore.sh` end-to-end on a real SUNO source
   - Input: `mastering_tool/source/<track>.mp3`
   - Outputs: `restored_vocal.wav`, `restored_full_mix.wav`, `final_master.wav`
2. `vocal_prep.sh` on restored output
3. `reference_benchmark.sh` on a new reference
   - CLAP embedding step
   - `REFERENCE_LIBRARY.csv` append
4. `matchering_xcheck.py --auto-reference`
5. `tools/clap_match/`
   - `python -m tools.clap_match.embed <wav>`
   - `python -m tools.clap_match.index`
   - `python -m tools.clap_match.match <wav>`
6. `tools/export_chain_to_json.py` on a `master_pipeline_*.sh` script
7. `tools/vocal_qc/`
   - `python -m tools.vocal_qc.transcribe <vocal.wav>`
   - `python -m tools.vocal_qc.diagnose <vocal.wav> --md report.md`
8. `tools/vocal_restore/`
   - `python -m tools.vocal_restore.restore <vocal.wav>`
   - `python -m tools.vocal_restore.remix <vocal.wav> <instrumental.wav>`

## Recommended test order

1. Start with `open_DAW/daw-engine` unit tests — fastest, highest confidence.
2. Run `mastering_tool` CLI scripts in dry-run / stub mode first where available.
3. Pick one real source track and run the full `mastering_tool` pipeline from stem extraction to final master.
4. Document every failure as a GitHub issue with reproduction steps.

## Known unknowns

- It is not confirmed which Python environments are installed and active.
- Heavy ML dependencies (Whisper, CLAP, Demucs/RoFormer, VoiceFixer, Apollo, AudioSR) may be missing.
- GPU/CUDA status unknown.
- Rust toolchain status unknown.
- JUCE build environment unknown.

## Safety rules for the next session

- Do not commit real audio files (`.wav`, `.mp3`) to git.
- Do not install system-wide packages without user approval.
- Run each test with absolute paths and the correct `Cwd` per project.
- Prefer one failing utility at a time; fix root cause, not symptoms.

## Files to inspect first

- `d:\Project\mastering_tool\UNIFIED_EXECUTION_PLAN.md`
- `d:\Project\open_DAW\docs\MASTER_BUS.md`
- `d:\Project\open_DAW\docs\PLUGINS.md`
- `d:\Project\HANDOFF.md` (previous handoff from 2026-06-19)

## Exit condition

Stop when the user confirms the full test matrix is green or when a blocker is found and escalated as a GitHub issue.
