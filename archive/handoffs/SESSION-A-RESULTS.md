# Session A Results: Systematic Debugging + #[used] Batch Fix

**Completion Time:** 35 minutes  
**Build Status:** FAIL - Approach invalid

---

## Summary

The `#[used]` attribute approach **does not work for functions** in Rust. This is a fundamental language constraint - `#[used]` is only valid on static variables, not functions. The experiment revealed a critical misunderstanding of Rust's symbol retention mechanisms.

---

## Unresolved Externals

- **Start:** 61 (baseline from HANDOFF-2026-04-08-PHASE-9-X-DEBUG.md)
- **End:** N/A - Build failed before linking
- **Delta:** N/A

---

## Changes Made

**Attempted (and reverted):**
1. `engine_ffi.rs` - Added `#[used]` to 18 functions (reverted)
2. `ffi_bridge.rs` - Added `#[used]` to ~80 functions (reverted)
3. `meter_ffi.rs` - Added `#[used]` to 8 functions (reverted)
4. `project_ffi.rs` - Added `#[used]` to 7 functions (reverted)
5. `clip_player_ffi.rs` - Added `#[used]` to 10 functions (reverted)
6. `transport_sync_ffi.rs` - Added `#[used]` to 14 functions (reverted)
7. `midi_ffi.rs` - Added `#[used]` to 6 functions (reverted)

**Files modified:** 7 FFI modules
**Total functions attempted:** ~150

---

## New Errors Discovered

```
error: `#[used]` attribute cannot be used on functions
```

This error appears 153 times - once for each function where `#[used]` was applied.

---

## Key Finding

**The `#[used]` attribute in Rust is for static variables only.**

According to Rust documentation:
- `#[used]` forces the linker to keep a symbol even if it appears unused
- It is ONLY valid on `static` items
- It CANNOT be applied to functions

This makes the Session A hypothesis fundamentally flawed.

---

## Working State

- [ ] Clean compile - FAILED
- [ ] Linker resolves all symbols - NOT TESTED
- [ ] Runtime test passes - NOT TESTED
- [ ] Partial functionality confirmed - N/A

---

## Handoff Notes

**What Sessions B and C should know:**

1. `#[used]` is NOT a viable solution for FFI symbol export
2. The actual problem remains unsolved: Rust `#[no_mangle] pub extern "C"` functions in a `staticlib` are not visible to MSVC linker
3. The 61 unresolved externals persist

**Alternative approaches to consider:**

1. **Linker flags approach:** Use `-C link-args=/EXPORT:symbol_name` for each FFI function
2. **Module-definition (.def) file:** Create a .def file with all exports and pass to linker
3. **CDYLIB instead of staticlib:** Switch to dynamic library which exports symbols more reliably
4. **C wrapper bridge:** Create a C DLL that links to Rust and exports symbols properly
5. **REST API replacement:** Use axum HTTP server instead of FFI (Session C approach)

---

## Recommendation

**[Pivot to Session C]**

Given that:
- Session A approach is fundamentally invalid (#[used] doesn't work on functions)
- Session B (C Wrapper DLL) adds complexity and may have same symbol issues
- Session C (REST API) bypasses the FFI linking problem entirely

**Recommendation:** Consolidate efforts on Session C (Axum REST API) approach, as it:
- Avoids the MSVC/Rust FFI linking complexity
- Uses already-available dependencies (axum in Cargo.toml)
- Provides a clean HTTP interface that works cross-platform
- Eliminates the symbol visibility problem entirely

---

## Time Investment

- **Evidence gathering:** 5 minutes
- **Implementation attempt:** 15 minutes
- **Revert changes:** 10 minutes
- **Documentation:** 5 minutes

**Total:** 35 minutes (within 45-minute budget)

---

## Files Affected (No Net Changes)

All changes were reverted. Files touched:
- `daw-engine/src/engine_ffi.rs`
- `daw-engine/src/ffi_bridge.rs`
- `daw-engine/src/meter_ffi.rs`
- `daw-engine/src/project_ffi.rs`
- `daw-engine/src/clip_player_ffi.rs`
- `daw-engine/src/transport_sync_ffi.rs`
- `daw-engine/src/midi_ffi.rs`
