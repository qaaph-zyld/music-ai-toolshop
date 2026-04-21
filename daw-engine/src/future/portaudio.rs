//! PortAudio Integration
//!
//! FFI bindings to PortAudio - cross-platform audio I/O supporting
//! ASIO, WASAPI, CoreAudio, ALSA, JACK, PulseAudio.
//! Powers Audacity and many other audio applications.
//!
//! License: MIT
//! Repo: https://github.com/PortAudio/portaudio

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_int, c_void};

/// PortAudio error codes
pub type PaError = c_int;

/// Opaque handle to PortAudio stream
#[repr(C)]
pub struct PaStream {
    _private: [u8; 0],
}

/// Device info structure
#[repr(C)]
#[derive(Debug, Clone)]
pub struct PaDeviceInfo {
    pub struct_version: c_int,
    pub name: *const c_char,
    pub host_api: c_int,
    pub max_input_channels: c_int,
    pub max_output_channels: c_int,
    pub default_low_input_latency: c_double,
    pub default_low_output_latency: c_double,
    pub default_high_input_latency: c_double,
    pub default_high_output_latency: c_double,
    pub default_sample_rate: c_double,
}

/// Stream parameters
#[repr(C)]
#[derive(Debug, Clone)]
pub struct PaStreamParameters {
    pub device: c_int,
    pub channel_count: c_int,
    pub sample_format: u64,
    pub suggested_latency: c_double,
    pub host_api_specific_stream_info: *mut c_void,
}

/// PortAudio error types
#[derive(Debug, Clone, PartialEq)]
pub enum PortAudioError {
    NotInitialized,
    InvalidDevice,
    InvalidChannelCount,
    InvalidSampleRate,
    InvalidFormat,
    StreamNotStarted,
    StreamNotStopped,
    FfiError(String),
}

impl std::fmt::Display for PortAudioError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PortAudioError::NotInitialized => write!(f, "PortAudio not initialized"),
            PortAudioError::InvalidDevice => write!(f, "Invalid device index"),
            PortAudioError::InvalidChannelCount => write!(f, "Invalid channel count"),
            PortAudioError::InvalidSampleRate => write!(f, "Invalid sample rate"),
            PortAudioError::InvalidFormat => write!(f, "Invalid sample format"),
            PortAudioError::StreamNotStarted => write!(f, "Stream not started"),
            PortAudioError::StreamNotStopped => write!(f, "Stream not stopped"),
            PortAudioError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for PortAudioError {}

/// Device information
#[derive(Debug, Clone)]
pub struct DeviceInfo {
    pub index: i32,
    pub name: String,
    pub max_input_channels: i32,
    pub max_output_channels: i32,
    pub default_sample_rate: f64,
    pub is_default_input: bool,
    pub is_default_output: bool,
}

/// Stream configuration
#[derive(Debug, Clone)]
pub struct StreamConfig {
    pub input_device: Option<i32>,
    pub output_device: Option<i32>,
    pub sample_rate: f64,
    pub frames_per_buffer: u32,
    pub input_channels: i32,
    pub output_channels: i32,
}

impl Default for StreamConfig {
    fn default() -> Self {
        Self {
            input_device: None,
            output_device: None,
            sample_rate: 44100.0,
            frames_per_buffer: 256,
            input_channels: 0,
            output_channels: 2,
        }
    }
}

/// PortAudio context
pub struct PortAudioContext {
    initialized: bool,
}

/// PortAudio stream
pub struct PortAudioStream {
    stream: *mut PaStream,
    running: bool,
}

// FFI function declarations
extern "C" {
    fn portaudio_ffi_is_available() -> c_int;
    fn portaudio_ffi_get_version() -> *const c_char;
    fn portaudio_ffi_get_version_text() -> *const c_char;
    
    // Initialization
    fn portaudio_ffi_initialize() -> PaError;
    fn portaudio_ffi_terminate() -> PaError;
    
    // Device enumeration
    fn portaudio_ffi_get_device_count() -> c_int;
    fn portaudio_ffi_get_default_input_device() -> c_int;
    fn portaudio_ffi_get_default_output_device() -> c_int;
    fn portaudio_ffi_get_device_info(device: c_int) -> *const PaDeviceInfo;
    
    // Stream
    fn portaudio_ffi_open_stream(
        input_params: *const PaStreamParameters,
        output_params: *const PaStreamParameters,
        sample_rate: c_double,
        frames_per_buffer: c_int,
        stream_flags: u64,
        callback: *mut c_void,
        user_data: *mut c_void,
    ) -> *mut PaStream;
    fn portaudio_ffi_close_stream(stream: *mut PaStream) -> PaError;
    fn portaudio_ffi_start_stream(stream: *mut PaStream) -> PaError;
    fn portaudio_ffi_stop_stream(stream: *mut PaStream) -> PaError;
    fn portaudio_ffi_abort_stream(stream: *mut PaStream) -> PaError;
    fn portaudio_ffi_is_stream_stopped(stream: *mut PaStream) -> c_int;
    fn portaudio_ffi_is_stream_active(stream: *mut PaStream) -> c_int;
}

impl PortAudioContext {
    /// Initialize PortAudio
    pub fn new() -> Result<Self, PortAudioError> {
        if !Self::is_available() {
            return Err(PortAudioError::FfiError("PortAudio not available".to_string()));
        }

        unsafe {
            let result = portaudio_ffi_initialize();
            if result != 0 {
                return Err(PortAudioError::NotInitialized);
            }
            Ok(Self { initialized: true })
        }
    }

    /// Check if PortAudio is available
    pub fn is_available() -> bool {
        unsafe { portaudio_ffi_is_available() != 0 }
    }

    /// Get PortAudio version
    pub fn version() -> String {
        unsafe {
            let version_ptr = portaudio_ffi_get_version_text();
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
        unsafe { portaudio_ffi_get_device_count() }
    }

    /// Get default input device index
    pub fn default_input_device(&self) -> Option<i32> {
        let device = unsafe { portaudio_ffi_get_default_input_device() };
        if device >= 0 {
            Some(device)
        } else {
            None
        }
    }

    /// Get default output device index
    pub fn default_output_device(&self) -> Option<i32> {
        let device = unsafe { portaudio_ffi_get_default_output_device() };
        if device >= 0 {
            Some(device)
        } else {
            None
        }
    }

    /// Get device info
    pub fn device_info(&self, device_index: i32) -> Option<DeviceInfo> {
        unsafe {
            let info_ptr = portaudio_ffi_get_device_info(device_index);
            if info_ptr.is_null() {
                return None;
            }

            let info = &*info_ptr;
            let name = CStr::from_ptr(info.name)
                .to_string_lossy()
                .into_owned();

            Some(DeviceInfo {
                index: device_index,
                name,
                max_input_channels: info.max_input_channels,
                max_output_channels: info.max_output_channels,
                default_sample_rate: info.default_sample_rate,
                is_default_input: self.default_input_device() == Some(device_index),
                is_default_output: self.default_output_device() == Some(device_index),
            })
        }
    }

    /// Enumerate all devices
    pub fn enumerate_devices(&self) -> Vec<DeviceInfo> {
        let count = self.device_count();
        (0..count)
            .filter_map(|i| self.device_info(i))
            .collect()
    }

    /// Open audio stream
    pub fn open_stream(&self, config: &StreamConfig) -> Result<PortAudioStream, PortAudioError> {
        // TODO: Implement stream opening with proper parameters
        Err(PortAudioError::FfiError("Stream opening not fully implemented".to_string()))
    }
}

impl Drop for PortAudioContext {
    fn drop(&mut self) {
        if self.initialized {
            unsafe {
                portaudio_ffi_terminate();
            }
        }
    }
}

impl PortAudioStream {
    /// Start the stream
    pub fn start(&mut self) -> Result<(), PortAudioError> {
        unsafe {
            let result = portaudio_ffi_start_stream(self.stream);
            if result == 0 {
                self.running = true;
                Ok(())
            } else {
                Err(PortAudioError::StreamNotStarted)
            }
        }
    }

    /// Stop the stream
    pub fn stop(&mut self) -> Result<(), PortAudioError> {
        unsafe {
            let result = portaudio_ffi_stop_stream(self.stream);
            if result == 0 {
                self.running = false;
                Ok(())
            } else {
                Err(PortAudioError::StreamNotStopped)
            }
        }
    }

    /// Check if stream is active
    pub fn is_active(&self) -> bool {
        unsafe { portaudio_ffi_is_stream_active(self.stream) != 0 }
    }

    /// Check if stream is stopped
    pub fn is_stopped(&self) -> bool {
        unsafe { portaudio_ffi_is_stream_stopped(self.stream) != 0 }
    }
}

impl Drop for PortAudioStream {
    fn drop(&mut self) {
        unsafe {
            if !self.stream.is_null() {
                portaudio_ffi_close_stream(self.stream);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_portaudio_module_exists() {
        let _ = PortAudioError::NotInitialized;
        let _config = StreamConfig::default();
    }

    #[test]
    fn test_portaudio_is_available() {
        let available = PortAudioContext::is_available();
        println!("PortAudio available: {}", available);
    }

    #[test]
    fn test_portaudio_version() {
        let version = PortAudioContext::version();
        println!("PortAudio version: {}", version);
    }

    #[test]
    fn test_context_creation() {
        let result = PortAudioContext::new();
        match result {
            Ok(ctx) => {
                // Context created successfully
                let count = ctx.device_count();
                println!("PortAudio device count: {}", count);
            }
            Err(e) => {
                println!("Context creation failed (expected if PortAudio not available): {}", e);
            }
        }
    }

    #[test]
    fn test_stream_config_defaults() {
        let config = StreamConfig::default();
        assert_eq!(config.sample_rate, 44100.0);
        assert_eq!(config.frames_per_buffer, 256);
        assert_eq!(config.output_channels, 2);
    }

    #[test]
    fn test_device_enumeration() {
        if let Ok(ctx) = PortAudioContext::new() {
            let devices = ctx.enumerate_devices();
            println!("Found {} devices", devices.len());
            for device in &devices {
                println!("  {}: {} (in: {}, out: {})",
                    device.index,
                    device.name,
                    device.max_input_channels,
                    device.max_output_channels
                );
            }
        }
    }

    #[test]
    fn test_default_devices() {
        if let Ok(ctx) = PortAudioContext::new() {
            let default_input = ctx.default_input_device();
            let default_output = ctx.default_output_device();
            println!("Default input: {:?}, Default output: {:?}", default_input, default_output);
        }
    }

    #[test]
    fn test_portaudio_error_display() {
        let err = PortAudioError::NotInitialized;
        assert!(err.to_string().contains("not initialized"));

        let err = PortAudioError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_device_info_structure() {
        let device = DeviceInfo {
            index: 0,
            name: "Test Device".to_string(),
            max_input_channels: 2,
            max_output_channels: 2,
            default_sample_rate: 48000.0,
            is_default_input: false,
            is_default_output: true,
        };
        
        assert_eq!(device.index, 0);
        assert_eq!(device.name, "Test Device");
        assert!(device.is_default_output);
    }
}
