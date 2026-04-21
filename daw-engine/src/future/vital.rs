//! Vital Integration
//!
//! FFI bindings to Vital - the powerful spectral warping
//! wavetable synthesizer with an exceptional free version.
//! Industry-grade sound quality with open-source core.
//!
//! License: GPL-3.0
//! Repo: https://github.com/mtytel/vital

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// Opaque handle to Vital synthesizer
#[repr(C)]
pub struct VitalSynth {
    _private: [u8; 0],
}

/// Vital error types
#[derive(Debug, Clone, PartialEq)]
pub enum VitalError {
    SynthInitFailed,
    InvalidPreset(String),
    WavetableLoadFailed(String),
    ModulationError(String),
    FfiError(String),
}

impl std::fmt::Display for VitalError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            VitalError::SynthInitFailed => write!(f, "Vital synthesizer initialization failed"),
            VitalError::InvalidPreset(name) => write!(f, "Invalid preset: {}", name),
            VitalError::WavetableLoadFailed(path) => write!(f, "Failed to load wavetable: {}", path),
            VitalError::ModulationError(msg) => write!(f, "Modulation error: {}", msg),
            VitalError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for VitalError {}

/// Oscillator type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VitalOscillatorType {
    Wavetable,
    WaveFold,
    Sine,
    SampleAndHold,
    AudioInput,
}

/// Filter type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VitalFilterType {
    LowPass,
    HighPass,
    BandPass,
    Notch,
    Comb,
    Formant,
    Diode,
    Dirty,
}

/// LFO shape
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VitalLFOShape {
    Sine,
    Triangle,
    Square,
    Saw,
    Random,
}

/// Modulation source
#[derive(Debug, Clone)]
pub enum VitalModSource {
    LFO1,
    LFO2,
    LFO3,
    Envelope1,
    Envelope2,
    Envelope3,
    Velocity,
    Aftertouch,
    ModWheel,
}

/// Oscillator configuration
#[derive(Debug, Clone)]
pub struct VitalOscConfig {
    pub osc_type: VitalOscillatorType,
    pub level: f32,
    pub pan: f32,
    pub spectral_morph: f32,
    pub spectral_unison: f32,
}

impl Default for VitalOscConfig {
    fn default() -> Self {
        Self {
            osc_type: VitalOscillatorType::Wavetable,
            level: 1.0,
            pan: 0.0,
            spectral_morph: 0.0,
            spectral_unison: 0.0,
        }
    }
}

/// Filter configuration
#[derive(Debug, Clone)]
pub struct VitalFilterConfig {
    pub filter_type: VitalFilterType,
    pub cutoff: f32,
    pub resonance: f32,
    pub drive: f32,
}

impl Default for VitalFilterConfig {
    fn default() -> Self {
        Self {
            filter_type: VitalFilterType::LowPass,
            cutoff: 20000.0,
            resonance: 0.0,
            drive: 0.0,
        }
    }
}

/// LFO configuration
#[derive(Debug, Clone)]
pub struct VitalLFOConfig {
    pub shape: VitalLFOShape,
    pub rate: f32,
    pub sync: bool,
    pub phase: f32,
}

impl Default for VitalLFOConfig {
    fn default() -> Self {
        Self {
            shape: VitalLFOShape::Sine,
            rate: 1.0,
            sync: false,
            phase: 0.0,
        }
    }
}

/// Envelope configuration
#[derive(Debug, Clone)]
pub struct VitalEnvelopeConfig {
    pub delay: f32,
    pub attack: f32,
    pub hold: f32,
    pub decay: f32,
    pub sustain: f32,
    pub release: f32,
}

impl Default for VitalEnvelopeConfig {
    fn default() -> Self {
        Self {
            delay: 0.0,
            attack: 0.0,
            hold: 0.0,
            decay: 0.5,
            sustain: 1.0,
            release: 0.5,
        }
    }
}

/// Modulation routing
#[derive(Debug, Clone)]
pub struct VitalModulation {
    pub source: VitalModSource,
    pub destination: String,
    pub amount: f32,
}

/// Vital synthesizer instance
pub struct VitalInstance {
    synth: *mut VitalSynth,
    sample_rate: f64,
}

/// Vital preset info
#[derive(Debug, Clone)]
pub struct VitalPresetInfo {
    pub name: String,
    pub author: String,
    pub category: String,
}

// FFI function declarations
extern "C" {
    fn vital_ffi_is_available() -> c_int;
    fn vital_ffi_get_version() -> *const c_char;
    
    // Synth creation
    fn vital_ffi_create(sample_rate: c_float) -> *mut VitalSynth;
    fn vital_ffi_destroy(synth: *mut VitalSynth);
    
    // Processing
    fn vital_ffi_process(synth: *mut VitalSynth, left: *mut c_float, right: *mut c_float, n_samples: c_int);
    fn vital_ffi_play_note(synth: *mut VitalSynth, note: c_int, velocity: c_int);
    fn vital_ffi_release_note(synth: *mut VitalSynth, note: c_int);
    fn vital_ffi_set_pitch_wheel(synth: *mut VitalSynth, value: c_float);
    fn vital_ffi_set_mod_wheel(synth: *mut VitalSynth, value: c_float);
    
    // Parameters
    fn vital_ffi_set_parameter(synth: *mut VitalSynth, name: *const c_char, value: c_float) -> c_int;
    fn vital_ffi_get_parameter(synth: *mut VitalSynth, name: *const c_char) -> c_float;
    
    // Presets
    fn vital_ffi_load_preset(synth: *mut VitalSynth, path: *const c_char) -> c_int;
    fn vital_ffi_get_preset_count(synth: *mut VitalSynth) -> c_int;
}

impl VitalInstance {
    /// Create new Vital synthesizer
    pub fn new(sample_rate: f64) -> Result<Self, VitalError> {
        if !Self::is_available() {
            return Err(VitalError::FfiError("Vital not available".to_string()));
        }

        unsafe {
            let synth = vital_ffi_create(sample_rate as c_float);
            if synth.is_null() {
                return Err(VitalError::SynthInitFailed);
            }
            Ok(Self { synth, sample_rate })
        }
    }

    /// Check if Vital is available
    pub fn is_available() -> bool {
        unsafe { vital_ffi_is_available() != 0 }
    }

    /// Get Vital version
    pub fn version() -> String {
        unsafe {
            let version_ptr = vital_ffi_get_version();
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
            vital_ffi_process(self.synth, left.as_mut_ptr(), right.as_mut_ptr(), n_samples);
        }
    }

    /// Play note
    pub fn play_note(&mut self, note: i32, velocity: i32) {
        unsafe {
            vital_ffi_play_note(self.synth, note, velocity);
        }
    }

    /// Release note
    pub fn release_note(&mut self, note: i32) {
        unsafe {
            vital_ffi_release_note(self.synth, note);
        }
    }

    /// Set pitch wheel
    pub fn set_pitch_wheel(&mut self, value: f32) {
        unsafe {
            vital_ffi_set_pitch_wheel(self.synth, value);
        }
    }

    /// Set mod wheel
    pub fn set_mod_wheel(&mut self, value: f32) {
        unsafe {
            vital_ffi_set_mod_wheel(self.synth, value);
        }
    }

    /// Set parameter by name
    pub fn set_parameter(&mut self, name: &str, value: f32) -> Result<(), VitalError> {
        let name_cstring = CString::new(name)
            .map_err(|e| VitalError::FfiError(e.to_string()))?;
        
        unsafe {
            let result = vital_ffi_set_parameter(self.synth, name_cstring.as_ptr(), value);
            if result != 0 {
                return Err(VitalError::InvalidPreset(name.to_string()));
            }
            Ok(())
        }
    }

    /// Get parameter by name
    pub fn get_parameter(&self, name: &str) -> f32 {
        let name_cstring = CString::new(name).ok();
        if name_cstring.is_none() {
            return 0.0;
        }
        
        unsafe {
            vital_ffi_get_parameter(self.synth, name_cstring.unwrap().as_ptr())
        }
    }

    /// Load preset
    pub fn load_preset(&mut self, path: &str) -> Result<(), VitalError> {
        let path_cstring = CString::new(path)
            .map_err(|e| VitalError::FfiError(e.to_string()))?;
        
        unsafe {
            let result = vital_ffi_load_preset(self.synth, path_cstring.as_ptr());
            if result != 0 {
                return Err(VitalError::InvalidPreset(path.to_string()));
            }
            Ok(())
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> f64 {
        self.sample_rate
    }
}

impl Drop for VitalInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.synth.is_null() {
                vital_ffi_destroy(self.synth);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vital_module_exists() {
        let _ = VitalError::SynthInitFailed;
        let _ = VitalOscillatorType::Wavetable;
        let _ = VitalFilterType::LowPass;
        let _ = VitalLFOShape::Sine;
    }

    #[test]
    fn test_vital_is_available() {
        let available = VitalInstance::is_available();
        println!("Vital available: {}", available);
    }

    #[test]
    fn test_vital_version() {
        let version = VitalInstance::version();
        println!("Vital version: {}", version);
    }

    #[test]
    fn test_vital_create() {
        let result = VitalInstance::new(48000.0);
        match result {
            Ok(synth) => {
                assert_eq!(synth.sample_rate(), 48000.0);
            }
            Err(e) => {
                println!("Vital creation failed (expected if not available): {}", e);
            }
        }
    }

    #[test]
    fn test_osc_config_defaults() {
        let config = VitalOscConfig::default();
        assert_eq!(config.osc_type, VitalOscillatorType::Wavetable);
        assert_eq!(config.level, 1.0);
        assert_eq!(config.pan, 0.0);
    }

    #[test]
    fn test_filter_config_defaults() {
        let config = VitalFilterConfig::default();
        assert_eq!(config.filter_type, VitalFilterType::LowPass);
        assert_eq!(config.cutoff, 20000.0);
    }

    #[test]
    fn test_lfo_config_defaults() {
        let config = VitalLFOConfig::default();
        assert_eq!(config.shape, VitalLFOShape::Sine);
        assert_eq!(config.rate, 1.0);
        assert!(!config.sync);
    }

    #[test]
    fn test_envelope_config_defaults() {
        let config = VitalEnvelopeConfig::default();
        assert_eq!(config.delay, 0.0);
        assert_eq!(config.attack, 0.0);
        assert_eq!(config.sustain, 1.0);
    }

    #[test]
    fn test_vital_error_display() {
        let err = VitalError::SynthInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = VitalError::InvalidPreset("test".to_string());
        assert!(err.to_string().contains("Invalid preset"));
    }

    #[test]
    fn test_oscillator_types() {
        let types = vec![
            VitalOscillatorType::Wavetable,
            VitalOscillatorType::WaveFold,
            VitalOscillatorType::Sine,
            VitalOscillatorType::SampleAndHold,
        ];
        for t in types {
            assert!(!format!("{:?}", t).is_empty());
        }
    }

    #[test]
    fn test_filter_types() {
        let types = vec![
            VitalFilterType::LowPass,
            VitalFilterType::HighPass,
            VitalFilterType::BandPass,
            VitalFilterType::Comb,
            VitalFilterType::Formant,
        ];
        for t in types {
            assert!(!format!("{:?}", t).is_empty());
        }
    }

    #[test]
    fn test_lfo_shapes() {
        let shapes = vec![
            VitalLFOShape::Sine,
            VitalLFOShape::Triangle,
            VitalLFOShape::Square,
            VitalLFOShape::Saw,
            VitalLFOShape::Random,
        ];
        for s in shapes {
            assert!(!format!("{:?}", s).is_empty());
        }
    }

    #[test]
    fn test_modulation_routing() {
        let mod_route = VitalModulation {
            source: VitalModSource::LFO1,
            destination: "filter_cutoff".to_string(),
            amount: 0.5,
        };
        
        assert_eq!(mod_route.amount, 0.5);
        assert_eq!(mod_route.destination, "filter_cutoff");
    }

    #[test]
    fn test_preset_info() {
        let info = VitalPresetInfo {
            name: "Bass".to_string(),
            author: "Vital".to_string(),
            category: "Bass".to_string(),
        };
        assert_eq!(info.name, "Bass");
        assert_eq!(info.category, "Bass");
    }
}
