//! Error handling for OpenDAW
//!
//! Centralized error types with context and proper error chaining.

use std::path::PathBuf;
use thiserror::Error;

/// Main error type for OpenDAW operations
#[derive(Error, Debug)]
pub enum DAWError {
    /// Audio device errors (CPAL)
    #[error("audio device error: {0}")]
    Audio(#[from] cpal::BuildStreamError),
    
    /// I/O errors with file path context
    #[error("io error on {path}: {source}")]
    IO {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    
    /// Simple I/O error without path context
    #[error("io error: {0}")]
    IoError(#[from] std::io::Error),
    
    /// JSON serialization/deserialization errors
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    
    /// WAV file parsing errors
    #[error("wav error: {0}")]
    Wav(String),
    
    /// Resource limit exceeded
    #[error("resource limit exceeded: {resource} (max: {max}, requested: {requested})")]
    ResourceLimit {
        resource: String,
        max: usize,
        requested: usize,
    },
    
    /// Invalid parameter value
    #[error("invalid parameter: {param} = {value} (expected: {expected})")]
    InvalidParameter {
        param: String,
        value: String,
        expected: String,
    },
    
    /// Audio format not supported
    #[error("unsupported audio format: {format}")]
    UnsupportedFormat {
        format: String,
    },
    
    /// AI bridge communication error
    #[error("ai bridge error: {0}")]
    AIBridge(String),
    
    /// Session index out of bounds
    #[error("index out of bounds: {index} (max: {max})")]
    OutOfBounds {
        index: usize,
        max: usize,
    },
    
    /// Transport state error
    #[error("transport error: {0}")]
    Transport(String),
    
    /// MIDI parsing/validation error
    #[error("midi error: {0}")]
    Midi(String),
}

impl DAWError {
    /// Create I/O error with path
    pub fn io_error(path: impl Into<PathBuf>, source: std::io::Error) -> Self {
        Self::IO {
            path: path.into(),
            source,
        }
    }
    
    /// Create resource limit error
    pub fn resource_limit(resource: impl Into<String>, max: usize, requested: usize) -> Self {
        Self::ResourceLimit {
            resource: resource.into(),
            max,
            requested,
        }
    }
    
    /// Create invalid parameter error
    pub fn invalid_param(param: impl Into<String>, value: impl Into<String>, expected: impl Into<String>) -> Self {
        Self::InvalidParameter {
            param: param.into(),
            value: value.into(),
            expected: expected.into(),
        }
    }
    
    /// Create out of bounds error
    pub fn out_of_bounds(index: usize, max: usize) -> Self {
        Self::OutOfBounds { index, max }
    }
    
    /// Create WAV error
    pub fn wav_error(msg: impl Into<String>) -> Self {
        Self::Wav(msg.into())
    }
}

/// Result type alias using DAWError
pub type DAWResult<T> = Result<T, DAWError>;

/// Constants for resource limits
pub mod limits {
    /// Maximum number of tracks in a project
    pub const MAX_TRACKS: usize = 128;
    
    /// Maximum number of scenes in session view
    pub const MAX_SCENES: usize = 256;
    
    /// Maximum number of clips per track
    pub const MAX_CLIPS_PER_TRACK: usize = 1024;
    
    /// Maximum number of MIDI notes per clip
    pub const MAX_MIDI_NOTES: usize = 100_000;
    
    /// Maximum sample rate supported
    pub const MAX_SAMPLE_RATE: u32 = 192_000;
    
    /// Minimum sample rate supported
    pub const MIN_SAMPLE_RATE: u32 = 8_000;
    
    /// Maximum buffer size in samples
    pub const MAX_BUFFER_SIZE: usize = 8192;
    
    /// Minimum buffer size in samples
    pub const MIN_BUFFER_SIZE: usize = 16;
    
    /// Maximum file size for project files (100MB)
    pub const MAX_PROJECT_FILE_SIZE: usize = 100 * 1024 * 1024;
    
    /// Maximum audio file size (1GB)
    pub const MAX_AUDIO_FILE_SIZE: usize = 1024 * 1024 * 1024;
    
    /// Maximum project name length
    pub const MAX_PROJECT_NAME_LEN: usize = 256;
    
    /// Maximum tempo (BPM)
    pub const MAX_TEMPO: f32 = 999.0;
    
    /// Minimum tempo (BPM)
    pub const MIN_TEMPO: f32 = 1.0;
}

/// Validate a sample rate is within supported range
pub fn validate_sample_rate(rate: u32) -> DAWResult<u32> {
    if rate < limits::MIN_SAMPLE_RATE || rate > limits::MAX_SAMPLE_RATE {
        return Err(DAWError::invalid_param(
            "sample_rate",
            rate.to_string(),
            format!("{}..={}", limits::MIN_SAMPLE_RATE, limits::MAX_SAMPLE_RATE),
        ));
    }
    Ok(rate)
}

/// Validate tempo is within supported range
pub fn validate_tempo(tempo: f32) -> DAWResult<f32> {
    if tempo < limits::MIN_TEMPO || tempo > limits::MAX_TEMPO {
        return Err(DAWError::invalid_param(
            "tempo",
            tempo.to_string(),
            format!("{}..={}", limits::MIN_TEMPO, limits::MAX_TEMPO),
        ));
    }
    Ok(tempo.clamp(limits::MIN_TEMPO, limits::MAX_TEMPO))
}

/// Validate buffer size is within supported range
pub fn validate_buffer_size(size: usize) -> DAWResult<usize> {
    if size < limits::MIN_BUFFER_SIZE || size > limits::MAX_BUFFER_SIZE {
        return Err(DAWError::invalid_param(
            "buffer_size",
            size.to_string(),
            format!("{}..={}", limits::MIN_BUFFER_SIZE, limits::MAX_BUFFER_SIZE),
        ));
    }
    Ok(size)
}

/// Validate track count is within supported range
pub fn validate_track_count(count: usize) -> DAWResult<usize> {
    if count > limits::MAX_TRACKS {
        return Err(DAWError::resource_limit("tracks", limits::MAX_TRACKS, count));
    }
    Ok(count)
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_error_creation() {
        let err = DAWError::resource_limit("tracks", 128, 200);
        assert!(err.to_string().contains("128"));
        assert!(err.to_string().contains("200"));
    }
    
    #[test]
    fn test_io_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let err = DAWError::io_error("/path/to/file.wav", io_err);
        assert!(err.to_string().contains("/path/to/file.wav"));
    }
    
    #[test]
    fn test_validate_sample_rate() {
        assert!(validate_sample_rate(48000).is_ok());
        assert!(validate_sample_rate(100).is_err());
        assert!(validate_sample_rate(200000).is_err());
    }
    
    #[test]
    fn test_validate_tempo() {
        assert!(validate_tempo(120.0).is_ok());
        assert!(validate_tempo(0.5).is_err());
        assert!(validate_tempo(2000.0).is_err());
    }
    
    #[test]
    fn test_validate_track_count() {
        assert!(validate_track_count(64).is_ok());
        assert!(validate_track_count(200).is_err());
    }
}
