//! Surge XT Integration
//!
//! FFI bindings to Surge XT - one of the best open-source
//! hybrid synthesizers with multiple synthesis methods,
//! extensive modulation, and professional-quality filters.
//!
//! License: GPL-3.0
//! Repo: https://github.com/surge-synthesizer/surge

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// Opaque handle to Surge synthesizer
#[repr(C)]
pub struct SurgeSynth {
    _private: [u8; 0],
}

/// Surge error types
#[derive(Debug, Clone, PartialEq)]
pub enum SurgeError {
    SynthInitFailed,
    InvalidPatch(String),
    InvalidParameter(String),
    TuningLoadFailed(String),
    FfiError(String),
}

impl std::fmt::Display for SurgeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SurgeError::SynthInitFailed => write!(f, "Synthesizer initialization failed"),
            SurgeError::InvalidPatch(name) => write!(f, "Invalid patch: {}", name),
            SurgeError::InvalidParameter(param) => write!(f, "Invalid parameter: {}", param),
            SurgeError::TuningLoadFailed(path) => write!(f, "Failed to load tuning: {}", path),
            SurgeError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for SurgeError {}

/// Synthesis type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SurgeSynthesisType {
    Classic,
    Modern,
    Wavetable,
    Window,
    Sine,
    FM2,
    FM3,
    String,
    Twist,
    Alias,
}

/// Filter type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SurgeFilterType {
    Lowpass12,
    Lowpass24,
    Highpass12,
    Bandpass,
    Notch,
    Comb,
    Sampler,
}

/// Oscillator configuration
#[derive(Debug, Clone)]
pub struct SurgeOscConfig {
    pub synthesis_type: SurgeSynthesisType,
    pub pitch: f32,
    pub octave: i32,
}

impl Default for SurgeOscConfig {
    fn default() -> Self {
        Self {
            synthesis_type: SurgeSynthesisType::Classic,
            pitch: 0.0,
            octave: 0,
        }
    }
}

/// Filter configuration
#[derive(Debug, Clone)]
pub struct SurgeFilterConfig {
    pub filter_type: SurgeFilterType,
    pub cutoff: f32,
    pub resonance: f32,
}

impl Default for SurgeFilterConfig {
    fn default() -> Self {
        Self {
            filter_type: SurgeFilterType::Lowpass24,
            cutoff: 1000.0,
            resonance: 0.7,
        }
    }
}

/// LFO configuration
#[derive(Debug, Clone)]
pub struct SurgeLFOConfig {
    pub rate: f32,
    pub shape: String,
    pub amplitude: f32,
}

impl Default for SurgeLFOConfig {
    fn default() -> Self {
        Self {
            rate: 1.0,
            shape: "sine".to_string(),
            amplitude: 1.0,
        }
    }
}

/// Envelope configuration
#[derive(Debug, Clone)]
pub struct SurgeEnvelopeConfig {
    pub attack: f32,
    pub decay: f32,
    pub sustain: f32,
    pub release: f32,
}

impl Default for SurgeEnvelopeConfig {
    fn default() -> Self {
        Self {
            attack: 0.01,
            decay: 0.5,
            sustain: 0.5,
            release: 0.5,
        }
    }
}

/// Surge synthesizer instance
pub struct SurgeInstance {
    synth: *mut SurgeSynth,
    sample_rate: f64,
}

/// Surge patch info
#[derive(Debug, Clone)]
pub struct SurgePatchInfo {
    pub name: String,
    pub category: String,
    pub author: String,
}

// FFI function declarations
extern "C" {
    fn surge_ffi_is_available() -> c_int;
    fn surge_ffi_get_version() -> *const c_char;
    
    // Synth creation
    fn surge_ffi_create(sample_rate: c_float, block_size: c_int) -> *mut SurgeSynth;
    fn surge_ffi_destroy(synth: *mut SurgeSynth);
    
    // Processing
    fn surge_ffi_process(synth: *mut SurgeSynth, left: *mut c_float, right: *mut c_float, n_samples: c_int);
    fn surge_ffi_play_note(synth: *mut SurgeSynth, channel: c_int, note: c_int, velocity: c_int, detune: c_float);
    fn surge_ffi_release_note(synth: *mut SurgeSynth, channel: c_int, note: c_int, velocity: c_int);
    fn surge_ffi_all_notes_off(synth: *mut SurgeSynth, channel: c_int);
    
    // Parameters
    fn surge_ffi_set_parameter(synth: *mut SurgeSynth, id: c_int, value: c_float) -> c_int;
    fn surge_ffi_get_parameter(synth: *mut SurgeSynth, id: c_int) -> c_float;
    
    // Patches
    fn surge_ffi_load_patch(synth: *mut SurgeSynth, path: *const c_char) -> c_int;
    fn surge_ffi_get_patch_count(synth: *mut SurgeSynth) -> c_int;
    fn surge_ffi_get_patch_info(synth: *mut SurgeSynth, index: c_int, name: *mut c_char, category: *mut c_char, author: *mut c_char);
}

impl SurgeInstance {
    /// Create new Surge synthesizer
    pub fn new(sample_rate: f64, block_size: u32) -> Result<Self, SurgeError> {
        if !Self::is_available() {
            return Err(SurgeError::FfiError("Surge not available".to_string()));
        }

        unsafe {
            let synth = surge_ffi_create(sample_rate as c_float, block_size as c_int);
            if synth.is_null() {
                return Err(SurgeError::SynthInitFailed);
            }
            Ok(Self { synth, sample_rate })
        }
    }

    /// Check if Surge is available
    pub fn is_available() -> bool {
        unsafe { surge_ffi_is_available() != 0 }
    }

    /// Get Surge version
    pub fn version() -> String {
        unsafe {
            let version_ptr = surge_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Process audio
    pub fn process(&mut self, left: &mut [f32], right: &mut [f32]) {
        let n_samples = left.len().min(right.len()) as c_int;
        unsafe {
            surge_ffi_process(self.synth, left.as_mut_ptr(), right.as_mut_ptr(), n_samples);
        }
    }

    /// Play note
    pub fn play_note(&mut self, channel: i32, note: i32, velocity: i32, detune: f32) {
        unsafe {
            surge_ffi_play_note(self.synth, channel, note, velocity, detune);
        }
    }

    /// Release note
    pub fn release_note(&mut self, channel: i32, note: i32, velocity: i32) {
        unsafe {
            surge_ffi_release_note(self.synth, channel, note, velocity);
        }
    }

    /// All notes off
    pub fn all_notes_off(&mut self, channel: i32) {
        unsafe {
            surge_ffi_all_notes_off(self.synth, channel);
        }
    }

    /// Load patch
    pub fn load_patch(&mut self, path: &str) -> Result<(), SurgeError> {
        let path_cstring = CString::new(path)
            .map_err(|e| SurgeError::FfiError(e.to_string()))?;
        
        unsafe {
            let result = surge_ffi_load_patch(self.synth, path_cstring.as_ptr());
            if result != 0 {
                return Err(SurgeError::InvalidPatch(path.to_string()));
            }
            Ok(())
        }
    }

    /// Set parameter
    pub fn set_parameter(&mut self, id: i32, value: f32) -> Result<(), SurgeError> {
        unsafe {
            let result = surge_ffi_set_parameter(self.synth, id, value);
            if result != 0 {
                return Err(SurgeError::InvalidParameter(format!("id: {}", id)));
            }
            Ok(())
        }
    }

    /// Get parameter
    pub fn get_parameter(&self, id: i32) -> f32 {
        unsafe { surge_ffi_get_parameter(self.synth, id) }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> f64 {
        self.sample_rate
    }
}

impl Drop for SurgeInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.synth.is_null() {
                surge_ffi_destroy(self.synth);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_surge_module_exists() {
        let _ = SurgeError::SynthInitFailed;
        let _ = SurgeSynthesisType::Classic;
        let _ = SurgeFilterType::Lowpass24;
    }

    #[test]
    fn test_surge_is_available() {
        let available = SurgeInstance::is_available();
        println!("Surge available: {}", available);
    }

    #[test]
    fn test_surge_version() {
        let version = SurgeInstance::version();
        println!("Surge version: {}", version);
    }

    #[test]
    fn test_surge_create() {
        let result = SurgeInstance::new(44100.0, 32);
        match result {
            Ok(synth) => {
                assert_eq!(synth.sample_rate(), 44100.0);
            }
            Err(e) => {
                println!("Surge creation failed (expected if not available): {}", e);
            }
        }
    }

    #[test]
    fn test_osc_config_defaults() {
        let config = SurgeOscConfig::default();
        assert_eq!(config.synthesis_type, SurgeSynthesisType::Classic);
        assert_eq!(config.pitch, 0.0);
        assert_eq!(config.octave, 0);
    }

    #[test]
    fn test_filter_config_defaults() {
        let config = SurgeFilterConfig::default();
        assert_eq!(config.filter_type, SurgeFilterType::Lowpass24);
        assert_eq!(config.cutoff, 1000.0);
        assert_eq!(config.resonance, 0.7);
    }

    #[test]
    fn test_envelope_config_defaults() {
        let config = SurgeEnvelopeConfig::default();
        assert_eq!(config.attack, 0.01);
        assert_eq!(config.decay, 0.5);
        assert_eq!(config.sustain, 0.5);
        assert_eq!(config.release, 0.5);
    }

    #[test]
    fn test_lfo_config_defaults() {
        let config = SurgeLFOConfig::default();
        assert_eq!(config.rate, 1.0);
        assert_eq!(config.shape, "sine");
        assert_eq!(config.amplitude, 1.0);
    }

    #[test]
    fn test_surge_error_display() {
        let err = SurgeError::SynthInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = SurgeError::InvalidPatch("test".to_string());
        assert!(err.to_string().contains("Invalid patch"));
    }

    #[test]
    fn test_synthesis_types() {
        let types = vec![
            SurgeSynthesisType::Classic,
            SurgeSynthesisType::Modern,
            SurgeSynthesisType::Wavetable,
            SurgeSynthesisType::FM2,
            SurgeSynthesisType::String,
        ];
        for t in types {
            assert!(!format!("{:?}", t).is_empty());
        }
    }

    #[test]
    fn test_filter_types() {
        let types = vec![
            SurgeFilterType::Lowpass12,
            SurgeFilterType::Lowpass24,
            SurgeFilterType::Highpass12,
            SurgeFilterType::Bandpass,
            SurgeFilterType::Comb,
        ];
        for t in types {
            assert!(!format!("{:?}", t).is_empty());
        }
    }

    #[test]
    fn test_patch_info() {
        let info = SurgePatchInfo {
            name: "Init".to_string(),
            category: "Keys".to_string(),
            author: "Surge".to_string(),
        };
        assert_eq!(info.name, "Init");
        assert_eq!(info.category, "Keys");
    }
}
