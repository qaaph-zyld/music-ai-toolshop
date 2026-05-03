#include "LoopMarkersComponent.h"
#include "../Engine/EngineBridge.h"

LoopMarkersComponent::LoopMarkersComponent()
{
    setSize(800, 60);
    startTimerHz(30);  // 30fps update for smooth playhead
}

LoopMarkersComponent::~LoopMarkersComponent()
{
    stopTimer();
}

void LoopMarkersComponent::paint(juce::Graphics& g)
{
    // Background
    g.fillAll(juce::Colour(0xFF1E1E1E));

    // Draw grid lines (every 4 beats = 1 bar)
    g.setColour(juce::Colour(0xFF3A3A3A));
    for (double beat = std::floor(visibleStartBeat / 4.0) * 4.0;
         beat <= visibleEndBeat;
         beat += 4.0)
    {
        float x = static_cast<float>(beatToX(beat));
        g.drawVerticalLine(static_cast<int>(x), 0.0f, static_cast<float>(getHeight()));
    }

    // Draw loop regions
    for (int i = 0; i < static_cast<int>(regions.size()); ++i)
    {
        const auto& region = regions[i];
        if (!region.enabled && region.id != contextMenuRegionId)
            continue;  // Skip disabled regions unless interacting

        float x1 = static_cast<float>(beatToX(region.startBeat));
        float x2 = static_cast<float>(beatToX(region.endBeat));
        float width = x2 - x1;

        if (width < 1.0f)
            continue;  // Too small to draw

        // Determine alpha based on state
        float alpha = region.enabled ? 0.3f : 0.15f;
        if (region.isActive && loopingEnabled)
            alpha = 0.5f;
        if (i == selectedRegionIndex)
            alpha += 0.1f;

        // Draw region background
        auto regionColor = region.color.withAlpha(alpha);
        g.setColour(regionColor);
        g.fillRect(x1, static_cast<float>(regionY), width, static_cast<float>(regionHeight));

        // Draw border (stronger for active region)
        float borderThickness = (region.isActive && loopingEnabled) ? 2.0f : 1.0f;
        auto borderColor = region.color.withAlpha(region.enabled ? 0.8f : 0.4f);
        g.setColour(borderColor);
        g.drawRect(x1, static_cast<float>(regionY), width, static_cast<float>(regionHeight), borderThickness);

        // Draw handles (only for selected or active region)
        if (i == selectedRegionIndex || region.isActive)
        {
            // Start handle (triangle pointing right)
            juce::Path startHandle;
            startHandle.addTriangle(
                x1, static_cast<float>(regionY),
                x1 + handleWidth, static_cast<float>(regionY + regionHeight / 2),
                x1, static_cast<float>(regionY + regionHeight)
            );
            g.fillPath(startHandle);

            // End handle (triangle pointing left)
            juce::Path endHandle;
            endHandle.addTriangle(
                x2, static_cast<float>(regionY),
                x2 - handleWidth, static_cast<float>(regionY + regionHeight / 2),
                x2, static_cast<float>(regionY + regionHeight)
            );
            g.fillPath(endHandle);
        }

        // Draw region name (if wide enough)
        if (width > 40.0f)
        {
            g.setColour(juce::Colours::white);
            g.setFont(juce::Font(12.0f));
            juce::String displayName = region.name.isEmpty() ? "Loop" : region.name;
            if (!region.enabled)
                displayName += " (off)";
            g.drawText(displayName,
                       static_cast<int>(x1 + 4),
                       regionY,
                       static_cast<int>(width - 8),
                       regionHeight,
                       juce::Justification::centredLeft,
                       true);
        }
    }

    // Draw playhead position
    float playheadX = static_cast<float>(beatToX(currentPlayheadBeat));
    g.setColour(juce::Colours::red.withAlpha(0.8f));
    g.drawVerticalLine(static_cast<int>(playheadX), 0.0f, static_cast<float>(getHeight()));

    // Draw loop enabled indicator
    if (loopingEnabled)
    {
        g.setColour(juce::Colour(0xFF4A90E2));
        g.setFont(juce::Font(10.0f));
        g.drawText("LOOP", 4, 2, 40, 14, juce::Justification::left, false);
    }

    // Draw border
    g.setColour(juce::Colour(0xFF4A4A4A));
    g.drawRect(getLocalBounds(), 1);
}

void LoopMarkersComponent::resized()
{
    // Component size doesn't affect internal layout significantly
    // Drawing is based on beat-to-pixel conversion
}

void LoopMarkersComponent::mouseDown(const juce::MouseEvent& event)
{
    if (event.mods.isPopupMenu())
    {
        // Right-click context menu
        int regionIndex = hitTestRegion(event.x, event.y);
        if (regionIndex >= 0)
        {
            selectedRegionIndex = regionIndex;
            contextMenuRegionId = regions[regionIndex].id;
            auto menu = createRegionContextMenu(regions[regionIndex]);
            menu.showMenuAsync(juce::PopupMenu::Options().withTargetComponent(this));
        }
        return;
    }

    int regionIndex = hitTestRegion(event.x, event.y);

    if (regionIndex >= 0)
    {
        selectedRegionIndex = regionIndex;
        const auto& region = regions[regionIndex];

        auto handleType = hitTestHandle(region, event.x, event.y);

        switch (handleType)
        {
            case HandleType::start:
                dragState = DragState::draggingStart;
                break;
            case HandleType::end:
                dragState = DragState::draggingEnd;
                break;
            case HandleType::body:
                dragState = DragState::draggingBody;
                break;
            default:
                dragState = DragState::none;
                break;
        }

        if (dragState != DragState::none)
        {
            draggedRegionIndex = regionIndex;
            dragStartX = event.x;
            dragOriginalStart = region.startBeat;
            dragOriginalEnd = region.endBeat;
            dragOriginalDuration = region.duration();
        }

        if (onRegionSelected)
            onRegionSelected(region.id);
    }
    else
    {
        selectedRegionIndex = -1;
    }

    repaint();
}

void LoopMarkersComponent::mouseDrag(const juce::MouseEvent& event)
{
    if (dragState == DragState::none || draggedRegionIndex < 0)
        return;

    double deltaX = event.x - dragStartX;
    double deltaBeats = (deltaX / getWidth()) * visibleDuration;
    double newStart = dragOriginalStart;
    double newEnd = dragOriginalEnd;

    switch (dragState)
    {
        case DragState::draggingStart:
            newStart = snapToGrid(dragOriginalStart + deltaBeats);
            newStart = juce::jmax(0.0, juce::jmin(newStart, newEnd - minRegionBeats));
            break;

        case DragState::draggingEnd:
            newEnd = snapToGrid(dragOriginalEnd + deltaBeats);
            newEnd = juce::jmax(newStart + minRegionBeats, newEnd);
            break;

        case DragState::draggingBody:
            newStart = snapToGrid(dragOriginalStart + deltaBeats);
            newEnd = newStart + dragOriginalDuration;
            if (newStart < 0.0)
            {
                newEnd -= newStart;  // Maintain duration
                newStart = 0.0;
            }
            break;

        default:
            break;
    }

    // Update the region in our local cache for visual feedback
    regions[draggedRegionIndex].startBeat = newStart;
    regions[draggedRegionIndex].endBeat = newEnd;

    repaint();
}

void LoopMarkersComponent::mouseUp(const juce::MouseEvent& event)
{
    if (dragState != DragState::none && draggedRegionIndex >= 0)
    {
        // Commit the change via callback
        const auto& region = regions[draggedRegionIndex];

        if (onRegionMoved)
            onRegionMoved(region.id, region.startBeat, region.endBeat);

        dragState = DragState::none;
        draggedRegionIndex = -1;
        repaint();
    }
}

void LoopMarkersComponent::mouseDoubleClick(const juce::MouseEvent& event)
{
    // Create new loop region at clicked position
    double clickBeat = snapToGrid(xToBeat(event.x));
    double defaultDuration = 4.0;  // 1 bar = 4 beats

    // Check if click is on existing region
    int hitRegion = hitTestRegion(event.x, event.y);
    if (hitRegion >= 0)
        return;  // Don't create if clicking existing region

    // Ensure region stays within visible range
    double startBeat = juce::jmax(0.0, clickBeat);
    double endBeat = startBeat + defaultDuration;

    if (onRegionCreated)
        onRegionCreated(startBeat, endBeat, "Loop " + juce::String(regions.size() + 1));
}

void LoopMarkersComponent::timerCallback()
{
    // Update playhead position from engine
    double newPlayhead = EngineBridge::getInstance().getCurrentBeat();
    if (std::abs(newPlayhead - currentPlayheadBeat) > 0.001)
    {
        currentPlayheadBeat = newPlayhead;
        repaint();
    }
}

void LoopMarkersComponent::setVisibleRange(double startBeat, double endBeat)
{
    visibleStartBeat = startBeat;
    visibleEndBeat = endBeat;
    visibleDuration = endBeat - startBeat;
    repaint();
}

void LoopMarkersComponent::setLoopRegions(const std::vector<LoopRegionView>& newRegions)
{
    regions = newRegions;

    // Maintain selection if region still exists
    if (selectedRegionIndex >= 0 && selectedRegionIndex < static_cast<int>(regions.size()))
    {
        juce::String selectedId = regions[selectedRegionIndex].id;
        bool found = false;
        for (int i = 0; i < static_cast<int>(regions.size()); ++i)
        {
            if (regions[i].id == selectedId)
            {
                selectedRegionIndex = i;
                found = true;
                break;
            }
        }
        if (!found)
            selectedRegionIndex = -1;
    }

    repaint();
}

void LoopMarkersComponent::setPlayheadPosition(double beat)
{
    currentPlayheadBeat = beat;
    repaint();
}

void LoopMarkersComponent::setLoopingEnabled(bool enabled)
{
    loopingEnabled = enabled;
    repaint();
}

void LoopMarkersComponent::addLoopRegion(double startBeat, double endBeat, const juce::String& name)
{
    if (onRegionCreated)
        onRegionCreated(startBeat, endBeat, name);
}

juce::PopupMenu LoopMarkersComponent::createRegionContextMenu(const LoopRegionView& region)
{
    juce::PopupMenu menu;

    menu.addItem("Set Active", true, region.isActive, [this, &region]() {
        if (onRegionSelected)
            onRegionSelected(region.id);
    });

    menu.addSeparator();

    menu.addItem(region.enabled ? "Disable" : "Enable", [this, &region]() {
        if (onRegionEnabledChanged)
            onRegionEnabledChanged(region.id, !region.enabled);
    });

    menu.addItem("Rename...", [this, &region]() {
        // JUCE async dialog for renaming loop region
        auto alert = std::make_unique<juce::AlertWindow>(
            "Rename Loop Region",
            "Enter new name for the loop region:",
            juce::AlertWindow::QuestionIcon, this);

        alert->addTextEditor("name", region.name, "Name:");
        alert->addButton("OK", 1, juce::KeyPress(juce::KeyPress::returnKey));
        alert->addButton("Cancel", 0, juce::KeyPress(juce::KeyPress::escapeKey));

        auto callback = [this, regionId = region.id, alert = alert.get()](int result) mutable {
            if (result == 1)
            {
                juce::String newName = alert->getTextEditorContents("name").trim();
                
                if (newName.isNotEmpty() && newName.length() <= 50)
                {
                    if (onRegionRenamed)
                        onRegionRenamed(regionId, newName);
                }
                else if (newName.isEmpty())
                {
                    juce::AlertWindow::showMessageBoxAsync(
                        juce::AlertWindow::WarningIcon,
                        "Invalid Name",
                        "Region name cannot be empty.",
                        "OK", this);
                }
            }
        };

        alert->enterModalState(true, juce::ModalCallbackFunction::create(callback));
        alert.release();
    });

    menu.addSeparator();

    menu.addItem("Delete", [this, &region]() {
        if (onRegionDeleted)
            onRegionDeleted(region.id);
    });

    return menu;
}

double LoopMarkersComponent::beatToX(double beat) const
{
    double normalized = (beat - visibleStartBeat) / visibleDuration;
    return normalized * getWidth();
}

double LoopMarkersComponent::xToBeat(double x) const
{
    double normalized = x / getWidth();
    return visibleStartBeat + normalized * visibleDuration;
}

int LoopMarkersComponent::hitTestRegion(double x, double y) const
{
    for (int i = 0; i < static_cast<int>(regions.size()); ++i)
    {
        if (hitTestHandle(regions[i], x, y) != HandleType::none)
            return i;
    }
    return -1;
}

LoopMarkersComponent::HandleType LoopMarkersComponent::hitTestHandle(
    const LoopRegionView& region, double x, double y) const
{
    double x1 = beatToX(region.startBeat);
    double x2 = beatToX(region.endBeat);

    // Check if y is within region vertical bounds
    if (y < regionY || y > regionY + regionHeight)
        return HandleType::none;

    // Check start handle
    if (x >= x1 - handleWidth && x <= x1 + handleWidth)
        return HandleType::start;

    // Check end handle
    if (x >= x2 - handleWidth && x <= x2 + handleWidth)
        return HandleType::end;

    // Check body
    if (x >= x1 && x <= x2)
        return HandleType::body;

    return HandleType::none;
}

double LoopMarkersComponent::snapToGrid(double beat) const
{
    // Snap to nearest 0.25 beat (16th note)
    constexpr double gridSize = 0.25;
    return std::round(beat / gridSize) * gridSize;
}
