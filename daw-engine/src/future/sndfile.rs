//! Libsndfile Integration
//!
//! FFI bindings to libsndfile - the industry-standard unified API
//! for WAV, AIFF, FLAC, Ogg/Vorbis, Opus, and MP3.
//!
//! License: LGPL-2.1+
//! Repo: https://github.com/libsndfile/libsndfile

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_short, c_void};
use std::path::Path;

/// Opaque handle to SNDFILE
#[repr(C)]
pub struct SndFile {
    _private: [u8; 0],
}

/// Opaque handle to SF_INFO
#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct SndFileInfo {
    pub frames: i64,
    pub sample_rate: c_int,
    pub channels: c_int,
    pub format: c_int,
    pub sections: c_int,
    pub seekable: c_int,
}

/// Libsndfile error types
#[derive(Debug, Clone, PartialEq)]
pub enum SndFileError {
    OpenFailed(String),
    ReadFailed(String),
    WriteFailed(String),
    InvalidFormat(String),
    SeekFailed(String),
    FfiError(String),
}

impl std::fmt::Display for SndFileError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SndFileError::OpenFailed(path) => write!(f, "Failed to open file: {}", path),
            SndFileError::ReadFailed(msg) => write!(f, "Read failed: {}", msg),
            SndFileError::WriteFailed(msg) => write!(f, "Write failed: {}", msg),
            SndFileError::InvalidFormat(fmt) => write!(f, "Invalid format: {}", fmt),
            SndFileError::SeekFailed(msg) => write!(f, "Seek failed: {}", msg),
            SndFileError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for SndFileError {}

/// File format enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum FileFormat {
    WAV,
    AIFF,
    FLAC,
    OggVorbis,
    MP3,
    Raw,
}

/// Sample format enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SampleFormat {
    PCM16,
    PCM24,
    PCM32,
    Float32,
    Float64,
}

/// Audio file handle
pub struct AudioFile {
    file: *mut SndFile,
    info: SndFileInfo,
    path: String,
}

// FFI function declarations
extern "C" {
    fn sndfile_ffi_is_available() -> c_int;
    fn sndfile_ffi_get_version() -> *const c_char;
    
    // File operations
    fn sndfile_ffi_open(path: *const c_char, mode: c_int, info: *mut SndFileInfo) -> *mut SndFile;
    fn sndfile_ffi_close(file: *mut SndFile) -> c_int;
    
    // Read operations
    fn sndfile_ffi_read_short(file: *mut SndFile, ptr: *mut c_short, frames: i64) -> i64;
    fn sndfile_ffi_read_int(file: *mut SndFile, ptr: *mut c_int, frames: i64) -> i64;
    fn sndfile_ffi_read_float(file: *mut SndFile, ptr: *mut c_float, frames: i64) -> i64;
    
    // Write operations
    fn sndfile_ffi_write_short(file: *mut SndFile, ptr: *const c_short, frames: i64) -> i64;
    fn sndfile_ffi_write_float(file: *mut SndFile, ptr: *const c_float, frames: i64) -> i64;
    
    // Seek
    fn sndfile_ffi_seek(file: *mut SndFile, frames: i64, whence: c_int) -> i64;
    
    // Error handling
    fn sndfile_ffi_error(file: *mut SndFile) -> *const c_char;
    fn sndfile_ffi_strerror(file: *mut SndFile) -> *const c_char;
}

impl AudioFile {
    /// Open audio file for reading
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self, SndFileError> {
        if !Self::is_available() {
            return Err(SndFileError::FfiError("libsndfile not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy().to_string();
        let path_cstring = CString::new(path_str.clone())
            .map_err(|e| SndFileError::FfiError(e.to_string()))?;

        let mut info: SndFileInfo = Default::default();

        unsafe {
            let file = sndfile_ffi_open(path_cstring.as_ptr(), 0x10, &mut info); // SFM_READ = 0x10
            if file.is_null() {
                return Err(SndFileError::OpenFailed(path_str));
            }
            Ok(Self { file, info, path: path_str })
        }
    }

    /// Create new audio file for writing
    pub fn create<P: AsRef<Path>>(
        path: P,
        format: FileFormat,
        sample_rate: u32,
        channels: u16,
        sample_format: SampleFormat,
    ) -> Result<Self, SndFileError> {
        if !Self::is_available() {
            return Err(SndFileError::FfiError("libsndfile not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy().to_string();
        let path_cstring = CString::new(path_str.clone())
            .map_err(|e| SndFileError::FfiError(e.to_string()))?;

        let mut info: SndFileInfo = Default::default();
        info.sample_rate = sample_rate as c_int;
        info.channels = channels as c_int;
        // TODO: Set format based on format + sample_format
        info.format = 0x010000; // WAV

        unsafe {
            let file = sndfile_ffi_open(path_cstring.as_ptr(), 0x20, &mut info); // SFM_WRITE = 0x20
            if file.is_null() {
                return Err(SndFileError::OpenFailed(path_str));
            }
            Ok(Self { file, info, path: path_str })
        }
    }

    /// Check if libsndfile is available
    pub fn is_available() -> bool {
        unsafe { sndfile_ffi_is_available() != 0 }
    }

    /// Get libsndfile version
    pub fn version() -> String {
        unsafe {
            let version_ptr = sndfile_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get file info
    pub fn info(&self) -> &SndFileInfo {
        &self.info
    }

    /// Get number of frames
    pub fn frames(&self) -> i64 {
        self.info.frames
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.info.sample_rate as u32
    }

    /// Get channel count
    pub fn channels(&self) -> u16 {
        self.info.channels as u16
    }

    /// Get duration in seconds
    pub fn duration_seconds(&self) -> f64 {
        if self.info.sample_rate > 0 {
            self.info.frames as f64 / self.info.sample_rate as f64
        } else {
            0.0
        }
    }

    /// Read frames as f32
    pub fn read_f32(&mut self, buffer: &mut [f32]) -> Result<usize, SndFileError> {
        let frames_to_read = (buffer.len() / self.channels() as usize) as i64;
        
        unsafe {
            let frames_read = sndfile_ffi_read_float(self.file, buffer.as_mut_ptr(), frames_to_read);
            if frames_read < 0 {
                let error_ptr = sndfile_ffi_error(self.file);
                let error_msg = CStr::from_ptr(error_ptr)
                    .to_string_lossy()
                    .into_owned();
                return Err(SndFileError::ReadFailed(error_msg));
            }
            Ok(frames_read as usize * self.channels() as usize)
        }
    }

    /// Write frames as f32
    pub fn write_f32(&mut self, buffer: &[f32]) -> Result<usize, SndFileError> {
        let frames_to_write = (buffer.len() / self.channels() as usize) as i64;
        
        unsafe {
            let frames_written = sndfile_ffi_write_float(self.file, buffer.as_ptr(), frames_to_write);
            if frames_written < 0 {
                let error_ptr = sndfile_ffi_error(self.file);
                let error_msg = CStr::from_ptr(error_ptr)
                    .to_string_lossy()
                    .into_owned();
                return Err(SndFileError::WriteFailed(error_msg));
            }
            Ok(frames_written as usize * self.channels() as usize)
        }
    }

    /// Seek to frame position
    pub fn seek(&mut self, frame: i64) -> Result<(), SndFileError> {
        unsafe {
            let result = sndfile_ffi_seek(self.file, frame, 0); // SEEK_SET = 0
            if result < 0 {
                return Err(SndFileError::SeekFailed(format!("Failed to seek to frame {}", frame)));
            }
            Ok(())
        }
    }

    /// Get file path
    pub fn path(&self) -> &str {
        &self.path
    }
}

impl Drop for AudioFile {
    fn drop(&mut self) {
        unsafe {
            if !self.file.is_null() {
                sndfile_ffi_close(self.file);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_sndfile_module_exists() {
        let _ = SndFileError::OpenFailed("test".to_string());
        let _ = FileFormat::WAV;
        let _ = SampleFormat::PCM16;
    }

    #[test]
    fn test_sndfile_is_available() {
        let available = AudioFile::is_available();
        println!("libsndfile available: {}", available);
    }

    #[test]
    fn test_sndfile_version() {
        let version = AudioFile::version();
        println!("libsndfile version: {}", version);
    }

    #[test]
    fn test_sndfile_info_default() {
        let info: SndFileInfo = Default::default();
        assert_eq!(info.frames, 0);
        assert_eq!(info.sample_rate, 0);
        assert_eq!(info.channels, 0);
    }

    #[test]
    fn test_file_open_fails_gracefully() {
        let result = AudioFile::open("/nonexistent/path/test.wav");
        match result {
            Err(SndFileError::OpenFailed(_)) | Err(SndFileError::FfiError(_)) => {
                // Expected - file doesn't exist or library not available
            }
            _ => panic!("Expected OpenFailed or FfiError"),
        }
    }

    #[test]
    fn test_file_create_fails_gracefully() {
        let result = AudioFile::create(
            "/nonexistent/path/test.wav",
            FileFormat::WAV,
            44100,
            2,
            SampleFormat::Float32,
        );
        match result {
            Err(SndFileError::OpenFailed(_)) | Err(SndFileError::FfiError(_)) => {
                // Expected - path doesn't exist or library not available
            }
            _ => panic!("Expected OpenFailed or FfiError"),
        }
    }

    #[test]
    fn test_file_format_variants() {
        let formats = vec![
            FileFormat::WAV,
            FileFormat::AIFF,
            FileFormat::FLAC,
            FileFormat::OggVorbis,
            FileFormat::MP3,
            FileFormat::Raw,
        ];
        for f in formats {
            assert!(!format!("{:?}", f).is_empty());
        }
    }

    #[test]
    fn test_sample_format_variants() {
        let formats = vec![
            SampleFormat::PCM16,
            SampleFormat::PCM24,
            SampleFormat::PCM32,
            SampleFormat::Float32,
            SampleFormat::Float64,
        ];
        for f in formats {
            assert!(!format!("{:?}", f).is_empty());
        }
    }

    #[test]
    fn test_sndfile_error_display() {
        let err = SndFileError::OpenFailed("test.wav".to_string());
        assert!(err.to_string().contains("Failed to open"));

        let err = SndFileError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_duration_calculation() {
        let info = SndFileInfo {
            frames: 44100,
            sample_rate: 44100,
            channels: 2,
            format: 0,
            sections: 0,
            seekable: 1,
        };
        
        // Create a mock AudioFile to test duration
        let mock_file = AudioFile {
            file: std::ptr::null_mut(),
            info,
            path: "test.wav".to_string(),
        };
        
        assert_eq!(mock_file.duration_seconds(), 1.0);
    }
}
