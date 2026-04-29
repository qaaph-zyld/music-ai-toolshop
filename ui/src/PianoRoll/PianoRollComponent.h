#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <vector>

struct MidiNote {
    int pitch;           // 0-127 MIDI pitch
    int velocity;        // 0-127 MIDI velocity
    float startBeat;     // Start position in beats
    float durationBeats; // Duration in beats
};

/**
 * Piano roll component for MIDI note editing
 * 
 * Features:
 * - Piano keyboard display on left side
 * - Note grid with time on X axis, pitch on Y axis
 * - Velocity visualization via color intensity
 * - Interactive note editing (add, move, delete)
 * - Zoom and scroll support
 */
class PianoRollComponent : public juce::Component,
                           public juce::ChangeBroadcaster
{
public:
    PianoRollComponent();
    ~PianoRollComponent() override = default;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Note management
    void setNotes(const std::vector<MidiNote>& notes);
    std::vector<MidiNote> getNotes() const { return notes; }
    void addNote(const MidiNote& note);
    void deleteNote(int index);
    void moveNote(int index, float newStartBeat, int newPitch);
    void updateNoteVelocity(int index, int newVelocity);

    // Editing operations
    void quantizeNotes(float gridDivision);
    void transposeNotes(int semitones);
    void scaleVelocities(float scale);

    // View settings
    void setZoomX(float zoom);  // Horizontal zoom (time)
    void setZoomY(float zoom);  // Vertical zoom (pitch range)
    void setViewRange(float startBeat, float endBeat);
    void scrollToNote(int pitch);

    // Callbacks
    std::function<void(int noteIndex)> onNoteSelected;
    std::function<void()> onNotesChanged;

private:
    std::vector<MidiNote> notes;
    
    // View state
    float zoomX = 50.0f;     // Pixels per beat
    float zoomY = 8.0f;      // Pixels per semitone
    float viewStartBeat = 0.0f;
    float viewEndBeat = 4.0f;  // Default 4-bar view
    int scrollOffsetY = 0;     // Vertical scroll offset (in semitones)
    
    // Piano keyboard dimensions
    static constexpr int keyboardWidth = 60;
    static constexpr int blackKeyWidth = 40;
    
    // Interaction state
    int selectedNoteIndex = -1;
    int draggingNoteIndex = -1;
    juce::Point<float> dragStartPos;
    float dragStartBeat = 0.0f;
    int dragStartPitch = 0;
    bool isAddingNote = false;
    
    // Grid settings
    float gridDivision = 0.25f; // 1/16 note grid
    bool snapToGrid = true;

    // Drawing helpers
    void drawKeyboard(juce::Graphics& g, juce::Rectangle<int> bounds);
    void drawGrid(juce::Graphics& g, juce::Rectangle<int> bounds);
    void drawNotes(juce::Graphics& g, juce::Rectangle<int> bounds);
    void drawVelocityIndicator(juce::Graphics& g, juce::Rectangle<int> noteBounds, int velocity);
    
    juce::Rectangle<int> getNoteBounds(const MidiNote& note, juce::Rectangle<int> gridArea) const;
    juce::Colour getNoteColor(int velocity) const;
    bool isBlackKey(int pitch) const;
    juce::String getNoteName(int pitch) const;
    
    // Coordinate conversion
    float beatToX(float beat, juce::Rectangle<int> gridArea) const;
    float xToBeat(float x, juce::Rectangle<int> gridArea) const;
    int pitchToY(int pitch, juce::Rectangle<int> gridArea) const;
    int yToPitch(int y, juce::Rectangle<int> gridArea) const;
    int snapPitchToGrid(int pitch) const;
    float snapBeatToGrid(float beat) const;
    
    int hitTestNote(juce::Point<int> pos, juce::Rectangle<int> gridArea) const;

    // Mouse handling
    void mouseDown(const juce::MouseEvent& event) override;
    void mouseDrag(const juce::MouseEvent& event) override;
    void mouseUp(const juce::MouseEvent& event) override;
    void mouseDoubleClick(const juce::MouseEvent& event) override;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(PianoRollComponent)
};
