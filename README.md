# OpenDAW - Library + Full DAW

**Production-ready Rust audio engine library with complete JUCE C++ UI**

OpenDAW is a high-performance, memory-safe Rust audio engine designed for integration into music production software, now with a fully functional JUCE-based C++ UI. With 600+ passing tests and verified audio output, it provides:

- **As a Library:** VST/AU plugin development, Python scripting, WebAssembly tools, custom DAWs
- **As a Full DAW:** Complete JUCE C++ UI with transport controls, mixer, arrangement view, and AI integrations

## Quick Start

```toml
[dependencies]
daw-engine = "0.1.0"
```

```rust
use daw_engine::{Mixer, Transport, SessionView, Clip};

// Create audio engine components
let mut transport = Transport::new(120.0, 48000);
let mut mixer = Mixer::new(2); // Stereo
let mut session = SessionView::new(8, 8); // 8 tracks, 8 scenes

// Add a clip
let clip = Clip::new_audio("drums", 4.0);
session.set_clip(0, 0, clip);

// Launch clip
session.launch_scene(0);
```

## Architecture

```
┌──────────────────────────────────────────────────┐
│           Audio Engine (Rust)                    │
│  Mixer │ SamplePlayer │ Transport │ Session      │
│  MIDI │ ClipPlayer │ Realtime Queue │ Export     │
├──────────────────────────────────────────────────┤
│          FFI Bridge (staticlib)                  │
│  C-compatible API for C++, Python, etc.         │
├──────────────────────────────────────────────────┤
│         JUCE C++ UI (Active)                     │
│  Transport │ Mixer │ Arrangement │ AI Tools      │
├──────────────────────────────────────────────────┤
│         Integration Examples                     │
│  Python bindings │ VST plugin │ WebAssembly     │
└──────────────────────────────────────────────────┘
```

## Project Structure

```
06-opendaw/
├── daw-engine/              # Rust audio engine library
│   ├── src/                 # Core engine, FFI, AI bridges
│   ├── tests/               # 600+ passing tests
│   ├── examples/            # Integration examples
│   │   ├── audio_e2e_test.rs
│   │   ├── python_integration_example.py
│   │   └── vst_plugin_integration_example.rs
│   └── LIBRARY_API.md       # Complete API documentation
├── ui/                      # JUCE C++ UI (Active - Built Successfully)
│   ├── src/                 # 73 C++ source files
│   │   ├── Transport/       # Transport controls, loop markers
│   │   ├── Mixer/           # Channel strips, level meters
│   │   ├── Arrangement/     # Timeline, clip editing
│   │   ├── SessionView/     # Clip grid, scene launching
│   │   ├── Engine/          # FFI bridge to Rust engine
│   │   └── Tools/           # Vocal cleanup, stem extraction
│   ├── CMakeLists.txt       # CMake build configuration
│   └── build/               # Visual Studio build output
├── ai_modules/              # Python AI integrations
│   ├── suno_library/        # SQLite track browser
│   ├── stem_extractor/      # Demucs wrapper
│   ├── pattern_generator/   # Algorithmic MIDI gen
│   ├── musicgen/            # AudioCraft bridge
│   └── production_analyzer/ # Audio classifier
├── CURRENT_STATE.md         # Single source of truth
└── archive/                 # Archived handoff documents
```

## Quick Start

### As a Library
```bash
# Build and test the audio engine
cd daw-engine
cargo test --lib    # 600 tests passing
cargo build --release  # Produces daw_engine.lib (staticlib)

# Run audio E2E test
cargo run --example audio_e2e_test  # Plays 440Hz tone

# See library API documentation
cat LIBRARY_API.md
```

### As a Full DAW (C++ UI)
```bash
# Build the Rust engine (staticlib for linking)
cd daw-engine
cargo build --release

# Build the C++ UI (requires Visual Studio Build Tools 2022)
cd ../ui
cmake -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Debug

# Run the application
./build/OpenDAW_artefacts/Debug/OpenDAW.exe
```

## Verified Status (2026-05-06)

| Metric | Value | Verified |
|--------|-------|----------|
| Rust tests | **600 passed, 0 failed, 6 ignored** | ✅ |
| Audio E2E | **PASSED** - 440Hz through full stack | ✅ |
| Export | **PASSED** - WAV export (2 tests) | ✅ |
| Clip Launch | **PASSED** - Programmatic (4 tests) | ✅ |
| C++ UI Build | **PASSED** - JUCE 7.0.9 + Visual Studio 2022 | ✅ |
| C++ UI Launch | **PASSED** - Application starts successfully | ✅ |
| Transport Controls | **PASSED** - Play/Stop/Record available | ✅ |
| Compiler warnings | 21 (0 errors) | ✅ |
| Active Rust modules | ~40 | ✅ |

See `CURRENT_STATE.md` for detailed component status.

## Features

### Audio Engine (Rust)
- **Memory Safety:** Rust's ownership model prevents buffer overflows and data races
- **Real-time Safe:** Lock-free SPSC queues for audio thread communication
- **Cross-platform:** Windows, macOS, Linux support via CPAL
- **Well-tested:** 600+ unit and integration tests
- **Verified:** Audio output, export, and clip launching all verified end-to-end
- **Performance:** Tracy profiler integration for optimization

### C++ UI (JUCE)
- **Transport Controls:** Play, Stop, Record with real-time feedback
- **Mixer:** 8-track mixer with level meters, mute/solo, pan, and volume
- **Session View:** Clip grid for scene-based launching
- **Arrangement View:** Timeline with clip editing, drag/resize, and loop markers
- **AI Tools:** Integrated Suno library, stem extraction, pattern generator
- **Onboarding:** First-launch tutorial and audio engine test

## Performance

- **Latency:** Sub-5ms audio latency achievable
- **CPU:** < 5% at 48kHz/128 buffer for 8-track projects
- **Memory:** < 50MB for typical projects
- **Threads:** Optimized multi-threaded processing

## Integration Examples

### Python
```python
# See examples/python_integration_example.py
import ctypes
engine = ctypes.CDLL("daw_engine.dll")
engine_ptr = engine.daw_engine_init(48000, 512)
engine.daw_transport_play(engine_ptr)
```

### VST Plugin
```rust
// See examples/vst_plugin_integration_example.rs
struct VST3Plugin {
    engine: OpenDAWPlugin,
}
impl VST3Plugin {
    pub fn process(&mut self, inputs: &[f32], outputs: &mut [f32]) {
        self.engine.process(inputs, outputs);
    }
}
```

### Direct Rust
```rust
use daw_engine::{Mixer, Transport, SessionView, Clip};
let mut mixer = Mixer::new(2);
let mut transport = Transport::new(120.0, 48000);
let mut session = SessionView::new(8, 8);
```

## Documentation

- **LIBRARY_API.md** - Complete API reference
- **CURRENT_STATE.md** - Detailed component status
- **examples/** - Integration examples

## AI Integrations

The engine includes Python AI modules for advanced music production:

### Pattern Generator (Algorithmic)
```python
from ai_modules.pattern_generator import ACEStepBridge
bridge = ACEStepBridge()
clip = bridge.generate_pattern("electronic", 120, "C", 4)
```

### Stem Extraction (Demucs)
```python
from ai_modules.stem_extractor import StemExtractor
extractor = StemExtractor()
stems = extractor.separate("song.wav")
```

### Suno Library (SQLite)
```python
from ai_modules.suno_library import SunoLibrary
library = SunoLibrary()
tracks = library.search(genre="electronic", tempo_range=(120, 130))
```

## License

MIT

## Repository

GitHub: https://github.com/qaaph-zyld/music-ai-toolshop
