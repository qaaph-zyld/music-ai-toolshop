#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_audio_utils/juce_audio_utils.h>
#include "LevelMeterComponent.h"

class ChannelStrip : public juce::Component,
                     public juce::Timer
{
public:
    explicit ChannelStrip(int channelIndex, bool isMaster = false);
    ~ChannelStrip() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;

    // Audio metering - updates both peak and RMS
    void setMeterLevel(float peakDb, float rmsDb);
    void setMeterLevel(float dbLevel); // Legacy: sets both peak and RMS

    // Control setters/getters
    void setVolume(float db);
    void setPan(float pan); // -1 to 1
    void setMuted(bool muted);
    void setSoloed(bool soloed);

    float getVolume() const { return volumeSlider.getValue(); }
    float getPan() const { return panSlider.getValue(); }

    // Callbacks for external binding
    std::function<void(float db)> onVolumeChange;
    std::function<void(float pan)> onPanChange;
    std::function<void()> onMuteToggle;
    std::function<void()> onSoloToggle;

private:
    int channelIdx;
    bool isMaster;
    juce::String channelName;

    // Controls
    juce::Label nameLabel;
    juce::Slider volumeSlider{juce::Slider::LinearVertical, juce::Slider::TextBoxBelow};
    juce::Slider panSlider{juce::Slider::LinearHorizontal, juce::Slider::NoTextBox};
    juce::TextButton muteButton{"M"};
    juce::TextButton soloButton{"S"};
    juce::ToggleButton armButton{"R"};

    // Level meter component (Phase 7.2)
    std::unique_ptr<LevelMeterComponent> levelMeter;

    void setupControls();
    void updateButtonColors();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ChannelStrip)
};
