//! Tempo automation track for defining tempo changes throughout the project
//!
//! Provides:
//! - Breakpoint-based tempo curves with multiple interpolation types
//! - Linear, exponential, step, and smooth interpolation
//! - Tempo queries at any beat position
//! - Tempo change management (add, remove, modify breakpoints)

use std::collections::BTreeMap;

/// Interpolation type for tempo changes
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InterpolationType {
    /// Instant change at the breakpoint (step)
    Step,
    /// Linear interpolation between breakpoints
    Linear,
    /// Exponential interpolation (smooth acceleration/deceleration)
    Exponential,
    /// Smooth interpolation (sigmoid curve)
    Smooth,
}

impl InterpolationType {
    /// Get the interpolation type as a string
    pub fn as_str(&self) -> &'static str {
        match self {
            InterpolationType::Step => "step",
            InterpolationType::Linear => "linear",
            InterpolationType::Exponential => "exponential",
            InterpolationType::Smooth => "smooth",
        }
    }

    /// Parse interpolation type from string
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "step" => Some(InterpolationType::Step),
            "linear" => Some(InterpolationType::Linear),
            "exponential" | "exp" => Some(InterpolationType::Exponential),
            "smooth" | "sigmoid" => Some(InterpolationType::Smooth),
            _ => None,
        }
    }
}

impl Default for InterpolationType {
    fn default() -> Self {
        InterpolationType::Linear
    }
}

/// A tempo breakpoint at a specific beat position
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TempoBreakpoint {
    /// Beat position where this breakpoint occurs
    pub beat: f64,
    /// Tempo in BPM at this breakpoint
    pub bpm: f64,
    /// How to interpolate from this breakpoint to the next
    pub interpolation: InterpolationType,
}

impl TempoBreakpoint {
    /// Create a new tempo breakpoint
    pub fn new(beat: f64, bpm: f64, interpolation: InterpolationType) -> Self {
        Self {
            beat: beat.max(0.0),
            bpm: bpm.max(1.0).min(999.0),
            interpolation,
        }
    }

    /// Create with linear interpolation (default)
    pub fn new_linear(beat: f64, bpm: f64) -> Self {
        Self::new(beat, bpm, InterpolationType::Linear)
    }
}

impl Default for TempoBreakpoint {
    fn default() -> Self {
        Self::new(0.0, 120.0, InterpolationType::Linear)
    }
}

/// Tempo automation track managing tempo changes throughout the project
#[derive(Debug, Clone)]
pub struct TempoAutomationTrack {
    /// Map of beat positions to tempo breakpoints
    /// Always contains at least one entry (default tempo at beat 0)
    breakpoints: BTreeMap<u64, TempoBreakpoint>,
    /// Default tempo if no breakpoints exist
    default_bpm: f64,
}

// Use scaled beat values for precise BTreeMap keys (0.001 beat resolution)
fn beat_to_key(beat: f64) -> u64 {
    (beat * 1000.0) as u64
}

fn key_to_beat(key: u64) -> f64 {
    key as f64 / 1000.0
}

impl TempoAutomationTrack {
    /// Create a new tempo automation track with default tempo
    pub fn new(default_bpm: f64) -> Self {
        let mut breakpoints = BTreeMap::new();
        let initial = TempoBreakpoint::new(0.0, default_bpm, InterpolationType::Linear);
        breakpoints.insert(0, initial);
        Self {
            breakpoints,
            default_bpm: default_bpm.max(1.0).min(999.0),
        }
    }

    /// Create with standard 120 BPM default
    pub fn default_tempo() -> Self {
        Self::new(120.0)
    }

    /// Reset to single breakpoint at beat 0
    pub fn reset(&mut self, bpm: f64) {
        self.breakpoints.clear();
        let initial = TempoBreakpoint::new(0.0, bpm, InterpolationType::Linear);
        self.breakpoints.insert(0, initial);
        self.default_bpm = bpm;
    }

    /// Add a tempo breakpoint at the specified beat
    /// If a breakpoint already exists at this beat, it will be replaced
    pub fn add_breakpoint(&mut self, beat: f64, bpm: f64, interpolation: InterpolationType) {
        if beat < 0.0 {
            return;
        }
        let breakpoint = TempoBreakpoint::new(beat, bpm, interpolation);
        let key = beat_to_key(beat);
        self.breakpoints.insert(key, breakpoint);
    }

    /// Add with linear interpolation (convenience method)
    pub fn add_linear(&mut self, beat: f64, bpm: f64) {
        self.add_breakpoint(beat, bpm, InterpolationType::Linear);
    }

    /// Remove a breakpoint at the specified beat
    /// Cannot remove beat 0 (must always have at least one breakpoint)
    pub fn remove_breakpoint(&mut self, beat: f64) -> bool {
        let key = beat_to_key(beat);
        if key == 0 {
            return false; // Can't remove the initial breakpoint
        }
        self.breakpoints.remove(&key).is_some()
    }

    /// Get the number of breakpoints
    pub fn breakpoint_count(&self) -> usize {
        self.breakpoints.len()
    }

    /// Get a breakpoint by index (0 = first, sorted by beat)
    pub fn get_breakpoint_at(&self, index: usize) -> Option<TempoBreakpoint> {
        self.breakpoints.values().nth(index).copied()
    }

    /// Get the breakpoint at a specific beat
    pub fn get_breakpoint_at_beat(&self, beat: f64) -> Option<TempoBreakpoint> {
        let key = beat_to_key(beat);
        self.breakpoints.get(&key).copied()
    }

    /// Get all breakpoints as a vector
    pub fn get_all_breakpoints(&self) -> Vec<TempoBreakpoint> {
        self.breakpoints.values().copied().collect()
    }

    /// Get the tempo at a specific beat position
    /// Uses interpolation between breakpoints based on their interpolation type
    pub fn get_tempo_at_beat(&self, beat: f64) -> f64 {
        if beat < 0.0 {
            return self.default_bpm;
        }

        let key = beat_to_key(beat);

        // Find the breakpoint at or before this beat
        let before = self.breakpoints.range(..=key).next_back();
        let after = self.breakpoints.range((key + 1)..).next();

        match (before, after) {
            (Some((_, &bp)), None) => bp.bpm,
            (Some((&k_before, &bp_before)), Some((&k_after, &bp_after))) => {
                let beat_before = key_to_beat(k_before);
                let beat_after = key_to_beat(k_after);

                if beat >= beat_after {
                    return bp_after.bpm;
                }

                // Calculate interpolation factor (0.0 = at before, 1.0 = at after)
                let t = if beat_after > beat_before {
                    (beat - beat_before) / (beat_after - beat_before)
                } else {
                    0.0
                };

                // Use the interpolation type from bp_after (how we arrived at this breakpoint)
                match bp_after.interpolation {
                    InterpolationType::Step => bp_before.bpm, // Hold value until step point
                    InterpolationType::Linear => {
                        bp_before.bpm + (bp_after.bpm - bp_before.bpm) * t
                    }
                    InterpolationType::Exponential => {
                        let ratio = bp_after.bpm / bp_before.bpm.max(0.001);
                        bp_before.bpm * ratio.powf(t)
                    }
                    InterpolationType::Smooth => {
                        // Smoothstep function: 3t^2 - 2t^3
                        let smooth_t = t * t * (3.0 - 2.0 * t);
                        bp_before.bpm + (bp_after.bpm - bp_before.bpm) * smooth_t
                    }
                }
            }
            _ => self.default_bpm,
        }
    }

    /// Get the average tempo over a range of beats
    pub fn get_average_tempo(&self, start_beat: f64, end_beat: f64) -> f64 {
        if start_beat >= end_beat {
            return self.get_tempo_at_beat(start_beat);
        }

        // Sample at multiple points and average
        let samples = 10;
        let step = (end_beat - start_beat) / samples as f64;
        let mut total = 0.0;

        for i in 0..samples {
            let beat = start_beat + step * i as f64;
            total += self.get_tempo_at_beat(beat);
        }

        total / samples as f64
    }

    /// Get time in seconds for a beat range at the current tempo
    /// This accounts for tempo automation
    pub fn beats_to_seconds(&self, start_beat: f64, end_beat: f64) -> f64 {
        if start_beat >= end_beat {
            return 0.0;
        }

        // Numerical integration of tempo over the beat range
        // time = integral(60/tempo(beat)) dbeat
        let samples = 100;
        let step = (end_beat - start_beat) / samples as f64;
        let mut total_time = 0.0;

        for i in 0..samples {
            let beat = start_beat + step * (i as f64 + 0.5);
            let tempo = self.get_tempo_at_beat(beat);
            if tempo > 0.0 {
                total_time += (60.0 / tempo) * step;
            }
        }

        total_time
    }

    /// Find the nearest breakpoint to a given beat position
    pub fn find_nearest_breakpoint(&self, beat: f64) -> Option<TempoBreakpoint> {
        let key = beat_to_key(beat);

        let before = self.breakpoints.range(..=key).next_back();
        let after = self.breakpoints.range((key + 1)..).next();

        match (before, after) {
            (Some((&k_before, &bp_before)), Some((&k_after, &bp_after))) => {
                let beat_before = key_to_beat(k_before);
                let beat_after = key_to_beat(k_after);

                if (beat - beat_before).abs() <= (beat_after - beat).abs() {
                    Some(bp_before)
                } else {
                    Some(bp_after)
                }
            }
            (Some((_, &bp)), None) | (None, Some((_, &bp))) => Some(bp),
            _ => None,
        }
    }
}

impl Default for TempoAutomationTrack {
    fn default() -> Self {
        Self::default_tempo()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tempo_track_creation() {
        let track = TempoAutomationTrack::new(120.0);
        assert_eq!(track.breakpoint_count(), 1);
        assert_eq!(track.get_tempo_at_beat(0.0), 120.0);
    }

    #[test]
    fn test_default_tempo() {
        let track = TempoAutomationTrack::default_tempo();
        assert_eq!(track.get_tempo_at_beat(0.0), 120.0);
        assert_eq!(track.get_tempo_at_beat(100.0), 120.0);
    }

    #[test]
    fn test_add_breakpoint() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);

        assert_eq!(track.breakpoint_count(), 2);
        assert_eq!(track.get_tempo_at_beat(0.0), 120.0);
        assert_eq!(track.get_tempo_at_beat(4.0), 140.0);
    }

    #[test]
    fn test_linear_interpolation() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);

        // At midpoint, should be 130 BPM
        let tempo = track.get_tempo_at_beat(2.0);
        assert!((tempo - 130.0).abs() < 0.01, "Expected ~130, got {}", tempo);
    }

    #[test]
    fn test_step_interpolation() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_breakpoint(4.0, 140.0, InterpolationType::Step);

        // Well before step point, should be 120
        assert!((track.get_tempo_at_beat(2.0) - 120.0).abs() < 0.1);
        // At step point, should be 140
        assert_eq!(track.get_tempo_at_beat(4.0), 140.0);
        // After step point, should be 140
        assert_eq!(track.get_tempo_at_beat(5.0), 140.0);
    }

    #[test]
    fn test_exponential_interpolation() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_breakpoint(4.0, 160.0, InterpolationType::Exponential);

        let tempo = track.get_tempo_at_beat(2.0);
        // Exponential: at midpoint should be geometric mean sqrt(120 * 160) = 138.56
        // But due to our implementation, it may be slightly different
        assert!(tempo > 120.0 && tempo < 160.0, "Expected 120-160, got {}", tempo);
        // Should be closer to geometric mean than linear (130)
        assert!(tempo > 135.0, "Expected > 135, got {}", tempo);
    }

    #[test]
    fn test_smooth_interpolation() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_breakpoint(4.0, 140.0, InterpolationType::Smooth);

        let tempo = track.get_tempo_at_beat(2.0);
        // Smoothstep gives 0.5 at midpoint, so should be 130
        assert!((tempo - 130.0).abs() < 0.1, "Expected ~130, got {}", tempo);
    }

    #[test]
    fn test_remove_breakpoint() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);
        track.add_linear(8.0, 160.0);

        assert_eq!(track.breakpoint_count(), 3);

        // Can't remove beat 0
        assert!(!track.remove_breakpoint(0.0));
        assert_eq!(track.breakpoint_count(), 3);

        // Can remove other breakpoints
        assert!(track.remove_breakpoint(4.0));
        assert_eq!(track.breakpoint_count(), 2);
    }

    #[test]
    fn test_get_breakpoint_at() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);
        track.add_linear(8.0, 160.0);

        let bp0 = track.get_breakpoint_at(0).unwrap();
        assert_eq!(bp0.bpm, 120.0);
        assert_eq!(bp0.beat, 0.0);

        let bp1 = track.get_breakpoint_at(1).unwrap();
        assert_eq!(bp1.bpm, 140.0);
        assert_eq!(bp1.beat, 4.0);
    }

    #[test]
    fn test_get_all_breakpoints() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);

        let bps = track.get_all_breakpoints();
        assert_eq!(bps.len(), 2);
        assert_eq!(bps[0].bpm, 120.0);
        assert_eq!(bps[1].bpm, 140.0);
    }

    #[test]
    fn test_tempo_clamping() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 1000.0); // Should be clamped to 999
        track.add_linear(8.0, 0.5);      // Should be clamped to 1.0

        assert_eq!(track.get_tempo_at_beat(4.0), 999.0);
        assert_eq!(track.get_tempo_at_beat(8.0), 1.0);
    }

    #[test]
    fn test_average_tempo() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);

        let avg = track.get_average_tempo(0.0, 4.0);
        assert!((avg - 130.0).abs() < 2.0, "Expected ~130, got {}", avg);
    }

    #[test]
    fn test_beats_to_seconds() {
        let track = TempoAutomationTrack::new(60.0); // 1 beat per second

        let seconds = track.beats_to_seconds(0.0, 4.0);
        assert!((seconds - 4.0).abs() < 0.1, "Expected ~4s, got {}", seconds);
    }

    #[test]
    fn test_find_nearest_breakpoint() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);

        let nearest = track.find_nearest_breakpoint(1.0).unwrap();
        assert_eq!(nearest.beat, 0.0);

        let nearest = track.find_nearest_breakpoint(3.0).unwrap();
        assert_eq!(nearest.beat, 4.0);
    }

    #[test]
    fn test_reset() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);
        track.add_linear(8.0, 160.0);

        track.reset(100.0);

        assert_eq!(track.breakpoint_count(), 1);
        assert_eq!(track.get_tempo_at_beat(0.0), 100.0);
    }

    #[test]
    fn test_interpolation_type_from_str() {
        assert_eq!(InterpolationType::from_str("linear"), Some(InterpolationType::Linear));
        assert_eq!(InterpolationType::from_str("step"), Some(InterpolationType::Step));
        assert_eq!(InterpolationType::from_str("exponential"), Some(InterpolationType::Exponential));
        assert_eq!(InterpolationType::from_str("smooth"), Some(InterpolationType::Smooth));
        assert_eq!(InterpolationType::from_str("exp"), Some(InterpolationType::Exponential));
        assert_eq!(InterpolationType::from_str("unknown"), None);
    }

    #[test]
    fn test_negative_beat_handling() {
        let track = TempoAutomationTrack::new(120.0);
        assert_eq!(track.get_tempo_at_beat(-10.0), 120.0);
    }

    #[test]
    fn test_multiple_breakpoints() {
        let mut track = TempoAutomationTrack::new(120.0);
        track.add_linear(4.0, 140.0);
        track.add_linear(8.0, 100.0);
        track.add_linear(12.0, 160.0);

        assert_eq!(track.breakpoint_count(), 4);

        // Check interpolation between second and third
        let tempo = track.get_tempo_at_beat(6.0); // Between 140 and 100
        assert!(tempo > 110.0 && tempo < 130.0, "Expected ~120, got {}", tempo);
    }
}
