//! Audio mixer
//! 
//! Combines multiple audio sources with gain control.

use crate::generators::SineWave;
use crate::sample_player::SamplePlayer;
use crate::plugin::PluginChain;
use crate::loudness::{LoudnessMeter, LoudnessReading};
use crate::ffi_bridge::invoke_meter_callback;

/// Audio mixer with multiple sources and loudness metering
pub struct Mixer {
    #[allow(dead_code)]
    channels: usize,
    sources: Vec<Box<dyn AudioSource>>,
    loudness_meter: Option<LoudnessMeter>,
    sample_rate: u32,
    track_peak_levels: Vec<f32>,
}

/// Trait for audio sources
pub trait AudioSource: Send {
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
        self.amplitude = gain;
    }
}

impl AudioSource for SamplePlayer {
    fn process(&mut self, output: &mut [f32]) {
        SamplePlayer::process(self, output);
    }
    
    fn gain(&self) -> f32 {
        SamplePlayer::gain(self)
    }
    
    fn set_gain(&mut self, gain: f32) {
        SamplePlayer::set_gain(self, gain);
    }
}

/// Audio source wrapper that processes audio through a plugin chain
pub struct PluginAudioSource {
    source: Box<dyn AudioSource>,
    plugin_chain: PluginChain,
    scratch_buffer: Vec<f32>,
    gain: f32,
}

impl PluginAudioSource {
    /// Create new PluginAudioSource wrapping an audio source with plugin effects
    pub fn new(source: Box<dyn AudioSource>, plugin_chain: PluginChain) -> Self {
        Self {
            source,
            plugin_chain,
            scratch_buffer: Vec::new(),
            gain: 1.0,
        }
    }
    
    /// Get reference to plugin chain
    pub fn plugin_chain(&self) -> &PluginChain {
        &self.plugin_chain
    }
    
    /// Get mutable reference to plugin chain
    pub fn plugin_chain_mut(&mut self) -> &mut PluginChain {
        &mut self.plugin_chain
    }
}

impl AudioSource for PluginAudioSource {
    fn process(&mut self, output: &mut [f32]) {
        // Ensure scratch buffer is large enough
        if self.scratch_buffer.len() < output.len() {
            self.scratch_buffer.resize(output.len(), 0.0);
        }
        
        // Get audio from underlying source
        self.source.process(&mut self.scratch_buffer[..output.len()]);
        
        // Process through plugin chain
        self.plugin_chain.process(&self.scratch_buffer[..output.len()], output);
    }
    
    fn gain(&self) -> f32 {
        self.gain
    }
    
    fn set_gain(&mut self, gain: f32) {
        self.gain = gain;
        self.source.set_gain(gain);
    }
}

impl Mixer {
    /// Create new mixer
    pub fn new(channels: usize) -> Self {
        Self {
            channels,
            sources: Vec::new(),
            loudness_meter: None,
            sample_rate: 48000, // Default, set properly via enable_loudness_meter
            track_peak_levels: Vec::new(),
        }
    }
    
    /// Enable loudness metering (EBU R 128)
    pub fn enable_loudness_meter(&mut self, sample_rate: u32) {
        self.sample_rate = sample_rate;
        match LoudnessMeter::new(sample_rate, self.channels as u32) {
            Ok(meter) => self.loudness_meter = Some(meter),
            Err(e) => eprintln!("Failed to create loudness meter: {}", e),
        }
    }
    
    /// Get current loudness reading (if enabled)
    pub fn loudness(&self) -> Option<LoudnessReading> {
        self.loudness_meter.as_ref().map(|m| m.reading())
    }
    
    /// Reset loudness meter
    pub fn reset_loudness_meter(&mut self) {
        if let Some(ref mut meter) = self.loudness_meter {
            meter.reset();
        }
    }
    
    /// Add audio source
    pub fn add_source(&mut self, source: Box<dyn AudioSource>) {
        self.sources.push(source);
        self.track_peak_levels.push(-96.0); // Initialize with silence level
    }
    
    /// Process audio - mix all sources
    pub fn process(&mut self, output: &mut [f32]) {
        // Clear output
        for sample in output.iter_mut() {
            *sample = 0.0;
        }
        
        // Mix all sources and calculate peak levels
        for (source_idx, source) in self.sources.iter_mut().enumerate() {
            let mut temp = vec![0.0f32; output.len()];
            source.process(&mut temp);
            
            // Calculate peak level for this source
            let mut peak = 0.0f32;
            for sample in &temp {
                peak = peak.max(sample.abs());
            }
            let db = if peak > 0.0 {
                20.0 * peak.log10()
            } else {
                -96.0
            };
            
            // Update stored peak level
            if source_idx < self.track_peak_levels.len() {
                self.track_peak_levels[source_idx] = db;
            }
            
            // Invoke callback for level meter update (every process call for real-time)
            invoke_meter_callback(source_idx, db);
            
            for (out, src) in output.iter_mut().zip(temp.iter()) {
                *out += src * source.gain();
            }
        }
        
        // Feed mixed output to loudness meter if enabled
        if let Some(ref mut meter) = self.loudness_meter {
            meter.process(output);
        }
    }
    
    /// Get peak level for a specific track (in dB)
    pub fn track_peak_db(&self, track: usize) -> f32 {
        self.track_peak_levels.get(track).copied().unwrap_or(-96.0)
    }
    
    /// Get number of sources
    pub fn source_count(&self) -> usize {
        self.sources.len()
    }
    
    /// Remove all sources
    pub fn clear(&mut self) {
        self.sources.clear();
        self.track_peak_levels.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sample::Sample;
    use crate::plugin::{GainPlugin, PluginChain, Plugin};

    #[test]
    fn test_mixer_creation() {
        let mixer = Mixer::new(2);
        assert_eq!(mixer.source_count(), 0);
    }

    #[test]
    fn test_mixer_loudness_meter() {
        let mut mixer = Mixer::new(2);
        mixer.enable_loudness_meter(48000);
        
        // Add a sine wave source
        let sine = SineWave::new(1000.0, 0.5);
        mixer.add_source(Box::new(sine));
        
        // Process audio for 1 second (enough for loudness measurement)
        let mut output = vec![0.0f32; 48000 * 2]; // 48kHz * 2 channels
        mixer.process(&mut output);
        
        // Get loudness reading
        let reading = mixer.loudness().expect("Loudness meter should be enabled");
        
        // Sine wave at 0.5 amplitude should have measurable loudness
        assert!(reading.integrated_lufs > -50.0, 
            "Sine wave should have loudness > -50 LUFS, got {} LUFS", 
            reading.integrated_lufs);
        assert!(reading.integrated_lufs < 0.0, 
            "Sine wave at 0.5 amplitude should have loudness < 0 LUFS, got {} LUFS", 
            reading.integrated_lufs);
        
        // Test reset
        mixer.reset_loudness_meter();
        let reading_after_reset = mixer.loudness().expect("Loudness meter should still exist");
        assert!(reading_after_reset.integrated_lufs < -50.0, 
            "After reset, loudness should be very low, got {} LUFS", 
            reading_after_reset.integrated_lufs);
    }

    #[test]
    fn test_add_source() {
        let mut mixer = Mixer::new(2);
        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));
        assert_eq!(mixer.source_count(), 1);
    }

    #[test]
    fn test_add_sample_player() {
        let mut mixer = Mixer::new(2);
        let data = vec![1.0f32, 1.0, 1.0, 1.0]; // 4 frames, mono
        let sample = Sample::from_raw(data, 1, 48000);
        let player = SamplePlayer::new(sample, 2);
        mixer.add_source(Box::new(player));
        assert_eq!(mixer.source_count(), 1);
    }

    #[test]
    fn test_clear() {
        let mut mixer = Mixer::new(2);
        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));
        mixer.clear();
        assert_eq!(mixer.source_count(), 0);
    }

    #[test]
    fn test_plugin_audio_source() {
        use crate::sample_player::SamplePlayer;
        
        // Create a sample player as the base audio source
        let data = vec![0.5f32; 64]; // Constant 0.5 values
        let sample = Sample::from_raw(data, 1, 48000);
        let mut player = SamplePlayer::new(sample, 1);
        
        // Start playback so the player produces audio
        player.play();
        
        // Create a plugin chain with a gain plugin
        let mut chain = PluginChain::new();
        let mut gain_plugin = GainPlugin::new();
        gain_plugin.activate(48000.0, 64).unwrap();
        gain_plugin.set_gain_db(6.0); // +6dB = 2x gain
        
        let plugin_info = gain_plugin.info().clone();
        chain.add_plugin("gain-1", plugin_info);
        
        // Create PluginAudioSource wrapping the player with the chain
        let mut plugin_source = PluginAudioSource::new(Box::new(player), chain);
        
        // Process audio
        let mut output = vec![0.0f32; 64];
        plugin_source.process(&mut output);
        
        // Verify output is approximately 2x the input (0.5 * 2 = 1.0 due to 6dB gain)
        let expected = 0.5 * 10.0_f32.powf(6.0 / 20.0);
        assert!((output[0] - expected).abs() < 0.001, "Expected {}, got {}", expected, output[0]);
    }

    #[test]
    fn test_mixer_with_plugin_source() {
        use crate::sample_player::SamplePlayer;
        
        let mut mixer = Mixer::new(1);
        
        // Create a sample player with constant 0.5 values
        let data = vec![0.5f32; 64];
        let sample = Sample::from_raw(data, 1, 48000);
        let mut player = SamplePlayer::new(sample, 1);
        player.play();
        
        // Create a plugin chain with +6dB gain
        let mut chain = PluginChain::new();
        let mut gain_plugin = GainPlugin::new();
        gain_plugin.activate(48000.0, 64).unwrap();
        gain_plugin.set_gain_db(6.0);
        
        let plugin_info = gain_plugin.info().clone();
        chain.add_plugin("gain-1", plugin_info);
        
        // Create PluginAudioSource and add to mixer
        let plugin_source = PluginAudioSource::new(Box::new(player), chain);
        mixer.add_source(Box::new(plugin_source));
        
        // Process through mixer
        let mut output = vec![0.0f32; 64];
        mixer.process(&mut output);
        
        // Verify output is amplified (0.5 * 2 = ~1.0)
        let expected = 0.5 * 10.0_f32.powf(6.0 / 20.0);
        assert!((output[0] - expected).abs() < 0.001, "Expected {}, got {}", expected, output[0]);
        assert_eq!(mixer.source_count(), 1);
    }
}
