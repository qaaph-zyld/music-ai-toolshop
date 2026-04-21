#include "ChannelStrip.h"
#include <iostream>

ChannelStrip::ChannelStrip(int channelIndex, bool isMasterChannel)
    : channelIdx(channelIndex), isMaster(isMasterChannel)
{
    std::cout << "ChannelStrip constructor - START (index=" << channelIndex << ")" << std::endl;
    
    if (isMaster)
        channelName = "Master";
    else
        channelName = "Ch " + juce::String(channelIdx + 1);

    std::cout << "ChannelStrip: Setting size..." << std::endl;
    setSize(80, 300);
    
    std::cout << "ChannelStrip: Setting up controls..." << std::endl;
    setupControls();

    std::cout << "ChannelStrip: Creating level meter..." << std::endl;
    levelMeter = std::make_unique<LevelMeterComponent>(
        LevelMeterComponent::Orientation::Vertical,
        LevelMeterComponent::Style::PeakAndRMS);
    addAndMakeVisible(levelMeter.get());

    std::cout << "ChannelStrip: Starting timer..." << std::endl;
    startTimer(33);
    
    std::cout << "ChannelStrip constructor - END" << std::endl;
}

ChannelStrip::~ChannelStrip()
{
    stopTimer();
}

void ChannelStrip::setupControls()
{
    // Name label
    nameLabel.setText(channelName, juce::dontSendNotification);
    nameLabel.setJustificationType(juce::Justification::centred);
    nameLabel.setFont(juce::Font(11.0f, juce::Font::bold));
    addAndMakeVisible(nameLabel);

    // Volume fader
    volumeSlider.setRange(-60.0, 12.0, 0.1);
    volumeSlider.setValue(0.0, juce::dontSendNotification);
    volumeSlider.setTextValueSuffix(" dB");
    volumeSlider.setTooltip("Volume");
    volumeSlider.onValueChange = [this] {
        if (onVolumeChange) onVolumeChange(static_cast<float>(volumeSlider.getValue()));
    };
    addAndMakeVisible(volumeSlider);

    // Pan knob
    panSlider.setRange(-1.0, 1.0, 0.01);
    panSlider.setValue(0.0, juce::dontSendNotification);
    panSlider.setTooltip("Pan (L/R)");
    panSlider.onValueChange = [this] {
        if (onPanChange) onPanChange(static_cast<float>(panSlider.getValue()));
    };
    addAndMakeVisible(panSlider);

    // Mute button
    muteButton.setTooltip("Mute");
    muteButton.onClick = [this] {
        if (onMuteToggle) onMuteToggle();
    };
    addAndMakeVisible(muteButton);

    // Solo button (not for master)
    if (!isMaster)
    {
        soloButton.setTooltip("Solo");
        soloButton.onClick = [this] {
            if (onSoloToggle) onSoloToggle();
        };
        addAndMakeVisible(soloButton);

        // Arm button (not for master)
        armButton.setTooltip("Arm for recording");
        addAndMakeVisible(armButton);
    }

    updateButtonColors();
}

void ChannelStrip::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds();

    // Background
    g.fillAll(juce::Colour(0xFF3B3B3B));

    // Border
    g.setColour(juce::Colour(0xFF4B4B4B));
    g.drawRect(bounds, 1);
}

void ChannelStrip::resized()
{
    std::cout << "ChannelStrip::resized - START" << std::endl;
    auto bounds = getLocalBounds().reduced(2);

    // Name at top
    std::cout << "ChannelStrip::resized - setting nameLabel bounds" << std::endl;
    nameLabel.setBounds(bounds.removeFromTop(25));

    // Meter on the right side (Phase 7.2: LevelMeterComponent)
    std::cout << "ChannelStrip::resized - setting levelMeter bounds" << std::endl;
    auto meterWidth = 20;
    auto meterArea = bounds.removeFromRight(meterWidth);
    if (levelMeter)
        levelMeter->setBounds(meterArea.reduced(0, 2));

    // Pan knob
    panSlider.setBounds(bounds.removeFromTop(25).reduced(2));

    // Mute/Solo/Arm buttons
    if (!isMaster)
    {
        auto buttonRow = bounds.removeFromTop(25);
        muteButton.setBounds(buttonRow.removeFromLeft(buttonRow.getWidth() / 2).reduced(1));
        soloButton.setBounds(buttonRow.reduced(1));

        armButton.setBounds(bounds.removeFromTop(20).reduced(2));
    }
    else
    {
        // Master only has mute
        muteButton.setBounds(bounds.removeFromTop(25).reduced(2));
    }

    // Volume fader fills remaining space
    volumeSlider.setBounds(bounds.reduced(2));
}

void ChannelStrip::timerCallback()
{
    // Timer is handled by LevelMeterComponent internally
    // This is kept for potential future expansion
}

void ChannelStrip::setMeterLevel(float peakDb, float rmsDb)
{
    if (levelMeter != nullptr)
    {
        levelMeter->setLevels(peakDb, rmsDb);
    }
}

void ChannelStrip::setMeterLevel(float dbLevel)
{
    // Legacy compatibility: set both peak and RMS to same value
    setMeterLevel(dbLevel, dbLevel);
}

void ChannelStrip::setVolume(float db)
{
    volumeSlider.setValue(db, juce::dontSendNotification);
}

void ChannelStrip::setPan(float pan)
{
    panSlider.setValue(pan, juce::dontSendNotification);
}

void ChannelStrip::setMuted(bool muted)
{
    muteButton.setToggleState(muted, juce::dontSendNotification);
    updateButtonColors();
}

void ChannelStrip::setSoloed(bool soloed)
{
    soloButton.setToggleState(soloed, juce::dontSendNotification);
    updateButtonColors();
}

void ChannelStrip::updateButtonColors()
{
    // Mute: yellow when active
    muteButton.setColour(juce::TextButton::buttonColourId,
                         muteButton.getToggleState() ? juce::Colours::yellow.darker(0.3f)
                                                      : juce::Colour(0xFF5B5B5B));

    // Solo: blue when active
    soloButton.setColour(juce::TextButton::buttonColourId,
                         soloButton.getToggleState() ? juce::Colours::cyan.darker(0.3f)
                                                      : juce::Colour(0xFF5B5B5B));

    // Arm: red when active
    armButton.setColour(juce::ToggleButton::tickColourId,
                        armButton.getToggleState() ? juce::Colours::red : juce::Colours::grey);
}
