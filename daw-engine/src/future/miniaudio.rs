//! Miniaudio Integration
//!
//! FFI bindings to miniaudio single-file audio library for alternative
//! audio I/O, mixing, and node graph processing.
//!
//! Miniaudio provides:
//! - Cross-platform audio device enumeration
//! - Playback and capture streams
//! - Built-in mixing and effects node graph
//! - Zero external dependencies (single C file)
//!
//! License: Public Domain / MIT-0
//! Repo: https://github.com/mackron/miniaudio

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_uint, c_void};

// FFI type aliases
#[allow(non_camel_case_types)]
type ma_bool32 = u32;
#[allow(non_camel_case_types)]
type ma_uint32 = u32;

/// Opaque handle to miniaudio context
#[repr(C)]
pub struct MaContext {
    _private: [u8; 0],
}

/// Miniaudio device information
#[derive(Debug, Clone)]
pub struct MiniaudioDeviceInfo {
    pub index: i32,
    pub name: String,
    pub channels: u16,
    pub sample_rate: u32,
    pub is_default: bool,
}

/// Miniaudio context for device management
pub struct MiniaudioContext {
    context: *mut MaContext,
    devices: Vec<MiniaudioDeviceInfo>,
}

/// Miniaudio playback configuration
#[derive(Debug, Clone)]
pub struct PlaybackConfig {
    pub device_index: Option<i32>, // None for default
    pub channels: u16,
    pub sample_rate: u32,
    pub buffer_size: u32,
}

impl Default for PlaybackConfig {
    fn default() -> Self {
        Self {
            device_index: None,
            channels: 2,
            sample_rate: 44100,
            buffer_size: 512,
        }
    }
}

/// Miniaudio error types
#[derive(Debug, Clone, PartialEq)]
pub enum MiniaudioError {
    ContextInitFailed,
    DeviceEnumerationFailed,
    DeviceNotFound,
    PlaybackInitFailed,
    InvalidConfig,
    FfiError(String),
}

impl std::fmt::Display for MiniaudioError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MiniaudioError::ContextInitFailed => write!(f, "Failed to initialize miniaudio context"),
            MiniaudioError::DeviceEnumerationFailed => write!(f, "Device enumeration failed"),
            MiniaudioError::DeviceNotFound => write!(f, "Audio device not found"),
            MiniaudioError::PlaybackInitFailed => write!(f, "Playback initialization failed"),
            MiniaudioError::InvalidConfig => write!(f, "Invalid playback configuration"),
            MiniaudioError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

// FFI function declarations
extern "C" {
    fn ma_ffi_context_create() -> *mut MaContext;
    fn ma_ffi_context_destroy(ctx: *mut MaContext);
    fn ma_ffi_get_device_count(ctx: *mut MaContext) -> ma_uint32;
    fn ma_ffi_get_device_info(ctx: *mut MaContext, index: ma_uint32, info: *mut MaDeviceInfoFfi) -> ma_bool32;
    fn ma_ffi_get_version() -> *const c_char;
    fn ma_ffi_is_available() -> ma_bool32;
}

/// Device info structure from FFI
#[repr(C)]
#[derive(Debug, Clone)]
pub struct MaDeviceInfoFfi {
    name: [c_char; 256],
    channels: ma_uint32,
    sample_rate: ma_uint32,
    is_default: ma_bool32,
}

impl MiniaudioContext {
    /// Create new miniaudio context and enumerate devices
    pub fn new() -> Result<Self, MiniaudioError> {
        unsafe {
            let ctx = ma_ffi_context_create();
            if ctx.is_null() {
                return Err(MiniaudioError::ContextInitFailed);
            }

            // Enumerate devices
            let count = ma_ffi_get_device_count(ctx);
            let mut devices = Vec::with_capacity(count as usize);

            for i in 0..count {
                let mut ffi_info = MaDeviceInfoFfi {
                    name: [0; 256],
                    channels: 0,
                    sample_rate: 0,
                    is_default: 0,
                };

                if ma_ffi_get_device_info(ctx, i, &mut ffi_info) != 0 {
                    let name = CStr::from_ptr(ffi_info.name.as_ptr())
                        .to_string_lossy()
                        .into_owned();
                    
                    devices.push(MiniaudioDeviceInfo {
                        index: i as i32,
                        name,
                        channels: ffi_info.channels as u16,
                        sample_rate: ffi_info.sample_rate,
                        is_default: ffi_info.is_default != 0,
                    });
                }
            }

            Ok(Self {
                context: ctx,
                devices,
            })
        }
    }

    /// Get miniaudio version string
    pub fn version() -> String {
        unsafe {
            let version_ptr = ma_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Check if miniaudio is available (library loaded)
    pub fn is_available() -> bool {
        unsafe {
            ma_ffi_is_available() != 0
        }
    }

    /// Get device info by index
    pub fn device_info(&self, index: i32) -> Option<&MiniaudioDeviceInfo> {
        self.devices.get(index as usize)
    }

    /// Get all devices
    pub fn devices(&self) -> &[MiniaudioDeviceInfo] {
        &self.devices
    }

    /// Get default device index
    pub fn default_device_index(&self) -> Option<i32> {
        self.devices.iter()
            .find(|d| d.is_default)
            .map(|d| d.index)
    }

    /// Initialize playback with configuration
    pub fn init_playback(&self, _config: PlaybackConfig) -> Result<(), MiniaudioError> {
        // TODO: Initialize playback device via FFI
        Err(MiniaudioError::PlaybackInitFailed)
    }

    /// Get number of available devices
    pub fn device_count(&self) -> i32 {
        self.devices.len() as i32
    }
}

impl Drop for MiniaudioContext {
    fn drop(&mut self) {
        unsafe {
            if !self.context.is_null() {
                ma_ffi_context_destroy(self.context);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_miniaudio_module_exists() {
        // Verify the miniaudio module compiles and types are accessible
        let _ = MiniaudioError::ContextInitFailed;
        let _config = PlaybackConfig::default();
    }

    #[test]
    fn test_miniaudio_is_available() {
        // Test that is_available() returns true when library is linked
        let available = MiniaudioContext::is_available();
        // Should be true since we compiled the C wrapper
        assert!(available, "miniaudio should be available after compilation");
    }

    #[test]
    fn test_miniaudio_version() {
        // Test that we can get the version string
        let version = MiniaudioContext::version();
        assert!(!version.is_empty(), "Version should not be empty");
        assert_ne!(version, "unknown", "Should get actual version string");
    }

    #[test]
    fn test_miniaudio_context_creation() {
        // Test that context creation succeeds with compiled library
        let result = MiniaudioContext::new();
        
        // May fail if no audio devices available, but should not crash
        match result {
            Ok(ctx) => {
                // If context created, verify basic operations
                let count = ctx.device_count();
                assert!(count >= 0, "Device count should be non-negative");
                
                // Test device enumeration if devices exist
                if count > 0 {
                    let device = ctx.device_info(0);
                    assert!(device.is_some(), "Should get device info");
                    
                    let device = device.unwrap();
                    assert!(!device.name.is_empty(), "Device should have a name");
                    // channels=0 means "all channels supported" in miniaudio
                    // sample_rate=0 means "all sample rates supported"
                    println!("Device: {} (channels: {}, sample_rate: {})", 
                        device.name, device.channels, device.sample_rate);
                }
            }
            Err(e) => {
                // Context creation may fail on CI/headless environments
                // but should fail gracefully
                println!("Context creation failed (may be expected in CI): {}", e);
            }
        }
    }

    #[test]
    fn test_playback_config_defaults() {
        let config = PlaybackConfig::default();
        assert_eq!(config.channels, 2);
        assert_eq!(config.sample_rate, 44100);
        assert_eq!(config.buffer_size, 512);
        assert!(config.device_index.is_none()); // Default device
    }

    #[test]
    fn test_miniaudio_error_display() {
        let err = MiniaudioError::DeviceNotFound;
        assert!(err.to_string().contains("not found"));

        let err = MiniaudioError::FfiError("test error".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_miniaudio_device_info_structure() {
        let device = MiniaudioDeviceInfo {
            index: 0,
            name: "Test Device".to_string(),
            channels: 2,
            sample_rate: 48000,
            is_default: true,
        };
        
        assert_eq!(device.index, 0);
        assert_eq!(device.name, "Test Device");
        assert_eq!(device.channels, 2);
        assert_eq!(device.sample_rate, 48000);
        assert!(device.is_default);
    }
}
