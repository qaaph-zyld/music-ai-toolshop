//! Project management
//! 
//! Save/load project state, tracks, and settings.

use std::path::Path;
use std::fs;
use crate::plugin::{PluginChain, PluginInfo, PluginInstance};

/// Track type (audio or MIDI)
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TrackType {
    /// Audio track with sample playback
    Audio,
    /// MIDI track with instrument
    Midi,
    /// Group/return track
    Group,
}

/// Track in a project
#[derive(Debug, Clone)]
pub struct Track {
    name: String,
    track_type: TrackType,
    volume_db: f32,
    pan: f32,
    muted: bool,
    soloed: bool,
    plugin_chain: PluginChain,
}

impl Track {
    /// Create new track
    pub fn new(name: &str, track_type: TrackType) -> Self {
        Self {
            name: name.to_string(),
            track_type,
            volume_db: 0.0,
            pan: 0.0,
            muted: false,
            soloed: false,
            plugin_chain: PluginChain::new(),
        }
    }
    
    /// Get track name
    pub fn name(&self) -> &str {
        &self.name
    }
    
    /// Get track type
    pub fn track_type(&self) -> TrackType {
        self.track_type
    }
    
    /// Check if audio track
    pub fn is_audio(&self) -> bool {
        self.track_type == TrackType::Audio
    }
    
    /// Check if MIDI track
    pub fn is_midi(&self) -> bool {
        self.track_type == TrackType::Midi
    }
    
    /// Set volume in dB
    pub fn set_volume_db(&mut self, db: f32) {
        self.volume_db = db;
    }
    
    /// Get volume in dB
    pub fn volume_db(&self) -> f32 {
        self.volume_db
    }
    
    /// Set pan (-1.0 = left, 0.0 = center, 1.0 = right)
    pub fn set_pan(&mut self, pan: f32) {
        self.pan = pan.clamp(-1.0, 1.0);
    }
    
    /// Get pan
    pub fn pan(&self) -> f32 {
        self.pan
    }
    
    /// Mute track
    pub fn mute(&mut self) {
        self.muted = true;
    }
    
    /// Unmute track
    pub fn unmute(&mut self) {
        self.muted = false;
    }
    
    /// Check if muted
    pub fn is_muted(&self) -> bool {
        self.muted
    }
    
    /// Solo track
    pub fn solo(&mut self) {
        self.soloed = true;
    }
    
    /// Unsolo track
    pub fn unsolo(&mut self) {
        self.soloed = false;
    }
    
    /// Check if soloed
    pub fn is_soloed(&self) -> bool {
        self.soloed
    }

    /// Get plugin chain reference
    pub fn plugin_chain(&self) -> &PluginChain {
        &self.plugin_chain
    }

    /// Get mutable plugin chain reference
    pub fn plugin_chain_mut(&mut self) -> &mut PluginChain {
        &mut self.plugin_chain
    }

    /// Add plugin to track
    pub fn add_plugin(&mut self, instance_id: &str, plugin_info: PluginInfo) -> usize {
        self.plugin_chain.add_plugin(instance_id, plugin_info)
    }

    /// Remove plugin from track by index
    pub fn remove_plugin(&mut self, index: usize) -> Option<PluginInstance> {
        self.plugin_chain.remove(index)
    }

    /// Process audio through the track's plugin chain
    /// 
    /// Routes input audio buffer through all enabled plugins in the chain.
    /// If track is muted, output will be silence.
    pub fn process(&mut self, input: &[f32], output: &mut [f32]) {
        // If track is muted, output silence
        if self.muted {
            for sample in output.iter_mut() {
                *sample = 0.0;
            }
            return;
        }
        
        // Process through plugin chain
        self.plugin_chain.process(input, output);
    }
}

/// Project containing tracks and settings
#[derive(Debug, Clone)]
pub struct Project {
    name: String,
    sample_rate: u32,
    tempo: f32,
    time_signature_numerator: u8,
    time_signature_denominator: u8,
    tracks: Vec<Track>,
}

impl Project {
    /// Create new project
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            sample_rate: 48000,
            tempo: 120.0,
            time_signature_numerator: 4,
            time_signature_denominator: 4,
            tracks: Vec::new(),
        }
    }
    
    /// Get project name
    pub fn name(&self) -> &str {
        &self.name
    }
    
    /// Set project name
    pub fn set_name(&mut self, name: &str) {
        self.name = name.to_string();
    }
    
    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
    
    /// Set sample rate
    pub fn set_sample_rate(&mut self, sample_rate: u32) {
        self.sample_rate = sample_rate;
    }
    
    /// Get tempo (BPM)
    pub fn tempo(&self) -> f32 {
        self.tempo
    }
    
    /// Set tempo (BPM)
    pub fn set_tempo(&mut self, tempo: f32) {
        self.tempo = tempo.max(1.0).min(999.0);
    }
    
    /// Get time signature
    pub fn time_signature(&self) -> (u8, u8) {
        (self.time_signature_numerator, self.time_signature_denominator)
    }
    
    /// Set time signature
    pub fn set_time_signature(&mut self, numerator: u8, denominator: u8) {
        if numerator > 0 && denominator > 0 {
            self.time_signature_numerator = numerator;
            self.time_signature_denominator = denominator;
        }
    }
    
    /// Add track
    pub fn add_track(&mut self, track: Track) {
        self.tracks.push(track);
    }
    
    /// Get track count
    pub fn track_count(&self) -> usize {
        self.tracks.len()
    }
    
    /// Get track by index
    pub fn get_track(&self, index: usize) -> Option<&Track> {
        self.tracks.get(index)
    }
    
    /// Get mutable track
    pub fn get_track_mut(&mut self, index: usize) -> Option<&mut Track> {
        self.tracks.get_mut(index)
    }
    
    /// Remove track
    pub fn remove_track(&mut self, index: usize) -> Option<Track> {
        if index < self.tracks.len() {
            Some(self.tracks.remove(index))
        } else {
            None
        }
    }
    
    /// Get all tracks
    pub fn tracks(&self) -> &[Track] {
        &self.tracks
    }
    
    /// Clear all tracks
    pub fn clear_tracks(&mut self) {
        self.tracks.clear();
    }
    
    /// Serialize to JSON string
    pub fn to_json(&self) -> String {
        // Simple JSON serialization without external deps
        let mut json = String::new();
        json.push_str("{\n");
        json.push_str(&format!("  \"name\": \"{}\",\n", self.name));
        json.push_str(&format!("  \"sample_rate\": {},\n", self.sample_rate));
        json.push_str(&format!("  \"tempo\": {},\n", self.tempo));
        json.push_str(&format!("  \"time_signature\": [{}, {}],\n", 
            self.time_signature_numerator, self.time_signature_denominator));
        
        // Tracks array
        json.push_str("  \"tracks\": [\n");
        for (i, track) in self.tracks.iter().enumerate() {
            json.push_str("    {\n");
            json.push_str(&format!("      \"name\": \"{}\",\n", track.name));
            let type_str = match track.track_type {
                TrackType::Audio => "Audio",
                TrackType::Midi => "Midi",
                TrackType::Group => "Group",
            };
            json.push_str(&format!("      \"track_type\": \"{}\",\n", type_str));
            json.push_str(&format!("      \"volume_db\": {},\n", track.volume_db));
            json.push_str(&format!("      \"pan\": {},\n", track.pan));
            json.push_str(&format!("      \"muted\": {},\n", track.muted));
            json.push_str(&format!("      \"soloed\": {}", track.soloed));
            json.push_str("\n    }");
            if i < self.tracks.len() - 1 {
                json.push_str(",");
            }
            json.push_str("\n");
        }
        json.push_str("  ]\n");
        json.push_str("}");
        
        json
    }
    
    /// Deserialize from JSON (stub - would need serde for full implementation)
    pub fn from_json(json: &str) -> Result<Self, String> {
        // This is a simplified parser for demonstration
        // Full implementation would use serde_json
        let mut project = Project::new("Loaded");
        
        // Extract name - handle both "name": " and "name":" formats
        if let Some(name_start) = json.find("\"name\"") {
            let after_name = &json[name_start + 6..]; // Skip past "name"
            // Find the colon
            if let Some(colon_pos) = after_name.find(':') {
                let after_colon = &after_name[colon_pos + 1..];
                // Find opening quote
                if let Some(quote_start) = after_colon.find('"') {
                    let after_quote = &after_colon[quote_start + 1..];
                    // Find closing quote
                    if let Some(quote_end) = after_quote.find('"') {
                        project.name = after_quote[..quote_end].to_string();
                    }
                }
            }
        }
        
        // Extract sample_rate
        if let Some(sr_start) = json.find("\"sample_rate\"") {
            let after_sr = &json[sr_start + 14..];
            if let Some(colon_pos) = after_sr.find(':') {
                let after_colon = &after_sr[colon_pos + 1..];
                let value_end = after_colon.find(',').or_else(|| after_colon.find('}'))
                    .unwrap_or(after_colon.len());
                let value_str = &after_colon[..value_end].trim();
                if let Ok(sr) = value_str.parse::<u32>() {
                    project.sample_rate = sr;
                }
            }
        }
        
        // Extract tempo
        if let Some(tempo_start) = json.find("\"tempo\"") {
            let after_tempo = &json[tempo_start + 7..];
            if let Some(colon_pos) = after_tempo.find(':') {
                let after_colon = &after_tempo[colon_pos + 1..];
                let value_end = after_colon.find(',').or_else(|| after_colon.find('}'))
                    .unwrap_or(after_colon.len());
                let value_str = &after_colon[..value_end].trim();
                if let Ok(t) = value_str.parse::<f32>() {
                    project.tempo = t;
                }
            }
        }
        
        // Count tracks by looking for track objects
        // Simple heuristic: count occurrences of "track_type"
        let mut search_start = 0;
        while let Some(pos) = json[search_start..].find("\"track_type\"") {
            project.add_track(Track::new("Track", TrackType::Audio)); // Add placeholder track
            search_start += pos + 12; // Advance past this occurrence
        }
        
        Ok(project)
    }
    
    /// Save to file
    pub fn save(&self, path: &Path) -> Result<(), String> {
        let json = self.to_json();
        fs::write(path, json).map_err(|e| e.to_string())
    }
    
    /// Load from file
    pub fn load(path: &Path) -> Result<Self, String> {
        let json = fs::read_to_string(path).map_err(|e| e.to_string())?;
        Self::from_json(&json)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::plugin::PluginFormat;
    
    #[test]
    fn test_project_creation() {
        let project = Project::new("Test");
        assert_eq!(project.name(), "Test");
        assert_eq!(project.tempo(), 120.0);
    }
    
    #[test]
    fn test_track_creation() {
        let track = Track::new("Drums", TrackType::Audio);
        assert_eq!(track.name(), "Drums");
        assert!(track.is_audio());
    }

    #[test]
    fn test_track_plugin_chain() {
        let mut track = Track::new("Vocals", TrackType::Audio);
        
        // Initially empty
        assert_eq!(track.plugin_chain().count(), 0);
        
        // Add plugins
        let eq_info = PluginInfo {
            name: "EQ".to_string(),
            vendor: "Test".to_string(),
            version: "1.0".to_string(),
            format: PluginFormat::Vst3,
            num_inputs: 2,
            num_outputs: 2,
            unique_id: "test.eq".to_string(),
        };
        
        let comp_info = PluginInfo {
            name: "Compressor".to_string(),
            vendor: "Test".to_string(),
            version: "1.0".to_string(),
            format: PluginFormat::Vst3,
            num_inputs: 2,
            num_outputs: 2,
            unique_id: "test.comp".to_string(),
        };
        
        let eq_slot = track.add_plugin("eq-1", eq_info);
        let comp_slot = track.add_plugin("comp-1", comp_info);
        
        assert_eq!(eq_slot, 0);
        assert_eq!(comp_slot, 1);
        assert_eq!(track.plugin_chain().count(), 2);
        
        // Verify plugins
        let eq_instance = track.plugin_chain().get(0).unwrap();
        assert_eq!(eq_instance.plugin_info().name, "EQ");
        assert_eq!(eq_instance.instance_id(), "eq-1");
        
        // Remove plugin
        let removed = track.remove_plugin(0);
        assert!(removed.is_some());
        assert_eq!(track.plugin_chain().count(), 1);
        
        // Remaining plugin should now be at slot 0
        let remaining = track.plugin_chain().get(0).unwrap();
        assert_eq!(remaining.plugin_info().name, "Compressor");
        assert_eq!(remaining.slot_index(), 0);
    }

    #[test]
    fn test_track_process_with_plugins() {
        use crate::plugin::{GainPlugin, Plugin};
        
        let mut track = Track::new("Test Track", TrackType::Audio);
        
        // Add a gain plugin with +6dB
        let mut gain_plugin = GainPlugin::new();
        gain_plugin.activate(48000.0, 64).unwrap();
        gain_plugin.set_gain_db(6.0);
        
        let plugin_info = gain_plugin.info().clone();
        track.add_plugin("gain-1", plugin_info);
        
        // Create input audio buffer (constant 0.5 values)
        let input = vec![0.5f32; 64];
        let mut output = vec![0.0f32; 64];
        
        // Process audio through track (through its plugin chain)
        track.process(&input, &mut output);
        
        // Verify output is amplified by ~2x (6dB gain)
        let expected = 0.5 * 10.0_f32.powf(6.0 / 20.0);
        assert!((output[0] - expected).abs() < 0.001, "Expected {}, got {}", expected, output[0]);
    }

    #[test]
    fn test_track_process_empty_chain() {
        // Track with no plugins should pass audio through unchanged
        let mut track = Track::new("Empty Track", TrackType::Audio);
        
        let input = vec![0.5f32; 64];
        let mut output = vec![0.0f32; 64];
        
        track.process(&input, &mut output);
        
        // Output should equal input (no plugins to process)
        assert!((output[0] - 0.5).abs() < 0.001);
        assert!((output[32] - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_track_process_muted() {
        use crate::plugin::{GainPlugin, Plugin};
        
        let mut track = Track::new("Muted Track", TrackType::Audio);
        
        // Add a gain plugin
        let mut gain_plugin = GainPlugin::new();
        gain_plugin.activate(48000.0, 64).unwrap();
        gain_plugin.set_gain_db(6.0);
        
        let plugin_info = gain_plugin.info().clone();
        track.add_plugin("gain-1", plugin_info);
        
        // Mute the track
        track.mute();
        assert!(track.is_muted());
        
        let input = vec![0.5f32; 64];
        let mut output = vec![0.0f32; 64];
        
        track.process(&input, &mut output);
        
        // Output should be silence (all zeros) regardless of plugins
        assert_eq!(output[0], 0.0);
        assert_eq!(output[32], 0.0);
        assert_eq!(output[63], 0.0);
    }
}
