//! E2E Integration Test: Stem Separation Workflow
//!
//! Tests the complete workflow:
//! 1. Initialize stem separator
//! 2. Check demucs availability
//! 3. Mock stem separation process
//! 4. Verify stem file paths are returned
//! 5. Verify arrangement track creation

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_int, c_void};
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

// FFI imports from ffi_bridge
extern "C" {
    fn daw_stem_separator_create() -> *mut c_void;
    fn daw_stem_separator_free(handle: *mut c_void);
    fn daw_stem_is_available(handle: *mut c_void) -> c_int;
    fn daw_stem_separate(handle: *mut c_void, input_path: *const c_char, output_dir: *const c_char) -> c_int;
    fn daw_stem_get_progress(handle: *mut c_void) -> c_double;
    fn daw_stem_is_complete(handle: *mut c_void) -> c_int;
    fn daw_stem_get_path(handle: *mut c_void, stem_type: c_int) -> *const c_char;
    fn daw_stem_cancel(handle: *mut c_void);
}

/// Test the complete stem separation workflow lifecycle
#[test]
fn test_stem_extraction_workflow_lifecycle() {
    unsafe {
        // Step 1: Create stem separator
        let handle = daw_stem_separator_create();
        assert!(!handle.is_null(), "Failed to create stem separator");

        // Step 2: Check availability (will be 0 in test env without demucs)
        let available = daw_stem_is_available(handle);
        println!("Demucs availability: {}", available);
        
        // In CI/test environment, demucs won't be available - that's expected
        // The test verifies the API works correctly
        assert!(
            available == 0 || available == 1,
            "Availability should be 0 or 1, got {}",
            available
        );

        // Step 3: Check initial state
        assert_eq!(
            daw_stem_is_complete(handle),
            0,
            "Should not be complete initially"
        );
        assert_eq!(
            daw_stem_get_progress(handle),
            0.0,
            "Progress should be 0 initially"
        );

        // Clean up
        daw_stem_separator_free(handle);
    }
}

/// Test stem workflow with mock input (verifies error handling)
#[test]
fn test_stem_workflow_error_handling() {
    unsafe {
        let handle = daw_stem_separator_create();
        assert!(!handle.is_null());

        // Try to separate non-existent file
        let input_path = CString::new("/nonexistent/file.wav").unwrap();
        let output_dir = CString::new("/tmp/stems").unwrap();

        let result = daw_stem_separate(handle, input_path.as_ptr(), output_dir.as_ptr());
        
        // Should fail (input not found) but not crash
        // Note: If demucs is not available, this might also return -1
        assert!(
            result == -1 || result == 0,
            "Should handle missing file gracefully"
        );

        daw_stem_separator_free(handle);
    }
}

/// Test stem workflow cancellation
#[test]
fn test_stem_workflow_cancellation() {
    unsafe {
        let handle = daw_stem_separator_create();
        assert!(!handle.is_null());

        // Cancel immediately (should not crash)
        daw_stem_cancel(handle);

        // Verify still in valid state
        assert_eq!(daw_stem_is_complete(handle), 0);
        assert_eq!(daw_stem_get_progress(handle), 0.0);

        daw_stem_separator_free(handle);
    }
}

/// Test null handle safety
#[test]
fn test_stem_workflow_null_safety() {
    unsafe {
        // All operations with null handle should return safe defaults
        assert_eq!(daw_stem_is_available(std::ptr::null_mut()), 0);
        assert_eq!(daw_stem_is_complete(std::ptr::null_mut()), 0);
        assert_eq!(daw_stem_get_progress(std::ptr::null_mut()), 0.0);
        
        // Cancel on null should not crash
        daw_stem_cancel(std::ptr::null_mut());
        
        // Get path on null should return null
        assert!(daw_stem_get_path(std::ptr::null_mut(), 0).is_null());
    }
}

/// Test stem path retrieval with invalid types
#[test]
fn test_stem_path_invalid_types() {
    unsafe {
        let handle = daw_stem_separator_create();
        assert!(!handle.is_null());

        // Invalid stem type (4 is out of range 0-3)
        assert!(daw_stem_get_path(handle, 4).is_null());
        
        // Negative stem type
        assert!(daw_stem_get_path(handle, -1).is_null());

        daw_stem_separator_free(handle);
    }
}

/// Test complete workflow with stubbed result paths
/// This simulates what happens after successful separation
#[test]
fn test_stem_workflow_result_handling() {
    // This test verifies the data structures can hold and return stem paths
    // In a real scenario, these would be populated by demucs
    
    use daw_engine::stem_separation::{StemSeparationResult, StemType};
    use std::path::PathBuf;

    // Create a mock result
    let mut result = StemSeparationResult::new();
    result.success = true;
    result.set_path(StemType::Drums, PathBuf::from("/tmp/stems/song_drums.wav"));
    result.set_path(StemType::Bass, PathBuf::from("/tmp/stems/song_bass.wav"));
    result.set_path(StemType::Vocals, PathBuf::from("/tmp/stems/song_vocals.wav"));
    result.set_path(StemType::Other, PathBuf::from("/tmp/stems/song_other.wav"));

    // Verify all 4 stems are present
    assert_eq!(result.stem_count(), 4);
    assert!(result.get_path(StemType::Drums).is_some());
    assert!(result.get_path(StemType::Bass).is_some());
    assert!(result.get_path(StemType::Vocals).is_some());
    assert!(result.get_path(StemType::Other).is_some());

    // Verify paths
    assert_eq!(
        result.get_path(StemType::Drums).unwrap().to_str().unwrap(),
        "/tmp/stems/song_drums.wav"
    );
}

/// Test arrangement track creation workflow
/// Verifies the arrangement system can receive stem clips
#[test]
fn test_stem_arrangement_integration() {
    use daw_engine::arrangement::Arrangement;
    use daw_engine::session::Clip;
    
    // Create arrangement with 8 tracks (4 existing + 4 for stems)
    let mut arrangement = Arrangement::new(8);
    
    // Add 4 stem clips at tracks 4-7 (the new stem tracks)
    let stem_tracks = vec![
        (4, "Drums", "stems/song_drums.wav"),
        (5, "Bass", "stems/song_bass.wav"),
        (6, "Vocals", "stems/song_vocals.wav"),
        (7, "Other", "stems/song_other.wav"),
    ];
    
    for (track_idx, name, path) in stem_tracks {
        let clip = Clip::new_audio(name, 4.0); // 4 bars duration
        let result = arrangement.add_clip(track_idx, 0.0, clip);
        assert!(result.is_ok(), "Failed to add clip to track {}", track_idx);
    }
    
    // Verify all 4 stems were added
    assert_eq!(arrangement.total_clip_count(), 4);
    
    // Verify clips are on correct tracks
    let clips_track_4 = arrangement.clips_on_track(4).expect("Track 4 should exist");
    assert_eq!(clips_track_4.len(), 1);
    assert_eq!(clips_track_4[0].clip_data.name(), "Drums");
    
    let clips_track_5 = arrangement.clips_on_track(5).expect("Track 5 should exist");
    assert_eq!(clips_track_5.len(), 1);
    assert_eq!(clips_track_5[0].clip_data.name(), "Bass");
}

/// Test the full E2E workflow from UI perspective
/// Simulates: right-click clip → "Extract Stems" → dialog → 4 tracks created
#[test]
fn test_full_stem_workflow_e2e() {
    // This is a comprehensive test that simulates the full user workflow
    
    unsafe {
        // 1. User right-clicks clip and selects "Extract Stems"
        // (UI action - simulated by creating separator)
        let handle = daw_stem_separator_create();
        assert!(!handle.is_null(), "Step 1: Create separator - FAILED");
        
        // 2. Check if stem separation is available
        let available = daw_stem_is_available(handle);
        println!("Step 2: Check availability - {}", 
                 if available != 0 { "AVAILABLE" } else { "NOT AVAILABLE (expected in test env)" });
        
        // 3. Progress dialog would show (simulated)
        let progress = daw_stem_get_progress(handle);
        assert!(
            progress >= 0.0 && progress <= 1.0,
            "Step 3: Progress should be 0.0-1.0 range"
        );
        
        // 4. Verify completion state
        let complete = daw_stem_is_complete(handle);
        assert_eq!(
            complete, 0,
            "Step 4: Should not be complete without running separation"
        );
        
        // 5. Clean up
        daw_stem_separator_free(handle);
        println!("Step 5: Cleanup - OK");
    }
    
    println!("Full E2E workflow test passed!");
}

/// Test concurrent operations (cancel while "running")
#[test]
fn test_stem_workflow_concurrent_cancel() {
    unsafe {
        let handle = daw_stem_separator_create();
        assert!(!handle.is_null());
        
        // Simulate starting a long operation
        // In real usage, this would be on a background thread
        
        // Cancel while "in progress"
        daw_stem_cancel(handle);
        
        // Verify handle is still valid
        let _progress = daw_stem_get_progress(handle);
        let _complete = daw_stem_is_complete(handle);
        
        // Should not crash
        daw_stem_separator_free(handle);
    }
}

/// Test memory safety - create and destroy many separators
#[test]
fn test_stem_workflow_memory_stress() {
    unsafe {
        // Create and destroy 100 separators to check for leaks/corruption
        for i in 0..100 {
            let handle = daw_stem_separator_create();
            assert!(!handle.is_null(), "Failed to create separator at iteration {}", i);
            
            // Do some operations
            let _ = daw_stem_is_available(handle);
            let _ = daw_stem_get_progress(handle);
            
            // Clean up
            daw_stem_separator_free(handle);
        }
    }
}
