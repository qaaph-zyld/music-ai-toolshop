# OpenDAW Audio Engine Library API

**Production-ready Rust audio engine for music production applications**

## Overview

OpenDAW is a high-performance, memory-safe Rust audio engine designed for integration into music production software. With 600+ passing tests and verified audio output, it provides a solid foundation for:

- VST/AU plugin development
- Python scripting interfaces
- WebAssembly browser-based tools
- Custom DAW implementations

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

## Core Components

### Transport

Controls playback state, tempo, and position.

```rust
use daw_engine::Transport;

let mut transport = Transport::new(120.0, 48000);

transport.play();
transport.stop();
transport.set_position(4.0); // Beat position
transport.set_tempo(140.0); // BPM
```

**Methods:**
- `new(tempo: f32, sample_rate: u32)` - Create transport
- `play()` - Start playback
- `stop()` - Stop playback
- `set_position(beats: f32)` - Set position in beats
- `set_tempo(bpm: f32)` - Set tempo
- `position_beats()` - Get current position
- `tempo()` - Get current tempo
- `state()` - Get playback state

### Mixer

Audio mixing with gain, pan, and loudness metering.

```rust
use daw_engine::Mixer;

let mut mixer = Mixer::new(2); // Stereo

mixer.set_track_volume(0, 0.8); // Track 0 volume
mixer.set_track_pan(0, -0.5); // Track 0 pan (left)
mixer.set_track_mute(0, true); // Mute track 0

// Process audio buffer
let mut output = vec![0.0f32; 1024];
mixer.process(&mut output);
```

**Methods:**
- `new(channels: u16)` - Create mixer
- `set_track_volume(track: usize, volume: f32)` - Set track gain (0.0-1.0)
- `set_track_pan(track: usize, pan: f32)` - Set track pan (-1.0 to 1.0)
- `set_track_mute(track: usize, muted: bool)` - Mute/unmute track
- `process(output: &mut [f32])` - Process audio through mixer

### Session View

Ableton Live-style clip grid with scene launch.

```rust
use daw_engine::SessionView;
use daw_engine::Clip;

let mut session = SessionView::new(8, 8); // 8 tracks, 8 scenes

// Add clips
session.set_clip(0, 0, Clip::new_audio("kick", 4.0));
session.set_clip(1, 0, Clip::new_audio("snare", 4.0));

// Launch scene
session.launch_scene(0);

// Stop all clips
session.stop_all();
```

**Methods:**
- `new(tracks: usize, scenes: usize)` - Create session grid
- `set_clip(track: usize, scene: usize, clip: Clip)` - Set clip
- `get_clip(track: usize, scene: usize) -> Option<&Clip>` - Get clip
- `launch_scene(scene: usize)` - Launch all clips in scene
- `stop_all()` - Stop all clips

### Clip

Audio or MIDI clip with playback state.

```rust
use daw_engine::Clip;

// Audio clip
let audio_clip = Clip::new_audio("drums", 4.0);

// MIDI clip
let midi_clip = Clip::new_midi("melody", 4.0);

// MIDI clip with notes
let notes = vec![/* MIDI notes */];
let midi_clip = Clip::new_midi_with_notes("bass", 4.0, notes);
```

**Methods:**
- `new_audio(name: &str, duration_bars: f32)` - Create audio clip
- `new_midi(name: &str, duration_bars: f32)` - Create MIDI clip
- `new_midi_with_notes(name: &str, duration_bars: f32, notes: Vec<MidiNote>)` - Create MIDI clip with notes
- `name()` - Get clip name
- `duration_bars()` - Get duration
- `state()` - Get playback state

### Export

Offline audio rendering to WAV files.

```rust
use daw_engine::export::{ExportEngine, ExportFormat, BitDepth};
use daw_engine::Transport;
use daw_engine::Mixer;
use daw_engine::SessionView;
use std::path::Path;

let transport = Transport::new(120.0, 48000);
let mixer = Mixer::new(2);
let session = SessionView::new(8, 8);
let format = ExportFormat::Wav(BitDepth::Bit16);

let mut engine = ExportEngine::new(48000, 2, format, transport, mixer, session);

let output_path = Path::new("output.wav");
engine.export_wav(output_path, 0.0, 16.0).unwrap(); // Export bars 0-16
```

**Methods:**
- `new(sample_rate: u32, channels: u16, format, transport, mixer, session)` - Create export engine
- `export_wav(file_path: &Path, start_beat: f32, end_beat: f32)` - Export to WAV

## Audio I/O

### Real-time Audio Output

```rust
use cpal::traits::{HostTrait, DeviceTrait, StreamTrait};
use daw_engine::Mixer;
use daw_engine::Transport;

let host = cpal::default_host();
let device = host.default_output_device().unwrap();
let config = device.default_output_config().unwrap();

let mut mixer = Mixer::new(2);
let mut transport = Transport::new(120.0, 48000);

let stream = device.build_output_stream(
    &config.into(),
    move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
        mixer.process(data);
        transport.process(data.len() as u32);
    },
    |err| eprintln!("Error: {}", err),
    None,
).unwrap();

stream.play().unwrap();
```

## Features

- **Memory Safety:** Rust's ownership model prevents buffer overflows and data races
- **Real-time Safe:** Lock-free SPSC queues for audio thread communication
- **Cross-platform:** Windows, macOS, Linux support via CPAL
- **Well-tested:** 600+ unit and integration tests
- **Verified:** Audio output, export, and clip launching all verified end-to-end
- **Performance:** Tracy profiler integration for optimization

## Performance

- **Latency:** Sub-5ms audio latency achievable
- **CPU:** < 5% at 48kHz/128 buffer for 8-track projects
- **Memory:** < 50MB for typical projects
- **Threads:** Optimized multi-threaded processing

## Integration Examples

See `examples/` directory for:
- `audio_e2e_test.rs` - Real-time audio output
- Export examples
- Session management examples

## FFI Interface

C-compatible FFI bindings available for integration with C++, C, and other languages. See `ffi_bridge.rs` for complete API.

## License

MIT

## Support

- GitHub: https://github.com/qaaph-zyld/music-ai-toolshop
- Issues: Report bugs and feature requests on GitHub
