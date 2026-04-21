# Step B: JUCE UI-to-Engine Connection - Design Spec

**Date:** 2026-04-04
**Status:** In Progress
**Target:** 125+ tests passing (currently 119)

## Goal
Add FFI callbacks to enable JUCE UI to receive real-time updates from the Rust engine:
- Transport state sync (play/stop/record)
- Mixer level meters (real-time from audio thread)
- Clip state updates (playing/stopped/queued)
- Position change callbacks (bars.beats.sixteenths)

## Architecture

### Callback Types (C-compatible function pointers)
```rust
pub type TransportStateCallback = extern "C" fn(state: c_int);
pub type LevelMeterCallback = extern "C" fn(track: c_int, db: c_float);
pub type ClipStateCallback = extern "C" fn(track: c_int, scene: c_int, state: c_int);
pub type PositionCallback = extern "C" fn(bars: c_int, beats: c_int, sixteenths: c_int);
```

### Registration Functions
```rust
daw_register_transport_callback(callback: TransportStateCallback);
daw_register_meter_callback(callback: LevelMeterCallback);
daw_register_clip_callback(callback: ClipStateCallback);
daw_register_position_callback(callback: PositionCallback);
```

### Thread-Safe Callback Storage
- Use `once_cell::sync::Lazy` for global callback storage (like MIDI_INPUT)
- Store callbacks as `Option<extern "C" fn(...)>` in static variables
- Call from audio thread with minimal overhead (no allocations)

## Implementation Plan

### Phase 1: Define FFI Types and Storage (TDD)
1. Add callback type definitions to `ffi_bridge.rs`
2. Add global static storage for callbacks
3. Write 6 tests for callback registration
   - test_transport_callback_registration
   - test_meter_callback_registration
   - test_clip_callback_registration
   - test_position_callback_registration
   - test_null_callback_registration
   - test_multiple_callback_registration

### Phase 2: Transport State Callbacks
1. Add `TransportStateCallback` type
2. Add `daw_register_transport_callback()` FFI function
3. Add callback invocation in transport state changes
4. Write tests for transport state callbacks

### Phase 3: Mixer Level Meters (Real-Time)
1. Add `LevelMeterCallback` type
2. Add `daw_register_meter_callback()` FFI function
3. Add peak level metering to `ChannelStrip` in `mixer.rs`
4. Add callback invocation in mixer `process()` method
5. Write tests for level meter callbacks

### Phase 4: Clip State Callbacks
1. Add `ClipStateCallback` type
2. Add `daw_register_clip_callback()` FFI function
3. Add callback invocation in `SessionView` clip state changes
4. Write tests for clip state callbacks

### Phase 5: Position Callbacks
1. Add `PositionCallback` type  
2. Add `daw_register_position_callback()` FFI function
3. Add callback invocation in transport `process()` when bars/beats/sixteenths change
4. Write tests for position callbacks

## C API for JUCE

```c
// Callback types
typedef void (*TransportStateCallback)(int state);  // 0=stopped, 1=playing, 2=recording
typedef void (*LevelMeterCallback)(int track, float db);
typedef void (*ClipStateCallback)(int track, int scene, int state);  // 0=empty, 1=loaded, 2=playing, 3=recording, 4=queued
typedef void (*PositionCallback)(int bars, int beats, int sixteenths);

// Registration
void daw_register_transport_callback(TransportStateCallback cb);
void daw_register_meter_callback(LevelMeterCallback cb);
void daw_register_clip_callback(ClipStateCallback cb);
void daw_register_position_callback(PositionCallback cb);

// Unregistration (pass NULL)
void daw_unregister_transport_callback();
void daw_unregister_meter_callback();
void daw_unregister_clip_callback();
void daw_unregister_position_callback();
```

## Testing Strategy (TDD)

Each callback type gets 2-3 tests:
1. Registration test - verify callback can be registered
2. Invocation test - verify callback is called when state changes
3. Null safety test - verify null callbacks don't crash

Expected test additions: +6 tests
Expected total: 125 tests

## Files to Modify

1. `daw-engine/src/ffi_bridge.rs` - Add callback types, storage, registration functions
2. `daw-engine/src/mixer.rs` - Add peak level metering and callback invocation
3. `daw-engine/src/transport.rs` - Add callback invocation on state changes
4. `daw-engine/src/session.rs` - Add callback invocation on clip state changes

## Dev Framework Compliance

- [x] Brainstorming: This design spec
- [ ] TDD: Write failing tests first
- [ ] RED-GREEN-REFACTOR for each callback type
- [ ] Evidence: Run tests after each phase
- [ ] Output pristine: Zero compiler errors

## Risk Mitigation

- Audio thread must not block - callbacks are simple C function calls
- Callback storage is lock-free (atomic Option store)
- Null checks before every callback invocation
- Thread-safe static initialization via once_cell
