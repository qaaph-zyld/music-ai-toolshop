#include "DemoProjectLoader.h"
#include "../Engine/EngineBridge.h"
#include "../MainComponent.h"

namespace OpenDAW {

bool DemoProjectLoader::loadDemoProject(MainComponent* mainComponent)
{
    if (mainComponent == nullptr)
        return false;
    
    DBG("DemoProjectLoader::loadDemoProject - loading demo project");
    
    auto& engine = EngineBridge::getInstance();
    
    // Create new project first
    engine.newProject();
    
    // Set BPM to 128
    engine.setTempo(128.0);
    
    // Setup demo clips
    setupDemoClips(mainComponent);
    
    // Setup mixer levels
    setupDemoMixer();
    
    DBG("DemoProjectLoader::loadDemoProject - demo project loaded successfully");
    return true;
}

bool DemoProjectLoader::isDemoProjectAvailable()
{
    // Demo project is always available (we generate it dynamically)
    return true;
}

juce::File DemoProjectLoader::getDemoProjectPath()
{
    auto appDataDir = juce::File::getSpecialLocation(juce::File::userApplicationDataDirectory)
                         .getChildFile("OpenDAW")
                         .getChildFile("Demo");
    
    if (!appDataDir.exists())
        appDataDir.createDirectory();
    
    return appDataDir.getChildFile("demo_project.opendaw");
}

void DemoProjectLoader::setupDemoClips(MainComponent* mainComponent)
{
    auto& engine = EngineBridge::getInstance();
    
    // Track 0: Kick drum pattern (red)
    mainComponent->setClip(0, 0, "Kick Pattern", juce::Colours::red);
    engine.setClipActive(0, 0, true);
    
    // Track 1: Bass loop (blue)
    mainComponent->setClip(1, 0, "Bass Loop", juce::Colours::blue);
    engine.setClipActive(1, 0, true);
    
    // Track 2: Synth stab (green)
    mainComponent->setClip(2, 0, "Synth Stab", juce::Colours::green);
    engine.setClipActive(2, 0, true);
    
    // Track 3: Hi-hats (yellow)
    mainComponent->setClip(3, 0, "Hi-Hats", juce::Colours::yellow);
    engine.setClipActive(3, 0, true);
    
    DBG("DemoProjectLoader::setupDemoClips - 4 demo clips created");
}

void DemoProjectLoader::setupDemoMixer()
{
    auto& engine = EngineBridge::getInstance();
    
    // Set track fader levels
    // Track 0 (Kick): loud
    engine.setTrackFader(0, 0.9f);
    
    // Track 1 (Bass): medium-loud
    engine.setTrackFader(1, 0.75f);
    
    // Track 2 (Synth): medium
    engine.setTrackFader(2, 0.6f);
    
    // Track 3 (Hi-hats): quieter
    engine.setTrackFader(3, 0.5f);
    
    // Master fader at unity
    engine.setMasterFader(0.8f);
    
    DBG("DemoProjectLoader::setupDemoMixer - mixer levels set");
}

} // namespace OpenDAW
