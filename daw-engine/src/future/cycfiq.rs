//! Cycfi Q Integration
//!
//! FFI bindings to Cycfi Q - a modern C++ DSP toolkit with
//! advanced pitch detection, filters, dynamics processors,
//! and envelope followers. Zero dependencies core.
//!
//! License: MIT
//! Repo: https://github.com/cycfi/q

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// Opaque handle to Q pitch detector
#[repr(C)]
pub struct QPitchDetector {
    _private: [u8; 0],
}

/// Opaque handle to Q filter
#[repr(C)]
pub struct QFilter {
    _private: [u8; 0],
}

/// Opaque handle to Q envelope follower
#[repr(C)]
pub struct QEnvelope {
    _private: [u8; 0],
}

/// Cycfi Q error types
#[derive(Debug, Clone, PartialEq)]
pub enum QError {
    DetectorInitFailed,
    FilterInitFailed,
    InvalidFrequency,
    InvalidParameter(String),
    FfiError(String),
}

impl std::fmt::Display for QError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            QError::DetectorInitFailed => write!(f, "Pitch detector initialization failed"),
            QError::FilterInitFailed => write!(f, "Filter initialization failed"),
            QError::InvalidFrequency => write!(f, "Invalid frequency parameter"),
            QError::InvalidParameter(param) => write!(f, "Invalid parameter: {}", param),
            QError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for QError {}

/// Pitch detection result
#[derive(Debug, Clone, Copy)]
pub struct PitchResult {
    pub frequency: f32,
    pub confidence: f32,
    pub is_voiced: bool,
}

/// Filter type enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum FilterType {
    Lowpass,
    Highpass,
    Bandpass,
    Notch,
    Peak,
    Lowshelf,
    Highshelf,
}

/// Filter configuration
#[derive(Debug, Clone)]
pub struct FilterConfig {
    pub filter_type: FilterType,
    pub freq: f32,
    pub q: f32,
    pub gain_db: f32,
}

impl Default for FilterConfig {
    fn default() -> Self {
        Self {
            filter_type: FilterType::Lowpass,
            freq: 1000.0,
            q: 0.707,
            gain_db: 0.0,
        }
    }
}

/// Envelope follower configuration
#[derive(Debug, Clone)]
pub struct EnvelopeConfig {
    pub attack_ms: f32,
    pub release_ms: f32,
    pub sample_rate: u32,
}

impl Default for EnvelopeConfig {
    fn default() -> Self {
        Self {
            attack_ms: 10.0,
            release_ms: 100.0,
            sample_rate: 44100,
        }
    }
}

/// Cycfi Q pitch detector
pub struct QPitchDetectorInstance {
    detector: *mut QPitchDetector,
    sample_rate: u32,
}

/// Cycfi Q filter
pub struct QFilterInstance {
    filter: *mut QFilter,
    config: FilterConfig,
}

/// Cycfi Q envelope follower
pub struct QEnvelopeFollower {
    envelope: *mut QEnvelope,
    config: EnvelopeConfig,
}

// FFI function declarations
extern "C" {
    fn q_ffi_is_available() -> c_int;
    fn q_ffi_get_version() -> *const c_char;
    
    // Pitch detection
    fn q_ffi_pitch_detector_create(sample_rate: c_int) -> *mut QPitchDetector;
    fn q_ffi_pitch_detector_destroy(detector: *mut QPitchDetector);
    fn q_ffi_pitch_detector_process(
        detector: *mut QPitchDetector,
        input: *const c_float,
        num_samples: c_int,
        frequency: *mut c_float,
        confidence: *mut c_float,
    ) -> c_int;
    
    // Filter
    fn q_ffi_filter_create(filter_type: c_int, freq: c_float, q: c_float, gain: c_float, sample_rate: c_int) -> *mut QFilter;
    fn q_ffi_filter_destroy(filter: *mut QFilter);
    fn q_ffi_filter_process(filter: *mut QFilter, input: c_float) -> c_float;
    fn q_ffi_filter_process_block(
        filter: *mut QFilter,
        input: *const c_float,
        output: *mut c_float,
        num_samples: c_int,
    );
    
    // Envelope
    fn q_ffi_envelope_create(attack_ms: c_float, release_ms: c_float, sample_rate: c_int) -> *mut QEnvelope;
    fn q_ffi_envelope_destroy(envelope: *mut QEnvelope);
    fn q_ffi_envelope_process(envelope: *mut QEnvelope, input: c_float) -> c_float;
}

impl QPitchDetectorInstance {
    /// Create new pitch detector with sample rate
    pub fn new(sample_rate: u32) -> Result<Self, QError> {
        if !Self::is_available() {
            return Err(QError::FfiError("Cycfi Q not available".to_string()));
        }

        unsafe {
            let detector = q_ffi_pitch_detector_create(sample_rate as c_int);
            if detector.is_null() {
                return Err(QError::DetectorInitFailed);
            }
            Ok(Self {
                detector,
                sample_rate,
            })
        }
    }

    /// Check if Cycfi Q is available
    pub fn is_available() -> bool {
        unsafe { q_ffi_is_available() != 0 }
    }

    /// Get Cycfi Q version
    pub fn version() -> String {
        unsafe {
            let version_ptr = q_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Process audio buffer and detect pitch
    pub fn process(&mut self, input: &[f32]) -> PitchResult {
        let mut frequency: c_float = 0.0;
        let mut confidence: c_float = 0.0;

        let result = unsafe {
            q_ffi_pitch_detector_process(
                self.detector,
                input.as_ptr(),
                input.len() as c_int,
                &mut frequency,
                &mut confidence,
            )
        };

        PitchResult {
            frequency: frequency as f32,
            confidence: confidence as f32,
            is_voiced: result != 0,
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
}

impl Drop for QPitchDetectorInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.detector.is_null() {
                q_ffi_pitch_detector_destroy(self.detector);
            }
        }
    }
}

impl QFilterInstance {
    /// Create new filter with configuration
    pub fn new(config: FilterConfig, sample_rate: u32) -> Result<Self, QError> {
        if !QPitchDetectorInstance::is_available() {
            return Err(QError::FfiError("Cycfi Q not available".to_string()));
        }

        let filter_type_int = match config.filter_type {
            FilterType::Lowpass => 0,
            FilterType::Highpass => 1,
            FilterType::Bandpass => 2,
            FilterType::Notch => 3,
            FilterType::Peak => 4,
            FilterType::Lowshelf => 5,
            FilterType::Highshelf => 6,
        };

        unsafe {
            let filter = q_ffi_filter_create(
                filter_type_int,
                config.freq,
                config.q,
                config.gain_db,
                sample_rate as c_int,
            );
            if filter.is_null() {
                return Err(QError::FilterInitFailed);
            }
            Ok(Self { filter, config })
        }
    }

    /// Process single sample
    pub fn process(&mut self, input: f32) -> f32 {
        unsafe { q_ffi_filter_process(self.filter, input) }
    }

    /// Process audio block
    pub fn process_block(&mut self, input: &[f32], output: &mut [f32]) {
        let num_samples = input.len().min(output.len());
        unsafe {
            q_ffi_filter_process_block(
                self.filter,
                input.as_ptr(),
                output.as_mut_ptr(),
                num_samples as c_int,
            );
        }
    }

    /// Get filter configuration
    pub fn config(&self) -> &FilterConfig {
        &self.config
    }
}

impl Drop for QFilterInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.filter.is_null() {
                q_ffi_filter_destroy(self.filter);
            }
        }
    }
}

impl QEnvelopeFollower {
    /// Create new envelope follower with configuration
    pub fn new(config: EnvelopeConfig) -> Result<Self, QError> {
        if !QPitchDetectorInstance::is_available() {
            return Err(QError::FfiError("Cycfi Q not available".to_string()));
        }

        unsafe {
            let envelope = q_ffi_envelope_create(
                config.attack_ms,
                config.release_ms,
                config.sample_rate as c_int,
            );
            if envelope.is_null() {
                return Err(QError::FfiError("Envelope init failed".to_string()));
            }
            Ok(Self { envelope, config })
        }
    }

    /// Process single sample
    pub fn process(&mut self, input: f32) -> f32 {
        unsafe { q_ffi_envelope_process(self.envelope, input) }
    }

    /// Get configuration
    pub fn config(&self) -> &EnvelopeConfig {
        &self.config
    }
}

impl Drop for QEnvelopeFollower {
    fn drop(&mut self) {
        unsafe {
            if !self.envelope.is_null() {
                q_ffi_envelope_destroy(self.envelope);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_q_module_exists() {
        let _ = QError::DetectorInitFailed;
        let _config = FilterConfig::default();
        let _ = FilterType::Lowpass;
    }

    #[test]
    fn test_q_is_available() {
        let available = QPitchDetectorInstance::is_available();
        println!("Cycfi Q available: {}", available);
    }

    #[test]
    fn test_q_version() {
        let version = QPitchDetectorInstance::version();
        println!("Cycfi Q version: {}", version);
    }

    #[test]
    fn test_pitch_detector_creation() {
        let result = QPitchDetectorInstance::new(44100);
        match result {
            Ok(detector) => {
                assert_eq!(detector.sample_rate(), 44100);
            }
            Err(e) => {
                println!("Pitch detector creation failed (expected if Q not available): {}", e);
            }
        }
    }

    #[test]
    fn test_filter_config_defaults() {
        let config = FilterConfig::default();
        assert_eq!(config.filter_type, FilterType::Lowpass);
        assert_eq!(config.freq, 1000.0);
        assert_eq!(config.q, 0.707);
        assert_eq!(config.gain_db, 0.0);
    }

    #[test]
    fn test_envelope_config_defaults() {
        let config = EnvelopeConfig::default();
        assert_eq!(config.attack_ms, 10.0);
        assert_eq!(config.release_ms, 100.0);
        assert_eq!(config.sample_rate, 44100);
    }

    #[test]
    fn test_filter_creation() {
        let config = FilterConfig::default();
        let result = QFilterInstance::new(config, 44100);
        match result {
            Ok(filter) => {
                assert_eq!(filter.config().freq, 1000.0);
            }
            Err(e) => {
                println!("Filter creation failed (expected if Q not available): {}", e);
            }
        }
    }

    #[test]
    fn test_envelope_creation() {
        let config = EnvelopeConfig::default();
        let result = QEnvelopeFollower::new(config);
        match result {
            Ok(env) => {
                assert_eq!(env.config().attack_ms, 10.0);
            }
            Err(e) => {
                println!("Envelope creation failed (expected if Q not available): {}", e);
            }
        }
    }

    #[test]
    fn test_q_error_display() {
        let err = QError::InvalidFrequency;
        assert!(err.to_string().contains("Invalid frequency"));

        let err = QError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_pitch_result_structure() {
        let result = PitchResult {
            frequency: 440.0,
            confidence: 0.95,
            is_voiced: true,
        };
        assert_eq!(result.frequency, 440.0);
        assert_eq!(result.confidence, 0.95);
        assert!(result.is_voiced);
    }

    #[test]
    fn test_filter_type_variants() {
        let types = vec![
            FilterType::Lowpass,
            FilterType::Highpass,
            FilterType::Bandpass,
            FilterType::Notch,
            FilterType::Peak,
            FilterType::Lowshelf,
            FilterType::Highshelf,
        ];
        for t in types {
            assert!(!format!("{:?}", t).is_empty());
        }
    }
}
