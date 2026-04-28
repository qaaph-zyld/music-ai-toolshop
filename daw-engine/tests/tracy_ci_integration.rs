//! Tracy CI Integration Tests
//!
//! Tests for CI/CD pipeline to verify Tracy integration compiles
//! and works correctly in automated builds.

use daw_engine::{ProfilerConfig, init_from_env, profile_scope, plot_value, frame_mark};

/// Test that Tracy feature compiles correctly
#[test]
fn test_tracy_feature_compiles() {
    // This test verifies the code compiles with tracy feature enabled
    // Run with: cargo test --test tracy_ci_integration --features tracy

    profile_scope!("ci_test_scope");
    plot_value!("ci_test_metric", 42.0);
    frame_mark!();

    // If we reach here, compilation succeeded
    assert!(true);
}

/// Test profiler config from environment
#[test]
fn test_profiler_config_from_env() {
    // Save original value
    let original = std::env::var("OPENDAW_TRACY").ok();

    // Test with env var set
    std::env::set_var("OPENDAW_TRACY", "1");
    let config = ProfilerConfig::from_env();
    assert!(config.is_enabled());

    // Test with env var unset
    std::env::remove_var("OPENDAW_TRACY");
    let config = ProfilerConfig::from_env();
    assert!(!config.is_enabled());

    // Restore original
    match original {
        Some(v) => std::env::set_var("OPENDAW_TRACY", v),
        None => std::env::remove_var("OPENDAW_TRACY"),
    }
}

/// Test various env var formats
#[test]
fn test_profiler_config_env_formats() {
    let original = std::env::var("OPENDAW_TRACY").ok();

    // Test "true"
    std::env::set_var("OPENDAW_TRACY", "true");
    let config = ProfilerConfig::from_env();
    assert!(config.is_enabled());

    // Test "yes"
    std::env::set_var("OPENDAW_TRACY", "yes");
    let config = ProfilerConfig::from_env();
    assert!(config.is_enabled());

    // Test "0" (disabled)
    std::env::set_var("OPENDAW_TRACY", "0");
    let config = ProfilerConfig::from_env();
    assert!(!config.is_enabled());

    // Test "false" (disabled)
    std::env::set_var("OPENDAW_TRACY", "false");
    let config = ProfilerConfig::from_env();
    assert!(!config.is_enabled());

    // Restore original
    match original {
        Some(v) => std::env::set_var("OPENDAW_TRACY", v),
        None => std::env::remove_var("OPENDAW_TRACY"),
    }
}

/// Test auto-start configuration
#[test]
fn test_profiler_config_auto_start() {
    let original_tracy = std::env::var("OPENDAW_TRACY").ok();
    let original_auto = std::env::var("OPENDAW_TRACY_AUTO_START").ok();

    // Set both vars
    std::env::set_var("OPENDAW_TRACY", "1");

    // Test auto-start enabled (default)
    std::env::remove_var("OPENDAW_TRACY_AUTO_START");
    let config = ProfilerConfig::from_env();
    assert!(config.auto_start());

    // Test auto-start disabled
    std::env::set_var("OPENDAW_TRACY_AUTO_START", "0");
    let config = ProfilerConfig::from_env();
    assert!(!config.auto_start());

    // Test auto-start explicitly enabled
    std::env::set_var("OPENDAW_TRACY_AUTO_START", "1");
    let config = ProfilerConfig::from_env();
    assert!(config.auto_start());

    // Restore originals
    match original_tracy {
        Some(v) => std::env::set_var("OPENDAW_TRACY", v),
        None => std::env::remove_var("OPENDAW_TRACY"),
    }
    match original_auto {
        Some(v) => std::env::set_var("OPENDAW_TRACY_AUTO_START", v),
        None => std::env::remove_var("OPENDAW_TRACY_AUTO_START"),
    }
}

/// Test init_from_env with various configurations
#[test]
fn test_init_from_env() {
    let original = std::env::var("OPENDAW_TRACY").ok();

    // When enabled, should return true
    std::env::set_var("OPENDAW_TRACY", "1");
    let should_start = init_from_env();
    assert!(should_start);
    assert!(ProfilerConfig::is_globally_enabled());

    // When disabled, should return false
    std::env::remove_var("OPENDAW_TRACY");
    let should_start = init_from_env();
    assert!(!should_start);
    assert!(!ProfilerConfig::is_globally_enabled());

    // Restore original
    match original {
        Some(v) => std::env::set_var("OPENDAW_TRACY", v),
        None => std::env::remove_var("OPENDAW_TRACY"),
    }
}

/// Test that profiling doesn't break without tracy feature
#[test]
fn test_profiling_no_panic_without_feature() {
    // These macros should work regardless of feature state
    profile_scope!("test_no_tracy");
    plot_value!("test_metric", 100.0);
    frame_mark!();

    // Nested scopes
    profile_scope!("outer");
    {
        profile_scope!("inner1");
    }
    {
        profile_scope!("inner2");
    }

    assert!(true);
}

/// Combined CI verification test
#[test]
fn test_tracy_ci_full_verification() {
    // 1. Config works
    let config = ProfilerConfig::new(true, true);
    assert!(config.is_enabled());
    assert!(config.auto_start());

    // 2. Macros don't panic
    profile_scope!("ci_verification");
    plot_value!("ci_value", 999.0);
    frame_mark!();

    // 3. Runtime toggle works
    let mut config = ProfilerConfig::new(false, true);
    config.enable();
    assert!(config.is_enabled());

    config.disable();
    assert!(!config.is_enabled());

    // All CI checks passed
    assert!(true);
}
