# OpenDAW

Custom AI-Powered Digital Audio Workstation with native desktop performance, integrating ACE-Step AI generation and stem extraction.

## Overview

OpenDAW is a hybrid Ableton-style DAW built with Rust (audio engine), C++ (UI), and Python (AI bridge) following TDD principles from dev_framework.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer (JUCE)                     │
├─────────────────────────────────────────────────────────┤
│                 Application Layer (C++)                │
├─────────────────────────────────────────────────────────┤
│                  Audio Engine (Rust)                     │
│   Real-time Mixer │ Sample Playback │ MIDI Engine      │
├─────────────────────────────────────────────────────────┤
│              AI/ML Bridge (Python via PyO3)          │
│       ACE-Step Gen │ Stem Extract │ Suno Library       │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
06-opendaw/
├── daw-engine/              # Rust audio engine
│   ├── src/
│   │   ├── lib.rs           # Main exports
│   │   ├── callback.rs      # Audio callback
│   │   ├── generators.rs    # SineWave, oscillators
│   │   ├── mixer.rs         # Audio mixing
│   │   ├── clock.rs         # Transport clock
│   │   ├── stream.rs        # CPAL integration
│   │   ├── sample.rs        # Sample loading
│   │   ├── sample_player.rs # Sample playback
│   │   ├── session.rs      # Session view
│   │   ├── midi.rs         # MIDI engine
│   │   ├── project.rs      # Save/load
│   │   └── transport.rs    # Transport controls
│   └── tests/
│       ├── audio_callback_test.rs  # 3 tests
│       ├── mixer_test.rs           # 3 tests
│       ├── clock_test.rs           # 4 tests
│       ├── cpal_integration_test.rs # 1+2 ignored
│       ├── sample_test.rs          # 1+4 ignored
│       ├── session_test.rs         # 10 tests
│       ├── midi_test.rs            # 9 tests
│       ├── project_test.rs         # 7 tests (1 ignored)
│       └── transport_test.rs       # 10 tests
└── ai_modules/               # Python AI integrations
    ├── ace_step_bridge/     # AI music generation
    ├── stem_extractor/      # Audio source separation
    └── suno_library/        # Sample/loop browser
```

## Quick Start

```bash
# Build the audio engine
cd daw-engine
cargo build

# Run all tests
cargo test

# Run with real audio (requires hardware)
cargo test -- --ignored
```

## Current Status

**Phase 1 Complete (Foundation):**
- ✅ Audio callback with sine wave generation
- ✅ Mixer with gain control
- ✅ Transport clock with tempo/BPM
- ✅ CPAL integration for device enumeration
- ✅ Sample playback structure
- ✅ Python AI bridge modules

**Phase 2 Complete (Core DAW):**
- ✅ Session View (clip slots, scene launch, playback states)
- ✅ MIDI support (note on/off, velocity, channels, CC)
- ✅ Project save/load (JSON serialization)
- ✅ Transport controls (play/stop/record/pause, loop, punch-in/out)

**Total Tests: 53 (48 passing + 5 hardware-dependent ignored)**

## Integration Points

### ACE-Step (AI Generation)
```python
from ai_modules.ace_step_bridge import ACEStepBridge

bridge = ACEStepBridge()
clip = bridge.generate_pattern("electronic", 120, "C", 4)
```

### Stem Extraction
```python
from ai_modules.stem_extractor import StemExtractor

extractor = StemExtractor()
stems = extractor.separate("song.wav")
# Returns: {drums, bass, vocals, other}
```

### Suno Library
```python
from ai_modules.suno_library import SunoLibrary

library = SunoLibrary()
tracks = library.search(genre="electronic", tempo_range=(120, 130))
```

## License

MIT
