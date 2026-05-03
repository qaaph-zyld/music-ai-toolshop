#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <memory>
#include <vector>
#include <map>
#include <functional>
#include "ArrangementClipComponent.h"

/**
 * ArrangementClipInfo - Information about a clip in the arrangement
 */
struct ArrangementClipInfo
{
    uint64_t id = 0;
    uint32_t trackIndex = 0;
    double startBeat = 0.0;
    double durationBeats = 4.0;
    juce::String name;
    bool isAudio = false;
    
    bool isValid() const { return id != 0; }
    double endBeat() const { return startBeat + durationBeats; }
};

/**
 * ArrangementTrack - Timeline component for arrangement view
 *
 * Provides:
 * - Visual timeline with bar/beat grid
 * - Clip rendering at beat positions
 * - Click to select clips
 * - Drag to move clips
 * - Drag edges to resize clips
 * - Double-click to add new clips
 * - Context menu for clip operations
 * - Playhead position indicator
 */
class ArrangementTrack : public juce::Component,
                        public juce::Timer,
                        public juce::DragAndDropTarget
{
public:
    ArrangementTrack();
    ~ArrangementTrack() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;

    // Mouse interaction
    void mouseDown(const juce::MouseEvent& event) override;
    void mouseDrag(const juce::MouseEvent& event) override;
    void mouseUp(const juce::MouseEvent& event) override;
    void mouseDoubleClick(const juce::MouseEvent& event) override;

    // Drag and drop target (Session H)
    bool isInterestedInDragSource(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDragEnter(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDragMove(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDragExit(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDropped(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;

    // View settings
    void setVisibleRange(double startBeat, double endBeat);
    void setPixelsPerBeat(double pixels);
    double getPixelsPerBeat() const { return pixelsPerBeat; }
    
    // Track configuration
    void setTrackCount(int count);
    int getTrackCount() const { return trackCount; }
    void setTrackHeight(int height);
    int getTrackHeight() const { return trackHeight; }
    
    // Clip management
    void addClip(const ArrangementClipInfo& info);
    void removeClip(uint64_t clipId);
    void updateClip(uint64_t clipId, const ArrangementClipInfo& info);
    void clearAllClips();
    
    // Selection
    uint64_t getSelectedClipId() const;
    void selectClip(uint64_t clipId);
    void deselectAll();
    
    // Playhead
    void setPlayheadPosition(double beat);
    double getPlayheadPosition() const { return playheadBeat; }

    // Callbacks (connect to EngineBridge)
    std::function<void(int trackIndex, double startBeat, const juce::String& name, bool isAudio)> onClipAdded;
    std::function<void(uint64_t clipId)> onClipRemoved;
    std::function<void(uint64_t clipId, int newTrackIndex, double newStartBeat)> onClipMoved;
    std::function<void(uint64_t clipId, double newDuration)> onClipResized;
    std::function<void(uint64_t clipId)> onClipSelected;
    std::function<void(uint64_t clipId)> onClipDoubleClicked;
    std::function<void(double beat, int trackIndex)> onEmptyAreaDoubleClicked;
    
    // Session H: Session clip dropped callback
    // Called when a session grid clip is dropped on the arrangement
    // Parameters: sourceTrack, sourceScene, targetTrack, targetBeat
    std::function<void(int sourceTrack, int sourceScene, int targetTrack, double targetBeat)> onSessionClipDropped;

private:
    // Visual constants
    static constexpr int defaultTrackHeight = 60;
    static constexpr int headerWidth = 60;
    static constexpr int minPixelsPerBeat = 10;
    static constexpr int maxPixelsPerBeat = 200;
    static constexpr int snapGridBeats = 4;  // Snap to bar by default
    
    // Layout
    int trackCount = 8;
    int trackHeight = defaultTrackHeight;
    double pixelsPerBeat = 40.0;
    double visibleStartBeat = 0.0;
    double visibleEndBeat = 32.0;  // 8 bars default
    
    // Clips
    std::map<uint64_t, std::unique_ptr<ArrangementClipComponent>> clips;
    uint64_t selectedClipId = 0;
    
    // Playhead
    double playheadBeat = 0.0;
    
    // Drag/resize state
    bool isDragging = false;
    bool isResizing = false;
    uint64_t activeClipId = 0;
    juce::Point<int> dragStartMouse;
    double dragStartBeat = 0.0;
    double dragStartDuration = 4.0;
    int dragStartTrack = 0;
    
    // Session H: Drag-drop target state
    bool isDraggingOver = false;
    juce::Point<int> dragDropPosition;
    
    // Coordinate conversions
    float beatToX(double beat) const;
    double xToBeat(float x) const;
    int yToTrack(float y) const;
    float trackToY(int track) const;
    
    // Hit testing
    uint64_t hitTestClip(float x, float y) const;
    
    // Context menu
    juce::PopupMenu createClipContextMenu(uint64_t clipId);
    juce::PopupMenu createEmptyContextMenu(double beat, int track);
    
    // Snap to grid
    double snapBeatToGrid(double beat) const;
    
    // Clip callbacks
    void onClipComponentSelected(uint64_t clipId);
    void onClipComponentDoubleClicked(uint64_t clipId);
    
    // Grid drawing
    void drawGrid(juce::Graphics& g);
    void drawPlayhead(juce::Graphics& g);
    void drawTrackHeaders(juce::Graphics& g);
    void drawTrackBackgrounds(juce::Graphics& g);
    
    // Layout clips
    void layoutClips();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ArrangementTrack)
};
