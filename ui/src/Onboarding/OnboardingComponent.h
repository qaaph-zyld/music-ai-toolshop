#pragma once

#include <JuceHeader.h>
#include "EngineBridge/EngineBridge.h"

/**
 * OnboardingComponent - First-launch experience
 * 
 * Shows welcome screen, demo project, interactive tutorial,
 * and audio engine test for new users.
 */
class OnboardingComponent : public juce::Component,
                            public juce::Button::Listener
{
public:
    OnboardingComponent();
    ~OnboardingComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Button::Listener
    void buttonClicked(juce::Button* button) override;

    // Check if this is first launch
    static bool isFirstLaunch();
    static void markFirstLaunchComplete();

    // Show specific onboarding screens
    void showWelcomeScreen();
    void showDemoProject();
    void showInteractiveTutorial();
    void showAudioTest();

    // Tutorial step management
    void nextTutorialStep();
    void previousTutorialStep();
    void skipTutorial();

    // Audio test
    void runAudioEngineTest();
    bool wasAudioTestSuccessful() const { return audioTestPassed; }

private:
    enum class Screen { Welcome, DemoProject, Tutorial, AudioTest, Complete };
    Screen currentScreen = Screen::Welcome;
    int tutorialStep = 0;
    static constexpr int totalTutorialSteps = 5;

    // UI Components
    std::unique_ptr<juce::Label> titleLabel;
    std::unique_ptr<juce::Label> descriptionLabel;
    std::unique_ptr<juce::TextButton> primaryButton;
    std::unique_ptr<juce::TextButton> secondaryButton;
    std::unique_ptr<juce::TextButton> skipButton;
    std::unique_ptr<juce::ProgressBar> progressBar;
    std::unique_ptr<juce::ComboBox> demoProjectSelector;

    // Audio test state
    bool audioTestPassed = false;
    bool audioTestRunning = false;

    // Demo projects
    juce::StringArray demoProjects = {
        "Electronic Beat Demo",
        "Jazz Quartet Demo",
        "Ambient Soundscape Demo",
        "Techno Loop Demo"
    };

    // Tutorial highlighting
    juce::Rectangle<int> highlightArea;
    std::function<void()> onTutorialHighlightChanged;

    void updateScreenLayout();
    void loadDemoProject(const juce::String& projectName);
    void showTutorialStep(int step);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(OnboardingComponent)
};
