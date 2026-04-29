# Phase 9: Audio Effects Chain Implementation Plan

**Goal:** Build UI for managing audio effects chains on mixer tracks - plugin browser, drag-and-drop loading, parameter controls, and chain reordering.

**Architecture:**
- Rust: Extend plugin_ffi.rs with chain management exports
- C++ UI: New PluginBrowser component, PluginChainComponent, PluginParameterComponent
- Integration: Drag-drop from browser to ChannelStrip, chain reordering UI

**Tech Stack:** Rust (cdylib), C++ (JUCE), FFI

---

## Task List

### 1. Rust FFI Exports for Plugin Chain (30 min)
**File:** `daw-engine/src/plugin_ffi.rs` (create)
- [ ] `daw_plugin_chain_create()` - Create chain for track
- [ ] `daw_plugin_chain_add()` - Add plugin to chain
- [ ] `daw_plugin_chain_remove()` - Remove plugin by index
- [ ] `daw_plugin_chain_move()` - Reorder plugins
- [ ] `daw_plugin_chain_get_count()` - Get plugin count
- [ ] `daw_plugin_chain_get_plugin_info()` - Get plugin info at index
- [ ] `daw_plugin_chain_set_bypass()` - Bypass/unbypass plugin
- [ ] `daw_plugin_chain_set_parameter()` - Set parameter value
- [ ] `daw_plugin_chain_get_parameter()` - Get parameter value
- [ ] Add to `lib.rs` exports
- **Verification:** `cargo check --lib` passes

### 2. Plugin Registry FFI (20 min)
**File:** `daw-engine/src/plugin_ffi.rs`
- [ ] `daw_plugin_registry_scan()` - Scan for available plugins
- [ ] `daw_plugin_registry_get_count()` - Get available plugin count
- [ ] `daw_plugin_registry_get_plugin()` - Get plugin info by index
- [ ] `daw_plugin_registry_search()` - Search plugins by name
- **Verification:** Unit tests for registry functions

### 3. PluginBrowser UI Component (45 min)
**Files:** `ui/src/PluginBrowser/PluginBrowserComponent.h/cpp` (create)
- [ ] Search text box with live filtering
- [ ] Plugin list (name, vendor, format)
- [ ] Category filters (EQ, Compressor, Reverb, etc.)
- [ ] Drag source for plugins
- [ ] Selection highlighting
- **Verification:** Component renders, search filters work

### 4. PluginChainComponent (40 min)
**Files:** `ui/src/PluginChain/PluginChainComponent.h/cpp` (create)
- [ ] Horizontal list of plugin slots
- [ ] Plugin name + enable/bypass toggle
- [ ] Drag-and-drop reordering
- [ ] Delete button per plugin
- [ ] Click to open parameter panel
- **Verification:** Drag reordering works, delete removes plugin

### 5. PluginParameterComponent (35 min)
**Files:** `ui/src/PluginChain/PluginParameterComponent.h/cpp` (create)
- [ ] Parameter name labels
- [ ] Sliders for continuous parameters (0-1 normalized)
- [ ] Toggle buttons for boolean parameters
- [ ] Real-time updates to engine
- **Verification:** Parameter changes affect audio

### 6. ChannelStrip Integration (25 min)
**Files:** `ui/src/Mixer/ChannelStrip.h/cpp`
- [ ] Add "FX" button to open plugin chain
- [ ] Add drop target for plugin browser drag
- [ ] Display plugin count badge
- **Verification:** Drag plugin to strip, opens chain dialog

### 7. EngineBridge Methods (20 min)
**Files:** `ui/src/Engine/EngineBridge.h/cpp`
- [ ] `getPluginRegistry()` - Get available plugins
- [ ] `addPluginToChain(track, pluginId)` - Add plugin
- [ ] `removePluginFromChain(track, index)` - Remove plugin
- [ ] `movePluginInChain(track, from, to)` - Reorder
- [ ] `setPluginBypass(track, index, bypass)` - Bypass
- [ ] `setPluginParameter(track, index, paramId, value)` - Set param
- **Verification:** All methods call FFI correctly

### 8. Integration Tests (30 min)
**File:** `daw-engine/tests/integration_plugin_chain.rs` (create)
- [ ] `test_plugin_chain_create` - Chain creation
- [ ] `test_plugin_chain_add_remove` - Add and remove plugins
- [ ] `test_plugin_chain_reorder` - Move plugins
- [ ] `test_plugin_chain_bypass` - Bypass/unbypass
- [ ] `test_plugin_chain_parameter_set` - Parameter setting
- [ ] `test_plugin_registry_scan` - Registry scanning
- **Verification:** All 6 tests pass

### 9. MainComponent Integration (15 min)
**Files:** `ui/src/MainComponent.h/cpp`
- [ ] Add menu item: View → Plugin Browser
- [ ] Toggle PluginBrowser visibility
- [ ] Keyboard shortcut (Ctrl+Shift+P)
- **Verification:** Menu opens browser, shortcut works

### 10. Documentation & Cleanup (20 min)
- [ ] Update CURRENT_STATE.md
- [ ] Create handoff document
- [ ] Run full test suite
- [ ] Verify 0 compiler warnings
- **Verification:** `cargo test --lib` passes

---

## Total Estimate: ~4 hours

## Success Criteria
- Plugin browser displays available plugins
- Drag plugin to channel strip adds to chain
- Plugin chain UI shows plugins with bypass toggles
- Can reorder plugins via drag-drop
- Parameter changes affect audio processing
- 6 integration tests passing
- 0 compiler warnings
