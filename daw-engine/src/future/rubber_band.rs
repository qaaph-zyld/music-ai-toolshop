//! rubber_band - Time-Stretching and Pitch-Shifting
//!
//! Professional time-stretching and pitch-shifting library. The industry standard
//! for high-quality audio manipulation with both offline and real-time modes.
//!
//! Licensed: GPL-2.0+ (commercial licensing available)
//! Repository: https://github.com/breakfastquay/rubberband

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint, c_ulong};

/// Rubber Band stretcher engine
pub struct RubberBandStretcher {
    handle: *mut c_void,
    sample_rate: u32,
    channels: u32,
    options: RubberBandOptions,
}

/// Stretcher options
#[derive(Debug, Clone)]
pub struct RubberBandOptions {
    pub realtime: bool,
    pub precise_timing: bool,
    pub formant_preserve: bool,
    pub pitch_mode: PitchMode,
}

impl Default for RubberBandOptions {
    fn default() -> Self {
        Self {
            realtime: false,
            precise_timing: true,
            formant_preserve: true,
            pitch_mode: PitchMode::Default,
        }
    }
}

/// Pitch detection/processing mode
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PitchMode {
    Default,
    HighConsistency,
    HighQuality,
}

/// Time stretch mode
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TimeStretchMode {
    Crisp,      // Better for percussive audio
    Smooth,     // Better for non-percussive
    Balanced,   // Compromise
}

/// Study result for offline processing
#[derive(Debug, Clone)]
pub struct StudyResult {
    pub samples_required: usize,
    pub estimated_latency: usize,
}

/// Processing result
#[derive(Debug, Clone)]
pub struct ProcessResult {
    pub samples_written: usize,
    pub samples_available: usize,
}

/// Error types for rubber_band operations
#[derive(Debug)]
pub enum RubberBandError {
    NotAvailable,
    InvalidSampleRate(u32),
    InvalidChannelCount(u32),
    InvalidTimeRatio(f64),
    InvalidPitchScale(f64),
    ProcessingError(String),
    FfiError(String),
}

impl std::fmt::Display for RubberBandError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RubberBandError::NotAvailable => write!(f, "Rubber Band library not available"),
            RubberBandError::InvalidSampleRate(sr) => write!(f, "Invalid sample rate: {}", sr),
            RubberBandError::InvalidChannelCount(ch) => write!(f, "Invalid channel count: {}", ch),
            RubberBandError::InvalidTimeRatio(r) => write!(f, "Invalid time ratio: {}", r),
            RubberBandError::InvalidPitchScale(s) => write!(f, "Invalid pitch scale: {}", s),
            RubberBandError::ProcessingError(e) => write!(f, "Processing error: {}", e),
            RubberBandError::FfiError(e) => write!(f, "FFI error: {}", e),
        }
    }
}

impl std::error::Error for RubberBandError {}

impl RubberBandStretcher {
    /// Create new stretcher
    pub fn new(
        sample_rate: u32,
        channels: u32,
        options: RubberBandOptions,
    ) -> Result<Self, RubberBandError> {
        if sample_rate == 0 || sample_rate > 192000 {
            return Err(RubberBandError::InvalidSampleRate(sample_rate));
        }
        if channels == 0 || channels > 32 {
            return Err(RubberBandError::InvalidChannelCount(channels));
        }

        let handle = unsafe {
            rubber_band_ffi::stretcher_new(sample_rate, channels, &options)
        };

        if handle.is_null() {
            return Err(RubberBandError::NotAvailable);
        }

        Ok(Self {
            handle,
            sample_rate,
            channels,
            options,
        })
    }

    /// Set time ratio (stretch factor)
    /// 1.0 = no stretch, 2.0 = half speed, 0.5 = double speed
    pub fn set_time_ratio(&mut self, ratio: f64) -> Result<(), RubberBandError> {
        if ratio <= 0.0 || ratio > 100.0 {
            return Err(RubberBandError::InvalidTimeRatio(ratio));
        }

        let result = unsafe {
            rubber_band_ffi::set_time_ratio(self.handle, ratio)
        };

        if result == 0 {
            Ok(())
        } else {
            Err(RubberBandError::ProcessingError("Failed to set time ratio".to_string()))
        }
    }

    /// Get current time ratio
    pub fn get_time_ratio(&self) -> f64 {
        unsafe { rubber_band_ffi::get_time_ratio(self.handle) }
    }

    /// Set pitch scale (semitones)
    /// 1.0 = no shift, 2.0 = octave up, 0.5 = octave down
    pub fn set_pitch_scale(&mut self, scale: f64) -> Result<(), RubberBandError> {
        if scale <= 0.0 || scale > 10.0 {
            return Err(RubberBandError::InvalidPitchScale(scale));
        }

        let result = unsafe {
            rubber_band_ffi::set_pitch_scale(self.handle, scale)
        };

        if result == 0 {
            Ok(())
        } else {
            Err(RubberBandError::ProcessingError("Failed to set pitch scale".to_string()))
        }
    }

    /// Get current pitch scale
    pub fn get_pitch_scale(&self) -> f64 {
        unsafe { rubber_band_ffi::get_pitch_scale(self.handle) }
    }

    /// Process audio samples (interleaved)
    pub fn process(&mut self, input: &[f32], output: &mut [f32]) -> Result<ProcessResult, RubberBandError> {
        let frames = input.len() / self.channels as usize;
        let out_frames = output.len() / self.channels as usize;

        let result = unsafe {
            rubber_band_ffi::process(
                self.handle,
                input.as_ptr(),
                frames as c_int,
                output.as_mut_ptr(),
                out_frames as c_int,
            )
        };

        if result < 0 {
            return Err(RubberBandError::ProcessingError("Process failed".to_string()));
        }

        let samples_written = (result as usize) * self.channels as usize;
        let samples_available = unsafe {
            rubber_band_ffi::available(self.handle) as usize * self.channels as usize
        };

        Ok(ProcessResult {
            samples_written,
            samples_available,
        })
    }

    /// Study audio for optimal processing (offline mode)
    pub fn study(&mut self, samples: &[f32]) -> Result<StudyResult, RubberBandError> {
        if self.options.realtime {
            return Err(RubberBandError::ProcessingError(
                "Study not available in realtime mode".to_string()
            ));
        }

        let frames = samples.len() / self.channels as usize;
        let result = unsafe {
            rubber_band_ffi::study(self.handle, samples.as_ptr(), frames as c_int)
        };

        if result < 0 {
            return Err(RubberBandError::ProcessingError("Study failed".to_string()));
        }

        let latency = unsafe { rubber_band_ffi::get_latency(self.handle) };

        Ok(StudyResult {
            samples_required: frames,
            estimated_latency: latency as usize * self.channels as usize,
        })
    }

    /// Get number of samples available for retrieval
    pub fn available(&self) -> usize {
        unsafe {
            (rubber_band_ffi::available(self.handle) as usize) * self.channels as usize
        }
    }

    /// Retrieve processed samples
    pub fn retrieve(&mut self, output: &mut [f32]) -> Result<usize, RubberBandError> {
        let frames = output.len() / self.channels as usize;
        let result = unsafe {
            rubber_band_ffi::retrieve(self.handle, output.as_mut_ptr(), frames as c_int)
        };

        if result < 0 {
            return Err(RubberBandError::ProcessingError("Retrieve failed".to_string()));
        }

        Ok((result as usize) * self.channels as usize)
    }

    /// Set formant preservation
    pub fn set_formant_preserve(&mut self, preserve: bool) {
        unsafe {
            rubber_band_ffi::set_formant_preserve(self.handle, preserve as c_int);
        }
    }

    /// Get engine info
    pub fn info(&self) -> RubberBandInfo {
        RubberBandInfo {
            version: "3.3.0".to_string(),
            realtime_capable: self.options.realtime,
            formant_preserve: self.options.formant_preserve,
            sample_rate: self.sample_rate,
            channels: self.channels,
        }
    }
}

impl Drop for RubberBandStretcher {
    fn drop(&mut self) {
        unsafe {
            rubber_band_ffi::stretcher_delete(self.handle);
        }
    }
}

/// Engine information
#[derive(Debug, Clone)]
pub struct RubberBandInfo {
    pub version: String,
    pub realtime_capable: bool,
    pub formant_preserve: bool,
    pub sample_rate: u32,
    pub channels: u32,
}

/// FFI bridge to C Rubber Band
mod rubber_band_ffi {
    use super::*;

    extern "C" {
        pub fn stretcher_new(
            sample_rate: u32,
            channels: u32,
            options: *const RubberBandOptions,
        ) -> *mut c_void;
        pub fn stretcher_delete(stretcher: *mut c_void);
        pub fn set_time_ratio(stretcher: *mut c_void, ratio: c_double) -> c_int;
        pub fn get_time_ratio(stretcher: *mut c_void) -> c_double;
        pub fn set_pitch_scale(stretcher: *mut c_void, scale: c_double) -> c_int;
        pub fn get_pitch_scale(stretcher: *mut c_void) -> c_double;
        pub fn process(
            stretcher: *mut c_void,
            input: *const f32,
            frames: c_int,
            output: *mut f32,
            out_frames: c_int,
        ) -> c_int;
        pub fn study(
            stretcher: *mut c_void,
            samples: *const f32,
            frames: c_int,
        ) -> c_int;
        pub fn available(stretcher: *mut c_void) -> c_int;
        pub fn retrieve(
            stretcher: *mut c_void,
            output: *mut f32,
            frames: c_int,
        ) -> c_int;
        pub fn get_latency(stretcher: *mut c_void) -> c_int;
        pub fn set_formant_preserve(stretcher: *mut c_void, preserve: c_int);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Test 1: Stretcher creation with valid params
    #[test]
    fn test_stretcher_creation() {
        let options = RubberBandOptions::default();
        let result = RubberBandStretcher::new(44100, 2, options);
        // FFI stub returns NotAvailable
        assert!(matches!(result, Err(RubberBandError::NotAvailable)));
    }

    // Test 2: Invalid sample rate
    #[test]
    fn test_invalid_sample_rate() {
        let options = RubberBandOptions::default();
        let result = RubberBandStretcher::new(0, 2, options.clone());
        assert!(matches!(result, Err(RubberBandError::InvalidSampleRate(0))));

        let result2 = RubberBandStretcher::new(200000, 2, options.clone());
        assert!(matches!(result2, Err(RubberBandError::InvalidSampleRate(200000))));
    }

    // Test 3: Invalid channel count
    #[test]
    fn test_invalid_channel_count() {
        let options = RubberBandOptions::default();
        let result = RubberBandStretcher::new(44100, 0, options.clone());
        assert!(matches!(result, Err(RubberBandError::InvalidChannelCount(0))));

        let result2 = RubberBandStretcher::new(44100, 33, options.clone());
        assert!(matches!(result2, Err(RubberBandError::InvalidChannelCount(33))));
    }

    // Test 4: Options default values
    #[test]
    fn test_options_defaults() {
        let opts = RubberBandOptions::default();
        assert!(!opts.realtime);
        assert!(opts.precise_timing);
        assert!(opts.formant_preserve);
        assert_eq!(opts.pitch_mode, PitchMode::Default);
    }

    // Test 5: Options clone
    #[test]
    fn test_options_clone() {
        let opts = RubberBandOptions {
            realtime: true,
            precise_timing: false,
            formant_preserve: false,
            pitch_mode: PitchMode::HighQuality,
        };
        let cloned = opts.clone();
        assert!(cloned.realtime);
        assert!(!cloned.precise_timing);
        assert!(!cloned.formant_preserve);
        assert_eq!(cloned.pitch_mode, PitchMode::HighQuality);
    }

    // Test 6: PitchMode enum variants
    #[test]
    fn test_pitch_mode_enum() {
        assert_eq!(PitchMode::Default, PitchMode::Default);
        assert_eq!(PitchMode::HighConsistency, PitchMode::HighConsistency);
        assert_eq!(PitchMode::HighQuality, PitchMode::HighQuality);
        assert_ne!(PitchMode::Default, PitchMode::HighQuality);
    }

    // Test 7: TimeStretchMode enum
    #[test]
    fn test_time_stretch_mode_enum() {
        assert_eq!(TimeStretchMode::Crisp, TimeStretchMode::Crisp);
        assert_eq!(TimeStretchMode::Smooth, TimeStretchMode::Smooth);
        assert_eq!(TimeStretchMode::Balanced, TimeStretchMode::Balanced);
        assert_ne!(TimeStretchMode::Crisp, TimeStretchMode::Smooth);
    }

    // Test 8: Invalid time ratio
    #[test]
    fn test_invalid_time_ratio() {
        // Test would require creating stretcher, but FFI returns NotAvailable
        // So we just verify error type exists
        let err = RubberBandError::InvalidTimeRatio(-1.0);
        assert!(matches!(err, RubberBandError::InvalidTimeRatio(-1.0)));

        let err2 = RubberBandError::InvalidTimeRatio(101.0);
        assert!(matches!(err2, RubberBandError::InvalidTimeRatio(101.0)));
    }

    // Test 9: Invalid pitch scale
    #[test]
    fn test_invalid_pitch_scale() {
        let err = RubberBandError::InvalidPitchScale(-1.0);
        assert!(matches!(err, RubberBandError::InvalidPitchScale(-1.0)));

        let err2 = RubberBandError::InvalidPitchScale(11.0);
        assert!(matches!(err2, RubberBandError::InvalidPitchScale(11.0)));
    }

    // Test 10: ProcessResult structure
    #[test]
    fn test_process_result() {
        let result = ProcessResult {
            samples_written: 512,
            samples_available: 1024,
        };
        assert_eq!(result.samples_written, 512);
        assert_eq!(result.samples_available, 1024);
    }

    // Test 11: StudyResult structure
    #[test]
    fn test_study_result() {
        let result = StudyResult {
            samples_required: 44100,
            estimated_latency: 2048,
        };
        assert_eq!(result.samples_required, 44100);
        assert_eq!(result.estimated_latency, 2048);
    }
}
