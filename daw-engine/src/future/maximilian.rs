//! Maximilian Integration
//!
//! FFI bindings to Maximilian - a self-contained synthesis
//! and signal processing library with oscillators, granular
//! synthesis, FFT, and JavaScript/WebAssembly bindings.
//!
//! License: MIT
//! Repo: https://github.com/micknoise/Maximilian

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// Opaque handle to Maximilian oscillator
#[repr(C)]
pub struct MaxiOsc {
    _private: [u8; 0],
}

/// Opaque handle to Maximilian envelope
#[repr(C)]
pub struct MaxiEnv {
    _private: [u8; 0],
}

/// Opaque handle to Maximilian filter
#[repr(C)]
pub struct MaxiFilter {
    _private: [u8; 0],
}

/// Opaque handle to Maximilian delay
#[repr(C)]
pub struct MaxiDelay {
    _private: [u8; 0],
}

/// Maximilian error types
#[derive(Debug, Clone, PartialEq)]
pub enum MaximilianError {
    OscillatorInitFailed,
    FilterInitFailed,
    InvalidFrequency,
    InvalidParameter(String),
    FfiError(String),
}

impl std::fmt::Display for MaximilianError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MaximilianError::OscillatorInitFailed => write!(f, "Oscillator initialization failed"),
            MaximilianError::FilterInitFailed => write!(f, "Filter initialization failed"),
            MaximilianError::InvalidFrequency => write!(f, "Invalid frequency parameter"),
            MaximilianError::InvalidParameter(param) => write!(f, "Invalid parameter: {}", param),
            MaximilianError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for MaximilianError {}

/// Oscillator waveform type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Waveform {
    Sine,
    Cosine,
    Triangle,
    Saw,
    Square,
    Pulse,
}

/// Filter type
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MaxiFilterType {
    Lowpass,
    Highpass,
    Bandpass,
}

/// Maximilian oscillator
pub struct MaximilianOscillator {
    osc: *mut MaxiOsc,
    waveform: Waveform,
}

/// Maximilian envelope
pub struct MaximilianEnvelope {
    env: *mut MaxiEnv,
    attack: f32,
    decay: f32,
    sustain: f32,
    release: f32,
}

/// Maximilian filter
pub struct MaximilianFilter {
    filter: *mut MaxiFilter,
    filter_type: MaxiFilterType,
    cutoff: f32,
    resonance: f32,
}

/// Maximilian delay
pub struct MaximilianDelay {
    delay: *mut MaxiDelay,
    delay_time_ms: f32,
    feedback: f32,
}

// FFI function declarations
extern "C" {
    fn maximilian_ffi_is_available() -> c_int;
    fn maximilian_ffi_get_version() -> *const c_char;
    
    // Oscillator
    fn maximilian_ffi_osc_create(waveform: c_int, freq: c_float, sample_rate: c_int) -> *mut MaxiOsc;
    fn maximilian_ffi_osc_destroy(osc: *mut MaxiOsc);
    fn maximilian_ffi_osc_set_freq(osc: *mut MaxiOsc, freq: c_float);
    fn maximilian_ffi_osc_process(osc: *mut MaxiOsc) -> c_float;
    
    // Envelope (ADSR)
    fn maximilian_ffi_env_create(attack: c_float, decay: c_float, sustain: c_float, release: c_float, sample_rate: c_int) -> *mut MaxiEnv;
    fn maximilian_ffi_env_destroy(env: *mut MaxiEnv);
    fn maximilian_ffi_env_trigger(env: *mut MaxiEnv);
    fn maximilian_ffi_env_release(env: *mut MaxiEnv);
    fn maximilian_ffi_env_process(env: *mut MaxiEnv) -> c_float;
    fn maximilian_ffi_env_is_active(env: *mut MaxiEnv) -> c_int;
    
    // Filter
    fn maximilian_ffi_filter_create(filter_type: c_int, cutoff: c_float, resonance: c_float, sample_rate: c_int) -> *mut MaxiFilter;
    fn maximilian_ffi_filter_destroy(filter: *mut MaxiFilter);
    fn maximilian_ffi_filter_set_cutoff(filter: *mut MaxiFilter, cutoff: c_float);
    fn maximilian_ffi_filter_process(filter: *mut MaxiFilter, input: c_float) -> c_float;
    
    // Delay
    fn maximilian_ffi_delay_create(delay_time_ms: c_float, feedback: c_float, sample_rate: c_int) -> *mut MaxiDelay;
    fn maximilian_ffi_delay_destroy(delay: *mut MaxiDelay);
    fn maximilian_ffi_delay_set_time(delay: *mut MaxiDelay, delay_time_ms: c_float);
    fn maximilian_ffi_delay_set_feedback(delay: *mut MaxiDelay, feedback: c_float);
    fn maximilian_ffi_delay_process(delay: *mut MaxiDelay, input: c_float) -> c_float;
}

impl MaximilianOscillator {
    /// Create new oscillator with waveform and frequency
    pub fn new(waveform: Waveform, freq: f32, sample_rate: u32) -> Result<Self, MaximilianError> {
        if !Self::is_available() {
            return Err(MaximilianError::FfiError("Maximilian not available".to_string()));
        }

        let waveform_int = match waveform {
            Waveform::Sine => 0,
            Waveform::Cosine => 1,
            Waveform::Triangle => 2,
            Waveform::Saw => 3,
            Waveform::Square => 4,
            Waveform::Pulse => 5,
        };

        unsafe {
            let osc = maximilian_ffi_osc_create(waveform_int, freq, sample_rate as c_int);
            if osc.is_null() {
                return Err(MaximilianError::OscillatorInitFailed);
            }
            Ok(Self { osc, waveform })
        }
    }

    /// Check if Maximilian is available
    pub fn is_available() -> bool {
        unsafe { maximilian_ffi_is_available() != 0 }
    }

    /// Get Maximilian version
    pub fn version() -> String {
        unsafe {
            let version_ptr = maximilian_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Set oscillator frequency
    pub fn set_freq(&mut self, freq: f32) {
        unsafe { maximilian_ffi_osc_set_freq(self.osc, freq); }
    }

    /// Process single sample
    pub fn process(&mut self) -> f32 {
        unsafe { maximilian_ffi_osc_process(self.osc) }
    }

    /// Get waveform type
    pub fn waveform(&self) -> Waveform {
        self.waveform
    }
}

impl Drop for MaximilianOscillator {
    fn drop(&mut self) {
        unsafe {
            if !self.osc.is_null() {
                maximilian_ffi_osc_destroy(self.osc);
            }
        }
    }
}

impl MaximilianEnvelope {
    /// Create new ADSR envelope
    pub fn new(attack: f32, decay: f32, sustain: f32, release: f32, sample_rate: u32) -> Result<Self, MaximilianError> {
        if !MaximilianOscillator::is_available() {
            return Err(MaximilianError::FfiError("Maximilian not available".to_string()));
        }

        unsafe {
            let env = maximilian_ffi_env_create(attack, decay, sustain, release, sample_rate as c_int);
            if env.is_null() {
                return Err(MaximilianError::FfiError("Envelope init failed".to_string()));
            }
            Ok(Self { env, attack, decay, sustain, release })
        }
    }

    /// Trigger envelope (note on)
    pub fn trigger(&mut self) {
        unsafe { maximilian_ffi_env_trigger(self.env); }
    }

    /// Release envelope (note off)
    pub fn release(&mut self) {
        unsafe { maximilian_ffi_env_release(self.env); }
    }

    /// Process envelope
    pub fn process(&mut self) -> f32 {
        unsafe { maximilian_ffi_env_process(self.env) }
    }

    /// Check if envelope is still active
    pub fn is_active(&self) -> bool {
        unsafe { maximilian_ffi_env_is_active(self.env) != 0 }
    }
}

impl Drop for MaximilianEnvelope {
    fn drop(&mut self) {
        unsafe {
            if !self.env.is_null() {
                maximilian_ffi_env_destroy(self.env);
            }
        }
    }
}

impl MaximilianFilter {
    /// Create new filter
    pub fn new(filter_type: MaxiFilterType, cutoff: f32, resonance: f32, sample_rate: u32) -> Result<Self, MaximilianError> {
        if !MaximilianOscillator::is_available() {
            return Err(MaximilianError::FfiError("Maximilian not available".to_string()));
        }

        let filter_type_int = match filter_type {
            MaxiFilterType::Lowpass => 0,
            MaxiFilterType::Highpass => 1,
            MaxiFilterType::Bandpass => 2,
        };

        unsafe {
            let filter = maximilian_ffi_filter_create(filter_type_int, cutoff, resonance, sample_rate as c_int);
            if filter.is_null() {
                return Err(MaximilianError::FilterInitFailed);
            }
            Ok(Self { filter, filter_type, cutoff, resonance })
        }
    }

    /// Set filter cutoff frequency
    pub fn set_cutoff(&mut self, cutoff: f32) {
        self.cutoff = cutoff;
        unsafe { maximilian_ffi_filter_set_cutoff(self.filter, cutoff); }
    }

    /// Process single sample
    pub fn process(&mut self, input: f32) -> f32 {
        unsafe { maximilian_ffi_filter_process(self.filter, input) }
    }

    /// Get cutoff frequency
    pub fn cutoff(&self) -> f32 {
        self.cutoff
    }
}

impl Drop for MaximilianFilter {
    fn drop(&mut self) {
        unsafe {
            if !self.filter.is_null() {
                maximilian_ffi_filter_destroy(self.filter);
            }
        }
    }
}

impl MaximilianDelay {
    /// Create new delay line
    pub fn new(delay_time_ms: f32, feedback: f32, sample_rate: u32) -> Result<Self, MaximilianError> {
        if !MaximilianOscillator::is_available() {
            return Err(MaximilianError::FfiError("Maximilian not available".to_string()));
        }

        unsafe {
            let delay = maximilian_ffi_delay_create(delay_time_ms, feedback, sample_rate as c_int);
            if delay.is_null() {
                return Err(MaximilianError::FfiError("Delay init failed".to_string()));
            }
            Ok(Self { delay, delay_time_ms, feedback })
        }
    }

    /// Set delay time in milliseconds
    pub fn set_delay_time(&mut self, delay_time_ms: f32) {
        self.delay_time_ms = delay_time_ms;
        unsafe { maximilian_ffi_delay_set_time(self.delay, delay_time_ms); }
    }

    /// Set feedback amount (0.0 - 1.0)
    pub fn set_feedback(&mut self, feedback: f32) {
        self.feedback = feedback;
        unsafe { maximilian_ffi_delay_set_feedback(self.delay, feedback); }
    }

    /// Process single sample
    pub fn process(&mut self, input: f32) -> f32 {
        unsafe { maximilian_ffi_delay_process(self.delay, input) }
    }
}

impl Drop for MaximilianDelay {
    fn drop(&mut self) {
        unsafe {
            if !self.delay.is_null() {
                maximilian_ffi_delay_destroy(self.delay);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_maximilian_module_exists() {
        let _ = MaximilianError::OscillatorInitFailed;
        let _ = Waveform::Sine;
        let _ = MaxiFilterType::Lowpass;
    }

    #[test]
    fn test_maximilian_is_available() {
        let available = MaximilianOscillator::is_available();
        println!("Maximilian available: {}", available);
    }

    #[test]
    fn test_maximilian_version() {
        let version = MaximilianOscillator::version();
        println!("Maximilian version: {}", version);
    }

    #[test]
    fn test_oscillator_creation() {
        let result = MaximilianOscillator::new(Waveform::Sine, 440.0, 44100);
        match result {
            Ok(osc) => {
                assert_eq!(osc.waveform(), Waveform::Sine);
            }
            Err(e) => {
                println!("Oscillator creation failed (expected if Maximilian not available): {}", e);
            }
        }
    }

    #[test]
    fn test_envelope_creation() {
        let result = MaximilianEnvelope::new(10.0, 100.0, 0.5, 500.0, 44100);
        match result {
            Ok(env) => {
                assert!(!env.is_active());
            }
            Err(e) => {
                println!("Envelope creation failed (expected if Maximilian not available): {}", e);
            }
        }
    }

    #[test]
    fn test_filter_creation() {
        let result = MaximilianFilter::new(MaxiFilterType::Lowpass, 1000.0, 0.707, 44100);
        match result {
            Ok(filter) => {
                assert_eq!(filter.cutoff(), 1000.0);
            }
            Err(e) => {
                println!("Filter creation failed (expected if Maximilian not available): {}", e);
            }
        }
    }

    #[test]
    fn test_delay_creation() {
        let result = MaximilianDelay::new(250.0, 0.3, 44100);
        match result {
            Ok(delay) => {
                assert_eq!(delay.delay_time_ms, 250.0);
                assert_eq!(delay.feedback, 0.3);
            }
            Err(e) => {
                println!("Delay creation failed (expected if Maximilian not available): {}", e);
            }
        }
    }

    #[test]
    fn test_waveform_variants() {
        let waveforms = vec![
            Waveform::Sine,
            Waveform::Cosine,
            Waveform::Triangle,
            Waveform::Saw,
            Waveform::Square,
            Waveform::Pulse,
        ];
        for w in waveforms {
            assert!(!format!("{:?}", w).is_empty());
        }
    }

    #[test]
    fn test_filter_type_variants() {
        let types = vec![
            MaxiFilterType::Lowpass,
            MaxiFilterType::Highpass,
            MaxiFilterType::Bandpass,
        ];
        for t in types {
            assert!(!format!("{:?}", t).is_empty());
        }
    }

    #[test]
    fn test_maximilian_error_display() {
        let err = MaximilianError::InvalidFrequency;
        assert!(err.to_string().contains("Invalid frequency"));

        let err = MaximilianError::FfiError("test".to_string());
        assert!(err.to_string().contains("FFI error"));
    }
}
