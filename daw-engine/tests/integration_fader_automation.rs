//! E2E Integration Test: Fader Automation
//!
//! Tests the complete fader automation workflow from lane creation
//! to mixer integration and audio processing with automation curves.

use daw_engine::automation::{CurveType, AutomationMode};
use daw_engine::mixer::{Mixer, ChannelStrip};

/// Test basic fader automation lane creation and value retrieval
#[test]
fn test_fader_automation_lane_basic() {
    let mut strip = ChannelStrip::new(0);
    
    // Set up automation: fade from 0.0 to 1.0 over 4 beats
    strip.fader_automation.lane_mut().add_point_at(0.0, 0.0, CurveType::Linear);
    strip.fader_automation.lane_mut().add_point_at(4.0, 1.0, CurveType::Linear);
    
    // Set to Read mode so automation is applied
    strip.set_fader_mode(AutomationMode::Read);
    
    // Test interpolation at midpoint (beat 2 = value 0.5)
    let value = strip.fader_automation.lane().value_at(2.0);
    assert!((value - 0.5).abs() < 0.001, "Expected 0.5 at beat 2, got {}", value);
    
    // Test at start
    let value = strip.fader_automation.lane().value_at(0.0);
    assert!((value - 0.0).abs() < 0.001, "Expected 0.0 at beat 0, got {}", value);
    
    // Test at end
    let value = strip.fader_automation.lane().value_at(4.0);
    assert!((value - 1.0).abs() < 0.001, "Expected 1.0 at beat 4, got {}", value);
}

/// Test mixer automation processing
#[test]
fn test_mixer_automation_processing() {
    // Create mixer with one channel
    let mut mixer = Mixer::new(1);
    mixer.enable_loudness_meter(48000);
    
    // Set up fader automation on channel 0
    if let Some(strip) = mixer.channel_strip_mut(0) {
        strip.fader_automation.lane_mut().add_point_at(0.0, 0.0, CurveType::Linear);
        strip.fader_automation.lane_mut().add_point_at(4.0, 1.0, CurveType::Linear);
        strip.set_fader_mode(AutomationMode::Read);
    }
    
    // Process automation at sample 0 (beat 0)
    mixer.process_automation(0, 120.0);
    
    // Fader should be at 0.0
    if let Some(strip) = mixer.channel_strip(0) {
        assert!((strip.fader_level - 0.0).abs() < 0.001, 
            "Fader should be at 0.0 at beat 0, got {}", strip.fader_level);
    }
    
    // Process automation at 2 beats (1 second at 120 BPM = 48000 samples)
    mixer.process_automation(48000, 120.0);
    
    // Fader should be at 0.5
    if let Some(strip) = mixer.channel_strip(0) {
        assert!((strip.fader_level - 0.5).abs() < 0.01,
            "Fader should be near 0.5 at beat 2, got {}", strip.fader_level);
    }
    
    // Process automation at 4 beats (2 seconds = 96000 samples)
    mixer.process_automation(96000, 120.0);
    
    // Fader should be at 1.0
    if let Some(strip) = mixer.channel_strip(0) {
        assert!((strip.fader_level - 1.0).abs() < 0.001,
            "Fader should be at 1.0 at beat 4, got {}", strip.fader_level);
    }
}

/// Test Write mode automation recording
#[test]
fn test_fader_write_mode_recording() {
    let mut mixer = Mixer::new(1);
    
    // Get mutable access to strip
    {
        let strip = mixer.channel_strip_mut(0).unwrap();
        strip.set_fader_mode(AutomationMode::Write);
        
        // Pre-existing automation
        strip.fader_automation.lane_mut().add_point_at(0.0, 0.5, CurveType::Linear);
        strip.fader_automation.lane_mut().add_point_at(10.0, 0.5, CurveType::Linear);
        
        // Start recording at beat 2
        strip.touch_fader(2.0);
        
        // Update values
        strip.update_fader(3.0, 0.7);
        strip.update_fader(4.0, 0.9);
        
        // End recording
        strip.release_fader(5.0);
    }
    
    // Verify automation was recorded
    let strip = mixer.channel_strip(0).unwrap();
    assert!(strip.fader_automation.lane().point_count() >= 3,
        "Write mode should record points");
    
    // Verify values at recorded positions
    let value_at_3 = strip.fader_automation.lane().value_at(3.0);
    assert!(value_at_3 >= 0.6, "Should have recorded value ~0.7 at beat 3, got {}", value_at_3);
}

/// Test Touch mode recording with return
#[test]
fn test_fader_touch_mode_with_return() {
    let mut mixer = Mixer::new(1);
    
    {
        let strip = mixer.channel_strip_mut(0).unwrap();
        strip.set_fader_mode(AutomationMode::Touch);
        
        // Set up pre-existing automation (baseline)
        strip.fader_automation.lane_mut().add_point_at(0.0, 0.2, CurveType::Linear);
        strip.fader_automation.lane_mut().add_point_at(10.0, 0.8, CurveType::Linear);
        
        // Touch and record at beat 2
        strip.touch_fader(2.0);  // Touch starts, baseline value ~0.36
        strip.update_fader(3.0, 0.9);  // Override with higher value
        strip.release_fader(4.0);  // Release, should add return point
    }
    
    // Verify points were recorded
    let strip = mixer.channel_strip(0).unwrap();
    let point_count = strip.fader_automation.lane().point_count();
    assert!(point_count > 2, "Touch mode should add recorded points plus return, got {}", point_count);
}

/// Test Latch mode recording (stays at last value)
#[test]
fn test_fader_latch_mode() {
    let mut mixer = Mixer::new(1);
    
    {
        let strip = mixer.channel_strip_mut(0).unwrap();
        strip.set_fader_mode(AutomationMode::Latch);
        
        // Record
        strip.touch_fader(0.0);
        strip.update_fader(1.0, 0.6);
        strip.update_fader(2.0, 0.8);
        strip.release_fader(3.0);
    }
    
    // Verify points recorded
    let strip = mixer.channel_strip(0).unwrap();
    assert!(strip.fader_automation.lane().point_count() >= 3,
        "Latch mode should record points");
    
    // Value should stay latched at last value
    let value = strip.fader_automation.lane().value_at(5.0);
    assert!((value - 0.8).abs() < 0.1, "Latch mode should stay at ~0.8, got {}", value);
}

/// Test S-curve interpolation
#[test]
fn test_scurve_interpolation() {
    let mut strip = ChannelStrip::new(0);
    
    // Set up S-curve automation
    strip.fader_automation.lane_mut().add_point_at(0.0, 0.0, CurveType::SCurve);
    strip.fader_automation.lane_mut().add_point_at(4.0, 1.0, CurveType::SCurve);
    strip.set_fader_mode(AutomationMode::Read);
    
    // At quarter point, S-curve should be smoother (less) than linear
    let linear_value = 0.25; // Linear would give 0.25 at beat 1
    let scurve_value = strip.fader_automation.lane().value_at(1.0);
    
    // S-curve: t=0.25, smooth_t = 0.25 * 0.25 * (3 - 0.5) = 0.15625
    assert!(scurve_value < linear_value,
        "S-curve at quarter should be less than linear ({} < {})", scurve_value, linear_value);
    
    // At midpoint, should still be 0.5
    let mid_value = strip.fader_automation.lane().value_at(2.0);
    assert!((mid_value - 0.5).abs() < 0.001, "Midpoint should be 0.5, got {}", mid_value);
}

/// Test multiple tracks with independent automation
#[test]
fn test_multiple_tracks_automation() {
    let mut mixer = Mixer::new(4);
    
    // Set up different automation on each track
    for i in 0..4 {
        if let Some(strip) = mixer.channel_strip_mut(i) {
            strip.set_fader_mode(AutomationMode::Read);
            
            // Each track has different curve
            let value = i as f32 * 0.25;
            strip.fader_automation.lane_mut().add_point_at(0.0, value, CurveType::Linear);
            strip.fader_automation.lane_mut().add_point_at(4.0, value + 0.25, CurveType::Linear);
        }
    }
    
    // Process automation
    mixer.process_automation(0, 120.0);
    
    // Verify each track has different value
    for i in 0..4 {
        let strip = mixer.channel_strip(i).unwrap();
        let expected = i as f32 * 0.25;
        assert!((strip.fader_level - expected).abs() < 0.001,
            "Track {} should have fader at {}, got {}", i, expected, strip.fader_level);
    }
}

/// Test automation with different BPM values
#[test]
fn test_automation_different_bpm() {
    use daw_engine::automation::sample_to_beat;
    
    // 48000 samples at different BPMs
    let beat_60 = sample_to_beat(48000, 48000, 60.0);
    let beat_120 = sample_to_beat(48000, 48000, 120.0);
    let beat_240 = sample_to_beat(48000, 48000, 240.0);
    
    // Same samples, different BPM = different beat positions
    // 60 BPM: 1 beat/second, 120 BPM: 2 beats/second, 240 BPM: 4 beats/second
    assert!((beat_60 - 1.0).abs() < 0.001, "60 BPM: 1s = 1 beat, got {}", beat_60);
    assert!((beat_120 - 2.0).abs() < 0.001, "120 BPM: 1s = 2 beats, got {}", beat_120);
    assert!((beat_240 - 4.0).abs() < 0.001, "240 BPM: 1s = 4 beats, got {}", beat_240);
}

/// Test fader value clamping via recorder
#[test]
fn test_fader_value_clamping() {
    use daw_engine::automation::{AutomationRecorder, AutomationLane};
    
    // Recorder clamps values during recording
    let mut recorder = AutomationRecorder::new("track_0_fader", 0.5, AutomationMode::Write);
    
    // Set range on the underlying lane
    recorder.lane_mut().min_value = 0.0;
    recorder.lane_mut().max_value = 1.0;
    
    // Record values outside range - they should be clamped
    recorder.start_touch(0.0, 0.5, 0.5);
    recorder.update_value(0.0, -0.5);  // Below min
    recorder.update_value(0.1, 1.5);   // Above max
    recorder.end_touch(0.2);
    
    // Values should be clamped to 0.0-1.0 when read back
    let value_low = recorder.lane().value_at(0.0);
    let value_high = recorder.lane().value_at(0.1);
    
    assert!(value_low >= 0.0 && value_low <= 1.0,
        "Value should be clamped to valid range, got {}", value_low);
    assert!(value_high >= 0.0 && value_high <= 1.0,
        "Value should be clamped to valid range, got {}", value_high);
}

/// Test Off and Read modes don't record
#[test]
fn test_read_off_modes_no_record() {
    let mut strip = ChannelStrip::new(0);
    
    // Test Off mode
    strip.set_fader_mode(AutomationMode::Off);
    strip.touch_fader(0.0);
    strip.update_fader(1.0, 0.8);
    strip.release_fader(2.0);
    assert!(strip.fader_automation.lane().is_empty(), "Off mode should not record");
    
    // Test Read mode
    strip.set_fader_mode(AutomationMode::Read);
    strip.touch_fader(0.0);
    strip.update_fader(1.0, 0.9);
    strip.release_fader(2.0);
    assert!(strip.fader_automation.lane().is_empty(), "Read mode should not record");
}
