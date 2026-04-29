#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "ChannelStrip.h"

class MixerPanel : public juce::Component,
                   public juce::Timer
{
public:
    explicit MixerPanel(int numChannels);
    ~MixerPanel() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;

    // Audio metering (called from audio thread - legacy)
    void setMeterLevel(int channelIndex, float dbLevel);
    
    // Phase 7: Poll meter levels from engine (called from timer)
    void pollMeterLevels();

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
    
    // Phase 7: Meter polling timer (30fps)
    static constexpr int meterTimerIntervalMs = 33;

    void setupChannels();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MixerPanel)
};
