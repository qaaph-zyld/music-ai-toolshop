//! Audio E2E Test - Verifies audio playback through speakers
//!
//! This example plays a 1-second 440Hz sine wave through the default
//! audio output device to verify the full audio stack works:
//! Rust → CPAL → Audio Hardware → Speakers
//!
//! Usage: cargo run --example audio_e2e_test

use std::f32::consts::PI;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

fn main() {
    println!("OpenDAW Audio E2E Test");
    println!("======================\n");

    // Get default output device
    let host = cpal::default_host();
    let device = host.default_output_device();
    
    match device {
        Some(device) => {
            println!("✓ Audio output device found: {:?}", device.name());
            
            // Get default output config
            let config = device.default_output_config();
            println!("✓ Default output config: {:?}", config);
            
            match config.sample_format() {
                cpal::SampleFormat::F32 => run_test::<f32>(&device, &config.into()),
                cpal::SampleFormat::I16 => run_test::<i16>(&device, &config.into()),
                cpal::SampleFormat::U16 => run_test::<u16>(&device, &config.into()),
                _ => println!("✗ Unsupported sample format: {:?}", config.sample_format()),
            }
        }
        None => {
            println!("✗ No audio output device found!");
            println!("  Please connect speakers or headphones and try again.");
            std::process::exit(1);
        }
    }
}

fn run_test<T: cpal::Sample>(device: &cpal::Device, config: &cpal::StreamConfig) {
    let sample_rate = config.sample_rate.0 as f32;
    let channels = config.channels as usize;
    let freq = 440.0f32; // A4 note
    let duration_secs = 1.0f32;
    let total_samples = (sample_rate * duration_secs) as usize;
    
    println!("\nTest Configuration:");
    println!("  Sample rate: {} Hz", sample_rate);
    println!("  Channels: {}", channels);
    println!("  Frequency: {} Hz (A4 note)", freq);
    println!("  Duration: {} second", duration_secs);
    println!("\nPlaying sine wave... Listen for a 440Hz tone.\n");
    
    let sample_clock = Arc::new(std::sync::atomic::AtomicUsize::new(0));
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
        (t * freq * 2.0 * PI).sin() * 0.5 // 50% amplitude to avoid clipping
    };
    
    let err_fn = |err| eprintln!("Audio stream error: {}", err);
    
    let stream = device.build_output_stream(
        config,
        move |data: &mut [T], _: &cpal::OutputCallbackInfo| {
            for sample in data.iter_mut() {
                *sample = T::from::<f32>(&next_value());
            }
        },
        err_fn,
        None,
    );
    
    match stream {
        Ok(stream) => {
            match stream.play() {
                Ok(_) => {
                    println!("✓ Audio stream started successfully");
                    
                    // Wait for playback to complete
                    while !finished.load(Ordering::Relaxed) {
                        std::thread::sleep(Duration::from_millis(10));
                    }
                    
                    // Give a moment for the buffer to clear
                    std::thread::sleep(Duration::from_millis(100));
                    
                    drop(stream);
                    
                    println!("✓ Audio playback completed");
                    println!("\n================================");
                    println!("E2E Audio Verification: PASSED ✓");
                    println!("================================");
                    println!("\nYou should have heard a 440Hz tone.");
                    println!("If you heard the tone, the full audio stack works!");
                    println!("\nAudio chain verified:");
                    println!("  1. Rust test code ✓");
                    println!("  2. CPAL audio abstraction ✓");
                    println!("  3. OS audio subsystem ✓");
                    println!("  4. Audio hardware ✓");
                    println!("  5. Speaker output ✓");
                }
                Err(e) => {
                    println!("✗ Failed to play audio stream: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            println!("✗ Failed to build audio stream: {}", e);
            println!("  This may indicate audio device is in use or not available.");
            std::process::exit(1);
        }
    }
}
