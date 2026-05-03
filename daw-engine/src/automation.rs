//! Parameter Automation System
//!
//! Record and playback fader/knob movements with automation lanes.
//! Supports: linear/log/exponential/s-curve interpolation, write/touch/latch modes

/// Curve type for interpolation between automation points
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum CurveType {
    Linear,
    Logarithmic,
    Exponential,
    SCurve,
}

impl CurveType {
    /// Convert integer to CurveType (for FFI)
    pub fn from_int(value: i32) -> Self {
        match value {
            1 => CurveType::Logarithmic,
            2 => CurveType::Exponential,
            3 => CurveType::SCurve,
            _ => CurveType::Linear,
        }
    }
    
    /// Convert to integer (for FFI)
    pub fn to_int(&self) -> i32 {
        match self {
            CurveType::Linear => 0,
            CurveType::Logarithmic => 1,
            CurveType::Exponential => 2,
            CurveType::SCurve => 3,
        }
    }
}

/// Single automation point at a specific beat position
#[derive(Clone, Debug)]
pub struct AutomationPoint {
    /// Position in beats (quarter notes)
    pub beat: f64,
    /// Parameter value (0.0 - 1.0 normalized, or actual range)
    pub value: f32,
    /// Interpolation curve type to next point
    pub curve_type: CurveType,
}

impl AutomationPoint {
    /// Create a new automation point
    pub fn new(beat: f64, value: f32, curve_type: CurveType) -> Self {
        Self {
            beat,
            value,
            curve_type,
        }
    }
}

/// Automation lane containing points for a single parameter
#[derive(Clone, Debug)]
pub struct AutomationLane {
    /// Parameter identifier (e.g., "track_0_fader", "track_0_pan")
    pub parameter_id: String,
    /// Automation points sorted by beat position
    pub points: Vec<AutomationPoint>,
    /// Whether automation is enabled for this parameter
    pub enabled: bool,
    /// Default value when no automation exists
    pub default_value: f32,
    /// Minimum allowed value
    pub min_value: f32,
    /// Maximum allowed value
    pub max_value: f32,
}

impl AutomationLane {
    /// Create a new automation lane for a parameter
    pub fn new(parameter_id: &str, default_value: f32) -> Self {
        Self {
            parameter_id: parameter_id.to_string(),
            points: Vec::new(),
            enabled: true,
            default_value,
            min_value: 0.0,
            max_value: 1.0,
        }
    }
    
    /// Create with full range specification
    pub fn new_with_range(parameter_id: &str, default_value: f32, min: f32, max: f32) -> Self {
        Self {
            parameter_id: parameter_id.to_string(),
            points: Vec::new(),
            enabled: true,
            default_value,
            min_value: min,
            max_value: max,
        }
    }
    
    /// Add a point to the lane (maintains sorted order)
    pub fn add_point(&mut self, point: AutomationPoint) {
        // Find insertion position to maintain sorted order
        let pos = self.points.binary_search_by(|p| {
            p.beat.partial_cmp(&point.beat).unwrap()
        }).unwrap_or_else(|e| e);
        
        self.points.insert(pos, point);
    }
    
    /// Add a point with explicit values
    pub fn add_point_at(&mut self, beat: f64, value: f32, curve_type: CurveType) {
        self.add_point(AutomationPoint::new(beat, value, curve_type));
    }
    
    /// Remove a point at specific beat (if exists)
    pub fn remove_point_at(&mut self, beat: f64) {
        if let Some(pos) = self.points.iter().position(|p| (p.beat - beat).abs() < 0.0001) {
            self.points.remove(pos);
        }
    }
    
    /// Clear all points
    pub fn clear(&mut self) {
        self.points.clear();
    }
    
    /// Get number of points
    pub fn point_count(&self) -> usize {
        self.points.len()
    }
    
    /// Check if lane has any points
    pub fn is_empty(&self) -> bool {
        self.points.is_empty()
    }
    
    /// Get the value range
    pub fn value_range(&self) -> (f32, f32) {
        (self.min_value, self.max_value)
    }
    
    /// Normalize value to 0.0-1.0 range
    pub fn normalize_value(&self, value: f32) -> f32 {
        (value - self.min_value) / (self.max_value - self.min_value)
    }
    
    /// Denormalize value from 0.0-1.0 range
    pub fn denormalize_value(&self, normalized: f32) -> f32 {
        self.min_value + normalized * (self.max_value - self.min_value)
    }
    
    /// Get interpolated value at specific beat position
    /// Returns value in the lane's native range (not normalized)
    pub fn value_at(&self, beat: f64) -> f32 {
        if self.points.is_empty() {
            return self.default_value;
        }
        
        // Before first point - return first point's value
        if beat <= self.points[0].beat {
            return self.points[0].value;
        }
        
        // After last point - return last point's value
        if beat >= self.points[self.points.len() - 1].beat {
            return self.points[self.points.len() - 1].value;
        }
        
        // Find surrounding points
        let mut i = 0;
        while i < self.points.len() - 1 && self.points[i + 1].beat < beat {
            i += 1;
        }
        
        let p1 = &self.points[i];
        let p2 = &self.points[i + 1];
        
        // Calculate interpolation factor (0.0 to 1.0)
        let range = p2.beat - p1.beat;
        if range < 0.0001 {
            return p1.value;
        }
        let t = ((beat - p1.beat) / range) as f32;
        
        // Apply curve-based interpolation
        let interpolated = match p1.curve_type {
            CurveType::Linear => {
                p1.value + t * (p2.value - p1.value)
            }
            CurveType::Logarithmic => {
                // Logarithmic curve: slower at start, faster at end
                let log_t = (1.0 + t * 9.0).ln() / 10.0_f32.ln();
                p1.value + log_t * (p2.value - p1.value)
            }
            CurveType::Exponential => {
                // Exponential curve: faster at start, slower at end
                let exp_t = (t * 3.0).exp() / 3.0_f32.exp();
                let normalized_exp = (exp_t - 1.0 / 3.0_f32.exp()) / (1.0 - 1.0 / 3.0_f32.exp());
                p1.value + normalized_exp * (p2.value - p1.value)
            }
            CurveType::SCurve => {
                // S-curve: smooth ease-in-out
                let smooth_t = t * t * (3.0 - 2.0 * t);
                p1.value + smooth_t * (p2.value - p1.value)
            }
        };
        
        // Clamp to valid range
        interpolated.clamp(self.min_value, self.max_value)
    }
    
    /// Get value for audio callback (sample-accurate)
    /// 
    /// # Arguments
    /// * `sample` - Sample position since start
    /// * `sample_rate` - Audio sample rate (e.g., 48000)
    /// * `bpm` - Current tempo in beats per minute
    pub fn value_at_sample(&self, sample: u64, sample_rate: u32, bpm: f64) -> f32 {
        let beat = sample_to_beat(sample, sample_rate, bpm);
        self.value_at(beat)
    }
}

/// Convert sample position to beat position
/// 
/// # Formula
/// beats = (samples / sample_rate) * (bpm / 60)
pub fn sample_to_beat(sample: u64, sample_rate: u32, bpm: f64) -> f64 {
    let seconds = sample as f64 / sample_rate as f64;
    seconds * bpm / 60.0
}

/// Convert beat position to sample position
/// 
/// # Formula  
/// samples = (beats * 60 / bpm) * sample_rate
pub fn beat_to_sample(beat: f64, sample_rate: u32, bpm: f64) -> u64 {
    let seconds = beat * 60.0 / bpm;
    (seconds * sample_rate as f64) as u64
}

/// Automation recorder for capturing parameter changes
/// Supports Write, Touch, and Latch recording modes
pub struct AutomationRecorder {
    /// Current recording mode
    mode: AutomationMode,
    /// The automation lane being recorded
    lane: AutomationLane,
    /// Whether the control is currently being touched/adjusted
    is_touched: bool,
    /// Beat position when touch started
    touch_start_beat: f64,
    /// Last recorded value
    last_value: f32,
    /// Value at touch start (for Touch mode return behavior)
    touch_start_value: f32,
    /// Time of last recorded point (to avoid duplicate points)
    last_record_beat: f64,
    /// Minimum time between recorded points (1/128th note = 0.0078125 beats)
    min_record_interval: f64,
}

impl AutomationRecorder {
    /// Create a new automation recorder for a lane
    pub fn new(parameter_id: &str, default_value: f32, mode: AutomationMode) -> Self {
        Self {
            mode,
            lane: AutomationLane::new(parameter_id, default_value),
            is_touched: false,
            touch_start_beat: 0.0,
            last_value: default_value,
            touch_start_value: default_value,
            last_record_beat: -1.0,
            min_record_interval: 0.0078125, // 1/128th note
        }
    }
    
    /// Get current recording mode
    pub fn mode(&self) -> AutomationMode {
        self.mode
    }
    
    /// Set recording mode
    pub fn set_mode(&mut self, mode: AutomationMode) {
        self.mode = mode;
    }
    
    /// Get the underlying automation lane
    pub fn lane(&self) -> &AutomationLane {
        &self.lane
    }
    
    /// Get mutable access to the lane
    pub fn lane_mut(&mut self) -> &mut AutomationLane {
        &mut self.lane
    }
    
    /// Start touching the control (user begins adjustment)
    /// 
    /// # Arguments
    /// * `beat` - Current beat position
    /// * `current_value` - Current value of the control (will be recorded as starting point)
    /// * `playback_value` - Value from existing automation at this position (for Touch mode)
    pub fn start_touch(&mut self, beat: f64, current_value: f32, playback_value: f32) {
        if self.mode == AutomationMode::Off || self.mode == AutomationMode::Read {
            return;
        }
        
        self.is_touched = true;
        self.touch_start_beat = beat;
        self.touch_start_value = playback_value;
        self.last_value = current_value;
        self.last_record_beat = -1.0;
        
        // For Write mode, clear existing points in the region we're about to write
        if self.mode == AutomationMode::Write {
            // We can't clear yet because we don't know the end point
            // Points will be overwritten as we record
        }
        
        // Record initial point
        self.record_point(beat, current_value);
    }
    
    /// Update value while control is being touched
    /// 
    /// # Arguments
    /// * `beat` - Current beat position
    /// * `value` - Current value of the control
    pub fn update_value(&mut self, beat: f64, value: f32) {
        if !self.is_touched {
            return;
        }
        
        // Don't record too frequently (rate limiting)
        if (beat - self.last_record_beat).abs() < self.min_record_interval {
            self.last_value = value;
            return;
        }
        
        match self.mode {
            AutomationMode::Write => {
                // In Write mode, we overwrite everything
                // Remove any existing points near this time to avoid duplicates
                self.remove_points_in_range(beat - self.min_record_interval, beat + self.min_record_interval);
                self.record_point(beat, value);
            }
            AutomationMode::Touch => {
                // In Touch mode, record the current value
                self.record_point(beat, value);
            }
            AutomationMode::Latch => {
                // In Latch mode, same as Touch but stays at last value when released
                self.record_point(beat, value);
            }
            _ => {}
        }
        
        self.last_value = value;
    }
    
    /// End touching the control (user releases)
    /// 
    /// # Arguments
    /// * `beat` - Current beat position when released
    pub fn end_touch(&mut self, beat: f64) {
        if !self.is_touched {
            return;
        }
        
        // Record final point at release
        self.record_point(beat, self.last_value);
        
        // Handle Touch mode: return to existing automation
        if self.mode == AutomationMode::Touch {
            // Calculate return time (standard 1 second fade back)
            // At 120 BPM, 1 second = 2 beats
            let return_beats = 2.0;
            let end_beat = beat + return_beats;
            
            // Add point for return destination
            self.record_point(end_beat, self.touch_start_value);
        }
        
        self.is_touched = false;
    }
    
    /// Check if control is currently being touched
    pub fn is_touched(&self) -> bool {
        self.is_touched
    }
    
    /// Record a point with rate limiting
    fn record_point(&mut self, beat: f64, value: f32) {
        // Clamp value to valid range
        let clamped = value.clamp(self.lane.min_value, self.lane.max_value);
        
        self.lane.add_point(AutomationPoint {
            beat,
            value: clamped,
            curve_type: CurveType::Linear,
        });
        
        self.last_record_beat = beat;
    }
    
    /// Remove points within a beat range (for Write mode)
    fn remove_points_in_range(&mut self, start_beat: f64, end_beat: f64) {
        self.lane.points.retain(|p| {
            !(p.beat >= start_beat && p.beat <= end_beat)
        });
    }
    
    /// Get current value considering recording state
    /// 
    /// Returns the recorded value if touched, otherwise the lane's value at position
    pub fn current_value(&self, beat: f64) -> f32 {
        if self.is_touched {
            self.last_value
        } else {
            self.lane.value_at(beat)
        }
    }
    
    /// Clear all recorded points
    pub fn clear(&mut self) {
        self.lane.clear();
        self.last_record_beat = -1.0;
    }
}

/// Automation recording modes
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum AutomationMode {
    /// Automation disabled
    Off,
    /// Read automation only (playback)
    Read,
    /// Overwrite all existing automation
    Write,
    /// Write when touched, return to existing after release
    Touch,
    /// Write when touched, stay at last value
    Latch,
}

impl AutomationMode {
    /// Convert integer to mode (for FFI)
    pub fn from_int(value: i32) -> Self {
        match value {
            0 => AutomationMode::Off,
            1 => AutomationMode::Read,
            2 => AutomationMode::Write,
            3 => AutomationMode::Touch,
            4 => AutomationMode::Latch,
            _ => AutomationMode::Off,
        }
    }
    
    /// Convert to integer (for FFI)
    pub fn to_int(&self) -> i32 {
        match self {
            AutomationMode::Off => 0,
            AutomationMode::Read => 1,
            AutomationMode::Write => 2,
            AutomationMode::Touch => 3,
            AutomationMode::Latch => 4,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_automation_lane_creation() {
        let lane = AutomationLane::new("track_0_fader", 0.75);
        assert_eq!(lane.parameter_id, "track_0_fader");
        assert_eq!(lane.default_value, 0.75);
        assert!(lane.is_empty());
        assert!(lane.enabled);
    }
    
    #[test]
    fn test_add_point() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(0.0, 0.0, CurveType::Linear);
        lane.add_point_at(4.0, 1.0, CurveType::Linear);
        
        assert_eq!(lane.point_count(), 2);
        assert_eq!(lane.points[0].beat, 0.0);
        assert_eq!(lane.points[1].beat, 4.0);
    }
    
    #[test]
    fn test_add_point_maintains_order() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(4.0, 1.0, CurveType::Linear);
        lane.add_point_at(0.0, 0.0, CurveType::Linear);
        lane.add_point_at(2.0, 0.5, CurveType::Linear);
        
        assert_eq!(lane.points[0].beat, 0.0);
        assert_eq!(lane.points[1].beat, 2.0);
        assert_eq!(lane.points[2].beat, 4.0);
    }
    
    #[test]
    fn test_remove_point() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(0.0, 0.0, CurveType::Linear);
        lane.add_point_at(4.0, 1.0, CurveType::Linear);
        
        lane.remove_point_at(0.0);
        assert_eq!(lane.point_count(), 1);
        assert_eq!(lane.points[0].beat, 4.0);
    }
    
    #[test]
    fn test_clear_points() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(0.0, 0.0, CurveType::Linear);
        lane.add_point_at(4.0, 1.0, CurveType::Linear);
        
        lane.clear();
        assert!(lane.is_empty());
    }
    
    #[test]
    fn test_curve_type_conversions() {
        assert_eq!(CurveType::from_int(0), CurveType::Linear);
        assert_eq!(CurveType::from_int(1), CurveType::Logarithmic);
        assert_eq!(CurveType::from_int(2), CurveType::Exponential);
        assert_eq!(CurveType::from_int(3), CurveType::SCurve);
        
        assert_eq!(CurveType::Linear.to_int(), 0);
        assert_eq!(CurveType::Logarithmic.to_int(), 1);
        assert_eq!(CurveType::Exponential.to_int(), 2);
        assert_eq!(CurveType::SCurve.to_int(), 3);
    }
    
    #[test]
    fn test_automation_mode_conversions() {
        assert_eq!(AutomationMode::from_int(0), AutomationMode::Off);
        assert_eq!(AutomationMode::from_int(1), AutomationMode::Read);
        assert_eq!(AutomationMode::from_int(2), AutomationMode::Write);
        assert_eq!(AutomationMode::from_int(3), AutomationMode::Touch);
        assert_eq!(AutomationMode::from_int(4), AutomationMode::Latch);
        
        assert_eq!(AutomationMode::Off.to_int(), 0);
        assert_eq!(AutomationMode::Read.to_int(), 1);
        assert_eq!(AutomationMode::Write.to_int(), 2);
        assert_eq!(AutomationMode::Touch.to_int(), 3);
        assert_eq!(AutomationMode::Latch.to_int(), 4);
    }
    
    #[test]
    fn test_value_range() {
        let lane = AutomationLane::new_with_range("track_0_fader", 0.0, -60.0, 12.0);
        assert_eq!(lane.value_range(), (-60.0, 12.0));
        
        // Test normalization
        assert_eq!(lane.normalize_value(-60.0), 0.0);
        assert_eq!(lane.normalize_value(12.0), 1.0);
        assert_eq!(lane.normalize_value(-24.0), 0.5);
        
        // Test denormalization
        assert_eq!(lane.denormalize_value(0.0), -60.0);
        assert_eq!(lane.denormalize_value(1.0), 12.0);
        assert_eq!(lane.denormalize_value(0.5), -24.0);
    }
    
    #[test]
    fn test_interpolation_empty_lane() {
        let lane = AutomationLane::new("track_0_fader", 0.75);
        assert_eq!(lane.value_at(0.0), 0.75); // Returns default value
        assert_eq!(lane.value_at(4.0), 0.75);
    }
    
    #[test]
    fn test_interpolation_before_first_point() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(2.0, 0.5, CurveType::Linear);
        lane.add_point_at(4.0, 1.0, CurveType::Linear);
        
        // Before first point should return first point's value
        assert_eq!(lane.value_at(0.0), 0.5);
        assert_eq!(lane.value_at(1.0), 0.5);
    }
    
    #[test]
    fn test_interpolation_after_last_point() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(0.0, 0.0, CurveType::Linear);
        lane.add_point_at(2.0, 0.5, CurveType::Linear);
        
        // After last point should return last point's value
        assert_eq!(lane.value_at(4.0), 0.5);
        assert_eq!(lane.value_at(10.0), 0.5);
    }
    
    #[test]
    fn test_linear_interpolation() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(0.0, 0.0, CurveType::Linear);
        lane.add_point_at(4.0, 1.0, CurveType::Linear);
        
        // Test mid-point
        let value = lane.value_at(2.0);
        assert!((value - 0.5).abs() < 0.001, "Expected 0.5, got {}", value);
        
        // Test quarter point
        let value = lane.value_at(1.0);
        assert!((value - 0.25).abs() < 0.001, "Expected 0.25, got {}", value);
    }
    
    #[test]
    fn test_sc_curve_interpolation() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(0.0, 0.0, CurveType::SCurve);
        lane.add_point_at(4.0, 1.0, CurveType::SCurve);
        
        // S-curve should be smoother at start and end
        let value_mid = lane.value_at(2.0);
        assert!((value_mid - 0.5).abs() < 0.001, "Expected ~0.5, got {}", value_mid);
        
        // At quarter point, S-curve should be less than linear
        let value_quarter = lane.value_at(1.0);
        // S-curve: t=0.25 gives smooth_t=0.25*0.25*(3-0.5)=0.15625
        assert!(value_quarter < 0.25, "S-curve at quarter should be < 0.25, got {}", value_quarter);
    }
    
    #[test]
    fn test_sample_accurate_value() {
        let mut lane = AutomationLane::new("track_0_fader", 0.0);
        lane.add_point_at(0.0, 0.0, CurveType::Linear);
        lane.add_point_at(4.0, 1.0, CurveType::Linear); // 4 beats at 120 BPM = 2 seconds
        
        // At 0 samples = beat 0
        let value = lane.value_at_sample(0, 48000, 120.0);
        assert!((value - 0.0).abs() < 0.001);
        
        // At 48000 samples = 1 second = 2 beats at 120 BPM
        let value = lane.value_at_sample(48000, 48000, 120.0);
        assert!((value - 0.5).abs() < 0.001, "Expected 0.5 at 2 beats, got {}", value);
        
        // At 96000 samples = 2 seconds = 4 beats
        let value = lane.value_at_sample(96000, 48000, 120.0);
        assert!((value - 1.0).abs() < 0.001);
    }
    
    #[test]
    fn test_sample_to_beat_conversion() {
        // 1 second at 48kHz = 48000 samples
        // 1 second at 120 BPM = 2 beats
        let beat = sample_to_beat(48000, 48000, 120.0);
        assert!((beat - 2.0).abs() < 0.001, "Expected 2.0 beats, got {}", beat);
        
        // 0 samples = 0 beats
        let beat = sample_to_beat(0, 48000, 120.0);
        assert_eq!(beat, 0.0);
        
        // 2 seconds at 60 BPM = 2 beats
        let beat = sample_to_beat(96000, 48000, 60.0);
        assert!((beat - 2.0).abs() < 0.001, "Expected 2.0 beats at 60 BPM, got {}", beat);
    }
    
    #[test]
    fn test_beat_to_sample_conversion() {
        // 2 beats at 120 BPM = 1 second = 48000 samples
        let samples = beat_to_sample(2.0, 48000, 120.0);
        assert_eq!(samples, 48000);
        
        // 0 beats = 0 samples
        let samples = beat_to_sample(0.0, 48000, 120.0);
        assert_eq!(samples, 0);
        
        // 2 beats at 60 BPM = 2 seconds = 96000 samples
        let samples = beat_to_sample(2.0, 48000, 60.0);
        assert_eq!(samples, 96000);
    }
    
    // === AutomationRecorder Tests ===
    
    #[test]
    fn test_recorder_write_mode() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.0, AutomationMode::Write);
        
        // Start touch at beat 0, value 0.5
        recorder.start_touch(0.0, 0.5, 0.0);
        assert!(recorder.is_touched());
        
        // Update value at beat 1
        recorder.update_value(1.0, 0.7);
        
        // Update value at beat 2
        recorder.update_value(2.0, 0.9);
        
        // End touch at beat 3
        recorder.end_touch(3.0);
        assert!(!recorder.is_touched());
        
        // Should have recorded points
        assert!(recorder.lane().point_count() >= 3);
        
        // Verify interpolation works
        let value = recorder.lane().value_at(1.5);
        assert!(value >= 0.7 && value <= 0.9);
    }
    
    #[test]
    fn test_recorder_touch_mode() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.0, AutomationMode::Touch);
        
        // Pre-existing automation
        recorder.lane_mut().add_point_at(0.0, 0.0, CurveType::Linear);
        recorder.lane_mut().add_point_at(10.0, 1.0, CurveType::Linear);
        
        // Start touch at beat 2, current value 0.5, playback value ~0.2
        recorder.start_touch(2.0, 0.5, 0.2);
        
        // Update while touching
        recorder.update_value(3.0, 0.7);
        recorder.update_value(4.0, 0.8);
        
        // End touch at beat 5
        recorder.end_touch(5.0);
        
        // Touch mode should add return point
        // Should have more points now (original 2 + recorded points + return point)
        assert!(recorder.lane().point_count() > 2, "Touch mode should add points during recording");
        
        // After recording, the lane should have automation data
        // Value at end should be the recorded value
        let value = recorder.lane().value_at(5.0);
        assert!(value >= 0.5, "Touch mode should record the value at release, got {}", value);
    }
    
    #[test]
    fn test_recorder_latch_mode() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.0, AutomationMode::Latch);
        
        // Start touch at beat 0
        recorder.start_touch(0.0, 0.5, 0.0);
        
        // Update while touching
        recorder.update_value(1.0, 0.7);
        recorder.update_value(2.0, 0.9);
        
        // End touch at beat 3
        recorder.end_touch(3.0);
        
        // Latch mode stays at last value - no return point added
        // Check that after release, value stays latched
        let value_after = recorder.lane().value_at(5.0);
        assert!((value_after - 0.9).abs() < 0.1, "Latch mode should stay at last value");
    }
    
    #[test]
    fn test_recorder_read_mode_no_recording() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.5, AutomationMode::Read);
        
        // Try to record in Read mode - should be ignored
        recorder.start_touch(0.0, 0.7, 0.5);
        assert!(!recorder.is_touched()); // Should not be touched in Read mode
        
        recorder.update_value(1.0, 0.9);
        recorder.end_touch(2.0);
        
        // Should still be empty
        assert!(recorder.lane().is_empty());
    }
    
    #[test]
    fn test_recoder_off_mode_no_recording() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.5, AutomationMode::Off);
        
        // Try to record in Off mode - should be ignored
        recorder.start_touch(0.0, 0.7, 0.5);
        assert!(!recorder.is_touched());
        
        // Should be empty
        assert!(recorder.lane().is_empty());
    }
    
    #[test]
    fn test_recorder_clear() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.0, AutomationMode::Write);
        
        recorder.start_touch(0.0, 0.5, 0.0);
        recorder.update_value(1.0, 0.7);
        recorder.end_touch(2.0);
        
        assert!(!recorder.lane().is_empty());
        
        recorder.clear();
        assert!(recorder.lane().is_empty());
    }
    
    #[test]
    fn test_recorder_current_value_while_touched() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.0, AutomationMode::Write);
        
        // When not touched, returns lane value (default)
        assert_eq!(recorder.current_value(0.0), 0.0);
        
        // Start touching
        recorder.start_touch(0.0, 0.8, 0.0);
        
        // While touched, returns last recorded value
        assert_eq!(recorder.current_value(0.0), 0.8);
        
        // Update value
        recorder.update_value(1.0, 0.9);
        assert_eq!(recorder.current_value(1.0), 0.9);
    }
    
    #[test]
    fn test_recorder_mode_switching() {
        let mut recorder = AutomationRecorder::new("track_0_fader", 0.0, AutomationMode::Off);
        assert_eq!(recorder.mode(), AutomationMode::Off);
        
        recorder.set_mode(AutomationMode::Write);
        assert_eq!(recorder.mode(), AutomationMode::Write);
        
        recorder.set_mode(AutomationMode::Touch);
        assert_eq!(recorder.mode(), AutomationMode::Touch);
    }
}
