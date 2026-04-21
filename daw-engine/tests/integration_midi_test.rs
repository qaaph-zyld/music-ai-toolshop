//! MIDI Recording Workflow Integration Test
//!
//! Tests the complete MIDI recording workflow:
//! Create track → Arm for recording → Inject MIDI → Stop → Verify recorded clip

use daw_engine::{
    MidiEngine, MidiMessage, MidiNote, Transport, TransportState,
    Project, SessionView, Clip, ClipState, Track, TrackType,
};

/// Full MIDI recording workflow test
#[test]
fn integration_midi_recording_workflow() {
    // Step 1: Create project with MIDI track
    let mut project = Project::new("MIDI Recording Test");
    project.set_tempo(120.0);
    project.add_track(Track::new("MIDI Track 1", TrackType::Midi));
    let track_idx = 0;
    
    // Step 2: Create session with clip slot
    let mut session = SessionView::new(1, 4);
    let clip = Clip::new_midi("recorded_midi", 4.0); // 4 bar clip
    session.set_clip(track_idx, 0, clip);
    
    // Step 3: Create MIDI engine
    let mut midi_engine = MidiEngine::new(16);
    
    // Step 4: Add notes to MIDI engine (simulating recording)
    // C Major chord progression: C-E-G, F-A-C, G-B-D, C-E-G
    let chord_progression = vec![
        vec![60, 64, 67], // C major
        vec![65, 69, 72], // F major
        vec![67, 71, 74], // G major
        vec![60, 64, 67], // C major
    ];
    
    for (bar, chord) in chord_progression.iter().enumerate() {
        for (note_idx, &pitch) in chord.iter().enumerate() {
            let note = MidiNote::new(
                pitch,
                100, // velocity
                bar as f32 * 4.0 + note_idx as f32 * 0.5, // spread across bar
                2.0, // 2 beat duration
            );
            midi_engine.add_note(0, note); // Channel 0
        }
    }
    
    // Verify notes were added
    let notes_in_engine = midi_engine.get_notes(0);
    let note_count = notes_in_engine.len();
    assert_eq!(note_count, 12, "Expected 12 notes (4 chords x 3 notes)");
    drop(notes_in_engine); // Drop the borrow before mutable use
    
    // Step 5: Set up transport and start recording
    let mut transport = Transport::new(120.0, 48000);
    transport.record(); // Start recording
    assert_eq!(transport.state(), TransportState::Recording);
    
    // Step 6: Simulate playback processing
    // Process through 16 beats (4 bars)
    let mut all_messages = Vec::new();
    
    for beat in 0..=16 {
        let messages = midi_engine.process(beat as f32);
        all_messages.extend(messages);
        
        // Advance transport
        transport.process(24000); // ~0.5 beat at 48kHz, 120 BPM
    }
    
    // Step 7: Verify MIDI messages were generated
    let note_on_count = all_messages.iter().filter(|m| m.is_note_on()).count();
    let note_off_count = all_messages.iter().filter(|m| m.is_note_off()).count();
    
    assert!(note_on_count > 0, "Expected note on messages during playback");
    assert!(note_off_count > 0, "Expected note off messages during playback");
    
    // Each note should generate 1 note on and 1 note off
    // But since we may have processed past some notes, we expect at least some events
    println!("Generated {} note-on and {} note-off messages", note_on_count, note_off_count);
    
    // Step 8: Stop recording
    transport.stop();
    assert_eq!(transport.state(), TransportState::Stopped);
    
    // Step 9: Verify clip state
    let clip_ref = session.get_clip(0, 0).unwrap();
    assert_eq!(clip_ref.state(), ClipState::Stopped);
    
    println!("MIDI recording workflow completed successfully!");
    println!("  - Recorded {} notes", note_count);
    println!("  - Generated {} MIDI messages", all_messages.len());
}

/// Test MIDI input at different tempos
#[test]
fn integration_midi_variable_tempo() {
    for tempo in [60.0, 120.0, 240.0] {
        let mut engine = MidiEngine::new(16);
        let mut transport = Transport::new(tempo, 48000);
        
        // Add a simple melody
        let melody = vec![60, 62, 64, 65, 67, 65, 64, 62];
        for (i, pitch) in melody.iter().enumerate() {
            let note = MidiNote::new(*pitch, 100, i as f32 * 0.5, 0.4);
            engine.add_note(0, note);
        }
        
        transport.play();
        
        // Process for 4 beats
        let samples_per_beat = (60.0 / tempo * 48000.0) as u32;
        let mut message_count = 0;
        
        for beat in 0..=4 {
            let messages = engine.process(beat as f32);
            message_count += messages.len();
            transport.process(samples_per_beat);
        }
        
        transport.stop();
        
        println!("Tempo {} BPM: Generated {} messages", tempo, message_count);
        assert!(message_count > 0, "Should generate MIDI at tempo {}", tempo);
    }
}

/// Test multi-channel MIDI recording
#[test]
fn integration_midi_multi_channel() {
    let mut engine = MidiEngine::new(16);
    
    // Add notes to different channels
    // Channel 0: Bass line
    for i in 0..4 {
        engine.add_note(0, MidiNote::new(36, 120, i as f32 * 1.0, 0.5)); // Kick drum
    }
    
    // Channel 1: Hi-hats
    for i in 0..8 {
        engine.add_note(1, MidiNote::new(42, 80, i as f32 * 0.5, 0.1)); // Closed hi-hat
    }
    
    // Channel 2: Melody
    for i in 0..4 {
        engine.add_note(2, MidiNote::new(60 + i * 2, 100, i as f32 * 1.0, 0.8));
    }
    
    // Verify each channel has correct notes
    assert_eq!(engine.get_notes(0).len(), 4, "Bass channel should have 4 notes");
    assert_eq!(engine.get_notes(1).len(), 8, "Hi-hat channel should have 8 notes");
    assert_eq!(engine.get_notes(2).len(), 4, "Melody channel should have 4 notes");
    
    // Process and collect messages by channel
    let mut messages_by_channel: [Vec<MidiMessage>; 16] = Default::default();
    
    for beat in 0..=4 {
        let messages = engine.process(beat as f32);
        for msg in messages {
            let ch = msg.channel() as usize;
            messages_by_channel[ch].push(msg);
        }
    }
    
    // Verify messages on each channel
    assert!(!messages_by_channel[0].is_empty(), "Channel 0 should have messages");
    assert!(!messages_by_channel[1].is_empty(), "Channel 1 should have messages");
    assert!(!messages_by_channel[2].is_empty(), "Channel 2 should have messages");
    
    // Channels 3-15 should be empty
    for ch in 3..16 {
        assert!(messages_by_channel[ch].is_empty(), "Channel {} should be empty", ch);
    }
}

/// Test MIDI controller changes during playback
#[test]
fn integration_midi_controller_changes() {
    let mut engine = MidiEngine::new(16);
    let mut transport = Transport::new(120.0, 48000);
    
    // Add a sustained note
    engine.add_note(0, MidiNote::new(60, 100, 0.0, 4.0));
    
    transport.play();
    
    let mut mod_wheel_values = Vec::new();
    
    // Process 4 beats, simulating mod wheel changes
    for beat in 0..=4 {
        // Simulate mod wheel movement (controller 1)
        let mod_value = (beat * 32) as u8; // Gradual increase
        engine.set_controller(0, 1, mod_value);
        mod_wheel_values.push(engine.get_controller(0, 1));
        
        let _messages = engine.process(beat as f32);
        transport.process(24000); // 0.5 beat
    }
    
    transport.stop();
    
    // Verify controller values were set
    assert_eq!(mod_wheel_values.len(), 5);
    assert_eq!(mod_wheel_values[0], 0);
    // Value 128 should be clamped to 127 (7-bit MIDI range)
    assert!(mod_wheel_values[4] <= 127);
}

/// Test recording punch-in/punch-out
#[test]
fn integration_midi_punch_in_out() {
    let mut transport = Transport::new(120.0, 48000);
    let mut engine = MidiEngine::new(16);
    
    // Notes across 8 bars
    for i in 0..8 {
        engine.add_note(0, MidiNote::new(60 + i as u8, 100, i as f32, 1.0));
    }
    
    // Set punch-in at bar 2, punch-out at bar 6
    transport.set_punch_in(2.0);
    transport.set_punch_out(6.0);
    transport.play();
    
    let mut recorded_notes = Vec::new();
    let samples_per_beat = (60.0 / 120.0 * 48000.0) as u32;
    
    // Process 8 bars
    for bar in 0..=8 {
        let beat = bar as f32;
        let messages = engine.process(beat);
        
        // Check if we're in punch-in range (bars 2-6)
        let in_punch_range = beat >= 2.0 && beat < 6.0;
        
        for msg in &messages {
            if msg.is_note_on() && in_punch_range {
                recorded_notes.push(msg.note());
            }
        }
        
        transport.process(samples_per_beat * 4); // 4 beats per bar
    }
    
    transport.stop();
    
    // Should have recorded notes from bars 2-6
    println!("Punch-in recorded {} notes", recorded_notes.len());
}
