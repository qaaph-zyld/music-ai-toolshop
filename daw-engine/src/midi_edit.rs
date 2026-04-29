//! MIDI editing operations
//!
//! Provides quantization, transposition, duplication, and note manipulation
//! for MIDI clip editing in the piano roll interface.

use crate::{MidiNote, SessionView, DAWError};

/// MIDI editor for clip manipulation operations
#[derive(Debug, Default)]
pub struct MidiEditor;

impl MidiEditor {
    /// Create new MIDI editor
    pub fn new() -> Self {
        Self
    }
    
    /// Quantize note timings to a grid
    /// 
    /// # Arguments
    /// * `notes` - Input notes to quantize
    /// * `grid_division` - Grid size in beats (e.g., 0.25 = 1/16, 0.5 = 1/8)
    /// 
    /// # Returns
    /// New vector with quantized note timings
    pub fn quantize(&mut self, notes: &[MidiNote], grid_division: f32) -> Vec<MidiNote> {
        notes.iter().map(|note| {
            let beat = note.start_beat();
            let quantized_beat = (beat / grid_division).round() * grid_division;
            MidiNote::new(
                note.pitch(),
                note.velocity(),
                quantized_beat.max(0.0),
                note.duration_beats(),
            )
        }).collect()
    }
    
    /// Transpose notes by semitones
    /// 
    /// # Arguments
    /// * `notes` - Input notes to transpose
    /// * `semitones` - Semitones to shift (positive = up, negative = down)
    /// 
    /// # Returns
    /// New vector with transposed pitches (clamped to 0-127)
    pub fn transpose(&mut self, notes: &[MidiNote], semitones: i32) -> Vec<MidiNote> {
        notes.iter().map(|note| {
            let new_pitch = (note.pitch() as i32 + semitones).clamp(0, 127) as u8;
            MidiNote::new(
                new_pitch,
                note.velocity(),
                note.start_beat(),
                note.duration_beats(),
            )
        }).collect()
    }
    
    /// Scale velocities by a factor
    /// 
    /// # Arguments
    /// * `notes` - Input notes
    /// * `scale` - Scale factor (1.0 = no change, 1.5 = 50% louder)
    /// 
    /// # Returns
    /// New vector with scaled velocities (clamped to 0-127)
    pub fn scale_velocity(&mut self, notes: &[MidiNote], scale: f32) -> Vec<MidiNote> {
        notes.iter().map(|note| {
            let new_velocity = ((note.velocity() as f32 * scale).round() as i32).clamp(0, 127) as u8;
            MidiNote::new(
                note.pitch(),
                new_velocity,
                note.start_beat(),
                note.duration_beats(),
            )
        }).collect()
    }
    
    /// Humanize note timings with small random variations
    /// 
    /// # Arguments
    /// * `notes` - Input notes
    /// * `amount` - Maximum timing variation in beats (e.g., 0.02 = 20ms at 120bpm)
    /// 
    /// # Returns
    /// New vector with humanized timings
    pub fn humanize(&mut self, notes: &[MidiNote], amount: f32) -> Vec<MidiNote> {
        use std::time::{SystemTime, UNIX_EPOCH};
        
        // Simple pseudo-random based on time for deterministic tests
        // In production, this could use a proper RNG
        let seed = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_micros() as u64;
        
        notes.iter().enumerate().map(|(i, note)| {
            let variation = ((seed.wrapping_add(i as u64) % 1000) as f32 / 1000.0 - 0.5) * 2.0 * amount;
            let new_beat = (note.start_beat() + variation).max(0.0);
            MidiNote::new(
                note.pitch(),
                note.velocity(),
                new_beat,
                note.duration_beats(),
            )
        }).collect()
    }
    
    /// Duplicate a clip to another location in the session
    /// 
    /// # Arguments
    /// * `session` - Session view containing clips
    /// * `from_track` - Source track index
    /// * `from_scene` - Source scene index
    /// * `to_track` - Target track index
    /// * `to_scene` - Target scene index
    /// 
    /// # Errors
    /// Returns error if source clip doesn't exist
    pub fn duplicate_clip(
        &mut self,
        session: &mut SessionView,
        from_track: usize,
        from_scene: usize,
        to_track: usize,
        to_scene: usize,
    ) -> Result<(), DAWError> {
        if let Some(clip) = session.get_clip(from_track, from_scene) {
            let cloned = clip.clone();
            session.set_clip(to_track, to_scene, cloned);
            Ok(())
        } else {
            Err(DAWError::InvalidParameter {
                param: "clip_location".to_string(),
                value: format!("track={}, scene={}", from_track, from_scene),
                expected: "valid clip location".to_string(),
            })
        }
    }
    
    /// Add a note to a clip's note list
    /// 
    /// # Arguments
    /// * `notes` - Mutable note vector
    /// * `pitch` - MIDI pitch (0-127)
    /// * `velocity` - MIDI velocity (0-127)
    /// * `start_beat` - Start position in beats
    /// * `duration_beats` - Duration in beats
    pub fn add_note(
        &mut self,
        notes: &mut Vec<MidiNote>,
        pitch: u8,
        velocity: u8,
        start_beat: f32,
        duration_beats: f32,
    ) {
        notes.push(MidiNote::new(pitch, velocity, start_beat, duration_beats));
    }
    
    /// Delete a note by index
    /// 
    /// # Arguments
    /// * `notes` - Mutable note vector
    /// * `index` - Index of note to remove
    pub fn delete_note(&mut self, notes: &mut Vec<MidiNote>, index: usize) {
        if index < notes.len() {
            notes.remove(index);
        }
    }
    
    /// Move a note to new timing and/or pitch
    /// 
    /// # Arguments
    /// * `notes` - Mutable note vector
    /// * `index` - Index of note to move
    /// * `new_start_beat` - New start position
    /// * `new_pitch` - New pitch (0-127)
    pub fn move_note(
        &mut self,
        notes: &mut Vec<MidiNote>,
        index: usize,
        new_start_beat: f32,
        new_pitch: u8,
    ) {
        if let Some(note) = notes.get_mut(index) {
            let duration = note.duration_beats();
            let velocity = note.velocity();
            *note = MidiNote::new(new_pitch, velocity, new_start_beat.max(0.0), duration);
        }
    }
    
    /// Get note at specific beat position (if any)
    /// 
    /// # Arguments
    /// * `notes` - Note vector to search
    /// * `beat` - Beat position to check
    /// * `pitch` - Pitch to check (optional - if None, returns any note at position)
    /// 
    /// # Returns
    /// Index of note if found, None otherwise
    pub fn get_note_at(&self, notes: &[MidiNote], beat: f32, pitch: Option<u8>) -> Option<usize> {
        notes.iter().position(|note| {
            let pitch_match = pitch.map(|p| p == note.pitch()).unwrap_or(true);
            pitch_match && note.is_active_at(beat)
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quantize_basic() {
        let mut editor = MidiEditor::new();
        let notes = vec![MidiNote::new(60, 100, 0.1, 0.5)];
        let result = editor.quantize(&notes, 0.25);
        assert!((result[0].start_beat() - 0.0).abs() < 0.001);
    }

    #[test]
    fn test_transpose_basic() {
        let mut editor = MidiEditor::new();
        let notes = vec![MidiNote::new(60, 100, 0.0, 1.0)];
        let result = editor.transpose(&notes, 12);
        assert_eq!(result[0].pitch(), 72);
    }

    #[test]
    fn test_add_note() {
        let mut editor = MidiEditor::new();
        let mut notes = vec![];
        editor.add_note(&mut notes, 60, 100, 0.0, 1.0);
        assert_eq!(notes.len(), 1);
    }

    #[test]
    fn test_delete_note() {
        let mut editor = MidiEditor::new();
        let mut notes = vec![
            MidiNote::new(60, 100, 0.0, 1.0),
            MidiNote::new(64, 100, 1.0, 1.0),
        ];
        editor.delete_note(&mut notes, 0);
        assert_eq!(notes.len(), 1);
    }

    #[test]
    fn test_move_note() {
        let mut editor = MidiEditor::new();
        let mut notes = vec![MidiNote::new(60, 100, 0.0, 1.0)];
        editor.move_note(&mut notes, 0, 2.0, 64);
        assert_eq!(notes[0].pitch(), 64);
        assert!((notes[0].start_beat() - 2.0).abs() < 0.001);
    }
}
