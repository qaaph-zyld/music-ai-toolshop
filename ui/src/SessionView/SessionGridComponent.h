#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "ClipSlotComponent.h"
#include "TrackHeaderComponent.h"
#include "SceneLaunchComponent.h"

class SessionGridComponent : public juce::Component,
                             public juce::DragAndDropContainer,
                             public juce::Timer
{
public:
    SessionGridComponent(int numTracks, int numScenes);
    ~SessionGridComponent() override = default;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Scene launching
    void launchScene(int sceneIndex);
    void stopAllClips();

    // Clip management
    void setClip(int track, int scene, const juce::String& name, juce::Colour color);
    void clearClip(int track, int scene);
    void clearAllClips();
    void moveClip(int fromTrack, int fromScene, int toTrack, int toScene);

    // Track/Scene management
    void setTrackName(int trackIndex, const juce::String& name);
    void setSceneName(int sceneIndex, const juce::String& name);

    // Get playing clips
    std::vector<std::pair<int, int>> getPlayingClips() const;

    // Static callback for clip state changes (set by parent)
    static std::function<void(int track, int scene, bool isPlaying)> onClipStateChange;

    // Callback for track arm changes (set by parent) - Phase 7.1
    static std::function<void(int trackIndex, bool armed)> onTrackArmChanged;

private:
    int numTracks;
    int numScenes;

    // Grid components
    std::vector<std::unique_ptr<TrackHeaderComponent>> trackHeaders;
    std::vector<std::unique_ptr<SceneLaunchComponent>> sceneButtons;
    std::vector<std::unique_ptr<ClipSlotComponent>> clipSlots; // Flattened grid

    // Layout
    juce::Viewport viewport;
    juce::Component contentComponent;

    // Constants
    static constexpr int trackHeaderWidth = 120;
    static constexpr int sceneButtonHeight = 30;
    static constexpr int clipSlotWidth = 120;
    static constexpr int clipSlotHeight = 60;

    void setupGrid();
    ClipSlotComponent* getClipSlot(int track, int scene);
    void layoutGrid();

    // Phase 6.8: Timer callback for polling clip states
    void timerCallback() override;
    
    // Phase 6.8: Handle clip state changes from child components
    void handleClipStateChange(int track, int scene, ClipSlotComponent::State state);

    // Phase 7.1: Handle track arm changes from TrackHeaderComponent
    void handleTrackArmChange(int trackIndex, bool armed);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(SessionGridComponent)
};
