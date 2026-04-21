//! LADSPA Plugin Host Integration
//!
//! FFI bindings to LADSPA (Linux Audio Developer's Simple Plugin API).
//! LADSPA is a standard for audio plugins on Linux, supported by many
//! DAWs including Ardour, Audacity, and LMMS.
//!
//! License: LGPL-2.1+ (LADSDK)
//! Repo: https://www.ladspa.org/

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};
use std::path::Path;

/// Opaque handle to LADSPA descriptor
#[repr(C)]
pub struct LadspaDescriptor {
    _private: [u8; 0],
}

/// Opaque handle to LADSPA instance
#[repr(C)]
pub struct LadspaHandle {
    _private: [u8; 0],
}

/// LADSPA port descriptor
#[repr(C)]
pub struct LadspaPort {
    _private: [u8; 0],
}

/// LADSPA error types
#[derive(Debug, Clone, PartialEq)]
pub enum LadspaError {
    LibraryInitFailed,
    PluginNotFound(String),
    PluginLoadFailed(String),
    PortNotFound(String),
    InvalidLabel(String),
    FfiError(String),
}

impl std::fmt::Display for LadspaError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LadspaError::LibraryInitFailed => write!(f, "LADSPA library initialization failed"),
            LadspaError::PluginNotFound(label) => write!(f, "Plugin not found: {}", label),
            LadspaError::PluginLoadFailed(msg) => write!(f, "Plugin load failed: {}", msg),
            LadspaError::PortNotFound(name) => write!(f, "Port not found: {}", name),
            LadspaError::InvalidLabel(label) => write!(f, "Invalid plugin label: {}", label),
            LadspaError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for LadspaError {}

/// Plugin information
#[derive(Debug, Clone)]
pub struct LadspaPluginInfo {
    pub unique_id: u64,
    pub label: String,
    pub name: String,
    pub maker: String,
    pub copyright: String,
    pub num_ports: u32,
}

/// Port information
#[derive(Debug, Clone)]
pub struct LadspaPortInfo {
    pub index: u32,
    pub name: String,
    pub is_audio: bool,
    pub is_control: bool,
    pub is_input: bool,
    pub is_output: bool,
    pub min_value: Option<f32>,
    pub max_value: Option<f32>,
    pub default_value: Option<f32>,
}

/// Port type enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PortType {
    Audio,
    Control,
}

/// Port direction enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PortDirection {
    Input,
    Output,
}

/// LADSPA plugin host
pub struct LadspaHost {
    library: *mut c_void,
}

/// LADSPA plugin instance
pub struct LadspaInstance {
    descriptor: *mut LadspaDescriptor,
    handle: *mut LadspaHandle,
    sample_rate: f64,
}

// FFI function declarations
extern "C" {
    fn ladspa_ffi_is_available() -> c_int;
    fn ladspa_ffi_get_version() -> *const c_char;
    
    // Library
    fn ladspa_ffi_library_init(path: *const c_char) -> *mut c_void;
    fn ladspa_ffi_library_free(library: *mut c_void);
    fn ladspa_ffi_library_get_descriptor_count(library: *mut c_void) -> c_int;
    fn ladspa_ffi_library_get_descriptor(library: *mut c_void, index: c_int) -> *mut LadspaDescriptor;
    fn ladspa_ffi_library_get_descriptor_by_label(library: *mut c_void, label: *const c_char) -> *mut LadspaDescriptor;
    
    // Plugin info
    fn ladspa_ffi_descriptor_get_unique_id(descriptor: *mut LadspaDescriptor) -> c_uint;
    fn ladspa_ffi_descriptor_get_label(descriptor: *mut LadspaDescriptor) -> *const c_char;
    fn ladspa_ffi_descriptor_get_name(descriptor: *mut LadspaDescriptor) -> *const c_char;
    fn ladspa_ffi_descriptor_get_maker(descriptor: *mut LadspaDescriptor) -> *const c_char;
    fn ladspa_ffi_descriptor_get_copyright(descriptor: *mut LadspaDescriptor) -> *const c_char;
    fn ladspa_ffi_descriptor_get_num_ports(descriptor: *mut LadspaDescriptor) -> c_uint;
    
    // Instance
    fn ladspa_ffi_instantiate(descriptor: *mut LadspaDescriptor, sample_rate: c_uint) -> *mut LadspaHandle;
    fn ladspa_ffi_cleanup(descriptor: *mut LadspaDescriptor, handle: *mut LadspaHandle);
    fn ladspa_ffi_activate(descriptor: *mut LadspaDescriptor, handle: *mut LadspaHandle);
    fn ladspa_ffi_deactivate(descriptor: *mut LadspaDescriptor, handle: *mut LadspaHandle);
    fn ladspa_ffi_run(descriptor: *mut LadspaDescriptor, handle: *mut LadspaHandle, sample_count: c_uint);
    
    // Port info
    fn ladspa_ffi_port_get_name(descriptor: *mut LadspaDescriptor, port_index: c_uint) -> *const c_char;
    fn ladspa_ffi_port_is_audio(descriptor: *mut LadspaDescriptor, port_index: c_uint) -> c_int;
    fn ladspa_ffi_port_is_control(descriptor: *mut LadspaDescriptor, port_index: c_uint) -> c_int;
    fn ladspa_ffi_port_is_input(descriptor: *mut LadspaDescriptor, port_index: c_uint) -> c_int;
    fn ladspa_ffi_port_is_output(descriptor: *mut LadspaDescriptor, port_index: c_uint) -> c_int;
    fn ladspa_ffi_port_get_range(descriptor: *mut LadspaDescriptor, port_index: c_uint, min: *mut c_float, max: *mut c_float, default_val: *mut c_float);
    
    // Port data
    fn ladspa_ffi_connect_port(descriptor: *mut LadspaDescriptor, handle: *mut LadspaHandle, port: c_uint, data: *mut c_float);
}

impl LadspaHost {
    /// Check if LADSPA is available
    pub fn is_available() -> bool {
        unsafe { ladspa_ffi_is_available() != 0 }
    }

    /// Get LADSPA version
    pub fn version() -> String {
        unsafe {
            let version_ptr = ladspa_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load plugin library
    pub fn load_library<P: AsRef<Path>>(path: P) -> Result<Self, LadspaError> {
        if !Self::is_available() {
            return Err(LadspaError::FfiError("LADSPA not available".to_string()));
        }

        let path_str = path.as_ref().to_string_lossy();
        let c_path = CString::new(path_str.as_bytes())
            .map_err(|e| LadspaError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let library = ladspa_ffi_library_init(c_path.as_ptr());
            if library.is_null() {
                return Err(LadspaError::LibraryInitFailed);
            }

            Ok(Self { library })
        }
    }

    /// Get number of plugins in library
    pub fn plugin_count(&self) -> usize {
        unsafe {
            ladspa_ffi_library_get_descriptor_count(self.library) as usize
        }
    }

    /// Get all plugins in library
    pub fn get_all_plugins(&self) -> Vec<LadspaPluginInfo> {
        let mut plugins = Vec::new();
        let count = self.plugin_count();

        for i in 0..count {
            unsafe {
                let descriptor = ladspa_ffi_library_get_descriptor(self.library, i as c_int);
                if !descriptor.is_null() {
                    if let Some(info) = Self::get_plugin_info(descriptor) {
                        plugins.push(info);
                    }
                }
            }
        }

        plugins
    }

    /// Get plugin by label
    pub fn get_plugin_by_label(&self, label: &str) -> Result<LadspaPluginHandle, LadspaError> {
        let c_label = CString::new(label)
            .map_err(|e| LadspaError::InvalidLabel(format!("Invalid label: {}", e)))?;

        unsafe {
            let descriptor = ladspa_ffi_library_get_descriptor_by_label(self.library, c_label.as_ptr());
            if descriptor.is_null() {
                return Err(LadspaError::PluginNotFound(label.to_string()));
            }

            Ok(LadspaPluginHandle { descriptor })
        }
    }

    unsafe fn get_plugin_info(descriptor: *mut LadspaDescriptor) -> Option<LadspaPluginInfo> {
        let label_ptr = ladspa_ffi_descriptor_get_label(descriptor);
        let name_ptr = ladspa_ffi_descriptor_get_name(descriptor);
        
        if label_ptr.is_null() || name_ptr.is_null() {
            return None;
        }

        let label = CStr::from_ptr(label_ptr).to_string_lossy().into_owned();
        let name = CStr::from_ptr(name_ptr).to_string_lossy().into_owned();
        
        let unique_id = ladspa_ffi_descriptor_get_unique_id(descriptor) as u64;
        let num_ports = ladspa_ffi_descriptor_get_num_ports(descriptor);
        
        let maker_ptr = ladspa_ffi_descriptor_get_maker(descriptor);
        let maker = if maker_ptr.is_null() {
            "Unknown".to_string()
        } else {
            CStr::from_ptr(maker_ptr).to_string_lossy().into_owned()
        };
        
        let copyright_ptr = ladspa_ffi_descriptor_get_copyright(descriptor);
        let copyright = if copyright_ptr.is_null() {
            "Unknown".to_string()
        } else {
            CStr::from_ptr(copyright_ptr).to_string_lossy().into_owned()
        };

        Some(LadspaPluginInfo {
            unique_id,
            label,
            name,
            maker,
            copyright,
            num_ports,
        })
    }
}

impl Drop for LadspaHost {
    fn drop(&mut self) {
        unsafe {
            if !self.library.is_null() {
                ladspa_ffi_library_free(self.library);
            }
        }
    }
}

/// Handle to a plugin descriptor
pub struct LadspaPluginHandle {
    descriptor: *mut LadspaDescriptor,
}

impl LadspaPluginHandle {
    /// Get plugin info
    pub fn info(&self) -> Option<LadspaPluginInfo> {
        unsafe {
            LadspaHost::get_plugin_info(self.descriptor)
        }
    }

    /// Get port count
    pub fn port_count(&self) -> u32 {
        unsafe {
            ladspa_ffi_descriptor_get_num_ports(self.descriptor)
        }
    }

    /// Get port info
    pub fn get_port(&self, index: u32) -> Option<LadspaPortInfo> {
        unsafe {
            let name_ptr = ladspa_ffi_port_get_name(self.descriptor, index);
            if name_ptr.is_null() {
                return None;
            }

            let name = CStr::from_ptr(name_ptr).to_string_lossy().into_owned();
            let is_audio = ladspa_ffi_port_is_audio(self.descriptor, index) != 0;
            let is_control = ladspa_ffi_port_is_control(self.descriptor, index) != 0;
            let is_input = ladspa_ffi_port_is_input(self.descriptor, index) != 0;
            let is_output = ladspa_ffi_port_is_output(self.descriptor, index) != 0;

            let mut min_val: c_float = 0.0;
            let mut max_val: c_float = 0.0;
            let mut default_val: c_float = 0.0;
            ladspa_ffi_port_get_range(self.descriptor, index, &mut min_val, &mut max_val, &mut default_val);

            Some(LadspaPortInfo {
                index,
                name,
                is_audio,
                is_control,
                is_input,
                is_output,
                min_value: Some(min_val),
                max_value: Some(max_val),
                default_value: Some(default_val),
            })
        }
    }

    /// Instantiate plugin
    pub fn instantiate(&self, sample_rate: f64) -> Result<LadspaInstance, LadspaError> {
        unsafe {
            let handle = ladspa_ffi_instantiate(self.descriptor, sample_rate as c_uint);
            if handle.is_null() {
                return Err(LadspaError::PluginLoadFailed("Instantiation failed".to_string()));
            }

            Ok(LadspaInstance {
                descriptor: self.descriptor,
                handle,
                sample_rate,
            })
        }
    }
}

impl LadspaInstance {
    /// Activate plugin (prepare for processing)
    pub fn activate(&self) {
        unsafe {
            ladspa_ffi_activate(self.descriptor, self.handle);
        }
    }

    /// Deactivate plugin
    pub fn deactivate(&self) {
        unsafe {
            ladspa_ffi_deactivate(self.descriptor, self.handle);
        }
    }

    /// Connect port to data buffer
    pub fn connect_port(&self, port: u32, data: &mut [f32]) {
        unsafe {
            ladspa_ffi_connect_port(self.descriptor, self.handle, port, data.as_mut_ptr());
        }
    }

    /// Run plugin for sample_count samples
    pub fn run(&self, sample_count: usize) {
        unsafe {
            ladspa_ffi_run(self.descriptor, self.handle, sample_count as c_uint);
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> f64 {
        self.sample_rate
    }
}

impl Drop for LadspaInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.handle.is_null() {
                ladspa_ffi_cleanup(self.descriptor, self.handle);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ladspa_module_exists() {
        let _ = LadspaError::LibraryInitFailed;
        let _ = PortType::Audio;
        let _ = PortDirection::Input;
    }

    #[test]
    fn test_ladspa_is_available() {
        let available = LadspaHost::is_available();
        println!("LADSPA available: {}", available);
    }

    #[test]
    fn test_ladspa_version() {
        let version = LadspaHost::version();
        println!("LADSPA version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_ladspa_error_display() {
        let err = LadspaError::LibraryInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = LadspaError::PluginNotFound("test".to_string());
        assert!(err.to_string().contains("Plugin not found"));

        let err = LadspaError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_plugin_info_structure() {
        let info = LadspaPluginInfo {
            unique_id: 1234,
            label: "test_plugin".to_string(),
            name: "Test Plugin".to_string(),
            maker: "Test Maker".to_string(),
            copyright: "MIT".to_string(),
            num_ports: 4,
        };
        
        assert_eq!(info.unique_id, 1234);
        assert_eq!(info.label, "test_plugin");
        assert_eq!(info.name, "Test Plugin");
        assert_eq!(info.num_ports, 4);
    }

    #[test]
    fn test_port_info_structure() {
        let port = LadspaPortInfo {
            index: 0,
            name: "Input".to_string(),
            is_audio: true,
            is_control: false,
            is_input: true,
            is_output: false,
            min_value: Some(-1.0),
            max_value: Some(1.0),
            default_value: Some(0.0),
        };
        
        assert_eq!(port.index, 0);
        assert!(port.is_audio);
        assert!(port.is_input);
        assert!(!port.is_output);
        assert_eq!(port.min_value, Some(-1.0));
    }

    #[test]
    fn test_port_type_enum() {
        assert_eq!(PortType::Audio, PortType::Audio);
        assert_eq!(PortType::Control, PortType::Control);
        assert_ne!(PortType::Audio, PortType::Control);
    }

    #[test]
    fn test_port_direction_enum() {
        assert_eq!(PortDirection::Input, PortDirection::Input);
        assert_eq!(PortDirection::Output, PortDirection::Output);
        assert_ne!(PortDirection::Input, PortDirection::Output);
    }

    #[test]
    fn test_load_library_returns_error_when_unavailable() {
        if !LadspaHost::is_available() {
            let result = LadspaHost::load_library("/usr/lib/ladspa/test.so");
            assert!(result.is_err());
        }
    }
}
