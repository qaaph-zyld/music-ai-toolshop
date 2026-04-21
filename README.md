# OpenDAW

Rust-based Digital Audio Workstation with JUCE C++ UI and Python AI integrations.

## Architecture

```
┌──────────────────────────────────────────────────┐
│              UI Layer (JUCE C++)                  │
│  SessionGrid │ Mixer │ Transport │ SunoBrowser   │
├──────────────────────────────────────────────────┤
│          FFI Bridge (cdylib DLL)                 │
│  ffi_bridge │ engine_ffi │ midi_ffi │ etc.       │
├──────────────────────────────────────────────────┤
│           Audio Engine (Rust)                    │
│  Mixer │ SamplePlayer │ Transport │ Session      │
│  MIDI │ ClipPlayer │ Realtime Queue │ Export     │
├──────────────────────────────────────────────────┤
│         AI Modules (Python)                      │
│  suno_library │ stem_extractor │ pattern_gen     │
└──────────────────────────────────────────────────┘
```

## Project Structure

```
06-opendaw/
├── daw-engine/              # Rust audio engine (~40 active modules)
│   ├── src/                 # Core engine, FFI, AI bridges
│   │   ├── future/          # 53 quarantined stub modules (aspirational)
│   │   └── ...
│   └── tests/               # Integration tests
├── ui/                      # JUCE C++ UI (52 source files)
│   └── src/
│       ├── SessionView/     # Clip grid (8x16)
│       ├── Mixer/           # Channel strips + meters
│       ├── Transport/       # Play/stop/record
│       ├── Engine/          # EngineBridge FFI
│       └── ...
├── ai_modules/              # Python AI integrations
│   ├── suno_library/        # SQLite track browser (real)
│   ├── stem_extractor/      # Demucs wrapper (real)
│   ├── pattern_generator/   # Algorithmic MIDI gen (real)
│   ├── musicgen/            # AudioCraft bridge (code exists)
│   └── production_analyzer/ # Audio classifier (code exists)
├── CURRENT_STATE.md         # Single source of truth
└── archive/                 # 44 archived handoff documents
```

## Quick Start

```bash
# Build and test the audio engine
cd daw-engine
cargo test --lib    # 341 tests passing
cargo build --release  # Produces daw_engine.dll

# Build C++ UI (requires JUCE + CMake)
cd ui
cmake -B build && cmake --build build
```

## Verified Status (2026-04-12)

| Metric | Value |
|--------|-------|
| Rust tests | **341 passed, 0 failed, 1 ignored** |
| Compiler warnings | 51 (0 errors) |
| Active Rust modules | ~40 |
| C++ UI files | 52 |
| AI modules (real) | 5 |

See `CURRENT_STATE.md` for detailed component status.

## AI Integrations

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
