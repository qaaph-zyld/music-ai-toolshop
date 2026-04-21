#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

class TrackHeaderComponent : public juce::Component
{
public:
    TrackHeaderComponent(int trackIndex);
    ~TrackHeaderComponent() override = default;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Track properties
    void setTrackName(const juce::String& name);
    void setTrackColor(juce::Colour color);

    // Control getters for external binding
    juce::TextButton& getArmButton() { return armButton; }
    juce::TextButton& getMuteButton() { return muteButton; }
    juce::TextButton& getSoloButton() { return soloButton; }
    juce::Slider& getVolumeSlider() { return volumeSlider; }
    juce::Slider& getPanSlider() { return panSlider; }

    // State setters
    void setArmed(bool armed);
    void setMuted(bool muted);
    void setSoloed(bool soloed);

private:
    int trackIdx;
    juce::String trackName{"Track " + juce::String(trackIdx + 1)};
    juce::Colour trackColor{juce::Colours::grey};

    // Controls
    juce::Label nameLabel;
    juce::TextButton armButton{"R"};
    juce::TextButton muteButton{"M"};
    juce::TextButton soloButton{"S"};
    juce::Slider volumeSlider{juce::Slider::LinearVertical, juce::Slider::NoTextBox};
    juce::Slider panSlider{juce::Slider::LinearHorizontal, juce::Slider::NoTextBox};

    bool isArmed = false;
    bool isMuted = false;
    bool isSoloed = false;

    void setupControls();
    void updateButtonColors();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(TrackHeaderComponent)
};
