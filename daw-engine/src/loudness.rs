//! Loudness metering using libebur128 (EBU R 128 standard)
//!
//! Provides integrated, momentary, and short-term loudness measurements
//! plus loudness range (LRA) calculation.

use ebur128::{EbuR128, Mode};

/// Loudness meter state wrapping ebur128
pub struct LoudnessMeter {
    ebu: EbuR128,
    sample_rate: u32,
    channels: u32,
}

/// Loudness measurement readings
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LoudnessReading {
    /// Momentary loudness (3-second window) in LUFS
    pub momentary_lufs: f64,
    /// Short-term loudness (10-second window) in LUFS  
    pub short_term_lufs: f64,
    /// Integrated loudness (entire measurement) in LUFS
    pub integrated_lufs: f64,
    /// Loudness Range in LU
    pub loudness_range_lu: f64,
    /// True peak in dBTP
    pub true_peak_db: f64,
}

impl LoudnessMeter {
    /// Create a new loudness meter
    /// 
    /// # Arguments
    /// * `sample_rate` - Sample rate in Hz (e.g., 48000)
    /// * `channels` - Number of channels (1 for mono, 2 for stereo)
    pub fn new(sample_rate: u32, channels: u32) -> Result<Self, LoudnessError> {
        // Validate parameters
        if sample_rate == 0 {
            return Err(LoudnessError::InvalidSampleRate(sample_rate));
        }
        if channels == 0 || channels > 8 {
            return Err(LoudnessError::InvalidChannels(channels));
        }
        
        // Create ebur128 instance with all measurement modes
        let mode = Mode::all();
        let ebu = EbuR128::new(channels, sample_rate, mode)
            .map_err(|e| LoudnessError::Internal(format!("{:?}", e)))?;
        
        Ok(Self {
            ebu,
            sample_rate,
            channels,
        })
    }
    
    /// Process audio samples and update loudness measurements
    /// 
    /// # Arguments
    /// * `samples` - Interleaved audio samples (f32)
    pub fn process(&mut self, samples: &[f32]) {
        // ebur128 expects f64 samples
        let samples_f64: Vec<f64> = samples.iter().map(|&s| s as f64).collect();
        
        // Feed samples to ebur128
        self.ebu.add_frames_f64(&samples_f64)
            .expect("ebur128 should accept valid samples");
    }
    
    /// Get current loudness readings
    pub fn reading(&self) -> LoudnessReading {
        LoudnessReading {
            momentary_lufs: self.ebu.loudness_momentary().unwrap_or(-70.0),
            short_term_lufs: self.ebu.loudness_shortterm().unwrap_or(-70.0),
            integrated_lufs: self.ebu.loudness_global().unwrap_or(-70.0),
            loudness_range_lu: self.ebu.loudness_range().unwrap_or(0.0),
            true_peak_db: self.max_true_peak_db(),
        }
    }
    
    /// Get maximum true peak across all channels in dBTP
    fn max_true_peak_db(&self) -> f64 {
        let mut max_peak = f64::NEG_INFINITY;
        
        for ch in 0..self.channels {
            if let Ok(peak) = self.ebu.true_peak(ch) {
                // Convert linear to dB
                let peak_db = 20.0 * peak.log10();
                if peak_db > max_peak {
                    max_peak = peak_db;
                }
            }
        }
        
        if max_peak.is_finite() {
            max_peak
        } else {
            -70.0 // Silence level
        }
    }
    
    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
    
    /// Get channel count
    pub fn channels(&self) -> u32 {
        self.channels
    }
    
    /// Reset the meter state
    pub fn reset(&mut self) {
        self.ebu.reset();
    }
}

/// Errors that can occur during loudness measurement
#[derive(Debug, Clone, PartialEq)]
pub enum LoudnessError {
    /// Invalid sample rate
    InvalidSampleRate(u32),
    /// Invalid channel count
    InvalidChannels(u32),
    /// Internal error from libebur128
    Internal(String),
}

impl std::fmt::Display for LoudnessError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LoudnessError::InvalidSampleRate(sr) => {
                write!(f, "Invalid sample rate: {}", sr)
            }
            LoudnessError::InvalidChannels(ch) => {
                write!(f, "Invalid channel count: {}", ch)
            }
            LoudnessError::Internal(msg) => {
                write!(f, "Internal error: {}", msg)
            }
        }
    }
}

impl std::error::Error for LoudnessError {}
