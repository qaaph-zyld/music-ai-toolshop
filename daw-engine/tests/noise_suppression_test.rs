//! RNNoise AI noise suppression tests
//!
//! TDD: RED phase - Write failing tests before implementation

use daw_engine::noise_suppression::{NoiseSuppressor, NoiseSuppressionResult};

#[test]
fn test_noise_suppressor_creation() {
    // RED: This test should fail until we implement NoiseSuppressor
    let suppressor = NoiseSuppressor::new(48000);
    assert!(suppressor.is_ok(), "NoiseSuppressor should be creatable");
}

#[test]
fn test_noise_suppressor_process_silence() {
    // RED: Silence should remain silent after processing
    let mut suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // Process 1 frame of silence (RNNoise uses 480-sample frames at 48kHz)
    let silence = vec![0.0f32; 480];
    let result = suppressor.process_frame(&silence);
    
    assert!(result.is_ok(), "Processing silence should succeed");
    let output = result.unwrap();
    
    // Output should still be silence (or very close)
    assert!(output.iter().all(|&s| s.abs() < 0.001),
        "Silence should remain silent after noise suppression");
}

#[test]
fn test_noise_suppressor_process_noise() {
    // RED: Test that noise gets reduced
    let mut suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // Generate synthetic noise (white noise)
    let noise: Vec<f32> = (0..480).map(|i| {
        // Simple pseudo-random noise
        let x = (i as f32 * 0.5).sin() * 0.3;
        x + (i as f32 * 0.3).cos() * 0.2
    }).collect();
    
    // Calculate input energy
    let input_energy: f32 = noise.iter().map(|&s| s * s).sum();
    
    // Process through RNNoise
    let result = suppressor.process_frame(&noise);
    assert!(result.is_ok(), "Processing noise should succeed");
    
    let output = result.unwrap();
    let output_energy: f32 = output.iter().map(|&s| s * s).sum();
    
    // Output energy should be different from input (RNNoise modifies signal)
    // Note: We can't guarantee reduction for pure noise, but signal should change
    assert_ne!(input_energy, output_energy, 
        "RNNoise should modify the signal");
}

#[test]
fn test_noise_suppression_result_vad() {
    // RED: Test that VAD (Voice Activity Detection) is returned
    let mut suppressor = NoiseSuppressor::new(48000).unwrap();
    
    let noise = vec![0.1f32; 480]; // Constant low-level signal
    let result = suppressor.process_frame_with_vad(&noise);
    
    assert!(result.is_ok());
    let ns_result = result.unwrap();
    
    // VAD should be present (0.0 to 1.0)
    assert!(ns_result.vad >= 0.0 && ns_result.vad <= 1.0,
        "VAD should be between 0.0 and 1.0, got {}", ns_result.vad);
}

#[test]
fn test_noise_suppressor_frame_size() {
    // RED: RNNoise requires specific frame sizes
    let suppressor = NoiseSuppressor::new(48000).unwrap();
    
    // At 48kHz, frame size should be 480 samples (10ms)
    assert_eq!(suppressor.frame_size(), 480, 
        "Frame size at 48kHz should be 480 samples");
    
    // At 44.1kHz, frame size should be different (usually 480 or adjusted)
    let suppressor_44k = NoiseSuppressor::new(44100).unwrap();
    assert!(suppressor_44k.frame_size() > 0,
        "Frame size should be positive");
}
