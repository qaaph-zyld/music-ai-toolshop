//! Fast WAV loading using hound (pure Rust)
//!
//! Uses hound crate for WAV loading - no FFI dependencies.

use std::path::Path;

/// Fast WAV loader using hound (pure Rust implementation)
pub struct FastWavLoader;

impl FastWavLoader {
    /// Load a WAV file using hound
    pub fn load(path: &Path) -> Result<(Vec<f32>, u32, u16), FastWavError> {
        let mut reader = hound::WavReader::open(path)
            .map_err(|e| FastWavError::LoadFailed(e.to_string()))?;
        
        let spec = reader.spec();
        let sample_rate = spec.sample_rate;
        let channels = spec.channels;
        
        // Convert samples to f32
        let samples: Vec<f32> = match spec.sample_format {
            hound::SampleFormat::Int => {
                let max_val = (1i32 << (spec.bits_per_sample - 1)) as f32;
                reader.samples::<i32>()
                    .map(|s| s.unwrap_or(0) as f32 / max_val)
                    .collect()
            }
            hound::SampleFormat::Float => {
                reader.samples::<f32>()
                    .map(|s| s.unwrap_or(0.0))
                    .collect()
            }
        };
        
        if samples.is_empty() {
            return Err(FastWavError::EmptyFile);
        }
        
        Ok((samples, sample_rate, channels))
    }
    
    /// Check if hound is available (always true)
    pub fn is_available() -> bool {
        true
    }
}

/// Errors that can occur during fast WAV loading
#[derive(Debug, Clone, PartialEq)]
pub enum FastWavError {
    /// Invalid file path
    InvalidPath,
    /// Failed to load file
    LoadFailed(String),
    /// File is empty (no samples)
    EmptyFile,
    /// Failed to read all samples
    ReadFailed,
    /// Internal error
    Internal(String),
}

impl std::fmt::Display for FastWavError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FastWavError::InvalidPath => write!(f, "Invalid file path"),
            FastWavError::LoadFailed(path) => write!(f, "Failed to load WAV file: {}", path),
            FastWavError::EmptyFile => write!(f, "WAV file is empty"),
            FastWavError::ReadFailed => write!(f, "Failed to read all samples"),
            FastWavError::Internal(msg) => write!(f, "Internal error: {}", msg),
        }
    }
}

impl std::error::Error for FastWavError {}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    #[test]
    fn test_fast_wav_loader_available() {
        assert!(FastWavLoader::is_available());
    }

    #[test]
    fn test_fast_wav_load_invalid_path() {
        let result = FastWavLoader::load(Path::new("/nonexistent/file.wav"));
        assert!(matches!(result, Err(FastWavError::LoadFailed(_))));
    }
}
