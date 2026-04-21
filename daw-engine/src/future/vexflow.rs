//! vexflow - Music Notation Rendering
//!
//! JavaScript library for rendering musical notation in SVG.
//! Supports standard notation, tablature, and rhythmic notation.
//!
//! Repository: https://github.com/0xfe/vexflow

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint};

/// VexFlow notation renderer
pub struct VexFlowRenderer {
    handle: *mut c_void,
    width: u32,
    height: u32,
}

/// Staff configuration
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum StaffType {
    Treble,
    Bass,
    Alto,
    Tenor,
    Percussion,
    Tablature(u16), // Number of strings
}

impl Default for StaffType {
    fn default() -> Self {
        StaffType::Treble
    }
}

/// Clef types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Clef {
    Treble,
    Bass,
    Alto,
    Tenor,
    Percussion,
}

impl Default for Clef {
    fn default() -> Self {
        Clef::Treble
    }
}

/// Note duration
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum NoteDuration {
    Whole,
    Half,
    Quarter,
    Eighth,
    Sixteenth,
    ThirtySecond,
    SixtyFourth,
}

impl Default for NoteDuration {
    fn default() -> Self {
        NoteDuration::Quarter
    }
}

impl NoteDuration {
    pub fn as_str(&self) -> &'static str {
        match self {
            NoteDuration::Whole => "w",
            NoteDuration::Half => "h",
            NoteDuration::Quarter => "q",
            NoteDuration::Eighth => "8",
            NoteDuration::Sixteenth => "16",
            NoteDuration::ThirtySecond => "32",
            NoteDuration::SixtyFourth => "64",
        }
    }
}

/// Musical note
#[derive(Debug, Clone, PartialEq)]
pub struct VexNote {
    pub keys: Vec<String>,     // Note names (e.g., "c/4", "e/4", "g/4")
    pub duration: NoteDuration,
    pub dots: u8,
    pub accidentals: Vec<Accidental>,
}

impl Default for VexNote {
    fn default() -> Self {
        VexNote {
            keys: vec!["c/4".to_string()],
            duration: NoteDuration::Quarter,
            dots: 0,
            accidentals: Vec::new(),
        }
    }
}

/// Accidental types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Accidental {
    Sharp,
    Flat,
    Natural,
    DoubleSharp,
    DoubleFlat,
}

impl Default for Accidental {
    fn default() -> Self {
        Accidental::Natural
    }
}

/// Key signature
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum KeySignature {
    CMajor,    // A minor
    GMajor,    // E minor
    DMajor,    // B minor
    AMajor,    // F# minor
    EMajor,    // C# minor
    BMajor,    // G# minor
    FSharpMajor, // D# minor
    CSharpMajor, // A# minor
    FMajor,    // D minor
    BFlatMajor, // G minor
    EFlatMajor, // C minor
    AFlatMajor, // F minor
    DFlatMajor, // Bb minor
    GFlatMajor, // Eb minor
    CFlatMajor, // Ab minor
}

impl Default for KeySignature {
    fn default() -> Self {
        KeySignature::CMajor
    }
}

/// Time signature
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TimeSignature {
    pub numerator: u8,
    pub denominator: u8,
}

impl Default for TimeSignature {
    fn default() -> Self {
        TimeSignature {
            numerator: 4,
            denominator: 4,
        }
    }
}

/// Rendering options
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RenderOptions {
    pub scale: f32,
    pub use_svg: bool,
    pub font_size: u8,
    pub stave_space: u8,
}

impl Default for RenderOptions {
    fn default() -> Self {
        RenderOptions {
            scale: 1.0,
            use_svg: true,
            font_size: 12,
            stave_space: 10,
        }
    }
}

/// Voice (a sequence of notes)
#[derive(Debug, Clone, PartialEq)]
pub struct Voice {
    pub notes: Vec<VexNote>,
    pub time_signature: TimeSignature,
    pub num_beats: u32,
    pub beat_value: u32,
}

impl Default for Voice {
    fn default() -> Self {
        Voice {
            notes: Vec::new(),
            time_signature: TimeSignature::default(),
            num_beats: 4,
            beat_value: 4,
        }
    }
}

/// VexFlow availability status
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VexFlowStatus {
    Available,
    NotAvailable,
    Error(&'static str),
}

/// FFI interface to VexFlow library
#[link(name = "daw_engine_ffi")]
extern "C" {
    fn vexflow_create(width: c_int, height: c_int, use_svg: c_int) -> *mut c_void;
    fn vexflow_destroy(handle: *mut c_void);
    fn vexflow_available() -> c_int;
    fn vexflow_add_staff(handle: *mut c_void, staff_type: c_int, x: c_int, y: c_int, width: c_int) -> c_int;
    fn vexflow_set_clef(handle: *mut c_void, staff_id: c_int, clef: c_int) -> c_int;
    fn vexflow_set_key_signature(handle: *mut c_void, staff_id: c_int, key: c_int) -> c_int;
    fn vexflow_set_time_signature(handle: *mut c_void, staff_id: c_int, numerator: c_int, denominator: c_int) -> c_int;
    fn vexflow_add_note(handle: *mut c_void, staff_id: c_int, note_json: *const c_char) -> c_int;
    fn vexflow_add_chord(handle: *mut c_void, staff_id: c_int, chord_json: *const c_char) -> c_int;
    fn vexflow_add_rest(handle: *mut c_void, staff_id: c_int, duration: *const c_char, position: c_double) -> c_int;
    fn vexflow_add_tie(handle: *mut c_void, from_note: c_int, to_note: c_int) -> c_int;
    fn vexflow_add_beam(handle: *mut c_void, note_indices: *const c_int, count: c_int) -> c_int;
    fn vexflow_render(handle: *mut c_void) -> c_int;
    fn vexflow_get_svg(handle: *mut c_void, buffer: *mut c_char, buffer_size: c_int) -> c_int;
    fn vexflow_clear(handle: *mut c_void) -> c_int;
    fn vexflow_resize(handle: *mut c_void, width: c_int, height: c_int) -> c_int;
}

impl VexFlowRenderer {
    /// Create new VexFlow renderer
    pub fn new(width: u32, height: u32, use_svg: bool) -> Option<Self> {
        unsafe {
            let handle = vexflow_create(
                width as c_int,
                height as c_int,
                if use_svg { 1 } else { 0 },
            );
            if handle.is_null() {
                None
            } else {
                Some(VexFlowRenderer {
                    handle,
                    width,
                    height,
                })
            }
        }
    }

    /// Check if VexFlow is available
    pub fn is_available() -> bool {
        unsafe { vexflow_available() != 0 }
    }

    /// Get availability status
    pub fn availability_status() -> VexFlowStatus {
        if Self::is_available() {
            VexFlowStatus::Available
        } else {
            VexFlowStatus::NotAvailable
        }
    }

    /// Add a staff
    pub fn add_staff(&mut self, staff_type: StaffType, x: u32, y: u32, width: u32) -> Result<usize, &'static str> {
        let staff_type_id = match staff_type {
            StaffType::Treble => 0,
            StaffType::Bass => 1,
            StaffType::Alto => 2,
            StaffType::Tenor => 3,
            StaffType::Percussion => 4,
            StaffType::Tablature(_) => 5,
        };
        
        unsafe {
            let result = vexflow_add_staff(
                self.handle,
                staff_type_id,
                x as c_int,
                y as c_int,
                width as c_int,
            );
            if result >= 0 {
                Ok(result as usize)
            } else {
                Err("Failed to add staff")
            }
        }
    }

    /// Set clef for a staff
    pub fn set_clef(&mut self, staff_id: usize, clef: Clef) -> Result<(), &'static str> {
        let clef_id = match clef {
            Clef::Treble => 0,
            Clef::Bass => 1,
            Clef::Alto => 2,
            Clef::Tenor => 3,
            Clef::Percussion => 4,
        };
        
        unsafe {
            let result = vexflow_set_clef(self.handle, staff_id as c_int, clef_id);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set clef")
            }
        }
    }

    /// Set key signature
    pub fn set_key_signature(&mut self, staff_id: usize, key: KeySignature) -> Result<(), &'static str> {
        let key_id = key as c_int;
        
        unsafe {
            let result = vexflow_set_key_signature(self.handle, staff_id as c_int, key_id);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set key signature")
            }
        }
    }

    /// Set time signature
    pub fn set_time_signature(&mut self, staff_id: usize, time: TimeSignature) -> Result<(), &'static str> {
        unsafe {
            let result = vexflow_set_time_signature(
                self.handle,
                staff_id as c_int,
                time.numerator as c_int,
                time.denominator as c_int,
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set time signature")
            }
        }
    }

    /// Add a note to a staff
    pub fn add_note(&mut self, staff_id: usize, note: &VexNote) -> Result<usize, &'static str> {
        unsafe {
            // Build note JSON
            let keys = note.keys.join(",");
            let duration = note.duration.as_str();
            let note_json = format!("{{\"keys\":[\"{}\"],\"duration\":\"{}\"}}", keys, duration);
            let c_json = CString::new(note_json).map_err(|_| "Invalid note data")?;
            
            let result = vexflow_add_note(self.handle, staff_id as c_int, c_json.as_ptr());
            if result >= 0 {
                Ok(result as usize)
            } else {
                Err("Failed to add note")
            }
        }
    }

    /// Add a chord
    pub fn add_chord(&mut self, staff_id: usize, notes: &[VexNote]) -> Result<usize, &'static str> {
        unsafe {
            // Build chord JSON
            let keys: Vec<_> = notes.iter()
                .map(|n| n.keys.join(","))
                .collect();
            let chord_json = format!("{{\"keys\":[\"{}\"],\"duration\":\"q\"}}", keys.join("\",\""));
            let c_json = CString::new(chord_json).map_err(|_| "Invalid chord data")?;
            
            let result = vexflow_add_chord(self.handle, staff_id as c_int, c_json.as_ptr());
            if result >= 0 {
                Ok(result as usize)
            } else {
                Err("Failed to add chord")
            }
        }
    }

    /// Add a rest
    pub fn add_rest(&mut self, staff_id: usize, duration: NoteDuration, position: f64) -> Result<usize, &'static str> {
        unsafe {
            let dur_str = CString::new(duration.as_str()).map_err(|_| "Invalid duration")?;
            let result = vexflow_add_rest(
                self.handle,
                staff_id as c_int,
                dur_str.as_ptr(),
                position,
            );
            if result >= 0 {
                Ok(result as usize)
            } else {
                Err("Failed to add rest")
            }
        }
    }

    /// Add a tie between notes
    pub fn add_tie(&mut self, from_note: usize, to_note: usize) -> Result<(), &'static str> {
        unsafe {
            let result = vexflow_add_tie(self.handle, from_note as c_int, to_note as c_int);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to add tie")
            }
        }
    }

    /// Add a beam group
    pub fn add_beam(&mut self, note_indices: &[usize]) -> Result<(), &'static str> {
        unsafe {
            let indices: Vec<c_int> = note_indices.iter().map(|&i| i as c_int).collect();
            let result = vexflow_add_beam(
                self.handle,
                indices.as_ptr(),
                indices.len() as c_int,
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to add beam")
            }
        }
    }

    /// Render the score
    pub fn render(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = vexflow_render(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to render")
            }
        }
    }

    /// Get SVG output
    pub fn get_svg(&self) -> Result<String, &'static str> {
        unsafe {
            let mut buffer = vec![0u8; 65536];
            let result = vexflow_get_svg(
                self.handle,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_int,
            );
            if result >= 0 {
                let svg = CStr::from_ptr(buffer.as_ptr() as *const c_char)
                    .to_str()
                    .map_err(|_| "Invalid UTF-8 in SVG")?;
                Ok(svg.to_string())
            } else {
                Err("Failed to get SVG")
            }
        }
    }

    /// Clear the score
    pub fn clear(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = vexflow_clear(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear")
            }
        }
    }

    /// Resize the renderer
    pub fn resize(&mut self, width: u32, height: u32) -> Result<(), &'static str> {
        unsafe {
            let result = vexflow_resize(self.handle, width as c_int, height as c_int);
            if result == 0 {
                self.width = width;
                self.height = height;
                Ok(())
            } else {
                Err("Failed to resize")
            }
        }
    }
}

impl Drop for VexFlowRenderer {
    fn drop(&mut self) {
        unsafe {
            vexflow_destroy(self.handle);
        }
    }
}

unsafe impl Send for VexFlowRenderer {}
unsafe impl Sync for VexFlowRenderer {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vexflow_availability() {
        let available = VexFlowRenderer::is_available();
        assert!(!available, "VexFlow should report not available (stub)");
    }

    #[test]
    fn test_vexflow_status() {
        let status = VexFlowRenderer::availability_status();
        match status {
            VexFlowStatus::NotAvailable => (),
            VexFlowStatus::Available => panic!("Should not be available with stub"),
            VexFlowStatus::Error(_) => (),
        }
    }

    #[test]
    fn test_staff_type_default() {
        let staff = StaffType::default();
        assert!(matches!(staff, StaffType::Treble));
    }

    #[test]
    fn test_staff_type_variants() {
        let types = [
            StaffType::Treble,
            StaffType::Bass,
            StaffType::Alto,
            StaffType::Tenor,
            StaffType::Percussion,
            StaffType::Tablature(6),
        ];
        
        for staff_type in &types {
            match staff_type {
                StaffType::Tablature(n) => assert_eq!(*n, 6),
                _ => (),
            }
        }
    }

    #[test]
    fn test_clef_default() {
        let clef = Clef::default();
        assert!(matches!(clef, Clef::Treble));
    }

    #[test]
    fn test_note_duration_default() {
        let dur = NoteDuration::default();
        assert!(matches!(dur, NoteDuration::Quarter));
    }

    #[test]
    fn test_note_duration_strings() {
        assert_eq!(NoteDuration::Whole.as_str(), "w");
        assert_eq!(NoteDuration::Half.as_str(), "h");
        assert_eq!(NoteDuration::Quarter.as_str(), "q");
        assert_eq!(NoteDuration::Eighth.as_str(), "8");
        assert_eq!(NoteDuration::Sixteenth.as_str(), "16");
        assert_eq!(NoteDuration::ThirtySecond.as_str(), "32");
        assert_eq!(NoteDuration::SixtyFourth.as_str(), "64");
    }

    #[test]
    fn test_note_default() {
        let note = VexNote::default();
        assert_eq!(note.keys, vec!["c/4"]);
        assert!(matches!(note.duration, NoteDuration::Quarter));
        assert_eq!(note.dots, 0);
        assert!(note.accidentals.is_empty());
    }

    #[test]
    fn test_note_custom() {
        let note = VexNote {
            keys: vec!["e/4".to_string(), "g/4".to_string(), "b/4".to_string()],
            duration: NoteDuration::Half,
            dots: 1,
            accidentals: vec![Accidental::Sharp, Accidental::Natural, Accidental::Flat],
        };
        assert_eq!(note.keys.len(), 3);
        assert!(matches!(note.duration, NoteDuration::Half));
        assert_eq!(note.dots, 1);
        assert_eq!(note.accidentals.len(), 3);
    }

    #[test]
    fn test_key_signature_variants() {
        // Just verify all variants exist
        let keys = [
            KeySignature::CMajor,
            KeySignature::GMajor,
            KeySignature::DMajor,
            KeySignature::AMajor,
            KeySignature::EMajor,
            KeySignature::BMajor,
            KeySignature::FSharpMajor,
            KeySignature::CSharpMajor,
            KeySignature::FMajor,
            KeySignature::BFlatMajor,
            KeySignature::EFlatMajor,
            KeySignature::AFlatMajor,
            KeySignature::DFlatMajor,
            KeySignature::GFlatMajor,
            KeySignature::CFlatMajor,
        ];
        
        for key in &keys {
            // Just verify they exist
            let _: KeySignature = *key;
        }
    }

    #[test]
    fn test_time_signature_default() {
        let time = TimeSignature::default();
        assert_eq!(time.numerator, 4);
        assert_eq!(time.denominator, 4);
    }

    #[test]
    fn test_time_signature_custom() {
        let time = TimeSignature {
            numerator: 3,
            denominator: 4,
        };
        assert_eq!(time.numerator, 3);
        assert_eq!(time.denominator, 4);
    }

    #[test]
    fn test_render_options_default() {
        let opts = RenderOptions::default();
        assert_eq!(opts.scale, 1.0);
        assert!(opts.use_svg);
        assert_eq!(opts.font_size, 12);
        assert_eq!(opts.stave_space, 10);
    }

    #[test]
    fn test_render_options_custom() {
        let opts = RenderOptions {
            scale: 1.5,
            use_svg: false,
            font_size: 14,
            stave_space: 12,
        };
        assert_eq!(opts.scale, 1.5);
        assert!(!opts.use_svg);
        assert_eq!(opts.font_size, 14);
        assert_eq!(opts.stave_space, 12);
    }

    #[test]
    fn test_voice_default() {
        let voice = Voice::default();
        assert!(voice.notes.is_empty());
        assert_eq!(voice.num_beats, 4);
        assert_eq!(voice.beat_value, 4);
    }

    #[test]
    fn test_voice_custom() {
        let voice = Voice {
            notes: vec![VexNote::default(), VexNote::default()],
            time_signature: TimeSignature { numerator: 3, denominator: 4 },
            num_beats: 3,
            beat_value: 4,
        };
        assert_eq!(voice.notes.len(), 2);
        assert_eq!(voice.num_beats, 3);
    }
}
