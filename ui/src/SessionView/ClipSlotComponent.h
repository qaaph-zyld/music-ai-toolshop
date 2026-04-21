#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>

class ClipSlotComponent : public juce::Component,
                          public juce::SettableTooltipClient,
                          public juce::DragAndDropTarget,
                          public juce::DragAndDropContainer
{
public:
    ClipSlotComponent(int trackIndex, int sceneIndex);
    ~ClipSlotComponent() override = default;

    void paint(juce::Graphics& g) override;
    void resized() override;

    void mouseDown(const juce::MouseEvent& event) override;
    // Drag and drop support (Phase 7.0)
    bool isInterestedInDragSource(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDragEnter(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDragMove(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDragExit(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDropped(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    
    // Drag source support
    void mouseDrag(const juce::MouseEvent& event) override;
    
    // Clip data getters for drag operations
    const juce::String& getClipName() const { return clipName; }
    juce::Colour getClipColor() const { return clipColor; }
    void mouseUp(const juce::MouseEvent& event) override;

    // Clip management
    bool hasClip() const { return clipLoaded; }
    void setClip(const juce::String& name, juce::Colour color);
    void clearClip();
    void launchClip();
    void stopClip();

    // State
    enum class State { Empty, Loaded, Playing, Recording, Queued };
    void setState(State newState);
    State getState() const { return currentState; }

    // Getters for grid layout
    int getTrackIndex() const { return trackIdx; }
    int getSceneIndex() const { return sceneIdx; }

    // Update state from engine (call periodically from timer)
    void updateStateFromEngine();

    // State change callback (set by parent SessionGridComponent)
    static std::function<void(int track, int scene, State state)> onStateChange;
    
    // Clip moved callback for drag and drop (Phase 7.0)
    // Called when a clip is dropped on this slot from another slot
    // Parameters: fromTrack, fromScene, toTrack, toScene
    static std::function<void(int fromTrack, int fromScene, int toTrack, int toScene)> onClipMoved;

private:
    int trackIdx, sceneIdx;
    bool clipLoaded = false;
    juce::String clipName;
    juce::Colour clipColor{juce::Colours::grey};
    State currentState = State::Empty;
    
    // Drag and drop state (Phase 7.0)
    bool isDraggingOver = false;

    // Visual settings
    static constexpr int borderWidth = 2;
    static constexpr int cornerRadius = 4;

    void drawEmptySlot(juce::Graphics& g, const juce::Rectangle<int>& bounds);
    void drawLoadedClip(juce::Graphics& g, const juce::Rectangle<int>& bounds);
    void drawPlayingClip(juce::Graphics& g, const juce::Rectangle<int>& bounds);
    void drawRecordingClip(juce::Graphics& g, const juce::Rectangle<int>& bounds);
    void drawQueueIndicator(juce::Graphics& g, const juce::Rectangle<int>& bounds);
    void drawDragOverOverlay(juce::Graphics& g, const juce::Rectangle<int>& bounds);

    // Phase 8.x: Stem extraction for this clip
    void extractStemsForClip();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ClipSlotComponent)
};
