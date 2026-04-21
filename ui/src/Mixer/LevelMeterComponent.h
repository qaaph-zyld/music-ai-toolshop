#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

/**
 * LevelMeterComponent - Real-time audio level meter display
 *
 * Displays peak and RMS levels with:
 * - Smooth decay animation
 * - Clipping indicator (red when peak > 0dB)
 * - Configurable orientation (vertical/horizontal)
 * - dB scale visualization
 */
class LevelMeterComponent : public juce::Component,
                            public juce::Timer
{
public:
    enum class Orientation { Vertical, Horizontal };
    enum class Style { PeakOnly, RMSOnly, PeakAndRMS };

    LevelMeterComponent(Orientation orient = Orientation::Vertical,
                        Style style = Style::PeakAndRMS);
    ~LevelMeterComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;

    // Set current levels (called from UI thread)
    void setLevels(float peakDb, float rmsDb);

    // Get current levels
    float getPeakDb() const { return currentPeakDb; }
    float getRmsDb() const { return currentRmsDb; }

    // Check if clipping
    bool isClipping() const { return currentPeakDb > 0.0f; }

    // Reset clipping indicator
    void resetClipping();

    // Configuration
    void setOrientation(Orientation orient);
    void setStyle(Style s);
    void setDecayRate(float dbPerSecond); // Default: 30.0 dB/s

private:
    Orientation orientation;
    Style style;

    // Current displayed levels (with smooth decay)
    float currentPeakDb = -96.0f;
    float currentRmsDb = -96.0f;

    // Target levels (set from audio thread)
    float targetPeakDb = -96.0f;
    float targetRmsDb = -96.0f;

    // Animation parameters
    float decayRateDbPerSec = 30.0f;  // How fast the meter falls
    float attackRateDbPerSec = 1000.0f; // How fast the meter rises (instant)
    int timerIntervalMs = 33;         // ~30 fps

    // Clipping indicator
    bool clipping = false;
    int clippingHoldFrames = 30;      // Hold clipping indication for ~1 second
    int clippingFrameCounter = 0;

    // dB range for visualization
    static constexpr float minDb = -60.0f;
    static constexpr float maxDb = 6.0f;

    // Helper methods
    void updateLevels();
    float dbToPosition(float db) const;
    juce::Colour getGradientColor(float db) const;
    void drawVerticalMeter(juce::Graphics& g, const juce::Rectangle<float>& bounds);
    void drawHorizontalMeter(juce::Graphics& g, const juce::Rectangle<float>& bounds);
    void drawDbScale(juce::Graphics& g, const juce::Rectangle<float>& bounds);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(LevelMeterComponent)
};
