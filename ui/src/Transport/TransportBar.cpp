#include "TransportBar.h"
#include "../Engine/EngineBridge.h"

TransportBar::TransportBar()
{
    setupControls();
    startTimerHz(30); // Update time display at 30fps
    setSize(1200, 60);
}

TransportBar::~TransportBar()
{
    stopTimer();
}

void TransportBar::setupControls()
{
    // Play button
    playButton.setTooltip("Play (Space)");
    playButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4B4B4B));
    playButton.onClick = [this] {
        auto& engine = EngineBridge::getInstance();
        engine.play();
        if (onPlay) onPlay();
    };
    addAndMakeVisible(playButton);

    // Stop button
    stopButton.setTooltip("Stop");
    stopButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4B4B4B));
    stopButton.onClick = [this] {
        auto& engine = EngineBridge::getInstance();
        engine.stop();
        if (onStop) onStop();
    };
    addAndMakeVisible(stopButton);

    // Record button
    recordButton.setTooltip("Record");
    recordButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4B4B4B));
    recordButton.onClick = [this] {
        auto& engine = EngineBridge::getInstance();
        engine.record();
        if (onRecord) onRecord();
    };
    addAndMakeVisible(recordButton);

    // Rewind button
    rewindButton.setTooltip("Rewind to beginning");
    rewindButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4B4B4B));
    rewindButton.onClick = [this] {
        auto& engine = EngineBridge::getInstance();
        engine.setPosition(0.0);
        if (onRewind) onRewind();
    };
    addAndMakeVisible(rewindButton);

    // Tempo slider
    tempoSlider.setRange(20.0, 999.0, 0.1);
    tempoSlider.setValue(currentTempo, juce::dontSendNotification);
    tempoSlider.setTooltip("Tempo (BPM)");
    tempoSlider.onValueChange = [this] {
        currentTempo = tempoSlider.getValue();
        auto& engine = EngineBridge::getInstance();
        engine.setTempo(currentTempo);
        if (onTempoChange) onTempoChange(currentTempo);
    };
    addAndMakeVisible(tempoSlider);

    // Tempo label
    tempoLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(tempoLabel);

    // BPM label
    bpmLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(bpmLabel);

    // Time display (large)
    timeDisplay.setFont(juce::Font(24.0f, juce::Font::bold));
    timeDisplay.setJustificationType(juce::Justification::centred);
    timeDisplay.setColour(juce::Label::textColourId, juce::Colours::white);
    timeDisplay.setColour(juce::Label::backgroundColourId, juce::Colour(0xFF1B1B1B));
    addAndMakeVisible(timeDisplay);

    // Metronome toggle
    metronomeButton.setTooltip("Toggle Metronome");
    addAndMakeVisible(metronomeButton);

    updateButtonStates();
    updateTimeDisplay();
}

void TransportBar::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(0xFF2B2B2B));

    // Subtle bottom border
    g.setColour(juce::Colour(0xFF3B3B3B));
    g.drawHorizontalLine(getHeight() - 1, 0, getWidth());
}

void TransportBar::resized()
{
    auto bounds = getLocalBounds().reduced(5, 2);

    // Left side: Transport buttons
    auto transportArea = bounds.removeFromLeft(200);
    rewindButton.setBounds(transportArea.removeFromLeft(40).reduced(2));
    playButton.setBounds(transportArea.removeFromLeft(40).reduced(2));
    stopButton.setBounds(transportArea.removeFromLeft(40).reduced(2));
    recordButton.setBounds(transportArea.removeFromLeft(40).reduced(2));

    // Right side: Tempo controls
    auto tempoArea = bounds.removeFromRight(150);
    tempoLabel.setBounds(tempoArea.removeFromTop(15));
    tempoSlider.setBounds(tempoArea.removeFromTop(30).reduced(2));
    bpmLabel.setBounds(tempoArea);

    // Far right: Metronome
    auto metronomeArea = bounds.removeFromRight(100);
    metronomeButton.setBounds(metronomeArea.reduced(5));

    // Center: Time display
    bounds.reduce(20, 5);
    timeDisplay.setBounds(bounds);
}

void TransportBar::timerCallback()
{
    // Phase 6.8: Poll transport state from EngineBridge
    auto& engine = EngineBridge::getInstance();
    
    // Update play state
    bool enginePlaying = engine.isPlaying();
    if (enginePlaying != isPlaying)
    {
        isPlaying = enginePlaying;
        updateButtonStates();
    }
    
    // Update recording state
    bool engineRecording = engine.isRecording();
    if (engineRecording != isRecording)
    {
        isRecording = engineRecording;
        updateButtonStates();
    }
    
    // Update position from engine (accurate beat position from audio thread)
    double beat = engine.getCurrentBeat();
    if (std::abs(beat - currentPosition) > 0.001)
    {
        currentPosition = beat;
        updateTimeDisplay();
    }
    
    // Update tempo if changed externally
    double tempo = engine.getTempo();
    if (std::abs(tempo - currentTempo) > 0.1)
    {
        currentTempo = tempo;
        tempoSlider.setValue(currentTempo, juce::dontSendNotification);
    }
}

void TransportBar::setPlaying(bool playing)
{
    isPlaying = playing;
    updateButtonStates();
}

void TransportBar::setRecording(bool recording)
{
    isRecording = recording;
    updateButtonStates();
}

void TransportBar::setPosition(double beats)
{
    currentPosition = beats;
    updateTimeDisplay();
}

void TransportBar::setTempo(double bpm)
{
    currentTempo = bpm;
    tempoSlider.setValue(bpm, juce::dontSendNotification);
}

void TransportBar::updateButtonStates()
{
    // Play button: green when playing
    playButton.setColour(juce::TextButton::buttonColourId,
                         isPlaying ? juce::Colours::green.darker(0.3f) : juce::Colour(0xFF4B4B4B));

    // Record button: red when recording
    recordButton.setColour(juce::TextButton::buttonColourId,
                           isRecording ? juce::Colours::red.darker(0.3f) : juce::Colour(0xFF4B4B4B));

    // Stop button: subtle highlight when stopped
    stopButton.setColour(juce::TextButton::buttonColourId,
                         (!isPlaying && !isRecording) ? juce::Colour(0xFF6B6B6B) : juce::Colour(0xFF4B4B4B));
}

void TransportBar::updateTimeDisplay()
{
    timeDisplay.setText(formatTimeDisplay(currentPosition), juce::dontSendNotification);
}

juce::String TransportBar::formatTimeDisplay(double beats)
{
    // Convert beats to bars.beats.sixteenths (assuming 4/4 time)
    int beatsPerBar = 4;
    int sixteenthsPerBeat = 4;

    int totalSixteenths = static_cast<int>(beats * sixteenthsPerBeat);
    int sixteenths = totalSixteenths % sixteenthsPerBeat;
    int totalBeats = totalSixteenths / sixteenthsPerBeat;
    int beat = totalBeats % beatsPerBar;
    int bar = totalBeats / beatsPerBar;

    return juce::String(bar + 1) + "." +
           juce::String(beat + 1) + "." +
           juce::String(sixteenths + 1);
}
