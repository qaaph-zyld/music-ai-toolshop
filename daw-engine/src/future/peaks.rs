//! peaks - BBC Peaks Waveform Visualization
//!
//! High-performance waveform visualization from BBC R&D.
//! Renders waveform data from pre-computed peaks or audio buffers.
//!
//! Repository: https://github.com/bbc/peaks.js

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_uint};

/// Peaks waveform viewer
pub struct PeaksViewer {
    handle: *mut c_void,
    container_id: String,
    width: u32,
    height: u32,
}

/// Waveform data point (min/max amplitude pair)
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PeakPoint {
    pub min: f32,
    pub max: f32,
}

impl Default for PeakPoint {
    fn default() -> Self {
        PeakPoint {
            min: 0.0,
            max: 0.0,
        }
    }
}

/// Waveform segment (marked region)
#[derive(Debug, Clone, PartialEq)]
pub struct PeaksSegment {
    pub id: String,
    pub start_time: f64,
    pub end_time: f64,
    pub label_text: String,
    pub color: u32,
    pub editable: bool,
}

impl Default for PeaksSegment {
    fn default() -> Self {
        PeaksSegment {
            id: String::new(),
            start_time: 0.0,
            end_time: 0.0,
            label_text: String::new(),
            color: 0x3366CC,
            editable: true,
        }
    }
}

/// Waveform point marker
#[derive(Debug, Clone, PartialEq)]
pub struct PeaksPoint {
    pub id: String,
    pub time: f64,
    pub label_text: String,
    pub color: u32,
    pub editable: bool,
}

impl Default for PeaksPoint {
    fn default() -> Self {
        PeaksPoint {
            id: String::new(),
            time: 0.0,
            label_text: String::new(),
            color: 0xFF0000,
            editable: true,
        }
    }
}

/// View options for zoom and offset
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ViewOptions {
    pub start_time: f64,
    pub end_time: f64,
    pub zoom_level: f32,
}

impl Default for ViewOptions {
    fn default() -> Self {
        ViewOptions {
            start_time: 0.0,
            end_time: 0.0,
            zoom_level: 1.0,
        }
    }
}

/// Audio metadata
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AudioMetadata {
    pub sample_rate: u32,
    pub channels: u16,
    pub duration: f64,
    pub bit_depth: u16,
}

impl Default for AudioMetadata {
    fn default() -> Self {
        AudioMetadata {
            sample_rate: 44100,
            channels: 2,
            duration: 0.0,
            bit_depth: 16,
        }
    }
}

/// Responsive sizing options
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ResponsiveOptions {
    pub enabled: bool,
    pub min_width: u32,
    pub max_width: u32,
    pub maintain_aspect_ratio: bool,
}

impl Default for ResponsiveOptions {
    fn default() -> Self {
        ResponsiveOptions {
            enabled: true,
            min_width: 200,
            max_width: 4096,
            maintain_aspect_ratio: false,
        }
    }
}

/// Peaks availability status
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PeaksStatus {
    Available,
    NotAvailable,
    Error(&'static str),
}

/// FFI interface to peaks.js library
#[link(name = "daw_engine_ffi")]
extern "C" {
    fn peaks_create(container_id: *const c_char, width: c_int, height: c_int) -> *mut c_void;
    fn peaks_destroy(handle: *mut c_void);
    fn peaks_available() -> c_int;
    fn peaks_load_data(
        handle: *mut c_void,
        peaks_data: *const c_float,
        length: c_int,
        channels: c_int,
        sample_rate: c_int,
    ) -> c_int;
    fn peaks_set_zoom(handle: *mut c_void, samples_per_pixel: c_int) -> c_int;
    fn peaks_get_zoom(handle: *mut c_void) -> c_int;
    fn peaks_set_offset(handle: *mut c_void, time: c_double) -> c_int;
    fn peaks_get_offset(handle: *mut c_void) -> c_double;
    fn peaks_add_segment(
        handle: *mut c_void,
        id: *const c_char,
        start_time: c_double,
        end_time: c_double,
        label: *const c_char,
        color: c_uint,
        editable: c_int,
    ) -> c_int;
    fn peaks_remove_segment(handle: *mut c_void, segment_id: *const c_char) -> c_int;
    fn peaks_clear_segments(handle: *mut c_void) -> c_int;
    fn peaks_add_point(
        handle: *mut c_void,
        id: *const c_char,
        time: c_double,
        label: *const c_char,
        color: c_uint,
        editable: c_int,
    ) -> c_int;
    fn peaks_remove_point(handle: *mut c_void, point_id: *const c_char) -> c_int;
    fn peaks_clear_points(handle: *mut c_void) -> c_int;
    fn peaks_set_view(handle: *mut c_void, start: c_double, end: c_double) -> c_int;
    fn peaks_get_duration(handle: *mut c_void) -> c_double;
    fn peaks_seek(handle: *mut c_void, time: c_double) -> c_int;
    fn peaks_resize(handle: *mut c_void, width: c_int, height: c_int) -> c_int;
    fn peaks_clear(handle: *mut c_void) -> c_int;
}

impl PeaksViewer {
    /// Create new Peaks viewer
    pub fn new(container_id: &str, width: u32, height: u32) -> Option<Self> {
        unsafe {
            let c_id = CString::new(container_id).ok()?;
            let handle = peaks_create(c_id.as_ptr(), width as c_int, height as c_int);
            if handle.is_null() {
                None
            } else {
                Some(PeaksViewer {
                    handle,
                    container_id: container_id.to_string(),
                    width,
                    height,
                })
            }
        }
    }

    /// Check if peaks library is available
    pub fn is_available() -> bool {
        unsafe { peaks_available() != 0 }
    }

    /// Get availability status
    pub fn availability_status() -> PeaksStatus {
        if Self::is_available() {
            PeaksStatus::Available
        } else {
            PeaksStatus::NotAvailable
        }
    }

    /// Load waveform data
    pub fn load_data(&mut self, peaks: &[PeakPoint], metadata: &AudioMetadata) -> Result<(), &'static str> {
        // Flatten peaks data into min/max pairs
        let mut data: Vec<f32> = Vec::with_capacity(peaks.len() * 2);
        for peak in peaks {
            data.push(peak.min);
            data.push(peak.max);
        }
        
        unsafe {
            let result = peaks_load_data(
                self.handle,
                data.as_ptr(),
                (data.len() / 2) as c_int, // Number of frames
                metadata.channels as c_int,
                metadata.sample_rate as c_int,
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to load peaks data")
            }
        }
    }

    /// Set zoom level (samples per pixel)
    pub fn set_zoom(&mut self, samples_per_pixel: u32) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_set_zoom(self.handle, samples_per_pixel as c_int);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set zoom")
            }
        }
    }

    /// Get current zoom level
    pub fn get_zoom(&self) -> u32 {
        unsafe { peaks_get_zoom(self.handle) as u32 }
    }

    /// Set view offset (start time)
    pub fn set_offset(&mut self, time: f64) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_set_offset(self.handle, time);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set offset")
            }
        }
    }

    /// Get current offset
    pub fn get_offset(&self) -> f64 {
        unsafe { peaks_get_offset(self.handle) }
    }

    /// Add a segment
    pub fn add_segment(&mut self, segment: &PeaksSegment) -> Result<(), &'static str> {
        unsafe {
            let c_id = CString::new(segment.id.clone()).map_err(|_| "Invalid segment ID")?;
            let c_label = CString::new(segment.label_text.clone()).map_err(|_| "Invalid label")?;
            
            let result = peaks_add_segment(
                self.handle,
                c_id.as_ptr(),
                segment.start_time,
                segment.end_time,
                c_label.as_ptr(),
                segment.color,
                if segment.editable { 1 } else { 0 },
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to add segment")
            }
        }
    }

    /// Remove a segment
    pub fn remove_segment(&mut self, segment_id: &str) -> Result<(), &'static str> {
        unsafe {
            let c_id = CString::new(segment_id).map_err(|_| "Invalid segment ID")?;
            let result = peaks_remove_segment(self.handle, c_id.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to remove segment")
            }
        }
    }

    /// Clear all segments
    pub fn clear_segments(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_clear_segments(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear segments")
            }
        }
    }

    /// Add a point marker
    pub fn add_point(&mut self, point: &PeaksPoint) -> Result<(), &'static str> {
        unsafe {
            let c_id = CString::new(point.id.clone()).map_err(|_| "Invalid point ID")?;
            let c_label = CString::new(point.label_text.clone()).map_err(|_| "Invalid label")?;
            
            let result = peaks_add_point(
                self.handle,
                c_id.as_ptr(),
                point.time,
                c_label.as_ptr(),
                point.color,
                if point.editable { 1 } else { 0 },
            );
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to add point")
            }
        }
    }

    /// Remove a point marker
    pub fn remove_point(&mut self, point_id: &str) -> Result<(), &'static str> {
        unsafe {
            let c_id = CString::new(point_id).map_err(|_| "Invalid point ID")?;
            let result = peaks_remove_point(self.handle, c_id.as_ptr());
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to remove point")
            }
        }
    }

    /// Clear all point markers
    pub fn clear_points(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_clear_points(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear points")
            }
        }
    }

    /// Set view window (start and end time)
    pub fn set_view(&mut self, start: f64, end: f64) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_set_view(self.handle, start, end);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to set view")
            }
        }
    }

    /// Get audio duration
    pub fn get_duration(&self) -> f64 {
        unsafe { peaks_get_duration(self.handle) }
    }

    /// Seek to time
    pub fn seek(&mut self, time: f64) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_seek(self.handle, time);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to seek")
            }
        }
    }

    /// Resize viewer
    pub fn resize(&mut self, width: u32, height: u32) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_resize(self.handle, width as c_int, height as c_int);
            if result == 0 {
                self.width = width;
                self.height = height;
                Ok(())
            } else {
                Err("Failed to resize")
            }
        }
    }

    /// Clear all data
    pub fn clear(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = peaks_clear(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear")
            }
        }
    }
}

impl Drop for PeaksViewer {
    fn drop(&mut self) {
        unsafe {
            peaks_destroy(self.handle);
        }
    }
}

unsafe impl Send for PeaksViewer {}
unsafe impl Sync for PeaksViewer {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_peaks_availability() {
        let available = PeaksViewer::is_available();
        assert!(!available, "Peaks should report not available (stub)");
    }

    #[test]
    fn test_peaks_status() {
        let status = PeaksViewer::availability_status();
        match status {
            PeaksStatus::NotAvailable => (),
            PeaksStatus::Available => panic!("Should not be available with stub"),
            PeaksStatus::Error(_) => (),
        }
    }

    #[test]
    fn test_peak_point_default() {
        let point = PeakPoint::default();
        assert_eq!(point.min, 0.0);
        assert_eq!(point.max, 0.0);
    }

    #[test]
    fn test_peak_point_custom() {
        let point = PeakPoint {
            min: -0.8,
            max: 0.9,
        };
        assert_eq!(point.min, -0.8);
        assert_eq!(point.max, 0.9);
    }

    #[test]
    fn test_segment_default() {
        let segment = PeaksSegment::default();
        assert!(segment.id.is_empty());
        assert_eq!(segment.start_time, 0.0);
        assert_eq!(segment.end_time, 0.0);
        assert!(segment.label_text.is_empty());
        assert_eq!(segment.color, 0x3366CC);
        assert!(segment.editable);
    }

    #[test]
    fn test_segment_custom() {
        let segment = PeaksSegment {
            id: "segment_1".to_string(),
            start_time: 10.0,
            end_time: 20.0,
            label_text: "Intro".to_string(),
            color: 0x00FF00,
            editable: false,
        };
        assert_eq!(segment.id, "segment_1");
        assert_eq!(segment.start_time, 10.0);
        assert_eq!(segment.end_time, 20.0);
        assert_eq!(segment.label_text, "Intro");
        assert_eq!(segment.color, 0x00FF00);
        assert!(!segment.editable);
    }

    #[test]
    fn test_point_default() {
        let point = PeaksPoint::default();
        assert!(point.id.is_empty());
        assert_eq!(point.time, 0.0);
        assert!(point.label_text.is_empty());
        assert_eq!(point.color, 0xFF0000);
        assert!(point.editable);
    }

    #[test]
    fn test_point_custom() {
        let point = PeaksPoint {
            id: "point_1".to_string(),
            time: 15.5,
            label_text: "Marker".to_string(),
            color: 0x3366CC,
            editable: false,
        };
        assert_eq!(point.id, "point_1");
        assert_eq!(point.time, 15.5);
        assert_eq!(point.label_text, "Marker");
        assert_eq!(point.color, 0x3366CC);
        assert!(!point.editable);
    }

    #[test]
    fn test_view_options_default() {
        let options = ViewOptions::default();
        assert_eq!(options.start_time, 0.0);
        assert_eq!(options.end_time, 0.0);
        assert_eq!(options.zoom_level, 1.0);
    }

    #[test]
    fn test_view_options_custom() {
        let options = ViewOptions {
            start_time: 5.0,
            end_time: 30.0,
            zoom_level: 2.5,
        };
        assert_eq!(options.start_time, 5.0);
        assert_eq!(options.end_time, 30.0);
        assert_eq!(options.zoom_level, 2.5);
    }

    #[test]
    fn test_audio_metadata_default() {
        let meta = AudioMetadata::default();
        assert_eq!(meta.sample_rate, 44100);
        assert_eq!(meta.channels, 2);
        assert_eq!(meta.duration, 0.0);
        assert_eq!(meta.bit_depth, 16);
    }

    #[test]
    fn test_audio_metadata_custom() {
        let meta = AudioMetadata {
            sample_rate: 48000,
            channels: 1,
            duration: 180.5,
            bit_depth: 24,
        };
        assert_eq!(meta.sample_rate, 48000);
        assert_eq!(meta.channels, 1);
        assert_eq!(meta.duration, 180.5);
        assert_eq!(meta.bit_depth, 24);
    }

    #[test]
    fn test_responsive_options_default() {
        let opts = ResponsiveOptions::default();
        assert!(opts.enabled);
        assert_eq!(opts.min_width, 200);
        assert_eq!(opts.max_width, 4096);
        assert!(!opts.maintain_aspect_ratio);
    }

    #[test]
    fn test_responsive_options_custom() {
        let opts = ResponsiveOptions {
            enabled: false,
            min_width: 100,
            max_width: 1920,
            maintain_aspect_ratio: true,
        };
        assert!(!opts.enabled);
        assert_eq!(opts.min_width, 100);
        assert_eq!(opts.max_width, 1920);
        assert!(opts.maintain_aspect_ratio);
    }
}
