//! Sample player
//! 
//! Playback of audio samples with pitch/time control.

use crate::sample::Sample;

/// Sample player with variable speed and interpolation
#[derive(Debug)]
pub struct SamplePlayer {
    sample: Sample,
    position: f32,       // Current position in frames
    speed: f32,         // Playback speed (1.0 = normal)
    playing: bool,
    looping: bool,      // Whether to loop when reaching end
    gain: f32,          // Output gain
    output_channels: u16, // Target output channel count
}

impl SamplePlayer {
    /// Create new sample player
    pub fn new(sample: Sample, output_channels: u16) -> Self {
        Self {
            sample,
            position: 0.0,
            speed: 1.0,
            playing: false,
            looping: false,
            gain: 1.0,
            output_channels,
        }
    }
    
    /// Start playback
    pub fn play(&mut self) {
        self.playing = true;
    }
    
    /// Stop playback
    pub fn stop(&mut self) {
        self.playing = false;
        self.position = 0.0;
    }
    
    /// Pause playback (stop without resetting position)
    pub fn pause(&mut self) {
        self.playing = false;
    }
    
    /// Set looping
    pub fn set_looping(&mut self, looping: bool) {
        self.looping = looping;
    }
    
    /// Check if looping
    pub fn is_looping(&self) -> bool {
        self.looping
    }
    
    /// Set playback speed (affects pitch)
    /// 1.0 = normal, 0.5 = half speed (octave down), 2.0 = double (octave up)
    pub fn set_speed(&mut self, speed: f32) {
        self.speed = speed.max(0.01); // Prevent negative or zero speed
    }
    
    /// Get current playback speed
    pub fn speed(&self) -> f32 {
        self.speed
    }
    
    /// Set output gain
    pub fn set_gain(&mut self, gain: f32) {
        self.gain = gain.max(0.0);
    }
    
    /// Get current gain
    pub fn gain(&self) -> f32 {
        self.gain
    }
    
    /// Get current playback position in frames
    pub fn position(&self) -> f32 {
        self.position
    }
    
    /// Set playback position in frames
    pub fn set_position(&mut self, position: f32) {
        let max_pos = self.sample.frame_count().saturating_sub(1) as f32;
        self.position = position.clamp(0.0, max_pos);
    }
    
    /// Get current position as seconds
    pub fn position_seconds(&self) -> f32 {
        self.position / self.sample.sample_rate() as f32
    }
    
    /// Set position in seconds
    pub fn set_position_seconds(&mut self, seconds: f32) {
        let frame = seconds * self.sample.sample_rate() as f32;
        self.set_position(frame);
    }
    
    /// Check if playback is finished (reached end, not looping)
    pub fn is_finished(&self) -> bool {
        let total_frames = self.sample.frame_count() as f32;
        !self.playing && !self.looping && self.position >= total_frames
    }
    
    /// Get sample reference
    pub fn sample(&self) -> &Sample {
        &self.sample
    }
    
    /// Check if currently playing
    pub fn is_playing(&self) -> bool {
        self.playing
    }
    
    /// Get duration in seconds
    pub fn duration_seconds(&self) -> f32 {
        self.sample.duration_seconds()
    }
    
    /// Process audio with linear interpolation
    pub fn process(&mut self, output: &mut [f32]) {
        let num_channels = self.output_channels as usize;
        let num_frames = output.len() / num_channels;
        let sample_channels = self.sample.channels() as usize;
        let total_sample_frames = self.sample.frame_count() as f32;
        
        if !self.playing || total_sample_frames == 0.0 {
            // Output silence
            for sample in output {
                *sample = 0.0;
            }
            return;
        }
        
        for frame in 0..num_frames {
            // Check if we've reached the end
            if self.position >= total_sample_frames {
                if self.looping {
                    self.position = 0.0;
                } else {
                    self.playing = false;
                    // Fill remaining with silence
                    for ch in 0..num_channels {
                        output[frame * num_channels + ch] = 0.0;
                    }
                    continue;
                }
            }
            
            // Get interpolated sample for each channel
            for ch in 0..num_channels {
                // Map output channel to sample channel (mono samples play to all channels)
                let sample_ch = ch.min(sample_channels.saturating_sub(1));
                
                let sample_value = self.sample.get_interpolated(self.position, sample_ch);
                output[frame * num_channels + ch] = sample_value * self.gain;
            }
            
            // Advance position
            self.position += self.speed;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_sample() -> Sample {
        // 2 channels, 4 frames, 48000 Hz
        // Frame 0: L=0.0, R=0.5
        // Frame 1: L=1.0, R=-0.5
        // Frame 2: L=-1.0, R=0.0
        // Frame 3: L=0.5, R=0.5
        let data = vec![
            0.0f32, 0.5,   // Frame 0
            1.0, -0.5,    // Frame 1
            -1.0, 0.0,    // Frame 2
            0.5, 0.5,     // Frame 3
        ];
        Sample::from_raw(data, 2, 48000)
    }

    #[test]
    fn test_player_creation() {
        let sample = create_test_sample();
        let player = SamplePlayer::new(sample, 2);
        
        assert!(!player.is_playing());
        assert!(!player.is_looping());
        assert_eq!(player.speed(), 1.0);
        assert_eq!(player.gain(), 1.0);
        assert_eq!(player.position(), 0.0);
    }

    #[test]
    fn test_play_stop() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        player.play();
        assert!(player.is_playing());
        
        player.stop();
        assert!(!player.is_playing());
        assert_eq!(player.position(), 0.0);
    }

    #[test]
    fn test_pause() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        player.play();
        player.set_position(2.0);
        player.pause();
        
        assert!(!player.is_playing());
        assert_eq!(player.position(), 2.0); // Position preserved
    }

    #[test]
    fn test_speed_control() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        player.set_speed(2.0);
        assert_eq!(player.speed(), 2.0);
        
        player.set_speed(0.5);
        assert_eq!(player.speed(), 0.5);
        
        // Should not allow values below 0.01
        player.set_speed(0.0);
        assert_eq!(player.speed(), 0.01);
    }

    #[test]
    fn test_gain_control() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        player.set_gain(0.5);
        assert_eq!(player.gain(), 0.5);
        
        // Should not allow negative values
        player.set_gain(-1.0);
        assert_eq!(player.gain(), 0.0);
    }

    #[test]
    fn test_position_seconds() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        // 4 frames at 48000 Hz = 0.0833 ms per frame
        player.set_position(2.0);
        assert!((player.position_seconds() - 0.00004167).abs() < 0.00001);
    }

    #[test]
    fn test_process_silence_when_stopped() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        // Don't start playback
        let mut output = vec![1.0f32; 4]; // 2 frames, stereo
        player.process(&mut output);
        
        assert_eq!(output, vec![0.0, 0.0, 0.0, 0.0]);
    }

    #[test]
    fn test_process_single_frame() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        player.play();
        let mut output = vec![0.0f32; 2]; // 1 frame, stereo
        player.process(&mut output);
        
        // First frame: L=0.0, R=0.5
        assert!(output[0].abs() < 0.0001); // Left channel ~0.0
        assert!((output[1] - 0.5).abs() < 0.0001); // Right channel ~0.5
    }

    #[test]
    fn test_looping() {
        let sample = create_test_sample();
        let mut player = SamplePlayer::new(sample, 2);
        
        player.set_looping(true);
        player.set_speed(4.0); // 4 frames per process call
        player.play();
        
        let mut output = vec![0.0f32; 8]; // 4 frames, stereo
        player.process(&mut output);
        
        // Should have looped, still playing
        assert!(player.is_playing());
    }

    #[test]
    fn test_mono_to_stereo() {
        // Mono sample
        let data = vec![1.0f32, 1.0, 1.0, 1.0]; // 4 frames, mono
        let sample = Sample::from_raw(data, 1, 48000);
        let mut player = SamplePlayer::new(sample, 2); // Stereo output
        
        player.play();
        let mut output = vec![0.0f32; 2];
        player.process(&mut output);
        
        // Mono sample should play to both channels
        assert!((output[0] - 1.0).abs() < 0.0001);
        assert!((output[1] - 1.0).abs() < 0.0001);
    }

    #[test]
    fn test_gain_applied() {
        let data = vec![1.0f32, 1.0]; // 1 frame, mono
        let sample = Sample::from_raw(data, 1, 48000);
        let mut player = SamplePlayer::new(sample, 1);
        
        player.set_gain(0.5);
        player.play();
        
        let mut output = vec![0.0f32; 1];
        player.process(&mut output);
        
        assert!((output[0] - 0.5).abs() < 0.0001);
    }
}
