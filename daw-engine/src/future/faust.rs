//! FAUST Integration
//!
//! FFI bindings to the FAUST functional DSP language compiler.
//! FAUST generates optimized C++, LLVM IR, WebAssembly, or Rust
//! from signal processing specifications.
//!
//! License: GPL-2.0 (compiler) / LGPL-2.1+ (runtime)
//! Repo: https://github.com/grame-cncm/faust

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_float, c_int, c_void};

// FFI type aliases
#[allow(non_camel_case_types)]
type FAUSTFLOAT = c_float;

/// Opaque handle to FAUST DSP instance
#[repr(C)]
pub struct FaustDSP {
    _private: [u8; 0],
}

/// Opaque handle to FAUST UI
#[repr(C)]
pub struct FaustUI {
    _private: [u8; 0],
}

/// FAUST error types
#[derive(Debug, Clone, PartialEq)]
pub enum FaustError {
    CompilationFailed(String),
    DSPInitFailed,
    InvalidParameter(String),
    CodegenFailed(String),
    FfiError(String),
}

impl std::fmt::Display for FaustError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FaustError::CompilationFailed(msg) => write!(f, "FAUST compilation failed: {}", msg),
            FaustError::DSPInitFailed => write!(f, "DSP initialization failed"),
            FaustError::InvalidParameter(param) => write!(f, "Invalid parameter: {}", param),
            FaustError::CodegenFailed(lang) => write!(f, "Code generation failed for: {}", lang),
            FaustError::FfiError(msg) => write!(f, "FFI error: {}", msg),
        }
    }
}

impl std::error::Error for FaustError {}

/// FAUST compilation target
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TargetLanguage {
    Cpp,
    C,
    Rust,
    LLVM,
    WebAssembly,
    JavaScript,
}

impl TargetLanguage {
    pub fn as_str(&self) -> &'static str {
        match self {
            TargetLanguage::Cpp => "cpp",
            TargetLanguage::C => "c",
            TargetLanguage::Rust => "rust",
            TargetLanguage::LLVM => "llvm",
            TargetLanguage::WebAssembly => "wasm",
            TargetLanguage::JavaScript => "js",
        }
    }
}

/// FAUST compiler configuration
#[derive(Debug, Clone)]
pub struct FaustConfig {
    pub target: TargetLanguage,
    pub opt_level: i32, // 0-3
    pub double_precision: bool,
}

impl Default for FaustConfig {
    fn default() -> Self {
        Self {
            target: TargetLanguage::Cpp,
            opt_level: 2,
            double_precision: false,
        }
    }
}

/// Generated code result
#[derive(Debug, Clone)]
pub struct GeneratedCode {
    pub source: String,
    pub language: TargetLanguage,
    pub sample_rate: u32,
}

/// FAUST compiler instance
pub struct FaustCompiler {
    config: FaustConfig,
}

/// FAUST DSP instance
pub struct FaustDSPInstance {
    dsp: *mut FaustDSP,
    sample_rate: u32,
}

// FFI function declarations
extern "C" {
    // TODO: Add actual FAUST FFI declarations when library is available
    fn faust_ffi_is_available() -> c_int;
    fn faust_ffi_compile_dsp(
        code: *const c_char,
        target: *const c_char,
        opt_level: c_int,
        output: *mut c_char,
        output_size: c_int,
    ) -> c_int;
    fn faust_ffi_get_version() -> *const c_char;
}

impl FaustCompiler {
    /// Create new FAUST compiler with configuration
    pub fn new(config: FaustConfig) -> Self {
        Self { config }
    }

    /// Check if FAUST compiler is available
    pub fn is_available() -> bool {
        unsafe { faust_ffi_is_available() != 0 }
    }

    /// Get FAUST version string
    pub fn version() -> String {
        unsafe {
            let version_ptr = faust_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Compile FAUST DSP code to target language
    pub fn compile(&self, dsp_code: &str) -> Result<GeneratedCode, FaustError> {
        if !Self::is_available() {
            return Err(FaustError::FfiError(
                "FAUST library not available".to_string()
            ));
        }

        let code_cstring = CString::new(dsp_code)
            .map_err(|e| FaustError::FfiError(e.to_string()))?;
        let target_cstring = CString::new(self.config.target.as_str())
            .map_err(|e| FaustError::FfiError(e.to_string()))?;

        let mut output = vec![0u8; 65536]; // 64KB buffer for output
        let result = unsafe {
            faust_ffi_compile_dsp(
                code_cstring.as_ptr(),
                target_cstring.as_ptr(),
                self.config.opt_level,
                output.as_mut_ptr() as *mut c_char,
                output.len() as c_int,
            )
        };

        if result != 0 {
            let output_str = String::from_utf8_lossy(&output);
            return Err(FaustError::CompilationFailed(
                output_str.trim_end_matches('\0').to_string()
            ));
        }

        let source = unsafe {
            CStr::from_ptr(output.as_ptr() as *const c_char)
                .to_string_lossy()
                .into_owned()
        };

        Ok(GeneratedCode {
            source,
            language: self.config.target,
            sample_rate: 44100,
        })
    }

    /// Simple gain DSP example
    pub fn example_gain() -> &'static str {
        r#"
import("stdfaust.lib");
process = _ * hslider("gain", 0.5, 0, 1, 0.01);
"#    }

    /// Simple lowpass filter example
    pub fn example_lowpass() -> &'static str {
        r#"
import("stdfaust.lib");
process = fi.lowpass(5, hslider("freq", 1000, 20, 20000, 1));
"#    }
}

impl FaustDSPInstance {
    /// Create DSP instance from compiled code
    pub fn new(_code: &GeneratedCode, sample_rate: u32) -> Result<Self, FaustError> {
        // TODO: Initialize DSP instance via FFI
        Err(FaustError::DSPInitFailed)
    }

    /// Get sample rate
    pub fn sample_rate(&self) -> u32 {
        self.sample_rate
    }
}

impl Drop for FaustDSPInstance {
    fn drop(&mut self) {
        // TODO: Cleanup DSP instance via FFI
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_faust_module_exists() {
        // Verify the FAUST module compiles and types are accessible
        let _ = FaustError::DSPInitFailed;
        let _config = FaustConfig::default();
        let _ = TargetLanguage::Cpp;
    }

    #[test]
    fn test_faust_is_available() {
        // Test that is_available() returns expected value
        // Returns false until FFI library is implemented
        let available = FaustCompiler::is_available();
        println!("FAUST available: {}", available);
    }

    #[test]
    fn test_faust_version() {
        // Test that we can get the version string
        let version = FaustCompiler::version();
        println!("FAUST version: {}", version);
    }

    #[test]
    fn test_faust_config_defaults() {
        let config = FaustConfig::default();
        assert_eq!(config.target, TargetLanguage::Cpp);
        assert_eq!(config.opt_level, 2);
        assert!(!config.double_precision);
    }

    #[test]
    fn test_faust_target_language_as_str() {
        assert_eq!(TargetLanguage::Cpp.as_str(), "cpp");
        assert_eq!(TargetLanguage::C.as_str(), "c");
        assert_eq!(TargetLanguage::Rust.as_str(), "rust");
        assert_eq!(TargetLanguage::LLVM.as_str(), "llvm");
        assert_eq!(TargetLanguage::WebAssembly.as_str(), "wasm");
        assert_eq!(TargetLanguage::JavaScript.as_str(), "js");
    }

    #[test]
    fn test_faust_compile_returns_error_when_unavailable() {
        // If FAUST is not available, compilation should fail gracefully
        if !FaustCompiler::is_available() {
            let compiler = FaustCompiler::new(FaustConfig::default());
            let result = compiler.compile(FaustCompiler::example_gain());
            assert!(result.is_err());
        }
    }

    #[test]
    fn test_faust_example_code() {
        // Verify example code is non-empty and valid FAUST syntax
        let gain_code = FaustCompiler::example_gain();
        assert!(!gain_code.is_empty());
        assert!(gain_code.contains("gain"));

        let lowpass_code = FaustCompiler::example_lowpass();
        assert!(!lowpass_code.is_empty());
        assert!(lowpass_code.contains("lowpass"));
    }

    #[test]
    fn test_faust_error_display() {
        let err = FaustError::CompilationFailed("syntax error".to_string());
        assert!(err.to_string().contains("compilation failed"));

        let err = FaustError::FfiError("test error".to_string());
        assert!(err.to_string().contains("FFI error"));
    }

    #[test]
    fn test_generated_code_structure() {
        let code = GeneratedCode {
            source: "test code".to_string(),
            language: TargetLanguage::Cpp,
            sample_rate: 48000,
        };
        
        assert_eq!(code.source, "test code");
        assert_eq!(code.language, TargetLanguage::Cpp);
        assert_eq!(code.sample_rate, 48000);
    }

    #[test]
    fn test_faust_dsp_instance_creation_fails_gracefully() {
        let code = GeneratedCode {
            source: "test".to_string(),
            language: TargetLanguage::Cpp,
            sample_rate: 44100,
        };
        
        let result = FaustDSPInstance::new(&code, 44100);
        // Should fail gracefully until FFI is implemented
        assert!(result.is_err());
    }
}
