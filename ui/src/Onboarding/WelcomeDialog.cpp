#include "WelcomeDialog.h"

namespace OpenDAW {

WelcomeDialog::WelcomeDialog()
{
    setupUI();
}

void WelcomeDialog::setupUI()
{
    // Title
    titleLabel.setText("Welcome to OpenDAW", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(28.0f, juce::Font::bold));
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(titleLabel);
    
    // Subtitle
    subtitleLabel.setText("Let's get you started with music production", juce::dontSendNotification);
    subtitleLabel.setFont(juce::Font(16.0f));
    subtitleLabel.setJustificationType(juce::Justification::centred);
    subtitleLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    addAndMakeVisible(subtitleLabel);
    
    // New user button
    newUserButton.setButtonText("I'm New - Show Me Around");
    newUserButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF2196F3));
    newUserButton.setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    newUserButton.onClick = [this] { 
        if (onNewUserSelected)
            onNewUserSelected(); 
    };
    addAndMakeVisible(newUserButton);
    
    // Experienced button
    experiencedButton.setButtonText("I'm Experienced");
    experiencedButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4CAF50));
    experiencedButton.setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    experiencedButton.onClick = [this] { 
        if (onExperiencedUserSelected)
            onExperiencedUserSelected(); 
    };
    addAndMakeVisible(experiencedButton);
    
    // Skip button
    skipButton.setButtonText("Skip for now");
    skipButton.setColour(juce::TextButton::buttonColourId, juce::Colours::transparentBlack);
    skipButton.setColour(juce::TextButton::textColourOffId, juce::Colours::lightgrey);
    skipButton.onClick = [this] { 
        if (onSkip)
            onSkip(); 
    };
    addAndMakeVisible(skipButton);
}

void WelcomeDialog::paint(juce::Graphics& g)
{
    // Dark gradient background
    juce::ColourGradient gradient(
        juce::Colour(0xFF1A1A2E), 0.0f, 0.0f,
        juce::Colour(0xFF16213E), 0.0f, (float)getHeight(),
        false
    );
    g.setGradientFill(gradient);
    g.fillAll();
    
    // Draw decorative elements
    g.setColour(juce::Colour(0xFF2196F3).withAlpha(0.1f));
    g.fillEllipse(-50.0f, -50.0f, 200.0f, 200.0f);
    g.fillEllipse(getWidth() - 150.0f, getHeight() - 150.0f, 200.0f, 200.0f);
}

void WelcomeDialog::resized()
{
    auto bounds = getLocalBounds();
    auto centerX = bounds.getCentreX();
    
    // Title at top
    titleLabel.setBounds(centerX - 200, 60, 400, 40);
    
    // Subtitle below title
    subtitleLabel.setBounds(centerX - 200, 110, 400, 30);
    
    // Buttons centered vertically
    auto buttonWidth = 250;
    auto buttonHeight = 50;
    auto buttonY = 180;
    auto gap = 20;
    
    newUserButton.setBounds(centerX - buttonWidth/2, buttonY, buttonWidth, buttonHeight);
    experiencedButton.setBounds(centerX - buttonWidth/2, buttonY + buttonHeight + gap, buttonWidth, buttonHeight);
    
    // Skip button at bottom
    skipButton.setBounds(centerX - 60, bounds.getHeight() - 50, 120, 30);
}

} // namespace OpenDAW
