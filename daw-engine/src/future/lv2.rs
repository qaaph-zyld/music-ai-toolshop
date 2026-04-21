//! LV2 Integration
//!
//! FFI bindings to Lilv/LV2 - host for LV2 plugins, the modern
//! open standard for audio plugins on Linux (and cross-platform).
//! Powers Guitarix, Ardour, and many other open-source DAWs.
//!
//! License: ISC (Lilv) / Various (LV2 spec)
//! Repo: https://github.com/lv2/lilv

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint, c_void};
use std::path::Path;

/// Opaque handle to Lilv world
#[repr(C)]
pub struct LilvWorld {
    _private: [u8; 0],
}

/// Opaque handle to Lilv plugin
#[repr(C)]
pub struct LilvPlugin {
    _private: [u8; 0],
}

/// Opaque handle to Lilv instance
#[repr(C)]
pub struct LilvInstance {
    _private: [u8; 0],
}

/// Opaque handle to Lilv port
#[repr(C)]
pub struct LilvPort {
    _private: [u8; 0],
}

/// LV2 error types
#[derive(Debug, Clone, PartialEq)]
pub enum LV2Error {
    WorldInitFailed,
    PluginNotFound(String),
    PluginLoadFailed(String),
    PortNotFound(String),
    InvalidUri(String),
    FfiError(String),
}

impl std::fmt::Display for LV2Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LV2Error::WorldInitFailed => write!(f, "LV2 world initialization failed"),
            LV2Error::PluginNotFound(uri) => write!(f, "Plugin not found: {}", uri),
            LV2Error::PluginLoadFailed(msg) => write!(f, "Plugin load failed: {}", msg),
            LV2Error::PortNotFound(name) => write!(f, "Port not found: {}", name),
            LV2Error::InvalidUri(uri) => write!(f, "Invalid URI: {}", uri),
            LV2Error::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for LV2Error {}

/// Plugin information
#[derive(Debug, Clone)]
pub struct LV2PluginInfo {
    pub uri: String,
    pub name: String,
    pub author: String,
    pub license: String,
    pub num_ports: u32,
}

/// Port information
#[derive(Debug, Clone)]
pub struct LV2PortInfo {
    pub index: u32,
    pub name: String,
    pub symbol: String,
    pub is_audio: bool,
    pub is_control: bool,
    pub is_input: bool,
    pub is_output: bool,
    pub min_value: Option<f32>,
    pub max_value: Option<f32>,
    pub default_value: Option<f32>,
}

/// LV2 world
pub struct LV2World {
    world: *mut LilvWorld,
}

/// LV2 plugin instance
pub struct LV2PluginInstance {
    plugin: *mut LilvPlugin,
    instance: *mut LilvInstance,
    sample_rate: f64,
}

// FFI function declarations
extern "C" {
    fn lv2_ffi_is_available() -> c_int;
    fn lv2_ffi_get_version() -> *const c_char;
    
    // World
    fn lv2_ffi_world_new() -> *mut LilvWorld;
    fn lv2_ffi_world_free(world: *mut LilvWorld);
    fn lv2_ffi_world_load_all(world: *mut LilvWorld);
    fn lv2_ffi_world_get_all_plugins(world: *mut LilvWorld) -> *mut c_void;
    
    // Plugin discovery
    fn lv2_ffi_plugins_get_size(plugins: *mut c_void) -> c_int;
    fn lv2_ffi_plugins_get_plugin(plugins: *mut c_void, index: c_int) -> *mut LilvPlugin;
    fn lv2_ffi_plugins_get_by_uri(world: *mut LilvWorld, uri: *const c_char) -> *mut LilvPlugin;
    
    // Plugin info
    fn lv2_ffi_plugin_get_uri(plugin: *mut LilvPlugin) -> *const c_char;
    fn lv2_ffi_plugin_get_name(plugin: *mut LilvPlugin) -> *const c_char;
    fn lv2_ffi_plugin_get_author_name(plugin: *mut LilvPlugin) -> *const c_char;
    fn lv2_ffi_plugin_get_license(plugin: *mut LilvPlugin) -> *const c_char;
    fn lv2_ffi_plugin_get_num_ports(plugin: *mut LilvPlugin) -> c_uint;
    fn lv2_ffi_plugin_has_feature(plugin: *mut LilvPlugin, feature: *const c_char) -> c_int;
    
    // Port info
    fn lv2_ffi_plugin_get_port_by_index(plugin: *mut LilvPlugin, index: c_uint) -> *mut LilvPort;
    fn lv2_ffi_plugin_get_port_by_symbol(plugin: *mut LilvPlugin, symbol: *const c_char) -> *mut LilvPort;
    fn lv2_ffi_port_get_name(plugin: *mut LilvPlugin, port: *mut LilvPort) -> *const c_char;
    fn lv2_ffi_port_get_symbol(plugin: *mut LilvPlugin, port: *mut LilvPort) -> *const c_char;
    fn lv2_ffi_port_is_a(plugin: *mut LilvPlugin, port: *mut LilvPort, class: *const c_char) -> c_int;
    fn lv2_ffi_port_get_range(plugin: *mut LilvPlugin, port: *mut LilvPort, min: *mut c_float, max: *mut c_float, def: *mut c_float);
}

impl LV2World {
    /// Create new LV2 world
    pub fn new() -> Result<Self, LV2Error> {
        if !Self::is_available() {
            return Err(LV2Error::FfiError("LV2 not available".to_string()));
        }

        unsafe {
            let world = lv2_ffi_world_new();
            if world.is_null() {
                return Err(LV2Error::WorldInitFailed);
            }
            
            lv2_ffi_world_load_all(world);
            
            Ok(Self { world })
        }
    }

    /// Check if LV2 is available
    pub fn is_available() -> bool {
        unsafe { lv2_ffi_is_available() != 0 }
    }

    /// Get LV2 version
    pub fn version() -> String {
        unsafe {
            let version_ptr = lv2_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get all plugins
    pub fn get_all_plugins(&self) -> Vec<LV2PluginInfo> {
        let mut plugins = Vec::new();
        
        unsafe {
            let all_plugins = lv2_ffi_world_get_all_plugins(self.world);
            if all_plugins.is_null() {
                return plugins;
            }
            
            let count = lv2_ffi_plugins_get_size(all_plugins);
            for i in 0..count {
                let plugin = lv2_ffi_plugins_get_plugin(all_plugins, i);
                if !plugin.is_null() {
                    if let Some(info) = self.get_plugin_info(plugin) {
                        plugins.push(info);
                    }
                }
            }
        }
        
        plugins
    }

    /// Get plugin info
    unsafe fn get_plugin_info(&self, plugin: *mut LilvPlugin) -> Option<LV2PluginInfo> {
        let uri_ptr = lv2_ffi_plugin_get_uri(plugin);
        let name_ptr = lv2_ffi_plugin_get_name(plugin);
        let author_ptr = lv2_ffi_plugin_get_author_name(plugin);
        let license_ptr = lv2_ffi_plugin_get_license(plugin);
        
        if uri_ptr.is_null() || name_ptr.is_null() {
            return None;
        }
        
        let uri = CStr::from_ptr(uri_ptr).to_string_lossy().into_owned();
        let name = CStr::from_ptr(name_ptr).to_string_lossy().into_owned();
        let author = if author_ptr.is_null() {
            "Unknown".to_string()
        } else {
            CStr::from_ptr(author_ptr).to_string_lossy().into_owned()
        };
        let license = if license_ptr.is_null() {
            "Unknown".to_string()
        } else {
            CStr::from_ptr(license_ptr).to_string_lossy().into_owned()
        };
        let num_ports = lv2_ffi_plugin_get_num_ports(plugin);
        
        Some(LV2PluginInfo {
            uri,
            name,
            author,
            license,
            num_ports,
        })
    }

    /// Find plugin by URI
    pub fn get_plugin_by_uri(&self, uri: &str) -> Option<LV2PluginHandle> {
        unsafe {
            let uri_cstring = CString::new(uri).ok()?;
            let plugin = lv2_ffi_plugins_get_by_uri(self.world, uri_cstring.as_ptr());
            if plugin.is_null() {
                None
            } else {
                Some(LV2PluginHandle { plugin })
            }
        }
    }
}

impl Drop for LV2World {
    fn drop(&mut self) {
        unsafe {
            if !self.world.is_null() {
                lv2_ffi_world_free(self.world);
            }
        }
    }
}

/// Handle to a plugin (doesn't own it)
pub struct LV2PluginHandle {
    plugin: *mut LilvPlugin,
}

impl LV2PluginHandle {
    /// Get plugin info
    pub fn info(&self, world: &LV2World) -> Option<LV2PluginInfo> {
        unsafe {
            world.get_plugin_info(self.plugin)
        }
    }

    /// Get port info
    pub fn get_port(&self, index: u32) -> Option<LV2PortInfo> {
        unsafe {
            let port = lv2_ffi_plugin_get_port_by_index(self.plugin, index);
            if port.is_null() {
                return None;
            }
            
            let name_ptr = lv2_ffi_port_get_name(self.plugin, port);
            let symbol_ptr = lv2_ffi_port_get_symbol(self.plugin, port);
            
            if name_ptr.is_null() || symbol_ptr.is_null() {
                return None;
            }
            
            let name = CStr::from_ptr(name_ptr).to_string_lossy().into_owned();
            let symbol = CStr::from_ptr(symbol_ptr).to_string_lossy().into_owned();
            
            let is_audio = lv2_ffi_port_is_a(self.plugin, port, "http://lv2plug.in/ns/lv2core#AudioPort".as_ptr() as *const c_char) != 0;
            let is_control = lv2_ffi_port_is_a(self.plugin, port, "http://lv2plug.in/ns/lv2core#ControlPort".as_ptr() as *const c_char) != 0;
            let is_input = lv2_ffi_port_is_a(self.plugin, port, "http://lv2plug.in/ns/lv2core#InputPort".as_ptr() as *const c_char) != 0;
            let is_output = lv2_ffi_port_is_a(self.plugin, port, "http://lv2plug.in/ns/lv2core#OutputPort".as_ptr() as *const c_char) != 0;
            
            let mut min_value: c_float = 0.0;
            let mut max_value: c_float = 0.0;
            let mut def_value: c_float = 0.0;
            lv2_ffi_port_get_range(self.plugin, port, &mut min_value, &mut max_value, &mut def_value);
            
            Some(LV2PortInfo {
                index,
                name,
                symbol,
                is_audio,
                is_control,
                is_input,
                is_output,
                min_value: Some(min_value),
                max_value: Some(max_value),
                default_value: Some(def_value),
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lv2_module_exists() {
        let _ = LV2Error::WorldInitFailed;
        let _info = LV2PluginInfo {
            uri: "test".to_string(),
            name: "Test".to_string(),
            author: "Author".to_string(),
            license: "MIT".to_string(),
            num_ports: 2,
        };
    }

    #[test]
    fn test_lv2_is_available() {
        let available = LV2World::is_available();
        println!("LV2 available: {}", available);
    }

    #[test]
    fn test_lv2_version() {
        let version = LV2World::version();
        println!("LV2 version: {}", version);
    }

    #[test]
    fn test_lv2_world_creation() {
        let result = LV2World::new();
        match result {
            Ok(world) => {
                let plugins = world.get_all_plugins();
                println!("Found {} LV2 plugins", plugins.len());
            }
            Err(e) => {
                println!("LV2 world creation failed (expected if not available): {}", e);
            }
        }
    }

    #[test]
    fn test_lv2_error_display() {
        let err = LV2Error::WorldInitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = LV2Error::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_plugin_info_structure() {
        let info = LV2PluginInfo {
            uri: "http://example.org/plugin".to_string(),
            name: "Test Plugin".to_string(),
            author: "Test Author".to_string(),
            license: "MIT".to_string(),
            num_ports: 4,
        };
        
        assert_eq!(info.uri, "http://example.org/plugin");
        assert_eq!(info.name, "Test Plugin");
        assert_eq!(info.num_ports, 4);
    }

    #[test]
    fn test_port_info_structure() {
        let port = LV2PortInfo {
            index: 0,
            name: "Input".to_string(),
            symbol: "input".to_string(),
            is_audio: true,
            is_control: false,
            is_input: true,
            is_output: false,
            min_value: None,
            max_value: None,
            default_value: None,
        };
        
        assert_eq!(port.index, 0);
        assert!(port.is_audio);
        assert!(port.is_input);
    }
}
