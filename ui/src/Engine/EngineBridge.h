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

    // Punch-In/Out Recording (Phase 10.1)
    void setPunchIn(double beats);
    void setPunchOut(double beats);  // -1 to disable
    void clearPunchOut();
    void setPreRoll(double beats);
    void setPunchEnabled(bool enabled);
    bool isPunchEnabled() const;
    void armPunchInOut();
    void disarmPunchInOut();
    int getPunchState() const;  // 0=disarmed, 1=armed, 2=preroll, 3=recording, 4=completed
    bool isInPunchRange(double beat) const;
    double getPunchIn() const;
    double getPunchOut() const;  // -1 if not set
    double getPreRoll() const;
    double getPreRollStart() const;
    double getPreRollProgress(double currentBeat) const;  // Returns 0.0-1.0 or -1.0 if not pre-rolling
    double getBeatsUntilPunchIn(double currentBeat) const;  // Returns -1.0 if not applicable
    double getBeatsUntilPunchOut(double currentBeat) const;  // Returns -1.0 if not applicable

    // Loop Markers (Phase 10.2)
    struct LoopRegion {
        juce::String id;
        juce::String name;
        double startBeat = 0.0;
        double endBeat = 4.0;
        bool enabled = true;
        juce::String color = "#4A90E2";
    };

    juce::String createLoopRegion(const juce::String& name, double startBeat, double endBeat);
    bool deleteLoopRegion(const juce::String& id);
    int getLoopRegionCount() const;
    LoopRegion getLoopRegionAt(int index) const;
    LoopRegion getLoopRegionById(const juce::String& id) const;
    bool setLoopRegionPosition(const juce::String& id, double startBeat, double endBeat);
    bool updateLoopRegion(const juce::String& id, double start, double end);
    bool renameLoopRegion(const juce::String& id, const juce::String& newName);
    bool setLoopRegionEnabled(const juce::String& id, bool enabled);
    juce::String getActiveLoopRegionId() const;
    bool setActiveLoopRegion(const juce::String& id);
    bool isLoopingEnabled() const;
    void setLoopingEnabled(bool enabled);
    double shouldLoopAtBeat(double beat) const;  // Returns loop point or -1.0
    bool getLoopBoundaries(double beat, double& outStart, double& outEnd) const;  // Returns true if in loop
    double getLoopStart();
    double getLoopEnd();
    std::vector<LoopRegion> getAllLoopRegions();

    // Time Signature (Phase 10.4)
    struct TimeSignature {
        uint32_t bar = 1;
        uint8_t numerator = 4;
        uint8_t denominator = 4;
    };

    bool addTimeSignatureChange(uint32_t bar, uint8_t numerator, uint8_t denominator);
    bool removeTimeSignatureChange(uint32_t bar);
    std::vector<TimeSignature> getAllTimeSignatureChanges();
    TimeSignature getTimeSignatureAtBar(uint32_t bar);
    void beatToBarBeat(double beat, uint32_t& bar, uint32_t& beatInBar, double& fraction);
    double barBeatToBeat(uint32_t bar, uint32_t beatInBar);

    // Tempo Automation (Phase 10.3)
    struct TempoBreakpoint {
        double beat = 0.0;
        double bpm = 120.0;
        int interpolation = 1; // 0=step, 1=linear, 2=exponential, 3=smooth
    };

    void initTempoAutomation(double defaultBpm);
    void resetTempoAutomation(double bpm);
    void addTempoBreakpoint(double beat, double bpm, int interpolation);
    bool removeTempoBreakpoint(double beat);
    int getTempoBreakpointCount();
    TempoBreakpoint getTempoBreakpointAt(int index);
    double getTempoAtBeat(double beat);
    double getAverageTempo(double startBeat, double endBeat);
    double beatsToSeconds(double startBeat, double endBeat);
    TempoBreakpoint findNearestTempoBreakpoint(double beat);
    void updateTempoBreakpoint(double oldBeat, double newBeat, double newBpm, int interpolation);

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
    
    // Create MIDI clip from recorded notes (Phase 6)
    bool createMidiClip(int trackIndex, int sceneIndex, const std::vector<RecordedNote>& notes, const juce::String& clipName);

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

    // MIDI Editing (Phase 8)
    struct MidiNoteData {
        int pitch = 60;
        int velocity = 100;
        float startBeat = 0.0f;
        float durationBeats = 1.0f;
    };
    
    // Quantize MIDI notes to grid (e.g., 0.25 = 1/16, 0.5 = 1/8)
    std::vector<MidiNoteData> quantizeMidiNotes(const std::vector<MidiNoteData>& notes, float gridDivision);
    
    // Transpose MIDI notes by semitones (positive = up, negative = down)
    std::vector<MidiNoteData> transposeMidiNotes(const std::vector<MidiNoteData>& notes, int semitones);
    
    // Scale velocities by factor (1.0 = no change, 1.5 = 50% louder)
    std::vector<MidiNoteData> scaleMidiVelocities(const std::vector<MidiNoteData>& notes, float scale);
    
    // Duplicate MIDI clip to new location
    bool duplicateMidiClip(int fromTrack, int fromScene, int toTrack, int toScene);

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

    // Plugin Chain Management (Phase 9)
    struct PluginInfo {
        juce::String name;
        juce::String vendor;
        juce::String version;
        juce::String uniqueId;
        int format;  // 0=VST3, 1=AU, 2=Internal
        int numInputs;
        int numOutputs;
    };

    // Plugin Registry
    std::vector<PluginInfo> scanPluginRegistry();
    std::vector<PluginInfo> searchPlugins(const juce::String& query);

    // Plugin Chain
    bool createPluginChain(int trackIndex);
    int getPluginChainCount(int trackIndex);
    std::vector<PluginInfo> getPluginChain(int trackIndex);
    int addPluginToChain(int trackIndex, const juce::String& uniqueId);
    bool removePluginFromChain(int trackIndex, int slotIndex);
    bool movePluginInChain(int trackIndex, int fromSlot, int toSlot);
    bool setPluginBypass(int trackIndex, int slotIndex, bool bypassed);
    bool getPluginBypass(int trackIndex, int slotIndex);

    // Arrangement View (Phase 10.5)
    struct ArrangementClipInfo {
        uint64_t id = 0;
        uint32_t trackIndex = 0;
        double startBeat = 0.0;
        double durationBeats = 4.0;
        juce::String name;
        bool isAudio = false;
        
        bool isValid() const { return id != 0; }
        double endBeat() const { return startBeat + durationBeats; }
    };
    
    void initArrangement(uint32_t trackCount);
    void resetArrangement();
    uint32_t getArrangementTrackCount();
    ArrangementClipInfo addMidiClipToArrangement(uint32_t trackIndex, double startBeat, const juce::String& name, double durationBars);
    ArrangementClipInfo addAudioClipToArrangement(uint32_t trackIndex, double startBeat, const juce::String& name, double durationBars, const juce::String& filePath);
    bool removeClipFromArrangement(uint32_t trackIndex, uint64_t clipId);
    bool moveClipInArrangement(uint32_t fromTrack, uint64_t clipId, uint32_t toTrack, double newStart);
    bool resizeClipInArrangement(uint32_t trackIndex, uint64_t clipId, double newDuration);
    uint32_t getArrangementClipCount(uint32_t trackIndex);
    uint32_t getArrangementTotalClipCount();
    std::vector<ArrangementClipInfo> getAllArrangementClips(uint32_t trackIndex);
    ArrangementClipInfo getArrangementClipById(uint32_t trackIndex, uint64_t clipId);
    double getArrangementTotalDuration();
    bool canMoveClipTo(uint32_t trackIndex, uint64_t clipId, double newStart, double duration);
    std::vector<uint64_t> getArrangementClipsInRange(uint32_t trackIndex, double startBeat, double endBeat);
    uint64_t getArrangementClipAtBeat(uint32_t trackIndex, double beat);
    std::vector<uint64_t> getActiveArrangementClips(double beat);

    // Audio callbacks (called from audio thread)
    void getMeterLevels(std::vector<float>& levels); // Per-channel dB levels
    
    // Test tone for audio check (Session Z: Onboarding)
    void playTestTone(float frequency, float amplitude);
    void stopTestTone();

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
