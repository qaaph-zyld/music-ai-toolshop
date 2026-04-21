//! FFI Bridge - C-compatible interface for JUCE UI integration
//!
//! This module provides a C ABI for the Rust audio engine,
//! allowing the JUCE C++ UI to control playback, mixing, and session state.

use std::ffi::{c_char, c_double, c_float, c_int, c_void, CStr, CString};
use std::sync::{Arc, Mutex, atomic::{AtomicPtr, Ordering}};
use std::sync::mpsc::{channel, Sender, Receiver};

use crate::mixer::Mixer;
use crate::project::Project;
use crate::session::{SessionView, ClipState};
use crate::transport::{Transport, TransportState};
use crate::midi_input::{MidiDeviceEnumerator, MidiInput};

// ============================================================================
// FFI Callback Types for JUCE UI-to-Engine Connection (Step B)
// ============================================================================

/// Transport state callback type (0=stopped, 1=playing, 2=recording, 3=paused)
pub type TransportStateCallback = extern "C" fn(state: c_int);

/// Level meter callback type (track index, peak dB)
pub type LevelMeterCallback = extern "C" fn(track: c_int, db: c_float);

/// Clip state callback type (track, scene, state: 0=empty, 1=loaded, 2=playing, 3=recording, 4=queued)
pub type ClipStateCallback = extern "C" fn(track: c_int, scene: c_int, state: c_int);

/// Position callback type (bars, beats, sixteenths)
pub type PositionCallback = extern "C" fn(bars: c_int, beats: c_int, sixteenths: c_int);

/// Global callback storage (thread-safe, lock-free)
static TRANSPORT_CALLBACK: AtomicPtr<()> = AtomicPtr::new(std::ptr::null_mut());
static METER_CALLBACK: AtomicPtr<()> = AtomicPtr::new(std::ptr::null_mut());
static CLIP_CALLBACK: AtomicPtr<()> = AtomicPtr::new(std::ptr::null_mut());
static POSITION_CALLBACK: AtomicPtr<()> = AtomicPtr::new(std::ptr::null_mut());

/// Register transport state callback
#[no_mangle]
pub extern "C" fn daw_register_transport_callback(callback: Option<TransportStateCallback>) {
    let ptr = callback.map(|f| f as *mut ()).unwrap_or(std::ptr::null_mut());
    TRANSPORT_CALLBACK.store(ptr, Ordering::Release);
}

/// Register level meter callback
#[no_mangle]
pub extern "C" fn daw_register_meter_callback(callback: Option<LevelMeterCallback>) {
    let ptr = callback.map(|f| f as *mut ()).unwrap_or(std::ptr::null_mut());
    METER_CALLBACK.store(ptr, Ordering::Release);
}

/// Register clip state callback
#[no_mangle]
pub extern "C" fn daw_register_clip_callback(callback: Option<ClipStateCallback>) {
    let ptr = callback.map(|f| f as *mut ()).unwrap_or(std::ptr::null_mut());
    CLIP_CALLBACK.store(ptr, Ordering::Release);
}

/// Register position callback
#[no_mangle]
pub extern "C" fn daw_register_position_callback(callback: Option<PositionCallback>) {
    let ptr = callback.map(|f| f as *mut ()).unwrap_or(std::ptr::null_mut());
    POSITION_CALLBACK.store(ptr, Ordering::Release);
}

/// Internal: Invoke transport callback (called from transport module)
pub fn invoke_transport_callback(state: TransportState) {
    let ptr = TRANSPORT_CALLBACK.load(Ordering::Acquire);
    if !ptr.is_null() {
        let callback: TransportStateCallback = unsafe { std::mem::transmute(ptr) };
        let state_int = match state {
            TransportState::Stopped => 0,
            TransportState::Playing => 1,
            TransportState::Recording => 2,
            TransportState::Paused => 3,
        };
        callback(state_int);
    }
}

/// Internal: Invoke meter callback (called from mixer audio thread)
pub fn invoke_meter_callback(track: usize, db: f32) {
    let ptr = METER_CALLBACK.load(Ordering::Acquire);
    if !ptr.is_null() {
        let callback: LevelMeterCallback = unsafe { std::mem::transmute(ptr) };
        callback(track as c_int, db);
    }
}

/// Internal: Invoke clip callback (called from session module)
pub fn invoke_clip_callback(track: usize, scene: usize, state: Option<ClipState>) {
    let ptr = CLIP_CALLBACK.load(Ordering::Acquire);
    if !ptr.is_null() {
        let callback: ClipStateCallback = unsafe { std::mem::transmute(ptr) };
        let state_int = match state {
            None => 0, // Empty slot
            Some(ClipState::Stopped) => 1,
            Some(ClipState::Queued) => 2,
            Some(ClipState::Playing) => 3,
            Some(ClipState::Recording) => 4,
        };
        callback(track as c_int, scene as c_int, state_int);
    }
}

/// Internal: Invoke position callback (called from transport audio thread)
pub fn invoke_position_callback(position_beats: f32) {
    let ptr = POSITION_CALLBACK.load(Ordering::Acquire);
    if !ptr.is_null() {
        let callback: PositionCallback = unsafe { std::mem::transmute(ptr) };
        // Convert beats to bars.beats.sixteenths (assuming 4/4 time, 16th = 1/4 beat)
        let bars = (position_beats / 4.0) as c_int;
        let beats_in_bar = position_beats % 4.0;
        let beats = beats_in_bar as c_int;
        let sixteenths = ((beats_in_bar - beats as f32) * 4.0) as c_int;
        callback(bars, beats, sixteenths);
    }
}

/// Opaque handle to the audio engine
pub struct DawEngine {
    _sample_rate: f64,
    _buffer_size: usize,
    _session: Arc<Mutex<SessionView>>,
    _project: Arc<Mutex<Project>>,
    transport: Arc<Mutex<Transport>>,
    mixer: Arc<Mutex<Mixer>>,
    command_sender: Sender<EngineCommand>,
}

/// Commands sent from UI to engine
#[derive(Debug, Clone)]
pub enum EngineCommand {
    Play,
    Stop,
    Record,
    SetPosition(f32),
    SetTempo(f32),
    LaunchClip(usize, usize),
    StopClip(usize, usize),
    LoadClip(usize, usize, String),
    SetVolume(usize, f32),
    SetPan(usize, f32),
    SetMute(usize, bool),
    SetSolo(usize, bool),
    ArmTrack(usize, bool),
    LaunchScene(usize),
    StopAll,
}

/// Initialize the audio engine
/// 
/// # Safety
/// Must be called before any other FFI functions. Returns opaque engine handle.
#[no_mangle]
pub extern "C" fn daw_engine_init(_sample_rate: c_int, _buffer_size: c_int) -> *mut c_void {
    let transport = Arc::new(Mutex::new(Transport::new(120.0, 48000)));
    let mixer = Arc::new(Mutex::new(Mixer::new(2)));
    let session = Arc::new(Mutex::new(SessionView::new(8, 8)));
    let project = Arc::new(Mutex::new(Project::new("Untitled")));
    
    let (command_sender, command_receiver): (Sender<EngineCommand>, Receiver<EngineCommand>) = channel();
    
    let engine = Box::new(DawEngine {
        _sample_rate: 48000.0,
        _buffer_size: 512,
        _session: session,
        _project: project,
        transport,
        mixer,
        command_sender,
    });
    
    // Start command processing thread
    std::thread::spawn(move || {
        command_processing_loop(command_receiver);
    });
    
    Box::into_raw(engine) as *mut c_void
}

/// Shutdown and free the audio engine
///
/// # Safety
/// Must be called exactly once per engine handle. Handle is invalid after call.
#[no_mangle]
pub unsafe extern "C" fn daw_engine_shutdown(engine_ptr: *mut c_void) {
    if engine_ptr.is_null() {
        return;
    }
    
    let _engine = Box::from_raw(engine_ptr as *mut DawEngine);
    // Engine is dropped here, cleaning up resources
}

/// Process pending commands (call from audio thread)
///
/// # Safety
/// Engine pointer must be valid. Not thread-safe - call only from audio thread.
#[no_mangle]
pub unsafe extern "C" fn daw_engine_process_commands(engine_ptr: *mut c_void) {
    if engine_ptr.is_null() {
        return;
    }
    
    let _engine = &*(engine_ptr as *mut DawEngine);
    
    // Process any pending commands
    // In a real implementation, this would drain a lock-free queue
    // For now, commands are handled by the processing thread
}

/// Process audio (call from audio callback)
///
/// # Safety
/// Engine pointer must be valid. output buffer must be valid with length samples * 2 (stereo).
#[no_mangle]
pub unsafe extern "C" fn daw_engine_process_audio(
    engine_ptr: *mut c_void,
    output: *mut c_float,
    samples: c_int,
) {
    if engine_ptr.is_null() || output.is_null() {
        return;
    }
    
    let engine = &*(engine_ptr as *mut DawEngine);
    let len = samples as usize * 2; // Stereo interleaved
    
    let output_slice = std::slice::from_raw_parts_mut(output, len);
    
    // Get transport state and advance
    if let Ok(mut transport) = engine.transport.lock() {
        transport.process(samples as u32);
    }
    
    // Process audio through mixer
    if let Ok(mut mixer) = engine.mixer.lock() {
        mixer.process(output_slice);
    }
}

/// Transport controls
#[no_mangle]
pub extern "C" fn daw_transport_play(engine_ptr: *mut c_void) {
    send_command(engine_ptr, EngineCommand::Play);
}

#[no_mangle]
pub extern "C" fn daw_transport_stop(engine_ptr: *mut c_void) {
    send_command(engine_ptr, EngineCommand::Stop);
}

#[no_mangle]
pub extern "C" fn daw_transport_record(engine_ptr: *mut c_void) {
    send_command(engine_ptr, EngineCommand::Record);
}

#[no_mangle]
pub extern "C" fn daw_transport_set_position(engine_ptr: *mut c_void, beats: c_float) {
    send_command(engine_ptr, EngineCommand::SetPosition(beats));
}

#[no_mangle]
pub extern "C" fn daw_transport_set_tempo(engine_ptr: *mut c_void, bpm: c_float) {
    send_command(engine_ptr, EngineCommand::SetTempo(bpm));
}

#[no_mangle]
pub extern "C" fn daw_transport_get_position(engine_ptr: *mut c_void) -> c_float {
    get_transport_state(engine_ptr, |t| t.position_beats())
}

#[no_mangle]
pub extern "C" fn daw_transport_get_tempo(engine_ptr: *mut c_void) -> c_float {
    get_transport_state(engine_ptr, |t| t.tempo())
}

#[no_mangle]
pub extern "C" fn daw_transport_is_playing(engine_ptr: *mut c_void) -> c_int {
    get_transport_state(engine_ptr, |t| matches!(t.state(), TransportState::Playing) as i32)
}

/// Clip controls
#[no_mangle]
pub extern "C" fn daw_session_launch_clip(engine_ptr: *mut c_void, track: c_int, scene: c_int) {
    send_command(engine_ptr, EngineCommand::LaunchClip(track as usize, scene as usize));
}

#[no_mangle]
pub extern "C" fn daw_session_stop_clip(engine_ptr: *mut c_void, track: c_int, scene: c_int) {
    send_command(engine_ptr, EngineCommand::StopClip(track as usize, scene as usize));
}

#[no_mangle]
pub unsafe extern "C" fn daw_session_load_clip(
    engine_ptr: *mut c_void,
    track: c_int,
    scene: c_int,
    file_path: *const c_char,
) {
    if file_path.is_null() {
        return;
    }
    
    let path = CStr::from_ptr(file_path).to_string_lossy().to_string();
    send_command(engine_ptr, EngineCommand::LoadClip(track as usize, scene as usize, path));
}

#[no_mangle]
pub extern "C" fn daw_session_launch_scene(engine_ptr: *mut c_void, scene: c_int) {
    send_command(engine_ptr, EngineCommand::LaunchScene(scene as usize));
}

#[no_mangle]
pub extern "C" fn daw_session_stop_all(engine_ptr: *mut c_void) {
    send_command(engine_ptr, EngineCommand::StopAll);
}

/// Mixer controls
#[no_mangle]
pub extern "C" fn daw_mixer_set_volume(engine_ptr: *mut c_void, track: c_int, db: c_float) {
    send_command(engine_ptr, EngineCommand::SetVolume(track as usize, db));
}

#[no_mangle]
pub extern "C" fn daw_mixer_set_pan(engine_ptr: *mut c_void, track: c_int, pan: c_float) {
    send_command(engine_ptr, EngineCommand::SetPan(track as usize, pan));
}

#[no_mangle]
pub extern "C" fn daw_mixer_set_mute(engine_ptr: *mut c_void, track: c_int, muted: c_int) {
    send_command(engine_ptr, EngineCommand::SetMute(track as usize, muted != 0));
}

#[no_mangle]
pub extern "C" fn daw_mixer_set_solo(engine_ptr: *mut c_void, track: c_int, soloed: c_int) {
    send_command(engine_ptr, EngineCommand::SetSolo(track as usize, soloed != 0));
}

/// Track controls
#[no_mangle]
pub extern "C" fn daw_track_set_armed(engine_ptr: *mut c_void, track: c_int, armed: c_int) {
    send_command(engine_ptr, EngineCommand::ArmTrack(track as usize, armed != 0));
}

// Helper functions

fn send_command(engine_ptr: *mut c_void, cmd: EngineCommand) {
    if engine_ptr.is_null() {
        return;
    }
    
    unsafe {
        let engine = &*(engine_ptr as *mut DawEngine);
        let _ = engine.command_sender.send(cmd);
    }
}

fn get_transport_state<T>(engine_ptr: *mut c_void, f: impl FnOnce(&Transport) -> T) -> T {
    if engine_ptr.is_null() {
        return f(&Transport::new(120.0, 48000));
    }
    
    unsafe {
        let engine = &*(engine_ptr as *mut DawEngine);
        if let Ok(transport) = engine.transport.lock() {
            f(&*transport)
        } else {
            f(&Transport::new(120.0, 48000))
        }
    }
}

fn command_processing_loop(receiver: Receiver<EngineCommand>) {
    while let Ok(cmd) = receiver.recv() {
        match cmd {
            EngineCommand::Play => {
                // Process play command
            }
            EngineCommand::Stop => {
                // Process stop command
            }
            EngineCommand::Record => {
                // Process record command
            }
            EngineCommand::SetPosition(_beats) => {
                // Set transport position
            }
            EngineCommand::SetTempo(_bpm) => {
                // Set transport tempo
            }
            EngineCommand::LaunchClip(_track, _scene) => {
                // Launch clip at track, scene
            }
            EngineCommand::StopClip(_track, _scene) => {
                // Stop clip at track, scene
            }
            EngineCommand::LoadClip(_track, _scene, _path) => {
                // Load audio file into clip slot
            }
            EngineCommand::SetVolume(_track, _db) => {
                // Set track volume
            }
            EngineCommand::SetPan(_track, _pan) => {
                // Set track pan
            }
            EngineCommand::SetMute(_track, _muted) => {
                // Set track mute state
            }
            EngineCommand::SetSolo(_track, _soloed) => {
                // Set track solo state
            }
            EngineCommand::ArmTrack(_track, _armed) => {
                // Set track armed state
            }
            EngineCommand::LaunchScene(_scene) => {
                // Launch all clips in scene
            }
            EngineCommand::StopAll => {
                // Stop all clips
            }
        }
    }
}

// ============================================================================
// Reverse Engineering Module - FFI Exports
// ============================================================================

use crate::reverse_engineer::{SpectralAnalyzer, DeltaAnalyzer};

/// Opaque handle to spectral analyzer
pub struct SpectralAnalyzerHandle {
    analyzer: SpectralAnalyzer,
}

/// Create a new spectral analyzer
/// 
/// # Safety
/// Returns opaque handle. Must be freed with `daw_spectral_free()`.
#[no_mangle]
pub extern "C" fn daw_spectral_create(fft_size: c_int, sample_rate: c_float) -> *mut c_void {
    let analyzer = SpectralAnalyzer::new(fft_size as usize, sample_rate);
    let handle = Box::new(SpectralAnalyzerHandle { analyzer });
    Box::into_raw(handle) as *mut c_void
}

/// Free spectral analyzer
/// 
/// # Safety
/// Handle must be valid and not already freed.
#[no_mangle]
pub unsafe extern "C" fn daw_spectral_free(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut SpectralAnalyzerHandle);
    }
}

/// Analyze audio buffer and return spectral features
/// 
/// # Safety
/// `buffer` must be valid with `buffer_len` samples. `features_out` must point to 10 floats.
#[no_mangle]
pub unsafe extern "C" fn daw_spectral_analyze(
    handle: *mut c_void,
    buffer: *const c_float,
    buffer_len: c_int,
    features_out: *mut c_float,
) -> c_int {
    if handle.is_null() || buffer.is_null() || features_out.is_null() {
        return -1;
    }
    
    let handle = &mut *(handle as *mut SpectralAnalyzerHandle);
    let buffer_slice = std::slice::from_raw_parts(buffer, buffer_len as usize);
    
    let features = handle.analyzer.analyze(buffer_slice);
    
    // Write features to output array
    let out = std::slice::from_raw_parts_mut(features_out, 10);
    out[0] = features.spectral_centroid;
    out[1] = features.spectral_rolloff;
    out[2] = features.spectral_flux;
    out[3] = features.spectral_flatness;
    out[4] = features.crest_factor;
    out[5] = features.rms_db;
    out[6] = features.peak_db;
    out[7] = features.lufs_estimate;
    out[8] = features.zero_crossing_rate;
    out[9] = features.bandwidth;
    
    0 // Success
}

/// Opaque handle to delta analyzer
pub struct DeltaAnalyzerHandle {
    analyzer: DeltaAnalyzer,
}

/// Create a new delta analyzer
#[no_mangle]
pub extern "C" fn daw_delta_create(fft_size: c_int, sample_rate: c_float) -> *mut c_void {
    let analyzer = DeltaAnalyzer::new(fft_size as usize, sample_rate);
    let handle = Box::new(DeltaAnalyzerHandle { analyzer });
    Box::into_raw(handle) as *mut c_void
}

/// Free delta analyzer
#[no_mangle]
pub unsafe extern "C" fn daw_delta_free(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut DeltaAnalyzerHandle);
    }
}

/// Compare two audio buffers and detect processing
/// 
/// # Safety
/// Both buffers must be valid. `detection_out` must point to valid memory.
#[no_mangle]
pub unsafe extern "C" fn daw_delta_compare(
    handle: *mut c_void,
    dry_buffer: *const c_float,
    dry_len: c_int,
    processed_buffer: *const c_float,
    processed_len: c_int,
    correlation_out: *mut c_float,
    crest_change_out: *mut c_float,
    compression_detected_out: *mut c_int,
    limiting_detected_out: *mut c_int,
) -> c_int {
    if handle.is_null() || dry_buffer.is_null() || processed_buffer.is_null() {
        return -1;
    }
    
    let handle = &mut *(handle as *mut DeltaAnalyzerHandle);
    let dry = std::slice::from_raw_parts(dry_buffer, dry_len as usize);
    let processed = std::slice::from_raw_parts(processed_buffer, processed_len as usize);
    
    let (delta, detection) = handle.analyzer.compare(dry, processed);
    
    if !correlation_out.is_null() {
        *correlation_out = delta.correlation;
    }
    if !crest_change_out.is_null() {
        *crest_change_out = delta.crest_factor_change_db;
    }
    if !compression_detected_out.is_null() {
        *compression_detected_out = if detection.compression_confidence > 0.5 { 1 } else { 0 };
    }
    if !limiting_detected_out.is_null() {
        *limiting_detected_out = if detection.limiting_detected { 1 } else { 0 };
    }
    
    0 // Success
}

// ============================================================================
// MIDI Device and Recording FFI (Step A)
// ============================================================================

/// C-compatible MIDI device info structure
#[repr(C)]
pub struct MidiDeviceInfoFFI {
    pub id: [c_char; 64],
    pub name: [c_char; 128],
    pub is_available: c_int,
}

/// C-compatible MIDI note structure
#[repr(C)]
pub struct MidiNoteFFI {
    pub pitch: c_int,
    pub velocity: c_int,
    pub start_beat: c_float,
    pub duration_beats: c_float,
}

/// Global MIDI input manager (singleton for FFI)
static MIDI_INPUT: once_cell::sync::Lazy<Arc<Mutex<MidiInput>>> = 
    once_cell::sync::Lazy::new(|| {
        Arc::new(Mutex::new(MidiInput::new(16, 48000)))
    });

/// Get count of available MIDI input devices
#[no_mangle]
pub extern "C" fn daw_midi_device_count() -> c_int {
    MidiDeviceEnumerator::device_count() as c_int
}

/// Get MIDI device info by index
/// 
/// # Safety
/// `info_out` must point to valid MidiDeviceInfoFFI struct. Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_midi_device_info(index: c_int, info_out: *mut MidiDeviceInfoFFI) -> c_int {
    if info_out.is_null() || index < 0 {
        return -1;
    }
    
    let devices = MidiDeviceEnumerator::list_input_devices();
    let idx = index as usize;
    
    if idx >= devices.len() {
        return -1;
    }
    
    let device = &devices[idx];
    let ffi_info = &mut *info_out;
    
    // Copy ID (truncate if needed)
    let id_bytes = device.id.as_bytes();
    let id_len = id_bytes.len().min(63);
    ffi_info.id[..id_len].copy_from_slice(&id_bytes[..id_len].iter().map(|&b| b as c_char).collect::<Vec<_>>());
    ffi_info.id[id_len] = 0; // Null terminate
    
    // Copy name (truncate if needed)
    let name_bytes = device.name.as_bytes();
    let name_len = name_bytes.len().min(127);
    ffi_info.name[..name_len].copy_from_slice(&name_bytes[..name_len].iter().map(|&b| b as c_char).collect::<Vec<_>>());
    ffi_info.name[name_len] = 0; // Null terminate
    
    ffi_info.is_available = if device.is_available { 1 } else { 0 };
    
    0 // Success
}

/// Start MIDI recording from specified beat position
#[no_mangle]
pub extern "C" fn daw_midi_start_recording(start_beat: c_float) {
    if let Ok(mut midi_input) = MIDI_INPUT.lock() {
        midi_input.start_recording(start_beat);
    }
}

/// Stop MIDI recording and get recorded notes
/// 
/// # Safety
/// `notes_out` receives pointer to allocated array (caller must free with daw_midi_free_notes).
/// Returns note count. Returns -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_midi_stop_recording(notes_out: *mut *mut MidiNoteFFI) -> c_int {
    if notes_out.is_null() {
        return -1;
    }
    
    let notes = match MIDI_INPUT.lock() {
        Ok(mut midi_input) => midi_input.stop_recording(),
        Err(_) => return -1,
    };
    
    let count = notes.len();
    if count == 0 {
        *notes_out = std::ptr::null_mut();
        return 0;
    }
    
    // Allocate array of FFI notes
    let ffi_notes: Vec<MidiNoteFFI> = notes.iter().map(|n| MidiNoteFFI {
        pitch: n.pitch() as c_int,
        velocity: n.velocity() as c_int,
        start_beat: n.start_beat(),
        duration_beats: n.duration_beats(),
    }).collect();
    
    // Convert to raw pointer (caller frees)
    let ptr = ffi_notes.as_ptr() as *mut MidiNoteFFI;
    std::mem::forget(ffi_notes); // Prevent drop, ownership transferred to caller
    
    *notes_out = ptr;
    count as c_int
}

/// Free notes array allocated by daw_midi_stop_recording
/// 
/// # Safety
/// Must be called exactly once per notes array from daw_midi_stop_recording.
#[no_mangle]
pub unsafe extern "C" fn daw_midi_free_notes(notes: *mut MidiNoteFFI, count: c_int) {
    if notes.is_null() || count <= 0 {
        return;
    }
    
    // Reconstruct Vec to drop properly
    let _ = Vec::from_raw_parts(notes, count as usize, count as usize);
}

/// Check if MIDI recording is active
#[no_mangle]
pub extern "C" fn daw_midi_is_recording() -> c_int {
    match MIDI_INPUT.lock() {
        Ok(midi_input) => if midi_input.is_recording() { 1 } else { 0 },
        Err(_) => 0,
    }
}

// ============================================================================
// Project Save/Load FFI (Step C)
// ============================================================================

use crate::serialization::{save_project_to_file, load_project_from_file};
use std::path::Path;

/// Last error message from save/load operations
static LAST_ERROR: once_cell::sync::Lazy<Mutex<String>> = 
    once_cell::sync::Lazy::new(|| Mutex::new(String::new()));

/// Save project to file
/// 
/// # Safety
/// `file_path` must be a valid null-terminated UTF-8 string.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_project_save(
    engine_ptr: *mut c_void,
    file_path: *const c_char,
) -> c_int {
    if engine_ptr.is_null() || file_path.is_null() {
        store_error("Null pointer provided");
        return -1;
    }
    
    let engine = &*(engine_ptr as *mut DawEngine);
    let path_str = match CStr::from_ptr(file_path).to_str() {
        Ok(s) => s,
        Err(_) => {
            store_error("Invalid UTF-8 in path");
            return -1;
        }
    };
    
    let path = Path::new(path_str);
    
    // Lock required components
    let project = match engine._project.lock() {
        Ok(p) => p,
        Err(_) => {
            store_error("Failed to lock project");
            return -1;
        }
    };
    
    let transport = match engine.transport.lock() {
        Ok(t) => t,
        Err(_) => {
            store_error("Failed to lock transport");
            return -1;
        }
    };
    
    let session = match engine._session.lock() {
        Ok(s) => s,
        Err(_) => {
            store_error("Failed to lock session");
            return -1;
        }
    };
    
    let mixer = match engine.mixer.lock() {
        Ok(m) => m,
        Err(_) => {
            store_error("Failed to lock mixer");
            return -1;
        }
    };
    
    match save_project_to_file(&*project, &*transport, &*session, &*mixer, path) {
        Ok(_) => 0,
        Err(e) => {
            store_error(&format!("Save failed: {}", e));
            -1
        }
    }
}

/// Load project from file
/// 
/// # Safety
/// `file_path` must be a valid null-terminated UTF-8 string.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_project_load(
    _engine_ptr: *mut c_void,
    file_path: *const c_char,
) -> c_int {
    if file_path.is_null() {
        store_error("Null pointer provided");
        return -1;
    }
    
    let path_str = match CStr::from_ptr(file_path).to_str() {
        Ok(s) => s,
        Err(_) => {
            store_error("Invalid UTF-8 in path");
            return -1;
        }
    };
    
    let path = Path::new(path_str);
    
    match load_project_from_file(path) {
        Ok(_project) => {
            // TODO: Apply loaded project to engine state
            // This requires mutable access to engine components
            0
        }
        Err(e) => {
            store_error(&format!("Load failed: {}", e));
            -1
        }
    }
}

/// Get last error message from save/load operations
/// 
/// # Safety
/// Returns pointer to static string. Do not free. Check for null.
#[no_mangle]
pub extern "C" fn daw_project_last_error() -> *const c_char {
    match LAST_ERROR.lock() {
        Ok(err) => {
            if err.is_empty() {
                std::ptr::null()
            } else {
                // Leak the CString to keep it alive (caller must not free)
                let c_string = match CString::new(err.clone()) {
                    Ok(cs) => cs,
                    Err(_) => return std::ptr::null(),
                };
                c_string.into_raw()
            }
        }
        Err(_) => std::ptr::null(),
    }
}

fn store_error(msg: &str) {
    if let Ok(mut err) = LAST_ERROR.lock() {
        *err = msg.to_string();
    }
}

// ============================================================================
// Stem Separation FFI (Step E)
// ============================================================================

use crate::stem_separation::{StemSeparator, StemSeparationResult, StemType};

/// Opaque handle to stem separator
pub struct StemSeparatorHandle {
    separator: StemSeparator,
    result: Option<StemSeparationResult>,
    progress: f64,
    complete: bool,
}

/// Create a new stem separator
/// 
/// # Safety
/// Returns opaque handle. Must be freed with `daw_stem_free()`.
#[no_mangle]
pub extern "C" fn daw_stem_separator_create() -> *mut c_void {
    let handle = Box::new(StemSeparatorHandle {
        separator: StemSeparator::new(),
        result: None,
        progress: 0.0,
        complete: false,
    });
    Box::into_raw(handle) as *mut c_void
}

/// Free stem separator handle
/// 
/// # Safety
/// Handle must be valid and not already freed.
#[no_mangle]
pub unsafe extern "C" fn daw_stem_separator_free(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut StemSeparatorHandle);
    }
}

/// Check if demucs is available for stem separation
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_stem_is_available(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }
    
    let handle = &*(handle as *mut StemSeparatorHandle);
    if handle.separator.is_available() { 1 } else { 0 }
}

/// Separate audio file into stems
/// 
/// # Safety
/// `input_path` and `output_dir` must be valid null-terminated UTF-8 strings.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_stem_separate(
    handle: *mut c_void,
    input_path: *const c_char,
    output_dir: *const c_char,
) -> c_int {
    if handle.is_null() || input_path.is_null() || output_dir.is_null() {
        store_error("Null pointer provided");
        return -1;
    }
    
    let handle = &mut *(handle as *mut StemSeparatorHandle);
    
    let input_str = match CStr::from_ptr(input_path).to_str() {
        Ok(s) => s,
        Err(_) => {
            store_error("Invalid UTF-8 in input path");
            return -1;
        }
    };
    
    let output_str = match CStr::from_ptr(output_dir).to_str() {
        Ok(s) => s,
        Err(_) => {
            store_error("Invalid UTF-8 in output path");
            return -1;
        }
    };
    
    match handle.separator.separate(input_str, output_str) {
        Ok(result) => {
            handle.result = Some(result);
            handle.complete = true;
            handle.progress = 1.0;
            0
        }
        Err(e) => {
            store_error(&format!("Stem separation failed: {}", e));
            -1
        }
    }
}

/// Get separation progress (0.0 to 1.0)
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_stem_get_progress(handle: *mut c_void) -> c_double {
    if handle.is_null() {
        return 0.0;
    }
    
    let handle = &*(handle as *mut StemSeparatorHandle);
    handle.progress
}

/// Check if separation is complete
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_stem_is_complete(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }
    
    let handle = &*(handle as *mut StemSeparatorHandle);
    if handle.complete { 1 } else { 0 }
}

/// Get stem file path by type
/// Types: 0=vocals, 1=drums, 2=bass, 3=other
/// 
/// # Safety
/// Returns pointer to static string. Do not free. Check for null.
#[no_mangle]
pub unsafe extern "C" fn daw_stem_get_path(
    handle: *mut c_void,
    stem_type: c_int,
) -> *const c_char {
    if handle.is_null() {
        return std::ptr::null();
    }
    
    let handle = &*(handle as *mut StemSeparatorHandle);
    
    let stem_type_enum = match stem_type {
        0 => StemType::Vocals,
        1 => StemType::Drums,
        2 => StemType::Bass,
        3 => StemType::Other,
        _ => return std::ptr::null(),
    };
    
    if let Some(ref result) = handle.result {
        if let Some(path) = result.get_path(stem_type_enum) {
            if let Some(path_str) = path.to_str() {
                if let Ok(c_string) = CString::new(path_str) {
                    return c_string.into_raw();
                }
            }
        }
    }
    
    std::ptr::null()
}

/// Cancel ongoing separation
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_stem_cancel(handle: *mut c_void) {
    if handle.is_null() {
        return;
    }
    
    let handle = &*(handle as *mut StemSeparatorHandle);
    handle.separator.cancel();
}

// ============================================================================
// Audio Device Management FFI (Task 12.1)
// ============================================================================

use crate::audio_device::AudioDeviceManager;

/// Opaque handle to audio device manager
pub struct AudioDeviceManagerHandle {
    manager: AudioDeviceManager,
}

/// Create audio device manager
/// 
/// # Safety
/// Returns opaque handle. Must be freed with `daw_audio_device_manager_free()`.
#[no_mangle]
pub extern "C" fn daw_audio_device_manager_create() -> *mut c_void {
    let handle = Box::new(AudioDeviceManagerHandle {
        manager: AudioDeviceManager::new(),
    });
    Box::into_raw(handle) as *mut c_void
}

/// Free audio device manager handle
/// 
/// # Safety
/// Handle must be valid and not already freed.
#[no_mangle]
pub unsafe extern "C" fn daw_audio_device_manager_free(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut AudioDeviceManagerHandle);
    }
}

/// Get number of audio output devices
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_audio_device_count(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }
    
    let handle = &*(handle as *mut AudioDeviceManagerHandle);
    handle.manager.device_count()
}

/// Get audio device name by index
/// 
/// # Safety
/// Handle must be valid. `name_out` must point to 256-byte buffer.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_audio_device_name(
    handle: *mut c_void,
    index: c_int,
    name_out: *mut c_char,
    name_len: c_int,
) -> c_int {
    if handle.is_null() || name_out.is_null() || index < 0 {
        return -1;
    }
    
    let handle = &*(handle as *mut AudioDeviceManagerHandle);
    
    if let Some(device) = handle.manager.device_info(index) {
        let name_bytes = device.name.as_bytes();
        let max_len = (name_len as usize).saturating_sub(1);
        let copy_len = name_bytes.len().min(max_len);
        
        for (i, &byte) in name_bytes[..copy_len].iter().enumerate() {
            *name_out.add(i) = byte as c_char;
        }
        *name_out.add(copy_len) = 0; // Null terminate
        
        0 // Success
    } else {
        -1 // Invalid index
    }
}

/// Check if audio stream is currently running
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_audio_is_streaming(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }
    
    let handle = &*(handle as *mut AudioDeviceManagerHandle);
    if handle.manager.is_streaming() { 1 } else { 0 }
}

// ============================================================================
// Export Audio FFI (Phase 7.4)
// ============================================================================

use crate::export::{ExportEngine, ExportFormat, BitDepth};
use std::path::PathBuf;

/// Opaque handle to export operation
pub struct ExportHandle {
    engine: Option<ExportEngine>,
    progress: f64,
    complete: bool,
    cancelled: bool,
    result: i32, // 0=in_progress, 1=success, 2=cancelled, 3=error
    output_path: Option<PathBuf>,
}

/// Export format constants
pub const EXPORT_FORMAT_WAV_16: c_int = 0;
pub const EXPORT_FORMAT_WAV_24: c_int = 1;
pub const EXPORT_FORMAT_WAV_32: c_int = 2;

/// Create a new export handle
/// 
/// # Safety
/// Returns opaque handle. Must be freed with `daw_export_destroy()`.
#[no_mangle]
pub extern "C" fn daw_export_create() -> *mut c_void {
    let handle = Box::new(ExportHandle {
        engine: None,
        progress: 0.0,
        complete: false,
        cancelled: false,
        result: 0,
        output_path: None,
    });
    Box::into_raw(handle) as *mut c_void
}

/// Configure export parameters
/// 
/// # Safety
/// `file_path` must be a valid null-terminated UTF-8 string.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_export_configure(
    handle: *mut c_void,
    file_path: *const c_char,
    format: c_int,
    sample_rate: c_int,
    _stem_export: c_int,
) -> c_int {
    if handle.is_null() || file_path.is_null() {
        return -1;
    }
    
    let handle = &mut *(handle as *mut ExportHandle);
    
    let path_str = match CStr::from_ptr(file_path).to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };
    
    // Parse format
    let bit_depth = match format {
        EXPORT_FORMAT_WAV_16 => BitDepth::Bit16,
        EXPORT_FORMAT_WAV_24 => BitDepth::Bit24,
        EXPORT_FORMAT_WAV_32 => BitDepth::Bit32Float,
        _ => BitDepth::Bit24, // Default
    };
    
    // Create export format
    let export_format = ExportFormat::Wav(bit_depth);
    
    // Create transport, mixer, session for export engine
    let transport = Transport::new(120.0, sample_rate as u32);
    let mixer = Mixer::new(2); // Stereo
    let session = SessionView::new(8, 8); // Default 8x8 session
    
    let engine = ExportEngine::new(
        sample_rate as u32,
        2, // Stereo
        export_format,
        transport,
        mixer,
        session,
    );
    
    handle.engine = Some(engine);
    handle.output_path = Some(PathBuf::from(path_str));
    
    0 // Success
}

/// Start the export process
/// 
/// # Safety
/// Handle must be valid and configured.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_export_start(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return -1;
    }
    
    let handle = &mut *(handle as *mut ExportHandle);
    
    if handle.engine.is_none() {
        return -1;
    }
    
    // Start export in a way that allows progress polling
    // For now, mark as started (actual rendering happens in get_progress calls)
    handle.progress = 0.0;
    handle.complete = false;
    handle.result = 0; // In progress
    
    0 // Success
}

/// Get export progress (0.0 to 1.0)
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_export_get_progress(handle: *mut c_void) -> c_double {
    if handle.is_null() {
        return 0.0;
    }
    
    let handle = &mut *(handle as *mut ExportHandle);
    
    if handle.cancelled {
        return 0.0;
    }
    
    // Simulate progress for now - in full implementation,
    // this would poll the actual engine progress
    if !handle.complete && handle.engine.is_some() {
        handle.progress += 0.01; // Increment for polling simulation
        if handle.progress >= 1.0 {
            handle.progress = 1.0;
            handle.complete = true;
            handle.result = 1; // Success
        }
    }
    
    handle.progress
}

/// Check if export is complete
/// 
/// # Safety
/// Handle must be valid.
/// Returns 1 if complete, 0 if not.
#[no_mangle]
pub unsafe extern "C" fn daw_export_is_complete(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }
    
    let handle = &*(handle as *mut ExportHandle);
    if handle.complete { 1 } else { 0 }
}

/// Cancel ongoing export
/// 
/// # Safety
/// Handle must be valid.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_export_cancel(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return -1;
    }
    
    let handle = &mut *(handle as *mut ExportHandle);
    handle.cancelled = true;
    handle.complete = true;
    handle.result = 2; // Cancelled
    
    0 // Success
}

/// Get export result
/// Returns: 0 = in progress, 1 = success, 2 = cancelled, 3 = error
/// 
/// # Safety
/// Handle must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_export_get_result(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 3; // Error
    }
    
    let handle = &*(handle as *mut ExportHandle);
    handle.result
}

/// Destroy export handle and free resources
/// 
/// # Safety
/// Handle must be valid and not already freed.
#[no_mangle]
pub unsafe extern "C" fn daw_export_destroy(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut ExportHandle);
    }
}

// ============================================================================
// MMM Pattern Generation FFI (Phase 8.3)
// ============================================================================

use crate::mmm::{MusicMotionMachine, PatternStyle, MidiPattern};

/// Opaque handle to MMM pattern generator
pub struct MmmHandle {
    machine: Option<MusicMotionMachine>,
    current_pattern: Option<MidiPattern>,
    style: String,
}

/// Pattern style constants
pub const MMM_STYLE_ELECTRONIC: c_int = 0;
pub const MMM_STYLE_HOUSE: c_int = 1;
pub const MMM_STYLE_TECHNO: c_int = 2;
pub const MMM_STYLE_AMBIENT: c_int = 3;
pub const MMM_STYLE_JAZZ: c_int = 4;
pub const MMM_STYLE_HIPHOP: c_int = 5;
pub const MMM_STYLE_ROCK: c_int = 6;

/// Pattern type constants
pub const MMM_PATTERN_DRUMS: c_int = 0;
pub const MMM_PATTERN_BASS: c_int = 1;
pub const MMM_PATTERN_MELODY: c_int = 2;

/// Check if MMM is available
#[no_mangle]
pub extern "C" fn daw_mmm_is_available() -> c_int {
    if MusicMotionMachine::is_available() { 1 } else { 0 }
}

/// Create a new MMM handle
///
/// # Safety
/// Returns opaque handle. Must be freed with `daw_mmm_destroy()`.
#[no_mangle]
pub extern "C" fn daw_mmm_create() -> *mut c_void {
    let handle = Box::new(MmmHandle {
        machine: None,
        current_pattern: None,
        style: String::new(),
    });
    Box::into_raw(handle) as *mut c_void
}

/// Load a style model
///
/// # Safety
/// `handle` must be valid. `style` must be a valid null-terminated UTF-8 string.
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_load_style(
    handle: *mut c_void,
    style: *const c_char,
) -> c_int {
    if handle.is_null() || style.is_null() {
        return -1;
    }

    let handle = &mut *(handle as *mut MmmHandle);

    let style_str = match CStr::from_ptr(style).to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };

    let pattern_style = match style_str.to_lowercase().as_str() {
        "electronic" => PatternStyle::Electronic,
        "house" => PatternStyle::House,
        "techno" => PatternStyle::Techno,
        "ambient" => PatternStyle::Ambient,
        "jazz" => PatternStyle::Jazz,
        "hiphop" => PatternStyle::HipHop,
        "rock" => PatternStyle::Rock,
        _ => PatternStyle::Electronic, // Default
    };

    match MusicMotionMachine::new(pattern_style) {
        Ok(machine) => {
            handle.machine = Some(machine);
            handle.style = style_str.to_string();
            0
        }
        Err(_) => -1,
    }
}

/// Generate a pattern
///
/// # Safety
/// `handle` must be valid with loaded style.
/// `key` must be valid null-terminated UTF-8 string (for melody).
/// `chords` must be valid null-terminated UTF-8 string comma-separated (for bass).
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_generate(
    handle: *mut c_void,
    pattern_type: c_int,
    bars: c_int,
    bpm: c_float,
    key: *const c_char,
    chords: *const c_char,
) -> c_int {
    if handle.is_null() {
        return -1;
    }

    let handle = &mut *(handle as *mut MmmHandle);

    if handle.machine.is_none() {
        return -1;
    }

    let machine = handle.machine.as_ref().unwrap();

    let result = match pattern_type {
        MMM_PATTERN_DRUMS => {
            machine.generate_drums(bars as usize, bpm)
        }
        MMM_PATTERN_BASS => {
            if chords.is_null() {
                return -1;
            }
            let chords_str = match CStr::from_ptr(chords).to_str() {
                Ok(s) => s,
                Err(_) => return -1,
            };
            let chord_vec: Vec<&str> = chords_str.split(',').collect();
            machine.generate_bass(&chord_vec, bars as usize)
        }
        MMM_PATTERN_MELODY => {
            let key_str = if key.is_null() { "C" } else {
                match CStr::from_ptr(key).to_str() {
                    Ok(s) => s,
                    Err(_) => "C",
                }
            };
            machine.generate_melody(key_str, "major", bars as usize)
        }
        _ => return -1,
    };

    match result {
        Ok(pattern) => {
            handle.current_pattern = Some(pattern);
            0
        }
        Err(_) => -1,
    }
}

/// Get the number of notes in current pattern
///
/// # Safety
/// `handle` must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_get_note_count(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return 0;
    }

    let handle = &*(handle as *mut MmmHandle);

    match &handle.current_pattern {
        Some(pattern) => pattern.notes.len() as c_int,
        None => 0,
    }
}

/// Get note data from current pattern
///
/// # Safety
/// `handle` must be valid. Arrays must be allocated with at least note_count elements.
/// Returns number of notes written.
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_get_notes(
    handle: *mut c_void,
    pitches: *mut c_int,
    velocities: *mut c_int,
    start_beats: *mut c_float,
    duration_beats: *mut c_float,
    max_notes: c_int,
) -> c_int {
    if handle.is_null() || pitches.is_null() || velocities.is_null()
        || start_beats.is_null() || duration_beats.is_null() {
        return 0;
    }

    let handle = &*(handle as *mut MmmHandle);

    match &handle.current_pattern {
        Some(pattern) => {
            let count = pattern.notes.len().min(max_notes as usize);
            for i in 0..count {
                let note = &pattern.notes[i];
                *pitches.add(i) = note.pitch as c_int;
                *velocities.add(i) = note.velocity as c_int;
                *start_beats.add(i) = note.start_beat;
                *duration_beats.add(i) = note.duration_beats;
            }
            count as c_int
        }
        None => 0,
    }
}

/// Get pattern duration in beats
///
/// # Safety
/// `handle` must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_get_duration_beats(handle: *mut c_void) -> c_float {
    if handle.is_null() {
        return 0.0;
    }

    let handle = &*(handle as *mut MmmHandle);

    match &handle.current_pattern {
        Some(pattern) => pattern.duration_beats,
        None => 0.0,
    }
}

/// Get current pattern track name
///
/// # Safety
/// `handle` must be valid. `buffer` must be allocated with at least `max_len` bytes.
/// Returns number of characters written (excluding null terminator).
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_get_track_name(
    handle: *mut c_void,
    buffer: *mut c_char,
    max_len: c_int,
) -> c_int {
    if handle.is_null() || buffer.is_null() || max_len <= 0 {
        return 0;
    }

    let handle = &*(handle as *mut MmmHandle);

    match &handle.current_pattern {
        Some(pattern) => {
            let name = &pattern.track_name;
            let bytes = name.as_bytes();
            let len = bytes.len().min((max_len - 1) as usize);
            std::ptr::copy_nonoverlapping(bytes.as_ptr() as *const c_char, buffer, len);
            *buffer.add(len) = 0; // Null terminator
            len as c_int
        }
        None => {
            *buffer = 0;
            0
        }
    }
}

/// Clear current pattern
///
/// # Safety
/// `handle` must be valid.
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_clear_pattern(handle: *mut c_void) -> c_int {
    if handle.is_null() {
        return -1;
    }

    let handle = &mut *(handle as *mut MmmHandle);
    handle.current_pattern = None;
    0
}

/// Destroy MMM handle
///
/// # Safety
/// `handle` must be valid and not already freed.
#[no_mangle]
pub unsafe extern "C" fn daw_mmm_destroy(handle: *mut c_void) {
    if !handle.is_null() {
        let _ = Box::from_raw(handle as *mut MmmHandle);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_init_shutdown() {
        unsafe {
            let engine = daw_engine_init(48000, 512);
            assert!(!engine.is_null());
            daw_engine_shutdown(engine);
        }
    }

    #[test]
    fn test_transport_commands() {
        unsafe {
            let engine = daw_engine_init(48000, 512);
            assert!(!engine.is_null());

            daw_transport_play(engine);
            daw_transport_stop(engine);
            daw_transport_set_tempo(engine, 128.0);
            daw_transport_set_position(engine, 4.0);

            let tempo = daw_transport_get_tempo(engine);
            assert!((tempo - 120.0).abs() < 0.01); // Default tempo (not yet updated)

            daw_engine_shutdown(engine);
        }
    }

    #[test]
    fn test_session_commands() {
        unsafe {
            let engine = daw_engine_init(48000, 512);
            assert!(!engine.is_null());

            daw_session_launch_clip(engine, 0, 0);
            daw_session_stop_clip(engine, 0, 0);
            daw_session_launch_scene(engine, 0);
            daw_session_stop_all(engine);

            daw_engine_shutdown(engine);
        }
    }

    #[test]
    fn test_mixer_commands() {
        unsafe {
            let engine = daw_engine_init(48000, 512);
            assert!(!engine.is_null());

            daw_mixer_set_volume(engine, 0, 0.0);
            daw_mixer_set_pan(engine, 0, 0.0);
            daw_mixer_set_mute(engine, 0, 1);
            daw_mixer_set_solo(engine, 0, 0);

            daw_engine_shutdown(engine);
        }
    }

    #[test]
    fn test_null_safety() {
        // These should not crash with null pointer
        daw_transport_play(std::ptr::null_mut());
        daw_transport_stop(std::ptr::null_mut());
        daw_session_launch_clip(std::ptr::null_mut(), 0, 0);
        daw_mixer_set_volume(std::ptr::null_mut(), 0, 0.0);
    }

    #[test]
    fn test_spectral_ffi() {
        unsafe {
            // Create analyzer
            let analyzer = daw_spectral_create(2048, 44100.0);
            assert!(!analyzer.is_null());
            
            // Generate sine wave
            let buffer: Vec<f32> = (0..2048)
                .map(|i| {
                    let phase = 2.0 * std::f32::consts::PI * 1000.0 * i as f32 / 44100.0;
                    phase.sin() * 0.5
                })
                .collect();
            
            // Analyze
            let mut features = [0.0f32; 10];
            let result = daw_spectral_analyze(
                analyzer,
                buffer.as_ptr(),
                buffer.len() as c_int,
                features.as_mut_ptr(),
            );
            assert_eq!(result, 0);
            
            // Check centroid is near 1000 Hz
            assert!(features[0] > 500.0 && features[0] < 1500.0, 
                "Centroid {} should be near 1000 Hz", features[0]);
            
            // Free analyzer
            daw_spectral_free(analyzer);
        }
    }

    #[test]
    fn test_delta_ffi() {
        unsafe {
            // Create analyzer
            let analyzer = daw_delta_create(2048, 44100.0);
            assert!(!analyzer.is_null());
            
            // Generate identical buffers
            let dry: Vec<f32> = (0..2048)
                .map(|i| {
                    let phase = 2.0 * std::f32::consts::PI * 1000.0 * i as f32 / 44100.0;
                    phase.sin() * 0.5
                })
                .collect();
            let processed = dry.clone();
            
            // Compare
            let mut correlation = 0.0f32;
            let mut crest_change = 0.0f32;
            let mut compression = 0i32;
            let mut limiting = 0i32;
            
            let result = daw_delta_compare(
                analyzer,
                dry.as_ptr(),
                dry.len() as c_int,
                processed.as_ptr(),
                processed.len() as c_int,
                &mut correlation,
                &mut crest_change,
                &mut compression,
                &mut limiting,
            );
            assert_eq!(result, 0);
            
            // Identical signals should have high correlation
            assert!(correlation > 0.99, "Correlation should be ~1.0 for identical signals");
            assert_eq!(compression, 0, "No compression on identical signals");
            assert_eq!(limiting, 0, "No limiting on identical signals");
            
            // Free analyzer
            daw_delta_free(analyzer);
        }
    }

    #[test]
    fn test_spectral_null_safety() {
        unsafe {
            // These should not crash
            daw_spectral_free(std::ptr::null_mut());
            
            let mut features = [0.0f32; 10];
            let result = daw_spectral_analyze(
                std::ptr::null_mut(),
                std::ptr::null(),
                0,
                features.as_mut_ptr(),
            );
            assert_eq!(result, -1);
        }
    }

    // MIDI FFI Tests (Step A)
    
    #[test]
    fn test_midi_device_count() {
        let count = daw_midi_device_count();
        // Should be >= 0 (could be 0 if no MIDI devices)
        assert!(count >= 0, "Device count should be non-negative");
    }

    #[test]
    fn test_midi_device_info() {
        let count = daw_midi_device_count();
        
        for i in 0..count {
            let mut info = MidiDeviceInfoFFI {
                id: [0; 64],
                name: [0; 128],
                is_available: 0,
            };
            
            unsafe {
                let result = daw_midi_device_info(i, &mut info);
                assert_eq!(result, 0, "Should succeed for valid index");
                
                // Verify non-empty name
                let name_len = info.name.iter().position(|&c| c == 0).unwrap_or(128);
                assert!(name_len > 0, "Device name should not be empty");
                
                // Should be available
                assert_eq!(info.is_available, 1, "Device should be available");
            }
        }
    }

    #[test]
    fn test_midi_device_info_invalid_index() {
        let count = daw_midi_device_count();
        let mut info = MidiDeviceInfoFFI {
            id: [0; 64],
            name: [0; 128],
            is_available: 0,
        };
        
        unsafe {
            let result = daw_midi_device_info(count, &mut info);
            assert_eq!(result, -1, "Should fail for out of bounds index");
        }
    }

    #[test]
    fn test_midi_recording_via_ffi() {
        // Test recording lifecycle via FFI
        assert_eq!(daw_midi_is_recording(), 0, "Should not be recording initially");
        
        // Start recording
        daw_midi_start_recording(0.0);
        assert_eq!(daw_midi_is_recording(), 1, "Should be recording after start");
        
        // Stop recording (no notes recorded)
        unsafe {
            let mut notes: *mut MidiNoteFFI = std::ptr::null_mut();
            let count = daw_midi_stop_recording(&mut notes);
            assert_eq!(count, 0, "Should have 0 notes (no MIDI input)");
            assert!(notes.is_null(), "Notes pointer should be null for empty recording");
        }
        
        assert_eq!(daw_midi_is_recording(), 0, "Should not be recording after stop");
    }

    #[test]
    fn test_midi_recording_null_safety() {
        // These should not crash
        assert_eq!(daw_midi_device_count(), 0); // Just check it doesn't panic
        
        unsafe {
            // Null pointer for device info
            let result = daw_midi_device_info(0, std::ptr::null_mut());
            assert_eq!(result, -1);
            
            // Null pointer for stop recording
            let result = daw_midi_stop_recording(std::ptr::null_mut());
            assert_eq!(result, -1);
            
            // Free null notes (should not crash)
            daw_midi_free_notes(std::ptr::null_mut(), 0);
            daw_midi_free_notes(std::ptr::null_mut(), -1);
        }
    }

    // ============================================================================
    // FFI Callback Tests (Step B)
    // ============================================================================

    use std::sync::atomic::{AtomicI32, AtomicUsize, Ordering as AtomicOrdering};

    static TEST_TRANSPORT_STATE: AtomicI32 = AtomicI32::new(-1);
    static TEST_METER_TRACK: AtomicI32 = AtomicI32::new(-1);
    static TEST_METER_DB: AtomicI32 = AtomicI32::new(0);
    static TEST_CLIP_TRACK: AtomicI32 = AtomicI32::new(-1);
    static TEST_CLIP_SCENE: AtomicI32 = AtomicI32::new(-1);
    static TEST_CLIP_STATE: AtomicI32 = AtomicI32::new(-1);
    static TEST_POS_BARS: AtomicI32 = AtomicI32::new(-1);
    static TEST_POS_BEATS: AtomicI32 = AtomicI32::new(-1);
    static TEST_POS_SIXTEENTHS: AtomicI32 = AtomicI32::new(-1);
    static TEST_CALLBACK_COUNT: AtomicUsize = AtomicUsize::new(0);

    extern "C" fn test_transport_callback(state: c_int) {
        TEST_TRANSPORT_STATE.store(state, AtomicOrdering::SeqCst);
        TEST_CALLBACK_COUNT.fetch_add(1, AtomicOrdering::SeqCst);
    }

    extern "C" fn test_meter_callback(track: c_int, db: c_float) {
        TEST_METER_TRACK.store(track, AtomicOrdering::SeqCst);
        TEST_METER_DB.store((db * 100.0) as i32, AtomicOrdering::SeqCst);
        TEST_CALLBACK_COUNT.fetch_add(1, AtomicOrdering::SeqCst);
    }

    extern "C" fn test_clip_callback(track: c_int, scene: c_int, state: c_int) {
        TEST_CLIP_TRACK.store(track, AtomicOrdering::SeqCst);
        TEST_CLIP_SCENE.store(scene, AtomicOrdering::SeqCst);
        TEST_CLIP_STATE.store(state, AtomicOrdering::SeqCst);
        TEST_CALLBACK_COUNT.fetch_add(1, AtomicOrdering::SeqCst);
    }

    extern "C" fn test_position_callback(bars: c_int, beats: c_int, sixteenths: c_int) {
        TEST_POS_BARS.store(bars, AtomicOrdering::SeqCst);
        TEST_POS_BEATS.store(beats, AtomicOrdering::SeqCst);
        TEST_POS_SIXTEENTHS.store(sixteenths, AtomicOrdering::SeqCst);
        TEST_CALLBACK_COUNT.fetch_add(1, AtomicOrdering::SeqCst);
    }

    fn reset_callback_state() {
        TEST_TRANSPORT_STATE.store(-1, AtomicOrdering::SeqCst);
        TEST_METER_TRACK.store(-1, AtomicOrdering::SeqCst);
        TEST_METER_DB.store(0, AtomicOrdering::SeqCst);
        TEST_CLIP_TRACK.store(-1, AtomicOrdering::SeqCst);
        TEST_CLIP_SCENE.store(-1, AtomicOrdering::SeqCst);
        TEST_CLIP_STATE.store(-1, AtomicOrdering::SeqCst);
        TEST_POS_BARS.store(-1, AtomicOrdering::SeqCst);
        TEST_POS_BEATS.store(-1, AtomicOrdering::SeqCst);
        TEST_POS_SIXTEENTHS.store(-1, AtomicOrdering::SeqCst);
        TEST_CALLBACK_COUNT.store(0, AtomicOrdering::SeqCst);
    }

    #[test]
    fn test_transport_callback_registration() {
        reset_callback_state();
        
        // Register callback
        daw_register_transport_callback(Some(test_transport_callback));
        
        // Invoke transport callback
        invoke_transport_callback(TransportState::Playing);
        
        // Verify callback was called
        assert_eq!(TEST_TRANSPORT_STATE.load(AtomicOrdering::SeqCst), 1, "Should receive Playing state (1)");
        assert_eq!(TEST_CALLBACK_COUNT.load(AtomicOrdering::SeqCst), 1, "Callback should be called once");
        
        // Test other states
        invoke_transport_callback(TransportState::Stopped);
        assert_eq!(TEST_TRANSPORT_STATE.load(AtomicOrdering::SeqCst), 0, "Should receive Stopped state (0)");
        
        invoke_transport_callback(TransportState::Recording);
        assert_eq!(TEST_TRANSPORT_STATE.load(AtomicOrdering::SeqCst), 2, "Should receive Recording state (2)");
        
        invoke_transport_callback(TransportState::Paused);
        assert_eq!(TEST_TRANSPORT_STATE.load(AtomicOrdering::SeqCst), 3, "Should receive Paused state (3)");
        
        // Unregister
        daw_register_transport_callback(None);
        invoke_transport_callback(TransportState::Playing);
        // State should remain unchanged since callback is unregistered
        assert_eq!(TEST_TRANSPORT_STATE.load(AtomicOrdering::SeqCst), 3, "State should be unchanged after unregister");
    }

    #[test]
    fn test_meter_callback_registration() {
        reset_callback_state();
        
        // Register callback
        daw_register_meter_callback(Some(test_meter_callback));
        
        // Invoke meter callback
        invoke_meter_callback(3, -12.5);
        
        // Verify callback was called
        assert_eq!(TEST_METER_TRACK.load(AtomicOrdering::SeqCst), 3, "Track should be 3");
        assert_eq!(TEST_METER_DB.load(AtomicOrdering::SeqCst), -1250, "dB should be -12.5 * 100 = -1250");
        
        // Unregister
        daw_register_meter_callback(None);
    }

    #[test]
    fn test_clip_callback_registration() {
        reset_callback_state();
        
        // Register callback
        daw_register_clip_callback(Some(test_clip_callback));
        
        // Invoke clip callback with different states
        invoke_clip_callback(2, 5, Some(ClipState::Playing));
        
        // Verify callback was called
        assert_eq!(TEST_CLIP_TRACK.load(AtomicOrdering::SeqCst), 2, "Track should be 2");
        assert_eq!(TEST_CLIP_SCENE.load(AtomicOrdering::SeqCst), 5, "Scene should be 5");
        assert_eq!(TEST_CLIP_STATE.load(AtomicOrdering::SeqCst), 3, "State should be Playing (3)");
        
        // Test all clip states
        invoke_clip_callback(0, 0, None); // Empty slot
        assert_eq!(TEST_CLIP_STATE.load(AtomicOrdering::SeqCst), 0, "Should be Empty (0)");
        
        invoke_clip_callback(1, 1, Some(ClipState::Stopped));
        assert_eq!(TEST_CLIP_STATE.load(AtomicOrdering::SeqCst), 1, "Should be Stopped (1)");
        
        invoke_clip_callback(2, 2, Some(ClipState::Queued));
        assert_eq!(TEST_CLIP_STATE.load(AtomicOrdering::SeqCst), 2, "Should be Queued (2)");
        
        invoke_clip_callback(3, 7, Some(ClipState::Recording));
        assert_eq!(TEST_CLIP_STATE.load(AtomicOrdering::SeqCst), 4, "Should be Recording (4)");
        
        // Unregister
        daw_register_clip_callback(None);
    }

    #[test]
    fn test_position_callback_registration() {
        reset_callback_state();
        
        // Register callback
        daw_register_position_callback(Some(test_position_callback));
        
        // Invoke position callback at bar 5, beat 2, sixteenth 1
        // Position: 5*4 + 2 + 0.25 = 22.25 beats
        invoke_position_callback(22.25);
        
        // Verify callback was called
        assert_eq!(TEST_POS_BARS.load(AtomicOrdering::SeqCst), 5, "Bars should be 5");
        assert_eq!(TEST_POS_BEATS.load(AtomicOrdering::SeqCst), 2, "Beats should be 2");
        assert_eq!(TEST_POS_SIXTEENTHS.load(AtomicOrdering::SeqCst), 1, "Sixteenths should be 1");
        
        // Test position 0
        invoke_position_callback(0.0);
        assert_eq!(TEST_POS_BARS.load(AtomicOrdering::SeqCst), 0, "Bars should be 0");
        assert_eq!(TEST_POS_BEATS.load(AtomicOrdering::SeqCst), 0, "Beats should be 0");
        assert_eq!(TEST_POS_SIXTEENTHS.load(AtomicOrdering::SeqCst), 0, "Sixteenths should be 0");
        
        // Test position 3.75 beats (bar 0, beat 3, sixteenth 3)
        invoke_position_callback(3.75);
        assert_eq!(TEST_POS_BARS.load(AtomicOrdering::SeqCst), 0, "Bars should be 0");
        assert_eq!(TEST_POS_BEATS.load(AtomicOrdering::SeqCst), 3, "Beats should be 3");
        assert_eq!(TEST_POS_SIXTEENTHS.load(AtomicOrdering::SeqCst), 3, "Sixteenths should be 3");
        
        // Unregister
        daw_register_position_callback(None);
    }

    #[test]
    fn test_null_callback_registration() {
        // Registering null should not crash
        daw_register_transport_callback(None);
        daw_register_meter_callback(None);
        daw_register_clip_callback(None);
        daw_register_position_callback(None);
        
        // Invoking with null registered should not crash
        invoke_transport_callback(TransportState::Playing);
        invoke_meter_callback(0, -6.0);
        invoke_clip_callback(0, 0, Some(ClipState::Playing));
        invoke_clip_callback(0, 0, None); // Empty slot
        invoke_position_callback(4.0);
        
        // If we get here, null callbacks handled safely
    }

    #[test]
    fn test_callback_re_registration() {
        reset_callback_state();
        
        // Register first callback
        daw_register_transport_callback(Some(test_transport_callback));
        invoke_transport_callback(TransportState::Playing);
        assert_eq!(TEST_CALLBACK_COUNT.load(AtomicOrdering::SeqCst), 1);
        
        // Re-register should replace, not add
        daw_register_transport_callback(Some(test_transport_callback));
        invoke_transport_callback(TransportState::Stopped);
        assert_eq!(TEST_CALLBACK_COUNT.load(AtomicOrdering::SeqCst), 2);
        
        // Unregister
        daw_register_transport_callback(None);
    }

    // Stem Separation FFI Tests (Step E)

    #[test]
    fn test_stem_separator_ffi_lifecycle() {
        unsafe {
            // Create separator
            let handle = daw_stem_separator_create();
            assert!(!handle.is_null());

            // Check availability (will be 0 in test env without demucs)
            let available = daw_stem_is_available(handle);
            assert!(available == 0 || available == 1);

            // Check initial state
            assert_eq!(daw_stem_is_complete(handle), 0);
            assert_eq!(daw_stem_get_progress(handle), 0.0);

            // Free handle
            daw_stem_separator_free(handle);
        }
    }

    #[test]
    fn test_stem_separator_null_safety() {
        unsafe {
            // Null handle operations should not crash
            daw_stem_separator_free(std::ptr::null_mut());
            assert_eq!(daw_stem_is_available(std::ptr::null_mut()), 0);
            assert_eq!(daw_stem_is_complete(std::ptr::null_mut()), 0);
            assert_eq!(daw_stem_get_progress(std::ptr::null_mut()), 0.0);
            daw_stem_cancel(std::ptr::null_mut());
            assert!(daw_stem_get_path(std::ptr::null_mut(), 0).is_null());

            // Null path should fail gracefully
            let handle = daw_stem_separator_create();
            assert!(!handle.is_null());
            
            let result = daw_stem_separate(handle, std::ptr::null(), std::ptr::null());
            assert_eq!(result, -1);

            daw_stem_separator_free(handle);
        }
    }

    // MMM Pattern Generation FFI Tests (Phase 8.3)

    #[test]
    fn test_mmm_ffi_lifecycle() {
        unsafe {
            // Check availability (will be 0 in test env without MMM backend)
            let available = daw_mmm_is_available();
            assert!(available == 0 || available == 1);

            // Create handle
            let handle = daw_mmm_create();
            assert!(!handle.is_null());

            // Check initial state
            assert_eq!(daw_mmm_get_note_count(handle), 0);
            assert_eq!(daw_mmm_get_duration_beats(handle), 0.0);

            // Clear pattern (should succeed even with no pattern)
            assert_eq!(daw_mmm_clear_pattern(handle), 0);

            // Destroy handle
            daw_mmm_destroy(handle);
        }
    }

    #[test]
    fn test_mmm_ffi_null_safety() {
        unsafe {
            // Null handle operations should not crash
            daw_mmm_destroy(std::ptr::null_mut());
            assert_eq!(daw_mmm_is_available(), 0); // Doesn't take handle
            assert_eq!(daw_mmm_get_note_count(std::ptr::null_mut()), 0);
            assert_eq!(daw_mmm_get_duration_beats(std::ptr::null_mut()), 0.0);
            assert_eq!(daw_mmm_clear_pattern(std::ptr::null_mut()), -1);

            // Null string operations should fail gracefully
            let handle = daw_mmm_create();
            assert!(!handle.is_null());

            let result = daw_mmm_load_style(handle, std::ptr::null());
            assert_eq!(result, -1);

            let result = daw_mmm_generate(handle, MMM_PATTERN_DRUMS, 4, 128.0, std::ptr::null(), std::ptr::null());
            // Should fail because no style loaded
            assert_eq!(result, -1);

            daw_mmm_destroy(handle);
        }
    }

    #[test]
    fn test_mmm_ffi_style_loading() {
        unsafe {
            let handle = daw_mmm_create();
            assert!(!handle.is_null());

            // Try to load various styles
            let style_electronic = std::ffi::CString::new("electronic").unwrap();
            let result = daw_mmm_load_style(handle, style_electronic.as_ptr());
            // Will fail in test env without MMM backend, but should not crash
            assert!(result == 0 || result == -1);

            // Try other styles
            let style_techno = std::ffi::CString::new("techno").unwrap();
            let result = daw_mmm_load_style(handle, style_techno.as_ptr());
            assert!(result == 0 || result == -1);

            daw_mmm_destroy(handle);
        }
    }

    #[test]
    fn test_mmm_ffi_get_track_name() {
        unsafe {
            let handle = daw_mmm_create();
            assert!(!handle.is_null());

            let mut buffer = vec![0u8; 256];
            let len = daw_mmm_get_track_name(
                handle,
                buffer.as_mut_ptr() as *mut c_char,
                buffer.len() as c_int,
            );
            // Should return 0 when no pattern is loaded
            assert_eq!(len, 0);
            assert_eq!(buffer[0], 0); // Null terminator

            daw_mmm_destroy(handle);
        }
    }
}
