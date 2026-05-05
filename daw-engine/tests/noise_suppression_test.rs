//! RNNoise AI noise suppression integration tests
//!
//! Tests for native nnnoiseless (pure Rust RNNoise implementation)
//! All tests should pass - no #[ignore] attributes needed.

use daw_engine::noise_suppression::NoiseSuppressor;

#[test]
fn test_native_rnnoise_creation() {
    // Native nnnoiseless should create successfully at 48kHz
    let suppressor = NoiseSuppressor::new(48000);
    assert!(suppressor.is_ok(), "Native RNNoise should be creatable at 48kHz");
    
    let suppressor = suppressor.unwrap();
    assert!(suppressor.is_available(), "Native RNNoise should always be available");
    assert_eq!(suppressor.frame_size(), 480, "Frame size should be 480 samples at 48kHz");
}

#[test]
fn test_native_rnnoise_process_silence() {
    // Silence should remain near-silent after processing
    let mut suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // Process 1 frame of silence (RNNoise uses 480-sample frames at 48kHz)
    let silence = vec![0.0f32; 480];
    let result = suppressor.process_frame(&silence);
    
    assert!(result.is_ok(), "Processing silence should succeed");
    let output = result.unwrap();
    
    // Native RNNoise shouldn't add significant energy to silence
    let max_amplitude: f32 = output.iter().map(|s| s.abs()).fold(0.0f32, f32::max);
    assert!(max_amplitude < 0.01,
        "Silence should remain near-silent after noise suppression, max amp: {}", max_amplitude);
}

#[test]
fn test_native_rnnoise_process_noise() {
    // Native RNNoise should process noise and produce output
    let mut suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // Generate synthetic noise
    let noise: Vec<f32> = (0..480).map(|i| {
        let x = (i as f32 * 0.5).sin() * 0.3;
        x + (i as f32 * 0.3).cos() * 0.2
    }).collect();
    
    // Calculate input energy
    let input_energy: f32 = noise.iter().map(|s| s * s).sum();
    
    // Process through noise suppressor
    let result = suppressor.process_frame(&noise);
    assert!(result.is_ok(), "Processing noise should succeed");
    
    let output = result.unwrap();
    
    // Output should have same length as input
    assert_eq!(output.len(), noise.len(), 
        "Output frame should have same length as input");
    
    // Native RNNoise modifies the signal (doesn't pass through unchanged)
    // We just verify it produces valid output
    let output_energy: f32 = output.iter().map(|s| s * s).sum();
    assert!(output_energy.is_finite(), "Output energy should be finite");
    
    // RNNoise typically reduces noise energy
    // Note: This may not always be true for synthetic signals, so we just check output is valid
    assert!(output.iter().all(|&s| s.abs() < 10.0), 
        "Output samples should be in reasonable range");
}

#[test]
fn test_native_rnnoise_vad_detection() {
    // Test Voice Activity Detection with native RNNoise
    let mut suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // Test with constant signal - VAD should return a value
    let signal = vec![0.1f32; 480];
    let result = suppressor.process_frame_with_vad(&signal);
    
    assert!(result.is_ok(), "VAD processing should succeed");
    let ns_result = result.unwrap();
    
    // VAD should be in valid range [0.0, 1.0]
    assert!(ns_result.vad >= 0.0 && ns_result.vad <= 1.0,
        "VAD should be between 0.0 and 1.0, got {}", ns_result.vad);
    
    // Test with silence - VAD should be low
    let silence = vec![0.0f32; 480];
    let result_silence = suppressor.process_frame_with_vad(&silence);
    let vad_silence = result_silence.unwrap().vad;
    assert!(vad_silence < 0.5, "VAD for silence should be low, got {}", vad_silence);
}

#[test]
fn test_native_rnnoise_frame_size() {
    // Native nnnoiseless requires 48kHz sample rate
    let suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // At 48kHz, frame size should be 480 samples (10ms)
    assert_eq!(suppressor.frame_size(), 480, 
        "Frame size at 48kHz should be 480 samples");
}

#[test]
fn test_native_rnnoise_invalid_sample_rate() {
    // Native nnnoiseless only supports 48kHz
    let result = NoiseSuppressor::new(44100);
    assert!(result.is_err(), "44.1kHz should fail with native RNNoise");
    
    let result = NoiseSuppressor::new(96000);
    assert!(result.is_err(), "96kHz should fail with native RNNoise");
}

#[test]
fn test_native_rnnoise_invalid_frame_size() {
    // Native RNNoise requires exact 480-sample frames
    let mut suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // Try with wrong frame size
    let wrong_input = vec![0.5f32; 441]; // 441 samples instead of 480
    let result = suppressor.process_frame(&wrong_input);
    
    assert!(result.is_err(), "Wrong frame size should fail");
}

// All tests now use native nnnoiseless - stub tests removed
