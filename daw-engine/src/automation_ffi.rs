//! Automation FFI Bridge
//!
//! C-compatible interface for parameter automation from C++ UI.

use std::ffi::{c_char, c_double, c_float, c_int, c_void, CStr, CString};
use std::ptr;
use crate::automation::{AutomationLane, AutomationMode, AutomationPoint, AutomationRecorder, CurveType};

/// Opaque handle to an automation lane
pub struct AutomationLaneHandle {
    lane: AutomationLane,
}

/// Opaque handle to an automation recorder
pub struct AutomationRecorderHandle {
    recorder: AutomationRecorder,
}

/// Create a new automation lane
/// 
/// # Arguments
/// * `parameter_id` - Parameter identifier string (e.g., "track_0_fader")
/// * `default_value` - Default value when no automation exists
/// 
/// # Returns
/// Handle to the created lane, or null on error
/// 
/// # Safety
/// parameter_id must be a valid null-terminated C string
#[no_mangle]
pub unsafe extern "C" fn daw_auto_lane_create(parameter_id: *const c_char, default_value: c_float) -> *mut c_void {
    if parameter_id.is_null() {
        return ptr::null_mut();
    }
    
    let id_str = match CStr::from_ptr(parameter_id).to_str() {
        Ok(s) => s,
        Err(_) => return ptr::null_mut(),
    };
    
    let handle = Box::new(AutomationLaneHandle {
        lane: AutomationLane::new(id_str, default_value),
    });
    
    Box::into_raw(handle) as *mut c_void
}

/// Destroy an automation lane
/// 
/// # Safety
/// handle must be a valid lane handle created by daw_auto_lane_create
#[no_mangle]
pub unsafe extern "C" fn daw_auto_lane_destroy(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut AutomationLaneHandle);
    }
}

/// Add a point to an automation lane
/// 
/// # Arguments
/// * `lane` - Lane handle
/// * `beat` - Position in beats
/// * `value` - Parameter value
/// * `curve_type` - 0=Linear, 1=Log, 2=Exp, 3=S-Curve
/// 
/// # Safety
/// lane must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_lane_add_point(
    lane: *mut c_void,
    beat: c_double,
    value: c_float,
    curve_type: c_int,
) {
    if lane.is_null() {
        return;
    }
    
    let handle = &mut *(lane as *mut AutomationLaneHandle);
    let point = AutomationPoint {
        beat,
        value,
        curve_type: CurveType::from_int(curve_type),
    };
    handle.lane.add_point(point);
}

/// Get interpolated value at beat position
/// 
/// # Arguments
/// * `lane` - Lane handle
/// * `beat` - Position in beats
/// 
/// # Returns
/// Interpolated value at the given beat
/// 
/// # Safety
/// lane must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_lane_get_value_at(lane: *mut c_void, beat: c_double) -> c_float {
    if lane.is_null() {
        return 0.0;
    }
    
    let handle = &*(lane as *const AutomationLaneHandle);
    handle.lane.value_at(beat)
}

/// Clear all points from a lane
/// 
/// # Safety
/// lane must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_lane_clear(lane: *mut c_void) {
    if lane.is_null() {
        return;
    }
    
    let handle = &mut *(lane as *mut AutomationLaneHandle);
    handle.lane.clear();
}

/// Get point count in lane
/// 
/// # Safety
/// lane must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_lane_point_count(lane: *mut c_void) -> c_int {
    if lane.is_null() {
        return 0;
    }
    
    let handle = &*(lane as *const AutomationLaneHandle);
    handle.lane.point_count() as c_int
}

/// Create an automation recorder
/// 
/// # Arguments
/// * `parameter_id` - Parameter identifier
/// * `default_value` - Default value
/// * `mode` - 0=Off, 1=Read, 2=Write, 3=Touch, 4=Latch
/// 
/// # Safety
/// parameter_id must be a valid null-terminated C string
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_create(
    parameter_id: *const c_char,
    default_value: c_float,
    mode: c_int,
) -> *mut c_void {
    if parameter_id.is_null() {
        return ptr::null_mut();
    }
    
    let id_str = match CStr::from_ptr(parameter_id).to_str() {
        Ok(s) => s,
        Err(_) => return ptr::null_mut(),
    };
    
    let handle = Box::new(AutomationRecorderHandle {
        recorder: AutomationRecorder::new(id_str, default_value, AutomationMode::from_int(mode)),
    });
    
    Box::into_raw(handle) as *mut c_void
}

/// Destroy an automation recorder
/// 
/// # Safety
/// handle must be a valid recorder handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_destroy(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut AutomationRecorderHandle);
    }
}

/// Set automation mode
/// 
/// # Arguments
/// * `recorder` - Recorder handle
/// * `mode` - 0=Off, 1=Read, 2=Write, 3=Touch, 4=Latch
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_set_mode(recorder: *mut c_void, mode: c_int) {
    if recorder.is_null() {
        return;
    }
    
    let handle = &mut *(recorder as *mut AutomationRecorderHandle);
    handle.recorder.set_mode(AutomationMode::from_int(mode));
}

/// Start touching/recording
/// 
/// # Arguments
/// * `recorder` - Recorder handle
/// * `beat` - Current beat position
/// * `current_value` - Current control value
/// * `playback_value` - Value from existing automation
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_start_touch(
    recorder: *mut c_void,
    beat: c_double,
    current_value: c_float,
    playback_value: c_float,
) {
    if recorder.is_null() {
        return;
    }
    
    let handle = &mut *(recorder as *mut AutomationRecorderHandle);
    handle.recorder.start_touch(beat, current_value, playback_value);
}

/// Update value while touching
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_update_value(
    recorder: *mut c_void,
    beat: c_double,
    value: c_float,
) {
    if recorder.is_null() {
        return;
    }
    
    let handle = &mut *(recorder as *mut AutomationRecorderHandle);
    handle.recorder.update_value(beat, value);
}

/// End touching/recording
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_end_touch(recorder: *mut c_void, beat: c_double) {
    if recorder.is_null() {
        return;
    }
    
    let handle = &mut *(recorder as *mut AutomationRecorderHandle);
    handle.recorder.end_touch(beat);
}

/// Check if recorder is currently touched
/// 
/// # Returns
/// 1 if touched, 0 if not
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_is_touched(recorder: *mut c_void) -> c_int {
    if recorder.is_null() {
        return 0;
    }
    
    let handle = &*(recorder as *const AutomationRecorderHandle);
    if handle.recorder.is_touched() {
        1
    } else {
        0
    }
}

/// Get current value from recorder
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_current_value(
    recorder: *mut c_void,
    beat: c_double,
) -> c_float {
    if recorder.is_null() {
        return 0.0;
    }
    
    let handle = &*(recorder as *const AutomationRecorderHandle);
    handle.recorder.current_value(beat)
}

/// Clear all recorded points
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_clear(recorder: *mut c_void) {
    if recorder.is_null() {
        return;
    }
    
    let handle = &mut *(recorder as *mut AutomationRecorderHandle);
    handle.recorder.clear();
}

/// Get point count in recorder's lane
/// 
/// # Safety
/// recorder must be a valid handle
#[no_mangle]
pub unsafe extern "C" fn daw_auto_recorder_point_count(recorder: *mut c_void) -> c_int {
    if recorder.is_null() {
        return 0;
    }
    
    let handle = &*(recorder as *const AutomationRecorderHandle);
    handle.recorder.lane().point_count() as c_int
}

/// Convert sample position to beat
/// 
/// Formula: beats = (samples / sample_rate) * (bpm / 60)
#[no_mangle]
pub extern "C" fn daw_auto_sample_to_beat(
    sample: u64,
    sample_rate: c_int,
    bpm: c_double,
) -> c_double {
    let seconds = sample as f64 / sample_rate as f64;
    seconds * bpm / 60.0
}

/// Convert beat to sample position
/// 
/// Formula: samples = (beats * 60 / bpm) * sample_rate
#[no_mangle]
pub extern "C" fn daw_auto_beat_to_sample(
    beat: c_double,
    sample_rate: c_int,
    bpm: c_double,
) -> u64 {
    let seconds = beat * 60.0 / bpm;
    (seconds * sample_rate as f64) as u64
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_lane_lifecycle() {
        unsafe {
            let id = CString::new("track_0_fader").unwrap();
            let lane = daw_auto_lane_create(id.as_ptr(), 0.75);
            assert!(!lane.is_null());
            
            // Add points
            daw_auto_lane_add_point(lane, 0.0, 0.0, 0);
            daw_auto_lane_add_point(lane, 4.0, 1.0, 0);
            
            // Check count
            assert_eq!(daw_auto_lane_point_count(lane), 2);
            
            // Test interpolation at midpoint
            let value = daw_auto_lane_get_value_at(lane, 2.0);
            assert!((value - 0.5).abs() < 0.001);
            
            // Clean up
            daw_auto_lane_destroy(lane);
        }
    }
    
    #[test]
    fn test_recorder_lifecycle() {
        unsafe {
            let id = CString::new("track_0_fader").unwrap();
            let recorder = daw_auto_recorder_create(id.as_ptr(), 0.5, 2); // Write mode
            assert!(!recorder.is_null());
            
            // Start recording
            daw_auto_recorder_start_touch(recorder, 0.0, 0.5, 0.5);
            assert_eq!(daw_auto_recorder_is_touched(recorder), 1);
            
            // Update values
            daw_auto_recorder_update_value(recorder, 1.0, 0.7);
            daw_auto_recorder_update_value(recorder, 2.0, 0.9);
            
            // End recording
            daw_auto_recorder_end_touch(recorder, 3.0);
            assert_eq!(daw_auto_recorder_is_touched(recorder), 0);
            
            // Verify points were recorded
            assert!(daw_auto_recorder_point_count(recorder) >= 3);
            
            // Clean up
            daw_auto_recorder_destroy(recorder);
        }
    }
    
    #[test]
    fn test_null_safety() {
        unsafe {
            // All these should handle null gracefully
            daw_auto_lane_destroy(ptr::null_mut());
            daw_auto_lane_add_point(ptr::null_mut(), 0.0, 0.0, 0);
            assert_eq!(daw_auto_lane_get_value_at(ptr::null_mut(), 0.0), 0.0);
            assert_eq!(daw_auto_lane_point_count(ptr::null_mut()), 0);
            
            daw_auto_recorder_destroy(ptr::null_mut());
            daw_auto_recorder_start_touch(ptr::null_mut(), 0.0, 0.0, 0.0);
            daw_auto_recorder_update_value(ptr::null_mut(), 0.0, 0.0);
            daw_auto_recorder_end_touch(ptr::null_mut(), 0.0);
            assert_eq!(daw_auto_recorder_is_touched(ptr::null_mut()), 0);
            assert_eq!(daw_auto_recorder_current_value(ptr::null_mut(), 0.0), 0.0);
        }
    }
    
    #[test]
    fn test_beat_sample_conversions() {
        // 2 beats at 120 BPM = 1 second = 48000 samples
        let beat = daw_auto_sample_to_beat(48000, 48000, 120.0);
        assert!((beat - 2.0).abs() < 0.001);
        
        let sample = daw_auto_beat_to_sample(2.0, 48000, 120.0);
        assert_eq!(sample, 48000);
        
        // 0 = 0
        assert_eq!(daw_auto_sample_to_beat(0, 48000, 120.0), 0.0);
        assert_eq!(daw_auto_beat_to_sample(0.0, 48000, 120.0), 0);
    }
}
