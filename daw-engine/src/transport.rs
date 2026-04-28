//! Transport controls
//! 
//! Playback transport: play, stop, record, loop, punch-in/out.

use crate::ffi_bridge::{invoke_transport_callback, invoke_position_callback};
use crate::{profile_scope, plot_value};
use serde::{Serialize, Deserialize};

/// Transport state
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum TransportState {
    /// Stopped
    Stopped,
    /// Playing
    Playing,
    /// Recording
    Recording,
    /// Paused
    Paused,
}

/// Play mode
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum PlayMode {
    /// Play once from position
    OneShot,
    /// Loop between loop start/end
    Loop,
}

/// Transport controls playback
#[derive(Debug)]
pub struct Transport {
    tempo: f32,
    sample_rate: u32,
    state: TransportState,
    play_mode: PlayMode,
    position_beats: f32,
    position_samples: u64,
    loop_start_beats: f32,
    loop_end_beats: f32,
    punch_in_beats: Option<f32>,
    punch_out_beats: Option<f32>,
    last_reported_bars: i32,
    last_reported_beats: i32,
    last_reported_sixteenths: i32,
}

impl Transport {
    /// Create new transport
    pub fn new(tempo: f32, sample_rate: u32) -> Self {
        Self {
            tempo,
            sample_rate,
            state: TransportState::Stopped,
            play_mode: PlayMode::OneShot,
            position_beats: 0.0,
            position_samples: 0,
            loop_start_beats: 0.0,
            loop_end_beats: 4.0,
            punch_in_beats: None,
            punch_out_beats: None,
            last_reported_bars: -1,
            last_reported_beats: -1,
            last_reported_sixteenths: -1,
        }
    }
    
    /// Get current state
    pub fn state(&self) -> TransportState {
        self.state
    }
    
    /// Start playback
    pub fn play(&mut self) {
        profile_scope!("transport_play");
        self.state = TransportState::Playing;
        invoke_transport_callback(self.state);
        plot_value!("transport_state", 1.0); // Playing
    }
    
    /// Stop playback
    pub fn stop(&mut self) {
        profile_scope!("transport_stop");
        self.state = TransportState::Stopped;
        invoke_transport_callback(self.state);
        plot_value!("transport_state", 0.0); // Stopped
    }
    
    /// Start recording
    pub fn record(&mut self) {
        profile_scope!("transport_record");
        self.state = TransportState::Recording;
        invoke_transport_callback(self.state);
        plot_value!("transport_state", 2.0); // Recording
    }
    
    /// Pause playback
    pub fn pause(&mut self) {
        if self.state == TransportState::Playing || self.state == TransportState::Recording {
            self.state = TransportState::Paused;
            invoke_transport_callback(self.state);
        }
    }
    
    /// Rewind to start
    pub fn rewind(&mut self) {
        self.position_beats = 0.0;
        self.position_samples = 0;
        self.state = TransportState::Stopped;
        invoke_transport_callback(self.state);
        self.report_position_change();
    }
    
    /// Get current position in beats
    pub fn position_beats(&self) -> f32 {
        self.position_beats
    }
    
    /// Set position in beats
    pub fn set_position(&mut self, beats: f32) {
        self.position_beats = beats.max(0.0);
        self.position_samples = self.beats_to_samples(self.position_beats);
        self.report_position_change();
    }
    
    /// Get play mode
    pub fn play_mode(&self) -> PlayMode {
        self.play_mode
    }
    
    /// Set play mode
    pub fn set_play_mode(&mut self, mode: PlayMode) {
        self.play_mode = mode;
    }
    
    /// Set loop range
    pub fn set_loop_range(&mut self, start: f32, end: f32) {
        self.loop_start_beats = start;
        self.loop_end_beats = end;
    }
    
    /// Get loop range
    pub fn loop_range(&self) -> (f32, f32) {
        (self.loop_start_beats, self.loop_end_beats)
    }
    
    /// Set punch-in point
    pub fn set_punch_in(&mut self, beats: f32) {
        self.punch_in_beats = Some(beats);
    }
    
    /// Set punch-out point
    pub fn set_punch_out(&mut self, beats: f32) {
        self.punch_out_beats = Some(beats);
    }
    
    /// Process audio samples and advance position
    pub fn process(&mut self, samples: u32) {
        profile_scope!("transport_process");
        
        if self.state == TransportState::Stopped {
            return;
        }
        
        self.position_samples += samples as u64;
        self.position_beats = self.samples_to_beats(self.position_samples);
        
        // Handle loop mode
        if self.play_mode == PlayMode::Loop {
            if self.position_beats >= self.loop_end_beats {
                profile_scope!("transport_loop");
                let loop_length = self.loop_end_beats - self.loop_start_beats;
                let excess = self.position_beats - self.loop_start_beats;
                self.position_beats = self.loop_start_beats + (excess % loop_length);
                self.position_samples = self.beats_to_samples(self.position_beats);
            }
        }
        
        // Handle punch-in/punch-out for recording
        if self.state == TransportState::Playing || self.state == TransportState::Recording {
            if let Some(punch_in) = self.punch_in_beats {
                if self.position_beats >= punch_in {
                    profile_scope!("transport_punch");
                    if let Some(punch_out) = self.punch_out_beats {
                        if self.position_beats < punch_out {
                            self.state = TransportState::Recording;
                            invoke_transport_callback(self.state);
                            plot_value!("transport_state", 2.0); // Recording
                        } else {
                            self.state = TransportState::Playing;
                            invoke_transport_callback(self.state);
                            plot_value!("transport_state", 1.0); // Playing
                        }
                    } else {
                        self.state = TransportState::Recording;
                        invoke_transport_callback(self.state);
                        plot_value!("transport_state", 2.0); // Recording
                    }
                }
            }
        }
        
        // Report position change if significant (bars/beats/sixteenths changed)
        self.report_position_if_changed();
        
        // Plot position for profiling
        plot_value!("transport_position", self.position_beats as f64);
    }
    
    /// Report position change to callback if bars/beats/sixteenths changed
    fn report_position_if_changed(&mut self) {
        let bars = (self.position_beats / 4.0) as i32;
        let beats_in_bar = self.position_beats % 4.0;
        let beats = beats_in_bar as i32;
        let sixteenths = ((beats_in_bar - beats as f32) * 4.0) as i32;
        
        if bars != self.last_reported_bars || 
           beats != self.last_reported_beats || 
           sixteenths != self.last_reported_sixteenths {
            self.last_reported_bars = bars;
            self.last_reported_beats = beats;
            self.last_reported_sixteenths = sixteenths;
            invoke_position_callback(self.position_beats);
        }
    }
    
    /// Force position change report
    fn report_position_change(&mut self) {
        self.last_reported_bars = -1; // Force update
        self.report_position_if_changed();
    }
    
    /// Get tempo (BPM)
    pub fn tempo(&self) -> f32 {
        self.tempo
    }
    
    /// Set tempo (BPM)
    pub fn set_tempo(&mut self, tempo: f32) {
        self.tempo = tempo.max(1.0).min(999.0);
    }
    
    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
    
    /// Set sample rate
    pub fn set_sample_rate(&mut self, sample_rate: u32) {
        self.sample_rate = sample_rate;
    }
    
    /// Convert beats to samples
    fn beats_to_samples(&self, beats: f32) -> u64 {
        let seconds = beats * 60.0 / self.tempo;
        (seconds * self.sample_rate as f32) as u64
    }
    
    /// Convert samples to beats
    fn samples_to_beats(&self, samples: u64) -> f32 {
        let seconds = samples as f32 / self.sample_rate as f32;
        seconds * self.tempo / 60.0
    }
    
    /// Jump forward by beats
    pub fn jump_forward(&mut self, beats: f32) {
        self.set_position(self.position_beats + beats);
    }
    
    /// Jump backward by beats
    pub fn jump_backward(&mut self, beats: f32) {
        self.set_position(self.position_beats - beats);
    }
    
    /// Get position in bars (assuming 4/4 time)
    pub fn position_bars(&self) -> f32 {
        self.position_beats / 4.0
    }
    
    /// Set position in bars
    pub fn set_position_bars(&mut self, bars: f32) {
        self.set_position(bars * 4.0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_transport_creation() {
        let transport = Transport::new(120.0, 48000);
        assert_eq!(transport.state(), TransportState::Stopped);
        assert_eq!(transport.tempo(), 120.0);
    }
    
    #[test]
    fn test_transport_play_stop() {
        let mut transport = Transport::new(120.0, 48000);
        transport.play();
        assert_eq!(transport.state(), TransportState::Playing);
        transport.stop();
        assert_eq!(transport.state(), TransportState::Stopped);
    }
    
    #[test]
    fn test_transport_loop() {
        let mut transport = Transport::new(120.0, 48000);
        transport.set_loop_range(0.0, 4.0);
        transport.set_play_mode(PlayMode::Loop);
        transport.play();
        transport.process(96000); // 2 seconds
        // At 120 BPM, 2 seconds = 4 beats
        assert_eq!(transport.position_beats(), 0.0); // Should loop back
    }
}
