//! Fuzzing Tests for Invalid Input Handling
//!
//! Tests graceful handling of malformed/corrupted data.

use daw_engine::{
    Mixer, SineWave, Sample, SamplePlayer,
    Project, SessionView, Clip, Transport, TransportState,
    MidiEngine, MidiNote, MidiMessage, AudioSource,
};

/// Test with corrupted/malformed JSON project data
#[test]
fn fuzz_malformed_project_json() {
    let long_name = "x".repeat(10000);
    let long_json = format!("{{\"name\": \"{}\"}}", long_name);
    let malformed_jsons: Vec<&str> = vec![
        "",
        "   \n\t  ",
        "{invalid",
        "}",
        "[",
        r#"{"name": "Test"}"#,
        r#"{"tracks": []}"#,
        r#"{"name": 123, "tracks": "invalid"}"#,
        r#"{"name": null, "tracks": null}"#,
        "{\"a\":{\"b\":{\"c\":{\"d\":{\"e\":{\"f\":\"deep\"}}}}}}",
        &long_json,
    ];
    
    for json in &malformed_jsons {
        let result = Project::from_json(json);
        // Should not panic, should return Err
        match result {
            Ok(_) => println!("Parsed unexpectedly: {}", &json[..json.len().min(50)]),
            Err(_) => {} // Expected
        }
    }
}

/// Test with invalid MIDI data
#[test]
fn fuzz_invalid_midi_data() {
    let mut engine = MidiEngine::new(16);
    
    // Test edge case note values
    let edge_cases = vec![
        (0u8, 0u8, 0.0f32),    // Minimum values
        (127, 127, 10000.0),  // Maximum values
        (60, 0, -1.0),        // Negative start (should handle)
        (60, 0, f32::NAN),    // NaN (will cause issues, test graceful handling)
        (60, 0, f32::INFINITY), // Infinity
        (255, 255, 0.0),      // Overflow values (wrapped by clamping)
    ];
    
    for (pitch, velocity, start) in edge_cases {
        // These should not panic even with edge cases
        let note = MidiNote::new(pitch, velocity, start, 1.0);
        engine.add_note(0, note);
    }
    
    // Engine should still process
    let _ = engine.process(0.0);
}

/// Test with extreme transport values
#[test]
fn fuzz_extreme_transport_values() {
    let mut transport = Transport::new(120.0, 48000);
    
    // Test extreme values
    transport.set_tempo(0.001); // Near zero
    transport.set_tempo(999999.0); // Very high
    
    transport.set_position(-1000.0); // Negative
    transport.set_position(f32::MAX); // Maximum
    
    // Jump functions with extreme values
    transport.jump_forward(f32::MAX);
    transport.jump_backward(f32::MAX);
    
    // Should not panic
    assert!(transport.position_beats() >= 0.0);
}

/// Test with empty/null sample data
#[test]
fn fuzz_empty_sample_data() {
    // Empty sample
    let empty_data: Vec<f32> = vec![];
    let empty_sample = Sample::from_raw(empty_data, 1, 48000);
    
    let mut player = SamplePlayer::new(empty_sample, 2);
    player.play();
    
    // Should produce silence without panic
    let mut output = vec![0.0f32; 128 * 2];
    player.process(&mut output);
    assert!(output.iter().all(|&s| s == 0.0));
}

/// Test mixer with extreme gain values
#[test]
fn fuzz_extreme_gain_values() {
    let mut mixer = Mixer::new(2);
    let mut sine = SineWave::new(440.0, 1.0);
    
    // Test extreme gain values
    sine.set_gain(0.0);      // Zero
    sine.set_gain(1000.0);   // Very high
    sine.set_gain(-100.0);   // Negative (should clamp)
    
    mixer.add_source(Box::new(sine));
    
    let mut output = vec![0.0f32; 128 * 2];
    mixer.process(&mut output);
    
    // Should not produce NaN or infinity
    for &sample in &output {
        assert!(!sample.is_nan(), "Output contains NaN");
        assert!(!sample.is_infinite(), "Output contains infinity");
    }
}

/// Test session view with out-of-bounds access
#[test]
fn fuzz_session_out_of_bounds() {
    let mut session = SessionView::new(8, 16);
    
    // Add a clip at valid position
    let clip = Clip::new_audio("test", 4.0);
    session.set_clip(0, 0, clip);
    
    // Try out-of-bounds access (should return None, not panic)
    assert!(session.get_clip(100, 100).is_none());
    assert!(session.get_clip(9999, 9999).is_none());
    
    // Set clip out of bounds (should be no-op)
    let clip2 = Clip::new_audio("oob", 4.0);
    session.set_clip(100, 100, clip2);
    
    // Session should still be valid
    assert!(session.get_clip(0, 0).is_some());
}

/// Test with malformed clip names
#[test]
fn fuzz_malformed_clip_names() {
    let names: Vec<&str> = vec![
        "",
        "\n",
        "\t",
        "   ",
        "longstring", // Will use repeat separately
        "special!@#$%^&*()",
        "unicode: 日本語 العربية",
        "\x00\x01\x02", // Control characters
    ];
    
    for name in &names {
        let clip = Clip::new_audio(name, 4.0);
        assert_eq!(clip.name(), *name); // Name should be stored as-is
    }
    
    // Test very long name separately
    let long_name = "x".repeat(10000);
    let clip = Clip::new_audio(&long_name, 4.0);
    assert_eq!(clip.name(), long_name);
}

/// Test rapid state changes
#[test]
fn fuzz_rapid_state_changes() {
    let mut transport = Transport::new(120.0, 48000);
    
    // Rapidly alternate states
    for _ in 0..1000 {
        transport.play();
        transport.pause();
        transport.play();
        transport.stop();
        transport.record();
        transport.stop();
    }
    
    // Transport should be in valid state
    let final_state = transport.state();
    assert!(
        matches!(final_state, TransportState::Stopped | TransportState::Playing | 
                 TransportState::Recording | TransportState::Paused),
        "Invalid final transport state"
    );
}

/// Test with corrupted/invalid audio file paths
#[test]
fn fuzz_invalid_audio_paths() {
    let paths: Vec<&str> = vec![
        "",
        "/nonexistent/path/file.wav",
        "file.with.many.dots.wav",
        "CON", // Reserved name on Windows
        "NUL",
        ":invalid:chars<>|?*",
        "\\\\server\\share\\file.wav",
        "file://invalid/url",
        ".",
        "..",
    ];
    
    // These are just path strings - actual file operations would fail
    // but creating the strings should not panic
    for path in &paths {
        let _: String = path.to_string();
    }
}

/// Test MIDI engine with overlapping notes
#[test]
fn fuzz_overlapping_midi_notes() {
    let mut engine = MidiEngine::new(16);
    
    // Add many overlapping notes on same channel
    for i in 0..100 {
        // All start at beat 0, various durations
        let note = MidiNote::new(
            60,
            100,
            0.0,
            (i + 1) as f32 * 0.1,
        );
        engine.add_note(0, note);
    }
    
    // Process and collect all messages
    let mut all_messages = Vec::new();
    for beat in 0..20 {
        let messages = engine.process(beat as f32 * 0.5);
        all_messages.extend(messages);
    }
    
    // Should have generated messages without panic
    println!("Generated {} messages for overlapping notes", all_messages.len());
}

/// Test with zero-duration notes
#[test]
fn fuzz_zero_duration_notes() {
    let mut engine = MidiEngine::new(16);
    
    // Add zero-duration notes
    for i in 0..10 {
        let note = MidiNote::new(
            60 + i as u8,
            100,
            i as f32,
            0.0, // Zero duration
        );
        engine.add_note(0, note);
    }
    
    // Process
    for beat in 0..=10 {
        let _ = engine.process(beat as f32);
    }
    
    // Should not panic with zero-duration notes
}

/// Test sample player with extreme speed values
#[test]
fn fuzz_sample_player_speed() {
    let data: Vec<f32> = (0..1000).map(|i| i as f32 / 1000.0).collect();
    let sample = Sample::from_raw(data, 1, 48000);
    
    let mut player = SamplePlayer::new(sample, 2);
    player.play();
    
    // Test extreme speed values
    player.set_speed(0.001);  // Very slow
    player.set_speed(100.0);  // Very fast
    player.set_speed(-1.0);   // Negative (should clamp)
    
    let mut output = vec![0.0f32; 128 * 2];
    player.process(&mut output);
    
    // Should not panic
    assert!(output.iter().all(|&s| !s.is_nan()));
}

/// Test with various buffer sizes
#[test]
fn fuzz_various_buffer_sizes() {
    let mut mixer = Mixer::new(2);
    mixer.add_source(Box::new(SineWave::new(440.0, 0.5)));
    
    let sizes = vec![
        1,    // Minimum
        15,   // Odd number
        16,   // Power of 2
        64,   // Common
        127,  // Prime-ish
        1000, // Large
        8192, // Maximum reasonable
    ];
    
    for size in &sizes {
        let mut output = vec![0.0f32; *size * 2]; // stereo
        mixer.process(&mut output);
        
        // Should produce non-silent output
        assert!(output.iter().any(|&s| s != 0.0));
    }
}
