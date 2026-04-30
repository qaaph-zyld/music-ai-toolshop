//! Arrangement View - Linear Timeline Composition
//!
//! Unlike the Session View (scene-based clip launching), the Arrangement View
//! provides a linear timeline where clips can be placed at specific positions
//! and play sequentially. This enables traditional DAW composition workflows.

use std::collections::BTreeMap;
use crate::error::{DAWError, DAWResult};
use crate::session::Clip;

/// Unique identifier for arrangement clips
pub type ArrangementClipId = u64;

/// A clip positioned on the arrangement timeline
#[derive(Debug, Clone)]
pub struct ArrangementClip {
    pub id: ArrangementClipId,
    pub track_index: usize,
    pub start_beat: f64,
    pub duration_beats: f64,
    pub clip_data: Clip,
}

impl ArrangementClip {
    /// Create a new arrangement clip
    pub fn new(
        id: ArrangementClipId,
        track_index: usize,
        start_beat: f64,
        clip_data: Clip,
    ) -> Self {
        // Convert bars to beats (assuming 4 beats per bar)
        let duration_beats = clip_data.duration_bars() as f64 * 4.0;
        Self {
            id,
            track_index,
            start_beat,
            duration_beats,
            clip_data,
        }
    }
    
    /// Get the end position in beats
    pub fn end_beat(&self) -> f64 {
        self.start_beat + self.duration_beats
    }
    
    /// Get clip name
    pub fn name(&self) -> &str {
        self.clip_data.name()
    }
    
    /// Check if this is an audio clip
    pub fn is_audio(&self) -> bool {
        self.clip_data.is_audio()
    }
    
    /// Check if this is a MIDI clip
    pub fn is_midi(&self) -> bool {
        self.clip_data.is_midi()
    }
    
    /// Check if this clip overlaps with a given beat range
    pub fn overlaps_range(&self, start: f64, end: f64) -> bool {
        self.start_beat < end && self.end_beat() > start
    }
    
    /// Check if a beat position falls within this clip
    pub fn contains_beat(&self, beat: f64) -> bool {
        beat >= self.start_beat && beat < self.end_beat()
    }
    
    /// Move the clip to a new start position
    pub fn move_to(&mut self, new_start_beat: f64) {
        self.start_beat = new_start_beat;
    }
    
    /// Resize the clip by changing duration
    pub fn resize(&mut self, new_duration: f64) {
        self.duration_beats = new_duration.max(0.25); // Minimum 1/4 beat
    }
}

/// Arrangement track containing clips for a single track lane
#[derive(Debug, Clone, Default)]
pub struct ArrangementTrack {
    pub clips: BTreeMap<ArrangementClipId, ArrangementClip>,
    pub next_clip_id: ArrangementClipId,
}

impl ArrangementTrack {
    pub fn new() -> Self {
        Self {
            clips: BTreeMap::new(),
            next_clip_id: 1,
        }
    }
    
    /// Add a clip to this track
    pub fn add_clip(&mut self, track_index: usize, start_beat: f64, clip_data: Clip) -> ArrangementClipId {
        let id = self.next_clip_id;
        self.next_clip_id += 1;
        
        let clip = ArrangementClip::new(id, track_index, start_beat, clip_data);
        self.clips.insert(id, clip);
        
        id
    }
    
    /// Remove a clip by ID
    pub fn remove_clip(&mut self, id: ArrangementClipId) -> DAWResult<()> {
        if self.clips.remove(&id).is_none() {
            return Err(DAWError::OutOfBounds { index: id as usize, max: self.next_clip_id as usize });
        }
        Ok(())
    }
    
    /// Get a clip by ID
    pub fn get_clip(&self, id: ArrangementClipId) -> Option<&ArrangementClip> {
        self.clips.get(&id)
    }
    
    /// Get a mutable reference to a clip
    pub fn get_clip_mut(&mut self, id: ArrangementClipId) -> Option<&mut ArrangementClip> {
        self.clips.get_mut(&id)
    }
    
    /// Move a clip to a new position
    pub fn move_clip(&mut self, id: ArrangementClipId, new_start: f64) -> DAWResult<()> {
        let max_id = self.next_clip_id as usize;
        let clip = self.get_clip_mut(id)
            .ok_or_else(|| DAWError::OutOfBounds { index: id as usize, max: max_id })?;
        clip.move_to(new_start);
        Ok(())
    }
    
    /// Resize a clip
    pub fn resize_clip(&mut self, id: ArrangementClipId, new_duration: f64) -> DAWResult<()> {
        let max_id = self.next_clip_id as usize;
        let clip = self.get_clip_mut(id)
            .ok_or_else(|| DAWError::OutOfBounds { index: id as usize, max: max_id })?;
        clip.resize(new_duration);
        Ok(())
    }
    
    /// Find clips overlapping a beat range
    pub fn clips_in_range(&self, start: f64, end: f64) -> Vec<&ArrangementClip> {
        self.clips.values()
            .filter(|clip| clip.overlaps_range(start, end))
            .collect()
    }
    
    /// Find clip at a specific beat position
    pub fn clip_at_beat(&self, beat: f64) -> Option<&ArrangementClip> {
        self.clips.values()
            .find(|clip| clip.contains_beat(beat))
    }
    
    /// Get all clips sorted by start position
    pub fn clips_sorted(&self) -> Vec<&ArrangementClip> {
        self.clips.values().collect()
    }
    
    /// Check if a time range is free (no clips overlap)
    pub fn is_range_free(&self, start: f64, end: f64, exclude_id: Option<ArrangementClipId>) -> bool {
        self.clips.values()
            .filter(|clip| exclude_id.map_or(true, |id| clip.id != id))
            .all(|clip| !clip.overlaps_range(start, end))
    }
}

/// Full arrangement with multiple tracks
#[derive(Debug, Clone, Default)]
pub struct Arrangement {
    pub tracks: Vec<ArrangementTrack>,
    pub max_tracks: usize,
}

impl Arrangement {
    pub fn new(max_tracks: usize) -> Self {
        let mut tracks = Vec::with_capacity(max_tracks);
        for _ in 0..max_tracks {
            tracks.push(ArrangementTrack::new());
        }
        
        Self { tracks, max_tracks }
    }
    
    /// Add a clip to a specific track
    pub fn add_clip(&mut self, track_idx: usize, start_beat: f64, clip_data: Clip) -> DAWResult<ArrangementClipId> {
        if track_idx >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: track_idx, max: self.max_tracks });
        }
        
        let id = self.tracks[track_idx].add_clip(track_idx, start_beat, clip_data);
        Ok(id)
    }
    
    /// Remove a clip from any track
    pub fn remove_clip(&mut self, track_idx: usize, id: ArrangementClipId) -> DAWResult<()> {
        if track_idx >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: track_idx, max: self.max_tracks });
        }
        
        self.tracks[track_idx].remove_clip(id)
    }
    
    /// Get a clip by track and ID
    pub fn get_clip(&self, track_idx: usize, id: ArrangementClipId) -> DAWResult<&ArrangementClip> {
        if track_idx >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: track_idx, max: self.max_tracks });
        }
        
        self.tracks[track_idx].get_clip(id)
            .ok_or_else(|| DAWError::OutOfBounds { index: id as usize, max: self.tracks[track_idx].next_clip_id as usize })
    }
    
    /// Move a clip to a new track and/or position
    pub fn move_clip(&mut self, from_track: usize, id: ArrangementClipId, to_track: usize, new_start: f64) -> DAWResult<()> {
        if from_track >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: from_track, max: self.max_tracks });
        }
        if to_track >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: to_track, max: self.max_tracks });
        }
        
        // If moving to same track, just update position
        if from_track == to_track {
            return self.tracks[from_track].move_clip(id, new_start);
        }
        
        // Moving to different track - transfer clip preserving ID
        let max_id = self.tracks[from_track].next_clip_id;
        let clip = self.tracks[from_track].clips.remove(&id)
            .ok_or_else(|| DAWError::OutOfBounds { index: id as usize, max: max_id as usize })?;
        
        // Create new clip at destination with same ID
        let mut new_clip = ArrangementClip::new(id, to_track, new_start, clip.clip_data);
        new_clip.duration_beats = clip.duration_beats;
        
        self.tracks[to_track].clips.insert(id, new_clip);
        
        Ok(())
    }
    
    /// Resize a clip
    pub fn resize_clip(&mut self, track_idx: usize, id: ArrangementClipId, new_duration: f64) -> DAWResult<()> {
        if track_idx >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: track_idx, max: self.max_tracks });
        }
        
        self.tracks[track_idx].resize_clip(id, new_duration)
    }
    
    /// Get all clips on a track
    pub fn clips_on_track(&self, track_idx: usize) -> DAWResult<Vec<&ArrangementClip>> {
        if track_idx >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: track_idx, max: self.max_tracks });
        }
        
        Ok(self.tracks[track_idx].clips_sorted())
    }
    
    /// Find clips on a specific track in a beat range
    pub fn clips_in_range(&self, track_idx: usize, start: f64, end: f64) -> DAWResult<Vec<&ArrangementClip>> {
        if track_idx >= self.max_tracks {
            return Err(DAWError::OutOfBounds { index: track_idx, max: self.max_tracks });
        }
        
        Ok(self.tracks[track_idx].clips_in_range(start, end))
    }
    
    /// Get clips that should play at a given beat position across all tracks
    pub fn active_clips_at_beat(&self, beat: f64) -> Vec<&ArrangementClip> {
        self.tracks.iter()
            .filter_map(|track| track.clip_at_beat(beat))
            .collect()
    }
    
    /// Get the total duration of the arrangement (end of last clip)
    pub fn total_duration(&self) -> f64 {
        self.tracks.iter()
            .filter_map(|track| {
                track.clips.values()
                    .map(|clip| clip.end_beat())
                    .fold(0.0f64, f64::max)
                    .into()
            })
            .fold(0.0f64, f64::max)
    }
    
    /// Check if a clip can be moved to a position without overlapping
    pub fn can_move_to(&self, track_idx: usize, clip_id: ArrangementClipId, new_start: f64, duration: f64) -> bool {
        if track_idx >= self.max_tracks {
            return false;
        }
        
        self.tracks[track_idx].is_range_free(new_start, new_start + duration, Some(clip_id))
    }
    
    /// Clear all clips from the arrangement
    pub fn clear(&mut self) {
        for track in &mut self.tracks {
            track.clips.clear();
            track.next_clip_id = 1;
        }
    }
    
    /// Get clip count across all tracks
    pub fn total_clip_count(&self) -> usize {
        self.tracks.iter().map(|t| t.clips.len()).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    fn create_test_midi_clip(name: &str) -> Clip {
        Clip::new_midi(name, 1.0) // 1 bar = 4 beats
    }
    
    fn create_test_audio_clip(name: &str, duration_bars: f32) -> Clip {
        Clip::new_audio(name, duration_bars)
    }
    
    #[test]
    fn test_arrangement_clip_new() {
        let clip_data = create_test_midi_clip("Test");
        let aclip = ArrangementClip::new(1, 0, 0.0, clip_data);
        
        assert_eq!(aclip.id, 1);
        assert_eq!(aclip.track_index, 0);
        assert_eq!(aclip.start_beat, 0.0);
        assert_eq!(aclip.duration_beats, 4.0);
    }
    
    #[test]
    fn test_arrangement_clip_end_beat() {
        let clip_data = create_test_midi_clip("Test");
        let aclip = ArrangementClip::new(1, 0, 2.0, clip_data);
        
        assert_eq!(aclip.end_beat(), 6.0); // 2.0 + 4.0
    }
    
    #[test]
    fn test_arrangement_clip_overlaps_range() {
        let clip_data = create_test_midi_clip("Test");
        let aclip = ArrangementClip::new(1, 0, 4.0, clip_data); // 4.0 to 8.0
        
        assert!(aclip.overlaps_range(0.0, 5.0));   // Overlaps at start
        assert!(aclip.overlaps_range(5.0, 10.0));  // Overlaps at middle
        assert!(aclip.overlaps_range(7.0, 10.0));  // Overlaps at end
        assert!(!aclip.overlaps_range(0.0, 4.0)); // Ends exactly at clip start (exclusive end)
        assert!(!aclip.overlaps_range(8.0, 12.0)); // Starts exactly at clip end
    }
    
    #[test]
    fn test_arrangement_clip_contains_beat() {
        let clip_data = create_test_midi_clip("Test");
        let aclip = ArrangementClip::new(1, 0, 4.0, clip_data); // 4.0 to 8.0
        
        assert!(!aclip.contains_beat(3.9));
        assert!(aclip.contains_beat(4.0));
        assert!(aclip.contains_beat(6.0));
        assert!(aclip.contains_beat(7.99));
        assert!(!aclip.contains_beat(8.0));
    }
    
    #[test]
    fn test_arrangement_clip_move_to() {
        let clip_data = create_test_midi_clip("Test");
        let mut aclip = ArrangementClip::new(1, 0, 4.0, clip_data);
        
        aclip.move_to(10.0);
        assert_eq!(aclip.start_beat, 10.0);
        assert_eq!(aclip.end_beat(), 14.0);
    }
    
    #[test]
    fn test_arrangement_clip_resize() {
        let clip_data = create_test_midi_clip("Test");
        let mut aclip = ArrangementClip::new(1, 0, 4.0, clip_data);
        
        aclip.resize(8.0);
        assert_eq!(aclip.duration_beats, 8.0);
        assert_eq!(aclip.end_beat(), 12.0);
    }
    
    #[test]
    fn test_arrangement_clip_resize_minimum() {
        let clip_data = create_test_midi_clip("Test");
        let mut aclip = ArrangementClip::new(1, 0, 4.0, clip_data);
        
        aclip.resize(0.1); // Below minimum
        assert_eq!(aclip.duration_beats, 0.25); // Clamped to minimum
    }
    
    #[test]
    fn test_arrangement_track_add_clip() {
        let mut track = ArrangementTrack::new();
        let clip_data = create_test_midi_clip("Test");
        
        let id1 = track.add_clip(0, 0.0, clip_data.clone());
        let id2 = track.add_clip(0, 4.0, clip_data.clone());
        
        assert_eq!(id1, 1);
        assert_eq!(id2, 2);
        assert_eq!(track.clips.len(), 2);
    }
    
    #[test]
    fn test_arrangement_track_remove_clip() {
        let mut track = ArrangementTrack::new();
        let clip_data = create_test_midi_clip("Test");
        
        let id = track.add_clip(0, 0.0, clip_data);
        assert!(track.get_clip(id).is_some());
        
        track.remove_clip(id).unwrap();
        assert!(track.get_clip(id).is_none());
    }
    
    #[test]
    fn test_arrangement_track_move_clip() {
        let mut track = ArrangementTrack::new();
        let clip_data = create_test_midi_clip("Test");
        
        let id = track.add_clip(0, 0.0, clip_data);
        track.move_clip(id, 8.0).unwrap();
        
        assert_eq!(track.get_clip(id).unwrap().start_beat, 8.0);
    }
    
    #[test]
    fn test_arrangement_track_clips_in_range() {
        let mut track = ArrangementTrack::new();
        let clip_data = create_test_midi_clip("Test");
        
        track.add_clip(0, 0.0, clip_data.clone());   // 0-4
        track.add_clip(0, 4.0, clip_data.clone());   // 4-8
        track.add_clip(0, 8.0, clip_data.clone());   // 8-12
        
        let clips = track.clips_in_range(2.0, 6.0);
        assert_eq!(clips.len(), 2); // First and second clips
    }
    
    #[test]
    fn test_arrangement_track_clip_at_beat() {
        let mut track = ArrangementTrack::new();
        let clip_data = create_test_midi_clip("Test");
        
        track.add_clip(0, 0.0, clip_data.clone());   // 0-4
        track.add_clip(0, 8.0, clip_data.clone());   // 8-12
        
        assert!(track.clip_at_beat(2.0).is_some());
        assert!(track.clip_at_beat(6.0).is_none()); // Gap between clips
        assert!(track.clip_at_beat(10.0).is_some());
    }
    
    #[test]
    fn test_arrangement_track_is_range_free() {
        let mut track = ArrangementTrack::new();
        let clip_data = create_test_midi_clip("Test");
        
        let id = track.add_clip(0, 4.0, clip_data); // 4-8
        
        assert!(track.is_range_free(0.0, 4.0, None));       // Before clip
        assert!(!track.is_range_free(2.0, 6.0, None));      // Overlaps clip
        assert!(track.is_range_free(8.0, 12.0, None));      // After clip
        assert!(track.is_range_free(4.0, 8.0, Some(id)));   // Same position, excluding self
    }
    
    #[test]
    fn test_arrangement_new() {
        let arr = Arrangement::new(8);
        assert_eq!(arr.tracks.len(), 8);
        assert_eq!(arr.max_tracks, 8);
    }
    
    #[test]
    fn test_arrangement_add_clip() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        let id = arr.add_clip(0, 0.0, clip_data).unwrap();
        assert_eq!(id, 1);
        
        let clip = arr.get_clip(0, id).unwrap();
        assert_eq!(clip.track_index, 0);
        assert_eq!(clip.start_beat, 0.0);
    }
    
    #[test]
    fn test_arrangement_add_clip_invalid_track() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        let result = arr.add_clip(10, 0.0, clip_data);
        assert!(result.is_err());
    }
    
    #[test]
    fn test_arrangement_move_clip_same_track() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        let id = arr.add_clip(0, 0.0, clip_data).unwrap();
        arr.move_clip(0, id, 0, 8.0).unwrap();
        
        assert_eq!(arr.get_clip(0, id).unwrap().start_beat, 8.0);
    }
    
    #[test]
    fn test_arrangement_move_clip_different_track() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        let id = arr.add_clip(0, 0.0, clip_data).unwrap();
        arr.move_clip(0, id, 2, 4.0).unwrap();
        
        // Clip should be removed from track 0
        assert!(arr.get_clip(0, id).is_err());
        
        // And added to track 2 (with new ID)
        let clips_on_track_2 = arr.clips_on_track(2).unwrap();
        assert_eq!(clips_on_track_2.len(), 1);
        assert_eq!(clips_on_track_2[0].start_beat, 4.0);
    }
    
    #[test]
    fn test_arrangement_resize_clip() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        let id = arr.add_clip(0, 0.0, clip_data).unwrap();
        arr.resize_clip(0, id, 8.0).unwrap();
        
        assert_eq!(arr.get_clip(0, id).unwrap().duration_beats, 8.0);
    }
    
    #[test]
    fn test_arrangement_active_clips_at_beat() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        arr.add_clip(0, 0.0, clip_data.clone()).unwrap();   // 0-4
        arr.add_clip(1, 2.0, clip_data.clone()).unwrap();   // 2-6
        arr.add_clip(2, 8.0, clip_data.clone()).unwrap();   // 8-12
        
        let active = arr.active_clips_at_beat(3.0);
        assert_eq!(active.len(), 2); // Track 0 and 1
        
        let active = arr.active_clips_at_beat(10.0);
        assert_eq!(active.len(), 1); // Only track 2
    }
    
    #[test]
    fn test_arrangement_total_duration() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_audio_clip("Test", 1.0); // 1 bar = 4 beats
        
        arr.add_clip(0, 0.0, clip_data.clone()).unwrap();    // 0-4
        arr.add_clip(1, 8.0, clip_data.clone()).unwrap();    // 8-12
        arr.add_clip(2, 16.0, clip_data.clone()).unwrap();   // 16-20
        
        assert_eq!(arr.total_duration(), 20.0);
    }
    
    #[test]
    fn test_arrangement_total_clip_count() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        arr.add_clip(0, 0.0, clip_data.clone()).unwrap();
        arr.add_clip(0, 4.0, clip_data.clone()).unwrap();
        arr.add_clip(1, 0.0, clip_data.clone()).unwrap();
        
        assert_eq!(arr.total_clip_count(), 3);
    }
    
    #[test]
    fn test_arrangement_clear() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        arr.add_clip(0, 0.0, clip_data.clone()).unwrap();
        arr.add_clip(1, 0.0, clip_data.clone()).unwrap();
        
        arr.clear();
        
        assert_eq!(arr.total_clip_count(), 0);
    }
    
    #[test]
    fn test_arrangement_can_move_to() {
        let mut arr = Arrangement::new(8);
        let clip_data = create_test_midi_clip("Test");
        
        // Add first clip at 4-8
        let id1 = arr.add_clip(0, 4.0, clip_data.clone()).unwrap();
        
        // Can move to 0-4 (no overlap with any other clip)
        assert!(arr.can_move_to(0, id1, 0.0, 4.0));
        
        // Can move to 2-6 even though it overlaps with current position 4-8
        // because we're moving the clip away from there
        assert!(arr.can_move_to(0, id1, 2.0, 4.0));
        
        // Can move to 8-12 (no overlap)
        assert!(arr.can_move_to(0, id1, 8.0, 4.0));
        
        // Add second clip at 12-16
        let id2 = arr.add_clip(0, 12.0, clip_data.clone()).unwrap();
        
        // Now id1 at 4-8 cannot move to 10-14 because it would overlap with id2 at 12-16
        assert!(!arr.can_move_to(0, id1, 10.0, 4.0));
        
        // But id1 can still move to 0-4 or 8-12
        assert!(arr.can_move_to(0, id1, 0.0, 4.0));
        assert!(arr.can_move_to(0, id1, 8.0, 4.0));
    }
}
