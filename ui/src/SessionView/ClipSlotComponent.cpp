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
        // Session H: Use simple format for session clip drag
        // Format: "session_clip:trackIdx:sceneIdx"
        juce::String dragData = "session_clip:" + juce::String(trackIdx) + ":" + juce::String(sceneIdx);
        
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
    
    // Get actual audio file path from the session/clip data
    // In a full implementation, this would query the engine for the clip's audio file
    // For now, we use the clip name to construct a path (simplified)
    juce::File audioFile = juce::File::getCurrentWorkingDirectory()
        .getChildFile("audio")
        .getChildFile(clipName + ".wav");
    
    // Fallback: if clip name doesn't resolve, use a test path
    juce::String audioFilePath = audioFile.existsAsFile() 
        ? audioFile.getFullPathName() 
        : clipName; // Engine will resolve relative paths
    
    juce::String outputDir = juce::File::getSpecialLocation(
        juce::File::userApplicationDataDirectory
    ).getChildFile("OpenDAW/stems").getFullPathName();
    
    // Create and show the extraction dialog
    auto* dialog = new StemExtractionDialog(audioFilePath, outputDir);
    
    dialog->onExtractionComplete = [this](const EngineBridge::StemPaths& result) {
        if (!result.success)
        {
            juce::Logger::writeToLog("Stem extraction failed");
            return;
        }
        
        juce::Logger::writeToLog("Stem extraction complete - creating arrangement tracks...");
        
        auto& engine = EngineBridge::getInstance();
        
        // Get current arrangement track count to find starting position
        uint32_t startTrack = engine.getArrangementTrackCount();
        
        // Ensure we have at least 4 arrangement tracks (for drums, bass, vocals, other)
        uint32_t requiredTracks = startTrack + 4;
        
        // Re-initialize arrangement with enough tracks if needed
        // Note: In production, this would dynamically add tracks
        if (startTrack < requiredTracks)
        {
            engine.initArrangement(requiredTracks);
            startTrack = requiredTracks - 4; // Place stems in the last 4 tracks
        }
        else
        {
            startTrack = 0; // Use first 4 tracks
        }
        
        // Add each stem to the arrangement
        struct StemInfo {
            juce::String path;
            juce::String name;
            juce::Colour color;
        };
        
        std::vector<StemInfo> stems;
        
        if (!result.drums.isEmpty())
            stems.push_back({result.drums, "Drums", juce::Colours::red});
        if (!result.bass.isEmpty())
            stems.push_back({result.bass, "Bass", juce::Colours::blue});
        if (!result.vocals.isEmpty())
            stems.push_back({result.vocals, "Vocals", juce::Colours::green});
        if (!result.other.isEmpty())
            stems.push_back({result.other, "Other", juce::Colours::yellow});
        
        // Add stems to arrangement (starting at beat 0, 4 bars duration)
        for (size_t i = 0; i < stems.size() && i < 4; ++i)
        {
            uint32_t trackIdx = startTrack + static_cast<uint32_t>(i);
            const auto& stem = stems[i];
            
            auto clipInfo = engine.addAudioClipToArrangement(
                trackIdx,
                0.0,                    // startBeat
                stem.name,              // name
                4.0,                    // durationBars (default, will auto-adjust)
                stem.path               // filePath
            );
            
            if (clipInfo.isValid())
            {
                juce::Logger::writeToLog("Added " + stem.name + " to arrangement track " + 
                                         juce::String(trackIdx + 1));
            }
            else
            {
                juce::Logger::writeToLog("Failed to add " + stem.name + " to arrangement");
            }
        }
        
        juce::Logger::writeToLog("Stem extraction workflow complete - " + 
                                 juce::String(static_cast<int>(stems.size())) + " stems added");
        
        // Notify that arrangement has been updated
        // This would typically trigger a UI refresh
        if (onStateChange)
            onStateChange(trackIdx, sceneIdx, State::Loaded);
    };
    
    dialog->onExtractionCancelled = []() {
        juce::Logger::writeToLog("Stem extraction cancelled or failed");
    };
    
    dialog->enterModalState(true, nullptr, false);
}
