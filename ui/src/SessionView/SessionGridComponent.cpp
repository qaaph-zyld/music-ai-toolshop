#include "SessionGridComponent.h"
#include "../Engine/EngineBridge.h"

// Static callback for clip state changes
std::function<void(int track, int scene, bool isPlaying)> SessionGridComponent::onClipStateChange;

// Static callback for track arm changes - Phase 7.1
std::function<void(int trackIndex, bool armed)> SessionGridComponent::onTrackArmChanged;

SessionGridComponent::SessionGridComponent(int numTracks_, int numScenes_)
    : numTracks(numTracks_), numScenes(numScenes_)
{
    addAndMakeVisible(viewport);
    viewport.setViewedComponent(&contentComponent, false);
    viewport.setScrollBarsShown(true, true);

    setupGrid();
    setSize(1000, 600);
    
    // Start timer for UI polling at 30Hz (33ms interval) - Phase 6.8
    startTimer(33);
}

void SessionGridComponent::setupGrid()
{
    // Set up clip move callback for drag and drop (Phase 7.0)
    ClipSlotComponent::onClipMoved = [this](int fromTrack, int fromScene, int toTrack, int toScene) {
        // Update the engine via EngineBridge
        EngineBridge::getInstance().moveClip(fromTrack, fromScene, toTrack, toScene);
    };

    // Create track headers
    for (int t = 0; t < numTracks; ++t)
    {
        auto header = std::make_unique<TrackHeaderComponent>(t);
        // Wire arm button to notify RecordingPanel via callback - Phase 7.1
        header->getArmButton().onClick = [this, t, &header]() mutable {
            bool isArmed = !header->getArmButton().getToggleState();
            header->getArmButton().setToggleState(isArmed, juce::dontSendNotification);
            header->setArmed(isArmed);
            EngineBridge::getInstance().armTrack(t, isArmed);
            handleTrackArmChange(t, isArmed);
        };
        trackHeaders.push_back(std::move(header));
        contentComponent.addAndMakeVisible(trackHeaders.back().get());
    }

    // Create scene launch buttons
    for (int s = 0; s < numScenes; ++s)
    {
        auto button = std::make_unique<SceneLaunchComponent>(s);
        sceneButtons.push_back(std::move(button));
        contentComponent.addAndMakeVisible(sceneButtons.back().get());
    }

    // Create clip slots (flattened: track * scenes)
    for (int t = 0; t < numTracks; ++t)
    {
        for (int s = 0; s < numScenes; ++s)
        {
            auto slot = std::make_unique<ClipSlotComponent>(t, s);
            clipSlots.push_back(std::move(slot));
            contentComponent.addAndMakeVisible(clipSlots.back().get());
        }
    }

    layoutGrid();
}

void SessionGridComponent::layoutGrid()
{
    // Calculate content size
    int contentWidth = trackHeaderWidth + (numTracks * clipSlotWidth) + 20;
    int contentHeight = sceneButtonHeight + (numScenes * clipSlotHeight) + 20;
    contentComponent.setSize(contentWidth, contentHeight);

    // Position track headers (top row, below scene buttons)
    for (int t = 0; t < numTracks; ++t)
    {
        int x = trackHeaderWidth + (t * clipSlotWidth);
        trackHeaders[t]->setBounds(x, 0, clipSlotWidth, sceneButtonHeight);
    }

    // Position scene buttons (left column)
    for (int s = 0; s < numScenes; ++s)
    {
        int y = sceneButtonHeight + (s * clipSlotHeight);
        sceneButtons[s]->setBounds(0, y, trackHeaderWidth, clipSlotHeight);
    }

    // Position clip slots in grid
    for (int t = 0; t < numTracks; ++t)
    {
        for (int s = 0; s < numScenes; ++s)
        {
            int x = trackHeaderWidth + (t * clipSlotWidth);
            int y = sceneButtonHeight + (s * clipSlotHeight);
            int index = t * numScenes + s;
            clipSlots[index]->setBounds(x, y, clipSlotWidth, clipSlotHeight);
        }
    }
}

void SessionGridComponent::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(0xFF2B2B2B));
}

void SessionGridComponent::resized()
{
    viewport.setBounds(getLocalBounds());
    layoutGrid();
}

void SessionGridComponent::launchScene(int sceneIndex)
{
    if (sceneIndex >= 0 && sceneIndex < numScenes)
    {
        // Launch all clips in this scene
        for (int t = 0; t < numTracks; ++t)
        {
            auto* slot = getClipSlot(t, sceneIndex);
            if (slot && slot->hasClip())
            {
                slot->launchClip();
            }
        }
    }
}

void SessionGridComponent::stopAllClips()
{
    for (auto& slot : clipSlots)
    {
        if (slot->getState() == ClipSlotComponent::State::Playing ||
            slot->getState() == ClipSlotComponent::State::Recording)
        {
            slot->stopClip();
        }
    }
}

void SessionGridComponent::setClip(int track, int scene, const juce::String& name, juce::Colour color)
{
    auto* slot = getClipSlot(track, scene);
    if (slot)
    {
        slot->setClip(name, color);
    }
}

void SessionGridComponent::clearClip(int track, int scene)
{
    auto* slot = getClipSlot(track, scene);
    if (slot)
    {
        slot->clearClip();
    }
}

void SessionGridComponent::clearAllClips()
{
    for (auto& slot : clipSlots)
    {
        if (slot->hasClip())
        {
            slot->clearClip();
        }
    }
}

void SessionGridComponent::moveClip(int fromTrack, int fromScene, int toTrack, int toScene)
{
    auto* fromSlot = getClipSlot(fromTrack, fromScene);
    auto* toSlot = getClipSlot(toTrack, toScene);

    if (fromSlot && toSlot && fromSlot->hasClip())
    {
        // Copy clip info from source to destination
        juce::String clipName = fromSlot->getClipName();
        juce::Colour clipColor = fromSlot->getClipColor();
        
        // Clear source and set destination
        fromSlot->clearClip();
        toSlot->setClip(clipName, clipColor);
        
        // Notify engine via EngineBridge (Phase 7.0)
        EngineBridge::getInstance().moveClip(fromTrack, fromScene, toTrack, toScene);
    }
}

void SessionGridComponent::setTrackName(int trackIndex, const juce::String& name)
{
    if (trackIndex >= 0 && trackIndex < numTracks)
    {
        trackHeaders[trackIndex]->setTrackName(name);
    }
}

void SessionGridComponent::setSceneName(int sceneIndex, const juce::String& name)
{
    if (sceneIndex >= 0 && sceneIndex < numScenes)
    {
        sceneButtons[sceneIndex]->setSceneName(name);
    }
}

std::vector<std::pair<int, int>> SessionGridComponent::getPlayingClips() const
{
    std::vector<std::pair<int, int>> playing;

    for (int t = 0; t < numTracks; ++t)
    {
        for (int s = 0; s < numScenes; ++s)
        {
            int index = t * numScenes + s;
            if (clipSlots[index]->getState() == ClipSlotComponent::State::Playing)
            {
                playing.emplace_back(t, s);
            }
        }
    }

    return playing;
}

ClipSlotComponent* SessionGridComponent::getClipSlot(int track, int scene)
{
    if (track >= 0 && track < numTracks && scene >= 0 && scene < numScenes)
    {
        int index = track * numScenes + scene;
        return clipSlots[index].get();
    }
    return nullptr;
}

// Phase 6.8: Timer callback for polling clip states from engine
void SessionGridComponent::timerCallback()
{
    // Poll all clip slots to update their state from the engine
    for (auto& slot : clipSlots)
    {
        if (slot != nullptr)
        {
            slot->updateStateFromEngine();
        }
    }
}

// Phase 6.8: Handle clip state changes from ClipSlotComponent::onStateChange
void SessionGridComponent::handleClipStateChange(int track, int scene, ClipSlotComponent::State state)
{
    // Forward to external callback if set
    if (onClipStateChange)
    {
        onClipStateChange(track, scene, state == ClipSlotComponent::State::Playing);
    }
}

// Phase 7.1: Handle track arm changes from TrackHeaderComponent
void SessionGridComponent::handleTrackArmChange(int trackIndex, bool armed)
{
    // Forward to external callback if set
    if (onTrackArmChanged)
    {
        onTrackArmChanged(trackIndex, armed);
    }
}
