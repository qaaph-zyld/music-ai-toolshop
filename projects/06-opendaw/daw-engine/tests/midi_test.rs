//! MIDI tests
//! 
//! Tests for MIDI message handling and note processing.

use daw_engine::midi::{MidiMessage, MidiNote, MidiEngine};

#[test]
fn test_midi_note_on_message() {
    let msg = MidiMessage::note_on(60, 100, 0); // Middle C, velocity 100, channel 0
    
    assert_eq!(msg.note(), 60);
    assert_eq!(msg.velocity(), 100);
    assert_eq!(msg.channel(), 0);
    assert!(msg.is_note_on());
}

#[test]
fn test_midi_note_off_message() {
    let msg = MidiMessage::note_off(60, 0); // Middle C, channel 0
    
    assert_eq!(msg.note(), 60);
    assert_eq!(msg.velocity(), 0);
    assert!(msg.is_note_off());
}

#[test]
fn test_midi_control_change() {
    let msg = MidiMessage::control_change(1, 64, 0); // Mod wheel, value 64, channel 0
    
    assert_eq!(msg.controller_number(), 1);
    assert_eq!(msg.controller_value(), 64);
    assert!(msg.is_control_change());
}

#[test]
fn test_midi_note_creation() {
    let note = MidiNote::new(60, 100, 0.0, 1.0); // C4, vel 100, start 0, dur 1 beat
    
    assert_eq!(note.pitch(), 60);
    assert_eq!(note.velocity(), 100);
    assert_eq!(note.start_beat(), 0.0);
    assert_eq!(note.duration_beats(), 1.0);
}

#[test]
fn test_midi_note_is_active() {
    let note = MidiNote::new(60, 100, 0.0, 1.0);
    
    assert!(note.is_active_at(0.5)); // Active at beat 0.5
    assert!(!note.is_active_at(1.5)); // Not active after duration
}

#[test]
fn test_midi_engine_stores_notes() {
    let mut engine = MidiEngine::new(16); // 16 channels
    let note = MidiNote::new(60, 100, 0.0, 1.0);
    
    engine.add_note(0, note); // Add to channel 0
    
    let notes = engine.get_notes(0);
    assert_eq!(notes.len(), 1);
}

#[test]
fn test_midi_engine_processes_at_time() {
    let mut engine = MidiEngine::new(16);
    engine.add_note(0, MidiNote::new(60, 100, 0.0, 1.0));
    engine.add_note(0, MidiNote::new(64, 80, 0.5, 1.0));
    
    let messages = engine.process(0.0); // At beat 0
    assert_eq!(messages.len(), 1); // Only first note should trigger
    assert!(messages[0].is_note_on());
}

#[test]
fn test_midi_engine_generates_note_off() {
    let mut engine = MidiEngine::new(16);
    engine.add_note(0, MidiNote::new(60, 100, 0.0, 0.5)); // Short note
    
    // Process at start - should get note on
    let msg1 = engine.process(0.0);
    assert_eq!(msg1.len(), 1);
    
    // Process after note ends - should get note off
    let msg2 = engine.process(0.6);
    assert_eq!(msg2.len(), 1);
    assert!(msg2[0].is_note_off());
}

#[test]
fn test_pitch_to_frequency() {
    // A4 (MIDI 69) should be 440Hz
    assert!((MidiMessage::pitch_to_freq(69) - 440.0).abs() < 0.01);
    
    // A3 (MIDI 57) should be 220Hz
    assert!((MidiMessage::pitch_to_freq(57) - 220.0).abs() < 0.01);
}
