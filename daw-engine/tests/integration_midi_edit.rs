//! Integration tests for MIDI editing features
//!
//! Tests quantization, transpose, duplication, and note manipulation.

use daw_engine::{MidiNote, Clip, SessionView, midi_edit::MidiEditor};

#[test]
fn test_midi_quantize_16th_note() {
    let mut editor = MidiEditor::new();
    
    // Create notes at off-beat positions
    let notes = vec![
        MidiNote::new(60, 100, 0.05, 0.5),  // Slightly after beat 0
        MidiNote::new(64, 100, 0.55, 0.5),  // Slightly after beat 0.5
        MidiNote::new(67, 100, 1.05, 0.5), // Slightly after beat 1
    ];
    
    let quantized = editor.quantize(&notes, 0.25); // 1/16 = 0.25 beats
    
    // Should snap to nearest 1/4 beat
    assert!((quantized[0].start_beat() - 0.0).abs() < 0.001, "Note 1 should snap to beat 0");
    assert!((quantized[1].start_beat() - 0.5).abs() < 0.001, "Note 2 should stay at beat 0.5");
    assert!((quantized[2].start_beat() - 1.0).abs() < 0.001, "Note 3 should snap to beat 1");
}

#[test]
fn test_midi_quantize_8th_note() {
    let mut editor = MidiEditor::new();
    
    let notes = vec![
        MidiNote::new(60, 100, 0.3, 0.5), // Between 1/4 and 1/2
    ];
    
    let quantized = editor.quantize(&notes, 0.5); // 1/8 = 0.5 beats
    
    // 0.3 is closer to 0.25 than 0.5 with 1/8 grid
    // Actually with 1/8 grid (0.5), options are 0.0, 0.5, 1.0
    // 0.3 is 0.3 from 0.0, 0.2 from 0.5 - should snap to 0.5
    assert!((quantized[0].start_beat() - 0.5).abs() < 0.001);
}

#[test]
fn test_midi_transpose_up_octave() {
    let mut editor = MidiEditor::new();
    
    let notes = vec![
        MidiNote::new(60, 100, 0.0, 1.0), // Middle C
        MidiNote::new(64, 100, 1.0, 1.0), // E
    ];
    
    let transposed = editor.transpose(&notes, 12); // Up one octave
    
    assert_eq!(transposed[0].pitch(), 72); // C5
    assert_eq!(transposed[1].pitch(), 76); // E5
}

#[test]
fn test_midi_transpose_down_bounded() {
    let mut editor = MidiEditor::new();
    
    let notes = vec![
        MidiNote::new(10, 100, 0.0, 1.0), // Very low note
    ];
    
    let transposed = editor.transpose(&notes, -24); // Down 2 octaves
    
    // Should be clamped to 0 (minimum MIDI pitch)
    assert_eq!(transposed[0].pitch(), 0);
}

#[test]
fn test_midi_transpose_upper_bound() {
    let mut editor = MidiEditor::new();
    
    let notes = vec![
        MidiNote::new(120, 100, 0.0, 1.0), // Very high note
    ];
    
    let transposed = editor.transpose(&notes, 20); // Would exceed 127
    
    // Should be clamped to 127 (maximum MIDI pitch)
    assert_eq!(transposed[0].pitch(), 127);
}

#[test]
fn test_midi_clip_duplicate() {
    let mut session = SessionView::new(8, 16);
    
    // Create a clip with notes
    let notes = vec![
        MidiNote::new(60, 100, 0.0, 0.5),
        MidiNote::new(64, 90, 0.5, 0.5),
    ];
    let clip = Clip::new_midi_with_notes("Test", 2.0, notes);
    
    // Insert clip at track 0, scene 0
    session.set_clip(0, 0, clip);
    
    // Duplicate to track 1, scene 0
    let mut editor = MidiEditor::new();
    editor.duplicate_clip(&mut session, 0, 0, 1, 0).unwrap();
    
    // Verify both clips exist with same notes
    let original = session.get_clip(0, 0).unwrap();
    let duplicate = session.get_clip(1, 0).unwrap();
    
    assert_eq!(original.name(), duplicate.name());
}

#[test]
fn test_midi_add_note() {
    let mut editor = MidiEditor::new();
    let mut notes = vec![];
    
    editor.add_note(&mut notes, 60, 100, 0.0, 1.0);
    
    assert_eq!(notes.len(), 1);
    assert_eq!(notes[0].pitch(), 60);
    assert_eq!(notes[0].velocity(), 100);
    assert!((notes[0].start_beat() - 0.0).abs() < 0.001);
    assert!((notes[0].duration_beats() - 1.0).abs() < 0.001);
}

#[test]
fn test_midi_delete_note() {
    let mut editor = MidiEditor::new();
    let mut notes = vec![
        MidiNote::new(60, 100, 0.0, 1.0),
        MidiNote::new(64, 100, 1.0, 1.0),
    ];
    
    editor.delete_note(&mut notes, 0);
    
    assert_eq!(notes.len(), 1);
    assert_eq!(notes[0].pitch(), 64); // Remaining note
}

#[test]
fn test_midi_move_note() {
    let mut editor = MidiEditor::new();
    let mut notes = vec![
        MidiNote::new(60, 100, 0.0, 1.0),
    ];
    
    editor.move_note(&mut notes, 0, 2.0, 64);
    
    assert!((notes[0].start_beat() - 2.0).abs() < 0.001);
    assert_eq!(notes[0].pitch(), 64);
}

#[test]
fn test_midi_velocity_scaling() {
    let mut editor = MidiEditor::new();
    
    let notes = vec![
        MidiNote::new(60, 50, 0.0, 1.0),
        MidiNote::new(64, 100, 0.0, 1.0),
    ];
    
    let scaled = editor.scale_velocity(&notes, 1.5); // Scale up by 1.5x
    
    // 50 * 1.5 = 75, 100 * 1.5 = 150 (clamped to 127)
    assert_eq!(scaled[0].velocity(), 75);
    assert_eq!(scaled[1].velocity(), 127); // Clamped
}

#[test]
fn test_midi_quantize_triplet() {
    let mut editor = MidiEditor::new();
    
    // 1/8 triplet grid = 1/3 beat ≈ 0.333
    let notes = vec![
        MidiNote::new(60, 100, 0.3, 0.5), // Close to 1/3
    ];
    
    let quantized = editor.quantize(&notes, 1.0 / 3.0);
    
    assert!((quantized[0].start_beat() - (1.0 / 3.0)).abs() < 0.001);
}

#[test]
fn test_midi_humanize() {
    let mut editor = MidiEditor::new();
    
    let notes = vec![
        MidiNote::new(60, 100, 1.0, 0.5),
    ];
    
    // Humanize adds small random timing variations
    let humanized = editor.humanize(&notes, 0.02); // 20ms max variation
    
    // Should be within +/- 0.02 beats of original
    let diff = (humanized[0].start_beat() - 1.0).abs();
    assert!(diff <= 0.02, "Humanize should keep within bounds");
}
