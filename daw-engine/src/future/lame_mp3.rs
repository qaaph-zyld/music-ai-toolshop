//! LAME MP3 Integration
//!
//! FFI bindings to LAME - high-quality MPEG Audio Layer III encoder
//! Industry-standard MP3 encoding library
//!
//! License: LGPL (with patent considerations)
//! Repo: https://github.com/libmp3lame/lame

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_void};
use std::path::Path;

/// LAME encoder handle
#[repr(C)]
pub struct LameEncoder {
    _private: [u8; 0],
}

/// LAME decoder/decoder handle (using mpg123 or similar)
#[repr(C)]
pub struct LameDecoder {
    _private: [u8; 0],
}

/// LAME error types
#[derive(Debug, Clone, PartialEq)]
pub enum LameError {
    OpenFailed(String),
    EncodeFailed(String),
    DecodeFailed(String),
    InvalidParams(String),
    NotAvailable,
}

impl std::fmt::Display for LameError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LameError::OpenFailed(path) => write!(f, "Failed to open MP3 file: {}", path),
            LameError::EncodeFailed(msg) => write!(f, "MP3 encoding failed: {}", msg),
            LameError::DecodeFailed(msg) => write!(f, "MP3 decoding failed: {}", msg),
            LameError::InvalidParams(msg) => write!(f, "Invalid MP3 parameters: {}", msg),
            LameError::NotAvailable => write!(f, "LAME library not available"),
        }
    }
}

impl std::error::Error for LameError {}

/// MP3 bitrate modes
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BitrateMode {
    CBR(u32),  // Constant bitrate (e.g., 128, 192, 256, 320)
    VBR(u32),  // Variable bitrate (quality 0-9, where 0 is best)
    ABR(u32),  // Average bitrate
}

/// MP3 quality preset
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum QualityPreset {
    Standard,      // Good quality, reasonable file size
    Extreme,       // Very high quality
    Insane,        // Maximum quality (320kbps)
    Medium,        // Balanced
    Phone,         // Low quality, small files
}

/// MP3 file info
#[derive(Debug, Clone, Default)]
pub struct Mp3Info {
    pub sample_rate: u32,
    pub channels: u16,
    pub bitrate: u32,
    pub duration_seconds: f64,
    pub frame_count: u32,
}

/// LAME MP3 encoder
pub struct LameMp3Encoder {
    encoder: *mut LameEncoder,
    sample_rate: u32,
    channels: u16,
    path: String,
}

/// LAME MP3 decoder
pub struct LameMp3Decoder {
    decoder: *mut LameDecoder,
    info: Mp3Info,
    path: String,
}

// FFI function declarations
extern "C" {
    fn lame_ffi_is_available() -> c_int;
    fn lame_ffi_get_version() -> *const c_char;
    
    // Encoder
    fn lame_ffi_encoder_new() -> *mut LameEncoder;
    fn lame_ffi_encoder_delete(encoder: *mut LameEncoder);
    fn lame_ffi_encoder_init(encoder: *mut LameEncoder, 
                              sample_rate: c_int, channels: c_int,
                              mode: c_int, quality: c_int) -> c_int;
    fn lame_ffi_encoder_encode_buffer_interleaved(encoder: *mut LameEncoder,
                                                   buffer: *const i16,
                                                   samples: c_int,
                                                   mp3_buffer: *mut c_char,
                                                   mp3_buffer_size: c_int) -> c_int;
    fn lame_ffi_encoder_encode_flush(encoder: *mut LameEncoder,
                                      mp3_buffer: *mut c_char,
                                      mp3_buffer_size: c_int) -> c_int;
    fn lame_ffi_encoder_set_bitrate(encoder: *mut LameEncoder, bitrate: c_int) -> c_int;
    fn lame_ffi_encoder_set_quality(encoder: *mut LameEncoder, quality: c_int) -> c_int;
    
    // Decoder
    fn lame_ffi_decoder_new() -> *mut LameDecoder;
    fn lame_ffi_decoder_delete(decoder: *mut LameDecoder);
    fn lame_ffi_decoder_init_file(decoder: *mut LameDecoder, path: *const c_char) -> c_int;
    fn lame_ffi_decoder_get_info(decoder: *mut LameDecoder, info: *mut Mp3Info) -> c_int;
    fn lame_ffi_decoder_decode_frame(decoder: *mut LameDecoder,
                                      pcm_buffer: *mut i16,
                                      buffer_size: c_int) -> c_int;
    fn lame_ffi_decoder_decode_interleaved(decoder: *mut LameDecoder,
                                            pcm_buffer: *mut f32,
                                            samples: c_int) -> c_int;
}

impl LameMp3Encoder {
    /// Create new MP3 encoder
    pub fn new<P: AsRef<Path>>(_path: P, sample_rate: u32, channels: u16, 
                                _mode: BitrateMode, quality: QualityPreset) 
        -> Result<Self, LameError> {
        if !Self::is_available() {
            return Err(LameError::NotAvailable);
        }

        let path_str = _path.as_ref().to_string_lossy().to_string();

        unsafe {
            let encoder = lame_ffi_encoder_new();
            if encoder.is_null() {
                return Err(LameError::EncodeFailed("Failed to create encoder".to_string()));
            }

            // Map quality preset to internal value
            let quality_val = match quality {
                QualityPreset::Phone => 7,
                QualityPreset::Medium => 5,
                QualityPreset::Standard => 2,
                QualityPreset::Extreme => 0,
                QualityPreset::Insane => 0,
            };

            let mode_val = match _mode {
                BitrateMode::CBR(_) => 0,
                BitrateMode::VBR(_) => 1,
                BitrateMode::ABR(_) => 2,
            };

            let result = lame_ffi_encoder_init(
                encoder,
                sample_rate as c_int,
                channels as c_int,
                mode_val,
                quality_val,
            );

            if result != 0 {
                lame_ffi_encoder_delete(encoder);
                return Err(LameError::EncodeFailed(format!("Encoder init failed: {}", result)));
            }

            // Set bitrate if CBR
            if let BitrateMode::CBR(kbps) = _mode {
                lame_ffi_encoder_set_bitrate(encoder, kbps as c_int);
            }

            Ok(Self { encoder, sample_rate, channels, path: path_str })
        }
    }

    /// Check if LAME is available
    pub fn is_available() -> bool {
        unsafe { lame_ffi_is_available() != 0 }
    }

    /// Get LAME version
    pub fn version() -> String {
        unsafe {
            let version_ptr = lame_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Encode interleaved PCM samples
    pub fn encode(&mut self, pcm_samples: &[i16]) -> Result<Vec<u8>, LameError> {
        const MP3_BUF_SIZE: usize = 16384;
        let mut mp3_buffer = vec![0i8; MP3_BUF_SIZE];
        
        unsafe {
            let result = lame_ffi_encoder_encode_buffer_interleaved(
                self.encoder,
                pcm_samples.as_ptr(),
                pcm_samples.len() as c_int,
                mp3_buffer.as_mut_ptr() as *mut c_char,
                MP3_BUF_SIZE as c_int,
            );
            
            if result < 0 {
                return Err(LameError::EncodeFailed(format!("Encode failed: {}", result)));
            }
            
            // Convert to Vec<u8> - only valid bytes
            let valid_bytes = result as usize;
            let output: Vec<u8> = mp3_buffer[..valid_bytes]
                .iter()
                .map(|&b| b as u8)
                .collect();
            Ok(output)
        }
    }

    /// Flush encoder and get final MP3 data
    pub fn flush(&mut self) -> Result<Vec<u8>, LameError> {
        const MP3_BUF_SIZE: usize = 16384;
        let mut mp3_buffer = vec![0i8; MP3_BUF_SIZE];
        
        unsafe {
            let result = lame_ffi_encoder_encode_flush(
                self.encoder,
                mp3_buffer.as_mut_ptr() as *mut c_char,
                MP3_BUF_SIZE as c_int,
            );
            
            if result < 0 {
                return Err(LameError::EncodeFailed(format!("Flush failed: {}", result)));
            }
            
            let valid_bytes = result as usize;
            let output: Vec<u8> = mp3_buffer[..valid_bytes]
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
}

impl Drop for LameMp3Encoder {
    fn drop(&mut self) {
        unsafe {
            if !self.encoder.is_null() {
                lame_ffi_encoder_delete(self.encoder);
            }
        }
    }
}

impl LameMp3Decoder {
    /// Open MP3 file for decoding
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self, LameError> {
        if !Self::is_available() {
            return Err(LameError::NotAvailable);
        }

        let path_str = path.as_ref().to_string_lossy().to_string();
        let path_cstring = CString::new(path_str.clone())
            .map_err(|e| LameError::DecodeFailed(e.to_string()))?;

        unsafe {
            let decoder = lame_ffi_decoder_new();
            if decoder.is_null() {
                return Err(LameError::DecodeFailed("Failed to create decoder".to_string()));
            }

            let result = lame_ffi_decoder_init_file(decoder, path_cstring.as_ptr());
            if result != 0 {
                lame_ffi_decoder_delete(decoder);
                return Err(LameError::DecodeFailed(format!("Failed to open file: {}", result)));
            }

            let mut info: Mp3Info = Default::default();
            lame_ffi_decoder_get_info(decoder, &mut info);

            Ok(Self { decoder, info, path: path_str })
        }
    }

    /// Check if LAME decoder is available
    pub fn is_available() -> bool {
        unsafe { lame_ffi_is_available() != 0 }
    }

    /// Get MP3 file info
    pub fn info(&self) -> &Mp3Info {
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

    /// Decode interleaved PCM samples as f32
    pub fn decode_f32(&mut self, buffer: &mut [f32]) -> Result<usize, LameError> {
        let samples = buffer.len();
        
        unsafe {
            let result = lame_ffi_decoder_decode_interleaved(
                self.decoder,
                buffer.as_mut_ptr(),
                samples as c_int,
            );
            
            if result < 0 {
                return Err(LameError::DecodeFailed(format!("Decode failed: {}", result)));
            }
            
            Ok(result as usize)
        }
    }
}

impl Drop for LameMp3Decoder {
    fn drop(&mut self) {
        unsafe {
            if !self.decoder.is_null() {
                lame_ffi_decoder_delete(self.decoder);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lame_module_exists() {
        let _ = LameError::NotAvailable;
        let _ = BitrateMode::CBR(192);
        let _ = QualityPreset::Standard;
        let _ = Mp3Info::default();
    }

    #[test]
    fn test_lame_is_available() {
        let available = LameMp3Encoder::is_available();
        println!("LAME available: {}", available);
    }

    #[test]
    fn test_lame_version() {
        let version = LameMp3Encoder::version();
        println!("LAME version: {}", version);
    }

    #[test]
    fn test_bitrate_modes() {
        let modes = vec![
            BitrateMode::CBR(128),
            BitrateMode::CBR(192),
            BitrateMode::CBR(320),
            BitrateMode::VBR(2),
            BitrateMode::VBR(5),
            BitrateMode::ABR(192),
        ];
        for mode in modes {
            let s = format!("{:?}", mode);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_quality_presets() {
        let presets = vec![
            QualityPreset::Phone,
            QualityPreset::Medium,
            QualityPreset::Standard,
            QualityPreset::Extreme,
            QualityPreset::Insane,
        ];
        for preset in presets {
            let s = format!("{:?}", preset);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_mp3_info_default() {
        let info: Mp3Info = Default::default();
        assert_eq!(info.sample_rate, 0);
        assert_eq!(info.channels, 0);
        assert_eq!(info.bitrate, 0);
        assert_eq!(info.duration_seconds, 0.0);
        assert_eq!(info.frame_count, 0);
    }

    #[test]
    fn test_encoder_new_fails_gracefully() {
        let result = LameMp3Encoder::new("/nonexistent/test.mp3", 44100, 2, 
                                          BitrateMode::CBR(192), QualityPreset::Standard);
        match result {
            Err(LameError::NotAvailable) | Err(LameError::EncodeFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable or EncodeFailed"),
        }
    }

    #[test]
    fn test_decoder_open_fails_gracefully() {
        let result = LameMp3Decoder::open("/nonexistent/test.mp3");
        match result {
            Err(LameError::NotAvailable) | Err(LameError::DecodeFailed(_)) | Err(LameError::OpenFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable, DecodeFailed, or OpenFailed"),
        }
    }

    #[test]
    fn test_lame_error_display() {
        let err = LameError::NotAvailable;
        assert!(err.to_string().contains("not available"));

        let err = LameError::EncodeFailed("test error".to_string());
        assert!(err.to_string().contains("encoding failed"));

        let err = LameError::DecodeFailed("test error".to_string());
        assert!(err.to_string().contains("decoding failed"));

        let err = LameError::InvalidParams("bad params".to_string());
        assert!(err.to_string().contains("Invalid MP3 parameters"));

        let err = LameError::OpenFailed("test.mp3".to_string());
        assert!(err.to_string().contains("Failed to open"));
    }

    #[test]
    fn test_decoder_info_accessors() {
        let info = Mp3Info {
            sample_rate: 44100,
            channels: 2,
            bitrate: 192,
            duration_seconds: 180.5,
            frame_count: 1000,
        };
        
        let decoder = LameMp3Decoder {
            decoder: std::ptr::null_mut(),
            info,
            path: "test.mp3".to_string(),
        };
        
        assert_eq!(decoder.sample_rate(), 44100);
        assert_eq!(decoder.channels(), 2);
        assert_eq!(decoder.bitrate(), 192);
        assert_eq!(decoder.duration(), 180.5);
    }

    #[test]
    fn test_encoder_accessors() {
        let encoder = LameMp3Encoder {
            encoder: std::ptr::null_mut(),
            sample_rate: 48000,
            channels: 2,
            path: "test.mp3".to_string(),
        };
        
        assert_eq!(encoder.sample_rate(), 48000);
        assert_eq!(encoder.channels(), 2);
    }
}
