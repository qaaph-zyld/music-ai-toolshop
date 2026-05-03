# Session X - Disk Streaming Foundation

```markdown
@ai_dev_meta_layer/framework_loader.md

**Task**: Implement disk streaming for long audio files - background read-ahead with circular buffer

**Session Type**: New Feature / Performance Optimization

**Context**: Currently samples fully loaded into RAM. For 10+ minute files, this is wasteful. Need disk streaming: background thread reads ahead, circular buffer, seamless playback. See NEXT_STEPS.md Phase 9.3.

---

## Toolkit Selection

| Toolkit | Selected | Rationale |
|---------|----------|-----------|
| Superpowers | ✅ Yes | TDD required for audio streaming |
| UI UX Pro Max | ⬜ No | Backend feature, minimal UI |
| Frontend Design | ⬜ No | No UI design needed |
| Claude-Mem | ⬜ No | Not a long-term context task |
| Awesome Claude Code | ⬜ No | No specialized tools needed |

**Meta Layer Skills Emphasized**:
- ✅ test-driven-development
- ✅ systematic-debugging
- ✅ verification-before-completion
- ✅ writing-plans

---

## Documentation Plan

**Utilization Log**: `ai_dev_meta_layer/utilization_logs/session_X_YYYY-MM-DD.md`

**Planned Checkpoints**:
- [ ] Post-bootstrap (design architecture)
- [ ] Post-plan (after buffer design)
- [ ] Mid-implementation (after thread + buffer)
- [ ] Pre-completion (before E2E test)
- [ ] Post-completion (10-min file test)

---

## Bite-Sized Tasks

### Task X.1: Architecture Design
**Time**: 10 min (planning, no code)

Document in `docs/disk_streaming_design.md`:
```markdown
# Disk Streaming Architecture

## Components
1. DiskStreamer - Manages file handle and read position
2. CircularBuffer - Lock-free SPSC ring buffer (audio thread <- reader thread)
3. ReadAheadThread - Background thread filling buffer
4. StreamedSamplePlayer - SamplePlayer variant using stream instead of full buffer

## Buffer Strategy
- 2-second read-ahead (configurable)
- Double-buffered I/O
- Lock-free consumer (audio thread)
- Mutex-protected producer (reader thread)

## Fallback
- If file < 30 seconds: load fully to RAM (current behavior)
- If file >= 30 seconds: use streaming
```

**Verification**: Document reviewed, approved

---

### Task X.2: CircularBuffer Implementation
**File**: `daw-engine/src/circular_buffer.rs` (new)  
**Time**: 15 min

Implement lock-free SPSC circular buffer:
```rust
pub struct CircularBuffer {
    buffer: Vec<f32>,
    write_idx: AtomicUsize,
    read_idx: AtomicUsize,
    capacity: usize,
}

impl CircularBuffer {
    pub fn new(capacity: usize) -> Self;
    pub fn write(&self, data: &[f32]) -> usize; // Returns written count
    pub fn read(&self, out: &mut [f32]) -> usize; // Returns read count
    pub fn available_read(&self) -> usize;
    pub fn available_write(&self) -> usize;
}
```

**Verification**: Unit tests pass (10+ tests)

---

### Task X.3: DiskStreamer Implementation
**File**: `daw-engine/src/disk_streamer.rs` (new)  
**Time**: 20 min

Implement file streaming:
```rust
pub struct DiskStreamer {
    file: File,
    buffer: CircularBuffer,
    sample_rate: u32,
    channels: u16,
    total_samples: u64,
    read_position: AtomicU64,
}

impl DiskStreamer {
    pub fn open(path: &Path) -> Result<Self, DiskStreamError>;
    pub fn read_ahead(&mut self) -> Result<(), DiskStreamError>;
    pub fn get_samples(&self, out: &mut [f32]) -> usize;
    pub fn seek(&mut self, sample: u64);
    pub fn is_eof(&self) -> bool;
}
```

**Verification**: Can open WAV file, read ahead, get samples

---

### Task X.4: ReadAheadThread
**File**: `daw-engine/src/disk_streamer.rs` (add thread logic)  
**Time**: 15 min

Add background thread:
```rust
pub struct StreamingPlayer {
    streamer: Arc<Mutex<DiskStreamer>>,
    thread: Option<JoinHandle<()>>,
    running: Arc<AtomicBool>,
}

impl StreamingPlayer {
    pub fn start(path: &Path) -> Result<Self, DiskStreamError> {
        // Spawn thread that calls read_ahead() in loop
    }
    
    pub fn process(&mut self, output: &mut [f32]) {
        // Called from audio thread
        // Get samples from buffer (lock-free)
    }
}
```

**Verification**: Thread spawns, fills buffer, audio thread consumes

---

### Task X.5: FFI Exports
**File**: `daw-engine/src/disk_streamer_ffi.rs` (new)  
**Time**: 15 min

Add FFI for C++ integration:
```rust
#[no_mangle]
pub extern "C" fn daw_streaming_player_open(path: *const c_char) -> *mut c_void;

#[no_mangle]
pub extern "C" fn daw_streaming_player_process(
    player: *mut c_void, 
    output: *mut f32, 
    frames: c_int
);

#[no_mangle]
pub extern "C" fn daw_streaming_player_close(player: *mut c_void);
```

**Verification**: FFI tests pass, exports link

---

### Task X.6: E2E Test - 10 Minute File
**File**: `daw-engine/tests/integration_disk_streaming.rs` (new)  
**Time**: 15 min

Create E2E test:
```rust
#[test]
fn test_streaming_10_minute_file() {
    // Create 10-minute sine wave test file
    let path = create_test_wav(600.0, 48000); // 10 min @ 48kHz
    
    // Open with streaming player
    let player = StreamingPlayer::start(&path).unwrap();
    
    // Process 1 second of audio
    let mut buffer = vec![0.0f32; 48000];
    player.process(&mut buffer);
    
    // Verify: output not silent, RAM usage < 50MB
    assert!(!buffer.iter().all(|&s| s == 0.0));
    
    // Memory check (via OS stats or custom allocator)
    let mem_usage = get_process_memory_mb();
    assert!(mem_usage < 50.0, "RAM usage {}MB > 50MB limit", mem_usage);
}
```

**Verification**: Test passes, RAM stays under 50MB

---

## Agent Report Format

Return exactly:
```markdown
**Status**: [✅ COMPLETE / ⚠️ PARTIAL / ❌ BLOCKED]

**Files Modified**:
- [exact paths]

**Test Results**:
- cargo test --lib: [X passed, Y failed]
- cargo test --test integration_disk_streaming: [X passed, Y failed]
- RAM usage for 10-min file: [X MB]

**Blockers**: [if any, with evidence]

**Recommended Next Actions**:
- Session X.2: [ ] (if not done)
- Session X.3: [ ] (if not done)
- etc.
```

---

Proceed with systematic approach per Core Memories.
