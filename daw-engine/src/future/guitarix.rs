//! Guitarix Guitar Effects Processor Integration
//!
//! FFI bindings to Guitarix - a virtual guitar amplifier and effects
//! processor designed for use with JACK.
//!
//! License: GPL-3.0 (Guitarix)
//! Repo: https://github.com/brummer10/guitarix

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};
use std::path::Path;

/// Opaque handle to Guitarix processor
#[repr(C)]
pub struct GuitarixProcessor {
    _private: [u8; 0],
}

/// Guitarix error types
#[derive(Debug, Clone, PartialEq)]
pub enum GuitarixError {
    LibraryInitFailed,
    EffectNotFound(String),
    EffectLoadFailed(String),
    InvalidParameter(String),
    FfiError(String),
}

impl std::fmt::Display for GuitarixError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GuitarixError::LibraryInitFailed => write!(f, "Guitarix library initialization failed"),
            GuitarixError::EffectNotFound(name) => write!(f, "Effect not found: {}", name),
            GuitarixError::EffectLoadFailed(msg) => write!(f, "Effect load failed: {}", msg),
            GuitarixError::InvalidParameter(msg) => write!(f, "Invalid parameter: {}", msg),
            GuitarixError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for GuitarixError {}

/// Effect information
#[derive(Debug, Clone)]
pub struct GuitarixEffectInfo {
    pub id: u32,
    pub name: String,
    pub category: String,
    pub num_inputs: u32,
    pub num_outputs: u32,
    pub num_params: u32,
}

/// Parameter information
#[derive(Debug, Clone)]
pub struct GuitarixParamInfo {
    pub index: u32,
    pub name: String,
    pub min_value: f32,
    pub max_value: f32,
    pub default_value: f32,
}

/// Guitarix host
pub struct GuitarixHost {
    library: *mut c_void,
}

/// Guitarix effect instance
pub struct GuitarixInstance {
    processor: *mut GuitarixProcessor,
    sample_rate: f64,
}

// FFI function declarations
extern "C" {
    fn guitarix_ffi_is_available() -> c_int;
    fn guitarix_ffi_get_version() -> *const c_char;
    
    // Library
    fn guitarix_ffi_library_init(path: *const c_char) -> *mut c_void;
    fn guitarix_ffi_library_free(library: *mut c_void);
    fn guitarix_ffi_get_effect_count(library: *mut c_void) -> c_int;
    fn guitarix_ffi_get_effect_info(library: *mut c_void, index: c_int, info: *mut GuitarixEffectInfoRaw) -> c_int;
    
    // Instance
    fn guitarix_ffi_instantiate(library: *mut c_void, effect_id: c_uint, sample_rate: c_float) -> *mut GuitarixProcessor;
    fn guitarix_ffi_cleanup(processor: *mut GuitarixProcessor);
    fn guitarix_ffi_activate(processor: *mut GuitarixProcessor);
    fn guitarix_ffi_deactivate(processor: *mut GuitarixProcessor);
    fn guitarix_ffi_process(processor: *mut GuitarixProcessor, inputs: *const *const c_float, outputs: *mut *mut c_float, sample_count: c_uint);
    
    // Parameters
    fn guitarix_ffi_get_param_count(processor: *mut GuitarixProcessor) -> c_uint;
    fn guitarix_ffi_get_param_info(processor: *mut GuitarixProcessor, index: c_uint, info: *mut GuitarixParamInfoRaw) -> c_int;
    fn guitarix_ffi_set_param(processor: *mut GuitarixProcessor, index: c_uint, value: c_float);
    fn guitarix_ffi_get_param(processor: *mut GuitarixProcessor, index: c_uint) -> c_float;
}

#[repr(C)]
struct GuitarixEffectInfoRaw {
    id: c_uint,
    name: [c_char; 256],
    category: [c_char; 256],
    num_inputs: c_uint,
    num_outputs: c_uint,
    num_params: c_uint,
}

#[repr(C)]
struct GuitarixParamInfoRaw {
    index: c_uint,
    name: [c_char; 256],
    min_value: c_float,
    max_value: c_float,
    default_value: c_float,
}

impl GuitarixHost {
    /// Check if Guitarix is available
    pub fn is_available() -> bool {
        unsafe { guitarix_ffi_is_available() != 0 }
    }

    /// Get Guitarix version
    pub fn version() -> String {
        unsafe {
            let version_ptr = guitarix_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load library
    pub fn load_library<P: AsRef<Path>>(path: P) -> Result<Self, GuitarixError> {
        if !Self::is_available() {
            return Err(GuitarixError::FfiError("Guitarix not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy();
        let c_path = CString::new(path_str.as_bytes())
            .map_err(|e| GuitarixError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let library = guitarix_ffi_library_init(c_path.as_ptr());
            if library.is_null() {
                return Err(GuitarixError::LibraryInitFailed);
            }

            Ok(Self { library })
        }
    }

    /// Get effect count
    pub fn effect_count(&self) -> usize {
        unsafe {
            guitarix_ffi_get_effect_count(self.library) as usize
        }
    }

    /// Get all effects
    pub fn get_all_effects(&self) -> Vec<GuitarixEffectInfo> {
        let mut effects = Vec::new();
        let count = self.effect_count();

        for i in 0..count {
            unsafe {
                let mut raw_info: GuitarixEffectInfoRaw = std::mem::zeroed();
                if guitarix_ffi_get_effect_info(self.library, i as c_int, &mut raw_info) == 0 {
                    let name = CStr::from_ptr(raw_info.name.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    let category = CStr::from_ptr(raw_info.category.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    
                    effects.push(GuitarixEffectInfo {
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
    pub fn instantiate(&self, effect_id: u32, sample_rate: f64) -> Result<GuitarixInstance, GuitarixError> {
        unsafe {
            let processor = guitarix_ffi_instantiate(self.library, effect_id, sample_rate as c_float);
            if processor.is_null() {
                return Err(GuitarixError::EffectLoadFailed(format!("Failed to instantiate effect {}", effect_id)));
            }

            Ok(GuitarixInstance {
                processor,
                sample_rate,
            })
        }
    }
}

impl Drop for GuitarixHost {
    fn drop(&mut self) {
        unsafe {
            if !self.library.is_null() {
                guitarix_ffi_library_free(self.library);
            }
        }
    }
}

impl GuitarixInstance {
    /// Activate
    pub fn activate(&self) {
        unsafe {
            guitarix_ffi_activate(self.processor);
        }
    }

    /// Deactivate
    pub fn deactivate(&self) {
        unsafe {
            guitarix_ffi_deactivate(self.processor);
        }
    }

    /// Get parameter count
    pub fn param_count(&self) -> u32 {
        unsafe {
            guitarix_ffi_get_param_count(self.processor)
        }
    }

    /// Get parameter info
    pub fn get_param(&self, index: u32) -> Option<GuitarixParamInfo> {
        unsafe {
            let mut raw_info: GuitarixParamInfoRaw = std::mem::zeroed();
            if guitarix_ffi_get_param_info(self.processor, index, &mut raw_info) != 0 {
                return None;
            }

            let name = CStr::from_ptr(raw_info.name.as_ptr())
                .to_string_lossy()
                .into_owned();

            Some(GuitarixParamInfo {
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
            guitarix_ffi_set_param(self.processor, index, value);
        }
    }

    /// Get parameter value
    pub fn get_param_value(&self, index: u32) -> f32 {
        unsafe {
            guitarix_ffi_get_param(self.processor, index)
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

            guitarix_ffi_process(
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

impl Drop for GuitarixInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.processor.is_null() {
                guitarix_ffi_cleanup(self.processor);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_guitarix_module_exists() {
        let _ = GuitarixError::LibraryInitFailed;
    }

    #[test]
    fn test_guitarix_is_available() {
        let available = GuitarixHost::is_available();
        println!("Guitarix available: {}", available);
    }

    #[test]
    fn test_guitarix_version() {
        let version = GuitarixHost::version();
        println!("Guitarix version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_guitarix_error_display() {
        let err = GuitarixError::LibraryInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = GuitarixError::EffectNotFound("test".to_string());
        assert!(err.to_string().contains("Effect not found"));

        let err = GuitarixError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_effect_info_structure() {
        let info = GuitarixEffectInfo {
            id: 1,
            name: "Tube Screamer".to_string(),
            category: "Distortion".to_string(),
            num_inputs: 1,
            num_outputs: 1,
            num_params: 3,
        };
        
        assert_eq!(info.id, 1);
        assert_eq!(info.name, "Tube Screamer");
        assert_eq!(info.num_params, 3);
    }

    #[test]
    fn test_param_info_structure() {
        let param = GuitarixParamInfo {
            index: 0,
            name: "Drive".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.5,
        };
        
        assert_eq!(param.index, 0);
        assert_eq!(param.name, "Drive");
        assert_eq!(param.default_value, 0.5);
    }

    #[test]
    fn test_load_library_returns_error_when_unavailable() {
        if !GuitarixHost::is_available() {
            let result = GuitarixHost::load_library("/usr/lib/guitarix/guitarix.so");
            assert!(result.is_err());
        }
    }
}
