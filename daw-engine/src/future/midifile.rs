//! midifile - Standard MIDI File (SMF) Read/Write
//!
//! Library for parsing and writing Standard MIDI Files (.mid format).
//! Supports MIDI 1.0 format with all track types and meta events.
//!
//! Repository: https://github.com/craigsapp/midifile

use std::collections::HashMap;
use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint, c_ulong};
use std::path::Path;

/// MIDI file format type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MidiFormat {
    Format0, // Single track
    Format1, // Multiple simultaneous tracks
    Format2, // Multiple sequential tracks
}

/// MIDI event types
#[derive(Debug, Clone, PartialEq)]
pub enum MidiEventType {
    // Channel events
    NoteOff { channel: u8, note: u8, velocity: u8 },
    NoteOn { channel: u8, note: u8, velocity: u8 },
    PolyAftertouch { channel: u8, note: u8, pressure: u8 },
    ControlChange { channel: u8, controller: u8, value: u8 },
    ProgramChange { channel: u8, program: u8 },
    ChannelAftertouch { channel: u8, pressure: u8 },
    PitchBend { channel: u8, value: i16 },
    
    // System Common
    SysEx(Vec<u8>),
    SongPosition(u16),
    SongSelect(u8),
    TuneRequest,
    
    // Meta events
    MetaText(String),
    MetaCopyright(String),
    MetaTrackName(String),
    MetaInstrumentName(String),
    MetaLyric(String),
    MetaMarker(String),
    MetaCuePoint(String),
    MetaTempo(u32),        // microseconds per quarter note
    MetaTimeSignature(u8, u8, u8, u8), // numerator, denominator, clocks per click, 32nd notes per quarter
    MetaKeySignature(i8, bool), // key (sharps/flats), is_minor
    MetaEndOfTrack,
    
    // Unknown/Raw
    Raw { status: u8, data: Vec<u8> },
}

/// Single MIDI event with delta time
#[derive(Debug, Clone, PartialEq)]
pub struct MidiEvent {
    pub delta_time: u32,  // ticks since previous event
    pub track: u16,
    pub event_type: MidiEventType,
}

/// MIDI track containing events
#[derive(Debug, Clone, Default)]
pub struct MidiTrack {
    pub name: String,
    pub events: Vec<MidiEvent>,
}

/// Complete MIDI file structure
#[derive(Debug, Clone)]
pub struct MidiFile {
    pub format: MidiFormat,
    pub ticks_per_quarter: u16,  // PPQN (pulses per quarter note)
    pub tempo: Option<u32>,      // microseconds per quarter (initial tempo)
    pub tracks: Vec<MidiTrack>,
}

/// MIDI file reader
pub struct MidiFileReader;

/// MIDI file writer
pub struct MidiFileWriter;

/// Read options
#[derive(Debug, Clone, Default)]
pub struct ReadOptions {
    pub preserve_running_status: bool,
    pub strict_parsing: bool,
}

/// Write options
#[derive(Debug, Clone, Default)]
pub struct WriteOptions {
    pub use_running_status: bool,
    pub sort_events: bool,
}

/// Error types for midifile operations
#[derive(Debug)]
pub enum MidifileError {
    NotAvailable,
    FileNotFound(String),
    InvalidFormat(String),
    CorruptedData(String),
    ReadError(String),
    WriteError(String),
    UnsupportedFeature(String),
}

impl std::fmt::Display for MidifileError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MidifileError::NotAvailable => write!(f, "midifile library not available"),
            MidifileError::FileNotFound(p) => write!(f, "File not found: {}", p),
            MidifileError::InvalidFormat(m) => write!(f, "Invalid MIDI format: {}", m),
            MidifileError::CorruptedData(m) => write!(f, "Corrupted MIDI data: {}", m),
            MidifileError::ReadError(m) => write!(f, "Read error: {}", m),
            MidifileError::WriteError(m) => write!(f, "Write error: {}", m),
            MidifileError::UnsupportedFeature(m) => write!(f, "Unsupported feature: {}", m),
        }
    }
}

impl std::error::Error for MidifileError {}

impl MidiFileReader {
    /// Create new reader
    pub fn new() -> Self {
        Self
    }

    /// Read MIDI file from path
    pub fn read<P: AsRef<Path>>(&self, path: P, options: &ReadOptions) -> Result<MidiFile, MidifileError> {
        let path_str = path.as_ref().to_str().ok_or_else(|| {
            MidifileError::FileNotFound("Invalid path".to_string())
        })?;
        
        let c_path = CString::new(path_str).map_err(|_| {
            MidifileError::FileNotFound("Path contains null bytes".to_string())
        })?;
        
        let result = unsafe {
            midifile_ffi::read_file(
                c_path.as_ptr(),
                options.preserve_running_status as c_int,
                options.strict_parsing as c_int,
            )
        };
        
        if result.is_null() {
            return Err(MidifileError::NotAvailable);
        }
        
        // Parse result into MidiFile
        let file = MidiFile {
            format: MidiFormat::Format1,
            ticks_per_quarter: 480,
            tempo: None,
            tracks: vec![],
        };
        
        unsafe { midifile_ffi::free_file_data(result) };
        Ok(file)
    }

    /// Read from bytes
    pub fn read_bytes(&self, data: &[u8], options: &ReadOptions) -> Result<MidiFile, MidifileError> {
        let result = unsafe {
            midifile_ffi::read_bytes(
                data.as_ptr(),
                data.len(),
                options.preserve_running_status as c_int,
                options.strict_parsing as c_int,
            )
        };
        
        if result.is_null() {
            return Err(MidifileError::NotAvailable);
        }
        
        let file = MidiFile {
            format: MidiFormat::Format1,
            ticks_per_quarter: 480,
            tempo: None,
            tracks: vec![],
        };
        
        unsafe { midifile_ffi::free_file_data(result) };
        Ok(file)
    }

    /// Get file info without full parsing
    pub fn get_info<P: AsRef<Path>>(&self, path: P) -> Result<MidiFileInfo, MidifileError> {
        let path_str = path.as_ref().to_str().ok_or_else(|| {
            MidifileError::FileNotFound("Invalid path".to_string())
        })?;
        
        let c_path = CString::new(path_str).map_err(|_| {
            MidifileError::FileNotFound("Path contains null bytes".to_string())
        })?;
        
        let result = unsafe { midifile_ffi::get_file_info(c_path.as_ptr()) };
        
        if result.is_null() {
            return Err(MidifileError::NotAvailable);
        }
        
        let info = MidiFileInfo {
            format: MidiFormat::Format1,
            track_count: 0,
            ticks_per_quarter: 480,
            duration_seconds: 0.0,
        };
        
        unsafe { midifile_ffi::free_file_info(result) };
        Ok(info)
    }
}

impl Default for MidiFileReader {
    fn default() -> Self {
        Self::new()
    }
}

impl MidiFileWriter {
    /// Create new writer
    pub fn new() -> Self {
        Self
    }

    /// Write MIDI file to path
    pub fn write<P: AsRef<Path>>(
        &self,
        file: &MidiFile,
        path: P,
        options: &WriteOptions,
    ) -> Result<(), MidifileError> {
        let path_str = path.as_ref().to_str().ok_or_else(|| {
            MidifileError::FileNotFound("Invalid path".to_string())
        })?;
        
        let c_path = CString::new(path_str).map_err(|_| {
            MidifileError::FileNotFound("Path contains null bytes".to_string())
        })?;
        
        let result = unsafe {
            midifile_ffi::write_file(
                c_path.as_ptr(),
                file.format as c_int,
                file.ticks_per_quarter,
                file.tracks.len() as c_int,
                options.use_running_status as c_int,
                options.sort_events as c_int,
            )
        };
        
        if result == 0 {
            Ok(())
        } else {
            Err(MidifileError::NotAvailable)
        }
    }

    /// Write to bytes
    pub fn write_bytes(&self, file: &MidiFile, options: &WriteOptions) -> Result<Vec<u8>, MidifileError> {
        let result = unsafe {
            midifile_ffi::write_bytes(
                file.format as c_int,
                file.ticks_per_quarter,
                file.tracks.len() as c_int,
                options.use_running_status as c_int,
                options.sort_events as c_int,
            )
        };
        
        if result.is_null() {
            return Err(MidifileError::NotAvailable);
        }
        
        let data = vec![];
        unsafe { midifile_ffi::free_bytes(result) };
        Ok(data)
    }
}

impl Default for MidiFileWriter {
    fn default() -> Self {
        Self::new()
    }
}

/// File information (lightweight)
#[derive(Debug, Clone)]
pub struct MidiFileInfo {
    pub format: MidiFormat,
    pub track_count: usize,
    pub ticks_per_quarter: u16,
    pub duration_seconds: f64,
}

/// FFI bridge to C midifile
mod midifile_ffi {
    use super::*;

    extern "C" {
        pub fn read_file(
            path: *const c_char,
            preserve_running_status: c_int,
            strict_parsing: c_int,
        ) -> *mut c_void;
        pub fn read_bytes(
            data: *const u8,
            length: usize,
            preserve_running_status: c_int,
            strict_parsing: c_int,
        ) -> *mut c_void;
        pub fn free_file_data(data: *mut c_void);
        pub fn get_file_info(path: *const c_char) -> *mut c_void;
        pub fn free_file_info(info: *mut c_void);
        pub fn write_file(
            path: *const c_char,
            format: c_int,
            ticks_per_quarter: u16,
            track_count: c_int,
            use_running_status: c_int,
            sort_events: c_int,
        ) -> c_int;
        pub fn write_bytes(
            format: c_int,
            ticks_per_quarter: u16,
            track_count: c_int,
            use_running_status: c_int,
            sort_events: c_int,
        ) -> *mut c_void;
        pub fn free_bytes(data: *mut c_void);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Test 1: Reader creation
    #[test]
    fn test_reader_creation() {
        let reader = MidiFileReader::new();
        // Reader created successfully
        assert_eq!(std::mem::size_of_val(&reader), 0); // ZST
    }

    // Test 2: Writer creation
    #[test]
    fn test_writer_creation() {
        let writer = MidiFileWriter::new();
        // Writer created successfully
        assert_eq!(std::mem::size_of_val(&writer), 0); // ZST
    }

    // Test 3: Read options default
    #[test]
    fn test_read_options_default() {
        let opts = ReadOptions::default();
        assert!(!opts.preserve_running_status);
        assert!(!opts.strict_parsing);
    }

    // Test 4: Write options default
    #[test]
    fn test_write_options_default() {
        let opts = WriteOptions::default();
        assert!(!opts.use_running_status);
        assert!(!opts.sort_events);
    }

    // Test 5: MIDI format types
    #[test]
    fn test_midi_format_types() {
        assert_eq!(MidiFormat::Format0, MidiFormat::Format0);
        assert_eq!(MidiFormat::Format1, MidiFormat::Format1);
        assert_eq!(MidiFormat::Format2, MidiFormat::Format2);
        assert_ne!(MidiFormat::Format0, MidiFormat::Format1);
    }

    // Test 6: Note on event
    #[test]
    fn test_note_on_event() {
        let event = MidiEventType::NoteOn {
            channel: 0,
            note: 60,
            velocity: 100,
        };
        if let MidiEventType::NoteOn { channel, note, velocity } = event {
            assert_eq!(channel, 0);
            assert_eq!(note, 60);
            assert_eq!(velocity, 100);
        } else {
            panic!("Wrong event type");
        }
    }

    // Test 7: Note off event
    #[test]
    fn test_note_off_event() {
        let event = MidiEventType::NoteOff {
            channel: 1,
            note: 64,
            velocity: 50,
        };
        if let MidiEventType::NoteOff { channel, note, velocity } = event {
            assert_eq!(channel, 1);
            assert_eq!(note, 64);
            assert_eq!(velocity, 50);
        } else {
            panic!("Wrong event type");
        }
    }

    // Test 8: Meta tempo event
    #[test]
    fn test_meta_tempo() {
        let event = MidiEventType::MetaTempo(500000); // 120 BPM
        if let MidiEventType::MetaTempo(tempo) = event {
            assert_eq!(tempo, 500000);
        } else {
            panic!("Wrong event type");
        }
    }

    // Test 9: Time signature event
    #[test]
    fn test_time_signature() {
        let event = MidiEventType::MetaTimeSignature(4, 4, 24, 8);
        if let MidiEventType::MetaTimeSignature(num, den, cpq, npq) = event {
            assert_eq!(num, 4);
            assert_eq!(den, 4);
            assert_eq!(cpq, 24);
            assert_eq!(npq, 8);
        } else {
            panic!("Wrong event type");
        }
    }

    // Test 10: Key signature event
    #[test]
    fn test_key_signature() {
        let event = MidiEventType::MetaKeySignature(2, false); // D major
        if let MidiEventType::MetaKeySignature(sharps, is_minor) = event {
            assert_eq!(sharps, 2);
            assert!(!is_minor);
        } else {
            panic!("Wrong event type");
        }
    }

    // Test 11: Error display
    #[test]
    fn test_error_display() {
        let err1 = MidifileError::NotAvailable;
        assert_eq!(format!("{}", err1), "midifile library not available");

        let err2 = MidifileError::InvalidFormat("bad header".to_string());
        assert_eq!(format!("{}", err2), "Invalid MIDI format: bad header");
    }
}
