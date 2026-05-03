# Session Y - Parameter Automation Core

```markdown
@ai_dev_meta_layer/framework_loader.md

**Task**: Implement parameter automation - record and playback fader/knob movements with automation lanes

**Session Type**: New Feature

**Context**: Mixer has manual fader control but no automation. Need: automation lane data structure, sample-accurate interpolation, write/touch/latch modes. See NEXT_STEPS.md Phase 6.3.

---

## Toolkit Selection

| Toolkit | Selected | Rationale |
|---------|----------|-----------|
| Superpowers | ✅ Yes | TDD required for automation system |
| UI UX Pro Max | ⬜ No | Core only, UI in follow-up |
| Frontend Design | ⬜ No | Core only, UI in follow-up |
| Claude-Mem | ⬜ No | Not a long-term context task |
| Awesome Claude Code | ⬜ No | No specialized tools needed |

**Meta Layer Skills Emphasized**:
- ✅ test-driven-development
- ✅ systematic-debugging
- ✅ verification-before-completion
- ✅ writing-plans

---

## Documentation Plan

**Utilization Log**: `ai_dev_meta_layer/utilization_logs/session_Y_YYYY-MM-DD.md`

**Planned Checkpoints**:
- [ ] Post-bootstrap (design data structures)
- [ ] Post-plan (after automation lane design)
- [ ] Mid-implementation (after interpolation + modes)
- [ ] Pre-completion (before E2E test)
- [ ] Post-completion (fader automation test)

---

## Bite-Sized Tasks

### Task Y.1: Automation Point Data Structure
**File**: `daw-engine/src/automation.rs` (new)  
**Time**: 10 min

Define core structures:
```rust
#[derive(Clone, Debug)]
pub struct AutomationPoint {
    pub beat: f64,          // Position in beats
    pub value: f32,         // Parameter value (0.0 - 1.0 normalized)
    pub curve_type: CurveType, // Linear, Log, Exponential, S-Curve
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum CurveType {
    Linear,
    Logarithmic,
    Exponential,
    SCurve,
}

pub struct AutomationLane {
    pub parameter_id: String,  // "track_0_fader", "track_0_pan", etc.
    pub points: Vec<AutomationPoint>,
    pub enabled: bool,
    pub default_value: f32,
}
```

**Verification**: Unit test - create lane, add points

---

### Task Y.2: Sample-Accurate Interpolation
**File**: `daw-engine/src/automation.rs` (add methods)  
**Time**: 15 min

Implement interpolation:
```rust
impl AutomationLane {
    /// Get interpolated value at specific beat
    pub fn value_at(&self, beat: f64) -> f32 {
        // Find surrounding points
        // Interpolate based on curve_type
        // Handle edge cases (before first, after last)
    }
    
    /// Get value for audio callback (sample-accurate)
    pub fn value_at_sample(&self, sample: u64, sample_rate: u32, bpm: f64) -> f32 {
        let beat = sample_to_beat(sample, sample_rate, bpm);
        self.value_at(beat)
    }
}

fn sample_to_beat(sample: u64, sample_rate: u32, bpm: f64) -> f64 {
    let seconds = sample as f64 / sample_rate as f64;
    seconds * bpm / 60.0
}
```

**Verification**: Test interpolation accuracy

---

### Task Y.3: Write/Touch/Latch Modes
**File**: `daw-engine/src/automation.rs` (add AutomationRecorder)  
**Time**: 20 min

Implement recording modes:
```rust
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum AutomationMode {
    Off,        // Playback only
    Read,       // Read automation
    Write,      // Overwrite all
    Touch,      // Write only when touched, return to existing
    Latch,      // Write when touched, stay at last value
}

pub struct AutomationRecorder {
    mode: AutomationMode,
    lane: AutomationLane,
    is_touched: bool,
    touch_start_beat: f64,
    last_value: f32,
}

impl AutomationRecorder {
    pub fn start_touch(&mut self, beat: f64, value: f32) {
        self.is_touched = true;
        self.touch_start_beat = beat;
        self.last_value = value;
    }
    
    pub fn update_value(&mut self, beat: f64, value: f32) {
        if !self.is_touched { return; }
        
        match self.mode {
            AutomationMode::Write => {
                // Clear points in range, add new
            }
            AutomationMode::Touch => {
                // Add point, will return to existing after release
            }
            AutomationMode::Latch => {
                // Add point, stay at value
            }
            _ => {}
        }
        self.last_value = value;
    }
    
    pub fn end_touch(&mut self, beat: f64) {
        // Handle Touch mode return to existing automation
        self.is_touched = false;
    }
}
```

**Verification**: Test each mode behavior

---

### Task Y.4: Mixer Integration
**File**: `daw-engine/src/mixer.rs` (add automation support)  
**Time**: 15 min

Connect to mixer:
```rust
pub struct ChannelStrip {
    pub fader_level: f32,
    pub pan: f32,
    pub fader_automation: AutomationLane,
    pub pan_automation: AutomationLane,
    pub fader_mode: AutomationMode,
}

impl ChannelStrip {
    pub fn process_with_automation(&mut self, samples: u64, sample_rate: u32, bpm: f64) {
        if self.fader_mode != AutomationMode::Off {
            let auto_value = self.fader_automation.value_at_sample(samples, sample_rate, bpm);
            self.fader_level = auto_value;
        }
    }
}
```

**Verification**: Mixer tests still pass

---

### Task Y.5: FFI Exports
**File**: `daw-engine/src/automation_ffi.rs` (new)  
**Time**: 15 min

Add FFI for C++ UI:
```rust
#[no_mangle]
pub extern "C" fn daw_auto_lane_create(parameter_id: *const c_char) -> *mut c_void;

#[no_mangle]
pub extern "C" fn daw_auto_lane_add_point(
    lane: *mut c_void, 
    beat: c_double, 
    value: c_float,
    curve_type: c_int
);

#[no_mangle]
pub extern "C" fn daw_auto_lane_get_value_at(lane: *mut c_void, beat: c_double) -> c_float;

#[no_mangle]
pub extern "C" fn daw_auto_set_mode(track: c_int, parameter: c_int, mode: c_int);
```

**Verification**: FFI tests pass

---

### Task Y.6: E2E Test - Fader Automation
**File**: `daw-engine/tests/integration_fader_automation.rs` (new)  
**Time**: 15 min

Create E2E test:
```rust
#[test]
fn test_fader_automation_record_and_playback() {
    // Create mixer with one track
    let mut mixer = Mixer::new(1);
    
    // Set up automation lane with fader curve
    let lane = mixer.track_fader_lane(0);
    lane.add_point(AutomationPoint { beat: 0.0, value: 0.0, curve_type: Linear });
    lane.add_point(AutomationPoint { beat: 4.0, value: 1.0, curve_type: Linear });
    
    // Process 4 beats at 120 BPM
    let mut output = vec![0.0f32; 48000 * 2]; // 2 seconds
    mixer.process_with_automation(&mut output, 0, 48000, 120.0);
    
    // Verify: fader level increased from 0.0 to 1.0 over time
    let early_level = mixer.track(0).fader_level;
    assert!(early_level < 0.5, "Fader should start low");
    
    // Process more to reach end
    let mut output2 = vec![0.0f32; 48000 * 2];
    mixer.process_with_automation(&mut output2, 48000 * 2, 48000, 120.0);
    let late_level = mixer.track(0).fader_level;
    assert!(late_level > 0.9, "Fader should reach near 1.0");
}
```

**Verification**: Test passes, fader follows curve

---

## Agent Report Format

Return exactly:
```markdown
**Status**: [✅ COMPLETE / ⚠️ PARTIAL / ❌ BLOCKED]

**Files Modified**:
- [exact paths]

**Test Results**:
- cargo test --lib: [X passed, Y failed]
- cargo test --test integration_fader_automation: [X passed, Y failed]
- automation unit tests: [X passed]

**Blockers**: [if any, with evidence]

**Recommended Next Actions**:
```

---

Proceed with systematic approach per Core Memories.
