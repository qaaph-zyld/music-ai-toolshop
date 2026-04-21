//! CPAL integration tests
//! 
//! Tests for audio device enumeration and stream creation.

use cpal::traits::{DeviceTrait, StreamTrait};
use daw_engine::stream::{create_output_stream, default_output_device};

#[test]
#[ignore = "Requires audio hardware"]
fn test_cpal_stream_creation() {
    let device = default_output_device()
        .expect("No output device available");
    
    let stream = create_output_stream(&device, 48000)
        .expect("Should create stream");
    
    stream.play().expect("Should play");
    std::thread::sleep(std::time::Duration::from_millis(100));
}

#[test]
fn test_default_output_device_exists() {
    // This test checks if a device exists, but doesn't require audio hardware to work
    // It will pass even without hardware (returning None is valid)
    let _device = default_output_device();
    // Test passes if we get here without panicking
}

#[test]
#[ignore = "Requires audio hardware"]
fn test_stream_produces_audio() {
    use std::sync::{Arc, Mutex};
    
    let device = default_output_device()
        .expect("No output device available");
    
    let samples_received = Arc::new(Mutex::new(Vec::new()));
    let samples_clone = samples_received.clone();
    
    let config = cpal::StreamConfig {
        channels: 2,
        sample_rate: cpal::SampleRate(48000),
        buffer_size: cpal::BufferSize::Default,
    };
    
    let stream = device.build_output_stream(
        &config,
        move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
            let mut samples = samples_clone.lock().unwrap();
            samples.extend_from_slice(data);
        },
        move |err| {
            eprintln!("Stream error: {}", err);
        },
        None,
    ).expect("Should create stream");
    
    stream.play().expect("Should play");
    std::thread::sleep(std::time::Duration::from_millis(100));
    
    let samples = samples_received.lock().unwrap();
    assert!(!samples.is_empty(), "Should have received audio samples");
    assert!(samples.iter().any(|&s| s != 0.0), "Should have non-zero samples");
}
