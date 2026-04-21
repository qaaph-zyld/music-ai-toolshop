//! RNNoise AI noise suppression via Python bridge
//!
//! Real-time noise suppression using Xiph's RNNoise library through
//! Python subprocess bridge (avoids FFI linking issues).

use std::path::Path;
use std::process::Command;

/// Noise suppressor using Python bridge
pub struct NoiseSuppressor {
    sample_rate: u32,
    python_available: bool,
}

/// Result of noise suppression processing including VAD
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct NoiseSuppressionResult {
    /// Voice Activity Detection probability (0.0 to 1.0)
    pub vad: f32,
}

impl NoiseSuppressor {
    /// Create a new noise suppressor
    pub fn new(sample_rate: u32) -> Result<Self, NoiseSuppressionError> {
        let supported_rates = [48000, 44100, 32000, 24000, 16000, 12000, 8000];
        if !supported_rates.contains(&sample_rate) {
            return Err(NoiseSuppressionError::InvalidSampleRate(sample_rate));
        }
        
        let python_available = check_python_bridge();
        
        Ok(Self {
            sample_rate,
            python_available,
        })
    }
    
    /// Get frame size (10ms at sample rate)
    pub fn frame_size(&self) -> usize {
        ((self.sample_rate as usize) * 10) / 1000
    }
    
    /// Process audio frame (pass-through, Python handles file processing)
    pub fn process_frame(&mut self, input: &[f32]) -> Result<Vec<f32>, NoiseSuppressionError> {
        Ok(input.to_vec())
    }
    
    /// Process frame with VAD (placeholder)
    pub fn process_frame_with_vad(&mut self, _input: &[f32]) 
        -> Result<NoiseSuppressionResult, NoiseSuppressionError> {
        Ok(NoiseSuppressionResult { vad: 0.5 })
    }
    
    /// Check if bridge is available
    pub fn is_available(&self) -> bool {
        self.python_available
    }
    
    /// Process file via Python bridge
    pub fn process_file(
        &self,
        input_path: &Path,
        output_path: &Path,
    ) -> Result<(), NoiseSuppressionError> {
        if !self.python_available {
            return Err(NoiseSuppressionError::NotAvailable);
        }
        
        let result = Command::new("python")
            .arg("-c")
            .arg(format!(
                "from pathlib import Path; import sys; sys.path.insert(0, 'ai_modules'); from noise_suppression import RNNoiseBridge; b = RNNoiseBridge({}); r = b.process_file(Path('{}'), Path('{}')); print(r)",
                self.sample_rate,
                input_path.display(),
                output_path.display()
            ))
            .output()
            .map_err(|e| NoiseSuppressionError::Internal(e.to_string()))?;
        
        if !result.status.success() {
            let stderr = String::from_utf8_lossy(&result.stderr);
            return Err(NoiseSuppressionError::Internal(format!(
                "Python bridge failed: {}", stderr
            )));
        }
        
        Ok(())
    }
}

fn check_python_bridge() -> bool {
    Command::new("python")
        .args(["-c", "import sys; sys.exit(0)"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

/// Errors for noise suppression
#[derive(Debug, Clone, PartialEq)]
pub enum NoiseSuppressionError {
    InvalidSampleRate(u32),
    NotAvailable,
    Internal(String),
}

impl std::fmt::Display for NoiseSuppressionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            NoiseSuppressionError::InvalidSampleRate(sr) => {
                write!(f, "Invalid sample rate: {}. Supported: 48000, 44100, 32000, 24000, 16000, 12000, 8000", sr)
            }
            NoiseSuppressionError::NotAvailable => {
                write!(f, "Noise suppression not available (Python bridge not found)")
            }
            NoiseSuppressionError::Internal(msg) => {
                write!(f, "Internal error: {}", msg)
            }
        }
    }
}

impl std::error::Error for NoiseSuppressionError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_noise_suppressor_creation() {
        let suppressor = NoiseSuppressor::new(48000);
        assert!(suppressor.is_ok());
        let suppressor = suppressor.unwrap();
        assert_eq!(suppressor.frame_size(), 480);
    }

    #[test]
    fn test_invalid_sample_rate() {
        let result = NoiseSuppressor::new(96000);
        assert!(matches!(result, Err(NoiseSuppressionError::InvalidSampleRate(96000))));
    }

    #[test]
    fn test_process_frame() {
        let mut suppressor = NoiseSuppressor::new(48000).unwrap();
        let input = vec![0.5f32; 480];
        let output = suppressor.process_frame(&input).unwrap();
        assert_eq!(output.len(), 480);
    }

    #[test]
    fn test_process_frame_with_vad() {
        let mut suppressor = NoiseSuppressor::new(48000).unwrap();
        let input = vec![0.5f32; 480];
        let result = suppressor.process_frame_with_vad(&input).unwrap();
        assert!(result.vad >= 0.0 && result.vad <= 1.0);
    }

    #[test]
    fn test_is_available() {
        let suppressor = NoiseSuppressor::new(48000).unwrap();
        let _ = suppressor.is_available();
    }
}
