//! Performance profiler with Tracy integration
//!
//! Provides instrumentation for the audio engine to track performance
//! and identify bottlenecks in real-time processing.

#[cfg(feature = "tracy")]
use tracy_client::{Client, Span, frame_mark};

/// Performance profiler for instrumentation
pub struct Profiler {
    #[cfg(feature = "tracy")]
    client: Client,
}

/// A profiling zone that automatically ends when dropped
#[cfg(feature = "tracy")]
pub struct Zone(Span);

#[cfg(not(feature = "tracy"))]
pub struct Zone;

impl Profiler {
    /// Create a new profiler instance
    pub fn new() -> Self {
        Self {
            #[cfg(feature = "tracy")]
            client: Client::start(),
        }
    }

    /// Mark the end of a frame (call once per UI/audio frame)
    pub fn frame_mark(&self) {
        #[cfg(feature = "tracy")]
        frame_mark();
    }

    /// Begin a named profiling zone
    pub fn zone_begin(&self, _name: &'static str) -> Zone {
        #[cfg(feature = "tracy")]
        return Zone(self.client.span(0, name, "", 0));
        
        #[cfg(not(feature = "tracy"))]
        Zone
    }
}

impl Default for Profiler {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(feature = "tracy")]
impl Drop for Zone {
    fn drop(&mut self) {
        // Span automatically ends when dropped
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_profiler_creation() {
        let profiler = Profiler::new();
        // Just verify it doesn't panic
    }

    #[test]
    fn test_profiler_default() {
        let profiler = Profiler::default();
        // Just verify it doesn't panic
    }

    #[test]
    fn test_frame_mark() {
        let profiler = Profiler::new();
        profiler.frame_mark();
        // Just verify it doesn't panic
    }

    #[test]
    fn test_zone_begin() {
        let profiler = Profiler::new();
        let _zone = profiler.zone_begin("test_zone");
        // Zone ends when dropped
    }

    #[test]
    fn test_nested_zones() {
        let profiler = Profiler::new();
        let _outer = profiler.zone_begin("outer");
        let _inner = profiler.zone_begin("inner");
        // Both zones end when dropped
    }
}
