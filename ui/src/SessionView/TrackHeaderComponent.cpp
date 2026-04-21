#include "TrackHeaderComponent.h"
#include "../Engine/EngineBridge.h"

TrackHeaderComponent::TrackHeaderComponent(int trackIndex)
    : trackIdx(trackIndex)
{
    setSize(120, 100);
    setupControls();
}

void TrackHeaderComponent::setupControls()
{
    // Name label
    nameLabel.setText(trackName, juce::dontSendNotification);
    nameLabel.setJustificationType(juce::Justification::centred);
    nameLabel.setFont(juce::Font(12.0f, juce::Font::bold));
    addAndMakeVisible(nameLabel);

    // Arm button (Record arm)
    armButton.setTooltip("Arm for recording");
    armButton.onClick = [this] {
        isArmed = !isArmed;
        updateButtonColors();
        EngineBridge::getInstance().armTrack(trackIdx, isArmed);
    };
    addAndMakeVisible(armButton);

    // Mute button
    muteButton.setTooltip("Mute track");
    muteButton.onClick = [this] {
        isMuted = !isMuted;
        updateButtonColors();
        EngineBridge::getInstance().setTrackMute(trackIdx, isMuted);
    };
    addAndMakeVisible(muteButton);

    // Solo button
    soloButton.setTooltip("Solo track");
    soloButton.onClick = [this] {
        isSoloed = !isSoloed;
        updateButtonColors();
        EngineBridge::getInstance().setTrackSolo(trackIdx, isSoloed);
    };
    addAndMakeVisible(soloButton);

    // Volume slider (dB range)
    volumeSlider.setRange(-60.0, 12.0, 0.1);
    volumeSlider.setValue(0.0, juce::dontSendNotification); // 0 dB default
    volumeSlider.setTooltip("Volume (dB)");
    volumeSlider.onValueChange = [this] {
        EngineBridge::getInstance().setTrackVolume(trackIdx, static_cast<float>(volumeSlider.getValue()));
    };
    addAndMakeVisible(volumeSlider);

    // Pan slider (-1 to 1)
    panSlider.setRange(-1.0, 1.0, 0.01);
    panSlider.setValue(0.0, juce::dontSendNotification); // Center default
    panSlider.setTooltip("Pan (L/R)");
    panSlider.onValueChange = [this] {
        EngineBridge::getInstance().setTrackPan(trackIdx, static_cast<float>(panSlider.getValue()));
    };
    addAndMakeVisible(panSlider);

    updateButtonColors();
}

void TrackHeaderComponent::paint(juce::Graphics& g)
{
    // Background
    g.fillAll(juce::Colour(0xFF3B3B3B));

    // Track color indicator bar on left
    g.setColour(trackColor);
    g.fillRect(0, 0, 4, getHeight());

    // Bottom border
    g.setColour(juce::Colour(0xFF4B4B4B));
    g.drawHorizontalLine(getHeight() - 1, 0, getWidth());
}

void TrackHeaderComponent::resized()
{
    auto bounds = getLocalBounds().reduced(2);
    bounds.removeFromLeft(6); // Space for color bar

    // Layout: Name at top, then buttons, then sliders
    nameLabel.setBounds(bounds.removeFromTop(20));

    // Button row
    auto buttonRow = bounds.removeFromTop(24);
    armButton.setBounds(buttonRow.removeFromLeft(30).reduced(2));
    muteButton.setBounds(buttonRow.removeFromLeft(30).reduced(2));
    soloButton.setBounds(buttonRow.removeFromLeft(30).reduced(2));

    // Pan slider
    panSlider.setBounds(bounds.removeFromTop(20).reduced(2));

    // Volume slider fills remaining space
    volumeSlider.setBounds(bounds.reduced(4, 2));
}

void TrackHeaderComponent::setTrackName(const juce::String& name)
{
    trackName = name;
    nameLabel.setText(trackName, juce::dontSendNotification);
}

void TrackHeaderComponent::setTrackColor(juce::Colour color)
{
    trackColor = color;
    repaint();
}

void TrackHeaderComponent::setArmed(bool armed)
{
    isArmed = armed;
    updateButtonColors();
}

void TrackHeaderComponent::setMuted(bool muted)
{
    isMuted = muted;
    updateButtonColors();
}

void TrackHeaderComponent::setSoloed(bool soloed)
{
    isSoloed = soloed;
    updateButtonColors();
}

void TrackHeaderComponent::updateButtonColors()
{
    // Arm button - red when armed
    armButton.setColour(juce::TextButton::buttonColourId,
                        isArmed ? juce::Colours::red : juce::Colour(0xFF5B5B5B));

    // Mute button - yellow when muted
    muteButton.setColour(juce::TextButton::buttonColourId,
                         isMuted ? juce::Colours::yellow : juce::Colour(0xFF5B5B5B));

    // Solo button - blue when soloed
    soloButton.setColour(juce::TextButton::buttonColourId,
                         isSoloed ? juce::Colours::cyan : juce::Colour(0xFF5B5B5B));
}
