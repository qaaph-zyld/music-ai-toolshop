//! Audio Device Management
//!
//! CPAL-based audio device enumeration and selection for real-time output.

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};
use std::sync::{Arc, Mutex};

use crate::mixer::Mixer;
use crate::transport::Transport;

/// Audio device information
#[derive(Debug, Clone)]
pub struct AudioDeviceInfo {
    pub index: i32,
    pub name: String,
    pub channels: u16,
    pub sample_rate: u32,
}

/// Audio device manager for enumeration and stream control
pub struct AudioDeviceManager {
    devices: Vec<AudioDeviceInfo>,
    current_device: AtomicI32,
    streaming: AtomicBool,
    stream_handle: Option<cpal::Stream>,
}

impl AudioDeviceManager {
    /// Create new device manager and enumerate devices
    pub fn new() -> Self {
        let devices = Self::enumerate_devices();
        Self {
            devices,
            current_device: AtomicI32::new(-1),
            streaming: AtomicBool::new(false),
            stream_handle: None,
        }
    }

    /// Enumerate available output devices
    fn enumerate_devices() -> Vec<AudioDeviceInfo> {
        let host = cpal::default_host();
        let mut devices = Vec::new();
        let mut index = 0;

        if let Ok(output_devices) = host.output_devices() {
            for device in output_devices {
                if let Ok(name) = device.name() {
                    // Try to get default config for channel count
                    let channels = if let Ok(config) = device.default_output_config() {
                        config.channels()
                    } else {
                        2 // Assume stereo
                    };

                    let sample_rate = if let Ok(config) = device.default_output_config() {
                        config.sample_rate().0
                    } else {
                        44100
                    };

                    devices.push(AudioDeviceInfo {
                        index,
                        name,
                        channels,
                        sample_rate,
                    });
                    index += 1;
                }
            }
        }

        devices
    }

    /// Get number of devices
    pub fn device_count(&self) -> i32 {
        self.devices.len() as i32
    }

    /// Get device info by index
    pub fn device_info(&self, index: i32) -> Option<&AudioDeviceInfo> {
        self.devices.get(index as usize)
    }

    /// Get all devices
    pub fn devices(&self) -> &[AudioDeviceInfo] {
        &self.devices
    }

    /// Check if currently streaming
    pub fn is_streaming(&self) -> bool {
        self.streaming.load(Ordering::SeqCst)
    }

    /// Get current device index
    pub fn current_device(&self) -> i32 {
        self.current_device.load(Ordering::SeqCst)
    }

    /// Start audio stream with mixer
    pub fn start_stream(
        &mut self,
        device_index: i32,
        sample_rate: u32,
        mixer: Arc<Mutex<Mixer>>,
        transport: Arc<Mutex<Transport>>,
    ) -> Result<(), AudioDeviceError> {
        if self.is_streaming() {
            return Err(AudioDeviceError::AlreadyStreaming);
        }

        let host = cpal::default_host();
        let devices: Vec<_> = host.output_devices().map_err(|_| AudioDeviceError::DeviceNotFound)?.collect();
        
        let device = devices.get(device_index as usize)
            .ok_or(AudioDeviceError::InvalidDeviceIndex)?;

        let config = cpal::StreamConfig {
            channels: 2,
            sample_rate: cpal::SampleRate(sample_rate),
            buffer_size: cpal::BufferSize::Default,
        };

        // Create mixer clone for callback
        let mixer_clone = Arc::clone(&mixer);
        let transport_clone = Arc::clone(&transport);

        let stream = device.build_output_stream(
            &config,
            move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
                // Process audio through mixer
                if let (Ok(mut mix), Ok(mut trans)) = (mixer_clone.lock(), transport_clone.lock()) {
                    // Process transport (advances position)
                    let frames = data.len() / 2; // Stereo frames
                    trans.process(frames as u32);
                    
                    // Process mixer (fills buffer)
                    mix.process(data);
                } else {
                    // Silence if mutex poisoned
                    for sample in data.iter_mut() {
                        *sample = 0.0;
                    }
                }
            },
            move |err| {
                eprintln!("Audio stream error: {}", err);
            },
            None,
        ).map_err(|e| AudioDeviceError::StreamError(e.to_string()))?;

        stream.play().map_err(|e: cpal::PlayStreamError| AudioDeviceError::StreamError(e.to_string()))?;

        self.current_device.store(device_index, Ordering::SeqCst);
        self.streaming.store(true, Ordering::SeqCst);
        self.stream_handle = Some(stream);

        Ok(())
    }

    /// Stop audio stream
    pub fn stop_stream(&mut self) -> Result<(), AudioDeviceError> {
        if !self.is_streaming() {
            return Err(AudioDeviceError::NotStreaming);
        }

        if let Some(stream) = self.stream_handle.take() {
            drop(stream);
        }

        self.streaming.store(false, Ordering::SeqCst);
        self.current_device.store(-1, Ordering::SeqCst);

        Ok(())
    }
}

impl Default for AudioDeviceManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Audio device errors
#[derive(Debug, thiserror::Error)]
pub enum AudioDeviceError {
    #[error("No audio devices found")]
    NoDevices,
    #[error("Device not found")]
    DeviceNotFound,
    #[error("Invalid device index")]
    InvalidDeviceIndex,
    #[error("Already streaming")]
    AlreadyStreaming,
    #[error("Not streaming")]
    NotStreaming,
    #[error("Stream error: {0}")]
    StreamError(String),
    #[error("Mutex poisoned")]
    MutexPoisoned,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_device_manager_creation() {
        let manager = AudioDeviceManager::new();
        // Should enumerate without panicking
        assert!(manager.device_count() >= 0);
    }

    #[test]
    fn test_device_info_bounds() {
        let manager = AudioDeviceManager::new();
        let count = manager.device_count();
        
        // Invalid index should return None
        assert!(manager.device_info(-1).is_none());
        assert!(manager.device_info(count).is_none());
        
        // Valid indices should return Some (if devices exist)
        if count > 0 {
            assert!(manager.device_info(0).is_some());
        }
    }

    #[test]
    fn test_not_streaming_initially() {
        let manager = AudioDeviceManager::new();
        assert!(!manager.is_streaming());
        assert_eq!(manager.current_device(), -1);
    }

    #[test]
    fn test_stop_without_start_fails() {
        let mut manager = AudioDeviceManager::new();
        assert!(matches!(
            manager.stop_stream(),
            Err(AudioDeviceError::NotStreaming)
        ));
    }

    #[test]
    fn test_invalid_device_index_fails() {
        let mut manager = AudioDeviceManager::new();
        let mixer = Arc::new(Mutex::new(Mixer::new(2)));
        let transport = Arc::new(Mutex::new(Transport::new(120.0, 44100)));
        
        let result = manager.start_stream(9999, 44100, mixer, transport);
        assert!(matches!(
            result,
            Err(AudioDeviceError::InvalidDeviceIndex) | Err(AudioDeviceError::DeviceNotFound)
        ));
    }

    #[test]
    fn test_double_start_fails() {
        let mut manager = AudioDeviceManager::new();
        
        // If no devices, can't test double start
        if manager.device_count() == 0 {
            return;
        }

        let mixer = Arc::new(Mutex::new(Mixer::new(2)));
        let transport = Arc::new(Mutex::new(Transport::new(120.0, 44100)));
        
        // First start (may succeed or fail depending on device availability)
        let _ = manager.start_stream(0, 44100, mixer.clone(), transport.clone());
        
        // Second start should fail with AlreadyStreaming if first succeeded
        if manager.is_streaming() {
            let result = manager.start_stream(0, 44100, mixer, transport);
            assert!(matches!(result, Err(AudioDeviceError::AlreadyStreaming)));
            
            // Cleanup
            let _ = manager.stop_stream();
        }
    }
}
