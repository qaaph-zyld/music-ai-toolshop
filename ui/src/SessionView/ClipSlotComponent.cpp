#include "ClipSlotComponent.h"
#include "../Engine/EngineBridge.h"
#include "../StemExtraction/StemExtractionDialog.h"

// Static callback for state changes (set by parent SessionGridComponent)
std::function<void(int track, int scene, ClipSlotComponent::State state)> ClipSlotComponent::onStateChange;

// Static callback for clip moves via drag and drop (Phase 7.0)
std::function<void(int fromTrack, int fromScene, int toTrack, int toScene)> ClipSlotComponent::onClipMoved;

ClipSlotComponent::ClipSlotComponent(int trackIndex, int sceneIndex)
    : trackIdx(trackIndex), sceneIdx(sceneIndex)
{
    setSize(120, 60);
    setTooltip("Track " + juce::String(trackIdx + 1) + ", Scene " + juce::String(sceneIdx + 1));
}

void ClipSlotComponent::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds().reduced(borderWidth);

    switch (currentState)
    {
        case State::Empty:
            drawEmptySlot(g, bounds);
            break;
        case State::Loaded:
            drawLoadedClip(g, bounds);
            break;
        case State::Playing:
            drawPlayingClip(g, bounds);
            break;
        case State::Recording:
            drawRecordingClip(g, bounds);
            break;
        case State::Queued:
            // Show queued state with pulse indicator (Phase 6.7)
            drawLoadedClip(g, bounds);
            drawQueueIndicator(g, bounds);
            break;
    }
    
    // Phase 7.0: Draw drag over overlay if dragging over this slot
    if (isDraggingOver)
    {
        drawDragOverOverlay(g, bounds);
    }
}

void ClipSlotComponent::resized()
{
    // Nothing special to resize
}

void ClipSlotComponent::mouseDown(const juce::MouseEvent& event)
{
    if (event.mods.isPopupMenu())
    {
        // Show context menu
        juce::PopupMenu menu;
        
        if (clipLoaded)
        {
            menu.addItem("Extract Stems", [this] { extractStemsForClip(); });
            menu.addSeparator();
        }
        
        menu.addItem("Duplicate Clip", [this] { /* duplicate logic */ });
        menu.addItem("Delete Clip", [this] { clearClip(); });
        menu.addSeparator();
        menu.addItem("Change Color", [this] { /* color picker */ });
        menu.showMenuAsync(juce::PopupMenu::Options().withTargetComponent(this));
    }
    else if (clipLoaded)
    {
        launchClip();
    }
}

void ClipSlotComponent::mouseDrag(const juce::MouseEvent& event)
{
    if (clipLoaded && !event.mods.isPopupMenu())
    {
        // Phase 7.0: Start drag and drop operation
        // Build drag data JSON properly for JUCE 7 compatibility
        auto* obj = new juce::DynamicObject();
        obj->setProperty("type", "clip");
        obj->setProperty("trackIdx", trackIdx);
        obj->setProperty("sceneIdx", sceneIdx);
        obj->setProperty("clipName", clipName);
        juce::var dragData(juce::JSON::toString(juce::var(obj)));
        
        juce::Image dragImage(juce::Image::ARGB, getWidth(), getHeight(), true);
        juce::Graphics g(dragImage);
        paint(g);
        
        startDragging(dragData, this, dragImage, true);
    }
}

void ClipSlotComponent::mouseUp(const juce::MouseEvent& event)
{
    // Handle drop or click release
}

void ClipSlotComponent::setClip(const juce::String& name, juce::Colour color)
{
    clipName = name;
    clipColor = color;
    clipLoaded = true;
    currentState = State::Loaded;
    repaint();
}

void ClipSlotComponent::clearClip()
{
    clipName.clear();
    clipColor = juce::Colours::grey;
    clipLoaded = false;
    currentState = State::Empty;
    repaint();
}

void ClipSlotComponent::launchClip()
{
    if (!clipLoaded)
        return;

    // Use EngineBridge to schedule quantized clip launch (Phase 6.7)
    auto& engine = EngineBridge::getInstance();
    engine.scheduleClipQuantized(trackIdx, sceneIdx, 1); // 1 bar quantization
    
    setState(State::Queued);
}

void ClipSlotComponent::stopClip()
{
    // Use EngineBridge to stop clip (Phase 6.7)
    auto& engine = EngineBridge::getInstance();
    engine.stopClip(trackIdx, sceneIdx);
    
    setState(State::Loaded);
}

void ClipSlotComponent::setState(State newState)
{
    if (currentState != newState)
    {
        currentState = newState;
        repaint();
        
        // Notify parent if callback is set
        if (onStateChange)
            onStateChange(trackIdx, sceneIdx, currentState);
    }
}

void ClipSlotComponent::updateStateFromEngine()
{
    if (!clipLoaded)
    {
        if (currentState != State::Empty)
            setState(State::Empty);
        return;
    }
    
    // Query engine for this clip's state (Phase 6.7)
    auto& engine = EngineBridge::getInstance();
    int clipState = engine.getClipState(trackIdx, sceneIdx);
    
    State newState = currentState;
    
    switch (clipState)
    {
        case 0: // Stopped
            newState = State::Loaded;
            break;
        case 1: // Playing
            newState = State::Playing;
            break;
        case 2: // Queued
            newState = State::Queued;
            break;
        default:
            newState = State::Loaded;
            break;
    }
    
    if (newState != currentState)
    {
        setState(newState);
    }
}

void ClipSlotComponent::drawQueueIndicator(juce::Graphics& g, const juce::Rectangle<int>& bounds)
{
    // Queue indicator - pulsing yellow highlight (Phase 6.7)
    float pulseAlpha = 0.2f + 0.3f * std::sin(juce::Time::getCurrentTime().getMilliseconds() * 0.008f);
    
    g.setColour(juce::Colours::yellow.withAlpha(pulseAlpha));
    g.fillRoundedRectangle(bounds.toFloat().reduced(3), cornerRadius - 1);
    
    // Queue dot in top right - JUCE 7: need mutable copy for removeFromTop
    juce::Rectangle<int> mutableBounds(bounds);
    auto dotBounds = mutableBounds.removeFromTop(8).removeFromRight(8).reduced(1);
    g.setColour(juce::Colours::yellow);
    g.fillEllipse(dotBounds.toFloat());
}

void ClipSlotComponent::drawEmptySlot(juce::Graphics& g, const juce::Rectangle<int>& bounds)
{
    // Draw dark background with subtle border
    g.setColour(juce::Colour(0xFF3B3B3B));
    g.fillRoundedRectangle(bounds.toFloat(), cornerRadius);

    g.setColour(juce::Colour(0xFF4B4B4B));
    g.drawRoundedRectangle(bounds.toFloat(), cornerRadius, 1.0f);
}

void ClipSlotComponent::drawLoadedClip(juce::Graphics& g, const juce::Rectangle<int>& bounds)
{
    // Draw clip with color
    g.setColour(clipColor.darker(0.2f));
    g.fillRoundedRectangle(bounds.toFloat(), cornerRadius);

    g.setColour(clipColor);
    g.drawRoundedRectangle(bounds.toFloat(), cornerRadius, 2.0f);

    // Draw clip name
    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(12.0f, juce::Font::bold));
    g.drawText(clipName, bounds.reduced(4), juce::Justification::centred, true);

    // Draw small scene indicator
    g.setFont(juce::Font(10.0f));
    g.setColour(juce::Colours::white.withAlpha(0.7f));
    g.drawText(juce::String(sceneIdx + 1), bounds.getWidth() - 16, 4, 12, 12, juce::Justification::centred);
}

void ClipSlotComponent::drawPlayingClip(juce::Graphics& g, const juce::Rectangle<int>& bounds)
{
    // Draw with brighter color and "playing" indicator
    g.setColour(clipColor);
    g.fillRoundedRectangle(bounds.toFloat(), cornerRadius);

    // Draw pulsing border effect (simplified)
    g.setColour(juce::Colours::green.withAlpha(0.8f));
    g.drawRoundedRectangle(bounds.toFloat(), cornerRadius, 3.0f);

    // Draw clip name
    g.setColour(juce::Colours::black);
    g.setFont(juce::Font(12.0f, juce::Font::bold));
    g.drawText(clipName, bounds.reduced(4), juce::Justification::centred, true);

    // Draw "playing" triangle indicator
    auto mutableBounds = bounds;  // Create non-const copy
    auto indicatorBounds = mutableBounds.removeFromLeft(20).reduced(4);
    juce::Path playIcon;
    playIcon.addTriangle(
        static_cast<float>(indicatorBounds.getX()),
        static_cast<float>(indicatorBounds.getY()),
        static_cast<float>(indicatorBounds.getX()),
        static_cast<float>(indicatorBounds.getBottom()),
        static_cast<float>(indicatorBounds.getRight()),
        static_cast<float>(indicatorBounds.getCentreY())
    );
    g.fillPath(playIcon);
}

void ClipSlotComponent::drawRecordingClip(juce::Graphics& g, const juce::Rectangle<int>& bounds)
{
    // Draw with red recording indicator
    g.setColour(juce::Colours::red.darker(0.3f));
    g.fillRoundedRectangle(bounds.toFloat(), cornerRadius);

    g.setColour(juce::Colours::red);
    g.drawRoundedRectangle(bounds.toFloat(), cornerRadius, 3.0f);

    // Draw clip name
    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(12.0f, juce::Font::bold));
    g.drawText("[REC] " + clipName, bounds.reduced(4), juce::Justification::centred, true);

    // Draw recording circle indicator
    auto mutableBounds = bounds;  // Create non-const copy
    auto indicatorBounds = mutableBounds.removeFromLeft(20).reduced(6);
    g.setColour(juce::Colours::red);
    g.fillEllipse(indicatorBounds.toFloat());
}

// Phase 7.0: Drag and Drop Target Implementation

bool ClipSlotComponent::isInterestedInDragSource(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    // Accept drops from other ClipSlotComponents that have a clip
    // JUCE 7: sourceComponent is a WeakReference
    auto* source = dragSourceDetails.sourceComponent.get();
    if (source == nullptr || source == this)
        return false; // Don't accept drops from self or deleted component
    
    auto* sourceSlot = dynamic_cast<ClipSlotComponent*>(source);
    if (sourceSlot && sourceSlot->hasClip())
        return true;
    
    return false;
}

void ClipSlotComponent::itemDragEnter(const juce::DragAndDropTarget::SourceDetails& /*dragSourceDetails*/)
{
    isDraggingOver = true;
    repaint();
}

void ClipSlotComponent::itemDragMove(const juce::DragAndDropTarget::SourceDetails& /*dragSourceDetails*/)
{
    // Could update position tracking here if needed
}

void ClipSlotComponent::itemDragExit(const juce::DragAndDropTarget::SourceDetails& /*dragSourceDetails*/)
{
    isDraggingOver = false;
    repaint();
}

void ClipSlotComponent::itemDropped(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    isDraggingOver = false;
    
    // JUCE 7: sourceComponent is a WeakReference
    auto* source = dragSourceDetails.sourceComponent.get();
    if (source == nullptr)
        return;
    
    auto* sourceSlot = dynamic_cast<ClipSlotComponent*>(source);
    
    if (sourceSlot && sourceSlot->hasClip())
    {
        // Get clip data from source
        juce::String sourceName = sourceSlot->getClipName();
        juce::Colour sourceColor = sourceSlot->getClipColor();
        int sourceTrack = sourceSlot->getTrackIndex();
        int sourceScene = sourceSlot->getSceneIndex();
        
        // Clear source
        sourceSlot->clearClip();
        
        // Set destination (even if occupied - we replace)
        setClip(sourceName, sourceColor);
        
        // Notify parent about the move for EngineBridge update (Phase 7.0)
        if (onClipMoved)
        {
            onClipMoved(sourceTrack, sourceScene, trackIdx, sceneIdx);
        }
    }
    
    repaint();
}

void ClipSlotComponent::drawDragOverOverlay(juce::Graphics& g, const juce::Rectangle<int>& bounds)
{
    // Draw a highlight border when dragging over
    g.setColour(juce::Colours::white.withAlpha(0.5f));
    g.drawRoundedRectangle(bounds.toFloat().reduced(2), cornerRadius, 3.0f);
    
    // Fill with subtle white overlay
    g.setColour(juce::Colours::white.withAlpha(0.2f));
    g.fillRoundedRectangle(bounds.toFloat().reduced(4), cornerRadius - 1);
}

// Phase 8.x: Stem Extraction
void ClipSlotComponent::extractStemsForClip()
{
    if (!clipLoaded)
        return;
    
    // TODO: Get actual audio file path from clip data
    // For now, we'll show the dialog with a placeholder path
    // The actual implementation should retrieve the audio file path 
    // associated with this clip from the engine/session data
    
    juce::String audioFilePath = "placeholder.wav"; // TODO: Get real path
    juce::String outputDir = juce::File::getSpecialLocation(
        juce::File::userApplicationDataDirectory
    ).getChildFile("OpenDAW/stems").getFullPathName();
    
    // Create and show the extraction dialog
    auto* dialog = new StemExtractionDialog(audioFilePath, outputDir);
    
    dialog->onExtractionComplete = [this](const EngineBridge::StemPaths& result) {
        // TODO: Create 4 new tracks with the extracted stems
        // This would involve:
        // 1. Getting the current track count
        // 2. Creating 4 new tracks at the end
        // 3. Loading each stem file into a clip on those tracks
        
        juce::Logger::writeToLog("Stem extraction complete:");
        juce::Logger::writeToLog("  Drums: " + result.drums);
        juce::Logger::writeToLog("  Bass: " + result.bass);
        juce::Logger::writeToLog("  Vocals: " + result.vocals);
        juce::Logger::writeToLog("  Other: " + result.other);
    };
    
    dialog->onExtractionCancelled = []() {
        juce::Logger::writeToLog("Stem extraction cancelled or failed");
    };
    
    dialog->enterModalState(true, nullptr, false);
}
