//! DPF Integration
//!
//! FFI bindings to DPF (Distro Plugin Framework) - a cross-platform
//! plugin framework for creating LV2, VST2, VST3, CLAP, and AU plugins
//! with a single codebase.
//!
//! License: ISC
//! Repo: https://github.com/DISTRHO/DPF

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// DPF plugin type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DPFPluginType {
    Instrument,
    Effect,
    MidiEffect,
}

/// DPF UI type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DPFUIType {
    External,
    Parented,
    Cocoa,
    X11,
    Windows,
    WebView,
}

/// DPF port type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DPFPortType {
    Audio,
    Control,
    Cv,
}

/// DPF parameter info
#[derive(Debug, Clone)]
pub struct DPFParameter {
    pub id: u32,
    pub name: String,
    pub symbol: String,
    pub min_value: f32,
    pub max_value: f32,
    pub default_value: f32,
    pub is_automatable: bool,
}

/// DPF port info
#[derive(Debug, Clone)]
pub struct DPFPort {
    pub id: u32,
    pub name: String,
    pub symbol: String,
    pub port_type: DPFPortType,
    pub is_input: bool,
}

/// DPF plugin info
#[derive(Debug, Clone)]
pub struct DPFPluginInfo {
    pub uri: String,
    pub name: String,
    pub author: String,
    pub plugin_type: DPFPluginType,
    pub version: String,
    pub license: String,
    pub num_inputs: u32,
    pub num_outputs: u32,
    pub parameters: Vec<DPFParameter>,
    pub ports: Vec<DPFPort>,
}

/// DPF error types
#[derive(Debug, Clone, PartialEq)]
pub enum DPFError {
    PluginNotFound(String),
    InvalidURI(String),
    InitFailed,
    ExportFailed(String),
    FfiError(String),
}

impl std::fmt::Display for DPFError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DPFError::PluginNotFound(uri) => write!(f, "Plugin not found: {}", uri),
            DPFError::InvalidURI(uri) => write!(f, "Invalid URI: {}", uri),
            DPFError::InitFailed => write!(f, "DPF initialization failed"),
            DPFError::ExportFailed(msg) => write!(f, "Export failed: {}", msg),
            DPFError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for DPFError {}

/// DPF plugin instance
pub struct DPFInstance {
    sample_rate: f64,
    buffer_size: u32,
}

impl DPFInstance {
    /// Create new DPF plugin instance
    pub fn new(sample_rate: f64, buffer_size: u32) -> Result<Self, DPFError> {
        Ok(Self {
            sample_rate,
            buffer_size,
        })
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> f64 {
        self.sample_rate
    }

    /// Get buffer size
    pub fn buffer_size(&self) -> u32 {
        self.buffer_size
    }
}

/// DPF builder for plugin development
pub struct DPFBuilder {
    name: String,
    author: String,
    plugin_type: DPFPluginType,
    parameters: Vec<DPFParameter>,
}

impl DPFBuilder {
    /// Create new DPF plugin builder
    pub fn new(name: &str, author: &str, plugin_type: DPFPluginType) -> Self {
        Self {
            name: name.to_string(),
            author: author.to_string(),
            plugin_type,
            parameters: Vec::new(),
        }
    }

    /// Add parameter
    pub fn add_parameter(mut self, param: DPFParameter) -> Self {
        self.parameters.push(param);
        self
    }

    /// Get parameter count
    pub fn parameter_count(&self) -> usize {
        self.parameters.len()
    }

    /// Build plugin info
    pub fn build(self) -> DPFPluginInfo {
        DPFPluginInfo {
            uri: format!("urn:dpf:{}", self.name.to_lowercase().replace(' ', "-")),
            name: self.name,
            author: self.author,
            plugin_type: self.plugin_type,
            version: "1.0.0".to_string(),
            license: "ISC".to_string(),
            num_inputs: 2,
            num_outputs: 2,
            parameters: self.parameters,
            ports: Vec::new(),
        }
    }
}

/// Check if DPF is available
pub fn is_available() -> bool {
    // DPF is a header-only framework that needs C++ compilation
    // For now, this returns false until proper FFI is implemented
    false
}

/// Get DPF version
pub fn version() -> &'static str {
    "0.0.0"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dpf_module_exists() {
        let _ = DPFError::InitFailed;
        let _ = DPFPluginType::Instrument;
        let _ = DPFUIType::External;
        let _ = DPFPortType::Audio;
    }

    #[test]
    fn test_dpf_is_available() {
        let available = is_available();
        println!("DPF available: {}", available);
        assert!(!available); // Not yet implemented
    }

    #[test]
    fn test_dpf_version() {
        let version_str = version();
        println!("DPF version: {}", version_str);
    }

    #[test]
    fn test_parameter_creation() {
        let param = DPFParameter {
            id: 0,
            name: "Gain".to_string(),
            symbol: "gain".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.5,
            is_automatable: true,
        };
        
        assert_eq!(param.name, "Gain");
        assert_eq!(param.min_value, 0.0);
        assert_eq!(param.max_value, 1.0);
        assert!(param.is_automatable);
    }

    #[test]
    fn test_port_creation() {
        let port = DPFPort {
            id: 0,
            name: "Audio Input".to_string(),
            symbol: "in".to_string(),
            port_type: DPFPortType::Audio,
            is_input: true,
        };
        
        assert_eq!(port.name, "Audio Input");
        assert!(port.is_input);
        assert_eq!(port.port_type, DPFPortType::Audio);
    }

    #[test]
    fn test_dpf_builder() {
        let builder = DPFBuilder::new("Test Plugin", "Test Author", DPFPluginType::Effect);
        assert_eq!(builder.name, "Test Plugin");
        assert_eq!(builder.author, "Test Author");
        assert_eq!(builder.plugin_type, DPFPluginType::Effect);
    }

    #[test]
    fn test_dpf_builder_with_parameters() {
        let param1 = DPFParameter {
            id: 0,
            name: "Gain".to_string(),
            symbol: "gain".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.5,
            is_automatable: true,
        };
        
        let param2 = DPFParameter {
            id: 1,
            name: "Mix".to_string(),
            symbol: "mix".to_string(),
            min_value: 0.0,
            max_value: 1.0,
            default_value: 0.5,
            is_automatable: true,
        };
        
        let info = DPFBuilder::new("Delay", "OpenDAW", DPFPluginType::Effect)
            .add_parameter(param1)
            .add_parameter(param2)
            .build();
        
        assert_eq!(info.name, "Delay");
        assert_eq!(info.author, "OpenDAW");
        assert_eq!(info.parameters.len(), 2);
        assert_eq!(info.plugin_type, DPFPluginType::Effect);
    }

    #[test]
    fn test_plugin_info_structure() {
        let info = DPFPluginInfo {
            uri: "urn:dpf:test".to_string(),
            name: "Test".to_string(),
            author: "Author".to_string(),
            plugin_type: DPFPluginType::Instrument,
            version: "1.0.0".to_string(),
            license: "MIT".to_string(),
            num_inputs: 0,
            num_outputs: 2,
            parameters: Vec::new(),
            ports: Vec::new(),
        };
        
        assert_eq!(info.name, "Test");
        assert_eq!(info.num_inputs, 0);
        assert_eq!(info.num_outputs, 2);
    }

    #[test]
    fn test_dpf_error_display() {
        let err = DPFError::InitFailed;
        assert!(err.to_string().contains("initialization failed"));

        let err = DPFError::PluginNotFound("test".to_string());
        assert!(err.to_string().contains("not found"));
    }

    #[test]
    fn test_dpf_instance() {
        let instance = DPFInstance::new(48000.0, 512);
        assert!(instance.is_ok());
        
        let instance = instance.unwrap();
        assert_eq!(instance.sample_rate(), 48000.0);
        assert_eq!(instance.buffer_size(), 512);
    }
}
