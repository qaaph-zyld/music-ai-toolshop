# Phase 3: Performance & Polish - Design Spec

**Date:** 2026-04-04  
**Status:** IN PROGRESS  
**Target:** 188+ tests passing (currently 173)

## Goal
Prepare OpenDAW for distribution with performance optimization, profiling, and user-facing polish.

---

## Architecture

### Task 3.1: Tracy Profiler Integration
```rust
// daw-engine/src/profiler.rs
pub struct Profiler;

impl Profiler {
    pub fn init() -> Self;
    pub fn frame_mark(&self);
    pub fn zone_begin(&self, name: &'static str) -> Zone;
}

// Usage in audio thread:
// let _zone = profiler.zone_begin("mixer::process");
```

**Deliverables:**
- Tracy client integration via `tracy-client` crate
- Zone markers for audio processing paths
- Frame marks for UI thread
- Memory allocation tracking

**Tests:** +3 (profiler creation, zone marking, frame marking)

---

### Task 3.2: Memory Pool Allocators
```rust
// daw-engine/src/memory_pool.rs
pub struct ObjectPool<T> {
    available: Vec<T>,
    in_use: Vec<T>,
}

pub struct SampleBufferPool {
    buffers: Vec<Vec<f32>>,
}
```

**Deliverables:**
- Object pool for `SamplePlayer` instances
- Pre-allocated scratch buffers (no allocations in `process()`)
- Lock-free ring buffer for commands (replace mpsc)
- Memory allocation tracking in Tracy

**Tests:** +5 (pool creation, acquire/release, buffer reuse, zero-allocation guarantee)

---

### Task 3.3: Disk Streaming
```rust
// daw-engine/src/disk_stream.rs
pub struct DiskStreamer {
    file: File,
    read_ahead_buffer: CircularBuffer<f32>,
    buffer_thread: JoinHandle<()>,
}
```

**Deliverables:**
- Background read-ahead thread
- Circular buffer for audio data
- Double-buffered file I/O
- <50MB RAM usage for 10-minute files

**Tests:** +4 (streamer creation, read-ahead, buffer underrun handling, file closing)

---

### Task 3.4: WiX Installer (Windows)
```xml
<!-- installer/windows/OpenDAW.wxs -->
<Product Id="*" Name="OpenDAW" Version="1.0.0">
  <Package InstallerVersion="200" Compressed="yes" />
  <Directory Id="TARGETDIR" Name="SourceDir">
    <Directory Id="ProgramFilesFolder">
      <Directory Id="INSTALLDIR" Name="OpenDAW">
        <Component>
          <File Source="..\..\ui\build\OpenDAW.exe" />
        </Component>
      </Directory>
    </Directory>
  </Directory>
</Product>
```

**Deliverables:**
- WiX installer project
- VCRedist bundle
- .opendaw file association
- Start menu shortcuts

**No Rust tests (installer is separate build artifact)**

---

### Task 3.5: User Documentation
```markdown
<!-- docs/user/quickstart.md -->
# OpenDAW Quick Start

1. Launch OpenDAW
2. Create new project or open demo
3. Add tracks from Suno library
4. Record MIDI
5. Export to WAV
```

**Deliverables:**
- Quick start guide (5-minute tutorial)
- Keyboard shortcut reference
- AI features guide
- Troubleshooting common issues

**No Rust tests (documentation)**

---

### Task 3.6: Onboarding Flow
```rust
// ui/src/OnboardingComponent.h
class OnboardingComponent : public Component {
    void showWelcomeScreen();
    void showDemoProject();
    void showInteractiveTutorial();
    void testAudioEngine();
};
```

**Deliverables:**
- Demo project pre-loaded
- Interactive tutorial ("Click here to add a clip")
- Audio engine test (play test tone)
- First-launch detection

**Tests:** +3 (first launch detection, tutorial progression, audio test)

---

## Implementation Plan

### Phase 1: Tracy Profiler (TDD)
1. Add `tracy-client` to Cargo.toml
2. Write 3 failing tests for profiler zones
3. Implement `Profiler` struct with zone/frame marking
4. Add zone markers to `mixer::process()` and `transport::process()`
5. Verify all tests pass

### Phase 2: Memory Pools (TDD)
1. Create `memory_pool.rs` module
2. Write 5 failing tests for pool operations
3. Implement `ObjectPool<T>` generic pool
4. Implement `SampleBufferPool` for audio buffers
5. Replace mpsc with lock-free queue in FFI bridge
6. Verify zero allocations in audio thread (Tracy validation)

### Phase 3: Disk Streaming (TDD)
1. Create `disk_stream.rs` module
2. Write 4 failing tests for streaming operations
3. Implement background read-ahead thread
4. Implement circular buffer with double-buffering
5. Integrate with `SamplePlayer` for large files
6. Verify <50MB RAM usage with test file

### Phase 4: WiX Installer
1. Create `installer/windows/` directory
2. Write OpenDAW.wxs with product structure
3. Configure VCRedist bundle
4. Add .opendaw file association registry entries
5. Test installer build

### Phase 5: Documentation
1. Create `docs/user/` directory structure
2. Write quickstart.md
3. Write shortcuts.md
4. Write ai-features.md
5. Write troubleshooting.md

### Phase 6: Onboarding (TDD)
1. Create `OnboardingComponent` in UI layer
2. Write 3 failing tests for onboarding flow
3. Implement first-launch detection (registry/settings)
4. Create demo project template
5. Implement interactive tutorial system
6. Add audio engine test tone

---

## Expected Test Count

| Task | Tests Added |
|------|-------------|
| 3.1 Tracy | +3 |
| 3.2 Memory Pools | +5 |
| 3.3 Disk Streaming | +4 |
| 3.4 WiX | 0 (installer) |
| 3.5 Docs | 0 (documentation) |
| 3.6 Onboarding | +3 |
| **Total** | **+15** |

**Final Target:** 188 tests passing

---

## Dev Framework Compliance

- [ ] TDD: Write failing tests first
- [ ] RED-GREEN-REFACTOR for each task
- [ ] Evidence: Tracy profiler validation for zero-allocation goal
- [ ] Output pristine: Zero compiler errors

---

## Risk Mitigation

- Tracy has minimal runtime overhead (can be disabled in release)
- Memory pools pre-allocate - monitor peak usage
- Disk streaming thread priority - keep below audio thread
- WiX installer - test on clean Windows VM
- Onboarding - allow skip for power users

---

## Verification Steps

```bash
# After each task
cd d:\Project\music-ai-toolshop\projects\06-opendaw\daw-engine
cargo test --lib

# Tracy validation
cargo build --release --features tracy
tracy-capture -o profile.tracy

# Memory validation
# Check Tracy shows zero allocations in mixer::process
```

---

*Phase 3 Design Spec created: 2026-04-04*
