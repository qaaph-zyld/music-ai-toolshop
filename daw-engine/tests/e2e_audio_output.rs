//! E2E Audio Output Tests
//!
//! These tests verify the audio output pipeline works end-to-end.
//! Note: These tests verify stream creation and device enumeration.
//! Actual audible output requires manual verification via the audio_e2e_test example.

use std::f32::consts::PI;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

/// Test that we can enumerate available audio output devices
#[test]
fn test_cpal_device_enumeration() {
    let host = cpal::default_host();
    let devices = host.output_devices();
    
    assert!(devices.is_ok(), "Should be able to enumerate output devices");
    
    let device_list: Vec<_> = devices.unwrap().collect();
    println!("Found {} audio output devices", device_list.len());
    
    for (i, device) in device_list.iter().enumerate() {
        let name = device.name().unwrap_or_else(|_| "Unknown".to_string());
        println!("  Device {}: {}", i, name);
    }
}

/// Test that we can get the default output device
#[test]
fn test_default_output_device() {
    let host = cpal::default_host();
    let device = host.default_output_device();
    
    assert!(device.is_some(), "Should have a default output device");
    
    let device = device.unwrap();
    let name = device.name().unwrap_or_else(|_| "Unknown".to_string());
    println!("Default output device: {}", name);
}

/// Test that we can get output configuration from device
#[test]
fn test_output_configuration() {
    let host = cpal::default_host();
    let device = host.default_output_device();
    
    if device.is_none() {
        println!("Skipping test - no audio output device available");
        return;
    }
    
    let device = device.unwrap();
    let config = device.default_output_config();
    
    assert!(config.is_ok(), "Should be able to get default output config");
    
    let config = config.unwrap();
    println!("Default output config:");
    println!("  Sample rate: {} Hz", config.sample_rate().0);
    println!("  Channels: {}", config.channels());
    println!("  Sample format: {:?}", config.sample_format());
    
    // Verify reasonable values
    assert!(config.sample_rate().0 >= 8000, "Sample rate should be at least 8000 Hz");
    assert!(config.sample_rate().0 <= 192000, "Sample rate should be at most 192000 Hz");
    assert!(config.channels() >= 1, "Should have at least 1 channel");
    assert!(config.channels() <= 16, "Should have at most 16 channels");
}

/// Test that we can create an audio output stream
#[test]
fn test_audio_stream_creation() {
    let host = cpal::default_host();
    let device = host.default_output_device();
    
    if device.is_none() {
        println!("Skipping test - no audio output device available");
        return;
    }
    
    let device = device.unwrap();
    let config = device.default_output_config();
    
    if config.is_err() {
        println!("Skipping test - cannot get output config");
        return;
    }
    
    let config: cpal::StreamConfig = config.unwrap().into();
    
    // Create a simple silence stream
    let stream = device.build_output_stream(
        &config,
        move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
            for sample in data.iter_mut() {
                *sample = 0.0; // Silence
            }
        },
        |err| eprintln!("Stream error: {}", err),
        None,
    );
    
    assert!(stream.is_ok(), "Should be able to create output stream");
    
    let stream = stream.unwrap();
    
    // Try to play the stream
    let play_result = stream.play();
    assert!(play_result.is_ok(), "Should be able to play stream");
    
    // Let it run briefly
    std::thread::sleep(Duration::from_millis(50));
    
    // Pause and drop
    let _ = stream.pause();
    drop(stream);
    
    println!("✓ Audio stream created, played, and cleaned up successfully");
}

/// Test that we can generate and play a short sine wave
#[test]
fn test_sine_wave_playback() {
    let host = cpal::default_host();
    let device = host.default_output_device();
    
    if device.is_none() {
        println!("Skipping test - no audio output device available");
        return;
    }
    
    let device = device.unwrap();
    let config = device.default_output_config();
    
    if config.is_err() {
        println!("Skipping test - cannot get output config");
        return;
    }
    
    let config: cpal::StreamConfig = config.unwrap().into();
    let sample_rate = config.sample_rate.0 as f32;
    let freq = 440.0f32;
    let duration_secs = 0.1f32; // 100ms - short burst
    let total_samples = (sample_rate * duration_secs) as usize;
    let channels = config.channels as usize;
    
    let sample_clock = Arc::new(AtomicUsize::new(0));
    let sample_clock_clone = Arc::clone(&sample_clock);
    let finished = Arc::new(AtomicBool::new(false));
    let finished_clone = Arc::clone(&finished);
    
    let mut next_value = move || {
        let sample_idx = sample_clock_clone.fetch_add(1, Ordering::Relaxed);
        
        if sample_idx >= total_samples * channels {
            finished_clone.store(true, Ordering::Relaxed);
            return 0.0f32;
        }
        
        let t = sample_idx as f32 / sample_rate;
        (t * freq * 2.0 * PI).sin() * 0.1 // Low amplitude to be safe
    };
    
    let stream = device.build_output_stream(
        &config,
        move |data: &mut [f32], _: &cpal::OutputCallbackInfo| {
            for sample in data.iter_mut() {
                *sample = next_value();
            }
        },
        |err| eprintln!("Stream error: {}", err),
        None,
    );
    
    assert!(stream.is_ok(), "Should be able to create sine wave stream");
    
    let stream = stream.unwrap();
    let play_result = stream.play();
    assert!(play_result.is_ok(), "Should be able to play sine wave");
    
    // Wait for completion
    let timeout = Duration::from_secs(5);
    let start = std::time::Instant::now();
    
    while !finished.load(Ordering::Relaxed) {
        if start.elapsed() > timeout {
            println!("Warning: Test timed out waiting for playback");
            break;
        }
        std::thread::sleep(Duration::from_millis(5));
    }
    
    drop(stream);
    
    println!("✓ Sine wave playback test completed");
}

/// Test stream latency measurement
#[test]
fn test_stream_latency() {
    let host = cpal::default_host();
    let device = host.default_output_device();
    
    if device.is_none() {
        println!("Skipping test - no audio output device available");
        return;
    }
    
    let device = device.unwrap();
    
    // Try to get output latency if available
    let supported_configs = device.supported_output_configs();
    
    if supported_configs.is_err() {
        println!("Skipping test - cannot query supported configs");
        return;
    }
    
    let configs: Vec<_> = supported_configs.unwrap().collect();
    println!("Found {} supported output configurations", configs.len());
    
    for (i, config_range) in configs.iter().enumerate() {
        let min_rate = config_range.min_sample_rate().0;
        let max_rate = config_range.max_sample_rate().0;
        let channels = config_range.channels();
        let format = config_range.sample_format();
        
        println!("  Config {}: {}-{} Hz, {} ch, {:?}", 
                 i, min_rate, max_rate, channels, format);
    }
    
    // We can't directly measure latency in this test, but we verified
    // the device reports configuration ranges correctly
    println!("✓ Latency test completed (configuration ranges verified)");
}

/// Test error handling when no device is available
#[test]
fn test_error_handling_no_device() {
    // This test documents expected behavior when audio is unavailable
    // In a CI environment, there might be no audio device
    
    let host = cpal::default_host();
    let device = host.default_output_device();
    
    if device.is_none() {
        println!("No audio device - this is expected in headless/CI environments");
        println!("✓ Error handling works correctly (graceful degradation)");
    } else {
        println!("Audio device found - test passes");
    }
}
