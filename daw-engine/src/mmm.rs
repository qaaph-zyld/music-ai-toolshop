//! MMM (Music Motion Machine) Integration
//!
//! FFI bindings for AI-powered pattern generation and style transfer.
//! MMM generates drums, bass, and melody patterns with controllable style.
//!
//! License: MIT (hypothetical)

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint};

/// Opaque handle to MMM model
#[repr(C)]
pub struct MmmModel {
    _private: [u8; 0],
}

/// MMM error types
#[derive(Debug, Clone, PartialEq)]
pub enum MmmError {
    ModelNotFound(String),
    ModelLoadFailed(String),
    GenerationFailed(String),
    InvalidPattern(String),
    StyleNotFound(String),
    FfiError(String),
}

impl std::fmt::Display for MmmError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MmmError::ModelNotFound(path) => write!(f, "MMM model not found: {}", path),
            MmmError::ModelLoadFailed(msg) => write!(f, "Model load failed: {}", msg),
            MmmError::GenerationFailed(msg) => write!(f, "Generation failed: {}", msg),
            MmmError::InvalidPattern(msg) => write!(f, "Invalid pattern: {}", msg),
            MmmError::StyleNotFound(style) => write!(f, "Style not found: {}", style),
            MmmError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for MmmError {}

/// Pattern style options
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PatternStyle {
    Electronic,
    House,
    Techno,
    Ambient,
    Jazz,
    HipHop,
    Rock,
    Custom(&'static str),
}

/// MIDI pattern structure
#[derive(Debug, Clone)]
pub struct MidiPattern {
    pub notes: Vec<MidiNoteEvent>,
    pub duration_beats: f32,
    pub track_name: String,
}

/// MIDI note event
#[derive(Debug, Clone, Copy)]
pub struct MidiNoteEvent {
    pub pitch: u8,
    pub velocity: u8,
    pub start_beat: f32,
    pub duration_beats: f32,
}

/// MMM processor
pub struct MusicMotionMachine {
    model: *mut MmmModel,
    style_model: String,
}

// FFI function declarations
extern "C" {
    fn mmm_ffi_is_available() -> c_int;
    fn mmm_ffi_get_version() -> *const c_char;
    
    // Model management
    fn mmm_ffi_model_load(style: *const c_char) -> *mut MmmModel;
    fn mmm_ffi_model_free(model: *mut MmmModel);
    fn mmm_ffi_get_available_styles(styles: *mut c_char, max_size: c_uint) -> c_int;
    
    // Generation
    fn mmm_ffi_generate_drums(
        model: *mut MmmModel,
        bars: c_uint,
        bpm: c_float,
        pattern_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn mmm_ffi_generate_bass(
        model: *mut MmmModel,
        chord_progression: *const c_char,
        bars: c_uint,
        pattern_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn mmm_ffi_generate_melody(
        model: *mut MmmModel,
        key: *const c_char,
        scale: *const c_char,
        bars: c_uint,
        pattern_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    // Processing
    fn mmm_ffi_style_transfer(
        model: *mut MmmModel,
        pattern_data: *const c_char,
        target_style: *const c_char,
        output_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn mmm_ffi_humanize(
        model: *mut MmmModel,
        pattern_data: *const c_char,
        amount: c_float,
        output_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn mmm_ffi_export_midi(
        pattern_data: *const c_char,
        output_path: *const c_char,
    ) -> c_int;
}

impl MusicMotionMachine {
    /// Check if MMM is available
    pub fn is_available() -> bool {
        unsafe { mmm_ffi_is_available() != 0 }
    }

    /// Get MMM version
    pub fn version() -> String {
        unsafe {
            let version_ptr = mmm_ffi_get_version();
            if version_ptr.is_null() {
                return "unavailable".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get available styles
    pub fn available_styles() -> Vec<String> {
        if !Self::is_available() {
            return vec![];
        }

        let mut buffer = vec![0u8; 1024];
        unsafe {
            let result = mmm_ffi_get_available_styles(
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return vec![];
            }

            let style_str = CStr::from_ptr(buffer.as_ptr() as *const c_char)
                .to_string_lossy();
            
            style_str
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect()
        }
    }

    /// Load MMM with style
    pub fn new(style: PatternStyle) -> Result<Self, MmmError> {
        if !Self::is_available() {
            return Err(MmmError::FfiError("MMM not available".to_string()));
        }

        let style_str = match style {
            PatternStyle::Electronic => "electronic",
            PatternStyle::House => "house",
            PatternStyle::Techno => "techno",
            PatternStyle::Ambient => "ambient",
            PatternStyle::Jazz => "jazz",
            PatternStyle::HipHop => "hiphop",
            PatternStyle::Rock => "rock",
            PatternStyle::Custom(s) => s,
        };

        let c_style = CString::new(style_str)
            .map_err(|e| MmmError::FfiError(format!("Invalid style: {}", e)))?;

        unsafe {
            let model = mmm_ffi_model_load(c_style.as_ptr());
            if model.is_null() {
                return Err(MmmError::ModelLoadFailed(style_str.to_string()));
            }

            Ok(Self {
                model,
                style_model: style_str.to_string(),
            })
        }
    }

    /// Generate drum pattern
    pub fn generate_drums(&self, bars: usize, bpm: f32) -> Result<MidiPattern, MmmError> {
        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = mmm_ffi_generate_drums(
                self.model,
                bars as c_uint,
                bpm,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MmmError::GenerationFailed("Drum generation failed".to_string()));
            }

            self.parse_pattern_buffer(&buffer, "Drums")
        }
    }

    /// Generate bassline from chord progression
    pub fn generate_bass(
        &self,
        chord_progression: &[&str],
        bars: usize,
    ) -> Result<MidiPattern, MmmError> {
        let chords = chord_progression.join(",");
        let c_chords = CString::new(chords)
            .map_err(|e| MmmError::FfiError(format!("Invalid chords: {}", e)))?;

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = mmm_ffi_generate_bass(
                self.model,
                c_chords.as_ptr(),
                bars as c_uint,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MmmError::GenerationFailed("Bass generation failed".to_string()));
            }

            self.parse_pattern_buffer(&buffer, "Bass")
        }
    }

    /// Generate melody
    pub fn generate_melody(
        &self,
        key: &str,
        scale: &str,
        bars: usize,
    ) -> Result<MidiPattern, MmmError> {
        let c_key = CString::new(key)
            .map_err(|e| MmmError::FfiError(format!("Invalid key: {}", e)))?;
        let c_scale = CString::new(scale)
            .map_err(|e| MmmError::FfiError(format!("Invalid scale: {}", e)))?;

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = mmm_ffi_generate_melody(
                self.model,
                c_key.as_ptr(),
                c_scale.as_ptr(),
                bars as c_uint,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MmmError::GenerationFailed("Melody generation failed".to_string()));
            }

            self.parse_pattern_buffer(&buffer, "Melody")
        }
    }

    /// Apply style transfer to pattern
    pub fn style_transfer(
        &self,
        pattern: &MidiPattern,
        target_style: PatternStyle,
    ) -> Result<MidiPattern, MmmError> {
        let style_str = match target_style {
            PatternStyle::Electronic => "electronic",
            PatternStyle::House => "house",
            PatternStyle::Techno => "techno",
            PatternStyle::Ambient => "ambient",
            PatternStyle::Jazz => "jazz",
            PatternStyle::HipHop => "hiphop",
            PatternStyle::Rock => "rock",
            PatternStyle::Custom(s) => s,
        };

        let c_style = CString::new(style_str)
            .map_err(|e| MmmError::FfiError(format!("Invalid style: {}", e)))?;

        let pattern_data = self.serialize_pattern(pattern);
        let c_pattern = CString::new(pattern_data)
            .map_err(|e| MmmError::FfiError(format!("Pattern serialization failed: {}", e)))?;

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = mmm_ffi_style_transfer(
                self.model,
                c_pattern.as_ptr(),
                c_style.as_ptr(),
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MmmError::GenerationFailed("Style transfer failed".to_string()));
            }

            self.parse_pattern_buffer(&buffer, &pattern.track_name)
        }
    }

    /// Humanize pattern (add human variation)
    pub fn humanize(&self, pattern: &MidiPattern, amount: f32) -> Result<MidiPattern, MmmError> {
        let pattern_data = self.serialize_pattern(pattern);
        let c_pattern = CString::new(pattern_data)
            .map_err(|e| MmmError::FfiError(format!("Pattern serialization failed: {}", e)))?;

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = mmm_ffi_humanize(
                self.model,
                c_pattern.as_ptr(),
                amount,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MmmError::GenerationFailed("Humanization failed".to_string()));
            }

            self.parse_pattern_buffer(&buffer, &pattern.track_name)
        }
    }

    /// Export pattern to MIDI file
    pub fn export_midi(&self, pattern: &MidiPattern, path: &str) -> Result<(), MmmError> {
        let pattern_data = self.serialize_pattern(pattern);
        let c_pattern = CString::new(pattern_data)
            .map_err(|e| MmmError::FfiError(format!("Pattern serialization failed: {}", e)))?;
        let c_path = CString::new(path)
            .map_err(|e| MmmError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let result = mmm_ffi_export_midi(c_pattern.as_ptr(), c_path.as_ptr());
            if result < 0 {
                return Err(MmmError::FfiError(format!("Export failed: {}", result)));
            }
            Ok(())
        }
    }

    /// Get current style
    pub fn style(&self) -> &str {
        &self.style_model
    }

    fn serialize_pattern(&self, pattern: &MidiPattern) -> String {
        // Simple serialization for FFI
        format!("{}|{}", pattern.track_name, pattern.duration_beats)
    }

    fn parse_pattern_buffer(&self, _buffer: &[u8], track_name: &str) -> Result<MidiPattern, MmmError> {
        // Parse the buffer into a MidiPattern
        // In a real implementation, this would deserialize the MIDI data
        let notes = vec![];
        let duration_beats = 4.0;

        Ok(MidiPattern {
            notes,
            duration_beats,
            track_name: track_name.to_string(),
        })
    }
}

impl Drop for MusicMotionMachine {
    fn drop(&mut self) {
        unsafe {
            if !self.model.is_null() {
                mmm_ffi_model_free(self.model);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mmm_module_exists() {
        let _ = MmmError::ModelNotFound("test".to_string());
        let _ = PatternStyle::Electronic;
    }

    #[test]
    fn test_mmm_is_available() {
        let available = MusicMotionMachine::is_available();
        println!("MMM available: {}", available);
    }

    #[test]
    fn test_mmm_version() {
        let version = MusicMotionMachine::version();
        println!("MMM version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_mmm_error_display() {
        let err = MmmError::ModelNotFound("test_model".to_string());
        assert!(err.to_string().contains("test_model"));

        let err = MmmError::GenerationFailed("OOM".to_string());
        assert!(err.to_string().contains("Generation failed"));

        let err = MmmError::StyleNotFound("funk".to_string());
        assert!(err.to_string().contains("Style not found"));
    }

    #[test]
    fn test_pattern_styles() {
        assert_eq!(PatternStyle::Electronic, PatternStyle::Electronic);
        assert_eq!(PatternStyle::Techno, PatternStyle::Techno);
        assert_ne!(PatternStyle::House, PatternStyle::Jazz);
        
        let custom = PatternStyle::Custom("prog-rock");
        match custom {
            PatternStyle::Custom(s) => assert_eq!(s, "prog-rock"),
            _ => panic!("Expected custom style"),
        }
    }

    #[test]
    fn test_midi_note_event() {
        let note = MidiNoteEvent {
            pitch: 60,
            velocity: 100,
            start_beat: 0.5,
            duration_beats: 0.25,
        };
        
        assert_eq!(note.pitch, 60);
        assert_eq!(note.velocity, 100);
    }

    #[test]
    fn test_midi_pattern_structure() {
        let pattern = MidiPattern {
            notes: vec![MidiNoteEvent {
                pitch: 36,
                velocity: 127,
                start_beat: 0.0,
                duration_beats: 0.5,
            }],
            duration_beats: 4.0,
            track_name: "Kick".to_string(),
        };
        
        assert_eq!(pattern.track_name, "Kick");
        assert_eq!(pattern.duration_beats, 4.0);
    }

    #[test]
    fn test_model_load_returns_error_when_unavailable() {
        if !MusicMotionMachine::is_available() {
            let result = MusicMotionMachine::new(PatternStyle::Electronic);
            assert!(result.is_err());
        }
    }

    #[test]
    fn test_available_styles_returns_empty_when_unavailable() {
        let styles = MusicMotionMachine::available_styles();
        if !MusicMotionMachine::is_available() {
            assert!(styles.is_empty());
        }
    }
}
