//! Calf Studio Gear Plugins Integration
//!
//! FFI bindings to Calf Studio Gear - a comprehensive collection
//! of audio plugins including EQs, compressors, reverbs, and
//! virtual instruments.
//!
//! License: GPL-2.0+ (Calf)
//! Repo: https://calf-studio-gear.org/

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};
use std::path::Path;

/// Opaque handle to Calf plugin
#[repr(C)]
pub struct CalfPlugin {
    _private: [u8; 0],
}

/// Calf error types
#[derive(Debug, Clone, PartialEq)]
pub enum CalfError {
    LibraryInitFailed,
    PluginNotFound(String),
    PluginLoadFailed(String),
    InvalidParameter(String),
    FfiError(String),
}

impl std::fmt::Display for CalfError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CalfError::LibraryInitFailed => write!(f, "Calf library initialization failed"),
            CalfError::PluginNotFound(name) => write!(f, "Plugin not found: {}", name),
            CalfError::PluginLoadFailed(msg) => write!(f, "Plugin load failed: {}", msg),
            CalfError::InvalidParameter(msg) => write!(f, "Invalid parameter: {}", msg),
            CalfError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for CalfError {}

/// Plugin information
#[derive(Debug, Clone)]
pub struct CalfPluginInfo {
    pub id: u32,
    pub name: String,
    pub category: String,
    pub num_inputs: u32,
    pub num_outputs: u32,
    pub num_params: u32,
}

/// Parameter information
#[derive(Debug, Clone)]
pub struct CalfParamInfo {
    pub index: u32,
    pub name: String,
    pub min_value: f32,
    pub max_value: f32,
    pub default_value: f32,
}

/// Calf plugin host
pub struct CalfHost {
    library: *mut c_void,
}

/// Calf plugin instance
pub struct CalfInstance {
    plugin: *mut CalfPlugin,
    sample_rate: f64,
}

// FFI function declarations
extern "C" {
    fn calf_ffi_is_available() -> c_int;
    fn calf_ffi_get_version() -> *const c_char;
    
    // Library
    fn calf_ffi_library_init(path: *const c_char) -> *mut c_void;
    fn calf_ffi_library_free(library: *mut c_void);
    fn calf_ffi_get_plugin_count(library: *mut c_void) -> c_int;
    fn calf_ffi_get_plugin_info(library: *mut c_void, index: c_int, info: *mut CalfPluginInfoRaw) -> c_int;
    
    // Instance
    fn calf_ffi_instantiate(library: *mut c_void, plugin_id: c_uint, sample_rate: c_float) -> *mut CalfPlugin;
    fn calf_ffi_cleanup(plugin: *mut CalfPlugin);
    fn calf_ffi_activate(plugin: *mut CalfPlugin);
    fn calf_ffi_deactivate(plugin: *mut CalfPlugin);
    fn calf_ffi_process(plugin: *mut CalfPlugin, inputs: *const *const c_float, outputs: *mut *mut c_float, sample_count: c_uint);
    
    // Parameters
    fn calf_ffi_get_param_count(plugin: *mut CalfPlugin) -> c_uint;
    fn calf_ffi_get_param_info(plugin: *mut CalfPlugin, index: c_uint, info: *mut CalfParamInfoRaw) -> c_int;
    fn calf_ffi_set_param(plugin: *mut CalfPlugin, index: c_uint, value: c_float);
    fn calf_ffi_get_param(plugin: *mut CalfPlugin, index: c_uint) -> c_float;
}

#[repr(C)]
struct CalfPluginInfoRaw {
    id: c_uint,
    name: [c_char; 256],
    category: [c_char; 256],
    num_inputs: c_uint,
    num_outputs: c_uint,
    num_params: c_uint,
}

#[repr(C)]
struct CalfParamInfoRaw {
    index: c_uint,
    name: [c_char; 256],
    min_value: c_float,
    max_value: c_float,
    default_value: c_float,
}

impl CalfHost {
    /// Check if Calf is available
    pub fn is_available() -> bool {
        unsafe { calf_ffi_is_available() != 0 }
    }

    /// Get Calf version
    pub fn version() -> String {
        unsafe {
            let version_ptr = calf_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load plugin library
    pub fn load_library<P: AsRef<Path>>(path: P) -> Result<Self, CalfError> {
        if !Self::is_available() {
            return Err(CalfError::FfiError("Calf not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy();
        let c_path = CString::new(path_str.as_bytes())
            .map_err(|e| CalfError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let library = calf_ffi_library_init(c_path.as_ptr());
            if library.is_null() {
                return Err(CalfError::LibraryInitFailed);
            }

            Ok(Self { library })
        }
    }

    /// Get plugin count
    pub fn plugin_count(&self) -> usize {
        unsafe {
            calf_ffi_get_plugin_count(self.library) as usize
        }
    }

    /// Get all plugins
    pub fn get_all_plugins(&self) -> Vec<CalfPluginInfo> {
        let mut plugins = Vec::new();
        let count = self.plugin_count();

        for i in 0..count {
            unsafe {
                let mut raw_info: CalfPluginInfoRaw = std::mem::zeroed();
                if calf_ffi_get_plugin_info(self.library, i as c_int, &mut raw_info) == 0 {
                    let name = CStr::from_ptr(raw_info.name.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    let category = CStr::from_ptr(raw_info.category.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    
                    plugins.push(CalfPluginInfo {
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
    pub fn instantiate(&self, plugin_id: u32, sample_rate: f64) -> Result<CalfInstance, CalfError> {
        unsafe {
            let plugin = calf_ffi_instantiate(self.library, plugin_id, sample_rate as c_float);
            if plugin.is_null() {
                return Err(CalfError::PluginLoadFailed(format!("Failed to instantiate plugin {}", plugin_id)));
            }

            Ok(CalfInstance {
                plugin,
                sample_rate,
            })
        }
    }
}

impl Drop for CalfHost {
    fn drop(&mut self) {
        unsafe {
            if !self.library.is_null() {
                calf_ffi_library_free(self.library);
            }
        }
    }
}

impl CalfInstance {
    /// Activate plugin
    pub fn activate(&self) {
        unsafe {
            calf_ffi_activate(self.plugin);
        }
    }

    /// Deactivate plugin
    pub fn deactivate(&self) {
        unsafe {
            calf_ffi_deactivate(self.plugin);
        }
    }

    /// Get parameter count
    pub fn param_count(&self) -> u32 {
        unsafe {
            calf_ffi_get_param_count(self.plugin)
        }
    }

    /// Get parameter info
    pub fn get_param(&self, index: u32) -> Option<CalfParamInfo> {
        unsafe {
            let mut raw_info: CalfParamInfoRaw = std::mem::zeroed();
            if calf_ffi_get_param_info(self.plugin, index, &mut raw_info) != 0 {
                return None;
            }

            let name = CStr::from_ptr(raw_info.name.as_ptr())
                .to_string_lossy()
                .into_owned();

            Some(CalfParamInfo {
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
            calf_ffi_set_param(self.plugin, index, value);
        }
    }

    /// Get parameter value
    pub fn get_param_value(&self, index: u32) -> f32 {
        unsafe {
            calf_ffi_get_param(self.plugin, index)
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

            calf_ffi_process(
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

impl Drop for CalfInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.plugin.is_null() {
                calf_ffi_cleanup(self.plugin);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calf_module_exists() {
        let _ = CalfError::LibraryInitFailed;
    }

    #[test]
    fn test_calf_is_available() {
        let available = CalfHost::is_available();
        println!("Calf available: {}", available);
    }

    #[test]
    fn test_calf_version() {
        let version = CalfHost::version();
        println!("Calf version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_calf_error_display() {
        let err = CalfError::LibraryInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = CalfError::PluginNotFound("test".to_string());
        assert!(err.to_string().contains("Plugin not found"));

        let err = CalfError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_plugin_info_structure() {
        let info = CalfPluginInfo {
            id: 1,
            name: "Calf Reverb".to_string(),
            category: "Reverb".to_string(),
            num_inputs: 2,
            num_outputs: 2,
            num_params: 8,
        };
        
        assert_eq!(info.id, 1);
        assert_eq!(info.name, "Calf Reverb");
        assert_eq!(info.num_params, 8);
    }

    #[test]
    fn test_param_info_structure() {
        let param = CalfParamInfo {
            index: 0,
            name: "Room Size".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.5,
        };
        
        assert_eq!(param.index, 0);
        assert_eq!(param.name, "Room Size");
        assert_eq!(param.default_value, 0.5);
    }

    #[test]
    fn test_load_library_returns_error_when_unavailable() {
        if !CalfHost::is_available() {
            let result = CalfHost::load_library("/usr/lib/calf/calf.so");
            assert!(result.is_err());
        }
    }
}
