#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>
#include "../Engine/EngineBridge.h"

/**
 * RecordingPanel - MIDI Recording Controls
 * 
 * Provides UI for:
 * - Recording start/stop
 * - MIDI device selection
 * - Quantization settings
 * - Recording timer/beat display
 */
class RecordingPanel : public juce::Component,
                       public juce::Timer
{
public:
    RecordingPanel();
    ~RecordingPanel() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;

    // Refresh MIDI device list
    void refreshDevices();

    // Recording target setters/getters
    void setTargetTrack(int track) { targetTrack = track; }
    void setTargetScene(int scene) { targetScene = scene; }
    int getTargetTrack() const { return targetTrack; }
    int getTargetScene() const { return targetScene; }
    void updateTargetLabel();

    // Callback for recording completion - Phase 7.1
    // Called when recording stops with recorded notes
    std::function<void(int track, int scene, const juce::Array<EngineBridge::RecordedNote>& notes)> onRecordingComplete;

private:
    // UI Components
    juce::TextButton recordButton;
    juce::ComboBox deviceSelector;
    juce::ComboBox quantizeSelector;
    juce::Label statusLabel;
    juce::Label timerLabel;
    juce::Label deviceLabel;
    juce::Label quantizeLabel;
    juce::Label targetLabel;

    // State
    bool isRecording = false;
    double recordingStartBeat = 0.0;
    int selectedDeviceIndex = -1;
    
    // Track/Scene for recording target
    int targetTrack = 0;
    int targetScene = 0;

    // Callbacks
    void onRecordButtonClicked();
    void onDeviceChanged();
    void onQuantizeChanged();
    
    // Update UI state
    void updateStatus();
    void updateTimer();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(RecordingPanel)
};
