# Session U: MIDI Duplicate C++ Integration

> Per session-start-template.md from dev_framework

---

## Bootstrap

```markdown
@ai_dev_meta_layer/framework_loader.md

**Task:** Wire Rust `daw_midi_duplicate_clip` FFI to C++ EngineBridge and add UI menu item.

**Session Type:** Integration / Feature

**Context:** Session T completed Rust implementation with engine pointer parameter. Now wire C++ side: EngineBridge methods + MainComponent menu item.

---

## Toolkit Selection

| Toolkit | Selected | Rationale |
|---------|----------|-----------|
| Superpowers | ✅ Yes | TDD workflow for FFI integration |
| UI UX Pro Max | ✅ Yes | Menu item addition |
| Frontend Design | ❌ No | No new components |
| Claude-Mem | ❌ No | Short session |
| Awesome Claude Code | ❌ No | Domain familiar |

**Meta Layer Skills Emphasized:**
- ✅ systematic-debugging
- ✅ test-driven-development
- ✅ verification-before-completion

---

## Documentation Plan

**Utilization Log:** `ai_dev_meta_layer/utilization_logs/session_U_2026-05-02.md`

**Planned Checkpoints:**
- [ ] Post-bootstrap (immediate)
- [ ] Post-plan (after reading handoff)
- [ ] Mid-implementation (after EngineBridge wiring)
- [ ] Pre-completion (before claiming done)
- [ ] Post-completion (final verification)

---

## Work Items (Bite-Sized)

### Task 1: EngineBridge.h - Add Declaration (2 min)
**File:** `ui/src/Engine/EngineBridge.h`
**Exact Code:**
```cpp
// Add to public section:
bool duplicateMidiClip(int fromTrack, int fromScene, int toTrack, int toScene);
```
**Verification:** File compiles, declaration present.

### Task 2: EngineBridge.cpp - FFI Declaration (3 min)
**File:** `ui/src/Engine/EngineBridge.cpp`
**Exact Code:**
Add to extern "C" block:
```cpp
extern "C" {
    // ... existing declarations ...
    int daw_midi_duplicate_clip(void* engine, int from_track, int from_scene,
                                 int to_track, int to_scene);
}
```
**Verification:** Declaration added, no syntax errors.

### Task 3: EngineBridge.cpp - Implementation (5 min)
**File:** `ui/src/Engine/EngineBridge.cpp`
**Exact Code:**
```cpp
bool EngineBridge::duplicateMidiClip(int fromTrack, int fromScene,
                                      int toTrack, int toScene) {
    if (!enginePtr) return false;
    return daw_midi_duplicate_clip(enginePtr, fromTrack, fromScene,
                                    toTrack, toScene) == 0;
}
```
**Verification:** Implementation matches FFI signature.

### Task 4: MainComponent.h - Menu ID (2 min)
**File:** `ui/src/MainComponent.h`
**Exact Code:**
Add to enum:
```cpp
editDuplicateClip,
```
**Verification:** ID added to menu enum.

### Task 5: MainComponent.cpp - Menu Item (3 min)
**File:** `ui/src/MainComponent.cpp`
**Exact Code:**
In `createEditMenu()`:
```cpp
editMenu.addCommandItem(commandManager, editDuplicateClip, "Duplicate Clip\tCtrl+D");
```
**Verification:** Menu shows in Edit menu.

### Task 6: MainComponent.cpp - Callback (5 min)
**File:** `ui/src/MainComponent.cpp`
**Exact Code:**
```cpp
void MainComponent::onDuplicateClip() {
    if (!engine || selectedTrack < 0 || selectedScene < 0) return;
    // Duplicate to next scene slot
    int toScene = selectedScene + 1;
    if (toScene < 16) {
        engine->duplicateMidiClip(selectedTrack, selectedScene, selectedTrack, toScene);
    }
}
```
**Verification:** Callback compiles, logic reasonable.

### Task 7: Command Registration (2 min)
**File:** `ui/src/MainComponent.cpp`
**Exact Code:**
In `getCommandInfo()`:
```cpp
case editDuplicateClip:
    info.shortName = "Duplicate Clip";
    info.description = "Duplicate the selected MIDI clip";
    info.setActive(true);
    break;
```
**Verification:** Command info registered.

### Task 8: Build Verification (3 min)
**Command:** `cmake --build build --config Debug`
**Expected:** 0 errors, 0 warnings
**Verification:** Exit code 0.

---

## Agent Report Format

When complete, report:

```markdown
## Session U Complete

**Status:** ✅ COMPLETE / ❌ BLOCKED

**Files Modified:**
1. `ui/src/Engine/EngineBridge.h` - Added duplicateMidiClip declaration
2. `ui/src/Engine/EngineBridge.cpp` - Added FFI declaration + implementation
3. `ui/src/MainComponent.h` - Added editDuplicateClip menu ID
4. `ui/src/MainComponent.cpp` - Added menu item + callback + command info

**Build Status:**
- C++ Build: ✅ 0 errors / ❌ X errors
- Rust Tests: ✅ 541 passing

**Blockers:**
None / [describe if any]

**Next Steps:**
- Session V can now test E2E duplicate workflow
- Consider adding context menu item for right-click duplicate
```

---

Proceed with systematic approach per Core Memories.
