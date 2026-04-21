# OpenDAW Phase 6.1 Design: Real-time Audio Thread

**Date:** 2026-04-06
**Phase:** 6.1 - Real-time Audio Thread Integration
**Goal:** Connect JUCE audio callback to Rust engine with <10ms latency

## Architecture

### Component Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                     JUCE Audio Thread                        │
│  ┌──────────────────┐         ┌──────────────────────┐     │
│  │ AudioAppComponent │         │ AudioDeviceManager   │     │
│  │  (getNextAudioBlock)│◄───────│  (enumerate devices) │     │
│  └────────┬───────────┘         └──────────────────────┘     │
│           │                                                  │
│           │ FFI call (lock-free)                             │
│           ▼                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │
┌───────────┼──────────────────────────────────────────────────┐
│           │              Rust Engine                         │
│           ▼                                                  │
│  ┌──────────────────┐         ┌──────────────────────┐     │
│  │ audio_processor  │◄────────│   mixer::Mixer       │     │
│  │ (process_buffer)  │         │   (sum tracks)       │     │
│  └────────┬──────────┘         └──────────────────────┘     │
│           │                                                  │
│           │ callbacks                                        │
│           ▼                                                  │
│  ┌──────────────────┐         ┌──────────────────────┐     │
│  │ transport::Transport│◄──────│   clip_players       │     │
│  │ (clock/position)   │       │   (sample playback)  │     │
│  └────────────────────┘       └──────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## FFI Interface

### Rust → C (Exports)
```rust
// Audio processing
pub extern "C" fn opendaw_process_audio(
    engine: *mut Engine,
    input_l: *const f32,
    input_r: *const f32,
    output_l: *mut f32,
    output_r: *mut f32,
    num_samples: usize,
    sample_rate: f64,
) -> i32;

// Meter reading (lock-free)
pub extern "C" fn opendaw_get_meter_levels(
    engine: *mut Engine,
    track_index: usize,
    peak: *mut f32,
    rms: *mut f32,
) -> i32;
```

### C++ → Rust (Imports)
```cpp
extern "C" {
    int opendaw_process_audio(
        void* engine,
        const float* input_l, const float* input_r,
        float* output_l, float* output_r,
        size_t num_samples, double sample_rate
    );
    
    int opendaw_get_meter_levels(
        void* engine, size_t track_index,
        float* peak, float* rms
    );
}
```

## Zero-Allocation Strategy

1. **Pre-allocated Buffers:** Engine owns `Vec<f32>` scratch buffers
2. **Lock-free Ring Buffer:** UI reads meter levels via atomic ring buffer
3. **No mallocs in process():** All allocations happen at init time
4. **Fixed-size mixing:** Max 32 tracks, pre-allocated mixer channels

## Real-time Safety Checklist

- [ ] No mutex/locks in audio callback
- [ ] No memory allocation in process()
- [ ] No file I/O in audio thread
- [ ] Bounded processing time (<1ms for 128 samples)
- [ ] Lock-free communication with UI thread

## Testing Strategy

1. **Unit Tests:** Mock audio callback, verify output buffer values
2. **Integration Tests:** JUCE AudioDeviceManager → Rust round-trip
3. **Latency Benchmark:** Measure callback duration
4. **Zero-allocation Test:** Custom allocator tracking

## Files to Create/Modify

### New Rust Files:
- `daw-engine/src/audio_processor.rs` - Audio processing FFI
- `daw-engine/src/ring_buffer.rs` - Lock-free ring buffer for meters

### Modified Rust Files:
- `daw-engine/src/lib.rs` - Add audio_processor module
- `daw-engine/src/engine_ffi.rs` - Add audio processing exports

### New C++ Files:
- `ui/src/Audio/AudioEngineComponent.h/.cpp` - JUCE audio app component

### Modified C++ Files:
- `ui/CMakeLists.txt` - Add Audio directory
- `ui/src/MainComponent.cpp` - Integrate audio engine

## Success Criteria

1. JUCE audio callback successfully delegates to Rust
2. 750+ tests passing (with new audio processor tests)
3. Zero compiler warnings
4. Meter levels update from audio thread (lock-free)
5. Transport sync is sample-accurate
6. No allocations during audio processing

## Verification Commands

```bash
cd d:\Project\music-ai-toolshop\projects\06-opendaw\daw-engine
cargo test audio_processor --lib
cargo test --lib  # All 750+ tests
cargo build --lib --release  # Zero warnings
```
