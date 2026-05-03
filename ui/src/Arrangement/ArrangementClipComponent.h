#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <functional>

/**
 * ArrangementClipComponent - Visual representation of a clip on the arrangement timeline
 *
 * Provides:
 * - Visual clip rendering with different colors for MIDI vs audio
 * - Selection highlighting
 * - Drag to move
 * - Drag edges to resize
 * - Double-click to open editor
 */
class ArrangementClipComponent : public juce::Component
{
public:
    ArrangementClipComponent(uint64_t clipId, bool isAudio);
    ~ArrangementClipComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Mouse interaction
    void mouseDown(const juce::MouseEvent& event) override;
    void mouseDrag(const juce::MouseEvent& event) override;
    void mouseUp(const juce::MouseEvent& event) override;
    void mouseDoubleClick(const juce::MouseEvent& event) override;

    // Clip properties
    uint64_t getClipId() const { return clipId; }
    bool isAudioClip() const { return isAudio; }
    
    void setClipName(const juce::String& name);
    juce::String getClipName() const { return clipName; }
    
    void setSelected(bool selected);
    bool isSelected() const { return selected; }
    
    void setPosition(double startBeat, double duration);
    double getStartBeat() const { return startBeat; }
    double getDuration() const { return duration; }
    double getEndBeat() const { return startBeat + duration; }

    // Callbacks
    std::function<void(uint64_t clipId)> onClipSelected;
    std::function<void(uint64_t clipId, double newStartBeat)> onClipMoved;
    std::function<void(uint64_t clipId, double newDuration)> onClipResized;
    std::function<void(uint64_t clipId)> onClipDoubleClicked;

    // Drag state for parent
    bool isDragging() const { return dragging; }
    bool isResizingLeft() const { return resizingLeft; }
    bool isResizingRight() const { return resizingRight; }

private:
    uint64_t clipId;
    bool isAudio;
    juce::String clipName;
    
    double startBeat = 0.0;
    double duration = 4.0;  // Default 1 bar
    
    bool selected = false;
    
    // Drag/resize state
    bool dragging = false;
    bool resizingLeft = false;
    bool resizingRight = false;
    juce::Point<int> dragStartPos;
    double dragStartBeat = 0.0;
    double dragStartDuration = 4.0;
    
    // Visual constants
    static constexpr int resizeHandleWidth = 6;
    static constexpr int minClipWidth = 20;
    
    // Hit testing
    enum class HitRegion { None, Body, LeftEdge, RightEdge };
    HitRegion hitTestRegion(const juce::Point<int>& pos) const;
    
    // Colors
    juce::Colour getClipColor() const;
    juce::Colour getSelectedColor() const;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ArrangementClipComponent)
};
