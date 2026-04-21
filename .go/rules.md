# OpenDAW Autonomous Execution Rules - Phase 9.x

## Mission
Execute Phase 9.x Rust FFI Linker Fix: Resolve Windows linker issues preventing C++ UI from linking to Rust DLL, enabling full UI-Engine connectivity.

## Current Status
- **Phase 8.3 COMPLETE** - AI Pattern Generation UI
- **Phase 9.x IN PROGRESS** - Rust FFI Linker Fix
- **858 Rust tests passing**
- **C++ UI:** 12 unresolved externals remaining (down from 83)

## Problem Statement
Fix Windows linker issues for Rust DLL exports:
1. Windows system libraries (Propsys.lib, Ole32.lib) - ✅ Fixed
2. Rust DLL import library naming (daw_engine.dll.lib) - ✅ Fixed
3. C++ compilation errors (CharPointer_UTF8) - ✅ Fixed
4. Rust DLL symbol exports (via .def file) - ⚠️ In Progress

## Phase 8.3 Tasks (5 Tasks)

### MMM FFI Bridge
1. ✅ Add daw_mmm_* FFI functions to ffi_bridge.rs
2. ✅ Create MmmHandle struct and constants (MMM_STYLE_*, MMM_PATTERN_*)
3. ✅ Implement daw_mmm_create, load_style, generate, get_notes, destroy
4. ✅ Add FFI tests (lifecycle, null safety, style loading)

### C++ Wrapper
5. ✅ Create MmmFFI.h/cpp with PatternStyle, PatternType, PatternConfig structs
6. ✅ Implement FFI wrapper methods (isAvailable, createHandle, loadStyle, etc.)

### UI Dialog
7. ✅ Create PatternGeneratorDialog.h/cpp
8. ✅ Add style picker, type selector, tempo/bars sliders, key/chords inputs
9. ✅ Implement generation workflow and preview area

### Integration
10. ✅ Add "Tools" menu to MainComponent
11. ✅ Wire up Tools > Generate Pattern... menu item
12. ✅ Implement onPatternGenerated callback to create clips in session grid
13. ✅ Update CMakeLists.txt with PatternGen source files

## Known Status

### What Exists (Verified)
- `daw-engine/src/ffi_bridge.rs` - MMM FFI functions added (258 lines)
- `ui/src/PatternGen/MmmFFI.h/cpp` - C++ wrapper complete
- `ui/src/PatternGen/PatternGeneratorDialog.h/cpp` - UI dialog complete
- `ui/src/MainComponent.h/cpp` - Tools menu and callback wired
- `ui/CMakeLists.txt` - PatternGen source files added
- **858 Rust tests passing** (added 4 new MMM FFI tests)

### Remaining Work
- Compile C++ to verify no syntax errors (linker issues are pre-existing)
- Create handoff document
- Update .go/state.txt

## Files to Verify/Update
- `ai_modules/suno_library/api_server.py` - Flask API server (EXISTS)
- `ai_modules/suno_library/suno_tracks.db` - SQLite database (EXISTS)
- `ai_modules/suno_library/test_api.py` - Test suite (EXISTS)
- `ui/src/SunoBrowser/SunoBrowserComponent.cpp` - Uses port 3000 (EXISTS, JUCE 7 syntax fixed)

## Verification Steps

### Rust Tests
```bash
cd d:/Project/music-ai-toolshop/projects/06-opendaw/daw-engine
cargo test --lib --release --jobs 1
# Result: 858 tests passing (4 new MMM FFI tests added)
```

### C++ Build
```bash
cd d:/Project/music-ai-toolshop/projects/06-opendaw/ui
cmake --build build
# Result: Compilation to check for syntax errors
# Note: Linker issues with Rust DLL are pre-existing
```

## Success Criteria
- [x] daw_mmm_* FFI functions added to ffi_bridge.rs
- [x] MMM FFI constants defined (MMM_STYLE_*, MMM_PATTERN_*)
- [x] MmmHandle struct with machine, pattern, style fields
- [x] 4 new MMM FFI tests added and passing
- [x] MmmFFI.h/cpp C++ wrapper created
- [x] PatternGeneratorDialog.h/cpp UI component created
- [x] Tools menu added to MainComponent
- [x] Generate Pattern... menu item wired up
- [x] onPatternGenerated callback creates clips in session grid
- [x] CMakeLists.txt updated with PatternGen sources
- [x] 858 Rust tests passing
- [x] .go/rules.md updated
- [ ] .go/state.txt updated
- [ ] Handoff document created

## Next Phase Recommendations (After 8.3)

### Option A: Phase 9.x Fix Rust FFI Linker Issues
- Add Windows system libraries to CMake (Propsys.lib, Ole32.lib, etc.)
- Resolve PropVariantToInt64, VariantToDouble unresolved symbols
- Test C++ build with Rust DLL linking

### Option B: Phase 7.5 Export Menu Integration
- Add "Export Audio..." to File menu
- Test end-to-end export workflow
- Verify WAV files created successfully
- **Note:** Requires linker fix first

### Option C: Phase 10.x Distribution Packaging
- WiX installer for Windows
- DMG for macOS
- User documentation and onboarding flow

## Known Limitations
- C++ cannot link to Rust DLL due to missing Windows system libraries (Propsys.lib, Ole32.lib)
- Extracted stems are not yet auto-imported as tracks (TODO in ClipSlotComponent)
- Audio file path is currently placeholder (needs clip-to-file mapping)
- Demucs must be installed separately for stem extraction to work
- MMM pattern generation is simulated in test environment (no actual AI model)

---

**Dev Framework Reference:** `d:/Project/dev_framework` - Superpowers workflow system
**Plan:** `d:/Project/.windsurf/plans/opendaw-phase-8-x-stem-extractor-ui-a99e41.md`
