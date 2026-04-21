//! React-JUCE Integration
//!
//! FFI bindings for React-JUCE - embed React components in JUCE audio plugins
//! Modern web-based UI for audio plugins
//!
//! License: MIT (React-JUCE) + GPL/commercial (JUCE)
//! Repo: https://github.com/nick-thompson/react-juce

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_void};
use std::path::Path;

/// React-JUCE backend handle
#[repr(C)]
pub struct ReactJuceBackend {
    _private: [u8; 0],
}

/// React component instance
#[repr(C)]
pub struct ReactComponent {
    _private: [u8; 0],
}

/// React-JUCE error types
#[derive(Debug, Clone, PartialEq)]
pub enum ReactJuceError {
    InitFailed(String),
    BundleLoadFailed(String),
    ComponentRenderFailed(String),
    BridgeCommunicationFailed(String),
    NotAvailable,
}

impl std::fmt::Display for ReactJuceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ReactJuceError::InitFailed(msg) => write!(f, "React-JUCE init failed: {}", msg),
            ReactJuceError::BundleLoadFailed(msg) => write!(f, "Bundle load failed: {}", msg),
            ReactJuceError::ComponentRenderFailed(msg) => write!(f, "Component render failed: {}", msg),
            ReactJuceError::BridgeCommunicationFailed(msg) => write!(f, "Bridge communication failed: {}", msg),
            ReactJuceError::NotAvailable => write!(f, "React-JUCE not available"),
        }
    }
}

impl std::error::Error for ReactJuceError {}

/// React-JUCE bundle source
#[derive(Debug, Clone, PartialEq)]
pub enum BundleSource {
    File(String),      // Path to bundle file
    Memory(Vec<u8>),   // In-memory bundle
    URL(String),       // URL to fetch bundle
}

/// React component props
#[derive(Debug, Clone, Default)]
pub struct ComponentProps {
    pub string_props: Vec<(String, String)>,
    pub number_props: Vec<(String, f64)>,
    pub bool_props: Vec<(String, bool)>,
}

impl ComponentProps {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_string(mut self, key: &str, value: &str) -> Self {
        self.string_props.push((key.to_string(), value.to_string()));
        self
    }

    pub fn with_number(mut self, key: &str, value: f64) -> Self {
        self.number_props.push((key.to_string(), value));
        self
    }

    pub fn with_bool(mut self, key: &str, value: bool) -> Self {
        self.bool_props.push((key.to_string(), value));
        self
    }
}

/// Native method callback
pub type NativeMethodCallback = Box<dyn Fn(&str, &str) -> String + Send + Sync>;

/// React-JUCE engine
pub struct ReactJuceEngine {
    backend: *mut ReactJuceBackend,
    bundle_source: BundleSource,
    native_methods: Vec<(String, NativeMethodCallback)>,
}

/// React component wrapper
pub struct ReactJuceComponent {
    component: *mut ReactComponent,
    name: String,
    engine: *mut ReactJuceBackend,
}

/// Audio parameter bridge
#[derive(Debug, Clone)]
pub struct AudioParameterBridge {
    param_id: String,
    param_name: String,
    min_value: f64,
    max_value: f64,
    default_value: f64,
    current_value: f64,
}

// FFI function declarations
extern "C" {
    fn react_juce_ffi_is_available() -> c_int;
    fn react_juce_ffi_get_version() -> *const c_char;
    
    // Backend
    fn react_juce_ffi_backend_new() -> *mut ReactJuceBackend;
    fn react_juce_ffi_backend_delete(backend: *mut ReactJuceBackend);
    fn react_juce_ffi_backend_init(backend: *mut ReactJuceBackend,
                                    bundle_path: *const c_char) -> c_int;
    fn react_juce_ffi_backend_init_from_memory(backend: *mut ReactJuceBackend,
                                                bundle_data: *const c_char,
                                                bundle_size: c_int) -> c_int;
    
    // Component management
    fn react_juce_ffi_component_create(backend: *mut ReactJuceBackend,
                                        component_name: *const c_char) -> *mut ReactComponent;
    fn react_juce_ffi_component_delete(component: *mut ReactComponent);
    fn react_juce_ffi_component_set_props(component: *mut ReactComponent,
                                           props_json: *const c_char) -> c_int;
    fn react_juce_ffi_component_render(component: *mut ReactComponent) -> c_int;
    fn react_juce_ffi_component_resize(component: *mut ReactComponent,
                                      width: c_int, height: c_int) -> c_int;
    
    // Native bridge
    fn react_juce_ffi_register_native_method(backend: *mut ReactJuceBackend,
                                              method_name: *const c_char,
                                              callback: *mut c_void) -> c_int;
    fn react_juce_ffi_call_js_method(backend: *mut ReactJuceBackend,
                                      component_id: c_int,
                                      method_name: *const c_char,
                                      args_json: *const c_char) -> *const c_char;
    
    // Audio parameter bridge
    fn react_juce_ffi_register_parameter(backend: *mut ReactJuceBackend,
                                          param_id: *const c_char,
                                          min_val: c_int,
                                          max_val: c_int,
                                          default_val: c_int) -> c_int;
    fn react_juce_ffi_set_parameter_value(backend: *mut ReactJuceBackend,
                                           param_id: *const c_char,
                                           value: c_int) -> c_int;
    fn react_juce_ffi_get_parameter_value(backend: *mut ReactJuceBackend,
                                         param_id: *const c_char) -> c_int;
    
    // Hot reload
    fn react_juce_ffi_enable_hot_reload(backend: *mut ReactJuceBackend,
                                         watch_path: *const c_char) -> c_int;
    fn react_juce_ffi_reload_bundle(backend: *mut ReactJuceBackend) -> c_int;
}

impl ReactJuceEngine {
    /// Create new React-JUCE engine with bundle
    pub fn new(bundle: BundleSource) -> Result<Self, ReactJuceError> {
        if !Self::is_available() {
            return Err(ReactJuceError::NotAvailable);
        }

        unsafe {
            let backend = react_juce_ffi_backend_new();
            if backend.is_null() {
                return Err(ReactJuceError::InitFailed("Failed to create backend".to_string()));
            }

            // Initialize with bundle
            let init_result = match &bundle {
                BundleSource::File(path) => {
                    let path_cstring = CString::new(path.as_str())
                        .map_err(|e| ReactJuceError::BundleLoadFailed(e.to_string()))?;
                    react_juce_ffi_backend_init(backend, path_cstring.as_ptr())
                }
                BundleSource::Memory(data) => {
                    react_juce_ffi_backend_init_from_memory(
                        backend,
                        data.as_ptr() as *const c_char,
                        data.len() as c_int,
                    )
                }
                BundleSource::URL(_) => {
                    // URLs would need to be fetched first
                    return Err(ReactJuceError::BundleLoadFailed(
                        "URL bundles not yet supported".to_string()
                    ));
                }
            };

            if init_result != 0 {
                react_juce_ffi_backend_delete(backend);
                return Err(ReactJuceError::BundleLoadFailed(
                    format!("Bundle init failed: {}", init_result)
                ));
            }

            Ok(Self {
                backend,
                bundle_source: bundle,
                native_methods: Vec::new(),
            })
        }
    }

    /// Check if React-JUCE is available
    pub fn is_available() -> bool {
        unsafe { react_juce_ffi_is_available() != 0 }
    }

    /// Get React-JUCE version
    pub fn version() -> String {
        unsafe {
            let version_ptr = react_juce_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Create React component instance
    pub fn create_component(&mut self, name: &str, props: ComponentProps) 
        -> Result<ReactJuceComponent, ReactJuceError> {
        let name_cstring = CString::new(name)
            .map_err(|e| ReactJuceError::ComponentRenderFailed(e.to_string()))?;

        unsafe {
            let component = react_juce_ffi_component_create(self.backend, name_cstring.as_ptr());
            if component.is_null() {
                return Err(ReactJuceError::ComponentRenderFailed(
                    format!("Failed to create component: {}", name)
                ));
            }

            // Build props JSON
            let props_json = Self::build_props_json(&props);
            let props_cstring = CString::new(props_json)
                .map_err(|e| ReactJuceError::ComponentRenderFailed(e.to_string()))?;

            react_juce_ffi_component_set_props(component, props_cstring.as_ptr());

            Ok(ReactJuceComponent {
                component,
                name: name.to_string(),
                engine: self.backend,
            })
        }
    }

    /// Register audio parameter
    pub fn register_parameter(&mut self, param: &AudioParameterBridge) -> Result<(), ReactJuceError> {
        let id_cstring = CString::new(param.param_id.as_str())
            .map_err(|e| ReactJuceError::BridgeCommunicationFailed(e.to_string()))?;

        unsafe {
            let result = react_juce_ffi_register_parameter(
                self.backend,
                id_cstring.as_ptr(),
                (param.min_value * 1000.0) as c_int,
                (param.max_value * 1000.0) as c_int,
                (param.default_value * 1000.0) as c_int,
            );

            if result != 0 {
                return Err(ReactJuceError::BridgeCommunicationFailed(
                    format!("Failed to register parameter: {}", param.param_id)
                ));
            }

            Ok(())
        }
    }

    /// Set parameter value
    pub fn set_parameter(&mut self, param_id: &str, value: f64) -> Result<(), ReactJuceError> {
        let id_cstring = CString::new(param_id)
            .map_err(|e| ReactJuceError::BridgeCommunicationFailed(e.to_string()))?;

        unsafe {
            react_juce_ffi_set_parameter_value(
                self.backend,
                id_cstring.as_ptr(),
                (value * 1000.0) as c_int,
            );
            Ok(())
        }
    }

    /// Enable hot reload for development
    pub fn enable_hot_reload<P: AsRef<Path>>(&mut self, watch_path: P) 
        -> Result<(), ReactJuceError> {
        let path_str = watch_path.as_ref().to_string_lossy().to_string();
        let path_cstring = CString::new(path_str)
            .map_err(|e| ReactJuceError::InitFailed(e.to_string()))?;

        unsafe {
            let result = react_juce_ffi_enable_hot_reload(self.backend, path_cstring.as_ptr());
            if result != 0 {
                return Err(ReactJuceError::InitFailed("Failed to enable hot reload".to_string()));
            }
            Ok(())
        }
    }

    /// Reload bundle (for hot reload)
    pub fn reload_bundle(&mut self) -> Result<(), ReactJuceError> {
        unsafe {
            let result = react_juce_ffi_reload_bundle(self.backend);
            if result != 0 {
                return Err(ReactJuceError::BundleLoadFailed("Failed to reload bundle".to_string()));
            }
            Ok(())
        }
    }

    fn build_props_json(props: &ComponentProps) -> String {
        let mut parts = vec![];
        
        for (k, v) in &props.string_props {
            parts.push(format!("\"{}\":\"{}\"", k, v.replace('"', "\\\"")));
        }
        
        for (k, v) in &props.number_props {
            parts.push(format!("\"{}\":{}", k, v));
        }
        
        for (k, v) in &props.bool_props {
            parts.push(format!("\"{}\":{}", k, if *v { "true" } else { "false" }));
        }
        
        format!("{{{}}}", parts.join(","))
    }
}

impl Drop for ReactJuceEngine {
    fn drop(&mut self) {
        unsafe {
            if !self.backend.is_null() {
                react_juce_ffi_backend_delete(self.backend);
            }
        }
    }
}

impl ReactJuceComponent {
    /// Render component
    pub fn render(&mut self) -> Result<(), ReactJuceError> {
        unsafe {
            let result = react_juce_ffi_component_render(self.component);
            if result != 0 {
                return Err(ReactJuceError::ComponentRenderFailed(
                    format!("Render failed for component: {}", self.name)
                ));
            }
            Ok(())
        }
    }

    /// Resize component
    pub fn resize(&mut self, width: i32, height: i32) -> Result<(), ReactJuceError> {
        unsafe {
            let result = react_juce_ffi_component_resize(self.component, width, height);
            if result != 0 {
                return Err(ReactJuceError::ComponentRenderFailed(
                    "Resize failed".to_string()
                ));
            }
            Ok(())
        }
    }

    /// Get component name
    pub fn name(&self) -> &str {
        &self.name
    }
}

impl Drop for ReactJuceComponent {
    fn drop(&mut self) {
        unsafe {
            if !self.component.is_null() {
                react_juce_ffi_component_delete(self.component);
            }
        }
    }
}

impl AudioParameterBridge {
    /// Create new audio parameter
    pub fn new(id: &str, name: &str, min: f64, max: f64, default: f64) -> Self {
        Self {
            param_id: id.to_string(),
            param_name: name.to_string(),
            min_value: min,
            max_value: max,
            default_value: default,
            current_value: default,
        }
    }

    /// Get normalized value (0-1)
    pub fn normalized(&self) -> f64 {
        if self.max_value > self.min_value {
            (self.current_value - self.min_value) / (self.max_value - self.min_value)
        } else {
            0.0
        }
    }

    /// Set from normalized value
    pub fn set_normalized(&mut self, norm: f64) {
        self.current_value = self.min_value + norm * (self.max_value - self.min_value);
    }

    /// Get parameter ID
    pub fn id(&self) -> &str {
        &self.param_id
    }

    /// Get parameter name
    pub fn name(&self) -> &str {
        &self.param_name
    }

    /// Get current value
    pub fn value(&self) -> f64 {
        self.current_value
    }

    /// Set current value
    pub fn set_value(&mut self, value: f64) {
        self.current_value = value.clamp(self.min_value, self.max_value);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_react_juce_module_exists() {
        let _ = ReactJuceError::NotAvailable;
        let _ = BundleSource::File("test.js".to_string());
        let _ = ComponentProps::new();
    }

    #[test]
    fn test_react_juce_is_available() {
        let available = ReactJuceEngine::is_available();
        println!("React-JUCE available: {}", available);
    }

    #[test]
    fn test_react_juce_version() {
        let version = ReactJuceEngine::version();
        println!("React-JUCE version: {}", version);
    }

    #[test]
    fn test_bundle_sources() {
        let sources = vec![
            BundleSource::File("bundle.js".to_string()),
            BundleSource::Memory(vec![1, 2, 3]),
            BundleSource::URL("http://localhost/bundle.js".to_string()),
        ];
        for source in sources {
            let s = format!("{:?}", source);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_component_props() {
        let props = ComponentProps::new()
            .with_string("title", "My Plugin")
            .with_number("value", 42.5)
            .with_bool("enabled", true);
        
        assert_eq!(props.string_props.len(), 1);
        assert_eq!(props.number_props.len(), 1);
        assert_eq!(props.bool_props.len(), 1);
    }

    #[test]
    fn test_audio_parameter_bridge() {
        let mut param = AudioParameterBridge::new("gain", "Gain", 0.0, 100.0, 50.0);
        
        assert_eq!(param.value(), 50.0);
        assert_eq!(param.normalized(), 0.5);
        
        param.set_normalized(0.75);
        assert_eq!(param.value(), 75.0);
        
        param.set_value(110.0); // Should clamp
        assert_eq!(param.value(), 100.0);
        
        assert_eq!(param.id(), "gain");
        assert_eq!(param.name(), "Gain");
    }

    #[test]
    fn test_new_fails_gracefully() {
        let result = ReactJuceEngine::new(BundleSource::File("/nonexistent/bundle.js".to_string()));
        match result {
            Err(ReactJuceError::NotAvailable) | Err(ReactJuceError::BundleLoadFailed(_)) | 
            Err(ReactJuceError::InitFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable, BundleLoadFailed, or InitFailed"),
        }
    }

    #[test]
    fn test_memory_bundle_fails_gracefully() {
        let result = ReactJuceEngine::new(BundleSource::Memory(vec![0u8; 100]));
        match result {
            Err(ReactJuceError::NotAvailable) | Err(ReactJuceError::BundleLoadFailed(_)) |
            Err(ReactJuceError::InitFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable, BundleLoadFailed, or InitFailed"),
        }
    }

    #[test]
    fn test_react_juce_error_display() {
        let err = ReactJuceError::NotAvailable;
        assert!(err.to_string().contains("not available"));

        let err = ReactJuceError::InitFailed("test".to_string());
        assert!(err.to_string().contains("init failed"));

        let err = ReactJuceError::BundleLoadFailed("test".to_string());
        assert!(err.to_string().contains("Bundle load failed"));

        let err = ReactJuceError::ComponentRenderFailed("test".to_string());
        assert!(err.to_string().contains("Component render failed"));

        let err = ReactJuceError::BridgeCommunicationFailed("test".to_string());
        assert!(err.to_string().contains("Bridge communication failed"));
    }

    #[test]
    fn test_component_accessors() {
        let component = ReactJuceComponent {
            component: std::ptr::null_mut(),
            name: "TestComponent".to_string(),
            engine: std::ptr::null_mut(),
        };
        
        assert_eq!(component.name(), "TestComponent");
    }
}
