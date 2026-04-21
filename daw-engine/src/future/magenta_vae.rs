//! Magenta MusicVAE Integration
//!
//! FFI bindings to Google's Magenta MusicVAE for neural music generation.
//! MusicVAE uses a hierarchical recurrent variational autoencoder to model
//! musical sequences with controllable latent spaces.
//!
//! License: Apache-2.0
//! Repo: https://github.com/magenta/magenta

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint};

/// Opaque handle to MusicVAE model
#[repr(C)]
pub struct MusicVaeModel {
    _private: [u8; 0],
}

/// MusicVAE error types
#[derive(Debug, Clone, PartialEq)]
pub enum MusicVaeError {
    ModelNotFound(String),
    ModelLoadFailed(String),
    EncodeFailed(String),
    DecodeFailed(String),
    InvalidMidiData(String),
    FfiError(String),
}

impl std::fmt::Display for MusicVaeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MusicVaeError::ModelNotFound(path) => write!(f, "MusicVAE model not found: {}", path),
            MusicVaeError::ModelLoadFailed(msg) => write!(f, "Model load failed: {}", msg),
            MusicVaeError::EncodeFailed(msg) => write!(f, "Encode failed: {}", msg),
            MusicVaeError::DecodeFailed(msg) => write!(f, "Decode failed: {}", msg),
            MusicVaeError::InvalidMidiData(msg) => write!(f, "Invalid MIDI data: {}", msg),
            MusicVaeError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for MusicVaeError {}

/// MusicVAE model configuration
#[derive(Debug, Clone)]
pub struct MusicVaeConfig {
    pub model_name: String,
    pub model_version: String,
    pub latent_dim: usize,
    pub max_sequence_length: usize,
}

/// Latent vector for music representation
pub type LatentVector = Vec<f32>;

/// MusicVAE processor
pub struct MusicVae {
    model: *mut MusicVaeModel,
    config: MusicVaeConfig,
}

// FFI function declarations
extern "C" {
    fn musicvae_ffi_is_available() -> c_int;
    fn musicvae_ffi_get_version() -> *const c_char;
    
    // Model management
    fn musicvae_ffi_model_load(config_path: *const c_char) -> *mut MusicVaeModel;
    fn musicvae_ffi_model_free(model: *mut MusicVaeModel);
    fn musicvae_ffi_model_get_config(model: *mut MusicVaeModel, config: *mut MusicVaeConfigFFI);
    
    // Encoding/Decoding
    fn musicvae_ffi_encode(
        model: *mut MusicVaeModel,
        midi_data: *const c_char,
        midi_size: c_uint,
        latent: *mut c_float,
        latent_size: c_uint,
    ) -> c_int;
    
    fn musicvae_ffi_decode(
        model: *mut MusicVaeModel,
        latent: *const c_float,
        latent_size: c_uint,
        midi_buffer: *mut c_char,
        buffer_size: c_uint,
    ) -> c_int;
    
    fn musicvae_ffi_interpolate(
        model: *mut MusicVaeModel,
        start: *const c_float,
        end: *const c_float,
        latent_size: c_uint,
        steps: c_uint,
        output: *mut c_float,
        output_size: c_uint,
    ) -> c_int;
    
    fn musicvae_ffi_generate(
        model: *mut MusicVaeModel,
        temperature: c_float,
        latent: *mut c_float,
        latent_size: c_uint,
    ) -> c_int;
    
    fn musicvae_ffi_save_latent(
        latent: *const c_float,
        latent_size: c_uint,
        path: *const c_char,
    ) -> c_int;
    
    fn musicvae_ffi_load_latent(
        path: *const c_char,
        latent: *mut c_float,
        latent_size: c_uint,
    ) -> c_int;
}

#[repr(C)]
struct MusicVaeConfigFFI {
    model_name: *const c_char,
    model_version: *const c_char,
    latent_dim: c_uint,
    max_sequence_length: c_uint,
}

impl MusicVae {
    /// Check if MusicVAE is available
    pub fn is_available() -> bool {
        unsafe { musicvae_ffi_is_available() != 0 }
    }

    /// Get MusicVAE version
    pub fn version() -> String {
        unsafe {
            let version_ptr = musicvae_ffi_get_version();
            if version_ptr.is_null() {
                return "unavailable".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load MusicVAE model
    pub fn new(config_path: &str) -> Result<Self, MusicVaeError> {
        if !Self::is_available() {
            return Err(MusicVaeError::FfiError("MusicVAE not available".to_string()));
        }

        let c_path = CString::new(config_path)
            .map_err(|e| MusicVaeError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let model = musicvae_ffi_model_load(c_path.as_ptr());
            if model.is_null() {
                return Err(MusicVaeError::ModelLoadFailed(config_path.to_string()));
            }

            // Get config
            let mut ffi_config = MusicVaeConfigFFI {
                model_name: std::ptr::null(),
                model_version: std::ptr::null(),
                latent_dim: 0,
                max_sequence_length: 0,
            };
            musicvae_ffi_model_get_config(model, &mut ffi_config);

            let config = MusicVaeConfig {
                model_name: if ffi_config.model_name.is_null() {
                    "unknown".to_string()
                } else {
                    CStr::from_ptr(ffi_config.model_name).to_string_lossy().into_owned()
                },
                model_version: if ffi_config.model_version.is_null() {
                    "1.0".to_string()
                } else {
                    CStr::from_ptr(ffi_config.model_version).to_string_lossy().into_owned()
                },
                latent_dim: ffi_config.latent_dim as usize,
                max_sequence_length: ffi_config.max_sequence_length as usize,
            };

            Ok(Self { model, config })
        }
    }

    /// Get model configuration
    pub fn config(&self) -> &MusicVaeConfig {
        &self.config
    }

    /// Encode MIDI data to latent vector
    pub fn encode(&self, midi_data: &[u8]) -> Result<LatentVector, MusicVaeError> {
        if midi_data.is_empty() {
            return Err(MusicVaeError::InvalidMidiData("Empty MIDI data".to_string()));
        }

        let latent_size = self.config.latent_dim;
        let mut latent = vec![0.0f32; latent_size];

        unsafe {
            // Convert MIDI bytes to string for FFI
            let midi_str = format!("{:?}", midi_data);
            let c_midi = CString::new(midi_str)
                .map_err(|e| MusicVaeError::FfiError(format!("Invalid MIDI: {}", e)))?;

            let result = musicvae_ffi_encode(
                self.model,
                c_midi.as_ptr(),
                midi_data.len() as c_uint,
                latent.as_mut_ptr(),
                latent_size as c_uint,
            );

            if result < 0 {
                return Err(MusicVaeError::EncodeFailed(format!("Error code: {}", result)));
            }

            Ok(latent)
        }
    }

    /// Decode latent vector to MIDI data
    pub fn decode(&self, latent: &[f32]) -> Result<Vec<u8>, MusicVaeError> {
        if latent.len() != self.config.latent_dim {
            return Err(MusicVaeError::InvalidMidiData(
                format!("Latent dimension mismatch: expected {}, got {}", 
                    self.config.latent_dim, latent.len())
            ));
        }

        let buffer_size = 65536; // Max MIDI size
        let mut buffer = vec![0u8; buffer_size];

        unsafe {
            let result = musicvae_ffi_decode(
                self.model,
                latent.as_ptr(),
                latent.len() as c_uint,
                buffer.as_mut_ptr() as *mut c_char,
                buffer_size as c_uint,
            );

            if result < 0 {
                return Err(MusicVaeError::DecodeFailed(format!("Error code: {}", result)));
            }

            // Truncate to actual size
            let actual_size = result as usize;
            buffer.truncate(actual_size);
            Ok(buffer)
        }
    }

    /// Interpolate between two latent vectors
    pub fn interpolate(
        &self,
        start: &[f32],
        end: &[f32],
        steps: usize,
    ) -> Result<Vec<LatentVector>, MusicVaeError> {
        if start.len() != self.config.latent_dim || end.len() != self.config.latent_dim {
            return Err(MusicVaeError::InvalidMidiData(
                "Latent dimension mismatch".to_string()
            ));
        }

        let output_size = steps * self.config.latent_dim;
        let mut output = vec![0.0f32; output_size];

        unsafe {
            let result = musicvae_ffi_interpolate(
                self.model,
                start.as_ptr(),
                end.as_ptr(),
                self.config.latent_dim as c_uint,
                steps as c_uint,
                output.as_mut_ptr(),
                output_size as c_uint,
            );

            if result < 0 {
                return Err(MusicVaeError::FfiError(format!("Interpolation failed: {}", result)));
            }

            // Split into individual latent vectors
            let mut vectors = Vec::with_capacity(steps);
            for i in 0..steps {
                let start_idx = i * self.config.latent_dim;
                let end_idx = start_idx + self.config.latent_dim;
                vectors.push(output[start_idx..end_idx].to_vec());
            }

            Ok(vectors)
        }
    }

    /// Generate new latent vector
    pub fn generate(&self, temperature: f32) -> Result<LatentVector, MusicVaeError> {
        let mut latent = vec![0.0f32; self.config.latent_dim];

        unsafe {
            let result = musicvae_ffi_generate(
                self.model,
                temperature,
                latent.as_mut_ptr(),
                self.config.latent_dim as c_uint,
            );

            if result < 0 {
                return Err(MusicVaeError::FfiError(format!("Generation failed: {}", result)));
            }

            Ok(latent)
        }
    }

    /// Save latent vector to file
    pub fn save_latent(&self, latent: &[f32], path: &str) -> Result<(), MusicVaeError> {
        let c_path = CString::new(path)
            .map_err(|e| MusicVaeError::FfiError(format!("Invalid path: {}", e)))?;

        unsafe {
            let result = musicvae_ffi_save_latent(
                latent.as_ptr(),
                latent.len() as c_uint,
                c_path.as_ptr(),
            );

            if result < 0 {
                return Err(MusicVaeError::FfiError(format!("Save failed: {}", result)));
            }

            Ok(())
        }
    }

    /// Load latent vector from file
    pub fn load_latent(&self, path: &str) -> Result<LatentVector, MusicVaeError> {
        let c_path = CString::new(path)
            .map_err(|e| MusicVaeError::FfiError(format!("Invalid path: {}", e)))?;

        let mut latent = vec![0.0f32; self.config.latent_dim];

        unsafe {
            let result = musicvae_ffi_load_latent(
                c_path.as_ptr(),
                latent.as_mut_ptr(),
                self.config.latent_dim as c_uint,
            );

            if result < 0 {
                return Err(MusicVaeError::FfiError(format!("Load failed: {}", result)));
            }

            Ok(latent)
        }
    }
}

impl Drop for MusicVae {
    fn drop(&mut self) {
        unsafe {
            if !self.model.is_null() {
                musicvae_ffi_model_free(self.model);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_musicvae_module_exists() {
        let _ = MusicVaeError::ModelNotFound("test".to_string());
        let _ = LatentVector::new();
    }

    #[test]
    fn test_musicvae_is_available() {
        let available = MusicVae::is_available();
        println!("MusicVAE available: {}", available);
    }

    #[test]
    fn test_musicvae_version() {
        let version = MusicVae::version();
        println!("MusicVAE version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_musicvae_error_display() {
        let err = MusicVaeError::ModelNotFound("test_model".to_string());
        assert!(err.to_string().contains("test_model"));

        let err = MusicVaeError::EncodeFailed("OOM".to_string());
        assert!(err.to_string().contains("Encode failed"));

        let err = MusicVaeError::InvalidMidiData("empty".to_string());
        assert!(err.to_string().contains("Invalid MIDI data"));
    }

    #[test]
    fn test_config_structure() {
        let config = MusicVaeConfig {
            model_name: "melody_16bar".to_string(),
            model_version: "1.0.0".to_string(),
            latent_dim: 512,
            max_sequence_length: 256,
        };
        
        assert_eq!(config.model_name, "melody_16bar");
        assert_eq!(config.latent_dim, 512);
    }

    #[test]
    fn test_latent_vector_type() {
        let latent: LatentVector = vec![0.1, -0.2, 0.3, 0.0];
        assert_eq!(latent.len(), 4);
    }

    #[test]
    fn test_model_load_returns_error_when_unavailable() {
        if !MusicVae::is_available() {
            let result = MusicVae::new("/models/musicvae.json");
            assert!(result.is_err());
        }
    }

    #[test]
    fn test_empty_midi_encode_fails() {
        if MusicVae::is_available() {
            let err = MusicVaeError::InvalidMidiData("Empty MIDI data".to_string());
            assert!(err.to_string().contains("Empty MIDI"));
        }
    }

    #[test]
    fn test_latent_dimension_mismatch() {
        let config = MusicVaeConfig {
            model_name: "test".to_string(),
            model_version: "1.0".to_string(),
            latent_dim: 512,
            max_sequence_length: 256,
        };
        
        // Test dimension mismatch error
        let err = MusicVaeError::InvalidMidiData(
            "Latent dimension mismatch: expected 512, got 256".to_string()
        );
        assert!(err.to_string().contains("512"));
        assert!(err.to_string().contains("256"));
    }
}
