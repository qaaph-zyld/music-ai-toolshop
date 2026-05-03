#include "EngineBridge.h"

// ============================================================================
// Loop Markers FFI Structures (Phase 10.2)
// ============================================================================
#pragma pack(push, 1)
struct LoopRegionInfoFFI {
    const char* id;
    const char* name;
    double start_beat;
    double end_beat;
    int enabled;
    const char* color;
};
#pragma pack(pop)

// FFI declarations - these match the Rust engine_ffi.rs, clip_player_ffi.rs, and transport_sync_ffi.rs exports
extern "C" {
    // Engine lifecycle
    void* opendaw_engine_init(int sample_rate, int buffer_size);
    void opendaw_engine_shutdown(void* engine);
    
    // Transport
    void opendaw_transport_play(void* engine);
    void opendaw_transport_stop(void* engine);
    void opendaw_transport_record(void* engine);
    void opendaw_transport_set_position(void* engine, double beats);
    double opendaw_transport_get_position(void* engine);
    void opendaw_transport_set_bpm(void* engine, float bpm);
    float opendaw_transport_get_bpm(void* engine);
    int opendaw_transport_is_playing(void* engine);
    int opendaw_transport_is_recording(void* engine);
    
    // Clip Player FFI (Phase 6.3)
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
    int opendaw_clip_player_load_sample(void* engine, int track_idx, int clip_idx, const char* file_path);
    
    // Mixer
    float opendaw_mixer_get_meter(void* engine, int track);
    int opendaw_mixer_get_track_count(void* engine);
    
    // Audio Processor - Transport Sync (Phase 6.5)
    double opendaw_get_current_beat();
    void opendaw_set_tempo(float bpm);
    float opendaw_get_tempo();
    int opendaw_get_last_triggered_clip(int* track_out, int* clip_out);
    void opendaw_reset_callback_count();
    int opendaw_get_callback_count();
    
    // Transport Sync FFI (Phase 6.5/6.6)
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
    
    // Session/Scene Controls (missing declarations - Phase 8.4)
    void opendaw_scene_launch(void* engine, int scene);
    void opendaw_stop_all_clips(void* engine);
    void opendaw_clip_play(void* engine, int track, int scene);
    void opendaw_clip_stop(void* engine, int track, int scene);
    
    // MIDI Recording FFI (Phase 7.1)
    int daw_midi_device_count();
    int daw_midi_device_info(int index, void* info_out);
    void daw_midi_start_recording(float start_beat);
    int daw_midi_stop_recording(void** notes_out);
    void daw_midi_free_notes(void* notes, int count);
    int daw_midi_is_recording();
    
    // MIDI Clip Creation FFI (Phase 6)
    int daw_create_midi_clip(void* engine_ptr, int track, int scene, const void* notes, int note_count, const char* clip_name);
    
    // Stem Separation FFI (Phase 8.x)
    void* daw_stem_separator_create();
    void daw_stem_separator_free(void* handle);
    int daw_stem_is_available(void* handle);
    int daw_stem_separate(void* handle, const char* input_path, const char* output_dir);
    double daw_stem_get_progress(void* handle);
    int daw_stem_is_complete(void* handle);
    const char* daw_stem_get_path(void* handle, int stem_type);
    void daw_stem_cancel(void* handle);

    // Plugin Chain FFI (Phase 9)
    int daw_plugin_registry_scan();
    int daw_plugin_registry_get_count();
    int daw_plugin_registry_get_plugin(int index, void* out_info);
    int daw_plugin_registry_search(const char* query, int* out_indices, int max_results);
    void daw_plugin_info_free(void* info);

    int daw_plugin_chain_get_or_create(int track_index);
    int daw_plugin_chain_add(int track_index, const char* unique_id);
    int daw_plugin_chain_remove(int track_index, int slot_index);
    int daw_plugin_chain_move(int track_index, int from_index, int to_index);
    int daw_plugin_chain_get_count(int track_index);
    int daw_plugin_chain_get_plugin_info(int track_index, int slot_index, void* out_info);
    int daw_plugin_chain_set_bypass(int track_index, int slot_index, int bypass);
    int daw_plugin_chain_get_bypass(int track_index, int slot_index);
    int daw_plugin_chain_clear(int track_index);

    // Punch-In/Out Recording FFI (Phase 10.1)
    int daw_punch_in_out_init();
    void daw_punch_in_out_shutdown();
    void daw_punch_in_out_set_in(float beats);
    void daw_punch_in_out_set_out(float beats);
    void daw_punch_in_out_set_pre_roll(float beats);
    void daw_punch_in_out_set_enabled(int enabled);
    int daw_punch_in_out_is_enabled();
    int daw_punch_in_out_arm(float current_beat);
    void daw_punch_in_out_disarm();
    int daw_punch_in_out_get_state();
    int daw_punch_in_out_is_in_range(float beat);
    float daw_punch_in_out_get_in();
    float daw_punch_in_out_get_out();
    float daw_punch_in_out_get_pre_roll();
    float daw_punch_in_out_get_pre_roll_start();
    int daw_punch_in_out_get_pre_roll_progress(float current_beat, float* out_progress);
    int daw_punch_in_out_get_beats_until_in(float current_beat, float* out_beats);
    int daw_punch_in_out_get_beats_until_out(float current_beat, float* out_beats);
    void daw_punch_in_out_reset();
    char* daw_punch_in_out_get_status_text();
    void daw_punch_in_out_free_string(char* ptr);

    // Loop Markers FFI (Phase 10.2)
    char* daw_loop_create_region(const char* name, double start_beat, double end_beat);
    int daw_loop_get_region_count();
    int daw_loop_get_region_at(int index, void* out_info);
    int daw_loop_get_region_by_id(const char* id, void* out_info);
    void daw_loop_free_region_info(void* info);
    void daw_loop_free_string(char* s);
    int daw_loop_delete_region(const char* id);
    int daw_loop_set_region_position(const char* id, double start_beat, double end_beat);
    int daw_loop_rename_region(const char* id, const char* new_name);
    int daw_loop_set_region_enabled(const char* id, int enabled);
    char* daw_loop_get_active_region_id();
    int daw_loop_set_active_region(const char* id);
    int daw_loop_is_looping_enabled();
    void daw_loop_set_looping_enabled(int enabled);
    double daw_loop_should_loop_at_beat(double beat);
    int daw_loop_get_boundaries(double beat, double* out_start, double* out_end);

    // Time Signature FFI (Phase 10.4)
    int daw_time_sig_init();
    int daw_time_sig_add_change(unsigned int bar, unsigned int numerator, unsigned int denominator);
    int daw_time_sig_remove_change(unsigned int bar);
    int daw_time_sig_get_change_count();
    int daw_time_sig_get_change_at(int index, void* out_info);
    int daw_time_sig_get_at_bar(unsigned int bar, void* out_info);
    int daw_time_sig_beat_to_bar_beat(double beat, void* out_result);
    double daw_time_sig_bar_beat_to_beat(unsigned int bar, unsigned int beat_in_bar);
    double daw_time_sig_get_bar_start(unsigned int bar);
    double daw_time_sig_get_bar_length(unsigned int bar);
    char* daw_time_sig_format_string(unsigned int numerator, unsigned int denominator);
    void daw_time_sig_free_string(char* s);

    // Tempo Automation FFI (Phase 10.3)
    void daw_tempo_auto_init(double default_bpm);
    void daw_tempo_auto_reset(double bpm);
    void daw_tempo_auto_add_breakpoint(double beat, double bpm, int interpolation);
    int daw_tempo_auto_remove_breakpoint(double beat);
    int daw_tempo_auto_get_breakpoint_count();
    int daw_tempo_auto_get_breakpoint_at(int index, void* out_info);
    double daw_tempo_auto_get_tempo_at_beat(double beat);
    double daw_tempo_auto_get_average_tempo(double start_beat, double end_beat);
    double daw_tempo_auto_beats_to_seconds(double start_beat, double end_beat);
    int daw_tempo_auto_find_nearest(double beat, void* out_info);

    // Arrangement FFI (Phase 10.5)
    void daw_arrangement_init(unsigned int track_count);
    void daw_arrangement_reset();
    unsigned int daw_arrangement_track_count();
    unsigned long long daw_arrangement_add_midi_clip(unsigned int track_idx, double start_beat, const char* name, double duration_bars);
    unsigned long long daw_arrangement_add_audio_clip(unsigned int track_idx, double start_beat, const char* name, double duration_bars, const char* file_path);
    int daw_arrangement_remove_clip(unsigned int track_idx, unsigned long long clip_id);
    int daw_arrangement_move_clip(unsigned int from_track, unsigned long long clip_id, unsigned int to_track, double new_start);
    int daw_arrangement_resize_clip(unsigned int track_idx, unsigned long long clip_id, double new_duration);
    unsigned int daw_arrangement_clip_count(unsigned int track_idx);
    unsigned int daw_arrangement_total_clip_count();
    int daw_arrangement_get_clip_at(unsigned int track_idx, unsigned int index, void* out_info);
    int daw_arrangement_get_clip_by_id(unsigned int track_idx, unsigned long long clip_id, void* out_info);
    void daw_arrangement_free_clip_info(void* info);
    double daw_arrangement_total_duration();
    int daw_arrangement_can_move_to(unsigned int track_idx, unsigned long long clip_id, double new_start, double duration);
    unsigned int daw_arrangement_clips_in_range(unsigned int track_idx, double start_beat, double end_beat, unsigned long long* out_ids, unsigned int max_count);
    unsigned long long daw_arrangement_clip_at_beat(unsigned int track_idx, double beat);
    unsigned int daw_arrangement_active_clips(double beat, unsigned long long* out_ids, unsigned int max_count);
}

// Time Signature FFI structures (match Rust TimeSignatureInfo and BarBeatResult)
#pragma pack(push, 1)
struct TimeSignatureInfoFFI {
    unsigned int bar;
    unsigned int numerator;
    unsigned int denominator;
};

struct BarBeatResultFFI {
    unsigned int bar;
    unsigned int beat_in_bar;
    double fraction;
};
#pragma pack(pop)

// Tempo Automation FFI structure (matches Rust TempoBreakpointFFI)
#pragma pack(push, 1)
struct TempoBreakpointFFI {
    double beat;
    double bpm;
    int interpolation; // 0=step, 1=linear, 2=exponential, 3=smooth
};
#pragma pack(pop)

// Arrangement FFI structure (matches Rust ArrangementClipInfo)
#pragma pack(push, 1)
struct ArrangementClipInfoFFI {
    unsigned long long id;
    unsigned int track_index;
    double start_beat;
    double duration_beats;
    const char* name;
    int is_audio;
};
#pragma pack(pop)

// Quantization levels matching Rust FFITransportQuantization enum
enum class TransportQuantization {
    Immediate = 0,
    Beat = 1,
    Bar = 2,
    Eighth = 3,
    Sixteenth = 4
};

// MIDI FFI Structures (Phase 7.1)
#pragma pack(push, 1)
struct MidiDeviceInfoFFI {
    char id[64];
    char name[128];
    int is_available;
};

struct MidiNoteFFI {
    int pitch;
    int velocity;
    float start_beat;
    float duration_beats;
};
#pragma pack(pop)

struct EngineBridge::Command
{
    enum Type {
        Play, Stop, Record,
        SetPosition, SetTempo,
        LaunchClip, StopClip, LoadClip,
        LaunchScene, StopAll,
        SetVolume, SetPan, SetMute, SetSolo, ArmTrack
    };

    Type type;
    int trackIndex = 0;
    int sceneIndex = 0;
    double value = 0.0;
    juce::String stringValue;
    bool boolValue = false;
};

EngineBridge& EngineBridge::getInstance()
{
    static EngineBridge instance;
    return instance;
}

EngineBridge::EngineBridge()
    : juce::Thread("EngineBridge")
{
}

EngineBridge::~EngineBridge()
{
    shutdown();
}

bool EngineBridge::initialize(int sampleRate, int bufferSize)
{
    rustEngine = opendaw_engine_init(sampleRate, bufferSize);
    
    if (rustEngine == nullptr)
    {
        return false;
    }
    
    // Initialize transport sync for sample-accurate scheduling (Phase 6.6)
    transportSyncHandle = opendaw_transport_sync_init(static_cast<float>(sampleRate), 120.0f);
    
    initialized = true;
    startThread();
    return true;
}

void EngineBridge::shutdown()
{
    if (initialized)
    {
        signalThreadShouldExit();
        commandEvent.signal();
        stopThread(1000);
        
        // Shutdown transport sync (Phase 6.6)
        if (transportSyncHandle != nullptr)
        {
            opendaw_transport_sync_shutdown(transportSyncHandle);
            transportSyncHandle = nullptr;
        }
        
        if (rustEngine != nullptr)
        {
            opendaw_engine_shutdown(rustEngine);
            rustEngine = nullptr;
        }
        
        initialized = false;
    }
}

void EngineBridge::run()
{
    while (!threadShouldExit())
    {
        commandEvent.wait(100);

        juce::GenericScopedLock<juce::CriticalSection> lock(commandLock);
        while (!commandQueue.empty())
        {
            auto cmd = std::move(commandQueue.front());
            commandQueue.pop();
            
            // Execute command via FFI
            if (rustEngine != nullptr)
            {
                switch (cmd->type)
                {
                    case Command::Play:
                        opendaw_transport_play(rustEngine);
                        break;
                    case Command::Stop:
                        opendaw_transport_stop(rustEngine);
                        break;
                    case Command::Record:
                        opendaw_transport_record(rustEngine);
                        break;
                    case Command::SetPosition:
                        opendaw_transport_set_position(rustEngine, cmd->value);
                        break;
                    case Command::SetTempo:
                        opendaw_transport_set_bpm(rustEngine, static_cast<float>(cmd->value));
                        // Also update transport sync tempo
                        if (transportSyncHandle != nullptr)
                        {
                            opendaw_transport_sync_set_tempo(transportSyncHandle, static_cast<float>(cmd->value));
                        }
                        break;
                    case Command::LaunchScene:
                        opendaw_scene_launch(rustEngine, cmd->sceneIndex);
                        break;
                    case Command::StopAll:
                        opendaw_stop_all_clips(rustEngine);
                        break;
                    case Command::LaunchClip:
                        opendaw_clip_play(rustEngine, cmd->trackIndex, cmd->sceneIndex);
                        break;
                    case Command::StopClip:
                        opendaw_clip_stop(rustEngine, cmd->trackIndex, cmd->sceneIndex);
                        break;
                    default:
                        break;
                }
            }
        }
    }
}

void EngineBridge::play()
{
    if (rustEngine != nullptr)
    {
        opendaw_transport_play(rustEngine);
        
        if (onTransportStateChange)
            onTransportStateChange(true);
    }
    else
    {
        DBG("EngineBridge::play() - engine not initialized!");
    }
}

void EngineBridge::stop()
{
    if (rustEngine != nullptr)
    {
        opendaw_transport_stop(rustEngine);
        
        if (onTransportStateChange)
            onTransportStateChange(false);
    }
    else
    {
        DBG("EngineBridge::stop() - engine not initialized!");
    }
}

void EngineBridge::record()
{
    if (rustEngine != nullptr)
    {
        opendaw_transport_record(rustEngine);
    }
    else
    {
        DBG("EngineBridge::record() - engine not initialized!");
    }
}

void EngineBridge::setPosition(double beats)
{
    if (rustEngine != nullptr)
    {
        opendaw_transport_set_position(rustEngine, beats);
    }
}

void EngineBridge::setTempo(double bpm)
{
    if (rustEngine != nullptr)
    {
        opendaw_transport_set_bpm(rustEngine, static_cast<float>(bpm));
    }
    
    // Also update transport sync tempo
    if (transportSyncHandle != nullptr)
    {
        opendaw_transport_sync_set_tempo(transportSyncHandle, static_cast<float>(bpm));
    }
}

double EngineBridge::getTempo() const
{
    if (rustEngine != nullptr)
    {
        return opendaw_transport_get_bpm(rustEngine);
    }
    return 120.0; // Default
}

bool EngineBridge::isPlaying() const
{
    if (rustEngine != nullptr)
    {
        return opendaw_transport_is_playing(rustEngine) != 0;
    }
    return false;
}

bool EngineBridge::isRecording() const
{
    if (rustEngine != nullptr)
    {
        return opendaw_transport_is_recording(rustEngine) != 0;
    }
    return false;
}

double EngineBridge::getCurrentBeat() const
{
    return opendaw_get_current_beat();
}

void EngineBridge::launchClip(int trackIndex, int sceneIndex)
{
    if (rustEngine != nullptr)
    {
        // Use clip_player_ffi to trigger clip
        opendaw_clip_player_trigger_clip(rustEngine, trackIndex, sceneIndex);
        
        if (onClipStateChange)
            onClipStateChange(trackIndex, sceneIndex, true);
    }
}

void EngineBridge::stopClip(int trackIndex, int sceneIndex)
{
    (void)sceneIndex; // sceneIndex not used in stop_clip (stops entire track)
    if (rustEngine != nullptr)
    {
        opendaw_clip_player_stop_clip(rustEngine, trackIndex);
        
        if (onClipStateChange)
            onClipStateChange(trackIndex, sceneIndex, false);
    }
}

void EngineBridge::loadClip(int trackIndex, int sceneIndex, const juce::String& filePath)
{
    if (rustEngine != nullptr && !filePath.isEmpty())
    {
        // Convert JUCE String to UTF-8 char array
        auto pathUtf8 = filePath.toUTF8();
        opendaw_clip_player_load_sample(rustEngine, trackIndex, sceneIndex, pathUtf8.getAddress());
    }
}

void EngineBridge::moveClip(int fromTrack, int fromScene, int toTrack, int toScene)
{
    (void)fromTrack;
    (void)fromScene;
    (void)toTrack;
    (void)toScene;
    // Phase 7.0: TODO - Implement clip move via FFI when available
    // For now, the UI layer handles the visual move and the engine
    // will be updated when clip persistence is implemented
}

// Clip player state methods (Phase 6.6)
int EngineBridge::getClipState(int trackIndex, int clipIndex)
{
    if (rustEngine != nullptr)
    {
        int state = 0;
        opendaw_clip_player_get_state(rustEngine, trackIndex, clipIndex, &state);
        return state;
    }
    return 0;
}

bool EngineBridge::isClipPlaying(int trackIndex)
{
    if (rustEngine != nullptr)
    {
        int playing = 0;
        opendaw_clip_player_is_playing(rustEngine, trackIndex, &playing);
        return playing != 0;
    }
    return false;
}

int EngineBridge::getPlayingClip(int trackIndex)
{
    if (rustEngine != nullptr)
    {
        int clipIdx = -1;
        opendaw_clip_player_get_playing_clip(rustEngine, trackIndex, &clipIdx);
        return clipIdx;
    }
    return -1;
}

void EngineBridge::queueClip(int trackIndex, int clipIndex)
{
    if (rustEngine != nullptr)
    {
        opendaw_clip_player_queue_clip(rustEngine, trackIndex, clipIndex);
    }
}

// Transport Sync / Scheduling (Phase 6.6)
void EngineBridge::scheduleClip(int trackIndex, int clipIndex, double targetBeat, bool looped)
{
    if (transportSyncHandle != nullptr)
    {
        opendaw_transport_sync_schedule_clip(transportSyncHandle, 
                                             static_cast<size_t>(trackIndex),
                                             static_cast<size_t>(clipIndex),
                                             targetBeat,
                                             looped ? 1 : 0);
    }
}

void EngineBridge::scheduleClipQuantized(int trackIndex, int clipIndex, int quantizationBars)
{
    if (transportSyncHandle != nullptr)
    {
        double currentBeat = opendaw_get_current_beat();
        
        // Map quantization bars to appropriate enum value
        TransportQuantization quant;
        switch (quantizationBars)
        {
            case 0: quant = TransportQuantization::Immediate; break;
            case 1: quant = TransportQuantization::Beat; break;
            default: quant = TransportQuantization::Bar; break; // 2+ bars -> Bar quantization
        }
        
        opendaw_transport_sync_schedule_clip_quantized(transportSyncHandle,
                                                        static_cast<size_t>(trackIndex),
                                                        static_cast<size_t>(clipIndex),
                                                        currentBeat,
                                                        static_cast<int>(quant),
                                                        0); // not looped by default
    }
}

void EngineBridge::cancelScheduledClip(int trackIndex, int clipIndex)
{
    if (transportSyncHandle != nullptr)
    {
        opendaw_transport_sync_cancel_clip(transportSyncHandle,
                                           static_cast<size_t>(trackIndex),
                                           static_cast<size_t>(clipIndex));
    }
}

void EngineBridge::cancelAllScheduledClips(int trackIndex)
{
    if (transportSyncHandle != nullptr)
    {
        opendaw_transport_sync_cancel_track(transportSyncHandle,
                                            static_cast<size_t>(trackIndex));
    }
}

bool EngineBridge::isClipScheduled(int trackIndex) const
{
    if (transportSyncHandle != nullptr)
    {
        int result = opendaw_transport_sync_is_track_scheduled(transportSyncHandle,
                                                                static_cast<size_t>(trackIndex));
        return result == 1;
    }
    return false;
}

double EngineBridge::getNextScheduledBeat(int trackIndex) const
{
    if (transportSyncHandle != nullptr)
    {
        double beat = opendaw_transport_sync_next_scheduled_beat(transportSyncHandle,
                                                                  static_cast<size_t>(trackIndex));
        return beat >= 0.0 ? beat : -1.0;
    }
    return -1.0;
}

// UI State Polling (Phase 6.6)
TriggeredClipInfo EngineBridge::pollTriggeredClip()
{
    TriggeredClipInfo info;
    
    int track = -1;
    int clip = -1;
    int result = opendaw_get_last_triggered_clip(&track, &clip);
    
    if (result == 0 && track >= 0 && clip >= 0)
    {
        info.trackIndex = track;
        info.clipIndex = clip;
        info.beat = getCurrentBeat(); // Approximate
    }
    
    return info;
}

std::vector<TriggeredClipInfo> EngineBridge::pollAllTriggeredClips()
{
    std::vector<TriggeredClipInfo> clips;
    
    // Poll for triggered clips - currently only one at a time via atomics
    // In future, could use a ring buffer for multiple
    TriggeredClipInfo info = pollTriggeredClip();
    if (info.isValid())
    {
        clips.push_back(info);
    }
    
    return clips;
}

void EngineBridge::setTrackVolume(int trackIndex, float db)
{
    (void)trackIndex;
    (void)db;
    // TODO: Implement via FFI when available
}

void EngineBridge::setTrackPan(int trackIndex, float pan)
{
    (void)trackIndex;
    (void)pan;
    // TODO: Implement via FFI when available
}

void EngineBridge::setTrackMute(int trackIndex, bool muted)
{
    (void)trackIndex;
    (void)muted;
    // TODO: Implement via FFI when available
}

void EngineBridge::setTrackSolo(int trackIndex, bool soloed)
{
    (void)trackIndex;
    (void)soloed;
    // TODO: Implement via FFI when available
}

void EngineBridge::armTrack(int trackIndex, bool armed)
{
    (void)trackIndex;
    (void)armed;
    // TODO: Implement via FFI when available
}

void EngineBridge::launchScene(int sceneIndex)
{
    if (rustEngine != nullptr)
    {
        opendaw_scene_launch(rustEngine, sceneIndex);
    }
}

void EngineBridge::stopAll()
{
    if (rustEngine != nullptr)
    {
        opendaw_stop_all_clips(rustEngine);
    }
}

void EngineBridge::getMeterLevels(std::vector<float>& levels)
{
    if (rustEngine != nullptr)
    {
        int trackCount = opendaw_mixer_get_track_count(rustEngine);
        levels.clear();
        for (int i = 0; i < trackCount; ++i)
        {
            levels.push_back(opendaw_mixer_get_meter(rustEngine, i));
        }
    }
    else
    {
        levels.assign(9, -60.0f);
    }
}

// ============================================================================
// Test Tone (Session Z: Onboarding)
// ============================================================================

void EngineBridge::playTestTone(float frequency, float amplitude)
{
    // TODO: Implement via Rust FFI - generate sine wave in audio callback
    DBG("EngineBridge::playTestTone - freq=" + juce::String(frequency) + 
        "Hz, amp=" + juce::String(amplitude));
    
    // For now, just store the values - actual implementation would
    // set a flag in the audio engine to mix in a sine wave
    if (rustEngine != nullptr)
    {
        // FFI call to enable test tone
        // daw_enable_test_tone(rustEngine, frequency, amplitude);
    }
}

void EngineBridge::stopTestTone()
{
    DBG("EngineBridge::stopTestTone");
    
    if (rustEngine != nullptr)
    {
        // FFI call to disable test tone
        // daw_disable_test_tone(rustEngine);
    }
}

// ============================================================================
// MIDI Recording (Phase 7.1)
// ============================================================================

std::vector<EngineBridge::MidiDeviceInfo> EngineBridge::getMidiInputDevices()
{
    std::vector<MidiDeviceInfo> devices;
    
    if (!initialized)
    {
        DBG("EngineBridge::getMidiInputDevices() - engine not initialized!");
        return devices;
    }
    
    int count = daw_midi_device_count();
    for (int i = 0; i < count; ++i)
    {
        MidiDeviceInfoFFI ffi_info;
        if (daw_midi_device_info(i, &ffi_info) == 0)
        {
            MidiDeviceInfo info;
            info.id = juce::String(ffi_info.id);
            info.name = juce::String(ffi_info.name);
            info.isAvailable = ffi_info.is_available != 0;
            devices.push_back(info);
        }
    }
    
    return devices;
}

void EngineBridge::selectMidiInputDevice(const juce::String& deviceId)
{
    // TODO: Implement device selection when FFI supports it
    // For now, device selection happens automatically in Rust layer
    (void)deviceId;
}

void EngineBridge::startMidiRecording(int trackIndex, int sceneIndex, float startBeat)
{
    (void)trackIndex;  // TODO: Associate recording with specific track/scene
    (void)sceneIndex;
    daw_midi_start_recording(startBeat);
}

std::vector<EngineBridge::RecordedNote> EngineBridge::stopMidiRecording()
{
    std::vector<RecordedNote> notes;
    
    MidiNoteFFI* notes_ptr = nullptr;
    int count = daw_midi_stop_recording(reinterpret_cast<void**>(&notes_ptr));
    
    if (count > 0 && notes_ptr != nullptr)
    {
        notes.reserve(count);
        for (int i = 0; i < count; ++i)
        {
            RecordedNote note;
            note.pitch = static_cast<uint8_t>(notes_ptr[i].pitch);
            note.velocity = static_cast<uint8_t>(notes_ptr[i].velocity);
            note.startBeat = notes_ptr[i].start_beat;
            note.duration = notes_ptr[i].duration_beats;
            notes.push_back(note);
        }
        
        // Free the allocated notes array
        daw_midi_free_notes(notes_ptr, count);
    }
    
    return notes;
}

bool EngineBridge::isMidiRecording() const
{
    return daw_midi_is_recording() != 0;
}

void EngineBridge::setQuantization(float gridDivision, float strength)
{
    // TODO: Implement when FFI supports quantization settings
    (void)gridDivision;
    (void)strength;
}

bool EngineBridge::createMidiClip(int trackIndex, int sceneIndex, const std::vector<RecordedNote>& notes, const juce::String& clipName)
{
    if (!initialized || rustEngine == nullptr)
    {
        DBG("EngineBridge::createMidiClip() - engine not initialized!");
        return false;
    }
    
    if (notes.empty())
    {
        DBG("EngineBridge::createMidiClip() - no notes to create clip");
        return false;
    }
    
    // Convert RecordedNote array to MidiNoteFFI array
    std::vector<MidiNoteFFI> ffiNotes;
    ffiNotes.reserve(notes.size());
    
    for (const auto& note : notes)
    {
        MidiNoteFFI ffiNote;
        ffiNote.pitch = note.pitch;
        ffiNote.velocity = note.velocity;
        ffiNote.start_beat = note.startBeat;
        ffiNote.duration_beats = note.duration;
        ffiNotes.push_back(ffiNote);
    }
    
    // Call Rust FFI to create the MIDI clip
    int result = daw_create_midi_clip(
        rustEngine,
        trackIndex,
        sceneIndex,
        ffiNotes.data(),
        static_cast<int>(ffiNotes.size()),
        clipName.toRawUTF8()
    );
    
    return result == 0;
}

// ============================================================================
// Meter Level Meters (Phase 7.2)
// ============================================================================

// FFI declarations for meter level functions
extern "C" {
    float daw_meter_get_track_peak(int track);
    float daw_meter_get_track_rms(int track);
    float daw_meter_get_master_peak();
    float daw_meter_get_master_rms();
}

EngineBridge::MeterLevels EngineBridge::getTrackMeterLevels(int trackIndex)
{
    MeterLevels levels;
    if (!initialized)
    {
        DBG("EngineBridge::getTrackMeterLevels() - engine not initialized!");
        return levels;
    }
    levels.peakDb = daw_meter_get_track_peak(trackIndex);
    levels.rmsDb = daw_meter_get_track_rms(trackIndex);
    return levels;
}

EngineBridge::MeterLevels EngineBridge::getMasterMeterLevels()
{
    MeterLevels levels;
    if (!initialized)
    {
        DBG("EngineBridge::getMasterMeterLevels() - engine not initialized!");
        return levels;
    }
    levels.peakDb = daw_meter_get_master_peak();
    levels.rmsDb = daw_meter_get_master_rms();
    return levels;
}

// ============================================================================
// MIDI Editing (Phase 8)
// ============================================================================

// FFI declarations for MIDI editing functions
extern "C" {
    void daw_midi_edit_init();
    int daw_midi_quantize(const void* notes_in, int note_count, float grid_division, void* notes_out);
    int daw_midi_transpose(const void* notes_in, int note_count, int semitones, void* notes_out);
    int daw_midi_scale_velocity(const void* notes_in, int note_count, float scale, void* notes_out);
    int daw_midi_duplicate_clip(void* engine, int from_track, int from_scene, int to_track, int to_scene);
}

std::vector<EngineBridge::MidiNoteData> EngineBridge::quantizeMidiNotes(
    const std::vector<MidiNoteData>& notes, float gridDivision)
{
    if (notes.empty()) return {};
    
    // Initialize MIDI editor
    daw_midi_edit_init();
    
    // Convert to FFI format
    std::vector<MidiNoteFFI> ffiNotes;
    ffiNotes.reserve(notes.size());
    for (const auto& note : notes) {
        ffiNotes.push_back({note.pitch, note.velocity, note.startBeat, note.durationBeats});
    }
    
    // Call Rust FFI
    std::vector<MidiNoteFFI> output(notes.size());
    int count = daw_midi_quantize(
        ffiNotes.data(), 
        static_cast<int>(ffiNotes.size()), 
        gridDivision, 
        output.data()
    );
    
    // Convert back
    std::vector<MidiNoteData> result;
    result.reserve(count);
    for (int i = 0; i < count; ++i) {
        result.push_back({output[i].pitch, output[i].velocity, 
                         output[i].start_beat, output[i].duration_beats});
    }
    return result;
}

std::vector<EngineBridge::MidiNoteData> EngineBridge::transposeMidiNotes(
    const std::vector<MidiNoteData>& notes, int semitones)
{
    if (notes.empty()) return {};
    
    daw_midi_edit_init();
    
    std::vector<MidiNoteFFI> ffiNotes;
    ffiNotes.reserve(notes.size());
    for (const auto& note : notes) {
        ffiNotes.push_back({note.pitch, note.velocity, note.startBeat, note.durationBeats});
    }
    
    std::vector<MidiNoteFFI> output(notes.size());
    int count = daw_midi_transpose(
        ffiNotes.data(), 
        static_cast<int>(ffiNotes.size()), 
        semitones, 
        output.data()
    );
    
    std::vector<MidiNoteData> result;
    result.reserve(count);
    for (int i = 0; i < count; ++i) {
        result.push_back({output[i].pitch, output[i].velocity, 
                         output[i].start_beat, output[i].duration_beats});
    }
    return result;
}

std::vector<EngineBridge::MidiNoteData> EngineBridge::scaleMidiVelocities(
    const std::vector<MidiNoteData>& notes, float scale)
{
    if (notes.empty()) return {};
    
    daw_midi_edit_init();
    
    std::vector<MidiNoteFFI> ffiNotes;
    ffiNotes.reserve(notes.size());
    for (const auto& note : notes) {
        ffiNotes.push_back({note.pitch, note.velocity, note.startBeat, note.durationBeats});
    }
    
    std::vector<MidiNoteFFI> output(notes.size());
    int count = daw_midi_scale_velocity(
        ffiNotes.data(), 
        static_cast<int>(ffiNotes.size()), 
        scale, 
        output.data()
    );
    
    std::vector<MidiNoteData> result;
    result.reserve(count);
    for (int i = 0; i < count; ++i) {
        result.push_back({output[i].pitch, output[i].velocity, 
                         output[i].start_beat, output[i].duration_beats});
    }
    return result;
}

bool EngineBridge::duplicateMidiClip(int fromTrack, int fromScene, int toTrack, int toScene)
{
    if (!initialized || rustEngine == nullptr) {
        DBG("EngineBridge::duplicateMidiClip() - engine not initialized!");
        return false;
    }
    
    int result = daw_midi_duplicate_clip(rustEngine, fromTrack, fromScene, toTrack, toScene);
    return result == 0;
}

// ============================================================================
// Project Management (Phase 7.3)
// ============================================================================

// FFI declarations for project functions (from ffi_bridge.rs and project_ffi.rs)
extern "C" {
    int daw_project_state_init();
    int daw_project_state_new();
    int daw_project_save(void* engine_ptr, const char* path);
    int daw_project_load(void* engine_ptr, const char* path);
    int daw_project_state_set_path(const char* path);
    int daw_project_state_get_path(char* path_out, int max_len);
    int daw_project_state_is_modified();
    void daw_project_state_mark_modified();
    void daw_project_state_clear_modified();
}

bool EngineBridge::newProject()
{
    if (!initialized)
    {
        DBG("EngineBridge::newProject() - engine not initialized!");
        return false;
    }
    
    // Initialize project state
    if (daw_project_state_init() != 0)
        return false;
    
    if (daw_project_state_new() != 0)
        return false;
    
    currentProjectPath.clear();
    return true;
}

bool EngineBridge::saveProject(const juce::String& path)
{
    if (rustEngine == nullptr)
        return false;
    
    // Call Rust FFI to save project
    int result = daw_project_save(rustEngine, path.toRawUTF8());
    
    if (result == 0)
    {
        // Update current path
        currentProjectPath = path;
        daw_project_state_set_path(path.toRawUTF8());
        daw_project_state_clear_modified();
        return true;
    }
    
    return false;
}

bool EngineBridge::loadProject(const juce::String& path)
{
    if (rustEngine == nullptr)
        return false;
    
    // Call Rust FFI to load project
    int result = daw_project_load(rustEngine, path.toRawUTF8());
    
    if (result == 0)
    {
        // Update current path
        currentProjectPath = path;
        daw_project_state_set_path(path.toRawUTF8());
        return true;
    }
    
    return false;
}

bool EngineBridge::saveCurrentProject()
{
    if (currentProjectPath.isEmpty())
        return false; // No current project path - use saveProject with dialog
    
    return saveProject(currentProjectPath);
}

juce::String EngineBridge::getCurrentProjectPath() const
{
    // Try to get path from FFI state first
    char buffer[1024];
    int len = daw_project_state_get_path(buffer, sizeof(buffer));
    
    if (len > 0)
        return juce::String(buffer);
    
    // Fall back to cached path
    return currentProjectPath;
}

bool EngineBridge::isProjectModified() const
{
    if (!initialized)
    {
        return false;
    }
    return daw_project_state_is_modified() != 0;
}

// ============================================================================
// Stem Separation (Phase 8.x)
// ============================================================================

bool EngineBridge::isStemSeparationAvailable()
{
    // Create temporary separator to check availability
    void* tempHandle = daw_stem_separator_create();
    if (tempHandle == nullptr)
        return false;
    
    int available = daw_stem_is_available(tempHandle);
    daw_stem_separator_free(tempHandle);
    
    return available != 0;
}

EngineBridge::StemPaths EngineBridge::extractStems(const juce::String& inputPath,
                                                    const juce::String& outputDir,
                                                    std::function<void(float progress)> onProgress)
{
    StemPaths result;
    
    // Clean up any existing separator
    if (stemSeparatorHandle != nullptr)
    {
        daw_stem_separator_free(stemSeparatorHandle);
        stemSeparatorHandle = nullptr;
    }
    
    // Create new separator
    stemSeparatorHandle = daw_stem_separator_create();
    if (stemSeparatorHandle == nullptr)
    {
        result.success = false;
        return result;
    }
    
    // Check if demucs is available
    if (!daw_stem_is_available(stemSeparatorHandle))
    {
        daw_stem_separator_free(stemSeparatorHandle);
        stemSeparatorHandle = nullptr;
        result.success = false;
        return result;
    }
    
    // Start separation
    int sepResult = daw_stem_separate(stemSeparatorHandle,
                                       inputPath.toRawUTF8(),
                                       outputDir.toRawUTF8());
    
    if (sepResult != 0)
    {
        daw_stem_separator_free(stemSeparatorHandle);
        stemSeparatorHandle = nullptr;
        result.success = false;
        return result;
    }
    
    // Poll for progress (blocking - should be called from background thread in UI)
    while (!daw_stem_is_complete(stemSeparatorHandle))
    {
        double progress = daw_stem_get_progress(stemSeparatorHandle);
        if (onProgress)
            onProgress(static_cast<float>(progress));
        
        // Small delay to avoid busy-waiting
        juce::Thread::sleep(100);
    }
    
    // Get final progress
    if (onProgress)
        onProgress(1.0f);
    
    // Get stem paths (0=vocals, 1=drums, 2=bass, 3=other)
    const char* vocalsPath = daw_stem_get_path(stemSeparatorHandle, 0);
    const char* drumsPath = daw_stem_get_path(stemSeparatorHandle, 1);
    const char* bassPath = daw_stem_get_path(stemSeparatorHandle, 2);
    const char* otherPath = daw_stem_get_path(stemSeparatorHandle, 3);
    
    if (vocalsPath != nullptr)
        result.vocals = juce::String(vocalsPath);
    if (drumsPath != nullptr)
        result.drums = juce::String(drumsPath);
    if (bassPath != nullptr)
        result.bass = juce::String(bassPath);
    if (otherPath != nullptr)
        result.other = juce::String(otherPath);
    
    result.success = !result.drums.isEmpty() || !result.bass.isEmpty() || 
                     !result.vocals.isEmpty() || !result.other.isEmpty();
    
    // Clean up separator
    daw_stem_separator_free(stemSeparatorHandle);
    stemSeparatorHandle = nullptr;
    
    return result;
}

void EngineBridge::cancelStemExtraction()
{
    if (stemSeparatorHandle != nullptr)
    {
        daw_stem_cancel(stemSeparatorHandle);
    }
}

// ============================================================================
// Plugin Chain Management (Phase 9)
// ============================================================================

// C-compatible structure matching Rust PluginInfoData
struct PluginInfoData {
    const char* name;
    const char* vendor;
    const char* version;
    int format;
    int num_inputs;
    int num_outputs;
    const char* unique_id;
};

std::vector<EngineBridge::PluginInfo> EngineBridge::scanPluginRegistry()
{
    std::vector<PluginInfo> plugins;

    int count = daw_plugin_registry_scan();
    if (count <= 0)
        return plugins;

    plugins.reserve(count);

    for (int i = 0; i < count; ++i)
    {
        PluginInfoData data;
        if (daw_plugin_registry_get_plugin(i, &data) == 0)
        {
            PluginInfo info;
            info.name = juce::String(data.name);
            info.vendor = juce::String(data.vendor);
            info.version = juce::String(data.version);
            info.uniqueId = juce::String(data.unique_id);
            info.format = data.format;
            info.numInputs = data.num_inputs;
            info.numOutputs = data.num_outputs;
            plugins.push_back(info);

            // Free allocated strings
            daw_plugin_info_free(&data);
        }
    }

    return plugins;
}

std::vector<EngineBridge::PluginInfo> EngineBridge::searchPlugins(const juce::String& query)
{
    std::vector<PluginInfo> results;

    if (query.isEmpty())
        return scanPluginRegistry();

    // First scan to populate registry
    daw_plugin_registry_scan();

    // Search for matching indices
    int indices[100];
    int count = daw_plugin_registry_search(query.toRawUTF8(), indices, 100);

    if (count <= 0)
        return results;

    results.reserve(count);

    for (int i = 0; i < count; ++i)
    {
        PluginInfoData data;
        if (daw_plugin_registry_get_plugin(indices[i], &data) == 0)
        {
            PluginInfo info;
            info.name = juce::String(data.name);
            info.vendor = juce::String(data.vendor);
            info.version = juce::String(data.version);
            info.uniqueId = juce::String(data.unique_id);
            info.format = data.format;
            info.numInputs = data.num_inputs;
            info.numOutputs = data.num_outputs;
            results.push_back(info);

            daw_plugin_info_free(&data);
        }
    }

    return results;
}

bool EngineBridge::createPluginChain(int trackIndex)
{
    if (trackIndex < 0)
        return false;

    return daw_plugin_chain_get_or_create(trackIndex) == 0;
}

int EngineBridge::getPluginChainCount(int trackIndex)
{
    if (trackIndex < 0)
        return -1;

    return daw_plugin_chain_get_count(trackIndex);
}

std::vector<EngineBridge::PluginInfo> EngineBridge::getPluginChain(int trackIndex)
{
    std::vector<PluginInfo> plugins;

    if (trackIndex < 0)
        return plugins;

    int count = daw_plugin_chain_get_count(trackIndex);
    if (count <= 0)
        return plugins;

    plugins.reserve(count);

    for (int i = 0; i < count; ++i)
    {
        PluginInfoData data;
        if (daw_plugin_chain_get_plugin_info(trackIndex, i, &data) == 0)
        {
            PluginInfo info;
            info.name = juce::String(data.name);
            info.vendor = juce::String(data.vendor);
            info.version = juce::String(data.version);
            info.uniqueId = juce::String(data.unique_id);
            info.format = data.format;
            info.numInputs = data.num_inputs;
            info.numOutputs = data.num_outputs;
            plugins.push_back(info);

            daw_plugin_info_free(&data);
        }
    }

    return plugins;
}

int EngineBridge::addPluginToChain(int trackIndex, const juce::String& uniqueId)
{
    if (trackIndex < 0 || uniqueId.isEmpty())
        return -1;

    // Ensure chain exists
    daw_plugin_chain_get_or_create(trackIndex);

    return daw_plugin_chain_add(trackIndex, uniqueId.toRawUTF8());
}

bool EngineBridge::removePluginFromChain(int trackIndex, int slotIndex)
{
    if (trackIndex < 0 || slotIndex < 0)
        return false;

    return daw_plugin_chain_remove(trackIndex, slotIndex) == 0;
}

bool EngineBridge::movePluginInChain(int trackIndex, int fromSlot, int toSlot)
{
    if (trackIndex < 0 || fromSlot < 0 || toSlot < 0)
        return false;

    return daw_plugin_chain_move(trackIndex, fromSlot, toSlot) == 0;
}

bool EngineBridge::setPluginBypass(int trackIndex, int slotIndex, bool bypassed)
{
    if (trackIndex < 0 || slotIndex < 0)
        return false;

    return daw_plugin_chain_set_bypass(trackIndex, slotIndex, bypassed ? 1 : 0) == 0;
}

bool EngineBridge::getPluginBypass(int trackIndex, int slotIndex)
{
    if (trackIndex < 0 || slotIndex < 0)
        return false;

    int result = daw_plugin_chain_get_bypass(trackIndex, slotIndex);
    return result == 1;  // 1 = bypassed
}

void EngineBridge::sendCommand(std::unique_ptr<Command> cmd)
{
    juce::GenericScopedLock<juce::CriticalSection> lock(commandLock);
    commandQueue.push(std::move(cmd));
    commandEvent.signal();
}

// ============================================================================
// Punch-In/Out Recording (Phase 10.1)
// ============================================================================

void EngineBridge::setPunchIn(double beats)
{
    daw_punch_in_out_set_in(static_cast<float>(beats));
}

void EngineBridge::setPunchOut(double beats)
{
    if (beats < 0)
        daw_punch_in_out_set_out(0.0f);  // 0 or negative clears punch-out
    else
        daw_punch_in_out_set_out(static_cast<float>(beats));
}

void EngineBridge::clearPunchOut()
{
    daw_punch_in_out_set_out(0.0f);  // Setting to 0 clears punch-out
}

void EngineBridge::setPreRoll(double beats)
{
    daw_punch_in_out_set_pre_roll(static_cast<float>(beats));
}

void EngineBridge::setPunchEnabled(bool enabled)
{
    daw_punch_in_out_set_enabled(enabled ? 1 : 0);
}

bool EngineBridge::isPunchEnabled() const
{
    return daw_punch_in_out_is_enabled() == 1;
}

void EngineBridge::armPunchInOut()
{
    double currentBeat = getCurrentBeat();
    daw_punch_in_out_arm(static_cast<float>(currentBeat));
}

void EngineBridge::disarmPunchInOut()
{
    daw_punch_in_out_disarm();
}

int EngineBridge::getPunchState() const
{
    return daw_punch_in_out_get_state();
}

bool EngineBridge::isInPunchRange(double beat) const
{
    return daw_punch_in_out_is_in_range(static_cast<float>(beat)) == 1;
}

double EngineBridge::getPunchIn() const
{
    return static_cast<double>(daw_punch_in_out_get_in());
}

double EngineBridge::getPunchOut() const
{
    float out = daw_punch_in_out_get_out();
    return (out < 0.0f) ? -1.0 : static_cast<double>(out);
}

double EngineBridge::getPreRoll() const
{
    return static_cast<double>(daw_punch_in_out_get_pre_roll());
}

double EngineBridge::getPreRollStart() const
{
    return static_cast<double>(daw_punch_in_out_get_pre_roll_start());
}

double EngineBridge::getPreRollProgress(double currentBeat) const
{
    float progress = 0.0f;
    int valid = daw_punch_in_out_get_pre_roll_progress(static_cast<float>(currentBeat), &progress);
    return (valid == 1) ? static_cast<double>(progress) : -1.0;
}

double EngineBridge::getBeatsUntilPunchIn(double currentBeat) const
{
    float beats = 0.0f;
    int valid = daw_punch_in_out_get_beats_until_in(static_cast<float>(currentBeat), &beats);
    return (valid == 1) ? static_cast<double>(beats) : -1.0;
}

double EngineBridge::getBeatsUntilPunchOut(double currentBeat) const
{
    float beats = 0.0f;
    int valid = daw_punch_in_out_get_beats_until_out(static_cast<float>(currentBeat), &beats);
    return (valid == 1) ? static_cast<double>(beats) : -1.0;
}

// ============================================================================
// Loop Markers (Phase 10.2)
// ============================================================================

juce::String EngineBridge::createLoopRegion(const juce::String& name, double startBeat, double endBeat)
{
    auto nameUtf8 = name.toUTF8();
    char* idPtr = daw_loop_create_region(nameUtf8.getAddress(), startBeat, endBeat);
    if (idPtr != nullptr)
    {
        juce::String id = juce::String(idPtr);
        daw_loop_free_string(idPtr);
        return id;
    }
    return juce::String();
}

bool EngineBridge::deleteLoopRegion(const juce::String& id)
{
    auto idUtf8 = id.toUTF8();
    return daw_loop_delete_region(idUtf8.getAddress()) == 0;
}

bool EngineBridge::setLoopRegionPosition(const juce::String& id, double startBeat, double endBeat)
{
    auto idUtf8 = id.toUTF8();
    return daw_loop_set_region_position(idUtf8.getAddress(), startBeat, endBeat) == 0;
}

bool EngineBridge::renameLoopRegion(const juce::String& id, const juce::String& newName)
{
    auto idUtf8 = id.toUTF8();
    auto nameUtf8 = newName.toUTF8();
    return daw_loop_rename_region(idUtf8.getAddress(), nameUtf8.getAddress()) == 0;
}

bool EngineBridge::setLoopRegionEnabled(const juce::String& id, bool enabled)
{
    auto idUtf8 = id.toUTF8();
    return daw_loop_set_region_enabled(idUtf8.getAddress(), enabled ? 1 : 0) == 0;
}

int EngineBridge::getLoopRegionCount() const
{
    return daw_loop_get_region_count();
}

EngineBridge::LoopRegion EngineBridge::getLoopRegionAt(int index) const
{
    LoopRegion region;
    LoopRegionInfoFFI ffiInfo;
    
    if (daw_loop_get_region_at(index, &ffiInfo) == 0)
    {
        if (ffiInfo.id != nullptr)
            region.id = juce::String(ffiInfo.id);
        if (ffiInfo.name != nullptr)
            region.name = juce::String(ffiInfo.name);
        region.startBeat = ffiInfo.start_beat;
        region.endBeat = ffiInfo.end_beat;
        region.enabled = ffiInfo.enabled != 0;
        if (ffiInfo.color != nullptr)
            region.color = juce::String(ffiInfo.color);
        
        daw_loop_free_region_info(&ffiInfo);
    }
    
    return region;
}

EngineBridge::LoopRegion EngineBridge::getLoopRegionById(const juce::String& id) const
{
    LoopRegion region;
    LoopRegionInfoFFI ffiInfo;
    auto idUtf8 = id.toUTF8();
    
    if (daw_loop_get_region_by_id(idUtf8.getAddress(), &ffiInfo) == 0)
    {
        if (ffiInfo.id != nullptr)
            region.id = juce::String(ffiInfo.id);
        if (ffiInfo.name != nullptr)
            region.name = juce::String(ffiInfo.name);
        region.startBeat = ffiInfo.start_beat;
        region.endBeat = ffiInfo.end_beat;
        region.enabled = ffiInfo.enabled != 0;
        if (ffiInfo.color != nullptr)
            region.color = juce::String(ffiInfo.color);
        
        daw_loop_free_region_info(&ffiInfo);
    }
    
    return region;
}

juce::String EngineBridge::getActiveLoopRegionId() const
{
    char* idPtr = daw_loop_get_active_region_id();
    if (idPtr != nullptr)
    {
        juce::String id = juce::String(idPtr);
        daw_loop_free_string(idPtr);
        return id;
    }
    return juce::String();
}

bool EngineBridge::setActiveLoopRegion(const juce::String& id)
{
    auto idUtf8 = id.toUTF8();
    return daw_loop_set_active_region(idUtf8.getAddress()) == 0;
}

bool EngineBridge::isLoopingEnabled() const
{
    return daw_loop_is_looping_enabled() == 1;
}

void EngineBridge::setLoopingEnabled(bool enabled)
{
    daw_loop_set_looping_enabled(enabled ? 1 : 0);
}

double EngineBridge::shouldLoopAtBeat(double beat) const
{
    double result = daw_loop_should_loop_at_beat(beat);
    return (result < 0.0) ? -1.0 : result;
}

bool EngineBridge::getLoopBoundaries(double beat, double& outStart, double& outEnd) const
{
    return daw_loop_get_boundaries(beat, &outStart, &outEnd) == 0;
}

std::vector<EngineBridge::LoopRegion> EngineBridge::getAllLoopRegions()
{
    std::vector<LoopRegion> result;

    int count = daw_loop_get_region_count();

    for (int i = 0; i < count; ++i)
    {
        LoopRegionInfoFFI ffiInfo;
        if (daw_loop_get_region_at(i, &ffiInfo) == 0)
        {
            LoopRegion info;
            if (ffiInfo.id != nullptr)
                info.id = juce::String(ffiInfo.id);
            if (ffiInfo.name != nullptr)
                info.name = juce::String(ffiInfo.name);
            info.startBeat = ffiInfo.start_beat;
            info.endBeat = ffiInfo.end_beat;
            info.enabled = ffiInfo.enabled != 0;
            if (ffiInfo.color != nullptr)
                info.color = juce::String(ffiInfo.color);

            result.push_back(info);
        }
        daw_loop_free_region_info(&ffiInfo);
    }

    return result;
}

bool EngineBridge::updateLoopRegion(const juce::String& id, double start, double end)
{
    return setLoopRegionPosition(id, start, end);
}

double EngineBridge::getLoopStart()
{
    juce::String activeId = getActiveLoopRegionId();
    if (activeId.isEmpty())
        return -1.0;

    LoopRegionInfoFFI ffiInfo;
    auto idUtf8 = activeId.toUTF8();
    if (daw_loop_get_region_by_id(idUtf8.getAddress(), &ffiInfo) == 0)
    {
        double start = ffiInfo.start_beat;
        daw_loop_free_region_info(&ffiInfo);
        return start;
    }
    return -1.0;
}

double EngineBridge::getLoopEnd()
{
    juce::String activeId = getActiveLoopRegionId();
    if (activeId.isEmpty())
        return -1.0;

    LoopRegionInfoFFI ffiInfo;
    auto idUtf8 = activeId.toUTF8();
    if (daw_loop_get_region_by_id(idUtf8.getAddress(), &ffiInfo) == 0)
    {
        double end = ffiInfo.end_beat;
        daw_loop_free_region_info(&ffiInfo);
        return end;
    }
    return -1.0;
}

// ============================================================================
// Time Signature (Phase 10.4)
// ============================================================================

bool EngineBridge::addTimeSignatureChange(uint32_t bar, uint8_t numerator, uint8_t denominator)
{
    int result = daw_time_sig_add_change(bar, numerator, denominator);
    return result == 0;
}

bool EngineBridge::removeTimeSignatureChange(uint32_t bar)
{
    int result = daw_time_sig_remove_change(bar);
    return result == 0;
}

std::vector<EngineBridge::TimeSignature> EngineBridge::getAllTimeSignatureChanges()
{
    std::vector<TimeSignature> result;

    // Initialize time sig track if needed
    daw_time_sig_init();

    int count = daw_time_sig_get_change_count();

    for (int i = 0; i < count; ++i)
    {
        TimeSignatureInfoFFI ffiInfo;
        if (daw_time_sig_get_change_at(i, &ffiInfo) == 0)
        {
            TimeSignature sig;
            sig.bar = ffiInfo.bar;
            sig.numerator = static_cast<uint8_t>(ffiInfo.numerator);
            sig.denominator = static_cast<uint8_t>(ffiInfo.denominator);
            result.push_back(sig);
        }
    }

    return result;
}

EngineBridge::TimeSignature EngineBridge::getTimeSignatureAtBar(uint32_t bar)
{
    TimeSignature result{1, 4, 4};  // Default 4/4

    TimeSignatureInfoFFI ffiInfo;
    if (daw_time_sig_get_at_bar(bar, &ffiInfo) == 0)
    {
        result.bar = ffiInfo.bar;
        result.numerator = static_cast<uint8_t>(ffiInfo.numerator);
        result.denominator = static_cast<uint8_t>(ffiInfo.denominator);
    }

    return result;
}

void EngineBridge::beatToBarBeat(double beat, uint32_t& bar, uint32_t& beatInBar, double& fraction)
{
    BarBeatResultFFI result;
    if (daw_time_sig_beat_to_bar_beat(beat, &result) == 0)
    {
        bar = result.bar;
        beatInBar = result.beat_in_bar;
        fraction = result.fraction;
    }
    else
    {
        bar = 1;
        beatInBar = 0;
        fraction = 0.0;
    }
}

double EngineBridge::barBeatToBeat(uint32_t bar, uint32_t beatInBar)
{
    return daw_time_sig_bar_beat_to_beat(bar, beatInBar);
}

// ============================================================================
// Tempo Automation (Phase 10.3)
// ============================================================================

void EngineBridge::initTempoAutomation(double defaultBpm)
{
    daw_tempo_auto_init(defaultBpm);
}

void EngineBridge::resetTempoAutomation(double bpm)
{
    daw_tempo_auto_reset(bpm);
}

void EngineBridge::addTempoBreakpoint(double beat, double bpm, int interpolation)
{
    daw_tempo_auto_add_breakpoint(beat, bpm, interpolation);
}

bool EngineBridge::removeTempoBreakpoint(double beat)
{
    return daw_tempo_auto_remove_breakpoint(beat) == 1;
}

int EngineBridge::getTempoBreakpointCount()
{
    return daw_tempo_auto_get_breakpoint_count();
}

EngineBridge::TempoBreakpoint EngineBridge::getTempoBreakpointAt(int index)
{
    TempoBreakpoint result{0.0, 120.0, 1};

    TempoBreakpointFFI ffiInfo;
    if (daw_tempo_auto_get_breakpoint_at(index, &ffiInfo) == 1)
    {
        result.beat = ffiInfo.beat;
        result.bpm = ffiInfo.bpm;
        result.interpolation = ffiInfo.interpolation;
    }

    return result;
}

double EngineBridge::getTempoAtBeat(double beat)
{
    return daw_tempo_auto_get_tempo_at_beat(beat);
}

double EngineBridge::getAverageTempo(double startBeat, double endBeat)
{
    return daw_tempo_auto_get_average_tempo(startBeat, endBeat);
}

double EngineBridge::beatsToSeconds(double startBeat, double endBeat)
{
    return daw_tempo_auto_beats_to_seconds(startBeat, endBeat);
}

EngineBridge::TempoBreakpoint EngineBridge::findNearestTempoBreakpoint(double beat)
{
    TempoBreakpoint result{0.0, 120.0, 1};

    TempoBreakpointFFI ffiInfo;
    if (daw_tempo_auto_find_nearest(beat, &ffiInfo) == 1)
    {
        result.beat = ffiInfo.beat;
        result.bpm = ffiInfo.bpm;
        result.interpolation = ffiInfo.interpolation;
    }

    return result;
}

void EngineBridge::updateTempoBreakpoint(double oldBeat, double newBeat, double newBpm, int interpolation)
{
    // Remove old breakpoint and add new one at updated position
    removeTempoBreakpoint(oldBeat);
    addTempoBreakpoint(newBeat, newBpm, interpolation);
}

// ============================================================================
// Arrangement View (Phase 10.5)
// ============================================================================

void EngineBridge::initArrangement(uint32_t trackCount)
{
    daw_arrangement_init(static_cast<unsigned int>(trackCount));
}

void EngineBridge::resetArrangement()
{
    daw_arrangement_reset();
}

uint32_t EngineBridge::getArrangementTrackCount()
{
    return static_cast<uint32_t>(daw_arrangement_track_count());
}

EngineBridge::ArrangementClipInfo EngineBridge::addMidiClipToArrangement(uint32_t trackIndex, double startBeat, const juce::String& name, double durationBars)
{
    ArrangementClipInfo result;
    
    uint64_t id = daw_arrangement_add_midi_clip(
        static_cast<unsigned int>(trackIndex),
        startBeat,
        name.toRawUTF8(),
        durationBars
    );
    
    if (id != 0)
    {
        result = getArrangementClipById(trackIndex, id);
    }
    
    return result;
}

EngineBridge::ArrangementClipInfo EngineBridge::addAudioClipToArrangement(uint32_t trackIndex, double startBeat, const juce::String& name, double durationBars, const juce::String& filePath)
{
    ArrangementClipInfo result;
    
    uint64_t id = daw_arrangement_add_audio_clip(
        static_cast<unsigned int>(trackIndex),
        startBeat,
        name.toRawUTF8(),
        durationBars,
        filePath.toRawUTF8()
    );
    
    if (id != 0)
    {
        result = getArrangementClipById(trackIndex, id);
    }
    
    return result;
}

bool EngineBridge::removeClipFromArrangement(uint32_t trackIndex, uint64_t clipId)
{
    int result = daw_arrangement_remove_clip(
        static_cast<unsigned int>(trackIndex),
        clipId
    );
    return result == 0;
}

bool EngineBridge::moveClipInArrangement(uint32_t fromTrack, uint64_t clipId, uint32_t toTrack, double newStart)
{
    int result = daw_arrangement_move_clip(
        static_cast<unsigned int>(fromTrack),
        clipId,
        static_cast<unsigned int>(toTrack),
        newStart
    );
    return result == 0;
}

bool EngineBridge::resizeClipInArrangement(uint32_t trackIndex, uint64_t clipId, double newDuration)
{
    int result = daw_arrangement_resize_clip(
        static_cast<unsigned int>(trackIndex),
        clipId,
        newDuration
    );
    return result == 0;
}

uint32_t EngineBridge::getArrangementClipCount(uint32_t trackIndex)
{
    return static_cast<uint32_t>(daw_arrangement_clip_count(static_cast<unsigned int>(trackIndex)));
}

uint32_t EngineBridge::getArrangementTotalClipCount()
{
    return static_cast<uint32_t>(daw_arrangement_total_clip_count());
}

std::vector<EngineBridge::ArrangementClipInfo> EngineBridge::getAllArrangementClips(uint32_t trackIndex)
{
    std::vector<ArrangementClipInfo> result;
    
    uint32_t count = getArrangementClipCount(trackIndex);
    result.reserve(count);
    
    for (uint32_t i = 0; i < count; ++i)
    {
        ArrangementClipInfoFFI ffiInfo;
        int ffiResult = daw_arrangement_get_clip_at(
            static_cast<unsigned int>(trackIndex),
            i,
            &ffiInfo
        );
        
        if (ffiResult == 0)
        {
            ArrangementClipInfo info;
            info.id = ffiInfo.id;
            info.trackIndex = ffiInfo.track_index;
            info.startBeat = ffiInfo.start_beat;
            info.durationBeats = ffiInfo.duration_beats;
            info.name = juce::String(ffiInfo.name);
            info.isAudio = ffiInfo.is_audio != 0;
            result.push_back(info);
            
            // Free the allocated name string
            daw_arrangement_free_clip_info(&ffiInfo);
        }
    }
    
    return result;
}

EngineBridge::ArrangementClipInfo EngineBridge::getArrangementClipById(uint32_t trackIndex, uint64_t clipId)
{
    ArrangementClipInfo result;
    
    ArrangementClipInfoFFI ffiInfo;
    int ffiResult = daw_arrangement_get_clip_by_id(
        static_cast<unsigned int>(trackIndex),
        clipId,
        &ffiInfo
    );
    
    if (ffiResult == 0)
    {
        result.id = ffiInfo.id;
        result.trackIndex = ffiInfo.track_index;
        result.startBeat = ffiInfo.start_beat;
        result.durationBeats = ffiInfo.duration_beats;
        result.name = juce::String(ffiInfo.name);
        result.isAudio = ffiInfo.is_audio != 0;
        
        // Free the allocated name string
        daw_arrangement_free_clip_info(&ffiInfo);
    }
    
    return result;
}

double EngineBridge::getArrangementTotalDuration()
{
    return daw_arrangement_total_duration();
}

bool EngineBridge::canMoveClipTo(uint32_t trackIndex, uint64_t clipId, double newStart, double duration)
{
    int result = daw_arrangement_can_move_to(
        static_cast<unsigned int>(trackIndex),
        clipId,
        newStart,
        duration
    );
    return result == 1;
}

std::vector<uint64_t> EngineBridge::getArrangementClipsInRange(uint32_t trackIndex, double startBeat, double endBeat)
{
    std::vector<uint64_t> result;
    
    uint64_t ids[64];  // Max 64 clips in range
    unsigned int count = daw_arrangement_clips_in_range(
        static_cast<unsigned int>(trackIndex),
        startBeat,
        endBeat,
        ids,
        64
    );
    
    result.reserve(count);
    for (unsigned int i = 0; i < count; ++i)
    {
        result.push_back(ids[i]);
    }
    
    return result;
}

uint64_t EngineBridge::getArrangementClipAtBeat(uint32_t trackIndex, double beat)
{
    return daw_arrangement_clip_at_beat(
        static_cast<unsigned int>(trackIndex),
        beat
    );
}

std::vector<uint64_t> EngineBridge::getActiveArrangementClips(double beat)
{
    std::vector<uint64_t> result;
    
    uint64_t ids[64];  // Max 64 active clips
    unsigned int count = daw_arrangement_active_clips(
        beat,
        ids,
        64
    );
    
    result.reserve(count);
    for (unsigned int i = 0; i < count; ++i)
    {
        result.push_back(ids[i]);
    }
    
    return result;
}
