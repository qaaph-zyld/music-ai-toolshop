//! Sample loading
//! 
//! WAV file loading and management using the hound crate.

use std::path::Path;

/// Audio sample data
#[derive(Clone, Debug)]
pub struct Sample {
    data: Vec<f32>,
    channels: u16,
    sample_rate: u32,
}

impl Sample {
    /// Create new sample from raw data
    pub fn new(data: Vec<f32>, channels: u16, sample_rate: u32) -> Self {
        Self {
            data,
            channels,
            sample_rate,
        }
    }
    
    /// Load sample from WAV file
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self, String> {
        let path_ref = path.as_ref();
        
        let reader = hound::WavReader::open(path_ref)
            .map_err(|e| format!("Failed to open WAV file: {}", e))?;
        
        let spec = reader.spec();
        
        // Validate format
        if spec.sample_format != hound::SampleFormat::Int {
            return Err(format!(
                "Unsupported sample format: {:?}. Only integer WAV files are supported.",
                spec.sample_format
            ));
        }
        
        let channels = spec.channels;
        let sample_rate = spec.sample_rate;
        let bits_per_sample = spec.bits_per_sample;
        
        // Read and convert samples to f32
        let mut data = Vec::new();
        
        match bits_per_sample {
            16 => {
                for sample in reader.into_samples::<i16>() {
                    let sample = sample.map_err(|e| format!("Failed to read sample: {}", e))?;
                    data.push(sample as f32 / i16::MAX as f32);
                }
            }
            24 => {
                for sample in reader.into_samples::<i32>() {
                    let sample = sample.map_err(|e| format!("Failed to read sample: {}", e))?;
                    // 24-bit samples are stored in 32-bit integers
                    data.push(sample as f32 / 8388608.0); // 2^23
                }
            }
            32 => {
                for sample in reader.into_samples::<i32>() {
                    let sample = sample.map_err(|e| format!("Failed to read sample: {}", e))?;
                    data.push(sample as f32 / i32::MAX as f32);
                }
            }
            8 => {
                for sample in reader.into_samples::<i8>() {
                    let sample = sample.map_err(|e| format!("Failed to read sample: {}", e))?;
                    data.push((sample as f32 - 128.0) / 128.0);
                }
            }
            _ => {
                return Err(format!(
                    "Unsupported bits per sample: {}. Supported: 8, 16, 24, 32.",
                    bits_per_sample
                ));
            }
        }
        
        Ok(Self {
            data,
            channels,
            sample_rate,
        })
    }
    
    /// Create a sample from raw f32 data
    pub fn from_raw(data: Vec<f32>, channels: u16, sample_rate: u32) -> Self {
        Self {
            data,
            channels,
            sample_rate,
        }
    }
    
    /// Get sample data reference
    pub fn data(&self) -> &[f32] {
        &self.data
    }
    
    /// Get channel count
    pub fn channels(&self) -> u16 {
        self.channels
    }
    
    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
    
    /// Get total frame count (samples per channel)
    pub fn frame_count(&self) -> usize {
        self.data.len() / self.channels as usize
    }
    
    /// Get duration in seconds
    pub fn duration_seconds(&self) -> f32 {
        let frames = self.frame_count();
        frames as f32 / self.sample_rate as f32
    }
    
    /// Get sample at frame index and channel
    pub fn get_sample(&self, frame: usize, channel: usize) -> Option<f32> {
        let idx = frame * self.channels as usize + channel;
        self.data.get(idx).copied()
    }
    
    /// Get interpolated sample at fractional frame position
    pub fn get_interpolated(&self, frame: f32, channel: usize) -> f32 {
        let frame_floor = frame.floor() as usize;
        let frame_ceil = (frame_floor + 1).min(self.frame_count().saturating_sub(1));
        let frac = frame - frame.floor();
        
        let sample_floor = self.get_sample(frame_floor, channel).unwrap_or(0.0);
        let sample_ceil = self.get_sample(frame_ceil, channel).unwrap_or(0.0);
        
        sample_floor + (sample_ceil - sample_floor) * frac
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sample_creation() {
        let data = vec![0.0f32, 0.5, 1.0, -0.5, -1.0, 0.0];
        let sample = Sample::from_raw(data, 2, 48000);
        
        assert_eq!(sample.channels(), 2);
        assert_eq!(sample.sample_rate(), 48000);
        assert_eq!(sample.frame_count(), 3);
        assert!((sample.duration_seconds() - 0.0000625).abs() < 0.000001);
    }

    #[test]
    fn test_get_sample() {
        let data = vec![0.0f32, 0.5, 1.0, -0.5]; // 2 frames, stereo
        let sample = Sample::from_raw(data, 2, 48000);
        
        assert_eq!(sample.get_sample(0, 0), Some(0.0));
        assert_eq!(sample.get_sample(0, 1), Some(0.5));
        assert_eq!(sample.get_sample(1, 0), Some(1.0));
        assert_eq!(sample.get_sample(1, 1), Some(-0.5));
        assert_eq!(sample.get_sample(2, 0), None);
    }

    #[test]
    fn test_interpolated_sample() {
        let data = vec![0.0f32, 1.0]; // 1 frame, stereo
        let sample = Sample::from_raw(data, 2, 48000);
        
        // At frame 0, channel 0 should be 0.0
        assert!(sample.get_interpolated(0.0, 0).abs() < 0.0001);
        // At frame 0, channel 1 should be 1.0
        assert!((sample.get_interpolated(0.0, 1) - 1.0).abs() < 0.0001);
    }
}
