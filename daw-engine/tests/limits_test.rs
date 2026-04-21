//! Resource Limit Tests
//!
//! Tests behavior at and beyond documented limits.

use daw_engine::{
    Mixer, SineWave, Sample, SessionView, Clip,
    MidiEngine, MidiNote, Transport, Project, Track, TrackType,
    limits, validate_sample_rate, validate_tempo,
};
use daw_engine::error::validate_track_count;

/// Test maximum tracks constant
#[test]
fn test_max_tracks_constant() {
    assert_eq!(limits::MAX_TRACKS, 128);
}

/// Test maximum scenes constant
#[test]
fn test_max_scenes_constant() {
    assert_eq!(limits::MAX_SCENES, 256);
}

/// Test maximum MIDI notes constant
#[test]
fn test_max_midi_notes_constant() {
    assert_eq!(limits::MAX_MIDI_NOTES, 100_000);
}

/// Test mixer at exactly MAX_TRACKS limit
#[test]
fn test_mixer_at_max_tracks() {
    let mut mixer = Mixer::new(2);
    
    // Add exactly MAX_TRACKS sources
    for i in 0..limits::MAX_TRACKS {
        let sine = SineWave::new(100.0 + i as f32, 0.01);
        mixer.add_source(Box::new(sine));
    }
    
    assert_eq!(mixer.source_count(), limits::MAX_TRACKS);
    
    // Process should succeed
    let mut output = vec![0.0f32; 128 * 2];
    mixer.process(&mut output);
}

/// Test mixer beyond MAX_TRACKS (should handle gracefully)
#[test]
fn test_mixer_beyond_max_tracks() {
    let mut mixer = Mixer::new(2);
    
    // Add more than MAX_TRACKS - this should still work
    // (we don't enforce hard limits, just document them)
    for i in 0..limits::MAX_TRACKS + 10 {
        let sine = SineWave::new(100.0 + i as f32, 0.005);
        mixer.add_source(Box::new(sine));
    }
    
    assert_eq!(mixer.source_count(), limits::MAX_TRACKS + 10);
    
    // Process should still succeed
    let mut output = vec![0.0f32; 128 * 2];
    mixer.process(&mut output);
}

/// Test session at maximum scenes
#[test]
fn test_session_at_max_scenes() {
    let session = SessionView::new(8, limits::MAX_SCENES);
    
    assert_eq!(session.scene_count(), limits::MAX_SCENES);
}

/// Test MIDI engine at maximum notes per clip
#[test]
fn test_midi_at_max_notes() {
    let mut engine = MidiEngine::new(16);
    
    // Add exactly MAX_MIDI_NOTES
    for i in 0..limits::MAX_MIDI_NOTES {
        let note = MidiNote::new(
            60 + (i % 60) as u8,
            100,
            i as f32 * 0.01,
            0.5,
        );
        engine.add_note(0, note);
    }
    
    assert_eq!(engine.get_notes(0).len(), limits::MAX_MIDI_NOTES);
    
    // Process should handle this
    let messages = engine.process(0.0);
    // May or may not have messages at beat 0.0
    let _ = messages; // Don't fail if empty
}

/// Test sample rate validation
#[test]
fn test_sample_rate_validation() {
    // Valid rates
    assert!(validate_sample_rate(8000).is_ok());
    assert!(validate_sample_rate(44100).is_ok());
    assert!(validate_sample_rate(48000).is_ok());
    assert!(validate_sample_rate(96000).is_ok());
    assert!(validate_sample_rate(192000).is_ok());
    
    // Invalid rates
    assert!(validate_sample_rate(1000).is_err());
    assert!(validate_sample_rate(200000).is_err());
}

/// Test tempo validation
#[test]
fn test_tempo_validation() {
    // Valid tempos
    assert!(validate_tempo(1.0).is_ok());
    assert!(validate_tempo(60.0).is_ok());
    assert!(validate_tempo(120.0).is_ok());
    assert!(validate_tempo(240.0).is_ok());
    assert!(validate_tempo(999.0).is_ok());
    
    // Invalid tempos
    assert!(validate_tempo(0.5).is_err());
    assert!(validate_tempo(1000.0).is_err());
}

/// Test track count validation
#[test]
fn test_track_count_validation() {
    // Valid counts
    assert!(validate_track_count(1).is_ok());
    assert!(validate_track_count(64).is_ok());
    assert!(validate_track_count(128).is_ok());
    
    // Invalid counts
    assert!(validate_track_count(200).is_err());
    assert!(validate_track_count(1000).is_err());
}

/// Test transport at extreme positions
#[test]
fn test_transport_extreme_positions() {
    let mut transport = Transport::new(120.0, 48000);
    
    // Very large position
    transport.set_position(1_000_000.0); // 1 million beats
    assert_eq!(transport.position_beats(), 1_000_000.0);
    
    // Process at this position
    transport.play();
    transport.process(48000); // 1 second
    assert!(transport.position_beats() > 1_000_000.0);
}

/// Test sample at maximum sample rate
#[test]
fn test_sample_max_sample_rate() {
    let sample_rate = limits::MAX_SAMPLE_RATE;
    let data = vec![0.5f32; sample_rate as usize * 2]; // 2 seconds
    
    let sample = Sample::from_raw(data, 2, sample_rate);
    assert_eq!(sample.sample_rate(), sample_rate);
    assert_eq!(sample.frame_count(), sample_rate as usize);
}

/// Test project with maximum tracks
#[test]
fn test_project_max_tracks() {
    let mut project = Project::new("Max Tracks Test");
    
    for i in 0..limits::MAX_TRACKS {
        project.add_track(Track::new(&format!("Track {}", i), TrackType::Audio));
    }
    
    assert_eq!(project.track_count(), limits::MAX_TRACKS);
}

/// Test large project serialization
#[test]
fn test_large_project_serialization() {
    let mut project = Project::new("Large Project");
    
    // Add many tracks with names
    for i in 0..64 {
        let name = format!("Track {} with a long descriptive name", i);
        project.add_track(Track::new(&name, TrackType::Audio));
    }
    
    // Serialize using native method
    let json = project.to_json();
    
    // Verify not empty
    assert!(!json.is_empty());
    
    // Deserialize using native method
    let restored = Project::from_json(&json).expect("Should deserialize large project");
    assert_eq!(restored.track_count(), 64);
}

/// Test session view at limits
#[test]
fn test_session_view_limits() {
    // Maximum tracks and scenes
    let session = SessionView::new(limits::MAX_TRACKS, limits::MAX_SCENES);
    
    assert_eq!(session.track_count(), limits::MAX_TRACKS);
    assert_eq!(session.scene_count(), limits::MAX_SCENES);
}

/// Test memory usage with many clips
#[test]
fn test_memory_many_clips() {
    let mut session = SessionView::new(8, 16);
    
    // Fill every slot with a clip
    for track in 0..8 {
        for scene in 0..16 {
            let clip = Clip::new_audio(
                &format!("clip_t{}_s{}", track, scene),
                4.0,
            );
            session.set_clip(track, scene, clip);
        }
    }
    
    // Verify all 128 clips added
    let mut clip_count = 0;
    for track in 0..8 {
        for scene in 0..16 {
            if session.get_clip(track, scene).is_some() {
                clip_count += 1;
            }
        }
    }
    
    assert_eq!(clip_count, 128);
}
