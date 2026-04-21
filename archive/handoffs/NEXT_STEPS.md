# OpenDAW Next Steps Documentation

## Current State (Completed)

**Engine Solidification: COMPLETE**
- 61 tests passing, zero compiler warnings
- Real audio testing with WAV files
- Serde-based JSON serialization
- Suno Library: 20 tracks from SQLite
- Stem Extractor: Demucs subprocess integration
- ACE-Step: Algorithmic pattern generation

---

## Phase 5: UI Layer (JUCE Integration)

### Task 5.1: Set up JUCE Project Structure
**Goal**: Create CMake-based JUCE project that links to Rust audio engine

**Files to create**:
- `06-opendaw/ui/CMakeLists.txt` - JUCE with CPPMM Rust bindings
- `06-opendaw/ui/src/Main.cpp` - Application entry point
- `06-opendaw/ui/src/MainComponent.h/.cpp` - Main window

**Verification**:
```bash
cd ui && cmake -B build && cmake --build build
./build/OpenDAW --help
```

### Task 5.2: Create Session View Grid UI
**Goal**: Ableton-style clip slot grid (8 tracks x 16 scenes)

**Components**:
- `ClipSlotComponent` - Clickable clip slot (colored by clip type)
- `TrackHeaderComponent` - Track name, mute/solo/arm buttons
- `SceneLaunchComponent` - Horizontal row of scene buttons
- `SessionGridComponent` - Grid container managing layout

**Key behaviors**:
- Click clip slot → select/load clip
- Click scene button → launch all clips in row
- Drag and drop clips between slots
- Right-click context menu (duplicate, delete, color)

**Verification**: UI shows 8x16 grid, slots clickable, colors render

### Task 5.3: Transport Controls
**Goal**: Play/Stop/Record with visual feedback

**Components**:
- `TransportBar` - BPM display, tap tempo, time signature
- `PlayButton`, `StopButton`, `RecordButton` - State-aware buttons
- `MetronomeToggle` - Visual beat indicator

**Integration**:
- Rust `Transport` struct controls via FFI
- UI updates from audio thread callback

**Verification**: Press play → audio starts, BPM changes update Rust clock

### Task 5.4: Mixer Panel
**Goal**: Per-track level meters and controls

**Components**:
- `ChannelStrip` - Fader, pan, mute, solo, meter
- `MasterStrip` - Master output with limiter visualization
- `MixerPanel` - Horizontal/vertical mixer layout

**Features**:
- Peak/RMS level meters (from audio callback)
- Fader automation recording
- Pan law implementation

**Verification**: Audio playback shows level movement on meters

---

## Phase 6: Real-time Features

### Task 6.1: Low-latency Audio Thread
**Goal**: <10ms round-trip latency

**Implementation**:
- Lock-free queue for UI → audio commands
- Pre-allocated buffers (no allocations in callback)
- ASIO driver support on Windows
- Adjustable buffer size (64-2048 samples)

**Verification**: `cargo test` latency benchmark <10ms at 128 samples

### Task 6.2: MIDI Input/Recording
**Goal**: Record MIDI from controller

**Implementation**:
- CPAL MIDI device enumeration
- MIDI message queue to Rust engine
- Recording buffer with timestamp quantization
- Clip creation from recorded MIDI

**Verification**: Press MIDI key → note appears in clip

### Task 6.3: Parameter Automation
**Goal**: Record and playback fader/knob movements

**Implementation**:
- Automation lane data structure
- Sample-accurate parameter interpolation
- Write/touch/latch automation modes

**Verification**: Record fader movement → playback follows curve

---

## Phase 7: Project System

### Task 7.1: Save/Load Project Files
**Goal**: `.opendaw` project format

**Structure**:
```
Project.opendaw/
├── project.json      # Tracks, scenes, tempo, settings
├── audio/            # Referenced audio files
├── samples/          # Recorded takes
└── stems/            # Cached stem separations
```

**Implementation**:
- JSON serialization of `SessionView` state
- Audio file referencing (not embedding)
- Version migration for format changes

**Verification**: Save project → close → reopen → identical state

### Task 7.2: Export Audio
**Goal**: Render project to WAV/MP3

**Features**:
- Real-time export (faster than real-time possible?)
- Stem export option (all tracks separate)
- MP3 320kbps / WAV 24-bit options

**Verification**: Export 2-minute song → valid audio file plays

---

## Phase 8: AI Integration Polish

### Task 8.1: Suno Library Browser UI
**Goal**: Browse, preview, import from Suno library

**UI Components**:
- Search/filter sidebar (genre, tempo, key)
- Waveform preview with playhead
- Drag to clip slot to import
- Metadata display (title, artist, tags)

**Verification**: Browse 20 tracks, preview plays audio

### Task 8.2: Stem Separation Workflow
**Goal**: One-click stem split and import

**Workflow**:
1. Drag audio to track
2. Right-click → "Extract Stems"
3. Progress dialog shows demucs processing
4. Results appear as 4 new tracks

**Verification**: Separate 30-second clip → 4 stems loaded in <2 min

### Task 8.3: AI Pattern Generation UI
**Goal**: Generate MIDI clips from style selection

**UI Components**:
- Style picker (electronic, house, techno, ambient, jazz)
- Tempo/key/bars input
- "Generate" button with loading state
- Preview before commit

**Verification**: Generate techno pattern 128 BPM → MIDI clip appears

---

## Phase 9: Performance Optimization

### Task 9.1: Audio Engine Profiling
**Goal**: Identify hotspots

**Tools**:
- Tracy profiler integration
- Per-plugin CPU metering
- Buffer underrun detection/logging

**Target**: <5% CPU at 48kHz/128 samples with 8 tracks

### Task 9.2: Memory Pool Allocators
**Goal**: Zero allocations in audio thread

**Implementation**:
- Object pool for `SamplePlayer` instances
- Pre-allocated scratch buffers
- Lock-free ring buffer for commands

**Verification**: Valgrind shows no mallocs during `process()` calls

### Task 9.3: Disk Streaming
**Goal**: Play long audio files without loading to RAM

**Implementation**:
- Background read-ahead thread
- Circular buffer for audio data
- Double-buffered file I/O

**Verification**: Play 10-minute WAV file, RAM usage <50MB

---

## Phase 10: Distribution

### Task 10.1: Installer/Package
**Goal**: One-click install for end users

**Windows**:
- WiX installer with VCRedist bundle
- Portable ZIP option
- Registry association for .opendaw files

**macOS**:
- DMG with drag-to-Applications
- Code signing (Apple Developer cert)

### Task 10.2: User Documentation
**Goal**: Help users be productive

**Contents**:
- Quick start guide (5-minute tutorial)
- Keyboard shortcut reference
- AI features explained
- Troubleshooting common issues

### Task 10.3: Onboarding Flow
**Goal**: First-launch experience

**Features**:
- Demo project pre-loaded
- Interactive tutorial ("Click here to add a clip")
- Audio engine test (play test tone)

---

## Priority Order

**Immediate (Next 2 weeks)**:
1. JUCE project setup (Task 5.1)
2. Session view grid (Task 5.2)
3. Transport controls (Task 5.3)

**Short-term (Next month)**:
4. Save/load projects (Task 7.1)
5. MIDI recording (Task 6.2)
6. Suno browser UI (Task 8.1)

**Medium-term (2-3 months)**:
7. Export audio (Task 7.2)
8. Performance optimization (Phase 9)
9. Distribution packaging (Phase 10)

---

## Technical Decisions to Make

1. **UI Framework**: JUCE vs. custom ImGui vs. web-based (Electron)
2. **FFI Binding**: Manual C bindings vs. CXX vs. UniFFI
3. **Plugin Support**: VST3 hosting for instrument/effect plugins
4. **Cloud Sync**: Optional project backup to cloud storage
5. **Collaboration**: Real-time multi-user editing (WebRTC?)

## Current Blockers

None - ready to proceed with UI layer.

**Recommended first step**: Create `06-opendaw/ui/` directory and JUCE CMake setup.
