#include "PunchInOutPanel.h"

PunchInOutPanel::PunchInOutPanel()
{
    setupUI();
    setSize(280, 220);
}

PunchInOutPanel::~PunchInOutPanel() = default;

void PunchInOutPanel::setupUI()
{
    // Title
    titleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    titleLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(titleLabel);
    
    // Enable toggle
    enableButton.setToggleState(punchEnabled, juce::dontSendNotification);
    enableButton.onClick = [this] {
        punchEnabled = enableButton.getToggleState();
        if (onEnabledChanged)
            onEnabledChanged(punchEnabled);
        updateUIState();
    };
    addAndMakeVisible(enableButton);
    
    // Punch In
    punchInLabel.setJustificationType(juce::Justification::right);
    addAndMakeVisible(punchInLabel);
    
    punchInEditor.setText(formatBeatTime(currentPunchIn), juce::dontSendNotification);
    punchInEditor.setJustification(juce::Justification::centred);
    punchInEditor.onReturnKey = [this] {
        currentPunchIn = parseBeatTime(punchInEditor.getText());
        punchInEditor.setText(formatBeatTime(currentPunchIn), juce::dontSendNotification);
        if (onPunchInChanged)
            onPunchInChanged(currentPunchIn);
    };
    punchInEditor.onFocusLost = punchInEditor.onReturnKey;
    addAndMakeVisible(punchInEditor);
    
    // Punch Out
    punchOutLabel.setJustificationType(juce::Justification::right);
    addAndMakeVisible(punchOutLabel);
    
    punchOutEditor.setText(formatBeatTime(currentPunchOut), juce::dontSendNotification);
    punchOutEditor.setJustification(juce::Justification::centred);
    punchOutEditor.onReturnKey = [this] {
        double val = parseBeatTime(punchOutEditor.getText());
        currentPunchOut = val > 0 ? val : -1.0;
        punchOutEditor.setText(formatBeatTime(currentPunchOut), juce::dontSendNotification);
        if (onPunchOutChanged)
            onPunchOutChanged(currentPunchOut);
    };
    punchOutEditor.onFocusLost = punchOutEditor.onReturnKey;
    addAndMakeVisible(punchOutEditor);
    
    // Clear Out button
    clearOutButton.onClick = [this] {
        currentPunchOut = -1.0;
        punchOutEditor.setText("---", juce::dontSendNotification);
        if (onPunchOutChanged)
            onPunchOutChanged(-1.0);
    };
    addAndMakeVisible(clearOutButton);
    
    // Pre-roll
    preRollLabel.setJustificationType(juce::Justification::right);
    addAndMakeVisible(preRollLabel);
    
    preRollCombo.addItem("Off", 1);
    preRollCombo.addItem("1 bar", 2);
    preRollCombo.addItem("2 bars", 3);
    preRollCombo.addItem("4 bars", 4);
    preRollCombo.setSelectedId(3, juce::dontSendNotification);  // 2 bars default
    preRollCombo.onChange = [this] {
        switch (preRollCombo.getSelectedId())
        {
            case 1: currentPreRoll = 0.0; break;
            case 2: currentPreRoll = 4.0; break;  // 1 bar = 4 beats
            case 3: currentPreRoll = 8.0; break;  // 2 bars = 8 beats
            case 4: currentPreRoll = 16.0; break; // 4 bars = 16 beats
        }
        if (onPreRollChanged)
            onPreRollChanged(currentPreRoll);
    };
    addAndMakeVisible(preRollCombo);
    
    // Arm button
    armButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4B4B4B));
    armButton.onClick = [this] {
        if (currentState == 0)  // Disarmed
        {
            if (onArmPressed)
                onArmPressed();
        }
        else
        {
            if (onDisarmPressed)
                onDisarmPressed();
        }
    };
    addAndMakeVisible(armButton);
    
    // Status label
    statusLabel.setFont(juce::Font(14.0f, juce::Font::bold));
    statusLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(statusLabel);
    
    // Progress bar (hidden by default)
    progressBar.setColour(juce::ProgressBar::foregroundColourId, juce::Colours::green);
    addChildComponent(progressBar);  // Hidden initially
    
    // Progress label
    progressLabel.setJustificationType(juce::Justification::centred);
    progressLabel.setFont(juce::Font(12.0f));
    addChildComponent(progressLabel);  // Hidden initially
    
    updateUIState();
}

void PunchInOutPanel::paint(juce::Graphics& g)
{
    // Background
    g.fillAll(juce::Colour(0xFF2B2B2B));
    
    // Border with state color
    g.setColour(getStateColor());
    g.drawRect(getLocalBounds(), 2);
}

void PunchInOutPanel::resized()
{
    auto bounds = getLocalBounds().reduced(8);
    
    // Title at top
    titleLabel.setBounds(bounds.removeFromTop(24));
    bounds.removeFromTop(4);
    
    // Enable checkbox
    enableButton.setBounds(bounds.removeFromTop(24));
    bounds.removeFromTop(8);
    
    // Grid layout for controls
    auto rowHeight = 28;
    auto labelWidth = 70;
    auto editorWidth = 80;
    auto buttonWidth = 60;
    
    // Punch In row
    auto row1 = bounds.removeFromTop(rowHeight);
    punchInLabel.setBounds(row1.removeFromLeft(labelWidth));
    row1.removeFromLeft(4);
    punchInEditor.setBounds(row1.removeFromLeft(editorWidth));
    bounds.removeFromTop(4);
    
    // Punch Out row
    auto row2 = bounds.removeFromTop(rowHeight);
    punchOutLabel.setBounds(row2.removeFromLeft(labelWidth));
    row2.removeFromLeft(4);
    punchOutEditor.setBounds(row2.removeFromLeft(editorWidth));
    row2.removeFromLeft(4);
    clearOutButton.setBounds(row2.removeFromLeft(buttonWidth));
    bounds.removeFromTop(4);
    
    // Pre-roll row
    auto row3 = bounds.removeFromTop(rowHeight);
    preRollLabel.setBounds(row3.removeFromLeft(labelWidth));
    row3.removeFromLeft(4);
    preRollCombo.setBounds(row3.removeFromLeft(editorWidth + buttonWidth + 4));
    bounds.removeFromTop(8);
    
    // Arm button and status
    auto bottomRow = bounds.removeFromTop(36);
    armButton.setBounds(bottomRow.removeFromLeft(100));
    bottomRow.removeFromLeft(8);
    statusLabel.setBounds(bottomRow);
    
    // Progress bar (positioned at bottom when visible)
    if (progressBar.isVisible())
    {
        auto progressRow = bounds.removeFromTop(20);
        progressLabel.setBounds(progressRow.removeFromLeft(100));
        progressRow.removeFromLeft(4);
        progressBar.setBounds(progressRow);
    }
}

void PunchInOutPanel::setPunchIn(double beats)
{
    currentPunchIn = beats;
    punchInEditor.setText(formatBeatTime(beats), juce::dontSendNotification);
}

void PunchInOutPanel::setPunchOut(double beats)
{
    currentPunchOut = beats;
    if (beats < 0)
        punchOutEditor.setText("---", juce::dontSendNotification);
    else
        punchOutEditor.setText(formatBeatTime(beats), juce::dontSendNotification);
}

void PunchInOutPanel::setPreRoll(double beats)
{
    currentPreRoll = beats;
    
    // Update combo selection
    if (beats <= 0)
        preRollCombo.setSelectedId(1, juce::dontSendNotification);
    else if (beats <= 4)
        preRollCombo.setSelectedId(2, juce::dontSendNotification);
    else if (beats <= 8)
        preRollCombo.setSelectedId(3, juce::dontSendNotification);
    else
        preRollCombo.setSelectedId(4, juce::dontSendNotification);
}

void PunchInOutPanel::setPunchState(int state)
{
    currentState = state;
    updateUIState();
}

void PunchInOutPanel::setEnabled(bool enabled)
{
    punchEnabled = enabled;
    enableButton.setToggleState(enabled, juce::dontSendNotification);
    updateUIState();
}

void PunchInOutPanel::updateUIState()
{
    // Update arm button text and color
    if (currentState == 0)
    {
        armButton.setButtonText("Arm");
        armButton.setColour(juce::TextButton::buttonColourId, juce::Colour(0xFF4B4B4B));
    }
    else
    {
        armButton.setButtonText("Disarm");
        armButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red.darker(0.3f));
    }
    
    // Update status label
    switch (currentState)
    {
        case 0: statusLabel.setText("Disarmed", juce::dontSendNotification); break;
        case 1: statusLabel.setText("Armed", juce::dontSendNotification); break;
        case 2: 
            statusLabel.setText("Pre-Roll", juce::dontSendNotification);
            progressLabel.setText("Pre-roll:", juce::dontSendNotification);
            break;
        case 3: 
            statusLabel.setText("Recording", juce::dontSendNotification);
            progressLabel.setText("Recording...", juce::dontSendNotification);
            break;
        case 4: statusLabel.setText("Completed", juce::dontSendNotification); break;
        default: statusLabel.setText("Unknown", juce::dontSendNotification);
    }
    
    // Show/hide progress bar during pre-roll and recording
    bool showProgress = (currentState == 2 || currentState == 3);
    progressBar.setVisible(showProgress);
    progressLabel.setVisible(showProgress);
    
    // Enable/disable editors based on state
    bool editable = (currentState == 0 || currentState == 4);
    punchInEditor.setEnabled(editable && punchEnabled);
    punchOutEditor.setEnabled(editable && punchEnabled);
    clearOutButton.setEnabled(editable && punchEnabled);
    preRollCombo.setEnabled(editable && punchEnabled);
    
    // Status label color
    statusLabel.setColour(juce::Label::textColourId, getStateColor());
    
    repaint();
}

juce::String PunchInOutPanel::formatBeatTime(double beats)
{
    if (beats < 0)
        return "---";
    
    // Format as bars.beats (e.g., 2.1 = bar 2, beat 1)
    int beatsPerBar = 4;
    int totalBeats = static_cast<int>(beats);
    int bars = totalBeats / beatsPerBar;
    int beat = totalBeats % beatsPerBar;
    double fraction = beats - totalBeats;
    
    if (fraction > 0.001)
        return juce::String(bars + 1) + "." + juce::String(beat + 1) + juce::String::formatted(".%02d", static_cast<int>(fraction * 100));
    else
        return juce::String(bars + 1) + "." + juce::String(beat + 1);
}

double PunchInOutPanel::parseBeatTime(const juce::String& text)
{
    // Parse bars.beats format
    auto parts = text.trim().split('.');
    if (parts.size() >= 2)
    {
        int bars = parts[0].getIntValue() - 1;  // Convert to 0-indexed
        int beats = parts[1].getIntValue() - 1;
        double fraction = 0.0;
        
        if (parts.size() >= 3)
            fraction = parts[2].getDoubleValue() / 100.0;
        
        return bars * 4.0 + beats + fraction;  // 4 beats per bar
    }
    
    // Try parsing as raw beats
    return text.getDoubleValue();
}

juce::Colour PunchInOutPanel::getStateColor() const
{
    if (!punchEnabled)
        return juce::Colours::grey;
    
    switch (currentState)
    {
        case 0: return juce::Colour(0xFF888888);  // Disarmed - grey
        case 1: return juce::Colour(0xFFFFAA00);  // Armed - orange
        case 2: return juce::Colour(0xFFFFDD00);  // Pre-roll - yellow
        case 3: return juce::Colours::red;        // Recording - red
        case 4: return juce::Colours::green;        // Completed - green
        default: return juce::Colours::grey;
    }
}
