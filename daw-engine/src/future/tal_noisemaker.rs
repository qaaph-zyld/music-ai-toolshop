//! TAL-NoiseMaker Synthesizer Integration
//!
//! FFI bindings to TAL-NoiseMaker - a virtual analog synthesizer
//! with effects. Simple yet powerful synth for electronic music.
//!
//! License: GPL-3.0 (TAL-NoiseMaker)
//! Repo: https://github.com/ftalbrecht/tal-noisemaker

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};
use std::path::Path;

/// Opaque handle to TAL-NoiseMaker synth
#[repr(C)]
pub struct TalNoiseMakerSynth {
    _private: [u8; 0],
}

/// TAL-NoiseMaker error types
#[derive(Debug, Clone, PartialEq)]
pub enum TalError {
    LibraryInitFailed,
    SynthLoadFailed(String),
    InvalidParameter(String),
    FfiError(String),
}

impl std::fmt::Display for TalError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TalError::LibraryInitFailed => write!(f, "TAL-NoiseMaker library initialization failed"),
            TalError::SynthLoadFailed(msg) => write!(f, "Synth load failed: {}", msg),
            TalError::InvalidParameter(msg) => write!(f, "Invalid parameter: {}", msg),
            TalError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for TalError {}

/// Synth information
#[derive(Debug, Clone)]
pub struct TalSynthInfo {
    pub version: String,
    pub num_params: u32,
    pub num_presets: u32,
}

/// Parameter information
#[derive(Debug, Clone)]
pub struct TalParamInfo {
    pub index: u32,
    pub name: String,
    pub min_value: f32,
    pub max_value: f32,
    pub default_value: f32,
}

/// Preset information
#[derive(Debug, Clone)]
pub struct TalPresetInfo {
    pub index: u32,
    pub name: String,
    pub category: String,
}

/// TAL-NoiseMaker host
pub struct TalHost {
    library: *mut c_void,
}

/// TAL-NoiseMaker synth instance
pub struct TalInstance {
    synth: *mut TalNoiseMakerSynth,
    sample_rate: f64,
}

// FFI function declarations
extern "C" {
    fn tal_ffi_is_available() -> c_int;
    fn tal_ffi_get_version() -> *const c_char;
    
    // Library
    fn tal_ffi_library_init(path: *const c_char) -> *mut c_void;
    fn tal_ffi_library_free(library: *mut c_void);
    fn tal_ffi_get_info(library: *mut c_void, info: *mut TalSynthInfoRaw) -> c_int;
    fn tal_ffi_get_preset_count(library: *mut c_void) -> c_uint;
    fn tal_ffi_get_preset_info(library: *mut c_void, index: c_uint, info: *mut TalPresetInfoRaw) -> c_int;
    
    // Instance
    fn tal_ffi_instantiate(library: *mut c_void, sample_rate: c_float) -> *mut TalNoiseMakerSynth;
    fn tal_ffi_cleanup(synth: *mut TalNoiseMakerSynth);
    fn tal_ffi_midi_note_on(synth: *mut TalNoiseMakerSynth, note: c_int, velocity: c_int);
    fn tal_ffi_midi_note_off(synth: *mut TalNoiseMakerSynth, note: c_int);
    fn tal_ffi_render(synth: *mut TalNoiseMakerSynth, outputs: *mut *mut c_float, sample_count: c_uint);
    fn tal_ffi_set_preset(synth: *mut TalNoiseMakerSynth, preset_index: c_uint);
    
    // Parameters
    fn tal_ffi_get_param_count(synth: *mut TalNoiseMakerSynth) -> c_uint;
    fn tal_ffi_get_param_info(synth: *mut TalNoiseMakerSynth, index: c_uint, info: *mut TalParamInfoRaw) -> c_int;
    fn tal_ffi_set_param(synth: *mut TalNoiseMakerSynth, index: c_uint, value: c_float);
    fn tal_ffi_get_param(synth: *mut TalNoiseMakerSynth, index: c_uint) -> c_float;
}

#[repr(C)]
struct TalSynthInfoRaw {
    version: [c_char; 32],
    num_params: c_uint,
    num_presets: c_uint,
}

#[repr(C)]
struct TalPresetInfoRaw {
    index: c_uint,
    name: [c_char; 256],
    category: [c_char; 256],
}

#[repr(C)]
struct TalParamInfoRaw {
    index: c_uint,
    name: [c_char; 256],
    min_value: c_float,
    max_value: c_float,
    default_value: c_float,
}

impl TalHost {
    /// Check if TAL-NoiseMaker is available
    pub fn is_available() -> bool {
        unsafe { tal_ffi_is_available() != 0 }
    }

    /// Get TAL-NoiseMaker version
    pub fn version() -> String {
        unsafe {
            let version_ptr = tal_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load library
    pub fn load_library<P: AsRef<Path>>(path: P) -> Result<Self, TalError> {
        if !Self::is_available() {
            return Err(TalError::FfiError("TAL-NoiseMaker not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy();
        let c_path = CString::new(path_str.as_bytes())
            .map_err(|e| TalError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let library = tal_ffi_library_init(c_path.as_ptr());
            if library.is_null() {
                return Err(TalError::LibraryInitFailed);
            }

            Ok(Self { library })
        }
    }

    /// Get synth info
    pub fn get_info(&self) -> Option<TalSynthInfo> {
        unsafe {
            let mut raw_info: TalSynthInfoRaw = std::mem::zeroed();
            if tal_ffi_get_info(self.library, &mut raw_info) != 0 {
                return None;
            }

            let version = CStr::from_ptr(raw_info.version.as_ptr())
                .to_string_lossy()
                .into_owned();

            Some(TalSynthInfo {
                version,
                num_params: raw_info.num_params,
                num_presets: raw_info.num_presets,
            })
        }
    }

    /// Get preset count
    pub fn preset_count(&self) -> u32 {
        unsafe {
            tal_ffi_get_preset_count(self.library)
        }
    }

    /// Get preset info
    pub fn get_preset(&self, index: u32) -> Option<TalPresetInfo> {
        unsafe {
            let mut raw_info: TalPresetInfoRaw = std::mem::zeroed();
            if tal_ffi_get_preset_info(self.library, index, &mut raw_info) != 0 {
                return None;
            }

            let name = CStr::from_ptr(raw_info.name.as_ptr())
                .to_string_lossy()
                .into_owned();
            let category = CStr::from_ptr(raw_info.category.as_ptr())
                .to_string_lossy()
                .into_owned();

            Some(TalPresetInfo {
                index: raw_info.index,
                name,
                category,
            })
        }
    }

    /// Instantiate synth
    pub fn instantiate(&self, sample_rate: f64) -> Result<TalInstance, TalError> {
        unsafe {
            let synth = tal_ffi_instantiate(self.library, sample_rate as c_float);
            if synth.is_null() {
                return Err(TalError::SynthLoadFailed("Failed to instantiate synth".to_string()));
            }

            Ok(TalInstance {
                synth,
                sample_rate,
            })
        }
    }
}

impl Drop for TalHost {
    fn drop(&mut self) {
        unsafe {
            if !self.library.is_null() {
                tal_ffi_library_free(self.library);
            }
        }
    }
}

impl TalInstance {
    /// MIDI note on
    pub fn note_on(&self, note: i32, velocity: i32) {
        unsafe {
            tal_ffi_midi_note_on(self.synth, note as c_int, velocity as c_int);
        }
    }

    /// MIDI note off
    pub fn note_off(&self, note: i32) {
        unsafe {
            tal_ffi_midi_note_off(self.synth, note as c_int);
        }
    }

    /// Render audio
    pub fn render(&self, outputs: &mut [&mut [f32]], sample_count: usize) {
        unsafe {
            let mut output_ptrs: Vec<*mut c_float> = outputs.iter_mut()
                .map(|buf| buf.as_mut_ptr())
                .collect();

            tal_ffi_render(
                self.synth,
                output_ptrs.as_mut_ptr(),
                sample_count as c_uint,
            );
        }
    }

    /// Set preset
    pub fn set_preset(&self, preset_index: u32) {
        unsafe {
            tal_ffi_set_preset(self.synth, preset_index);
        }
    }

    /// Get parameter count
    pub fn param_count(&self) -> u32 {
        unsafe {
            tal_ffi_get_param_count(self.synth)
        }
    }

    /// Get parameter info
    pub fn get_param(&self, index: u32) -> Option<TalParamInfo> {
        unsafe {
            let mut raw_info: TalParamInfoRaw = std::mem::zeroed();
            if tal_ffi_get_param_info(self.synth, index, &mut raw_info) != 0 {
                return None;
            }

            let name = CStr::from_ptr(raw_info.name.as_ptr())
                .to_string_lossy()
                .into_owned();

            Some(TalParamInfo {
                index: raw_info.index,
                name,
                min_value: raw_info.min_value,
                max_value: raw_info.max_value,
                default_value: raw_info.default_value,
            })
        }
    }

    /// Set parameter value
    pub fn set_param(&self, index: u32, value: f32) {
        unsafe {
            tal_ffi_set_param(self.synth, index, value);
        }
    }

    /// Get parameter value
    pub fn get_param_value(&self, index: u32) -> f32 {
        unsafe {
            tal_ffi_get_param(self.synth, index)
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> f64 {
        self.sample_rate
    }
}

impl Drop for TalInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.synth.is_null() {
                tal_ffi_cleanup(self.synth);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tal_module_exists() {
        let _ = TalError::LibraryInitFailed;
    }

    #[test]
    fn test_tal_is_available() {
        let available = TalHost::is_available();
        println!("TAL-NoiseMaker available: {}", available);
    }

    #[test]
    fn test_tal_version() {
        let version = TalHost::version();
        println!("TAL-NoiseMaker version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_tal_error_display() {
        let err = TalError::LibraryInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = TalError::SynthLoadFailed("test".to_string());
        assert!(err.to_string().contains("load failed"));

        let err = TalError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_synth_info_structure() {
        let info = TalSynthInfo {
            version: "1.0.0".to_string(),
            num_params: 32,
            num_presets: 128,
        };
        
        assert_eq!(info.version, "1.0.0");
        assert_eq!(info.num_params, 32);
        assert_eq!(info.num_presets, 128);
    }

    #[test]
    fn test_preset_info_structure() {
        let preset = TalPresetInfo {
            index: 0,
            name: "Init".to_string(),
            category: "Default".to_string(),
        };
        
        assert_eq!(preset.index, 0);
        assert_eq!(preset.name, "Init");
    }

    #[test]
    fn test_param_info_structure() {
        let param = TalParamInfo {
            index: 0,
            name: "Osc1 Waveform".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.0,
        };
        
        assert_eq!(param.index, 0);
        assert_eq!(param.name, "Osc1 Waveform");
    }

    #[test]
    fn test_load_library_returns_error_when_unavailable() {
        if !TalHost::is_available() {
            let result = TalHost::load_library("/usr/lib/tal/tal.so");
            assert!(result.is_err());
        }
    }
}
