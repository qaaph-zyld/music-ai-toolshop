#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "../Engine/EngineBridge.h"

namespace OpenDAW {

/**
 * Audio test dialog for verifying audio output works.
 * Plays a test tone and asks user if they can hear it.
 */
class AudioTestDialog : public juce::Component, 
                        public juce::Timer
{
public:
    AudioTestDialog();
    ~AudioTestDialog() override;
    
    // Callbacks
    std::function<void()> onAudioWorking;
    std::function<void()> onAudioNotWorking;
    std::function<void()> onOpenSettings;
    
    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;

private:
    juce::Label titleLabel;
    juce::Label instructionLabel;
    juce::TextButton playToneButton;
    juce::TextButton yesButton;
    juce::TextButton noButton;
    juce::TextButton settingsButton;
    
    bool isPlayingTone = false;
    
    void setupUI();
    void playTestTone();
    void stopTestTone();
};

} // namespace OpenDAW
