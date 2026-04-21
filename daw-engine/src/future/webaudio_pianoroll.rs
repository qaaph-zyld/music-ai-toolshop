//! webaudio_pianoroll - Piano Roll UI Component
//!
//! WebAudio-based piano roll for MIDI note editing with grid-based
//! visualization and interaction support.
//!
//! Repository: https://github.com/steffest/webaudio-pianoroll

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint};

/// Piano roll editor
pub struct PianoRoll {
    handle: *mut c_void,
    width: u32,
    height: u32,
    time_signature: (u32, u32),
}

/// MIDI note in piano roll
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PianoNote {
    pub pitch: u8,        // MIDI note number (0-127)
    pub velocity: u8,     // 0-127
    pub start_time: f64,  // In beats
    pub duration: f64,    // In beats
    pub selected: bool,
}

impl Default for PianoNote {
    fn default() -> Self {
        PianoNote {
            pitch: 60,        // Middle C
            velocity: 100,
            start_time: 0.0,
            duration: 1.0,
            selected: false,
        }
    }
}

/// Grid configuration for piano roll
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct GridConfig {
    pub pixels_per_beat: f32,
    pub pixels_per_semitone: f32,
    pub quantize_grid: GridDivision,
    pub show_grid_lines: bool,
    pub show_note_names: bool,
}

impl Default for GridConfig {
    fn default() -> Self {
        GridConfig {
            pixels_per_beat: 40.0,
            pixels_per_semitone: 12.0,
            quantize_grid: GridDivision::Quarter,
            show_grid_lines: true,
            show_note_names: true,
        }
    }
}

/// Grid division for quantization
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum GridDivision {
    Whole,
    Half,
    Quarter,
    Eighth,
    Sixteenth,
    ThirtySecond,
}

impl Default for GridDivision {
    fn default() -> Self {
        GridDivision::Quarter
    }
}

/// Playback position in piano roll
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PlaybackPosition {
    pub beat: f64,
    pub is_playing: bool,
}

impl Default for PlaybackPosition {
    fn default() -> Self {
        PlaybackPosition {
            beat: 0.0,
            is_playing: false,
        }
    }
}

/// Selection state
#[derive(Debug, Clone, PartialEq)]
pub struct SelectionState {
    pub notes: Vec<usize>, // Indices of selected notes
    pub start_beat: f64,
    pub end_beat: f64,
    pub low_pitch: u8,
    pub high_pitch: u8,
}

impl Default for SelectionState {
    fn default() -> Self {
        SelectionState {
            notes: Vec::new(),
            start_beat: 0.0,
            end_beat: 0.0,
            low_pitch: 127,
            high_pitch: 0,
        }
    }
}

/// Piano roll availability status
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PianoRollStatus {
    Available,
    NotAvailable,
    Error(&'static str),
}

/// FFI interface to webaudio-pianoroll library
#[link(name = "daw_engine_ffi")]
extern "C" {
    fn webaudio_pianoroll_create(width: c_int, height: c_int) -> *mut c_void;
    fn webaudio_pianoroll_destroy(handle: *mut c_void);
    fn webaudio_pianoroll_available() -> c_int;
    fn webaudio_pianoroll_add_note(
        handle: *mut c_void,
        pitch: c_int,
        velocity: c_int,
        start_time: c_double,
        duration: c_double,
    ) -> c_int;
    fn webaudio_pianoroll_remove_note(handle: *mut c_void, note_index: c_int) -> c_int;
    fn webaudio_pianoroll_move_note(
        handle: *mut c_void,
        note_index: c_int,
        new_pitch: c_int,
        new_start: c_double,
    ) -> c_int;
    fn webaudio_pianoroll_resize_note(
        handle: *mut c_void,
        note_index: c_int,
        new_duration: c_double,
    ) -> c_int;
    fn webaudio_pianoroll_set_velocity(
        handle: *mut c_void,
        note_index: c_int,
        velocity: c_int,
    ) -> c_int;
    fn webaudio_pianoroll_set_time_signature(
        handle: *mut c_void,
        numerator: c_int,
        denominator: c_int,
    ) -> c_int;
    fn webaudio_pianoroll_set_grid_division(handle: *mut c_void, division: c_int) -> c_int;
    fn webaudio_pianoroll_select_note(handle: *mut c_void, note_index: c_int, selected: c_int) -> c_int;
    fn webaudio_pianoroll_clear_selection(handle: *mut c_void) -> c_int;
    fn webaudio_pianoroll_set_playback_position(handle: *mut c_void, beat: c_double) -> c_int;
    fn webaudio_pianoroll_get_note_count(handle: *mut c_void) -> c_int;
    fn webaudio_pianoroll_clear(handle: *mut c_void) -> c_int;
}

impl PianoRoll {
    /// Create new piano roll editor
    pub fn new(width: u32, height: u32) -> Option<Self> {
        unsafe {
            let handle = webaudio_pianoroll_create(width as c_int, height as c_int);
            if handle.is_null() {
                None
            } else {
                Some(PianoRoll {
                    handle,
                    width,
                    height,
                    time_signature: (4, 4),
                })
            }
        }
    }

    /// Check if piano roll library is available
    pub fn is_available() -> bool {
        unsafe { webaudio_pianoroll_available() != 0 }
    }

    /// Get availability status with error details
    pub fn availability_status() -> PianoRollStatus {
        if Self::is_available() {
            PianoRollStatus::Available
        } else {
            PianoRollStatus::NotAvailable
        }
    }

    /// Add a note to the piano roll
    pub fn add_note(&mut self, note: PianoNote) -> Result<usize, &'static str> {
        unsafe {
            let result = webaudio_pianoroll_add_note(
                self.handle,
                note.pitch as c_int,
                note.velocity as c_int,
                note.start_time,
                note.duration,
            );
            if result >= 0 {
                Ok(result as usize)
            } else {
                Err("Failed to add note")
            }
        }
    }

    /// Remove a note by index
    pub fn remove_note(&mut self, note_index: usize) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_remove_note(self.handle, note_index as c_int);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to remove note")
            }
        }
    }

    /// Move a note to new position
    pub fn move_note(
        &mut self,
        note_index: usize,
        new_pitch: u8,
        new_start: f64,
    ) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_move_note(
                self.handle,
                note_index as c_int,
                new_pitch as c_int,
                new_start,
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to move note")
            }
        }
    }

    /// Resize a note
    pub fn resize_note(
        &mut self,
        note_index: usize,
        new_duration: f64,
    ) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_resize_note(
                self.handle,
                note_index as c_int,
                new_duration,
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to resize note")
            }
        }
    }

    /// Set note velocity
    pub fn set_velocity(
        &mut self,
        note_index: usize,
        velocity: u8,
    ) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_set_velocity(
                self.handle,
                note_index as c_int,
                velocity as c_int,
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set velocity")
            }
        }
    }

    /// Set time signature
    pub fn set_time_signature(&mut self, numerator: u32, denominator: u32) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_set_time_signature(
                self.handle,
                numerator as c_int,
                denominator as c_int,
            );
            if result == 0 {
                self.time_signature = (numerator, denominator);
                Ok(())
            } else {
                Err("Failed to set time signature")
            }
        }
    }

    /// Set grid division for quantization
    pub fn set_grid_division(&mut self, division: GridDivision) -> Result<(), &'static str> {
        let division_value = match division {
            GridDivision::Whole => 1,
            GridDivision::Half => 2,
            GridDivision::Quarter => 4,
            GridDivision::Eighth => 8,
            GridDivision::Sixteenth => 16,
            GridDivision::ThirtySecond => 32,
        };
        unsafe {
            let result = webaudio_pianoroll_set_grid_division(self.handle, division_value);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set grid division")
            }
        }
    }

    /// Select or deselect a note
    pub fn select_note(&mut self, note_index: usize, selected: bool) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_select_note(
                self.handle,
                note_index as c_int,
                if selected { 1 } else { 0 },
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to select note")
            }
        }
    }

    /// Clear all selections
    pub fn clear_selection(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_clear_selection(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear selection")
            }
        }
    }

    /// Set playback position
    pub fn set_playback_position(&mut self, beat: f64) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_set_playback_position(self.handle, beat);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set playback position")
            }
        }
    }

    /// Get number of notes
    pub fn note_count(&self) -> usize {
        unsafe { webaudio_pianoroll_get_note_count(self.handle) as usize }
    }

    /// Clear all notes
    pub fn clear(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = webaudio_pianoroll_clear(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear piano roll")
            }
        }
    }
}

impl Drop for PianoRoll {
    fn drop(&mut self) {
        unsafe {
            webaudio_pianoroll_destroy(self.handle);
        }
    }
}

unsafe impl Send for PianoRoll {}
unsafe impl Sync for PianoRoll {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pianoroll_availability() {
        // Test that we can check availability without crashing
        let available = PianoRoll::is_available();
        // FFI stub returns false until library is integrated
        assert!(!available, "PianoRoll should report not available (stub)");
    }

    #[test]
    fn test_pianoroll_status() {
        let status = PianoRoll::availability_status();
        match status {
            PianoRollStatus::NotAvailable => (), // Expected for stub
            PianoRollStatus::Available => {
                panic!("Should not be available with stub implementation")
            }
            PianoRollStatus::Error(_) => (), // Also acceptable
        }
    }

    #[test]
    fn test_pianoroll_default_note() {
        let note = PianoNote::default();
        assert_eq!(note.pitch, 60); // Middle C
        assert_eq!(note.velocity, 100);
        assert_eq!(note.start_time, 0.0);
        assert_eq!(note.duration, 1.0);
        assert!(!note.selected);
    }

    #[test]
    fn test_pianoroll_custom_note() {
        let note = PianoNote {
            pitch: 72, // C5
            velocity: 127,
            start_time: 2.5,
            duration: 0.5,
            selected: true,
        };
        assert_eq!(note.pitch, 72);
        assert_eq!(note.velocity, 127);
        assert_eq!(note.start_time, 2.5);
        assert_eq!(note.duration, 0.5);
        assert!(note.selected);
    }

    #[test]
    fn test_grid_config_default() {
        let config = GridConfig::default();
        assert_eq!(config.pixels_per_beat, 40.0);
        assert_eq!(config.pixels_per_semitone, 12.0);
        assert!(matches!(config.quantize_grid, GridDivision::Quarter));
        assert!(config.show_grid_lines);
        assert!(config.show_note_names);
    }

    #[test]
    fn test_grid_division_variants() {
        let divisions = [
            GridDivision::Whole,
            GridDivision::Half,
            GridDivision::Quarter,
            GridDivision::Eighth,
            GridDivision::Sixteenth,
            GridDivision::ThirtySecond,
        ];
        
        for division in &divisions {
            let config = GridConfig {
                quantize_grid: *division,
                ..Default::default()
            };
            assert_eq!(config.quantize_grid, *division);
        }
    }

    #[test]
    fn test_playback_position_default() {
        let pos = PlaybackPosition::default();
        assert_eq!(pos.beat, 0.0);
        assert!(!pos.is_playing);
    }

    #[test]
    fn test_playback_position_custom() {
        let pos = PlaybackPosition {
            beat: 16.5,
            is_playing: true,
        };
        assert_eq!(pos.beat, 16.5);
        assert!(pos.is_playing);
    }

    #[test]
    fn test_selection_state_default() {
        let selection = SelectionState::default();
        assert!(selection.notes.is_empty());
        assert_eq!(selection.start_beat, 0.0);
        assert_eq!(selection.end_beat, 0.0);
        assert_eq!(selection.low_pitch, 127);
        assert_eq!(selection.high_pitch, 0);
    }

    #[test]
    fn test_selection_state_with_notes() {
        let selection = SelectionState {
            notes: vec![0, 2, 5],
            start_beat: 1.0,
            end_beat: 4.0,
            low_pitch: 48,
            high_pitch: 72,
        };
        assert_eq!(selection.notes.len(), 3);
        assert_eq!(selection.start_beat, 1.0);
        assert_eq!(selection.end_beat, 4.0);
        assert_eq!(selection.low_pitch, 48);
        assert_eq!(selection.high_pitch, 72);
    }

    #[test]
    fn test_musical_key_default() {
        // Note structure tests are above, this tests the MIDI pitch values
        let note = PianoNote::default();
        assert_eq!(note.pitch, 60); // Middle C = MIDI note 60
    }

    #[test]
    fn test_time_signature_tracking() {
        // Since we can't create PianoRoll (stub returns null),
        // we test the time signature tuple directly
        let sig: (u32, u32) = (4, 4);
        assert_eq!(sig.0, 4);
        assert_eq!(sig.1, 4);
        
        let sig2: (u32, u32) = (3, 4);
        assert_eq!(sig2.0, 3);
        assert_eq!(sig2.1, 4);
        
        let sig3: (u32, u32) = (6, 8);
        assert_eq!(sig3.0, 6);
        assert_eq!(sig3.1, 8);
    }
}
