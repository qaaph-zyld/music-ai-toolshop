//! FFI exports for tempo automation
//!
//! Provides C-compatible exports for:
//! - Tempo breakpoint management
//! - Tempo queries at any position
//! - Interpolation type selection

use std::ffi::{c_char, CStr, CString};
use std::sync::Mutex;

use crate::tempo_automation::{InterpolationType, TempoAutomationTrack, TempoBreakpoint};

// Global tempo automation state (similar to time_signature_ffi pattern)
static TEMPO_TRACK: Mutex<Option<TempoAutomationTrack>> = Mutex::new(None);

fn with_track<F, R>(default_bpm: f64, f: F) -> R
where
    F: FnOnce(&mut TempoAutomationTrack) -> R,
{
    let mut guard = TEMPO_TRACK.lock().unwrap();
    let track = guard.get_or_insert_with(|| TempoAutomationTrack::new(default_bpm));
    f(track)
}

/// Initialize the tempo automation track with a default tempo
#[no_mangle]
pub extern "C" fn daw_tempo_auto_init(default_bpm: f64) {
    let mut guard = TEMPO_TRACK.lock().unwrap();
    *guard = Some(TempoAutomationTrack::new(default_bpm));
}

/// Reset tempo track to single breakpoint
#[no_mangle]
pub extern "C" fn daw_tempo_auto_reset(bpm: f64) {
    with_track(bpm, |track| track.reset(bpm));
}

/// Add a tempo breakpoint with specified interpolation type
/// interpolation: 0=step, 1=linear, 2=exponential, 3=smooth
#[no_mangle]
pub extern "C" fn daw_tempo_auto_add_breakpoint(beat: f64, bpm: f64, interpolation: i32) {
    let interp = match interpolation {
        0 => InterpolationType::Step,
        1 => InterpolationType::Linear,
        2 => InterpolationType::Exponential,
        3 => InterpolationType::Smooth,
        _ => InterpolationType::Linear,
    };
    with_track(120.0, |track| track.add_breakpoint(beat, bpm, interp));
}

/// Remove a breakpoint at the specified beat
/// Returns 1 if successful, 0 if not (can't remove beat 0)
#[no_mangle]
pub extern "C" fn daw_tempo_auto_remove_breakpoint(beat: f64) -> i32 {
    with_track(120.0, |track| {
        if track.remove_breakpoint(beat) {
            1
        } else {
            0
        }
    })
}

/// Get the number of breakpoints
#[no_mangle]
pub extern "C" fn daw_tempo_auto_get_breakpoint_count() -> i32 {
    with_track(120.0, |track| track.breakpoint_count() as i32)
}

/// C-compatible breakpoint structure
#[repr(C)]
pub struct TempoBreakpointFFI {
    pub beat: f64,
    pub bpm: f64,
    pub interpolation: i32, // 0=step, 1=linear, 2=exponential, 3=smooth
}

/// Get breakpoint at index
/// Returns 1 if successful, 0 if index out of bounds
#[no_mangle]
pub extern "C" fn daw_tempo_auto_get_breakpoint_at(index: i32, out: *mut TempoBreakpointFFI) -> i32 {
    if out.is_null() {
        return 0;
    }

    with_track(120.0, |track| {
        if let Some(bp) = track.get_breakpoint_at(index as usize) {
            unsafe {
                (*out).beat = bp.beat;
                (*out).bpm = bp.bpm;
                (*out).interpolation = match bp.interpolation {
                    InterpolationType::Step => 0,
                    InterpolationType::Linear => 1,
                    InterpolationType::Exponential => 2,
                    InterpolationType::Smooth => 3,
                };
            }
            1
        } else {
            0
        }
    })
}

/// Get the tempo at a specific beat position
#[no_mangle]
pub extern "C" fn daw_tempo_auto_get_tempo_at_beat(beat: f64) -> f64 {
    with_track(120.0, |track| track.get_tempo_at_beat(beat))
}

/// Get the average tempo over a range
#[no_mangle]
pub extern "C" fn daw_tempo_auto_get_average_tempo(start_beat: f64, end_beat: f64) -> f64 {
    with_track(120.0, |track| track.get_average_tempo(start_beat, end_beat))
}

/// Convert beats to seconds (accounting for tempo automation)
#[no_mangle]
pub extern "C" fn daw_tempo_auto_beats_to_seconds(start_beat: f64, end_beat: f64) -> f64 {
    with_track(120.0, |track| track.beats_to_seconds(start_beat, end_beat))
}

/// Find the nearest breakpoint to a beat position
/// Returns 1 if found, 0 if no breakpoints
#[no_mangle]
pub extern "C" fn daw_tempo_auto_find_nearest(beat: f64, out: *mut TempoBreakpointFFI) -> i32 {
    if out.is_null() {
        return 0;
    }

    with_track(120.0, |track| {
        if let Some(bp) = track.find_nearest_breakpoint(beat) {
            unsafe {
                (*out).beat = bp.beat;
                (*out).bpm = bp.bpm;
                (*out).interpolation = match bp.interpolation {
                    InterpolationType::Step => 0,
                    InterpolationType::Linear => 1,
                    InterpolationType::Exponential => 2,
                    InterpolationType::Smooth => 3,
                };
            }
            1
        } else {
            0
        }
    })
}

/// Get interpolation type as string (caller must free)
#[no_mangle]
pub extern "C" fn daw_tempo_auto_interpolation_to_string(interpolation: i32) -> *mut c_char {
    let s = match interpolation {
        0 => "step",
        1 => "linear",
        2 => "exponential",
        3 => "smooth",
        _ => "unknown",
    };

    match CString::new(s) {
        Ok(cs) => cs.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Free a string returned by this module
#[no_mangle]
pub extern "C" fn daw_tempo_auto_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = CString::from_raw(s);
        }
    }
}

/// Parse interpolation type from string
#[no_mangle]
pub extern "C" fn daw_tempo_auto_interpolation_from_string(s: *const c_char) -> i32 {
    if s.is_null() {
        return 1; // Default to linear
    }

    let c_str = unsafe { CStr::from_ptr(s) };
    match c_str.to_str() {
        Ok(str_slice) => {
            if let Some(interp) = InterpolationType::from_str(str_slice) {
                match interp {
                    InterpolationType::Step => 0,
                    InterpolationType::Linear => 1,
                    InterpolationType::Exponential => 2,
                    InterpolationType::Smooth => 3,
                }
            } else {
                1 // Default to linear
            }
        }
        Err(_) => 1, // Default to linear on error
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffi_init() {
        daw_tempo_auto_init(120.0);
        assert_eq!(daw_tempo_auto_get_breakpoint_count(), 1);
    }

    #[test]
    fn test_ffi_add_and_count() {
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1); // linear

        assert_eq!(daw_tempo_auto_get_breakpoint_count(), 2);
    }

    #[test]
    fn test_ffi_get_tempo() {
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1);

        assert!((daw_tempo_auto_get_tempo_at_beat(0.0) - 120.0).abs() < 0.01);
        assert!((daw_tempo_auto_get_tempo_at_beat(4.0) - 140.0).abs() < 0.01);

        // At midpoint, should be ~130
        let tempo = daw_tempo_auto_get_tempo_at_beat(2.0);
        assert!((tempo - 130.0).abs() < 1.0);
    }

    #[test]
    fn test_ffi_get_breakpoint_at() {
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1);

        let mut ffi_bp = TempoBreakpointFFI {
            beat: 0.0,
            bpm: 0.0,
            interpolation: 0,
        };

        assert_eq!(daw_tempo_auto_get_breakpoint_at(0, &mut ffi_bp), 1);
        assert!((ffi_bp.bpm - 120.0).abs() < 0.01);
        assert_eq!(ffi_bp.interpolation, 1); // linear

        assert_eq!(daw_tempo_auto_get_breakpoint_at(1, &mut ffi_bp), 1);
        assert!((ffi_bp.bpm - 140.0).abs() < 0.01);
        assert_eq!(ffi_bp.beat, 4.0);

        assert_eq!(daw_tempo_auto_get_breakpoint_at(99, &mut ffi_bp), 0);
    }

    #[test]
    fn test_ffi_remove_breakpoint() {
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1);

        assert_eq!(daw_tempo_auto_get_breakpoint_count(), 2);

        // Can't remove beat 0
        assert_eq!(daw_tempo_auto_remove_breakpoint(0.0), 0);
        assert_eq!(daw_tempo_auto_get_breakpoint_count(), 2);

        // Can remove beat 4
        assert_eq!(daw_tempo_auto_remove_breakpoint(4.0), 1);
        assert_eq!(daw_tempo_auto_get_breakpoint_count(), 1);
    }

    #[test]
    fn test_ffi_null_safety() {
        // These should not crash
        assert_eq!(daw_tempo_auto_get_breakpoint_at(0, std::ptr::null_mut()), 0);
        assert_eq!(daw_tempo_auto_find_nearest(0.0, std::ptr::null_mut()), 0);
        assert_eq!(daw_tempo_auto_interpolation_from_string(std::ptr::null()), 1);
    }

    #[test]
    fn test_ffi_interpolation_types() {
        // Step
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 0);
        let tempo = daw_tempo_auto_get_tempo_at_beat(1.0);
        assert!((tempo - 120.0).abs() < 0.1, "Step should be ~120 at 1.0, got {}", tempo);

        // Linear (new init)
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1);
        let tempo = daw_tempo_auto_get_tempo_at_beat(2.0);
        assert!((tempo - 130.0).abs() < 1.0, "Linear should be ~130 at 2.0, got {}", tempo);

        // Exponential
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 160.0, 2);
        let tempo = daw_tempo_auto_get_tempo_at_beat(2.0);
        assert!(tempo > 130.0 && tempo < 140.0, "Exponential at 2.0 should be 130-140, got {}", tempo);

        // Smooth
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 3);
        let tempo = daw_tempo_auto_get_tempo_at_beat(2.0);
        assert!((tempo - 130.0).abs() < 1.0, "Smooth should be ~130 at 2.0, got {}", tempo);
    }

    #[test]
    fn test_ffi_string_conversion() {
        let ptr = daw_tempo_auto_interpolation_to_string(0);
        assert!(!ptr.is_null());
        unsafe {
            let c_str = CStr::from_ptr(ptr);
            assert_eq!(c_str.to_str().unwrap(), "step");
        }
        daw_tempo_auto_free_string(ptr);

        let ptr = daw_tempo_auto_interpolation_to_string(1);
        unsafe {
            let c_str = CStr::from_ptr(ptr);
            assert_eq!(c_str.to_str().unwrap(), "linear");
        }
        daw_tempo_auto_free_string(ptr);

        // Test parsing
        let linear_str = CString::new("linear").unwrap();
        assert_eq!(daw_tempo_auto_interpolation_from_string(linear_str.as_ptr()), 1);

        let step_str = CString::new("step").unwrap();
        assert_eq!(daw_tempo_auto_interpolation_from_string(step_str.as_ptr()), 0);

        let exp_str = CString::new("exponential").unwrap();
        assert_eq!(daw_tempo_auto_interpolation_from_string(exp_str.as_ptr()), 2);
    }

    #[test]
    fn test_ffi_average_tempo() {
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1);

        let avg = daw_tempo_auto_get_average_tempo(0.0, 4.0);
        assert!((avg - 130.0).abs() < 2.0, "Expected ~130, got {}", avg);
    }

    #[test]
    fn test_ffi_beats_to_seconds() {
        daw_tempo_auto_init(60.0); // 1 beat per second

        let seconds = daw_tempo_auto_beats_to_seconds(0.0, 4.0);
        assert!((seconds - 4.0).abs() < 0.2, "Expected ~4s, got {}", seconds);
    }

    #[test]
    fn test_ffi_find_nearest() {
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1);

        let mut ffi_bp = TempoBreakpointFFI {
            beat: 0.0,
            bpm: 0.0,
            interpolation: 0,
        };

        assert_eq!(daw_tempo_auto_find_nearest(1.0, &mut ffi_bp), 1);
        assert_eq!(ffi_bp.beat, 0.0);

        assert_eq!(daw_tempo_auto_find_nearest(3.0, &mut ffi_bp), 1);
        assert_eq!(ffi_bp.beat, 4.0);
    }

    #[test]
    fn test_ffi_reset() {
        daw_tempo_auto_init(120.0);
        daw_tempo_auto_add_breakpoint(4.0, 140.0, 1);
        daw_tempo_auto_add_breakpoint(8.0, 160.0, 1);

        assert_eq!(daw_tempo_auto_get_breakpoint_count(), 3);

        daw_tempo_auto_reset(100.0);

        assert_eq!(daw_tempo_auto_get_breakpoint_count(), 1);
        assert!((daw_tempo_auto_get_tempo_at_beat(0.0) - 100.0).abs() < 0.01);
    }
}
