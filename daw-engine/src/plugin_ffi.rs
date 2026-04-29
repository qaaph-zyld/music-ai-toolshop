//! Plugin chain FFI exports for C++ UI integration
//!
//! Provides C-compatible exports for managing plugin chains on mixer tracks:
//! - Plugin registry scanning and search
//! - Plugin chain creation and management
//! - Parameter control

use std::ffi::{c_char, c_float, c_int, CStr, CString};
use std::ptr;
use std::sync::Mutex;
use std::collections::HashMap;
use once_cell::sync::Lazy;

use crate::plugin::{PluginChain, PluginInfo, PluginFormat, PluginRegistry};

// =============================================================================
// Global state for plugin chains per track
// =============================================================================

/// Plugin chain storage per track index
type TrackChains = HashMap<usize, PluginChain>;

static PLUGIN_CHAINS: Lazy<Mutex<TrackChains>> = Lazy::new(|| {
    Mutex::new(HashMap::new())
});

/// Global plugin registry
static PLUGIN_REGISTRY: Lazy<Mutex<PluginRegistry>> = Lazy::new(|| {
    Mutex::new(PluginRegistry::new())
});

// =============================================================================
// C-compatible structures
// =============================================================================

/// C-compatible plugin info structure
#[repr(C)]
pub struct PluginInfoData {
    pub name: *const c_char,
    pub vendor: *const c_char,
    pub version: *const c_char,
    pub format: c_int,  // 0=VST3, 1=AU, 2=Internal
    pub num_inputs: c_int,
    pub num_outputs: c_int,
    pub unique_id: *const c_char,
}

/// C-compatible plugin parameter structure
#[repr(C)]
pub struct PluginParameterData {
    pub id: u32,
    pub name: *const c_char,
    pub min_value: c_float,
    pub max_value: c_float,
    pub default_value: c_float,
    pub current_value: c_float,
}

// =============================================================================
// Plugin Registry FFI
// =============================================================================

/// Scan for available plugins and populate registry
/// 
/// Returns: number of plugins found
#[no_mangle]
pub extern "C" fn daw_plugin_registry_scan() -> c_int {
    let mut registry = PLUGIN_REGISTRY.lock().unwrap();
    
    // Add internal plugins for testing
    registry.register(PluginInfo {
        name: "Gain".to_string(),
        vendor: "OpenDAW".to_string(),
        version: "1.0.0".to_string(),
        format: PluginFormat::Internal,
        num_inputs: 2,
        num_outputs: 2,
        unique_id: "opendaw.gain".to_string(),
    });
    
    registry.register(PluginInfo {
        name: "EQ".to_string(),
        vendor: "OpenDAW".to_string(),
        version: "1.0.0".to_string(),
        format: PluginFormat::Internal,
        num_inputs: 2,
        num_outputs: 2,
        unique_id: "opendaw.eq".to_string(),
    });
    
    registry.register(PluginInfo {
        name: "Compressor".to_string(),
        vendor: "OpenDAW".to_string(),
        version: "1.0.0".to_string(),
        format: PluginFormat::Internal,
        num_inputs: 2,
        num_outputs: 2,
        unique_id: "opendaw.compressor".to_string(),
    });
    
    registry.register(PluginInfo {
        name: "Reverb".to_string(),
        vendor: "OpenDAW".to_string(),
        version: "1.0.0".to_string(),
        format: PluginFormat::Internal,
        num_inputs: 2,
        num_outputs: 2,
        unique_id: "opendaw.reverb".to_string(),
    });
    
    registry.register(PluginInfo {
        name: "Delay".to_string(),
        vendor: "OpenDAW".to_string(),
        version: "1.0.0".to_string(),
        format: PluginFormat::Internal,
        num_inputs: 2,
        num_outputs: 2,
        unique_id: "opendaw.delay".to_string(),
    });
    
    registry.count() as c_int
}

/// Get number of available plugins
#[no_mangle]
pub extern "C" fn daw_plugin_registry_get_count() -> c_int {
    let registry = PLUGIN_REGISTRY.lock().unwrap();
    registry.count() as c_int
}

/// Get plugin info at index
/// 
/// Returns: 0 on success, -1 if index out of bounds
/// The caller is responsible for freeing the strings in PluginInfoData
#[no_mangle]
pub extern "C" fn daw_plugin_registry_get_plugin(
    index: c_int,
    out_info: *mut PluginInfoData,
) -> c_int {
    if out_info.is_null() {
        return -1;
    }
    
    let registry = PLUGIN_REGISTRY.lock().unwrap();
    let plugins: Vec<&PluginInfo> = registry.list_all();
    
    let idx = index as usize;
    if idx >= plugins.len() {
        return -1;
    }
    
    let info = plugins[idx];
    
    unsafe {
        (*out_info).name = CString::new(info.name.clone()).unwrap().into_raw();
        (*out_info).vendor = CString::new(info.vendor.clone()).unwrap().into_raw();
        (*out_info).version = CString::new(info.version.clone()).unwrap().into_raw();
        (*out_info).format = match info.format {
            PluginFormat::Vst3 => 0,
            PluginFormat::Au => 1,
            PluginFormat::Internal => 2,
        };
        (*out_info).num_inputs = info.num_inputs as c_int;
        (*out_info).num_outputs = info.num_outputs as c_int;
        (*out_info).unique_id = CString::new(info.unique_id.clone()).unwrap().into_raw();
    }
    
    0
}

/// Free strings in PluginInfoData
#[no_mangle]
pub extern "C" fn daw_plugin_info_free(info: *mut PluginInfoData) {
    if info.is_null() {
        return;
    }
    
    unsafe {
        if !(*info).name.is_null() {
            let _ = CString::from_raw((*info).name as *mut c_char);
        }
        if !(*info).vendor.is_null() {
            let _ = CString::from_raw((*info).vendor as *mut c_char);
        }
        if !(*info).version.is_null() {
            let _ = CString::from_raw((*info).version as *mut c_char);
        }
        if !(*info).unique_id.is_null() {
            let _ = CString::from_raw((*info).unique_id as *mut c_char);
        }
    }
}

/// Search plugins by name (case-insensitive substring match)
/// 
/// Returns: number of matching plugins
#[no_mangle]
pub extern "C" fn daw_plugin_registry_search(
    query: *const c_char,
    out_indices: *mut c_int,
    max_results: c_int,
) -> c_int {
    if query.is_null() || out_indices.is_null() || max_results <= 0 {
        return 0;
    }
    
    let query_str = unsafe {
        match CStr::from_ptr(query).to_str() {
            Ok(s) => s.to_lowercase(),
            Err(_) => return 0,
        }
    };
    
    let registry = PLUGIN_REGISTRY.lock().unwrap();
    let plugins: Vec<&PluginInfo> = registry.list_all();
    
    let mut count = 0;
    for (i, info) in plugins.iter().enumerate() {
        if info.name.to_lowercase().contains(&query_str) ||
           info.vendor.to_lowercase().contains(&query_str) {
            if count < max_results as usize {
                unsafe {
                    *out_indices.add(count) = i as c_int;
                }
                count += 1;
            }
        }
    }
    
    count as c_int
}

// =============================================================================
// Plugin Chain FFI
// =============================================================================

/// Get or create plugin chain for a track
/// 
/// Returns: 0 on success
#[no_mangle]
pub extern "C" fn daw_plugin_chain_get_or_create(track_index: c_int) -> c_int {
    if track_index < 0 {
        return -1;
    }
    
    let mut chains = PLUGIN_CHAINS.lock().unwrap();
    let idx = track_index as usize;
    
    chains.entry(idx).or_insert_with(PluginChain::new);
    
    0
}

/// Add plugin to track's chain
/// 
/// Returns: slot index on success, -1 on failure
#[no_mangle]
pub extern "C" fn daw_plugin_chain_add(
    track_index: c_int,
    unique_id: *const c_char,
) -> c_int {
    if track_index < 0 || unique_id.is_null() {
        return -1;
    }
    
    let unique_id_str = unsafe {
        match CStr::from_ptr(unique_id).to_str() {
            Ok(s) => s.to_string(),
            Err(_) => return -1,
        }
    };
    
    // Find plugin info from registry
    let registry = PLUGIN_REGISTRY.lock().unwrap();
    let plugins = registry.list_all();
    let plugin_info = match plugins.iter().find(|p| p.unique_id == unique_id_str) {
        Some(info) => (*info).clone(),
        None => return -1,
    };
    drop(registry);
    
    let mut chains = PLUGIN_CHAINS.lock().unwrap();
    let chain = chains.entry(track_index as usize).or_insert_with(PluginChain::new);
    
    let instance_id = format!("{}-instance-{:?}", unique_id_str, std::time::Instant::now());
    let slot = chain.add_plugin(&instance_id, plugin_info);
    
    slot as c_int
}

/// Remove plugin from chain
/// 
/// Returns: 0 on success, -1 on failure
#[no_mangle]
pub extern "C" fn daw_plugin_chain_remove(
    track_index: c_int,
    slot_index: c_int,
) -> c_int {
    if track_index < 0 || slot_index < 0 {
        return -1;
    }
    
    let mut chains = PLUGIN_CHAINS.lock().unwrap();
    
    if let Some(chain) = chains.get_mut(&(track_index as usize)) {
        if chain.remove(slot_index as usize).is_some() {
            0
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Move plugin in chain (reorder)
/// 
/// Returns: 0 on success, -1 on failure
#[no_mangle]
pub extern "C" fn daw_plugin_chain_move(
    track_index: c_int,
    from_index: c_int,
    to_index: c_int,
) -> c_int {
    if track_index < 0 || from_index < 0 || to_index < 0 {
        return -1;
    }
    
    let mut chains = PLUGIN_CHAINS.lock().unwrap();
    
    if let Some(chain) = chains.get_mut(&(track_index as usize)) {
        if chain.move_plugin(from_index as usize, to_index as usize) {
            0
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Get number of plugins in chain
/// 
/// Returns: count on success, -1 if track not found
#[no_mangle]
pub extern "C" fn daw_plugin_chain_get_count(track_index: c_int) -> c_int {
    if track_index < 0 {
        return -1;
    }
    
    let chains = PLUGIN_CHAINS.lock().unwrap();
    
    if let Some(chain) = chains.get(&(track_index as usize)) {
        chain.count() as c_int
    } else {
        0  // No chain = 0 plugins
    }
}

/// Get plugin info at slot index
/// 
/// Returns: 0 on success, -1 on failure
#[no_mangle]
pub extern "C" fn daw_plugin_chain_get_plugin_info(
    track_index: c_int,
    slot_index: c_int,
    out_info: *mut PluginInfoData,
) -> c_int {
    if track_index < 0 || slot_index < 0 || out_info.is_null() {
        return -1;
    }
    
    let chains = PLUGIN_CHAINS.lock().unwrap();
    
    if let Some(chain) = chains.get(&(track_index as usize)) {
        if let Some(instance) = chain.get(slot_index as usize) {
            let info = instance.plugin_info();
            unsafe {
                (*out_info).name = CString::new(info.name.clone()).unwrap().into_raw();
                (*out_info).vendor = CString::new(info.vendor.clone()).unwrap().into_raw();
                (*out_info).version = CString::new(info.version.clone()).unwrap().into_raw();
                (*out_info).format = match info.format {
                    PluginFormat::Vst3 => 0,
                    PluginFormat::Au => 1,
                    PluginFormat::Internal => 2,
                };
                (*out_info).num_inputs = info.num_inputs as c_int;
                (*out_info).num_outputs = info.num_outputs as c_int;
                (*out_info).unique_id = CString::new(info.unique_id.clone()).unwrap().into_raw();
            }
            0
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Set plugin bypass state
/// 
/// Returns: 0 on success, -1 on failure
#[no_mangle]
pub extern "C" fn daw_plugin_chain_set_bypass(
    track_index: c_int,
    slot_index: c_int,
    bypass: c_int,  // 0=enabled, 1=bypassed
) -> c_int {
    if track_index < 0 || slot_index < 0 {
        return -1;
    }
    
    let mut chains = PLUGIN_CHAINS.lock().unwrap();
    
    if let Some(chain) = chains.get_mut(&(track_index as usize)) {
        if let Some(instance) = chain.get_mut(slot_index as usize) {
            if bypass != 0 {
                instance.disable();
            } else {
                instance.enable();
            }
            0
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Get plugin bypass state
/// 
/// Returns: 0=enabled, 1=bypassed, -1=error
#[no_mangle]
pub extern "C" fn daw_plugin_chain_get_bypass(
    track_index: c_int,
    slot_index: c_int,
) -> c_int {
    if track_index < 0 || slot_index < 0 {
        return -1;
    }
    
    let chains = PLUGIN_CHAINS.lock().unwrap();
    
    if let Some(chain) = chains.get(&(track_index as usize)) {
        if let Some(instance) = chain.get(slot_index as usize) {
            if instance.is_enabled() {
                0
            } else {
                1
            }
        } else {
            -1
        }
    } else {
        -1
    }
}

/// Clear all plugins from chain
/// 
/// Returns: 0 on success
#[no_mangle]
pub extern "C" fn daw_plugin_chain_clear(track_index: c_int) -> c_int {
    if track_index < 0 {
        return -1;
    }
    
    let mut chains = PLUGIN_CHAINS.lock().unwrap();
    
    if let Some(chain) = chains.get_mut(&(track_index as usize)) {
        chain.clear();
    }
    
    0
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plugin_registry_scan() {
        let count = daw_plugin_registry_scan();
        assert!(count > 0, "Should find at least some plugins");
        
        let get_count = daw_plugin_registry_get_count();
        assert_eq!(count, get_count, "Scan count should match get_count");
    }

    #[test]
    fn test_plugin_registry_get_plugin() {
        daw_plugin_registry_scan();
        
        let count = daw_plugin_registry_get_count();
        assert!(count > 0);
        
        let mut info = PluginInfoData {
            name: ptr::null(),
            vendor: ptr::null(),
            version: ptr::null(),
            format: 0,
            num_inputs: 0,
            num_outputs: 0,
            unique_id: ptr::null(),
        };
        
        let result = daw_plugin_registry_get_plugin(0, &mut info);
        assert_eq!(result, 0, "Should get plugin at index 0");
        
        unsafe {
            assert!(!info.name.is_null());
            assert!(!info.unique_id.is_null());
        }
        
        daw_plugin_info_free(&mut info);
    }

    #[test]
    fn test_plugin_registry_search() {
        daw_plugin_registry_scan();
        
        let query = CString::new("gain").unwrap();
        let mut indices = [0i32; 10];
        
        let count = daw_plugin_registry_search(query.as_ptr(), indices.as_mut_ptr(), 10);
        assert!(count >= 0, "Search should succeed");
        
        // Search for something that doesn't exist
        let query2 = CString::new("xyz_nonexistent").unwrap();
        let count2 = daw_plugin_registry_search(query2.as_ptr(), indices.as_mut_ptr(), 10);
        assert_eq!(count2, 0, "Should find no results for nonexistent query");
    }

    #[test]
    fn test_plugin_chain_lifecycle() {
        // Setup
        daw_plugin_registry_scan();
        
        let track_index = 0;
        
        // Create chain
        let result = daw_plugin_chain_get_or_create(track_index);
        assert_eq!(result, 0, "Should create chain");
        
        // Add plugin
        let plugin_id = CString::new("opendaw.gain").unwrap();
        let slot = daw_plugin_chain_add(track_index, plugin_id.as_ptr());
        assert!(slot >= 0, "Should add plugin to chain");
        
        // Check count
        let count = daw_plugin_chain_get_count(track_index);
        assert_eq!(count, 1, "Should have 1 plugin");
        
        // Get plugin info
        let mut info = PluginInfoData {
            name: ptr::null(),
            vendor: ptr:: null(),
            version: ptr::null(),
            format: 0,
            num_inputs: 0,
            num_outputs: 0,
            unique_id: ptr::null(),
        };
        let result = daw_plugin_chain_get_plugin_info(track_index, 0, &mut info);
        assert_eq!(result, 0, "Should get plugin info");
        
        unsafe {
            assert!(!info.name.is_null());
        }
        daw_plugin_info_free(&mut info);
        
        // Test bypass
        let bypass_result = daw_plugin_chain_set_bypass(track_index, 0, 1);
        assert_eq!(bypass_result, 0, "Should set bypass");
        
        let bypass_state = daw_plugin_chain_get_bypass(track_index, 0);
        assert_eq!(bypass_state, 1, "Should be bypassed");
        
        // Remove plugin
        let remove_result = daw_plugin_chain_remove(track_index, 0);
        assert_eq!(remove_result, 0, "Should remove plugin");
        
        let count_after = daw_plugin_chain_get_count(track_index);
        assert_eq!(count_after, 0, "Should have 0 plugins after removal");
        
        // Clear
        daw_plugin_chain_clear(track_index);
    }

    #[test]
    fn test_plugin_chain_reorder() {
        daw_plugin_registry_scan();
        
        let track_index = 1;
        daw_plugin_chain_get_or_create(track_index);
        
        // Add two plugins
        let plugin_id1 = CString::new("opendaw.gain").unwrap();
        let plugin_id2 = CString::new("opendaw.eq").unwrap();
        
        let slot1 = daw_plugin_chain_add(track_index, plugin_id1.as_ptr());
        let slot2 = daw_plugin_chain_add(track_index, plugin_id2.as_ptr());
        
        assert_eq!(slot1, 0);
        assert_eq!(slot2, 1);
        
        // Move: swap positions
        let move_result = daw_plugin_chain_move(track_index, 0, 1);
        assert_eq!(move_result, 0, "Should move plugin");
        
        // Clear
        daw_plugin_chain_clear(track_index);
    }

    #[test]
    fn test_null_safety() {
        // Test null pointer handling
        let result = daw_plugin_chain_add(0, ptr::null());
        assert_eq!(result, -1, "Should handle null unique_id");
        
        let result = daw_plugin_registry_get_plugin(0, ptr::null_mut());
        assert_eq!(result, -1, "Should handle null out_info");
        
        let result = daw_plugin_registry_search(ptr::null(), ptr::null_mut(), 0);
        assert_eq!(result, 0, "Should handle null query");
    }
}
