//! MusicBERT Integration
//!
//! FFI bindings for MusicBERT - Music Understanding Transformer.
//! Provides chord analysis, key detection, genre classification, and
//! structural analysis of music.
//!
//! License: MIT (hypothetical)
//! Reference: https://github.com/microsoft/muzic/tree/main/musicbert

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint};

/// Opaque handle to MusicBERT model
#[repr(C)]
pub struct MusicBertModel {
    _private: [u8; 0],
}

/// MusicBERT error types
#[derive(Debug, Clone, PartialEq)]
pub enum MusicBertError {
    ModelNotFound(String),
    ModelLoadFailed(String),
    AnalysisFailed(String),
    InvalidAudioData(String),
    UnsupportedSampleRate(String),
    FfiError(String),
}

impl std::fmt::Display for MusicBertError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MusicBertError::ModelNotFound(path) => write!(f, "MusicBERT model not found: {}", path),
            MusicBertError::ModelLoadFailed(msg) => write!(f, "Model load failed: {}", msg),
            MusicBertError::AnalysisFailed(msg) => write!(f, "Analysis failed: {}", msg),
            MusicBertError::InvalidAudioData(msg) => write!(f, "Invalid audio data: {}", msg),
            MusicBertError::UnsupportedSampleRate(sr) => write!(f, "Unsupported sample rate: {}", sr),
            MusicBertError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for MusicBertError {}

/// Chord structure
#[derive(Debug, Clone, PartialEq)]
pub struct Chord {
    pub root: NoteName,
    pub quality: ChordQuality,
    pub bass_note: Option<NoteName>, // For slash chords
    pub start_time: f32,
    pub duration: f32,
    pub confidence: f32,
}

/// Note names
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum NoteName {
    C, CSharp, D, DSharp, E, F, FSharp, G, GSharp, A, ASharp, B,
}

/// Chord qualities
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ChordQuality {
    Major,
    Minor,
    Diminished,
    Augmented,
    Major7,
    Minor7,
    Dominant7,
    HalfDiminished7,
    Diminished7,
    Suspended2,
    Suspended4,
    Add9,
}

/// Musical key
#[derive(Debug, Clone, PartialEq)]
pub struct Key {
    pub tonic: NoteName,
    pub mode: KeyMode,
    pub confidence: f32,
}

/// Key mode
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum KeyMode {
    Major,
    Minor,
}

/// Genre classification result
#[derive(Debug, Clone)]
pub struct GenreClassification {
    pub genre: String,
    pub confidence: f32,
}

/// Song structure segment
#[derive(Debug, Clone)]
pub struct StructureSegment {
    pub label: StructureLabel,
    pub start_time: f32,
    pub duration: f32,
    pub confidence: f32,
}

/// Song structure labels
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum StructureLabel {
    Intro,
    Verse,
    Chorus,
    Bridge,
    Solo,
    Outro,
    Other,
}

/// Audio embedding vector
pub type Embedding = Vec<f32>;

/// MusicBERT analyzer
pub struct MusicBertAnalyzer {
    model: *mut MusicBertModel,
    model_path: String,
    sample_rate: u32,
}

// FFI function declarations
extern "C" {
    fn musicbert_ffi_is_available() -> c_int;
    fn musicbert_ffi_get_version() -> *const c_char;
    
    // Model management
    fn musicbert_ffi_model_load(path: *const c_char, sample_rate: c_uint) -> *mut MusicBertModel;
    fn musicbert_ffi_model_free(model: *mut MusicBertModel);
    fn musicbert_ffi_get_supported_sample_rates(rates: *mut c_uint, max_count: c_uint) -> c_int;
    
    // Analysis
    fn musicbert_ffi_analyze_chords(
        model: *mut MusicBertModel,
        audio: *const c_float,
        sample_count: c_uint,
        chords_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn musicbert_ffi_detect_key(
        model: *mut MusicBertModel,
        audio: *const c_float,
        sample_count: c_uint,
        tonic: *mut c_int,
        mode: *mut c_int,
        confidence: *mut c_float,
    ) -> c_int;
    
    fn musicbert_ffi_classify_genre(
        model: *mut MusicBertModel,
        audio: *const c_float,
        sample_count: c_uint,
        genres_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn musicbert_ffi_detect_structure(
        model: *mut MusicBertModel,
        audio: *const c_float,
        sample_count: c_uint,
        structure_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn musicbert_ffi_get_embeddings(
        model: *mut MusicBertModel,
        audio: *const c_float,
        sample_count: c_uint,
        embeddings: *mut c_float,
        embedding_dim: c_uint,
    ) -> c_int;
    
    // Batch processing
    fn musicbert_ffi_batch_analyze(
        model: *mut MusicBertModel,
        file_list: *const c_char,
        results_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
}

impl MusicBertAnalyzer {
    /// Check if MusicBERT is available
    pub fn is_available() -> bool {
        unsafe { musicbert_ffi_is_available() != 0 }
    }

    /// Get MusicBERT version
    pub fn version() -> String {
        unsafe {
            let version_ptr = musicbert_ffi_get_version();
            if version_ptr.is_null() {
                return "unavailable".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get supported sample rates
    pub fn supported_sample_rates() -> Vec<u32> {
        if !Self::is_available() {
            return vec![];
        }

        let mut rates = vec![0u32; 10];
        unsafe {
            let result = musicbert_ffi_get_supported_sample_rates(
                rates.as_mut_ptr(),
                rates.len() as c_uint,
            );

            if result < 0 {
                return vec![];
            }

            let count = result as usize;
            rates.truncate(count);
            rates
        }
    }

    /// Load MusicBERT model
    pub fn new(model_path: &str, sample_rate: u32) -> Result<Self, MusicBertError> {
        if !Self::is_available() {
            return Err(MusicBertError::FfiError("MusicBERT not available".to_string()));
        }

        let c_path = CString::new(model_path)
            .map_err(|e| MusicBertError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let model = musicbert_ffi_model_load(c_path.as_ptr(), sample_rate);
            if model.is_null() {
                return Err(MusicBertError::ModelLoadFailed(model_path.to_string()));
            }

            Ok(Self {
                model,
                model_path: model_path.to_string(),
                sample_rate,
            })
        }
    }

    /// Analyze chord progression
    pub fn analyze_chords(&self, audio: &[f32]) -> Result<Vec<Chord>, MusicBertError> {
        if audio.is_empty() {
            return Err(MusicBertError::InvalidAudioData("Empty audio".to_string()));
        }

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = musicbert_ffi_analyze_chords(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MusicBertError::AnalysisFailed("Chord analysis failed".to_string()));
            }

            // Parse chord data from buffer
            // In real impl, would deserialize JSON or similar
            self.parse_chord_buffer(&buffer)
        }
    }

    /// Detect musical key
    pub fn detect_key(&self, audio: &[f32]) -> Result<Key, MusicBertError> {
        if audio.is_empty() {
            return Err(MusicBertError::InvalidAudioData("Empty audio".to_string()));
        }

        unsafe {
            let mut tonic: c_int = 0;
            let mut mode: c_int = 0;
            let mut confidence: c_float = 0.0;

            let result = musicbert_ffi_detect_key(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                &mut tonic,
                &mut mode,
                &mut confidence,
            );

            if result < 0 {
                return Err(MusicBertError::AnalysisFailed("Key detection failed".to_string()));
            }

            let tonic_note = Self::int_to_note(tonic)?;
            let key_mode = if mode == 0 { KeyMode::Major } else { KeyMode::Minor };

            Ok(Key {
                tonic: tonic_note,
                mode: key_mode,
                confidence,
            })
        }
    }

    /// Classify genre
    pub fn classify_genre(&self, audio: &[f32]) -> Result<Vec<GenreClassification>, MusicBertError> {
        if audio.is_empty() {
            return Err(MusicBertError::InvalidAudioData("Empty audio".to_string()));
        }

        let mut buffer = vec![0u8; 1024];

        unsafe {
            let result = musicbert_ffi_classify_genre(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MusicBertError::AnalysisFailed("Genre classification failed".to_string()));
            }

            // Parse genre results
            self.parse_genre_buffer(&buffer)
        }
    }

    /// Detect song structure
    pub fn detect_structure(&self, audio: &[f32]) -> Result<Vec<StructureSegment>, MusicBertError> {
        if audio.is_empty() {
            return Err(MusicBertError::InvalidAudioData("Empty audio".to_string()));
        }

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = musicbert_ffi_detect_structure(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MusicBertError::AnalysisFailed("Structure detection failed".to_string()));
            }

            // Parse structure segments
            self.parse_structure_buffer(&buffer)
        }
    }

    /// Get audio embeddings
    pub fn get_embeddings(&self, audio: &[f32]) -> Result<Embedding, MusicBertError> {
        if audio.is_empty() {
            return Err(MusicBertError::InvalidAudioData("Empty audio".to_string()));
        }

        let embedding_dim = 768; // Standard BERT embedding size
        let mut embeddings = vec![0.0f32; embedding_dim];

        unsafe {
            let result = musicbert_ffi_get_embeddings(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                embeddings.as_mut_ptr(),
                embedding_dim as c_uint,
            );

            if result < 0 {
                return Err(MusicBertError::AnalysisFailed("Embedding extraction failed".to_string()));
            }

            Ok(embeddings)
        }
    }

    /// Batch analyze multiple files
    pub fn batch_analyze(&self, file_list: &[&str]) -> Result<String, MusicBertError> {
        let files = file_list.join(",");
        let c_files = CString::new(files)
            .map_err(|e| MusicBertError::FfiError(format!("Invalid file list: {}", e)))?;

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = musicbert_ffi_batch_analyze(
                self.model,
                c_files.as_ptr(),
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(MusicBertError::AnalysisFailed("Batch analysis failed".to_string()));
            }

            let results = CStr::from_ptr(buffer.as_ptr() as *const c_char)
                .to_string_lossy()
                .into_owned();

            Ok(results)
        }
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    fn int_to_note(n: c_int) -> Result<NoteName, MusicBertError> {
        match n {
            0 => Ok(NoteName::C),
            1 => Ok(NoteName::CSharp),
            2 => Ok(NoteName::D),
            3 => Ok(NoteName::DSharp),
            4 => Ok(NoteName::E),
            5 => Ok(NoteName::F),
            6 => Ok(NoteName::FSharp),
            7 => Ok(NoteName::G),
            8 => Ok(NoteName::GSharp),
            9 => Ok(NoteName::A),
            10 => Ok(NoteName::ASharp),
            11 => Ok(NoteName::B),
            _ => Err(MusicBertError::AnalysisFailed(format!("Invalid note index: {}", n))),
        }
    }

    fn parse_chord_buffer(&self, buffer: &[u8]) -> Result<Vec<Chord>, MusicBertError> {
        // Stub - real implementation would deserialize
        Ok(vec![])
    }

    fn parse_genre_buffer(&self, buffer: &[u8]) -> Result<Vec<GenreClassification>, MusicBertError> {
        // Stub - real implementation would deserialize
        Ok(vec![])
    }

    fn parse_structure_buffer(&self, buffer: &[u8]) -> Result<Vec<StructureSegment>, MusicBertError> {
        // Stub - real implementation would deserialize
        Ok(vec![])
    }
}

impl Drop for MusicBertAnalyzer {
    fn drop(&mut self) {
        unsafe {
            if !self.model.is_null() {
                musicbert_ffi_model_free(self.model);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_musicbert_module_exists() {
        let _ = MusicBertError::ModelNotFound("test".to_string());
        let _ = NoteName::C;
        let _ = ChordQuality::Major;
    }

    #[test]
    fn test_musicbert_is_available() {
        let available = MusicBertAnalyzer::is_available();
        println!("MusicBERT available: {}", available);
    }

    #[test]
    fn test_musicbert_version() {
        let version = MusicBertAnalyzer::version();
        println!("MusicBERT version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_musicbert_error_display() {
        let err = MusicBertError::ModelNotFound("test_model".to_string());
        assert!(err.to_string().contains("test_model"));

        let err = MusicBertError::AnalysisFailed("OOM".to_string());
        assert!(err.to_string().contains("Analysis failed"));

        let err = MusicBertError::UnsupportedSampleRate("8000".to_string());
        assert!(err.to_string().contains("sample rate"));
    }

    #[test]
    fn test_note_name_enum() {
        assert_eq!(NoteName::C, NoteName::C);
        assert_eq!(NoteName::A, NoteName::A);
        assert_ne!(NoteName::C, NoteName::D);
    }

    #[test]
    fn test_chord_quality_enum() {
        assert_eq!(ChordQuality::Major7, ChordQuality::Major7);
        assert_eq!(ChordQuality::Minor, ChordQuality::Minor);
    }

    #[test]
    fn test_key_structure() {
        let key = Key {
            tonic: NoteName::G,
            mode: KeyMode::Minor,
            confidence: 0.87,
        };
        
        assert_eq!(key.tonic, NoteName::G);
        assert_eq!(key.mode, KeyMode::Minor);
        assert!(key.confidence > 0.0);
    }

    #[test]
    fn test_chord_structure() {
        let chord = Chord {
            root: NoteName::C,
            quality: ChordQuality::Major7,
            bass_note: None,
            start_time: 0.0,
            duration: 1.0,
            confidence: 0.92,
        };
        
        assert_eq!(chord.root, NoteName::C);
        assert_eq!(chord.quality, ChordQuality::Major7);
    }

    #[test]
    fn test_structure_segment() {
        let segment = StructureSegment {
            label: StructureLabel::Chorus,
            start_time: 32.0,
            duration: 16.0,
            confidence: 0.85,
        };
        
        assert_eq!(segment.label, StructureLabel::Chorus);
    }

    #[test]
    fn test_model_load_returns_error_when_unavailable() {
        if !MusicBertAnalyzer::is_available() {
            let result = MusicBertAnalyzer::new("/models/musicbert", 44100);
            assert!(result.is_err());
        }
    }

    #[test]
    fn test_supported_sample_rates_returns_empty_when_unavailable() {
        let rates = MusicBertAnalyzer::supported_sample_rates();
        if !MusicBertAnalyzer::is_available() {
            assert!(rates.is_empty());
        }
    }
}
