//! RtAudio Integration
//!
//! FFI bindings to RtAudio - a set of C++ classes for
//! cross-platform realtime audio I/O. Lighter alternative to
//! PortAudio with ASIO/DirectSound/WASAPI/CoreAudio/ALSA/JACK/Pulse.
//!
//! License: MIT (with STK)
//! Repo: https://github.com/thestk/rtaudio

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_uint, c_void};

/// Opaque handle to RtAudio
#[repr(C)]
pub struct RtAudio {
    _private: [u8; 0],
}

/// Device information structure
#[repr(C)]
#[derive(Debug, Clone)]
pub struct RtAudioDeviceInfo {
    probed: bool,
    name: [c_char; 256],
    output_channels: c_uint,
    input_channels: c_uint,
    duplex_channels: c_uint,
    is_default_output: bool,
    is_default_input: bool,
    sample_rates: [c_uint; 16],
    num_sample_rates: c_uint,
    preferred_sample_rate: c_uint,
    native_formats: c_uint,
}

/// Stream options
#[repr(C)]
#[derive(Debug, Clone)]
pub struct RtAudioStreamOptions {
    flags: c_uint,
    num_buffers: c_uint,
    buffer_size: c_uint,
    priority: c_int,
}

/// Stream parameters
#[repr(C)]
#[derive(Debug, Clone)]
pub struct RtAudioStreamParameters {
    device_id: c_uint,
    num_channels: c_uint,
    first_channel: c_uint,
}

/// RtAudio error types
#[derive(Debug, Clone, PartialEq)]
pub enum RtAudioError {
    Warning,
    DebugWarning,
    Unspecified,
    NoDevicesFound,
    InvalidDevice,
    MemoryError,
    InvalidParameter,
    InvalidUse,
    DriverError,
    SystemError,
    ThreadError,
    FfiError(String),
}

impl std::fmt::Display for RtAudioError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RtAudioError::Warning => write!(f, "RtAudio warning"),
            RtAudioError::DebugWarning => write!(f, "RtAudio debug warning"),
            RtAudioError::Unspecified => write!(f, "Unspecified error"),
            RtAudioError::NoDevicesFound => write!(f, "No audio devices found"),
            RtAudioError::InvalidDevice => write!(f, "Invalid device index"),
            RtAudioError::MemoryError => write!(f, "Memory allocation error"),
            RtAudioError::InvalidParameter => write!(f, "Invalid parameter"),
            RtAudioError::InvalidUse => write!(f, "Invalid function use"),
            RtAudioError::DriverError => write!(f, "Audio driver error"),
            RtAudioError::SystemError => write!(f, "System error"),
            RtAudioError::ThreadError => write!(f, "Thread error"),
            RtAudioError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for RtAudioError {}

/// Audio format enum
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum RtAudioFormat {
    Sint8,
    Sint16,
    Sint24,
    Sint32,
    Float32,
    Float64,
}

impl RtAudioFormat {
    pub fn as_uint(&self) -> c_uint {
        match self {
            RtAudioFormat::Sint8 => 0x01,
            RtAudioFormat::Sint16 => 0x02,
            RtAudioFormat::Sint24 => 0x04,
            RtAudioFormat::Sint32 => 0x08,
            RtAudioFormat::Float32 => 0x10,
            RtAudioFormat::Float64 => 0x20,
        }
    }
}

/// Stream configuration
#[derive(Debug, Clone)]
pub struct RtAudioStreamConfig {
    pub output_device: Option<u32>,
    pub input_device: Option<u32>,
    pub sample_rate: u32,
    pub buffer_frames: u32,
    pub format: RtAudioFormat,
}

impl Default for RtAudioStreamConfig {
    fn default() -> Self {
        Self {
            output_device: None,
            input_device: None,
            sample_rate: 44100,
            buffer_frames: 256,
            format: RtAudioFormat::Float32,
        }
    }
}

/// RtAudio instance
pub struct RtAudioInstance {
    rt: *mut RtAudio,
}

/// RtAudio stream
pub struct RtAudioStream {
    rt: *mut RtAudio,
    running: bool,
}

// FFI function declarations
extern "C" {
    fn rtaudio_ffi_is_available() -> c_int;
    fn rtaudio_ffi_get_version() -> *const c_char;
    
    // Instance creation/destruction
    fn rtaudio_ffi_create(api: c_uint) -> *mut RtAudio;
    fn rtaudio_ffi_destroy(rt: *mut RtAudio);
    
    // Device enumeration
    fn rtaudio_ffi_get_device_count(rt: *mut RtAudio) -> c_int;
    fn rtaudio_ffi_get_device_info(rt: *mut RtAudio, device: c_uint) -> RtAudioDeviceInfo;
    fn rtaudio_ffi_get_default_output_device(rt: *mut RtAudio) -> c_uint;
    fn rtaudio_ffi_get_default_input_device(rt: *mut RtAudio) -> c_uint;
    
    // Stream
    fn rtaudio_ffi_open_stream(
        rt: *mut RtAudio,
        output_params: *const RtAudioStreamParameters,
        input_params: *const RtAudioStreamParameters,
        format: c_uint,
        sample_rate: c_uint,
        buffer_frames: *mut c_uint,
        callback: *mut c_void,
        user_data: *mut c_void,
        options: *const RtAudioStreamOptions,
    ) -> c_int;
    fn rtaudio_ffi_close_stream(rt: *mut RtAudio);
    fn rtaudio_ffi_start_stream(rt: *mut RtAudio) -> c_int;
    fn rtaudio_ffi_stop_stream(rt: *mut RtAudio) -> c_int;
    fn rtaudio_ffi_abort_stream(rt: *mut RtAudio) -> c_int;
    fn rtaudio_ffi_is_stream_running(rt: *mut RtAudio) -> c_int;
    fn rtaudio_ffi_is_stream_open(rt: *mut RtAudio) -> c_int;
    
    // Error handling
    fn rtaudio_ffi_get_error_text(rt: *mut RtAudio) -> *const c_char;
}

impl RtAudioInstance {
    /// Create new RtAudio instance with specified API (0 for unspecified)
    pub fn new(api: u32) -> Result<Self, RtAudioError> {
        if !Self::is_available() {
            return Err(RtAudioError::FfiError("RtAudio not available".to_string()));
        }

        unsafe {
            let rt = rtaudio_ffi_create(api);
            if rt.is_null() {
                return Err(RtAudioError::MemoryError);
            }
            Ok(Self { rt })
        }
    }

    /// Check if RtAudio is available
    pub fn is_available() -> bool {
        unsafe { rtaudio_ffi_is_available() != 0 }
    }

    /// Get RtAudio version
    pub fn version() -> String {
        unsafe {
            let version_ptr = rtaudio_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get device count
    pub fn device_count(&self) -> i32 {
        unsafe { rtaudio_ffi_get_device_count(self.rt) }
    }

    /// Get default output device
    pub fn default_output_device(&self) -> u32 {
        unsafe { rtaudio_ffi_get_default_output_device(self.rt) }
    }

    /// Get default input device
    pub fn default_input_device(&self) -> u32 {
        unsafe { rtaudio_ffi_get_default_input_device(self.rt) }
    }

    /// Get device info
    pub fn device_info(&self, device: u32) -> Option<RtAudioDeviceInfo> {
        unsafe {
            let info = rtaudio_ffi_get_device_info(self.rt, device);
            if !info.probed {
                return None;
            }
            Some(info)
        }
    }

    /// Get last error text
    pub fn error_text(&self) -> String {
        unsafe {
            let error_ptr = rtaudio_ffi_get_error_text(self.rt);
            if error_ptr.is_null() {
                return "unknown error".to_string();
            }
            CStr::from_ptr(error_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }
}

impl Drop for RtAudioInstance {
    fn drop(&mut self) {
        unsafe {
            if !self.rt.is_null() {
                rtaudio_ffi_destroy(self.rt);
            }
        }
    }
}

impl RtAudioStream {
    /// Check if stream is running
    pub fn is_running(&self) -> bool {
        unsafe { rtaudio_ffi_is_stream_running(self.rt) != 0 }
    }

    /// Check if stream is open
    pub fn is_open(&self) -> bool {
        unsafe { rtaudio_ffi_is_stream_open(self.rt) != 0 }
    }

    /// Start the stream
    pub fn start(&mut self) -> Result<(), RtAudioError> {
        unsafe {
            let result = rtaudio_ffi_start_stream(self.rt);
            if result != 0 {
                return Err(RtAudioError::DriverError);
            }
            self.running = true;
            Ok(())
        }
    }

    /// Stop the stream
    pub fn stop(&mut self) -> Result<(), RtAudioError> {
        unsafe {
            let result = rtaudio_ffi_stop_stream(self.rt);
            if result != 0 {
                return Err(RtAudioError::DriverError);
            }
            self.running = false;
            Ok(())
        }
    }
}

impl Drop for RtAudioStream {
    fn drop(&mut self) {
        unsafe {
            if !self.rt.is_null() {
                rtaudio_ffi_close_stream(self.rt);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rtaudio_module_exists() {
        let _ = RtAudioError::NoDevicesFound;
        let _ = RtAudioFormat::Float32;
        let _config = RtAudioStreamConfig::default();
    }

    #[test]
    fn test_rtaudio_is_available() {
        let available = RtAudioInstance::is_available();
        println!("RtAudio available: {}", available);
    }

    #[test]
    fn test_rtaudio_version() {
        let version = RtAudioInstance::version();
        println!("RtAudio version: {}", version);
    }

    #[test]
    fn test_rtaudio_create() {
        let result = RtAudioInstance::new(0); // Unspecified API
        match result {
            Ok(rt) => {
                let count = rt.device_count();
                println!("RtAudio device count: {}", count);
            }
            Err(e) => {
                println!("RtAudio creation failed (expected if not available): {}", e);
            }
        }
    }

    #[test]
    fn test_stream_config_defaults() {
        let config = RtAudioStreamConfig::default();
        assert_eq!(config.sample_rate, 44100);
        assert_eq!(config.buffer_frames, 256);
        assert_eq!(config.format, RtAudioFormat::Float32);
    }

    #[test]
    fn test_rtaudio_format_as_uint() {
        assert_eq!(RtAudioFormat::Sint8.as_uint(), 0x01);
        assert_eq!(RtAudioFormat::Sint16.as_uint(), 0x02);
        assert_eq!(RtAudioFormat::Float32.as_uint(), 0x10);
        assert_eq!(RtAudioFormat::Float64.as_uint(), 0x20);
    }

    #[test]
    fn test_device_enumeration() {
        if let Ok(rt) = RtAudioInstance::new(0) {
            let count = rt.device_count();
            println!("Found {} RtAudio devices", count);
            
            for i in 0..count as u32 {
                if let Some(info) = rt.device_info(i) {
                    let name = unsafe {
                        CStr::from_ptr(info.name.as_ptr())
                            .to_string_lossy()
                            .into_owned()
                    };
                    println!("  {}: {} (in: {}, out: {})",
                        i, name, info.input_channels, info.output_channels);
                }
            }
        }
    }

    #[test]
    fn test_default_devices() {
        if let Ok(rt) = RtAudioInstance::new(0) {
            let default_output = rt.default_output_device();
            let default_input = rt.default_input_device();
            println!("Default output: {}, Default input: {}", default_output, default_input);
        }
    }

    #[test]
    fn test_rtaudio_error_display() {
        let err = RtAudioError::NoDevicesFound;
        assert!(err.to_string().contains("No audio devices"));

        let err = RtAudioError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }
}
