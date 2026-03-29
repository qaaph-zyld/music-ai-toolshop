//! Audio mixer
//! 
//! Combines multiple audio sources with gain control.

use crate::generators::SineWave;

/// Audio mixer with multiple sources
pub struct Mixer {
    channels: usize,
    sources: Vec<Box<dyn AudioSource>>,
}

/// Trait for audio sources
pub trait AudioSource {
    fn process(&mut self, output: &mut [f32]);
    fn gain(&self) -> f32;
    fn set_gain(&mut self, gain: f32);
}

impl AudioSource for SineWave {
    fn process(&mut self, output: &mut [f32]) {
        SineWave::process(self, output);
    }
    
    fn gain(&self) -> f32 {
        // Use amplitude as gain
        1.0
    }
    
    fn set_gain(&mut self, gain: f32) {
        // Apply gain by adjusting amplitude
        // Original amplitude was set at construction
        // This is a simplified approach - ideally we'd store base_amplitude separately
        self.amplitude = gain;
    }
}

impl Mixer {
    /// Create new mixer
    pub fn new(channels: usize) -> Self {
        Self {
            channels,
            sources: Vec::new(),
        }
    }
    
    /// Add audio source
    pub fn add_source(&mut self, source: Box<dyn AudioSource>) {
        self.sources.push(source);
    }
    
    /// Process audio - mix all sources
    pub fn process(&mut self, output: &mut [f32]) {
        // Clear output
        for sample in output.iter_mut() {
            *sample = 0.0;
        }
        
        // Mix all sources
        let frames = output.len() / self.channels;
        for source in &mut self.sources {
            let mut temp = vec![0.0f32; output.len()];
            source.process(&mut temp);
            
            for (out, src) in output.iter_mut().zip(temp.iter()) {
                *out += src * source.gain();
            }
        }
    }
}
