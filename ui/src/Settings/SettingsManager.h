#pragma once

#include <juce_core/juce_core.h>

namespace OpenDAW {

/**
 * Manages application settings for first-launch detection
 * and user preferences. Settings are stored in a JSON file
 * in the user's config directory.
 */
class SettingsManager
{
public:
    /** Check if this is the first launch (no settings file exists) */
    static bool isFirstLaunch();
    
    /** Mark onboarding as completed */
    static void markOnboardingComplete();
    
    /** Check if onboarding should be shown on startup */
    static bool shouldShowOnboarding();
    
    /** Enable/disable showing onboarding on startup */
    static void setShowOnboardingOnStartup(bool show);
    
    /** Get the last opened project path */
    static juce::String getLastProjectPath();
    
    /** Set the last opened project path */
    static void setLastProjectPath(const juce::String& path);
    
    /** Load a specific setting value */
    static juce::var getSetting(const juce::String& key, const juce::var& defaultValue = {});
    
    /** Save a specific setting value */
    static void setSetting(const juce::String& key, const juce::var& value);

private:
    static juce::File getSettingsFile();
    static juce::var loadSettings();
    static void saveSettings(const juce::var& settings);
    static juce::var getSettingsObject();
};

} // namespace OpenDAW
