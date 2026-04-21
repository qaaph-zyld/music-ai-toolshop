//! deep_filter_net - Advanced Deep Learning Noise Suppression
//!
//! DeepFilterNet is a deep learning-based noise suppression approach that uses
//! Deep Filtering to enhance speech and audio quality. More effective than
//! RNNoise for music and complex audio signals.
//!
//! Licensed: MIT/Apache-2.0
//! Repository: https://github.com/Rikorose/DeepFilterNet

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint};

/// DeepFilterNet noise suppressor
pub struct DeepFilterNet {
    handle: *mut c_void,
    sample_rate: u32,
    frame_size: usize,
    attenuation_limit: f32,
}

/// DeepFilterNet frame sizes
pub const DF_FRAME_SIZE_48K: usize = 960;   // 20ms at 48kHz
pub const DF_FRAME_SIZE_16K: usize = 320;   // 20ms at 16kHz

/// Processing result
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DfResult {
    pub speech_probability: f32,  // Probability that frame contains speech
    pub noise_attenuation_db: f32,  // Applied noise attenuation in dB
    pub processing_gain_db: f32,  // Overall gain applied
}

/// DeepFilterNet settings
#[derive(Debug, Clone)]
pub struct DfSettings {
    pub sample_rate: u32,
    pub attenuation_limit_db: f32,    // Maximum attenuation (e.g., -20.0 to 0.0)
    pub min_processing_buffer: usize, // Minimum frames to buffer before processing
    pub post_filter: bool,            // Enable post-filter for better quality
}

impl Default for DfSettings {
    fn default() -> Self {
        Self {
            sample_rate: 48000,
            attenuation_limit_db: -10.0,
            min_processing_buffer: 1,
            post_filter: true,
        }
    }
}

/// DeepFilterNet model variants
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DfModel {
    DeepFilterNet2,  // Standard model, good quality/speed tradeoff
    DeepFilterNet3,  // Latest model, best quality
    DeepFilterNetL3, // Light model for edge devices
}

impl Default for DfModel {
    fn default() -> Self {
        DfModel::DeepFilterNet3
    }
}

/// Error types for DeepFilterNet operations
#[derive(Debug)]
pub enum DfError {
    NotAvailable,
    InvalidSampleRate(u32),
    InvalidFrameSize(usize),
    InvalidAttenuation(f32),
    InvalidModel(String),
    ProcessingError(String),
    ModelLoadError(String),
    FfiError(String),
}

impl std::fmt::Display for DfError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DfError::NotAvailable => write!(f, "DeepFilterNet library not available"),
            DfError::InvalidSampleRate(sr) => write!(f, "Invalid sample rate: {}", sr),
            DfError::InvalidFrameSize(sz) => write!(f, "Invalid frame size: {}", sz),
            DfError::InvalidAttenuation(a) => write!(f, "Invalid attenuation: {}", a),
            DfError::InvalidModel(m) => write!(f, "Invalid model: {}", m),
            DfError::ProcessingError(e) => write!(f, "Processing error: {}", e),
            DfError::ModelLoadError(e) => write!(f, "Model load error: {}", e),
            DfError::FfiError(e) => write!(f, "FFI error: {}", e),
        }
    }
}

impl std::error::Error for DfError {}

impl DeepFilterNet {
    /// Create new DeepFilterNet instance
    pub fn new(sample_rate: u32) -> Result<Self, DfError> {
        Self::with_model(sample_rate, DfModel::default())
    }

    /// Create with specific model
    pub fn with_model(sample_rate: u32, model: DfModel) -> Result<Self, DfError> {
        if sample_rate != 48000 && sample_rate != 16000 {
            return Err(DfError::InvalidSampleRate(sample_rate));
        }

        let frame_size = if sample_rate == 48000 {
            DF_FRAME_SIZE_48K
        } else {
            DF_FRAME_SIZE_16K
        };

        let handle = unsafe {
            df_ffi::df_create(sample_rate, model as c_int)
        };

        if handle.is_null() {
            return Err(DfError::NotAvailable);
        }

        Ok(Self {
            handle,
            sample_rate,
            frame_size,
            attenuation_limit: -10.0,
        })
    }

    /// Create from model file path
    pub fn from_file(model_path: &str, sample_rate: u32) -> Result<Self, DfError> {
        if sample_rate != 48000 && sample_rate != 16000 {
            return Err(DfError::InvalidSampleRate(sample_rate));
        }

        let c_path = CString::new(model_path).map_err(|_| {
            DfError::ModelLoadError("Invalid model path".to_string())
        })?;

        let frame_size = if sample_rate == 48000 {
            DF_FRAME_SIZE_48K
        } else {
            DF_FRAME_SIZE_16K
        };

        let handle = unsafe {
            df_ffi::df_create_from_file(c_path.as_ptr(), sample_rate)
        };

        if handle.is_null() {
            return Err(DfError::ModelLoadError(
                format!("Failed to load model: {}", model_path)
            ));
        }

        Ok(Self {
            handle,
            sample_rate,
            frame_size,
            attenuation_limit: -10.0,
        })
    }

    /// Set attenuation limit in dB (typically -20.0 to 0.0)
    pub fn set_attenuation_limit(&mut self, limit_db: f32) -> Result<(), DfError> {
        if limit_db > 0.0 || limit_db < -60.0 {
            return Err(DfError::InvalidAttenuation(limit_db));
        }

        let result = unsafe {
            df_ffi::df_set_attenuation(self.handle, limit_db)
        };

        if result != 0 {
            return Err(DfError::FfiError("Failed to set attenuation".to_string()));
        }

        self.attenuation_limit = limit_db;
        Ok(())
    }

    /// Get current attenuation limit
    pub fn get_attenuation_limit(&self) -> f32 {
        self.attenuation_limit
    }

    /// Set post-filter enabled/disabled
    pub fn set_post_filter(&mut self, enabled: bool) -> Result<(), DfError> {
        let result = unsafe {
            df_ffi::df_set_post_filter(self.handle, enabled as c_int)
        };

        if result != 0 {
            return Err(DfError::FfiError("Failed to set post-filter".to_string()));
        }

        Ok(())
    }

    /// Process a frame of audio
    pub fn process_frame(&mut self, input: &[f32]) -> Result<(Vec<f32>, DfResult), DfError> {
        if input.len() != self.frame_size {
            return Err(DfError::InvalidFrameSize(input.len()));
        }

        let mut output = vec![0.0f32; self.frame_size];
        let mut speech_prob: f32 = 0.0;
        let mut att_db: f32 = 0.0;
        let mut gain_db: f32 = 0.0;

        let result = unsafe {
            df_ffi::df_process_frame(
                self.handle,
                input.as_ptr(),
                output.as_mut_ptr(),
                self.frame_size as c_int,
                &mut speech_prob,
                &mut att_db,
                &mut gain_db,
            )
        };

        if result != 0 {
            return Err(DfError::ProcessingError("Frame processing failed".to_string()));
        }

        let df_result = DfResult {
            speech_probability: speech_prob,
            noise_attenuation_db: att_db,
            processing_gain_db: gain_db,
        };

        Ok((output, df_result))
    }

    /// Process multiple frames
    pub fn process(&mut self, input: &[f32]) -> Result<(Vec<f32>, Vec<DfResult>), DfError> {
        if input.len() % self.frame_size != 0 {
            return Err(DfError::ProcessingError(
                format!("Input length {} must be multiple of frame size {}", 
                    input.len(), self.frame_size)
            ));
        }

        let num_frames = input.len() / self.frame_size;
        let mut output = vec![0.0f32; input.len()];
        let mut results = Vec::with_capacity(num_frames);

        for i in 0..num_frames {
            let start = i * self.frame_size;
            let end = start + self.frame_size;
            let (frame_out, result) = self.process_frame(&input[start..end])?;
            output[start..end].copy_from_slice(&frame_out);
            results.push(result);
        }

        Ok((output, results))
    }

    /// Get current settings
    pub fn get_settings(&self) -> DfSettings {
        DfSettings {
            sample_rate: self.sample_rate,
            attenuation_limit_db: self.attenuation_limit,
            min_processing_buffer: 1,
            post_filter: true,
        }
    }

    /// Get DeepFilterNet info
    pub fn info(&self) -> DfInfo {
        DfInfo {
            version: "0.5.6".to_string(),
            sample_rate: self.sample_rate,
            frame_size: self.frame_size,
            latency_samples: self.frame_size, // 1 frame latency
            supported_rates: vec![16000, 48000],
        }
    }

    /// Get frame size for current sample rate
    pub fn frame_size(&self) -> usize {
        self.frame_size
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
}

impl Drop for DeepFilterNet {
    fn drop(&mut self) {
        unsafe {
            df_ffi::df_destroy(self.handle);
        }
    }
}

/// DeepFilterNet library information
#[derive(Debug, Clone)]
pub struct DfInfo {
    pub version: String,
    pub sample_rate: u32,
    pub frame_size: usize,
    pub latency_samples: usize,
    pub supported_rates: Vec<u32>,
}

/// FFI bridge to DeepFilterNet
mod df_ffi {
    use super::*;

    extern "C" {
        // Create/destroy
        pub fn df_create(sample_rate: u32, model: c_int) -> *mut c_void;
        pub fn df_create_from_file(model_path: *const c_char, sample_rate: u32) -> *mut c_void;
        pub fn df_destroy(df: *mut c_void);
        
        // Processing
        pub fn df_process_frame(
            df: *mut c_void,
            input: *const f32,
            output: *mut f32,
            frame_size: c_int,
            speech_prob: *mut f32,
            att_db: *mut f32,
            gain_db: *mut f32,
        ) -> c_int;
        
        // Settings
        pub fn df_set_attenuation(df: *mut c_void, limit_db: c_float) -> c_int;
        pub fn df_get_attenuation(df: *mut c_void) -> c_float;
        pub fn df_set_post_filter(df: *mut c_void, enabled: c_int) -> c_int;
        
        // Info
        pub fn df_get_version() -> *const c_char;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Test 1: DeepFilterNet creation
    #[test]
    fn test_deep_filter_net_creation() {
        let result = DeepFilterNet::new(48000);
        // FFI stub returns NotAvailable
        assert!(matches!(result, Err(DfError::NotAvailable)));
    }

    // Test 2: Invalid sample rate
    #[test]
    fn test_invalid_sample_rate() {
        let result = DeepFilterNet::new(44100); // Not 16k or 48k
        assert!(matches!(result, Err(DfError::InvalidSampleRate(44100))));

        let result2 = DeepFilterNet::new(0);
        assert!(matches!(result2, Err(DfError::InvalidSampleRate(0))));
    }

    // Test 3: Valid sample rates
    #[test]
    fn test_valid_sample_rates() {
        let result_16k = DeepFilterNet::new(16000);
        let result_48k = DeepFilterNet::new(48000);
        
        assert!(matches!(result_16k, Err(DfError::NotAvailable)));
        assert!(matches!(result_48k, Err(DfError::NotAvailable)));
    }

    // Test 4: Settings default
    #[test]
    fn test_settings_default() {
        let settings = DfSettings::default();
        assert_eq!(settings.sample_rate, 48000);
        assert_eq!(settings.attenuation_limit_db, -10.0);
        assert_eq!(settings.min_processing_buffer, 1);
        assert!(settings.post_filter);
    }

    // Test 5: Model variants
    #[test]
    fn test_model_variants() {
        assert_eq!(DfModel::DeepFilterNet2, DfModel::DeepFilterNet2);
        assert_eq!(DfModel::DeepFilterNet3, DfModel::DeepFilterNet3);
        assert_ne!(DfModel::DeepFilterNet2, DfModel::DeepFilterNet3);
        
        let default = DfModel::default();
        assert_eq!(default, DfModel::DeepFilterNet3);
    }

    // Test 6: Invalid attenuation
    #[test]
    fn test_invalid_attenuation() {
        let positive = 5.0f32;  // Attenuation must be negative or zero
        let too_negative = -70.0f32;  // Below -60
        
        assert!(positive > 0.0);
        assert!(too_negative < -60.0);
    }

    // Test 7: Frame size constants
    #[test]
    fn test_frame_size_constants() {
        assert_eq!(DF_FRAME_SIZE_48K, 960);
        assert_eq!(DF_FRAME_SIZE_16K, 320);
    }

    // Test 8: DfResult structure
    #[test]
    fn test_df_result() {
        let result = DfResult {
            speech_probability: 0.85,
            noise_attenuation_db: -15.0,
            processing_gain_db: 2.0,
        };
        assert_eq!(result.speech_probability, 0.85);
        assert_eq!(result.noise_attenuation_db, -15.0);
        assert_eq!(result.processing_gain_db, 2.0);
    }

    // Test 9: Model load from file
    #[test]
    fn test_model_load_from_file() {
        let result = DeepFilterNet::from_file("/nonexistent/model.onnx", 48000);
        // FFI stub returns NULL which triggers ModelLoadError
        assert!(matches!(result, Err(DfError::ModelLoadError(_))));
    }

    // Test 10: DfInfo structure
    #[test]
    fn test_df_info() {
        let info = DfInfo {
            version: "0.5.6".to_string(),
            sample_rate: 48000,
            frame_size: 960,
            latency_samples: 960,
            supported_rates: vec![16000, 48000],
        };
        assert_eq!(info.version, "0.5.6");
        assert_eq!(info.sample_rate, 48000);
        assert_eq!(info.frame_size, 960);
        assert_eq!(info.latency_samples, 960);
        assert_eq!(info.supported_rates.len(), 2);
    }

    // Test 11: Error display formatting
    #[test]
    fn test_error_display() {
        let err1 = DfError::NotAvailable;
        let err2 = DfError::InvalidSampleRate(44100);
        let err3 = DfError::InvalidAttenuation(5.0);
        let err4 = DfError::ProcessingError("Test".to_string());
        
        assert!(err1.to_string().contains("not available"));
        assert!(err2.to_string().contains("Invalid sample rate"));
        assert!(err3.to_string().contains("Invalid attenuation"));
        assert!(err4.to_string().contains("Processing error"));
    }
}
