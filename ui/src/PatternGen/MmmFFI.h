#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_gui_extra/juce_gui_extra.h>

/**
 * FFI Wrapper for MMM (Music Motion Machine) Pattern Generation
 *
 * Provides C++ interface to Rust MMM pattern generation engine.
 * Supports drums, bass, and melody generation with style selection.
 */

namespace OpenDAW {

/// Pattern style options
enum class PatternStyle {
    Electronic,
    House,
    Techno,
    Ambient,
    Jazz,
    HipHop,
    Rock
};

/// Pattern type options
enum class PatternType {
    Drums,
    Bass,
    Melody
};

/// MIDI note structure
struct MidiNote {
    uint8_t pitch;        // MIDI note number (0-127)
    uint8_t velocity;     // Velocity (0-127)
    float startBeat;    // Start position in beats
    float durationBeats;  // Duration in beats
};

/// Pattern configuration
struct PatternConfig {
    PatternStyle style = PatternStyle::Electronic;
    PatternType type = PatternType::Drums;
    int bars = 4;
    float bpm = 120.0f;
    juce::String key = "C";
    juce::String chords = "Am,F,C,G";  // For bass generation
};

/// Pattern data
struct PatternData {
    juce::String trackName;
    float durationBeats = 0.0f;
    std::vector<MidiNote> notes;
};

/// FFI wrapper class
class MmmFFI {
public:
    /// Check if MMM is available
    static bool isAvailable();

    /// Create new MMM handle
    static void* createHandle();

    /// Load style model
    static bool loadStyle(void* handle, PatternStyle style);

    /// Generate pattern
    static bool generatePattern(void* handle, const PatternConfig& config);

    /// Get generated pattern
    static PatternData getPattern(void* handle);

    /// Clear current pattern
    static bool clearPattern(void* handle);

    /// Destroy handle
    static void destroyHandle(void* handle);

    /// Convert style to string
    static juce::String styleToString(PatternStyle style);

private:
    // Prevent instantiation
    MmmFFI() = delete;
};

} // namespace OpenDAW
