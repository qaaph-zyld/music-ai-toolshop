#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

namespace OpenDAW {

/**
 * Represents a single step in the tutorial
 */
struct TutorialStep
{
    juce::String title;
    juce::String message;
    juce::Component* targetComponent = nullptr;
    juce::Rectangle<int> highlightBounds;
};

/**
 * Tutorial overlay that highlights UI components and shows
 * explanatory text for guided onboarding.
 */
class TutorialOverlay : public juce::Component
{
public:
    TutorialOverlay();
    ~TutorialOverlay() override = default;
    
    /** Start the tutorial with given steps */
    void startTutorial(const std::vector<TutorialStep>& steps);
    
    /** Advance to next step */
    void nextStep();
    
    /** Skip remaining tutorial */
    void skipTutorial();
    
    /** Check if tutorial is active */
    bool isActive() const { return !steps.empty() && currentStep < steps.size(); }
    
    // Callbacks
    std::function<void()> onTutorialComplete;
    std::function<void()> onTutorialSkipped;

    void paint(juce::Graphics& g) override;
    void resized() override;

private:
    std::vector<TutorialStep> steps;
    size_t currentStep = 0;
    
    juce::Label titleLabel;
    juce::Label messageLabel;
    juce::TextButton nextButton;
    juce::TextButton skipButton;
    
    void setupUI();
    void updateForCurrentStep();
    void completeTutorial();
};

} // namespace OpenDAW
