//! RNNoise AI noise suppression via native nnnoiseless
//!
//! Real-time noise suppression using Xiph's RNNoise algorithm via
//! the pure Rust nnnoiseless crate (no C library linking required).

use std::path::Path;

/// Noise suppressor using native nnnoiseless
pub struct NoiseSuppressor {
    sample_rate: u32,
    frame_size: usize,
    /// Internal nnnoiseless state
    state: nnnoiseless::DenoiseState<'static>,
    /// Track if this is the first frame (first output should be discarded per nnnoiseless docs)
    first_frame: bool,
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
        // nnnoiseless only supports 48kHz (RNNoise standard)
        // Other rates would require resampling
        if sample_rate != 48000 {
            return Err(NoiseSuppressionError::InvalidSampleRate(sample_rate));
        }
        
        // Use nnnoiseless constant for frame size
        let frame_size = nnnoiseless::DenoiseState::FRAME_SIZE;
        
        // Create nnnoiseless state with default model (returns Box, need to dereference)
        let state = *nnnoiseless::DenoiseState::new();
        
        Ok(Self {
            sample_rate,
            frame_size,
            state,
            first_frame: true,
        })
    }
    
    /// Get frame size (10ms at sample rate)
    pub fn frame_size(&self) -> usize {
        self.frame_size
    }
    
    /// Process audio frame using native RNNoise
    /// 
    /// Note: Per nnnoiseless docs, the first output frame should be discarded
    /// as the neural network warms up.
    pub fn process_frame(&mut self, input: &[f32]) -> Result<Vec<f32>, NoiseSuppressionError> {
        if input.len() != self.frame_size {
            return Err(NoiseSuppressionError::InvalidFrameSize {
                expected: self.frame_size,
                got: input.len(),
            });
        }
        
        // Process through nnnoiseless
        let mut output = vec![0.0f32; self.frame_size];
        self.state.process_frame(&mut output, input);
        
        // Per nnnoiseless docs: discard first output frame
        if self.first_frame {
            self.first_frame = false;
            // Return silence for first frame (network warmup)
            output.fill(0.0);
        }
        
        Ok(output)
    }
    
    /// Process frame with VAD (Voice Activity Detection)
    /// 
    /// Note: nnnoiseless doesn't expose VAD directly. We estimate it from
    /// the output energy (lower output energy = more noise suppression = less voice activity).
    pub fn process_frame_with_vad(&mut self, input: &[f32]) 
        -> Result<NoiseSuppressionResult, NoiseSuppressionError> {
        if input.len() != self.frame_size {
            return Err(NoiseSuppressionError::InvalidFrameSize {
                expected: self.frame_size,
                got: input.len(),
            });
        }
        
        // Process through nnnoiseless
        let mut output = vec![0.0f32; self.frame_size];
        self.state.process_frame(&mut output, input);
        
        // Per nnnoiseless docs: discard first output frame
        if self.first_frame {
            self.first_frame = false;
            output.fill(0.0);
        }
        
        // Estimate VAD from input/output energy ratio
        // Higher ratio = more voice (less suppressed), Lower ratio = more noise
        let input_energy: f32 = input.iter().map(|s| s * s).sum();
        let output_energy: f32 = output.iter().map(|s| s * s).sum();
        
        // VAD estimation: if output is similar to input, likely voice
        // If output is much quieter, likely noise was suppressed
        let vad = if input_energy > 0.0001 {
            let ratio = output_energy / input_energy;
            // Clamp between 0.0 and 1.0, invert so high ratio = high VAD
            (ratio * 2.0).min(1.0).max(0.0)
        } else {
            0.0 // Silence = no voice activity
        };
        
        Ok(NoiseSuppressionResult { vad })
    }
    
    /// Check if native RNNoise is available (always true now)
    pub fn is_available(&self) -> bool {
        true
    }
    
    /// Process file (delegates to frame-by-frame processing)
    pub fn process_file(
        &self,
        _input_path: &Path,
        _output_path: &Path,
    ) -> Result<(), NoiseSuppressionError> {
        // File processing would require hound for WAV I/O
        // For now, return not implemented
        Err(NoiseSuppressionError::Internal(
            "File processing not yet implemented with native RNNoise".to_string()
        ))
    }
}

/// Errors for noise suppression
#[derive(Debug, Clone, PartialEq)]
pub enum NoiseSuppressionError {
    InvalidSampleRate(u32),
    InvalidFrameSize { expected: usize, got: usize },
    NotAvailable,
    Internal(String),
}

impl std::fmt::Display for NoiseSuppressionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            NoiseSuppressionError::InvalidSampleRate(sr) => {
                write!(f, "Invalid sample rate: {}. Only 48000 Hz is supported with native RNNoise", sr)
            }
            NoiseSuppressionError::InvalidFrameSize { expected, got } => {
                write!(f, "Invalid frame size: expected {}, got {}", expected, got)
            }
            NoiseSuppressionError::NotAvailable => {
                write!(f, "Noise suppression not available")
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
        assert!(suppressor.is_ok(), "Native RNNoise should create successfully at 48kHz");
        let suppressor = suppressor.unwrap();
        assert_eq!(suppressor.frame_size(), 480, "Frame size should be 480 samples at 48kHz");
        assert!(suppressor.is_available(), "Native RNNoise should always be available");
    }

    #[test]
    fn test_invalid_sample_rate() {
        // Native nnnoiseless only supports 48kHz
        let result_44k = NoiseSuppressor::new(44100);
        assert!(matches!(result_44k, Err(NoiseSuppressionError::InvalidSampleRate(44100))));
        
        let result_96k = NoiseSuppressor::new(96000);
        assert!(matches!(result_96k, Err(NoiseSuppressionError::InvalidSampleRate(96000))));
    }

    #[test]
    fn test_process_frame() {
        let mut suppressor = NoiseSuppressor::new(48000).unwrap();
        let input = vec![0.5f32; 480];
        let output = suppressor.process_frame(&input).unwrap();
        assert_eq!(output.len(), 480, "Output should have same length as input");
    }

    #[test]
    fn test_process_frame_with_vad() {
        let mut suppressor = NoiseSuppressor::new(48000).unwrap();
        let input = vec![0.5f32; 480];
        let result = suppressor.process_frame_with_vad(&input).unwrap();
        assert!(result.vad >= 0.0 && result.vad <= 1.0, "VAD should be in valid range [0.0, 1.0]");
    }

    #[test]
    fn test_is_available() {
        let suppressor = NoiseSuppressor::new(48000).unwrap();
        assert!(suppressor.is_available(), "Native RNNoise should always report available");
    }
    
    #[test]
    fn test_invalid_frame_size() {
        let mut suppressor = NoiseSuppressor::new(48000).unwrap();
        
        // Try with wrong frame size (should fail)
        let wrong_input = vec![0.5f32; 441]; // 441 samples instead of 480
        let result = suppressor.process_frame(&wrong_input);
        assert!(matches!(result, Err(NoiseSuppressionError::InvalidFrameSize { expected: 480, got: 441 })));
    }
    
    #[test]
    fn test_silence_processing() {
        let mut suppressor = NoiseSuppressor::new(48000).unwrap();
        let silence = vec![0.0f32; 480];
        let output = suppressor.process_frame(&silence).unwrap();
        
        // Silence should remain close to silent (RNNoise should not add significant energy)
        let max_amplitude: f32 = output.iter().map(|s| s.abs()).fold(0.0f32, f32::max);
        assert!(max_amplitude < 0.1, "Silence should remain near-silent after processing, max amp: {}", max_amplitude);
    }
}
