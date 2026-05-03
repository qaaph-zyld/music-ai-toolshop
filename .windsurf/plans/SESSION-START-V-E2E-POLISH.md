# Session V: E2E Integration Test + UI Polish

> Per session-start-template.md from dev_framework

---

## Bootstrap

```markdown
@ai_dev_meta_layer/framework_loader.md

**Task:** Create E2E test for MIDI duplicate workflow and complete UI polish items.

**Session Type:** Testing / Refinement

**Context:** Session T completed Rust, Session U completing C++. Now verify E2E workflow and polish UI.

---

## Toolkit Selection

| Toolkit | Selected | Rationale |
|---------|----------|-----------|
| Superpowers | ✅ Yes | TDD for E2E test |
| UI UX Pro Max | ✅ Yes | UI polish items |
| Frontend Design | ❌ No | Minor refinements |
| Claude-Mem | ❌ No | Short session |
| Awesome Claude Code | ❌ No | Domain familiar |

**Meta Layer Skills Emphasized:**
- ✅ test-driven-development
- ✅ verification-before-completion
- ✅ writing-plans

---

## Documentation Plan

**Utilization Log:** `ai_dev_meta_layer/utilization_logs/session_V_2026-05-02.md`

**Planned Checkpoints:**
- [ ] Post-bootstrap (immediate)
- [ ] Post-plan (after test design)
- [ ] Mid-implementation (after first test passes)
- [ ] Pre-completion (before claiming done)
- [ ] Post-completion (final verification)

---

## Work Items (Bite-Sized)

### Task 1: Create E2E Test File (3 min)
**File:** `daw-engine/tests/integration_midi_duplicate.rs`
**Exact Code:**
```rust
//! E2E test for MIDI clip duplicate functionality

use daw_engine::*;

#[test]
fn test_duplicate_midi_clip_success() {
    let engine = DawEngine::new(48000.0, 512).unwrap();
    let session = engine.session().lock().unwrap();
    
    // Create source MIDI clip with notes
    let notes = vec![
        MidiNote::new(60, 100, 0.0, 1.0),
        MidiNote::new(64, 100, 0.5, 1.0),
    ];
    session.create_midi_clip(0, 0, "Source", notes.clone());
    
    // Duplicate to track 0, scene 1
    let result = unsafe {
        daw_midi_duplicate_clip(
            &engine as *const _ as *mut c_void,
            0, 0, 0, 1
        )
    };
    
    assert_eq!(result, 0, "Duplicate should succeed");
    
    // Verify destination clip exists with same notes
    let dest_clip = session.get_clip(0, 1).unwrap();
    assert!(dest_clip.is_midi());
    assert_eq!(dest_clip.midi_notes().len(), 2);
}

#[test]
fn test_duplicate_to_invalid_location_fails() {
    let engine = DawEngine::new(48000.0, 512).unwrap();
    let session = engine.session().lock().unwrap();
    
    // Create source clip
    let notes = vec![MidiNote::new(60, 100, 0.0, 1.0)];
    session.create_midi_clip(0, 0, "Source", notes);
    
    // Try duplicate to invalid track
    let result = unsafe {
        daw_midi_duplicate_clip(&engine as *const _ as *mut c_void, 0, 0, 99, 1)
    };
    
    assert_eq!(result, -1, "Should fail with invalid track");
}

#[test]
fn test_duplicate_audio_clip_rejected() {
    let engine = DawEngine::new(48000.0, 512).unwrap();
    let session = engine.session().lock().unwrap();
    
    // Create audio clip (not MIDI)
    session.create_audio_clip(0, 0, "Audio", "test.wav", 4.0);
    
    // Try duplicate - should fail since it's audio
    let result = unsafe {
        daw_midi_duplicate_clip(&engine as *const _ as *mut c_void, 0, 0, 0, 1)
    };
    
    assert_eq!(result, -1, "Should reject audio clip duplication");
}
```
**Verification:** File compiles, test functions present.

### Task 2: Run E2E Tests (3 min)
**Command:** `cargo test --test integration_midi_duplicate`
**Expected:** 3 tests pass
**Verification:** All tests green.

### Task 3: UI Polish - Status Bar Notification (5 min)
**File:** `ui/src/MainComponent.cpp`
**Code:** Add status feedback in `onDuplicateClip()`:
```cpp
void MainComponent::onDuplicateClip() {
    if (!engine || selectedTrack < 0 || selectedScene < 0) {
        statusBar.setText("No clip selected to duplicate", juce::dontSendNotification);
        return;
    }
    
    int toScene = selectedScene + 1;
    if (toScene >= 16) {
        statusBar.setText("Cannot duplicate: no empty scene slot", juce::dontSendNotification);
        return;
    }
    
    if (engine->duplicateMidiClip(selectedTrack, selectedScene, selectedTrack, toScene)) {
        statusBar.setText("Clip duplicated successfully", juce::dontSendNotification);
        refreshSessionGrid();
    } else {
        statusBar.setText("Failed to duplicate clip", juce::dontSendNotification);
    }
}
```
**Verification:** Status messages shown on actions.

### Task 4: UI Polish - Context Menu (5 min)
**File:** `ui/src/SessionGrid/ClipSlotComponent.cpp`
**Code:** Add right-click duplicate:
```cpp
void ClipSlotComponent::showContextMenu() {
    juce::PopupMenu menu;
    menu.addItem("Duplicate", [this]() {
        if (onDuplicateRequested) onDuplicateRequested(trackIndex, sceneIndex);
    });
    // ... other items ...
    menu.showMenuAsync(juce::PopupMenu::Options());
}
```
**Verification:** Right-click shows duplicate option.

### Task 5: Full Test Suite (5 min)
**Commands:**
```bash
cargo test --lib
cargo test --test integration_midi_duplicate
cmake --build build --config Debug
```
**Expected:** All pass, 0 errors
**Verification:** Exit codes 0.

---

## Agent Report Format

When complete, report:

```markdown
## Session V Complete

**Status:** ✅ COMPLETE / ❌ BLOCKED

**Files Created/Modified:**
1. `daw-engine/tests/integration_midi_duplicate.rs` - NEW: 3 E2E tests
2. `ui/src/MainComponent.cpp` - MODIFIED: Status bar notifications
3. `ui/src/SessionGrid/ClipSlotComponent.cpp` - MODIFIED: Context menu

**Test Status:**
- Rust Library: ✅ 541 passing
- E2E Tests: ✅ 3 passing
- C++ Build: ✅ 0 errors

**Blockers:**
None / [describe if any]

**Next Steps:**
- Sessions U and V complete the MIDI duplicate feature
- Ready for Phase W: next major feature
```

---

Proceed with systematic approach per Core Memories.
