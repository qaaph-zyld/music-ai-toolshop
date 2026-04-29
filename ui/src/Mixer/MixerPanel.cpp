#include "MixerPanel.h"
#include "../Engine/EngineBridge.h"
#include <iostream>

MixerPanel::MixerPanel(int numChannels_)
    : numChannels(numChannels_)
{
    std::cout << "MixerPanel constructor - START" << std::endl;
    setupChannels();
    setSize(800, 250);
    
    // Phase 7: Start meter polling timer (30fps)
    startTimer(meterTimerIntervalMs);
    std::cout << "MixerPanel constructor - meter polling timer started" << std::endl;
    
    std::cout << "MixerPanel constructor - END" << std::endl;
}

MixerPanel::~MixerPanel()
{
    stopTimer();
}

void MixerPanel::setupChannels()
{
    std::cout << "MixerPanel::setupChannels - START" << std::endl;
    // Create channel strips with EngineBridge callback wiring
    for (int i = 0; i < numChannels; ++i)
    {
        std::cout << "MixerPanel: Creating ChannelStrip " << i << std::endl;
        auto strip = std::make_unique<ChannelStrip>(i, false);

        // Wire callbacks to EngineBridge
        strip->onVolumeChange = [i](float db) {
            EngineBridge::getInstance().setTrackVolume(i, db);
        };
        strip->onPanChange = [i](float pan) {
            EngineBridge::getInstance().setTrackPan(i, pan);
        };
        strip->onMuteToggle = [i, this]() {
            auto* strip = channelStrips[i].get();
            if (strip)
            {
                bool muted = strip->getVolume() < -59.0f; // Approximate mute detection
                EngineBridge::getInstance().setTrackMute(i, muted);
            }
        };
        strip->onSoloToggle = [i]() {
            // Toggle solo state - engine will handle the logic
            EngineBridge::getInstance().setTrackSolo(i, true);
        };

        channelStrips.push_back(std::move(strip));
        contentComponent.addAndMakeVisible(channelStrips.back().get());
    }

    // Create master strip
    masterStrip = std::make_unique<ChannelStrip>(-1, true);
    contentComponent.addAndMakeVisible(masterStrip.get());

    // Set up viewport
    addAndMakeVisible(viewport);
    viewport.setViewedComponent(&contentComponent, false);
    viewport.setScrollBarsShown(false, true); // Horizontal scrolling only

    // Layout content
    int stripWidth = 80;
    int stripHeight = 240;
    int contentWidth = (numChannels + 1) * (stripWidth + 5) + 20;
    int contentHeight = stripHeight + 20;
    contentComponent.setSize(contentWidth, contentHeight);

    // Position strips
    int x = 10;
    for (auto& strip : channelStrips)
    {
        strip->setBounds(x, 10, stripWidth, stripHeight);
        x += stripWidth + 5;
    }

    // Master strip at the end
    x += 10; // Extra gap before master
    masterStrip->setBounds(x, 10, stripWidth, stripHeight);
}

void MixerPanel::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(0xFF2B2B2B));

    // Top border
    g.setColour(juce::Colour(0xFF3B3B3B));
    g.drawHorizontalLine(0, 0, getWidth());
}

void MixerPanel::resized()
{
    viewport.setBounds(getLocalBounds());
}

void MixerPanel::setMeterLevel(int channelIndex, float dbLevel)
{
    // Legacy method - kept for backward compatibility
    if (channelIndex >= 0 && channelIndex < numChannels)
    {
        channelStrips[channelIndex]->setMeterLevel(dbLevel);
    }
    else if (channelIndex == -1) // Master
    {
        masterStrip->setMeterLevel(dbLevel);
    }
}

void MixerPanel::timerCallback()
{
    pollMeterLevels();
}

void MixerPanel::pollMeterLevels()
{
    // Phase 7: Poll meter levels from EngineBridge and update ChannelStrips
    auto& engine = EngineBridge::getInstance();
    
    if (!engine.isInitialized())
        return;
    
    // Update track meters
    for (int i = 0; i < numChannels; ++i)
    {
        auto levels = engine.getTrackMeterLevels(i);
        if (i < (int)channelStrips.size())
        {
            channelStrips[i]->setMeterLevel(levels.peakDb, levels.rmsDb);
        }
    }
    
    // Update master meter
    if (masterStrip != nullptr)
    {
        auto masterLevels = engine.getMasterMeterLevels();
        masterStrip->setMeterLevel(masterLevels.peakDb, masterLevels.rmsDb);
    }
}

ChannelStrip* MixerPanel::getChannelStrip(int index)
{
    if (index >= 0 && index < numChannels)
    {
        return channelStrips[index].get();
    }
    return nullptr;
}
