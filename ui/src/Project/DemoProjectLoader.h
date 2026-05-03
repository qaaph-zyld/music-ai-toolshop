#pragma once

#include <juce_core/juce_core.h>

namespace OpenDAW {

// Forward declaration
class MainComponent;

/**
 * Loads a demo project with pre-configured clips, patterns,
 * and mixer settings for new users to explore.
 */
class DemoProjectLoader
{
public:
    /** Load demo project into MainComponent */
    static bool loadDemoProject(MainComponent* mainComponent);
    
    /** Check if demo project is available */
    static bool isDemoProjectAvailable();
    
    /** Get demo project path */
    static juce::File getDemoProjectPath();

private:
    static void createDemoProjectFiles();
    static void setupDemoClips(MainComponent* mainComponent);
    static void setupDemoMixer();
};

} // namespace OpenDAW
