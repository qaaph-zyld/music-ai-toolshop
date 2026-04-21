//! AI Stem Separation Module
//!
//! Bridge to demucs for AI-powered audio stem separation.
//! Supports separating audio into vocals, drums, bass, and other stems.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Type of stem produced by separation
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum StemType {
    Vocals,
    Drums,
    Bass,
    Other,
}

impl StemType {
    /// Get the file suffix for this stem type
    pub fn file_suffix(&self) -> &'static str {
        match self {
            StemType::Vocals => "vocals",
            StemType::Drums => "drums",
            StemType::Bass => "bass",
            StemType::Other => "other",
        }
    }

    /// Get all stem types
    pub fn all() -> [StemType; 4] {
        [StemType::Vocals, StemType::Drums, StemType::Bass, StemType::Other]
    }
}

/// Result of stem separation
#[derive(Debug, Clone, PartialEq)]
pub struct StemSeparationResult {
    /// Path to vocals stem file
    pub vocals_path: Option<PathBuf>,
    /// Path to drums stem file
    pub drums_path: Option<PathBuf>,
    /// Path to bass stem file
    pub bass_path: Option<PathBuf>,
    /// Path to other stem file
    pub other_path: Option<PathBuf>,
    /// Whether separation was successful
    pub success: bool,
    /// Error message if failed
    pub error_message: Option<String>,
}

impl StemSeparationResult {
    /// Create empty result
    pub fn new() -> Self {
        Self {
            vocals_path: None,
            drums_path: None,
            bass_path: None,
            other_path: None,
            success: false,
            error_message: None,
        }
    }

    /// Get path for specific stem type
    pub fn get_path(&self, stem_type: StemType) -> Option<&PathBuf> {
        match stem_type {
            StemType::Vocals => self.vocals_path.as_ref(),
            StemType::Drums => self.drums_path.as_ref(),
            StemType::Bass => self.bass_path.as_ref(),
            StemType::Other => self.other_path.as_ref(),
        }
    }

    /// Set path for specific stem type
    pub fn set_path(&mut self, stem_type: StemType, path: PathBuf) {
        match stem_type {
            StemType::Vocals => self.vocals_path = Some(path),
            StemType::Drums => self.drums_path = Some(path),
            StemType::Bass => self.bass_path = Some(path),
            StemType::Other => self.other_path = Some(path),
        }
    }

    /// Get count of successfully separated stems
    pub fn stem_count(&self) -> usize {
        StemType::all().iter().filter(|st| self.get_path(**st).is_some()).count()
    }
}

impl Default for StemSeparationResult {
    fn default() -> Self {
        Self::new()
    }
}

/// Progress callback for stem separation
pub type StemProgressCallback = Box<dyn Fn(f32, StemType) + Send>;

/// Stem separator using demucs
pub struct StemSeparator {
    demucs_script_path: PathBuf,
    cancel_flag: Arc<AtomicBool>,
    progress_callback: Option<StemProgressCallback>,
}

impl StemSeparator {
    /// Create new stem separator
    pub fn new() -> Self {
        // Default path to demucs bridge script
        let demucs_path = PathBuf::from("ai_modules/demucs/demucs_bridge.py");
        
        Self {
            demucs_script_path: demucs_path,
            cancel_flag: Arc::new(AtomicBool::new(false)),
            progress_callback: None,
        }
    }

    /// Create with custom demucs script path
    pub fn with_script_path(mut self, path: impl AsRef<Path>) -> Self {
        self.demucs_script_path = path.as_ref().to_path_buf();
        self
    }

    /// Set progress callback
    pub fn set_progress_callback(&mut self, callback: StemProgressCallback) {
        self.progress_callback = Some(callback);
    }

    /// Get cancel flag for external control
    pub fn cancel_flag(&self) -> Arc<AtomicBool> {
        Arc::clone(&self.cancel_flag)
    }

    /// Check if demucs is available
    pub fn is_available(&self) -> bool {
        self.demucs_script_path.exists()
    }

    /// Separate audio file into stems
    pub fn separate(
        &self,
        input_path: impl AsRef<Path>,
        output_dir: impl AsRef<Path>,
    ) -> Result<StemSeparationResult, StemSeparationError> {
        let input_path = input_path.as_ref();
        let output_dir = output_dir.as_ref();

        // Validate input file exists
        if !input_path.exists() {
            return Err(StemSeparationError::InputNotFound);
        }

        // Check demucs availability
        if !self.is_available() {
            return Err(StemSeparationError::DemucsNotAvailable);
        }

        // Create output directory if needed
        std::fs::create_dir_all(output_dir)?;

        // Build demucs command
        let mut cmd = Command::new("python");
        cmd.arg(&self.demucs_script_path)
            .arg("separate")
            .arg(input_path)
            .arg("--output")
            .arg(output_dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        // Run demucs
        let mut child = cmd.spawn()
            .map_err(|e| StemSeparationError::IoError(e.to_string()))?;

        // Monitor for cancellation
        let cancel_flag = Arc::clone(&self.cancel_flag);
        
        // Wait for completion (with cancellation check)
        let status = loop {
            match child.try_wait() {
                Ok(Some(status)) => break status,
                Ok(None) => {
                    // Still running, check for cancellation
                    if cancel_flag.load(Ordering::Relaxed) {
                        let _ = child.kill();
                        return Err(StemSeparationError::Cancelled);
                    }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }
                Err(e) => return Err(StemSeparationError::IoError(e.to_string())),
            }
        };

        if !status.success() {
            return Err(StemSeparationError::SeparationFailed);
        }

        // Collect results
        let mut result = StemSeparationResult::new();
        result.success = true;

        // Find stem files in output directory
        let input_stem = input_path.file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("output");

        for stem_type in StemType::all() {
            let stem_filename = format!("{}_{}.wav", input_stem, stem_type.file_suffix());
            let stem_path = output_dir.join(&stem_filename);
            
            if stem_path.exists() {
                result.set_path(stem_type, stem_path);
                
                // Report progress
                if let Some(ref callback) = self.progress_callback {
                    let progress = result.stem_count() as f32 / 4.0;
                    callback(progress, stem_type);
                }
            }
        }

        Ok(result)
    }

    /// Cancel ongoing separation
    pub fn cancel(&self) {
        self.cancel_flag.store(true, Ordering::Relaxed);
    }
}

impl Default for StemSeparator {
    fn default() -> Self {
        Self::new()
    }
}

/// Stem separation errors
#[derive(Debug, Clone, PartialEq)]
pub enum StemSeparationError {
    InputNotFound,
    DemucsNotAvailable,
    SeparationFailed,
    Cancelled,
    IoError(String),
}

impl std::fmt::Display for StemSeparationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StemSeparationError::InputNotFound => write!(f, "Input file not found"),
            StemSeparationError::DemucsNotAvailable => write!(f, "Demucs not available"),
            StemSeparationError::SeparationFailed => write!(f, "Stem separation failed"),
            StemSeparationError::Cancelled => write!(f, "Separation cancelled"),
            StemSeparationError::IoError(e) => write!(f, "IO error: {}", e),
        }
    }
}

impl std::error::Error for StemSeparationError {}

impl From<std::io::Error> for StemSeparationError {
    fn from(e: std::io::Error) -> Self {
        StemSeparationError::IoError(e.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_stem_type_file_suffixes() {
        assert_eq!(StemType::Vocals.file_suffix(), "vocals");
        assert_eq!(StemType::Drums.file_suffix(), "drums");
        assert_eq!(StemType::Bass.file_suffix(), "bass");
        assert_eq!(StemType::Other.file_suffix(), "other");
    }

    #[test]
    fn test_stem_type_all() {
        let all = StemType::all();
        assert_eq!(all.len(), 4);
        assert!(all.contains(&StemType::Vocals));
        assert!(all.contains(&StemType::Drums));
        assert!(all.contains(&StemType::Bass));
        assert!(all.contains(&StemType::Other));
    }

    #[test]
    fn test_separation_result_creation() {
        let result = StemSeparationResult::new();
        assert!(!result.success);
        assert!(result.vocals_path.is_none());
        assert!(result.drums_path.is_none());
        assert!(result.bass_path.is_none());
        assert!(result.other_path.is_none());
        assert!(result.error_message.is_none());
    }

    #[test]
    fn test_separation_result_set_and_get() {
        let mut result = StemSeparationResult::new();
        
        let vocals_path = PathBuf::from("/tmp/vocals.wav");
        result.set_path(StemType::Vocals, vocals_path.clone());
        
        assert_eq!(result.get_path(StemType::Vocals), Some(&vocals_path));
        assert!(result.get_path(StemType::Drums).is_none());
    }

    #[test]
    fn test_separation_result_stem_count() {
        let mut result = StemSeparationResult::new();
        assert_eq!(result.stem_count(), 0);
        
        result.set_path(StemType::Vocals, PathBuf::from("/tmp/vocals.wav"));
        assert_eq!(result.stem_count(), 1);
        
        result.set_path(StemType::Drums, PathBuf::from("/tmp/drums.wav"));
        result.set_path(StemType::Bass, PathBuf::from("/tmp/bass.wav"));
        assert_eq!(result.stem_count(), 3);
    }

    #[test]
    fn test_stem_separator_creation() {
        let separator = StemSeparator::new();
        assert!(!separator.is_available()); // demucs script doesn't exist in test env
        assert!(!separator.cancel_flag.load(Ordering::Relaxed));
    }

    #[test]
    fn test_stem_separator_with_custom_path() {
        let separator = StemSeparator::new()
            .with_script_path("/custom/path/demucs.py");
        
        assert!(!separator.is_available());
    }

    #[test]
    fn test_stem_separator_cancel() {
        let separator = StemSeparator::new();
        assert!(!separator.cancel_flag.load(Ordering::Relaxed));
        
        separator.cancel();
        assert!(separator.cancel_flag.load(Ordering::Relaxed));
    }

    #[test]
    fn test_separation_error_display() {
        let err = StemSeparationError::InputNotFound;
        assert!(format!("{}", err).contains("not found"));
        
        let err = StemSeparationError::DemucsNotAvailable;
        assert!(format!("{}", err).contains("not available"));
        
        let err = StemSeparationError::Cancelled;
        assert!(format!("{}", err).contains("cancelled"));
    }

    #[test]
    fn test_separation_input_not_found() {
        let separator = StemSeparator::new();
        let result = separator.separate("/nonexistent/file.wav", "/tmp/output");
        
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), StemSeparationError::InputNotFound);
    }

    #[test]
    fn test_progress_callback() {
        let mut separator = StemSeparator::new();
        
        let progress_values = Arc::new(std::sync::Mutex::new(Vec::new()));
        let progress_clone = Arc::clone(&progress_values);
        
        separator.set_progress_callback(Box::new(move |progress, stem_type| {
            progress_clone.lock().unwrap().push((progress, stem_type));
        }));
        
        // Callback is set (can't test invocation without demucs)
        assert!(separator.progress_callback.is_some());
    }
}
