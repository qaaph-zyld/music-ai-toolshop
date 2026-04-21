# OpenDAW Project - Continuation Prompt

## Project Overview
OpenDAW is a Rust-based digital audio workstation with JUCE C++ UI integration, featuring AI-powered music generation (Suno, ACE-Step), stem separation (Demucs), and a session-based clip launcher.

## Current Status (Session of Apr 7, 2026)

### ✅ Completed Features

**Phase 1-4: Core Engine (SOLID)**
- Audio engine with 854 passing tests
- Mixer, SamplePlayer, Transport, SessionView
- MIDI engine with note events
- Callback system with profiling metrics
- WAV loading via hound with real test assets
- Serde-based JSON parsing
- Zero compiler warnings

**Phase 5: JUCE UI Framework**
- CMake project structure at `ui/`
- Session View grid (8x16 clip slots, track headers, scene buttons)
- Transport Bar (play/stop/record, tempo, time display)
- Mixer Panel (channel strips with level meters)
- EngineBridge FFI for Rust communication

**Phase 6: Real-time Features**
- Lock-free SPSC queue with atomic indices
- Real-time safe command processing
- MIDI Input/Recording with quantization
- Transport Sync with quantized clip launching
- Clip Player state management

**Phase 7: Project System (COMPLETE)**
- **Phase 7.1**: MIDI Recording - Record from MIDI devices to clips
- **Phase 7.2**: Mixer Level Meters - Peak/RMS meters per track + master
- **Phase 7.3 Core**: Project Save/Load - `.opendaw` format, JSON serialization
- **Phase 7.3 UI**: File menu, ProjectManager dialogs, keyboard shortcuts

**Phase 8: AI Integration Polish**
- **Phase 8.1-8.4**: API fixes, Test API Server, EngineBridge FFI fixes
- **Phase 8.5**: Suno Browser re-enabled with async HTTP, proper JSON parsing
  - View menu toggle
  - Side panel integration (350px)
  - Import creates orange clip in session grid

**AI Integrations**
- Suno Library: Real SQLite queries (20 tracks loaded)
- Stem Extractor: Demucs subprocess with caching
- ACE-Step: Algorithmic pattern generation

### 📁 Key Files

**Backend:**
- `daw-engine/src/api_server.rs` - Axum HTTP server
- `daw-engine/Cargo.toml` - Dependencies

**Engine Core:**
- `daw-engine/src/lib.rs` - Module exports
- `daw-engine/src/mixer.rs` - Audio mixing
- `daw-engine/src/session.rs` - Session view clips/scenes
- `daw-engine/src/transport.rs` - Playback transport
- `daw-engine/src/midi.rs` - MIDI engine
- `daw-engine/src/midi_input.rs` - MIDI recording
- `daw-engine/src/project.rs` - Project/tracks
- `daw-engine/src/project_file.rs` - Save/load
- `daw-engine/src/project_ffi.rs` - Project FFI (7 tests)
- `daw-engine/src/meter_ffi.rs` - Meter level FFI
- `daw-engine/src/ffi_bridge.rs` - Main FFI bridge
- `daw-engine/src/ai_bridge.rs` - AI integrations
- `daw-engine/src/error.rs` - DAWError types

**UI Layer:**
- `ui/CMakeLists.txt` - JUCE build config
- `ui/src/Main.cpp` - App entry
- `ui/src/MainComponent.{h,cpp}` - Main window with menu bar
- `ui/src/Project/ProjectManager.{h,cpp}` - Project dialogs
- `ui/src/SessionView/*` - Grid UI with clearAllClips()
- `ui/src/Transport/*` - Transport controls
- `ui/src/Mixer/*` - Channel strips with meters
- `ui/src/Engine/EngineBridge.{h,cpp}` - FFI bridge with project methods

**Tests:**
- 853 tests passing (`cargo test --lib`)
- 1 pre-existing flaky profiling test

### 📋 Pending Tasks

**High Priority:**
1. **Phase 8.1**: Suno Library Browser UI
   - Fix SunoBrowserComponent API compatibility
   - Integrate with ai_modules/suno_library Python backend
   - Search, filter by genre/tempo, preview, drag-to-import

2. **Phase 9.1**: Audio Engine Profiling
   - Tracy profiler integration
   - Per-track CPU metering
   - Buffer underrun detection

3. **Phase 7.4**: Export Audio (if not done)
   - Render project to WAV/MP3
   - Stem export option

**Medium Priority:**
4. **Phase 9.2**: Memory Pool Allocators
5. **Phase 9.3**: Disk Streaming for long audio files
6. **Phase 10**: Distribution packaging

### 🔧 Current Build Status

```bash
cd d:\Project\music-ai-toolshop\projects\06-opendaw\daw-engine
cargo test --lib  # 853 tests passing

cd d:\Project\music-ai-toolshop\projects\06-opendaw\ui
cmake -B build && cmake --build build  # MainComponent/ProjectManager compile OK
# Note: SunoBrowserComponent/ExportDialog have pre-existing API issues
```

### 📦 Dependencies
- `serde`, `serde_json` - Serialization
- `chrono` - Timestamps
- `cpal` - Audio I/O
- `crossbeam` - Thread channels
- `hound` - WAV files
- `thiserror` - Error handling
- `std::sync::atomic` - Lock-free data structures

### 🎯 Next Immediate Task

**RECOMMENDED: Phase 8.1 - Suno Library Browser UI**
Fix API compatibility issues, integrate Python backend, enable track browsing/importing.

Alternative options:
- Phase 9.1 - Audio Engine Profiling (Tracy)
- Phase 7.4 - Export Audio dialog

### 🔗 Git Repository
Repository: `music-ai-toolshop/projects/06-opendaw/`
Commit state: Phase 7.3 UI COMPLETE, 853 tests passing

---

## Session Start Instructions

1. Read latest handoff: `HANDOFF-2026-04-08-PHASE-8-5.md`
2. Verify test status: `cargo test --lib`
3. Check `.go/rules.md` for current phase
4. Continue with recommended task or user-directed priority

---

**COPY-PASTE PROMPT FOR NEXT SESSION:**
```
@[music-ai-toolshop/projects/06-opendaw/HANDOFF-2026-04-08-PHASE-8-5.md] lets brainstorm a bit regarding next steps and determine a plan. don't forget to implement @rules: .go as far as you can, then, once you finish proceeding autonomously, write another handoff and write in copy paste block this same prompt, just with new handoff version
```

