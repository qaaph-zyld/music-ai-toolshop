//! Transport Sync FFI - C interface for transport synchronization
//!
//! Provides FFI exports to allow audio thread to process scheduled clips
//! with sample-accurate timing from the transport sync manager.

use std::ffi::c_void;
use std::os::raw::{c_double, c_float, c_int};

use crate::transport_sync::{TransportSync, Quantization, QuantizeDirection};

/// Opaque handle to the transport sync instance
pub struct TransportSyncHandle {
    sync: TransportSync,
}

/// Quantization levels for FFI
#[repr(C)]
pub enum FFITransportQuantization {
    Immediate = 0,
    Beat = 1,
    Bar = 2,
    Eighth = 3,
    Sixteenth = 4,
}

impl From<FFITransportQuantization> for Quantization {
    fn from(q: FFITransportQuantization) -> Self {
        match q {
            FFITransportQuantization::Immediate => Quantization::Immediate,
            FFITransportQuantization::Beat => Quantization::Beat,
            FFITransportQuantization::Bar => Quantization::Bar,
            FFITransportQuantization::Eighth => Quantization::Eighth,
            FFITransportQuantization::Sixteenth => Quantization::Sixteenth,
        }
    }
}

/// Initialize transport sync manager
///
/// # Safety
/// Returns an opaque pointer that must be passed to other transport_sync_ffi functions.
/// Must be freed with opendaw_transport_sync_shutdown.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_init(
    sample_rate: c_float,
    tempo: c_float,
) -> *mut c_void {
    let handle = Box::new(TransportSyncHandle {
        sync: TransportSync::new(sample_rate, tempo),
    });
    Box::into_raw(handle) as *mut c_void
}

/// Shutdown and free the transport sync
///
/// # Safety
/// handle_ptr must be a valid pointer returned by opendaw_transport_sync_init.
/// After this call, the pointer is invalid.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_shutdown(handle_ptr: *mut c_void) {
    if handle_ptr.is_null() {
        return;
    }
    let _ = Box::from_raw(handle_ptr as *mut TransportSyncHandle);
}

/// Update tempo (BPM)
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_set_tempo(
    handle_ptr: *mut c_void,
    tempo: c_float,
) {
    if handle_ptr.is_null() {
        return;
    }
    let handle = &mut *(handle_ptr as *mut TransportSyncHandle);
    handle.sync.set_tempo(tempo);
}

/// Get current tempo
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_get_tempo(handle_ptr: *mut c_void) -> c_float {
    if handle_ptr.is_null() {
        return 120.0;
    }
    let handle = &*(handle_ptr as *const TransportSyncHandle);
    handle.sync.tempo()
}

/// Schedule a clip to trigger at a specific beat
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_schedule_clip(
    handle_ptr: *mut c_void,
    track_idx: usize,
    clip_idx: usize,
    target_beat: c_double,
    looped: c_int,
) -> c_int {
    if handle_ptr.is_null() {
        return -1;
    }
    let handle = &mut *(handle_ptr as *mut TransportSyncHandle);
    handle.sync.schedule_clip(track_idx, clip_idx, target_beat, looped != 0);
    0
}

/// Schedule a clip with quantization applied to current beat
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_schedule_clip_quantized(
    handle_ptr: *mut c_void,
    track_idx: usize,
    clip_idx: usize,
    current_beat: c_double,
    quantization: FFITransportQuantization,
    looped: c_int,
) -> c_double {
    if handle_ptr.is_null() {
        return -1.0;
    }
    let handle = &mut *(handle_ptr as *mut TransportSyncHandle);
    let quant: Quantization = quantization.into();
    let target = quant.quantize(current_beat, QuantizeDirection::Up);
    handle.sync.schedule_clip(track_idx, clip_idx, target, looped != 0);
    target
}

/// Process scheduled clips at current beat position
/// Returns number of clips that triggered
///
/// # Safety
/// handle_ptr must be a valid pointer.
/// triggered_clips_out must be a valid pointer to write triggered clips (max 64).
/// Each clip is 4 doubles: track_idx, clip_idx, target_beat, looped
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_process(
    handle_ptr: *mut c_void,
    current_beat: c_double,
    triggered_clips_out: *mut c_double,
    max_clips: usize,
) -> c_int {
    if handle_ptr.is_null() || triggered_clips_out.is_null() {
        return -1;
    }
    let handle = &mut *(handle_ptr as *mut TransportSyncHandle);
    let triggered = handle.sync.process(current_beat);

    let count = triggered.len().min(max_clips);
    for (i, clip) in triggered.iter().take(count).enumerate() {
        let base = i * 4;
        *triggered_clips_out.add(base) = clip.track_idx as c_double;
        *triggered_clips_out.add(base + 1) = clip.clip_idx as c_double;
        *triggered_clips_out.add(base + 2) = clip.target_beat;
        *triggered_clips_out.add(base + 3) = if clip.looped { 1.0 } else { 0.0 };
    }
    count as c_int
}

/// Cancel all pending clips for a track
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_cancel_track(
    handle_ptr: *mut c_void,
    track_idx: usize,
) {
    if handle_ptr.is_null() {
        return;
    }
    let handle = &mut *(handle_ptr as *mut TransportSyncHandle);
    handle.sync.cancel_track(track_idx);
}

/// Cancel a specific scheduled clip
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_cancel_clip(
    handle_ptr: *mut c_void,
    track_idx: usize,
    clip_idx: usize,
) {
    if handle_ptr.is_null() {
        return;
    }
    let handle = &mut *(handle_ptr as *mut TransportSyncHandle);
    handle.sync.cancel_clip(track_idx, clip_idx);
}

/// Clear all pending scheduled clips
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_clear_all(handle_ptr: *mut c_void) {
    if handle_ptr.is_null() {
        return;
    }
    let handle = &mut *(handle_ptr as *mut TransportSyncHandle);
    handle.sync.clear_all();
}

/// Get number of pending scheduled clips
///
/// # Safety
/// handle_ptr must be a valid pointer.
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_pending_count(handle_ptr: *mut c_void) -> c_int {
    if handle_ptr.is_null() {
        return 0;
    }
    let handle = &*(handle_ptr as *const TransportSyncHandle);
    handle.sync.pending_count() as c_int
}

/// Check if any clip is scheduled for a track
///
/// # Safety
/// handle_ptr must be a valid pointer.
/// Returns: 1 if scheduled, 0 if not, -1 on error
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_is_track_scheduled(
    handle_ptr: *mut c_void,
    track_idx: usize,
) -> c_int {
    if handle_ptr.is_null() {
        return -1;
    }
    let handle = &*(handle_ptr as *const TransportSyncHandle);
    if handle.sync.is_track_scheduled(track_idx) {
        1
    } else {
        0
    }
}

/// Get next scheduled beat for a track
///
/// # Safety
/// handle_ptr must be a valid pointer.
/// Returns beat position, or -1.0 if none scheduled
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_next_scheduled_beat(
    handle_ptr: *mut c_void,
    track_idx: usize,
) -> c_double {
    if handle_ptr.is_null() {
        return -1.0;
    }
    let handle = &*(handle_ptr as *const TransportSyncHandle);
    handle.sync.next_scheduled_beat(track_idx).unwrap_or(-1.0)
}

/// Get beats until next scheduled event for a track
///
/// # Safety
/// handle_ptr must be a valid pointer.
/// Returns beats until next event, or -1.0 if none scheduled
#[no_mangle]
pub unsafe extern "C" fn opendaw_transport_sync_beats_until_next(
    handle_ptr: *mut c_void,
    track_idx: usize,
    current_beat: c_double,
) -> c_double {
    if handle_ptr.is_null() {
        return -1.0;
    }
    let handle = &*(handle_ptr as *const TransportSyncHandle);
    handle.sync.beats_until_next(track_idx, current_beat).unwrap_or(-1.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffi_sync_init() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);
            assert!(!sync.is_null());

            // Check initial tempo
            let tempo = opendaw_transport_sync_get_tempo(sync);
            assert!((tempo - 120.0).abs() < 0.01);

            opendaw_transport_sync_shutdown(sync);
        }
    }

    #[test]
    fn test_ffi_sync_tempo_change() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);
            assert_eq!(opendaw_transport_sync_get_tempo(sync), 120.0);

            opendaw_transport_sync_set_tempo(sync, 140.0);
            let new_tempo = opendaw_transport_sync_get_tempo(sync);
            assert!((new_tempo - 140.0).abs() < 0.01);

            opendaw_transport_sync_shutdown(sync);
        }
    }

    #[test]
    fn test_ffi_sync_schedule_clip() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 0);

            // Schedule a clip
            let result = opendaw_transport_sync_schedule_clip(sync, 0, 2, 4.0, 0);
            assert_eq!(result, 0);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 1);

            opendaw_transport_sync_shutdown(sync);
        }
    }

    #[test]
    fn test_ffi_sync_process_triggers() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);

            // Schedule a clip at beat 4
            opendaw_transport_sync_schedule_clip(sync, 0, 2, 4.0, 0);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 1);

            // Process at beat 3 - should not trigger yet
            let mut buffer = [0.0; 256]; // 64 clips * 4 values each
            let count1 = opendaw_transport_sync_process(sync, 3.0, buffer.as_mut_ptr(), 64);
            assert_eq!(count1, 0);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 1);

            // Process at beat 4 - should trigger
            let count2 = opendaw_transport_sync_process(sync, 4.0, buffer.as_mut_ptr(), 64);
            assert_eq!(count2, 1);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 0);

            // Check triggered clip data
            assert_eq!(buffer[0] as usize, 0); // track_idx
            assert_eq!(buffer[1] as usize, 2); // clip_idx
            assert_eq!(buffer[2], 4.0); // target_beat

            opendaw_transport_sync_shutdown(sync);
        }
    }

    #[test]
    fn test_ffi_sync_cancel_operations() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);

            // Schedule multiple clips
            opendaw_transport_sync_schedule_clip(sync, 0, 0, 1.0, 0);
            opendaw_transport_sync_schedule_clip(sync, 0, 1, 2.0, 0);
            opendaw_transport_sync_schedule_clip(sync, 1, 0, 3.0, 0);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 3);

            // Cancel track 0
            opendaw_transport_sync_cancel_track(sync, 0);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 1);

            // Clear all
            opendaw_transport_sync_clear_all(sync);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 0);

            opendaw_transport_sync_shutdown(sync);
        }
    }

    #[test]
    fn test_ffi_sync_scheduled_queries() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);

            // No clips scheduled initially
            assert_eq!(opendaw_transport_sync_is_track_scheduled(sync, 0), 0);
            assert_eq!(opendaw_transport_sync_next_scheduled_beat(sync, 0), -1.0);

            // Schedule clip at beat 8
            opendaw_transport_sync_schedule_clip(sync, 0, 3, 8.0, 0);

            // Check queries
            assert_eq!(opendaw_transport_sync_is_track_scheduled(sync, 0), 1);
            assert_eq!(opendaw_transport_sync_next_scheduled_beat(sync, 0), 8.0);

            // Check beats until next
            let beats_until = opendaw_transport_sync_beats_until_next(sync, 0, 5.0);
            assert_eq!(beats_until, 3.0); // 8 - 5 = 3

            opendaw_transport_sync_shutdown(sync);
        }
    }

    #[test]
    fn test_ffi_sync_schedule_quantized() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);

            // Current beat at 1.5, quantize to next beat
            let target = opendaw_transport_sync_schedule_clip_quantized(
                sync,
                0,
                0,
                1.5,
                FFITransportQuantization::Beat,
                0,
            );
            assert_eq!(target, 2.0); // Should round up to beat 2

            // Current beat at 3.0, quantize to next bar
            let target2 = opendaw_transport_sync_schedule_clip_quantized(
                sync,
                1,
                0,
                3.0,
                FFITransportQuantization::Bar,
                0,
            );
            assert_eq!(target2, 4.0); // Should round up to bar 4

            opendaw_transport_sync_shutdown(sync);
        }
    }

    #[test]
    fn test_ffi_sync_null_safety() {
        unsafe {
            // All functions should handle null gracefully
            assert_eq!(opendaw_transport_sync_get_tempo(std::ptr::null_mut()), 120.0);
            assert_eq!(opendaw_transport_sync_pending_count(std::ptr::null_mut()), 0);
            assert_eq!(opendaw_transport_sync_is_track_scheduled(std::ptr::null_mut(), 0), -1);
            assert_eq!(opendaw_transport_sync_next_scheduled_beat(std::ptr::null_mut(), 0), -1.0);

            // These should not crash
            opendaw_transport_sync_set_tempo(std::ptr::null_mut(), 120.0);
            opendaw_transport_sync_clear_all(std::ptr::null_mut());
            opendaw_transport_sync_cancel_track(std::ptr::null_mut(), 0);
            opendaw_transport_sync_shutdown(std::ptr::null_mut());
        }
    }

    #[test]
    fn test_ffi_sync_multiple_tracks() {
        unsafe {
            let sync = opendaw_transport_sync_init(48000.0, 120.0);

            // Schedule clips on multiple tracks
            for track in 0..8 {
                for clip in 0..4 {
                    let beat = (track * 4 + clip) as f64;
                    opendaw_transport_sync_schedule_clip(sync, track, clip, beat, 0);
                }
            }
            assert_eq!(opendaw_transport_sync_pending_count(sync), 32);

            // Check each track is scheduled
            for track in 0..8 {
                assert_eq!(opendaw_transport_sync_is_track_scheduled(sync, track), 1);
            }

            // Process all at once
            let mut buffer = [0.0; 256];
            let count = opendaw_transport_sync_process(sync, 100.0, buffer.as_mut_ptr(), 64);
            assert_eq!(count, 32);
            assert_eq!(opendaw_transport_sync_pending_count(sync), 0);

            opendaw_transport_sync_shutdown(sync);
        }
    }
}
