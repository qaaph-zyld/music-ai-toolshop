#include "ArrangementTrack.h"

ArrangementTrack::ArrangementTrack()
{
    setSize(800, trackCount * trackHeight + 30);  // +30 for time ruler
    
    // Start timer for playhead updates
    startTimerHz(30);  // 30fps
}

ArrangementTrack::~ArrangementTrack()
{
    stopTimer();
}

void ArrangementTrack::paint(juce::Graphics& g)
{
    // Background
    g.fillAll(juce::Colour(0xFF1E1E1E));
    
    // Draw track backgrounds
    drawTrackBackgrounds(g);
    
    // Draw grid
    drawGrid(g);
    
    // Draw track headers
    drawTrackHeaders(g);
    
    // Draw time ruler at top
    g.setColour(juce::Colour(0xFF252525));
    g.fillRect(0, 0, getWidth(), 30);
    g.setColour(juce::Colour(0xFF4A4A4A));
    g.drawHorizontalLine(30, 0, static_cast<float>(getWidth()));
    
    // Draw bar/beat numbers on ruler
    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(10.0f));
    
    int startBar = static_cast<int>(visibleStartBeat / 4) + 1;
    int endBar = static_cast<int>(visibleEndBeat / 4) + 2;
    
    for (int bar = startBar; bar <= endBar; ++bar)
    {
        double beat = (bar - 1) * 4.0;
        float x = beatToX(beat);
        if (x >= headerWidth && x < getWidth())
        {
            juce::String barText = juce::String(bar);
            g.drawText(barText, static_cast<int>(x) + 2, 2, 30, 26, juce::Justification::left, false);
        }
    }
    
    // Draw playhead
    drawPlayhead(g);
    
    // Border
    g.setColour(juce::Colour(0xFF4A4A4A));
    g.drawRect(getLocalBounds(), 1);
}

void ArrangementTrack::resized()
{
    layoutClips();
}

void ArrangementTrack::timerCallback()
{
    // Playhead position updated externally via setPlayheadPosition
    repaint();
}

void ArrangementTrack::mouseDown(const juce::MouseEvent& event)
{
    if (event.mods.isPopupMenu())
    {
        // Right-click context menu
        auto clipId = hitTestClip(static_cast<float>(event.x), static_cast<float>(event.y));
        if (clipId != 0)
        {
            auto menu = createClipContextMenu(clipId);
            menu.showMenuAsync(juce::PopupMenu::Options().withTargetComponent(this));
        }
        else
        {
            double beat = xToBeat(static_cast<float>(event.x));
            int track = yToTrack(static_cast<float>(event.y));
            auto menu = createEmptyContextMenu(beat, track);
            menu.showMenuAsync(juce::PopupMenu::Options().withTargetComponent(this));
        }
        return;
    }
    
    // Left click - select clip or start drag
    auto clipId = hitTestClip(static_cast<float>(event.x), static_cast<float>(event.y));
    
    if (clipId != 0)
    {
        selectClip(clipId);
        
        auto* clipComponent = clips[clipId].get();
        if (clipComponent)
        {
            isDragging = clipComponent->isDragging();
            isResizing = clipComponent->isResizingLeft() || clipComponent->isResizingRight();
            
            if (isDragging || isResizing)
            {
                activeClipId = clipId;
                dragStartMouse = event.getPosition();
                dragStartBeat = clipComponent->getStartBeat();
                dragStartDuration = clipComponent->getDuration();
                dragStartTrack = static_cast<int>(clips[clipId]->getY() / trackHeight);
            }
        }
    }
    else
    {
        // Clicked on empty area
        deselectAll();
    }
}

void ArrangementTrack::mouseDrag(const juce::MouseEvent& event)
{
    if (activeClipId == 0)
        return;
        
    auto* clipComponent = clips[activeClipId].get();
    if (!clipComponent)
        return;
    
    int deltaX = event.x - dragStartMouse.x;
    double deltaBeats = deltaX / pixelsPerBeat;
    
    if (isDragging)
    {
        // Moving clip
        double newBeat = dragStartBeat + deltaBeats;
        newBeat = snapBeatToGrid(newBeat);
        
        // Calculate new track from Y position
        int newTrack = yToTrack(static_cast<float>(event.y));
        newTrack = juce::jlimit(0, trackCount - 1, newTrack);
        
        // Update visual position (actual move happens on mouseUp)
        float x = beatToX(newBeat);
        float y = trackToY(newTrack) + 2;  // +2 for padding
        clipComponent->setTopLeftPosition(static_cast<int>(x), static_cast<int>(y));
    }
    else if (isResizing)
    {
        // Resizing clip
        double newDuration = dragStartDuration + deltaBeats;
        newDuration = juce::jmax(0.25, newDuration);  // Minimum 1/16 note
        newDuration = snapBeatToGrid(newDuration);
        
        // Update visual size
        float newWidth = static_cast<float>(newDuration * pixelsPerBeat);
        clipComponent->setSize(static_cast<int>(newWidth), clipComponent->getHeight());
    }
}

void ArrangementTrack::mouseUp(const juce::MouseEvent& event)
{
    if (activeClipId == 0)
        return;
        
    auto* clipComponent = clips[activeClipId].get();
    if (!clipComponent)
    {
        isDragging = false;
        isResizing = false;
        activeClipId = 0;
        return;
    }
    
    if (isDragging)
    {
        // Calculate final position
        int deltaX = event.x - dragStartMouse.x;
        double deltaBeats = deltaX / pixelsPerBeat;
        double newBeat = dragStartBeat + deltaBeats;
        newBeat = snapBeatToGrid(newBeat);
        
        int newTrack = yToTrack(static_cast<float>(event.y));
        newTrack = juce::jlimit(0, trackCount - 1, newTrack);
        
        // Notify callback
        if (onClipMoved)
            onClipMoved(activeClipId, newTrack, newBeat);
    }
    else if (isResizing)
    {
        // Calculate final duration
        int deltaX = event.x - dragStartMouse.x;
        double deltaBeats = deltaX / pixelsPerBeat;
        double newDuration = dragStartDuration + deltaBeats;
        newDuration = juce::jmax(0.25, newDuration);
        newDuration = snapBeatToGrid(newDuration);
        
        // Notify callback
        if (onClipResized)
            onClipResized(activeClipId, newDuration);
    }
    
    isDragging = false;
    isResizing = false;
    activeClipId = 0;
    
    // Re-layout all clips
    layoutClips();
}

void ArrangementTrack::mouseDoubleClick(const juce::MouseEvent& event)
{
    // Check if clicked on a clip
    auto clipId = hitTestClip(static_cast<float>(event.x), static_cast<float>(event.y));
    
    if (clipId != 0)
    {
        // Open clip editor
        if (onClipDoubleClicked)
            onClipDoubleClicked(clipId);
    }
    else
    {
        // Add new clip at position
        double beat = xToBeat(static_cast<float>(event.x));
        beat = snapBeatToGrid(beat);
        int track = yToTrack(static_cast<float>(event.y));
        track = juce::jlimit(0, trackCount - 1, track);
        
        if (onEmptyAreaDoubleClicked)
            onEmptyAreaDoubleClicked(beat, track);
    }
}

void ArrangementTrack::setVisibleRange(double startBeat, double endBeat)
{
    visibleStartBeat = startBeat;
    visibleEndBeat = endBeat;
    layoutClips();
    repaint();
}

void ArrangementTrack::setPixelsPerBeat(double pixels)
{
    pixelsPerBeat = juce::jlimit(static_cast<double>(minPixelsPerBeat), static_cast<double>(maxPixelsPerBeat), pixels);
    layoutClips();
    repaint();
}

void ArrangementTrack::setTrackCount(int count)
{
    trackCount = juce::jmax(1, count);
    setSize(getWidth(), trackCount * trackHeight + 30);
    layoutClips();
    repaint();
}

void ArrangementTrack::setTrackHeight(int height)
{
    trackHeight = juce::jmax(30, height);
    setSize(getWidth(), trackCount * trackHeight + 30);
    layoutClips();
    repaint();
}

void ArrangementTrack::addClip(const ArrangementClipInfo& info)
{
    if (!info.isValid())
        return;
        
    auto clipComponent = std::make_unique<ArrangementClipComponent>(info.id, info.isAudio);
    clipComponent->setClipName(info.name);
    clipComponent->setPosition(info.startBeat, info.durationBeats);
    clipComponent->setSize(static_cast<int>(info.durationBeats * pixelsPerBeat), trackHeight - 4);
    
    // Set callbacks
    clipComponent->onClipSelected = [this](uint64_t id) { onClipComponentSelected(id); };
    clipComponent->onClipDoubleClicked = [this](uint64_t id) { onClipComponentDoubleClicked(id); };
    
    // Position the clip
    float x = beatToX(info.startBeat);
    float y = trackToY(static_cast<int>(info.trackIndex)) + 2;
    clipComponent->setTopLeftPosition(static_cast<int>(x), static_cast<int>(y));
    
    addAndMakeVisible(clipComponent.get());
    clips[info.id] = std::move(clipComponent);
}

void ArrangementTrack::removeClip(uint64_t clipId)
{
    auto it = clips.find(clipId);
    if (it != clips.end())
    {
        removeChildComponent(it->second.get());
        clips.erase(it);
        
        if (selectedClipId == clipId)
            selectedClipId = 0;
    }
}

void ArrangementTrack::updateClip(uint64_t clipId, const ArrangementClipInfo& info)
{
    auto it = clips.find(clipId);
    if (it != clips.end())
    {
        it->second->setClipName(info.name);
        it->second->setPosition(info.startBeat, info.durationBeats);
        layoutClips();
    }
}

void ArrangementTrack::clearAllClips()
{
    clips.clear();
    selectedClipId = 0;
    repaint();
}

uint64_t ArrangementTrack::getSelectedClipId() const
{
    return selectedClipId;
}

void ArrangementTrack::selectClip(uint64_t clipId)
{
    // Deselect previous
    if (selectedClipId != 0)
    {
        auto it = clips.find(selectedClipId);
        if (it != clips.end())
            it->second->setSelected(false);
    }
    
    // Select new
    selectedClipId = clipId;
    auto it = clips.find(clipId);
    if (it != clips.end())
        it->second->setSelected(true);
        
    if (onClipSelected)
        onClipSelected(clipId);
}

void ArrangementTrack::deselectAll()
{
    if (selectedClipId != 0)
    {
        auto it = clips.find(selectedClipId);
        if (it != clips.end())
            it->second->setSelected(false);
        selectedClipId = 0;
    }
}

void ArrangementTrack::setPlayheadPosition(double beat)
{
    playheadBeat = beat;
    repaint();
}

float ArrangementTrack::beatToX(double beat) const
{
    return static_cast<float>(headerWidth + (beat - visibleStartBeat) * pixelsPerBeat);
}

double ArrangementTrack::xToBeat(float x) const
{
    return visibleStartBeat + (x - headerWidth) / pixelsPerBeat;
}

int ArrangementTrack::yToTrack(float y) const
{
    if (y < 30)  // Time ruler area
        return -1;
    return static_cast<int>((y - 30) / trackHeight);
}

float ArrangementTrack::trackToY(int track) const
{
    return 30.0f + (track * trackHeight);
}

uint64_t ArrangementTrack::hitTestClip(float x, float y) const
{
    for (const auto& [id, clip] : clips)
    {
        auto bounds = clip->getBounds();
        if (bounds.contains(static_cast<int>(x), static_cast<int>(y)))
            return id;
    }
    return 0;
}

juce::PopupMenu ArrangementTrack::createClipContextMenu(uint64_t clipId)
{
    juce::PopupMenu menu;
    
    menu.addItem("Edit", [this, clipId]() {
        if (onClipDoubleClicked)
            onClipDoubleClicked(clipId);
    });
    
    menu.addItem("Duplicate", [this, clipId]() {
        // TODO: Implement duplicate
        (void)clipId;
    });
    
    menu.addSeparator();
    
    menu.addItem("Delete", [this, clipId]() {
        if (onClipRemoved)
            onClipRemoved(clipId);
    });
    
    return menu;
}

juce::PopupMenu ArrangementTrack::createEmptyContextMenu(double beat, int track)
{
    juce::PopupMenu menu;
    
    menu.addItem("Add MIDI Clip", [this, beat, track]() {
        if (onClipAdded)
            onClipAdded(track, beat, "New MIDI Clip", false);
    });
    
    menu.addItem("Add Audio Clip", [this, beat, track]() {
        if (onClipAdded)
            onClipAdded(track, beat, "New Audio Clip", true);
    });
    
    return menu;
}

double ArrangementTrack::snapBeatToGrid(double beat) const
{
    double gridBeats = 1.0;  // 1/4 note grid
    return std::round(beat / gridBeats) * gridBeats;
}

void ArrangementTrack::onClipComponentSelected(uint64_t clipId)
{
    selectClip(clipId);
}

void ArrangementTrack::onClipComponentDoubleClicked(uint64_t clipId)
{
    if (onClipDoubleClicked)
        onClipDoubleClicked(clipId);
}

void ArrangementTrack::drawGrid(juce::Graphics& g)
{
    g.setColour(juce::Colour(0xFF3A3A3A));
    
    // Draw vertical bar lines
    int startBar = static_cast<int>(visibleStartBeat / 4);
    int endBar = static_cast<int>(visibleEndBeat / 4) + 1;
    
    for (int bar = startBar; bar <= endBar; ++bar)
    {
        double beat = bar * 4.0;
        float x = beatToX(beat);
        if (x >= headerWidth && x < getWidth())
        {
            // Bar line - stronger
            g.drawVerticalLine(static_cast<int>(x), 30.0f, static_cast<float>(getHeight()));
        }
    }
    
    // Draw beat lines (subdivisions)
    g.setColour(juce::Colour(0xFF333333));
    int startBeat = static_cast<int>(visibleStartBeat);
    int endBeat = static_cast<int>(visibleEndBeat) + 1;
    
    for (int beat = startBeat; beat <= endBeat; ++beat)
    {
        if (beat % 4 == 0)  // Skip bar lines (already drawn)
            continue;
            
        float x = beatToX(static_cast<double>(beat));
        if (x >= headerWidth && x < getWidth())
        {
            g.drawVerticalLine(static_cast<int>(x), 30.0f, static_cast<float>(getHeight()));
        }
    }
}

void ArrangementTrack::drawPlayhead(juce::Graphics& g)
{
    float x = beatToX(playheadBeat);
    if (x < headerWidth || x > getWidth())
        return;
        
    // Playhead line
    g.setColour(juce::Colours::red);
    g.drawVerticalLine(static_cast<int>(x), 0.0f, static_cast<float>(getHeight()));
    
    // Playhead triangle at top
    juce::Path triangle;
    triangle.addTriangle(x, 0.0f, x - 6.0f, 10.0f, x + 6.0f, 10.0f);
    g.fillPath(triangle);
}

void ArrangementTrack::drawTrackHeaders(juce::Graphics& g)
{
    // Draw track name/number labels on the left
    g.setColour(juce::Colour(0xFF252525));
    g.fillRect(0, 30, headerWidth, getHeight() - 30);
    
    g.setColour(juce::Colour(0xFF4A4A4A));
    g.drawVerticalLine(headerWidth, 30, getHeight());
    
    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(10.0f));
    
    for (int track = 0; track < trackCount; ++track)
    {
        float y = trackToY(track);
        juce::String trackText = "Tr " + juce::String(track + 1);
        g.drawText(trackText, 2, static_cast<int>(y) + trackHeight / 2 - 5, 
                   headerWidth - 4, 20, juce::Justification::left, false);
    }
}

void ArrangementTrack::drawTrackBackgrounds(juce::Graphics& g)
{
    // Alternate track backgrounds for visual separation
    for (int track = 0; track < trackCount; ++track)
    {
        float y = trackToY(track);
        
        if (track % 2 == 0)
        {
            g.setColour(juce::Colour(0xFF222222));
        }
        else
        {
            g.setColour(juce::Colour(0xFF282828));
        }
        
        g.fillRect(headerWidth, static_cast<int>(y), getWidth() - headerWidth, trackHeight);
    }
}

void ArrangementTrack::layoutClips()
{
    for (auto& [id, clip] : clips)
    {
        // Calculate position based on stored beat/duration values
        // Note: actual values come from clipComponent->getStartBeat() etc.
        double startBeat = clip->getStartBeat();
        double duration = clip->getDuration();
        
        float x = beatToX(startBeat);
        float width = static_cast<float>(duration * pixelsPerBeat);
        
        // Find track index from current Y position
        int currentY = clip->getY();
        int trackIndex = (currentY - 30) / trackHeight;
        float y = trackToY(trackIndex) + 2;  // +2 for padding
        
        clip->setBounds(static_cast<int>(x), static_cast<int>(y), 
                       static_cast<int>(width), trackHeight - 4);
    }
}

// ============================================================================
// Drag and Drop Target (Session H)
// ============================================================================

bool ArrangementTrack::isInterestedInDragSource(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    // Check if drag source is a session clip
    auto dragData = dragSourceDetails.description.toString();
    return dragData.startsWith("session_clip:");
}

void ArrangementTrack::itemDragEnter(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    (void)dragSourceDetails;
    isDraggingOver = true;
    repaint();
}

void ArrangementTrack::itemDragMove(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    dragDropPosition = dragSourceDetails.localPosition;
    repaint();
}

void ArrangementTrack::itemDragExit(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    (void)dragSourceDetails;
    isDraggingOver = false;
    repaint();
}

void ArrangementTrack::itemDropped(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    isDraggingOver = false;
    
    // Parse session clip data
    auto dragData = dragSourceDetails.description.toString();
    if (!dragData.startsWith("session_clip:"))
        return;
    
    // Extract track and scene from drag data: "session_clip:track:scene"
    auto parts = juce::StringArray::fromTokens(dragData, ":", "");
    if (parts.size() < 3)
        return;
    
    int sourceTrack = parts[1].getIntValue();
    int sourceScene = parts[2].getIntValue();
    
    // Calculate drop position
    float x = static_cast<float>(dragSourceDetails.localPosition.x);
    float y = static_cast<float>(dragSourceDetails.localPosition.y);
    
    double targetBeat = xToBeat(x);
    int targetTrack = yToTrack(y);
    
    // Clamp track to valid range
    targetTrack = juce::jlimit(0, trackCount - 1, targetTrack);
    
    std::cout << "ArrangementTrack: Dropped session clip from track " << sourceTrack 
              << " scene " << sourceScene << " to track " << targetTrack 
              << " beat " << targetBeat << std::endl;
    
    // Call callback
    if (onSessionClipDropped)
    {
        onSessionClipDropped(sourceTrack, sourceScene, targetTrack, targetBeat);
    }
    
    repaint();
}
