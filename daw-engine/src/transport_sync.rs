//! Transport Sync - Sample-accurate clip triggering with transport beat clock
//!
//! Synchronizes clip playback to the transport's beat clock for
//! sample-accurate triggering and quantization.

use crate::{profile_scope, plot_value};
use std::collections::VecDeque;

/// Scheduled clip event for quantized playback
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ScheduledClip {
    /// Track index
    pub track_idx: usize,
    /// Clip index within track
    pub clip_idx: usize,
    /// Target beat to trigger on
    pub target_beat: f64,
    /// Whether this is a one-shot or looped trigger
    pub looped: bool,
}

/// Beat quantization settings
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Quantization {
    /// No quantization - immediate trigger
    Immediate,
    /// Quantize to next beat
    Beat,
    /// Quantize to next bar (4 beats)
    Bar,
    /// Quantize to 8th note
    Eighth,
    /// Quantize to 16th note
    Sixteenth,
}

impl Quantization {
    /// Get beat interval for this quantization
    pub fn beat_interval(&self) -> f64 {
        match self {
            Quantization::Immediate => 0.0,
            Quantization::Beat => 1.0,
            Quantization::Bar => 4.0,
            Quantization::Eighth => 0.5,
            Quantization::Sixteenth => 0.25,
        }
    }
    
    /// Quantize a beat position to the grid
    pub fn quantize(&self, beat: f64, direction: QuantizeDirection) -> f64 {
        if matches!(self, Quantization::Immediate) {
            return beat;
        }
        
        let interval = self.beat_interval();
        let grid_pos = beat / interval;
        
        match direction {
            QuantizeDirection::Up => grid_pos.ceil() * interval,
            QuantizeDirection::Down => grid_pos.floor() * interval,
            QuantizeDirection::Nearest => grid_pos.round() * interval,
        }
    }
}

/// Direction for quantization
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum QuantizeDirection {
    /// Round up (next grid point)
    Up,
    /// Round down (previous grid point)
    Down,
    /// Round to nearest
    Nearest,
}

/// Transport synchronization manager
#[derive(Debug)]
pub struct TransportSync {
    /// Pending scheduled clips
    pending: VecDeque<ScheduledClip>,
    /// Default quantization
    default_quantization: Quantization,
    /// Sample rate for timing calculations
    sample_rate: f32,
    /// Current tempo in BPM
    tempo: f32,
    /// Samples per beat at current tempo
    samples_per_beat: f64,
}

impl TransportSync {
    /// Create new transport sync manager
    pub fn new(sample_rate: f32, tempo: f32) -> Self {
        let samples_per_beat = Self::calculate_samples_per_beat(sample_rate, tempo);
        
        Self {
            pending: VecDeque::new(),
            default_quantization: Quantization::Beat,
            sample_rate,
            tempo,
            samples_per_beat,
        }
    }
    
    /// Calculate samples per beat from tempo and sample rate
    fn calculate_samples_per_beat(sample_rate: f32, tempo: f32) -> f64 {
        let seconds_per_beat = 60.0 / tempo as f64;
        (sample_rate as f64) * seconds_per_beat
    }
    
    /// Update tempo (recalculates timing)
    pub fn set_tempo(&mut self, tempo: f32) {
        profile_scope!("sync_set_tempo");
        self.tempo = tempo;
        self.samples_per_beat = Self::calculate_samples_per_beat(self.sample_rate, tempo);
        plot_value!("samples_per_beat", self.samples_per_beat);
    }
    
    /// Get current tempo
    pub fn tempo(&self) -> f32 {
        self.tempo
    }
    
    /// Get samples per beat
    pub fn samples_per_beat(&self) -> f64 {
        self.samples_per_beat
    }
    
    /// Set default quantization
    pub fn set_quantization(&mut self, quantization: Quantization) {
        self.default_quantization = quantization;
    }
    
    /// Get default quantization
    pub fn quantization(&self) -> Quantization {
        self.default_quantization
    }
    
    /// Schedule a clip to trigger at a specific beat
    pub fn schedule_clip(&mut self, track_idx: usize, clip_idx: usize, target_beat: f64, looped: bool) {
        profile_scope!("sync_schedule");
        let scheduled = ScheduledClip {
            track_idx,
            clip_idx,
            target_beat,
            looped,
        };
        self.pending.push_back(scheduled);
        plot_value!("pending_clips", self.pending.len() as f64);
    }
    
    /// Schedule a clip with quantization applied to current transport position
    pub fn schedule_clip_quantized(
        &mut self,
        track_idx: usize,
        clip_idx: usize,
        current_beat: f64,
        quantization: Quantization,
        looped: bool,
    ) {
        let target_beat = quantization.quantize(current_beat, QuantizeDirection::Up);
        self.schedule_clip(track_idx, clip_idx, target_beat, looped);
    }
    
    /// Cancel all pending clips for a track
    pub fn cancel_track(&mut self, track_idx: usize) {
        self.pending.retain(|s| s.track_idx != track_idx);
    }
    
    /// Cancel a specific scheduled clip
    pub fn cancel_clip(&mut self, track_idx: usize, clip_idx: usize) {
        self.pending.retain(|s| !(s.track_idx == track_idx && s.clip_idx == clip_idx));
    }
    
    /// Clear all pending scheduled clips
    pub fn clear_all(&mut self) {
        profile_scope!("sync_clear_all");
        self.pending.clear();
        plot_value!("pending_clips", 0.0);
    }
    
    /// Get number of pending scheduled clips
    pub fn pending_count(&self) -> usize {
        self.pending.len()
    }
    
    /// Calculate sample position for a beat
    pub fn beat_to_sample(&self, beat: f64, start_sample: u64) -> u64 {
        start_sample + (beat * self.samples_per_beat) as u64
    }
    
    /// Calculate beat position from sample
    pub fn sample_to_beat(&self, sample: u64, start_sample: u64) -> f64 {
        let samples_elapsed = sample.saturating_sub(start_sample) as f64;
        samples_elapsed / self.samples_per_beat
    }
    
    /// Process scheduled clips at current beat position
    /// Returns vector of clips that should trigger now
    pub fn process(&mut self, current_beat: f64) -> Vec<ScheduledClip> {
        profile_scope!("sync_process");
        let mut triggered = Vec::new();
        
        // Find clips that should trigger (target beat <= current beat)
        while let Some(clip) = self.pending.front() {
            if clip.target_beat <= current_beat {
                triggered.push(*clip);
                self.pending.pop_front();
            } else {
                break;
            }
        }
        
        plot_value!("pending_clips", self.pending.len() as f64);
        plot_value!("triggered_clips", triggered.len() as f64);
        
        triggered
    }
    
    /// Check if any clip is scheduled for a specific track
    pub fn is_track_scheduled(&self, track_idx: usize) -> bool {
        self.pending.iter().any(|s| s.track_idx == track_idx)
    }
    
    /// Get next scheduled beat for a track (if any)
    pub fn next_scheduled_beat(&self, track_idx: usize) -> Option<f64> {
        self.pending
            .iter()
            .filter(|s| s.track_idx == track_idx)
            .map(|s| s.target_beat)
            .min_by(|a, b| a.partial_cmp(b).unwrap())
    }
    
    /// Get beats until next scheduled event for a track
    pub fn beats_until_next(&self, track_idx: usize, current_beat: f64) -> Option<f64> {
        self.next_scheduled_beat(track_idx)
            .map(|target| target - current_beat)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_transport_sync_creation() {
        let sync = TransportSync::new(48000.0, 120.0);
        
        assert_eq!(sync.tempo(), 120.0);
        assert_eq!(sync.samples_per_beat(), 24000.0); // 48000 * 0.5 seconds
        assert_eq!(sync.pending_count(), 0);
    }

    #[test]
    fn test_tempo_change() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        assert_eq!(sync.samples_per_beat(), 24000.0);
        
        sync.set_tempo(60.0);
        assert_eq!(sync.tempo(), 60.0);
        assert_eq!(sync.samples_per_beat(), 48000.0); // Slower tempo = more samples per beat
    }

    #[test]
    fn test_quantization_intervals() {
        assert_eq!(Quantization::Immediate.beat_interval(), 0.0);
        assert_eq!(Quantization::Beat.beat_interval(), 1.0);
        assert_eq!(Quantization::Bar.beat_interval(), 4.0);
        assert_eq!(Quantization::Eighth.beat_interval(), 0.5);
        assert_eq!(Quantization::Sixteenth.beat_interval(), 0.25);
    }

    #[test]
    fn test_quantize_up() {
        let beat = Quantization::Beat.quantize(1.5, QuantizeDirection::Up);
        assert_eq!(beat, 2.0);
        
        let bar = Quantization::Bar.quantize(3.0, QuantizeDirection::Up);
        assert_eq!(bar, 4.0);
        
        let eighth = Quantization::Eighth.quantize(1.3, QuantizeDirection::Up);
        assert_eq!(eighth, 1.5);
    }

    #[test]
    fn test_quantize_down() {
        let beat = Quantization::Beat.quantize(1.5, QuantizeDirection::Down);
        assert_eq!(beat, 1.0);
        
        let bar = Quantization::Bar.quantize(5.0, QuantizeDirection::Down);
        assert_eq!(bar, 4.0);
    }

    #[test]
    fn test_quantize_nearest() {
        let beat1 = Quantization::Beat.quantize(1.4, QuantizeDirection::Nearest);
        assert_eq!(beat1, 1.0);
        
        let beat2 = Quantization::Beat.quantize(1.6, QuantizeDirection::Nearest);
        assert_eq!(beat2, 2.0);
    }

    #[test]
    fn test_schedule_clip() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        sync.schedule_clip(0, 2, 4.0, false);
        assert_eq!(sync.pending_count(), 1);
        
        sync.schedule_clip(1, 3, 8.0, true);
        assert_eq!(sync.pending_count(), 2);
    }

    #[test]
    fn test_schedule_clip_quantized() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        // At beat 1.5, quantize to next beat = 2.0
        sync.schedule_clip_quantized(0, 0, 1.5, Quantization::Beat, false);
        
        // Process at beat 2.0 - should trigger
        let triggered = sync.process(2.0);
        assert_eq!(triggered.len(), 1);
        assert_eq!(triggered[0].target_beat, 2.0);
    }

    #[test]
    fn test_process_triggers_at_beat() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        sync.schedule_clip(0, 0, 4.0, false);
        sync.schedule_clip(1, 2, 4.0, false);
        
        // Process at beat 3.0 - nothing should trigger
        let triggered = sync.process(3.0);
        assert_eq!(triggered.len(), 0);
        assert_eq!(sync.pending_count(), 2);
        
        // Process at beat 4.0 - both should trigger
        let triggered = sync.process(4.0);
        assert_eq!(triggered.len(), 2);
        assert_eq!(sync.pending_count(), 0);
    }

    #[test]
    fn test_cancel_track() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        sync.schedule_clip(0, 0, 4.0, false);
        sync.schedule_clip(0, 1, 8.0, false);
        sync.schedule_clip(1, 0, 4.0, false);
        assert_eq!(sync.pending_count(), 3);
        
        sync.cancel_track(0);
        assert_eq!(sync.pending_count(), 1); // Only track 1 remains
    }

    #[test]
    fn test_cancel_clip() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        sync.schedule_clip(0, 0, 4.0, false);
        sync.schedule_clip(0, 1, 8.0, false);
        assert_eq!(sync.pending_count(), 2);
        
        sync.cancel_clip(0, 0);
        assert_eq!(sync.pending_count(), 1);
    }

    #[test]
    fn test_clear_all() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        sync.schedule_clip(0, 0, 4.0, false);
        sync.schedule_clip(1, 0, 4.0, false);
        sync.schedule_clip(2, 0, 4.0, false);
        assert_eq!(sync.pending_count(), 3);
        
        sync.clear_all();
        assert_eq!(sync.pending_count(), 0);
    }

    #[test]
    fn test_beat_to_sample() {
        let sync = TransportSync::new(48000.0, 120.0);
        // At 120 BPM, 1 beat = 0.5 seconds = 24000 samples
        
        let sample = sync.beat_to_sample(4.0, 0);
        assert_eq!(sample, 96000); // 4 beats * 24000 samples/beat
    }

    #[test]
    fn test_sample_to_beat() {
        let sync = TransportSync::new(48000.0, 120.0);
        
        let beat = sync.sample_to_beat(96000, 0);
        assert_eq!(beat, 4.0);
    }

    #[test]
    fn test_is_track_scheduled() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        assert!(!sync.is_track_scheduled(0));
        
        sync.schedule_clip(0, 0, 4.0, false);
        assert!(sync.is_track_scheduled(0));
        assert!(!sync.is_track_scheduled(1));
    }

    #[test]
    fn test_next_scheduled_beat() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        assert!(sync.next_scheduled_beat(0).is_none());
        
        sync.schedule_clip(0, 0, 8.0, false);
        sync.schedule_clip(0, 1, 4.0, false); // Earlier beat
        
        assert_eq!(sync.next_scheduled_beat(0), Some(4.0));
    }

    #[test]
    fn test_beats_until_next() {
        let mut sync = TransportSync::new(48000.0, 120.0);
        
        sync.schedule_clip(0, 0, 8.0, false);
        
        let beats = sync.beats_until_next(0, 4.0);
        assert_eq!(beats, Some(4.0)); // 8.0 - 4.0 = 4 beats
    }
}
