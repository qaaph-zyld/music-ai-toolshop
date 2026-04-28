//! Profiler configuration for runtime profiling control
//!
//! Provides environment variable based configuration and runtime
//! toggle for Tracy profiler.

use std::sync::atomic::{AtomicBool, Ordering};

/// Global profiler enable flag
static PROFILER_ENABLED: AtomicBool = AtomicBool::new(false);

/// Profiler configuration
#[derive(Debug, Clone)]
pub struct ProfilerConfig {
    enabled: bool,
    auto_start: bool,
}

impl ProfilerConfig {
    /// Create new config from environment variables
    ///
    /// Environment variables:
    /// - `OPENDAW_TRACY=1` - Enable Tracy profiler
    /// - `OPENDAW_TRACY_AUTO_START=0` - Disable auto-start (default: 1)
    pub fn from_env() -> Self {
        let enabled = std::env::var("OPENDAW_TRACY")
            .map(|v| v == "1" || v.eq_ignore_ascii_case("true") || v.eq_ignore_ascii_case("yes"))
            .unwrap_or(false);

        let auto_start = std::env::var("OPENDAW_TRACY_AUTO_START")
            .map(|v| v != "0" && !v.eq_ignore_ascii_case("false") && !v.eq_ignore_ascii_case("no"))
            .unwrap_or(true);

        Self {
            enabled,
            auto_start,
        }
    }

    /// Create with explicit settings
    pub fn new(enabled: bool, auto_start: bool) -> Self {
        Self {
            enabled,
            auto_start,
        }
    }

    /// Check if profiler is enabled
    pub fn is_enabled(&self) -> bool {
        self.enabled
    }

    /// Check if auto-start is enabled
    pub fn auto_start(&self) -> bool {
        self.auto_start
    }

    /// Enable profiler at runtime
    pub fn enable(&mut self) {
        self.enabled = true;
        PROFILER_ENABLED.store(true, Ordering::SeqCst);
    }

    /// Disable profiler at runtime
    pub fn disable(&mut self) {
        self.enabled = false;
        PROFILER_ENABLED.store(false, Ordering::SeqCst);
    }

    /// Get current global enable state
    pub fn is_globally_enabled() -> bool {
        PROFILER_ENABLED.load(Ordering::SeqCst)
    }
}

impl Default for ProfilerConfig {
    fn default() -> Self {
        Self::from_env()
    }
}

/// Initialize profiler from environment
///
/// Call this early in main() to configure Tracy based on env vars.
/// Returns true if Tracy should be started.
pub fn init_from_env() -> bool {
    let config = ProfilerConfig::from_env();
    PROFILER_ENABLED.store(config.enabled, Ordering::SeqCst);
    config.enabled && config.auto_start
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_profiler_config_default() {
        let config = ProfilerConfig::default();
        // Default should be disabled (unless env var set)
        assert!(!config.is_enabled() || std::env::var("OPENDAW_TRACY").is_ok());
    }

    #[test]
    fn test_profiler_config_explicit() {
        let config = ProfilerConfig::new(true, true);
        assert!(config.is_enabled());
        assert!(config.auto_start());

        let config = ProfilerConfig::new(false, false);
        assert!(!config.is_enabled());
        assert!(!config.auto_start());
    }

    #[test]
    fn test_profiler_enable_disable() {
        let mut config = ProfilerConfig::new(false, true);
        assert!(!config.is_enabled());

        config.enable();
        assert!(config.is_enabled());
        assert!(ProfilerConfig::is_globally_enabled());

        config.disable();
        assert!(!config.is_enabled());
        assert!(!ProfilerConfig::is_globally_enabled());
    }
}
