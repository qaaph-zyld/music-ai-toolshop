//! FFI exports for Disk Streaming
//!
//! Provides C-compatible interface for streaming audio file playback

use crate::disk_streamer::{DiskStreamer, DiskStreamError, StreamingPlayer, load_file_to_ram};
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_int, c_void};
use std::path::Path;

/// Opaque handle for streaming player
pub struct StreamingPlayerHandle {
    player: StreamingPlayer,
}

/// Create a new streaming player for a file
/// 
/// # Safety
/// `path` must be a valid null-terminated UTF-8 string.
/// Returns opaque handle or null on error.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_open(path: *const c_char) -> *mut c_void {
    if path.is_null() {
        return std::ptr::null_mut();
    }
    
    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };
    
    match StreamingPlayer::start(Path::new(path_str)) {
        Ok(player) => {
            let handle = Box::new(StreamingPlayerHandle { player });
            Box::into_raw(handle) as *mut c_void
        }
        Err(_) => std::ptr::null_mut(),
    }
}

/// Close streaming player and free resources
/// 
/// # Safety
/// Handle must be valid and not already freed.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_close(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut StreamingPlayerHandle);
    }
}

/// Process audio - fill output buffer with samples
/// 
/// # Safety
/// `handle` must be valid. `output` must point to valid memory of `frames * channels` floats.
/// Returns number of frames written, or -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_process(
    handle: *mut c_void,
    output: *mut f32,
    frames: c_int,
) -> c_int {
    if handle.is_null() || output.is_null() || frames <= 0 {
        return -1;
    }
    
    let handle = &*(handle as *mut StreamingPlayerHandle);
    let output_slice = std::slice::from_raw_parts_mut(output, frames as usize * 2); // Assume stereo
    
    match handle.player.process(output_slice) {
        Ok(frames_written) => frames_written as c_int,
        Err(_) => -1,
    }
}

/// Check if player has reached end of file
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_is_eof(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }
    
    let handle = &*(handle as *mut StreamingPlayerHandle);
    if handle.player.is_eof() { 1 } else { 0 }
}

/// Get current playback position in seconds
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_get_position(handle: *mut c_void) -> c_double {
    if handle.is_null() {
        return 0.0;
    }
    
    let handle = &*(handle as *mut StreamingPlayerHandle);
    handle.player.position_seconds()
}

/// Get total duration in seconds
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_get_duration(handle: *mut c_void) -> c_double {
    if handle.is_null() {
        return 0.0;
    }
    
    let handle = &*(handle as *mut StreamingPlayerHandle);
    handle.player.duration_seconds()
}

/// Seek to position in seconds
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_seek(handle: *mut c_void, seconds: c_double) -> c_int {
    if handle.is_null() {
        return -1;
    }
    
    let handle = &mut *(handle as *mut StreamingPlayerHandle);
    match handle.player.seek_seconds(seconds) {
        Ok(_) => 0,
        Err(_) => -1,
    }
}

/// Get buffered time in seconds (how much audio is ready to play)
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_get_buffered(handle: *mut c_void) -> c_double {
    if handle.is_null() {
        return 0.0;
    }
    
    let handle = &*(handle as *mut StreamingPlayerHandle);
    handle.player.buffered_seconds()
}

/// Check if this file is using streaming (vs short file in RAM)
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_player_is_streaming(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }
    
    let handle = &*(handle as *mut StreamingPlayerHandle);
    if handle.player.is_streaming() { 1 } else { 0 }
}

/// Load a short file fully into RAM (non-streaming fallback)
/// 
/// # Safety
/// `path` must be valid null-terminated UTF-8 string.
/// `samples_out` receives pointer to allocated samples (caller must free with daw_streaming_free_samples).
/// `sample_count_out` receives number of samples.
/// `sample_rate_out` receives sample rate.
/// `channels_out` receives channel count.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_load_ram(
    path: *const c_char,
    samples_out: *mut *mut f32,
    sample_count_out: *mut c_int,
    sample_rate_out: *mut c_int,
    channels_out: *mut c_int,
) -> c_int {
    if path.is_null() || samples_out.is_null() || sample_count_out.is_null() {
        return -1;
    }
    
    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };
    
    match load_file_to_ram(Path::new(path_str)) {
        Ok((samples, spec)) => {
            let sample_count = samples.len();
            let boxed = samples.into_boxed_slice();
            let raw = Box::into_raw(boxed) as *mut f32;
            
            *samples_out = raw;
            *sample_count_out = sample_count as c_int;
            
            if !sample_rate_out.is_null() {
                *sample_rate_out = spec.sample_rate as c_int;
            }
            if !channels_out.is_null() {
                *channels_out = spec.channels as c_int;
            }
            
            0
        }
        Err(_) => -1,
    }
}

/// Free samples allocated by daw_streaming_load_ram
/// 
/// # Safety
/// `samples` must be a pointer returned by daw_streaming_load_ram.
#[no_mangle]
pub unsafe extern "C" fn daw_streaming_free_samples(samples: *mut f32, count: c_int) {
    if !samples.is_null() && count > 0 {
        let _ = Vec::from_raw_parts(samples, count as usize, count as usize);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use std::path::PathBuf;
    use tempfile::NamedTempFile;
    use hound::{WavWriter, WavSpec, SampleFormat};
    
    fn create_test_wav(duration_sec: f64, sample_rate: u32) -> (PathBuf, NamedTempFile) {
        let spec = WavSpec {
            channels: 2,
            sample_rate,
            bits_per_sample: 16,
            sample_format: SampleFormat::Int,
        };
        
        let mut temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path().to_path_buf();
        
        {
            let mut writer = WavWriter::create(&path, spec).unwrap();
            let num_samples = (duration_sec * sample_rate as f64) as usize * 2;
            
            for i in 0..num_samples {
                let t = i as f64 / sample_rate as f64;
                let sample = (t * 440.0 * 2.0 * std::f64::consts::PI).sin() as f32;
                let sample_i16 = (sample * 32767.0) as i16;
                writer.write_sample(sample_i16).unwrap();
            }
            
            writer.finalize().unwrap();
        }
        
        (path, temp_file)
    }
    
    #[test]
    fn test_ffi_lifecycle() {
        unsafe {
            let (path, _temp) = create_test_wav(60.0, 48000);
            let path_cstring = CString::new(path.to_str().unwrap()).unwrap();
            
            // Create player
            let handle = daw_streaming_player_open(path_cstring.as_ptr());
            assert!(!handle.is_null());
            
            // Check streaming flag
            assert_eq!(daw_streaming_player_is_streaming(handle), 1);
            
            // Check duration
            let duration = daw_streaming_player_get_duration(handle);
            println!("Duration: {}", duration);
            assert!(duration > 59.0 && duration < 61.0, "Expected duration ~60s, got {}", duration);
            
            // Process some audio
            let mut buffer = vec![0.0f32; 1024 * 2]; // 1024 frames, stereo
            let frames = daw_streaming_player_process(handle, buffer.as_mut_ptr(), 1024);
            assert!(frames >= 0);
            
            // Close player
            daw_streaming_player_close(handle);
        }
    }
    
    #[test]
    fn test_ffi_null_safety() {
        unsafe {
            // Null handle operations should not crash
            daw_streaming_player_close(std::ptr::null_mut());
            assert_eq!(daw_streaming_player_is_eof(std::ptr::null_mut()), 0);
            assert_eq!(daw_streaming_player_get_position(std::ptr::null_mut()), 0.0);
            assert_eq!(daw_streaming_player_get_duration(std::ptr::null_mut()), 0.0);
            assert_eq!(daw_streaming_player_is_streaming(std::ptr::null_mut()), 0);
            assert_eq!(daw_streaming_player_get_buffered(std::ptr::null_mut()), 0.0);
            
            // Null path should fail gracefully
            assert!(daw_streaming_player_open(std::ptr::null()).is_null());
            
            // Null output should fail
            let (path, _temp) = create_test_wav(1.0, 48000);
            let path_cstring = CString::new(path.to_str().unwrap()).unwrap();
            let handle = daw_streaming_player_open(path_cstring.as_ptr());
            
            if !handle.is_null() {
                assert_eq!(daw_streaming_player_process(handle, std::ptr::null_mut(), 256), -1);
                daw_streaming_player_close(handle);
            }
        }
    }
    
    #[test]
    fn test_ffi_seek() {
        unsafe {
            let (path, _temp) = create_test_wav(60.0, 48000);
            let path_cstring = CString::new(path.to_str().unwrap()).unwrap();
            
            let handle = daw_streaming_player_open(path_cstring.as_ptr());
            assert!(!handle.is_null());
            
            // Check duration first
            let duration = daw_streaming_player_get_duration(handle);
            println!("Duration before seek: {}", duration);
            
            // Seek to 30 seconds
            let seek_result = daw_streaming_player_seek(handle, 30.0);
            println!("Seek result: {}", seek_result);
            assert_eq!(seek_result, 0, "Seek failed");
            
            // Position should be near 30 seconds
            let pos = daw_streaming_player_get_position(handle);
            println!("Position after seek: {}", pos);
            assert!(pos >= 29.0 && pos <= 31.0, "Position {} not in expected range", pos);
            
            daw_streaming_player_close(handle);
        }
    }
    
    #[test]
    fn test_ffi_load_ram() {
        unsafe {
            let (path, _temp) = create_test_wav(0.5, 48000); // Short file
            let path_cstring = CString::new(path.to_str().unwrap()).unwrap();
            
            let mut samples: *mut f32 = std::ptr::null_mut();
            let mut count: c_int = 0;
            let mut sample_rate: c_int = 0;
            let mut channels: c_int = 0;
            
            let result = daw_streaming_load_ram(
                path_cstring.as_ptr(),
                &mut samples,
                &mut count,
                &mut sample_rate,
                &mut channels,
            );
            
            assert_eq!(result, 0);
            assert!(!samples.is_null());
            assert_eq!(count, (0.5 * 48000.0) as c_int * 2); // 0.5 sec * 48k * stereo
            assert_eq!(sample_rate, 48000);
            assert_eq!(channels, 2);
            
            // Free samples
            daw_streaming_free_samples(samples, count);
        }
    }
    
    #[test]
    fn test_ffi_load_ram_null_safety() {
        unsafe {
            assert_eq!(daw_streaming_load_ram(std::ptr::null(), std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null_mut()), -1);
        }
    }
}
