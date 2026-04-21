//! MusicGen text-to-music generation bridge
//!
//! Provides FFI to AudioCraft MusicGen for AI-generated music clips.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::io::Write;

/// MusicGen model sizes
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum ModelSize {
    Small,
    Medium,
    Large,
    Melody,
}

impl ModelSize {
    pub fn as_str(&self) -> &'static str {
        match self {
            ModelSize::Small => "small",
            ModelSize::Medium => "medium",
            ModelSize::Large => "large",
            ModelSize::Melody => "melody",
        }
    }
}

/// Generation request parameters
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationRequest {
    pub prompt: String,
    pub duration_seconds: u32,
    pub model_size: ModelSize,
    pub output_path: Option<PathBuf>,
}

impl Default for GenerationRequest {
    fn default() -> Self {
        Self {
            prompt: String::new(),
            duration_seconds: 10,
            model_size: ModelSize::Small,
            output_path: None,
        }
    }
}

/// Generation progress update
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GenerationProgress {
    pub percent: u8,
    pub stage: String,
}

/// Generation result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationResult {
    pub success: bool,
    pub prompt: String,
    pub duration: u32,
    pub sample_rate: u32,
    pub output_path: Option<PathBuf>,
    pub model_used: String,
    pub error: Option<String>,
}

/// MusicGen availability check
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MusicGenStatus {
    pub available: bool,
    pub torch_version: Option<String>,
    pub cuda_available: bool,
    pub models_available: Vec<String>,
    pub error: Option<String>,
}

/// MusicGen bridge for subprocess communication
pub struct MusicGenBridge {
    python_executable: String,
    working_dir: PathBuf,
}

impl MusicGenBridge {
    /// Create new bridge instance
    pub fn new() -> Result<Self, String> {
        let working_dir = PathBuf::from("ai_modules");
        if !working_dir.exists() {
            return Err("ai_modules directory not found".to_string());
        }
        
        Ok(Self {
            python_executable: "python".to_string(),
            working_dir: working_dir.parent().unwrap_or(&working_dir).to_path_buf(),
        })
    }
    
    /// Create bridge with custom Python executable
    pub fn with_python(python_path: impl Into<String>) -> Result<Self, String> {
        let working_dir = PathBuf::from("ai_modules");
        Ok(Self {
            python_executable: python_path.into(),
            working_dir: working_dir.parent().unwrap_or(&working_dir).to_path_buf(),
        })
    }
    
    /// Check if MusicGen is available
    pub fn check(&self) -> Result<MusicGenStatus, String> {
        let output = Command::new(&self.python_executable)
            .args(&["-m", "ai_modules.musicgen", "check"])
            .current_dir(&self.working_dir)
            .output()
            .map_err(|e| format!("Failed to run check: {}", e))?;
        
        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Ok(MusicGenStatus {
                available: false,
                torch_version: None,
                cuda_available: false,
                models_available: vec![],
                error: Some(stderr.to_string()),
            });
        }
        
        let stdout = String::from_utf8_lossy(&output.stdout);
        serde_json::from_str(&stdout)
            .map_err(|e| format!("Failed to parse check result: {}", e))
    }
    
    /// Check if bridge is ready (convenience method)
    pub fn is_ready(&self) -> bool {
        match self.check() {
            Ok(status) => status.available,
            Err(_) => false,
        }
    }
    
    /// Generate music from text prompt
    pub fn generate(&self, request: GenerationRequest) -> Result<GenerationResult, String> {
        // Serialize request
        let json_request = serde_json::to_string(&request)
            .map_err(|e| format!("Failed to serialize request: {}", e))?;
        
        // Run generation
        let mut child = Command::new(&self.python_executable)
            .args(&["-m", "ai_modules.musicgen", "generate"])
            .current_dir(&self.working_dir)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to spawn generator: {}", e))?;
        
        // Write request to stdin
        if let Some(mut stdin) = child.stdin.take() {
            stdin.write_all(json_request.as_bytes())
                .map_err(|e| format!("Failed to write to stdin: {}", e))?;
        }
        
        // Wait for result
        let output = child.wait_with_output()
            .map_err(|e| format!("Failed to get output: {}", e))?;
        
        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("Generation failed: {}", stderr));
        }
        
        let stdout = String::from_utf8_lossy(&output.stdout);
        serde_json::from_str(&stdout)
            .map_err(|e| format!("Failed to parse result: {}", e))
    }
    
    /// Convenience: generate with minimal parameters
    pub fn generate_simple(
        &self,
        prompt: &str,
        duration_seconds: u32
    ) -> Result<GenerationResult, String> {
        self.generate(GenerationRequest {
            prompt: prompt.to_string(),
            duration_seconds,
            model_size: ModelSize::Small,
            output_path: None,
        })
    }
}

impl Default for MusicGenBridge {
    fn default() -> Self {
        Self::new().unwrap_or_else(|_| Self {
            python_executable: "python".to_string(),
            working_dir: PathBuf::from("."),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_size_serialization() {
        let size = ModelSize::Medium;
        assert_eq!(size.as_str(), "medium");
    }

    #[test]
    fn test_all_model_sizes() {
        assert_eq!(ModelSize::Small.as_str(), "small");
        assert_eq!(ModelSize::Medium.as_str(), "medium");
        assert_eq!(ModelSize::Large.as_str(), "large");
        assert_eq!(ModelSize::Melody.as_str(), "melody");
    }

    #[test]
    fn test_generation_request_default() {
        let req = GenerationRequest::default();
        assert_eq!(req.duration_seconds, 10);
        assert_eq!(req.model_size, ModelSize::Small);
        assert!(req.prompt.is_empty());
        assert!(req.output_path.is_none());
    }

    #[test]
    fn test_generation_request_custom() {
        let req = GenerationRequest {
            prompt: "electronic music".to_string(),
            duration_seconds: 30,
            model_size: ModelSize::Large,
            output_path: Some(PathBuf::from("output.wav")),
        };
        assert_eq!(req.prompt, "electronic music");
        assert_eq!(req.duration_seconds, 30);
        assert_eq!(req.model_size, ModelSize::Large);
        assert_eq!(req.output_path, Some(PathBuf::from("output.wav")));
    }

    #[test]
    fn test_generation_progress_equality() {
        let p1 = GenerationProgress { percent: 50, stage: "generating".to_string() };
        let p2 = GenerationProgress { percent: 50, stage: "generating".to_string() };
        assert_eq!(p1, p2);
    }

    #[test]
    fn test_generation_progress_values() {
        let progress = GenerationProgress { percent: 75, stage: "downloading".to_string() };
        assert_eq!(progress.percent, 75);
        assert_eq!(progress.stage, "downloading");
    }

    #[test]
    fn test_generation_result_structure() {
        let result = GenerationResult {
            success: true,
            prompt: "jazz".to_string(),
            duration: 15,
            sample_rate: 32000,
            output_path: Some(PathBuf::from("jazz.wav")),
            model_used: "medium".to_string(),
            error: None,
        };
        assert!(result.success);
        assert_eq!(result.prompt, "jazz");
        assert_eq!(result.duration, 15);
        assert_eq!(result.sample_rate, 32000);
    }

    #[test]
    fn test_musicgen_status_defaults() {
        let status = MusicGenStatus {
            available: false,
            torch_version: None,
            cuda_available: false,
            models_available: vec![],
            error: Some("test error".to_string()),
        };
        assert!(!status.available);
        assert_eq!(status.error, Some("test error".to_string()));
    }

    #[test]
    fn test_bridge_default() {
        let bridge: MusicGenBridge = Default::default();
        assert_eq!(bridge.python_executable, "python");
    }

    #[test]
    fn test_bridge_with_python() {
        let bridge = MusicGenBridge::with_python("python3").unwrap();
        assert_eq!(bridge.python_executable, "python3");
    }

    #[test]
    fn test_model_size_partial_eq() {
        assert_eq!(ModelSize::Small, ModelSize::Small);
        assert_ne!(ModelSize::Small, ModelSize::Medium);
    }
}
