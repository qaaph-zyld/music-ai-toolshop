#include "PianoRollComponent.h"

PianoRollComponent::PianoRollComponent()
{
    setOpaque(true);
}

void PianoRollComponent::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds();
    
    // Fill background
    g.fillAll(juce::Colour(0xFF1a1a1a));
    
    // Draw piano keyboard on left
    auto keyboardArea = bounds.removeFromLeft(keyboardWidth);
    drawKeyboard(g, keyboardArea);
    
    // Draw grid and notes in remaining area
    drawGrid(g, bounds);
    drawNotes(g, bounds);
}

void PianoRollComponent::resized()
{
    repaint();
}

void PianoRollComponent::setNotes(const std::vector<MidiNote>& newNotes)
{
    notes = newNotes;
    repaint();
    sendChangeMessage();
}

void PianoRollComponent::addNote(const MidiNote& note)
{
    notes.push_back(note);
    repaint();
    sendChangeMessage();
    if (onNotesChanged)
        onNotesChanged();
}

void PianoRollComponent::deleteNote(int index)
{
    if (index >= 0 && index < static_cast<int>(notes.size()))
    {
        notes.erase(notes.begin() + index);
        if (selectedNoteIndex == index)
            selectedNoteIndex = -1;
        repaint();
        sendChangeMessage();
        if (onNotesChanged)
            onNotesChanged();
    }
}

void PianoRollComponent::moveNote(int index, float newStartBeat, int newPitch)
{
    if (index >= 0 && index < static_cast<int>(notes.size()))
    {
        notes[index].startBeat = juce::jmax(0.0f, newStartBeat);
        notes[index].pitch = juce::jlimit(0, 127, newPitch);
        repaint();
        sendChangeMessage();
        if (onNotesChanged)
            onNotesChanged();
    }
}

void PianoRollComponent::updateNoteVelocity(int index, int newVelocity)
{
    if (index >= 0 && index < static_cast<int>(notes.size()))
    {
        notes[index].velocity = juce::jlimit(0, 127, newVelocity);
        repaint();
        sendChangeMessage();
    }
}

void PianoRollComponent::quantizeNotes(float division)
{
    for (auto& note : notes)
    {
        float snappedBeat = std::round(note.startBeat / division) * division;
        note.startBeat = juce::jmax(0.0f, snappedBeat);
    }
    repaint();
    sendChangeMessage();
    if (onNotesChanged)
        onNotesChanged();
}

void PianoRollComponent::transposeNotes(int semitones)
{
    for (auto& note : notes)
    {
        note.pitch = juce::jlimit(0, 127, note.pitch + semitones);
    }
    repaint();
    sendChangeMessage();
    if (onNotesChanged)
        onNotesChanged();
}

void PianoRollComponent::scaleVelocities(float scale)
{
    for (auto& note : notes)
    {
        int newVelocity = static_cast<int>(std::round(note.velocity * scale));
        note.velocity = juce::jlimit(0, 127, newVelocity);
    }
    repaint();
    sendChangeMessage();
    if (onNotesChanged)
        onNotesChanged();
}

void PianoRollComponent::setZoomX(float zoom)
{
    zoomX = juce::jlimit(10.0f, 500.0f, zoom);
    repaint();
}

void PianoRollComponent::setZoomY(float zoom)
{
    zoomY = juce::jlimit(4.0f, 20.0f, zoom);
    repaint();
}

void PianoRollComponent::setViewRange(float startBeat, float endBeat)
{
    viewStartBeat = juce::jmax(0.0f, startBeat);
    viewEndBeat = juce::jmax(viewStartBeat + 1.0f, endBeat);
    repaint();
}

void PianoRollComponent::scrollToNote(int pitch)
{
    scrollOffsetY = juce::jlimit(0, 127 - static_cast<int>(getHeight() / zoomY), 127 - pitch);
    repaint();
}

void PianoRollComponent::drawKeyboard(juce::Graphics& g, juce::Rectangle<int> bounds)
{
    int startPitch = 127 - scrollOffsetY;
    int endPitch = juce::jmax(0, startPitch - static_cast<int>(bounds.getHeight() / zoomY));
    
    for (int pitch = startPitch; pitch >= endPitch; --pitch)
    {
        int y = pitchToY(pitch, bounds);
        int keyHeight = static_cast<int>(zoomY);
        
        bool isBlack = isBlackKey(pitch);
        
        if (isBlack)
        {
            g.setColour(juce::Colours::black);
            g.fillRect(bounds.getX(), y - keyHeight, blackKeyWidth, keyHeight);
        }
        else
        {
            g.setColour(juce::Colours::white);
            g.fillRect(bounds.getX(), y - keyHeight, keyboardWidth, keyHeight);
            g.setColour(juce::Colours::lightgrey);
            g.drawLine(bounds.getX(), y, bounds.getRight(), y);
        }
        
        // Draw note name for C keys
        if (pitch % 12 == 0)
        {
            g.setColour(juce::Colours::darkgrey);
            g.setFont(10.0f);
            g.drawText(getNoteName(pitch), bounds.getX() + 2, y - keyHeight + 2, 
                       keyboardWidth - 4, keyHeight - 4, juce::Justification::centredLeft);
        }
    }
    
    // Keyboard border
    g.setColour(juce::Colours::darkgrey);
    g.drawVerticalLine(bounds.getRight() - 1, bounds.getY(), bounds.getBottom());
}

void PianoRollComponent::drawGrid(juce::Graphics& g, juce::Rectangle<int> bounds)
{
    g.setColour(juce::Colour(0xFF2a2a2a));
    g.fillRect(bounds);
    
    // Draw beat lines
    g.setColour(juce::Colour(0xFF3a3a3a));
    for (float beat = std::floor(viewStartBeat); beat <= viewEndBeat; beat += 1.0f)
    {
        int x = static_cast<int>(beatToX(beat, bounds));
        g.drawVerticalLine(x, bounds.getY(), bounds.getBottom());
    }
    
    // Draw sub-beat lines (based on grid division)
    g.setColour(juce::Colour(0xFF333333));
    for (float beat = std::floor(viewStartBeat / gridDivision) * gridDivision;
         beat <= viewEndBeat; beat += gridDivision)
    {
        if (std::fmod(beat, 1.0f) != 0.0f) // Skip whole beats (already drawn)
        {
            int x = static_cast<int>(beatToX(beat, bounds));
            g.drawVerticalLine(x, bounds.getY(), bounds.getBottom());
        }
    }
    
    // Draw pitch lines
    int startPitch = 127 - scrollOffsetY;
    int endPitch = juce::jmax(0, startPitch - static_cast<int>(bounds.getHeight() / zoomY));
    
    for (int pitch = startPitch; pitch >= endPitch; --pitch)
    {
        int y = pitchToY(pitch, bounds);
        
        if (isBlackKey(pitch))
            g.setColour(juce::Colour(0xFF252525));
        else
            g.setColour(juce::Colour(0xFF2a2a2a));
            
        g.drawHorizontalLine(y - 1, bounds.getX(), bounds.getRight());
    }
}

void PianoRollComponent::drawNotes(juce::Graphics& g, juce::Rectangle<int> bounds)
{
    for (size_t i = 0; i < notes.size(); ++i)
    {
        const auto& note = notes[i];
        
        // Skip notes outside view
        if (note.startBeat + note.durationBeats < viewStartBeat ||
            note.startBeat > viewEndBeat)
            continue;
        
        auto noteBounds = getNoteBounds(note, bounds);
        
        // Check if note is in view vertically
        if (noteBounds.getBottom() < bounds.getY() || noteBounds.getY() > bounds.getBottom())
            continue;
        
        // Selection highlight
        if (static_cast<int>(i) == selectedNoteIndex)
        {
            g.setColour(juce::Colours::orange);
            g.drawRect(noteBounds.expanded(2), 2);
        }
        
        // Note body with velocity-based color
        g.setColour(getNoteColor(note.velocity));
        g.fillRect(noteBounds);
        
        // Note border
        g.setColour(juce::Colours::white.withAlpha(0.3f));
        g.drawRect(noteBounds);
        
        // Velocity indicator bar at bottom of note
        drawVelocityIndicator(g, noteBounds, note.velocity);
    }
}

void PianoRollComponent::drawVelocityIndicator(juce::Graphics& g, juce::Rectangle<int> noteBounds, int velocity)
{
    int barHeight = 3;
    int barWidth = (velocity * noteBounds.getWidth()) / 127;
    
    auto barBounds = noteBounds.removeFromBottom(barHeight).removeFromLeft(barWidth);
    
    g.setColour(juce::Colours::white.withAlpha(0.7f));
    g.fillRect(barBounds);
}

juce::Rectangle<int> PianoRollComponent::getNoteBounds(const MidiNote& note, juce::Rectangle<int> gridArea) const
{
    int x = static_cast<int>(beatToX(note.startBeat, gridArea));
    int width = static_cast<int>(note.durationBeats * zoomX);
    int y = pitchToY(note.pitch, gridArea);
    int height = static_cast<int>(zoomY);
    
    return { x, y - height, width, height };
}

juce::Colour PianoRollComponent::getNoteColor(int velocity) const
{
    // Map velocity to color: dim blue-gray (low velocity) to bright yellow-orange (high velocity)
    float normalized = velocity / 127.0f;
    
    juce::Colour lowVelColor(0xFF4a5a6a);   // Blue-gray
    juce::Colour highVelColor(0xFFf0c040);  // Yellow-orange
    
    return lowVelColor.interpolatedWith(highVelColor, normalized);
}

bool PianoRollComponent::isBlackKey(int pitch) const
{
    int noteInOctave = pitch % 12;
    return noteInOctave == 1 || noteInOctave == 3 || noteInOctave == 6 ||
           noteInOctave == 8 || noteInOctave == 10;
}

juce::String PianoRollComponent::getNoteName(int pitch) const
{
    static const char* noteNames[] = { "C", "C#", "D", "D#", "E", "F", 
                                        "F#", "G", "G#", "A", "A#", "B" };
    int octave = (pitch / 12) - 1;
    int note = pitch % 12;
    return juce::String(noteNames[note]) + juce::String(octave);
}

float PianoRollComponent::beatToX(float beat, juce::Rectangle<int> gridArea) const
{
    return gridArea.getX() + (beat - viewStartBeat) * zoomX;
}

float PianoRollComponent::xToBeat(float x, juce::Rectangle<int> gridArea) const
{
    return viewStartBeat + (x - gridArea.getX()) / zoomX;
}

int PianoRollComponent::pitchToY(int pitch, juce::Rectangle<int> gridArea) const
{
    int relativePitch = 127 - pitch - scrollOffsetY;
    return gridArea.getY() + relativePitch * static_cast<int>(zoomY);
}

int PianoRollComponent::yToPitch(int y, juce::Rectangle<int> gridArea) const
{
    int relativePitch = (y - gridArea.getY()) / static_cast<int>(zoomY);
    return 127 - relativePitch - scrollOffsetY;
}

int PianoRollComponent::snapPitchToGrid(int pitch) const
{
    return pitch; // No pitch snapping for now
}

float PianoRollComponent::snapBeatToGrid(float beat) const
{
    if (!snapToGrid)
        return beat;
    return std::round(beat / gridDivision) * gridDivision;
}

int PianoRollComponent::hitTestNote(juce::Point<int> pos, juce::Rectangle<int> gridArea) const
{
    for (int i = static_cast<int>(notes.size()) - 1; i >= 0; --i)
    {
        auto bounds = getNoteBounds(notes[i], gridArea);
        if (bounds.contains(pos))
            return i;
    }
    return -1;
}

void PianoRollComponent::mouseDown(const juce::MouseEvent& event)
{
    auto bounds = getLocalBounds().withLeft(keyboardWidth);
    
    if (!bounds.contains(event.getPosition()))
        return;
    
    int noteIndex = hitTestNote(event.getPosition(), bounds);
    
    if (noteIndex >= 0)
    {
        // Select existing note
        selectedNoteIndex = noteIndex;
        draggingNoteIndex = noteIndex;
        dragStartPos = event.getPosition().toFloat();
        dragStartBeat = notes[noteIndex].startBeat;
        dragStartPitch = notes[noteIndex].pitch;
        
        if (onNoteSelected)
            onNoteSelected(noteIndex);
    }
    else
    {
        // Start adding a new note
        isAddingNote = true;
        selectedNoteIndex = -1;
    }
    
    repaint();
}

void PianoRollComponent::mouseDrag(const juce::MouseEvent& event)
{
    auto bounds = getLocalBounds().withLeft(keyboardWidth);
    
    if (draggingNoteIndex >= 0)
    {
        float deltaX = event.getPosition().getX() - dragStartPos.getX();
        float deltaBeats = deltaX / zoomX;
        float newBeat = snapBeatToGrid(dragStartBeat + deltaBeats);
        
        int newPitch = yToPitch(event.getPosition().getY(), bounds);
        newPitch = juce::jlimit(0, 127, newPitch);
        
        notes[draggingNoteIndex].startBeat = newBeat;
        notes[draggingNoteIndex].pitch = newPitch;
        
        repaint();
    }
}

void PianoRollComponent::mouseUp(const juce::MouseEvent& event)
{
    if (draggingNoteIndex >= 0)
    {
        // Commit the move
        if (onNotesChanged)
            onNotesChanged();
        sendChangeMessage();
    }
    else if (isAddingNote)
    {
        // Add new note
        auto bounds = getLocalBounds().withLeft(keyboardWidth);
        
        float beat = snapBeatToGrid(xToBeat(event.getPosition().getX(), bounds));
        int pitch = juce::jlimit(0, 127, yToPitch(event.getPosition().getY(), bounds));
        
        MidiNote newNote{ pitch, 100, beat, gridDivision };
        addNote(newNote);
    }
    
    draggingNoteIndex = -1;
    isAddingNote = false;
    repaint();
}

void PianoRollComponent::mouseDoubleClick(const juce::MouseEvent& event)
{
    auto bounds = getLocalBounds().withLeft(keyboardWidth);
    
    if (!bounds.contains(event.getPosition()))
        return;
    
    int noteIndex = hitTestNote(event.getPosition(), bounds);
    if (noteIndex >= 0)
    {
        deleteNote(noteIndex);
    }
}
