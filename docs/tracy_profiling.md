# Tracy Performance Profiling

This document describes how to use Tracy profiler with OpenDAW for real-time performance analysis.

## Overview

Tracy is a real-time profiling tool that allows visualization of CPU usage, frame times, and custom metrics. OpenDAW has integrated Tracy instrumentation into the audio engine to help identify performance bottlenecks.

## Building with Tracy

### Enable Tracy Feature

```bash
cd daw-engine
cargo build --features tracy
cargo test --features tracy
```

### Default Build (Tracy Disabled)

When Tracy is disabled, all profiling macros compile to no-ops with zero runtime overhead:

```bash
cargo build              # No Tracy overhead
cargo test --lib         # 351 tests passing
```

## Instrumented Zones

### Phase 1: Audio Engine Core (7 zones)

| Zone Name | Location | Description |
|-----------|----------|-------------|
| `audio_callback` | `callback.rs:63` | Main audio callback entry |
| `mixer_process` | `callback.rs:69` | Mixer processing within callback |
| `mixer_process` | `mixer.rs:154` | Mixer process method entry |
| `mixer_clear_output` | `mixer.rs:159` | Output buffer clearing |
| `mixer_sources` | `mixer.rs:166` | Source mixing loop |
| `mixer_source_process` | `mixer.rs:168` | Individual source processing |
| `mixer_loudness` | `mixer.rs:199` | Loudness metering |

### Phase 2: Critical Path Instrumentation (20+ zones)

#### Transport (`transport.rs`)
| Zone Name | Description |
|-----------|-------------|
| `transport_process` | Main transport position update |
| `transport_loop` | Loop wrap handling |
| `transport_punch` | Punch-in/punch-out logic |
| `transport_play` | Play command |
| `transport_stop` | Stop command |
| `transport_record` | Record command |

#### Transport Sync (`transport_sync.rs`)
| Zone Name | Description |
|-----------|-------------|
| `sync_process` | Process scheduled clips |
| `sync_schedule` | Schedule clip for playback |
| `sync_set_tempo` | Tempo change handling |
| `sync_clear_all` | Clear all scheduled clips |

#### Clip Player (`clip_player.rs`)
| Zone Name | Description |
|-----------|-------------|
| `clip_player_trigger` | Trigger clip on track |
| `clip_player_stop_all` | Stop all clips (panic) |
| `clip_player_process_queue` | Process queued clips |
| `track_trigger_clip` | Per-track clip trigger |
| `track_stop_clip` | Per-track clip stop |
| `track_queue_clip` | Queue clip for next beat |

#### Real-time (`realtime.rs`)
| Zone Name | Description |
|-----------|-------------|
| `lockfree_push` | Lock-free queue push |
| `lockfree_pop` | Lock-free queue pop |
| `rt_command_process` | Real-time command processing |
| `rt_command_handler` | Individual command handler |
| `watchdog_pet` | Watchdog timer reset |
| `stats_record_callback` | Stats recording |

#### Session (`session.rs`)
| Zone Name | Description |
|-----------|-------------|
| `session_launch_scene` | Launch scene/row |
| `session_stop_all` | Stop all clips |

#### MIDI (`midi.rs`)
| Zone Name | Description |
|-----------|-------------|
| `midi_process` | MIDI message generation |
| `midi_channel_process` | Per-channel processing |
| `midi_note_on` | Note on generation |
| `midi_note_off` | Note off generation |
| `midi_stop_all` | All notes off (panic) |

## Plotted Metrics

### Phase 1: Audio Engine Core (5 metrics)

| Metric Name | Description |
|-------------|-------------|
| `callback_cpu_usage` | Audio callback CPU percentage |
| `callback_processing_us` | Processing time in microseconds |
| `callback_samples` | Number of samples processed |
| `mixer_source_count` | Number of active mixer sources |
| `mixer_output_samples` | Output buffer sample count |

### Phase 2: Critical Path Metrics (10+ metrics)

| Metric Name | Module | Description |
|-------------|--------|-------------|
| `transport_position` | Transport | Current beat position |
| `transport_state` | Transport | Transport state (0-3: stopped/playing/recording/paused) |
| `samples_per_beat` | TransportSync | Current samples per beat |
| `pending_clips` | TransportSync | Number of scheduled clips waiting |
| `triggered_clips` | TransportSync | Clips triggered this process cycle |
| `playing_tracks` | ClipPlayer | Number of tracks with playing clips |
| `queue_length` | Realtime | Real-time command queue length |
| `callback_duration_us` | Realtime | Audio callback duration |
| `active_scene` | Session | Currently active scene index (0 = none) |
| `midi_message_count` | MIDI | Messages generated per process |
| `midi_playing_notes` | MIDI | Total active MIDI notes |

## Using Tracy Profiler

### 1. Download Tracy

Download the Tracy profiler from: https://github.com/wolfpld/tracy/releases

### 2. Start OpenDAW with Tracy Enabled

Build and run with the `tracy` feature:

```bash
cargo run --features tracy
```

### 3. Connect Tracy Profiler

1. Open Tracy profiler application
2. Click "Connect" 
3. The profiler will auto-discover the OpenDAW application on localhost
4. Alternatively, enter `localhost:9000` manually

### 4. Analyze Performance

The Tracy UI will show:
- **Timeline view**: Visual representation of all profiled zones
- **Statistics**: Average, min, max times for each zone
- **Plots**: Real-time graphs of CPU usage and other metrics
- **Frame analysis**: Detailed breakdown of each audio callback

## Profiling Macros

### `profile_scope!(name)`

Creates a named profiling zone that automatically ends when the scope exits:

```rust
fn process_audio() {
    profile_scope!("audio_process");
    
    // Do work...
    
} // Zone ends here
```

### `plot_value!(name, value)`

Plots a named numeric value for visualization:

```rust
plot_value!("cpu_usage", 45.0);
plot_value!("active_voices", voice_count as f64);
```

### `frame_mark!()`

Marks the end of a frame for frame time analysis:

```rust
fn audio_callback() {
    process_audio();
    frame_mark!();  // Marks end of this audio frame
}
```

## Performance Considerations

### Runtime Overhead

When Tracy is **disabled** (default): **Zero overhead**
- All macros compile to no-ops via `#[cfg(feature = "tracy")]`
- No runtime cost
- No additional dependencies linked
- Same code works with or without Tracy

When Tracy is **enabled**: **Minimal overhead**
- ~50-100ns per zone entry/exit
- Plotting has minimal cost
- Safe for real-time audio threads
- ~27 instrumented zones total (Phase 1 + Phase 2)

### Best Practices

1. **Instrument hot paths**: Focus on code that runs every audio callback
2. **Use descriptive names**: Zone names appear in Tracy UI
3. **Avoid excessive zones**: Too many zones can clutter the timeline
4. **Plot sparingly**: Plot only values that change meaningfully
5. **Test both modes**: Always test with and without Tracy enabled

## Troubleshooting

### "Client not running" panic

If you see this error when using Tracy macros:
```
plot! without a running Client
```

Make sure the Tracy client is initialized. This happens automatically when using the macros if the `tracy` feature is enabled.

### Connection refused

If Tracy can't connect:
1. Verify OpenDAW is built with `--features tracy`
2. Check firewall settings (port 9000)
3. Try localhost:9000 manually in Tracy connect dialog

### Missing zones

If zones don't appear in Tracy:
1. Verify code is being executed (add a print statement)
2. Check that `profile_scope!` is inside a function that actually runs
3. Rebuild with `cargo clean` and rebuild

## Example: Adding Custom Instrumentation

To add profiling to your own code:

```rust
use daw_engine::{profile_scope, plot_value, frame_mark};

fn my_audio_process() {
    profile_scope!("my_process");
    
    {
        profile_scope!("setup");
        // Setup code...
    }
    
    {
        profile_scope!("processing");
        // Heavy processing...
        plot_value!("buffer_size", samples as f64);
    }
    
    frame_mark!();
}

## Production Usage

### Server Initialization

When running the OpenDAW engine server with Tracy enabled:

```bash
# Enable Tracy via environment variable
OPENDAW_TRACY=1 cargo run --bin opendaw-server --features tracy

# Or disable auto-start (client starts but waits for connection)
OPENDAW_TRACY=1 OPENDAW_TRACY_AUTO_START=0 cargo run --bin opendaw-server --features tracy
```

The server will display Tracy status on startup:
```
║ Tracy Profiler: ENABLED (OPENDAW_TRACY=1)                    ║
```

### Build Profiles

Use the `release-tracy` profile for optimized profiling builds:

```bash
# Build with debug symbols for profiling
cargo build --profile release-tracy --features tracy

# Run tests with Tracy
cargo test --profile release-tracy --features tracy
```

**Profile Settings:**
- Debug symbols enabled (for stack traces)
- Thin LTO for balance of speed and optimization
- No symbol stripping
- Optimized for profiling accuracy

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENDAW_TRACY` | unset | Set to `1`, `true`, or `yes` to enable |
| `OPENDAW_TRACY_AUTO_START` | `1` | Set to `0` to disable auto-start |

### Memory Overhead

When Tracy is enabled:
- **Runtime overhead:** ~50-100ns per zone entry/exit
- **Memory overhead:** ~5-10MB for trace buffer
- **Network:** Localhost TCP on port 9000

When Tracy is disabled (default): **Zero overhead**

### CI/CD Integration

Run CI tests to verify Tracy integration:

```bash
# Verify Tracy feature compiles
cargo test --test tracy_ci_integration --features tracy

# Full test suite with Tracy
cargo test --features tracy
```

## Further Reading

- [Tracy Manual](https://github.com/wolfpld/tracy/releases)
- [Tracy Rust Bindings](https://docs.rs/tracy-client/)
- OpenDAW Architecture: `docs/architecture.md`
