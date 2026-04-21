//! Transport clock
//! 
//! Sample-accurate timing for transport position.

/// Transport clock for timing
pub struct TransportClock {
    sample_rate: u32,
    tempo: f32,
    samples_elapsed: u64,
}

impl TransportClock {
    /// Create new transport clock
    pub fn new(sample_rate: u32) -> Self {
        Self {
            sample_rate,
            tempo: 120.0,
            samples_elapsed: 0,
        }
    }
    
    /// Set tempo in BPM
    pub fn set_tempo(&mut self, tempo: f32) {
        self.tempo = tempo;
    }
    
    /// Advance clock by sample count
    pub fn advance(&mut self, samples: u64) {
        self.samples_elapsed += samples;
    }
    
    /// Get current position in beats
    pub fn beats(&self) -> f64 {
        let seconds = self.samples_elapsed as f64 / self.sample_rate as f64;
        let beats = seconds * (self.tempo as f64 / 60.0);
        beats
    }
}
