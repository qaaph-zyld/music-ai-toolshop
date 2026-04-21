//! Audio callback for real-time processing
//! 
//! Handles the audio thread callback from CPAL,
//! calling generators and mixers to fill output buffers.

use crate::mixer::Mixer;
use crate::generators::SineWave;
use crate::sample_player::SamplePlayer;

/// Profiling data for a single process callback
#[derive(Debug, Clone, Copy, Default)]
pub struct CallbackMetrics {
    /// Total processing time in nanoseconds
    pub processing_time_ns: u64,
    /// Number of samples processed
    pub sample_count: usize,
    /// CPU usage percentage (0.0 - 100.0)
    pub cpu_usage_percent: f32,
}

/// Audio callback handler using the mixer for multiple sources
pub struct AudioCallback {
    mixer: Mixer,
    #[allow(dead_code)]
    channels: u16,
    /// Profiling metrics from last process call
    pub last_metrics: CallbackMetrics,
    /// Sample rate for timing calculations
    sample_rate: u32,
}

impl AudioCallback {
    /// Create new audio callback with an empty mixer
    pub fn new(sample_rate: u32, channels: u16) -> Self {
        Self { 
            mixer: Mixer::new(channels as usize),
            channels,
            last_metrics: CallbackMetrics::default(),
            sample_rate,
        }
    }
    
    /// Add a sine wave generator to the mixer
    pub fn add_sine_wave(&mut self, frequency: f32, amplitude: f32, sample_rate: u32) {
        let mut sine = SineWave::new(frequency, amplitude);
        sine.set_sample_rate(sample_rate);
        self.mixer.add_source(Box::new(sine));
    }
    
    /// Add a sample player to the mixer
    pub fn add_sample_player(&mut self, player: SamplePlayer) {
        self.mixer.add_source(Box::new(player));
    }
    
    /// Get mutable reference to the mixer for direct control
    pub fn mixer(&mut self) -> &mut Mixer {
        &mut self.mixer
    }
    
    /// Process audio buffer - mixes all sources with profiling
    pub fn process(&mut self, output: &mut [f32]) {
        let start = std::time::Instant::now();
        
        self.mixer.process(output);
        
        let elapsed = start.elapsed();
        let processing_time_ns = elapsed.as_nanos() as u64;
        
        // Calculate theoretical time available for this buffer
        // At sample_rate Hz, each sample takes 1/sample_rate seconds
        let buffer_duration_us = (output.len() as f64 / self.channels as f64) * 1_000_000.0 / self.sample_rate as f64;
        let processing_time_us = processing_time_ns as f64 / 1000.0;
        
        self.last_metrics = CallbackMetrics {
            processing_time_ns,
            sample_count: output.len() / self.channels as usize,
            cpu_usage_percent: (processing_time_us / buffer_duration_us * 100.0) as f32,
        };
    }
    
    /// Clear all sources from the mixer
    pub fn clear(&mut self) {
        self.mixer.clear();
    }
    
    /// Get number of active sources
    pub fn source_count(&self) -> usize {
        self.mixer.source_count()
    }
    
    /// Get profiling metrics from last process call
    pub fn last_metrics(&self) -> &CallbackMetrics {
        &self.last_metrics
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sample::Sample;

    #[test]
    fn test_callback_creation() {
        let callback = AudioCallback::new(48000, 2);
        assert_eq!(callback.source_count(), 0);
    }

    #[test]
    fn test_callback_add_sine() {
        let mut callback = AudioCallback::new(48000, 2);
        callback.add_sine_wave(440.0, 0.5, 48000);
        assert_eq!(callback.source_count(), 1);
    }

    #[test]
    fn test_callback_add_sample_player() {
        let mut callback = AudioCallback::new(48000, 2);
        let data = vec![1.0f32, 1.0, 1.0, 1.0];
        let sample = Sample::from_raw(data, 1, 48000);
        let player = SamplePlayer::new(sample, 2);
        callback.add_sample_player(player);
        assert_eq!(callback.source_count(), 1);
    }

    #[test]
    fn test_callback_process_silence_with_no_sources() {
        let mut callback = AudioCallback::new(48000, 2);
        let mut output = vec![1.0f32; 4];
        callback.process(&mut output);
        // Should be silence when no sources
        assert!(output.iter().all(|&s| s == 0.0));
    }

    #[test]
    fn test_callback_process_with_sine() {
        let mut callback = AudioCallback::new(48000, 2);
        callback.add_sine_wave(440.0, 0.5, 48000);
        let mut output = vec![0.0f32; 128]; // 64 frames, stereo
        callback.process(&mut output);
        // Should have non-zero output
        assert!(output.iter().any(|&s| s != 0.0));
    }

    #[test]
    fn test_callback_clear() {
        let mut callback = AudioCallback::new(48000, 2);
        callback.add_sine_wave(440.0, 0.5, 48000);
        callback.clear();
        assert_eq!(callback.source_count(), 0);
    }

    #[test]
    fn test_callback_profiling_metrics() {
        let mut callback = AudioCallback::new(48000, 2);
        callback.add_sine_wave(440.0, 0.5, 48000);
        
        let mut output = vec![0.0f32; 128]; // 64 frames, stereo
        callback.process(&mut output);
        
        // Check that metrics were recorded
        let metrics = callback.last_metrics();
        assert!(metrics.processing_time_ns > 0);
        assert_eq!(metrics.sample_count, 64);
        assert!(metrics.cpu_usage_percent >= 0.0);
        assert!(metrics.cpu_usage_percent <= 100.0);
    }
}
