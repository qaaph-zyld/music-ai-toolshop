//! Sample Player Integration - Wire clip playback to audio output
//!
//! Connects the clip_player state management to the sample_player
//! for actual audio output generation.

use std::collections::HashMap;
use crate::clip_player::ClipPlayer;
use crate::sample_player::SamplePlayer;
use crate::sample::Sample;

/// Sample identifier type
pub type SampleId = usize;

/// Integration between clip player and sample player
#[derive(Debug)]
pub struct SamplePlayerIntegration {
    /// Sample players for each track
    track_players: Vec<Option<SamplePlayer>>,
    /// Map of (track_idx, clip_idx) -> Sample
    clip_samples: HashMap<(usize, usize), Sample>,
    /// Currently loaded sample IDs per track
    active_samples: HashMap<usize, SampleId>,
    /// Output buffer for mixing
    mix_buffer: Vec<f32>,
}

impl SamplePlayerIntegration {
    /// Create new integration with given track count
    pub fn new(track_count: usize) -> Self {
        Self {
            track_players: (0..track_count).map(|_| None).collect(),
            clip_samples: HashMap::new(),
            active_samples: HashMap::new(),
            mix_buffer: Vec::new(),
        }
    }
    
    /// Load a sample for a specific clip slot
    pub fn load_sample(&mut self, track_idx: usize, clip_idx: usize, sample: Sample) {
        self.clip_samples.insert((track_idx, clip_idx), sample);
    }
    
    /// Unload sample from a clip slot
    pub fn unload_sample(&mut self, track_idx: usize, clip_idx: usize) {
        self.clip_samples.remove(&(track_idx, clip_idx));
    }
    
    /// Check if a clip has a sample loaded
    pub fn has_sample(&self, track_idx: usize, clip_idx: usize) -> bool {
        self.clip_samples.contains_key(&(track_idx, clip_idx))
    }
    
    /// Get loaded sample count
    pub fn loaded_sample_count(&self) -> usize {
        self.clip_samples.len()
    }
    
    /// Process audio for tracks based on clip player state
    /// Returns the number of tracks actively playing
    pub fn process(
        &mut self,
        clip_player: &ClipPlayer,
        output_buffer: &mut [f32],
        num_frames: usize,
        num_channels: usize,
    ) -> usize {
        // Ensure mix buffer is large enough
        if self.mix_buffer.len() < num_frames * num_channels {
            self.mix_buffer.resize(num_frames * num_channels, 0.0f32);
        }
        
        // Clear output buffer
        output_buffer.fill(0.0f32);
        
        let mut active_tracks = 0;
        
        // Process each track
        for track_idx in 0..self.track_players.len() {
            if self.process_track(clip_player, track_idx, num_frames, num_channels) {
                active_tracks += 1;
            }
            
            // Mix track output to main output
            self.mix_track_to_output(track_idx, output_buffer, num_frames, num_channels);
        }
        
        active_tracks
    }
    
    /// Process a single track based on clip player state
    fn process_track(
        &mut self,
        clip_player: &ClipPlayer,
        track_idx: usize,
        num_frames: usize,
        num_channels: usize,
    ) -> bool {
        // Check if track is playing
        if !clip_player.is_track_playing(track_idx) {
            // Clear sample player if it was active
            if let Some(player) = self.track_players[track_idx].as_mut() {
                player.stop();
            }
            return false;
        }
        
        // Get the currently playing clip
        let Some(playing_clip) = clip_player.get_playing_clip(track_idx) else {
            return false;
        };
        
        // Check if we need to load a new sample
        let current_sample = self.active_samples.get(&track_idx).copied();
        let needs_load = current_sample.map_or(true, |s| s != playing_clip);
        
        if needs_load {
            // Load sample for this clip
            if let Some(sample) = self.clip_samples.get(&(track_idx, playing_clip)) {
                let player = SamplePlayer::new(sample.clone(), num_channels as u16);
                self.track_players[track_idx] = Some(player);
                self.active_samples.insert(track_idx, playing_clip);
            } else {
                // No sample loaded for this clip
                self.track_players[track_idx] = None;
                self.active_samples.remove(&track_idx);
                return false;
            }
        }
        
        // Process audio from sample player
        if let Some(player) = self.track_players[track_idx].as_mut() {
            let track_buffer_start = track_idx * num_frames * num_channels;
            let track_buffer_end = track_buffer_start + num_frames * num_channels;
            
            if self.mix_buffer.len() < track_buffer_end {
                self.mix_buffer.resize(track_buffer_end, 0.0f32);
            }
            
            let track_buffer = &mut self.mix_buffer[track_buffer_start..track_buffer_end];
            // Start playback if not already playing
            if !player.is_playing() {
                player.play();
            }
            player.process(track_buffer);
            true
        } else {
            false
        }
    }
    
    /// Mix track audio to main output
    fn mix_track_to_output(
        &self,
        track_idx: usize,
        output_buffer: &mut [f32],
        num_frames: usize,
        num_channels: usize,
    ) {
        let track_buffer_start = track_idx * num_frames * num_channels;
        let track_buffer_end = track_buffer_start + num_frames * num_channels;
        
        if track_buffer_end > self.mix_buffer.len() {
            return;
        }
        
        let track_buffer = &self.mix_buffer[track_buffer_start..track_buffer_end];
        
        // Simple mix: add track to output
        for (out, track) in output_buffer.iter_mut().zip(track_buffer.iter()) {
            *out += *track;
        }
    }
    
    /// Clear all loaded samples
    pub fn clear_all_samples(&mut self) {
        self.clip_samples.clear();
        self.active_samples.clear();
        for player in &mut self.track_players {
            *player = None;
        }
    }
    
    /// Get track count
    pub fn track_count(&self) -> usize {
        self.track_players.len()
    }
    
    /// Check if track has an active sample player
    pub fn is_track_active(&self, track_idx: usize) -> bool {
        track_idx < self.track_players.len() 
            && self.track_players[track_idx].is_some()
    }
    
    /// Stop all tracks
    pub fn stop_all(&mut self) {
        for player in &mut self.track_players {
            if let Some(p) = player.as_mut() {
                p.stop();
            }
        }
    }
}

/// Track output buffer management
#[derive(Debug)]
pub struct TrackOutput {
    /// Track index
    pub track_idx: usize,
    /// Audio buffer
    pub buffer: Vec<f32>,
    /// Number of frames in buffer
    pub num_frames: usize,
    /// Number of channels
    pub num_channels: usize,
}

impl TrackOutput {
    /// Create new track output
    pub fn new(track_idx: usize, num_frames: usize, num_channels: usize) -> Self {
        Self {
            track_idx,
            buffer: vec![0.0f32; num_frames * num_channels],
            num_frames,
            num_channels,
        }
    }
    
    /// Clear buffer
    pub fn clear(&mut self) {
        self.buffer.fill(0.0f32);
    }
    
    /// Get sample at frame and channel
    pub fn get_sample(&self, frame: usize, channel: usize) -> f32 {
        let idx = frame * self.num_channels + channel;
        self.buffer.get(idx).copied().unwrap_or(0.0f32)
    }
    
    /// Set sample at frame and channel
    pub fn set_sample(&mut self, frame: usize, channel: usize, value: f32) {
        let idx = frame * self.num_channels + channel;
        if let Some(slot) = self.buffer.get_mut(idx) {
            *slot = value;
        }
    }
}

/// Audio routing configuration
#[derive(Debug, Clone)]
pub struct AudioRouting {
    /// Track to output channel mapping
    pub track_to_output: Vec<Vec<usize>>,
    /// Track volume/gain
    pub track_gain: Vec<f32>,
    /// Master output gain
    pub master_gain: f32,
}

impl Default for AudioRouting {
    fn default() -> Self {
        Self {
            track_to_output: Vec::new(),
            track_gain: Vec::new(),
            master_gain: 1.0f32,
        }
    }
}

impl AudioRouting {
    /// Create default routing for N tracks to stereo output
    pub fn stereo_default(track_count: usize) -> Self {
        let mut track_to_output = Vec::with_capacity(track_count);
        let mut track_gain = Vec::with_capacity(track_count);
        
        for _ in 0..track_count {
            // Each track routes to both stereo channels
            track_to_output.push(vec![0, 1]);
            track_gain.push(1.0f32);
        }
        
        Self {
            track_to_output,
            track_gain,
            master_gain: 1.0f32,
        }
    }
    
    /// Set gain for a track
    pub fn set_track_gain(&mut self, track_idx: usize, gain: f32) {
        if track_idx < self.track_gain.len() {
            self.track_gain[track_idx] = gain;
        }
    }
    
    /// Get track gain
    pub fn track_gain(&self, track_idx: usize) -> f32 {
        self.track_gain.get(track_idx).copied().unwrap_or(1.0f32)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_sample() -> Sample {
        // Create a simple test sample with 1000 frames, stereo
        let data = vec![0.0f32; 2000];
        Sample::new(data, 2, 48000)
    }

    #[test]
    fn test_integration_creation() {
        let integration = SamplePlayerIntegration::new(8);
        
        assert_eq!(integration.track_count(), 8);
        assert_eq!(integration.loaded_sample_count(), 0);
    }

    #[test]
    fn test_load_sample() {
        let mut integration = SamplePlayerIntegration::new(4);
        let sample = create_test_sample();
        
        integration.load_sample(0, 0, sample);
        assert_eq!(integration.loaded_sample_count(), 1);
        assert!(integration.has_sample(0, 0));
        assert!(!integration.has_sample(0, 1));
    }

    #[test]
    fn test_unload_sample() {
        let mut integration = SamplePlayerIntegration::new(4);
        let sample = create_test_sample();
        
        integration.load_sample(0, 0, sample);
        assert_eq!(integration.loaded_sample_count(), 1);
        
        integration.unload_sample(0, 0);
        assert_eq!(integration.loaded_sample_count(), 0);
        assert!(!integration.has_sample(0, 0));
    }

    #[test]
    fn test_clear_all_samples() {
        let mut integration = SamplePlayerIntegration::new(4);
        let sample = create_test_sample();
        
        integration.load_sample(0, 0, sample.clone());
        integration.load_sample(1, 2, sample.clone());
        integration.load_sample(2, 1, sample);
        assert_eq!(integration.loaded_sample_count(), 3);
        
        integration.clear_all_samples();
        assert_eq!(integration.loaded_sample_count(), 0);
    }

    #[test]
    fn test_track_output_creation() {
        let output = TrackOutput::new(0, 512, 2);
        
        assert_eq!(output.track_idx, 0);
        assert_eq!(output.num_frames, 512);
        assert_eq!(output.num_channels, 2);
        assert_eq!(output.buffer.len(), 1024);
    }

    #[test]
    fn test_track_output_clear() {
        let mut output = TrackOutput::new(0, 512, 2);
        output.buffer.fill(1.0f32);
        
        output.clear();
        
        assert!(output.buffer.iter().all(|&s| s == 0.0f32));
    }

    #[test]
    fn test_track_output_get_set_sample() {
        let mut output = TrackOutput::new(0, 512, 2);
        
        output.set_sample(100, 0, 0.5f32);
        output.set_sample(100, 1, 0.75f32);
        
        assert_eq!(output.get_sample(100, 0), 0.5f32);
        assert_eq!(output.get_sample(100, 1), 0.75f32);
    }

    #[test]
    fn test_audio_routing_default() {
        let routing = AudioRouting::default();
        
        assert_eq!(routing.master_gain, 1.0f32);
        assert!(routing.track_to_output.is_empty());
    }

    #[test]
    fn test_audio_routing_stereo_default() {
        let routing = AudioRouting::stereo_default(8);
        
        assert_eq!(routing.track_to_output.len(), 8);
        assert_eq!(routing.track_gain.len(), 8);
        
        // Each track should route to stereo channels 0 and 1
        for track_routing in &routing.track_to_output {
            assert_eq!(track_routing, &vec![0, 1]);
        }
    }

    #[test]
    fn test_audio_routing_track_gain() {
        let mut routing = AudioRouting::stereo_default(4);
        
        assert_eq!(routing.track_gain(0), 1.0f32);
        
        routing.set_track_gain(0, 0.5f32);
        assert_eq!(routing.track_gain(0), 0.5f32);
    }

    #[test]
    fn test_stop_all() {
        let mut integration = SamplePlayerIntegration::new(4);
        
        // Stop all shouldn't panic even with no active players
        integration.stop_all();
    }

    #[test]
    fn test_process_with_no_active_clips() {
        let mut integration = SamplePlayerIntegration::new(4);
        let clip_player = ClipPlayer::new(4, 4);
        
        let mut output = vec![0.0f32; 1024]; // 512 frames * 2 channels
        let active = integration.process(&clip_player, &mut output, 512, 2);
        
        assert_eq!(active, 0);
        // Output should be silent
        assert!(output.iter().all(|&s| s == 0.0f32));
    }

    #[test]
    fn test_process_buffer_sizes() {
        let mut integration = SamplePlayerIntegration::new(4);
        let clip_player = ClipPlayer::new(4, 4);
        
        // Test with different buffer sizes
        let sizes = vec![64, 128, 256, 512, 1024];
        
        for size in sizes {
            let mut output = vec![0.0f32; size * 2];
            let _ = integration.process(&clip_player, &mut output, size, 2);
        }
    }
}
