#include "TempoAutomationTrack.h"

TempoAutomationTrack::TempoAutomationTrack()
{
    setupContextMenu();
    setSize(800, trackHeight);
}

TempoAutomationTrack::~TempoAutomationTrack()
{
}

void TempoAutomationTrack::setupContextMenu()
{
    contextMenu.clear();
}

juce::PopupMenu TempoAutomationTrack::createBreakpointContextMenu(const TempoBreakpoint& bp)
{
    juce::PopupMenu menu;

    menu.addItem(1, "Edit BPM...", true, false);
    menu.addItem(2, "Delete", bp.beat > 0.0, false); // Can't delete beat 0

    menu.addSeparator();

    juce::PopupMenu interpMenu;
    interpMenu.addItem(10, "Step", true, bp.interpolation == 0);
    interpMenu.addItem(11, "Linear", true, bp.interpolation == 1);
    interpMenu.addItem(12, "Exponential", true, bp.interpolation == 2);
    interpMenu.addItem(13, "Smooth", true, bp.interpolation == 3);
    menu.addSubMenu("Interpolation", interpMenu);

    return menu;
}

void TempoAutomationTrack::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds();

    // Background
    g.fillAll(juce::Colour(0xFF2A2A2A));

    // Draw grid lines
    g.setColour(juce::Colour(0xFF3A3A3A));
    for (int b = 0; b <= static_cast<int>(visibleEndBeat); ++b)
    {
        float x = beatToX(static_cast<double>(b));
        if (x >= 0 && x <= bounds.getWidth())
        {
            g.drawVerticalLine(static_cast<int>(x), 0.0f, static_cast<float>(bounds.getHeight()));
        }
    }

    // Draw tempo curve
    drawTempoCurve(g);

    // Draw breakpoints
    for (size_t i = 0; i < breakpoints.size(); ++i)
    {
        drawBreakpoint(g, breakpoints[i], static_cast<int>(i) == selectedIndex);
    }

    // Draw border
    g.setColour(juce::Colour(0xFF4A4A4A));
    g.drawRect(bounds, 1);
}

void TempoAutomationTrack::drawTempoCurve(juce::Graphics& g)
{
    if (breakpoints.empty())
        return;

    juce::Path curve;
    bool first = true;

    // Sort breakpoints by beat position
    auto sorted = breakpoints;
    std::sort(sorted.begin(), sorted.end(), [](const TempoBreakpoint& a, const TempoBreakpoint& b) {
        return a.beat < b.beat;
    });

    // Draw curve segments between breakpoints
    for (size_t i = 0; i < sorted.size(); ++i)
    {
        double beat = sorted[i].beat;
        float x = beatToX(beat);
        float y = bpmToY(sorted[i].bpm);

        if (first)
        {
            curve.startNewSubPath(x, y);
            first = false;
        }
        else
        {
            curve.lineTo(x, y);
        }

        // Draw interpolation curve to next breakpoint
        if (i + 1 < sorted.size())
        {
            const auto& next = sorted[i + 1];
            double step = 0.25; // Draw curve in 1/4 beat increments

            for (double b = beat + step; b < next.beat; b += step)
            {
                double tempo = interpolateTempo(b, sorted[i], next);
                float px = beatToX(b);
                float py = bpmToY(tempo);
                curve.lineTo(px, py);
            }
        }
    }

    // Stroke the curve
    g.setColour(juce::Colour(0xFF4A90E2));
    g.strokePath(curve, juce::PathStrokeType(2.0f));
}

double TempoAutomationTrack::interpolateTempo(double beat, const TempoBreakpoint& from, const TempoBreakpoint& to) const
{
    if (beat <= from.beat) return from.bpm;
    if (beat >= to.beat) return to.bpm;

    double t = (beat - from.beat) / (to.beat - from.beat);

    switch (from.interpolation)
    {
        case 0: // Step
            return from.bpm;
        case 1: // Linear
            return from.bpm + (to.bpm - from.bpm) * t;
        case 2: // Exponential
            return from.bpm * std::pow(to.bpm / from.bpm, t);
        case 3: // Smooth (sigmoid)
            {
                double smoothT = t * t * (3.0 - 2.0 * t); // Smoothstep
                return from.bpm + (to.bpm - from.bpm) * smoothT;
            }
        default:
            return from.bpm + (to.bpm - from.bpm) * t;
    }
}

void TempoAutomationTrack::drawBreakpoint(juce::Graphics& g, const TempoBreakpoint& bp, bool selected)
{
    float x = beatToX(bp.beat);
    float y = bpmToY(bp.bpm);

    if (selected)
    {
        // Selection glow
        g.setColour(juce::Colour(0x804A90E2));
        g.fillEllipse(x - breakpointRadius - 2, y - breakpointRadius - 2,
                      (breakpointRadius + 2) * 2, (breakpointRadius + 2) * 2);
    }

    // Breakpoint circle
    juce::Colour fillColour = selected ? juce::Colour(0xFF6AB0F2) : juce::Colour(0xFF4A90E2);
    juce::Colour strokeColour = juce::Colours::white;

    g.setColour(fillColour);
    g.fillEllipse(x - breakpointRadius, y - breakpointRadius,
                  breakpointRadius * 2, breakpointRadius * 2);

    g.setColour(strokeColour);
    g.drawEllipse(x - breakpointRadius, y - breakpointRadius,
                  breakpointRadius * 2, breakpointRadius * 2, 1.5f);

    // BPM label
    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(10.0f));
    juce::String label = juce::String(static_cast<int>(bp.bpm)) + " BPM";
    g.drawText(label, static_cast<int>(x) + 10, static_cast<int>(y) - 6, 60, 12, juce::Justification::left);
}

void TempoAutomationTrack::resized()
{
    // Component maintains fixed height
    setSize(getWidth(), trackHeight);
}

void TempoAutomationTrack::mouseDown(const juce::MouseEvent& event)
{
    if (event.mods.isRightButtonDown())
    {
        int index = hitTestBreakpoint(static_cast<float>(event.x), static_cast<float>(event.y));
        if (index >= 0)
        {
            selectedIndex = index;
            contextMenuIndex = index;
            repaint();

            auto menu = createBreakpointContextMenu(breakpoints[static_cast<size_t>(index)]);
            menu.showMenuAsync(juce::PopupMenu::Options(),
                [this, index](int result)
                {
                    if (result == 1) // Edit BPM
                    {
                        openEditDialog(breakpoints[static_cast<size_t>(index)]);
                    }
                    else if (result == 2) // Delete
                    {
                        if (onBreakpointRemoved)
                            onBreakpointRemoved(breakpoints[static_cast<size_t>(index)].beat);
                    }
                    else if (result >= 10 && result <= 13) // Interpolation
                    {
                        auto& bp = breakpoints[static_cast<size_t>(index)];
                        if (onBreakpointModified)
                            onBreakpointModified(bp.beat, bp.beat, bp.bpm, result - 10);
                    }
                });
        }
    }
    else
    {
        int index = hitTestBreakpoint(static_cast<float>(event.x), static_cast<float>(event.y));
        selectedIndex = index;
        repaint();

        if (index >= 0)
        {
            isDragging = true;
            dragMoved = false;
            dragStartPos = event.position;
            dragStartBeat = breakpoints[static_cast<size_t>(index)].beat;
            dragStartBpm = breakpoints[static_cast<size_t>(index)].bpm;
        }
    }
}

void TempoAutomationTrack::mouseDoubleClick(const juce::MouseEvent& event)
{
    double beat = xToBeat(static_cast<float>(event.x));
    openAddDialog(beat);
}

void TempoAutomationTrack::mouseDrag(const juce::MouseEvent& event)
{
    if (!isDragging || selectedIndex < 0)
        return;

    float dx = event.position.x - dragStartPos.x;
    float dy = event.position.y - dragStartPos.y;

    if (std::abs(dx) > minDragPixels || std::abs(dy) > minDragPixels)
    {
        dragMoved = true;

        double newBeat = xToBeat(dragStartPos.x + dx);
        double newBpm = yToBpm(dragStartPos.y + dy);

        // Clamp values
        newBeat = std::max(0.0, newBeat);
        newBpm = std::max(minBpm, std::min(maxBpm, newBpm));

        // Update local state
        breakpoints[static_cast<size_t>(selectedIndex)].beat = newBeat;
        breakpoints[static_cast<size_t>(selectedIndex)].bpm = newBpm;

        repaint();
    }
}

void TempoAutomationTrack::mouseUp(const juce::MouseEvent& event)
{
    if (isDragging && dragMoved && selectedIndex >= 0)
    {
        // Notify callback of final position
        const auto& bp = breakpoints[static_cast<size_t>(selectedIndex)];
        if (onBreakpointModified)
            onBreakpointModified(dragStartBeat, bp.beat, bp.bpm, bp.interpolation);
    }

    isDragging = false;
    dragMoved = false;
}

float TempoAutomationTrack::beatToX(double beat) const
{
    double range = visibleEndBeat - visibleStartBeat;
    if (range <= 0) return 0.0f;

    double t = (beat - visibleStartBeat) / range;
    return static_cast<float>(t * getWidth());
}

double TempoAutomationTrack::xToBeat(float x) const
{
    double range = visibleEndBeat - visibleStartBeat;
    if (getWidth() <= 0) return visibleStartBeat;

    double t = x / getWidth();
    return visibleStartBeat + t * range;
}

float TempoAutomationTrack::bpmToY(double bpm) const
{
    double range = maxBpm - minBpm;
    if (range <= 0) return static_cast<float>(getHeight()) / 2.0f;

    // Invert: higher BPM = lower Y (top of component)
    double t = (bpm - minBpm) / range;
    return static_cast<float>((1.0 - t) * getHeight());
}

double TempoAutomationTrack::yToBpm(float y) const
{
    double range = maxBpm - minBpm;
    if (getHeight() <= 0) return (minBpm + maxBpm) / 2.0;

    // Invert: lower Y = higher BPM
    double t = (getHeight() - y) / getHeight();
    return minBpm + t * range;
}

int TempoAutomationTrack::hitTestBreakpoint(float x, float y) const
{
    for (size_t i = 0; i < breakpoints.size(); ++i)
    {
        float bx = beatToX(breakpoints[i].beat);
        float by = bpmToY(breakpoints[i].bpm);

        float dx = x - bx;
        float dy = y - by;
        float dist = std::sqrt(dx * dx + dy * dy);

        if (dist <= breakpointRadius + 3) // Slightly larger hit area
        {
            return static_cast<int>(i);
        }
    }
    return -1;
}

void TempoAutomationTrack::setVisibleRange(double startBeat, double endBeat)
{
    visibleStartBeat = startBeat;
    visibleEndBeat = endBeat;
    repaint();
}

void TempoAutomationTrack::setBreakpoints(const std::vector<TempoBreakpoint>& newBreakpoints)
{
    breakpoints = newBreakpoints;
    repaint();
}

TempoBreakpoint TempoAutomationTrack::getSelectedBreakpoint() const
{
    if (selectedIndex >= 0 && selectedIndex < static_cast<int>(breakpoints.size()))
        return breakpoints[static_cast<size_t>(selectedIndex)];
    return TempoBreakpoint{};
}

void TempoAutomationTrack::addBreakpoint(double beat, double bpm, int interpolation)
{
    if (onBreakpointAdded)
        onBreakpointAdded(beat, bpm, interpolation);
}

void TempoAutomationTrack::openEditDialog(const TempoBreakpoint& bp)
{
    // Simple dialog using JUCE alerts
    auto* alert = new juce::AlertWindow("Edit Tempo",
        "Enter new BPM value:",
        juce::AlertWindow::NoIcon);

    alert->addTextEditor("bpm", juce::String(static_cast<int>(bp.bpm)), "BPM:");
    alert->addButton("OK", 1, juce::KeyPress(juce::KeyPress::returnKey));
    alert->addButton("Cancel", 0, juce::KeyPress(juce::KeyPress::escapeKey));

    alert->enterModalState(true, juce::ModalCallbackFunction::create(
        [this, alert, bp](int result)
        {
            if (result == 1)
            {
                auto bpmText = alert->getTextEditorContents("bpm");
                double newBpm = bpmText.getDoubleValue();

                if (newBpm >= minBpm && newBpm <= maxBpm)
                {
                    if (onBreakpointModified)
                        onBreakpointModified(bp.beat, bp.beat, newBpm, bp.interpolation);
                }
            }
            delete alert;
        }));
}

void TempoAutomationTrack::openAddDialog(double beat)
{
    // Default to current tempo at that position or 120
    double defaultBpm = 120.0;

    // Find nearest breakpoint for default value
    for (const auto& bp : breakpoints)
    {
        if (std::abs(bp.beat - beat) < 0.5)
        {
            defaultBpm = bp.bpm;
            break;
        }
    }

    auto* alert = new juce::AlertWindow("Add Tempo Breakpoint",
        "Enter BPM for beat " + juce::String(beat, 2),
        juce::AlertWindow::NoIcon);

    alert->addTextEditor("bpm", juce::String(static_cast<int>(defaultBpm)), "BPM:");
    alert->addButton("OK", 1, juce::KeyPress(juce::KeyPress::returnKey));
    alert->addButton("Cancel", 0, juce::KeyPress(juce::KeyPress::escapeKey));

    alert->enterModalState(true, juce::ModalCallbackFunction::create(
        [this, alert, beat](int result)
        {
            if (result == 1)
            {
                auto bpmText = alert->getTextEditorContents("bpm");
                double bpm = bpmText.getDoubleValue();

                if (bpm >= minBpm && bpm <= maxBpm)
                {
                    addBreakpoint(beat, bpm, 1); // Default to linear interpolation
                }
            }
            delete alert;
        }));
}
