#include "DemoProjectLoader.h"
#include "../Engine/EngineBridge.h"
#include "../MainComponent.h"

namespace OpenDAW {

bool DemoProjectLoader::loadDemoProject(::MainComponent* mainComponent)
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

void DemoProjectLoader::setupDemoClips(::MainComponent* mainComponent)
{
    auto& engine = EngineBridge::getInstance();
    
    // Track 0: Kick drum pattern (red)
    mainComponent->setClip(0, 0, "Kick Pattern", juce::Colours::red);
    // engine.setClipActive(0, 0, true); // TODO: Implement setClipActive in EngineBridge
    
    // Track 1: Bass loop (blue)
    mainComponent->setClip(1, 0, "Bass Loop", juce::Colours::blue);
    // engine.setClipActive(1, 0, true); // TODO: Implement setClipActive in EngineBridge
    
    // Track 2: Synth stab (green)
    mainComponent->setClip(2, 0, "Synth Stab", juce::Colours::green);
    // engine.setClipActive(2, 0, true); // TODO: Implement setClipActive in EngineBridge
    
    // Track 3: Hi-hats (yellow)
    mainComponent->setClip(3, 0, "Hi-Hats", juce::Colours::yellow);
    // engine.setClipActive(3, 0, true); // TODO: Implement setClipActive in EngineBridge
    
    DBG("DemoProjectLoader::setupDemoClips - 4 demo clips created");
}

void DemoProjectLoader::setupDemoMixer()
{
    auto& engine = EngineBridge::getInstance();
    
    // Set track volume levels (using setTrackVolume instead of setTrackFader)
    // Track 0 (Kick): loud
    engine.setTrackVolume(0, -0.9f); // dB to linear conversion needed
    
    // Track 1 (Bass): medium-loud
    engine.setTrackVolume(1, -1.25f);
    
    // Track 2 (Synth): medium
    engine.setTrackVolume(2, -1.6f);
    
    // Track 3 (Hi-hats): quieter
    engine.setTrackVolume(3, -2.0f);
    
    // Master fader - set via mixer channel if needed
    // engine.setMasterFader(0.8f); // TODO: Implement master fader control
    
    DBG("DemoProjectLoader::setupDemoMixer - mixer levels set");
}

} // namespace OpenDAW
