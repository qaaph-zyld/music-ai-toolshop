#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "ChannelStrip.h"

class MixerPanel : public juce::Component
{
public:
    explicit MixerPanel(int numChannels);
    ~MixerPanel() override = default;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Audio metering (called from audio thread)
    void setMeterLevel(int channelIndex, float dbLevel);

    // Control access for binding to engine
    ChannelStrip* getChannelStrip(int index);

    // Master strip access
    ChannelStrip* getMasterStrip() { return masterStrip.get(); }

private:
    int numChannels;
    std::vector<std::unique_ptr<ChannelStrip>> channelStrips;
    std::unique_ptr<ChannelStrip> masterStrip;

    juce::Viewport viewport;
    juce::Component contentComponent;

    void setupChannels();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MixerPanel)
};
