//! Rakarrack Effects Rack Integration
//!
//! FFI bindings to Rakarrack - a versatile effects processor
//! with a wide range of guitar and general audio effects.
//!
//! License: GPL-2.0+ (Rakarrack)
//! Repo: https://github.com/Stazed/rakarrack

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};
use std::path::Path;

/// Opaque handle to Rakarrack processor
#[repr(C)]
pub struct RakarrackProcessor {
    _private: [u8; 0],
}

/// Rakarrack error types
#[derive(Debug, Clone, PartialEq)]
pub enum RakarrackError {
    LibraryInitFailed,
    EffectNotFound(String),
    EffectLoadFailed(String),
    InvalidParameter(String),
    FfiError(String),
}

impl std::fmt::Display for RakarrackError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RakarrackError::LibraryInitFailed => write!(f, "Rakarrack library initialization failed"),
            RakarrackError::EffectNotFound(name) => write!(f, "Effect not found: {}", name),
            RakarrackError::EffectLoadFailed(msg) => write!(f, "Effect load failed: {}", msg),
            RakarrackError::InvalidParameter(msg) => write!(f, "Invalid parameter: {}", msg),
            RakarrackError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for RakarrackError {}

/// Effect information
#[derive(Debug, Clone)]
pub struct RakarrackEffectInfo {
    pub id: u32,
    pub name: String,
    pub category: String,
    pub num_inputs: u32,
    pub num_outputs: u32,
    pub num_params: u32,
}

/// Parameter information
#[derive(Debug, Clone)]
pub struct RakarrackParamInfo {
    pub index: u32,
    pub name: String,
    pub min_value: f32,
    pub max_value: f32,
    pub default_value: f32,
}

/// Rakarrack host
pub struct RakarrackHost {
    library: *mut c_void,
}

/// Rakarrack effect instance
pub struct RakarrackInstance {
    processor: *mut RakarrackProcessor,
    sample_rate: f64,
}

// FFI function declarations
extern "C" {
    fn rakarrack_ffi_is_available() -> c_int;
    fn rakarrack_ffi_get_version() -> *const c_char;
    
    // Library
    fn rakarrack_ffi_library_init(path: *const c_char) -> *mut c_void;
    fn rakarrack_ffi_library_free(library: *mut c_void);
    fn rakarrack_ffi_get_effect_count(library: *mut c_void) -> c_int;
    fn rakarrack_ffi_get_effect_info(library: *mut c_void, index: c_int, info: *mut RakarrackEffectInfoRaw) -> c_int;
    
    // Instance
    fn rakarrack_ffi_instantiate(library: *mut c_void, effect_id: c_uint, sample_rate: c_float) -> *mut RakarrackProcessor;
    fn rakarrack_ffi_cleanup(processor: *mut RakarrackProcessor);
    fn rakarrack_ffi_activate(processor: *mut RakarrackProcessor);
    fn rakarrack_ffi_deactivate(processor: *mut RakarrackProcessor);
    fn rakarrack_ffi_process(processor: *mut RakarrackProcessor, inputs: *const *const c_float, outputs: *mut *mut c_float, sample_count: c_uint);
    
    // Parameters
    fn rakarrack_ffi_get_param_count(processor: *mut RakarrackProcessor) -> c_uint;
    fn rakarrack_ffi_get_param_info(processor: *mut RakarrackProcessor, index: c_uint, info: *mut RakarrackParamInfoRaw) -> c_int;
    fn rakarrack_ffi_set_param(processor: *mut RakarrackProcessor, index: c_uint, value: c_float);
    fn rakarrack_ffi_get_param(processor: *mut RakarrackProcessor, index: c_uint) -> c_float;
}

#[repr(C)]
struct RakarrackEffectInfoRaw {
    id: c_uint,
    name: [c_char; 256],
    category: [c_char; 256],
    num_inputs: c_uint,
    num_outputs: c_uint,
    num_params: c_uint,
}

#[repr(C)]
struct RakarrackParamInfoRaw {
    index: c_uint,
    name: [c_char; 256],
    min_value: c_float,
    max_value: c_float,
    default_value: c_float,
}

impl RakarrackHost {
    /// Check if Rakarrack is available
    pub fn is_available() -> bool {
        unsafe { rakarrack_ffi_is_available() != 0 }
    }

    /// Get Rakarrack version
    pub fn version() -> String {
        unsafe {
            let version_ptr = rakarrack_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load library
    pub fn load_library<P: AsRef<Path>>(path: P) -> Result<Self, RakarrackError> {
        if !Self::is_available() {
            return Err(RakarrackError::FfiError("Rakarrack not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy();
        let c_path = CString::new(path_str.as_bytes())
            .map_err(|e| RakarrackError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let library = rakarrack_ffi_library_init(c_path.as_ptr());
            if library.is_null() {
                return Err(RakarrackError::LibraryInitFailed);
            }

            Ok(Self { library })
        }
    }

    /// Get effect count
    pub fn effect_count(&self) -> usize {
        unsafe {
            rakarrack_ffi_get_effect_count(self.library) as usize
        }
    }

    /// Get all effects
    pub fn get_all_effects(&self) -> Vec<RakarrackEffectInfo> {
        let mut effects = Vec::new();
        let count = self.effect_count();

        for i in 0..count {
            unsafe {
                let mut raw_info: RakarrackEffectInfoRaw = std::mem::zeroed();
                if rakarrack_ffi_get_effect_info(self.library, i as c_int, &mut raw_info) == 0 {
                    let name = CStr::from_ptr(raw_info.name.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    let category = CStr::from_ptr(raw_info.category.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    
                    effects.push(RakarrackEffectInfo {
                        id: raw_info.id,
                        name,
                        category,
                        num_inputs: raw_info.num_inputs,
                        num_outputs: raw_info.num_outputs,
                        num_params: raw_info.num_params,
                    });
                }
            }
        }

        effects
    }

    /// Instantiate effect
    pub fn instantiate(&self, effect_id: u32, sample_rate: f64) -> Result<RakarrackInstance, RakarrackError> {
        unsafe {
            let processor = rakarrack_ffi_instantiate(self.library, effect_id, sample_rate as c_float);
            if processor.is_null() {
                return Err(RakarrackError::EffectLoadFailed(format!("Failed to instantiate effect {}", effect_id)));
            }

            Ok(RakarrackInstance {
                processor,
                sample_rate,
            })
        }
    }
}

impl Drop for RakarrackHost {
    fn drop(&mut self) {
        unsafe {
            if !self.library.is_null() {
                rakarrack_ffi_library_free(self.library);
            }
        }
    }
}

impl RakarrackInstance {
    /// Activate
    pub fn activate(&self) {
        unsafe {
            rakarrack_ffi_activate(self.processor);
        }
    }

    /// Deactivate
    pub fn deactivate(&self) {
        unsafe {
            rakarrack_ffi_deactivate(self.processor);
        }
    }

    /// Get parameter count
    pub fn param_count(&self) -> u32 {
        unsafe {
            rakarrack_ffi_get_param_count(self.processor)
        }
    }

    /// Get parameter info
    pub fn get_param(&self, index: u32) -> Option<RakarrackParamInfo> {
        unsafe {
            let mut raw_info: RakarrackParamInfoRaw = std::mem::zeroed();
            if rakarrack_ffi_get_param_info(self.processor, index, &mut raw_info) != 0 {
                return None;
            }

            let name = CStr::from_ptr(raw_info.name.as_ptr())
                .to_string_lossy()
                .into_owned();

            Some(RakarrackParamInfo {
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
            rakarrack_ffi_set_param(self.processor, index, value);
        }
    }

    /// Get parameter value
    pub fn get_param_value(&self, index: u32) -> f32 {
        unsafe {
            rakarrack_ffi_get_param(self.processor, index)
        }
    }

    /// Process audio
    pub fn process(&self, inputs: &[&[f32]], outputs: &mut [&mut [f32]], sample_count: usize) {
        unsafe {
            let input_ptrs: Vec<*const c_float> = inputs.iter()
                .map(|buf| buf.as_ptr())
                .collect();
            let mut output_ptrs: Vec<*mut c_float> = outputs.iter_mut()
                .map(|buf| buf.as_mut_ptr())
                .collect();

            rakarrack_ffi_process(
                self.processor,
                input_ptrs.as_ptr(),
                output_ptrs.as_mut_ptr(),
                sample_count as c_uint,
            );
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> f64 {
        self.sample_rate
    }
}

impl Drop for RakarrackInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.processor.is_null() {
                rakarrack_ffi_cleanup(self.processor);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rakarrack_module_exists() {
        let _ = RakarrackError::LibraryInitFailed;
    }

    #[test]
    fn test_rakarrack_is_available() {
        let available = RakarrackHost::is_available();
        println!("Rakarrack available: {}", available);
    }

    #[test]
    fn test_rakarrack_version() {
        let version = RakarrackHost::version();
        println!("Rakarrack version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_rakarrack_error_display() {
        let err = RakarrackError::LibraryInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = RakarrackError::EffectNotFound("test".to_string());
        assert!(err.to_string().contains("Effect not found"));

        let err = RakarrackError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_effect_info_structure() {
        let info = RakarrackEffectInfo {
            id: 1,
            name: "Echo".to_string(),
            category: "Delay".to_string(),
            num_inputs: 2,
            num_outputs: 2,
            num_params: 4,
        };
        
        assert_eq!(info.id, 1);
        assert_eq!(info.name, "Echo");
        assert_eq!(info.num_params, 4);
    }

    #[test]
    fn test_param_info_structure() {
        let param = RakarrackParamInfo {
            index: 0,
            name: "Delay Time".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.5,
        };
        
        assert_eq!(param.index, 0);
        assert_eq!(param.name, "Delay Time");
        assert_eq!(param.default_value, 0.5);
    }

    #[test]
    fn test_load_library_returns_error_when_unavailable() {
        if !RakarrackHost::is_available() {
            let result = RakarrackHost::load_library("/usr/lib/rakarrack/rakarrack.so");
            assert!(result.is_err());
        }
    }
}
