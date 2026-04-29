//! Time Signature FFI exports for C++ UI integration
//!
//! Provides C-compatible exports for managing time signatures:
//! - Add/remove time signature changes
//! - Query signatures at bars and beats
//! - Beat <-> bar/beat conversions

use std::ffi::{c_char, c_double, c_int, c_uint, CStr, CString};
use std::ptr;
use std::sync::Mutex;
use once_cell::sync::Lazy;

use crate::time_signature::{TimeSignature, TimeSignatureTrack};

// =============================================================================
// Global state
// =============================================================================

static TIME_SIG_TRACK: Lazy<Mutex<TimeSignatureTrack>> = Lazy::new(|| {
    Mutex::new(TimeSignatureTrack::new())
});

// =============================================================================
// C-compatible structures
// =============================================================================

/// C-compatible time signature info
#[repr(C)]
pub struct TimeSignatureInfo {
    pub bar: c_uint,
    pub numerator: c_uint,
    pub denominator: c_uint,
}

/// C-compatible bar/beat result
#[repr(C)]
pub struct BarBeatResult {
    pub bar: c_uint,
    pub beat_in_bar: c_uint,
    pub fraction: c_double,
}

// =============================================================================
// Time Signature Management
// =============================================================================

/// Initialize/reset the time signature track to default 4/4
#[no_mangle]
pub extern "C" fn daw_time_sig_init() -> c_int {
    let mut track = TIME_SIG_TRACK.lock().unwrap();
    track.reset();
    0
}

/// Add a time signature change at the specified bar
///
/// Parameters:
///   bar: 1-indexed bar number (must be >= 1)
///   numerator: beats per bar (e.g., 4)
///   denominator: beat unit (e.g., 4 for quarter note)
///
/// Returns: 0 on success, -1 on error
#[no_mangle]
pub extern "C" fn daw_time_sig_add_change(
    bar: c_uint,
    numerator: c_uint,
    denominator: c_uint,
) -> c_int {
    if bar < 1 {
        return -1;
    }
    if numerator < 1 || numerator > 255 || denominator < 1 || denominator > 255 {
        return -1;
    }

    let mut track = TIME_SIG_TRACK.lock().unwrap();
    track.add_change(bar, numerator as u8, denominator as u8);
    0
}

/// Remove a time signature change at the specified bar
/// Cannot remove bar 1 (must always have at least one signature)
///
/// Returns: 0 on success, -1 if not found or can't remove
#[no_mangle]
pub extern "C" fn daw_time_sig_remove_change(bar: c_uint) -> c_int {
    if bar <= 1 {
        return -1;
    }

    let mut track = TIME_SIG_TRACK.lock().unwrap();
    if track.remove_change(bar) {
        0
    } else {
        -1
    }
}

/// Get the number of time signature changes
#[no_mangle]
pub extern "C" fn daw_time_sig_get_change_count() -> c_int {
    let track = TIME_SIG_TRACK.lock().unwrap();
    track.change_count() as c_int
}

/// Get time signature info at a specific index
///
/// Returns: 0 on success, -1 if index out of bounds
#[no_mangle]
pub extern "C" fn daw_time_sig_get_change_at(
    index: c_int,
    out_info: *mut TimeSignatureInfo,
) -> c_int {
    if index < 0 || out_info.is_null() {
        return -1;
    }

    let track = TIME_SIG_TRACK.lock().unwrap();
    let changes = track.all_changes();

    let idx = index as usize;
    if idx >= changes.len() {
        return -1;
    }

    let sig = &changes[idx];
    unsafe {
        (*out_info).bar = sig.bar;
        (*out_info).numerator = sig.numerator as c_uint;
        (*out_info).denominator = sig.denominator as c_uint;
    }

    0
}

/// Get time signature at a specific bar
///
/// Returns: 0 on success (info written to out_info), -1 on error
#[no_mangle]
pub extern "C" fn daw_time_sig_get_at_bar(
    bar: c_uint,
    out_info: *mut TimeSignatureInfo,
) -> c_int {
    if out_info.is_null() {
        return -1;
    }

    let track = TIME_SIG_TRACK.lock().unwrap();
    let sig = track.get_signature_at_bar(bar);

    unsafe {
        (*out_info).bar = sig.bar;
        (*out_info).numerator = sig.numerator as c_uint;
        (*out_info).denominator = sig.denominator as c_uint;
    }

    0
}

/// Get time signature at a specific beat
///
/// Returns: 0 on success, -1 on error
#[no_mangle]
pub extern "C" fn daw_time_sig_get_at_beat(
    beat: c_double,
    out_info: *mut TimeSignatureInfo,
) -> c_int {
    if out_info.is_null() {
        return -1;
    }

    let track = TIME_SIG_TRACK.lock().unwrap();
    let sig = track.get_signature_at_beat(beat);

    unsafe {
        (*out_info).bar = sig.bar;
        (*out_info).numerator = sig.numerator as c_uint;
        (*out_info).denominator = sig.denominator as c_uint;
    }

    0
}

// =============================================================================
// Beat <-> Bar/Beat Conversions
// =============================================================================

/// Convert absolute beat to bar/beat
///
/// Parameters:
///   beat: absolute beat position
///   out_result: pointer to BarBeatResult structure to fill
///
/// Returns: 0 on success, -1 on error
#[no_mangle]
pub extern "C" fn daw_time_sig_beat_to_bar_beat(
    beat: c_double,
    out_result: *mut BarBeatResult,
) -> c_int {
    if out_result.is_null() {
        return -1;
    }

    let track = TIME_SIG_TRACK.lock().unwrap();
    let (bar, beat_in_bar, fraction) = track.beat_to_bar_beat(beat);

    unsafe {
        (*out_result).bar = bar;
        (*out_result).beat_in_bar = beat_in_bar;
        (*out_result).fraction = fraction;
    }

    0
}

/// Convert bar and beat to absolute beat
///
/// Parameters:
///   bar: 1-indexed bar number
///   beat_in_bar: 0-indexed beat within bar
///
/// Returns: absolute beat position, or -1.0 on error
#[no_mangle]
pub extern "C" fn daw_time_sig_bar_beat_to_beat(
    bar: c_uint,
    beat_in_bar: c_uint,
) -> c_double {
    if bar < 1 {
        return -1.0;
    }

    let track = TIME_SIG_TRACK.lock().unwrap();
    track.bar_beat_to_beat(bar, beat_in_bar)
}

/// Get the starting beat of a specific bar
///
/// Returns: starting beat position, or -1.0 on error
#[no_mangle]
pub extern "C" fn daw_time_sig_get_bar_start(bar: c_uint) -> c_double {
    if bar < 1 {
        return -1.0;
    }

    let track = TIME_SIG_TRACK.lock().unwrap();
    track.get_bar_start_beat(bar)
}

/// Get the number of beats in a specific bar
///
/// Returns: beats per bar, or -1.0 on error
#[no_mangle]
pub extern "C" fn daw_time_sig_get_bar_length(bar: c_uint) -> c_double {
    if bar < 1 {
        return -1.0;
    }

    let track = TIME_SIG_TRACK.lock().unwrap();
    track.get_bar_length(bar)
}

/// Format time signature as string (e.g., "4/4", "3/4")
///
/// Returns: allocated string (caller must free with daw_time_sig_free_string)
#[no_mangle]
pub extern "C" fn daw_time_sig_format_string(
    numerator: c_uint,
    denominator: c_uint,
) -> *mut c_char {
    if numerator < 1 || denominator < 1 {
        return ptr::null_mut();
    }

    let sig = TimeSignature::new(1, numerator as u8, denominator as u8);
    CString::new(sig.to_string()).unwrap().into_raw()
}

/// Free a string returned by the time signature API
#[no_mangle]
pub extern "C" fn daw_time_sig_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = CString::from_raw(s);
        }
    }
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn reset_track() {
        let mut track = TIME_SIG_TRACK.lock().unwrap();
        track.reset();
    }

    #[test]
    fn test_ffi_init() {
        reset_track();
        assert_eq!(daw_time_sig_init(), 0);
        assert_eq!(daw_time_sig_get_change_count(), 1);
    }

    #[test]
    fn test_ffi_add_change() {
        reset_track();

        assert_eq!(daw_time_sig_add_change(5, 3, 4), 0);
        assert_eq!(daw_time_sig_get_change_count(), 2);

        // Invalid parameters
        assert_eq!(daw_time_sig_add_change(0, 4, 4), -1);  // bar < 1
    }

    #[test]
    fn test_ffi_get_at_bar() {
        reset_track();
        daw_time_sig_add_change(5, 3, 4);

        let mut info = TimeSignatureInfo {
            bar: 0,
            numerator: 0,
            denominator: 0,
        };

        // Bar 4 should be 4/4
        assert_eq!(daw_time_sig_get_at_bar(4, &mut info), 0);
        assert_eq!(info.numerator, 4);
        assert_eq!(info.denominator, 4);

        // Bar 5 should be 3/4
        assert_eq!(daw_time_sig_get_at_bar(5, &mut info), 0);
        assert_eq!(info.numerator, 3);
        assert_eq!(info.denominator, 4);
    }

    #[test]
    fn test_ffi_get_change_at() {
        reset_track();
        daw_time_sig_add_change(5, 3, 4);
        daw_time_sig_add_change(10, 6, 8);

        let mut info = TimeSignatureInfo {
            bar: 0,
            numerator: 0,
            denominator: 0,
        };

        // Index 0 = default 4/4 at bar 1
        assert_eq!(daw_time_sig_get_change_at(0, &mut info), 0);
        assert_eq!(info.bar, 1);
        assert_eq!(info.numerator, 4);

        // Index 1 = 3/4 at bar 5
        assert_eq!(daw_time_sig_get_change_at(1, &mut info), 0);
        assert_eq!(info.bar, 5);
        assert_eq!(info.numerator, 3);

        // Index 2 = 6/8 at bar 10
        assert_eq!(daw_time_sig_get_change_at(2, &mut info), 0);
        assert_eq!(info.bar, 10);
        assert_eq!(info.numerator, 6);

        // Index out of bounds
        assert_eq!(daw_time_sig_get_change_at(99, &mut info), -1);
    }

    #[test]
    fn test_ffi_remove_change() {
        reset_track();
        daw_time_sig_add_change(5, 3, 4);

        assert_eq!(daw_time_sig_get_change_count(), 2);

        // Cannot remove bar 1
        assert_eq!(daw_time_sig_remove_change(1), -1);

        // Remove bar 5
        assert_eq!(daw_time_sig_remove_change(5), 0);
        assert_eq!(daw_time_sig_get_change_count(), 1);

        // Already removed
        assert_eq!(daw_time_sig_remove_change(5), -1);
    }

    #[test]
    fn test_ffi_beat_to_bar_beat() {
        reset_track();
        // Default 4/4: beat 4 = bar 2, beat 0

        let mut result = BarBeatResult {
            bar: 0,
            beat_in_bar: 0,
            fraction: 0.0,
        };

        assert_eq!(daw_time_sig_beat_to_bar_beat(0.0, &mut result), 0);
        assert_eq!(result.bar, 1);
        assert_eq!(result.beat_in_bar, 0);

        assert_eq!(daw_time_sig_beat_to_bar_beat(4.0, &mut result), 0);
        assert_eq!(result.bar, 2);
        assert_eq!(result.beat_in_bar, 0);

        assert_eq!(daw_time_sig_beat_to_bar_beat(4.5, &mut result), 0);
        assert_eq!(result.bar, 2);
        assert_eq!(result.beat_in_bar, 0);
        assert!(result.fraction > 0.49 && result.fraction < 0.51);
    }

    #[test]
    fn test_ffi_bar_beat_to_beat() {
        reset_track();

        assert!(daw_time_sig_bar_beat_to_beat(1, 0) - 0.0 < 0.001);
        assert!(daw_time_sig_bar_beat_to_beat(1, 3) - 3.0 < 0.001);
        assert!(daw_time_sig_bar_beat_to_beat(2, 0) - 4.0 < 0.001);
        assert!(daw_time_sig_bar_beat_to_beat(5, 0) - 16.0 < 0.001);

        // Invalid bar
        assert_eq!(daw_time_sig_bar_beat_to_beat(0, 0), -1.0);
    }

    #[test]
    fn test_ffi_with_time_sig_change() {
        reset_track();
        // Add 3/4 at bar 3
        daw_time_sig_add_change(3, 3, 4);

        // In 4/4: bar 1 = beats 0-3, bar 2 = beats 4-7
        // In 3/4: bar 3 = beats 8-10
        // Bar 4 = beats 11-13

        let mut result = BarBeatResult {
            bar: 0,
            beat_in_bar: 0,
            fraction: 0.0,
        };

        // Beat 8 should be bar 3, beat 0
        assert_eq!(daw_time_sig_beat_to_bar_beat(8.0, &mut result), 0);
        assert_eq!(result.bar, 3);
        assert_eq!(result.beat_in_bar, 0);

        // Bar 3 beat 0 should be beat 8
        assert!(daw_time_sig_bar_beat_to_beat(3, 0) - 8.0 < 0.001);

        // Bar 4 beat 0 should be beat 11 (8 + 3)
        assert!(daw_time_sig_bar_beat_to_beat(4, 0) - 11.0 < 0.001);
    }

    #[test]
    fn test_ffi_get_bar_start_and_length() {
        reset_track();

        assert!(daw_time_sig_get_bar_start(1) - 0.0 < 0.001);
        assert!(daw_time_sig_get_bar_start(2) - 4.0 < 0.001);
        assert!(daw_time_sig_get_bar_start(5) - 16.0 < 0.001);

        assert!(daw_time_sig_get_bar_length(1) - 4.0 < 0.001);
        assert!(daw_time_sig_get_bar_length(3) - 4.0 < 0.001);

        // Invalid bar
        assert_eq!(daw_time_sig_get_bar_start(0), -1.0);
        assert_eq!(daw_time_sig_get_bar_length(0), -1.0);
    }

    #[test]
    fn test_ffi_format_string() {
        let ptr = daw_time_sig_format_string(4, 4);
        assert!(!ptr.is_null());

        unsafe {
            let c_str = CStr::from_ptr(ptr);
            assert_eq!(c_str.to_str().unwrap(), "4/4");
            daw_time_sig_free_string(ptr);
        }
    }

    #[test]
    fn test_ffi_null_safety() {
        reset_track();

        // Null pointer tests
        assert_eq!(daw_time_sig_get_at_bar(1, ptr::null_mut()), -1);
        assert_eq!(daw_time_sig_get_at_beat(0.0, ptr::null_mut()), -1);
        assert_eq!(daw_time_sig_get_change_at(0, ptr::null_mut()), -1);
        assert_eq!(daw_time_sig_beat_to_bar_beat(0.0, ptr::null_mut()), -1);

        // Should not crash
        daw_time_sig_free_string(ptr::null_mut());
    }

    #[test]
    fn test_ffi_roundtrip() {
        reset_track();
        daw_time_sig_add_change(5, 3, 4);
        daw_time_sig_add_change(10, 6, 8);

        // Test roundtrip for various positions
        for bar in [1, 2, 4, 5, 6, 9, 10, 12] {
            let info_result = daw_time_sig_get_at_bar(bar, &mut TimeSignatureInfo { bar: 0, numerator: 0, denominator: 0 });
            assert_eq!(info_result, 0);

            for beat_in_bar in [0, 1, 2] {
                let absolute = daw_time_sig_bar_beat_to_beat(bar, beat_in_bar);
                assert!(absolute >= 0.0);

                let mut result = BarBeatResult {
                    bar: 0,
                    beat_in_bar: 0,
                    fraction: 0.0,
                };
                let conv_result = daw_time_sig_beat_to_bar_beat(absolute, &mut result);
                assert_eq!(conv_result, 0);
                assert_eq!(result.bar, bar, "Bar mismatch for bar {} beat {}", bar, beat_in_bar);
                assert_eq!(result.beat_in_bar, beat_in_bar, "Beat mismatch for bar {} beat {}", bar, beat_in_bar);
            }
        }
    }
}
