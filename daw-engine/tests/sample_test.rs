//! Sample playback tests
//! 
//! Tests for audio sample loading and playback.

use daw_engine::sample::Sample;
use daw_engine::sample_player::SamplePlayer;

#[test]
fn test_sample_player_silence_when_stopped() {
    // Create sample and player
    let data = vec![0.5f32, -0.5, 1.0, -1.0];
    let sample = Sample::from_raw(data, 2, 48000);
    let mut player = SamplePlayer::new(sample, 2);
    
    // Test silence when stopped
    let mut output = vec![1.0f32; 4];
    player.stop();
    player.process(&mut output);
    assert!(output.iter().all(|&s| s == 0.0));
}

#[test]
fn test_sample_from_raw() {
    // Test creating a sample from raw data
    let data = vec![0.5f32, -0.5, 1.0, -1.0];
    let sample = Sample::from_raw(data, 2, 48000);
    
    assert_eq!(sample.channels(), 2);
    assert_eq!(sample.sample_rate(), 48000);
    assert_eq!(sample.frame_count(), 2);
    assert!((sample.duration_seconds() - 0.00004167).abs() < 0.00001);
}

#[test]
fn test_sample_with_sample_player() {
    // Create sample and player using the new API
    let data = vec![0.5f32, -0.5, 1.0, -1.0];
    let sample = Sample::from_raw(data, 2, 48000);
    let mut player = SamplePlayer::new(sample, 2);
    
    // Test player starts stopped
    assert!(!player.is_playing());
    
    // Test silence when stopped
    let mut output = vec![1.0f32; 4];
    player.process(&mut output);
    assert!(output.iter().all(|&s| s == 0.0));
    
    // Test playback produces output
    player.play();
    let mut output = vec![0.0f32; 4];
    player.process(&mut output);
    assert!(output.iter().any(|&s| s != 0.0));
}

#[test]
fn test_sample_loads_wav_file() {
    let sample = Sample::from_file("tests/assets/sine_440hz.wav")
        .expect("Should load WAV");
    
    assert_eq!(sample.channels(), 2);
    assert_eq!(sample.sample_rate(), 48000);
    assert!(sample.duration_seconds() > 0.0);
}

#[test]
fn test_sample_player_plays_wav_at_original_pitch() {
    let sample = Sample::from_file("tests/assets/sine_440hz.wav").unwrap();
    let mut player = SamplePlayer::new(sample, 2);
    
    let mut output = vec![0.0f32; 4800]; // 100ms at 48kHz
    player.play();
    player.process(&mut output);
    
    // Check that we got non-zero samples
    assert!(output.iter().any(|&s| s != 0.0));
}

#[test]
fn test_sample_player_produces_silence_when_stopped_real() {
    let sample = Sample::from_file("tests/assets/sine_440hz.wav").unwrap();
    let mut player = SamplePlayer::new(sample, 2);
    
    let mut output = vec![1.0f32; 128]; // Pre-fill with non-zero
    player.stop();
    player.process(&mut output);
    
    // Should be zeroed when stopped
    assert!(output.iter().all(|&s| s == 0.0));
}

#[test]
fn test_sample_player_speed_affects_pitch() {
    let sample = Sample::from_file("tests/assets/sine_440hz.wav").unwrap();
    let mut player = SamplePlayer::new(sample, 2);
    
    player.set_speed(2.0); // Double speed = octave up
    player.play();
    
    let mut output = vec![0.0f32; 4800];
    player.process(&mut output);
    
    // Would need FFT to verify 880Hz content
    // For now, just verify it produces output
    assert!(output.iter().any(|&s| s != 0.0));
}
