//! Clip Player - Real-time clip playback integration
//!
//! Manages clip triggering and playback state, integrating with the
//! audio processor for sample-accurate clip playback.

use crate::{profile_scope, plot_value};

/// Playback state for a single clip
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ClipPlaybackState {
    /// Clip is stopped
    Stopped,
    /// Clip is playing (with position in beats)
    Playing { position_beats: f64 },
    /// Clip is queued to start on next beat
    Queued,
}

impl Default for ClipPlaybackState {
    fn default() -> Self {
        ClipPlaybackState::Stopped
    }
}

/// Track playback state containing clip states
#[derive(Debug, Clone)]
pub struct TrackPlaybackState {
    /// Current playback state per clip slot
    pub clip_states: Vec<ClipPlaybackState>,
    /// Currently playing clip index (if any)
    pub playing_clip_idx: Option<usize>,
    /// Clip queued to start
    pub queued_clip_idx: Option<usize>,
}

impl TrackPlaybackState {
    /// Create new track playback state with given clip count
    pub fn new(clip_count: usize) -> Self {
        Self {
            clip_states: vec![ClipPlaybackState::Stopped; clip_count],
            playing_clip_idx: None,
            queued_clip_idx: None,
        }
    }
    
    /// Trigger a clip to play
    pub fn trigger_clip(&mut self, clip_idx: usize) {
        profile_scope!("track_trigger_clip");
        
        if clip_idx >= self.clip_states.len() {
            return;
        }
        
        // Stop any currently playing clip
        if let Some(current) = self.playing_clip_idx {
            self.clip_states[current] = ClipPlaybackState::Stopped;
        }
        
        // Start new clip
        self.clip_states[clip_idx] = ClipPlaybackState::Playing { position_beats: 0.0 };
        self.playing_clip_idx = Some(clip_idx);
        self.queued_clip_idx = None;
    }
    
    /// Stop playing clip
    pub fn stop_clip(&mut self) {
        profile_scope!("track_stop_clip");
        
        if let Some(current) = self.playing_clip_idx {
            self.clip_states[current] = ClipPlaybackState::Stopped;
            self.playing_clip_idx = None;
        }
    }
    
    /// Queue a clip to start on next beat
    pub fn queue_clip(&mut self, clip_idx: usize) {
        profile_scope!("track_queue_clip");
        
        if clip_idx < self.clip_states.len() {
            self.queued_clip_idx = Some(clip_idx);
        }
    }
    
    /// Process queued clip at beat boundary
    pub fn process_queue(&mut self) {
        if let Some(queued) = self.queued_clip_idx {
            self.trigger_clip(queued);
        }
    }
    
    /// Get playback state for a clip
    pub fn get_clip_state(&self, clip_idx: usize) -> ClipPlaybackState {
        if clip_idx >= self.clip_states.len() {
            return ClipPlaybackState::Stopped;
        }
        
        // Check if this clip is queued
        if self.queued_clip_idx == Some(clip_idx) {
            return ClipPlaybackState::Queued;
        }
        
        self.clip_states[clip_idx]
    }
    
    /// Check if any clip is playing
    pub fn is_playing(&self) -> bool {
        self.playing_clip_idx.is_some()
    }
}

/// Global clip player managing all track playback
#[derive(Debug)]
pub struct ClipPlayer {
    /// Playback state per track
    track_states: Vec<TrackPlaybackState>,
    /// Number of clips per track
    clips_per_track: usize,
}

impl ClipPlayer {
    /// Create new clip player
    pub fn new(track_count: usize, clips_per_track: usize) -> Self {
        Self {
            track_states: (0..track_count)
                .map(|_| TrackPlaybackState::new(clips_per_track))
                .collect(),
            clips_per_track,
        }
    }
    
    /// Trigger a clip on a specific track
    pub fn trigger_clip(&mut self, track_idx: usize, clip_idx: usize) -> bool {
        profile_scope!("clip_player_trigger");
        
        if let Some(track) = self.track_states.get_mut(track_idx) {
            track.trigger_clip(clip_idx);
            plot_value!("playing_tracks", self.track_states.iter().filter(|t| t.is_playing()).count() as f64);
            true
        } else {
            false
        }
    }
    
    /// Stop clip on a specific track
    pub fn stop_track(&mut self, track_idx: usize) -> bool {
        if let Some(track) = self.track_states.get_mut(track_idx) {
            track.stop_clip();
            true
        } else {
            false
        }
    }
    
    /// Queue a clip on a specific track
    pub fn queue_clip(&mut self, track_idx: usize, clip_idx: usize) -> bool {
        if let Some(track) = self.track_states.get_mut(track_idx) {
            track.queue_clip(clip_idx);
            true
        } else {
            false
        }
    }
    
    /// Get playback state for a clip
    pub fn get_clip_state(&self, track_idx: usize, clip_idx: usize) -> ClipPlaybackState {
        self.track_states
            .get(track_idx)
            .map(|t| t.get_clip_state(clip_idx))
            .unwrap_or(ClipPlaybackState::Stopped)
    }
    
    /// Get track playback state
    pub fn get_track_state(&self, track_idx: usize) -> Option<&TrackPlaybackState> {
        self.track_states.get(track_idx)
    }
    
    /// Check if track has playing clip
    pub fn is_track_playing(&self, track_idx: usize) -> bool {
        self.track_states
            .get(track_idx)
            .map(|t| t.is_playing())
            .unwrap_or(false)
    }
    
    /// Process queued clips at beat boundary (call from audio thread)
    pub fn process_queued_clips(&mut self) {
        profile_scope!("clip_player_process_queue");
        
        for track in &mut self.track_states {
            track.process_queue();
        }
        
        // Plot playing track count
        let playing_count = self.track_states.iter().filter(|t| t.is_playing()).count();
        plot_value!("playing_tracks", playing_count as f64);
    }
    
    /// Stop clip on a specific track (alias for stop_track for API consistency)
    pub fn stop_clip(&mut self, track_idx: usize) -> bool {
        let result = self.stop_track(track_idx);
        if result {
            plot_value!("playing_tracks", self.track_states.iter().filter(|t| t.is_playing()).count() as f64);
        }
        result
    }
    
    /// Get number of tracks
    pub fn track_count(&self) -> usize {
        self.track_states.len()
    }
    
    /// Get number of clips per track
    pub fn clip_count_per_track(&self) -> usize {
        self.clips_per_track
    }
    
    /// Get playback position in beats for a track (returns 0.0 if not playing)
    pub fn get_playback_position(&self, track_idx: usize) -> Option<f64> {
        self.track_states.get(track_idx).and_then(|t| {
            if let Some(clip_idx) = t.playing_clip_idx {
                match t.clip_states.get(clip_idx) {
                    Some(ClipPlaybackState::Playing { position_beats }) => Some(*position_beats),
                    _ => None,
                }
            } else {
                None
            }
        })
    }
    
    /// Get currently playing clip index for a track (alias for get_playing_clip)
    pub fn get_playing_clip_index(&self, track_idx: usize) -> Option<usize> {
        self.get_playing_clip(track_idx)
    }
    
    /// Get currently playing clip index for a track
    pub fn get_playing_clip(&self, track_idx: usize) -> Option<usize> {
        self.track_states
            .get(track_idx)
            .and_then(|t| t.playing_clip_idx)
    }
    
    /// Stop all clips (panic button)
    pub fn stop_all(&mut self) {
        profile_scope!("clip_player_stop_all");
        
        for track in &mut self.track_states {
            track.stop_clip();
        }
        plot_value!("playing_tracks", 0.0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    // TDD: Test 1 - Clip player creation
    #[test]
    fn test_clip_player_creation() {
        let player = ClipPlayer::new(8, 8); // 8 tracks, 8 clips per track
        
        // All tracks should be stopped
        for i in 0..8 {
            assert!(!player.is_track_playing(i), "Track {} should be stopped", i);
        }
    }
    
    // TDD: Test 2 - Trigger clip plays it
    #[test]
    fn test_clip_player_trigger_clip() {
        let mut player = ClipPlayer::new(8, 8);
        
        // Trigger clip 2 on track 3
        let result = player.trigger_clip(3, 2);
        assert!(result, "Should succeed triggering valid clip");
        
        // Track 3 should be playing
        assert!(player.is_track_playing(3), "Track 3 should be playing");
        
        // Playing clip should be index 2
        assert_eq!(player.get_playing_clip(3), Some(2), "Playing clip should be index 2");
    }
    
    // TDD: Test 3 - Stop clip stops playback
    #[test]
    fn test_clip_player_stop_clip() {
        let mut player = ClipPlayer::new(8, 8);
        
        // Start and stop
        player.trigger_clip(1, 3);
        assert!(player.is_track_playing(1));
        
        let result = player.stop_track(1);
        assert!(result, "Should succeed stopping valid track");
        assert!(!player.is_track_playing(1), "Track should be stopped");
        assert_eq!(player.get_playing_clip(1), None, "No clip should be playing");
    }
    
    // TDD: Test 4 - Get clip playback state
    #[test]
    fn test_clip_player_get_playback_state() {
        let mut player = ClipPlayer::new(8, 8);
        
        // Initially stopped
        let state = player.get_clip_state(0, 0);
        assert!(matches!(state, ClipPlaybackState::Stopped));
        
        // Trigger and check playing state
        player.trigger_clip(0, 1);
        let state = player.get_clip_state(0, 1);
        assert!(matches!(state, ClipPlaybackState::Playing { .. }));
        
        // Other clips still stopped
        let state = player.get_clip_state(0, 0);
        assert!(matches!(state, ClipPlaybackState::Stopped));
    }
    
    // TDD: Test 5 - Invalid track index returns error
    #[test]
    fn test_clip_player_invalid_track() {
        let mut player = ClipPlayer::new(4, 4);
        
        // Try to trigger on invalid track
        let result = player.trigger_clip(10, 0);
        assert!(!result, "Should fail for invalid track index");
        
        let result = player.stop_track(99);
        assert!(!result, "Should fail for invalid track index");
    }
    
    // TDD: Test 6 - Invalid clip index is ignored
    #[test]
    fn test_clip_player_invalid_clip() {
        let mut player = ClipPlayer::new(4, 4);
        
        // Try to trigger invalid clip (should be ignored)
        player.trigger_clip(0, 10);
        
        // Track should still not be playing
        assert!(!player.is_track_playing(0));
    }
    
    // TDD: Test 7 - Queue clip for next beat
    #[test]
    fn test_clip_player_queue_clip() {
        let mut player = ClipPlayer::new(8, 8);
        
        // Queue a clip
        let result = player.queue_clip(2, 5);
        assert!(result, "Should succeed queuing valid clip");
        
        // Not playing yet
        assert!(!player.is_track_playing(2));
        
        // Process queue
        player.process_queued_clips();
        
        // Now playing
        assert!(player.is_track_playing(2));
        assert_eq!(player.get_playing_clip(2), Some(5));
    }
    
    // TDD: Test 8 - Stop all stops everything
    #[test]
    fn test_clip_player_stop_all() {
        let mut player = ClipPlayer::new(8, 8);
        
        // Start multiple clips
        player.trigger_clip(0, 0);
        player.trigger_clip(2, 3);
        player.trigger_clip(5, 7);
        
        assert!(player.is_track_playing(0));
        assert!(player.is_track_playing(2));
        assert!(player.is_track_playing(5));
        
        // Stop all
        player.stop_all();
        
        // All stopped
        for i in 0..8 {
            assert!(!player.is_track_playing(i), "Track {} should be stopped", i);
        }
    }
    
    // TDD: Test 9 - Trigger new clip stops previous
    #[test]
    fn test_clip_player_new_clip_stops_old() {
        let mut player = ClipPlayer::new(8, 8);
        
        // Start first clip
        player.trigger_clip(0, 2);
        assert_eq!(player.get_playing_clip(0), Some(2));
        
        // Start different clip on same track
        player.trigger_clip(0, 5);
        
        // New clip playing, old stopped
        assert_eq!(player.get_playing_clip(0), Some(5));
        let state = player.get_clip_state(0, 2);
        assert!(matches!(state, ClipPlaybackState::Stopped));
    }
    
    // TDD: Test 10 - Track playback state structure
    #[test]
    fn test_track_playback_state() {
        let mut state = TrackPlaybackState::new(8);
        
        // Initial state
        assert!(state.playing_clip_idx.is_none());
        assert!(state.queued_clip_idx.is_none());
        assert!(!state.is_playing());
        
        // Trigger
        state.trigger_clip(3);
        assert_eq!(state.playing_clip_idx, Some(3));
        assert!(state.is_playing());
        
        // Get state
        let clip_state = state.get_clip_state(3);
        assert!(matches!(clip_state, ClipPlaybackState::Playing { .. }));
    }
}
