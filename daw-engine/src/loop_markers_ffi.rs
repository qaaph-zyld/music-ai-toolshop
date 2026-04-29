//! Loop marker FFI exports for C++ UI integration
//!
//! Provides C-compatible exports for managing loop markers:
//! - Loop region CRUD operations
//! - Position updates
//! - Enable/disable control
//! - Active region management

use std::ffi::{c_char, c_double, c_int, CStr, CString};
use std::ptr;
use std::sync::Mutex;
use once_cell::sync::Lazy;

use crate::loop_markers::LoopController;

// =============================================================================
// Global state
// =============================================================================

static LOOP_CONTROLLER: Lazy<Mutex<LoopController>> = Lazy::new(|| {
    Mutex::new(LoopController::new())
});

// =============================================================================
// C-compatible structures
// =============================================================================

/// C-compatible loop region info
#[repr(C)]
pub struct LoopRegionInfo {
    pub id: *const c_char,
    pub name: *const c_char,
    pub start_beat: c_double,
    pub end_beat: c_double,
    pub enabled: c_int,  // 0=disabled, 1=enabled
    pub color: *const c_char,
}

// =============================================================================
// Loop Region Management
// =============================================================================

/// Create a new loop region
/// 
/// Returns: region ID string (caller must free with daw_loop_free_string), or null on error
#[no_mangle]
pub extern "C" fn daw_loop_create_region(
    name: *const c_char,
    start_beat: c_double,
    end_beat: c_double,
) -> *mut c_char {
    if name.is_null() {
        return ptr::null_mut();
    }

    let name_str = unsafe {
        match CStr::from_ptr(name).to_str() {
            Ok(s) => s,
            Err(_) => return ptr::null_mut(),
        }
    };

    let mut controller = LOOP_CONTROLLER.lock().unwrap();
    let id = controller.create_region(name_str, start_beat, end_beat);
    
    CString::new(id).unwrap().into_raw()
}

/// Get the number of loop regions
#[no_mangle]
pub extern "C" fn daw_loop_get_region_count() -> c_int {
    let controller = LOOP_CONTROLLER.lock().unwrap();
    controller.region_count() as c_int
}

/// Get region info at index
/// 
/// Returns: 0 on success, -1 if index out of bounds
#[no_mangle]
pub extern "C" fn daw_loop_get_region_at(
    index: c_int,
    out_info: *mut LoopRegionInfo,
) -> c_int {
    if index < 0 || out_info.is_null() {
        return -1;
    }

    let controller = LOOP_CONTROLLER.lock().unwrap();
    let regions = controller.all_regions();
    
    let idx = index as usize;
    if idx >= regions.len() {
        return -1;
    }

    let region = regions[idx];
    
    unsafe {
        (*out_info).id = CString::new(region.id.clone()).unwrap().into_raw();
        (*out_info).name = CString::new(region.name.clone()).unwrap().into_raw();
        (*out_info).start_beat = region.start_beat;
        (*out_info).end_beat = region.end_beat;
        (*out_info).enabled = if region.enabled { 1 } else { 0 };
        (*out_info).color = CString::new(region.color.clone()).unwrap().into_raw();
    }
    
    0
}

/// Get region info by ID
/// 
/// Returns: 0 on success, -1 if not found
#[no_mangle]
pub extern "C" fn daw_loop_get_region_by_id(
    id: *const c_char,
    out_info: *mut LoopRegionInfo,
) -> c_int {
    if id.is_null() || out_info.is_null() {
        return -1;
    }

    let id_str = unsafe {
        match CStr::from_ptr(id).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };

    let controller = LOOP_CONTROLLER.lock().unwrap();
    
    if let Some(region) = controller.get_region(id_str) {
        unsafe {
            (*out_info).id = CString::new(region.id.clone()).unwrap().into_raw();
            (*out_info).name = CString::new(region.name.clone()).unwrap().into_raw();
            (*out_info).start_beat = region.start_beat;
            (*out_info).end_beat = region.end_beat;
            (*out_info).enabled = if region.enabled { 1 } else { 0 };
            (*out_info).color = CString::new(region.color.clone()).unwrap().into_raw();
        }
        0
    } else {
        -1
    }
}

/// Free a region info struct (and its strings)
#[no_mangle]
pub extern "C" fn daw_loop_free_region_info(info: *mut LoopRegionInfo) {
    if info.is_null() {
        return;
    }

    unsafe {
        if !(*info).id.is_null() {
            let _ = CString::from_raw((*info).id as *mut c_char);
        }
        if !(*info).name.is_null() {
            let _ = CString::from_raw((*info).name as *mut c_char);
        }
        if !(*info).color.is_null() {
            let _ = CString::from_raw((*info).color as *mut c_char);
        }
    }
}

/// Free a string returned by the API
#[no_mangle]
pub extern "C" fn daw_loop_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = CString::from_raw(s);
        }
    }
}

/// Delete a loop region
/// 
/// Returns: 0 on success, -1 if not found
#[no_mangle]
pub extern "C" fn daw_loop_delete_region(id: *const c_char) -> c_int {
    if id.is_null() {
        return -1;
    }

    let id_str = unsafe {
        match CStr::from_ptr(id).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };

    let mut controller = LOOP_CONTROLLER.lock().unwrap();
    
    if controller.delete_region(id_str) {
        0
    } else {
        -1
    }
}

// =============================================================================
// Region Updates
// =============================================================================

/// Update region position (start and end beats)
/// 
/// Returns: 0 on success, -1 if not found
#[no_mangle]
pub extern "C" fn daw_loop_set_region_position(
    id: *const c_char,
    start_beat: c_double,
    end_beat: c_double,
) -> c_int {
    if id.is_null() {
        return -1;
    }

    let id_str = unsafe {
        match CStr::from_ptr(id).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };

    let mut controller = LOOP_CONTROLLER.lock().unwrap();
    
    if controller.set_region_position(id_str, start_beat, end_beat) {
        0
    } else {
        -1
    }
}

/// Rename a region
/// 
/// Returns: 0 on success, -1 if not found
#[no_mangle]
pub extern "C" fn daw_loop_rename_region(
    id: *const c_char,
    new_name: *const c_char,
) -> c_int {
    if id.is_null() || new_name.is_null() {
        return -1;
    }

    let id_str = unsafe {
        match CStr::from_ptr(id).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };

    let new_name_str = unsafe {
        match CStr::from_ptr(new_name).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };

    let mut controller = LOOP_CONTROLLER.lock().unwrap();
    
    if controller.rename_region(id_str, new_name_str) {
        0
    } else {
        -1
    }
}

/// Enable/disable a region
/// 
/// Returns: 0 on success, -1 if not found
#[no_mangle]
pub extern "C" fn daw_loop_set_region_enabled(
    id: *const c_char,
    enabled: c_int,
) -> c_int {
    if id.is_null() {
        return -1;
    }

    let id_str = unsafe {
        match CStr::from_ptr(id).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };

    let mut controller = LOOP_CONTROLLER.lock().unwrap();
    
    if controller.set_region_enabled(id_str, enabled != 0) {
        0
    } else {
        -1
    }
}

// =============================================================================
// Active Region & Looping State
// =============================================================================

/// Get the ID of the active region
/// 
/// Returns: region ID string (caller must free), or null if no active region
#[no_mangle]
pub extern "C" fn daw_loop_get_active_region_id() -> *mut c_char {
    let controller = LOOP_CONTROLLER.lock().unwrap();
    
    if let Some(id) = controller.active_region_id() {
        CString::new(id).unwrap().into_raw()
    } else {
        ptr::null_mut()
    }
}

/// Set the active region by ID
/// 
/// Returns: 0 on success, -1 if region not found
#[no_mangle]
pub extern "C" fn daw_loop_set_active_region(id: *const c_char) -> c_int {
    let id_opt = if id.is_null() {
        None
    } else {
        let id_str = unsafe {
            match CStr::from_ptr(id).to_str() {
                Ok(s) => Some(s),
                Err(_) => return -1,
            }
        };
        id_str
    };

    let mut controller = LOOP_CONTROLLER.lock().unwrap();
    
    if controller.set_active_region(id_opt) {
        0
    } else {
        -1
    }
}

/// Check if looping is globally enabled
#[no_mangle]
pub extern "C" fn daw_loop_is_looping_enabled() -> c_int {
    let controller = LOOP_CONTROLLER.lock().unwrap();
    if controller.is_looping_enabled() { 1 } else { 0 }
}

/// Enable/disable global looping
#[no_mangle]
pub extern "C" fn daw_loop_set_looping_enabled(enabled: c_int) {
    let mut controller = LOOP_CONTROLLER.lock().unwrap();
    controller.set_looping_enabled(enabled != 0);
}

// =============================================================================
// Transport Integration
// =============================================================================

/// Check if playback should loop at the given beat position
/// 
/// Returns: loop start beat if should loop, -1.0 if no loop needed
#[no_mangle]
pub extern "C" fn daw_loop_should_loop_at_beat(beat: c_double) -> c_double {
    let controller = LOOP_CONTROLLER.lock().unwrap();
    
    if let Some(loop_start) = controller.should_loop_at_beat(beat) {
        loop_start
    } else {
        -1.0
    }
}

/// Get loop boundaries for a beat position
/// 
/// Returns: 0 if in loop (start/end written to out params), -1 if not in loop
#[no_mangle]
pub extern "C" fn daw_loop_get_boundaries(
    beat: c_double,
    out_start: *mut c_double,
    out_end: *mut c_double,
) -> c_int {
    if out_start.is_null() || out_end.is_null() {
        return -1;
    }

    let controller = LOOP_CONTROLLER.lock().unwrap();
    
    if let Some((start, end)) = controller.get_loop_boundaries(beat) {
        unsafe {
            *out_start = start;
            *out_end = end;
        }
        0
    } else {
        -1
    }
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_loop_ffi_create_and_get() {
        // Reset global state
        let mut controller = LOOP_CONTROLLER.lock().unwrap();
        *controller = LoopController::new();
        drop(controller);

        // Create a region
        let name = CString::new("Verse").unwrap();
        let id_ptr = daw_loop_create_region(name.as_ptr(), 4.0, 20.0);
        
        assert!(!id_ptr.is_null());
        
        // Check count (should be at least 1)
        assert!(daw_loop_get_region_count() >= 1);

        // Get region info by ID (more reliable than index with shared state)
        let mut info = LoopRegionInfo {
            id: ptr::null(),
            name: ptr::null(),
            start_beat: 0.0,
            end_beat: 0.0,
            enabled: 0,
            color: ptr::null(),
        };
        
        unsafe {
            // Verify ID format
            let id_str = CStr::from_ptr(id_ptr).to_str().unwrap();
            assert!(id_str.starts_with("loop-"));
            
            // Get region by ID
            let result = daw_loop_get_region_by_id(id_ptr, &mut info);
            assert_eq!(result, 0);
            
            assert!(!info.id.is_null());
            assert!(!info.name.is_null());
            let name = CStr::from_ptr(info.name).to_str().unwrap();
            assert_eq!(name, "Verse");
            assert_eq!(info.start_beat, 4.0);
            assert_eq!(info.end_beat, 20.0);
            assert_eq!(info.enabled, 1);
            
            daw_loop_free_region_info(&mut info);
            daw_loop_free_string(id_ptr);
        }
    }

    #[test]
    fn test_loop_ffi_update_region() {
        // Reset
        let mut controller = LOOP_CONTROLLER.lock().unwrap();
        *controller = LoopController::new();
        drop(controller);

        // Create region
        let name = CString::new("Chorus").unwrap();
        let id_ptr = daw_loop_create_region(name.as_ptr(), 16.0, 32.0);
        
        unsafe {
            let id = CString::from_raw(id_ptr);
            let id_str = id.as_ptr();

            // Update position
            let result = daw_loop_set_region_position(id_str, 20.0, 40.0);
            assert_eq!(result, 0);

            // Rename
            let new_name = CString::new("Bridge").unwrap();
            let result = daw_loop_rename_region(id_str, new_name.as_ptr());
            assert_eq!(result, 0);

            // Disable
            let result = daw_loop_set_region_enabled(id_str, 0);
            assert_eq!(result, 0);

            // Verify changes
            let mut info = LoopRegionInfo {
                id: ptr::null(),
                name: ptr::null(),
                start_beat: 0.0,
                end_beat: 0.0,
                enabled: 0,
                color: ptr::null(),
            };
            
            daw_loop_get_region_by_id(id_str, &mut info);
            
            assert_eq!(info.start_beat, 20.0);
            assert_eq!(info.end_beat, 40.0);
            assert_eq!(info.enabled, 0);
            
            let name = CStr::from_ptr(info.name).to_str().unwrap();
            assert_eq!(name, "Bridge");
            
            daw_loop_free_region_info(&mut info);
        }
    }

    #[test]
    fn test_loop_ffi_active_region() {
        // Reset
        let mut controller = LOOP_CONTROLLER.lock().unwrap();
        *controller = LoopController::new();
        drop(controller);

        // Create two regions
        let name1 = CString::new("Verse").unwrap();
        let id1_ptr = daw_loop_create_region(name1.as_ptr(), 0.0, 16.0);
        
        let name2 = CString::new("Chorus").unwrap();
        let id2_ptr = daw_loop_create_region(name2.as_ptr(), 16.0, 32.0);

        unsafe {
            // Get the current active region (should be id1 since it was created first after reset)
            let active_ptr = daw_loop_get_active_region_id();
            assert!(!active_ptr.is_null());
            
            // Verify we have an active region
            let active_id = CStr::from_ptr(active_ptr).to_str().unwrap();
            let id1 = CStr::from_ptr(id1_ptr).to_str().unwrap();
            let id2 = CStr::from_ptr(id2_ptr).to_str().unwrap();
            
            // Active should be one of our created regions
            assert!(active_id == id1 || active_id == id2);
            
            daw_loop_free_string(active_ptr);

            // Switch to second region
            let result = daw_loop_set_active_region(id2_ptr);
            assert_eq!(result, 0);

            let active_ptr = daw_loop_get_active_region_id();
            let active_id = CStr::from_ptr(active_ptr).to_str().unwrap();
            assert_eq!(active_id, id2);
            
            daw_loop_free_string(active_ptr);
            daw_loop_free_string(id1_ptr);
            daw_loop_free_string(id2_ptr);
        }
    }

    #[test]
    fn test_loop_ffi_looping_state() {
        // Reset
        let mut controller = LOOP_CONTROLLER.lock().unwrap();
        *controller = LoopController::new();
        drop(controller);

        assert_eq!(daw_loop_is_looping_enabled(), 0);
        
        daw_loop_set_looping_enabled(1);
        assert_eq!(daw_loop_is_looping_enabled(), 1);
        
        daw_loop_set_looping_enabled(0);
        assert_eq!(daw_loop_is_looping_enabled(), 0);
    }

    #[test]
    fn test_loop_ffi_should_loop() {
        // Reset
        let mut controller = LOOP_CONTROLLER.lock().unwrap();
        *controller = LoopController::new();
        drop(controller);

        // Create and enable
        let name = CString::new("Loop").unwrap();
        let id_ptr = daw_loop_create_region(name.as_ptr(), 4.0, 20.0);
        daw_loop_set_looping_enabled(1);

        // Should not loop before end
        let result = daw_loop_should_loop_at_beat(10.0);
        assert_eq!(result, -1.0);

        // Should loop at/past end
        let result = daw_loop_should_loop_at_beat(20.0);
        assert_eq!(result, 4.0);

        unsafe {
            daw_loop_free_string(id_ptr);
        }
    }

    #[test]
    fn test_loop_ffi_get_boundaries() {
        // Reset
        let mut controller = LOOP_CONTROLLER.lock().unwrap();
        *controller = LoopController::new();
        drop(controller);

        // Create and enable
        let name = CString::new("Loop").unwrap();
        let id_ptr = daw_loop_create_region(name.as_ptr(), 4.0, 20.0);
        daw_loop_set_looping_enabled(1);
        
        // Set as active region
        unsafe {
            daw_loop_set_active_region(id_ptr);
            daw_loop_free_string(id_ptr);
        }

        let mut start: c_double = 0.0;
        let mut end: c_double = 0.0;

        // Within loop
        let result = daw_loop_get_boundaries(10.0, &mut start, &mut end);
        assert_eq!(result, 0);
        assert_eq!(start, 4.0);
        assert_eq!(end, 20.0);

        // Outside loop
        let result = daw_loop_get_boundaries(2.0, &mut start, &mut end);
        assert_eq!(result, -1);
    }

    #[test]
    fn test_loop_ffi_null_safety() {
        // Test null pointer handling
        let result = daw_loop_create_region(ptr::null(), 0.0, 16.0);
        assert!(result.is_null());

        let result = daw_loop_delete_region(ptr::null());
        assert_eq!(result, -1);

        let result = daw_loop_set_region_position(ptr::null(), 0.0, 16.0);
        assert_eq!(result, -1);

        let result = daw_loop_rename_region(ptr::null(), ptr::null());
        assert_eq!(result, -1);

        let mut info = LoopRegionInfo {
            id: ptr::null(),
            name: ptr::null(),
            start_beat: 0.0,
            end_beat: 0.0,
            enabled: 0,
            color: ptr::null(),
        };
        
        let result = daw_loop_get_region_at(0, ptr::null_mut());
        assert_eq!(result, -1);

        let result = daw_loop_get_region_by_id(ptr::null(), &mut info);
        assert_eq!(result, -1);

        // Should not crash
        daw_loop_free_region_info(ptr::null_mut());
        daw_loop_free_string(ptr::null_mut());
    }

    #[test]
    fn test_loop_ffi_delete_region() {
        // Reset
        let mut controller = LOOP_CONTROLLER.lock().unwrap();
        *controller = LoopController::new();
        drop(controller);

        // Get initial count
        let initial_count = daw_loop_get_region_count();

        // Create region
        let name = CString::new("ToDelete").unwrap();
        let id_ptr = daw_loop_create_region(name.as_ptr(), 0.0, 8.0);
        
        // Count should have increased by 1
        assert_eq!(daw_loop_get_region_count(), initial_count + 1);

        unsafe {
            // Delete it
            let result = daw_loop_delete_region(id_ptr);
            assert_eq!(result, 0);
            
            daw_loop_free_string(id_ptr);
        }

        // Count should be back to initial
        assert_eq!(daw_loop_get_region_count(), initial_count);

        // Try to delete non-existent
        let fake_id = CString::new("nonexistent").unwrap();
        let result = daw_loop_delete_region(fake_id.as_ptr());
        assert_eq!(result, -1);
    }
}
