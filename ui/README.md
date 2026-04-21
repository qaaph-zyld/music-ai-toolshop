# OpenDAW UI (JUCE)

This directory contains the JUCE-based C++ UI for OpenDAW.

## Structure

```
ui/
├── CMakeLists.txt          # JUCE CMake configuration
├── src/
│   ├── Main.cpp            # Application entry point
│   ├── MainComponent.h/.cpp # Main window layout
│   ├── SessionView/         # Ableton-style clip grid
│   │   ├── ClipSlotComponent.h/.cpp
│   │   ├── TrackHeaderComponent.h/.cpp
│   │   ├── SceneLaunchComponent.h/.cpp
│   │   └── SessionGridComponent.h/.cpp
│   ├── Transport/           # Play/Stop/Record controls
│   │   └── TransportBar.h/.cpp
│   ├── Mixer/               # Channel strips and meters
│   │   ├── ChannelStrip.h/.cpp
│   │   └── MixerPanel.h/.cpp
│   └── Engine/              # Rust FFI bridge
│       └── EngineBridge.h/.cpp
```

## Building

### Prerequisites
- CMake 3.15+
- C++17 compiler (MSVC, Clang, or GCC)
- Internet connection (JUCE fetched via CMake)

### Build Steps

```bash
cd ui
mkdir build && cd build
cmake ..
cmake --build . --config Release
```

### Running

```bash
./build/OpenDAW_artefacts/Release/OpenDAW.exe
```

## Architecture

### UI Components

**SessionGridComponent** - Ableton-style clip launcher
- 8 tracks x 16 scenes
- Clip slots with color coding
- Drag-and-drop support
- Scene launch buttons

**TransportBar** - Playback controls
- Play/Stop/Record buttons
- BPM display and tap tempo
- Time display (bars.beats.sixteenths)
- Metronome toggle

**MixerPanel** - Channel strips
- Per-track fader, pan, mute, solo
- Real-time level meters
- Master output strip

### Engine Integration

The `EngineBridge` class provides:
- Thread-safe command queue for UI → Engine communication
- Callbacks for Engine → UI state updates
- Placeholder FFI stubs for Rust integration

## Integration with Rust Engine

To connect to the Rust audio engine:

1. Implement FFI bindings in `daw-engine/src/ffi.rs`
2. Update `EngineBridge.cpp` to call actual FFI functions
3. Link Rust library in CMakeLists.txt

## TODO

- [ ] Add keyboard shortcuts (Space=Play, Ctrl+S=Save)
- [ ] Implement project file open/save dialogs
- [ ] Add audio file drag-and-drop
- [ ] Implement MIDI controller mapping
- [ ] Add plugin window hosting (VST3)
