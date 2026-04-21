//! Engine FFI Module - C interface for UI to Rust engine communication
//!
//! This module provides a C FFI layer that allows the JUCE C++ UI to communicate
//! with the Rust audio engine. All functions follow the C ABI for cross-language compatibility.

use std::ffi::{c_double, c_float, c_int, c_void};
use std::sync::{Arc, Mutex};

// Reuse existing engine components
use crate::transport::{Transport, TransportState};
use crate::session::{SessionView, ClipState};
use crate::mixer::Mixer;

/// Opaque handle to the Rust engine instance
pub struct EngineHandle {
    transport: Arc<Mutex<Transport>>,
    session: Arc<Mutex<SessionView>>,
    mixer: Arc<Mutex<Mixer>>,
}

/// Initialize the audio engine
///
/// # Safety
/// This function is unsafe because it deals with raw pointers and FFI boundaries.
/// The caller must ensure valid parameters and proper synchronization.
#[no_mangle]
pub extern "C" fn opendaw_engine_init(sample_rate: c_int, _buffer_size: c_int) -> *mut c_void {
    let handle = Box::new(EngineHandle {
        transport: Arc::new(Mutex::new(Transport::new(120.0, sample_rate as u32))),
        session: Arc::new(Mutex::new(SessionView::new(8, 16))), // 8 tracks, 16 scenes
        mixer: Arc::new(Mutex::new(Mixer::new(8))), // 8 tracks
    });

    Box::into_raw(handle) as *mut c_void
}

/// Shutdown and free the audio engine
///
/// # Safety
/// The engine_ptr must be a valid pointer returned by opendaw_engine_init.
/// After this call, the pointer is invalid and must not be used.
#[no_mangle]
pub extern "C" fn opendaw_engine_shutdown(engine_ptr: *mut c_void) {
    if engine_ptr.is_null() {
        return;
    }

    unsafe {
        let _ = Box::from_raw(engine_ptr as *mut EngineHandle);
        // Box will be dropped here, cleaning up the engine
    }
}

// ============================================================================
// Transport Controls
// ============================================================================

/// Start playback
#[no_mangle]
pub extern "C" fn opendaw_transport_play(engine_ptr: *mut c_void) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut transport) = handle.transport.lock() {
        transport.play();
    }
}

/// Stop playback
#[no_mangle]
pub extern "C" fn opendaw_transport_stop(engine_ptr: *mut c_void) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut transport) = handle.transport.lock() {
        transport.stop();
    }
}

/// Start recording
#[no_mangle]
pub extern "C" fn opendaw_transport_record(engine_ptr: *mut c_void) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut transport) = handle.transport.lock() {
        transport.record();
    }
}

/// Set playback position in beats
#[no_mangle]
pub extern "C" fn opendaw_transport_set_position(engine_ptr: *mut c_void, beats: c_double) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut transport) = handle.transport.lock() {
        transport.set_position(beats as f32);
    }
}

/// Get current playback position in beats
#[no_mangle]
pub extern "C" fn opendaw_transport_get_position(engine_ptr: *mut c_void) -> c_double {
    if engine_ptr.is_null() {
        return 0.0;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(transport) = handle.transport.lock() {
        transport.position_beats() as c_double
    } else {
        0.0
    }
}

/// Set tempo in BPM
#[no_mangle]
pub extern "C" fn opendaw_transport_set_bpm(engine_ptr: *mut c_void, bpm: c_float) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut transport) = handle.transport.lock() {
        transport.set_tempo(bpm);
    }
}

/// Get current tempo in BPM
#[no_mangle]
pub extern "C" fn opendaw_transport_get_bpm(engine_ptr: *mut c_void) -> c_float {
    if engine_ptr.is_null() {
        return 120.0;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(transport) = handle.transport.lock() {
        transport.tempo()
    } else {
        120.0
    }
}

/// Check if transport is playing
#[no_mangle]
pub extern "C" fn opendaw_transport_is_playing(engine_ptr: *mut c_void) -> c_int {
    if engine_ptr.is_null() {
        return 0;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(transport) = handle.transport.lock() {
        if transport.state() == TransportState::Playing { 1 } else { 0 }
    } else {
        0
    }
}

/// Check if transport is recording
#[no_mangle]
pub extern "C" fn opendaw_transport_is_recording(engine_ptr: *mut c_void) -> c_int {
    if engine_ptr.is_null() {
        return 0;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(transport) = handle.transport.lock() {
        if transport.state() == TransportState::Recording { 1 } else { 0 }
    } else {
        0
    }
}

// ============================================================================
// Clip / Session View Controls
// ============================================================================

/// Launch all clips in a scene
#[no_mangle]
pub extern "C" fn opendaw_scene_launch(engine_ptr: *mut c_void, scene: c_int) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut session) = handle.session.lock() {
        session.launch_scene(scene as usize);
    }
}

/// Stop all clips
#[no_mangle]
pub extern "C" fn opendaw_stop_all_clips(engine_ptr: *mut c_void) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut session) = handle.session.lock() {
        session.stop_all();
    }
}

/// Get current scene index (-1 if none)
#[no_mangle]
pub extern "C" fn opendaw_session_get_current_scene(engine_ptr: *mut c_void) -> c_int {
    if engine_ptr.is_null() {
        return -1;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(session) = handle.session.lock() {
        session.current_scene().map(|s| s as c_int).unwrap_or(-1)
    } else {
        -1
    }
}

/// Get clip state at track/scene (0 = stopped, 1 = playing, 2 = recording, -1 = no clip)
#[no_mangle]
pub extern "C" fn opendaw_clip_get_state(engine_ptr: *mut c_void, track: c_int, scene: c_int) -> c_int {
    if engine_ptr.is_null() {
        return -1;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(session) = handle.session.lock() {
        if let Some(clip) = session.get_clip(track as usize, scene as usize) {
            match clip.state() {
                ClipState::Stopped => 0,
                ClipState::Playing => 1,
                ClipState::Recording => 2,
                ClipState::Queued => 3,
            }
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Play a specific clip
#[no_mangle]
pub extern "C" fn opendaw_clip_play(engine_ptr: *mut c_void, _track: c_int, scene: c_int) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut session) = handle.session.lock() {
        // Note: SessionView doesn't have direct clip play method per track/scene
        // This would need to be implemented or use scene launch
        // For now, launch the scene containing this clip
        session.launch_scene(scene as usize);
    }
}

/// Stop a specific clip
#[no_mangle]
pub extern "C" fn opendaw_clip_stop(engine_ptr: *mut c_void, _track: c_int, _scene: c_int) {
    if engine_ptr.is_null() {
        return;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mut session) = handle.session.lock() {
        // Note: SessionView doesn't have direct clip stop method per track/scene
        // This would need to be implemented
        // For now, stop all clips
        session.stop_all();
    }
}

// ============================================================================
// Mixer Controls
// ============================================================================

/// Get meter level for a track (dB, typically -60.0 to 0.0)
/// track = -1 for master bus (not implemented, returns 0.0)
#[no_mangle]
pub extern "C" fn opendaw_mixer_get_meter(engine_ptr: *mut c_void, track: c_int) -> c_float {
    if engine_ptr.is_null() || track < 0 {
        return -60.0;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mixer) = handle.mixer.lock() {
        mixer.track_peak_db(track as usize)
    } else {
        -60.0
    }
}

/// Get track count
#[no_mangle]
pub extern "C" fn opendaw_mixer_get_track_count(engine_ptr: *mut c_void) -> c_int {
    if engine_ptr.is_null() {
        return 0;
    }

    let handle = unsafe { &*(engine_ptr as *const EngineHandle) };
    if let Ok(mixer) = handle.mixer.lock() {
        mixer.source_count() as c_int
    } else {
        0
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_lifecycle() {
        let engine = opendaw_engine_init(48000, 512);
        assert!(!engine.is_null());

        opendaw_engine_shutdown(engine);
        // After shutdown, engine pointer is invalid (freed)
    }

    #[test]
    fn test_transport_controls() {
        let engine = opendaw_engine_init(48000, 512);
        assert!(!engine.is_null());

        // Initially not playing
        assert_eq!(opendaw_transport_is_playing(engine), 0);

        // Play
        opendaw_transport_play(engine);
        assert_eq!(opendaw_transport_is_playing(engine), 1);

        // Stop
        opendaw_transport_stop(engine);
        assert_eq!(opendaw_transport_is_playing(engine), 0);

        // Record
        opendaw_transport_record(engine);
        assert_eq!(opendaw_transport_is_recording(engine), 1);

        opendaw_engine_shutdown(engine);
    }

    #[test]
    fn test_tempo() {
        let engine = opendaw_engine_init(48000, 512);

        // Default tempo should be 120 BPM
        let default_bpm = opendaw_transport_get_bpm(engine);
        assert!((default_bpm - 120.0).abs() < 0.01);

        // Set new tempo
        opendaw_transport_set_bpm(engine, 140.0);
        let new_bpm = opendaw_transport_get_bpm(engine);
        assert!((new_bpm - 140.0).abs() < 0.01);

        opendaw_engine_shutdown(engine);
    }

    #[test]
    fn test_position() {
        let engine = opendaw_engine_init(48000, 512);

        // Initially at position 0
        assert_eq!(opendaw_transport_get_position(engine), 0.0);

        // Set position
        opendaw_transport_set_position(engine, 16.0);
        assert_eq!(opendaw_transport_get_position(engine), 16.0);

        opendaw_engine_shutdown(engine);
    }

    #[test]
    fn test_session_controls() {
        let engine = opendaw_engine_init(48000, 512);

        // Initially no current scene
        assert_eq!(opendaw_session_get_current_scene(engine), -1);

        // Launch scene 0
        opendaw_scene_launch(engine, 0);
        assert_eq!(opendaw_session_get_current_scene(engine), 0);

        // Launch scene 1
        opendaw_scene_launch(engine, 1);
        assert_eq!(opendaw_session_get_current_scene(engine), 1);

        // Stop all
        opendaw_stop_all_clips(engine);
        // Current scene may still be set after stop_all

        opendaw_engine_shutdown(engine);
    }

    #[test]
    fn test_null_safety() {
        // All functions should handle null engine gracefully
        opendaw_transport_play(std::ptr::null_mut());
        opendaw_transport_stop(std::ptr::null_mut());
        opendaw_transport_set_bpm(std::ptr::null_mut(), 120.0);
        opendaw_scene_launch(std::ptr::null_mut(), 0);
        opendaw_stop_all_clips(std::ptr::null_mut());

        assert_eq!(opendaw_transport_is_playing(std::ptr::null_mut()), 0);
        assert_eq!(opendaw_transport_get_bpm(std::ptr::null_mut()), 120.0);
        assert_eq!(opendaw_mixer_get_meter(std::ptr::null_mut(), 0), -60.0);
        assert_eq!(opendaw_session_get_current_scene(std::ptr::null_mut()), -1);
    }
}
