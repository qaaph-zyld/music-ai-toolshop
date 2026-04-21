# Task B.1: CLAP SDK Plugin Hosting - Design Specification

**Date:** 2026-04-01  
**Status:** Implementation Phase  
**Estimated Duration:** 3-4 weeks

## Goal
Enable OpenDAW to host CLAP (CLever Audio Plugin API) plugins alongside existing native plugins.

## Architecture

### CLAP Plugin Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    PluginInstance                        │
├─────────────────────────────────────────────────────────┤
│  NativePlugin │ ClapPluginHost │ Lv2PluginHost         │
├─────────────────────────────────────────────────────────┤
│                    PluginChain                           │
├─────────────────────────────────────────────────────────┤
│                    Mixer Track                           │
└─────────────────────────────────────────────────────────┘
```

### Key Components

1. **ClapPluginHost** (`src/plugin_clap.rs`)
   - Wraps CLAP C ABI in safe Rust
   - Handles plugin lifecycle: create → activate → process → destroy
   - Manages audio ports (input/output buffers)
   - Bridges parameter changes (Rust ↔ CLAP)
   - Supports per-note modulation (CLAP unique feature)

2. **PluginInstance Updates** (`src/plugin.rs`)
   - Extend enum to include Clap variant
   - Unified parameter interface
   - State serialization/deserialization

3. **PluginRegistry** (`src/plugin_registry.rs`)
   - Scan for CLAP plugins in standard paths
   - Cache plugin metadata
   - Support plugin categories (Instrument, Effect, Note FX)

## CLAP → Rust Mapping

| CLAP Concept | Rust Implementation |
|--------------|---------------------|
| `clap_plugin` | `ClapPluginHost` struct |
| `clap_plugin_descriptor` | `PluginInfo` metadata |
| `clap_audio_port` | `AudioPort` buffer management |
| `clap_param` | `PluginParameter` with id/value |
| `clap_note` | `NoteEvent` for per-note modulation |
| `clap_process` | `process()` method |

## Implementation Steps

### Week 1: FFI Bindings
1. Generate FFI bindings for CLAP C headers
2. Create safe wrappers for core structs
3. Implement `ClapPluginHost::new()` with validation

### Week 2: Audio Processing
1. Implement buffer management (input/output ports)
2. Audio processing callback bridge
3. Parameter change handling (automation)

### Week 3: Advanced Features
1. Per-note modulation support
2. Note expression handling
3. Plugin state save/restore

### Week 4: Integration & Testing
1. Integrate with existing PluginChain
2. Plugin scanner/discovery
3. Write comprehensive tests

## Testing Strategy

### Unit Tests
- `test_clap_load_simple_plugin` - Load a simple CLAP plugin
- `test_clap_audio_processing` - Verify audio passes through
- `test_clap_parameter_set_get` - Parameter changes
- `test_clap_state_save_restore` - State serialization

### Integration Tests
- `test_clap_in_plugin_chain` - Full chain processing
- `test_clap_note_modulation` - Per-note features
- `test_clap_scan_discover` - Plugin discovery

## Dependencies

- `third_party/clap` - CLAP SDK (MIT licensed)
- `bindgen` - FFI binding generation (build dependency)
- `libc` - C interop

## License Compatibility

CLAP SDK is MIT licensed - fully compatible with OpenDAW's MIT license.

## Success Criteria

- [ ] Load and process audio through at least 1 CLAP plugin
- [ ] Pass all 12 planned tests
- [ ] No memory leaks (verified with valgrind/miri)
- [ ] < 1% CPU overhead vs native plugins
