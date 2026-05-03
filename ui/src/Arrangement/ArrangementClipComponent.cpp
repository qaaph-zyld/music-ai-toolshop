#include "ArrangementClipComponent.h"

ArrangementClipComponent::ArrangementClipComponent(uint64_t id, bool audio)
    : clipId(id), isAudio(audio)
{
    setSize(100, 40);
}

ArrangementClipComponent::~ArrangementClipComponent() = default;

void ArrangementClipComponent::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds();
    
    // Clip background
    juce::Colour baseColor = getClipColor();
    if (selected)
    {
        baseColor = getSelectedColor();
    }
    
    g.setColour(baseColor);
    g.fillRect(bounds);
    
    // Clip border
    g.setColour(selected ? juce::Colours::white : baseColor.darker(0.3f));
    g.drawRect(bounds, selected ? 2 : 1);
    
    // Resize handle indicators
    if (selected)
    {
        g.setColour(juce::Colours::white.withAlpha(0.5f));
        // Left handle
        g.fillRect(0, 0, resizeHandleWidth, bounds.getHeight());
        // Right handle
        g.fillRect(bounds.getWidth() - resizeHandleWidth, 0, resizeHandleWidth, bounds.getHeight());
    }
    
    // Clip name
    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(11.0f, juce::Font::bold));
    
    juce::String displayName = clipName.isEmpty() 
        ? (isAudio ? "Audio" : "MIDI") 
        : clipName;
    
    // Truncate if too long
    int textMargin = 4;
    int maxTextWidth = bounds.getWidth() - (textMargin * 2);
    if (maxTextWidth > 20)
    {
        g.drawText(displayName,
                   textMargin, 0,
                   maxTextWidth, bounds.getHeight(),
                   juce::Justification::centredLeft,
                   true);
    }
    
    // Audio/MIDI indicator icon
    int iconSize = 8;
    int iconX = bounds.getWidth() - iconSize - 4;
    int iconY = 4;
    
    g.setColour(juce::Colours::white.withAlpha(0.7f));
    if (isAudio)
    {
        // Draw waveform icon (simplified as zigzag)
        juce::Path wavePath;
        wavePath.startNewSubPath(static_cast<float>(iconX), static_cast<float>(iconY + iconSize / 2));
        wavePath.lineTo(static_cast<float>(iconX + 2), static_cast<float>(iconY));
        wavePath.lineTo(static_cast<float>(iconX + 4), static_cast<float>(iconY + iconSize));
        wavePath.lineTo(static_cast<float>(iconX + 6), static_cast<float>(iconY));
        wavePath.lineTo(static_cast<float>(iconX + iconSize), static_cast<float>(iconY + iconSize / 2));
        g.strokePath(wavePath, juce::PathStrokeType(1.0f));
    }
    else
    {
        // Draw MIDI note icon (simplified as small rectangles)
        g.fillRect(iconX, iconY, 3, 3);
        g.fillRect(iconX + 4, iconY + 2, 3, 3);
    }
}

void ArrangementClipComponent::resized()
{
    // Size is set by parent based on duration
}

void ArrangementClipComponent::mouseDown(const juce::MouseEvent& event)
{
    auto region = hitTestRegion(event.getPosition());
    
    if (event.mods.isPopupMenu())
    {
        // Right-click context menu handled by parent
        return;
    }
    
    dragStartPos = event.getPosition();
    dragStartBeat = startBeat;
    dragStartDuration = duration;
    
    switch (region)
    {
        case HitRegion::LeftEdge:
            resizingLeft = true;
            break;
        case HitRegion::RightEdge:
            resizingRight = true;
            break;
        case HitRegion::Body:
            dragging = true;
            setSelected(true);
            if (onClipSelected)
                onClipSelected(clipId);
            break;
        default:
            break;
    }
}

void ArrangementClipComponent::mouseDrag(const juce::MouseEvent& event)
{
    if (!dragging && !resizingLeft && !resizingRight)
        return;
        
    // Movement calculation is handled by parent (ArrangementTrack)
    // which has access to beat-to-pixel conversion
}

void ArrangementClipComponent::mouseUp(const juce::MouseEvent& event)
{
    if (dragging)
    {
        dragging = false;
    }
    if (resizingLeft || resizingRight)
    {
        resizingLeft = false;
        resizingRight = false;
    }
}

void ArrangementClipComponent::mouseDoubleClick(const juce::MouseEvent& event)
{
    if (onClipDoubleClicked)
        onClipDoubleClicked(clipId);
}

void ArrangementClipComponent::setClipName(const juce::String& name)
{
    clipName = name;
    repaint();
}

void ArrangementClipComponent::setSelected(bool sel)
{
    selected = sel;
    repaint();
}

void ArrangementClipComponent::setPosition(double start, double dur)
{
    startBeat = start;
    duration = dur;
    repaint();
}

ArrangementClipComponent::HitRegion ArrangementClipComponent::hitTestRegion(const juce::Point<int>& pos) const
{
    auto bounds = getLocalBounds();
    
    if (!bounds.contains(pos))
        return HitRegion::None;
        
    // Check left edge
    if (pos.x < resizeHandleWidth)
        return HitRegion::LeftEdge;
        
    // Check right edge
    if (pos.x > bounds.getWidth() - resizeHandleWidth)
        return HitRegion::RightEdge;
        
    return HitRegion::Body;
}

juce::Colour ArrangementClipComponent::getClipColor() const
{
    if (isAudio)
    {
        return juce::Colour(0xFF6B8E9F);  // Blue-ish for audio
    }
    else
    {
        return juce::Colour(0xFF8E9F6B);  // Green-ish for MIDI
    }
}

juce::Colour ArrangementClipComponent::getSelectedColor() const
{
    if (isAudio)
    {
        return juce::Colour(0xFF8AB4C7);  // Lighter blue for selected audio
    }
    else
    {
        return juce::Colour(0xFFB4C78A);  // Lighter green for selected MIDI
    }
}
