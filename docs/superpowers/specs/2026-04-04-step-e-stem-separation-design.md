# Step E: AI Stem Separation UI - Design Spec

**Date:** 2026-04-04
**Status:** In Progress
**Target:** 150+ tests passing (currently 145)

## Goal
Implement UI integration for AI-powered stem separation using demucs, enabling users to separate audio into stems (vocals, drums, bass, other) and import them into the session grid.

## Architecture

### Stem Separation Bridge
```rust
pub struct StemSeparator {
    demucs_path: PathBuf,
    output_dir: PathBuf,
    progress_callback: Option<StemProgressCallback>,
}

pub struct StemSeparationResult {
    pub vocals_path: Option<PathBuf>,
    pub drums_path: Option<PathBuf>,
    pub bass_path: Option<PathBuf>,
    pub other_path: Option<PathBuf>,
    pub success: bool,
    pub error_message: Option<String>,
}

pub enum StemType {
    Vocals,
    Drums,
    Bass,
    Other,
}

pub type StemProgressCallback = Box<dyn Fn(f32, StemType) + Send>;
```

### Separation Process
1. Receive input audio file path
2. Validate file exists and is supported format (WAV, MP3, FLAC)
3. Call demucs Python bridge via subprocess
4. Monitor output directory for stem files
5. Report progress via callback (0.0 to 1.0 per stem)
6. Return paths to separated stems

### FFI Interface
```c
// Start stem separation
// Returns separation handle or NULL on error
void* daw_stem_separate_start(
    void* engine,
    const char* input_path,
    const char* output_dir
);

// Get separation progress (0.0 to 1.0)
double daw_stem_get_progress(void* handle);

// Check if separation is complete
int daw_stem_is_complete(void* handle);

// Get result paths (call after complete)
// Returns JSON string: {"vocals": "path", "drums": "path", ...}
const char* daw_stem_get_result(void* handle);

// Cancel separation
void daw_stem_cancel(void* handle);

// Clean up separation handle
void daw_stem_free(void* handle);
```

## Implementation Plan

### Phase 1: Core Stem Types (TDD)
1. Create `stem_separation.rs` module
2. Define `StemSeparator`, `StemSeparationResult`, `StemType`
3. Write 3 tests for type creation

### Phase 2: Demucs Bridge
1. Implement `StemSeparator::separate()` method
2. Use Python subprocess to call demucs
3. Support 4-stem model (vocals, drums, bass, other)
4. Write 3 tests for separation

### Phase 3: Progress Callbacks
1. Add `StemProgressCallback` support
2. Monitor demucs output for progress
3. Write 2 tests for progress reporting

### Phase 4: FFI Integration
1. Add `daw_stem_separate_start()` FFI function
2. Add progress query and result functions
3. Add cancellation and cleanup
4. Write 2 tests for FFI exports

**Expected Tests:** +5 passing
**Expected Total:** 150+ tests

## Dev Framework Compliance

- [x] Brainstorming: This design spec
- [ ] TDD: Write failing tests first
- [ ] RED-GREEN-REFACTOR for each phase
- [ ] Evidence: Run tests after each phase
- [ ] Output pristine: Zero compiler errors

## Risk Mitigation

- demucs Python module already exists at `ai_modules/demucs/`
- Use subprocess bridge (proven pattern from other modules)
- Progress monitoring via file system watching
- Error handling for missing input files
- Timeout handling for long separations
