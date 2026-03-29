//! Signal generators
//! 
//! Oscillators and noise generators for audio synthesis.

/// Sine wave oscillator
pub struct SineWave {
    frequency: f32,
    pub(crate) amplitude: f32,
    phase: f32,
    sample_rate: u32,
}

impl SineWave {
    /// Create new sine wave generator
    pub fn new(frequency: f32, amplitude: f32) -> Self {
        Self {
            frequency,
            amplitude,
            phase: 0.0,
            sample_rate: 48000,
        }
    }
    
    /// Set sample rate
    pub fn set_sample_rate(&mut self, sample_rate: u32) {
        self.sample_rate = sample_rate;
    }
    
    /// Generate next sample
    pub fn next_sample(&mut self) -> f32 {
        let value = (self.phase * 2.0 * std::f32::consts::PI).sin() * self.amplitude;
        self.phase += self.frequency / self.sample_rate as f32;
        if self.phase > 1.0 {
            self.phase -= 1.0;
        }
        value
    }
    
    /// Fill buffer with samples
    pub fn process(&mut self, output: &mut [f32]) {
        for sample in output {
            *sample = self.next_sample();
        }
    }
}
