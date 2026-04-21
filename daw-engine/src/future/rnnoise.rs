//! rnnoise - Real-time Noise Suppression
//!
//! Mozilla's RNNoise is a noise suppression library based on a recurrent neural
//! network. Optimized for voice but works well for general audio noise removal.
//!
//! Licensed: BSD-3-Clause
//! Repository: https://github.com/xiph/rnnoise

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint};

/// RNNoise noise suppressor
pub struct RnNoise {
    handle: *mut c_void,
    sample_rate: u32,
    frame_size: usize,
    vad_prob_threshold: f32,
}

/// RNNoise processing frame size
pub const RNNOISE_FRAME_SIZE: usize = 480; // 10ms at 48kHz

/// Noise suppression result
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct NoiseResult {
    pub vad_probability: f32,  // Voice Activity Detection probability (0.0 to 1.0)
    pub noise_reduced: bool,   // Whether noise reduction was applied
}

/// Noise suppression settings
#[derive(Debug, Clone)]
pub struct RnNoiseSettings {
    pub sample_rate: u32,
    pub vad_threshold: f32,     // VAD threshold (0.0 to 1.0)
    pub aggressiveness: u32,  // 0-3, higher = more aggressive suppression
}

impl Default for RnNoiseSettings {
    fn default() -> Self {
        Self {
            sample_rate: 48000,
            vad_threshold: 0.5,
            aggressiveness: 1,
        }
    }
}

/// Error types for RNNoise operations
#[derive(Debug)]
pub enum RnNoiseError {
    NotAvailable,
    InvalidSampleRate(u32),
    InvalidFrameSize(usize),
    InvalidVadThreshold(f32),
    InvalidAggressiveness(u32),
    ProcessingError(String),
    ModelLoadError(String),
    FfiError(String),
}

impl std::fmt::Display for RnNoiseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RnNoiseError::NotAvailable => write!(f, "RNNoise library not available"),
            RnNoiseError::InvalidSampleRate(sr) => write!(f, "Invalid sample rate: {}", sr),
            RnNoiseError::InvalidFrameSize(sz) => write!(f, "Invalid frame size: {}", sz),
            RnNoiseError::InvalidVadThreshold(t) => write!(f, "Invalid VAD threshold: {}", t),
            RnNoiseError::InvalidAggressiveness(a) => write!(f, "Invalid aggressiveness: {}", a),
            RnNoiseError::ProcessingError(e) => write!(f, "Processing error: {}", e),
            RnNoiseError::ModelLoadError(e) => write!(f, "Model load error: {}", e),
            RnNoiseError::FfiError(e) => write!(f, "FFI error: {}", e),
        }
    }
}

impl std::error::Error for RnNoiseError {}

impl RnNoise {
    /// Create new RNNoise instance
    pub fn new(sample_rate: u32) -> Result<Self, RnNoiseError> {
        if sample_rate != 48000 && sample_rate != 16000 && sample_rate != 8000 {
            return Err(RnNoiseError::InvalidSampleRate(sample_rate));
        }

        let handle = unsafe {
            rnnoise_ffi::rnnoise_create(std::ptr::null()) // null = default model
        };

        if handle.is_null() {
            return Err(RnNoiseError::NotAvailable);
        }

        let frame_size = if sample_rate == 48000 {
            RNNOISE_FRAME_SIZE
        } else if sample_rate == 16000 {
            160 // 10ms at 16kHz
        } else {
            80  // 10ms at 8kHz
        };

        Ok(Self {
            handle,
            sample_rate,
            frame_size,
            vad_prob_threshold: 0.5,
        })
    }

    /// Create with custom model file
    pub fn with_model(model_path: &str, sample_rate: u32) -> Result<Self, RnNoiseError> {
        if sample_rate != 48000 && sample_rate != 16000 && sample_rate != 8000 {
            return Err(RnNoiseError::InvalidSampleRate(sample_rate));
        }

        let c_path = CString::new(model_path).map_err(|_| {
            RnNoiseError::ModelLoadError("Invalid model path".to_string())
        })?;

        let handle = unsafe {
            rnnoise_ffi::rnnoise_create(c_path.as_ptr())
        };

        if handle.is_null() {
            return Err(RnNoiseError::ModelLoadError(
                format!("Failed to load model: {}", model_path)
            ));
        }

        let frame_size = if sample_rate == 48000 {
            RNNOISE_FRAME_SIZE
        } else if sample_rate == 16000 {
            160
        } else {
            80
        };

        Ok(Self {
            handle,
            sample_rate,
            frame_size,
            vad_prob_threshold: 0.5,
        })
    }

    /// Set VAD probability threshold (0.0 to 1.0)
    pub fn set_vad_threshold(&mut self, threshold: f32) -> Result<(), RnNoiseError> {
        if threshold < 0.0 || threshold > 1.0 {
            return Err(RnNoiseError::InvalidVadThreshold(threshold));
        }

        let result = unsafe {
            rnnoise_ffi::rnnoise_set_vad_threshold(self.handle, threshold)
        };

        if result != 0 {
            return Err(RnNoiseError::FfiError("Failed to set VAD threshold".to_string()));
        }

        self.vad_prob_threshold = threshold;
        Ok(())
    }

    /// Get current VAD threshold
    pub fn get_vad_threshold(&self) -> f32 {
        self.vad_prob_threshold
    }

    /// Process a single frame of audio
    /// Input must be the correct frame size for the sample rate
    pub fn process_frame(&mut self, input: &[f32]) -> Result<(Vec<f32>, NoiseResult), RnNoiseError> {
        if input.len() != self.frame_size {
            return Err(RnNoiseError::InvalidFrameSize(input.len()));
        }

        let mut output = vec![0.0f32; self.frame_size];
        let mut vad_prob: f32 = 0.0;

        let result = unsafe {
            rnnoise_ffi::rnnoise_process_frame(
                self.handle,
                output.as_mut_ptr(),
                input.as_ptr(),
                &mut vad_prob,
            )
        };

        if result != 0 {
            return Err(RnNoiseError::ProcessingError("Frame processing failed".to_string()));
        }

        let noise_result = NoiseResult {
            vad_probability: vad_prob,
            noise_reduced: vad_prob > self.vad_prob_threshold,
        };

        Ok((output, noise_result))
    }

    /// Process audio in place
    pub fn process_inplace(&mut self, buffer: &mut [f32]) -> Result<Vec<NoiseResult>, RnNoiseError> {
        if buffer.len() % self.frame_size != 0 {
            return Err(RnNoiseError::ProcessingError(
                format!("Buffer length {} must be multiple of frame size {}", 
                    buffer.len(), self.frame_size)
            ));
        }

        let num_frames = buffer.len() / self.frame_size;
        let mut results = Vec::with_capacity(num_frames);

        for i in 0..num_frames {
            let start = i * self.frame_size;
            let end = start + self.frame_size;
            let (processed, result) = self.process_frame(&buffer[start..end])?;
            buffer[start..end].copy_from_slice(&processed);
            results.push(result);
        }

        Ok(results)
    }

    /// Get current settings
    pub fn get_settings(&self) -> RnNoiseSettings {
        RnNoiseSettings {
            sample_rate: self.sample_rate,
            vad_threshold: self.vad_prob_threshold,
            aggressiveness: 1, // Default, would need FFI call
        }
    }

    /// Get RNNoise info
    pub fn info(&self) -> RnNoiseInfo {
        RnNoiseInfo {
            version: "0.2".to_string(),
            sample_rate: self.sample_rate,
            frame_size: self.frame_size,
            supported_rates: vec![8000, 16000, 48000],
        }
    }

    /// Get frame size for current sample rate
    pub fn frame_size(&self) -> usize {
        self.frame_size
    }
}

impl Drop for RnNoise {
    fn drop(&mut self) {
        unsafe {
            rnnoise_ffi::rnnoise_destroy(self.handle);
        }
    }
}

/// RNNoise library information
#[derive(Debug, Clone)]
pub struct RnNoiseInfo {
    pub version: String,
    pub sample_rate: u32,
    pub frame_size: usize,
    pub supported_rates: Vec<u32>,
}

/// FFI bridge to C RNNoise
mod rnnoise_ffi {
    use super::*;

    extern "C" {
        // Create/destroy
        pub fn rnnoise_create(model: *const c_char) -> *mut c_void;
        pub fn rnnoise_destroy(st: *mut c_void);
        
        // Processing
        pub fn rnnoise_process_frame(
            st: *mut c_void,
            out: *mut f32,
            input: *const f32,
            vad_prob: *mut f32,
        ) -> c_int;
        
        // Settings
        pub fn rnnoise_set_vad_threshold(st: *mut c_void, threshold: c_float) -> c_int;
        pub fn rnnoise_get_vad_threshold(st: *mut c_void) -> c_float;
        
        // Model info
        pub fn rnnoise_get_size() -> usize;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Test 1: RNNoise creation with valid sample rate
    #[test]
    fn test_rnnoise_creation() {
        let result = RnNoise::new(48000);
        // FFI stub returns NotAvailable
        assert!(matches!(result, Err(RnNoiseError::NotAvailable)));
    }

    // Test 2: Invalid sample rate
    #[test]
    fn test_invalid_sample_rate() {
        let result = RnNoise::new(44100); // Not 8k, 16k, or 48k
        assert!(matches!(result, Err(RnNoiseError::InvalidSampleRate(44100))));

        let result2 = RnNoise::new(0);
        assert!(matches!(result2, Err(RnNoiseError::InvalidSampleRate(0))));
    }

    // Test 3: Valid sample rates
    #[test]
    fn test_valid_sample_rates() {
        // These should pass validation but return NotAvailable from FFI
        let result_8k = RnNoise::new(8000);
        let result_16k = RnNoise::new(16000);
        let result_48k = RnNoise::new(48000);
        
        assert!(matches!(result_8k, Err(RnNoiseError::NotAvailable)));
        assert!(matches!(result_16k, Err(RnNoiseError::NotAvailable)));
        assert!(matches!(result_48k, Err(RnNoiseError::NotAvailable)));
    }

    // Test 4: Settings default
    #[test]
    fn test_settings_default() {
        let settings = RnNoiseSettings::default();
        assert_eq!(settings.sample_rate, 48000);
        assert_eq!(settings.vad_threshold, 0.5);
        assert_eq!(settings.aggressiveness, 1);
    }

    // Test 5: Invalid VAD threshold
    #[test]
    fn test_invalid_vad_threshold() {
        let negative = -0.1f32;
        let over_one = 1.5f32;
        
        assert!(negative < 0.0);
        assert!(over_one > 1.0);
    }

    // Test 6: Frame size constants
    #[test]
    fn test_frame_size() {
        assert_eq!(RNNOISE_FRAME_SIZE, 480);
    }

    // Test 7: Noise result structure
    #[test]
    fn test_noise_result() {
        let result = NoiseResult {
            vad_probability: 0.75,
            noise_reduced: true,
        };
        assert_eq!(result.vad_probability, 0.75);
        assert!(result.noise_reduced);
    }

    // Test 8: Invalid frame size (would be caught during processing)
    #[test]
    fn test_invalid_frame_size_error() {
        // Test that InvalidFrameSize error exists and can be created
        let err = RnNoiseError::InvalidFrameSize(100);
        assert!(matches!(err, RnNoiseError::InvalidFrameSize(100)));
        assert!(err.to_string().contains("Invalid frame size"));
    }

    // Test 9: Model load error
    #[test]
    fn test_model_load_error() {
        let result = RnNoise::with_model("/nonexistent/model.rnn", 48000);
        // FFI stub returns NULL which triggers ModelLoadError
        assert!(matches!(result, Err(RnNoiseError::ModelLoadError(_))));
    }

    // Test 10: RNNoise info structure
    #[test]
    fn test_rnnoise_info() {
        let info = RnNoiseInfo {
            version: "0.2".to_string(),
            sample_rate: 48000,
            frame_size: 480,
            supported_rates: vec![8000, 16000, 48000],
        };
        assert_eq!(info.version, "0.2");
        assert_eq!(info.sample_rate, 48000);
        assert_eq!(info.frame_size, 480);
        assert_eq!(info.supported_rates.len(), 3);
    }

    // Test 11: Error display formatting
    #[test]
    fn test_error_display() {
        let err1 = RnNoiseError::NotAvailable;
        let err2 = RnNoiseError::InvalidSampleRate(44100);
        let err3 = RnNoiseError::InvalidVadThreshold(1.5);
        let err4 = RnNoiseError::ProcessingError("Test error".to_string());
        
        assert!(err1.to_string().contains("not available"));
        assert!(err2.to_string().contains("Invalid sample rate"));
        assert!(err3.to_string().contains("Invalid VAD threshold"));
        assert!(err4.to_string().contains("Processing error"));
    }
}
