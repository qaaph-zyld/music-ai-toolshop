//! Meter Level FFI - Foreign Function Interface for audio level metering
//!
//! Provides C-compatible FFI functions for retrieving real-time peak and RMS
//! audio levels from the mixer for display in the JUCE UI.

use std::ffi::{c_float, c_int};
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::RwLock;

/// Maximum number of tracks supported for metering
const MAX_METER_TRACKS: usize = 32;

/// Convert f32 to bits for atomic storage
fn f32_to_bits(f: f32) -> u32 {
    f.to_bits()
}

/// Convert bits back to f32
fn bits_to_f32(bits: u32) -> f32 {
    f32::from_bits(bits)
}

/// Per-channel meter levels (thread-safe using AtomicU32 for f32 storage)
struct MeterLevel {
    /// Peak level in dB (0.0 = unity, negative = below, positive = above)
    peak_db: AtomicU32,
    /// RMS level in dB
    rms_db: AtomicU32,
}

impl MeterLevel {
    fn new() -> Self {
        Self {
            peak_db: AtomicU32::new(f32_to_bits(-96.0)), // Start at silence
            rms_db: AtomicU32::new(f32_to_bits(-96.0)),
        }
    }
    
    fn set_peak(&self, db: f32) {
        self.peak_db.store(f32_to_bits(db), Ordering::Relaxed);
    }
    
    fn set_rms(&self, db: f32) {
        self.rms_db.store(f32_to_bits(db), Ordering::Relaxed);
    }
    
    fn get_peak(&self) -> f32 {
        bits_to_f32(self.peak_db.load(Ordering::Relaxed))
    }
    
    fn get_rms(&self) -> f32 {
        bits_to_f32(self.rms_db.load(Ordering::Relaxed))
    }
}

/// Global meter state for all tracks + master
static METER_STATE: RwLock<Option<MeterState>> = RwLock::new(None);

/// Meter state containing levels for all tracks and master
struct MeterState {
    /// Per-track meter levels
    track_levels: Vec<MeterLevel>,
    /// Master output meter levels (stereo, but we store combined)
    master_level: MeterLevel,
}

impl MeterState {
    fn new(num_tracks: usize) -> Self {
        let track_levels = (0..num_tracks.max(1).min(MAX_METER_TRACKS))
            .map(|_| MeterLevel::new())
            .collect();
        
        Self {
            track_levels,
            master_level: MeterLevel::new(),
        }
    }
    
    fn update_track_peak(&self, track: usize, peak_db: f32) {
        if track < self.track_levels.len() {
            self.track_levels[track].set_peak(peak_db);
        }
    }
    
    fn update_track_rms(&self, track: usize, rms_db: f32) {
        if track < self.track_levels.len() {
            self.track_levels[track].set_rms(rms_db);
        }
    }
    
    fn update_master_peak(&self, peak_db: f32) {
        self.master_level.set_peak(peak_db);
    }
    
    fn update_master_rms(&self, rms_db: f32) {
        self.master_level.set_rms(rms_db);
    }
    
    fn get_track_peak(&self, track: usize) -> f32 {
        if track < self.track_levels.len() {
            self.track_levels[track].get_peak()
        } else {
            -96.0
        }
    }
    
    fn get_track_rms(&self, track: usize) -> f32 {
        if track < self.track_levels.len() {
            self.track_levels[track].get_rms()
        } else {
            -96.0
        }
    }
    
    fn get_master_peak(&self) -> f32 {
        self.master_level.get_peak()
    }
    
    fn get_master_rms(&self) -> f32 {
        self.master_level.get_rms()
    }
}

/// Initialize meter state with the specified number of tracks
/// 
/// # Safety
/// Should be called once during engine initialization
#[no_mangle]
pub extern "C" fn daw_meter_init(num_tracks: c_int) {
    if let Ok(mut state) = METER_STATE.write() {
        *state = Some(MeterState::new(num_tracks as usize));
    }
}

/// Get the number of meter tracks currently configured
#[no_mangle]
pub extern "C" fn daw_meter_get_track_count() -> c_int {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            return s.track_levels.len() as c_int;
        }
    }
    0
}

/// Get peak level for a specific track in dB
/// 
/// # Arguments
/// * `track` - Track index (0-based)
/// 
/// # Returns
/// Peak level in dB (0.0 = unity gain, negative = below unity, positive = above)
/// Returns -96.0 if track index is invalid or meters not initialized
#[no_mangle]
pub extern "C" fn daw_meter_get_track_peak(track: c_int) -> c_float {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            return s.get_track_peak(track as usize);
        }
    }
    -96.0
}

/// Get RMS level for a specific track in dB
/// 
/// # Arguments
/// * `track` - Track index (0-based)
/// 
/// # Returns
/// RMS level in dB (0.0 = unity gain, negative = below unity, positive = above)
/// Returns -96.0 if track index is invalid or meters not initialized
#[no_mangle]
pub extern "C" fn daw_meter_get_track_rms(track: c_int) -> c_float {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            return s.get_track_rms(track as usize);
        }
    }
    -96.0
}

/// Get both peak and RMS levels for a track
/// 
/// # Arguments
/// * `track` - Track index (0-based)
/// * `peak_out` - Pointer to store peak level (can be null)
/// * `rms_out` - Pointer to store RMS level (can be null)
/// 
/// # Returns
/// 0 on success, -1 if meters not initialized or track invalid
#[no_mangle]
pub extern "C" fn daw_meter_get_track_levels(track: c_int, peak_out: *mut c_float, rms_out: *mut c_float) -> c_int {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            let track_idx = track as usize;
            if track_idx >= s.track_levels.len() {
                return -1;
            }
            
            if !peak_out.is_null() {
                unsafe { *peak_out = s.get_track_peak(track_idx); }
            }
            if !rms_out.is_null() {
                unsafe { *rms_out = s.get_track_rms(track_idx); }
            }
            return 0;
        }
    }
    -1
}

/// Get master output peak level in dB
#[no_mangle]
pub extern "C" fn daw_meter_get_master_peak() -> c_float {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            return s.get_master_peak();
        }
    }
    -96.0
}

/// Get master output RMS level in dB
#[no_mangle]
pub extern "C" fn daw_meter_get_master_rms() -> c_float {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            return s.get_master_rms();
        }
    }
    -96.0
}

/// Get both peak and RMS levels for master output
/// 
/// # Arguments
/// * `peak_out` - Pointer to store peak level (can be null)
/// * `rms_out` - Pointer to store RMS level (can be null)
/// 
/// # Returns
/// 0 on success, -1 if meters not initialized
#[no_mangle]
pub extern "C" fn daw_meter_get_master_levels(peak_out: *mut c_float, rms_out: *mut c_float) -> c_int {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            if !peak_out.is_null() {
                unsafe { *peak_out = s.get_master_peak(); }
            }
            if !rms_out.is_null() {
                unsafe { *rms_out = s.get_master_rms(); }
            }
            return 0;
        }
    }
    -1
}

// =============================================================================
// Internal API for Audio Thread (not exposed via FFI)
// =============================================================================

/// Update track peak level (called from audio thread)
pub fn update_track_peak(track: usize, peak_db: f32) {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            s.update_track_peak(track, peak_db);
        }
    }
}

/// Update track RMS level (called from audio thread)
pub fn update_track_rms(track: usize, rms_db: f32) {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            s.update_track_rms(track, rms_db);
        }
    }
}

/// Update master peak level (called from audio thread)
pub fn update_master_peak(peak_db: f32) {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            s.update_master_peak(peak_db);
        }
    }
}

/// Update master RMS level (called from audio thread)
pub fn update_master_rms(rms_db: f32) {
    if let Ok(state) = METER_STATE.read() {
        if let Some(ref s) = *state {
            s.update_master_rms(rms_db);
        }
    }
}

/// Reset meter state (test-only)
#[cfg(test)]
pub fn reset_meter_state() {
    if let Ok(mut state) = METER_STATE.write() {
        *state = None;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    // Serial test guard to prevent parallel test conflicts
    static TEST_GUARD: Mutex<()> = Mutex::new(());

    #[test]
    fn test_meter_init() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_meter_state();
        daw_meter_init(8);
        assert_eq!(daw_meter_get_track_count(), 8);
    }

    #[test]
    fn test_track_level_update_and_get() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_meter_state();
        daw_meter_init(4);
        
        // Update track 0 levels
        update_track_peak(0, -6.0);
        update_track_rms(0, -12.0);
        
        // Verify retrieval
        assert_eq!(daw_meter_get_track_peak(0), -6.0);
        assert_eq!(daw_meter_get_track_rms(0), -12.0);
    }

    #[test]
    fn test_invalid_track_returns_silence() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_meter_state();
        daw_meter_init(4);
        assert_eq!(daw_meter_get_track_peak(99), -96.0);
        assert_eq!(daw_meter_get_track_rms(99), -96.0);
    }

    #[test]
    fn test_master_level_update() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_meter_state();
        daw_meter_init(4);
        
        update_master_peak(-3.0);
        update_master_rms(-9.0);
        
        assert_eq!(daw_meter_get_master_peak(), -3.0);
        assert_eq!(daw_meter_get_master_rms(), -9.0);
    }

    #[test]
    fn test_get_track_levels_pointer() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_meter_state();
        daw_meter_init(4);
        update_track_peak(1, -6.0);
        update_track_rms(1, -18.0);
        
        let mut peak: c_float = 0.0;
        let mut rms: c_float = 0.0;
        
        let result = daw_meter_get_track_levels(1, &mut peak, &mut rms);
        assert_eq!(result, 0);
        assert_eq!(peak, -6.0);
        assert_eq!(rms, -18.0);
    }

    #[test]
    fn test_get_master_levels_pointer() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_meter_state();
        daw_meter_init(4);
        update_master_peak(-1.5);
        update_master_rms(-6.0);
        
        let mut peak: c_float = 0.0;
        let mut rms: c_float = 0.0;
        
        let result = daw_meter_get_master_levels(&mut peak, &mut rms);
        assert_eq!(result, 0);
        assert_eq!(peak, -1.5);
        assert_eq!(rms, -6.0);
    }

    #[test]
    fn test_invalid_track_levels_returns_error() {
        let _guard = TEST_GUARD.lock().unwrap();
        reset_meter_state();
        daw_meter_init(4);
        let mut peak: c_float = 0.0;
        let result = daw_meter_get_track_levels(99, &mut peak, std::ptr::null_mut());
        assert_eq!(result, -1);
    }
}
