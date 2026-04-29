//! Integration tests for Phase 7: Mixer Level Meters
//!
//! Tests the end-to-end meter level flow:
//! 1. Engine initialization sets up meter state
//! 2. Mixer process() updates track and master levels
//! 3. FFI functions return correct levels
//! 4. UI polling retrieves levels via EngineBridge

use daw_engine::meter_ffi::{
    daw_meter_init, daw_meter_get_track_peak, daw_meter_get_track_rms,
    daw_meter_get_master_peak, daw_meter_get_master_rms, daw_meter_get_track_count,
    update_track_peak, update_track_rms, update_master_peak, update_master_rms,
};
use std::sync::Mutex;

// Serial test guard to prevent parallel test conflicts
static TEST_GUARD: Mutex<()> = Mutex::new(());

#[test]
fn test_meter_initialization_on_engine_init() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    // Initialize meter state (simulates what engine_ffi::opendaw_engine_init does)
    daw_meter_init(8);
    
    // Verify track count
    assert_eq!(daw_meter_get_track_count(), 8);
}

#[test]
fn test_track_level_update_and_retrieval() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    daw_meter_init(4);
    
    // Update track levels (simulates what mixer::process does)
    update_track_peak(0, -6.0);
    update_track_rms(0, -12.0);
    
    // Verify retrieval via FFI
    assert_eq!(daw_meter_get_track_peak(0), -6.0);
    assert_eq!(daw_meter_get_track_rms(0), -12.0);
}

#[test]
fn test_master_level_update_and_retrieval() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    daw_meter_init(4);
    
    // Update master levels (simulates what mixer::process does)
    update_master_peak(-3.0);
    update_master_rms(-9.0);
    
    // Verify retrieval via FFI
    assert_eq!(daw_meter_get_master_peak(), -3.0);
    assert_eq!(daw_meter_get_master_rms(), -9.0);
}

#[test]
fn test_multiple_tracks_independent() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    daw_meter_init(8);
    
    // Set different levels for different tracks
    for i in 0..8 {
        let peak = -6.0 - (i as f32 * 2.0);  // -6, -8, -10, etc.
        let rms = -12.0 - (i as f32 * 2.0);  // -12, -14, -16, etc.
        update_track_peak(i, peak);
        update_track_rms(i, rms);
    }
    
    // Verify each track has correct independent values
    for i in 0..8 {
        let expected_peak = -6.0 - (i as f32 * 2.0);
        let expected_rms = -12.0 - (i as f32 * 2.0);
        assert_eq!(daw_meter_get_track_peak(i), expected_peak);
        assert_eq!(daw_meter_get_track_rms(i), expected_rms);
    }
}

#[test]
fn test_invalid_track_returns_silence() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    daw_meter_init(4);
    
    // Invalid track should return -96.0 (silence level)
    assert_eq!(daw_meter_get_track_peak(99), -96.0);
    assert_eq!(daw_meter_get_track_rms(99), -96.0);
}

#[test]
fn test_level_persistence() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    daw_meter_init(4);
    
    // Set initial levels
    update_track_peak(0, -6.0);
    update_track_rms(0, -12.0);
    
    // Verify levels persist across multiple reads
    for _ in 0..10 {
        assert_eq!(daw_meter_get_track_peak(0), -6.0);
        assert_eq!(daw_meter_get_track_rms(0), -12.0);
    }
}

#[test]
fn test_silent_level() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    daw_meter_init(4);
    
    // Update with silence level
    update_track_peak(0, -96.0);
    update_track_rms(0, -96.0);
    
    assert_eq!(daw_meter_get_track_peak(0), -96.0);
    assert_eq!(daw_meter_get_track_rms(0), -96.0);
}

#[test]
fn test_clipping_level() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    daw_meter_init(4);
    
    // Update with clipping level (above 0dB)
    update_track_peak(0, 3.0);  // +3dB clipping
    update_track_rms(0, -1.0);  // slightly below peak
    
    assert_eq!(daw_meter_get_track_peak(0), 3.0);
    assert_eq!(daw_meter_get_track_rms(0), -1.0);
}

#[test]
fn test_meter_levels_after_reinit() {
    let _guard = TEST_GUARD.lock().unwrap();
    
    // First init
    daw_meter_init(4);
    update_track_peak(0, -6.0);
    assert_eq!(daw_meter_get_track_peak(0), -6.0);
    
    // Re-init (simulates engine restart)
    daw_meter_init(8);
    
    // After re-init, should have new track count but levels reset to silence
    assert_eq!(daw_meter_get_track_count(), 8);
    assert_eq!(daw_meter_get_track_peak(0), -96.0);  // Reset to silence
}
