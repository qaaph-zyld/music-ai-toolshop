//! Settings Management
//!
//! Persistent settings storage for first-launch detection and user preferences.

use std::fs;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};

/// Application settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    /// Whether onboarding has been completed
    pub onboarding_complete: bool,
    /// Whether to show onboarding on startup
    pub show_onboarding_on_startup: bool,
    /// Last project path
    pub last_project_path: Option<String>,
    /// Default audio device
    pub default_audio_device: Option<String>,
    /// Default sample rate
    pub default_sample_rate: u32,
    /// Default buffer size
    pub default_buffer_size: u32,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            onboarding_complete: false,
            show_onboarding_on_startup: true,
            last_project_path: None,
            default_audio_device: None,
            default_sample_rate: 48000,
            default_buffer_size: 512,
        }
    }
}

impl AppSettings {
    /// Load settings from file
    pub fn load() -> Result<Self, SettingsError> {
        let path = Self::settings_path()?;
        
        if !path.exists() {
            return Ok(Self::default());
        }
        
        let content = fs::read_to_string(&path)
            .map_err(|e| SettingsError::IoError(e.to_string()))?;
        
        let settings: AppSettings = serde_json::from_str(&content)
            .map_err(|e| SettingsError::ParseError(e.to_string()))?;
        
        Ok(settings)
    }
    
    /// Save settings to file
    pub fn save(&self) -> Result<(), SettingsError> {
        let path = Self::settings_path()?;
        
        // Ensure parent directory exists
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| SettingsError::IoError(e.to_string()))?;
        }
        
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| SettingsError::ParseError(e.to_string()))?;
        
        fs::write(&path, content)
            .map_err(|e| SettingsError::IoError(e.to_string()))?;
        
        Ok(())
    }
    
    /// Check if this is the first launch (no settings file exists)
    pub fn is_first_launch() -> bool {
        !Self::settings_path().map(|p| p.exists()).unwrap_or(false)
    }
    
    /// Mark onboarding as complete
    pub fn mark_onboarding_complete(&mut self) {
        self.onboarding_complete = true;
    }
    
    /// Check if onboarding should be shown
    pub fn should_show_onboarding(&self) -> bool {
        self.show_onboarding_on_startup && !self.onboarding_complete
    }
    
    /// Get settings file path
    fn settings_path() -> Result<PathBuf, SettingsError> {
        let config_dir = dirs::config_dir()
            .ok_or_else(|| SettingsError::IoError("Could not find config directory".to_string()))?;
        
        Ok(config_dir.join("OpenDAW").join("settings.json"))
    }
}

/// Settings error types
#[derive(Debug, Clone)]
pub enum SettingsError {
    IoError(String),
    ParseError(String),
}

impl std::fmt::Display for SettingsError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SettingsError::IoError(msg) => write!(f, "IO Error: {}", msg),
            SettingsError::ParseError(msg) => write!(f, "Parse Error: {}", msg),
        }
    }
}

impl std::error::Error for SettingsError {}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;
    
    #[test]
    fn test_default_settings() {
        let settings = AppSettings::default();
        assert!(!settings.onboarding_complete);
        assert!(settings.show_onboarding_on_startup);
        assert_eq!(settings.default_sample_rate, 48000);
        assert_eq!(settings.default_buffer_size, 512);
    }
    
    #[test]
    fn test_onboarding_logic() {
        let mut settings = AppSettings::default();
        
        // Initially should show onboarding
        assert!(settings.should_show_onboarding());
        
        // Mark as complete
        settings.mark_onboarding_complete();
        assert!(settings.onboarding_complete);
        assert!(!settings.should_show_onboarding());
        
        // Disable showing on startup
        settings.show_onboarding_on_startup = false;
        assert!(!settings.should_show_onboarding());
    }
    
    #[test]
    fn test_save_and_load() {
        let temp_dir = TempDir::new().unwrap();
        let settings_path = temp_dir.path().join("test_settings.json");
        
        // Create and save settings
        let mut settings = AppSettings::default();
        settings.onboarding_complete = true;
        settings.last_project_path = Some("/path/to/project".to_string());
        
        let json = serde_json::to_string_pretty(&settings).unwrap();
        std::fs::write(&settings_path, json).unwrap();
        
        // Load settings
        let content = std::fs::read_to_string(&settings_path).unwrap();
        let loaded: AppSettings = serde_json::from_str(&content).unwrap();
        
        assert!(loaded.onboarding_complete);
        assert_eq!(loaded.last_project_path, Some("/path/to/project".to_string()));
    }
    
    #[test]
    fn test_serialization() {
        let settings = AppSettings {
            onboarding_complete: true,
            show_onboarding_on_startup: false,
            last_project_path: Some("test".to_string()),
            default_audio_device: Some("device".to_string()),
            default_sample_rate: 44100,
            default_buffer_size: 256,
        };
        
        let json = serde_json::to_string(&settings).unwrap();
        assert!(json.contains("onboarding_complete"));
        assert!(json.contains("true"));
        
        let deserialized: AppSettings = serde_json::from_str(&json).unwrap();
        assert!(deserialized.onboarding_complete);
        assert_eq!(deserialized.default_sample_rate, 44100);
    }
}
