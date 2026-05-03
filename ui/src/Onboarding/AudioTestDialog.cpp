#include "AudioTestDialog.h"

namespace OpenDAW {

AudioTestDialog::AudioTestDialog()
{
    setupUI();
}

AudioTestDialog::~AudioTestDialog()
{
    stopTimer();
    if (isPlayingTone)
        stopTestTone();
}

void AudioTestDialog::setupUI()
{
    // Title
    titleLabel.setText("Let's Test Your Audio", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(24.0f, juce::Font::bold));
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(titleLabel);
    
    // Instructions
    instructionLabel.setText("Click the button below to play a test tone", juce::dontSendNotification);
    instructionLabel.setFont(juce::Font(14.0f));
    instructionLabel.setJustificationType(juce::Justification::centred);
    instructionLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    addAndMakeVisible(instructionLabel);
    
    // Play tone button
    playToneButton.setButtonText("Play Test Tone");
    playToneButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF2196F3));
    playToneButton.setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    playToneButton.onClick = [this] { 
        if (isPlayingTone)
            stopTestTone();
        else
            playTestTone();
    };
    addAndMakeVisible(playToneButton);
    
    // Yes button
    yesButton.setButtonText("I Can Hear It");
    yesButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4CAF50));
    yesButton.setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    yesButton.onClick = [this] { 
        stopTestTone();
        if (onAudioWorking)
            onAudioWorking(); 
    };
    addAndMakeVisible(yesButton);
    
    // No button
    noButton.setButtonText("No Audio");
    noButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFFF44336));
    noButton.setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    noButton.onClick = [this] { 
        stopTestTone();
        if (onAudioNotWorking)
            onAudioNotWorking(); 
    };
    addAndMakeVisible(noButton);
    
    // Settings button
    settingsButton.setButtonText("Open Audio Settings");
    settingsButton.setColour(juce::TextButton::buttonColourId, juce::Colours::transparentBlack);
    settingsButton.setColour(juce::TextButton::textColourOffId, juce::Colours::lightgrey);
    settingsButton.onClick = [this] { 
        stopTestTone();
        if (onOpenSettings)
            onOpenSettings(); 
    };
    addAndMakeVisible(settingsButton);
}

void AudioTestDialog::paint(juce::Graphics& g)
{
    // Dark gradient background
    juce::ColourGradient gradient(
        juce::Colour(0xFF1A1A2E), 0.0f, 0.0f,
        juce::Colour(0xFF16213E), 0.0f, (float)getHeight(),
        false
    );
    g.setGradientFill(gradient);
    g.fillAll();
}

void AudioTestDialog::resized()
{
    auto bounds = getLocalBounds();
    auto centerX = bounds.getCentreX();
    
    // Title
    titleLabel.setBounds(centerX - 200, 50, 400, 40);
    
    // Instructions
    instructionLabel.setBounds(centerX - 200, 100, 400, 30);
    
    // Play tone button
    playToneButton.setBounds(centerX - 100, 150, 200, 50);
    
    // Yes/No buttons
    auto buttonY = 230;
    auto buttonWidth = 120;
    auto gap = 20;
    
    yesButton.setBounds(centerX - buttonWidth - gap/2, buttonY, buttonWidth, 45);
    noButton.setBounds(centerX + gap/2, buttonY, buttonWidth, 45);
    
    // Settings button at bottom
    settingsButton.setBounds(centerX - 100, bounds.getHeight() - 50, 200, 30);
}

void AudioTestDialog::playTestTone()
{
    // Play 1kHz test tone via EngineBridge
    auto& engine = EngineBridge::getInstance();
    engine.playTestTone(1000.0f, 0.5f); // 1kHz, 0.5 amplitude
    
    isPlayingTone = true;
    playToneButton.setButtonText("Stop Tone");
    
    // Auto-stop after 3 seconds
    startTimer(3000);
}

void AudioTestDialog::stopTestTone()
{
    if (!isPlayingTone)
        return;
    
    // Stop test tone via EngineBridge
    auto& engine = EngineBridge::getInstance();
    engine.stopTestTone();
    
    isPlayingTone = false;
    playToneButton.setButtonText("Play Test Tone");
    stopTimer();
}

void AudioTestDialog::timerCallback()
{
    stopTestTone();
}

} // namespace OpenDAW
