//! Audio callback tests
//! 
//! Tests for the audio engine callback system.

use daw_engine::AudioCallback;

#[test]
fn test_audio_callback_produces_samples() {
    let mut callback = AudioCallback::new(48000, 2);
    let mut output = vec![0.0f32; 128];
    
    callback.process(&mut output);
    
    // Should produce non-zero samples (sine wave)
    assert!(output.iter().any(|&s| s != 0.0), 
        "Audio callback should produce samples");
}

#[test]
fn test_audio_callback_produces_sine_wave() {
    let mut callback = AudioCallback::new(48000, 2);
    let mut output = vec![0.0f32; 4800]; // 100ms at 48kHz
    
    callback.process(&mut output);
    
    // Check that we have both positive and negative values (sine wave)
    let has_positive = output.iter().any(|&s| s > 0.1);
    let has_negative = output.iter().any(|&s| s < -0.1);
    
    assert!(has_positive, "Sine wave should have positive values");
    assert!(has_negative, "Sine wave should have negative values");
}

#[test]
fn test_audio_callback_respects_channel_count() {
    let mut callback = AudioCallback::new(48000, 2);
    let mut output = vec![0.0f32; 128]; // 64 stereo frames
    
    callback.process(&mut output);
    
    // Check that both channels have the same value (mono sine wave)
    for frame in output.chunks(2) {
        assert_eq!(frame[0], frame[1], "Both channels should have same value");
    }
}
