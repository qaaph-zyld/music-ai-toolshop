//! Loudness metering tests (libebur128 integration)
//!
//! TDD: RED phase - Write failing tests before implementation

use daw_engine::loudness::{LoudnessMeter, LoudnessReading};

#[test]
fn test_loudness_meter_creation() {
    // RED: This test should fail until we implement LoudnessMeter
    let meter = LoudnessMeter::new(48000, 2);
    assert!(meter.is_ok(), "LoudnessMeter should be creatable");
}

#[test]
fn test_loudness_meter_process_silence() {
    // RED: Test that silence produces -inf LUFS (or very low value)
    let mut meter = LoudnessMeter::new(48000, 2).unwrap();
    
    // Process 1 second of silence
    let silence = vec![0.0f32; 48000 * 2]; // 48kHz * 2 channels
    meter.process(&silence);
    
    let reading = meter.reading();
    assert!(reading.integrated_lufs < -50.0, 
        "Silence should have very low loudness (< -50 LUFS), got {} LUFS", 
        reading.integrated_lufs);
}

#[test]
fn test_loudness_meter_process_sine() {
    // RED: Test that a sine wave produces measurable loudness
    let mut meter = LoudnessMeter::new(48000, 1).unwrap();
    
    // Generate 1 second of sine wave at -12 dBFS
    let sample_rate = 48000f32;
    let frequency = 1000.0f32;
    let amplitude = 0.25f32; // -12 dBFS approx
    
    let sine: Vec<f32> = (0..48000)
        .map(|i| {
            let t = i as f32 / sample_rate;
            amplitude * (2.0 * std::f32::consts::PI * frequency * t).sin()
        })
        .collect();
    
    meter.process(&sine);
    
    let reading = meter.reading();
    // Sine at -12 dBFS should produce approximately -12 LUFS (give or take)
    assert!(reading.integrated_lufs > -20.0 && reading.integrated_lufs < -5.0,
        "Sine wave at -12 dBFS should produce ~-12 LUFS, got {} LUFS",
        reading.integrated_lufs);
}

#[test]
fn test_loudness_meter_reset() {
    // RED: Test that reset clears the meter state
    let mut meter = LoudnessMeter::new(48000, 1).unwrap();
    
    // Process some audio
    let sine: Vec<f32> = (0..48000).map(|i| 0.5 * (i as f32 * 0.1).sin()).collect();
    meter.process(&sine);
    
    let reading_before = meter.reading();
    assert!(reading_before.integrated_lufs > -50.0, "Should have measurable loudness");
    
    // Reset and check
    meter.reset();
    let reading_after = meter.reading();
    assert!(reading_after.integrated_lufs < -50.0,
        "After reset, loudness should be very low, got {} LUFS",
        reading_after.integrated_lufs);
}

#[test]
fn test_loudness_reading_has_momentary_shortterm_integrated() {
    // RED: Test that all three loudness measurements are available
    let mut meter = LoudnessMeter::new(48000, 2).unwrap();
    
    // Process 5 seconds of audio (enough for all measurements)
    let audio: Vec<f32> = (0..48000 * 5).map(|i| 0.3 * (i as f32 * 0.05).sin()).collect();
    meter.process(&audio);
    
    let reading = meter.reading();
    
    // All measurements should be finite (not NaN or inf)
    assert!(reading.momentary_lufs.is_finite(), "Momentary loudness should be finite");
    assert!(reading.short_term_lufs.is_finite(), "Short-term loudness should be finite");
    assert!(reading.integrated_lufs.is_finite(), "Integrated loudness should be finite");
    
    // LRA (Loudness Range) should also be available
    assert!(reading.loudness_range_lu >= 0.0, "LRA should be non-negative");
}
