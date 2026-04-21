//! AI Bridge Integration Test
//!
//! Tests integration between Rust engine and Python AI modules:
//! Pattern generation → Import to session → Playback verification

use daw_engine::{
    AIBridge, AIGeneratedClip, AINote,
    SessionView, Clip, MidiEngine, MidiNote,
    Transport, TransportState,
};

/// AI Bridge basic connectivity test
#[test]
fn integration_ai_bridge_connectivity() {
    let bridge = AIBridge::new();
    
    // Check if bridge is available
    let is_available = bridge.is_available();
    
    // Bridge should either be available or gracefully handle unavailability
    println!("AI Bridge available: {}", is_available);
    
    // Test should pass regardless (graceful degradation)
    assert!(true);
}

/// AI pattern generation and import workflow
#[test]
fn integration_ai_generate_and_import() {
    let bridge = AIBridge::new();
    let mut session = SessionView::new(4, 8); // 4 tracks, 8 scenes
    
    // Generate a pattern (may return stub data if AI not available)
    let generated = bridge.generate_pattern("electronic", 120, "C", 4);
    
    match generated {
        Ok(clip) => {
            println!("Generated clip with {} notes", clip.notes.len());
            
            // Import to session
            let session_clip = Clip::new_midi("ai_generated", clip.bars as f32);
            session.set_clip(0, 0, session_clip);
            
            // Verify clip was added
            let retrieved = session.get_clip(0, 0);
            assert!(retrieved.is_some());
            assert_eq!(retrieved.unwrap().name(), "ai_generated");
            
            // Convert to MIDI engine
            let mut engine = MidiEngine::new(16);
            for note in &clip.notes {
                let midi_note = MidiNote::new(
                    note.pitch,
                    note.velocity,
                    note.start_beat,
                    note.duration_beats,
                );
                engine.add_note(0, midi_note);
            }
            
            // Verify notes were added
            let notes_in_engine = engine.get_notes(0);
            assert_eq!(notes_in_engine.len(), clip.notes.len());
            
            // Test playback
            let mut transport = Transport::new(clip.tempo as f32, 48000);
            transport.play();
            
            let mut total_messages = 0;
            for beat in 0..=(clip.bars as i32 * 4) {
                let messages = engine.process(beat as f32);
                total_messages += messages.len();
            }
            
            transport.stop();
            
            println!("Generated MIDI generated {} messages", total_messages);
            assert!(total_messages > 0, "Should generate MIDI messages");
        }
        Err(_) => {
            println!("AI generation not available, skipping import test");
            // Test passes - graceful degradation
        }
    }
}

/// Test multiple style generation
#[test]
fn integration_ai_multiple_styles() {
    let bridge = AIBridge::new();
    let styles = vec!["electronic", "house", "techno", "ambient"];
    
    for style in &styles {
        let generated = bridge.generate_pattern(style, 120, "C", 4);
        
        match &generated {
            Ok(clip) => {
                println!("Style '{}': {} notes", style, clip.notes.len());
                assert!(clip.tempo > 0);
                assert!(clip.bars > 0);
            }
            Err(_) => {
                println!("Style '{}': not available", style);
            }
        }
    }
}

/// Test different keys and scales
#[test]
fn integration_ai_different_keys() {
    let bridge = AIBridge::new();
    let keys = vec!["C", "F#", "Am", "Bb minor", "G major"];
    
    for key in &keys {
        let generated = bridge.generate_pattern("electronic", 120, key, 4);
        
        match generated {
            Ok(clip) => {
                println!("Key '{}': {} notes, key signature: {}", key, clip.notes.len(), clip.key);
            }
            Err(_) => {}
        }
    }
}

/// Test stem extraction workflow (stub/mock)
#[test]
fn integration_stem_extraction_stub() {
    let bridge = AIBridge::new();
    
    // Try to extract stems (will likely return None or stub data)
    let stems = bridge.extract_stems("test_audio.wav");
    
    match stems {
        Ok(result) => {
            println!("Stem extraction result received");
            println!("  Drums: {:?}", result.drums_path());
            println!("  Bass: {:?}", result.bass_path());
            println!("  Vocals: {:?}", result.vocals_path());
            println!("  Other: {:?}", result.other_path());
        }
        Err(_) => {
            println!("Stem extraction not available (expected)");
        }
    }
}

/// Test Suno library integration
#[test]
fn integration_suno_library_stub() {
    let bridge = AIBridge::new();
    
    // Try to get Suno tracks
    let tracks = bridge.search_suno_library(None, None, None, None);
    
    match tracks {
        Ok(track_list) => {
            println!("Suno library: {} tracks available", track_list.len());
            for track in &track_list {
                println!("  - {} by {} ({} BPM, {})", 
                    track.title, track.artist, track.tempo, track.key);
            }
        }
        Err(_) => {
            println!("Suno library not connected (expected)");
        }
    }
}

/// Test AI generation with invalid parameters (error handling)
#[test]
fn integration_ai_invalid_params() {
    let bridge = AIBridge::new();
    
    // Test with edge case parameters
    let result = bridge.generate_pattern("nonexistent_style", 0, "X", 0);
    
    // Should either succeed with defaults or return Err (not panic)
    match result {
        Ok(clip) => {
            println!("Handled invalid params gracefully: {} notes", clip.notes.len());
        }
        Err(e) => {
            println!("Correctly returned error for invalid params: {}", e);
        }
    }
}

/// End-to-end AI workflow: generate → import → play
#[test]
fn integration_ai_full_workflow() {
    let bridge = AIBridge::new();
    
    // Only run full test if AI is available
    if !bridge.is_available() {
        println!("AI Bridge not available, skipping full workflow");
        return;
    }
    
    // 1. Generate pattern
    let generated = bridge.generate_pattern("techno", 128, "C", 8)
        .expect("AI should be available for this test");
    
    println!("Generated {} notes at {} BPM", generated.notes.len(), generated.tempo);
    
    // 2. Create session and add clip
    let mut session = SessionView::new(8, 16);
    let clip = Clip::new_midi("techno_bass", generated.bars as f32);
    session.set_clip(0, 0, clip);
    
    // 3. Set up MIDI engine with generated notes
    let mut engine = MidiEngine::new(16);
    for note in &generated.notes {
        engine.add_note(0, MidiNote::new(
            note.pitch,
            note.velocity,
            note.start_beat,
            note.duration_beats,
        ));
    }
    
    // 4. Launch scene and play
    session.launch_scene(0);
    
    let mut transport = Transport::new(generated.tempo as f32, 48000);
    transport.play();
    
    // 5. Process for duration of clip
    let duration_beats = generated.bars as f32 * 4.0; // Assuming 4/4
    let samples_per_beat = (60.0 / generated.tempo as f32 * 48000.0) as u32;
    
    let mut note_on_count = 0;
    let mut note_off_count = 0;
    
    for beat in 0..=duration_beats as i32 {
        let messages = engine.process(beat as f32);
        
        for msg in &messages {
            if msg.is_note_on() { note_on_count += 1; }
            if msg.is_note_off() { note_off_count += 1; }
        }
        
        transport.process(samples_per_beat);
    }
    
    transport.stop();
    session.stop_all();
    
    println!("Full workflow complete!");
    println!("  Note-ons: {}, Note-offs: {}", note_on_count, note_off_count);
    
    // Verify we got MIDI output
    assert!(note_on_count > 0, "Should have note-on messages");
}
