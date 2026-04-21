//! LibFLAC Integration
//!
//! FFI bindings to libFLAC - Free Lossless Audio Codec
//! High-quality lossless audio compression
//!
//! License: BSD-3-Clause / GPL
//! Repo: https://github.com/xiph/flac

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_void};
use std::path::Path;

/// FLAC encoder handle
#[repr(C)]
pub struct FlacEncoder {
    _private: [u8; 0],
}

/// FLAC decoder handle
#[repr(C)]
pub struct FlacDecoder {
    _private: [u8; 0],
}

/// FLAC error types
#[derive(Debug, Clone, PartialEq)]
pub enum FlacError {
    OpenFailed(String),
    EncodeFailed(String),
    DecodeFailed(String),
    InvalidFormat(String),
    NotAvailable,
}

impl std::fmt::Display for FlacError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FlacError::OpenFailed(path) => write!(f, "Failed to open FLAC file: {}", path),
            FlacError::EncodeFailed(msg) => write!(f, "FLAC encoding failed: {}", msg),
            FlacError::DecodeFailed(msg) => write!(f, "FLAC decoding failed: {}", msg),
            FlacError::InvalidFormat(fmt) => write!(f, "Invalid FLAC format: {}", fmt),
            FlacError::NotAvailable => write!(f, "libFLAC not available"),
        }
    }
}

impl std::error::Error for FlacError {}

/// FLAC compression levels (0-8)
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CompressionLevel {
    Fastest = 0,  // Fastest, least compression
    Low = 2,
    Default = 5,
    High = 7,
    Best = 8,     // Best compression, slowest
}

/// FLAC file metadata
#[derive(Debug, Clone, Default)]
pub struct FlacMetadata {
    pub sample_rate: u32,
    pub channels: u16,
    pub bits_per_sample: u16,
    pub total_samples: u64,
    pub compression_ratio: f32,
}

/// FLAC encoder
pub struct FlacEncoderHandle {
    encoder: *mut FlacEncoder,
    path: String,
}

/// FLAC decoder
pub struct FlacDecoderHandle {
    decoder: *mut FlacDecoder,
    metadata: FlacMetadata,
    path: String,
}

// FFI function declarations
extern "C" {
    fn flac_ffi_is_available() -> c_int;
    fn flac_ffi_get_version() -> *const c_char;
    
    // Encoder
    fn flac_ffi_encoder_new() -> *mut FlacEncoder;
    fn flac_ffi_encoder_delete(encoder: *mut FlacEncoder);
    fn flac_ffi_encoder_init_file(encoder: *mut FlacEncoder, path: *const c_char, 
                                   sample_rate: c_int, channels: c_int, 
                                   bits_per_sample: c_int, compression: c_int) -> c_int;
    fn flac_ffi_encoder_process_interleaved(encoder: *mut FlacEncoder, 
                                             buffer: *const i32, samples: c_int) -> c_int;
    fn flac_ffi_encoder_finish(encoder: *mut FlacEncoder) -> c_int;
    fn flac_ffi_encoder_get_state(encoder: *mut FlacEncoder) -> c_int;
    
    // Decoder
    fn flac_ffi_decoder_new() -> *mut FlacDecoder;
    fn flac_ffi_decoder_delete(decoder: *mut FlacDecoder);
    fn flac_ffi_decoder_init_file(decoder: *mut FlacDecoder, path: *const c_char) -> c_int;
    fn flac_ffi_decoder_process_single(decoder: *mut FlacDecoder) -> c_int;
    fn flac_ffi_decoder_process_until_end_of_stream(decoder: *mut FlacDecoder) -> c_int;
    fn flac_ffi_decoder_get_metadata(decoder: *mut FlacDecoder, metadata: *mut FlacMetadata) -> c_int;
    fn flac_ffi_decoder_get_state(decoder: *mut FlacDecoder) -> c_int;
}

impl FlacEncoderHandle {
    /// Create new FLAC encoder
    pub fn new<P: AsRef<Path>>(path: P, sample_rate: u32, channels: u16, 
                                bits_per_sample: u16, compression: CompressionLevel) 
        -> Result<Self, FlacError> {
        if !Self::is_available() {
            return Err(FlacError::NotAvailable);
        }

        let path_str = path.as_ref().to_string_lossy().to_string();
        let path_cstring = CString::new(path_str.clone())
            .map_err(|e| FlacError::EncodeFailed(e.to_string()))?;

        unsafe {
            let encoder = flac_ffi_encoder_new();
            if encoder.is_null() {
                return Err(FlacError::EncodeFailed("Failed to create encoder".to_string()));
            }

            let result = flac_ffi_encoder_init_file(
                encoder,
                path_cstring.as_ptr(),
                sample_rate as c_int,
                channels as c_int,
                bits_per_sample as c_int,
                compression as c_int,
            );

            if result != 0 {
                flac_ffi_encoder_delete(encoder);
                return Err(FlacError::EncodeFailed(format!("Encoder init failed: {}", result)));
            }

            Ok(Self { encoder, path: path_str })
        }
    }

    /// Check if libFLAC is available
    pub fn is_available() -> bool {
        unsafe { flac_ffi_is_available() != 0 }
    }

    /// Get libFLAC version
    pub fn version() -> String {
        unsafe {
            let version_ptr = flac_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Encode interleaved audio samples
    pub fn encode(&mut self, samples: &[i32]) -> Result<(), FlacError> {
        unsafe {
            let result = flac_ffi_encoder_process_interleaved(
                self.encoder,
                samples.as_ptr(),
                samples.len() as c_int,
            );
            if result != 0 {
                return Err(FlacError::EncodeFailed(format!("Encode failed: {}", result)));
            }
            Ok(())
        }
    }

    /// Finish encoding and write file
    pub fn finish(self) -> Result<(), FlacError> {
        unsafe {
            let result = flac_ffi_encoder_finish(self.encoder);
            if result != 0 {
                return Err(FlacError::EncodeFailed(format!("Finish failed: {}", result)));
            }
            Ok(())
        }
    }

    /// Get encoder state
    pub fn state(&self) -> i32 {
        unsafe { flac_ffi_encoder_get_state(self.encoder) }
    }
}

impl Drop for FlacEncoderHandle {
    fn drop(&mut self) {
        unsafe {
            if !self.encoder.is_null() {
                flac_ffi_encoder_delete(self.encoder);
            }
        }
    }
}

impl FlacDecoderHandle {
    /// Open FLAC file for decoding
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self, FlacError> {
        if !Self::is_available() {
            return Err(FlacError::NotAvailable);
        }

        let path_str = path.as_ref().to_string_lossy().to_string();
        let path_cstring = CString::new(path_str.clone())
            .map_err(|e| FlacError::DecodeFailed(e.to_string()))?;

        unsafe {
            let decoder = flac_ffi_decoder_new();
            if decoder.is_null() {
                return Err(FlacError::DecodeFailed("Failed to create decoder".to_string()));
            }

            let result = flac_ffi_decoder_init_file(decoder, path_cstring.as_ptr());
            if result != 0 {
                flac_ffi_decoder_delete(decoder);
                return Err(FlacError::DecodeFailed(format!("Decoder init failed: {}", result)));
            }

            let mut metadata: FlacMetadata = Default::default();
            flac_ffi_decoder_get_metadata(decoder, &mut metadata);

            Ok(Self { decoder, metadata, path: path_str })
        }
    }

    /// Check if libFLAC is available
    pub fn is_available() -> bool {
        unsafe { flac_ffi_is_available() != 0 }
    }

    /// Get file metadata
    pub fn metadata(&self) -> &FlacMetadata {
        &self.metadata
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.metadata.sample_rate
    }

    /// Get channel count
    pub fn channels(&self) -> u16 {
        self.metadata.channels
    }

    /// Get bits per sample
    pub fn bits_per_sample(&self) -> u16 {
        self.metadata.bits_per_sample
    }

    /// Get total samples
    pub fn total_samples(&self) -> u64 {
        self.metadata.total_samples
    }

    /// Get duration in seconds
    pub fn duration_seconds(&self) -> f64 {
        if self.metadata.sample_rate > 0 {
            self.metadata.total_samples as f64 / self.metadata.sample_rate as f64
        } else {
            0.0
        }
    }

    /// Decode single frame
    pub fn decode_frame(&mut self) -> Result<(), FlacError> {
        unsafe {
            let result = flac_ffi_decoder_process_single(self.decoder);
            if result != 0 {
                return Err(FlacError::DecodeFailed(format!("Decode failed: {}", result)));
            }
            Ok(())
        }
    }

    /// Decode entire file
    pub fn decode_all(&mut self) -> Result<(), FlacError> {
        unsafe {
            let result = flac_ffi_decoder_process_until_end_of_stream(self.decoder);
            if result != 0 {
                return Err(FlacError::DecodeFailed(format!("Decode failed: {}", result)));
            }
            Ok(())
        }
    }

    /// Get decoder state
    pub fn state(&self) -> i32 {
        unsafe { flac_ffi_decoder_get_state(self.decoder) }
    }
}

impl Drop for FlacDecoderHandle {
    fn drop(&mut self) {
        unsafe {
            if !self.decoder.is_null() {
                flac_ffi_decoder_delete(self.decoder);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_flac_module_exists() {
        let _ = FlacError::NotAvailable;
        let _ = CompressionLevel::Default;
        let _ = FlacMetadata::default();
    }

    #[test]
    fn test_flac_is_available() {
        let available = FlacEncoderHandle::is_available();
        println!("libFLAC available: {}", available);
    }

    #[test]
    fn test_flac_version() {
        let version = FlacEncoderHandle::version();
        println!("libFLAC version: {}", version);
    }

    #[test]
    fn test_compression_levels() {
        let levels = vec![
            CompressionLevel::Fastest,
            CompressionLevel::Low,
            CompressionLevel::Default,
            CompressionLevel::High,
            CompressionLevel::Best,
        ];
        for level in levels {
            let val = level as i32;
            assert!(val >= 0 && val <= 8);
        }
    }

    #[test]
    fn test_metadata_default() {
        let meta: FlacMetadata = Default::default();
        assert_eq!(meta.sample_rate, 0);
        assert_eq!(meta.channels, 0);
        assert_eq!(meta.bits_per_sample, 0);
        assert_eq!(meta.total_samples, 0);
        assert_eq!(meta.compression_ratio, 0.0);
    }

    #[test]
    fn test_encoder_new_fails_gracefully() {
        let result = FlacEncoderHandle::new("/nonexistent/test.flac", 44100, 2, 16, CompressionLevel::Default);
        match result {
            Err(FlacError::NotAvailable) | Err(FlacError::EncodeFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable or EncodeFailed"),
        }
    }

    #[test]
    fn test_decoder_open_fails_gracefully() {
        let result = FlacDecoderHandle::open("/nonexistent/test.flac");
        match result {
            Err(FlacError::NotAvailable) | Err(FlacError::DecodeFailed(_)) | Err(FlacError::OpenFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable, DecodeFailed, or OpenFailed"),
        }
    }

    #[test]
    fn test_flac_error_display() {
        let err = FlacError::NotAvailable;
        assert!(err.to_string().contains("not available"));

        let err = FlacError::EncodeFailed("test error".to_string());
        assert!(err.to_string().contains("encoding failed"));

        let err = FlacError::DecodeFailed("test error".to_string());
        assert!(err.to_string().contains("decoding failed"));

        let err = FlacError::OpenFailed("test.flac".to_string());
        assert!(err.to_string().contains("Failed to open"));

        let err = FlacError::InvalidFormat("bad format".to_string());
        assert!(err.to_string().contains("Invalid FLAC format"));
    }

    #[test]
    fn test_duration_calculation() {
        let meta = FlacMetadata {
            sample_rate: 44100,
            total_samples: 44100,
            ..Default::default()
        };
        
        // Create mock decoder to test duration
        let mock_decoder = FlacDecoderHandle {
            decoder: std::ptr::null_mut(),
            metadata: meta,
            path: "test.flac".to_string(),
        };
        
        assert_eq!(mock_decoder.duration_seconds(), 1.0);
        
        // Test zero sample rate
        let meta_zero_sr = FlacMetadata {
            sample_rate: 0,
            total_samples: 1000,
            ..Default::default()
        };
        let mock_decoder_zero = FlacDecoderHandle {
            decoder: std::ptr::null_mut(),
            metadata: meta_zero_sr,
            path: "test.flac".to_string(),
        };
        assert_eq!(mock_decoder_zero.duration_seconds(), 0.0);
    }

    #[test]
    fn test_decoder_metadata_accessors() {
        let meta = FlacMetadata {
            sample_rate: 48000,
            channels: 2,
            bits_per_sample: 24,
            total_samples: 96000,
            compression_ratio: 0.5,
        };
        
        let decoder = FlacDecoderHandle {
            decoder: std::ptr::null_mut(),
            metadata: meta,
            path: "test.flac".to_string(),
        };
        
        assert_eq!(decoder.sample_rate(), 48000);
        assert_eq!(decoder.channels(), 2);
        assert_eq!(decoder.bits_per_sample(), 24);
        assert_eq!(decoder.total_samples(), 96000);
    }
}
