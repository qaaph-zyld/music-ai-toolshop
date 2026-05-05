//! Vocal Cleanup Module
//!
//! Rust interface to the Python vocal cleanup pipeline.
//! Provides FFI bindings for C++ UI integration.

use std::path::{Path, PathBuf};
use std::process::Command;

/// Configuration for vocal cleanup
#[derive(Debug, Clone)]
pub struct VocalCleanupSettings {
    /// Silence detection threshold in dB (default: -40)
    pub silence_threshold_db: f32,
    /// Minimum silence duration in seconds (default: 0.2)
    pub silence_min_duration: f32,
    /// Gap compression ratio 0.0-1.0 (default: 0.3)
    pub gap_compress_ratio: f32,
    /// Crossfade duration in ms (default: 10)
    pub crossfade_ms: f32,
    /// Breath detection sensitivity 0.0-1.0 (default: 0.5)
    pub breath_sensitivity: f32,
}

impl Default for VocalCleanupSettings {
    fn default() -> Self {
        Self {
            silence_threshold_db: -40.0,
            silence_min_duration: 0.2,
            gap_compress_ratio: 0.3,
            crossfade_ms: 10.0,
            breath_sensitivity: 0.5,
        }
    }
}

/// Result of vocal cleanup processing
#[derive(Debug, Clone)]
pub struct VocalCleanupResult {
    /// Number of gaps detected
    pub gaps_detected: i32,
    /// Number of breaths detected
    pub breaths_detected: i32,
    /// Original file duration in seconds
    pub original_duration: f32,
    /// Output file duration in seconds
    pub output_duration: f32,
    /// Time removed in seconds
    pub time_removed: f32,
    /// Whether processing succeeded
    pub success: bool,
    /// Error message if failed
    pub error_message: Option<String>,
}

impl Default for VocalCleanupResult {
    fn default() -> Self {
        Self {
            gaps_detected: 0,
            breaths_detected: 0,
            original_duration: 0.0,
            output_duration: 0.0,
            time_removed: 0.0,
            success: false,
            error_message: None,
        }
    }
}

/// Vocal cleanup processor
pub struct VocalCleanupProcessor {
    python_available: bool,
}

impl VocalCleanupProcessor {
    /// Create new processor
    pub fn new() -> Self {
        let python_available = Self::check_python_bridge();
        Self { python_available }
    }

    /// Check if Python bridge is available
    fn check_python_bridge() -> bool {
        Command::new("python")
            .args(["-c", "import sys; sys.exit(0)"])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    /// Check if processor is available
    pub fn is_available(&self) -> bool {
        self.python_available
    }

    /// Process audio file through vocal cleanup pipeline
    pub fn process(
        &self,
        input_path: &Path,
        output_path: &Path,
        settings: &VocalCleanupSettings,
    ) -> Result<VocalCleanupResult, VocalCleanupError> {
        if !self.python_available {
            return Err(VocalCleanupError::NotAvailable);
        }

        if !input_path.exists() {
            return Err(VocalCleanupError::InputNotFound);
        }

        // Build Python command to run pipeline
        let settings_json = format!(
            "{{'silence_threshold_db': {}, 'silence_min_duration': {}, 'gap_compress_ratio': {}, 'crossfade_ms': {}, 'breath_sensitivity': {}}}",
            settings.silence_threshold_db,
            settings.silence_min_duration,
            settings.gap_compress_ratio,
            settings.crossfade_ms,
            settings.breath_sensitivity
        );

        let input_path_str = input_path.display().to_string().replace('\\', "/");
        let output_path_str = output_path.display().to_string().replace('\\', "/");
        
        let python_script = format!(
            "import sys; sys.path.insert(0, 'ai_modules/vocal_cleanup'); from pipeline import VocalCleanupPipeline; p = VocalCleanupPipeline(silence_threshold_db={}, silence_min_duration={}, gap_compress_ratio={}, gap_crossfade_ms={}, breath_sensitivity={}); r = p.process('{}', '{}'); print(r)",
            settings.silence_threshold_db,
            settings.silence_min_duration,
            settings.gap_compress_ratio,
            settings.crossfade_ms,
            settings.breath_sensitivity,
            input_path_str,
            output_path_str
        );

        let result = Command::new("python")
            .arg("-c")
            .arg(&python_script)
            .current_dir(PathBuf::from("."))
            .output()
            .map_err(|e| VocalCleanupError::Internal(e.to_string()))?;

        if !result.status.success() {
            let stderr = String::from_utf8_lossy(&result.stderr);
            return Err(VocalCleanupError::Internal(format!(
                "Python pipeline failed: {}",
                stderr
            )));
        }

        // Parse result from Python output
        let stdout = String::from_utf8_lossy(&result.stdout);
        let result = Self::parse_result(&stdout)?;

        Ok(result)
    }

    /// Preview what would be processed without actually processing
    pub fn preview(
        &self,
        input_path: &Path,
        settings: &VocalCleanupSettings,
    ) -> Result<VocalCleanupResult, VocalCleanupError> {
        if !self.python_available {
            return Err(VocalCleanupError::NotAvailable);
        }

        if !input_path.exists() {
            return Err(VocalCleanupError::InputNotFound);
        }

        let input_path_str = input_path.display().to_string().replace('\\', "/");
        
        let python_script = format!(
            "import sys; sys.path.insert(0, 'ai_modules/vocal_cleanup'); from pipeline import VocalCleanupPipeline; p = VocalCleanupPipeline(silence_threshold_db={}, silence_min_duration={}, gap_compress_ratio={}, gap_crossfade_ms={}, breath_sensitivity={}); r = p.preview('{}'); print(r)",
            settings.silence_threshold_db,
            settings.silence_min_duration,
            settings.gap_compress_ratio,
            settings.crossfade_ms,
            settings.breath_sensitivity,
            input_path_str
        );

        let result = Command::new("python")
            .arg("-c")
            .arg(&python_script)
            .current_dir(PathBuf::from("."))
            .output()
            .map_err(|e| VocalCleanupError::Internal(e.to_string()))?;

        if !result.status.success() {
            let stderr = String::from_utf8_lossy(&result.stderr);
            return Err(VocalCleanupError::Internal(format!(
                "Python preview failed: {}",
                stderr
            )));
        }

        let stdout = String::from_utf8_lossy(&result.stdout);
        let result = Self::parse_result(&stdout)?;

        Ok(result)
    }

    /// Parse Python result string
    fn parse_result(output: &str) -> Result<VocalCleanupResult, VocalCleanupError> {
        // Simplified parsing - in real implementation would use JSON
        // For now, return success with defaults
        Ok(VocalCleanupResult {
            success: true,
            ..Default::default()
        })
    }
}

impl Default for VocalCleanupProcessor {
    fn default() -> Self {
        Self::new()
    }
}

/// Errors for vocal cleanup operations
#[derive(Debug, Clone, PartialEq)]
pub enum VocalCleanupError {
    NotAvailable,
    InputNotFound,
    OutputFailed,
    Internal(String),
}

impl std::fmt::Display for VocalCleanupError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            VocalCleanupError::NotAvailable => write!(f, "Vocal cleanup not available (Python bridge not found)"),
            VocalCleanupError::InputNotFound => write!(f, "Input file not found"),
            VocalCleanupError::OutputFailed => write!(f, "Failed to write output file"),
            VocalCleanupError::Internal(msg) => write!(f, "Internal error: {}", msg),
        }
    }
}

impl std::error::Error for VocalCleanupError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_settings_default() {
        let settings = VocalCleanupSettings::default();
        assert_eq!(settings.silence_threshold_db, -40.0);
        assert_eq!(settings.silence_min_duration, 0.2);
        assert_eq!(settings.gap_compress_ratio, 0.3);
        assert_eq!(settings.crossfade_ms, 10.0);
        assert_eq!(settings.breath_sensitivity, 0.5);
    }

    #[test]
    fn test_processor_creation() {
        let processor = VocalCleanupProcessor::new();
        // May or may not be available depending on Python
        let _ = processor.is_available();
    }

    #[test]
    fn test_result_default() {
        let result = VocalCleanupResult::default();
        assert_eq!(result.gaps_detected, 0);
        assert_eq!(result.breaths_detected, 0);
        assert!(!result.success);
    }

    #[test]
    fn test_error_display() {
        let err1 = VocalCleanupError::NotAvailable;
        let err2 = VocalCleanupError::InputNotFound;
        let err3 = VocalCleanupError::Internal("test".to_string());

        assert!(err1.to_string().contains("not available"));
        assert!(err2.to_string().contains("not found"));
        assert!(err3.to_string().contains("Internal error"));
    }

    #[test]
    fn test_custom_settings() {
        let settings = VocalCleanupSettings {
            silence_threshold_db: -50.0,
            silence_min_duration: 0.3,
            gap_compress_ratio: 0.5,
            crossfade_ms: 20.0,
            breath_sensitivity: 0.7,
        };

        assert_eq!(settings.silence_threshold_db, -50.0);
        assert_eq!(settings.silence_min_duration, 0.3);
        assert_eq!(settings.gap_compress_ratio, 0.5);
        assert_eq!(settings.crossfade_ms, 20.0);
        assert_eq!(settings.breath_sensitivity, 0.7);
    }
}
