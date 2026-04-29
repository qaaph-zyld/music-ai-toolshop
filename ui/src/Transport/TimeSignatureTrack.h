#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <vector>
#include <functional>

/**
 * TimeSignatureChange - Visual representation of a time signature change
 */
struct TimeSignatureChange
{
    uint32_t bar = 1;
    uint8_t numerator = 4;
    uint8_t denominator = 4;

    juce::String toString() const
    {
        return juce::String(numerator) + "/" + juce::String(denominator);
    }

    bool isValid() const
    {
        return numerator >= 1 && numerator <= 32 &&
               denominator >= 1 && denominator <= 32 &&
               bar >= 1;
    }
};

/**
 * TimeSignatureTrack - UI component for displaying and editing time signatures
 *
 * Provides:
 * - Visual strip showing time signature changes at bar positions
 * - Click to select/edit time signature
 * - Double-click to add new time signature change
 * - Context menu for delete/rename operations
 * - Integration with Transport for bar/beat display
 */
class TimeSignatureTrack : public juce::Component
{
public:
    TimeSignatureTrack();
    ~TimeSignatureTrack() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Mouse interaction
    void mouseDown(const juce::MouseEvent& event) override;
    void mouseDoubleClick(const juce::MouseEvent& event) override;

    // Set visible bar range (1-indexed)
    void setVisibleRange(uint32_t startBar, uint32_t endBar);

    // Update time signature changes from engine
    void setTimeSignatureChanges(const std::vector<TimeSignatureChange>& changes);

    // Get current changes
    const std::vector<TimeSignatureChange>& getChanges() const { return changes; }

    // Add a new time signature change
    void addTimeSignatureChange(uint32_t bar, uint8_t numerator, uint8_t denominator);

    // Callbacks (connect to EngineBridge)
    std::function<void(uint32_t bar, uint8_t numerator, uint8_t denominator)> onChangeAdded;
    std::function<void(uint32_t bar)> onChangeRemoved;
    std::function<void(uint32_t bar, uint8_t numerator, uint8_t denominator)> onChangeModified;

private:
    void setupContextMenu();
    juce::PopupMenu createChangeContextMenu(const TimeSignatureChange& change);
    void openEditDialog(const TimeSignatureChange& change);
    void openAddDialog(uint32_t bar);

    // Coordinate conversions
    float barToX(uint32_t bar) const;
    uint32_t xToBar(float x) const;

    // Hit testing
    int hitTestChange(float x, float y) const;

    // Visual constants
    static constexpr int trackHeight = 24;
    static constexpr int barWidthMin = 40;   // Minimum pixels per bar
    static constexpr int signatureWidth = 30; // Width of signature display

    // State
    std::vector<TimeSignatureChange> changes;
    uint32_t visibleStartBar = 1;
    uint32_t visibleEndBar = 33;
    int selectedIndex = -1;

    // Context menu
    juce::PopupMenu contextMenu;
    int contextMenuIndex = -1;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(TimeSignatureTrack)
};
