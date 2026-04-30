//! E2E Transport Workflow Integration Test
//!
//! Tests the full transport play/record/stop workflow end-to-end.
//! Session B: E2E Integration Testing

use daw_engine::{Transport, TransportState, PlayMode, SessionView, MidiNote, LoopController};

/// Test: Play for 2 bars, stop, verify position is correct
#[test]
fn e2e_transport_play_stop_position() {
    // Create transport at 120 BPM, 48kHz
    let mut transport = Transport::new(120.0, 48000);
    
    // Initial state should be stopped
    assert_eq!(transport.state(), TransportState::Stopped);
    assert_eq!(transport.position_beats(), 0.0);
    
    // Start playback
    transport.play();
    assert_eq!(transport.state(), TransportState::Playing);
    
    // Process 2 bars worth of audio at 120 BPM
    // 1 bar = 4 beats, 2 bars = 8 beats
    // At 120 BPM, 1 beat = 0.5 seconds = 24000 samples at 48kHz
    // 8 beats = 4 seconds = 192000 samples
    let samples_per_beat = (60.0 / 120.0 * 48000.0) as u32;
    let total_samples = samples_per_beat * 8; // 8 beats = 2 bars
    
    transport.process(total_samples);
    
    // Verify position is approximately 8 beats (2 bars)
    let pos = transport.position_beats();
    assert!((pos - 8.0).abs() < 0.01, "Expected ~8.0 beats after 2 bars, got {}", pos);
    
    // Stop transport
    transport.stop();
    assert_eq!(transport.state(), TransportState::Stopped);
    
    // Position should remain at the stopped location
    let final_pos = transport.position_beats();
    assert!((final_pos - 8.0).abs() < 0.01, "Position should remain at ~8.0 after stop, got {}", final_pos);
}

/// Test: Record MIDI, verify clip is created in session
#[test]
fn e2e_transport_record_midi_clip_created() {
    // Create transport
    let mut transport = Transport::new(120.0, 48000);
    
    // Create session view (8 tracks, 16 scenes)
    let mut session = SessionView::new(8, 16);
    
    // Start recording
    transport.record();
    assert_eq!(transport.state(), TransportState::Recording);
    
    // Simulate recording MIDI notes during transport processing
    let test_notes = vec![
        MidiNote::new(60, 100, 0.0, 0.5),    // Middle C
        MidiNote::new(64, 100, 0.25, 0.5),   // E
        MidiNote::new(67, 100, 0.5, 0.5),    // G
    ];
    
    // Create MIDI clip at track 0, scene 0 with the recorded notes
    let success = session.create_midi_clip(0, 0, test_notes.clone(), "Recorded Clip");
    assert!(success, "MIDI clip should be created successfully");
    
    // Stop recording
    transport.stop();
    assert_eq!(transport.state(), TransportState::Stopped);
    
    // Verify the clip exists and has the correct notes
    let clip = session.get_clip(0, 0);
    assert!(clip.is_some(), "Clip should exist at track 0, scene 0");
    
    let clip = clip.unwrap();
    assert!(clip.is_midi(), "Clip should be a MIDI clip");
    assert_eq!(clip.name(), "Recorded Clip");
    
    let midi_notes = clip.midi_notes();
    assert_eq!(midi_notes.len(), 3, "Clip should have 3 MIDI notes");
    
    // Verify note contents
    assert_eq!(midi_notes[0].pitch(), 60);
    assert_eq!(midi_notes[0].velocity(), 100);
    assert!((midi_notes[0].start_beat() - 0.0).abs() < 0.001);
    
    assert_eq!(midi_notes[1].pitch(), 64);
    assert!((midi_notes[1].start_beat() - 0.25).abs() < 0.001);
    
    assert_eq!(midi_notes[2].pitch(), 67);
    assert!((midi_notes[2].start_beat() - 0.5).abs() < 0.001);
}

/// Test: Loop playback with auto-rewind
#[test]
fn e2e_transport_loop_playback_auto_rewind() {
    // Create transport
    let mut transport = Transport::new(120.0, 48000);
    
    // Create loop controller
    let mut loop_controller = LoopController::new();
    
    // Create a loop region: bars 1-2 (beats 0-8)
    let loop_id = loop_controller.create_region("Test Loop", 0.0, 8.0);
    loop_controller.set_looping_enabled(true);
    
    // Set transport to loop mode
    transport.set_play_mode(PlayMode::Loop);
    transport.set_loop_range(0.0, 8.0);
    
    // Start playback
    transport.play();
    assert_eq!(transport.state(), TransportState::Playing);
    
    // Process past the loop end (12 beats = 3 bars)
    let samples_per_beat = (60.0 / 120.0 * 48000.0) as u32;
    let total_samples = samples_per_beat * 12; // 12 beats
    
    transport.process(total_samples);
    
    // Verify position wrapped back (should be at beat 4, not beat 12)
    let pos = transport.position_beats();
    assert!(
        pos >= 0.0 && pos < 8.0,
        "Position should loop back to within 0-8 beats, got {}",
        pos
    );
    
    // Verify loop controller agrees
    let region = loop_controller.get_region(&loop_id).unwrap();
    assert!(region.enabled);
    assert!(region.contains_beat(4.0));
    
    // Check wrap_beat behavior
    let wrapped = region.wrap_beat(12.0);
    assert!((wrapped - 4.0).abs() < 0.01, "Beat 12 should wrap to ~4.0, got {}", wrapped);
    
    // Continue playing for more loops
    transport.process(total_samples); // Another 12 beats
    let pos2 = transport.position_beats();
    assert!(
        pos2 >= 0.0 && pos2 < 8.0,
        "Position should still loop within 0-8 beats after multiple loops, got {}",
        pos2
    );
}

/// Test: Transport record state triggers correctly at punch-in/out points
#[test]
fn e2e_transport_punch_in_out_states() {
    let mut transport = Transport::new(120.0, 48000);
    
    // Set up punch-in at beat 4, punch-out at beat 8
    transport.set_punch_in(4.0);
    transport.set_punch_out(8.0);
    
    // Start playing (not recording yet)
    transport.play();
    assert_eq!(transport.state(), TransportState::Playing);
    
    // Process first 2 beats - should still be playing
    let samples_per_beat = (60.0 / 120.0 * 48000.0) as u32;
    transport.process(samples_per_beat * 2);
    assert_eq!(transport.state(), TransportState::Playing, "Should be playing before punch-in");
    
    // Process past punch-in (beat 4) - should auto-switch to recording
    transport.process(samples_per_beat * 3); // 3 more beats = beat 5
    assert_eq!(transport.state(), TransportState::Recording, "Should be recording after punch-in");
    
    // Continue processing - should stay recording until punch-out
    transport.process(samples_per_beat * 2); // 2 more beats = beat 7
    assert_eq!(transport.state(), TransportState::Recording, "Should still be recording before punch-out");
    
    // Process past punch-out (beat 8) - should switch back to playing
    transport.process(samples_per_beat * 2); // 2 more beats = beat 9
    assert_eq!(transport.state(), TransportState::Playing, "Should switch back to playing after punch-out");
}
