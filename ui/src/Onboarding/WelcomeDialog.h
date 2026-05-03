#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

namespace OpenDAW {

/**
 * Welcome dialog for new users.
 * Allows users to choose between guided onboarding or immediate use.
 */
class WelcomeDialog : public juce::Component
{
public:
    WelcomeDialog();
    ~WelcomeDialog() override = default;
    
    // Callbacks for button actions
    std::function<void()> onNewUserSelected;
    std::function<void()> onExperiencedUserSelected;
    std::function<void()> onSkip;
    
    void paint(juce::Graphics& g) override;
    void resized() override;

private:
    juce::Label titleLabel;
    juce::Label subtitleLabel;
    juce::TextButton newUserButton;
    juce::TextButton experiencedButton;
    juce::TextButton skipButton;
    
    void setupUI();
};

} // namespace OpenDAW
