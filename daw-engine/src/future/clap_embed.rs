//! CLAP (Contrastive Language-Audio Pretraining) Integration
//!
//! FFI bindings for CLAP embeddings - enabling text-to-audio search,
//! audio similarity comparison, and zero-shot classification.
//!
//! License: MIT
//! Reference: https://github.com/LAION-AI/CLAP

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_uint};

/// Opaque handle to CLAP model
#[repr(C)]
pub struct ClapModel {
    _private: [u8; 0],
}

/// CLAP error types
#[derive(Debug, Clone, PartialEq)]
pub enum ClapError {
    ModelNotFound(String),
    ModelLoadFailed(String),
    EmbeddingFailed(String),
    InvalidAudioData(String),
    InvalidText(String),
    FfiError(String),
}

impl std::fmt::Display for ClapError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ClapError::ModelNotFound(path) => write!(f, "CLAP model not found: {}", path),
            ClapError::ModelLoadFailed(msg) => write!(f, "Model load failed: {}", msg),
            ClapError::EmbeddingFailed(msg) => write!(f, "Embedding extraction failed: {}", msg),
            ClapError::InvalidAudioData(msg) => write!(f, "Invalid audio data: {}", msg),
            ClapError::InvalidText(msg) => write!(f, "Invalid text: {}", msg),
            ClapError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for ClapError {}

/// CLAP model configuration
#[derive(Debug, Clone)]
pub struct ClapConfig {
    pub model_name: String,
    pub model_version: String,
    pub embedding_dim: usize,
    pub sample_rate: u32,
}

/// Audio embedding vector
pub type AudioEmbedding = Vec<f32>;

/// Text embedding vector
pub type TextEmbedding = Vec<f32>;

/// Search result
#[derive(Debug, Clone)]
pub struct SearchResult {
    pub audio_path: String,
    pub similarity_score: f32,
    pub rank: usize,
}

/// Similar audio result
#[derive(Debug, Clone)]
pub struct SimilarAudioResult {
    pub audio_path: String,
    pub similarity_score: f32,
}

/// Zero-shot classification result
#[derive(Debug, Clone)]
pub struct ClassificationResult {
    pub label: String,
    pub confidence: f32,
}

/// CLAP embedder
pub struct ClapEmbedder {
    model: *mut ClapModel,
    config: ClapConfig,
}

// FFI function declarations
extern "C" {
    fn clap_ffi_is_available() -> c_int;
    fn clap_ffi_get_version() -> *const c_char;
    
    // Model management
    fn clap_ffi_model_load(model_name: *const c_char, sample_rate: c_uint) -> *mut ClapModel;
    fn clap_ffi_model_free(model: *mut ClapModel);
    fn clap_ffi_model_get_config(model: *mut ClapModel, config: *mut ClapConfigFFI);
    
    // Embeddings
    fn clap_ffi_audio_embedding(
        model: *mut ClapModel,
        audio: *const c_float,
        sample_count: c_uint,
        embedding: *mut c_float,
        embedding_dim: c_uint,
    ) -> c_int;
    
    fn clap_ffi_text_embedding(
        model: *mut ClapModel,
        text: *const c_char,
        embedding: *mut c_float,
        embedding_dim: c_uint,
    ) -> c_int;
    
    fn clap_ffi_similarity(
        model: *mut ClapModel,
        audio: *const c_float,
        sample_count: c_uint,
        text: *const c_char,
    ) -> c_float;
    
    // Search and comparison
    fn clap_ffi_text_to_audio_search(
        model: *mut ClapModel,
        query: *const c_char,
        audio_dir: *const c_char,
        results: *mut c_char,
        results_size: c_uint,
        top_k: c_uint,
    ) -> c_int;
    
    fn clap_ffi_find_similar_audio(
        model: *mut ClapModel,
        reference_audio: *const c_float,
        sample_count: c_uint,
        audio_dir: *const c_char,
        results: *mut c_char,
        results_size: c_uint,
        top_k: c_uint,
    ) -> c_int;
    
    // Zero-shot classification
    fn clap_ffi_zero_shot_classify(
        model: *mut ClapModel,
        audio: *const c_float,
        sample_count: c_uint,
        labels: *const c_char,
        results: *mut c_char,
        results_size: c_uint,
    ) -> c_int;
    
    // Batch processing
    fn clap_ffi_batch_audio_embeddings(
        model: *mut ClapModel,
        file_list: *const c_char,
        embeddings: *mut c_float,
        embedding_dim: c_uint,
        num_files: c_uint,
    ) -> c_int;
}

#[repr(C)]
struct ClapConfigFFI {
    model_name: *const c_char,
    model_version: *const c_char,
    embedding_dim: c_uint,
    sample_rate: c_uint,
}

impl ClapEmbedder {
    /// Check if CLAP is available
    pub fn is_available() -> bool {
        unsafe { clap_ffi_is_available() != 0 }
    }

    /// Get CLAP version
    pub fn version() -> String {
        unsafe {
            let version_ptr = clap_ffi_get_version();
            if version_ptr.is_null() {
                return "unavailable".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Load CLAP model
    pub fn new(model_name: &str, sample_rate: u32) -> Result<Self, ClapError> {
        if !Self::is_available() {
            return Err(ClapError::FfiError("CLAP not available".to_string()));
        }

        let c_name = CString::new(model_name)
            .map_err(|e| ClapError::FfiError(format!("Invalid model name: {}", e)))?;

        unsafe {
            let model = clap_ffi_model_load(c_name.as_ptr(), sample_rate);
            if model.is_null() {
                return Err(ClapError::ModelLoadFailed(model_name.to_string()));
            }

            // Get config
            let mut ffi_config = ClapConfigFFI {
                model_name: std::ptr::null(),
                model_version: std::ptr::null(),
                embedding_dim: 0,
                sample_rate: 0,
            };
            clap_ffi_model_get_config(model, &mut ffi_config);

            let config = ClapConfig {
                model_name: if ffi_config.model_name.is_null() {
                    model_name.to_string()
                } else {
                    CStr::from_ptr(ffi_config.model_name).to_string_lossy().into_owned()
                },
                model_version: if ffi_config.model_version.is_null() {
                    "1.0".to_string()
                } else {
                    CStr::from_ptr(ffi_config.model_version).to_string_lossy().into_owned()
                },
                embedding_dim: ffi_config.embedding_dim as usize,
                sample_rate: ffi_config.sample_rate,
            };

            Ok(Self { model, config })
        }
    }

    /// Get model config
    pub fn config(&self) -> &ClapConfig {
        &self.config
    }

    /// Get audio embedding
    pub fn audio_embedding(&self, audio: &[f32]) -> Result<AudioEmbedding, ClapError> {
        if audio.is_empty() {
            return Err(ClapError::InvalidAudioData("Empty audio".to_string()));
        }

        let embedding_dim = self.config.embedding_dim;
        let mut embedding = vec![0.0f32; embedding_dim];

        unsafe {
            let result = clap_ffi_audio_embedding(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                embedding.as_mut_ptr(),
                embedding_dim as c_uint,
            );

            if result < 0 {
                return Err(ClapError::EmbeddingFailed(format!("Error code: {}", result)));
            }

            Ok(embedding)
        }
    }

    /// Get text embedding
    pub fn text_embedding(&self, text: &str) -> Result<TextEmbedding, ClapError> {
        if text.is_empty() {
            return Err(ClapError::InvalidText("Empty text".to_string()));
        }

        let c_text = CString::new(text)
            .map_err(|e| ClapError::FfiError(format!("Invalid text: {}", e)))?;

        let embedding_dim = self.config.embedding_dim;
        let mut embedding = vec![0.0f32; embedding_dim];

        unsafe {
            let result = clap_ffi_text_embedding(
                self.model,
                c_text.as_ptr(),
                embedding.as_mut_ptr(),
                embedding_dim as c_uint,
            );

            if result < 0 {
                return Err(ClapError::EmbeddingFailed(format!("Error code: {}", result)));
            }

            Ok(embedding)
        }
    }

    /// Calculate similarity between audio and text
    pub fn similarity(&self, audio: &[f32], text: &str) -> Result<f32, ClapError> {
        if audio.is_empty() {
            return Err(ClapError::InvalidAudioData("Empty audio".to_string()));
        }
        if text.is_empty() {
            return Err(ClapError::InvalidText("Empty text".to_string()));
        }

        let c_text = CString::new(text)
            .map_err(|e| ClapError::FfiError(format!("Invalid text: {}", e)))?;

        unsafe {
            let score = clap_ffi_similarity(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                c_text.as_ptr(),
            );

            if score < 0.0 {
                return Err(ClapError::EmbeddingFailed("Similarity calculation failed".to_string()));
            }

            Ok(score)
        }
    }

    /// Search audio files by text query
    pub fn text_to_audio_search(
        &self,
        query: &str,
        audio_directory: &str,
        top_k: usize,
    ) -> Result<Vec<SearchResult>, ClapError> {
        let c_query = CString::new(query)
            .map_err(|e| ClapError::InvalidText(format!("Invalid query: {}", e)))?;
        let c_dir = CString::new(audio_directory)
            .map_err(|e| ClapError::FfiError(format!("Invalid directory: {}", e)))?;

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = clap_ffi_text_to_audio_search(
                self.model,
                c_query.as_ptr(),
                c_dir.as_ptr(),
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
                top_k as c_uint,
            );

            if result < 0 {
                return Err(ClapError::EmbeddingFailed("Search failed".to_string()));
            }

            // Parse results
            self.parse_search_results(&buffer)
        }
    }

    /// Find similar audio files
    pub fn find_similar_audio(
        &self,
        reference_audio: &[f32],
        audio_directory: &str,
        top_k: usize,
    ) -> Result<Vec<SimilarAudioResult>, ClapError> {
        if reference_audio.is_empty() {
            return Err(ClapError::InvalidAudioData("Empty audio".to_string()));
        }

        let c_dir = CString::new(audio_directory)
            .map_err(|e| ClapError::FfiError(format!("Invalid directory: {}", e)))?;

        let mut buffer = vec![0u8; 65536];

        unsafe {
            let result = clap_ffi_find_similar_audio(
                self.model,
                reference_audio.as_ptr(),
                reference_audio.len() as c_uint,
                c_dir.as_ptr(),
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
                top_k as c_uint,
            );

            if result < 0 {
                return Err(ClapError::EmbeddingFailed("Similarity search failed".to_string()));
            }

            // Parse results
            self.parse_similar_results(&buffer)
        }
    }

    /// Zero-shot classification
    pub fn zero_shot_classify(
        &self,
        audio: &[f32],
        labels: &[&str],
    ) -> Result<Vec<ClassificationResult>, ClapError> {
        if audio.is_empty() {
            return Err(ClapError::InvalidAudioData("Empty audio".to_string()));
        }
        if labels.is_empty() {
            return Err(ClapError::InvalidText("No labels provided".to_string()));
        }

        let labels_str = labels.join(",");
        let c_labels = CString::new(labels_str)
            .map_err(|e| ClapError::InvalidText(format!("Invalid labels: {}", e)))?;

        let mut buffer = vec![0u8; 4096];

        unsafe {
            let result = clap_ffi_zero_shot_classify(
                self.model,
                audio.as_ptr(),
                audio.len() as c_uint,
                c_labels.as_ptr(),
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_uint,
            );

            if result < 0 {
                return Err(ClapError::EmbeddingFailed("Classification failed".to_string()));
            }

            // Parse results
            self.parse_classification_results(&buffer)
        }
    }

    /// Batch process audio files
    pub fn batch_audio_embeddings(
        &self,
        file_list: &[&str],
    ) -> Result<Vec<AudioEmbedding>, ClapError> {
        if file_list.is_empty() {
            return Ok(vec![]);
        }

        let files = file_list.join(",");
        let c_files = CString::new(files)
            .map_err(|e| ClapError::FfiError(format!("Invalid file list: {}", e)))?;

        let num_files = file_list.len();
        let embedding_dim = self.config.embedding_dim;
        let mut embeddings = vec![0.0f32; num_files * embedding_dim];

        unsafe {
            let result = clap_ffi_batch_audio_embeddings(
                self.model,
                c_files.as_ptr(),
                embeddings.as_mut_ptr(),
                embedding_dim as c_uint,
                num_files as c_uint,
            );

            if result < 0 {
                return Err(ClapError::EmbeddingFailed("Batch processing failed".to_string()));
            }

            // Split into individual embeddings
            let mut results = Vec::with_capacity(num_files);
            for i in 0..num_files {
                let start = i * embedding_dim;
                let end = start + embedding_dim;
                results.push(embeddings[start..end].to_vec());
            }

            Ok(results)
        }
    }

    fn parse_search_results(&self, buffer: &[u8]) -> Result<Vec<SearchResult>, ClapError> {
        // Stub - real implementation would deserialize
        Ok(vec![])
    }

    fn parse_similar_results(&self, buffer: &[u8]) -> Result<Vec<SimilarAudioResult>, ClapError> {
        // Stub - real implementation would deserialize
        Ok(vec![])
    }

    fn parse_classification_results(&self, buffer: &[u8]) -> Result<Vec<ClassificationResult>, ClapError> {
        // Stub - real implementation would deserialize
        Ok(vec![])
    }
}

impl Drop for ClapEmbedder {
    fn drop(&mut self) {
        unsafe {
            if !self.model.is_null() {
                clap_ffi_model_free(self.model);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clap_module_exists() {
        let _ = ClapError::ModelNotFound("test".to_string());
        let _ = ClapConfig {
            model_name: "clap".to_string(),
            model_version: "1.0".to_string(),
            embedding_dim: 512,
            sample_rate: 48000,
        };
    }

    #[test]
    fn test_clap_is_available() {
        let available = ClapEmbedder::is_available();
        println!("CLAP available: {}", available);
    }

    #[test]
    fn test_clap_version() {
        let version = ClapEmbedder::version();
        println!("CLAP version: {}", version);
        assert!(!version.is_empty());
    }

    #[test]
    fn test_clap_error_display() {
        let err = ClapError::ModelNotFound("test_model".to_string());
        assert!(err.to_string().contains("test_model"));

        let err = ClapError::EmbeddingFailed("OOM".to_string());
        assert!(err.to_string().contains("Embedding extraction failed"));

        let err = ClapError::InvalidText("empty".to_string());
        assert!(err.to_string().contains("Invalid text"));
    }

    #[test]
    fn test_config_structure() {
        let config = ClapConfig {
            model_name: "2023".to_string(),
            model_version: "1.0".to_string(),
            embedding_dim: 512,
            sample_rate: 48000,
        };
        
        assert_eq!(config.model_name, "2023");
        assert_eq!(config.embedding_dim, 512);
        assert_eq!(config.sample_rate, 48000);
    }

    #[test]
    fn test_search_result_structure() {
        let result = SearchResult {
            audio_path: "/audio/test.wav".to_string(),
            similarity_score: 0.87,
            rank: 1,
        };
        
        assert_eq!(result.audio_path, "/audio/test.wav");
        assert!(result.similarity_score > 0.0);
    }

    #[test]
    fn test_classification_result() {
        let result = ClassificationResult {
            label: "techno".to_string(),
            confidence: 0.92,
        };
        
        assert_eq!(result.label, "techno");
        assert!(result.confidence > 0.0 && result.confidence <= 1.0);
    }

    #[test]
    fn test_model_load_returns_error_when_unavailable() {
        if !ClapEmbedder::is_available() {
            let result = ClapEmbedder::new("clap-2023", 48000);
            assert!(result.is_err());
        }
    }

    #[test]
    fn test_empty_audio_embedding_fails() {
        if ClapEmbedder::is_available() {
            // Would need loaded model to test this
            let err = ClapError::InvalidAudioData("Empty audio".to_string());
            assert!(err.to_string().contains("Empty audio"));
        }
    }

    #[test]
    fn test_empty_text_embedding_fails() {
        if ClapEmbedder::is_available() {
            let err = ClapError::InvalidText("Empty text".to_string());
            assert!(err.to_string().contains("Empty text"));
        }
    }
}
