//! E2E Integration Test: Onboarding Flow
//!
//! Tests the first-launch detection and settings persistence
//! for the onboarding system.

use daw_engine::settings::{AppSettings, SettingsError};

/// Test default settings values
#[test]
fn test_default_settings() {
    let settings = AppSettings::default();
    
    // Default: onboarding not complete, show on startup
    assert!(!settings.onboarding_complete);
    assert!(settings.show_onboarding_on_startup);
    
    // Default audio settings
    assert_eq!(settings.default_sample_rate, 48000);
    assert_eq!(settings.default_buffer_size, 512);
    
    // No last project initially
    assert!(settings.last_project_path.is_none());
}

/// Test onboarding logic
#[test]
fn test_onboarding_should_show() {
    let mut settings = AppSettings::default();
    
    // Initially should show onboarding
    assert!(settings.should_show_onboarding());
    
    // Mark as complete
    settings.mark_onboarding_complete();
    assert!(settings.onboarding_complete);
    
    // Should not show anymore
    assert!(!settings.should_show_onboarding());
    
    // Even if we reset show_onboarding_on_startup to true
    settings.show_onboarding_on_startup = true;
    assert!(!settings.should_show_onboarding());
}

/// Test JSON serialization
#[test]
fn test_settings_json_serialization() {
    let mut settings = AppSettings::default();
    settings.onboarding_complete = true;
    settings.last_project_path = Some("/path/to/project.opendaw".to_string());
    settings.default_sample_rate = 44100;
    
    // Serialize to JSON
    let json = serde_json::to_string_pretty(&settings).unwrap();
    
    // Verify JSON contains expected fields
    assert!(json.contains("onboarding_complete"));
    assert!(json.contains("true")); // onboarding_complete = true
    assert!(json.contains("last_project_path"));
    assert!(json.contains("/path/to/project.opendaw"));
    assert!(json.contains("44100"));
    
    // Deserialize back
    let deserialized: AppSettings = serde_json::from_str(&json).unwrap();
    
    assert!(deserialized.onboarding_complete);
    assert_eq!(deserialized.last_project_path, Some("/path/to/project.opendaw".to_string()));
    assert_eq!(deserialized.default_sample_rate, 44100);
}

/// Test deserialization of partial JSON (missing fields)
#[test]
fn test_settings_partial_deserialization() {
    // JSON with only some fields
    let partial_json = r#"{
        "onboarding_complete": true,
        "default_sample_rate": 96000
    }"#;
    
    let settings: AppSettings = serde_json::from_str(partial_json).unwrap();
    
    // Specified fields
    assert!(settings.onboarding_complete);
    assert_eq!(settings.default_sample_rate, 96000);
    
    // Default values for missing fields
    assert!(settings.show_onboarding_on_startup); // default
    assert_eq!(settings.default_buffer_size, 512); // default
}

/// Test that default values work when deserializing empty object
#[test]
fn test_settings_empty_json() {
    let empty_json = r#"{}"#;
    
    let settings: AppSettings = serde_json::from_str(empty_json).unwrap();
    
    // All defaults should be applied
    assert!(!settings.onboarding_complete);
    assert!(settings.show_onboarding_on_startup);
    assert_eq!(settings.default_sample_rate, 48000);
}

/// Test invalid JSON handling
#[test]
fn test_settings_invalid_json() {
    let invalid_json = r#"{ invalid json }"#;
    
    let result: Result<AppSettings, _> = serde_json::from_str(invalid_json);
    assert!(result.is_err());
}
