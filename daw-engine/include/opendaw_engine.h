/**
 * OpenDAW Engine C API
 *
 * FFI interface for JUCE C++ UI integration.
 * All functions use C ABI for cross-language compatibility.
 * 
 * This header matches the Rust FFI exports from engine_ffi.rs, clip_player_ffi.rs,
 * transport_sync_ffi.rs, midi_ffi.rs, meter_ffi.rs, and project_ffi.rs
 */

#ifndef DAW_ENGINE_H
#define DAW_ENGINE_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Types
// ============================================================================

/// Opaque handle to engine instance
typedef void* DawEngineHandle;

/// Opaque handle to transport sync
typedef void* DawTransportSyncHandle;

/// Opaque handle to clip player
typedef void* DawClipPlayerHandle;

/// MIDI device info structure
typedef struct {
    char id[64];
    char name[128];
    int is_available;
} DawMidiDeviceInfo;

/// MIDI note structure
typedef struct {
    int pitch;
    int velocity;
    float start_beat;
    float duration_beats;
} DawMidiNote;

// ============================================================================
// Engine Lifecycle (engine_ffi.rs)
// ============================================================================

/**
 * Initialize the audio engine
 * @param sample_rate Sample rate in Hz (e.g., 48000)
 * @param buffer_size Buffer size in samples (e.g., 512)
 * @return Engine handle or NULL on error
 */
void* opendaw_engine_init(int sample_rate, int buffer_size);

/**
 * Shutdown and free the audio engine
 * @param engine Engine handle from opendaw_engine_init
 */
void opendaw_engine_shutdown(void* engine);

// ============================================================================
// Transport Controls (engine_ffi.rs)
// ============================================================================

/**
 * Start playback
 */
void opendaw_transport_play(void* engine);

/**
 * Stop playback
 */
void opendaw_transport_stop(void* engine);

/**
 * Start recording
 */
void opendaw_transport_record(void* engine);

/**
 * Set playback position in beats
 */
void opendaw_transport_set_position(void* engine, double beats);

/**
 * Get current playback position in beats
 */
double opendaw_transport_get_position(void* engine);

/**
 * Set tempo in BPM
 */
void opendaw_transport_set_bpm(void* engine, float bpm);

/**
 * Get current tempo in BPM
 */
float opendaw_transport_get_bpm(void* engine);

/**
 * Check if transport is playing (returns 0 or 1)
 */
int opendaw_transport_is_playing(void* engine);

/**
 * Check if transport is recording (returns 0 or 1)
 */
int opendaw_transport_is_recording(void* engine);

// ============================================================================
// Session/Scene/Clip Controls (engine_ffi.rs + clip_player_ffi.rs)
// ============================================================================

/**
 * Launch all clips in a scene
 */
void opendaw_scene_launch(void* engine, int scene);

/**
 * Stop all clips
 */
void opendaw_stop_all_clips(void* engine);

/**
 * Play a specific clip at track/scene
 */
void opendaw_clip_play(void* engine, int track, int scene);

/**
 * Stop clips on a specific track
 */
void opendaw_clip_stop(void* engine, int track, int scene);

/**
 * Get clip state (0=stopped, 1=playing, 2=recording, -1=no clip)
 */
int opendaw_clip_get_state(void* engine, int track, int scene);

/**
 * Get current scene index (-1 if none)
 */
int opendaw_session_get_current_scene(void* engine);

// Clip Player FFI (clip_player_ffi.rs)
void* opendaw_clip_player_init(void* session_ptr);
void opendaw_clip_player_shutdown(void* handle);
int opendaw_clip_player_trigger_clip(void* engine, int track_idx, int clip_idx);
int opendaw_clip_player_stop_clip(void* engine, int track_idx);
int opendaw_clip_player_get_state(void* engine, int track_idx, int clip_idx, int* state_out);
int opendaw_clip_player_queue_clip(void* engine, int track_idx, int clip_idx);
int opendaw_clip_player_stop_all(void* engine);
int opendaw_clip_player_get_position(void* engine, int track_idx, double* position_out);
int opendaw_clip_player_is_playing(void* engine, int track_idx, int* playing_out);
int opendaw_clip_player_get_playing_clip(void* engine, int track_idx, int* clip_idx_out);

// ============================================================================
// Transport Sync / Scheduling (transport_sync_ffi.rs)
// ============================================================================

void* opendaw_transport_sync_init(float sample_rate, float tempo);
void opendaw_transport_sync_shutdown(void* handle);
void opendaw_transport_sync_set_tempo(void* handle, float tempo);
float opendaw_transport_sync_get_tempo(void* handle);
int opendaw_transport_sync_schedule_clip(void* handle, size_t track_idx, size_t clip_idx, 
                                           double target_beat, int looped);
int opendaw_transport_sync_schedule_clip_quantized(void* handle, size_t track_idx, size_t clip_idx,
                                                    double current_beat, int quantization, int looped);
int opendaw_transport_sync_process(void* handle, double current_beat, 
                                     double* triggered_clips_out, size_t max_clips);
void opendaw_transport_sync_cancel_track(void* handle, size_t track_idx);
void opendaw_transport_sync_cancel_clip(void* handle, size_t track_idx, size_t clip_idx);
void opendaw_transport_sync_clear_all(void* handle);
int opendaw_transport_sync_pending_count(void* handle);
int opendaw_transport_sync_is_track_scheduled(void* handle, size_t track_idx);
double opendaw_transport_sync_next_scheduled_beat(void* handle, size_t track_idx);
double opendaw_transport_sync_beats_until_next(void* handle, size_t track_idx, double current_beat);

// Global transport sync accessors
double opendaw_get_current_beat(void);
void opendaw_set_tempo(float bpm);
float opendaw_get_tempo(void);
int opendaw_get_last_triggered_clip(int* track_out, int* clip_out);
void opendaw_reset_callback_count(void);
int opendaw_get_callback_count(void);

// ============================================================================
// Mixer Controls (engine_ffi.rs)
// ============================================================================

/**
 * Get meter level for a track in dB (typically -60.0 to 0.0)
 */
float opendaw_mixer_get_meter(void* engine, int track);

/**
 * Get track count
 */
int opendaw_mixer_get_track_count(void* engine);

// Meter FFI (meter_ffi.rs)
float daw_meter_get_track_peak(int track);
float daw_meter_get_track_rms(int track);
float daw_meter_get_master_peak(void);
float daw_meter_get_master_rms(void);

// ============================================================================
// MIDI Recording (midi_ffi.rs)
// ============================================================================

int daw_midi_device_count(void);
int daw_midi_device_info(int index, DawMidiDeviceInfo* info_out);
void daw_midi_start_recording(float start_beat);
int daw_midi_stop_recording(void** notes_out);
void daw_midi_free_notes(void* notes, int count);
int daw_midi_is_recording(void);

// ============================================================================
// Project Save/Load (project_ffi.rs)
// ============================================================================

int daw_project_state_init(void);
int daw_project_state_new(void);
int daw_project_save(void* engine_ptr, const char* path);
int daw_project_load(void* engine_ptr, const char* path);
int daw_project_state_set_path(const char* path);
int daw_project_state_get_path(char* path_out, int max_len);
int daw_project_state_is_modified(void);
void daw_project_state_mark_modified(void);
void daw_project_state_clear_modified(void);

#ifdef __cplusplus
}
#endif

#endif // DAW_ENGINE_H
