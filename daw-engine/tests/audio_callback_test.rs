//! Audio callback tests
//! 
//! Tests for the audio engine callback system.

use daw_engine::AudioCallback;

#[test]
fn test_audio_callback_produces_silence_with_no_sources() {
    let mut callback = AudioCallback::new(48000, 2);
    let mut output = vec![1.0f32; 128];
    
    callback.process(&mut output);
    
    // Should produce silence when no sources added
    assert!(output.iter().all(|&s| s == 0.0), 
        "Audio callback should produce silence with no sources");
}

#[test]
fn test_audio_callback_produces_samples_with_sine() {
    let mut callback = AudioCallback::new(48000, 2);
    callback.add_sine_wave(440.0, 0.5, 48000);
    
    let mut output = vec![0.0f32; 128];
    callback.process(&mut output);
    
    // Should produce non-zero samples (sine wave)
    assert!(output.iter().any(|&s| s != 0.0), 
        "Audio callback with sine wave should produce samples");
}

#[test]
fn test_audio_callback_produces_sine_wave() {
    let mut callback = AudioCallback::new(48000, 2);
    callback.add_sine_wave(440.0, 0.5, 48000);
    
    let mut output = vec![0.0f32; 4800]; // 100ms at 48kHz
    callback.process(&mut output);
    
    // Check that we have both positive and negative values (sine wave)
    let has_positive = output.iter().any(|&s| s > 0.1);
    let has_negative = output.iter().any(|&s| s < -0.1);
    
    assert!(has_positive, "Sine wave should have positive values");
    assert!(has_negative, "Sine wave should have negative values");
}

#[test]
fn test_audio_callback_stereo_output() {
    let mut callback = AudioCallback::new(48000, 2);
    callback.add_sine_wave(440.0, 0.5, 48000);
    
    let mut output = vec![0.0f32; 128]; // 64 stereo frames
    callback.process(&mut output);
    
    // Check that we have non-zero output on both channels
    let left_has_signal = output.chunks(2).any(|f| f[0].abs() > 0.01);
    let right_has_signal = output.chunks(2).any(|f| f[1].abs() > 0.01);
    
    assert!(left_has_signal, "Left channel should have signal");
    assert!(right_has_signal, "Right channel should have signal");
}
