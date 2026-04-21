//! Clip Player FFI - C interface for clip playback control
//!
//! Provides FFI exports to allow JUCE C++ UI to control clip playback
//! through the Rust clip_player module.

use std::ffi::{c_char, c_void, CStr};
use std::sync::{Arc, Mutex};

use crate::clip_player::{ClipPlayer, ClipPlaybackState};
use crate::session::SessionView;
use crate::sample_player_integration::SamplePlayerIntegration;
use crate::sample::Sample;

/// Opaque handle to the clip player instance
pub struct ClipPlayerHandle {
    player: Arc<Mutex<ClipPlayer>>,
    _session: Arc<Mutex<SessionView>>,
    sample_integration: Arc<Mutex<SamplePlayerIntegration>>,
}

/// Initialize the clip player subsystem
/// 
/// # Safety
/// Returns an opaque pointer that must be passed to other clip_player_ffi functions.
/// Must be freed with opendaw_clip_player_shutdown.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_init(
    session_ptr: *mut c_void
) -> *mut c_void {
    if session_ptr.is_null() {
        return std::ptr::null_mut();
    }
    
    let handle = Box::new(ClipPlayerHandle {
        player: Arc::new(Mutex::new(ClipPlayer::new(8, 16))), // 8 tracks, 16 clips per track
        _session: Arc::new(Mutex::new(SessionView::new(8, 16))),
        sample_integration: Arc::new(Mutex::new(SamplePlayerIntegration::new(8))), // 8 tracks
    });
    
    Box::into_raw(handle) as *mut c_void
}

/// Shutdown and free the clip player
/// 
/// # Safety
/// handle_ptr must be a valid pointer returned by opendaw_clip_player_init.
/// After this call, the pointer is invalid.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_shutdown(handle_ptr: *mut c_void) {
    if handle_ptr.is_null() {
        return;
    }
    
    let _ = Box::from_raw(handle_ptr as *mut ClipPlayerHandle);
}

/// Trigger a clip to start playing on a track
/// 
/// # Safety
/// engine_ptr must be a valid pointer. track_idx and clip_idx must be within bounds.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_trigger_clip(
    engine_ptr: *mut c_void,
    track_idx: usize,
    clip_idx: usize,
) -> i32 {
    if engine_ptr.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(mut player) = handle.player.lock() {
        if track_idx >= player.track_count() || clip_idx >= player.clip_count_per_track() {
            return -1;
        }
        player.trigger_clip(track_idx, clip_idx);
        0
    } else {
        -1
    }
}

/// Stop playback on a track
/// 
/// # Safety
/// engine_ptr must be a valid pointer.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_stop_clip(
    engine_ptr: *mut c_void,
    track_idx: usize,
) -> i32 {
    if engine_ptr.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(mut player) = handle.player.lock() {
        if track_idx >= player.track_count() {
            return -1;
        }
        player.stop_clip(track_idx);
        0
    } else {
        -1
    }
}

/// Get the playback state of a clip
/// 
/// # Safety
/// engine_ptr must be valid. state_out must be a valid pointer to write the state.
/// State values: 0=stopped, 1=playing, 2=queued
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_get_state(
    engine_ptr: *mut c_void,
    track_idx: usize,
    clip_idx: usize,
    state_out: *mut i32,
) -> i32 {
    if engine_ptr.is_null() || state_out.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(player) = handle.player.lock() {
        if track_idx >= player.track_count() || clip_idx >= player.clip_count_per_track() {
            return -1;
        }
        
        let state = player.get_clip_state(track_idx, clip_idx);
        let state_value = match state {
            ClipPlaybackState::Stopped => 0,
            ClipPlaybackState::Playing { .. } => 1,
            ClipPlaybackState::Queued => 2,
        };
        
        *state_out = state_value;
        0
    } else {
        -1
    }
}

/// Queue a clip to start on the next beat boundary
/// 
/// # Safety
/// engine_ptr must be valid.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_queue_clip(
    engine_ptr: *mut c_void,
    track_idx: usize,
    clip_idx: usize,
) -> i32 {
    if engine_ptr.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(mut player) = handle.player.lock() {
        if track_idx >= player.track_count() || clip_idx >= player.clip_count_per_track() {
            return -1;
        }
        player.queue_clip(track_idx, clip_idx);
        0
    } else {
        -1
    }
}

/// Stop all clips across all tracks
/// 
/// # Safety
/// engine_ptr must be valid.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_stop_all(engine_ptr: *mut c_void) -> i32 {
    if engine_ptr.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(mut player) = handle.player.lock() {
        player.stop_all();
        0
    } else {
        -1
    }
}

/// Get the current playback position of a playing clip in beats
/// 
/// # Safety
/// engine_ptr must be valid. position_out must be a valid pointer.
/// Returns 0 on success, -1 if clip not playing or error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_get_position(
    engine_ptr: *mut c_void,
    track_idx: usize,
    position_out: *mut f64,
) -> i32 {
    if engine_ptr.is_null() || position_out.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(player) = handle.player.lock() {
        if track_idx >= player.track_count() {
            return -1;
        }
        
        if let Some(pos) = player.get_playback_position(track_idx) {
            *position_out = pos;
            0
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Check if any clip is currently playing on a track
/// 
/// # Safety
/// engine_ptr must be valid. playing_out must be a valid pointer (0=false, 1=true).
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_is_playing(
    engine_ptr: *mut c_void,
    track_idx: usize,
    playing_out: *mut i32,
) -> i32 {
    if engine_ptr.is_null() || playing_out.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(player) = handle.player.lock() {
        if track_idx >= player.track_count() {
            return -1;
        }
        
        *playing_out = if player.is_track_playing(track_idx) { 1 } else { 0 };
        0
    } else {
        -1
    }
}

/// Get the index of the currently playing clip on a track
/// 
/// # Safety
/// engine_ptr must be valid. clip_idx_out must be a valid pointer.
/// Returns 0 on success with clip index, -1 if no clip playing or error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_get_playing_clip(
    engine_ptr: *mut c_void,
    track_idx: usize,
    clip_idx_out: *mut usize,
) -> i32 {
    if engine_ptr.is_null() || clip_idx_out.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    if let Ok(player) = handle.player.lock() {
        if track_idx >= player.track_count() {
            return -1;
        }
        
        if let Some(idx) = player.get_playing_clip_index(track_idx) {
            *clip_idx_out = idx;
            0
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Load a sample (WAV file) into a clip slot
/// 
/// # Safety
/// engine_ptr must be valid. file_path must be a valid null-terminated C string.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn opendaw_clip_player_load_sample(
    engine_ptr: *mut c_void,
    track_idx: usize,
    clip_idx: usize,
    file_path: *const c_char,
) -> i32 {
    if engine_ptr.is_null() || file_path.is_null() {
        return -1;
    }
    
    let handle = &*(engine_ptr as *const ClipPlayerHandle);
    
    // Convert C string to Rust string
    let path_str = match CStr::from_ptr(file_path).to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };
    
    // Load the sample from file
    let sample = match Sample::from_file(path_str) {
        Ok(s) => s,
        Err(_) => return -1,
    };
    
    // Store the sample in the integration
    if let Ok(mut integration) = handle.sample_integration.lock() {
        integration.load_sample(track_idx, clip_idx, sample);
        0
    } else {
        -1
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Helper to create a test handle
    fn create_test_handle() -> *mut c_void {
        unsafe {
            // Create a minimal session for testing
            let session = Box::new(SessionView::new(8, 16));
            let session_ptr = Box::into_raw(session) as *mut c_void;
            let handle = opendaw_clip_player_init(session_ptr);
            // Don't free session here, it's managed by handle
            handle
        }
    }

    fn cleanup_handle(handle: *mut c_void) {
        unsafe {
            opendaw_clip_player_shutdown(handle);
        }
    }

    #[test]
    fn test_ffi_trigger_clip() {
        let handle = create_test_handle();
        assert!(!handle.is_null());
        
        unsafe {
            // Trigger clip on track 0, clip 1
            let result = opendaw_clip_player_trigger_clip(handle, 0, 1);
            assert_eq!(result, 0, "Trigger clip should succeed");
            
            // Verify state is playing
            let mut state: i32 = -1;
            let state_result = opendaw_clip_player_get_state(handle, 0, 1, &mut state);
            assert_eq!(state_result, 0, "Get state should succeed");
            assert_eq!(state, 1, "Clip should be playing (state=1)");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_stop_clip() {
        let handle = create_test_handle();
        
        unsafe {
            // Trigger then stop
            opendaw_clip_player_trigger_clip(handle, 0, 1);
            let result = opendaw_clip_player_stop_clip(handle, 0);
            assert_eq!(result, 0, "Stop clip should succeed");
            
            // Verify stopped state
            let mut state: i32 = -1;
            opendaw_clip_player_get_state(handle, 0, 1, &mut state);
            assert_eq!(state, 0, "Clip should be stopped (state=0)");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_get_state() {
        let handle = create_test_handle();
        
        unsafe {
            // Initially stopped
            let mut state: i32 = -1;
            let result = opendaw_clip_player_get_state(handle, 0, 0, &mut state);
            assert_eq!(result, 0, "Get state should succeed");
            assert_eq!(state, 0, "Initial state should be stopped (0)");
            
            // After trigger
            opendaw_clip_player_trigger_clip(handle, 0, 0);
            opendaw_clip_player_get_state(handle, 0, 0, &mut state);
            assert_eq!(state, 1, "After trigger state should be playing (1)");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_queue_clip() {
        let handle = create_test_handle();
        
        unsafe {
            // Queue a clip
            let result = opendaw_clip_player_queue_clip(handle, 0, 2);
            assert_eq!(result, 0, "Queue clip should succeed");
            
            // Verify queued state
            let mut state: i32 = -1;
            opendaw_clip_player_get_state(handle, 0, 2, &mut state);
            assert_eq!(state, 2, "Clip should be queued (state=2)");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_stop_all() {
        let handle = create_test_handle();
        
        unsafe {
            // Trigger multiple clips
            opendaw_clip_player_trigger_clip(handle, 0, 0);
            opendaw_clip_player_trigger_clip(handle, 1, 1);
            opendaw_clip_player_trigger_clip(handle, 2, 2);
            
            // Stop all
            let result = opendaw_clip_player_stop_all(handle);
            assert_eq!(result, 0, "Stop all should succeed");
            
            // Verify all stopped
            let mut state: i32 = -1;
            for track in 0..3 {
                opendaw_clip_player_get_state(handle, track, track, &mut state);
                assert_eq!(state, 0, "Track {} should be stopped", track);
            }
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_invalid_engine() {
        unsafe {
            let result = opendaw_clip_player_trigger_clip(std::ptr::null_mut(), 0, 0);
            assert_eq!(result, -1, "NULL engine should return error");
            
            let result = opendaw_clip_player_stop_clip(std::ptr::null_mut(), 0);
            assert_eq!(result, -1, "NULL engine should return error");
            
            let mut state: i32 = -1;
            let result = opendaw_clip_player_get_state(std::ptr::null_mut(), 0, 0, &mut state);
            assert_eq!(result, -1, "NULL engine should return error");
        }
    }

    #[test]
    fn test_ffi_invalid_track() {
        let handle = create_test_handle();
        
        unsafe {
            // Track 99 is out of bounds (we have 8 tracks: 0-7)
            let result = opendaw_clip_player_trigger_clip(handle, 99, 0);
            assert_eq!(result, -1, "Invalid track should return error");
            
            let result = opendaw_clip_player_stop_clip(handle, 99);
            assert_eq!(result, -1, "Invalid track should return error");
            
            let mut state: i32 = -1;
            let result = opendaw_clip_player_get_state(handle, 99, 0, &mut state);
            assert_eq!(result, -1, "Invalid track should return error");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_invalid_clip() {
        let handle = create_test_handle();
        
        unsafe {
            // Clip 99 is out of bounds (we have 16 clips: 0-15)
            let result = opendaw_clip_player_trigger_clip(handle, 0, 99);
            assert_eq!(result, -1, "Invalid clip should return error");
            
            let mut state: i32 = -1;
            let result = opendaw_clip_player_get_state(handle, 0, 99, &mut state);
            assert_eq!(result, -1, "Invalid clip should return error");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_concurrent_trigger() {
        use std::thread;
        use std::sync::Arc;
        use std::sync::atomic::{AtomicUsize, Ordering};
        
        let handle = create_test_handle();
        let handle_arc = Arc::new(AtomicUsize::new(handle as usize));
        let mut handles = vec![];
        
        for i in 0..4 {
            let h_clone = Arc::clone(&handle_arc);
            let t = thread::spawn(move || {
                let h = h_clone.load(Ordering::SeqCst) as *mut c_void;
                unsafe {
                    opendaw_clip_player_trigger_clip(h, i, i);
                }
            });
            handles.push(t);
        }
        
        for t in handles {
            t.join().unwrap();
        }
        
        // Verify all clips triggered
        unsafe {
            let mut state: i32 = -1;
            for i in 0..4 {
                opendaw_clip_player_get_state(handle, i, i, &mut state);
                assert_eq!(state, 1, "Clip on track {} should be playing", i);
            }
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_state_consistency() {
        let handle = create_test_handle();
        
        unsafe {
            // Trigger clip
            opendaw_clip_player_trigger_clip(handle, 0, 1);
            
            // Read state multiple times - should be consistent
            let mut state1: i32 = -1;
            let mut state2: i32 = -1;
            let mut state3: i32 = -1;
            
            opendaw_clip_player_get_state(handle, 0, 1, &mut state1);
            opendaw_clip_player_get_state(handle, 0, 1, &mut state2);
            opendaw_clip_player_get_state(handle, 0, 1, &mut state3);
            
            assert_eq!(state1, state2, "State reads should be consistent");
            assert_eq!(state2, state3, "State reads should be consistent");
            assert_eq!(state1, 1, "All reads should show playing");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_get_position() {
        let handle = create_test_handle();
        
        unsafe {
            // Initially no position (not playing)
            let mut pos: f64 = -1.0;
            let result = opendaw_clip_player_get_position(handle, 0, &mut pos);
            assert_eq!(result, -1, "Position for stopped track should return error");
            
            // Trigger clip
            opendaw_clip_player_trigger_clip(handle, 0, 0);
            
            // Now should have position
            let result = opendaw_clip_player_get_position(handle, 0, &mut pos);
            assert_eq!(result, 0, "Position for playing track should succeed");
            assert_eq!(pos, 0.0, "Initial position should be 0.0");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_is_playing() {
        let handle = create_test_handle();
        
        unsafe {
            // Initially not playing
            let mut playing: i32 = -1;
            let result = opendaw_clip_player_is_playing(handle, 0, &mut playing);
            assert_eq!(result, 0, "is_playing should succeed");
            assert_eq!(playing, 0, "Should not be playing initially");
            
            // Trigger clip
            opendaw_clip_player_trigger_clip(handle, 0, 0);
            
            opendaw_clip_player_is_playing(handle, 0, &mut playing);
            assert_eq!(playing, 1, "Should be playing after trigger");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_get_playing_clip() {
        let handle = create_test_handle();
        
        unsafe {
            // Initially no playing clip
            let mut clip_idx: usize = 999;
            let result = opendaw_clip_player_get_playing_clip(handle, 0, &mut clip_idx);
            assert_eq!(result, -1, "No playing clip should return error");
            
            // Trigger clip 3
            opendaw_clip_player_trigger_clip(handle, 0, 3);
            
            // Now should report clip 3
            let result = opendaw_clip_player_get_playing_clip(handle, 0, &mut clip_idx);
            assert_eq!(result, 0, "Should succeed with playing clip");
            assert_eq!(clip_idx, 3, "Should report clip index 3");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_init_null_session() {
        unsafe {
            let handle = opendaw_clip_player_init(std::ptr::null_mut());
            assert!(handle.is_null(), "Init with NULL session should return NULL");
        }
    }

    #[test]
    fn test_ffi_null_state_out() {
        let handle = create_test_handle();
        
        unsafe {
            // NULL state_out should return error
            let result = opendaw_clip_player_get_state(handle, 0, 0, std::ptr::null_mut());
            assert_eq!(result, -1, "NULL state_out should return error");
        }
        
        cleanup_handle(handle);
    }

    #[test]
    fn test_ffi_new_clip_stops_old() {
        let handle = create_test_handle();
        
        unsafe {
            // Trigger clip 0
            opendaw_clip_player_trigger_clip(handle, 0, 0);
            
            // Trigger clip 1 on same track - should stop clip 0
            opendaw_clip_player_trigger_clip(handle, 0, 1);
            
            // Verify clip 0 stopped
            let mut state: i32 = -1;
            opendaw_clip_player_get_state(handle, 0, 0, &mut state);
            assert_eq!(state, 0, "Clip 0 should be stopped");
            
            // Verify clip 1 playing
            opendaw_clip_player_get_state(handle, 0, 1, &mut state);
            assert_eq!(state, 1, "Clip 1 should be playing");
        }
        
        cleanup_handle(handle);
    }
}
