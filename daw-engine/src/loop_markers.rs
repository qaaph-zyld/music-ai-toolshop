//! Loop marker system for defining and managing playback loops
//!
//! Provides loop region management with:
//! - Named loop regions
//! - Draggable start/end markers
//! - Enable/disable toggle
//! - Integration with Transport for auto-rewind

use std::collections::HashMap;

/// A loop marker region
#[derive(Debug, Clone, PartialEq)]
pub struct LoopRegion {
    /// Unique identifier for this loop
    pub id: String,
    /// Human-readable name (e.g., "Verse", "Chorus")
    pub name: String,
    /// Start position in beats
    pub start_beat: f64,
    /// End position in beats
    pub end_beat: f64,
    /// Whether this loop is enabled
    pub enabled: bool,
    /// Color for UI display (RGB hex, e.g., "#FF6B6B")
    pub color: String,
}

impl LoopRegion {
    /// Create a new loop region
    pub fn new(id: &str, name: &str, start_beat: f64, end_beat: f64) -> Self {
        Self {
            id: id.to_string(),
            name: name.to_string(),
            start_beat,
            end_beat,
            enabled: true,
            color: "#4A90E2".to_string(), // Default blue
        }
    }

    /// Get the duration of this loop in beats
    pub fn duration_beats(&self) -> f64 {
        self.end_beat - self.start_beat
    }

    /// Check if a given beat position is within this loop
    pub fn contains_beat(&self, beat: f64) -> bool {
        self.enabled && beat >= self.start_beat && beat < self.end_beat
    }

    /// Snap a beat position to the loop boundaries (for auto-rewind)
    pub fn wrap_beat(&self, beat: f64) -> f64 {
        if !self.enabled || self.duration_beats() <= 0.0 {
            return beat;
        }

        let duration = self.duration_beats();
        let relative = beat - self.start_beat;
        
        // Use modulo to wrap within loop
        let wrapped = relative.rem_euclid(duration);
        self.start_beat + wrapped
    }
}

/// Controller for managing loop markers
#[derive(Debug, Clone)]
pub struct LoopController {
    /// All defined loop regions
    regions: HashMap<String, LoopRegion>,
    /// Currently active loop region ID (if any)
    active_region_id: Option<String>,
    /// Whether looping is globally enabled
    looping_enabled: bool,
    /// Next available region ID number
    next_id: u32,
}

impl LoopController {
    /// Create a new loop controller
    pub fn new() -> Self {
        Self {
            regions: HashMap::new(),
            active_region_id: None,
            looping_enabled: false,
            next_id: 1,
        }
    }

    /// Create a new loop region
    pub fn create_region(&mut self, name: &str, start_beat: f64, end_beat: f64) -> String {
        let id = format!("loop-{}", self.next_id);
        self.next_id += 1;

        let region = LoopRegion::new(&id, name, start_beat, end_beat);
        self.regions.insert(id.clone(), region);

        // Auto-activate if first region
        if self.active_region_id.is_none() {
            self.active_region_id = Some(id.clone());
        }

        id
    }

    /// Get a region by ID
    pub fn get_region(&self, id: &str) -> Option<&LoopRegion> {
        self.regions.get(id)
    }

    /// Get a mutable region by ID
    pub fn get_region_mut(&mut self, id: &str) -> Option<&mut LoopRegion> {
        self.regions.get_mut(id)
    }

    /// Update region position
    pub fn set_region_position(&mut self, id: &str, start_beat: f64, end_beat: f64) -> bool {
        if let Some(region) = self.regions.get_mut(id) {
            region.start_beat = start_beat;
            region.end_beat = end_beat;
            true
        } else {
            false
        }
    }

    /// Rename a region
    pub fn rename_region(&mut self, id: &str, new_name: &str) -> bool {
        if let Some(region) = self.regions.get_mut(id) {
            region.name = new_name.to_string();
            true
        } else {
            false
        }
    }

    /// Enable/disable a specific region
    pub fn set_region_enabled(&mut self, id: &str, enabled: bool) -> bool {
        if let Some(region) = self.regions.get_mut(id) {
            region.enabled = enabled;
            true
        } else {
            false
        }
    }

    /// Delete a region
    pub fn delete_region(&mut self, id: &str) -> bool {
        let removed = self.regions.remove(id).is_some();
        
        // Clear active region if it was deleted
        if let Some(ref active_id) = self.active_region_id {
            if active_id == id {
                // Set to another region if available
                self.active_region_id = self.regions.keys().next().cloned();
            }
        }
        
        removed
    }

    /// Get all regions
    pub fn all_regions(&self) -> Vec<&LoopRegion> {
        self.regions.values().collect()
    }

    /// Get region count
    pub fn region_count(&self) -> usize {
        self.regions.len()
    }

    /// Set the active region
    pub fn set_active_region(&mut self, id: Option<&str>) -> bool {
        if let Some(id_str) = id {
            if self.regions.contains_key(id_str) {
                self.active_region_id = Some(id_str.to_string());
                true
            } else {
                false
            }
        } else {
            self.active_region_id = None;
            true
        }
    }

    /// Get the active region
    pub fn active_region(&self) -> Option<&LoopRegion> {
        self.active_region_id.as_ref()
            .and_then(|id| self.regions.get(id))
    }

    /// Get ID of active region
    pub fn active_region_id(&self) -> Option<&str> {
        self.active_region_id.as_deref()
    }

    /// Enable/disable global looping
    pub fn set_looping_enabled(&mut self, enabled: bool) {
        self.looping_enabled = enabled;
    }

    /// Check if looping is enabled
    pub fn is_looping_enabled(&self) -> bool {
        self.looping_enabled
    }

    /// Check if a beat position should trigger loop rewind
    pub fn should_loop_at_beat(&self, beat: f64) -> Option<f64> {
        if !self.looping_enabled {
            return None;
        }

        let region = self.active_region()?;
        
        if !region.enabled {
            return None;
        }

        // Check if we've passed the end of the loop
        if beat >= region.end_beat {
            Some(region.start_beat)
        } else {
            None
        }
    }

    /// Get loop boundaries for a given beat position
    /// Returns (start, end) if in a loop region, None otherwise
    pub fn get_loop_boundaries(&self, beat: f64) -> Option<(f64, f64)> {
        if !self.looping_enabled {
            return None;
        }

        self.active_region()
            .filter(|r| r.enabled && r.contains_beat(beat))
            .map(|r| (r.start_beat, r.end_beat))
    }
}

impl Default for LoopController {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_loop_region_creation() {
        let region = LoopRegion::new("loop-1", "Verse", 0.0, 16.0);
        
        assert_eq!(region.id, "loop-1");
        assert_eq!(region.name, "Verse");
        assert_eq!(region.start_beat, 0.0);
        assert_eq!(region.end_beat, 16.0);
        assert!(region.enabled);
        assert_eq!(region.duration_beats(), 16.0);
    }

    #[test]
    fn test_loop_region_contains_beat() {
        let region = LoopRegion::new("loop-1", "Verse", 4.0, 20.0);
        
        assert!(!region.contains_beat(0.0));  // Before start
        assert!(!region.contains_beat(3.99)); // Before start
        assert!(region.contains_beat(4.0));   // At start
        assert!(region.contains_beat(12.0));  // Middle
        assert!(region.contains_beat(19.99)); // Just before end
        assert!(!region.contains_beat(20.0)); // At end (exclusive)
        assert!(!region.contains_beat(25.0)); // After end
    }

    #[test]
    fn test_loop_region_contains_disabled() {
        let mut region = LoopRegion::new("loop-1", "Verse", 4.0, 20.0);
        region.enabled = false;
        
        assert!(!region.contains_beat(12.0)); // Should not contain when disabled
    }

    #[test]
    fn test_loop_region_wrap_beat() {
        let region = LoopRegion::new("loop-1", "Verse", 4.0, 20.0); // 16 beat loop
        
        // Within loop - no change
        assert_eq!(region.wrap_beat(4.0), 4.0);
        assert_eq!(region.wrap_beat(12.0), 12.0);
        assert_eq!(region.wrap_beat(19.99), 19.99);
        
        // Past end - should wrap to start
        assert_eq!(region.wrap_beat(20.0), 4.0);
        assert_eq!(region.wrap_beat(36.0), 4.0);  // Two loops
        assert_eq!(region.wrap_beat(52.0), 4.0);  // Three loops
        
        // Partway through a wrap
        assert_eq!(region.wrap_beat(24.0), 8.0);  // 24 - 16 = 8
        assert_eq!(region.wrap_beat(30.0), 14.0); // 30 - 16 = 14
    }

    #[test]
    fn test_loop_region_wrap_disabled() {
        let mut region = LoopRegion::new("loop-1", "Verse", 4.0, 20.0);
        region.enabled = false;
        
        // When disabled, should return beat unchanged
        assert_eq!(region.wrap_beat(25.0), 25.0);
    }

    #[test]
    fn test_loop_controller_creation() {
        let controller = LoopController::new();
        
        assert_eq!(controller.region_count(), 0);
        assert!(!controller.is_looping_enabled());
        assert!(controller.active_region_id().is_none());
    }

    #[test]
    fn test_create_region() {
        let mut controller = LoopController::new();
        
        let id = controller.create_region("Intro", 0.0, 8.0);
        
        assert_eq!(controller.region_count(), 1);
        assert!(controller.active_region_id().is_some());
        
        let region = controller.get_region(&id).unwrap();
        assert_eq!(region.name, "Intro");
        assert_eq!(region.start_beat, 0.0);
        assert_eq!(region.end_beat, 8.0);
    }

    #[test]
    fn test_auto_activate_first_region() {
        let mut controller = LoopController::new();
        
        assert!(controller.active_region_id().is_none());
        
        let id = controller.create_region("Verse", 0.0, 16.0);
        
        assert_eq!(controller.active_region_id(), Some(id.as_str()));
    }

    #[test]
    fn test_set_region_position() {
        let mut controller = LoopController::new();
        let id = controller.create_region("Verse", 0.0, 16.0);
        
        let success = controller.set_region_position(&id, 4.0, 20.0);
        
        assert!(success);
        let region = controller.get_region(&id).unwrap();
        assert_eq!(region.start_beat, 4.0);
        assert_eq!(region.end_beat, 20.0);
    }

    #[test]
    fn test_rename_region() {
        let mut controller = LoopController::new();
        let id = controller.create_region("Old Name", 0.0, 16.0);
        
        let success = controller.rename_region(&id, "Chorus");
        
        assert!(success);
        assert_eq!(controller.get_region(&id).unwrap().name, "Chorus");
    }

    #[test]
    fn test_set_region_enabled() {
        let mut controller = LoopController::new();
        let id = controller.create_region("Verse", 0.0, 16.0);
        
        let success = controller.set_region_enabled(&id, false);
        
        assert!(success);
        assert!(!controller.get_region(&id).unwrap().enabled);
    }

    #[test]
    fn test_delete_region() {
        let mut controller = LoopController::new();
        let id = controller.create_region("Verse", 0.0, 16.0);
        
        let success = controller.delete_region(&id);
        
        assert!(success);
        assert_eq!(controller.region_count(), 0);
        assert!(controller.active_region_id().is_none());
    }

    #[test]
    fn test_delete_active_region_switches_to_another() {
        let mut controller = LoopController::new();
        let id1 = controller.create_region("Verse", 0.0, 16.0);
        let id2 = controller.create_region("Chorus", 16.0, 32.0);
        
        // id1 should be active (first created)
        assert_eq!(controller.active_region_id(), Some(id1.as_str()));
        
        // Delete the active region
        controller.delete_region(&id1);
        
        // Should auto-switch to id2
        assert_eq!(controller.active_region_id(), Some(id2.as_str()));
    }

    #[test]
    fn test_all_regions() {
        let mut controller = LoopController::new();
        controller.create_region("Intro", 0.0, 8.0);
        controller.create_region("Verse", 8.0, 24.0);
        controller.create_region("Chorus", 24.0, 40.0);
        
        let regions = controller.all_regions();
        assert_eq!(regions.len(), 3);
    }

    #[test]
    fn test_set_active_region() {
        let mut controller = LoopController::new();
        let id1 = controller.create_region("Verse", 0.0, 16.0);
        let id2 = controller.create_region("Chorus", 16.0, 32.0);
        
        // Initially id1 is active
        assert_eq!(controller.active_region_id(), Some(id1.as_str()));
        
        // Switch to id2
        let success = controller.set_active_region(Some(&id2));
        assert!(success);
        assert_eq!(controller.active_region_id(), Some(id2.as_str()));
        
        // Clear active
        let success = controller.set_active_region(None);
        assert!(success);
        assert!(controller.active_region_id().is_none());
    }

    #[test]
    fn test_set_active_region_invalid() {
        let mut controller = LoopController::new();
        controller.create_region("Verse", 0.0, 16.0);
        
        // Try to set non-existent region
        let success = controller.set_active_region(Some("invalid-id"));
        assert!(!success);
    }

    #[test]
    fn test_looping_enabled() {
        let mut controller = LoopController::new();
        
        assert!(!controller.is_looping_enabled());
        
        controller.set_looping_enabled(true);
        assert!(controller.is_looping_enabled());
        
        controller.set_looping_enabled(false);
        assert!(!controller.is_looping_enabled());
    }

    #[test]
    fn test_should_loop_at_beat() {
        let mut controller = LoopController::new();
        controller.create_region("Verse", 4.0, 20.0);
        controller.set_looping_enabled(true);
        
        // Before end - no loop
        assert_eq!(controller.should_loop_at_beat(10.0), None);
        assert_eq!(controller.should_loop_at_beat(19.99), None);
        
        // At/past end - should loop to start
        assert_eq!(controller.should_loop_at_beat(20.0), Some(4.0));
        assert_eq!(controller.should_loop_at_beat(25.0), Some(4.0));
    }

    #[test]
    fn test_should_loop_disabled() {
        let mut controller = LoopController::new();
        controller.create_region("Verse", 4.0, 20.0);
        controller.set_looping_enabled(true);
        
        // Disable the region
        let active_id = controller.active_region_id().unwrap().to_string();
        controller.set_region_enabled(&active_id, false);
        
        // Should not loop even past end
        assert_eq!(controller.should_loop_at_beat(25.0), None);
    }

    #[test]
    fn test_should_loop_global_disabled() {
        let mut controller = LoopController::new();
        controller.create_region("Verse", 4.0, 20.0);
        // Looping not enabled globally
        
        assert_eq!(controller.should_loop_at_beat(25.0), None);
    }

    #[test]
    fn test_get_loop_boundaries() {
        let mut controller = LoopController::new();
        controller.create_region("Verse", 4.0, 20.0);
        controller.set_looping_enabled(true);
        
        // Within loop
        assert_eq!(controller.get_loop_boundaries(10.0), Some((4.0, 20.0)));
        
        // Outside loop
        assert_eq!(controller.get_loop_boundaries(2.0), None);
        assert_eq!(controller.get_loop_boundaries(25.0), None);
    }

    #[test]
    fn test_get_loop_boundaries_no_active() {
        let mut controller = LoopController::new();
        controller.create_region("Verse", 4.0, 20.0);
        controller.set_looping_enabled(true);
        controller.set_active_region(None);
        
        assert_eq!(controller.get_loop_boundaries(10.0), None);
    }

    #[test]
    fn test_operations_on_nonexistent_region() {
        let mut controller = LoopController::new();
        
        assert!(!controller.set_region_position("nonexistent", 0.0, 16.0));
        assert!(!controller.rename_region("nonexistent", "Name"));
        assert!(!controller.set_region_enabled("nonexistent", false));
        assert!(!controller.delete_region("nonexistent"));
        assert!(controller.get_region("nonexistent").is_none());
    }

    #[test]
    fn test_multiple_regions_auto_ids() {
        let mut controller = LoopController::new();
        
        let id1 = controller.create_region("Verse 1", 0.0, 16.0);
        let id2 = controller.create_region("Chorus", 16.0, 32.0);
        let id3 = controller.create_region("Verse 2", 32.0, 48.0);
        
        assert_eq!(id1, "loop-1");
        assert_eq!(id2, "loop-2");
        assert_eq!(id3, "loop-3");
    }
}
