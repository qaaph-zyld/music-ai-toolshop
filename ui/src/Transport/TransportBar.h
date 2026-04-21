#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_audio_utils/juce_audio_utils.h>

class TransportBar : public juce::Component,
                     public juce::Timer
{
public:
    TransportBar();
    ~TransportBar() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Timer callback for updating time display
    void timerCallback() override;

    // Transport control callbacks
    std::function<void()> onPlay;
    std::function<void()> onStop;
    std::function<void()> onRecord;
    std::function<void()> onRewind;
    std::function<void(double bpm)> onTempoChange;

    // State setters (called from engine)
    void setPlaying(bool playing);
    void setRecording(bool recording);
    void setPosition(double beats);
    void setTempo(double bpm);

private:
    // Transport buttons
    juce::TextButton playButton{u8"\u25B6"};  // Play triangle
    juce::TextButton stopButton{u8"\u25A0"};  // Stop square
    juce::TextButton recordButton{u8"\u25CF"}; // Record circle
    juce::TextButton rewindButton{u8"\u23EE"}; // Rewind

    // Tempo controls
    juce::Label tempoLabel{"Tempo:", "Tempo:"};
    juce::Slider tempoSlider{juce::Slider::IncDecButtons, juce::Slider::TextBoxAbove};
    juce::Label bpmLabel{"BPM", "BPM"};

    // Time display
    juce::Label timeDisplay{"Time", "1.1.1"};

    // Metronome toggle
    juce::ToggleButton metronomeButton{"Metronome"};

    // State
    bool isPlaying = false;
    bool isRecording = false;
    double currentPosition = 0.0; // in beats
    double currentTempo = 120.0;

    void setupControls();
    void updateButtonStates();
    void updateTimeDisplay();
    juce::String formatTimeDisplay(double beats);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(TransportBar)
};
