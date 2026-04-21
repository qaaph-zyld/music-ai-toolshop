# OpenDAW Phase 9.x - Windows FFI Linker Debug Handoff

**Date:** 2026-04-08  
**Status:** IN PROGRESS - Linker issues partially resolved, symbol exports remain problematic  
**Issue:** Rust FFI functions not visible to MSVC (61 unresolved externals)

---

## ✅ What Has Been Fixed

### 1. Windows System Libraries (CMakeLists.txt)
- **Added:** Propsys.lib, Ole32.lib, OleAut32.lib
- **Purpose:** Resolves `PropVariantToInt64` and `VariantToDouble` linker errors
- **Status:** Working

### 2. Rust Library Path
- **Changed from:** `daw_engine.lib` 
- **Changed to:** `daw_engine.dll.lib` (Windows cdylib import library)
- **Status:** Working for DLL approach

### 3. CharPointer_UTF8 Conversion (MmmFFI.cpp)
- **Fixed:** Explicit conversion using `.getAddress()` instead of implicit
- **Status:** Compiles successfully

### 4. Build Configuration Changes
- **Cargo.toml:** Switched to `crate-type = ["staticlib"]` only
- **build.rs:** Disabled .def file generation (not needed for staticlib)
- **CMakeLists.txt:** Added `/WHOLEARCHIVE` linker flag
- **engine_ffi.rs:** Added `#[used]` attribute to `opendaw_engine_init`

---

## ❌ The Persistent Problem

### Root Cause
Rust `#[no_mangle] pub extern "C"` functions are **NOT being exported** in a way that MSVC can link against:

**Attempt 1: cdylib + .def file**
- Created comprehensive .def file with 180+ exports
- Used `cargo:rustc-cdylib-link-arg=/DEF:path`
- **Result:** .def file created but symbols not in DLL (verified with GetProcAddress)

**Attempt 2: staticlib + /WHOLEARCHIVE**
- Switched to `crate-type = ["staticlib"]`
- Added CMake `$<LINKER:/WHOLEARCHIVE:lib>`
- **Result:** 61 unresolved externals - symbols not in .lib file

**Attempt 3: #[used] attribute**
- Added to `opendaw_engine_init` in engine_ffi.rs
- **Result:** No change - still unresolved

---

## 🔍 Evidence

### DLL Export Check
```powershell
# Loaded DLL successfully
# GetProcAddress for opendaw_engine_init returned 0
# GetProcAddress for opendaw_transport_play returned 0
# Result: NONE of the 5 tested FFI functions exported
```

### Static Library Check
```powershell
# Built daw_engine.lib (29.9 MB)
# Linked with /WHOLEARCHIVE
# Result: 61 unresolved externals
# Sample missing: opendaw_engine_init, opendaw_transport_play, etc.
```

---

## 🧪 Current State

### File Locations
- **Static lib:** `C:\temp\opendaw-fresh\release\daw_engine.lib` (29.9 MB)
- **Old DLL:** `d:\Project\...\target\release\daw_engine.dll` (3.5 MB)
- **C++ Build:** `d:\Project\...\ui\build\OpenDAW.vcxproj`

### Modified Files
1. `daw-engine/Cargo.toml` - staticlib only
2. `daw-engine/build.rs` - disabled .def generation
3. `ui/CMakeLists.txt` - /WHOLEARCHIVE flag
4. `daw-engine/src/engine_ffi.rs` - #[used] attribute

### Build Commands That Work
```powershell
# Clean Rust build
$env:CARGO_TARGET_DIR = "C:\temp\opendaw-fresh"
cd d:\Project\music-ai-toolshop\projects\06-opendaw\daw-engine
cargo build --release --lib
# Result: Success (1m 47s), produces 29.9 MB static lib

# C++ build
cd d:\Project\music-ai-toolshop\projects\06-opendaw\ui\build
cmake --build . --config Release --target OpenDAW
# Result: 61 unresolved externals
```

---

## 🎯 What Needs To Be Done

### Option A: Fix All FFI Exports (Comprehensive)
Add proper Windows export directives to ALL FFI functions:

```rust
// Current (not working on Windows)
#[no_mangle]
pub extern "C" fn opendaw_engine_init(...) { }

// Required for Windows visibility
#[no_mangle]
#[used]
#[link(name = "opendaw_engine_init")]  // or similar
pub extern "C" fn opendaw_engine_init(...) { }
```

**Files to modify:**
- `engine_ffi.rs` - 20+ functions
- `clip_player_ffi.rs` - 15+ functions  
- `transport_sync_ffi.rs` - 15+ functions
- `midi_ffi.rs` - 10+ functions
- `meter_ffi.rs` - 10+ functions
- `project_ffi.rs` - 15+ functions
- All synth FFI files (dexed, helm, obxd, odin2, tunefish)

### Option B: Use Native Windows Exports
Research and implement Windows-specific export mechanism:
- Use `windows-targets` crate
- Or use `#[export_name]` attributes
- Or use linker scripts

### Option C: Alternative Architecture
Bypass the problem entirely:
- Use a C wrapper DLL that calls Rust staticlib
- Use REST API instead of FFI (axum already in dependencies)
- Use different interop mechanism (gRPC, shared memory, etc.)

---

## 📋 Verification Steps for Next Session

1. **Check if symbols are in .lib:**
   ```powershell
   # Find dumpbin.exe in Visual Studio
   dumpbin /SYMBOLS daw_engine.lib | findstr opendaw_engine_init
   ```

2. **Try rustflags to preserve symbols:**
   ```powershell
   $env:RUSTFLAGS = "-C link-args=/EXPORT:opendaw_engine_init"
   cargo build --release --lib
   ```

3. **Check if #[used] works on more functions:**
   - Add #[used] to all functions in engine_ffi.rs
   - Rebuild and check if count reduces from 61

4. **Try #[linkage = "external"]:**
   ```rust
   #[no_mangle]
   #[linkage = "external"]
   pub extern "C" fn opendaw_engine_init(...) { }
   ```

---

## 🔗 Related Resources

- **Original handoff:** `HANDOFF-2026-04-08-PHASE-9-X.md`
- **Rust FFI docs:** https://doc.rust-lang.org/nomicon/ffi.html
- **Windows static libs:** https://docs.rust-embedded.org/book/interoperability/rust-with-c.html
- **#[used] attribute:** https://doc.rust-lang.org/reference/attributes.html#the-used-attribute

---

## 📝 Notes

- File locks were a major issue - use `$env:CARGO_TARGET_DIR` to fresh directory
- Build takes ~2 minutes when clean
- Windows file locks persist even after process kill - restart may help
- The .def file WAS created successfully but not picked up by linker

---

**Next AI:** Pick up from Option A, B, or C above. Current state is that we have a working static library build but the symbols aren't visible to MSVC linker.
