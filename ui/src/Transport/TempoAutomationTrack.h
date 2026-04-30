#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <vector>
#include <functional>

/**
 * TempoBreakpoint - Visual representation of a tempo breakpoint
 */
struct TempoBreakpoint
{
    double beat = 0.0;
    double bpm = 120.0;
    int interpolation = 1; // 0=step, 1=linear, 2=exponential, 3=smooth

    juce::String getInterpolationName() const
    {
        switch (interpolation)
        {
            case 0: return "Step";
            case 1: return "Linear";
            case 2: return "Exp";
            case 3: return "Smooth";
            default: return "Linear";
        }
    }

    bool isValid() const
    {
        return bpm >= 1.0 && bpm <= 999.0 && beat >= 0.0;
    }
};

/**
 * TempoAutomationTrack - UI component for displaying and editing tempo automation
 *
 * Provides:
 * - Visual tempo curve display with breakpoint markers
 * - Click to select breakpoint
 * - Double-click to add new breakpoint
 * - Drag horizontally to change beat position
 * - Drag vertically to change BPM value
 * - Context menu for interpolation type and deletion
 * - Integration with Transport for tempo display
 */
class TempoAutomationTrack : public juce::Component
{
public:
    TempoAutomationTrack();
    ~TempoAutomationTrack() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Mouse interaction
    void mouseDown(const juce::MouseEvent& event) override;
    void mouseDoubleClick(const juce::MouseEvent& event) override;
    void mouseDrag(const juce::MouseEvent& event) override;
    void mouseUp(const juce::MouseEvent& event) override;

    // Set visible beat range
    void setVisibleRange(double startBeat, double endBeat);

    // Update breakpoints from engine
    void setBreakpoints(const std::vector<TempoBreakpoint>& breakpoints);

    // Get current breakpoints
    const std::vector<TempoBreakpoint>& getBreakpoints() const { return breakpoints; }

    // Get selected breakpoint
    int getSelectedBreakpointIndex() const { return selectedIndex; }
    TempoBreakpoint getSelectedBreakpoint() const;

    // Add a new breakpoint
    void addBreakpoint(double beat, double bpm, int interpolation);

    // Callbacks (connect to EngineBridge)
    std::function<void(double beat, double bpm, int interpolation)> onBreakpointAdded;
    std::function<void(double beat)> onBreakpointRemoved;
    std::function<void(double oldBeat, double newBeat, double newBpm, int interpolation)> onBreakpointModified;

private:
    void setupContextMenu();
    juce::PopupMenu createBreakpointContextMenu(const TempoBreakpoint& bp);
    void openEditDialog(const TempoBreakpoint& bp);
    void openAddDialog(double beat);

    // Coordinate conversions
    float beatToX(double beat) const;
    double xToBeat(float x) const;
    float bpmToY(double bpm) const;
    double yToBpm(float y) const;

    // Hit testing
    int hitTestBreakpoint(float x, float y) const;

    // Curve drawing
    void drawTempoCurve(juce::Graphics& g);
    void drawBreakpoint(juce::Graphics& g, const TempoBreakpoint& bp, bool selected);
    double interpolateTempo(double beat, const TempoBreakpoint& from, const TempoBreakpoint& to) const;

    // Visual constants
    static constexpr int trackHeight = 40;
    static constexpr int breakpointRadius = 6;
    static constexpr int minDragPixels = 5;
    static constexpr double minBpm = 40.0;
    static constexpr double maxBpm = 240.0;

    // State
    std::vector<TempoBreakpoint> breakpoints;
    double visibleStartBeat = 0.0;
    double visibleEndBeat = 32.0;
    int selectedIndex = -1;

    // Drag state
    bool isDragging = false;
    bool dragMoved = false;
    double dragStartBeat = 0.0;
    double dragStartBpm = 0.0;
    juce::Point<float> dragStartPos;

    // Context menu
    juce::PopupMenu contextMenu;
    int contextMenuIndex = -1;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(TempoAutomationTrack)
};
