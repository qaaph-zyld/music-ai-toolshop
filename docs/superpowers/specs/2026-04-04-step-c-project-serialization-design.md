# Step C: Project Save/Load System - Design Spec

**Date:** 2026-04-04
**Status:** In Progress
**Target:** 135+ tests passing (currently 125)

## Goal
Implement JSON serialization for projects with full state preservation, enabling project save/load functionality for the JUCE UI.

## Architecture

### JSON Format Structure
```json
{
  "version": "1.0",
  "project": {
    "name": "My Song",
    "created_at": "2026-04-04T03:00:00Z",
    "modified_at": "2026-04-04T03:30:00Z"
  },
  "transport": {
    "tempo": 120.0,
    "position_beats": 16.0,
    "loop_enabled": true,
    "loop_start": 0.0,
    "loop_end": 16.0,
    "play_mode": "Loop"
  },
  "mixer": {
    "channels": 8,
    "tracks": [
      {
        "index": 0,
        "name": "Kick",
        "volume_db": -6.0,
        "pan": 0.0,
        "mute": false,
        "solo": false
      }
    ]
  },
  "session": {
    "tracks": 8,
    "scenes": 16,
    "clips": [
      {
        "track": 0,
        "scene": 0,
        "name": "Kick Loop",
        "duration_bars": 4.0,
        "type": "audio",
        "file_path": "samples/kick.wav"
      }
    ]
  },
  "plugin_chains": {
    "track_0": [
      {
        "id": "gain-1",
        "type": "GainPlugin",
        "enabled": true,
        "params": {
          "gain_db": 6.0
        }
      }
    ]
  }
}
```

### Serde Implementation Strategy

**Files to Create/Modify:**
1. `daw-engine/Cargo.toml` - Add `serde = { version = "1.0", features = ["derive"] }` and `serde_json = "1.0"`
2. `daw-engine/src/serialization.rs` (new) - Core serialization module
3. `daw-engine/src/project.rs` - Add `save_to_file()` and `load_from_file()`
4. `daw-engine/src/ffi_bridge.rs` - Add FFI exports for save/load

## Implementation Plan

### Phase 1: Dependencies and Core Types (TDD)
1. Add serde dependencies to Cargo.toml
2. Derive Serialize/Deserialize for core types:
   - `TransportState`, `PlayMode`
   - `ClipState`
   - Project configuration structs
3. Write 3 tests for basic serialization round-trip

### Phase 2: Project Serialization
1. Implement `Project::to_json()` and `Project::from_json()`
2. Add file I/O methods: `save_to_file()`, `load_from_file()`
3. Write 3 tests for project save/load

### Phase 3: Session Serialization
1. Implement `SessionView` serialization
2. Serialize clips with their positions (track, scene)
3. Serialize scene states
4. Write 3 tests for session round-trip

### Phase 4: Mixer State Serialization
1. Implement mixer track state serialization
2. Include volume, pan, mute, solo for each track
3. Write 2 tests for mixer state preservation

### Phase 5: Transport State Serialization
1. Serialize tempo, position, loop settings
2. Serialize play mode
3. Write 2 tests for transport state

### Phase 6: Plugin Chain Serialization
1. Serialize plugin chains per track
2. Include plugin IDs, enabled state, parameters
3. Write 2 tests for plugin chain serialization

### Phase 7: FFI Integration
1. Add `daw_project_save(engine, path) -> i32`
2. Add `daw_project_load(engine, path) -> i32`
3. Write 2 tests for FFI save/load

**Expected Tests:** +10 passing
**Expected Total:** 135 tests

## Dev Framework Compliance

- [x] Brainstorming: This design spec
- [ ] TDD: Write failing tests first
- [ ] RED-GREEN-REFACTOR for each module
- [ ] Evidence: Run tests after each phase
- [ ] Output pristine: Zero compiler errors

## C API for JUCE

```c
// Save project to file
// Returns 0 on success, -1 on error
int daw_project_save(void* engine, const char* file_path);

// Load project from file
// Returns 0 on success, -1 on error
int daw_project_load(void* engine, const char* file_path);

// Get last error message (if save/load failed)
const char* daw_project_last_error();
```

## Risk Mitigation

- Use serde's default values for backward compatibility
- Validate JSON version on load (warn if mismatched)
- Atomic file writes (write to temp, rename on success)
- Graceful degradation for missing optional fields
