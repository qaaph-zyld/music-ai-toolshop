use std::ffi::{c_char, c_int, c_float, CStr, CString};
use std::os::raw::c_void;
use std::ptr;

// Opaque C handle for FFI
#[repr(C)]
pub struct DexedHandle {
    _private: [u8; 0],
}

// Error types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DexedError {
    NotAvailable,
    InvalidConfig,
    NullPointer,
    ProcessingFailed,
    InvalidAlgorithm,
}

impl std::fmt::Display for DexedError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NotAvailable => write!(f, "Dexed not available - library not linked"),
            Self::InvalidConfig => write!(f, "Invalid Dexed configuration"),
            Self::NullPointer => write!(f, "Null pointer provided"),
            Self::ProcessingFailed => write!(f, "Audio processing failed"),
            Self::InvalidAlgorithm => write!(f, "Invalid FM algorithm (must be 0-31)"),
        }
    }
}

impl std::error::Error for DexedError {}

// FM Algorithm type (0-31, matching Yamaha DX7)
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum FmAlgorithm {
    Algorithm0, Algorithm1, Algorithm2, Algorithm3,
    Algorithm4, Algorithm5, Algorithm6, Algorithm7,
    Algorithm8, Algorithm9, Algorithm10, Algorithm11,
    Algorithm12, Algorithm13, Algorithm14, Algorithm15,
    Algorithm16, Algorithm17, Algorithm18, Algorithm19,
    Algorithm20, Algorithm21, Algorithm22, Algorithm23,
    Algorithm24, Algorithm25, Algorithm26, Algorithm27,
    Algorithm28, Algorithm29, Algorithm30, Algorithm31,
}

impl FmAlgorithm {
    pub fn to_u8(&self) -> u8 {
        *self as u8
    }
    
    pub fn from_u8(value: u8) -> Result<Self, DexedError> {
        if value <= 31 {
            Ok(unsafe { std::mem::transmute(value) })
        } else {
            Err(DexedError::InvalidAlgorithm)
        }
    }
}

impl Default for FmAlgorithm {
    fn default() -> Self {
        FmAlgorithm::Algorithm0
    }
}

// Operator configuration (6 operators like DX7)
#[derive(Debug, Clone, Copy)]
pub struct OperatorConfig {
    pub output_level: f32,      // 0.0 - 1.0
    pub coarse: u8,             // 0.5 - 32 (multiplier)
    pub fine: f32,              // 0.0 - 1.0 (detune)
    pub attack_rate: u8,        // 0 - 99
    pub decay_rate: u8,         // 0 - 99
    pub sustain_level: u8,      // 0 - 99
    pub release_rate: u8,       // 0 - 99
    pub eg_bias: bool,          // Envelope Generator bias
    pub key_velocity: bool,     // Keyboard velocity sensitivity
    pub keyboard_level_scaling: bool,
}

impl Default for OperatorConfig {
    fn default() -> Self {
        Self {
            output_level: 0.5,
            coarse: 1,
            fine: 0.0,
            attack_rate: 50,
            decay_rate: 50,
            sustain_level: 50,
            release_rate: 50,
            eg_bias: false,
            key_velocity: true,
            keyboard_level_scaling: false,
        }
    }
}

// Dexed configuration
#[derive(Debug, Clone)]
pub struct DexedConfig {
    pub sample_rate: u32,
    pub channels: u32,
    pub buffer_size: usize,
    pub algorithm: FmAlgorithm,
    pub operators: [OperatorConfig; 6],
    pub feedback: f32,           // 0.0 - 1.0
    pub lfo_rate: f32,          // 0.0 - 1.0
    pub lfo_depth: f32,         // 0.0 - 1.0
    pub transpose: i8,          // -24 to +24 semitones
}

impl Default for DexedConfig {
    fn default() -> Self {
        Self {
            sample_rate: 48000,
            channels: 2,
            buffer_size: 512,
            algorithm: FmAlgorithm::default(),
            operators: [OperatorConfig::default(); 6],
            feedback: 0.0,
            lfo_rate: 0.3,
            lfo_depth: 0.2,
            transpose: 0,
        }
    }
}

// Safe wrapper around FFI
#[derive(Debug)]
pub struct DexedInstance {
    handle: *mut DexedHandle,
    config: DexedConfig,
}

impl DexedInstance {
    pub fn new(config: DexedConfig) -> Result<Self, DexedError> {
        // Initially returns NotAvailable until library linked
        Err(DexedError::NotAvailable)
    }
    
    pub fn is_available(&self) -> bool {
        false
    }
    
    pub fn process(&mut self, _input: &[f32], _output: &mut [f32]) -> Result<(), DexedError> {
        Err(DexedError::NotAvailable)
    }
    
    pub fn get_version(&self) -> String {
        "not-available".to_string()
    }
    
    pub fn get_algorithm(&self) -> FmAlgorithm {
        self.config.algorithm
    }
    
    pub fn set_algorithm(&mut self, algorithm: FmAlgorithm) {
        self.config.algorithm = algorithm;
    }
    
    pub fn note_on(&mut self, _note: u8, _velocity: u8) -> Result<(), DexedError> {
        Err(DexedError::NotAvailable)
    }
    
    pub fn note_off(&mut self, _note: u8) -> Result<(), DexedError> {
        Err(DexedError::NotAvailable)
    }
}

impl Drop for DexedInstance {
    fn drop(&mut self) {
        if !self.handle.is_null() {
            // Call FFI cleanup when implemented
        }
    }
}

// FFI exports
#[no_mangle]
pub extern "C" fn daw_dexed_create(_config_ptr: *const DexedConfig) -> *mut DexedHandle {
    ptr::null_mut()
}

#[no_mangle]
pub extern "C" fn daw_dexed_free(_handle: *mut DexedHandle) {
}

#[no_mangle]
pub extern "C" fn daw_dexed_is_available() -> c_int {
    0
}

#[no_mangle]
pub extern "C" fn daw_dexed_get_version() -> *mut c_char {
    let c_str = CString::new("not-available").unwrap();
    c_str.into_raw()
}

#[no_mangle]
pub extern "C" fn daw_dexed_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe { let _ = CString::from_raw(s); }
    }
}

#[no_mangle]
pub extern "C" fn daw_dexed_process(
    _handle: *mut DexedHandle,
    _input: *const c_float,
    _output: *mut c_float,
    _samples: c_int
) -> c_int {
    -1
}

#[no_mangle]
pub extern "C" fn daw_dexed_note_on(_handle: *mut DexedHandle, _note: c_int, _velocity: c_int) -> c_int {
    -1
}

#[no_mangle]
pub extern "C" fn daw_dexed_note_off(_handle: *mut DexedHandle, _note: c_int) -> c_int {
    -1
}

#[no_mangle]
pub extern "C" fn daw_dexed_set_algorithm(_handle: *mut DexedHandle, _algorithm: c_int) -> c_int {
    -1
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dexed_creation() {
        let config = DexedConfig::default();
        let instance = DexedInstance::new(config);
        assert!(instance.is_err());
        assert_eq!(instance.unwrap_err(), DexedError::NotAvailable);
    }

    #[test]
    fn test_dexed_version() {
        let config = DexedConfig::default();
        // Can't create instance, so test the FFI function directly
        let version = unsafe {
            let ptr = daw_dexed_get_version();
            let c_str = CStr::from_ptr(ptr);
            let s = c_str.to_string_lossy().to_string();
            daw_dexed_free_string(ptr);
            s
        };
        assert_eq!(version, "not-available");
    }

    #[test]
    fn test_dexed_is_available() {
        let available = daw_dexed_is_available();
        assert_eq!(available, 0);
    }

    #[test]
    fn test_dexed_config_default() {
        let config = DexedConfig::default();
        assert_eq!(config.sample_rate, 48000);
        assert_eq!(config.channels, 2);
        assert_eq!(config.buffer_size, 512);
        assert_eq!(config.algorithm.to_u8(), 0);
        assert_eq!(config.operators.len(), 6);
        assert_eq!(config.feedback, 0.0);
    }

    #[test]
    fn test_dexed_config_custom() {
        let mut config = DexedConfig::default();
        config.sample_rate = 44100;
        config.channels = 1;
        config.algorithm = FmAlgorithm::Algorithm5;
        config.feedback = 0.5;
        
        assert_eq!(config.sample_rate, 44100);
        assert_eq!(config.channels, 1);
        assert_eq!(config.algorithm.to_u8(), 5);
        assert_eq!(config.feedback, 0.5);
    }

    #[test]
    fn test_fm_algorithm_conversion() {
        assert_eq!(FmAlgorithm::Algorithm0.to_u8(), 0);
        assert_eq!(FmAlgorithm::Algorithm31.to_u8(), 31);
        
        let alg = FmAlgorithm::from_u8(10).unwrap();
        assert_eq!(alg.to_u8(), 10);
        
        assert!(FmAlgorithm::from_u8(32).is_err());
        assert!(FmAlgorithm::from_u8(255).is_err());
    }

    #[test]
    fn test_operator_config_default() {
        let op = OperatorConfig::default();
        assert_eq!(op.output_level, 0.5);
        assert_eq!(op.coarse, 1);
        assert_eq!(op.attack_rate, 50);
        assert!(op.key_velocity);
        assert!(!op.eg_bias);
    }

    #[test]
    fn test_error_display() {
        let err = DexedError::NotAvailable;
        let msg = format!("{}", err);
        assert!(msg.contains("not available"));
        
        let err = DexedError::InvalidAlgorithm;
        let msg = format!("{}", err);
        assert!(msg.contains("algorithm"));
    }

    #[test]
    fn test_null_safety() {
        let result = unsafe { daw_dexed_create(ptr::null()) };
        assert!(result.is_null());
        
        // Should not crash with null handle
        let process_result = unsafe { daw_dexed_process(ptr::null_mut(), ptr::null(), ptr::null_mut(), 0) };
        assert_eq!(process_result, -1);
    }

    #[test]
    fn test_note_functions() {
        let handle = daw_dexed_create(ptr::null());
        
        let on_result = daw_dexed_note_on(handle, 60, 100);
        assert_eq!(on_result, -1);
        
        let off_result = daw_dexed_note_off(handle, 60);
        assert_eq!(off_result, -1);
        
        daw_dexed_free(handle);
    }

    #[test]
    fn test_algorithm_setting() {
        let handle = daw_dexed_create(ptr::null());
        
        let result = daw_dexed_set_algorithm(handle, 5);
        assert_eq!(result, -1);
        
        daw_dexed_free(handle);
    }
}
