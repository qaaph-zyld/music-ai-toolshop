/**
 * OpenDAW Engine C API
 *
 * FFI interface for JUCE C++ UI integration.
 * All functions use C ABI for cross-language compatibility.
 */

#ifndef DAW_ENGINE_H
#define DAW_ENGINE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Types
// ============================================================================

/// Opaque handle to engine instance
typedef void* DawEngineHandle;

/// Opaque handle to transport
typedef void* DawTransportHandle;

/// Opaque handle to mixer
typedef void* DawMixerHandle;

/// Opaque handle to session
typedef void* DawSessionHandle;

/// Opaque handle to audio device manager
typedef void* DawAudioDeviceManagerHandle;

/// Opaque handle to stem separator
typedef void* DawStemSeparatorHandle;

/// Transport states
typedef enum {
    DAW_STATE_STOPPED = 0,
    DAW_STATE_PLAYING = 1,
    DAW_STATE_RECORDING = 2,
    DAW_STATE_PAUSED = 3
} DawTransportState;

/// Callback types
typedef void (*DawTransportCallback)(int state);
typedef void (*DawMeterCallback)(int track, float db);
typedef void (*DawClipCallback)(int track, int scene, int state);
typedef void (*DawPositionCallback)(int bars, int beats, int sixteenths);

// ============================================================================
// Engine Lifecycle
// ============================================================================

/**
 * Initialize the audio engine
 * @param sample_rate Sample rate in Hz (e.g., 48000)
 * @param buffer_size Buffer size in samples (e.g., 512)
 * @return Engine handle or NULL on error
 */
DawEngineHandle daw_engine_init(int sample_rate, int buffer_size);

/**
 * Shutdown the audio engine
 * @param engine Engine handle from daw_engine_init
 */
void daw_engine_shutdown(DawEngineHandle engine);

/**
 * Get the last error message
 * @return Error string (static, do not free)
 */
const char* daw_last_error(void);

// ============================================================================
// Transport Controls
// ============================================================================

/**
 * Get transport from engine
 */
DawTransportHandle daw_get_transport(DawEngineHandle engine);

/**
 * Start playback
 */
void daw_transport_play(DawTransportHandle transport);

/**
 * Stop playback
 */
void daw_transport_stop(DawTransportHandle transport);

/**
 * Start recording
 */
void daw_transport_record(DawTransportHandle transport);

/**
 * Set playback position in beats
 */
void daw_transport_set_position(DawTransportHandle transport, double beats);

/**
 * Set tempo in BPM
 */
void daw_transport_set_tempo(DawTransportHandle transport, double bpm);

/**
 * Get current transport state
 */
int daw_transport_get_state(DawTransportHandle transport);

/**
 * Get current position in beats
 */
double daw_transport_get_position(DawTransportHandle transport);

// ============================================================================
// Session/Clip Controls
// ============================================================================

/**
 * Get session from engine
 */
DawSessionHandle daw_get_session(DawEngineHandle engine);

/**
 * Launch a clip at track/scene
 */
void daw_session_launch_clip(DawSessionHandle session, int track, int scene);

/**
 * Stop a clip at track/scene
 */
void daw_session_stop_clip(DawSessionHandle session, int track, int scene);

/**
 * Load audio file into clip slot
 */
int daw_session_load_clip(DawSessionHandle session, int track, int scene, const char* file_path);

/**
 * Launch all clips in a scene
 */
void daw_session_launch_scene(DawSessionHandle session, int scene);

/**
 * Stop all clips
 */
void daw_session_stop_all(DawSessionHandle session);

// ============================================================================
// Mixer Controls
// ============================================================================

/**
 * Get mixer from engine
 */
DawMixerHandle daw_get_mixer(DawEngineHandle engine);

/**
 * Set track volume in dB
 */
void daw_mixer_set_volume(DawMixerHandle mixer, int track, float db);

/**
 * Set track pan (-1.0 to 1.0)
 */
void daw_mixer_set_pan(DawMixerHandle mixer, int track, float pan);

/**
 * Set track mute state
 */
void daw_mixer_set_mute(DawMixerHandle mixer, int track, int muted);

/**
 * Set track solo state
 */
void daw_mixer_set_solo(DawMixerHandle mixer, int track, int soloed);

/**
 * Get track peak level in dB
 */
float daw_mixer_get_peak(DawMixerHandle mixer, int track);

// ============================================================================
// Audio Device Management
// ============================================================================

/**
 * Create audio device manager
 */
DawAudioDeviceManagerHandle daw_audio_device_manager_create(void);

/**
 * Free audio device manager
 */
void daw_audio_device_manager_free(DawAudioDeviceManagerHandle handle);

/**
 * Get number of audio output devices
 */
int daw_audio_device_count(DawAudioDeviceManagerHandle handle);

/**
 * Get audio device name by index
 * @param handle Device manager handle
 * @param index Device index
 * @param name_out Output buffer (must be 256 bytes)
 * @param name_len Buffer length
 * @return 0 on success, -1 on error
 */
int daw_audio_device_name(DawAudioDeviceManagerHandle handle, int index, char* name_out, int name_len);

/**
 * Check if audio stream is running
 */
int daw_audio_is_streaming(DawAudioDeviceManagerHandle handle);

// ============================================================================
// Callback Registration
// ============================================================================

/**
 * Register transport state callback
 */
void daw_register_transport_callback(DawTransportCallback callback);

/**
 * Register level meter callback
 */
void daw_register_meter_callback(DawMeterCallback callback);

/**
 * Register clip state callback
 */
void daw_register_clip_callback(DawClipCallback callback);

/**
 * Register position callback
 */
void daw_register_position_callback(DawPositionCallback callback);

// ============================================================================
// Project Save/Load
// ============================================================================

/**
 * Save project to file
 */
int daw_project_save(DawEngineHandle engine, const char* file_path);

/**
 * Load project from file
 */
int daw_project_load(DawEngineHandle engine, const char* file_path);

// ============================================================================
// Stem Separation
// ============================================================================

/**
 * Create stem separator
 */
DawStemSeparatorHandle daw_stem_separator_create(void);

/**
 * Free stem separator
 */
void daw_stem_separator_free(DawStemSeparatorHandle handle);

/**
 * Check if demucs is available
 */
int daw_stem_is_available(DawStemSeparatorHandle handle);

/**
 * Start stem separation
 */
int daw_stem_separate(DawStemSeparatorHandle handle, const char* input_path, const char* output_dir);

/**
 * Get separation progress (0.0 to 1.0)
 */
double daw_stem_get_progress(DawStemSeparatorHandle handle);

/**
 * Check if separation is complete
 */
int daw_stem_is_complete(DawStemSeparatorHandle handle);

/**
 * Get stem file path by type
 * Types: 0=vocals, 1=drums, 2=bass, 3=other
 */
const char* daw_stem_get_path(DawStemSeparatorHandle handle, int stem_type);

/**
 * Cancel ongoing separation
 */
void daw_stem_cancel(DawStemSeparatorHandle handle);

// ============================================================================
// MIDI
// ============================================================================

/**
 * Get MIDI input device count
 */
int daw_midi_device_count(void);

/**
 * Get MIDI device info
 */
typedef struct {
    char id[64];
    char name[128];
    int is_available;
} DawMidiDeviceInfo;

/**
 * Get MIDI device info by index
 */
int daw_midi_device_info(int index, DawMidiDeviceInfo* info_out);

/**
 * Start MIDI recording
 */
void daw_midi_start_recording(float start_beat);

/**
 * Stop MIDI recording
 */
typedef struct {
    float pitch;
    float velocity;
    float beat;
    float duration;
} DawMidiNote;

/**
 * Stop recording and get notes
 * @param notes_out Receives pointer to note array (caller must free with daw_midi_free_notes)
 * @return Note count, -1 on error
 */
int daw_midi_stop_recording(DawMidiNote** notes_out);

/**
 * Free notes array
 */
void daw_midi_free_notes(DawMidiNote* notes, int count);

/**
 * Check if currently recording
 */
int daw_midi_is_recording(void);

#ifdef __cplusplus
}
#endif

#endif // DAW_ENGINE_H
