//! wavesurfer - Waveform Visualization
//!
//! Interactive waveform display with zoom, region selection,
//! and playback cursor. Web-based visualization component.
//!
//! Repository: https://github.com/katspaugh/wavesurfer.js

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint};

/// WaveSurfer waveform viewer
pub struct WaveSurfer {
    handle: *mut c_void,
    container_id: String,
    width: u32,
    height: u32,
}

/// Waveform region for selection
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct WaveRegion {
    pub start: f64,      // Start time in seconds
    pub end: f64,        // End time in seconds
    pub color: u32,      // RGB color
    pub selected: bool,
}

impl Default for WaveRegion {
    fn default() -> Self {
        WaveRegion {
            start: 0.0,
            end: 1.0,
            color: 0x3366CC,
            selected: false,
        }
    }
}

/// Zoom configuration
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ZoomConfig {
    pub min_pixels_per_second: f32,
    pub max_pixels_per_second: f32,
    pub current_zoom: f32,
    pub auto_zoom: bool,
}

impl Default for ZoomConfig {
    fn default() -> Self {
        ZoomConfig {
            min_pixels_per_second: 10.0,
            max_pixels_per_second: 1000.0,
            current_zoom: 50.0,
            auto_zoom: false,
        }
    }
}

/// Waveform rendering options
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct WaveformOptions {
    pub wave_color: u32,      // RGB color for waveform
    pub progress_color: u32,  // RGB color for played portion
    pub cursor_color: u32,    // RGB color for cursor
    pub bar_width: f32,
    pub bar_gap: f32,
    pub bar_radius: f32,
    pub responsive: bool,
}

impl Default for WaveformOptions {
    fn default() -> Self {
        WaveformOptions {
            wave_color: 0x3366CC,
            progress_color: 0x9944CC,
            cursor_color: 0xFF0000,
            bar_width: 2.0,
            bar_gap: 1.0,
            bar_radius: 2.0,
            responsive: true,
        }
    }
}

/// Playback cursor state
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CursorState {
    pub position: f64,   // Current position in seconds
    pub visible: bool,
    pub follows_playback: bool,
}

impl Default for CursorState {
    fn default() -> Self {
        CursorState {
            position: 0.0,
            visible: true,
            follows_playback: true,
        }
    }
}

/// Audio buffer reference
#[derive(Debug, Clone)]
pub struct AudioBuffer {
    pub sample_rate: u32,
    pub channels: u16,
    pub duration: f64,
    pub data: Vec<f32>,
}

impl Default for AudioBuffer {
    fn default() -> Self {
        AudioBuffer {
            sample_rate: 44100,
            channels: 2,
            duration: 0.0,
            data: Vec::new(),
        }
    }
}

/// WaveSurfer availability status
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum WaveSurferStatus {
    Available,
    NotAvailable,
    Error(&'static str),
}

/// FFI interface to wavesurfer.js library
#[link(name = "daw_engine_ffi")]
extern "C" {
    fn wavesurfer_create(container_id: *const c_char, width: c_int, height: c_int) -> *mut c_void;
    fn wavesurfer_destroy(handle: *mut c_void);
    fn wavesurfer_available() -> c_int;
    fn wavesurfer_load_buffer(
        handle: *mut c_void,
        buffer: *const c_float,
        length: c_int,
        channels: c_int,
        sample_rate: c_int,
    ) -> c_int;
    fn wavesurfer_set_zoom(handle: *mut c_void, pixels_per_second: c_float) -> c_int;
    fn wavesurfer_get_zoom(handle: *mut c_void) -> c_float;
    fn wavesurfer_add_region(
        handle: *mut c_void,
        start: c_double,
        end: c_double,
        color: c_uint,
    ) -> c_int;
    fn wavesurfer_remove_region(handle: *mut c_void, region_id: c_int) -> c_int;
    fn wavesurfer_clear_regions(handle: *mut c_void) -> c_int;
    fn wavesurfer_set_cursor(handle: *mut c_void, position: c_double) -> c_int;
    fn wavesurfer_set_cursor_visible(handle: *mut c_void, visible: c_int) -> c_int;
    fn wavesurfer_set_wave_color(handle: *mut c_void, color: c_uint) -> c_int;
    fn wavesurfer_set_progress_color(handle: *mut c_void, color: c_uint) -> c_int;
    fn wavesurfer_get_duration(handle: *mut c_void) -> c_double;
    fn wavesurfer_clear(handle: *mut c_void) -> c_int;
    fn wavesurfer_resize(handle: *mut c_void, width: c_int, height: c_int) -> c_int;
    fn wavesurfer_zoom_in(handle: *mut c_void, factor: c_float) -> c_int;
    fn wavesurfer_zoom_out(handle: *mut c_void, factor: c_float) -> c_int;
}

impl WaveSurfer {
    /// Create new WaveSurfer instance
    pub fn new(container_id: &str, width: u32, height: u32) -> Option<Self> {
        unsafe {
            let c_id = CString::new(container_id).ok()?;
            let handle = wavesurfer_create(c_id.as_ptr(), width as c_int, height as c_int);
            if handle.is_null() {
                None
            } else {
                Some(WaveSurfer {
                    handle,
                    container_id: container_id.to_string(),
                    width,
                    height,
                })
            }
        }
    }

    /// Check if wavesurfer library is available
    pub fn is_available() -> bool {
        unsafe { wavesurfer_available() != 0 }
    }

    /// Get availability status
    pub fn availability_status() -> WaveSurferStatus {
        if Self::is_available() {
            WaveSurferStatus::Available
        } else {
            WaveSurferStatus::NotAvailable
        }
    }

    /// Load audio buffer
    pub fn load_buffer(&mut self, buffer: &AudioBuffer) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_load_buffer(
                self.handle,
                buffer.data.as_ptr(),
                buffer.data.len() as c_int,
                buffer.channels as c_int,
                buffer.sample_rate as c_int,
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to load buffer")
            }
        }
    }

    /// Set zoom level (pixels per second)
    pub fn set_zoom(&mut self, pixels_per_second: f32) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_set_zoom(self.handle, pixels_per_second);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set zoom")
            }
        }
    }

    /// Get current zoom level
    pub fn get_zoom(&self) -> f32 {
        unsafe { wavesurfer_get_zoom(self.handle) }
    }

    /// Add a region
    pub fn add_region(&mut self, region: WaveRegion) -> Result<usize, &'static str> {
        unsafe {
            let result = wavesurfer_add_region(
                self.handle,
                region.start,
                region.end,
                region.color,
            );
            if result >= 0 {
                Ok(result as usize)
            } else {
                Err("Failed to add region")
            }
        }
    }

    /// Remove a region
    pub fn remove_region(&mut self, region_id: usize) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_remove_region(self.handle, region_id as c_int);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to remove region")
            }
        }
    }

    /// Clear all regions
    pub fn clear_regions(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_clear_regions(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear regions")
            }
        }
    }

    /// Set cursor position
    pub fn set_cursor(&mut self, position: f64) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_set_cursor(self.handle, position);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set cursor")
            }
        }
    }

    /// Set cursor visibility
    pub fn set_cursor_visible(&mut self, visible: bool) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_set_cursor_visible(self.handle, if visible { 1 } else { 0 });
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set cursor visibility")
            }
        }
    }

    /// Set waveform color
    pub fn set_wave_color(&mut self, color: u32) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_set_wave_color(self.handle, color);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set wave color")
            }
        }
    }

    /// Set progress color
    pub fn set_progress_color(&mut self, color: u32) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_set_progress_color(self.handle, color);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set progress color")
            }
        }
    }

    /// Get audio duration
    pub fn get_duration(&self) -> f64 {
        unsafe { wavesurfer_get_duration(self.handle) }
    }

    /// Clear waveform
    pub fn clear(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_clear(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear waveform")
            }
        }
    }

    /// Resize container
    pub fn resize(&mut self, width: u32, height: u32) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_resize(self.handle, width as c_int, height as c_int);
            if result == 0 {
                self.width = width;
                self.height = height;
                Ok(())
            } else {
                Err("Failed to resize")
            }
        }
    }

    /// Zoom in
    pub fn zoom_in(&mut self, factor: f32) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_zoom_in(self.handle, factor);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to zoom in")
            }
        }
    }

    /// Zoom out
    pub fn zoom_out(&mut self, factor: f32) -> Result<(), &'static str> {
        unsafe {
            let result = wavesurfer_zoom_out(self.handle, factor);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to zoom out")
            }
        }
    }
}

impl Drop for WaveSurfer {
    fn drop(&mut self) {
        unsafe {
            wavesurfer_destroy(self.handle);
        }
    }
}

unsafe impl Send for WaveSurfer {}
unsafe impl Sync for WaveSurfer {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wavesurfer_availability() {
        let available = WaveSurfer::is_available();
        assert!(!available, "WaveSurfer should report not available (stub)");
    }

    #[test]
    fn test_wavesurfer_status() {
        let status = WaveSurfer::availability_status();
        match status {
            WaveSurferStatus::NotAvailable => (),
            WaveSurferStatus::Available => panic!("Should not be available with stub"),
            WaveSurferStatus::Error(_) => (),
        }
    }

    #[test]
    fn test_wave_region_default() {
        let region = WaveRegion::default();
        assert_eq!(region.start, 0.0);
        assert_eq!(region.end, 1.0);
        assert_eq!(region.color, 0x3366CC);
        assert!(!region.selected);
    }

    #[test]
    fn test_wave_region_custom() {
        let region = WaveRegion {
            start: 10.5,
            end: 20.0,
            color: 0xFF5733,
            selected: true,
        };
        assert_eq!(region.start, 10.5);
        assert_eq!(region.end, 20.0);
        assert_eq!(region.color, 0xFF5733);
        assert!(region.selected);
    }

    #[test]
    fn test_zoom_config_default() {
        let config = ZoomConfig::default();
        assert_eq!(config.min_pixels_per_second, 10.0);
        assert_eq!(config.max_pixels_per_second, 1000.0);
        assert_eq!(config.current_zoom, 50.0);
        assert!(!config.auto_zoom);
    }

    #[test]
    fn test_zoom_config_custom() {
        let config = ZoomConfig {
            min_pixels_per_second: 5.0,
            max_pixels_per_second: 500.0,
            current_zoom: 100.0,
            auto_zoom: true,
        };
        assert_eq!(config.min_pixels_per_second, 5.0);
        assert_eq!(config.max_pixels_per_second, 500.0);
        assert_eq!(config.current_zoom, 100.0);
        assert!(config.auto_zoom);
    }

    #[test]
    fn test_waveform_options_default() {
        let options = WaveformOptions::default();
        assert_eq!(options.wave_color, 0x3366CC);
        assert_eq!(options.progress_color, 0x9944CC);
        assert_eq!(options.cursor_color, 0xFF0000);
        assert_eq!(options.bar_width, 2.0);
        assert_eq!(options.bar_gap, 1.0);
        assert_eq!(options.bar_radius, 2.0);
        assert!(options.responsive);
    }

    #[test]
    fn test_waveform_options_custom() {
        let options = WaveformOptions {
            wave_color: 0x00FF00,
            progress_color: 0x0000FF,
            cursor_color: 0xFFFFFF,
            bar_width: 4.0,
            bar_gap: 2.0,
            bar_radius: 4.0,
            responsive: false,
        };
        assert_eq!(options.wave_color, 0x00FF00);
        assert_eq!(options.progress_color, 0x0000FF);
        assert_eq!(options.cursor_color, 0xFFFFFF);
        assert_eq!(options.bar_width, 4.0);
        assert_eq!(options.bar_gap, 2.0);
        assert_eq!(options.bar_radius, 4.0);
        assert!(!options.responsive);
    }

    #[test]
    fn test_cursor_state_default() {
        let state = CursorState::default();
        assert_eq!(state.position, 0.0);
        assert!(state.visible);
        assert!(state.follows_playback);
    }

    #[test]
    fn test_cursor_state_custom() {
        let state = CursorState {
            position: 45.5,
            visible: false,
            follows_playback: false,
        };
        assert_eq!(state.position, 45.5);
        assert!(!state.visible);
        assert!(!state.follows_playback);
    }

    #[test]
    fn test_audio_buffer_default() {
        let buffer = AudioBuffer::default();
        assert_eq!(buffer.sample_rate, 44100);
        assert_eq!(buffer.channels, 2);
        assert_eq!(buffer.duration, 0.0);
        assert!(buffer.data.is_empty());
    }

    #[test]
    fn test_audio_buffer_with_data() {
        let buffer = AudioBuffer {
            sample_rate: 48000,
            channels: 1,
            duration: 60.0,
            data: vec![0.5, -0.5, 0.25, -0.25],
        };
        assert_eq!(buffer.sample_rate, 48000);
        assert_eq!(buffer.channels, 1);
        assert_eq!(buffer.duration, 60.0);
        assert_eq!(buffer.data.len(), 4);
    }
}
