//! Lo-Fi ML Effects Integration
//!
//! FFI bindings for neural lo-fi audio processing effects.
//! Provides ML-based wow/flutter, tape saturation, vinyl noise,
//! and filter drift effects.
//!
//! License: MIT (hypothetical)

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint};

/// Opaque handle to Lo-Fi ML model
#[repr(C)]
pub struct LofiMlModel {
    _private: [u8; 0],
}

/// Lo-Fi ML error types
#[derive(Debug, Clone, PartialEq)]
pub enum LofiMlError {
    ModelNotFound(String),
    ModelLoadFailed(String),
    ProcessingFailed(String),
    InvalidAudioData(String),
    InvalidEffectChain(String),
    RealtimeNotSupported(String),
    FfiError(String),
}

impl std::fmt::Display for LofiMlError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LofiMlError::ModelNotFound(path) => write!(f, "Lo-Fi ML model not found: {}", path),
            LofiMlError::ModelLoadFailed(msg) => write!(f, "Model load failed: {}", msg),
            LofiMlError::ProcessingFailed(msg) => write!(f, "Processing failed: {}", msg),
            LofiMlError::InvalidAudioData(msg) => write!(f, "Invalid audio data: {}", msg),
            LofiMlError::InvalidEffectChain(msg) => write!(f, "Invalid effect chain: {}", msg),
            LofiMlError::RealtimeNotSupported(msg) => write!(f, "Realtime not supported: {}", msg),
            LofiMlError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for LofiMlError {}

/// Lo-Fi effect types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LofiEffectType {
    WowFlutter,
    TapeSaturation,
    VinylNoise,
    FilterDrift,
    BitCrush,
    SampleRateReduction,
    StereoDrift,
}

/// Lo-Fi effect with parameters
#[derive(Debug, Clone, Copy)]
pub struct LofiEffect {
    pub effect_type: LofiEffectType,
    pub amount: f32,      // 0.0 - 1.0
    pub variation: f32,   // Random variation amount
}

impl LofiEffect {
    /// Create new effect with amount
    pub fn new(effect_type: LofiEffectType, amount: f32) -> Self {
        Self {
            effect_type,
            amount: amount.clamp(0.0, 1.0),
            variation: 0.0,
        }
    }

    /// Set variation amount
    pub fn with_variation(mut self, variation: f32) -> Self {
        self.variation = variation.clamp(0.0, 1.0);
        self
    }
}

/// Processed audio result
#[derive(Debug, Clone)]
pub struct LofiProcessResult {
    pub audio: Vec<f32>,
    pub effects_applied: Vec<LofiEffectType>,
    pub processing_time_ms: f32,
    pub is_realtime_safe: bool,
}

/// Lo-Fi ML processor
pub struct LoFiMLProcessor {
    model: *mut LofiMlModel,
    effect_chain: Vec<LofiEffect>,
    sample_rate: u32,
}

// FFI function declarations
extern "C" {
    fn lofi_ml_ffi_is_available() -> c_int;
    fn lofi_ml_ffi_get_version() -> *const c_char;
    fn lofi_ml_ffi_is_realtime_safe() -> c_int;
    
    // Model management
    fn lofi_ml_ffi_model_load(sample_rate: c_uint) -> *mut LofiMlModel;
    fn lofi_ml_ffi_model_free(model: *mut LofiMlModel);
    
    // Effect processing
    fn lofi_ml_ffi_apply_wow_flutter(
        model: *mut LofiMlModel,
        audio: *const c_float,
        sample_count: c_uint,
        amount: c_float,
        output: *mut c_float,
    ) -> c_int;
    
    fn lofi_ml_ffi_apply_tape_saturation(
        model: *mut LofiMlModel,
        audio: *const c_float,
        sample_count: c_uint,
        amount: c_float,
        output: *mut c_float,
    ) -> c_int;
    
    fn lofi_ml_ffi_apply_vinyl_noise(
        model: *mut LofiMlModel,
        audio: *const c_float,
        sample_count: c_uint,
        amount: c_float,
        output: *mut c_float,
    ) -> c_int;
    
    fn lofi_ml_ffi_apply_filter_drift(
        model: *mut LofiMlModel,
        audio: *const c_float,
        sample_count: c_uint,
        amount: c_float,
        output: *mut c_float,
    ) -> c_int;
    
    fn lofi_ml_ffi_apply_bitcrush(
        model: *mut LofiMlModel,
        audio: *const c_float,
        sample_count: c_uint,
        amount: c_float,
        output: *mut c_float,
    ) -> c_int;
    
    fn lofi_ml_ffi_apply_sample_rate_reduction(
        model: *mut LofiMlModel,
        audio: *const c_float,
        sample_count: c_uint,
        amount: c_float,
        output: *mut c_float,
    ) -> c_int;
    
    fn lofi_ml_ffi_apply_stereo_drift(
        model: *mut LofiMlModel,
        audio_left: *const c_float,
        audio_right: *const c_float,
        sample_count: c_uint,
        amount: c_float,
        output_left: *mut c_float,
        output_right: *mut c_float,
    ) -> c_int;
    
    // Chain processing
    fn lofi_ml_ffi_process_chain(
        model: *mut LofiMlModel,
        audio: *const c_float,
        sample_count: c_uint,
        effect_chain: *const c_char,
        output: *mut c_float,
    ) -> c_int;
    
    // Presets
    fn lofi_ml_ffi_load_preset(
        model: *mut LofiMlModel,
        preset_name: *const c_char,
    ) -> c_int;
    
    fn lofi_ml_ffi_get_available_presets(
        presets_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
}

impl LoFiMLProcessor {
    /// Check if Lo-Fi ML is available
    pub fn is_available() -> bool {
        unsafe { lofi_ml_ffi_is_available() != 0 }
    }

    /// Check if realtime processing is supported
    pub fn is_realtime_safe() -> bool {
        unsafe { lofi_ml_ffi_is_realtime_safe() != 0 }
    }

    /// Get Lo-Fi ML version
    pub fn version() -> String {
        unsafe {
            let version_ptr = lofi_ml_ffi_get_version();
            if version_ptr.is_null() {
                return "unavailable".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get available presets
    pub fn available_presets() -> Vec<String> {
        if !Self::is_available() {
            return vec![];
        }

        let mut buffer = vec![0u8; 1024];
        unsafe {
            let result = lofi_ml_ffi_get_available_presets(
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return vec![];
            }

            let presets_str = CStr::from_ptr(buffer.as_ptr() as *const c_char)
                .to_string_lossy();
            
            presets_str
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect()
        }
    }

    /// Load Lo-Fi ML processor
    pub fn new(sample_rate: u32) -> Result<Self, LofiMlError> {
        if !Self::is_available() {
            return Err(LofiMlError::FfiError("Lo-Fi ML not available".to_string()));
        }

        unsafe {
            let model = lofi_ml_ffi_model_load(sample_rate);
            if model.is_null() {
                return Err(LofiMlError::ModelLoadFailed("Failed to load model".to_string()));
            }

            Ok(Self {
                model,
                effect_chain: vec![],
                sample_rate,
            })
        }
    }

    /// Add effect to chain
    pub fn add_effect(&mut self, effect: LofiEffect) {
        self.effect_chain.push(effect);
    }

    /// Clear effect chain
    pub fn clear_effects(&mut self) {
        self.effect_chain.clear();
    }

    /// Get current effect chain
    pub fn effect_chain(&self) -> &[LofiEffect] {
        &self.effect_chain
    }

    /// Load preset
    pub fn load_preset(&self, preset_name: &str) -> Result<(), LofiMlError> {
        let c_name = CString::new(preset_name)
            .map_err(|e| LofiMlError::FfiError(format!("Invalid preset name: {}", e)))?;

        unsafe {
            let result = lofi_ml_ffi_load_preset(self.model, c_name.as_ptr());
            if result < 0 {
                return Err(LofiMlError::ModelLoadFailed(format!("Preset not found: {}", preset_name)));
            }
            Ok(())
        }
    }

    /// Process audio with current effect chain
    pub fn process(&self, audio: &[f32]) -> Result<LofiProcessResult, LofiMlError> {
        if audio.is_empty() {
            return Err(LofiMlError::InvalidAudioData("Empty audio".to_string()));
        }

        if self.effect_chain.is_empty() {
            // No effects, return copy
            return Ok(LofiProcessResult {
                audio: audio.to_vec(),
                effects_applied: vec![],
                processing_time_ms: 0.0,
                is_realtime_safe: Self::is_realtime_safe(),
            });
        }

        let mut output = vec![0.0f32; audio.len()];

        unsafe {
            // Serialize effect chain for FFI
            let chain_str = self.serialize_effect_chain();
            let c_chain = CString::new(chain_str)
                .map_err(|e| LofiMlError::FfiError(format!("Chain serialization failed: {}", e)))?;

            let start_time = std::time::Instant::now();

            let result = lofi_ml_ffi_process_chain(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                c_chain.as_ptr(),
                output.as_mut_ptr(),
            );

            let processing_time = start_time.elapsed().as_millis() as f32;

            if result < 0 {
                return Err(LofiMlError::ProcessingFailed("Chain processing failed".to_string()));
            }

            let effects_applied = self.effect_chain.iter()
                .map(|e| e.effect_type)
                .collect();

            Ok(LofiProcessResult {
                audio: output,
                effects_applied,
                processing_time_ms: processing_time,
                is_realtime_safe: Self::is_realtime_safe(),
            })
        }
    }

    /// Apply single effect
    pub fn apply_effect(&self, audio: &[f32], effect: LofiEffect) -> Result<Vec<f32>, LofiMlError> {
        if audio.is_empty() {
            return Err(LofiMlError::InvalidAudioData("Empty audio".to_string()));
        }

        let mut output = vec![0.0f32; audio.len()];

        unsafe {
            let result = match effect.effect_type {
                LofiEffectType::WowFlutter => lofi_ml_ffi_apply_wow_flutter(
                    self.model, audio.as_ptr(), audio.len() as c_uint, effect.amount, output.as_mut_ptr()
                ),
                LofiEffectType::TapeSaturation => lofi_ml_ffi_apply_tape_saturation(
                    self.model, audio.as_ptr(), audio.len() as c_uint, effect.amount, output.as_mut_ptr()
                ),
                LofiEffectType::VinylNoise => lofi_ml_ffi_apply_vinyl_noise(
                    self.model, audio.as_ptr(), audio.len() as c_uint, effect.amount, output.as_mut_ptr()
                ),
                LofiEffectType::FilterDrift => lofi_ml_ffi_apply_filter_drift(
                    self.model, audio.as_ptr(), audio.len() as c_uint, effect.amount, output.as_mut_ptr()
                ),
                LofiEffectType::BitCrush => lofi_ml_ffi_apply_bitcrush(
                    self.model, audio.as_ptr(), audio.len() as c_uint, effect.amount, output.as_mut_ptr()
                ),
                LofiEffectType::SampleRateReduction => lofi_ml_ffi_apply_sample_rate_reduction(
                    self.model, audio.as_ptr(), audio.len() as c_uint, effect.amount, output.as_mut_ptr()
                ),
                LofiEffectType::StereoDrift => {
                    // Stereo drift requires left/right channels
                    return Err(LofiMlError::InvalidAudioData(
                        "Use apply_stereo_drift for stereo drift effect".to_string()
                    ));
                }
            };

            if result < 0 {
                return Err(LofiMlError::ProcessingFailed(format!("{:?} failed", effect.effect_type)));
            }

            Ok(output)
        }
    }

    /// Apply stereo drift effect
    pub fn apply_stereo_drift(
        &self,
        left: &[f32],
        right: &[f32],
        amount: f32,
    ) -> Result<(Vec<f32>, Vec<f32>), LofiMlError> {
        if left.len() != right.len() {
            return Err(LofiMlError::InvalidAudioData("Channel length mismatch".to_string()));
        }
        if left.is_empty() {
            return Err(LofiMlError::InvalidAudioData("Empty audio".to_string()));
        }

        let mut output_left = vec![0.0f32; left.len()];
        let mut output_right = vec![0.0f32; right.len()];

        unsafe {
            let result = lofi_ml_ffi_apply_stereo_drift(
                self.model,
                left.as_ptr(),
                right.as_ptr(),
                left.len() as c_uint,
                amount,
                output_left.as_mut_ptr(),
                output_right.as_mut_ptr(),
            );

            if result < 0 {
                return Err(LofiMlError::ProcessingFailed("Stereo drift failed".to_string()));
            }

            Ok((output_left, output_right))
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    fn serialize_effect_chain(&self) -> String {
        // Simple serialization: effect_type:amount,...
        self.effect_chain.iter()
            .map(|e| format!("{:?}:{:.2}", e.effect_type, e.amount))
            .collect::<Vec<_>>()
            .join(",")
    }
}

impl Drop for LoFiMLProcessor {
    fn drop(&mut self) {
        unsafe {
            if !self.model.is_null() {
                lofi_ml_ffi_model_free(self.model);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lofi_ml_module_exists() {
        let _ = LofiMlError::ModelNotFound("test".to_string());
        let _ = LofiEffectType::WowFlutter;
    }

    #[test]
    fn test_lofi_ml_is_available() {
        let available = LoFiMLProcessor::is_available();
        println!("Lo-Fi ML available: {}", available);
    }

    #[test]
    fn test_lofi_ml_is_realtime_safe() {
        let realtime = LoFiMLProcessor::is_realtime_safe();
        println!("Lo-Fi ML realtime safe: {}", realtime);
    }

    #[test]
    fn test_lofi_ml_version() {
        let version = LoFiMLProcessor::version();
        println!("Lo-Fi ML version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_lofi_ml_error_display() {
        let err = LofiMlError::ModelNotFound("test_model".to_string());
        assert!(err.to_string().contains("test_model"));

        let err = LofiMlError::ProcessingFailed("OOM".to_string());
        assert!(err.to_string().contains("Processing failed"));

        let err = LofiMlError::RealtimeNotSupported("high latency".to_string());
        assert!(err.to_string().contains("Realtime not supported"));
    }

    #[test]
    fn test_lofi_effect_types() {
        assert_eq!(LofiEffectType::WowFlutter, LofiEffectType::WowFlutter);
        assert_eq!(LofiEffectType::TapeSaturation, LofiEffectType::TapeSaturation);
        assert_ne!(LofiEffectType::VinylNoise, LofiEffectType::BitCrush);
    }

    #[test]
    fn test_lofi_effect_creation() {
        let effect = LofiEffect::new(LofiEffectType::WowFlutter, 0.5);
        assert_eq!(effect.effect_type, LofiEffectType::WowFlutter);
        assert!((effect.amount - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_lofi_effect_with_variation() {
        let effect = LofiEffect::new(LofiEffectType::TapeSaturation, 0.7)
            .with_variation(0.3);
        assert!((effect.variation - 0.3).abs() < 0.01);
    }

    #[test]
    fn test_lofi_effect_amount_clamping() {
        let effect_low = LofiEffect::new(LofiEffectType::FilterDrift, -0.5);
        assert_eq!(effect_low.amount, 0.0);

        let effect_high = LofiEffect::new(LofiEffectType::VinylNoise, 1.5);
        assert_eq!(effect_high.amount, 1.0);
    }

    #[test]
    fn test_processor_creation() {
        if LoFiMLProcessor::is_available() {
            let processor = LoFiMLProcessor::new(44100);
            assert!(processor.is_ok());
        }
    }

    #[test]
    fn test_processor_add_effect() {
        if LoFiMLProcessor::is_available() {
            let mut processor = LoFiMLProcessor::new(44100).unwrap();
            processor.add_effect(LofiEffect::new(LofiEffectType::WowFlutter, 0.5));
            assert_eq!(processor.effect_chain().len(), 1);
        }
    }

    #[test]
    fn test_processor_clear_effects() {
        if LoFiMLProcessor::is_available() {
            let mut processor = LoFiMLProcessor::new(44100).unwrap();
            processor.add_effect(LofiEffect::new(LofiEffectType::TapeSaturation, 0.6));
            processor.clear_effects();
            assert!(processor.effect_chain().is_empty());
        }
    }

    #[test]
    fn test_process_result_structure() {
        let result = LofiProcessResult {
            audio: vec![0.1, -0.1, 0.05],
            effects_applied: vec![LofiEffectType::WowFlutter, LofiEffectType::TapeSaturation],
            processing_time_ms: 12.5,
            is_realtime_safe: true,
        };
        
        assert_eq!(result.effects_applied.len(), 2);
        assert!(result.is_realtime_safe);
    }

    #[test]
    fn test_model_load_returns_error_when_unavailable() {
        if !LoFiMLProcessor::is_available() {
            let result = LoFiMLProcessor::new(44100);
            assert!(result.is_err());
        }
    }

    #[test]
    fn test_available_presets_returns_empty_when_unavailable() {
        let presets = LoFiMLProcessor::available_presets();
        if !LoFiMLProcessor::is_available() {
            assert!(presets.is_empty());
        }
    }
}
