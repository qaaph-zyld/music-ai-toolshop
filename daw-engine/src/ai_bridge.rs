//! Python AI Bridge
//! 
//! Subprocess-based bridge to call Python AI modules from Rust.
//! Communicates via JSON over stdin/stdout for simplicity and reliability.

use std::process::{Command, Stdio};
use std::io::Read;
use serde::{Deserialize, Serialize};

/// Result from AI generation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AIGeneratedClip {
    pub notes: Vec<AINote>,
    pub tempo: u32,
    pub key: String,
    pub bars: u32,
}

/// Note data from AI generation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AINote {
    pub pitch: u8,
    pub velocity: u8,
    #[serde(rename = "start")]
    pub start_beat: f32,
    #[serde(rename = "duration")]
    pub duration_beats: f32,
}

/// Stem extraction result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StemResult {
    pub drums: Option<String>,
    pub bass: Option<String>,
    pub vocals: Option<String>,
    pub other: Option<String>,
}

impl StemResult {
    pub fn drums_path(&self) -> Option<&str> {
        self.drums.as_deref()
    }
    pub fn bass_path(&self) -> Option<&str> {
        self.bass.as_deref()
    }
    pub fn vocals_path(&self) -> Option<&str> {
        self.vocals.as_deref()
    }
    pub fn other_path(&self) -> Option<&str> {
        self.other.as_deref()
    }
}

/// Suno track metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SunoTrack {
    pub id: String,
    pub title: String,
    pub artist: String,
    pub genre: String,
    pub tempo: u32,
    pub key: String,
    pub audio_path: String,
}

/// Python bridge for AI modules
pub struct AIBridge {
    python_path: String,
    ai_modules_path: String,
}

impl AIBridge {
    /// Create new AI bridge
    pub fn new() -> Self {
        Self {
            python_path: "python".to_string(),
            ai_modules_path: "d:\\Project\\music-ai-toolshop\\projects\\06-opendaw\\ai_modules".to_string(),
        }
    }
    
    /// Set custom Python executable path
    pub fn set_python_path(&mut self, path: &str) {
        self.python_path = path.to_string();
    }
    
    /// Set custom AI modules path
    pub fn set_ai_modules_path(&mut self, path: &str) {
        self.ai_modules_path = path.to_string();
    }
    
    /// Check if Python and AI modules are available
    pub fn is_available(&self) -> bool {
        match Command::new(&self.python_path)
            .arg("-c")
            .arg("import sys; print(sys.version)")
            .output() 
        {
            Ok(output) => output.status.success(),
            Err(_) => false,
        }
    }
    
    /// Generate MIDI pattern via ACE-Step
    pub fn generate_pattern(
        &self,
        style: &str,
        tempo: u32,
        key: &str,
        bars: u32,
    ) -> Result<AIGeneratedClip, String> {
        let script = format!(r#"
import sys
sys.path.insert(0, r'{}')
from pattern_generator import generate_to_daw_clip
import json

result = generate_to_daw_clip("{}", {}, "{}", {})
print(json.dumps(result))
"#, self.ai_modules_path, style, tempo, key, bars);
        
        let output = self.run_python(&script)?;
        self.parse_generated_clip(&output)
    }
    
    /// Extract stems from audio file
    pub fn extract_stems(&self, audio_path: &str) -> Result<StemResult, String> {
        let script = format!(r#"
import sys
sys.path.insert(0, r'{}')
from stem_extractor import extract_to_daw_tracks
import json

result = extract_to_daw_tracks(r'{}')
print(json.dumps(result))
"#, self.ai_modules_path, audio_path);
        
        let output = self.run_python(&script)?;
        self.parse_stem_result(&output)
    }
    
    /// Search Suno library
    pub fn search_suno_library(
        &self,
        query: Option<&str>,
        genre: Option<&str>,
        tempo_min: Option<u32>,
        tempo_max: Option<u32>,
    ) -> Result<Vec<SunoTrack>, String> {
        let query_str = query.unwrap_or("");
        let genre_str = genre.unwrap_or("");
        let tempo_min_str = tempo_min.map(|t| t.to_string()).unwrap_or("None".to_string());
        let tempo_max_str = tempo_max.map(|t| t.to_string()).unwrap_or("None".to_string());
        
        let script = format!(r#"
import sys
sys.path.insert(0, r'{}')
from suno_library import search_to_daw_results
import json

query = "{}" if "{}" else None
genre = "{}" if "{}" else None
tempo_min = {} if "{}" != "None" else None
tempo_max = {} if "{}" != "None" else None

results = search_to_daw_results(query, genre, tempo_min, tempo_max)
print(json.dumps(results))
"#, self.ai_modules_path, query_str, query_str, genre_str, genre_str, 
            tempo_min_str, tempo_min_str, tempo_max_str, tempo_max_str);
        
        let output = self.run_python(&script)?;
        self.parse_suno_tracks(&output)
    }
    
    /// Run Python script and capture output
    fn run_python(&self, script: &str) -> Result<String, String> {
        let mut child = Command::new(&self.python_path)
            .arg("-c")
            .arg(script)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to spawn Python: {}", e))?;
        
        let mut stdout = String::new();
        if let Some(ref mut pipe) = child.stdout {
            pipe.read_to_string(&mut stdout)
                .map_err(|e| format!("Failed to read stdout: {}", e))?;
        }
        
        let mut stderr = String::new();
        if let Some(ref mut pipe) = child.stderr {
            pipe.read_to_string(&mut stderr)
                .map_err(|e| format!("Failed to read stderr: {}", e))?;
        }
        
        let status = child.wait()
            .map_err(|e| format!("Failed to wait for Python: {}", e))?;
        
        if !status.success() {
            return Err(format!("Python script failed: {}", stderr));
        }
        
        // Extract JSON from output (last line that looks like JSON)
        let json_line = stdout.lines()
            .rev()
            .find(|line| line.trim().starts_with('{') || line.trim().starts_with('['))
            .unwrap_or(&stdout)
            .trim()
            .to_string();
        
        Ok(json_line)
    }
    
    /// Parse generated clip from JSON using serde
    fn parse_generated_clip(&self, json: &str) -> Result<AIGeneratedClip, String> {
        serde_json::from_str(json).map_err(|e| format!("Failed to parse clip: {}", e))
    }
    
    /// Parse stem result from JSON using serde
    fn parse_stem_result(&self, json: &str) -> Result<StemResult, String> {
        serde_json::from_str(json).map_err(|e| format!("Failed to parse stems: {}", e))
    }
    
    /// Parse Suno tracks from JSON using serde
    fn parse_suno_tracks(&self, json: &str) -> Result<Vec<SunoTrack>, String> {
        serde_json::from_str(json).map_err(|e| format!("Failed to parse tracks: {}", e))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bridge_creation() {
        let bridge = AIBridge::new();
        assert!(bridge.is_available());
    }

    #[test]
    fn test_generate_pattern() {
        let bridge = AIBridge::new();
        let result = bridge.generate_pattern("electronic", 120, "C", 4);
        
        // Bridge should successfully call Python and return a result
        // (stub data may have empty notes due to simple parser)
        assert!(result.is_ok());
        let clip = result.unwrap();
        assert_eq!(clip.tempo, 120);
        assert_eq!(clip.key, "C");
        assert_eq!(clip.bars, 4);
        // Note: Stub may return empty notes due to simple JSON parser
    }

    #[test]
    fn test_extract_stems() {
        let bridge = AIBridge::new();
        // Use the actual test file we created
        let test_path = "d:/Project/music-ai-toolshop/projects/06-opendaw/daw-engine/tests/assets/sine_440hz.wav";
        let result = bridge.extract_stems(test_path);
        
        // Bridge should successfully call Python and return stem paths
        assert!(result.is_ok());
        let stems = result.unwrap();
        // Verify we got all 4 stems back
        assert!(stems.drums_path().is_some());
        assert!(stems.bass_path().is_some());
        assert!(stems.vocals_path().is_some());
        assert!(stems.other_path().is_some());
    }

    #[test]
    fn test_search_suno() {
        let bridge = AIBridge::new();
        let result = bridge.search_suno_library(None, Some("electronic"), Some(120), Some(130));
        
        // Bridge should successfully call Python and return a result
        // (stub may return empty tracks due to simple parser)
        assert!(result.is_ok());
    }

    #[test]
    fn test_serde_json_parsing() {
        // Test AI generated clip parsing
        let json = r#"{"notes":[{"pitch":60,"velocity":100,"start":0.0,"duration":0.5}],"tempo":120,"key":"C","bars":4}"#;
        let clip: AIGeneratedClip = serde_json::from_str(json).unwrap();
        assert_eq!(clip.tempo, 120);
        assert_eq!(clip.key, "C");
        assert_eq!(clip.bars, 4);
        assert_eq!(clip.notes.len(), 1);
        assert_eq!(clip.notes[0].pitch, 60);
        
        // Test stem result parsing
        let stem_json = r#"{"drums":"drums.wav","bass":"bass.wav","vocals":null,"other":"other.wav"}"#;
        let stems: StemResult = serde_json::from_str(stem_json).unwrap();
        assert_eq!(stems.drums_path(), Some("drums.wav"));
        assert_eq!(stems.vocals_path(), None);
        
        // Test Suno track parsing
        let track_json = r#"{"id":"123","title":"Test","artist":"Artist","genre":"electronic","tempo":120,"key":"C","audio_path":"test.mp3"}"#;
        let track: SunoTrack = serde_json::from_str(track_json).unwrap();
        assert_eq!(track.id, "123");
        assert_eq!(track.title, "Test");
    }
}
