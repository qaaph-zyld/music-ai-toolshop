//! Clip Launch Verification Test
//!
//! Verifies that the Rust engine can launch clips programmatically.

use daw_engine::session::{SessionView, Clip, ClipState};

#[test]
fn test_clip_launch_state_change() {
    // Create a clip
    let mut clip = Clip::new_audio("test_clip", 4.0);
    
    // Verify initial state is stopped
    assert_eq!(clip.state(), ClipState::Stopped);
    
    // Launch clip
    clip.play(0, 0);
    
    // Verify state changed to playing
    assert_eq!(clip.state(), ClipState::Playing);
}

#[test]
fn test_clip_stop_state_change() {
    // Create and launch a clip
    let mut clip = Clip::new_audio("test_clip", 4.0);
    clip.play(0, 0);
    
    // Verify it's playing
    assert_eq!(clip.state(), ClipState::Playing);
    
    // Stop clip
    clip.stop(0, 0);
    
    // Verify state changed back to stopped
    assert_eq!(clip.state(), ClipState::Stopped);
}

#[test]
fn test_session_view_clip_management() {
    // Create session view
    let mut session = SessionView::new(8, 8);

    // Add clip to session
    let clip = Clip::new_audio("test_clip", 4.0);
    session.set_clip(0, 0, clip);

    // Verify clip was added
    let retrieved_clip = session.get_clip(0, 0);
    assert!(retrieved_clip.is_some());
    assert_eq!(retrieved_clip.unwrap().name(), "test_clip");
}

#[test]
fn test_session_scene_launch() {
    // Create session view with clips
    let mut session = SessionView::new(8, 8);

    // Add clips to scene 0
    session.set_clip(0, 0, Clip::new_audio("clip1", 4.0));
    session.set_clip(1, 0, Clip::new_audio("clip2", 4.0));

    // Launch scene 0
    session.launch_scene(0);

    // Verify clips in scene are playing
    let clip0 = session.get_clip(0, 0);
    let clip1 = session.get_clip(1, 0);

    assert!(clip0.is_some());
    assert!(clip1.is_some());
    assert_eq!(clip0.unwrap().state(), ClipState::Playing);
    assert_eq!(clip1.unwrap().state(), ClipState::Playing);
}
