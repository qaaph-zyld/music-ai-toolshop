#include "RecordingPanel.h"

RecordingPanel::RecordingPanel()
{
    // Record button setup
    recordButton.setButtonText("Record");
    recordButton.setColour(juce::TextButton::buttonColourId, juce::Colours::darkred);
    recordButton.setColour(juce::TextButton::textColourOnId, juce::Colours::white);
    recordButton.onClick = [this] { onRecordButtonClicked(); };
    addAndMakeVisible(recordButton);

    // Device selector
    deviceLabel.setText("MIDI Device:", juce::dontSendNotification);
    deviceLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(deviceLabel);
    
    deviceSelector.setTextWhenNoChoicesAvailable("No MIDI Devices");
    deviceSelector.onChange = [this] { onDeviceChanged(); };
    addAndMakeVisible(deviceSelector);

    // Quantization selector
    quantizeLabel.setText("Quantize:", juce::dontSendNotification);
    quantizeLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(quantizeLabel);
    
    quantizeSelector.addItem("Off", 1);
    quantizeSelector.addItem("1/4 Note", 2);
    quantizeSelector.addItem("1/8 Note", 3);
    quantizeSelector.addItem("1/16 Note", 4);
    quantizeSelector.addItem("1/32 Note", 5);
    quantizeSelector.setSelectedId(4, juce::dontSendNotification); // Default to 1/16
    quantizeSelector.onChange = [this] { onQuantizeChanged(); };
    addAndMakeVisible(quantizeSelector);

    // Status label
    statusLabel.setText("Ready", juce::dontSendNotification);
    statusLabel.setJustificationType(juce::Justification::centred);
    statusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    addAndMakeVisible(statusLabel);

    // Target label (shows recording target)
    targetLabel.setText("Target: Track 1, Scene 1", juce::dontSendNotification);
    targetLabel.setJustificationType(juce::Justification::left);
    targetLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    addAndMakeVisible(targetLabel);

    // Timer label (shows recording position)
    timerLabel.setText("1.1.1", juce::dontSendNotification);
    timerLabel.setJustificationType(juce::Justification::centred);
    timerLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    timerLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    addAndMakeVisible(timerLabel);

    // Start timer for UI updates
    startTimerHz(30); // 30 fps

    // Initial device refresh
    refreshDevices();
}

RecordingPanel::~RecordingPanel()
{
    stopTimer();
}

void RecordingPanel::paint(juce::Graphics& g)
{
    // Dark background
    g.fillAll(juce::Colour(0x20, 0x20, 0x20));
    
    // Border
    g.setColour(juce::Colours::darkgrey);
    g.drawRect(getLocalBounds(), 1);
    
    // Recording indicator when active
    if (isRecording)
    {
        auto bounds = getLocalBounds().reduced(4);
        g.setColour(juce::Colours::red.withAlpha(0.3f));
        g.drawRoundedRectangle(bounds.toFloat(), 4.0f, 2.0f);
    }
}

void RecordingPanel::resized()
{
    auto area = getLocalBounds().reduced(10);
    
    // Top row: Status and Timer
    auto topRow = area.removeFromTop(25);
    statusLabel.setBounds(topRow.removeFromLeft(topRow.getWidth() / 2));
    timerLabel.setBounds(topRow);
    
    area.removeFromTop(5); // Spacing

    // Target row
    auto targetRow = area.removeFromTop(20);
    targetLabel.setBounds(targetRow);
    
    area.removeFromTop(10); // Spacing
    
    // Record button (large, centered)
    auto buttonRow = area.removeFromTop(40);
    recordButton.setBounds(buttonRow.withSizeKeepingCentre(100, 35));
    
    area.removeFromTop(15); // Spacing
    
    // Device selector
    auto deviceRow = area.removeFromTop(25);
    deviceLabel.setBounds(deviceRow.removeFromLeft(80));
    deviceSelector.setBounds(deviceRow);
    
    area.removeFromTop(10); // Spacing
    
    // Quantization selector
    auto quantRow = area.removeFromTop(25);
    quantizeLabel.setBounds(quantRow.removeFromLeft(80));
    quantizeSelector.setBounds(quantRow);
}

void RecordingPanel::timerCallback()
{
    updateTimer();
    
    // Check if recording was stopped externally
    auto& bridge = EngineBridge::getInstance();
    bool bridgeRecording = bridge.isMidiRecording();
    
    if (isRecording != bridgeRecording)
    {
        isRecording = bridgeRecording;
        updateStatus();
        repaint();
    }
}

void RecordingPanel::refreshDevices()
{
    deviceSelector.clear();
    
    auto& bridge = EngineBridge::getInstance();
    auto devices = bridge.getMidiInputDevices();
    
    if (devices.empty())
    {
        deviceSelector.setTextWhenNoChoicesAvailable("No MIDI Devices");
        selectedDeviceIndex = -1;
    }
    else
    {
        for (int i = 0; i < devices.size(); ++i)
        {
            deviceSelector.addItem(devices[i].name, i + 1);
        }
        deviceSelector.setSelectedId(1, juce::sendNotification);
        selectedDeviceIndex = 0;
    }
}

void RecordingPanel::onRecordButtonClicked()
{
    auto& bridge = EngineBridge::getInstance();
    
    if (!isRecording)
    {
        // Start recording
        double currentBeat = bridge.getCurrentBeat();
        recordingStartBeat = currentBeat;
        
        bridge.startMidiRecording(targetTrack, targetScene, static_cast<float>(currentBeat));
        isRecording = true;
        
        recordButton.setButtonText("Stop");
        recordButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red);
    }
    else
    {
        // Stop recording
        auto notes = bridge.stopMidiRecording();
        isRecording = false;
        
        recordButton.setButtonText("Record");
        recordButton.setColour(juce::TextButton::buttonColourId, juce::Colours::darkred);
        
        // Notify parent component to create clip - Phase 7.1
        if (onRecordingComplete)
        {
            juce::Array<EngineBridge::RecordedNote> notesArray(notes.data(), notes.size());
            onRecordingComplete(targetTrack, targetScene, notesArray);
        }
        
        juce::String status = "Recorded " + juce::String(notes.size()) + " notes";
        statusLabel.setText(status, juce::dontSendNotification);
    }
    
    updateStatus();
    repaint();
}

void RecordingPanel::onDeviceChanged()
{
    selectedDeviceIndex = deviceSelector.getSelectedId() - 1;
    
    auto& bridge = EngineBridge::getInstance();
    auto devices = bridge.getMidiInputDevices();
    
    if (selectedDeviceIndex >= 0 && selectedDeviceIndex < devices.size())
    {
        bridge.selectMidiInputDevice(devices[selectedDeviceIndex].id);
    }
}

void RecordingPanel::onQuantizeChanged()
{
    auto& bridge = EngineBridge::getInstance();
    
    // Map selector IDs to grid divisions
    float gridDivision = 0.25f; // Default 1/16
    switch (quantizeSelector.getSelectedId())
    {
        case 1: gridDivision = 0.0f; break;  // Off
        case 2: gridDivision = 1.0f; break;  // 1/4
        case 3: gridDivision = 0.5f; break; // 1/8
        case 4: gridDivision = 0.25f; break; // 1/16
        case 5: gridDivision = 0.125f; break; // 1/32
    }
    
    float strength = (quantizeSelector.getSelectedId() == 1) ? 0.0f : 1.0f;
    bridge.setQuantization(gridDivision, strength);
}

void RecordingPanel::updateStatus()
{
    if (isRecording)
    {
        statusLabel.setText("Recording...", juce::dontSendNotification);
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::red);
    }
    else
    {
        if (statusLabel.getText() == "Recording...")
        {
            statusLabel.setText("Ready", juce::dontSendNotification);
        }
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    }
}

void RecordingPanel::updateTimer()
{
    auto& bridge = EngineBridge::getInstance();
    double currentBeat = bridge.getCurrentBeat();
    
    // Convert beats to bars.beats.sixteenths (assuming 4/4 time)
    int bars = static_cast<int>(currentBeat / 4.0) + 1;
    int beats = static_cast<int>(currentBeat) % 4 + 1;
    int sixteenths = static_cast<int>((currentBeat - static_cast<int>(currentBeat)) * 4.0) + 1;
    
    juce::String timeStr = juce::String(bars) + "." + 
                           juce::String(beats) + "." + 
                           juce::String(sixteenths);
    timerLabel.setText(timeStr, juce::dontSendNotification);
}

void RecordingPanel::updateTargetLabel()
{
    juce::String text = "Target: Track " + juce::String(targetTrack + 1) + 
                        ", Scene " + juce::String(targetScene + 1);
    targetLabel.setText(text, juce::dontSendNotification);
}
