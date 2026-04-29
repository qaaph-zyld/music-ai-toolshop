//! Punch-In/Out Recording Controller
//!
//! Manages automated recording with pre-roll and punch points.
//! Supports workflows like: pre-roll → punch-in → record → punch-out

use serde::{Serialize, Deserialize};

/// Current state of punch-in/out recording
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PunchState {
    /// Not armed, normal operation
    Disarmed,
    /// Armed and waiting for trigger
    Armed,
    /// Playing pre-roll before punch-in
    PreRolling,
    /// Currently recording in punch range
    Recording,
    /// Recording completed after punch-out
    Completed,
}

/// Configuration for punch-in/out recording
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PunchConfig {
    /// Punch-in position in beats
    pub punch_in_beats: f32,
    /// Punch-out position in beats (None = no punch-out, record until stopped)
    pub punch_out_beats: Option<f32>,
    /// Pre-roll duration in beats (0 = no pre-roll)
    pub pre_roll_beats: f32,
    /// Whether to auto-start transport when armed
    pub auto_punch: bool,
}

impl Default for PunchConfig {
    fn default() -> Self {
        Self {
            punch_in_beats: 4.0,
            punch_out_beats: Some(8.0),
            pre_roll_beats: 2.0,
            auto_punch: true,
        }
    }
}

/// Controller for punch-in/out recording
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PunchInOutController {
    config: PunchConfig,
    state: PunchState,
    /// The beat position where we started pre-rolling
    pre_roll_start_beats: f32,
    /// Whether punch-in/out is enabled
    enabled: bool,
}

impl PunchInOutController {
    /// Create a new punch-in/out controller with default settings
    pub fn new() -> Self {
        Self {
            config: PunchConfig::default(),
            state: PunchState::Disarmed,
            pre_roll_start_beats: 0.0,
            enabled: true,
        }
    }

    /// Create with custom configuration
    pub fn with_config(config: PunchConfig) -> Self {
        Self {
            config,
            state: PunchState::Disarmed,
            pre_roll_start_beats: 0.0,
            enabled: true,
        }
    }

    /// Check if punch-in/out is enabled
    pub fn is_enabled(&self) -> bool {
        self.enabled
    }

    /// Enable or disable punch-in/out
    pub fn set_enabled(&mut self, enabled: bool) {
        self.enabled = enabled;
        if !enabled {
            self.state = PunchState::Disarmed;
        }
    }

    /// Get current punch state
    pub fn state(&self) -> PunchState {
        self.state
    }

    /// Get current configuration
    pub fn config(&self) -> &PunchConfig {
        &self.config
    }

    /// Set punch-in position
    pub fn set_punch_in(&mut self, beats: f32) {
        self.config.punch_in_beats = beats.max(0.0);
    }

    /// Set punch-out position (None for no punch-out)
    pub fn set_punch_out(&mut self, beats: Option<f32>) {
        self.config.punch_out_beats = beats.map(|b| b.max(0.0));
    }

    /// Clear punch-out (record until manually stopped)
    pub fn clear_punch_out(&mut self) {
        self.config.punch_out_beats = None;
    }

    /// Set pre-roll duration
    pub fn set_pre_roll(&mut self, beats: f32) {
        self.config.pre_roll_beats = beats.max(0.0);
    }

    /// Set auto-punch mode
    pub fn set_auto_punch(&mut self, auto_punch: bool) {
        self.config.auto_punch = auto_punch;
    }

    /// Get punch-in position
    pub fn punch_in(&self) -> f32 {
        self.config.punch_in_beats
    }

    /// Get punch-out position
    pub fn punch_out(&self) -> Option<f32> {
        self.config.punch_out_beats
    }

    /// Get pre-roll duration
    pub fn pre_roll(&self) -> f32 {
        self.config.pre_roll_beats
    }

    /// Check if auto-punch is enabled
    pub fn auto_punch(&self) -> bool {
        self.config.auto_punch
    }

    /// Arm the punch-in/out system
    /// Returns the current state after arming
    pub fn arm(&mut self, current_beat: f32) -> PunchState {
        if !self.enabled {
            return PunchState::Disarmed;
        }

        self.state = PunchState::Armed;
        
        // If no pre-roll and we're already at or past punch-in, go straight to recording
        if self.config.pre_roll_beats <= 0.0 && current_beat >= self.config.punch_in_beats {
            self.state = PunchState::Recording;
        }
        
        self.state
    }

    /// Disarm the system
    pub fn disarm(&mut self) {
        self.state = PunchState::Disarmed;
        self.pre_roll_start_beats = 0.0;
    }

    /// Check if current beat is within the punch range
    /// Note: Punch-in is exclusive (at exact punch-in beat, not yet recording)
    /// Punch-out is inclusive (at exact punch-out beat, still recording until that point)
    pub fn is_in_punch_range(&self, beat: f32) -> bool {
        if beat <= self.config.punch_in_beats {
            return false;
        }
        
        if let Some(punch_out) = self.config.punch_out_beats {
            beat < punch_out
        } else {
            true // No punch-out set, always in range after punch-in
        }
    }

    /// Get the beat where pre-roll should start
    pub fn pre_roll_start(&self) -> f32 {
        (self.config.punch_in_beats - self.config.pre_roll_beats).max(0.0)
    }

    /// Process transport position and update state
    /// Returns true if recording should be active
    pub fn process(&mut self, current_beat: f32, is_playing: bool) -> bool {
        if !self.enabled || !is_playing {
            return false;
        }

        match self.state {
            PunchState::Disarmed => false,
            
            PunchState::Armed => {
                // Check if we should start pre-rolling
                let pre_roll_start = self.pre_roll_start();
                
                if self.config.pre_roll_beats > 0.0 && current_beat >= pre_roll_start {
                    // Start pre-rolling
                    self.state = PunchState::PreRolling;
                    self.pre_roll_start_beats = current_beat;
                    false
                } else if self.config.pre_roll_beats <= 0.0 && current_beat >= self.config.punch_in_beats {
                    // No pre-roll, go straight to recording
                    self.state = PunchState::Recording;
                    true
                } else {
                    false
                }
            }
            
            PunchState::PreRolling => {
                // Check if we've reached punch-in
                if current_beat >= self.config.punch_in_beats {
                    self.state = PunchState::Recording;
                    true
                } else {
                    false
                }
            }
            
            PunchState::Recording => {
                // Check if we've reached punch-out
                if let Some(punch_out) = self.config.punch_out_beats {
                    if current_beat >= punch_out {
                        self.state = PunchState::Completed;
                        false
                    } else {
                        true
                    }
                } else {
                    // No punch-out, keep recording
                    true
                }
            }
            
            PunchState::Completed => false,
        }
    }

    /// Calculate progress through pre-roll (0.0 to 1.0)
    /// Returns None if not pre-rolling
    pub fn pre_roll_progress(&self, current_beat: f32) -> Option<f32> {
        if self.state != PunchState::PreRolling {
            return None;
        }

        let pre_roll_duration = self.config.pre_roll_beats;
        if pre_roll_duration <= 0.0 {
            return Some(1.0);
        }

        let beats_into_pre_roll = current_beat - self.pre_roll_start_beats;
        let progress = beats_into_pre_roll / pre_roll_duration;
        Some(progress.clamp(0.0, 1.0))
    }

    /// Get remaining beats until punch-in
    /// Returns None if not armed or pre-rolling, or if already past punch-in
    pub fn beats_until_punch_in(&self, current_beat: f32) -> Option<f32> {
        match self.state {
            PunchState::Armed | PunchState::PreRolling => {
                if current_beat >= self.config.punch_in_beats {
                    return None;
                }
                let remaining = self.config.punch_in_beats - current_beat;
                Some(remaining.max(0.0))
            }
            _ => None,
        }
    }

    /// Get remaining beats until punch-out
    /// Returns None if not recording or no punch-out set
    pub fn beats_until_punch_out(&self, current_beat: f32) -> Option<f32> {
        match self.state {
            PunchState::Recording => {
                self.config.punch_out_beats.map(|punch_out| {
                    let remaining = punch_out - current_beat;
                    remaining.max(0.0)
                })
            }
            _ => None,
        }
    }

    /// Reset to initial state
    pub fn reset(&mut self) {
        self.state = PunchState::Disarmed;
        self.pre_roll_start_beats = 0.0;
    }

    /// Get a human-readable status description
    pub fn status_text(&self) -> &'static str {
        match self.state {
            PunchState::Disarmed => "Disarmed",
            PunchState::Armed => "Armed",
            PunchState::PreRolling => "Pre-Roll",
            PunchState::Recording => "Recording",
            PunchState::Completed => "Completed",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_punch_controller_creation() {
        let controller = PunchInOutController::new();
        assert_eq!(controller.state(), PunchState::Disarmed);
        assert!(controller.is_enabled());
        assert_eq!(controller.punch_in(), 4.0);
        assert_eq!(controller.punch_out(), Some(8.0));
        assert_eq!(controller.pre_roll(), 2.0);
    }

    #[test]
    fn test_custom_config() {
        let config = PunchConfig {
            punch_in_beats: 8.0,
            punch_out_beats: Some(16.0),
            pre_roll_beats: 4.0,
            auto_punch: false,
        };
        let controller = PunchInOutController::with_config(config);
        assert_eq!(controller.punch_in(), 8.0);
        assert_eq!(controller.punch_out(), Some(16.0));
        assert_eq!(controller.pre_roll(), 4.0);
        assert!(!controller.auto_punch());
    }

    #[test]
    fn test_set_punch_range() {
        let mut controller = PunchInOutController::new();
        controller.set_punch_in(10.0);
        controller.set_punch_out(Some(20.0));
        
        assert_eq!(controller.punch_in(), 10.0);
        assert_eq!(controller.punch_out(), Some(20.0));
    }

    #[test]
    fn test_clear_punch_out() {
        let mut controller = PunchInOutController::new();
        controller.clear_punch_out();
        assert_eq!(controller.punch_out(), None);
    }

    #[test]
    fn test_arm_disarm() {
        let mut controller = PunchInOutController::new();
        
        // Arm at beat 0
        let state = controller.arm(0.0);
        assert_eq!(state, PunchState::Armed);
        assert_eq!(controller.state(), PunchState::Armed);
        
        // Disarm
        controller.disarm();
        assert_eq!(controller.state(), PunchState::Disarmed);
    }

    #[test]
    fn test_arm_past_punch_in_no_preroll() {
        // With no pre-roll, arming past punch-in should go straight to recording
        let config = PunchConfig {
            punch_in_beats: 4.0,
            punch_out_beats: Some(8.0),
            pre_roll_beats: 0.0,
            auto_punch: true,
        };
        let mut controller = PunchInOutController::with_config(config);
        
        let state = controller.arm(5.0);
        assert_eq!(state, PunchState::Recording);
    }

    #[test]
    fn test_is_in_punch_range() {
        let mut controller = PunchInOutController::new();
        controller.set_punch_in(4.0);
        controller.set_punch_out(Some(8.0));
        
        assert!(!controller.is_in_punch_range(2.0));  // Before punch-in
        assert!(!controller.is_in_punch_range(4.0));  // At punch-in boundary (exclusive)
        assert!(controller.is_in_punch_range(5.0));    // In range
        assert!(controller.is_in_punch_range(7.0));    // In range
        assert!(!controller.is_in_punch_range(8.0));  // At punch-out boundary (exclusive)
        assert!(!controller.is_in_punch_range(10.0)); // After punch-out
    }

    #[test]
    fn test_pre_roll_progress() {
        let config = PunchConfig {
            punch_in_beats: 4.0,
            punch_out_beats: Some(8.0),
            pre_roll_beats: 2.0,
            auto_punch: true,
        };
        let mut controller = PunchInOutController::with_config(config);
        
        // Not pre-rolling yet
        assert_eq!(controller.pre_roll_progress(1.0), None);
        
        // Arm and start pre-roll
        controller.arm(0.0);
        controller.process(2.0, true); // Start pre-rolling at beat 2
        
        assert_eq!(controller.state(), PunchState::PreRolling);
        assert_eq!(controller.pre_roll_progress(2.0), Some(0.0));
        assert_eq!(controller.pre_roll_progress(3.0), Some(0.5));
        assert_eq!(controller.pre_roll_progress(4.0), Some(1.0));
    }

    #[test]
    fn test_process_state_transitions() {
        let config = PunchConfig {
            punch_in_beats: 4.0,
            punch_out_beats: Some(8.0),
            pre_roll_beats: 2.0,
            auto_punch: true,
        };
        let mut controller = PunchInOutController::with_config(config);
        
        // Arm at beat 0
        controller.arm(0.0);
        assert_eq!(controller.state(), PunchState::Armed);
        
        // Process at beat 1 - still armed, before pre-roll
        let recording = controller.process(1.0, true);
        assert!(!recording);
        assert_eq!(controller.state(), PunchState::Armed);
        
        // Process at beat 2 - start pre-rolling
        let recording = controller.process(2.0, true);
        assert!(!recording);
        assert_eq!(controller.state(), PunchState::PreRolling);
        
        // Process at beat 4 - punch-in, start recording
        let recording = controller.process(4.0, true);
        assert!(recording);
        assert_eq!(controller.state(), PunchState::Recording);
        
        // Process at beat 6 - still recording
        let recording = controller.process(6.0, true);
        assert!(recording);
        assert_eq!(controller.state(), PunchState::Recording);
        
        // Process at beat 8 - punch-out, complete
        let recording = controller.process(8.0, true);
        assert!(!recording);
        assert_eq!(controller.state(), PunchState::Completed);
        
        // Process after punch-out - still complete
        let recording = controller.process(10.0, true);
        assert!(!recording);
        assert_eq!(controller.state(), PunchState::Completed);
    }

    #[test]
    fn test_process_no_punch_out() {
        let config = PunchConfig {
            punch_in_beats: 4.0,
            punch_out_beats: None,
            pre_roll_beats: 0.0,
            auto_punch: true,
        };
        let mut controller = PunchInOutController::with_config(config);
        
        // Arm and immediately start recording (no pre-roll)
        controller.arm(0.0);
        controller.process(4.0, true);
        assert_eq!(controller.state(), PunchState::Recording);
        
        // Keep recording indefinitely
        let recording = controller.process(100.0, true);
        assert!(recording);
        assert_eq!(controller.state(), PunchState::Recording);
    }

    #[test]
    fn test_beats_until_punch_in() {
        let mut controller = PunchInOutController::new();
        controller.arm(0.0);
        
        // At beat 1, should have 3 beats until punch-in (at beat 4)
        assert_eq!(controller.beats_until_punch_in(1.0), Some(3.0));
        assert_eq!(controller.beats_until_punch_in(3.0), Some(1.0));
        assert_eq!(controller.beats_until_punch_in(4.0), Some(0.0));
        
        // After punch-in, should return None
        controller.process(4.0, true);
        assert_eq!(controller.beats_until_punch_in(5.0), None);
    }

    #[test]
    fn test_beats_until_punch_out() {
        let mut controller = PunchInOutController::new();
        controller.arm(0.0);
        controller.process(2.0, true); // Pre-rolling
        controller.process(4.0, true); // Recording
        
        // At beat 5, should have 3 beats until punch-out (at beat 8)
        assert_eq!(controller.beats_until_punch_out(5.0), Some(3.0));
        assert_eq!(controller.beats_until_punch_out(7.0), Some(1.0));
        assert_eq!(controller.beats_until_punch_out(8.0), Some(0.0));
    }

    #[test]
    fn test_beats_until_punch_out_no_out() {
        let mut controller = PunchInOutController::new();
        controller.clear_punch_out();
        controller.arm(0.0);
        controller.process(4.0, true); // Recording
        
        // No punch-out set, should return None
        assert_eq!(controller.beats_until_punch_out(5.0), None);
    }

    #[test]
    fn test_disabled_controller() {
        let mut controller = PunchInOutController::new();
        controller.set_enabled(false);
        
        // Should not arm when disabled
        let state = controller.arm(0.0);
        assert_eq!(state, PunchState::Disarmed);
        
        // Process should always return false
        assert!(!controller.process(4.0, true));
    }

    #[test]
    fn test_pre_roll_start() {
        let mut controller = PunchInOutController::new();
        controller.set_punch_in(8.0);
        controller.set_pre_roll(4.0);
        
        assert_eq!(controller.pre_roll_start(), 4.0); // 8 - 4 = 4
        
        // Should not go below 0
        controller.set_punch_in(2.0);
        controller.set_pre_roll(4.0);
        assert_eq!(controller.pre_roll_start(), 0.0); // max(2-4, 0) = 0
    }

    #[test]
    fn test_reset() {
        let mut controller = PunchInOutController::new();
        controller.arm(0.0);
        controller.process(4.0, true);
        assert_eq!(controller.state(), PunchState::Recording);
        
        controller.reset();
        assert_eq!(controller.state(), PunchState::Disarmed);
        assert_eq!(controller.pre_roll_progress(0.0), None);
    }

    #[test]
    fn test_status_text() {
        let mut controller = PunchInOutController::new();
        assert_eq!(controller.status_text(), "Disarmed");
        
        controller.arm(0.0);
        assert_eq!(controller.status_text(), "Armed");
        
        controller.process(2.0, true);
        assert_eq!(controller.status_text(), "Pre-Roll");
        
        controller.process(4.0, true);
        assert_eq!(controller.status_text(), "Recording");
        
        controller.process(8.0, true);
        assert_eq!(controller.status_text(), "Completed");
    }

    #[test]
    fn test_process_when_not_playing() {
        let mut controller = PunchInOutController::new();
        controller.arm(0.0);
        
        // Process when not playing should not advance state
        let recording = controller.process(2.0, false);
        assert!(!recording);
        assert_eq!(controller.state(), PunchState::Armed); // Still armed
    }

    #[test]
    fn test_serialization() {
        let config = PunchConfig {
            punch_in_beats: 10.0,
            punch_out_beats: Some(20.0),
            pre_roll_beats: 4.0,
            auto_punch: false,
        };
        let controller = PunchInOutController::with_config(config);
        
        // Serialize
        let serialized = serde_json::to_string(&controller).unwrap();
        
        // Deserialize
        let deserialized: PunchInOutController = serde_json::from_str(&serialized).unwrap();
        
        assert_eq!(deserialized.punch_in(), 10.0);
        assert_eq!(deserialized.punch_out(), Some(20.0));
        assert_eq!(deserialized.pre_roll(), 4.0);
        assert!(!deserialized.auto_punch());
    }
}
