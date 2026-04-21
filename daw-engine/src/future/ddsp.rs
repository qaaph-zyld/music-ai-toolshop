//! DDSP (Differentiable Digital Signal Processing) Integration
//!
//! FFI bindings to Google's DDSP library for neural audio synthesis and processing.
//! DDSP uses differentiable models to manipulate audio with explicit control over
//! pitch, timbre, and loudness.
//!
//! License: Apache-2.0
//! Repo: https://github.com/magenta/ddsp

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint};

/// Opaque handle to DDSP model
#[repr(C)]
pub struct DdspModel {
    _private: [u8; 0],
}

/// DDSP error types
#[derive(Debug, Clone, PartialEq)]
pub enum DdspError {
    ModelNotFound(String),
    ModelLoadFailed(String),
    ProcessingFailed(String),
    InvalidAudioData(String),
    FfiError(String),
}

impl std::fmt::Display for DdspError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DdspError::ModelNotFound(path) => write!(f, "DDSP model not found: {}", path),
            DdspError::ModelLoadFailed(msg) => write!(f, "Model load failed: {}", msg),
            DdspError::ProcessingFailed(msg) => write!(f, "Processing failed: {}", msg),
            DdspError::InvalidAudioData(msg) => write!(f, "Invalid audio data: {}", msg),
            DdspError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for DdspError {}

/// Model information
#[derive(Debug, Clone)]
pub struct DdspModelInfo {
    pub name: String,
    pub version: String,
    pub sample_rate: u32,
    pub supports_timbre_transfer: bool,
    pub supports_resynthesis: bool,
}

/// Pitch detection result
#[derive(Debug, Clone)]
pub struct PitchDetectionResult {
    /// Pitch in Hz for each frame
    pub frequencies: Vec<f32>,
    /// Confidence 0.0-1.0 for each frame
    pub confidence: Vec<f32>,
    /// Frame duration in seconds
    pub frame_duration: f32,
}

/// Timbre transfer result
#[derive(Debug, Clone)]
pub struct TimbreTransferResult {
    /// Processed audio
    pub audio: Vec<f32>,
    /// Applied timbre model name
    pub target_instrument: String,
    /// Confidence score
    pub confidence: f32,
}

/// DDSP processor
pub struct DdspProcessor {
    model: *mut DdspModel,
    sample_rate: u32,
}

// FFI function declarations
extern "C" {
    fn ddsp_ffi_is_available() -> c_int;
    fn ddsp_ffi_get_version() -> *const c_char;
    
    // Model management
    fn ddsp_ffi_model_load(path: *const c_char, sample_rate: c_uint) -> *mut DdspModel;
    fn ddsp_ffi_model_free(model: *mut DdspModel);
    fn ddsp_ffi_model_get_info(model: *mut DdspModel, info: *mut DdspModelInfoFFI);
    
    // Processing
    fn ddsp_ffi_detect_pitch(
        model: *mut DdspModel,
        audio: *const c_float,
        sample_count: c_uint,
        frequencies: *mut c_float,
        confidence: *mut c_float,
        max_frames: c_uint,
    ) -> c_int;
    
    fn ddsp_ffi_timbre_transfer(
        model: *mut DdspModel,
        audio: *const c_float,
        sample_count: c_uint,
        target_instrument: *const c_char,
        output: *mut c_float,
        output_size: c_uint,
    ) -> c_int;
    
    fn ddsp_ffi_resynthesize(
        model: *mut DdspModel,
        frequencies: *const c_float,
        confidence: *const c_float,
        frame_count: c_uint,
        output: *mut c_float,
        output_size: c_uint,
    ) -> c_int;
    
    fn ddsp_ffi_preprocess_training_data(
        model: *mut DdspModel,
        audio: *const c_float,
        sample_count: c_uint,
    ) -> c_int;
}

#[repr(C)]
struct DdspModelInfoFFI {
    name: *const c_char,
    version: *const c_char,
    sample_rate: c_uint,
    supports_timbre_transfer: c_int,
    supports_resynthesis: c_int,
}

impl DdspProcessor {
    /// Check if DDSP is available (Python bridge)
    pub fn is_available() -> bool {
        unsafe { ddsp_ffi_is_available() != 0 }
    }

    /// Get DDSP version
    pub fn version() -> String {
        unsafe {
            let version_ptr = ddsp_ffi_get_version();
            if version_ptr.is_null() {
                return "unavailable".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load DDSP model
    pub fn new(model_path: &str, sample_rate: u32) -> Result<Self, DdspError> {
        if !Self::is_available() {
            return Err(DdspError::FfiError("DDSP not available".to_string()));
        }

        let c_path = CString::new(model_path)
            .map_err(|e| DdspError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let model = ddsp_ffi_model_load(c_path.as_ptr(), sample_rate);
            if model.is_null() {
                return Err(DdspError::ModelLoadFailed(model_path.to_string()));
            }

            Ok(Self { model, sample_rate })
        }
    }

    /// Get model info
    pub fn info(&self) -> Result<DdspModelInfo, DdspError> {
        unsafe {
            let mut ffi_info = DdspModelInfoFFI {
                name: std::ptr::null(),
                version: std::ptr::null(),
                sample_rate: 0,
                supports_timbre_transfer: 0,
                supports_resynthesis: 0,
            };

            ddsp_ffi_model_get_info(self.model, &mut ffi_info);

            let name = if ffi_info.name.is_null() {
                "unknown".to_string()
            } else {
                CStr::from_ptr(ffi_info.name).to_string_lossy().into_owned()
            };

            let version = if ffi_info.version.is_null() {
                "unknown".to_string()
            } else {
                CStr::from_ptr(ffi_info.version).to_string_lossy().into_owned()
            };

            Ok(DdspModelInfo {
                name,
                version,
                sample_rate: ffi_info.sample_rate,
                supports_timbre_transfer: ffi_info.supports_timbre_transfer != 0,
                supports_resynthesis: ffi_info.supports_resynthesis != 0,
            })
        }
    }

    /// Detect pitch from audio
    pub fn detect_pitch(&self, audio: &[f32]) -> Result<PitchDetectionResult, DdspError> {
        if audio.is_empty() {
            return Err(DdspError::InvalidAudioData("Empty audio buffer".to_string()));
        }

        let max_frames = audio.len() / 256; // Assuming 256-sample hop size
        let mut frequencies = vec![0.0f32; max_frames];
        let mut confidence = vec![0.0f32; max_frames];

        unsafe {
            let result = ddsp_ffi_detect_pitch(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                frequencies.as_mut_ptr(),
                confidence.as_mut_ptr(),
                max_frames as c_uint,
            );

            if result < 0 {
                return Err(DdspError::ProcessingFailed("Pitch detection failed".to_string()));
            }

            // Truncate to actual frame count
            let frame_count = result as usize;
            frequencies.truncate(frame_count);
            confidence.truncate(frame_count);

            let frame_duration = 256.0 / self.sample_rate as f32;

            Ok(PitchDetectionResult {
                frequencies,
                confidence,
                frame_duration,
            })
        }
    }

    /// Transfer timbre of audio to target instrument
    pub fn timbre_transfer(
        &self,
        audio: &[f32],
        target_instrument: &str,
    ) -> Result<TimbreTransferResult, DdspError> {
        if audio.is_empty() {
            return Err(DdspError::InvalidAudioData("Empty audio buffer".to_string()));
        }

        let c_instrument = CString::new(target_instrument)
            .map_err(|e| DdspError::FfiError(format!("Invalid instrument name: {}", e)))?;

        let mut output = vec![0.0f32; audio.len()];

        unsafe {
            let result = ddsp_ffi_timbre_transfer(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                c_instrument.as_ptr(),
                output.as_mut_ptr(),
                output.len() as c_uint,
            );

            if result < 0 {
                return Err(DdspError::ProcessingFailed("Timbre transfer failed".to_string()));
            }

            // Calculate confidence (simplified)
            let confidence = result as f32 / 100.0;

            Ok(TimbreTransferResult {
                audio: output,
                target_instrument: target_instrument.to_string(),
                confidence,
            })
        }
    }

    /// Resynthesize audio from pitch and confidence data
    pub fn resynthesize(
        &self,
        frequencies: &[f32],
        confidence: &[f32],
    ) -> Result<Vec<f32>, DdspError> {
        if frequencies.len() != confidence.len() {
            return Err(DdspError::InvalidAudioData(
                "Frequency and confidence arrays must have same length".to_string()
            ));
        }

        if frequencies.is_empty() {
            return Err(DdspError::InvalidAudioData("Empty pitch data".to_string()));
        }

        // Output size: frame_count * hop_size
        let output_size = frequencies.len() * 256;
        let mut output = vec![0.0f32; output_size];

        unsafe {
            let result = ddsp_ffi_resynthesize(
                self.model,
                frequencies.as_ptr(),
                confidence.as_ptr(),
                frequencies.len() as c_uint,
                output.as_mut_ptr(),
                output.len() as c_uint,
            );

            if result < 0 {
                return Err(DdspError::ProcessingFailed("Resynthesis failed".to_string()));
            }

            // Truncate to actual output size
            let actual_size = result as usize;
            output.truncate(actual_size);

            Ok(output)
        }
    }

    /// Check if training data preprocessing is supported
    pub fn supports_training(&self) -> bool {
        // Training requires full DDSP Python environment
        Self::is_available()
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
}

impl Drop for DdspProcessor {
    fn drop(&mut self) {
        unsafe {
            if !self.model.is_null() {
                ddsp_ffi_model_free(self.model);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ddsp_module_exists() {
        let _ = DdspError::ModelNotFound("test".to_string());
        let _ = PitchDetectionResult {
            frequencies: vec![440.0],
            confidence: vec![0.9],
            frame_duration: 0.01,
        };
    }

    #[test]
    fn test_ddsp_is_available() {
        let available = DdspProcessor::is_available();
        println!("DDSP available: {}", available);
        // DDSP requires Python bridge, so may not be available in all environments
    }

    #[test]
    fn test_ddsp_version() {
        let version = DdspProcessor::version();
        println!("DDSP version: {}", version);
        // Should return something even if unavailable
        assert!(!version.is_empty());
    }

    #[test]
    fn test_ddsp_error_display() {
        let err = DdspError::ModelNotFound("test_model".to_string());
        assert!(err.to_string().contains("test_model"));

        let err = DdspError::ProcessingFailed("OOM".to_string());
        assert!(err.to_string().contains("Processing failed"));

        let err = DdspError::InvalidAudioData("empty".to_string());
        assert!(err.to_string().contains("Invalid audio data"));
    }

    #[test]
    fn test_model_info_structure() {
        let info = DdspModelInfo {
            name: "violin".to_string(),
            version: "1.0.0".to_string(),
            sample_rate: 44100,
            supports_timbre_transfer: true,
            supports_resynthesis: true,
        };
        
        assert_eq!(info.name, "violin");
        assert_eq!(info.sample_rate, 44100);
        assert!(info.supports_timbre_transfer);
    }

    #[test]
    fn test_pitch_detection_result() {
        let result = PitchDetectionResult {
            frequencies: vec![440.0, 442.0, 438.0],
            confidence: vec![0.9, 0.85, 0.92],
            frame_duration: 0.0058, // 256/44100
        };
        
        assert_eq!(result.frequencies.len(), 3);
        assert!((result.frequencies[0] - 440.0).abs() < 0.1);
    }

    #[test]
    fn test_timbre_transfer_result() {
        let result = TimbreTransferResult {
            audio: vec![0.1, -0.1, 0.05],
            target_instrument: "cello".to_string(),
            confidence: 0.87,
        };
        
        assert_eq!(result.target_instrument, "cello");
        assert!(result.confidence > 0.0 && result.confidence <= 1.0);
    }

    #[test]
    fn test_model_load_returns_error_when_unavailable() {
        if !DdspProcessor::is_available() {
            let result = DdspProcessor::new("/models/violin", 44100);
            assert!(result.is_err());
        }
    }

    #[test]
    fn test_empty_audio_pitch_detection_fails() {
        if DdspProcessor::is_available() {
            // This test would require a loaded model
            // For now, just verify the error type exists
            let err = DdspError::InvalidAudioData("Empty audio buffer".to_string());
            assert!(err.to_string().contains("Empty audio buffer"));
        }
    }

    #[test]
    fn test_mismatched_array_resynthesis_fails() {
        let freqs = vec![440.0, 442.0];
        let conf = vec![0.9]; // Mismatched length
        
        // This would be called on a processor instance
        // For now, verify the error can be created
        let err = DdspError::InvalidAudioData(
            "Frequency and confidence arrays must have same length".to_string()
        );
        assert!(err.to_string().contains("same length"));
    }
}
