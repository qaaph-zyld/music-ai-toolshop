//! JACK2 Integration
//!
//! FFI bindings to JACK2 - low-latency audio server for
//! professional audio on Linux, macOS, and Windows.
//! Powers Ardour, Qtractor, and many pro-audio applications.
//!
//! License: LGPL-2.1+
//! Repo: https://github.com/jackaudio/jack2

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// Opaque handle to JACK client
#[repr(C)]
pub struct JackClient {
    _private: [u8; 0],
}

/// Opaque handle to JACK port
#[repr(C)]
pub struct JackPort {
    _private: [u8; 0],
}

/// JACK error types
#[derive(Debug, Clone, PartialEq)]
pub enum JackError {
    ClientOpenFailed,
    PortRegistrationFailed(String),
    ActivationFailed,
    TransportError,
    SampleRateMismatch,
    BufferSizeMismatch,
    FfiError(String),
}

impl std::fmt::Display for JackError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            JackError::ClientOpenFailed => write!(f, "Failed to open JACK client"),
            JackError::PortRegistrationFailed(name) => write!(f, "Failed to register port: {}", name),
            JackError::ActivationFailed => write!(f, "Failed to activate JACK client"),
            JackError::TransportError => write!(f, "JACK transport error"),
            JackError::SampleRateMismatch => write!(f, "Sample rate mismatch with JACK server"),
            JackError::BufferSizeMismatch => write!(f, "Buffer size mismatch with JACK server"),
            JackError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for JackError {}

/// Port type enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum JackPortType {
    Audio,
    Midi,
}

impl JackPortType {
    pub fn as_str(&self) -> &'static str {
        match self {
            JackPortType::Audio => "32 bit float mono audio",
            JackPortType::Midi => "8 bit raw midi",
        }
    }
}

/// Port flags
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum JackPortFlags {
    IsInput = 0x1,
    IsOutput = 0x2,
    IsPhysical = 0x4,
    CanMonitor = 0x8,
    IsTerminal = 0x10,
}

/// JACK client configuration
#[derive(Debug, Clone)]
pub struct JackConfig {
    pub client_name: String,
    pub server_name: Option<String>,
}

impl Default for JackConfig {
    fn default() -> Self {
        Self {
            client_name: "OpenDAW".to_string(),
            server_name: None,
        }
    }
}

/// JACK port information
#[derive(Debug, Clone)]
pub struct JackPortInfo {
    pub name: String,
    pub port_type: JackPortType,
    pub is_input: bool,
    pub is_output: bool,
    pub is_physical: bool,
}

/// JACK client instance
pub struct JackClientInstance {
    client: *mut JackClient,
    config: JackConfig,
    sample_rate: u32,
    buffer_size: u32,
}

/// JACK port
pub struct JackPortHandle {
    port: *mut JackPort,
    name: String,
}

/// JACK transport state
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TransportState {
    Stopped,
    Playing,
    Starting,
}

/// JACK transport position
#[derive(Debug, Clone)]
pub struct JackTransportPos {
    pub frame: u64,
    pub valid: u64,
    pub bar: i32,
    pub beat: i32,
    pub tick: i32,
    pub bar_start_tick: f64,
    pub beats_per_bar: f32,
    pub beat_type: f32,
    pub ticks_per_beat: f64,
    pub ticks_per_minute: f64,
}

// FFI function declarations
extern "C" {
    fn jack_ffi_is_available() -> c_int;
    fn jack_ffi_get_version() -> *const c_char;
    
    // Client
    fn jack_ffi_client_open(name: *const c_char, server: *const c_char) -> *mut JackClient;
    fn jack_ffi_client_close(client: *mut JackClient) -> c_int;
    fn jack_ffi_activate(client: *mut JackClient) -> c_int;
    fn jack_ffi_deactivate(client: *mut JackClient) -> c_int;
    
    // Ports
    fn jack_ffi_port_register(
        client: *mut JackClient,
        name: *const c_char,
        port_type: *const c_char,
        flags: c_int,
        buffer_size: c_int,
    ) -> *mut JackPort;
    fn jack_ffi_port_unregister(client: *mut JackClient, port: *mut JackPort) -> c_int;
    fn jack_ffi_port_get_buffer(port: *mut JackPort, nframes: c_int) -> *mut c_void;
    fn jack_ffi_port_connect(client: *mut JackClient, source: *const c_char, dest: *const c_char) -> c_int;
    fn jack_ffi_port_disconnect(client: *mut JackClient, source: *const c_char, dest: *const c_char) -> c_int;
    
    // Server info
    fn jack_ffi_get_sample_rate(client: *mut JackClient) -> c_int;
    fn jack_ffi_get_buffer_size(client: *mut JackClient) -> c_int;
    
    // Transport
    fn jack_ffi_transport_start(client: *mut JackClient);
    fn jack_ffi_transport_stop(client: *mut JackClient);
    fn jack_ffi_transport_locate(client: *mut JackClient, frame: c_int);
    fn jack_ffi_get_transport_state(client: *mut JackClient) -> c_int;
}

impl JackClientInstance {
    /// Create new JACK client
    pub fn new(config: JackConfig) -> Result<Self, JackError> {
        if !Self::is_available() {
            return Err(JackError::FfiError("JACK not available".to_string()));
        }

        let name_cstring = CString::new(config.client_name.clone())
            .map_err(|e| JackError::FfiError(e.to_string()))?;
        
        let server_cstring = config.server_name.as_ref()
            .map(|s| CString::new(s.clone()).ok())
            .flatten();

        unsafe {
            let client = jack_ffi_client_open(
                name_cstring.as_ptr(),
                server_cstring.as_ref().map(|s| s.as_ptr()).unwrap_or(std::ptr::null()),
            );
            
            if client.is_null() {
                return Err(JackError::ClientOpenFailed);
            }

            let sample_rate = jack_ffi_get_sample_rate(client) as u32;
            let buffer_size = jack_ffi_get_buffer_size(client) as u32;

            Ok(Self {
                client,
                config,
                sample_rate,
                buffer_size,
            })
        }
    }

    /// Check if JACK is available
    pub fn is_available() -> bool {
        unsafe { jack_ffi_is_available() != 0 }
    }

    /// Get JACK version
    pub fn version() -> String {
        unsafe {
            let version_ptr = jack_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Activate JACK client
    pub fn activate(&self) -> Result<(), JackError> {
        unsafe {
            let result = jack_ffi_activate(self.client);
            if result != 0 {
                return Err(JackError::ActivationFailed);
            }
            Ok(())
        }
    }

    /// Deactivate JACK client
    pub fn deactivate(&self) -> Result<(), JackError> {
        unsafe {
            jack_ffi_deactivate(self.client);
            Ok(())
        }
    }

    /// Register port
    pub fn register_port(&self, name: &str, port_type: JackPortType, is_input: bool) -> Result<JackPortHandle, JackError> {
        let name_cstring = CString::new(name)
            .map_err(|e| JackError::FfiError(e.to_string()))?;
        let type_cstring = CString::new(port_type.as_str())
            .map_err(|e| JackError::FfiError(e.to_string()))?;
        
        let flags = if is_input {
            JackPortFlags::IsInput as c_int
        } else {
            JackPortFlags::IsOutput as c_int
        };

        unsafe {
            let port = jack_ffi_port_register(
                self.client,
                name_cstring.as_ptr(),
                type_cstring.as_ptr(),
                flags,
                0,
            );
            
            if port.is_null() {
                return Err(JackError::PortRegistrationFailed(name.to_string()));
            }
            
            Ok(JackPortHandle {
                port,
                name: name.to_string(),
            })
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    /// Get buffer size
    pub fn buffer_size(&self) -> u32 {
        self.buffer_size
    }

    /// Connect ports
    pub fn connect_ports(&self, source: &str, destination: &str) -> Result<(), JackError> {
        let source_cstring = CString::new(source)
            .map_err(|e| JackError::FfiError(e.to_string()))?;
        let dest_cstring = CString::new(destination)
            .map_err(|e| JackError::FfiError(e.to_string()))?;

        unsafe {
            let result = jack_ffi_port_connect(
                self.client,
                source_cstring.as_ptr(),
                dest_cstring.as_ptr(),
            );
            
            if result != 0 {
                return Err(JackError::FfiError("Failed to connect ports".to_string()));
            }
            
            Ok(())
        }
    }

    /// Start transport
    pub fn transport_start(&self) {
        unsafe { jack_ffi_transport_start(self.client); }
    }

    /// Stop transport
    pub fn transport_stop(&self) {
        unsafe { jack_ffi_transport_stop(self.client); }
    }

    /// Get transport state
    pub fn transport_state(&self) -> TransportState {
        unsafe {
            let state = jack_ffi_get_transport_state(self.client);
            match state {
                0 => TransportState::Stopped,
                1 => TransportState::Playing,
                _ => TransportState::Starting,
            }
        }
    }
}

impl Drop for JackClientInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.client.is_null() {
                jack_ffi_client_close(self.client);
            }
        }
    }
}

impl JackPortHandle {
    /// Get port name
    pub fn name(&self) -> &str {
        &self.name
    }
}

impl Drop for JackPortHandle {
    fn drop(&mut self) {
        // Port is unregistered when client closes
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jack_module_exists() {
        let _ = JackError::ClientOpenFailed;
        let _ = JackPortType::Audio;
        let _ = JackPortFlags::IsInput;
    }

    #[test]
    fn test_jack_is_available() {
        let available = JackClientInstance::is_available();
        println!("JACK available: {}", available);
    }

    #[test]
    fn test_jack_version() {
        let version = JackClientInstance::version();
        println!("JACK version: {}", version);
    }

    #[test]
    fn test_jack_client_creation() {
        let config = JackConfig::default();
        let result = JackClientInstance::new(config);
        match result {
            Ok(client) => {
                println!("JACK client created, sample rate: {}", client.sample_rate());
            }
            Err(e) => {
                println!("JACK client creation failed (expected if JACK not running): {}", e);
            }
        }
    }

    #[test]
    fn test_jack_config_defaults() {
        let config = JackConfig::default();
        assert_eq!(config.client_name, "OpenDAW");
        assert!(config.server_name.is_none());
    }

    #[test]
    fn test_port_type_as_str() {
        assert_eq!(JackPortType::Audio.as_str(), "32 bit float mono audio");
        assert_eq!(JackPortType::Midi.as_str(), "8 bit raw midi");
    }

    #[test]
    fn test_jack_error_display() {
        let err = JackError::ClientOpenFailed;
        assert!(err.to_string().contains("Failed to open"));

        let err = JackError::PortRegistrationFailed("test".to_string());
        assert!(err.to_string().contains("Failed to register"));
    }

    #[test]
    fn test_transport_states() {
        let states = vec![
            TransportState::Stopped,
            TransportState::Playing,
            TransportState::Starting,
        ];
        for state in states {
            assert!(!format!("{:?}", state).is_empty());
        }
    }

    #[test]
    fn test_jack_port_info() {
        let info = JackPortInfo {
            name: "audio_out".to_string(),
            port_type: JackPortType::Audio,
            is_input: false,
            is_output: true,
            is_physical: false,
        };
        
        assert_eq!(info.name, "audio_out");
        assert!(info.is_output);
        assert!(!info.is_input);
    }
}
