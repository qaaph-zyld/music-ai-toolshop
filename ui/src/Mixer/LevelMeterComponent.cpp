#include "LevelMeterComponent.h"

LevelMeterComponent::LevelMeterComponent(Orientation orient, Style s)
    : orientation(orient), style(s)
{
    // Start the animation timer
    startTimer(timerIntervalMs);
}

LevelMeterComponent::~LevelMeterComponent()
{
    stopTimer();
}

void LevelMeterComponent::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds().toFloat();

    // Background
    g.fillAll(juce::Colour(0x20, 0x20, 0x20));

    // Draw meter based on orientation
    if (orientation == Orientation::Vertical)
    {
        drawVerticalMeter(g, bounds);
    }
    else
    {
        drawHorizontalMeter(g, bounds);
    }

    // Draw dB scale
    drawDbScale(g, bounds);

    // Clipping indicator
    if (clipping)
    {
        g.setColour(juce::Colours::red);
        if (orientation == Orientation::Vertical)
        {
            g.fillRect(bounds.getX(), bounds.getY(), bounds.getWidth(), 3.0f);
        }
        else
        {
            g.fillRect(bounds.getRight() - 3.0f, bounds.getY(), 3.0f, bounds.getHeight());
        }
    }
}

void LevelMeterComponent::resized()
{
    // Component size determines meter dimensions
    repaint();
}

void LevelMeterComponent::timerCallback()
{
    updateLevels();

    // Update clipping indicator
    if (clippingFrameCounter > 0)
    {
        --clippingFrameCounter;
        if (clippingFrameCounter == 0)
        {
            clipping = false;
        }
    }

    repaint();
}

void LevelMeterComponent::setLevels(float peakDb, float rmsDb)
{
    // Update target levels (called from message thread)
    targetPeakDb = juce::jlimit(minDb, maxDb, peakDb);
    targetRmsDb = juce::jlimit(minDb, maxDb, rmsDb);

    // Check for clipping
    if (peakDb > 0.0f)
    {
        clipping = true;
        clippingFrameCounter = clippingHoldFrames;
    }
}

void LevelMeterComponent::resetClipping()
{
    clipping = false;
    clippingFrameCounter = 0;
}

void LevelMeterComponent::setOrientation(Orientation orient)
{
    orientation = orient;
    repaint();
}

void LevelMeterComponent::setStyle(Style s)
{
    style = s;
    repaint();
}

void LevelMeterComponent::setDecayRate(float dbPerSecond)
{
    decayRateDbPerSec = dbPerSecond;
}

void LevelMeterComponent::updateLevels()
{
    const float deltaTime = timerIntervalMs / 1000.0f;

    // Update peak level with smooth decay
    if (targetPeakDb > currentPeakDb)
    {
        // Attack (fast)
        currentPeakDb += attackRateDbPerSec * deltaTime;
        if (currentPeakDb > targetPeakDb)
            currentPeakDb = targetPeakDb;
    }
    else if (targetPeakDb < currentPeakDb)
    {
        // Decay (slow)
        currentPeakDb -= decayRateDbPerSec * deltaTime;
        if (currentPeakDb < targetPeakDb)
            currentPeakDb = targetPeakDb;
    }

    // Update RMS level (slower response)
    if (targetRmsDb > currentRmsDb)
    {
        currentRmsDb += (attackRateDbPerSec * 0.5f) * deltaTime;
        if (currentRmsDb > targetRmsDb)
            currentRmsDb = targetRmsDb;
    }
    else if (targetRmsDb < currentRmsDb)
    {
        currentRmsDb -= (decayRateDbPerSec * 0.5f) * deltaTime;
        if (currentRmsDb < targetRmsDb)
            currentRmsDb = targetRmsDb;
    }

    // Clamp to valid range
    currentPeakDb = juce::jlimit(minDb, maxDb, currentPeakDb);
    currentRmsDb = juce::jlimit(minDb, maxDb, currentRmsDb);
}

float LevelMeterComponent::dbToPosition(float db) const
{
    // Convert dB to normalized position (0.0 to 1.0)
    float normalized = (db - minDb) / (maxDb - minDb);
    return juce::jlimit(0.0f, 1.0f, normalized);
}

juce::Colour LevelMeterComponent::getGradientColor(float db) const
{
    // Color gradient: green -> yellow -> orange -> red
    if (db < -18.0f)
    {
        // Green zone (-60 to -18 dB)
        float t = (db - minDb) / (-18.0f - minDb);
        return juce::Colours::green.interpolatedWith(juce::Colours::lightgreen, t);
    }
    else if (db < -6.0f)
    {
        // Yellow zone (-18 to -6 dB)
        float t = (db - (-18.0f)) / (-6.0f - (-18.0f));
        return juce::Colours::lightgreen.interpolatedWith(juce::Colours::yellow, t);
    }
    else if (db < 0.0f)
    {
        // Orange zone (-6 to 0 dB)
        float t = (db - (-6.0f)) / (0.0f - (-6.0f));
        return juce::Colours::yellow.interpolatedWith(juce::Colours::orange, t);
    }
    else
    {
        // Red zone (0+ dB - clipping)
        return juce::Colours::red;
    }
}

void LevelMeterComponent::drawVerticalMeter(juce::Graphics& g, const juce::Rectangle<float>& bounds)
{
    const float margin = 2.0f;
    auto meterBounds = bounds.reduced(margin);

    // Draw background bar
    g.setColour(juce::Colour(0x10, 0x10, 0x10));
    g.fillRect(meterBounds);

    // Draw RMS level (filled area)
    if (style == Style::RMSOnly || style == Style::PeakAndRMS)
    {
        float rmsPos = dbToPosition(currentRmsDb);
        float rmsHeight = meterBounds.getHeight() * rmsPos;
        auto rmsBounds = meterBounds.removeFromBottom(rmsHeight);

        // Gradient fill for RMS
        juce::ColourGradient gradient(
            getGradientColor(minDb), meterBounds.getX(), meterBounds.getBottom(),
            getGradientColor(maxDb), meterBounds.getX(), meterBounds.getY(),
            false);
        g.setGradientFill(gradient);
        g.fillRect(rmsBounds);
    }

    // Draw peak level (thin line)
    if (style == Style::PeakOnly || style == Style::PeakAndRMS)
    {
        float peakPos = dbToPosition(currentPeakDb);
        float peakY = meterBounds.getBottom() - (meterBounds.getHeight() * peakPos);

        g.setColour(juce::Colours::white);
        g.fillRect(meterBounds.getX(), peakY - 1.0f, meterBounds.getWidth(), 2.0f);
    }
}

void LevelMeterComponent::drawHorizontalMeter(juce::Graphics& g, const juce::Rectangle<float>& bounds)
{
    const float margin = 2.0f;
    auto meterBounds = bounds.reduced(margin);

    // Draw background bar
    g.setColour(juce::Colour(0x10, 0x10, 0x10));
    g.fillRect(meterBounds);

    // Draw RMS level (filled area)
    if (style == Style::RMSOnly || style == Style::PeakAndRMS)
    {
        float rmsPos = dbToPosition(currentRmsDb);
        float rmsWidth = meterBounds.getWidth() * rmsPos;
        auto rmsBounds = meterBounds.removeFromLeft(rmsWidth);

        // Gradient fill for RMS
        juce::ColourGradient gradient(
            getGradientColor(minDb), meterBounds.getX(), meterBounds.getY(),
            getGradientColor(maxDb), meterBounds.getRight(), meterBounds.getY(),
            false);
        g.setGradientFill(gradient);
        g.fillRect(rmsBounds);
    }

    // Draw peak level (thin line)
    if (style == Style::PeakOnly || style == Style::PeakAndRMS)
    {
        float peakPos = dbToPosition(currentPeakDb);
        float peakX = meterBounds.getX() + (meterBounds.getWidth() * peakPos);

        g.setColour(juce::Colours::white);
        g.fillRect(peakX - 1.0f, meterBounds.getY(), 2.0f, meterBounds.getHeight());
    }
}

void LevelMeterComponent::drawDbScale(juce::Graphics& g, const juce::Rectangle<float>& bounds)
{
    // Draw subtle dB markers at -18, -12, -6, 0 dB
    const float markers[] = { -18.0f, -12.0f, -6.0f, 0.0f };
    const int numMarkers = sizeof(markers) / sizeof(markers[0]);

    g.setColour(juce::Colours::darkgrey.withAlpha(0.5f));

    for (int i = 0; i < numMarkers; ++i)
    {
        float db = markers[i];
        if (db < minDb || db > maxDb)
            continue;

        float pos = dbToPosition(db);

        if (orientation == Orientation::Vertical)
        {
            float y = bounds.getBottom() - (bounds.getHeight() * pos);
            g.drawLine(bounds.getX(), y, bounds.getRight(), y, 1.0f);
        }
        else
        {
            float x = bounds.getX() + (bounds.getWidth() * pos);
            g.drawLine(x, bounds.getY(), x, bounds.getBottom(), 1.0f);
        }
    }
}
