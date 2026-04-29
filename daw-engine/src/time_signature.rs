//! Time signature track for defining meter changes throughout the project
//!
//! Provides:
//! - Multiple time signature changes at any bar boundary
//! - Beat to bar/beat conversion
//! - Bar/beat to absolute beat conversion
//! - Variable bar lengths based on time signature

use std::collections::BTreeMap;

/// A time signature change at a specific bar
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TimeSignature {
    /// Bar number where this signature takes effect (1-indexed)
    pub bar: u32,
    /// Number of beats per bar (e.g., 4 for 4/4, 3 for 3/4)
    pub numerator: u8,
    /// Beat unit (e.g., 4 = quarter note, 8 = eighth note)
    pub denominator: u8,
}

impl TimeSignature {
    /// Create a new time signature
    pub fn new(bar: u32, numerator: u8, denominator: u8) -> Self {
        Self {
            bar,
            numerator: numerator.max(1),
            denominator: denominator.max(1),
        }
    }

    /// Get the number of beats in one bar with this signature
    /// Note: We always return the numerator as the beat count
    /// (e.g., 6/8 has 6 beats, not 2 dotted-quarter beats)
    pub fn beats_per_bar(&self) -> f64 {
        self.numerator as f64
    }

    /// Get the duration of one beat in whole notes
    /// (e.g., 4/4 beat = 1/4 note, 6/8 beat = 1/8 note)
    pub fn beat_duration_whole_notes(&self) -> f64 {
        1.0 / self.denominator as f64
    }

    /// Format as string (e.g., "4/4", "3/4", "6/8")
    pub fn to_string(&self) -> String {
        format!("{}/{}", self.numerator, self.denominator)
    }
}

impl Default for TimeSignature {
    fn default() -> Self {
        Self::new(1, 4, 4)  // Default 4/4 at bar 1
    }
}

/// Track managing time signature changes throughout the project
#[derive(Debug, Clone)]
pub struct TimeSignatureTrack {
    /// Map of bar numbers to time signatures
    /// Always contains at least one entry (default 4/4 at bar 1)
    changes: BTreeMap<u32, TimeSignature>,
}

impl TimeSignatureTrack {
    /// Create a new time signature track with default 4/4
    pub fn new() -> Self {
        let mut changes = BTreeMap::new();
        changes.insert(1, TimeSignature::default());
        Self { changes }
    }

    /// Add a time signature change at the specified bar
    /// If a change already exists at this bar, it will be replaced
    pub fn add_change(&mut self, bar: u32, numerator: u8, denominator: u8) {
        if bar < 1 {
            return;  // Bar 1 is the minimum
        }
        let signature = TimeSignature::new(bar, numerator, denominator);
        self.changes.insert(bar, signature);
    }

    /// Remove a time signature change at the specified bar
    /// Cannot remove bar 1 (must always have at least one signature)
    pub fn remove_change(&mut self, bar: u32) -> bool {
        if bar <= 1 {
            return false;  // Can't remove the initial signature
        }
        self.changes.remove(&bar).is_some()
    }

    /// Get the time signature in effect at a given bar
    pub fn get_signature_at_bar(&self, bar: u32) -> TimeSignature {
        if bar < 1 {
            return TimeSignature::default();
        }

        // Find the last change at or before this bar
        self.changes
            .range(..=bar)
            .next_back()
            .map(|(_, sig)| *sig)
            .unwrap_or_default()
    }

    /// Get the time signature in effect at a given beat
    pub fn get_signature_at_beat(&self, beat: f64) -> TimeSignature {
        let (bar, _, _) = self.beat_to_bar_beat(beat);
        self.get_signature_at_bar(bar)
    }

    /// Get all time signature changes as a sorted vector
    pub fn all_changes(&self) -> Vec<TimeSignature> {
        self.changes.values().copied().collect()
    }

    /// Get the number of time signature changes
    pub fn change_count(&self) -> usize {
        self.changes.len()
    }

    /// Convert absolute beat to (bar, beat_in_bar, fraction)
    /// Returns (bar, beat_in_bar, fraction) where:
    /// - bar is 1-indexed
    /// - beat_in_bar is 0-indexed (0 to numerator-1)
    /// - fraction is the fractional part of the beat
    pub fn beat_to_bar_beat(&self, beat: f64) -> (u32, u32, f64) {
        if beat < 0.0 {
            return (1, 0, 0.0);
        }

        let mut current_beat = 0.0;
        let mut prev_bar = 1u32;
        let mut prev_sig = self.changes.get(&1).copied().unwrap_or_default();

        // Find which section this beat falls into
        for (&bar, &sig) in &self.changes {
            if bar > 1 {
                // Calculate beats from prev_bar to this bar
                let bars_from_prev = (bar - prev_bar) as f64;
                let beats_from_prev = bars_from_prev * prev_sig.beats_per_bar();

                if current_beat + beats_from_prev > beat {
                    // Found the section
                    let beat_offset = beat - current_beat;
                    let total_bar_offset = (beat_offset / prev_sig.beats_per_bar()).floor() as u32;
                    let bar = prev_bar + total_bar_offset;
                    let beat_in_bar = ((beat_offset % prev_sig.beats_per_bar()).floor() as u32) % prev_sig.numerator as u32;
                    let fraction = beat_offset.fract();
                    return (bar.max(1), beat_in_bar, fraction);
                }

                current_beat += beats_from_prev;
                prev_bar = bar;
                prev_sig = sig;
            }
        }

        // In the last section
        let beat_offset = beat - current_beat;
        let total_bar_offset = (beat_offset / prev_sig.beats_per_bar()).floor() as u32;
        let bar = prev_bar + total_bar_offset;
        let beat_in_bar = ((beat_offset % prev_sig.beats_per_bar()).floor() as u32) % prev_sig.numerator as u32;
        let fraction = beat_offset.fract();

        (bar.max(1), beat_in_bar, fraction)
    }

    /// Convert bar and beat to absolute beat
    /// bar is 1-indexed, beat_in_bar is 0-indexed
    pub fn bar_beat_to_beat(&self, bar: u32, beat_in_bar: u32) -> f64 {
        if bar < 1 {
            return 0.0;
        }

        let mut current_beat = 0.0;
        let mut prev_bar = 1u32;
        let mut prev_sig = self.changes.get(&1).copied().unwrap_or_default();

        // Iterate through changes to find the right section
        for (&change_bar, &sig) in &self.changes {
            if change_bar > 1 && change_bar <= bar {
                let bars_from_prev = (change_bar - prev_bar) as f64;
                current_beat += bars_from_prev * prev_sig.beats_per_bar();
                prev_bar = change_bar;
                prev_sig = sig;
            }
        }

        // Add beats in the final section
        let bars_from_prev = (bar - prev_bar) as f64;
        current_beat += bars_from_prev * prev_sig.beats_per_bar();
        current_beat += beat_in_bar.min(prev_sig.numerator as u32 - 1) as f64;

        current_beat
    }

    /// Get the starting beat of a specific bar
    pub fn get_bar_start_beat(&self, bar: u32) -> f64 {
        self.bar_beat_to_beat(bar, 0)
    }

    /// Get the number of beats in a specific bar
    pub fn get_bar_length(&self, bar: u32) -> f64 {
        self.get_signature_at_bar(bar).beats_per_bar()
    }

    /// Calculate the number of bars between two beat positions
    pub fn beats_to_bars(&self, start_beat: f64, end_beat: f64) -> f64 {
        let (start_bar, _, _) = self.beat_to_bar_beat(start_beat);
        let (end_bar, _, _) = self.beat_to_bar_beat(end_beat);
        (end_bar - start_bar) as f64
    }

    /// Clear all changes and reset to default 4/4
    pub fn reset(&mut self) {
        self.changes.clear();
        self.changes.insert(1, TimeSignature::default());
    }
}

impl Default for TimeSignatureTrack {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_time_signature_creation() {
        let sig = TimeSignature::new(1, 4, 4);
        assert_eq!(sig.bar, 1);
        assert_eq!(sig.numerator, 4);
        assert_eq!(sig.denominator, 4);
        assert_eq!(sig.beats_per_bar(), 4.0);
        assert_eq!(sig.to_string(), "4/4");
    }

    #[test]
    fn test_time_signature_3_4() {
        let sig = TimeSignature::new(1, 3, 4);
        assert_eq!(sig.numerator, 3);
        assert_eq!(sig.beats_per_bar(), 3.0);
        assert_eq!(sig.to_string(), "3/4");
    }

    #[test]
    fn test_time_signature_6_8() {
        let sig = TimeSignature::new(1, 6, 8);
        assert_eq!(sig.numerator, 6);
        assert_eq!(sig.beats_per_bar(), 6.0);
        assert_eq!(sig.to_string(), "6/8");
    }

    #[test]
    fn test_time_signature_track_default() {
        let track = TimeSignatureTrack::new();
        assert_eq!(track.change_count(), 1);

        let sig = track.get_signature_at_bar(1);
        assert_eq!(sig.numerator, 4);
        assert_eq!(sig.denominator, 4);
    }

    #[test]
    fn test_add_change() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);  // 3/4 at bar 5

        assert_eq!(track.change_count(), 2);

        // Before bar 5, should be 4/4
        let sig = track.get_signature_at_bar(4);
        assert_eq!(sig.numerator, 4);

        // At and after bar 5, should be 3/4
        let sig = track.get_signature_at_bar(5);
        assert_eq!(sig.numerator, 3);

        let sig = track.get_signature_at_bar(10);
        assert_eq!(sig.numerator, 3);
    }

    #[test]
    fn test_add_change_replace() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);
        track.add_change(5, 6, 8);  // Replace 3/4 with 6/8 at bar 5

        assert_eq!(track.change_count(), 2);

        let sig = track.get_signature_at_bar(5);
        assert_eq!(sig.numerator, 6);
        assert_eq!(sig.denominator, 8);
    }

    #[test]
    fn test_remove_change() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);
        track.add_change(9, 6, 8);

        assert!(track.remove_change(5));
        assert_eq!(track.change_count(), 2);  // 1 default + 6/8

        // After removing 3/4 at bar 5, bar 5 should use 4/4
        let sig = track.get_signature_at_bar(5);
        assert_eq!(sig.numerator, 4);

        // Bar 9 should still be 6/8
        let sig = track.get_signature_at_bar(9);
        assert_eq!(sig.numerator, 6);
    }

    #[test]
    fn test_cannot_remove_bar_1() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);

        assert!(!track.remove_change(1));  // Should fail
        assert_eq!(track.change_count(), 2);
    }

    #[test]
    fn test_beat_to_bar_beat_4_4() {
        let track = TimeSignatureTrack::new();

        // Beat 0 = bar 1, beat 0
        let (bar, beat, frac) = track.beat_to_bar_beat(0.0);
        assert_eq!(bar, 1);
        assert_eq!(beat, 0);
        assert_eq!(frac, 0.0);

        // Beat 3 = bar 1, beat 3
        let (bar, beat, frac) = track.beat_to_bar_beat(3.0);
        assert_eq!(bar, 1);
        assert_eq!(beat, 3);

        // Beat 4 = bar 2, beat 0
        let (bar, beat, frac) = track.beat_to_bar_beat(4.0);
        assert_eq!(bar, 2);
        assert_eq!(beat, 0);

        // Beat 7 = bar 2, beat 3
        let (bar, beat, frac) = track.beat_to_bar_beat(7.0);
        assert_eq!(bar, 2);
        assert_eq!(beat, 3);

        // Beat 4.5 = bar 2, beat 0, fraction 0.5
        let (bar, beat, frac) = track.beat_to_bar_beat(4.5);
        assert_eq!(bar, 2);
        assert_eq!(beat, 0);
        assert!(frac > 0.49 && frac < 0.51);
    }

    #[test]
    fn test_beat_to_bar_beat_with_change() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(3, 3, 4);  // 3/4 starting at bar 3

        // Bar 1: beats 0-3
        // Bar 2: beats 4-7
        // Bar 3 (3/4): beats 8-10
        // Bar 4 (3/4): beats 11-13

        let (bar, beat, _) = track.beat_to_bar_beat(0.0);
        assert_eq!(bar, 1);

        let (bar, beat, _) = track.beat_to_bar_beat(7.0);
        assert_eq!(bar, 2);
        assert_eq!(beat, 3);

        // Beat 8 should be bar 3, beat 0 (start of 3/4)
        let (bar, beat, _) = track.beat_to_bar_beat(8.0);
        assert_eq!(bar, 3);
        assert_eq!(beat, 0);

        // Beat 10 should be bar 3, beat 2 (last beat of 3/4 bar 3)
        let (bar, beat, _) = track.beat_to_bar_beat(10.0);
        assert_eq!(bar, 3);
        assert_eq!(beat, 2);

        // Beat 11 should be bar 4, beat 0
        let (bar, beat, _) = track.beat_to_bar_beat(11.0);
        assert_eq!(bar, 4);
        assert_eq!(beat, 0);
    }

    #[test]
    fn test_bar_beat_to_beat_4_4() {
        let track = TimeSignatureTrack::new();

        assert_eq!(track.bar_beat_to_beat(1, 0), 0.0);
        assert_eq!(track.bar_beat_to_beat(1, 3), 3.0);
        assert_eq!(track.bar_beat_to_beat(2, 0), 4.0);
        assert_eq!(track.bar_beat_to_beat(2, 2), 6.0);
        assert_eq!(track.bar_beat_to_beat(5, 0), 16.0);
    }

    #[test]
    fn test_bar_beat_to_beat_with_change() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(3, 3, 4);  // 3/4 at bar 3

        // Bar 1, beat 0 = beat 0
        assert_eq!(track.bar_beat_to_beat(1, 0), 0.0);

        // Bar 2, beat 0 = beat 4 (after 4 beats of 4/4)
        assert_eq!(track.bar_beat_to_beat(2, 0), 4.0);

        // Bar 3 (3/4), beat 0 = beat 8 (after 4+4 beats)
        assert_eq!(track.bar_beat_to_beat(3, 0), 8.0);

        // Bar 3, beat 2 = beat 10
        assert_eq!(track.bar_beat_to_beat(3, 2), 10.0);

        // Bar 4 (3/4), beat 0 = beat 11 (8 + 3 beats of 3/4)
        assert_eq!(track.bar_beat_to_beat(4, 0), 11.0);

        // Bar 4, beat 2 = beat 13
        assert_eq!(track.bar_beat_to_beat(4, 2), 13.0);
    }

    #[test]
    fn test_roundtrip_conversion() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);
        track.add_change(10, 6, 8);

        // Test various positions
        for bar in [1, 2, 4, 5, 6, 9, 10, 12] {
            for beat_in_bar in [0, 1, 2, 3] {
                let original_bar = bar;
                let original_beat = beat_in_bar.min(
                    track.get_signature_at_bar(bar).numerator as u32 - 1
                );

                let absolute_beat = track.bar_beat_to_beat(original_bar, original_beat);
                let (converted_bar, converted_beat, _) = track.beat_to_bar_beat(absolute_beat);

                assert_eq!(original_bar, converted_bar,
                    "Bar mismatch: {} -> {} -> {}", original_bar, absolute_beat, converted_bar);
                assert_eq!(original_beat, converted_beat,
                    "Beat mismatch at bar {}: {} -> {} -> {}",
                    original_bar, original_beat, absolute_beat, converted_beat);
            }
        }
    }

    #[test]
    fn test_get_signature_at_beat() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);

        // Bar 1-4: 4/4 (beats 0-15)
        // With 4/4: bars 1-4 = 4*4 = 16 beats total (0-15)
        let sig = track.get_signature_at_beat(0.0);
        assert_eq!(sig.numerator, 4);

        let sig = track.get_signature_at_beat(7.9);
        assert_eq!(sig.numerator, 4);

        let sig = track.get_signature_at_beat(8.0);  // Bar 3 beat 0
        assert_eq!(sig.numerator, 4);

        let sig = track.get_signature_at_beat(15.0);  // Bar 4 beat 3
        assert_eq!(sig.numerator, 4);

        // Bar 5+: 3/4 (beats 16+)
        let sig = track.get_signature_at_beat(16.0);  // Bar 5 beat 0
        assert_eq!(sig.numerator, 3);

        let sig = track.get_signature_at_beat(18.0);  // Bar 5 beat 2
        assert_eq!(sig.numerator, 3);
    }

    #[test]
    fn test_get_bar_start_beat() {
        let track = TimeSignatureTrack::new();

        assert_eq!(track.get_bar_start_beat(1), 0.0);
        assert_eq!(track.get_bar_start_beat(2), 4.0);
        assert_eq!(track.get_bar_start_beat(5), 16.0);
    }

    #[test]
    fn test_get_bar_length() {
        let mut track = TimeSignatureTrack::new();

        assert_eq!(track.get_bar_length(1), 4.0);
        assert_eq!(track.get_bar_length(3), 4.0);

        track.add_change(5, 3, 4);
        assert_eq!(track.get_bar_length(1), 4.0);
        assert_eq!(track.get_bar_length(5), 3.0);
        assert_eq!(track.get_bar_length(10), 3.0);
    }

    #[test]
    fn test_all_changes() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);
        track.add_change(10, 6, 8);

        let changes = track.all_changes();
        assert_eq!(changes.len(), 3);
        assert_eq!(changes[0].to_string(), "4/4");
        assert_eq!(changes[1].to_string(), "3/4");
        assert_eq!(changes[2].to_string(), "6/8");
    }

    #[test]
    fn test_reset() {
        let mut track = TimeSignatureTrack::new();
        track.add_change(5, 3, 4);
        track.add_change(10, 6, 8);

        track.reset();

        assert_eq!(track.change_count(), 1);
        let sig = track.get_signature_at_bar(1);
        assert_eq!(sig.numerator, 4);
        assert_eq!(sig.denominator, 4);
    }

    #[test]
    fn test_negative_beat() {
        let track = TimeSignatureTrack::new();

        let (bar, beat, frac) = track.beat_to_bar_beat(-1.0);
        assert_eq!(bar, 1);
        assert_eq!(beat, 0);
        assert_eq!(frac, 0.0);
    }

    #[test]
    fn test_zero_bar_input() {
        let track = TimeSignatureTrack::new();

        let sig = track.get_signature_at_bar(0);
        assert_eq!(sig.numerator, 4);  // Returns default

        assert_eq!(track.bar_beat_to_beat(0, 0), 0.0);  // Clamped to 0
    }
}
