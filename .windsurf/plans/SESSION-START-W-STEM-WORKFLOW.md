# Session W - Stem Separation Workflow UI

```markdown
@ai_dev_meta_layer/framework_loader.md

**Task**: Implement one-click stem separation workflow UI (drag audio → extract → progress → 4 tracks)

**Session Type**: New Feature

**Context**: Stem extractor backend complete (Demucs subprocess with caching). Need UI workflow: right-click clip → "Extract Stems" → progress dialog → 4 new tracks (drums, bass, vocals, other). See NEXT_STEPS.md Phase 8.2.

---

## Toolkit Selection

| Toolkit | Selected | Rationale |
|---------|----------|-----------|
| Superpowers | ✅ Yes | TDD workflow required |
| UI UX Pro Max | ✅ Yes | Designing new UI workflow |
| Frontend Design | ✅ Yes | JUCE dialog components |
| Claude-Mem | ⬜ No | Not a long-term context task |
| Awesome Claude Code | ⬜ No | No specialized tools needed |

**Meta Layer Skills Emphasized**:
- ✅ test-driven-development
- ✅ systematic-debugging
- ✅ verification-before-completion
- ⬜ Other: UI/UX workflow design

---

## Documentation Plan

**Utilization Log**: `ai_dev_meta_layer/utilization_logs/session_W_YYYY-MM-DD.md`

**Planned Checkpoints**:
- [ ] Post-bootstrap (immediate)
- [ ] Post-plan (after designing workflow)
- [ ] Mid-implementation (after context menu + dialog)
- [ ] Pre-completion (before claiming done)
- [ ] Post-completion (E2E verification)

---

## Bite-Sized Tasks

### Task 1: Context Menu Integration
**File**: `ui/src/SessionGrid/ClipSlotComponent.cpp`  
**Time**: 5 min

Add "Extract Stems" menu item to context menu (only for audio clips):
```cpp
if (hasAudioClip) {
    menu.addItem(999, "Extract Stems...");
}
```

**Verification**: Right-click audio clip → see "Extract Stems..." option

---

### Task 2: Stem Extraction Dialog
**Files**: 
- `ui/src/StemExtraction/StemExtractionDialog.h` (new)
- `ui/src/StemExtraction/StemExtractionDialog.cpp` (new)
**Time**: 15 min

Create dialog with:
- Source clip name display
- Progress bar (0-100%)
- Status label ("Processing...", "Separating drums...")
- Cancel button
- Result: 4 checkboxes for stems (drums, bass, vocals, other)

**Verification**: Dialog opens, progress bar animates, cancel works

---

### Task 3: EngineBridge FFI Methods
**File**: `ui/src/Engine/EngineBridge.cpp`  
**Time**: 10 min

Add FFI wrapper methods:
```cpp
// In EngineBridge.h
bool startStemExtraction(const juce::String& sourceFile);
int getStemExtractionProgress();
bool isStemExtractionComplete();
std::vector<juce::String> getExtractedStemFiles();
bool cancelStemExtraction();
```

**Verification**: Methods compile, link to Rust FFI stubs

---

### Task 4: Rust FFI Exports (Stubs for Now)
**File**: `daw-engine/src/stem_ffi.rs` (new or add to existing)  
**Time**: 10 min

Add FFI exports:
```rust
#[no_mangle]
pub extern "C" fn daw_stem_start_extraction(source_path: *const c_char) -> c_int;

#[no_mangle]
pub extern "C" fn daw_stem_get_progress() -> c_int;

#[no_mangle]
pub extern "C" fn daw_stem_is_complete() -> c_int;

#[no_mangle]
pub extern "C" fn daw_stem_get_result_count() -> c_int;

#[no_mangle]
pub extern "C" fn daw_stem_cancel() -> c_int;
```

**Verification**: `cargo test --lib` still passes (541 tests)

---

### Task 5: Track Auto-Creation
**File**: `ui/src/MainComponent.cpp` (callback)  
**Time**: 10 min

After extraction complete:
```cpp
for (int i = 0; i < 4; ++i) {
    int track = findEmptyTrackOrCreate();
    engine.addAudioClipToArrangement(track, 0.0, stemFiles[i]);
}
```

**Verification**: 4 new tracks appear with stem clips

---

### Task 6: E2E Integration Test
**File**: `daw-engine/tests/integration_stem_workflow.rs` (new)  
**Time**: 15 min

Create test:
```rust
#[test]
fn test_stem_extraction_workflow() {
    // Load test audio file
    // Trigger stem extraction
    // Wait for completion (mocked)
    // Verify 4 stems created
}
```

**Verification**: Test passes

---

## Agent Report Format

Return exactly:
```markdown
**Status**: [✅ COMPLETE / ⚠️ PARTIAL / ❌ BLOCKED]

**Files Modified**:
- [exact paths]

**Test Results**:
- cargo test --lib: [X passed, Y failed]
- cargo check --lib: [X errors, Y warnings]
- cmake build: [errors?]

**Blockers**: [if any, with evidence]

**Recommended Next Actions**:
```

---

Proceed with systematic approach per Core Memories.
