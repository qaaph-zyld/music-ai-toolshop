//! TAP (Tom's Audio Processing) Plugins Integration
//!
//! FFI bindings to TAP - a collection of LADSPA plugins including
//! reverb, echo, equalizer, limiter, and other effects.
//!
//! License: GPL-2.0+ (TAP)
//! Repo: https://github.com/tomszilagyi/tap-plugins

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};
use std::path::Path;

/// Opaque handle to TAP plugin
#[repr(C)]
pub struct TapPlugin {
    _private: [u8; 0],
}

/// TAP error types
#[derive(Debug, Clone, PartialEq)]
pub enum TapError {
    LibraryInitFailed,
    PluginNotFound(String),
    PluginLoadFailed(String),
    InvalidParameter(String),
    FfiError(String),
}

impl std::fmt::Display for TapError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TapError::LibraryInitFailed => write!(f, "TAP library initialization failed"),
            TapError::PluginNotFound(name) => write!(f, "Plugin not found: {}", name),
            TapError::PluginLoadFailed(msg) => write!(f, "Plugin load failed: {}", msg),
            TapError::InvalidParameter(msg) => write!(f, "Invalid parameter: {}", msg),
            TapError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for TapError {}

/// Plugin information
#[derive(Debug, Clone)]
pub struct TapPluginInfo {
    pub id: u32,
    pub name: String,
    pub category: String,
    pub num_inputs: u32,
    pub num_outputs: u32,
    pub num_params: u32,
}

/// Parameter information
#[derive(Debug, Clone)]
pub struct TapParamInfo {
    pub index: u32,
    pub name: String,
    pub min_value: f32,
    pub max_value: f32,
    pub default_value: f32,
}

/// TAP plugin host
pub struct TapHost {
    library: *mut c_void,
}

/// TAP plugin instance
pub struct TapInstance {
    plugin: *mut TapPlugin,
    sample_rate: f64,
}

// FFI function declarations
extern "C" {
    fn tap_ffi_is_available() -> c_int;
    fn tap_ffi_get_version() -> *const c_char;
    
    // Library
    fn tap_ffi_library_init(path: *const c_char) -> *mut c_void;
    fn tap_ffi_library_free(library: *mut c_void);
    fn tap_ffi_get_plugin_count(library: *mut c_void) -> c_int;
    fn tap_ffi_get_plugin_info(library: *mut c_void, index: c_int, info: *mut TapPluginInfoRaw) -> c_int;
    
    // Instance
    fn tap_ffi_instantiate(library: *mut c_void, plugin_id: c_uint, sample_rate: c_float) -> *mut TapPlugin;
    fn tap_ffi_cleanup(plugin: *mut TapPlugin);
    fn tap_ffi_activate(plugin: *mut TapPlugin);
    fn tap_ffi_deactivate(plugin: *mut TapPlugin);
    fn tap_ffi_process(plugin: *mut TapPlugin, inputs: *const *const c_float, outputs: *mut *mut c_float, sample_count: c_uint);
    
    // Parameters
    fn tap_ffi_get_param_count(plugin: *mut TapPlugin) -> c_uint;
    fn tap_ffi_get_param_info(plugin: *mut TapPlugin, index: c_uint, info: *mut TapParamInfoRaw) -> c_int;
    fn tap_ffi_set_param(plugin: *mut TapPlugin, index: c_uint, value: c_float);
    fn tap_ffi_get_param(plugin: *mut TapPlugin, index: c_uint) -> c_float;
}

#[repr(C)]
struct TapPluginInfoRaw {
    id: c_uint,
    name: [c_char; 256],
    category: [c_char; 256],
    num_inputs: c_uint,
    num_outputs: c_uint,
    num_params: c_uint,
}

#[repr(C)]
struct TapParamInfoRaw {
    index: c_uint,
    name: [c_char; 256],
    min_value: c_float,
    max_value: c_float,
    default_value: c_float,
}

impl TapHost {
    /// Check if TAP is available
    pub fn is_available() -> bool {
        unsafe { tap_ffi_is_available() != 0 }
    }

    /// Get TAP version
    pub fn version() -> String {
        unsafe {
            let version_ptr = tap_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load plugin library
    pub fn load_library<P: AsRef<Path>>(path: P) -> Result<Self, TapError> {
        if !Self::is_available() {
            return Err(TapError::FfiError("TAP not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy();
        let c_path = CString::new(path_str.as_bytes())
            .map_err(|e| TapError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let library = tap_ffi_library_init(c_path.as_ptr());
            if library.is_null() {
                return Err(TapError::LibraryInitFailed);
            }

            Ok(Self { library })
        }
    }

    /// Get plugin count
    pub fn plugin_count(&self) -> usize {
        unsafe {
            tap_ffi_get_plugin_count(self.library) as usize
        }
    }

    /// Get all plugins
    pub fn get_all_plugins(&self) -> Vec<TapPluginInfo> {
        let mut plugins = Vec::new();
        let count = self.plugin_count();

        for i in 0..count {
            unsafe {
                let mut raw_info: TapPluginInfoRaw = std::mem::zeroed();
                if tap_ffi_get_plugin_info(self.library, i as c_int, &mut raw_info) == 0 {
                    let name = CStr::from_ptr(raw_info.name.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    let category = CStr::from_ptr(raw_info.category.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    
                    plugins.push(TapPluginInfo {
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

        plugins
    }

    /// Instantiate plugin
    pub fn instantiate(&self, plugin_id: u32, sample_rate: f64) -> Result<TapInstance, TapError> {
        unsafe {
            let plugin = tap_ffi_instantiate(self.library, plugin_id, sample_rate as c_float);
            if plugin.is_null() {
                return Err(TapError::PluginLoadFailed(format!("Failed to instantiate plugin {}", plugin_id)));
            }

            Ok(TapInstance {
                plugin,
                sample_rate,
            })
        }
    }
}

impl Drop for TapHost {
    fn drop(&mut self) {
        unsafe {
            if !self.library.is_null() {
                tap_ffi_library_free(self.library);
            }
        }
    }
}

impl TapInstance {
    /// Activate plugin
    pub fn activate(&self) {
        unsafe {
            tap_ffi_activate(self.plugin);
        }
    }

    /// Deactivate plugin
    pub fn deactivate(&self) {
        unsafe {
            tap_ffi_deactivate(self.plugin);
        }
    }

    /// Get parameter count
    pub fn param_count(&self) -> u32 {
        unsafe {
            tap_ffi_get_param_count(self.plugin)
        }
    }

    /// Get parameter info
    pub fn get_param(&self, index: u32) -> Option<TapParamInfo> {
        unsafe {
            let mut raw_info: TapParamInfoRaw = std::mem::zeroed();
            if tap_ffi_get_param_info(self.plugin, index, &mut raw_info) != 0 {
                return None;
            }

            let name = CStr::from_ptr(raw_info.name.as_ptr())
                .to_string_lossy()
                .into_owned();

            Some(TapParamInfo {
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
            tap_ffi_set_param(self.plugin, index, value);
        }
    }

    /// Get parameter value
    pub fn get_param_value(&self, index: u32) -> f32 {
        unsafe {
            tap_ffi_get_param(self.plugin, index)
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

            tap_ffi_process(
                self.plugin,
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

impl Drop for TapInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.plugin.is_null() {
                tap_ffi_cleanup(self.plugin);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tap_module_exists() {
        let _ = TapError::LibraryInitFailed;
    }

    #[test]
    fn test_tap_is_available() {
        let available = TapHost::is_available();
        println!("TAP available: {}", available);
    }

    #[test]
    fn test_tap_version() {
        let version = TapHost::version();
        println!("TAP version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_tap_error_display() {
        let err = TapError::LibraryInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = TapError::PluginNotFound("test".to_string());
        assert!(err.to_string().contains("Plugin not found"));

        let err = TapError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_plugin_info_structure() {
        let info = TapPluginInfo {
            id: 1,
            name: "TAP Reverb".to_string(),
            category: "Reverb".to_string(),
            num_inputs: 2,
            num_outputs: 2,
            num_params: 6,
        };
        
        assert_eq!(info.id, 1);
        assert_eq!(info.name, "TAP Reverb");
        assert_eq!(info.num_params, 6);
    }

    #[test]
    fn test_param_info_structure() {
        let param = TapParamInfo {
            index: 0,
            name: "Decay".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.5,
        };
        
        assert_eq!(param.index, 0);
        assert_eq!(param.name, "Decay");
        assert_eq!(param.default_value, 0.5);
    }

    #[test]
    fn test_load_library_returns_error_when_unavailable() {
        if !TapHost::is_available() {
            let result = TapHost::load_library("/usr/lib/tap/tap.so");
            assert!(result.is_err());
        }
    }
}
