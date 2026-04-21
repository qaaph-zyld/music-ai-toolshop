//! Project FFI - Foreign Function Interface for project save/load
//!
//! Provides C-compatible FFI functions for project state management.
//! Note: daw_project_save and daw_project_load are in ffi_bridge.rs

use std::ffi::{c_char, c_int, CStr};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, RwLock};

/// Global project state for FFI
static PROJECT_STATE: RwLock<Option<Arc<Mutex<ProjectState>>>> = RwLock::new(None);

/// Project state containing current project info
struct ProjectState {
    /// Path to current project file (.opendaw directory)
    current_path: Option<PathBuf>,
    /// Whether project has unsaved changes
    modified: bool,
    /// Last error message (if any)
    _last_error: Option<String>,
}

impl ProjectState {
    fn new() -> Self {
        Self {
            current_path: None,
            modified: false,
            _last_error: None,
        }
    }
    
    fn set_path(&mut self, path: PathBuf) {
        self.current_path = Some(path);
        self.modified = false;
    }
    
    fn clear(&mut self) {
        self.current_path = None;
        self.modified = false;
    }
    
    fn mark_modified(&mut self) {
        self.modified = true;
    }
    
    fn _set_error(&mut self, error: String) {
        self._last_error = Some(error);
    }
    
    fn _clear_error(&mut self) {
        self._last_error = None;
    }
}

/// Initialize project state (called once on engine startup)
#[no_mangle]
pub extern "C" fn daw_project_state_init() -> c_int {
    if let Ok(mut state) = PROJECT_STATE.write() {
        *state = Some(Arc::new(Mutex::new(ProjectState::new())));
        return 0;
    }
    -1
}

/// Create a new empty project (clears state)
/// 
/// # Returns
/// 0 on success, -1 on failure
#[no_mangle]
pub extern "C" fn daw_project_state_new() -> c_int {
    if let Ok(state) = PROJECT_STATE.read() {
        if let Some(ref s) = *state {
            if let Ok(mut project) = s.lock() {
                project.clear();
                return 0;
            }
        }
    }
    -1
}

/// Set current project path (called after successful save/load)
#[no_mangle]
pub extern "C" fn daw_project_state_set_path(path: *const c_char) -> c_int {
    if path.is_null() {
        return -1;
    }
    
    let path_str = unsafe {
        match CStr::from_ptr(path).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };
    
    let path_buf = PathBuf::from(path_str);
    
    if let Ok(state) = PROJECT_STATE.read() {
        if let Some(ref s) = *state {
            if let Ok(mut project) = s.lock() {
                project.set_path(path_buf);
                return 0;
            }
        }
    }
    -1
}

/// Get current project path
/// 
/// # Arguments
/// * `path_out` - Buffer to store path (can be null to get required length)
/// * `max_len` - Maximum length of buffer
/// 
/// # Returns
/// Length of path string (not including null terminator), or 0 if no project open
/// If path_out is null, returns required buffer size
#[no_mangle]
pub extern "C" fn daw_project_state_get_path(path_out: *mut c_char, max_len: c_int) -> c_int {
    if let Ok(state) = PROJECT_STATE.read() {
        if let Some(ref s) = *state {
            if let Ok(project) = s.lock() {
                if let Some(ref path) = project.current_path {
                    let path_str = path.to_string_lossy();
                    let len = path_str.len() as c_int;
                    
                    if path_out.is_null() {
                        return len;
                    }
                    
                    let max = max_len as usize;
                    let to_copy = std::cmp::min(path_str.len(), max - 1);
                    
                    unsafe {
                        std::ptr::copy_nonoverlapping(
                            path_str.as_bytes().as_ptr() as *const c_char,
                            path_out,
                            to_copy,
                        );
                        *path_out.add(to_copy) = 0;
                    }
                    
                    return len;
                }
            }
        }
    }
    0
}

/// Check if project has unsaved changes
/// 
/// # Returns
/// 1 if modified, 0 if not modified or no project open
#[no_mangle]
pub extern "C" fn daw_project_state_is_modified() -> c_int {
    if let Ok(state) = PROJECT_STATE.read() {
        if let Some(ref s) = *state {
            if let Ok(project) = s.lock() {
                return if project.modified { 1 } else { 0 };
            }
        }
    }
    0
}

/// Mark project as modified (call when changes are made)
#[no_mangle]
pub extern "C" fn daw_project_state_mark_modified() {
    if let Ok(state) = PROJECT_STATE.read() {
        if let Some(ref s) = *state {
            if let Ok(mut project) = s.lock() {
                project.mark_modified();
            }
        }
    }
}

/// Clear modified flag (call after successful save)
#[no_mangle]
pub extern "C" fn daw_project_state_clear_modified() {
    if let Ok(state) = PROJECT_STATE.read() {
        if let Some(ref s) = *state {
            if let Ok(mut project) = s.lock() {
                project.modified = false;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CString;
    use std::sync::Mutex;

    // Serial test guard to prevent parallel test conflicts
    static TEST_GUARD: Mutex<()> = Mutex::new(());

    fn reset_state() {
        if let Ok(mut state) = PROJECT_STATE.write() {
            *state = Some(Arc::new(Mutex::new(ProjectState::new())));
        }
    }

    #[test]
    fn test_project_state_init() {
        let _guard = TEST_GUARD.lock().unwrap();
        assert_eq!(daw_project_state_init(), 0);
    }

    #[test]
    fn test_project_state_new() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_state();
        assert_eq!(daw_project_state_new(), 0);
        assert_eq!(daw_project_state_is_modified(), 0);
    }

    #[test]
    fn test_project_state_set_and_get_path() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_state();
        
        let test_path = CString::new("test_project.opendaw").unwrap();
        assert_eq!(daw_project_state_set_path(test_path.as_ptr()), 0);
        
        // Get required buffer size
        let required_len = daw_project_state_get_path(std::ptr::null_mut(), 0);
        assert!(required_len > 0);
        
        // Get actual path
        let mut buffer = vec![0i8; (required_len + 1) as usize];
        let actual_len = daw_project_state_get_path(buffer.as_mut_ptr(), required_len + 1);
        assert_eq!(actual_len, required_len);
        
        let path = unsafe { CStr::from_ptr(buffer.as_ptr()) }.to_string_lossy();
        assert_eq!(path, "test_project.opendaw");
    }

    #[test]
    fn test_project_state_modified() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_state();
        
        // Initially not modified
        assert_eq!(daw_project_state_is_modified(), 0);
        
        // Mark as modified
        daw_project_state_mark_modified();
        assert_eq!(daw_project_state_is_modified(), 1);
        
        // Clear modified flag
        daw_project_state_clear_modified();
        assert_eq!(daw_project_state_is_modified(), 0);
    }

    #[test]
    fn test_project_state_modified_cleared_on_set_path() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_state();
        
        // Mark as modified
        daw_project_state_mark_modified();
        assert_eq!(daw_project_state_is_modified(), 1);
        
        // Set path clears modified flag
        let test_path = CString::new("test.opendaw").unwrap();
        daw_project_state_set_path(test_path.as_ptr());
        assert_eq!(daw_project_state_is_modified(), 0);
    }

    #[test]
    fn test_null_path_returns_error() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_state();
        
        assert_eq!(daw_project_state_set_path(std::ptr::null()), -1);
    }

    #[test]
    fn test_get_path_no_project() {
        let _guard = TEST_GUARD.lock().unwrap();
        // Don't reset state - ensure it's None
        if let Ok(mut state) = PROJECT_STATE.write() {
            *state = None;
        }
        
        // No project state, should return 0
        assert_eq!(daw_project_state_get_path(std::ptr::null_mut(), 0), 0);
    }
}
