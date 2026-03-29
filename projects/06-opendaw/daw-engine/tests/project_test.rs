//! Project serialization tests
//! 
//! Tests for save/load project state to JSON.

use daw_engine::project::{Project, Track, TrackType};

#[test]
fn test_project_creates_with_default_settings() {
    let project = Project::new("Test Project");
    
    assert_eq!(project.name(), "Test Project");
    assert_eq!(project.sample_rate(), 48000);
    assert_eq!(project.tempo(), 120.0);
}

#[test]
fn test_project_adds_tracks() {
    let mut project = Project::new("My Song");
    
    project.add_track(Track::new("Drums", TrackType::Audio));
    project.add_track(Track::new("Bass", TrackType::Audio));
    project.add_track(Track::new("Lead", TrackType::Midi));
    
    assert_eq!(project.track_count(), 3);
}

#[test]
fn test_track_has_correct_type() {
    let audio_track = Track::new("Audio", TrackType::Audio);
    let midi_track = Track::new("MIDI", TrackType::Midi);
    
    assert!(audio_track.is_audio());
    assert!(!audio_track.is_midi());
    
    assert!(midi_track.is_midi());
    assert!(!midi_track.is_audio());
}

#[test]
fn test_project_serializes_to_json() {
    let mut project = Project::new("Test");
    project.set_tempo(140.0);
    project.add_track(Track::new("Kick", TrackType::Audio));
    
    let json = project.to_json();
    
    assert!(json.contains("Test"));
    assert!(json.contains("Kick"));
    assert!(json.contains("140"));
}

#[test]
#[ignore = "serde dependency not yet added"]
fn test_project_deserializes_from_json() {
    let json = r#"{
        "name": "Loaded Project",
        "sample_rate": 44100,
        "tempo": 128.0,
        "tracks": [
            {"name": "Drums", "track_type": "Audio"}
        ]
    }"#;
    
    let project = Project::from_json(json).expect("Should parse");
    
    assert_eq!(project.name(), "Loaded Project");
    assert_eq!(project.sample_rate(), 44100);
    assert_eq!(project.tempo(), 128.0);
}

#[test]
fn test_project_sets_tempo() {
    let mut project = Project::new("Test");
    
    project.set_tempo(140.0);
    
    assert_eq!(project.tempo(), 140.0);
}

#[test]
fn test_project_sets_sample_rate() {
    let mut project = Project::new("Test");
    
    project.set_sample_rate(96000);
    
    assert_eq!(project.sample_rate(), 96000);
}

#[test]
fn test_project_saves_and_loads_file() {
    use std::path::Path;
    
    let mut project = Project::new("File Test");
    project.add_track(Track::new("Track 1", TrackType::Audio));
    
    let path = Path::new("test_project.json");
    
    // Save
    assert!(project.save(path).is_ok());
    
    // Load
    let loaded = Project::load(path);
    assert!(loaded.is_ok());
    
    let loaded_project = loaded.unwrap();
    assert_eq!(loaded_project.name(), "File Test");
    assert_eq!(loaded_project.track_count(), 1);
    
    // Cleanup
    let _ = std::fs::remove_file(path);
}
