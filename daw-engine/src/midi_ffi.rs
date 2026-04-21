//! MIDI Input FFI - Foreign Function Interface for MIDI device access
//!
//! Provides C-compatible FFI functions for enumerating, opening, and reading
//! from MIDI input devices from the JUCE UI layer.

use std::ffi::{c_char, CString};
use std::sync::{Arc, Mutex, RwLock};
use std::collections::HashMap;
use crate::midi_input::{MidiDeviceEnumerator, MidiDeviceInfo};
use crate::MidiMessage;

/// Maximum device name length (used in tests)
#[allow(unused)]
const MAX_DEVICE_NAME_LEN: usize = 256;
/// Maximum number of open devices
const MAX_OPEN_DEVICES: usize = 16;

/// Global device manager for FFI
static DEVICE_MANAGER: RwLock<Option<Arc<Mutex<MidiDeviceManager>>>> = RwLock::new(None);

/// MIDI device manager for FFI
struct MidiDeviceManager {
    /// Currently open devices
    open_devices: HashMap<usize, MidiDeviceHandle>,
    /// Next device ID
    next_device_id: usize,
    /// Cached device list
    cached_devices: Vec<MidiDeviceInfo>,
}

/// Handle to an open MIDI device
struct MidiDeviceHandle {
    _device_id: usize,
    _name: String,
    /// Message buffer for this device
    message_buffer: Arc<Mutex<Vec<MidiMessage>>>,
}

impl MidiDeviceManager {
    fn new() -> Self {
        Self {
            open_devices: HashMap::new(),
            next_device_id: 1,
            cached_devices: Vec::new(),
        }
    }
    
    /// Refresh the cached device list
    fn refresh_device_list(&mut self) {
        self.cached_devices = MidiDeviceEnumerator::list_input_devices();
    }
    
    /// Get device count
    fn device_count(&mut self) -> usize {
        self.refresh_device_list();
        self.cached_devices.len()
    }
    
    /// Get device name
    fn get_device_name(&mut self, index: usize) -> Option<String> {
        self.refresh_device_list();
        self.cached_devices.get(index).map(|d| d.name.clone())
    }
    
    /// Open a device (simulated - real implementation would use midir)
    fn open_device(&mut self, index: usize) -> Option<usize> {
        self.refresh_device_list();
        
        if index >= self.cached_devices.len() {
            return None;
        }
        
        if self.open_devices.len() >= MAX_OPEN_DEVICES {
            return None;
        }
        
        let device_info = &self.cached_devices[index];
        let device_id = self.next_device_id;
        self.next_device_id += 1;
        
        let handle = MidiDeviceHandle {
            _device_id: device_id,
            _name: device_info.name.clone(),
            message_buffer: Arc::new(Mutex::new(Vec::new())),
        };
        
        self.open_devices.insert(device_id, handle);
        Some(device_id)
    }
    
    /// Close a device
    fn close_device(&mut self, device_id: usize) -> bool {
        self.open_devices.remove(&device_id).is_some()
    }
    
    /// Read a message from device (simulated for testing)
    fn read_message(&self, device_id: usize) -> Option<MidiMessage> {
        self.open_devices.get(&device_id).and_then(|handle| {
            let mut buffer = handle.message_buffer.lock().ok()?;
            // For testing, we might inject test messages
            buffer.pop()
        })
    }
    
    /// Inject a test message (for testing purposes)
    fn inject_test_message(&self, device_id: usize, message: MidiMessage) -> bool {
        if let Some(handle) = self.open_devices.get(&device_id) {
            if let Ok(mut buffer) = handle.message_buffer.lock() {
                buffer.push(message);
                return true;
            }
        }
        false
    }
}

/// Initialize the device manager
fn get_manager() -> Option<Arc<Mutex<MidiDeviceManager>>> {
    if let Ok(guard) = DEVICE_MANAGER.read() {
        if let Some(manager) = guard.as_ref() {
            return Some(manager.clone());
        }
    }
    
    // Initialize if not exists
    if let Ok(mut guard) = DEVICE_MANAGER.write() {
        if guard.is_none() {
            *guard = Some(Arc::new(Mutex::new(MidiDeviceManager::new())));
        }
        guard.as_ref().cloned()
    } else {
        None
    }
}

/// Get the number of available MIDI input devices
/// 
/// # Safety
/// Safe to call from any thread. Returns 0 on error.
#[no_mangle]
pub extern "C" fn opendaw_midi_device_count() -> usize {
    if let Some(manager) = get_manager() {
        if let Ok(mut mgr) = manager.lock() {
            return mgr.device_count();
        }
    }
    0
}

/// Get the name of a MIDI device by index
/// 
/// # Arguments
/// * `index` - Device index (0 to device_count-1)
/// * `name_buffer` - Buffer to write name into
/// * `buffer_size` - Size of the buffer
/// 
/// # Returns
/// 0 on success, -1 on error
/// 
/// # Safety
/// Caller must ensure name_buffer is valid and buffer_size > 0
#[no_mangle]
pub extern "C" fn opendaw_midi_get_device_name(
    index: usize,
    name_buffer: *mut c_char,
    buffer_size: usize,
) -> i32 {
    if name_buffer.is_null() || buffer_size == 0 {
        return -1;
    }
    
    if let Some(manager) = get_manager() {
        if let Ok(mut mgr) = manager.lock() {
            if let Some(name) = mgr.get_device_name(index) {
                let c_name = CString::new(name).unwrap_or_default();
                let bytes = c_name.as_bytes_with_nul();
                let copy_len = bytes.len().min(buffer_size).saturating_sub(1);
                
                unsafe {
                    std::ptr::copy_nonoverlapping(
                        bytes.as_ptr() as *const c_char,
                        name_buffer,
                        copy_len,
                    );
                    *name_buffer.add(copy_len) = 0; // Null terminate
                }
                
                return 0;
            }
        }
    }
    
    // Write empty string on error
    unsafe { *name_buffer = 0; }
    -1
}

/// Open a MIDI device for input
/// 
/// # Arguments
/// * `index` - Device index
/// * `device_id` - Output: device handle ID
/// 
/// # Returns
/// 0 on success, -1 on error
/// 
/// # Safety
/// device_id must be a valid pointer
#[no_mangle]
pub extern "C" fn opendaw_midi_open_device(
    index: usize,
    device_id: *mut usize,
) -> i32 {
    if device_id.is_null() {
        return -1;
    }
    
    if let Some(manager) = get_manager() {
        if let Ok(mut mgr) = manager.lock() {
            if let Some(id) = mgr.open_device(index) {
                unsafe { *device_id = id; }
                return 0;
            }
        }
    }
    
    -1
}

/// Close a MIDI device
/// 
/// # Arguments
/// * `device_id` - Device handle ID from opendaw_midi_open_device
/// 
/// # Returns
/// 0 on success, -1 on error
#[no_mangle]
pub extern "C" fn opendaw_midi_close_device(device_id: usize) -> i32 {
    if device_id == 0 {
        return -1;
    }
    
    if let Some(manager) = get_manager() {
        if let Ok(mut mgr) = manager.lock() {
            if mgr.close_device(device_id) {
                return 0;
            }
        }
    }
    
    -1
}

/// Read a MIDI message from a device
/// 
/// # Arguments
/// * `device_id` - Device handle ID
/// * `status` - Output: MIDI status byte
/// * `data1` - Output: First data byte
/// * `data2` - Output: Second data byte
/// 
/// # Returns
/// 0 on success (message read), 1 on no message available, -1 on error
/// 
/// # Safety
/// All output pointers must be valid
#[no_mangle]
pub extern "C" fn opendaw_midi_read_message(
    device_id: usize,
    status: *mut u8,
    data1: *mut u8,
    data2: *mut u8,
) -> i32 {
    if device_id == 0 || status.is_null() || data1.is_null() || data2.is_null() {
        return -1;
    }
    
    if let Some(manager) = get_manager() {
        if let Ok(mgr) = manager.lock() {
            if let Some(msg) = mgr.read_message(device_id) {
                unsafe {
                    match msg {
                        MidiMessage::NoteOn { note, velocity, channel } => {
                            *status = 0x90 | (channel & 0x0F);
                            *data1 = note;
                            *data2 = velocity;
                        }
                        MidiMessage::NoteOff { note, velocity, channel } => {
                            *status = 0x80 | (channel & 0x0F);
                            *data1 = note;
                            *data2 = velocity;
                        }
                        MidiMessage::ControlChange { controller, value, channel } => {
                            *status = 0xB0 | (channel & 0x0F);
                            *data1 = controller;
                            *data2 = value;
                        }
                        _ => {
                            *status = 0;
                            *data1 = 0;
                            *data2 = 0;
                        }
                    }
                }
                return 0;
            } else {
                return 1; // No message available
            }
        }
    }
    
    -1
}

/// Inject a test message (for testing only)
/// 
/// # Safety
/// For testing purposes only
#[no_mangle]
pub extern "C" fn opendaw_midi_inject_test_message(
    device_id: usize,
    status: u8,
    data1: u8,
    data2: u8,
) -> i32 {
    if device_id == 0 {
        return -1;
    }
    
    let msg = if (status & 0xF0) == 0x90 {
        MidiMessage::note_on(data1, data2, status & 0x0F)
    } else if (status & 0xF0) == 0x80 {
        MidiMessage::note_off(data1, status & 0x0F)
    } else if (status & 0xF0) == 0xB0 {
        MidiMessage::control_change(data1, data2, status & 0x0F)
    } else {
        return -1;
    };
    
    if let Some(manager) = get_manager() {
        if let Ok(mgr) = manager.lock() {
            if mgr.inject_test_message(device_id, msg) {
                return 0;
            }
        }
    }
    
    -1
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::{CStr, CString};
    
    // TDD: Test 1 - FFI device count returns consistent value
    #[test]
    fn test_midi_ffi_device_count() {
        // Get count twice - should be consistent
        let count1 = unsafe { opendaw_midi_device_count() };
        let count2 = unsafe { opendaw_midi_device_count() };
        
        // Should return same count
        assert_eq!(count1, count2, "Device count should be consistent");
        
        // Count should be reasonable (0 or more devices)
        assert!(count1 < 100, "Device count should be reasonable");
    }
    
    // TDD: Test 2 - Get device name returns valid string
    #[test]
    fn test_midi_ffi_get_device_name() {
        let count = unsafe { opendaw_midi_device_count() };
        
        if count > 0 {
            let mut buffer = vec![0i8; MAX_DEVICE_NAME_LEN];
            let result = unsafe {
                opendaw_midi_get_device_name(0, buffer.as_mut_ptr(), buffer.len())
            };
            
            assert_eq!(result, 0, "Should succeed for valid device index");
            
            // Should have non-empty name
            let name = unsafe { CStr::from_ptr(buffer.as_ptr()) };
            assert!(!name.to_bytes().is_empty(), "Device name should not be empty");
        }
    }
    
    // TDD: Test 3 - Get device name for invalid index fails
    #[test]
    fn test_midi_ffi_invalid_device_index() {
        let count = unsafe { opendaw_midi_device_count() };
        let mut buffer = vec![0i8; MAX_DEVICE_NAME_LEN];
        
        let result = unsafe {
            opendaw_midi_get_device_name(count + 100, buffer.as_mut_ptr(), buffer.len())
        };
        
        assert_eq!(result, -1, "Should fail for invalid device index");
        
        // Buffer should be empty
        let name = unsafe { CStr::from_ptr(buffer.as_ptr()) };
        assert!(name.to_bytes().is_empty(), "Buffer should be empty on error");
    }
    
    // TDD: Test 4 - Open device returns valid handle
    #[test]
    fn test_midi_ffi_open_device() {
        let count = unsafe { opendaw_midi_device_count() };
        
        if count > 0 {
            let mut device_id: usize = 0;
            let result = unsafe {
                opendaw_midi_open_device(0, &mut device_id)
            };
            
            assert_eq!(result, 0, "Should succeed opening device");
            assert!(device_id > 0, "Device ID should be positive");
            
            // Clean up
            unsafe { opendaw_midi_close_device(device_id) };
        }
    }
    
    // TDD: Test 5 - Open invalid device index fails
    #[test]
    fn test_midi_ffi_open_invalid_device() {
        let count = unsafe { opendaw_midi_device_count() };
        let mut device_id: usize = 0;
        
        let result = unsafe {
            opendaw_midi_open_device(count + 100, &mut device_id)
        };
        
        assert_eq!(result, -1, "Should fail for invalid index");
        assert_eq!(device_id, 0, "Device ID should remain 0 on failure");
    }
    
    // TDD: Test 6 - Close device succeeds
    #[test]
    fn test_midi_ffi_close_device() {
        let count = unsafe { opendaw_midi_device_count() };
        
        if count > 0 {
            // Open a device first
            let mut device_id: usize = 0;
            unsafe { opendaw_midi_open_device(0, &mut device_id) };
            
            if device_id > 0 {
                let result = unsafe { opendaw_midi_close_device(device_id) };
                assert_eq!(result, 0, "Should succeed closing valid device");
                
                // Closing again should fail
                let result2 = unsafe { opendaw_midi_close_device(device_id) };
                assert_eq!(result2, -1, "Closing same device twice should fail");
            }
        }
    }
    
    // TDD: Test 7 - Close invalid device ID fails
    #[test]
    fn test_midi_ffi_close_invalid_device() {
        let result = unsafe { opendaw_midi_close_device(0) };
        assert_eq!(result, -1, "Closing device ID 0 should fail");
        
        let result2 = unsafe { opendaw_midi_close_device(999999) };
        assert_eq!(result2, -1, "Closing non-existent device should fail");
    }
    
    // TDD: Test 8 - Read message from device
    #[test]
    fn test_midi_ffi_read_message() {
        let count = unsafe { opendaw_midi_device_count() };
        
        if count > 0 {
            // Open device
            let mut device_id: usize = 0;
            let result = unsafe { opendaw_midi_open_device(0, &mut device_id) };
            
            if result == 0 && device_id > 0 {
                // Initially no message
                let mut status: u8 = 0;
                let mut data1: u8 = 0;
                let mut data2: u8 = 0;
                
                let result = unsafe {
                    opendaw_midi_read_message(device_id, &mut status, &mut data1, &mut data2)
                };
                
                assert_eq!(result, 1, "Should return 1 when no message available");
                
                // Inject a test message
                unsafe {
                    opendaw_midi_inject_test_message(device_id, 0x90, 60, 100);
                }
                
                // Now should read the message
                let result = unsafe {
                    opendaw_midi_read_message(device_id, &mut status, &mut data1, &mut data2)
                };
                
                assert_eq!(result, 0, "Should succeed reading injected message");
                assert_eq!(status, 0x90, "Status should be Note On");
                assert_eq!(data1, 60, "Data1 should be note 60");
                assert_eq!(data2, 100, "Data2 should be velocity 100");
                
                // Clean up
                unsafe { opendaw_midi_close_device(device_id) };
            }
        }
    }
    
    // TDD: Test 9 - Null pointer safety
    #[test]
    fn test_midi_ffi_null_pointer_safety() {
        // Null buffer for get_device_name
        let result = unsafe { opendaw_midi_get_device_name(0, std::ptr::null_mut(), 256) };
        assert_eq!(result, -1, "Null buffer should return error");
        
        // Zero buffer size
        let mut buffer = vec![0i8; 10];
        let result = unsafe { opendaw_midi_get_device_name(0, buffer.as_mut_ptr(), 0) };
        assert_eq!(result, -1, "Zero buffer size should return error");
        
        // Null device_id for open_device
        let result = unsafe { opendaw_midi_open_device(0, std::ptr::null_mut()) };
        assert_eq!(result, -1, "Null device_id should return error");
    }
    
    // TDD: Test 10 - Concurrent access safety
    #[test]
    fn test_midi_ffi_concurrent_access() {
        use std::thread;
        
        let count = unsafe { opendaw_midi_device_count() };
        
        // Spawn multiple threads to access device count
        let handles: Vec<_> = (0..10)
            .map(|_| {
                thread::spawn(|| {
                    unsafe { opendaw_midi_device_count() }
                })
            })
            .collect();
        
        // All should complete without panicking
        let results: Vec<_> = handles.into_iter().map(|h| h.join().unwrap()).collect();
        
        // All should return same count
        let first = results[0];
        for count in &results {
            assert_eq!(*count, first, "All threads should get same count");
        }
    }
}
