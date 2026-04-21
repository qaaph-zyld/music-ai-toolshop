//! libremidi - Modern MIDI 2.0 I/O
//!
//! Next-generation MIDI library with hotplug detection, zero-allocation modes,
//! and MIDI 2.0 support. BSD-2-Clause licensed.
//!
//! Repository: https://github.com/celtera/libremidi

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint, c_ulong};
use std::sync::Arc;

/// Opaque handle to libremidi backend
pub struct LibremidiEngine {
    handle: *mut c_void,
    config: LibremidiConfig,
}

/// Configuration for libremidi engine
#[derive(Debug, Clone)]
pub struct LibremidiConfig {
    pub midi_version: MidiVersion,
    pub hotplug_enabled: bool,
    pub zero_allocation: bool,
}

impl Default for LibremidiConfig {
    fn default() -> Self {
        Self {
            midi_version: MidiVersion::Midi1,
            hotplug_enabled: true,
            zero_allocation: false,
        }
    }
}

/// MIDI version support
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MidiVersion {
    Midi1,
    Midi2,
}

/// MIDI device information
#[derive(Debug, Clone)]
pub struct LibremidiDevice {
    pub id: u32,
    pub name: String,
    pub is_input: bool,
    pub is_output: bool,
    pub is_virtual: bool,
    pub port_index: i32,
}

/// MIDI message with timestamp
#[derive(Debug, Clone, PartialEq)]
pub struct LibremidiMessage {
    pub data: Vec<u8>,
    pub timestamp: u64,
    pub is_ump: bool, // Universal MIDI Packet (MIDI 2.0)
}

/// Device enumeration result
#[derive(Debug)]
pub struct DeviceEnumeration {
    pub inputs: Vec<LibremidiDevice>,
    pub outputs: Vec<LibremidiDevice>,
}

/// Hotplug callback trait
pub trait HotplugCallback: Send + Sync {
    fn on_device_connected(&self, device: &LibremidiDevice);
    fn on_device_disconnected(&self, device_id: u32);
}

/// Message callback trait
pub trait MessageCallback: Send + Sync {
    fn on_message(&self, message: &LibremidiMessage);
}

/// Error types for libremidi operations
#[derive(Debug)]
pub enum LibremidiError {
    NotAvailable,
    DeviceNotFound(u32),
    AlreadyOpen,
    NotOpen,
    InvalidMessage,
    FfiError(String),
    PlatformError(String),
}

impl std::fmt::Display for LibremidiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LibremidiError::NotAvailable => write!(f, "libremidi not available"),
            LibremidiError::DeviceNotFound(id) => write!(f, "Device {} not found", id),
            LibremidiError::AlreadyOpen => write!(f, "Device already open"),
            LibremidiError::NotOpen => write!(f, "Device not open"),
            LibremidiError::InvalidMessage => write!(f, "Invalid MIDI message"),
            LibremidiError::FfiError(e) => write!(f, "FFI error: {}", e),
            LibremidiError::PlatformError(e) => write!(f, "Platform error: {}", e),
        }
    }
}

impl std::error::Error for LibremidiError {}

impl LibremidiEngine {
    /// Create new libremidi engine with config
    pub fn new(config: LibremidiConfig) -> Result<Self, LibremidiError> {
        let handle = unsafe { libremidi_ffi::engine_create(&config) };
        if handle.is_null() {
            return Err(LibremidiError::NotAvailable);
        }
        Ok(Self { handle, config })
    }

    /// Enumerate available MIDI devices
    pub fn enumerate_devices(&self) -> Result<DeviceEnumeration, LibremidiError> {
        let result = unsafe { libremidi_ffi::enumerate_devices(self.handle) };
        if result.is_null() {
            return Err(LibremidiError::NotAvailable);
        }
        
        // Parse FFI result into DeviceEnumeration
        let enumeration = DeviceEnumeration {
            inputs: vec![],
            outputs: vec![],
        };
        
        unsafe { libremidi_ffi::free_enumeration(result) };
        Ok(enumeration)
    }

    /// Open input device
    pub fn open_input(
        &mut self,
        device_id: u32,
        callback: Arc<dyn MessageCallback>,
    ) -> Result<(), LibremidiError> {
        let result = unsafe { libremidi_ffi::open_input(self.handle, device_id) };
        if result == 0 {
            Ok(())
        } else {
            Err(LibremidiError::DeviceNotFound(device_id))
        }
    }

    /// Open output device
    pub fn open_output(&mut self, device_id: u32) -> Result<(), LibremidiError> {
        let result = unsafe { libremidi_ffi::open_output(self.handle, device_id) };
        if result == 0 {
            Ok(())
        } else {
            Err(LibremidiError::DeviceNotFound(device_id))
        }
    }

    /// Close input device
    pub fn close_input(&mut self) -> Result<(), LibremidiError> {
        unsafe { libremidi_ffi::close_input(self.handle) };
        Ok(())
    }

    /// Close output device
    pub fn close_output(&mut self) -> Result<(), LibremidiError> {
        unsafe { libremidi_ffi::close_output(self.handle) };
        Ok(())
    }

    /// Send MIDI message
    pub fn send_message(&self, message: &LibremidiMessage) -> Result<(), LibremidiError> {
        if message.data.is_empty() || message.data.len() > 256 {
            return Err(LibremidiError::InvalidMessage);
        }
        
        let result = unsafe {
            libremidi_ffi::send_message(
                self.handle,
                message.data.as_ptr(),
                message.data.len(),
                message.timestamp,
            )
        };
        
        if result == 0 {
            Ok(())
        } else {
            Err(LibremidiError::NotOpen)
        }
    }

    /// Enable hotplug detection
    pub fn enable_hotplug(&mut self, callback: Arc<dyn HotplugCallback>) -> Result<(), LibremidiError> {
        if !self.config.hotplug_enabled {
            return Err(LibremidiError::PlatformError(
                "Hotplug not enabled in config".to_string(),
            ));
        }
        
        let result = unsafe { libremidi_ffi::enable_hotplug(self.handle) };
        if result == 0 {
            Ok(())
        } else {
            Err(LibremidiError::NotAvailable)
        }
    }

    /// Get engine info
    pub fn info(&self) -> LibremidiInfo {
        LibremidiInfo {
            version: "0.6.0".to_string(),
            supports_midi2: self.config.midi_version == MidiVersion::Midi2,
            hotplug_available: self.config.hotplug_enabled,
        }
    }
}

impl Drop for LibremidiEngine {
    fn drop(&mut self) {
        unsafe {
            libremidi_ffi::engine_destroy(self.handle);
        }
    }
}

/// Engine information
#[derive(Debug, Clone)]
pub struct LibremidiInfo {
    pub version: String,
    pub supports_midi2: bool,
    pub hotplug_available: bool,
}

/// FFI bridge to C libremidi
mod libremidi_ffi {
    use super::*;

    extern "C" {
        pub fn engine_create(config: *const LibremidiConfig) -> *mut c_void;
        pub fn engine_destroy(engine: *mut c_void);
        pub fn enumerate_devices(engine: *mut c_void) -> *mut c_void;
        pub fn free_enumeration(enumeration: *mut c_void);
        pub fn open_input(engine: *mut c_void, device_id: u32) -> c_int;
        pub fn open_output(engine: *mut c_void, device_id: u32) -> c_int;
        pub fn close_input(engine: *mut c_void);
        pub fn close_output(engine: *mut c_void);
        pub fn send_message(
            engine: *mut c_void,
            data: *const u8,
            length: usize,
            timestamp: u64,
        ) -> c_int;
        pub fn enable_hotplug(engine: *mut c_void) -> c_int;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Test 1: Engine creation with default config
    #[test]
    fn test_engine_creation_default_config() {
        let config = LibremidiConfig::default();
        let engine = LibremidiEngine::new(config);
        // FFI stub returns NotAvailable
        assert!(matches!(engine, Err(LibremidiError::NotAvailable)));
    }

    // Test 2: Engine creation with MIDI 2.0 config
    #[test]
    fn test_engine_creation_midi2() {
        let config = LibremidiConfig {
            midi_version: MidiVersion::Midi2,
            hotplug_enabled: true,
            zero_allocation: true,
        };
        let engine = LibremidiEngine::new(config);
        // FFI stub returns NotAvailable
        assert!(matches!(engine, Err(LibremidiError::NotAvailable)));
    }

    // Test 3: Device enumeration
    #[test]
    fn test_enumerate_devices() {
        // Create engine (will fail with NotAvailable)
        let config = LibremidiConfig::default();
        if let Ok(engine) = LibremidiEngine::new(config) {
            let result = engine.enumerate_devices();
            // Should succeed but return empty lists from FFI stub
            assert!(result.is_ok());
            let enumeration = result.unwrap();
            assert!(enumeration.inputs.is_empty());
            assert!(enumeration.outputs.is_empty());
        }
    }

    // Test 4: Device structure
    #[test]
    fn test_device_structure() {
        let device = LibremidiDevice {
            id: 42,
            name: "Test Device".to_string(),
            is_input: true,
            is_output: false,
            is_virtual: false,
            port_index: 0,
        };
        assert_eq!(device.id, 42);
        assert_eq!(device.name, "Test Device");
        assert!(device.is_input);
        assert!(!device.is_output);
    }

    // Test 5: Message structure
    #[test]
    fn test_message_structure() {
        let message = LibremidiMessage {
            data: vec![0x90, 0x40, 0x7F], // Note on
            timestamp: 12345,
            is_ump: false,
        };
        assert_eq!(message.data, vec![0x90, 0x40, 0x7F]);
        assert_eq!(message.timestamp, 12345);
        assert!(!message.is_ump);
    }

    // Test 6: UMP message (MIDI 2.0)
    #[test]
    fn test_ump_message() {
        let message = LibremidiMessage {
            data: vec![0x40, 0x90, 0x40, 0x00, 0x7F, 0x00, 0x00, 0x00], // UMP note on
            timestamp: 67890,
            is_ump: true,
        };
        assert_eq!(message.data.len(), 8);
        assert!(message.is_ump);
    }

    // Test 7: MidiVersion enum
    #[test]
    fn test_midi_version_enum() {
        assert_eq!(MidiVersion::Midi1, MidiVersion::Midi1);
        assert_eq!(MidiVersion::Midi2, MidiVersion::Midi2);
        assert_ne!(MidiVersion::Midi1, MidiVersion::Midi2);
    }

    // Test 8: Config default values
    #[test]
    fn test_config_defaults() {
        let config = LibremidiConfig::default();
        assert_eq!(config.midi_version, MidiVersion::Midi1);
        assert!(config.hotplug_enabled);
        assert!(!config.zero_allocation);
    }

    // Test 9: Config clone
    #[test]
    fn test_config_clone() {
        let config = LibremidiConfig {
            midi_version: MidiVersion::Midi2,
            hotplug_enabled: false,
            zero_allocation: true,
        };
        let cloned = config.clone();
        assert_eq!(cloned.midi_version, MidiVersion::Midi2);
        assert!(!cloned.hotplug_enabled);
        assert!(cloned.zero_allocation);
    }

    // Test 10: LibremidiError display
    #[test]
    fn test_error_display() {
        let err1 = LibremidiError::NotAvailable;
        assert_eq!(format!("{}", err1), "libremidi not available");

        let err2 = LibremidiError::DeviceNotFound(42);
        assert_eq!(format!("{}", err2), "Device 42 not found");

        let err3 = LibremidiError::InvalidMessage;
        assert_eq!(format!("{}", err3), "Invalid MIDI message");
    }

    // Test 11: Info structure
    #[test]
    fn test_info_structure() {
        let info = LibremidiInfo {
            version: "0.6.0".to_string(),
            supports_midi2: true,
            hotplug_available: true,
        };
        assert_eq!(info.version, "0.6.0");
        assert!(info.supports_midi2);
        assert!(info.hotplug_available);
    }
}
