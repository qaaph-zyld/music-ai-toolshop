#include "TutorialOverlay.h"

namespace OpenDAW {

TutorialOverlay::TutorialOverlay()
{
    setupUI();
    setVisible(false);
}

void TutorialOverlay::setupUI()
{
    // Title label
    titleLabel.setFont(juce::Font(20.0f, juce::Font::bold));
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(titleLabel);
    
    // Message label
    messageLabel.setFont(juce::Font(14.0f));
    messageLabel.setJustificationType(juce::Justification::centred);
    messageLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(messageLabel);
    
    // Next button
    nextButton.setButtonText("Next");
    nextButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF2196F3));
    nextButton.setColour(juce::TextButton::textColourOffId, juce::Colours::white);
    nextButton.onClick = [this] { nextStep(); };
    addAndMakeVisible(nextButton);
    
    // Skip button
    skipButton.setButtonText("Skip Tutorial");
    skipButton.setColour(juce::TextButton::buttonColourId, juce::Colours::transparentBlack);
    skipButton.setColour(juce::TextButton::textColourOffId, juce::Colours::lightgrey);
    skipButton.onClick = [this] { skipTutorial(); };
    addAndMakeVisible(skipButton);
}

void TutorialOverlay::paint(juce::Graphics& g)
{
    // Darken entire screen with semi-transparent black
    g.fillAll(juce::Colours::black.withAlpha(0.75f));
    
    if (currentStep < steps.size())
    {
        // Cut out hole for highlighted component
        auto bounds = steps[currentStep].highlightBounds;
        
        // Create a path that excludes the highlight area
        juce::Path highlightPath;
        highlightPath.addRectangle(bounds);
        
        // Fill everything except the highlight
        juce::Path screenPath;
        screenPath.addRectangle(getLocalBounds());
        
        // Draw border around highlighted area
        g.setColour(juce::Colour(0xFF2196F3));
        g.drawRect(bounds.expanded(4), 4);
        
        // Draw arrow pointing to highlight
        auto arrowY = bounds.getBottom() + 20;
        auto centerX = bounds.getCentreX();
        
        juce::Path arrow;
        arrow.addTriangle(
            centerX - 10.0f, (float)arrowY,
            centerX + 10.0f, (float)arrowY,
            centerX, (float)(arrowY + 15)
        );
        g.fillPath(arrow);
    }
    
    // Draw info box background at bottom
    auto infoBoxBounds = getLocalBounds().removeFromBottom(150);
    g.setColour(juce::Colours::black.withAlpha(0.9f));
    g.fillRect(infoBoxBounds);
    
    g.setColour(juce::Colour(0xFF2196F3));
    g.drawRect(infoBoxBounds, 2);
}

void TutorialOverlay::resized()
{
    auto bounds = getLocalBounds();
    auto infoBox = bounds.removeFromBottom(150);
    
    // Title at top of info box
    titleLabel.setBounds(infoBox.getX() + 20, infoBox.getY() + 15, infoBox.getWidth() - 40, 30);
    
    // Message below title
    messageLabel.setBounds(infoBox.getX() + 20, infoBox.getY() + 50, infoBox.getWidth() - 40, 50);
    
    // Buttons at bottom right
    auto buttonY = infoBox.getBottom() - 50;
    nextButton.setBounds(infoBox.getRight() - 120, buttonY, 100, 35);
    skipButton.setBounds(infoBox.getRight() - 240, buttonY, 110, 35);
}

void TutorialOverlay::startTutorial(const std::vector<TutorialStep>& tutorialSteps)
{
    steps = tutorialSteps;
    currentStep = 0;
    
    if (!steps.empty())
    {
        setVisible(true);
        toFront(true);
        updateForCurrentStep();
    }
}

void TutorialOverlay::nextStep()
{
    currentStep++;
    
    if (currentStep >= steps.size())
    {
        completeTutorial();
    }
    else
    {
        updateForCurrentStep();
        repaint();
    }
}

void TutorialOverlay::skipTutorial()
{
    setVisible(false);
    
    if (onTutorialSkipped)
        onTutorialSkipped();
}

void TutorialOverlay::updateForCurrentStep()
{
    if (currentStep < steps.size())
    {
        const auto& step = steps[currentStep];
        titleLabel.setText(step.title, juce::dontSendNotification);
        messageLabel.setText(step.message, juce::dontSendNotification);
        
        // Update button text for last step
        if (currentStep == steps.size() - 1)
        {
            nextButton.setButtonText("Finish");
        }
        else
        {
            nextButton.setButtonText("Next");
        }
    }
}

void TutorialOverlay::completeTutorial()
{
    setVisible(false);
    
    if (onTutorialComplete)
        onTutorialComplete();
}

} // namespace OpenDAW
