//! Audio callback for real-time processing
//! 
//! Handles the audio thread callback from CPAL,
//! calling generators and mixers to fill output buffers.

use crate::generators::SineWave;

/// Audio callback handler
pub struct AudioCallback {
    sample_rate: u32,
    channels: u16,
    generator: SineWave,
}

impl AudioCallback {
    /// Create new audio callback
    pub fn new(sample_rate: u32, channels: u16) -> Self {
        let mut generator = SineWave::new(440.0, 0.5);
        generator.set_sample_rate(sample_rate);
        Self { 
            sample_rate, 
            channels, 
            generator,
        }
    }
    
    /// Process audio buffer - generates samples
    pub fn process(&mut self, output: &mut [f32]) {
        for sample in output.chunks_mut(self.channels as usize) {
            let value = self.generator.next_sample();
            for ch in sample {
                *ch = value;
            }
        }
    }
}
