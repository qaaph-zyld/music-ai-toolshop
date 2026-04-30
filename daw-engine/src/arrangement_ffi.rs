//! Arrangement FFI Layer
//!
//! C-compatible exports for the Arrangement View, enabling C++ JUCE UI
//! to interact with the Rust arrangement timeline.

use std::ffi::{c_char, c_double, c_uint, CStr, CString};
use std::sync::Mutex;
use once_cell::sync::Lazy;
use crate::arrangement::{Arrangement, ArrangementClip, ArrangementClipId};
use crate::session::Clip;
use crate::error::DAWError;

/// Global arrangement state (singleton for FFI)
static ARRANGEMENT: Lazy<Mutex<Arrangement>> = Lazy::new(|| {
    Mutex::new(Arrangement::new(16)) // Default 16 tracks
});

/// Opaque handle for arrangement clip info
#[repr(C)]
pub struct ArrangementClipInfo {
    pub id: u64,
    pub track_index: u32,
    pub start_beat: c_double,
    pub duration_beats: c_double,
    pub name: *const c_char,
    pub is_audio: i32,
}

/// Initialize arrangement with specified track count
#[no_mangle]
pub extern "C" fn daw_arrangement_init(track_count: c_uint) {
    let mut arr = ARRANGEMENT.lock().unwrap();
    *arr = Arrangement::new(track_count as usize);
}

/// Reset arrangement to empty state
#[no_mangle]
pub extern "C" fn daw_arrangement_reset() {
    let mut arr = ARRANGEMENT.lock().unwrap();
    arr.clear();
}

/// Get total track count
#[no_mangle]
pub extern "C" fn daw_arrangement_track_count() -> c_uint {
    let arr = ARRANGEMENT.lock().unwrap();
    arr.max_tracks as c_uint
}

/// Add a MIDI clip to arrangement
#[no_mangle]
pub extern "C" fn daw_arrangement_add_midi_clip(
    track_idx: c_uint,
    start_beat: c_double,
    name: *const c_char,
    duration_bars: c_double,
) -> u64 {
    if name.is_null() {
        return 0;
    }
    
    let name_str = unsafe { CStr::from_ptr(name) }
        .to_string_lossy()
        .to_string();
    
    let clip = Clip::new_midi(&name_str, duration_bars as f32);
    
    let mut arr = ARRANGEMENT.lock().unwrap();
    match arr.add_clip(track_idx as usize, start_beat, clip) {
        Ok(id) => id,
        Err(_) => 0,
    }
}

/// Add an audio clip to arrangement
#[no_mangle]
pub extern "C" fn daw_arrangement_add_audio_clip(
    track_idx: c_uint,
    start_beat: c_double,
    name: *const c_char,
    duration_bars: c_double,
    file_path: *const c_char,
) -> u64 {
    if name.is_null() || file_path.is_null() {
        return 0;
    }
    
    let name_str = unsafe { CStr::from_ptr(name) }
        .to_string_lossy()
        .to_string();
    
    let file_str = unsafe { CStr::from_ptr(file_path) }
        .to_string_lossy()
        .to_string();
    
    let clip = Clip::new_audio(&name_str, duration_bars as f32);
    
    let mut arr = ARRANGEMENT.lock().unwrap();
    match arr.add_clip(track_idx as usize, start_beat, clip) {
        Ok(id) => id,
        Err(_) => 0,
    }
}

/// Remove a clip from arrangement
#[no_mangle]
pub extern "C" fn daw_arrangement_remove_clip(track_idx: c_uint, clip_id: u64) -> i32 {
    let mut arr = ARRANGEMENT.lock().unwrap();
    match arr.remove_clip(track_idx as usize, clip_id) {
        Ok(_) => 0,
        Err(_) => -1,
    }
}

/// Move clip to new track and/or position
#[no_mangle]
pub extern "C" fn daw_arrangement_move_clip(
    from_track: c_uint,
    clip_id: u64,
    to_track: c_uint,
    new_start: c_double,
) -> i32 {
    let mut arr = ARRANGEMENT.lock().unwrap();
    match arr.move_clip(from_track as usize, clip_id, to_track as usize, new_start) {
        Ok(_) => 0,
        Err(_) => -1,
    }
}

/// Resize a clip
#[no_mangle]
pub extern "C" fn daw_arrangement_resize_clip(
    track_idx: c_uint,
    clip_id: u64,
    new_duration: c_double,
) -> i32 {
    let mut arr = ARRANGEMENT.lock().unwrap();
    match arr.resize_clip(track_idx as usize, clip_id, new_duration) {
        Ok(_) => 0,
        Err(_) => -1,
    }
}

/// Get clip count on a track
#[no_mangle]
pub extern "C" fn daw_arrangement_clip_count(track_idx: c_uint) -> c_uint {
    let arr = ARRANGEMENT.lock().unwrap();
    match arr.clips_on_track(track_idx as usize) {
        Ok(clips) => clips.len() as c_uint,
        Err(_) => 0,
    }
}

/// Get total clip count across all tracks
#[no_mangle]
pub extern "C" fn daw_arrangement_total_clip_count() -> c_uint {
    let arr = ARRANGEMENT.lock().unwrap();
    arr.total_clip_count() as c_uint
}

/// Get clip info at index on a track
#[no_mangle]
pub extern "C" fn daw_arrangement_get_clip_at(
    track_idx: c_uint,
    index: c_uint,
    out_info: *mut ArrangementClipInfo,
) -> i32 {
    if out_info.is_null() {
        return -1;
    }
    
    let arr = ARRANGEMENT.lock().unwrap();
    
    match arr.clips_on_track(track_idx as usize) {
        Ok(clips) => {
            if index as usize >= clips.len() {
                return -1;
            }
            
            let clip = clips[index as usize];
            let name_cstring = CString::new(clip.name()).unwrap_or_default();
            
            unsafe {
                (*out_info).id = clip.id;
                (*out_info).track_index = clip.track_index as u32;
                (*out_info).start_beat = clip.start_beat;
                (*out_info).duration_beats = clip.duration_beats;
                (*out_info).name = CString::into_raw(name_cstring);
                (*out_info).is_audio = if clip.is_audio() { 1 } else { 0 };
            }
            
            0
        }
        Err(_) => -1,
    }
}

/// Get clip info by ID
#[no_mangle]
pub extern "C" fn daw_arrangement_get_clip_by_id(
    track_idx: c_uint,
    clip_id: u64,
    out_info: *mut ArrangementClipInfo,
) -> i32 {
    if out_info.is_null() {
        return -1;
    }
    
    let arr = ARRANGEMENT.lock().unwrap();
    
    match arr.get_clip(track_idx as usize, clip_id) {
        Ok(clip) => {
            let name_cstring = CString::new(clip.name()).unwrap_or_default();
            
            unsafe {
                (*out_info).id = clip.id;
                (*out_info).track_index = clip.track_index as u32;
                (*out_info).start_beat = clip.start_beat;
                (*out_info).duration_beats = clip.duration_beats;
                (*out_info).name = CString::into_raw(name_cstring);
                (*out_info).is_audio = if clip.is_audio() { 1 } else { 0 };
            }
            
            0
        }
        Err(_) => -1,
    }
}

/// Free clip info name string
#[no_mangle]
pub extern "C" fn daw_arrangement_free_clip_info(info: *mut ArrangementClipInfo) {
    if info.is_null() {
        return;
    }
    
    unsafe {
        if !(*info).name.is_null() {
            let _ = CString::from_raw((*info).name as *mut c_char);
        }
    }
}

/// Get total arrangement duration (end of last clip)
#[no_mangle]
pub extern "C" fn daw_arrangement_total_duration() -> c_double {
    let arr = ARRANGEMENT.lock().unwrap();
    arr.total_duration()
}

/// Check if a clip can be moved to a position
#[no_mangle]
pub extern "C" fn daw_arrangement_can_move_to(
    track_idx: c_uint,
    clip_id: u64,
    new_start: c_double,
    duration: c_double,
) -> i32 {
    let arr = ARRANGEMENT.lock().unwrap();
    if arr.can_move_to(track_idx as usize, clip_id, new_start, duration) {
        1
    } else {
        0
    }
}

/// Find clips in a beat range on a track
#[no_mangle]
pub extern "C" fn daw_arrangement_clips_in_range(
    track_idx: c_uint,
    start_beat: c_double,
    end_beat: c_double,
    out_ids: *mut u64,
    max_count: c_uint,
) -> c_uint {
    if out_ids.is_null() {
        return 0;
    }
    
    let arr = ARRANGEMENT.lock().unwrap();
    
    match arr.clips_in_range(track_idx as usize, start_beat, end_beat) {
        Ok(clips) => {
            let count = clips.len().min(max_count as usize);
            unsafe {
                for i in 0..count {
                    *out_ids.add(i) = clips[i].id;
                }
            }
            count as c_uint
        }
        Err(_) => 0,
    }
}

/// Find clip at a specific beat position on a track
#[no_mangle]
pub extern "C" fn daw_arrangement_clip_at_beat(
    track_idx: c_uint,
    beat: c_double,
) -> u64 {
    let arr = ARRANGEMENT.lock().unwrap();
    
    if track_idx as usize >= arr.max_tracks {
        return 0;
    }
    
    match arr.tracks[track_idx as usize].clip_at_beat(beat) {
        Some(clip) => clip.id,
        None => 0,
    }
}

/// Get clips playing at a beat position across all tracks
#[no_mangle]
pub extern "C" fn daw_arrangement_active_clips(
    beat: c_double,
    out_ids: *mut u64,
    max_count: c_uint,
) -> c_uint {
    if out_ids.is_null() {
        return 0;
    }
    
    let arr = ARRANGEMENT.lock().unwrap();
    let clips = arr.active_clips_at_beat(beat);
    
    let count = clips.len().min(max_count as usize);
    unsafe {
        for i in 0..count {
            *out_ids.add(i) = clips[i].id;
        }
    }
    
    count as c_uint
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;
    
    // Static mutex to serialize tests that use global arrangement state
    static TEST_MUTEX: Mutex<()> = Mutex::new(());
    
    #[test]
    fn test_ffi_arrangement_init() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_init(8);
        assert_eq!(daw_arrangement_track_count(), 8);
    }
    
    #[test]
    fn test_ffi_add_midi_clip() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test MIDI").unwrap();
        let id = daw_arrangement_add_midi_clip(0, 0.0, name.as_ptr(), 1.0);
        
        assert!(id > 0);
        assert_eq!(daw_arrangement_total_clip_count(), 1);
    }
    
    #[test]
    fn test_ffi_add_audio_clip() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test Audio").unwrap();
        let path = CString::new("test.wav").unwrap();
        let id = daw_arrangement_add_audio_clip(0, 4.0, name.as_ptr(), 1.0, path.as_ptr());
        
        assert!(id > 0);
        assert_eq!(daw_arrangement_total_clip_count(), 1);
    }
    
    #[test]
    fn test_ffi_get_clip_info() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test Clip").unwrap();
        let id = daw_arrangement_add_midi_clip(0, 2.0, name.as_ptr(), 1.0);
        
        let mut info = ArrangementClipInfo {
            id: 0,
            track_index: 0,
            start_beat: 0.0,
            duration_beats: 0.0,
            name: std::ptr::null(),
            is_audio: 0,
        };
        
        let result = daw_arrangement_get_clip_by_id(0, id, &mut info);
        assert_eq!(result, 0);
        assert_eq!(info.id, id);
        assert_eq!(info.start_beat, 2.0);
        assert_eq!(info.duration_beats, 4.0); // 1 bar = 4 beats
        
        // Free the allocated name
        daw_arrangement_free_clip_info(&mut info);
    }
    
    #[test]
    fn test_ffi_move_clip() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test").unwrap();
        let id = daw_arrangement_add_midi_clip(0, 0.0, name.as_ptr(), 1.0);
        
        // Move to track 1, position 4.0
        let result = daw_arrangement_move_clip(0, id, 1, 4.0);
        assert_eq!(result, 0);
        
        // Verify clip moved
        let mut info = ArrangementClipInfo {
            id: 0,
            track_index: 0,
            start_beat: 0.0,
            duration_beats: 0.0,
            name: std::ptr::null(),
            is_audio: 0,
        };
        
        let result = daw_arrangement_get_clip_by_id(1, id, &mut info);
        assert_eq!(result, 0);
        assert_eq!(info.track_index, 1);
        assert_eq!(info.start_beat, 4.0);
        
        daw_arrangement_free_clip_info(&mut info);
    }
    
    #[test]
    fn test_ffi_remove_clip() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test").unwrap();
        let id = daw_arrangement_add_midi_clip(0, 0.0, name.as_ptr(), 1.0);
        
        assert_eq!(daw_arrangement_total_clip_count(), 1);
        
        let result = daw_arrangement_remove_clip(0, id);
        assert_eq!(result, 0);
        
        assert_eq!(daw_arrangement_total_clip_count(), 0);
    }
    
    #[test]
    fn test_ffi_resize_clip() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test").unwrap();
        let id = daw_arrangement_add_midi_clip(0, 0.0, name.as_ptr(), 1.0);
        
        // Resize to 8 beats (2 bars)
        let result = daw_arrangement_resize_clip(0, id, 8.0);
        assert_eq!(result, 0);
        
        let mut info = ArrangementClipInfo {
            id: 0,
            track_index: 0,
            start_beat: 0.0,
            duration_beats: 0.0,
            name: std::ptr::null(),
            is_audio: 0,
        };
        
        let result = daw_arrangement_get_clip_by_id(0, id, &mut info);
        assert_eq!(result, 0);
        assert_eq!(info.duration_beats, 8.0);
        
        daw_arrangement_free_clip_info(&mut info);
    }
    
    #[test]
    fn test_ffi_can_move_to() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test").unwrap();
        let id = daw_arrangement_add_midi_clip(0, 4.0, name.as_ptr(), 1.0); // 4-8
        
        // Can move to 0-4
        assert_eq!(daw_arrangement_can_move_to(0, id, 0.0, 4.0), 1);
        
        // Can move to 8-12
        assert_eq!(daw_arrangement_can_move_to(0, id, 8.0, 4.0), 1);
    }
    
    #[test]
    fn test_ffi_clips_in_range() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test").unwrap();
        let id1 = daw_arrangement_add_midi_clip(0, 0.0, name.as_ptr(), 1.0); // 0-4
        let _id2 = daw_arrangement_add_midi_clip(0, 4.0, name.as_ptr(), 1.0); // 4-8
        let _id3 = daw_arrangement_add_midi_clip(0, 8.0, name.as_ptr(), 1.0); // 8-12
        
        let mut ids: [u64; 10] = [0; 10];
        let count = daw_arrangement_clips_in_range(0, 2.0, 6.0, ids.as_mut_ptr(), 10);
        
        assert_eq!(count, 2); // First and second clips overlap 2-6
        assert_eq!(ids[0], id1);
    }
    
    #[test]
    fn test_ffi_clip_at_beat() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test").unwrap();
        let id = daw_arrangement_add_midi_clip(0, 4.0, name.as_ptr(), 1.0); // 4-8
        
        assert_eq!(daw_arrangement_clip_at_beat(0, 2.0), 0); // No clip
        assert_eq!(daw_arrangement_clip_at_beat(0, 6.0), id); // In clip
        assert_eq!(daw_arrangement_clip_at_beat(0, 10.0), 0); // No clip
    }
    
    #[test]
    fn test_ffi_total_duration() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        let name = CString::new("Test").unwrap();
        let _id = daw_arrangement_add_midi_clip(0, 0.0, name.as_ptr(), 1.0); // 0-4
        let _id = daw_arrangement_add_midi_clip(1, 8.0, name.as_ptr(), 1.0); // 8-12
        let _id = daw_arrangement_add_midi_clip(2, 16.0, name.as_ptr(), 1.0); // 16-20
        
        assert_eq!(daw_arrangement_total_duration(), 20.0);
    }
    
    #[test]
    fn test_ffi_null_safety() {
        let _guard = TEST_MUTEX.lock().unwrap();
        daw_arrangement_reset();
        daw_arrangement_init(8);
        
        // Test null name returns 0
        let id = daw_arrangement_add_midi_clip(0, 0.0, std::ptr::null(), 1.0);
        assert_eq!(id, 0);
        
        // Test null out_info returns -1
        let result = daw_arrangement_get_clip_by_id(0, 1, std::ptr::null_mut());
        assert_eq!(result, -1);
        
        // Test null out_ids returns 0
        let count = daw_arrangement_clips_in_range(0, 0.0, 10.0, std::ptr::null_mut(), 10);
        assert_eq!(count, 0);
    }
}
