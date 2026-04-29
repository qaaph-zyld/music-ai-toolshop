#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <vector>
#include <functional>

/**
 * LoopRegionView - Visual representation of a loop region for the UI
 */
struct LoopRegionView
{
    juce::String id;
    juce::String name;
    double startBeat = 0.0;
    double endBeat = 4.0;
    bool enabled = true;
    juce::Colour color = juce::Colour(0xFF4A90E2);
    bool isActive = false;

    double duration() const { return endBeat - startBeat; }
    bool containsBeat(double beat) const { return enabled && beat >= startBeat && beat < endBeat; }
};

/**
 * LoopMarkersComponent - Visual loop boundaries on timeline
 *
 * Provides:
 * - Visual display of loop regions as colored rectangles
 * - Draggable start/end handles for adjusting boundaries
 * - Drag entire region to move loop position
 * - Double-click to create new loop region
 * - Right-click context menu (delete, rename, set active, enable/disable)
 * - Visual feedback for active region and loop state
 */
class LoopMarkersComponent : public juce::Component,
                             public juce::Timer
{
public:
    LoopMarkersComponent();
    ~LoopMarkersComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Mouse interaction
    void mouseDown(const juce::MouseEvent& event) override;
    void mouseDrag(const juce::MouseEvent& event) override;
    void mouseUp(const juce::MouseEvent& event) override;
    void mouseDoubleClick(const juce::MouseEvent& event) override;

    // Timer callback for playback position updates
    void timerCallback() override;

    // Set visible time range (in beats)
    void setVisibleRange(double startBeat, double endBeat);

    // Update loop regions from engine
    void setLoopRegions(const std::vector<LoopRegionView>& regions);

    // Set current playhead position
    void setPlayheadPosition(double beat);

    // Set whether looping is globally enabled
    void setLoopingEnabled(bool enabled);

    // Add a new loop region
    void addLoopRegion(double startBeat, double endBeat, const juce::String& name = "Loop");

    // Get current visible regions (for testing)
    const std::vector<LoopRegionView>& getRegions() const { return regions; }

    // Check if currently dragging
    bool isDragging() const { return dragState != DragState::none; }

    // Callbacks (connect to EngineBridge)
    std::function<void(const juce::String& id, double newStart, double newEnd)> onRegionMoved;
    std::function<void(const juce::String& id)> onRegionSelected;
    std::function<void(double startBeat, double endBeat, const juce::String& name)> onRegionCreated;
    std::function<void(const juce::String& id)> onRegionDeleted;
    std::function<void(const juce::String& id, const juce::String& newName)> onRegionRenamed;
    std::function<void(const juce::String& id, bool enabled)> onRegionEnabledChanged;
    std::function<void(bool enabled)> onLoopingEnabledChanged;

private:
    void setupContextMenu();
    juce::PopupMenu createRegionContextMenu(const LoopRegionView& region);

    // Coordinate conversions
    double beatToX(double beat) const;
    double xToBeat(double x) const;

    // Hit testing
    int hitTestRegion(double x, double y) const;
    enum class HandleType { none, start, end, body };
    HandleType hitTestHandle(const LoopRegionView& region, double x, double y) const;

    // Dragging
    enum class DragState { none, draggingStart, draggingEnd, draggingBody };
    DragState dragState = DragState::none;
    int draggedRegionIndex = -1;
    double dragStartX = 0.0;
    double dragStartBeat = 0.0;
    double dragOriginalStart = 0.0;
    double dragOriginalEnd = 0.0;
    double dragOriginalDuration = 0.0;

    // Beat snapping (for drag operations)
    double snapToGrid(double beat) const;

    // Visual constants
    static constexpr int handleWidth = 8;
    static constexpr int regionHeight = 40;
    static constexpr int regionY = 10;
    static constexpr int minRegionBeats = 1.0;  // Minimum 1 beat

    // State
    std::vector<LoopRegionView> regions;
    double visibleStartBeat = 0.0;
    double visibleEndBeat = 32.0;
    double visibleDuration = 32.0;
    double currentPlayheadBeat = 0.0;
    bool loopingEnabled = false;
    int selectedRegionIndex = -1;

    // Context menu
    juce::PopupMenu contextMenu;
    juce::String contextMenuRegionId;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(LoopMarkersComponent)
};
