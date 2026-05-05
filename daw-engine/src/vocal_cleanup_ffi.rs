//! Vocal Cleanup FFI Bridge
//!
//! FFI exports for C++ UI integration.
//! Provides C-compatible interface for the vocal cleanup pipeline.

use std::ffi::{c_char, c_float, c_int, CStr, CString};
use std::os::raw::c_void;
use std::path::PathBuf;

use crate::vocal_cleanup::{VocalCleanupProcessor, VocalCleanupSettings, VocalCleanupResult, VocalCleanupError};

/// C-compatible settings structure
#[repr(C)]
pub struct VocalCleanupSettingsFFI {
    pub silence_threshold_db: c_float,
    pub silence_min_duration: c_float,
    pub gap_compress_ratio: c_float,
    pub crossfade_ms: c_float,
    pub breath_sensitivity: c_float,
}

impl Default for VocalCleanupSettingsFFI {
    fn default() -> Self {
        Self {
            silence_threshold_db: -40.0,
            silence_min_duration: 0.2,
            gap_compress_ratio: 0.3,
            crossfade_ms: 10.0,
            breath_sensitivity: 0.5,
        }
    }
}

/// C-compatible result structure
#[repr(C)]
pub struct VocalCleanupResultFFI {
    pub gaps_detected: c_int,
    pub breaths_detected: c_int,
    pub original_duration: c_float,
    pub output_duration: c_float,
    pub time_removed: c_float,
    pub success: c_int,  // 0 = false, 1 = true
}

/// Create default settings
#[no_mangle]
pub extern "C" fn vocal_cleanup_settings_default() -> VocalCleanupSettingsFFI {
    VocalCleanupSettingsFFI::default()
}

/// Check if vocal cleanup is available
#[no_mangle]
pub extern "C" fn vocal_cleanup_is_available() -> c_int {
    let processor = VocalCleanupProcessor::new();
    if processor.is_available() {
        1
    } else {
        0
    }
}

/// Process audio file through vocal cleanup pipeline
#[no_mangle]
pub extern "C" fn vocal_cleanup_process(
    input_path: *const c_char,
    output_path: *const c_char,
    settings: *const VocalCleanupSettingsFFI,
    result: *mut VocalCleanupResultFFI,
) -> c_int {
    // Safety checks
    if input_path.is_null() || output_path.is_null() || settings.is_null() || result.is_null() {
        return -1; // Invalid arguments
    }

    // Convert C strings to Rust
    let input_str = unsafe {
        match CStr::from_ptr(input_path).to_str() {
            Ok(s) => s,
            Err(_) => return -2, // Invalid UTF-8
        }
    };

    let output_str = unsafe {
        match CStr::from_ptr(output_path).to_str() {
            Ok(s) => s,
            Err(_) => return -2,
        }
    };

    // Convert settings
    let ffi_settings = unsafe { &*settings };
    let rust_settings = VocalCleanupSettings {
        silence_threshold_db: ffi_settings.silence_threshold_db,
        silence_min_duration: ffi_settings.silence_min_duration,
        gap_compress_ratio: ffi_settings.gap_compress_ratio,
        crossfade_ms: ffi_settings.crossfade_ms,
        breath_sensitivity: ffi_settings.breath_sensitivity,
    };

    // Process
    let processor = VocalCleanupProcessor::new();
    let process_result = processor.process(
        &PathBuf::from(input_str),
        &PathBuf::from(output_str),
        &rust_settings,
    );

    // Convert result
    match process_result {
        Ok(r) => {
            let ffi_result = VocalCleanupResultFFI {
                gaps_detected: r.gaps_detected,
                breaths_detected: r.breaths_detected,
                original_duration: r.original_duration,
                output_duration: r.output_duration,
                time_removed: r.time_removed,
                success: if r.success { 1 } else { 0 },
            };
            unsafe {
                *result = ffi_result;
            }
            0 // Success
        }
        Err(e) => {
            // Store error in result
            let ffi_result = VocalCleanupResultFFI {
                gaps_detected: 0,
                breaths_detected: 0,
                original_duration: 0.0,
                output_duration: 0.0,
                time_removed: 0.0,
                success: 0,
            };
            unsafe {
                *result = ffi_result;
            }
            match e {
                VocalCleanupError::NotAvailable => -3,
                VocalCleanupError::InputNotFound => -4,
                VocalCleanupError::OutputFailed => -5,
                VocalCleanupError::Internal(_) => -6,
            }
        }
    }
}

/// Preview what would be processed (without actually processing)
#[no_mangle]
pub extern "C" fn vocal_cleanup_preview(
    input_path: *const c_char,
    settings: *const VocalCleanupSettingsFFI,
    result: *mut VocalCleanupResultFFI,
) -> c_int {
    // Safety checks
    if input_path.is_null() || settings.is_null() || result.is_null() {
        return -1;
    }

    // Convert C strings to Rust
    let input_str = unsafe {
        match CStr::from_ptr(input_path).to_str() {
            Ok(s) => s,
            Err(_) => return -2,
        }
    };

    // Convert settings
    let ffi_settings = unsafe { &*settings };
    let rust_settings = VocalCleanupSettings {
        silence_threshold_db: ffi_settings.silence_threshold_db,
        silence_min_duration: ffi_settings.silence_min_duration,
        gap_compress_ratio: ffi_settings.gap_compress_ratio,
        crossfade_ms: ffi_settings.crossfade_ms,
        breath_sensitivity: ffi_settings.breath_sensitivity,
    };

    // Preview
    let processor = VocalCleanupProcessor::new();
    let preview_result = processor.preview(
        &PathBuf::from(input_str),
        &rust_settings,
    );

    // Convert result
    match preview_result {
        Ok(r) => {
            let ffi_result = VocalCleanupResultFFI {
                gaps_detected: r.gaps_detected,
                breaths_detected: r.breaths_detected,
                original_duration: r.original_duration,
                output_duration: r.output_duration,
                time_removed: r.time_removed,
                success: if r.success { 1 } else { 0 },
            };
            unsafe {
                *result = ffi_result;
            }
            0 // Success
        }
        Err(e) => {
            let ffi_result = VocalCleanupResultFFI {
                gaps_detected: 0,
                breaths_detected: 0,
                original_duration: 0.0,
                output_duration: 0.0,
                time_removed: 0.0,
                success: 0,
            };
            unsafe {
                *result = ffi_result;
            }
            match e {
                VocalCleanupError::NotAvailable => -3,
                VocalCleanupError::InputNotFound => -4,
                VocalCleanupError::OutputFailed => -5,
                VocalCleanupError::Internal(_) => -6,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffi_settings_default() {
        let settings = vocal_cleanup_settings_default();
        assert_eq!(settings.silence_threshold_db, -40.0);
        assert_eq!(settings.silence_min_duration, 0.2);
        assert_eq!(settings.gap_compress_ratio, 0.3);
    }

    #[test]
    fn test_ffi_is_available() {
        // Should return 0 or 1
        let available = vocal_cleanup_is_available();
        assert!(available == 0 || available == 1);
    }

    #[test]
    fn test_ffi_null_safety() {
        // Test with null pointers - should return error
        let result = vocal_cleanup_process(
            std::ptr::null(),
            std::ptr::null(),
            std::ptr::null(),
            std::ptr::null_mut(),
        );
        assert_eq!(result, -1);

        let result2 = vocal_cleanup_preview(
            std::ptr::null(),
            std::ptr::null(),
            std::ptr::null_mut(),
        );
        assert_eq!(result2, -1);
    }
}
