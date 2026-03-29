//! Session view tests
//! 
//! Tests for Ableton-style session grid with clip slots and scene launch.

use daw_engine::session::{SessionView, Clip, ClipState, Scene};

#[test]
fn test_session_view_creates_empty_grid() {
    let session = SessionView::new(8, 16); // 8 tracks, 16 scenes
    
    assert_eq!(session.track_count(), 8);
    assert_eq!(session.scene_count(), 16);
}

#[test]
fn test_clip_slot_starts_empty() {
    let session = SessionView::new(4, 8);
    
    let clip = session.get_clip(0, 0);
    assert!(clip.is_none(), "Clip slot should start empty");
}

#[test]
fn test_session_can_add_clip() {
    let mut session = SessionView::new(4, 8);
    let clip = Clip::new_audio("test.wav", 4.0); // 4 bar clip
    
    session.set_clip(0, 0, clip);
    
    let retrieved = session.get_clip(0, 0);
    assert!(retrieved.is_some(), "Clip should be stored");
}

#[test]
fn test_clip_has_correct_properties() {
    let clip = Clip::new_audio("drums.wav", 4.0);
    
    assert_eq!(clip.name(), "drums.wav");
    assert_eq!(clip.duration_bars(), 4.0);
    assert_eq!(clip.state(), ClipState::Stopped);
}

#[test]
fn test_clip_state_changes_to_playing() {
    let mut clip = Clip::new_audio("test.wav", 2.0);
    
    clip.play();
    
    assert_eq!(clip.state(), ClipState::Playing);
}

#[test]
fn test_clip_state_changes_to_stopped() {
    let mut clip = Clip::new_audio("test.wav", 2.0);
    
    clip.play();
    clip.stop();
    
    assert_eq!(clip.state(), ClipState::Stopped);
}

#[test]
fn test_scene_launch_plays_all_clips_in_row() {
    let mut session = SessionView::new(4, 8);
    
    // Add clips to scene 2 (row index 2)
    session.set_clip(0, 2, Clip::new_audio("kick.wav", 4.0));
    session.set_clip(1, 2, Clip::new_audio("snare.wav", 4.0));
    session.set_clip(2, 2, Clip::new_audio("hihat.wav", 4.0));
    
    // Launch scene 2
    session.launch_scene(2);
    
    // All clips in scene 2 should be playing
    assert_eq!(session.get_clip(0, 2).unwrap().state(), ClipState::Playing);
    assert_eq!(session.get_clip(1, 2).unwrap().state(), ClipState::Playing);
    assert_eq!(session.get_clip(2, 2).unwrap().state(), ClipState::Playing);
}

#[test]
fn test_scene_launch_stops_other_scenes() {
    let mut session = SessionView::new(2, 4);
    
    // Add clips to scene 0 and scene 1
    session.set_clip(0, 0, Clip::new_audio("old.wav", 4.0));
    session.set_clip(0, 1, Clip::new_audio("new.wav", 4.0));
    
    // Launch scene 0 first
    session.launch_scene(0);
    assert_eq!(session.get_clip(0, 0).unwrap().state(), ClipState::Playing);
    
    // Then launch scene 1 - should stop scene 0
    session.launch_scene(1);
    
    assert_eq!(session.get_clip(0, 0).unwrap().state(), ClipState::Stopped);
    assert_eq!(session.get_clip(0, 1).unwrap().state(), ClipState::Playing);
}

#[test]
fn test_clip_can_be_queued() {
    let mut clip = Clip::new_audio("test.wav", 2.0);
    
    clip.queue();
    
    assert_eq!(clip.state(), ClipState::Queued);
}

#[test]
fn test_session_gets_playing_clips() {
    let mut session = SessionView::new(4, 8);
    
    session.set_clip(0, 0, Clip::new_audio("kick.wav", 4.0));
    session.set_clip(1, 0, Clip::new_audio("snare.wav", 4.0));
    session.set_clip(0, 1, Clip::new_audio("bass.wav", 4.0));
    
    session.launch_scene(0);
    
    let playing = session.get_playing_clips();
    assert_eq!(playing.len(), 2, "Should have 2 playing clips from scene 0");
}
