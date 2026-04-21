//! Audio stream management
//! 
//! CPAL integration for device enumeration and stream creation.

use cpal::traits::{DeviceTrait, HostTrait};

/// Create output stream for device
pub fn create_output_stream(
    device: &cpal::Device,
    sample_rate: u32,
) -> Result<cpal::Stream, cpal::BuildStreamError> {
    let config = cpal::StreamConfig {
        channels: 2,
        sample_rate: cpal::SampleRate(sample_rate),
        buffer_size: cpal::BufferSize::Default,
    };
    
    let mut callback = crate::callback::AudioCallback::new(sample_rate, 2);
    
    let stream = device.build_output_stream(
        &config,
        move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
            callback.process(data);
        },
        move |err| {
            eprintln!("Stream error: {}", err);
        },
        None,
    )?;
    
    Ok(stream)
}

/// Get default output device
pub fn default_output_device() -> Option<cpal::Device> {
    let host = cpal::default_host();
    host.default_output_device()
}
