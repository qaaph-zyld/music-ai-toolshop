#include "EngineBridge.h"

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
    
    // Stem Separation FFI (Phase 8.x)
    void* daw_stem_separator_create();
    void daw_stem_separator_free(void* handle);
    int daw_stem_is_available(void* handle);
    int daw_stem_separate(void* handle, const char* input_path, const char* output_dir);
    double daw_stem_get_progress(void* handle);
    int daw_stem_is_complete(void* handle);
    const char* daw_stem_get_path(void* handle, int stem_type);
    void daw_stem_cancel(void* handle);
}

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
    (void)trackIndex;
    (void)sceneIndex;
    (void)filePath;
    // TODO: Implement clip loading via FFI when available
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

void EngineBridge::sendCommand(std::unique_ptr<Command> cmd)
{
    juce::GenericScopedLock<juce::CriticalSection> lock(commandLock);
    commandQueue.push(std::move(cmd));
    commandEvent.signal();
}
