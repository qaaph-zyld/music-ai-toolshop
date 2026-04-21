# OpenDAW - Current State

**Last Updated:** 2026-04-21
**Single Source of Truth** — replaces 44 archived handoff documents (see `archive/handoffs/`)

---

## Verified Metrics

| Metric | Value | Verified |
|--------|-------|----------|
| `cargo test --lib` | **350 passed, 0 failed, 1 ignored** | 2026-04-21 |
| `cargo test --tests` (integration) | **425 passed, 1 failed*, 3 ignored** | 2026-04-21 |
| `cargo check --lib` | **0 errors, 0 warnings** | 2026-04-21 |
| Rust source files (active) | ~40 | 2026-04-12 |
| Quarantined stubs | 53 (in `src/future/`) | 2026-04-12 |
| C++ UI files | 52 | 2026-04-12 |
| AI Python modules (real) | 5 | 2026-04-12 |

\* 1 pre-existing failure in `noise_suppression_test` (RNNoise not linked — expected)

## Phase 0: E2E Verification ✅ PASSED (2026-04-12)

| Test | Status | Evidence |
|------|--------|----------|
| Audio playback pipeline | ✅ | `integration_full_playback_workflow` — peak 0.50, CPU 2.6% |
| Transport play/stop/loop | ✅ | Loop mode wraps position correctly |
| Session scene launch | ✅ | `integration_scene_launch_with_audio` — clips play/stop correctly |
| Project save/load roundtrip | ✅ | `integration_project_roundtrip` — name, tempo, tracks identical |
| AI bridge → pattern gen | ✅ | `integration_ai_full_workflow` — pattern → session import works |
| Suno library search | ✅ | `integration_suno_library_stub` — search/filter/count works |
| `crate-type = ["cdylib", "lib"]` | ✅ | DLL + rlib both build, integration tests link |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│              UI Layer (JUCE C++)                  │
│  SessionGrid │ Mixer │ Transport │ SunoBrowser   │
├──────────────────────────────────────────────────┤
│          FFI Bridge (cdylib DLL)                 │
│  ffi_bridge.rs │ engine_ffi │ midi_ffi │ etc.    │
├──────────────────────────────────────────────────┤
│           Audio Engine (Rust)                    │
│  Mixer │ SamplePlayer │ Transport │ Session      │
│  MIDI │ ClipPlayer │ Realtime Queue │ Export     │
├──────────────────────────────────────────────────┤
│         AI Modules (Python)                      │
│  suno_library │ stem_extractor │ pattern_gen     │
│  musicgen │ (api_server bridge)                  │
└──────────────────────────────────────────────────┘
```

**Communication:** Rust cdylib DLL → JUCE C++ via FFI (verified with GetProcAddress + EXE launch)

---

## What Actually Works

### Rust Core Engine (VERIFIED — 341 tests)
- **Audio callback** with sine wave generation
- **Mixer** with gain control, loudness metering (EBU R 128)
- **Transport** (play/stop/record/pause, loop, punch-in/out, tempo/BPM)
- **Session View** (clip slots, scene launch, playback states)
- **MIDI engine** (note on/off, velocity, channels, CC)
- **MIDI input** (device enumeration via midir, quantization)
- **Sample playback** (WAV loading via hound)
- **Project save/load** (JSON serialization, `.opendaw` format)
- **Lock-free SPSC queue** (atomic indices, real-time safe)
- **Clip player** with state management
- **Transport sync** with quantized clip launching
- **Serialization** system with version migration
- **Export engine** (WAV/MP3 format support — code exists, E2E untested)
- **Noise suppression** module
- **Plugin system** (base + CLAP host — code exists, no real plugins tested)

### FFI Layer (VERIFIED — DLL exports + EXE launch)
- cdylib DLL (~1.5 MB) with `#[no_mangle] pub extern "C"` exports
- EngineBridge initialization fix applied
- Null safety checks on all FFI entry points
- Callback registration (transport, meters, clips, position)

### JUCE UI (BUILDS — functional verification pending)
- **52 C++ source files** across 10 component groups
- Session grid (8x16 clip slots, track headers, scene buttons)
- Transport bar (play/stop/record, tempo, time display)
- Mixer panel (channel strips with level meters)
- Project manager (save/load dialogs, keyboard shortcuts)
- Suno browser component (side panel, 350px)
- Stem extraction dialog
- Pattern generator dialog (MMM FFI)
- Recording panel
- Export dialog
- Onboarding component

### AI Modules (5 real, cleaned up)
| Module | Status | Details |
|--------|--------|---------|
| `suno_library/` | **Real** | SQLite queries, API server, 10 test tracks, search/filter |
| `stem_extractor/` | **Real** | Demucs subprocess with caching; stubs when demucs unavailable |
| `pattern_generator/` | **Real** | Algorithmic MIDI generation (renamed from ace_step_bridge) |
| `musicgen/` | **Has code** | bridge.py + generator.py; untested against real AudioCraft model |
| `production_analyzer/` | **Has code** | classifier.py, batch_analyzer.py |

---

## What's NOT Verified (E2E)

These components have code but **no evidence of end-to-end testing**:
- Audio playback through full stack (Rust → CPAL → speakers)
- Transport controls in UI actually controlling Rust engine
- Clip launching from session grid producing sound
- MIDI recording from real devices
- Audio export producing valid playable files
- Suno browser loading/playing tracks in UI
- Any real plugin hosting

---

## Key Files

### Engine Core
- `daw-engine/src/lib.rs` — Module exports (cleaned, 40 active modules)
- `daw-engine/src/mixer.rs` — Audio mixing with loudness metering
- `daw-engine/src/session.rs` — Session view clips/scenes
- `daw-engine/src/transport.rs` — Playback transport
- `daw-engine/src/realtime.rs` — Lock-free SPSC queue
- `daw-engine/src/ffi_bridge.rs` — Main FFI bridge (2215 lines)
- `daw-engine/Cargo.toml` — Dependencies (cdylib crate type)

### UI Layer
- `ui/CMakeLists.txt` — JUCE build config
- `ui/src/Main.cpp` — App entry
- `ui/src/MainComponent.{h,cpp}` — Main window with menu bar
- `ui/src/Engine/EngineBridge.{h,cpp}` — FFI bridge with null checks

### AI Modules
- `ai_modules/suno_library/__init__.py` — SQLite-backed track browser
- `ai_modules/stem_extractor/__init__.py` — Demucs wrapper
- `ai_modules/ace_step_bridge/__init__.py` — Algorithmic pattern gen (TO RENAME)

---

## Build Commands

```bash
# Rust engine
cd daw-engine
cargo test --lib        # 341 tests
cargo check --lib       # 0 errors, 51 warnings
cargo build --release   # Produces daw_engine.dll (~1.5 MB)

# C++ UI (requires JUCE + CMake)
cd ui
cmake -B build && cmake --build build
```

---

## Dependencies
- `cpal 0.15` — Audio I/O
- `hound 3.5` — WAV files
- `serde/serde_json 1.0` — Serialization
- `axum 0.7` + `tokio 1.0` — HTTP API server
- `crossbeam 0.8` — Thread channels
- `ebur128 0.1` — Loudness metering
- `rustfft 6.2` — FFT analysis
- `rusqlite 0.32` — SQLite (bundled)
- `midir 0.10` — MIDI device enumeration
- `thiserror 1.0` — Error handling

---

## Cleanup Done (2026-04-12)

- **Quarantined 53 stub modules** to `daw-engine/src/future/` — aspirational FFI bindings for synths/tools not actually integrated
- **Archived 44 handoff documents** to `archive/handoffs/`
- **Reduced warnings** from 204 → 51
- **Established honest test baseline**: 341 real tests (was claimed as "853")

## Pending
- ~~Address remaining 51 compiler warnings~~ ✅ DONE (2026-04-21: 0 warnings)
- ~~Set up dedicated git repo for 06-opendaw~~ ✅ DONE (2026-04-21: initialized, committed)
- Push to GitHub (requires manual action: `git remote add origin <url>` then `git push -u origin main`)
- Fix pre-existing `noise_suppression_test` failure (needs real RNNoise library — Phase 11)

---

## Recommended Next Steps

1. **~~E2E audio verification~~** ✅ VERIFIED (2026-04-21: `integration_full_playback_workflow` passes, peak 0.50, non-zero audio)
2. **~~Audio export verification~~** ✅ VERIFIED (2026-04-21: `test_export_wav_success` produces valid 48kHz/16-bit WAV)
3. **Complete Suno browser integration** — Wire UI → API → import → playback
4. **Performance profiling** (Tracy integration)
