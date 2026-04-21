//! audiowaveform - Pre-computed Waveform Generation
//!
//! Command-line tool for generating waveform data from audio files.
//! Creates JSON or binary waveform data for efficient visualization.
//!
//! Repository: https://github.com/bbc/audiowaveform

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::os::raw::{c_double, c_float, c_short, c_uint};
use std::path::Path;

/// Waveform generator
pub struct WaveformGenerator {
    handle: *mut c_void,
}

/// Output format for waveform data
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OutputFormat {
    Json,
    Binary,
    Dat,
}

impl Default for OutputFormat {
    fn default() -> Self {
        OutputFormat::Json
    }
}

/// Resolution/precision of waveform data
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum WaveformResolution {
    Low,     // 256 samples per pixel
    Medium,  // 512 samples per pixel  
    High,    // 1024 samples per pixel
    Custom(u32),
}

impl Default for WaveformResolution {
    fn default() -> Self {
        WaveformResolution::Medium
    }
}

impl WaveformResolution {
    pub fn samples_per_pixel(&self) -> u32 {
        match self {
            WaveformResolution::Low => 256,
            WaveformResolution::Medium => 512,
            WaveformResolution::High => 1024,
            WaveformResolution::Custom(n) => *n,
        }
    }
}

/// Bits for output precision
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BitDepth {
    Bit8,
    Bit16,
}

impl Default for BitDepth {
    fn default() -> Self {
        BitDepth::Bit16
    }
}

impl BitDepth {
    pub fn bits(&self) -> u8 {
        match self {
            BitDepth::Bit8 => 8,
            BitDepth::Bit16 => 16,
        }
    }
}

/// Generated waveform data
#[derive(Debug, Clone)]
pub struct WaveformData {
    pub samples_per_pixel: u32,
    pub bits: u8,
    pub length: u32,
    pub data_min: Vec<i16>,
    pub data_max: Vec<i16>,
    pub sample_rate: u32,
    pub channels: u16,
    pub duration: f64,
}

impl Default for WaveformData {
    fn default() -> Self {
        WaveformData {
            samples_per_pixel: 512,
            bits: 16,
            length: 0,
            data_min: Vec::new(),
            data_max: Vec::new(),
            sample_rate: 44100,
            channels: 2,
            duration: 0.0,
        }
    }
}

/// Waveform generation options
#[derive(Debug, Clone)]
pub struct GenerationOptions {
    pub input_path: String,
    pub output_path: String,
    pub format: OutputFormat,
    pub resolution: WaveformResolution,
    pub bits: BitDepth,
    pub start_time: f64,
    pub end_time: f64,
    pub zoom: u32,
}

impl Default for GenerationOptions {
    fn default() -> Self {
        GenerationOptions {
            input_path: String::new(),
            output_path: String::new(),
            format: OutputFormat::default(),
            resolution: WaveformResolution::default(),
            bits: BitDepth::default(),
            start_time: 0.0,
            end_time: 0.0,
            zoom: 1,
        }
    }
}

/// Analysis result
#[derive(Debug, Clone)]
pub struct AnalysisResult {
    pub peak_amplitude: f32,
    pub rms_amplitude: f32,
    pub dc_offset: f32,
    pub true_peak: f32,
    pub loudness_lufs: f32,
}

impl Default for AnalysisResult {
    fn default() -> Self {
        AnalysisResult {
            peak_amplitude: 0.0,
            rms_amplitude: 0.0,
            dc_offset: 0.0,
            true_peak: 0.0,
            loudness_lufs: -70.0,
        }
    }
}

/// Cache entry for waveform data
#[derive(Debug, Clone)]
pub struct WaveformCache {
    pub file_hash: String,
    pub waveform: WaveformData,
    pub created_at: u64,
}

/// audiowaveform availability status
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AudiowaveformStatus {
    Available,
    NotAvailable,
    Error(&'static str),
}

/// FFI interface to audiowaveform library
#[link(name = "daw_engine_ffi")]
extern "C" {
    fn audiowaveform_create() -> *mut c_void;
    fn audiowaveform_destroy(handle: *mut c_void);
    fn audiowaveform_available() -> c_int;
    fn audiowaveform_generate(
        handle: *mut c_void,
        input_path: *const c_char,
        output_path: *const c_char,
        format: c_int,
        samples_per_pixel: c_int,
        bits: c_int,
    ) -> c_int;
    fn audiowaveform_generate_partial(
        handle: *mut c_void,
        input_path: *const c_char,
        output_path: *const c_char,
        format: c_int,
        samples_per_pixel: c_int,
        bits: c_int,
        start_time: c_double,
        end_time: c_double,
    ) -> c_int;
    fn audiowaveform_analyze(
        handle: *mut c_void,
        input_path: *const c_char,
        peak_amp: *mut c_float,
        rms_amp: *mut c_float,
        dc_offset: *mut c_float,
        true_peak: *mut c_float,
        loudness: *mut c_float,
    ) -> c_int;
    fn audiowaveform_load_data(
        handle: *mut c_void,
        data_path: *const c_char,
        samples_per_pixel: *mut c_int,
        bits: *mut c_int,
        length: *mut c_int,
    ) -> c_int;
    fn audiowaveform_get_peak_data(
        handle: *mut c_void,
        min_data: *mut c_short,
        max_data: *mut c_short,
        offset: c_int,
        count: c_int,
    ) -> c_int;
    fn audiowaveform_clear(handle: *mut c_void) -> c_int;
}

impl WaveformGenerator {
    /// Create new waveform generator
    pub fn new() -> Option<Self> {
        unsafe {
            let handle = audiowaveform_create();
            if handle.is_null() {
                None
            } else {
                Some(WaveformGenerator { handle })
            }
        }
    }

    /// Check if audiowaveform is available
    pub fn is_available() -> bool {
        unsafe { audiowaveform_available() != 0 }
    }

    /// Get availability status
    pub fn availability_status() -> AudiowaveformStatus {
        if Self::is_available() {
            AudiowaveformStatus::Available
        } else {
            AudiowaveformStatus::NotAvailable
        }
    }

    /// Generate waveform from audio file
    pub fn generate(&mut self, options: &GenerationOptions) -> Result<(), &'static str> {
        unsafe {
            let c_input = CString::new(options.input_path.clone())
                .map_err(|_| "Invalid input path")?;
            let c_output = CString::new(options.output_path.clone())
                .map_err(|_| "Invalid output path")?;
            
            let format = match options.format {
                OutputFormat::Json => 0,
                OutputFormat::Binary => 1,
                OutputFormat::Dat => 2,
            };
            
            let result = audiowaveform_generate(
                self.handle,
                c_input.as_ptr(),
                c_output.as_ptr(),
                format,
                options.resolution.samples_per_pixel() as c_int,
                options.bits.bits() as c_int,
            );
            
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to generate waveform")
            }
        }
    }

    /// Generate waveform for a time range
    pub fn generate_partial(&mut self, options: &GenerationOptions) -> Result<(), &'static str> {
        unsafe {
            let c_input = CString::new(options.input_path.clone())
                .map_err(|_| "Invalid input path")?;
            let c_output = CString::new(options.output_path.clone())
                .map_err(|_| "Invalid output path")?;
            
            let format = match options.format {
                OutputFormat::Json => 0,
                OutputFormat::Binary => 1,
                OutputFormat::Dat => 2,
            };
            
            let result = audiowaveform_generate_partial(
                self.handle,
                c_input.as_ptr(),
                c_output.as_ptr(),
                format,
                options.resolution.samples_per_pixel() as c_int,
                options.bits.bits() as c_int,
                options.start_time,
                options.end_time,
            );
            
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to generate partial waveform")
            }
        }
    }

    /// Analyze audio file
    pub fn analyze(&mut self, input_path: &str) -> Result<AnalysisResult, &'static str> {
        unsafe {
            let c_input = CString::new(input_path)
                .map_err(|_| "Invalid input path")?;
            
            let mut result = AnalysisResult::default();
            
            let status = audiowaveform_analyze(
                self.handle,
                c_input.as_ptr(),
                &mut result.peak_amplitude,
                &mut result.rms_amplitude,
                &mut result.dc_offset,
                &mut result.true_peak,
                &mut result.loudness_lufs,
            );
            
            if status == 0 {
                Ok(result)
            } else {
                Err("Failed to analyze audio file")
            }
        }
    }

    /// Load existing waveform data
    pub fn load_data(&mut self, data_path: &str) -> Result<WaveformData, &'static str> {
        unsafe {
            let c_path = CString::new(data_path)
                .map_err(|_| "Invalid data path")?;
            
            let mut samples_per_pixel: c_int = 0;
            let mut bits: c_int = 0;
            let mut length: c_int = 0;
            
            let status = audiowaveform_load_data(
                self.handle,
                c_path.as_ptr(),
                &mut samples_per_pixel,
                &mut bits,
                &mut length,
            );
            
            if status == 0 {
                let mut waveform = WaveformData {
                    samples_per_pixel: samples_per_pixel as u32,
                    bits: bits as u8,
                    length: length as u32,
                    ..Default::default()
                };
                
                // Load actual data
                if length > 0 {
                    waveform.data_min = vec![0; length as usize];
                    waveform.data_max = vec![0; length as usize];
                    
                    audiowaveform_get_peak_data(
                        self.handle,
                        waveform.data_min.as_mut_ptr(),
                        waveform.data_max.as_mut_ptr(),
                        0,
                        length,
                    );
                }
                
                Ok(waveform)
            } else {
                Err("Failed to load waveform data")
            }
        }
    }

    /// Clear generator state
    pub fn clear(&mut self) -> Result<(), &'static str> {
        unsafe {
            let result = audiowaveform_clear(self.handle);
            if result == 0 {
                Ok(())
            } else {
                Err("Failed to clear generator")
            }
        }
    }
}

impl Drop for WaveformGenerator {
    fn drop(&mut self) {
        unsafe {
            audiowaveform_destroy(self.handle);
        }
    }
}

unsafe impl Send for WaveformGenerator {}
unsafe impl Sync for WaveformGenerator {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audiowaveform_availability() {
        let available = WaveformGenerator::is_available();
        assert!(!available, "Audiowaveform should report not available (stub)");
    }

    #[test]
    fn test_audiowaveform_status() {
        let status = WaveformGenerator::availability_status();
        match status {
            AudiowaveformStatus::NotAvailable => (),
            AudiowaveformStatus::Available => panic!("Should not be available with stub"),
            AudiowaveformStatus::Error(_) => (),
        }
    }

    #[test]
    fn test_output_format_default() {
        let format = OutputFormat::default();
        assert!(matches!(format, OutputFormat::Json));
    }

    #[test]
    fn test_output_format_variants() {
        let formats = [
            OutputFormat::Json,
            OutputFormat::Binary,
            OutputFormat::Dat,
        ];
        
        for format in &formats {
            // Just verify they exist and are distinct
            match format {
                OutputFormat::Json | OutputFormat::Binary | OutputFormat::Dat => (),
            }
        }
    }

    #[test]
    fn test_waveform_resolution_default() {
        let res = WaveformResolution::default();
        assert_eq!(res.samples_per_pixel(), 512);
    }

    #[test]
    fn test_waveform_resolution_variants() {
        assert_eq!(WaveformResolution::Low.samples_per_pixel(), 256);
        assert_eq!(WaveformResolution::Medium.samples_per_pixel(), 512);
        assert_eq!(WaveformResolution::High.samples_per_pixel(), 1024);
        assert_eq!(WaveformResolution::Custom(2048).samples_per_pixel(), 2048);
    }

    #[test]
    fn test_bit_depth_default() {
        let depth = BitDepth::default();
        assert_eq!(depth.bits(), 16);
    }

    #[test]
    fn test_bit_depth_variants() {
        assert_eq!(BitDepth::Bit8.bits(), 8);
        assert_eq!(BitDepth::Bit16.bits(), 16);
    }

    #[test]
    fn test_waveform_data_default() {
        let data = WaveformData::default();
        assert_eq!(data.samples_per_pixel, 512);
        assert_eq!(data.bits, 16);
        assert_eq!(data.length, 0);
        assert!(data.data_min.is_empty());
        assert!(data.data_max.is_empty());
        assert_eq!(data.sample_rate, 44100);
        assert_eq!(data.channels, 2);
        assert_eq!(data.duration, 0.0);
    }

    #[test]
    fn test_waveform_data_custom() {
        let data = WaveformData {
            samples_per_pixel: 256,
            bits: 8,
            length: 1000,
            data_min: vec![-100; 1000],
            data_max: vec![100; 1000],
            sample_rate: 48000,
            channels: 1,
            duration: 180.0,
        };
        assert_eq!(data.samples_per_pixel, 256);
        assert_eq!(data.bits, 8);
        assert_eq!(data.length, 1000);
        assert_eq!(data.data_min.len(), 1000);
        assert_eq!(data.data_max.len(), 1000);
        assert_eq!(data.sample_rate, 48000);
        assert_eq!(data.channels, 1);
        assert_eq!(data.duration, 180.0);
    }

    #[test]
    fn test_generation_options_default() {
        let opts = GenerationOptions::default();
        assert!(opts.input_path.is_empty());
        assert!(opts.output_path.is_empty());
        assert!(matches!(opts.format, OutputFormat::Json));
        assert_eq!(opts.resolution.samples_per_pixel(), 512);
        assert_eq!(opts.bits.bits(), 16);
        assert_eq!(opts.start_time, 0.0);
        assert_eq!(opts.end_time, 0.0);
        assert_eq!(opts.zoom, 1);
    }

    #[test]
    fn test_generation_options_custom() {
        let opts = GenerationOptions {
            input_path: "input.wav".to_string(),
            output_path: "output.json".to_string(),
            format: OutputFormat::Binary,
            resolution: WaveformResolution::High,
            bits: BitDepth::Bit8,
            start_time: 10.0,
            end_time: 60.0,
            zoom: 2,
        };
        assert_eq!(opts.input_path, "input.wav");
        assert_eq!(opts.output_path, "output.json");
        assert!(matches!(opts.format, OutputFormat::Binary));
        assert_eq!(opts.resolution.samples_per_pixel(), 1024);
        assert_eq!(opts.bits.bits(), 8);
        assert_eq!(opts.start_time, 10.0);
        assert_eq!(opts.end_time, 60.0);
        assert_eq!(opts.zoom, 2);
    }

    #[test]
    fn test_analysis_result_default() {
        let result = AnalysisResult::default();
        assert_eq!(result.peak_amplitude, 0.0);
        assert_eq!(result.rms_amplitude, 0.0);
        assert_eq!(result.dc_offset, 0.0);
        assert_eq!(result.true_peak, 0.0);
        assert_eq!(result.loudness_lufs, -70.0);
    }

    #[test]
    fn test_analysis_result_custom() {
        let result = AnalysisResult {
            peak_amplitude: 0.95,
            rms_amplitude: 0.5,
            dc_offset: 0.001,
            true_peak: 1.0,
            loudness_lufs: -14.0,
        };
        assert_eq!(result.peak_amplitude, 0.95);
        assert_eq!(result.rms_amplitude, 0.5);
        assert_eq!(result.dc_offset, 0.001);
        assert_eq!(result.true_peak, 1.0);
        assert_eq!(result.loudness_lufs, -14.0);
    }

    #[test]
    fn test_waveform_cache() {
        let cache = WaveformCache {
            file_hash: "abc123".to_string(),
            waveform: WaveformData::default(),
            created_at: 1234567890,
        };
        assert_eq!(cache.file_hash, "abc123");
        assert_eq!(cache.created_at, 1234567890);
    }
}
