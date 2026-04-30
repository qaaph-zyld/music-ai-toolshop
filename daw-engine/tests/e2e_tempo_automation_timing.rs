//! E2E Tempo Automation Timing Integration Test
//!
//! Tests tempo changes affect playback timing correctly.
//! Session B: E2E Integration Testing

use daw_engine::{TempoAutomationTrack, InterpolationType, Transport};

/// Test: Static tempo, verify beat-to-seconds conversion
#[test]
fn e2e_tempo_static_beat_to_seconds() {
    // Create tempo track with static 120 BPM
    let tempo_track = TempoAutomationTrack::new(120.0);
    
    // Verify initial tempo
    assert_eq!(tempo_track.get_tempo_at_beat(0.0), 120.0);
    assert_eq!(tempo_track.get_tempo_at_beat(4.0), 120.0); // Still 120 at bar 2
    assert_eq!(tempo_track.get_tempo_at_beat(100.0), 120.0); // Still 120 way out
    
    // Verify beat-to-seconds conversion
    // At 120 BPM: 1 beat = 0.5 seconds
    // 4 beats = 2.0 seconds
    let seconds_4_beats = tempo_track.beats_to_seconds(0.0, 4.0);
    assert!(
        (seconds_4_beats - 2.0).abs() < 0.01,
        "Expected ~2.0s for 4 beats at 120 BPM, got {}s",
        seconds_4_beats
    );
    
    // 8 beats = 4.0 seconds
    let seconds_8_beats = tempo_track.beats_to_seconds(0.0, 8.0);
    assert!(
        (seconds_8_beats - 4.0).abs() < 0.01,
        "Expected ~4.0s for 8 beats at 120 BPM, got {}s",
        seconds_8_beats
    );
    
    // Test different tempo
    let tempo_track_60 = TempoAutomationTrack::new(60.0);
    // At 60 BPM: 1 beat = 1.0 second
    let seconds_4_beats_60 = tempo_track_60.beats_to_seconds(0.0, 4.0);
    assert!(
        (seconds_4_beats_60 - 4.0).abs() < 0.01,
        "Expected ~4.0s for 4 beats at 60 BPM, got {}s",
        seconds_4_beats_60
    );
}

/// Test: Tempo curve, verify timing calculations adjust
#[test]
fn e2e_tempo_curve_timing_adjustment() {
    // Create tempo track with linear ramp from 120 to 160 BPM over 4 beats
    let mut tempo_track = TempoAutomationTrack::new(120.0);
    tempo_track.add_linear(4.0, 160.0);
    
    // Verify tempo interpolation
    assert_eq!(tempo_track.get_tempo_at_beat(0.0), 120.0);
    assert_eq!(tempo_track.get_tempo_at_beat(4.0), 160.0);
    
    // At beat 2 (midpoint), should be ~140 BPM (linear interpolation)
    let tempo_at_2 = tempo_track.get_tempo_at_beat(2.0);
    assert!(
        (tempo_at_2 - 140.0).abs() < 0.1,
        "Expected ~140 BPM at beat 2, got {}",
        tempo_at_2
    );
    
    // Verify time calculation accounts for tempo change
    // With linear ramp 120->160 over 4 beats, average tempo is ~140 BPM
    // So 4 beats should take less time than at constant 120 BPM
    let seconds_with_ramp = tempo_track.beats_to_seconds(0.0, 4.0);
    
    // At constant 120 BPM: 4 beats = 2.0 seconds
    // With ramp to 160 BPM: should be less than 2.0 seconds
    assert!(
        seconds_with_ramp < 2.0,
        "Tempo ramp should result in faster playback, expected < 2.0s, got {}s",
        seconds_with_ramp
    );
    
    // But more than at constant 160 BPM (which would be 1.5 seconds)
    assert!(
        seconds_with_ramp > 1.5,
        "Starting at 120 BPM should keep time > 1.5s, got {}s",
        seconds_with_ramp
    );
}

/// Test: Abrupt tempo change, verify playback sync
#[test]
fn e2e_tempo_abrupt_change_playback_sync() {
    // Create tempo track with step change (abrupt)
    let mut tempo_track = TempoAutomationTrack::new(120.0);
    tempo_track.add_breakpoint(4.0, 180.0, InterpolationType::Step);
    
    // Before step: 120 BPM
    assert_eq!(tempo_track.get_tempo_at_beat(0.0), 120.0);
    assert_eq!(tempo_track.get_tempo_at_beat(3.99), 120.0);
    
    // At and after step: 180 BPM
    assert_eq!(tempo_track.get_tempo_at_beat(4.0), 180.0);
    assert_eq!(tempo_track.get_tempo_at_beat(8.0), 180.0);
    
    // Calculate time for first 4 beats (at 120 BPM)
    let seconds_first_4 = tempo_track.beats_to_seconds(0.0, 4.0);
    assert!(
        (seconds_first_4 - 2.0).abs() < 0.01,
        "First 4 beats at 120 BPM should be ~2.0s, got {}s",
        seconds_first_4
    );
    
    // Calculate time for next 4 beats (at 180 BPM)
    let seconds_next_4 = tempo_track.beats_to_seconds(4.0, 8.0);
    // At 180 BPM: 4 beats = 4 * (60/180) = 4 * 0.333 = 1.333 seconds
    assert!(
        (seconds_next_4 - 1.333).abs() < 0.05,
        "Next 4 beats at 180 BPM should be ~1.33s, got {}s",
        seconds_next_4
    );
    
    // Total time for 8 beats should be ~3.33 seconds
    let seconds_total = tempo_track.beats_to_seconds(0.0, 8.0);
    assert!(
        (seconds_total - 3.333).abs() < 0.05,
        "Total 8 beats should be ~3.33s, got {}s",
        seconds_total
    );
}

/// Test: Transport position sync with tempo automation
#[test]
fn e2e_transport_tempo_position_sync() {
    // Create transport at 120 BPM
    let mut transport = Transport::new(120.0, 48000);
    
    // Create tempo track that will be used for position calculations
    let tempo_track = TempoAutomationTrack::new(120.0);
    
    // Start playback
    transport.play();
    
    // Process 2 bars worth of samples
    // At 120 BPM with 48kHz: 1 beat = 24000 samples
    let samples_per_beat = (60.0 / 120.0 * 48000.0) as u32;
    transport.process(samples_per_beat * 8); // 8 beats = 2 bars
    
    // Position should be at 8 beats
    let pos = transport.position_beats();
    assert!((pos - 8.0).abs() < 0.01, "Expected position ~8.0, got {}", pos);
    
    // Verify tempo track time calculation matches
    let seconds_elapsed = tempo_track.beats_to_seconds(0.0, 8.0);
    assert!((seconds_elapsed - 4.0).abs() < 0.01, "Expected ~4.0s elapsed, got {}s", seconds_elapsed);
}

/// Test: Multiple tempo changes throughout project
#[test]
fn e2e_tempo_multiple_changes() {
    // Create tempo track with multiple breakpoints
    let mut tempo_track = TempoAutomationTrack::new(100.0);
    
    // Add several tempo changes
    tempo_track.add_linear(4.0, 120.0);   // Ramp to 120 at bar 2
    tempo_track.add_linear(8.0, 140.0);   // Ramp to 140 at bar 3
    tempo_track.add_linear(12.0, 120.0);    // Ramp back to 120 at bar 4
    
    assert_eq!(tempo_track.breakpoint_count(), 4);
    
    // Verify tempo at various points
    assert_eq!(tempo_track.get_tempo_at_beat(0.0), 100.0);
    assert_eq!(tempo_track.get_tempo_at_beat(4.0), 120.0);
    assert_eq!(tempo_track.get_tempo_at_beat(8.0), 140.0);
    assert_eq!(tempo_track.get_tempo_at_beat(12.0), 120.0);
    
    // Verify interpolated values
    let tempo_at_2 = tempo_track.get_tempo_at_beat(2.0); // Between 100 and 120
    assert!((tempo_at_2 - 110.0).abs() < 0.1, "Expected ~110 BPM at beat 2, got {}", tempo_at_2);
    
    // Calculate total time for 16 beats with varying tempo
    let seconds_total = tempo_track.beats_to_seconds(0.0, 16.0);
    
    // With tempo ranging 100-140, average is around 120 BPM
    // So time should be around 16 beats / 120 BPM * 60 = 8 seconds
    assert!(
        seconds_total > 6.0 && seconds_total < 10.0,
        "16 beats with varying tempo should take ~6-10 seconds, got {}s",
        seconds_total
    );
}

/// Test: Tempo automation average calculation
#[test]
fn e2e_tempo_average_calculation() {
    // Create tempo track with linear ramp
    let mut tempo_track = TempoAutomationTrack::new(80.0);
    tempo_track.add_linear(8.0, 160.0); // Ramp from 80 to 160 over 8 beats
    
    // Average tempo over the range should be around 120
    let avg = tempo_track.get_average_tempo(0.0, 8.0);
    assert!(
        (avg - 120.0).abs() < 5.0,
        "Expected average ~120 BPM, got {}",
        avg
    );
    
    // Calculate time using average
    // 8 beats at ~120 BPM average = ~4 seconds
    let seconds = tempo_track.beats_to_seconds(0.0, 8.0);
    assert!(
        (seconds - 4.0).abs() < 0.5,
        "Expected ~4.0s for 8 beats with average 120 BPM, got {}s",
        seconds
    );
}
