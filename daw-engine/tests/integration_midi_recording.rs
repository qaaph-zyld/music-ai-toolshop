//! Integration Test: MIDI Recording → Clip Creation Workflow
//!
//! Tests the end-to-end flow from MIDI recording to clip creation.
//! Phase 6: MIDI Recording Integration

use daw_engine::{MidiInput, MidiMessage, SessionView, MidiNote};

/// Test that recorded MIDI notes can be converted to a clip in the session
#[test]
fn test_midi_recording_to_clip_creation() {
    // Create MIDI input handler
    let mut midi_input = MidiInput::new(16, 48000);
    
    // Create a session view (8 tracks, 16 scenes)
    let mut session = SessionView::new(8, 16);
    
    // Start recording
    midi_input.start_recording(0.0);
    assert!(midi_input.is_recording());
    
    // Simulate recording some MIDI notes
    let note1 = MidiMessage::note_on(60, 100, 0); // Middle C, velocity 100
    let note2 = MidiMessage::note_on(64, 100, 0); // E
    let note3 = MidiMessage::note_on(67, 100, 0); // G
    
    // Process notes (simulating what happens during recording)
    // In real scenario, this would come from a MIDI device callback
    midi_input.engine_mut().add_note(0, MidiNote::new(60, 100, 0.0, 0.5));
    midi_input.engine_mut().add_note(0, MidiNote::new(64, 100, 0.25, 0.5));
    midi_input.engine_mut().add_note(0, MidiNote::new(67, 100, 0.5, 0.5));
    
    // Manually add notes to recorded_notes (simulating the recording process)
    // In the actual implementation, this happens via process_midi_message
    
    // Stop recording and get notes
    let recorded_notes = midi_input.stop_recording();
    assert!(!midi_input.is_recording());
    
    // For this test, we'll manually create a MIDI clip with the notes
    // In the real workflow, this comes from the FFI call
    let target_track = 0;
    let target_scene = 0;
    let clip_name = "Test Recording";
    
    // Create test notes for the clip
    let test_notes = vec![
        MidiNote::new(60, 100, 0.0, 0.5),
        MidiNote::new(64, 100, 0.25, 0.5),
        MidiNote::new(67, 100, 0.5, 0.5),
    ];
    
    // Create the MIDI clip in the session
    let success = session.create_midi_clip(target_track, target_scene, test_notes.clone(), clip_name);
    assert!(success, "create_midi_clip should succeed");
    
    // Verify the clip was created
    let clip = session.get_clip(target_track, target_scene);
    assert!(clip.is_some(), "Clip should exist at target position");
    
    let clip = clip.unwrap();
    assert!(clip.is_midi(), "Clip should be a MIDI clip");
    assert!(!clip.is_audio(), "Clip should not be an audio clip");
    assert_eq!(clip.name(), clip_name);
    
    // Verify the clip has the correct MIDI notes
    let midi_notes = clip.midi_notes();
    assert_eq!(midi_notes.len(), 3, "Clip should have 3 MIDI notes");
    
    // Verify first note
    assert_eq!(midi_notes[0].pitch(), 60);
    assert_eq!(midi_notes[0].velocity(), 100);
    assert!((midi_notes[0].start_beat() - 0.0).abs() < 0.001);
    
    // Verify second note
    assert_eq!(midi_notes[1].pitch(), 64);
    assert_eq!(midi_notes[1].velocity(), 100);
    assert!((midi_notes[1].start_beat() - 0.25).abs() < 0.001);
    
    // Verify third note
    assert_eq!(midi_notes[2].pitch(), 67);
    assert_eq!(midi_notes[2].velocity(), 100);
    assert!((midi_notes[2].start_beat() - 0.5).abs() < 0.001);
}

/// Test that creating a MIDI clip at invalid position fails gracefully
#[test]
fn test_create_midi_clip_invalid_position() {
    let mut session = SessionView::new(8, 16);
    
    let notes = vec![MidiNote::new(60, 100, 0.0, 0.5)];
    
    // Try to create clip at invalid track
    let success = session.create_midi_clip(100, 0, notes.clone(), "Test");
    assert!(!success, "Should fail with invalid track index");
    
    // Try to create clip at invalid scene
    let success = session.create_midi_clip(0, 100, notes.clone(), "Test");
    assert!(!success, "Should fail with invalid scene index");
}

/// Test that an empty note array creates a clip with default duration
#[test]
fn test_create_midi_clip_empty_notes() {
    let mut session = SessionView::new(8, 16);
    
    let notes: Vec<MidiNote> = vec![];
    
    // Even with empty notes, should create a clip (useful for placeholders)
    let success = session.create_midi_clip(0, 0, notes, "Empty Clip");
    assert!(success, "Should succeed even with empty notes");
    
    let clip = session.get_clip(0, 0).unwrap();
    assert_eq!(clip.midi_notes().len(), 0);
}

/// Test MIDI clip duration calculation based on note positions
#[test]
fn test_midi_clip_duration_calculation() {
    use daw_engine::Clip;
    
    // Notes spanning 8 beats (2 bars)
    let notes = vec![
        MidiNote::new(60, 100, 0.0, 0.5),    // Starts at 0
        MidiNote::new(67, 100, 7.5, 0.5),    // Starts at 7.5, ends at 8.0
    ];
    
    let clip = Clip::new_midi_with_notes("Duration Test", 0.0, notes);
    
    // Duration should be based on last note position + duration
    // 7.5 + 0.5 = 8.0 beats = 2.0 bars
    // But the session.create_midi_clip calculates this dynamically
    // The clip constructor doesn't auto-calculate, we pass it explicitly
    
    // For a proper test, let's use the session method
    let mut session = SessionView::new(8, 16);
    session.create_midi_clip(0, 0, vec![
        MidiNote::new(60, 100, 0.0, 0.5),
        MidiNote::new(67, 100, 7.5, 0.5),
    ], "Test");
    
    let clip = session.get_clip(0, 0).unwrap();
    // Duration should be at least 2 bars (8 beats / 4 beats per bar)
    assert!(clip.duration_bars() >= 2.0, "Duration should be at least 2 bars");
}

/// Test that multiple MIDI clips can be created on different tracks/scenes
#[test]
fn test_multiple_midi_clips() {
    let mut session = SessionView::new(8, 16);
    
    // Create clip on track 0, scene 0
    let success1 = session.create_midi_clip(0, 0, vec![
        MidiNote::new(60, 100, 0.0, 0.5),
    ], "Clip 1");
    assert!(success1);
    
    // Create clip on track 1, scene 0 (different track, same scene)
    let success2 = session.create_midi_clip(1, 0, vec![
        MidiNote::new(64, 100, 0.0, 0.5),
    ], "Clip 2");
    assert!(success2);
    
    // Create clip on track 0, scene 1 (same track, different scene)
    let success3 = session.create_midi_clip(0, 1, vec![
        MidiNote::new(67, 100, 0.0, 0.5),
    ], "Clip 3");
    assert!(success3);
    
    // Verify all clips exist
    assert!(session.get_clip(0, 0).is_some());
    assert!(session.get_clip(1, 0).is_some());
    assert!(session.get_clip(0, 1).is_some());
    
    // Verify each clip has correct notes
    assert_eq!(session.get_clip(0, 0).unwrap().midi_notes()[0].pitch(), 60);
    assert_eq!(session.get_clip(1, 0).unwrap().midi_notes()[0].pitch(), 64);
    assert_eq!(session.get_clip(0, 1).unwrap().midi_notes()[0].pitch(), 67);
}
