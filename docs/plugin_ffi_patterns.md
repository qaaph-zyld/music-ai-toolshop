# Plugin FFI UI Integration Patterns

**Document:** UI Integration Patterns for Plugin Chain FFI  
**Project:** OpenDAW Phase 9 - Audio Effects Chain  
**Date:** 2026-04-30

## Overview

This document describes the UI integration patterns used for the Plugin Chain FFI layer, following the established conventions from `meter_ffi.rs` and `midi_edit_ffi.rs`.

## Architecture Pattern

The Plugin FFI follows the **Global State with FFI Exports** pattern, consistent with other FFI modules in OpenDAW:

```
┌──────────────────────────────────────────────────┐
│              C++ UI Layer (JUCE)                  │
│  PluginBrowser │ PluginChainDialog │ ChannelStrip│
├──────────────────────────────────────────────────┤
│              EngineBridge (C++)                   │
│  getPluginRegistry() │ addPluginToChain()         │
├──────────────────────────────────────────────────┤
│              Rust FFI Layer                       │
│  plugin_ffi.rs - Global state + FFI exports       │
├──────────────────────────────────────────────────┤
│              Rust Core Engine                     │
│  PluginChain │ PluginRegistry │ GainPlugin       │
└──────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Global State with Lazy Initialization

**Pattern:** Use `Lazy<Mutex<HashMap>>` for global state that persists across FFI calls.

**Example from `plugin_ffi.rs`:**

```rust
use once_cell::sync::Lazy;
use std::collections::HashMap;
use std::sync::Mutex;

// Plugin chain storage per track index
type TrackChains = HashMap<usize, PluginChain>;

static PLUGIN_CHAINS: Lazy<Mutex<TrackChains>> = Lazy::new(|| {
    Mutex::new(HashMap::new())
});

static PLUGIN_REGISTRY: Lazy<Mutex<PluginRegistry>> = Lazy::new(|| {
    Mutex::new(PluginRegistry::new())
});
```

**Why this pattern:**
- Simple approach for FFI-safe global state
- Lock contention minimal (UI thread only)
- Matches existing patterns in `meter_ffi.rs`

### 2. C-Compatible Structures

**Pattern:** Use `#[repr(C)]` structs with raw pointers for FFI boundaries.

**Example:**

```rust
#[repr(C)]
pub struct PluginInfoData {
    pub name: *const c_char,
    pub vendor: *const c_char,
    pub version: *const c_char,
    pub format: c_int,  // 0=VST3, 1=AU, 2=Internal
    pub num_inputs: c_int,
    pub num_outputs: c_int,
    pub unique_id: *const c_char,
}
```

**Memory management:**
- Caller allocates output struct
- Rust allocates strings via `CString::into_raw()`
- Caller must free strings with matching `daw_plugin_info_free()`

### 3. Null Safety Pattern

**Pattern:** All FFI functions check for null pointers and return error codes.

```rust
#[no_mangle]
pub extern "C" fn daw_plugin_chain_add(
    track_index: c_int,
    unique_id: *const c_char,
) -> c_int {
    if track_index < 0 || unique_id.is_null() {
        return -1;  // Error code
    }
    // ... process
    0  // Success
}
```

### 4. Error Code Convention

| Return Value | Meaning |
|--------------|---------|
| 0 | Success |
| -1 | General error (null pointer, invalid index) |
| -2 | Plugin not found |
| -3 | Chain not found |
| positive int | Success with data (count, slot index) |

### 5. Test Isolation Pattern

**Pattern:** Use serial test guards for tests that use global state.

```rust
// In integration tests
use std::sync::Mutex;

static PLUGIN_TEST_GUARD: Mutex<()> = Mutex::new(());

#[test]
fn integration_plugin_chain_audio_process() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    // Test code here
}
```

## C++ Integration Pattern

### EngineBridge Wrappers

The C++ side wraps FFI calls in `EngineBridge` methods:

```cpp
// EngineBridge.h
class EngineBridge {
public:
    // Plugin Registry
    int scanPluginRegistry();
    int getPluginCount();
    PluginInfo getPlugin(int index);
    
    // Plugin Chain
    bool addPluginToChain(int trackIndex, const std::string& pluginId);
    bool removePluginFromChain(int trackIndex, int slotIndex);
    bool movePluginInChain(int trackIndex, int fromSlot, int toSlot);
    void setPluginBypass(int trackIndex, int slotIndex, bool bypassed);
};
```

### String Handling

```cpp
// Convert C++ string to C string for FFI
CString pluginId(pluginUniqueId.toRawUTF8());
int slot = daw_plugin_chain_add(trackIndex, pluginId.get());

// Free strings returned from Rust
PluginInfoData info;
daw_plugin_registry_get_plugin(index, &info);
String name(info.name);  // Copy
String vendor(info.vendor);
daw_plugin_info_free(&info);  // Must free!
```

## Comparison with Other FFI Modules

### meter_ffi.rs

| Aspect | meter_ffi | plugin_ffi |
|--------|-----------|------------|
| State type | Array (fixed tracks) | HashMap (dynamic tracks) |
| Data | f32 levels | Complex structs |
| Allocations | None | CString allocations |
| Thread safety | Mutex guard | Mutex guard |

### midi_edit_ffi.rs

| Aspect | midi_edit_ffi | plugin_ffi |
|--------|---------------|------------|
| Inputs | MIDI data pointers | Plugin ID strings |
| Outputs | Modified MIDI | Plugin info structs |
| Pattern | State machine | Registry + chain |

## Best Practices

1. **Always use `#[no_mangle]` and `pub extern "C"`** for FFI functions
2. **Check all pointer arguments** for null before dereferencing
3. **Use `CString` for strings** - remember caller must free
4. **Return error codes** - don't panic across FFI boundary
5. **Document memory ownership** in function comments
6. **Use test guards** for integration tests with global state
7. **Follow naming convention:** `daw_<module>_<action>()`

## Future Enhancements

When adding new plugin types to `PluginInstanceWrapper`:

1. Add variant to the enum
2. Implement `process()` dispatch
3. Add parameter get/set methods
4. Export in lib.rs if needed for tests
5. Add integration tests for the new plugin type

## References

- `daw-engine/src/plugin_ffi.rs` - FFI implementation
- `daw-engine/src/plugin.rs` - Core plugin types
- `daw-engine/tests/integration_plugin_chain.rs` - Integration tests
- `daw-engine/src/meter_ffi.rs` - Reference FFI pattern
- `daw-engine/src/midi_edit_ffi.rs` - Reference FFI pattern
