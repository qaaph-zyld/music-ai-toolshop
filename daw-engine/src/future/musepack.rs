//! MusePack Integration
//!
//! FFI bindings to MusePack (MPC) - lossy audio codec
//! Superior audio quality at high bitrates
//!
//! License: BSD-3-Clause
//! Repo: https://github.com/musepack

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_void};
use std::path::Path;

/// MusePack encoder handle
#[repr(C)]
pub struct MpcEncoder {
    _private: [u8; 0],
}

/// MusePack decoder handle
#[repr(C)]
pub struct MpcDecoder {
    _private: [u8; 0],
}

/// MusePack error types
#[derive(Debug, Clone, PartialEq)]
pub enum MusePackError {
    OpenFailed(String),
    EncodeFailed(String),
    DecodeFailed(String),
    InvalidFile(String),
    NotAvailable,
}

impl std::fmt::Display for MusePackError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MusePackError::OpenFailed(path) => write!(f, "Failed to open MPC file: {}", path),
            MusePackError::EncodeFailed(msg) => write!(f, "MPC encoding failed: {}", msg),
            MusePackError::DecodeFailed(msg) => write!(f, "MPC decoding failed: {}", msg),
            MusePackError::InvalidFile(msg) => write!(f, "Invalid MPC file: {}", msg),
            MusePackError::NotAvailable => write!(f, "MusePack library not available"),
        }
    }
}

impl std::error::Error for MusePackError {}

/// MPC quality/profile settings
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MpcProfile {
    Thumb,      // Low quality (~60kbps)
    Radio,      // Radio quality (~96kbps)
    Standard,   // Standard quality (~130kbps)
    Extreme,    // Extreme quality (~180kbps)
    Insane,     // Insane quality (~210kbps)
    BrainDead,  // Maximum quality (~240kbps+)
}

/// MPC file info
#[derive(Debug, Clone, Default)]
pub struct MpcInfo {
    pub sample_rate: u32,
    pub channels: u16,
    pub bitrate: u32,
    pub duration_seconds: f64,
    pub profile: u32,
    pub is_sv8: bool,  // Stream Version 8
}

/// MusePack encoder
pub struct MusePackEncoder {
    encoder: *mut MpcEncoder,
    sample_rate: u32,
    channels: u16,
    profile: MpcProfile,
    path: String,
}

/// MusePack decoder
pub struct MusePackDecoder {
    decoder: *mut MpcDecoder,
    info: MpcInfo,
    path: String,
}

// FFI function declarations
extern "C" {
    fn mpc_ffi_is_available() -> c_int;
    fn mpc_ffi_get_version() -> *const c_char;
    fn mpc_ffi_get_encoder_version() -> *const c_char;
    
    // Encoder
    fn mpc_ffi_encoder_new() -> *mut MpcEncoder;
    fn mpc_ffi_encoder_delete(encoder: *mut MpcEncoder);
    fn mpc_ffi_encoder_init(encoder: *mut MpcEncoder, 
                             sample_rate: c_int, channels: c_int,
                             profile: c_int) -> c_int;
    fn mpc_ffi_encoder_encode(encoder: *mut MpcEncoder,
                               pcm_buffer: *const f32,
                               samples: c_int) -> c_int;
    fn mpc_ffi_encoder_finish(encoder: *mut MpcEncoder) -> c_int;
    fn mpc_ffi_encoder_get_buffer(encoder: *mut MpcEncoder,
                                   buffer: *mut c_char,
                                   buffer_size: c_int) -> c_int;
    
    // Decoder
    fn mpc_ffi_decoder_new() -> *mut MpcDecoder;
    fn mpc_ffi_decoder_delete(decoder: *mut MpcDecoder);
    fn mpc_ffi_decoder_init_file(decoder: *mut MpcDecoder, path: *const c_char) -> c_int;
    fn mpc_ffi_decoder_get_info(decoder: *mut MpcDecoder, info: *mut MpcInfo) -> c_int;
    fn mpc_ffi_decoder_decode(decoder: *mut MpcDecoder,
                               pcm_buffer: *mut f32,
                               samples: c_int) -> c_int;
    fn mpc_ffi_decoder_seek_sample(decoder: *mut MpcDecoder, sample: c_int) -> c_int;
    fn mpc_ffi_decoder_get_state(decoder: *mut MpcDecoder) -> c_int;
}

impl MusePackEncoder {
    /// Create new MusePack encoder
    pub fn new<P: AsRef<Path>>(_path: P, sample_rate: u32, channels: u16, profile: MpcProfile) 
        -> Result<Self, MusePackError> {
        if !Self::is_available() {
            return Err(MusePackError::NotAvailable);
        }

        let path_str = _path.as_ref().to_string_lossy().to_string();

        unsafe {
            let encoder = mpc_ffi_encoder_new();
            if encoder.is_null() {
                return Err(MusePackError::EncodeFailed("Failed to create encoder".to_string()));
            }

            let profile_val = match profile {
                MpcProfile::Thumb => 0,
                MpcProfile::Radio => 1,
                MpcProfile::Standard => 2,
                MpcProfile::Extreme => 3,
                MpcProfile::Insane => 4,
                MpcProfile::BrainDead => 5,
            };

            let result = mpc_ffi_encoder_init(
                encoder,
                sample_rate as c_int,
                channels as c_int,
                profile_val,
            );

            if result != 0 {
                mpc_ffi_encoder_delete(encoder);
                return Err(MusePackError::EncodeFailed(format!("Encoder init failed: {}", result)));
            }

            Ok(Self { encoder, sample_rate, channels, profile, path: path_str })
        }
    }

    /// Check if MusePack is available
    pub fn is_available() -> bool {
        unsafe { mpc_ffi_is_available() != 0 }
    }

    /// Get MusePack version
    pub fn version() -> String {
        unsafe {
            let version_ptr = mpc_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get encoder version
    pub fn encoder_version() -> String {
        unsafe {
            let version_ptr = mpc_ffi_get_encoder_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Encode PCM samples (interleaved f32)
    pub fn encode(&mut self, pcm_samples: &[f32]) -> Result<(), MusePackError> {
        unsafe {
            let result = mpc_ffi_encoder_encode(
                self.encoder,
                pcm_samples.as_ptr(),
                pcm_samples.len() as c_int,
            );
            
            if result != 0 {
                return Err(MusePackError::EncodeFailed(format!("Encode failed: {}", result)));
            }
            
            Ok(())
        }
    }

    /// Finish encoding
    pub fn finish(&mut self) -> Result<Vec<u8>, MusePackError> {
        unsafe {
            let result = mpc_ffi_encoder_finish(self.encoder);
            if result != 0 {
                return Err(MusePackError::EncodeFailed(format!("Finish failed: {}", result)));
            }
            
            // Get encoded buffer
            const BUF_SIZE: usize = 65536;
            let mut buffer = vec![0i8; BUF_SIZE];
            let size = mpc_ffi_encoder_get_buffer(
                self.encoder,
                buffer.as_mut_ptr() as *mut c_char,
                BUF_SIZE as c_int,
            );
            
            if size < 0 {
                return Err(MusePackError::EncodeFailed(format!("Get buffer failed: {}", size)));
            }
            
            let output: Vec<u8> = buffer[..size as usize]
                .iter()
                .map(|&b| b as u8)
                .collect();
            Ok(output)
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    /// Get channel count
    pub fn channels(&self) -> u16 {
        self.channels
    }

    /// Get profile
    pub fn profile(&self) -> MpcProfile {
        self.profile
    }
}

impl Drop for MusePackEncoder {
    fn drop(&mut self) {
        unsafe {
            if !self.encoder.is_null() {
                mpc_ffi_encoder_delete(self.encoder);
            }
        }
    }
}

impl MusePackDecoder {
    /// Open MPC file for decoding
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self, MusePackError> {
        if !Self::is_available() {
            return Err(MusePackError::NotAvailable);
        }

        let path_str = path.as_ref().to_string_lossy().to_string();
        let path_cstring = CString::new(path_str.clone())
            .map_err(|e| MusePackError::DecodeFailed(e.to_string()))?;

        unsafe {
            let decoder = mpc_ffi_decoder_new();
            if decoder.is_null() {
                return Err(MusePackError::DecodeFailed("Failed to create decoder".to_string()));
            }

            let result = mpc_ffi_decoder_init_file(decoder, path_cstring.as_ptr());
            if result != 0 {
                mpc_ffi_decoder_delete(decoder);
                return Err(MusePackError::OpenFailed(format!("Failed to open file: {}", result)));
            }

            let mut info: MpcInfo = Default::default();
            mpc_ffi_decoder_get_info(decoder, &mut info);

            Ok(Self { decoder, info, path: path_str })
        }
    }

    /// Check if MusePack decoder is available
    pub fn is_available() -> bool {
        unsafe { mpc_ffi_is_available() != 0 }
    }

    /// Get file info
    pub fn info(&self) -> &MpcInfo {
        &self.info
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.info.sample_rate
    }

    /// Get channel count
    pub fn channels(&self) -> u16 {
        self.info.channels
    }

    /// Get bitrate
    pub fn bitrate(&self) -> u32 {
        self.info.bitrate
    }

    /// Get duration
    pub fn duration(&self) -> f64 {
        self.info.duration_seconds
    }

    /// Check if SV8 format
    pub fn is_sv8(&self) -> bool {
        self.info.is_sv8
    }

    /// Decode PCM samples as f32 (interleaved)
    pub fn decode(&mut self, buffer: &mut [f32]) -> Result<usize, MusePackError> {
        let samples = buffer.len();
        
        unsafe {
            let result = mpc_ffi_decoder_decode(
                self.decoder,
                buffer.as_mut_ptr(),
                samples as c_int,
            );
            
            if result < 0 {
                return Err(MusePackError::DecodeFailed(format!("Decode failed: {}", result)));
            }
            
            Ok(result as usize)
        }
    }

    /// Seek to sample position
    pub fn seek(&mut self, sample: i32) -> Result<(), MusePackError> {
        unsafe {
            let result = mpc_ffi_decoder_seek_sample(self.decoder, sample);
            if result != 0 {
                return Err(MusePackError::DecodeFailed(format!("Seek failed: {}", result)));
            }
            Ok(())
        }
    }

    /// Get decoder state
    pub fn state(&self) -> i32 {
        unsafe { mpc_ffi_decoder_get_state(self.decoder) }
    }
}

impl Drop for MusePackDecoder {
    fn drop(&mut self) {
        unsafe {
            if !self.decoder.is_null() {
                mpc_ffi_decoder_delete(self.decoder);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_musepack_module_exists() {
        let _ = MusePackError::NotAvailable;
        let _ = MpcProfile::Standard;
        let _ = MpcInfo::default();
    }

    #[test]
    fn test_musepack_is_available() {
        let available = MusePackEncoder::is_available();
        println!("MusePack available: {}", available);
    }

    #[test]
    fn test_musepack_version() {
        let version = MusePackEncoder::version();
        println!("MusePack version: {}", version);
        
        let enc_version = MusePackEncoder::encoder_version();
        println!("MusePack encoder version: {}", enc_version);
    }

    #[test]
    fn test_mpc_profiles() {
        let profiles = vec![
            MpcProfile::Thumb,
            MpcProfile::Radio,
            MpcProfile::Standard,
            MpcProfile::Extreme,
            MpcProfile::Insane,
            MpcProfile::BrainDead,
        ];
        for profile in profiles {
            let s = format!("{:?}", profile);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_mpc_info_default() {
        let info: MpcInfo = Default::default();
        assert_eq!(info.sample_rate, 0);
        assert_eq!(info.channels, 0);
        assert_eq!(info.bitrate, 0);
        assert_eq!(info.duration_seconds, 0.0);
        assert_eq!(info.profile, 0);
        assert!(!info.is_sv8);
    }

    #[test]
    fn test_encoder_new_fails_gracefully() {
        let result = MusePackEncoder::new("/nonexistent/test.mpc", 44100, 2, MpcProfile::Standard);
        match result {
            Err(MusePackError::NotAvailable) | Err(MusePackError::EncodeFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable or EncodeFailed"),
        }
    }

    #[test]
    fn test_decoder_open_fails_gracefully() {
        let result = MusePackDecoder::open("/nonexistent/test.mpc");
        match result {
            Err(MusePackError::NotAvailable) | Err(MusePackError::OpenFailed(_)) | Err(MusePackError::DecodeFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable, OpenFailed, or DecodeFailed"),
        }
    }

    #[test]
    fn test_musepack_error_display() {
        let err = MusePackError::NotAvailable;
        assert!(err.to_string().contains("not available"));

        let err = MusePackError::EncodeFailed("test error".to_string());
        assert!(err.to_string().contains("encoding failed"));

        let err = MusePackError::DecodeFailed("test error".to_string());
        assert!(err.to_string().contains("decoding failed"));

        let err = MusePackError::InvalidFile("bad file".to_string());
        assert!(err.to_string().contains("Invalid MPC file"));

        let err = MusePackError::OpenFailed("test.mpc".to_string());
        assert!(err.to_string().contains("Failed to open"));
    }

    #[test]
    fn test_decoder_info_accessors() {
        let info = MpcInfo {
            sample_rate: 44100,
            channels: 2,
            bitrate: 180,
            duration_seconds: 200.0,
            profile: 3,
            is_sv8: true,
        };
        
        let decoder = MusePackDecoder {
            decoder: std::ptr::null_mut(),
            info,
            path: "test.mpc".to_string(),
        };
        
        assert_eq!(decoder.sample_rate(), 44100);
        assert_eq!(decoder.channels(), 2);
        assert_eq!(decoder.bitrate(), 180);
        assert_eq!(decoder.duration(), 200.0);
        assert!(decoder.is_sv8());
    }

    #[test]
    fn test_encoder_accessors() {
        let encoder = MusePackEncoder {
            encoder: std::ptr::null_mut(),
            sample_rate: 48000,
            channels: 2,
            profile: MpcProfile::Extreme,
            path: "test.mpc".to_string(),
        };
        
        assert_eq!(encoder.sample_rate(), 48000);
        assert_eq!(encoder.channels(), 2);
        assert_eq!(encoder.profile(), MpcProfile::Extreme);
    }
}
