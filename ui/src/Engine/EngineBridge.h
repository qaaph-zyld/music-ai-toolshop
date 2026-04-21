#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <vector>

/**
 * TriggeredClipInfo - Information about a clip triggered by transport sync
 */
struct TriggeredClipInfo
{
    int trackIndex = -1;
    int clipIndex = -1;
    double beat = 0.0;
    bool looped = false;
    
    bool isValid() const { return trackIndex >= 0 && clipIndex >= 0; }
};

/**
 * EngineBridge - FFI bridge between JUCE UI and Rust audio engine
 *
 * This class handles communication between the C++ UI layer and the Rust audio engine.
 * It uses a simple message queue for thread-safe communication.
 */
class EngineBridge : public juce::Thread
{
public:
    static EngineBridge& getInstance();

    // Lifecycle
    bool initialize(int sampleRate, int bufferSize);
    void shutdown();
    bool isInitialized() const { return initialized; }

    // Transport controls
    void play();
    void stop();
    void record();
    void setPosition(double beats);
    void setTempo(double bpm);
    double getTempo() const;
    bool isPlaying() const;
    bool isRecording() const;
    double getCurrentBeat() const;

    // Clip management
    void launchClip(int trackIndex, int sceneIndex);
    void stopClip(int trackIndex, int sceneIndex);
    void loadClip(int trackIndex, int sceneIndex, const juce::String& filePath);
    void moveClip(int fromTrack, int fromScene, int toTrack, int toScene); // Phase 7.0: Drag & Drop
    
    // Clip player state (Phase 6.3 clip_player_ffi)
    int getClipState(int trackIndex, int clipIndex); // Returns: 0=stopped, 1=playing, 2=queued
    bool isClipPlaying(int trackIndex);
    int getPlayingClip(int trackIndex); // Returns clip index or -1
    void queueClip(int trackIndex, int clipIndex);

    // Transport Sync / Scheduling (Phase 6.6)
    void scheduleClip(int trackIndex, int clipIndex, double targetBeat, bool looped = false);
    void scheduleClipQuantized(int trackIndex, int clipIndex, int quantizationBars = 1);
    void cancelScheduledClip(int trackIndex, int clipIndex);
    void cancelAllScheduledClips(int trackIndex);
    bool isClipScheduled(int trackIndex) const;
    double getNextScheduledBeat(int trackIndex) const;
    
    // UI State Polling (Phase 6.6)
    TriggeredClipInfo pollTriggeredClip(); // Returns next triggered clip, or invalid if none
    std::vector<TriggeredClipInfo> pollAllTriggeredClips();

    // Track controls
    void setTrackVolume(int trackIndex, float db);
    void setTrackPan(int trackIndex, float pan);
    void setTrackMute(int trackIndex, bool muted);
    void setTrackSolo(int trackIndex, bool soloed);
    void armTrack(int trackIndex, bool armed);

    // Scene controls
    void launchScene(int sceneIndex);
    void stopAll();

    // MIDI Recording (Phase 7.1)
    struct MidiDeviceInfo {
        juce::String id;
        juce::String name;
        bool isAvailable;
    };
    
    struct RecordedNote {
        uint8_t pitch;
        uint8_t velocity;
        float startBeat;
        float duration;
    };
    
    std::vector<MidiDeviceInfo> getMidiInputDevices();
    void selectMidiInputDevice(const juce::String& deviceId);
    void startMidiRecording(int trackIndex, int sceneIndex, float startBeat);
    std::vector<RecordedNote> stopMidiRecording();
    bool isMidiRecording() const;
    void setQuantization(float gridDivision, float strength);

    // Meter Level Meters (Phase 7.2)
    struct MeterLevels {
        float peakDb = -96.0f;  // Peak level in dB (0.0 = unity)
        float rmsDb = -96.0f;   // RMS level in dB
        
        bool isClipping() const { return peakDb > 0.0f; }
        bool isSilent() const { return peakDb < -60.0f; }
    };
    
    // Get meter levels for a specific track
    MeterLevels getTrackMeterLevels(int trackIndex);
    
    // Get master output meter levels
    MeterLevels getMasterMeterLevels();

    // Project Management (Phase 7.3)
    bool newProject();
    bool saveProject(const juce::String& path);
    bool loadProject(const juce::String& path);
    bool saveCurrentProject(); // Save to current path
    juce::String getCurrentProjectPath() const;
    bool isProjectModified() const;

    // Stem Separation (Phase 8.x)
    struct StemPaths {
        juce::String drums;
        juce::String bass;
        juce::String vocals;
        juce::String other;
        bool success = false;
    };
    
    bool isStemSeparationAvailable();
    StemPaths extractStems(const juce::String& inputPath, 
                           const juce::String& outputDir,
                           std::function<void(float progress)> onProgress = nullptr);
    void cancelStemExtraction();

    // Audio callbacks (called from audio thread)
    void getMeterLevels(std::vector<float>& levels); // Per-channel dB levels

    // State callbacks (UI thread)
    std::function<void(bool isPlaying)> onTransportStateChange;
    std::function<void(double position)> onPositionChange;
    std::function<void(int track, int scene, bool isPlaying)> onClipStateChange;

private:
    EngineBridge();
    ~EngineBridge() override;

    void run() override; // Thread loop for processing commands

    // Command queue for thread-safe communication
    struct Command;
    std::queue<std::unique_ptr<Command>> commandQueue;
    juce::CriticalSection commandLock;
    juce::WaitableEvent commandEvent;

    void sendCommand(std::unique_ptr<Command> cmd);

    // Rust FFI handles (opaque pointers)
    void* rustEngine = nullptr;
    void* rustTransport = nullptr;
    void* rustMixer = nullptr;
    void* rustSession = nullptr;
    void* transportSyncHandle = nullptr; // Phase 6.6: transport_sync instance
    void* stemSeparatorHandle = nullptr; // Phase 8.x: stem separator handle

    bool initialized = false;
    juce::String currentProjectPath; // Phase 7.3: Current project file path

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(EngineBridge)
};
