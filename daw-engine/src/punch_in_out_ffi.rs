//! Punch-In/Out FFI - C interface for punch-in/out recording control
//!
//! Provides FFI exports to allow C++ UI to control punch-in/out recording.

use std::ffi::{c_void, c_char, CStr, CString};
use std::os::raw::{c_float, c_int};
use std::sync::{Arc, Mutex};
use once_cell::sync::Lazy;

use crate::punch_in_out::{PunchInOutController, PunchConfig, PunchState};

/// Global punch-in/out controller instance
static PUNCH_CONTROLLER: Lazy<Arc<Mutex<PunchInOutController>>> = 
    Lazy::new(|| Arc::new(Mutex::new(PunchInOutController::new())));

/// Initialize the punch-in/out system
/// 
/// # Safety
/// Safe to call multiple times - will reset the controller to default state.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub extern "C" fn daw_punch_in_out_init() -> c_int {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    *controller = PunchInOutController::new();
    0
}

/// Shutdown and reset the punch-in/out system
/// 
/// # Safety
/// Safe to call multiple times. Resets to disarmed state.
#[no_mangle]
pub extern "C" fn daw_punch_in_out_shutdown() {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.reset();
}

/// Set the punch-in position in beats
/// 
/// # Arguments
/// * `beats` - Beat position where recording should start
#[no_mangle]
pub extern "C" fn daw_punch_in_out_set_in(beats: c_float) {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.set_punch_in(beats);
}

/// Set the punch-out position in beats
/// 
/// # Arguments
/// * `beats` - Beat position where recording should stop (0 or negative to disable)
#[no_mangle]
pub extern "C" fn daw_punch_in_out_set_out(beats: c_float) {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    if beats <= 0.0 {
        controller.clear_punch_out();
    } else {
        controller.set_punch_out(Some(beats));
    }
}

/// Set the pre-roll duration in beats
/// 
/// # Arguments
/// * `beats` - Number of beats to play before punch-in (0 for no pre-roll)
#[no_mangle]
pub extern "C" fn daw_punch_in_out_set_pre_roll(beats: c_float) {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.set_pre_roll(beats);
}

/// Set auto-punch mode
/// 
/// # Arguments
/// * `enabled` - 1 to enable auto-punch (auto-start transport), 0 to disable
#[no_mangle]
pub extern "C" fn daw_punch_in_out_set_auto_punch(enabled: c_int) {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.set_auto_punch(enabled != 0);
}

/// Enable or disable punch-in/out system
/// 
/// # Arguments
/// * `enabled` - 1 to enable, 0 to disable
#[no_mangle]
pub extern "C" fn daw_punch_in_out_set_enabled(enabled: c_int) {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.set_enabled(enabled != 0);
}

/// Check if punch-in/out is enabled
/// 
/// Returns: 1 if enabled, 0 if disabled
#[no_mangle]
pub extern "C" fn daw_punch_in_out_is_enabled() -> c_int {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    if controller.is_enabled() { 1 } else { 0 }
}

/// Arm the punch-in/out system
/// 
/// # Arguments
/// * `current_beat` - Current transport position in beats
/// 
/// Returns: State code (0=disarmed, 1=armed, 2=preroll, 3=recording, 4=completed)
#[no_mangle]
pub extern "C" fn daw_punch_in_out_arm(current_beat: c_float) -> c_int {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    let state = controller.arm(current_beat);
    punch_state_to_int(state)
}

/// Disarm the punch-in/out system
#[no_mangle]
pub extern "C" fn daw_punch_in_out_disarm() {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.disarm();
}

/// Get the current punch-in/out state
/// 
/// Returns: State code (0=disarmed, 1=armed, 2=preroll, 3=recording, 4=completed)
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_state() -> c_int {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    punch_state_to_int(controller.state())
}

/// Process transport position and update punch state
/// 
/// # Arguments
/// * `current_beat` - Current transport position in beats
/// * `is_playing` - 1 if transport is playing, 0 if stopped/paused
/// 
/// Returns: 1 if recording should be active, 0 otherwise
#[no_mangle]
pub extern "C" fn daw_punch_in_out_process(current_beat: c_float, is_playing: c_int) -> c_int {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    let should_record = controller.process(current_beat, is_playing != 0);
    if should_record { 1 } else { 0 }
}

/// Check if a beat position is within the punch range
/// 
/// # Arguments
/// * `beat` - Beat position to check
/// 
/// Returns: 1 if in punch range, 0 otherwise
#[no_mangle]
pub extern "C" fn daw_punch_in_out_is_in_range(beat: c_float) -> c_int {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    if controller.is_in_punch_range(beat) { 1 } else { 0 }
}

/// Get the punch-in position
/// 
/// Returns: Punch-in beat position
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_in() -> c_float {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.punch_in()
}

/// Get the punch-out position
/// 
/// Returns: Punch-out beat position, or -1.0 if not set
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_out() -> c_float {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    match controller.punch_out() {
        Some(beat) => beat,
        None => -1.0,
    }
}

/// Get the pre-roll duration
/// 
/// Returns: Pre-roll duration in beats
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_pre_roll() -> c_float {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.pre_roll()
}

/// Check if auto-punch is enabled
/// 
/// Returns: 1 if enabled, 0 if disabled
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_auto_punch() -> c_int {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    if controller.auto_punch() { 1 } else { 0 }
}

/// Get the pre-roll start position
/// 
/// Returns: Beat position where pre-roll should start
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_pre_roll_start() -> c_float {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.pre_roll_start()
}

/// Calculate pre-roll progress
/// 
/// # Arguments
/// * `current_beat` - Current transport position in beats
/// * `out_progress` - Pointer to store progress (0.0 to 1.0)
/// 
/// Returns: 1 if pre-rolling (progress valid), 0 otherwise
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_pre_roll_progress(
    current_beat: c_float,
    out_progress: *mut c_float,
) -> c_int {
    if out_progress.is_null() {
        return 0;
    }
    
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    match controller.pre_roll_progress(current_beat) {
        Some(progress) => {
            unsafe { *out_progress = progress; }
            1
        }
        None => 0,
    }
}

/// Get remaining beats until punch-in
/// 
/// # Arguments
/// * `current_beat` - Current transport position in beats
/// * `out_beats` - Pointer to store remaining beats
/// 
/// Returns: 1 if valid (armed or pre-rolling), 0 otherwise
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_beats_until_in(
    current_beat: c_float,
    out_beats: *mut c_float,
) -> c_int {
    if out_beats.is_null() {
        return 0;
    }
    
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    match controller.beats_until_punch_in(current_beat) {
        Some(beats) => {
            unsafe { *out_beats = beats; }
            1
        }
        None => 0,
    }
}

/// Get remaining beats until punch-out
/// 
/// # Arguments
/// * `current_beat` - Current transport position in beats
/// * `out_beats` - Pointer to store remaining beats
/// 
/// Returns: 1 if valid (recording with punch-out), 0 otherwise
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_beats_until_out(
    current_beat: c_float,
    out_beats: *mut c_float,
) -> c_int {
    if out_beats.is_null() {
        return 0;
    }
    
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    match controller.beats_until_punch_out(current_beat) {
        Some(beats) => {
            unsafe { *out_beats = beats; }
            1
        }
        None => 0,
    }
}

/// Reset the punch-in/out system to initial state
#[no_mangle]
pub extern "C" fn daw_punch_in_out_reset() {
    let mut controller = PUNCH_CONTROLLER.lock().unwrap();
    controller.reset();
}

/// Get status text as C string
/// 
/// # Safety
/// Caller must free the returned string with daw_punch_in_out_free_string.
/// Returns null pointer if error.
#[no_mangle]
pub extern "C" fn daw_punch_in_out_get_status_text() -> *mut c_char {
    let controller = PUNCH_CONTROLLER.lock().unwrap();
    let text = controller.status_text();
    
    match CString::new(text) {
        Ok(cstr) => cstr.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Free a string returned by punch-in/out FFI
/// 
/// # Safety
/// `ptr` must be a valid pointer returned by daw_punch_in_out_get_status_text.
/// After this call, the pointer is invalid.
#[no_mangle]
pub extern "C" fn daw_punch_in_out_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
    }
}

/// Helper function to convert PunchState to integer code
fn punch_state_to_int(state: PunchState) -> c_int {
    match state {
        PunchState::Disarmed => 0,
        PunchState::Armed => 1,
        PunchState::PreRolling => 2,
        PunchState::Recording => 3,
        PunchState::Completed => 4,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffi_init_shutdown() {
        assert_eq!(daw_punch_in_out_init(), 0);
        daw_punch_in_out_shutdown();
        // Should be disarmed after shutdown
        assert_eq!(daw_punch_in_out_get_state(), 0);
    }

    #[test]
    fn test_ffi_set_get_in_out() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_in(10.0);
        daw_punch_in_out_set_out(20.0);
        
        assert!((daw_punch_in_out_get_in() - 10.0).abs() < 0.001);
        assert!((daw_punch_in_out_get_out() - 20.0).abs() < 0.001);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_set_get_pre_roll() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_pre_roll(4.0);
        assert!((daw_punch_in_out_get_pre_roll() - 4.0).abs() < 0.001);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_clear_punch_out() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_out(20.0);
        assert!(daw_punch_in_out_get_out() > 0.0);
        
        // Setting to 0 or negative clears punch-out
        daw_punch_in_out_set_out(0.0);
        assert_eq!(daw_punch_in_out_get_out(), -1.0);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_enable_disable() {
        daw_punch_in_out_init();
        
        assert_eq!(daw_punch_in_out_is_enabled(), 1);
        
        daw_punch_in_out_set_enabled(0);
        assert_eq!(daw_punch_in_out_is_enabled(), 0);
        
        daw_punch_in_out_set_enabled(1);
        assert_eq!(daw_punch_in_out_is_enabled(), 1);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_arm_disarm() {
        daw_punch_in_out_init();
        
        // Initially disarmed
        assert_eq!(daw_punch_in_out_get_state(), 0);
        
        // Arm at beat 0
        let state = daw_punch_in_out_arm(0.0);
        assert_eq!(state, 1); // Armed
        assert_eq!(daw_punch_in_out_get_state(), 1);
        
        // Disarm
        daw_punch_in_out_disarm();
        assert_eq!(daw_punch_in_out_get_state(), 0);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_process_state_machine() {
        daw_punch_in_out_init();
        
        // Configure: punch-in at 4, punch-out at 8, pre-roll 2
        daw_punch_in_out_set_in(4.0);
        daw_punch_in_out_set_out(8.0);
        daw_punch_in_out_set_pre_roll(2.0);
        
        // Arm at beat 0
        daw_punch_in_out_arm(0.0);
        assert_eq!(daw_punch_in_out_get_state(), 1); // Armed
        
        // Process at beat 1 - still armed (before pre-roll)
        let recording = daw_punch_in_out_process(1.0, 1);
        assert_eq!(recording, 0);
        assert_eq!(daw_punch_in_out_get_state(), 1);
        
        // Process at beat 2 - start pre-rolling
        let recording = daw_punch_in_out_process(2.0, 1);
        assert_eq!(recording, 0);
        assert_eq!(daw_punch_in_out_get_state(), 2); // PreRolling
        
        // Process at beat 4 - punch-in, start recording
        let recording = daw_punch_in_out_process(4.0, 1);
        assert_eq!(recording, 1);
        assert_eq!(daw_punch_in_out_get_state(), 3); // Recording
        
        // Process at beat 8 - punch-out, complete
        let recording = daw_punch_in_out_process(8.0, 1);
        assert_eq!(recording, 0);
        assert_eq!(daw_punch_in_out_get_state(), 4); // Completed
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_is_in_range() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_in(4.0);
        daw_punch_in_out_set_out(8.0);
        
        assert_eq!(daw_punch_in_out_is_in_range(2.0), 0); // Before
        assert_eq!(daw_punch_in_out_is_in_range(5.0), 1);  // In range
        assert_eq!(daw_punch_in_out_is_in_range(10.0), 0); // After
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_pre_roll_progress() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_in(4.0);
        daw_punch_in_out_set_pre_roll(2.0);
        daw_punch_in_out_arm(0.0);
        
        // Get pre-rolling
        daw_punch_in_out_process(2.0, 1);
        assert_eq!(daw_punch_in_out_get_state(), 2);
        
        // Check progress at beat 3 (halfway through pre-roll)
        let mut progress: c_float = 0.0;
        let has_progress = daw_punch_in_out_get_pre_roll_progress(3.0, &mut progress);
        assert_eq!(has_progress, 1);
        assert!((progress - 0.5).abs() < 0.001);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_beats_until_in() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_in(4.0);
        daw_punch_in_out_arm(0.0);
        
        let mut beats: c_float = 0.0;
        let valid = daw_punch_in_out_get_beats_until_in(1.0, &mut beats);
        assert_eq!(valid, 1);
        assert!((beats - 3.0).abs() < 0.001);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_beats_until_out() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_in(4.0);
        daw_punch_in_out_set_out(8.0);
        daw_punch_in_out_arm(0.0);
        daw_punch_in_out_process(4.0, 1); // Start recording
        
        let mut beats: c_float = 0.0;
        let valid = daw_punch_in_out_get_beats_until_out(5.0, &mut beats);
        assert_eq!(valid, 1);
        assert!((beats - 3.0).abs() < 0.001);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_auto_punch() {
        daw_punch_in_out_init();
        
        assert_eq!(daw_punch_in_out_get_auto_punch(), 1); // Default enabled
        
        daw_punch_in_out_set_auto_punch(0);
        assert_eq!(daw_punch_in_out_get_auto_punch(), 0);
        
        daw_punch_in_out_set_auto_punch(1);
        assert_eq!(daw_punch_in_out_get_auto_punch(), 1);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_pre_roll_start() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_in(8.0);
        daw_punch_in_out_set_pre_roll(4.0);
        
        assert!((daw_punch_in_out_get_pre_roll_start() - 4.0).abs() < 0.001);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_status_text() {
        daw_punch_in_out_init();
        
        let text_ptr = daw_punch_in_out_get_status_text();
        assert!(!text_ptr.is_null());
        
        // Convert back to Rust string and verify
        unsafe {
            let cstr = CStr::from_ptr(text_ptr);
            let text = cstr.to_str().unwrap();
            assert_eq!(text, "Disarmed");
        }
        
        // Free the string
        daw_punch_in_out_free_string(text_ptr);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_reset() {
        daw_punch_in_out_init();
        
        daw_punch_in_out_set_in(10.0);
        daw_punch_in_out_arm(0.0);
        daw_punch_in_out_process(10.0, 1);
        
        assert_eq!(daw_punch_in_out_get_state(), 3); // Recording
        
        daw_punch_in_out_reset();
        assert_eq!(daw_punch_in_out_get_state(), 0); // Disarmed
        // Settings should persist after reset
        assert!((daw_punch_in_out_get_in() - 10.0).abs() < 0.001);
        
        daw_punch_in_out_shutdown();
    }

    #[test]
    fn test_ffi_null_pointer_safety() {
        // These should not crash
        let result = daw_punch_in_out_get_pre_roll_progress(0.0, std::ptr::null_mut());
        assert_eq!(result, 0);
        
        let result = daw_punch_in_out_get_beats_until_in(0.0, std::ptr::null_mut());
        assert_eq!(result, 0);
        
        let result = daw_punch_in_out_get_beats_until_out(0.0, std::ptr::null_mut());
        assert_eq!(result, 0);
        
        // Free null should not crash
        daw_punch_in_out_free_string(std::ptr::null_mut());
    }
}
