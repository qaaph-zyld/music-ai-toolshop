//! Opus Integration
//!
//! FFI bindings to Opus - the BSD-3-Clause IETF codec for
//! high-quality compressed streaming and export.
//!
//! License: BSD-3-Clause
//! Repo: https://github.com/xiph/opus

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_uchar, c_void};

/// Opaque handle to Opus encoder
#[repr(C)]
pub struct OpusEncoder {
    _private: [u8; 0],
}

/// Opaque handle to Opus decoder
#[repr(C)]
pub struct OpusDecoder {
    _private: [u8; 0],
}

/// Opus error types
#[derive(Debug, Clone, PartialEq)]
pub enum OpusError {
    EncoderInitFailed,
    DecoderInitFailed,
    InvalidSampleRate,
    InvalidChannels,
    BufferTooSmall,
    InvalidPacket,
    FfiError(String),
}

impl std::fmt::Display for OpusError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OpusError::EncoderInitFailed => write!(f, "Opus encoder initialization failed"),
            OpusError::DecoderInitFailed => write!(f, "Opus decoder initialization failed"),
            OpusError::InvalidSampleRate => write!(f, "Invalid sample rate (must be 8k, 12k, 16k, 24k, or 48k)"),
            OpusError::InvalidChannels => write!(f, "Invalid channel count (must be 1 or 2)"),
            OpusError::BufferTooSmall => write!(f, "Output buffer too small"),
            OpusError::InvalidPacket => write!(f, "Invalid Opus packet"),
            OpusError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for OpusError {}

/// Opus application type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OpusApplication {
    VoIP,
    Audio,
    RestrictedLowdelay,
}

impl OpusApplication {
    fn to_int(&self) -> c_int {
        match self {
            OpusApplication::VoIP => 2048,
            OpusApplication::Audio => 2049,
            OpusApplication::RestrictedLowdelay => 2051,
        }
    }
}

/// Opus encoder configuration
#[derive(Debug, Clone)]
pub struct OpusEncoderConfig {
    pub sample_rate: u32,
    pub channels: u8,
    pub application: OpusApplication,
    pub bitrate: i32, // bits per second, -1 for auto
    pub complexity: i32, // 0-10
}

impl Default for OpusEncoderConfig {
    fn default() -> Self {
        Self {
            sample_rate: 48000,
            channels: 2,
            application: OpusApplication::Audio,
            bitrate: -1, // Auto
            complexity: 10,
        }
    }
}

/// Opus decoder configuration
#[derive(Debug, Clone)]
pub struct OpusDecoderConfig {
    pub sample_rate: u32,
    pub channels: u8,
}

impl Default for OpusDecoderConfig {
    fn default() -> Self {
        Self {
            sample_rate: 48000,
            channels: 2,
        }
    }
}

/// Opus encoder instance
pub struct OpusEncoderInstance {
    encoder: *mut OpusEncoder,
    config: OpusEncoderConfig,
}

/// Opus decoder instance
pub struct OpusDecoderInstance {
    decoder: *mut OpusDecoder,
    config: OpusDecoderConfig,
}

// FFI function declarations
extern "C" {
    fn opus_ffi_is_available() -> c_int;
    fn opus_ffi_get_version() -> *const c_char;
    
    // Encoder
    fn opus_ffi_encoder_create(
        sample_rate: c_int,
        channels: c_int,
        application: c_int,
    ) -> *mut OpusEncoder;
    fn opus_ffi_encoder_destroy(encoder: *mut OpusEncoder);
    fn opus_ffi_encode_float(
        encoder: *mut OpusEncoder,
        pcm: *const f32,
        frame_size: c_int,
        data: *mut c_uchar,
        max_data_bytes: c_int,
    ) -> c_int;
    fn opus_ffi_encoder_set_bitrate(encoder: *mut OpusEncoder, bitrate: c_int) -> c_int;
    fn opus_ffi_encoder_set_complexity(encoder: *mut OpusEncoder, complexity: c_int) -> c_int;
    
    // Decoder
    fn opus_ffi_decoder_create(sample_rate: c_int, channels: c_int) -> *mut OpusDecoder;
    fn opus_ffi_decoder_destroy(decoder: *mut OpusDecoder);
    fn opus_ffi_decode_float(
        decoder: *mut OpusDecoder,
        data: *const c_uchar,
        len: c_int,
        pcm: *mut f32,
        frame_size: c_int,
        decode_fec: c_int,
    ) -> c_int;
    
    // Packet info
    fn opus_ffi_packet_get_bandwidth(data: *const c_uchar) -> c_int;
    fn opus_ffi_packet_get_samples_per_frame(data: *const c_uchar, sample_rate: c_int) -> c_int;
}

impl OpusEncoderInstance {
    /// Create new Opus encoder with configuration
    pub fn new(config: OpusEncoderConfig) -> Result<Self, OpusError> {
        if !Self::is_available() {
            return Err(OpusError::FfiError("Opus not available".to_string()));
        }

        // Validate sample rate
        let valid_rates = [8000, 12000, 16000, 24000, 48000];
        if !valid_rates.contains(&config.sample_rate) {
            return Err(OpusError::InvalidSampleRate);
        }

        // Validate channels
        if config.channels != 1 && config.channels != 2 {
            return Err(OpusError::InvalidChannels);
        }

        unsafe {
            let encoder = opus_ffi_encoder_create(
                config.sample_rate as c_int,
                config.channels as c_int,
                config.application.to_int(),
            );
            if encoder.is_null() {
                return Err(OpusError::EncoderInitFailed);
            }

            // Set bitrate
            opus_ffi_encoder_set_bitrate(encoder, config.bitrate);
            
            // Set complexity
            opus_ffi_encoder_set_complexity(encoder, config.complexity);

            Ok(Self { encoder, config })
        }
    }

    /// Check if Opus is available
    pub fn is_available() -> bool {
        unsafe { opus_ffi_is_available() != 0 }
    }

    /// Get Opus version
    pub fn version() -> String {
        unsafe {
            let version_ptr = opus_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Encode PCM float samples to Opus packet
    pub fn encode(&mut self, pcm: &[f32], output: &mut [u8]) -> Result<usize, OpusError> {
        let frame_size = pcm.len() / self.config.channels as usize;
        
        unsafe {
            let bytes_written = opus_ffi_encode_float(
                self.encoder,
                pcm.as_ptr(),
                frame_size as c_int,
                output.as_mut_ptr(),
                output.len() as c_int,
            );
            
            if bytes_written < 0 {
                return Err(OpusError::BufferTooSmall);
            }
            
            Ok(bytes_written as usize)
        }
    }

    /// Get configuration
    pub fn config(&self) -> &OpusEncoderConfig {
        &self.config
    }

    /// Set bitrate (bits per second)
    pub fn set_bitrate(&mut self, bitrate: i32) {
        self.config.bitrate = bitrate;
        unsafe {
            opus_ffi_encoder_set_bitrate(self.encoder, bitrate);
        }
    }
}

impl Drop for OpusEncoderInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.encoder.is_null() {
                opus_ffi_encoder_destroy(self.encoder);
            }
        }
    }
}

impl OpusDecoderInstance {
    /// Create new Opus decoder with configuration
    pub fn new(config: OpusDecoderConfig) -> Result<Self, OpusError> {
        if !OpusEncoderInstance::is_available() {
            return Err(OpusError::FfiError("Opus not available".to_string()));
        }

        // Validate sample rate
        let valid_rates = [8000, 12000, 16000, 24000, 48000];
        if !valid_rates.contains(&config.sample_rate) {
            return Err(OpusError::InvalidSampleRate);
        }

        // Validate channels
        if config.channels != 1 && config.channels != 2 {
            return Err(OpusError::InvalidChannels);
        }

        unsafe {
            let decoder = opus_ffi_decoder_create(
                config.sample_rate as c_int,
                config.channels as c_int,
            );
            if decoder.is_null() {
                return Err(OpusError::DecoderInitFailed);
            }

            Ok(Self { decoder, config })
        }
    }

    /// Decode Opus packet to PCM float samples
    pub fn decode(&mut self, packet: &[u8], pcm: &mut [f32], fec: bool) -> Result<usize, OpusError> {
        let frame_size = pcm.len() / self.config.channels as usize;
        
        unsafe {
            let samples_decoded = opus_ffi_decode_float(
                self.decoder,
                packet.as_ptr(),
                packet.len() as c_int,
                pcm.as_mut_ptr(),
                frame_size as c_int,
                if fec { 1 } else { 0 },
            );
            
            if samples_decoded < 0 {
                return Err(OpusError::InvalidPacket);
            }
            
            Ok(samples_decoded as usize * self.config.channels as usize)
        }
    }

    /// Get configuration
    pub fn config(&self) -> &OpusDecoderConfig {
        &self.config
    }
}

impl Drop for OpusDecoderInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.decoder.is_null() {
                opus_ffi_decoder_destroy(self.decoder);
            }
        }
    }
}

/// Get packet bandwidth information
pub fn packet_bandwidth(packet: &[u8]) -> Option<i32> {
    if packet.is_empty() {
        return None;
    }
    unsafe {
        let result = opus_ffi_packet_get_bandwidth(packet.as_ptr());
        if result < 0 {
            None
        } else {
            Some(result)
        }
    }
}

/// Get samples per frame from packet
pub fn packet_samples_per_frame(packet: &[u8], sample_rate: u32) -> Option<i32> {
    if packet.is_empty() {
        return None;
    }
    unsafe {
        let result = opus_ffi_packet_get_samples_per_frame(packet.as_ptr(), sample_rate as c_int);
        if result < 0 {
            None
        } else {
            Some(result)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_opus_module_exists() {
        let _ = OpusError::EncoderInitFailed;
        let _config = OpusEncoderConfig::default();
        let _ = OpusApplication::Audio;
    }

    #[test]
    fn test_opus_is_available() {
        let available = OpusEncoderInstance::is_available();
        println!("Opus available: {}", available);
    }

    #[test]
    fn test_opus_version() {
        let version = OpusEncoderInstance::version();
        println!("Opus version: {}", version);
    }

    #[test]
    fn test_encoder_config_defaults() {
        let config = OpusEncoderConfig::default();
        assert_eq!(config.sample_rate, 48000);
        assert_eq!(config.channels, 2);
        assert_eq!(config.application, OpusApplication::Audio);
        assert_eq!(config.bitrate, -1); // Auto
        assert_eq!(config.complexity, 10);
    }

    #[test]
    fn test_decoder_config_defaults() {
        let config = OpusDecoderConfig::default();
        assert_eq!(config.sample_rate, 48000);
        assert_eq!(config.channels, 2);
    }

    #[test]
    fn test_opus_application_to_int() {
        assert_eq!(OpusApplication::VoIP.to_int(), 2048);
        assert_eq!(OpusApplication::Audio.to_int(), 2049);
        assert_eq!(OpusApplication::RestrictedLowdelay.to_int(), 2051);
    }

    #[test]
    fn test_encoder_creation() {
        let config = OpusEncoderConfig::default();
        let result = OpusEncoderInstance::new(config);
        match result {
            Ok(encoder) => {
                assert_eq!(encoder.config().sample_rate, 48000);
            }
            Err(e) => {
                println!("Encoder creation failed (expected if Opus not available): {}", e);
            }
        }
    }

    #[test]
    fn test_decoder_creation() {
        let config = OpusDecoderConfig::default();
        let result = OpusDecoderInstance::new(config);
        match result {
            Ok(decoder) => {
                assert_eq!(decoder.config().sample_rate, 48000);
            }
            Err(e) => {
                println!("Decoder creation failed (expected if Opus not available): {}", e);
            }
        }
    }

    #[test]
    fn test_invalid_sample_rate() {
        if !OpusEncoderInstance::is_available() {
            return; // Skip when library not available
        }
        let mut config = OpusEncoderConfig::default();
        config.sample_rate = 44100; // Invalid - not in valid rates
        let result = OpusEncoderInstance::new(config);
        assert!(matches!(result, Err(OpusError::InvalidSampleRate)));
    }

    #[test]
    fn test_invalid_channels() {
        if !OpusEncoderInstance::is_available() {
            return; // Skip when library not available
        }
        let mut config = OpusEncoderConfig::default();
        config.channels = 5; // Invalid - must be 1 or 2
        let result = OpusEncoderInstance::new(config);
        assert!(matches!(result, Err(OpusError::InvalidChannels)));
    }

    #[test]
    fn test_opus_error_display() {
        let err = OpusError::InvalidSampleRate;
        assert!(err.to_string().contains("Invalid sample rate"));

        let err = OpusError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_valid_sample_rates() {
        let valid_rates = [8000, 12000, 16000, 24000, 48000];
        for rate in &valid_rates {
            let mut config = OpusEncoderConfig::default();
            config.sample_rate = *rate;
            // Should not return InvalidSampleRate for valid rates
            // (may still fail if library not available)
            if OpusEncoderInstance::is_available() {
                let result = OpusEncoderInstance::new(config);
                assert!(!matches!(result, Err(OpusError::InvalidSampleRate)));
            }
        }
    }
}
