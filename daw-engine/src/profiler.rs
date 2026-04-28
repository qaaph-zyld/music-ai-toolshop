//! Performance profiler with Tracy integration
//!
//! Provides instrumentation for the audio engine to track performance
//! and identify bottlenecks in real-time processing.
//!
//! ## Usage
//!
//! ```rust
//! use daw_engine::profiler::{profile_scope, plot_value, frame_mark};
//!
//! fn process_audio() {
//!     profile_scope!("audio_process");
//!     
//!     // Do work...
//!     
//!     plot_value!("cpu_usage", 45.0);
//!     frame_mark!();
//! }
//! ```

// Re-export Tracy types when feature enabled
#[cfg(feature = "tracy")]
pub use tracy_client::Span as TracySpan;

/// Frame mark macro - marks the end of a frame in Tracy
/// Uses Tracy when the 'tracy' feature is enabled, otherwise no-op
#[macro_export]
macro_rules! frame_mark {
    () => {
        #[cfg(feature = "tracy")]
        {
            tracy_client::frame_mark();
        }
        #[cfg(not(feature = "tracy"))]
        {
            // No-op when Tracy disabled
        }
    };
}

/// Plot value macro - plots a named value in Tracy
/// Uses Tracy when the 'tracy' feature is enabled, otherwise no-op
#[macro_export]
macro_rules! plot_value {
    ($name:expr, $value:expr) => {
        #[cfg(feature = "tracy")]
        {
            tracy_client::plot!($name, $value);
        }
        #[cfg(not(feature = "tracy"))]
        {
            // No-op when Tracy disabled
            let _ = ($name, $value);
        }
    };
}

/// Profile scope macro - creates a named profiling zone
/// Uses Tracy when the 'tracy' feature is enabled, otherwise no-op
#[macro_export]
macro_rules! profile_scope {
    ($name:expr) => {
        #[cfg(feature = "tracy")]
        {
            let _tracy_zone = tracy_client::span!($name, 0);
        }
        #[cfg(not(feature = "tracy"))]
        {
            // No-op when Tracy disabled
        }
    };
    ($name:expr, $callstack:expr) => {
        #[cfg(feature = "tracy")]
        {
            let _tracy_zone = tracy_client::span!($name, $callstack);
        }
        #[cfg(not(feature = "tracy"))]
        {
            // No-op when Tracy disabled
        }
    };
}

/// Performance profiler singleton for manual zone management
pub struct Profiler {
    #[cfg(feature = "tracy")]
    _private: (),
}

impl Profiler {
    /// Create a new profiler instance (no-op with Tracy's global client)
    pub fn new() -> Self {
        Self {
            #[cfg(feature = "tracy")]
            _private: (),
        }
    }

    /// Mark the end of a frame (call once per audio callback)
    #[inline]
    pub fn frame_mark(&self) {
        #[cfg(feature = "tracy")]
        tracy_client::frame_mark();
    }

    /// Plot a named value for visualization
    /// Note: This is a no-op wrapper. Use the plot_value! macro directly for actual plotting.
    #[inline]
    pub fn plot(&self, _name: &'static str, _value: f64) {
        // The plot_value! macro should be used directly since it needs a running Client
        // This method exists for API compatibility
        let _ = (_name, _value);
    }
}

impl Default for Profiler {
    fn default() -> Self {
        Self::new()
    }
}

/// CPU usage tracker for audio callback profiling
pub struct CpuUsageTracker {
    sample_rate: u32,
    channels: u16,
    last_cpu_usage: f32,
}

impl CpuUsageTracker {
    /// Create a new CPU usage tracker
    pub fn new(sample_rate: u32, channels: u16) -> Self {
        Self {
            sample_rate,
            channels,
            last_cpu_usage: 0.0,
        }
    }

    /// Calculate CPU usage percentage from processing time
    pub fn calculate(&mut self, processing_time_ns: u64, sample_count: usize) -> f32 {
        let buffer_duration_us = (sample_count as f64 / self.channels as f64) 
            * 1_000_000.0 / self.sample_rate as f64;
        let processing_time_us = processing_time_ns as f64 / 1000.0;
        
        self.last_cpu_usage = (processing_time_us / buffer_duration_us * 100.0) as f32;
        
        // Note: Direct plotting here would require a running Client
        // The plot_value! macro handles this automatically when used in the calling code
        
        self.last_cpu_usage
    }

    /// Get last calculated CPU usage
    pub fn last_cpu_usage(&self) -> f32 {
        self.last_cpu_usage
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_profiler_creation() {
        let _profiler = Profiler::new();
    }

    #[test]
    fn test_profiler_default() {
        let _profiler = Profiler::default();
    }

    #[test]
    fn test_frame_mark() {
        let profiler = Profiler::new();
        profiler.frame_mark();
    }

    #[test]
    fn test_plot_value() {
        let profiler = Profiler::new();
        profiler.plot("test_metric", 42.0);
    }

    #[test]
    fn test_cpu_usage_tracker() {
        let mut tracker = CpuUsageTracker::new(48000, 2);
        
        // Simulate 1ms processing time for 128 samples at 48kHz stereo
        // Buffer time = 128/2 / 48000 * 1e6 = 1333 us
        // Processing time = 1000 us
        // CPU = 1000/1333 * 100 = 75%
        let cpu = tracker.calculate(1_000_000, 256); // 128 frames * 2 channels
        
        assert!(cpu > 0.0);
        assert!(cpu <= 100.0);
        assert_eq!(tracker.last_cpu_usage(), cpu);
    }

    #[test]
    fn test_cpu_usage_zero_load() {
        let mut tracker = CpuUsageTracker::new(48000, 2);
        let cpu = tracker.calculate(0, 256);
        assert_eq!(cpu, 0.0);
    }
}
