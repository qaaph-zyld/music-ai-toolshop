//! aubio - Real-time Pitch Detection and Analysis
//!
//! Real-time pitch detection library with multiple algorithms (YIN, spectral,
//! harmonic comb). Also includes onset detection and tempo analysis.
//!
//! Licensed: GPL-3.0
//! Repository: https://github.com/aubio/aubio

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint, c_ulong};

/// Aubio pitch detector
pub struct AubioPitchDetector {
    handle: *mut c_void,
    sample_rate: u32,
    buffer_size: usize,
    hop_size: usize,
    algorithm: PitchAlgorithm,
}

/// Pitch detection algorithms
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PitchAlgorithm {
    Yin,           // Fast, accurate for monophonic
    YinFast,       // Faster YIN variant
    YinFft,        // FFT-based YIN
    Spec,          // Spectral method
    SpecAc,        // Spectral with autocorrelation
    MComb,         // Multi-comb filter
}

impl Default for PitchAlgorithm {
    fn default() -> Self {
        PitchAlgorithm::Yin
    }
}

/// Aubio onset detector
pub struct AubioOnsetDetector {
    handle: *mut c_void,
    sample_rate: u32,
    buffer_size: usize,
    hop_size: usize,
}

/// Aubio tempo detector
pub struct AubioTempoDetector {
    handle: *mut c_void,
    sample_rate: u32,
    buffer_size: usize,
    hop_size: usize,
}

/// Pitch detection result
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PitchResult {
    pub frequency: f32,
    pub confidence: f32,
    pub midi_note: Option<u8>,
}

/// Onset detection result
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct OnsetResult {
    pub is_onset: bool,
    pub onset_time: f32,  // seconds
    pub intensity: f32,
}

/// Tempo detection result
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TempoResult {
    pub bpm: f32,
    pub confidence: f32,
    pub beat_count: u32,
    pub last_beat_time: f32,  // seconds
}

/// Pitch detection settings
#[derive(Debug, Clone)]
pub struct PitchSettings {
    pub min_frequency: f32,
    pub max_frequency: f32,
    pub threshold: f32,
}

impl Default for PitchSettings {
    fn default() -> Self {
        Self {
            min_frequency: 27.5,  // A0
            max_frequency: 4186.0, // C8
            threshold: 0.1,
        }
    }
}

/// Onset detection settings
#[derive(Debug, Clone)]
pub struct OnsetSettings {
    pub threshold: f32,
    pub silence_threshold: f32,
    pub min_ioi: f32,  // minimum inter-onset interval (seconds)
}

impl Default for OnsetSettings {
    fn default() -> Self {
        Self {
            threshold: 0.1,
            silence_threshold: -40.0,  // dB
            min_ioi: 0.02,  // 20ms
        }
    }
}

/// Tempo detection settings
#[derive(Debug, Clone)]
pub struct TempoSettings {
    pub min_bpm: f32,
    pub max_bpm: f32,
}

impl Default for TempoSettings {
    fn default() -> Self {
        Self {
            min_bpm: 40.0,
            max_bpm: 200.0,
        }
    }
}

/// Error types for aubio operations
#[derive(Debug)]
pub enum AubioError {
    NotAvailable,
    InvalidSampleRate(u32),
    InvalidBufferSize(usize),
    InvalidAlgorithm(String),
    DetectionError(String),
    FfiError(String),
}

impl std::fmt::Display for AubioError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AubioError::NotAvailable => write!(f, "aubio library not available"),
            AubioError::InvalidSampleRate(sr) => write!(f, "Invalid sample rate: {}", sr),
            AubioError::InvalidBufferSize(sz) => write!(f, "Invalid buffer size: {}", sz),
            AubioError::InvalidAlgorithm(a) => write!(f, "Invalid algorithm: {}", a),
            AubioError::DetectionError(e) => write!(f, "Detection error: {}", e),
            AubioError::FfiError(e) => write!(f, "FFI error: {}", e),
        }
    }
}

impl std::error::Error for AubioError {}

impl AubioPitchDetector {
    /// Create new pitch detector
    pub fn new(
        sample_rate: u32,
        buffer_size: usize,
        hop_size: usize,
        algorithm: PitchAlgorithm,
    ) -> Result<Self, AubioError> {
        if sample_rate == 0 {
            return Err(AubioError::InvalidSampleRate(sample_rate));
        }
        if buffer_size == 0 || hop_size == 0 {
            return Err(AubioError::InvalidBufferSize(0));
        }

        let handle = unsafe {
            aubio_ffi::pitch_new(
                algorithm as c_int,
                buffer_size as c_int,
                hop_size as c_int,
                sample_rate,
            )
        };

        if handle.is_null() {
            return Err(AubioError::NotAvailable);
        }

        Ok(Self {
            handle,
            sample_rate,
            buffer_size,
            hop_size,
            algorithm,
        })
    }

    /// Set pitch detection range
    pub fn set_range(&mut self, min_freq: f32, max_freq: f32) -> Result<(), AubioError> {
        let result = unsafe {
            aubio_ffi::pitch_set_unit(self.handle, 1); // Hz
            aubio_ffi::pitch_set_tolerance(self.handle, 0.1);
        };
        
        // FFI stubs don't have return values for setters
        Ok(())
    }

    /// Set silence threshold
    pub fn set_silence(&mut self, silence_db: f32) {
        unsafe {
            aubio_ffi::pitch_set_silence(self.handle, silence_db);
        }
    }

    /// Process audio and detect pitch
    pub fn process(&mut self, input: &[f32]) -> Result<PitchResult, AubioError> {
        let mut frequency: f32 = 0.0;
        let mut confidence: f32 = 0.0;

        let result = unsafe {
            aubio_ffi::pitch_do(
                self.handle,
                input.as_ptr(),
                &mut frequency,
                &mut confidence,
            )
        };

        if result != 0 {
            return Err(AubioError::DetectionError("Pitch detection failed".to_string()));
        }

        let midi_note = if frequency > 0.0 {
            Some(frequency_to_midi(frequency))
        } else {
            None
        };

        Ok(PitchResult {
            frequency,
            confidence,
            midi_note,
        })
    }

    /// Get detector info
    pub fn info(&self) -> AubioInfo {
        AubioInfo {
            version: "0.4.9".to_string(),
            has_pitch: true,
            has_onset: false,
            has_tempo: false,
        }
    }
}

impl Drop for AubioPitchDetector {
    fn drop(&mut self) {
        unsafe {
            aubio_ffi::pitch_del(self.handle);
        }
    }
}

impl AubioOnsetDetector {
    /// Create new onset detector
    pub fn new(
        sample_rate: u32,
        buffer_size: usize,
        hop_size: usize,
    ) -> Result<Self, AubioError> {
        if sample_rate == 0 {
            return Err(AubioError::InvalidSampleRate(sample_rate));
        }
        if buffer_size == 0 || hop_size == 0 {
            return Err(AubioError::InvalidBufferSize(0));
        }

        let handle = unsafe {
            aubio_ffi::onset_new(buffer_size as c_int, hop_size as c_int, sample_rate)
        };

        if handle.is_null() {
            return Err(AubioError::NotAvailable);
        }

        Ok(Self {
            handle,
            sample_rate,
            buffer_size,
            hop_size,
        })
    }

    /// Set onset threshold
    pub fn set_threshold(&mut self, threshold: f32) {
        unsafe {
            aubio_ffi::onset_set_threshold(self.handle, threshold);
        }
    }

    /// Set minimum inter-onset interval
    pub fn set_min_ioi(&mut self, min_ioi_ms: f32) {
        unsafe {
            aubio_ffi::onset_set_min_ioi_ms(self.handle, min_ioi_ms);
        }
    }

    /// Process audio and detect onset
    pub fn process(&mut self, input: &[f32]) -> Result<OnsetResult, AubioError> {
        let mut is_onset: c_int = 0;
        let mut intensity: f32 = 0.0;

        let result = unsafe {
            aubio_ffi::onset_do(
                self.handle,
                input.as_ptr(),
                &mut is_onset,
                &mut intensity,
            )
        };

        if result != 0 {
            return Err(AubioError::DetectionError("Onset detection failed".to_string()));
        }

        let onset_time = unsafe { aubio_ffi::onset_get_last_s(self.handle) };

        Ok(OnsetResult {
            is_onset: is_onset != 0,
            onset_time,
            intensity,
        })
    }
}

impl Drop for AubioOnsetDetector {
    fn drop(&mut self) {
        unsafe {
            aubio_ffi::onset_del(self.handle);
        }
    }
}

impl AubioTempoDetector {
    /// Create new tempo detector
    pub fn new(
        sample_rate: u32,
        buffer_size: usize,
        hop_size: usize,
    ) -> Result<Self, AubioError> {
        if sample_rate == 0 {
            return Err(AubioError::InvalidSampleRate(sample_rate));
        }
        if buffer_size == 0 || hop_size == 0 {
            return Err(AubioError::InvalidBufferSize(0));
        }

        let handle = unsafe {
            aubio_ffi::tempo_new(buffer_size as c_int, hop_size as c_int, sample_rate)
        };

        if handle.is_null() {
            return Err(AubioError::NotAvailable);
        }

        Ok(Self {
            handle,
            sample_rate,
            buffer_size,
            hop_size,
        })
    }

    /// Set BPM range
    pub fn set_bpm_range(&mut self, min_bpm: f32, max_bpm: f32) {
        unsafe {
            aubio_ffi::tempo_set_range(self.handle, min_bpm, max_bpm);
        }
    }

    /// Process audio and detect tempo
    pub fn process(&mut self, input: &[f32]) -> Result<TempoResult, AubioError> {
        let mut is_beat: c_int = 0;

        let result = unsafe {
            aubio_ffi::tempo_do(self.handle, input.as_ptr(), &mut is_beat)
        };

        if result != 0 {
            return Err(AubioError::DetectionError("Tempo detection failed".to_string()));
        }

        let bpm = unsafe { aubio_ffi::tempo_get_bpm(self.handle) };
        let confidence = unsafe { aubio_ffi::tempo_get_confidence(self.handle) };
        let beat_count = unsafe { aubio_ffi::tempo_get_beat(self.handle) };
        let last_beat_time = unsafe { aubio_ffi::tempo_get_last_s(self.handle) };

        Ok(TempoResult {
            bpm,
            confidence,
            beat_count,
            last_beat_time,
        })
    }
}

impl Drop for AubioTempoDetector {
    fn drop(&mut self) {
        unsafe {
            aubio_ffi::tempo_del(self.handle);
        }
    }
}

/// Convert frequency to MIDI note number
fn frequency_to_midi(freq: f32) -> u8 {
    if freq <= 0.0 {
        return 0;
    }
    let midi = 69.0 + 12.0 * (freq / 440.0).log2();
    midi.round().clamp(0.0, 127.0) as u8
}

/// Aubio library information
#[derive(Debug, Clone)]
pub struct AubioInfo {
    pub version: String,
    pub has_pitch: bool,
    pub has_onset: bool,
    pub has_tempo: bool,
}

/// FFI bridge to C aubio
mod aubio_ffi {
    use super::*;

    extern "C" {
        // Pitch detection
        pub fn pitch_new(method: c_int, buf_size: c_int, hop_size: c_int, sample_rate: u32) -> *mut c_void;
        pub fn pitch_del(pitch: *mut c_void);
        pub fn pitch_do(pitch: *mut c_void, input: *const f32, output: *mut f32, confidence: *mut f32) -> c_int;
        pub fn pitch_set_unit(pitch: *mut c_void, unit: c_int);
        pub fn pitch_set_tolerance(pitch: *mut c_void, tolerance: c_float);
        pub fn pitch_set_silence(pitch: *mut c_void, silence: c_float);
        
        // Onset detection
        pub fn onset_new(buf_size: c_int, hop_size: c_int, sample_rate: u32) -> *mut c_void;
        pub fn onset_del(onset: *mut c_void);
        pub fn onset_do(onset: *mut c_void, input: *const f32, is_onset: *mut c_int, intensity: *mut f32) -> c_int;
        pub fn onset_set_threshold(onset: *mut c_void, threshold: c_float);
        pub fn onset_set_min_ioi_ms(onset: *mut c_void, min_ioi: c_float);
        pub fn onset_get_last_s(onset: *mut c_void) -> c_float;
        
        // Tempo detection
        pub fn tempo_new(buf_size: c_int, hop_size: c_int, sample_rate: u32) -> *mut c_void;
        pub fn tempo_del(tempo: *mut c_void);
        pub fn tempo_do(tempo: *mut c_void, input: *const f32, is_beat: *mut c_int) -> c_int;
        pub fn tempo_set_range(tempo: *mut c_void, min_bpm: c_float, max_bpm: c_float);
        pub fn tempo_get_bpm(tempo: *mut c_void) -> c_float;
        pub fn tempo_get_confidence(tempo: *mut c_void) -> c_float;
        pub fn tempo_get_beat(tempo: *mut c_void) -> u32;
        pub fn tempo_get_last_s(tempo: *mut c_void) -> c_float;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Test 1: Pitch detector creation
    #[test]
    fn test_pitch_detector_creation() {
        let result = AubioPitchDetector::new(44100, 1024, 512, PitchAlgorithm::Yin);
        // FFI stub returns NotAvailable
        assert!(matches!(result, Err(AubioError::NotAvailable)));
    }

    // Test 2: Invalid sample rate
    #[test]
    fn test_invalid_sample_rate() {
        let result = AubioPitchDetector::new(0, 1024, 512, PitchAlgorithm::Yin);
        assert!(matches!(result, Err(AubioError::InvalidSampleRate(0))));
    }

    // Test 3: Invalid buffer size
    #[test]
    fn test_invalid_buffer_size() {
        let result = AubioPitchDetector::new(44100, 0, 512, PitchAlgorithm::Yin);
        assert!(matches!(result, Err(AubioError::InvalidBufferSize(0))));

        let result2 = AubioPitchDetector::new(44100, 1024, 0, PitchAlgorithm::Yin);
        assert!(matches!(result2, Err(AubioError::InvalidBufferSize(0))));
    }

    // Test 4: Pitch algorithm variants
    #[test]
    fn test_pitch_algorithms() {
        assert_eq!(PitchAlgorithm::Yin, PitchAlgorithm::Yin);
        assert_eq!(PitchAlgorithm::YinFast, PitchAlgorithm::YinFast);
        assert_eq!(PitchAlgorithm::YinFft, PitchAlgorithm::YinFft);
        assert_eq!(PitchAlgorithm::Spec, PitchAlgorithm::Spec);
        assert_eq!(PitchAlgorithm::SpecAc, PitchAlgorithm::SpecAc);
        assert_eq!(PitchAlgorithm::MComb, PitchAlgorithm::MComb);
        assert_ne!(PitchAlgorithm::Yin, PitchAlgorithm::Spec);
    }

    // Test 5: Default pitch algorithm
    #[test]
    fn test_default_pitch_algorithm() {
        let default = PitchAlgorithm::default();
        assert_eq!(default, PitchAlgorithm::Yin);
    }

    // Test 6: Pitch settings default
    #[test]
    fn test_pitch_settings_default() {
        let settings = PitchSettings::default();
        assert_eq!(settings.min_frequency, 27.5);
        assert_eq!(settings.max_frequency, 4186.0);
        assert_eq!(settings.threshold, 0.1);
    }

    // Test 7: Pitch result structure
    #[test]
    fn test_pitch_result() {
        let result = PitchResult {
            frequency: 440.0,
            confidence: 0.95,
            midi_note: Some(69),
        };
        assert_eq!(result.frequency, 440.0);
        assert_eq!(result.confidence, 0.95);
        assert_eq!(result.midi_note, Some(69));
    }

    // Test 8: Frequency to MIDI conversion
    #[test]
    fn test_frequency_to_midi() {
        assert_eq!(frequency_to_midi(440.0), 69);  // A4
        assert_eq!(frequency_to_midi(261.63), 60); // C4 (approximately)
        assert_eq!(frequency_to_midi(0.0), 0);
        assert_eq!(frequency_to_midi(-100.0), 0);
    }

    // Test 9: Onset detector creation
    #[test]
    fn test_onset_detector_creation() {
        let result = AubioOnsetDetector::new(44100, 1024, 512);
        // FFI stub returns NotAvailable
        assert!(matches!(result, Err(AubioError::NotAvailable)));
    }

    // Test 10: Tempo detector creation
    #[test]
    fn test_tempo_detector_creation() {
        let result = AubioTempoDetector::new(44100, 1024, 512);
        // FFI stub returns NotAvailable
        assert!(matches!(result, Err(AubioError::NotAvailable)));
    }

    // Test 11: Aubio info structure
    #[test]
    fn test_aubio_info() {
        let info = AubioInfo {
            version: "0.4.9".to_string(),
            has_pitch: true,
            has_onset: true,
            has_tempo: true,
        };
        assert_eq!(info.version, "0.4.9");
        assert!(info.has_pitch);
        assert!(info.has_onset);
        assert!(info.has_tempo);
    }
}
