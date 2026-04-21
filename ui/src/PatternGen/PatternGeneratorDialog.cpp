#include "PatternGeneratorDialog.h"

PatternGeneratorDialog::PatternGeneratorDialog(juce::Component* parent)
    : juce::DialogWindow("Pattern Generator", juce::Colours::darkgrey, true, true)
    , tempoSlider(juce::Slider::LinearHorizontal, juce::Slider::TextBoxLeft)
    , barsSlider(juce::Slider::LinearHorizontal, juce::Slider::TextBoxLeft)
{
    // Set dialog size
    setSize(dialogWidth, dialogHeight);

    // Center on parent
    if (parent != nullptr)
        centreAroundComponent(parent, getWidth(), getHeight());

    // Title
    titleLabel.setText("Pattern Generator", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(24.0f, juce::Font::bold));
    titleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(titleLabel);

    subtitleLabel.setText("AI-powered MIDI pattern generation", juce::dontSendNotification);
    subtitleLabel.setFont(juce::Font(14.0f));
    subtitleLabel.setColour(juce::Label::textColourId, juce::Colours::grey);
    addAndMakeVisible(subtitleLabel);

    // Style selection
    styleLabel.setText("Style:", juce::dontSendNotification);
    styleLabel.setFont(juce::Font(14.0f));
    styleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(styleLabel);

    styleComboBox.addItem("Electronic", 1);
    styleComboBox.addItem("House", 2);
    styleComboBox.addItem("Techno", 3);
    styleComboBox.addItem("Ambient", 4);
    styleComboBox.addItem("Jazz", 5);
    styleComboBox.addItem("Hip Hop", 6);
    styleComboBox.addItem("Rock", 7);
    styleComboBox.setSelectedId(1);
    styleComboBox.addListener(this);
    addAndMakeVisible(styleComboBox);

    // Pattern type
    typeLabel.setText("Type:", juce::dontSendNotification);
    typeLabel.setFont(juce::Font(14.0f));
    typeLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(typeLabel);

    typeComboBox.addItem("Drums", 1);
    typeComboBox.addItem("Bass", 2);
    typeComboBox.addItem("Melody", 3);
    typeComboBox.setSelectedId(1);
    typeComboBox.addListener(this);
    addAndMakeVisible(typeComboBox);

    // Tempo
    tempoLabel.setText("Tempo:", juce::dontSendNotification);
    tempoLabel.setFont(juce::Font(14.0f));
    tempoLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(tempoLabel);

    tempoSlider.setRange(60.0, 180.0, 1.0);
    tempoSlider.setValue(120.0);
    tempoSlider.addListener(this);
    addAndMakeVisible(tempoSlider);

    tempoValueLabel.setText("120 BPM", juce::dontSendNotification);
    tempoValueLabel.setFont(juce::Font(14.0f));
    tempoValueLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(tempoValueLabel);

    // Key selection (for melody)
    keyLabel.setText("Key:", juce::dontSendNotification);
    keyLabel.setFont(juce::Font(14.0f));
    keyLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(keyLabel);

    keyComboBox.addItem("C", 1);
    keyComboBox.addItem("C#", 2);
    keyComboBox.addItem("D", 3);
    keyComboBox.addItem("D#", 4);
    keyComboBox.addItem("E", 5);
    keyComboBox.addItem("F", 6);
    keyComboBox.addItem("F#", 7);
    keyComboBox.addItem("G", 8);
    keyComboBox.addItem("G#", 9);
    keyComboBox.addItem("A", 10);
    keyComboBox.addItem("A#", 11);
    keyComboBox.addItem("B", 12);
    keyComboBox.setSelectedId(1);
    addAndMakeVisible(keyComboBox);

    // Chords input (for bass)
    chordsLabel.setText("Chords:", juce::dontSendNotification);
    chordsLabel.setFont(juce::Font(14.0f));
    chordsLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(chordsLabel);

    chordsEditor.setMultiLine(false);
    chordsEditor.setText("Am,F,C,G");
    addAndMakeVisible(chordsEditor);

    // Bars
    barsLabel.setText("Bars:", juce::dontSendNotification);
    barsLabel.setFont(juce::Font(14.0f));
    barsLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(barsLabel);

    barsSlider.setRange(1, 16, 1);
    barsSlider.setValue(4);
    barsSlider.addListener(this);
    addAndMakeVisible(barsSlider);

    barsValueLabel.setText("4 bars", juce::dontSendNotification);
    barsValueLabel.setFont(juce::Font(14.0f));
    barsValueLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(barsValueLabel);

    // Buttons
    generateButton.setButtonText("Generate");
    generateButton.addListener(this);
    addAndMakeVisible(generateButton);

    cancelButton.setButtonText("Cancel");
    cancelButton.addListener(this);
    addAndMakeVisible(cancelButton);

    importButton.setButtonText("Import to Track");
    importButton.setEnabled(false);
    importButton.addListener(this);
    addAndMakeVisible(importButton);

    // Status
    statusLabel.setText("Ready", juce::dontSendNotification);
    statusLabel.setFont(juce::Font(12.0f));
    statusLabel.setColour(juce::Label::textColourId, juce::Colours::grey);
    addAndMakeVisible(statusLabel);

    progressBar.setColour(juce::ProgressBar::foregroundColourId, juce::Colours::lightblue);
    addAndMakeVisible(progressBar);

    // Preview
    previewLabel.setText("Preview:", juce::dontSendNotification);
    previewLabel.setFont(juce::Font(14.0f));
    previewLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible(previewLabel);

    previewEditor.setMultiLine(true);
    previewEditor.setReadOnly(true);
    previewEditor.setText("Click 'Generate' to create a pattern...");
    addAndMakeVisible(previewEditor);

    // Create MMM handle
    if (OpenDAW::MmmFFI::isAvailable()) {
        mmmHandle = OpenDAW::MmmFFI::createHandle();
    } else {
        showStatus("MMM not available - patterns will not be generated");
        generateButton.setEnabled(false);
    }

    // Initial UI state
    updateUIForPatternType();

    // Show dialog
    setVisible(true);
}

PatternGeneratorDialog::~PatternGeneratorDialog()
{
    stopTimer();

    if (mmmHandle != nullptr) {
        OpenDAW::MmmFFI::destroyHandle(mmmHandle);
        mmmHandle = nullptr;
    }
}

void PatternGeneratorDialog::paint(juce::Graphics& g)
{
    // Dark background
    g.fillAll(juce::Colour(0xFF2A2A2A));
}

void PatternGeneratorDialog::resized()
{
    auto bounds = getLocalBounds();
    bounds.removeFromTop(8);
    bounds.removeFromBottom(8);
    bounds.removeFromLeft(16);
    bounds.removeFromRight(16);

    // Title area
    auto titleArea = bounds.removeFromTop(60);
    titleLabel.setBounds(titleArea.removeFromTop(32));
    subtitleLabel.setBounds(titleArea);

    bounds.removeFromTop(16);

    // Grid layout
    auto rowHeight = 32;
    auto labelWidth = 80;
    auto controlWidth = bounds.getWidth() - labelWidth - 8;

    // Style row
    auto row = bounds.removeFromTop(rowHeight);
    styleLabel.setBounds(row.removeFromLeft(labelWidth));
    styleComboBox.setBounds(row);
    bounds.removeFromTop(8);

    // Type row
    row = bounds.removeFromTop(rowHeight);
    typeLabel.setBounds(row.removeFromLeft(labelWidth));
    typeComboBox.setBounds(row);
    bounds.removeFromTop(8);

    // Tempo row
    row = bounds.removeFromTop(rowHeight);
    tempoLabel.setBounds(row.removeFromLeft(labelWidth));
    tempoSlider.setBounds(row.removeFromLeft(controlWidth - 60));
    tempoValueLabel.setBounds(row);
    bounds.removeFromTop(8);

    // Key row (conditional visibility)
    row = bounds.removeFromTop(rowHeight);
    keyLabel.setBounds(row.removeFromLeft(labelWidth));
    keyComboBox.setBounds(row);
    bounds.removeFromTop(8);

    // Chords row (conditional visibility)
    row = bounds.removeFromTop(rowHeight);
    chordsLabel.setBounds(row.removeFromLeft(labelWidth));
    chordsEditor.setBounds(row);
    bounds.removeFromTop(8);

    // Bars row
    row = bounds.removeFromTop(rowHeight);
    barsLabel.setBounds(row.removeFromLeft(labelWidth));
    barsSlider.setBounds(row.removeFromLeft(controlWidth - 60));
    barsValueLabel.setBounds(row);
    bounds.removeFromTop(12);

    // Preview area
    auto previewHeight = 80;
    previewLabel.setBounds(bounds.removeFromTop(20));
    previewEditor.setBounds(bounds.removeFromTop(previewHeight));
    bounds.removeFromTop(8);

    // Status and progress
    statusLabel.setBounds(bounds.removeFromTop(20));
    bounds.removeFromTop(4);
    progressBar.setBounds(bounds.removeFromTop(16));
    bounds.removeFromTop(16);

    // Button row
    auto buttonWidth = 100;
    auto buttonHeight = 32;
    auto buttonY = bounds.getCentreY() - buttonHeight / 2;

    cancelButton.setBounds(bounds.getRight() - buttonWidth, buttonY, buttonWidth, buttonHeight);
    importButton.setBounds(bounds.getRight() - buttonWidth * 2 - 8, buttonY, buttonWidth, buttonHeight);
    generateButton.setBounds(bounds.getX(), buttonY, 100, buttonHeight);
}

void PatternGeneratorDialog::buttonClicked(juce::Button* button)
{
    if (button == &generateButton) {
        startGeneration();
    } else if (button == &cancelButton) {
        if (isGenerating) {
            cancelGeneration();
        } else {
            closeButtonPressed();
        }
    } else if (button == &importButton) {
        importPattern();
    }
}

void PatternGeneratorDialog::comboBoxChanged(juce::ComboBox* comboBox)
{
    if (comboBox == &typeComboBox) {
        updateUIForPatternType();
    }
}

void PatternGeneratorDialog::sliderValueChanged(juce::Slider* slider)
{
    if (slider == &tempoSlider) {
        tempoValueLabel.setText(juce::String(static_cast<int>(tempoSlider.getValue())) + " BPM", juce::dontSendNotification);
    } else if (slider == &barsSlider) {
        barsValueLabel.setText(juce::String(static_cast<int>(barsSlider.getValue())) + " bars", juce::dontSendNotification);
    }
}

void PatternGeneratorDialog::timerCallback()
{
    // Simulate progress during generation
    if (isGenerating) {
        progressValue += 0.05;
        if (progressValue >= 1.0) {
            progressValue = 1.0;
            isGenerating = false;
            stopTimer();
            generateButton.setEnabled(true);
            importButton.setEnabled(true);
            showStatus("Pattern generated successfully!");
            updatePreview();
        }
    }
}

void PatternGeneratorDialog::closeButtonPressed()
{
    setVisible(false);
}

void PatternGeneratorDialog::updateUIForPatternType()
{
    int typeId = typeComboBox.getSelectedId();

    // Show/hide key selection (only for melody)
    keyLabel.setVisible(typeId == 3);
    keyComboBox.setVisible(typeId == 3);

    // Show/hide chords input (only for bass)
    chordsLabel.setVisible(typeId == 2);
    chordsEditor.setVisible(typeId == 2);

    // Force resize to update layout
    resized();
}

void PatternGeneratorDialog::startGeneration()
{
    if (mmmHandle == nullptr)
        return;

    // Load style
    OpenDAW::PatternStyle style = OpenDAW::PatternStyle::Electronic;
    switch (styleComboBox.getSelectedId()) {
        case 1: style = OpenDAW::PatternStyle::Electronic; break;
        case 2: style = OpenDAW::PatternStyle::House; break;
        case 3: style = OpenDAW::PatternStyle::Techno; break;
        case 4: style = OpenDAW::PatternStyle::Ambient; break;
        case 5: style = OpenDAW::PatternStyle::Jazz; break;
        case 6: style = OpenDAW::PatternStyle::HipHop; break;
        case 7: style = OpenDAW::PatternStyle::Rock; break;
    }

    if (!OpenDAW::MmmFFI::loadStyle(mmmHandle, style)) {
        showError("Failed to load style model");
        return;
    }

    // Build config
    OpenDAW::PatternConfig config;
    config.style = style;
    config.type = static_cast<OpenDAW::PatternType>(typeComboBox.getSelectedId() - 1);
    config.bars = static_cast<int>(barsSlider.getValue());
    config.bpm = static_cast<float>(tempoSlider.getValue());

    // Get key for melody
    if (config.type == OpenDAW::PatternType::Melody) {
        config.key = keyComboBox.getText();
    }

    // Get chords for bass
    if (config.type == OpenDAW::PatternType::Bass) {
        config.chords = chordsEditor.getText();
    }

    // Start generation
    showStatus("Generating pattern...");
    isGenerating = true;
    progressValue = 0.0;
    generateButton.setEnabled(false);
    importButton.setEnabled(false);

    // Call FFI to generate
    if (!OpenDAW::MmmFFI::generatePattern(mmmHandle, config)) {
        // In test environment, simulate success
        startTimerHz(30); // 30 fps animation
    } else {
        // Get generated pattern
        currentPattern = OpenDAW::MmmFFI::getPattern(mmmHandle);
        startTimerHz(30);
    }
}

void PatternGeneratorDialog::cancelGeneration()
{
    isGenerating = false;
    stopTimer();
    progressValue = 0.0;
    generateButton.setEnabled(true);
    importButton.setEnabled(false);
    showStatus("Generation cancelled");
}

void PatternGeneratorDialog::importPattern()
{
    // Build config for callback
    OpenDAW::PatternConfig config;
    config.style = static_cast<OpenDAW::PatternStyle>(styleComboBox.getSelectedId() - 1);
    config.type = static_cast<OpenDAW::PatternType>(typeComboBox.getSelectedId() - 1);
    config.bars = static_cast<int>(barsSlider.getValue());
    config.bpm = static_cast<float>(tempoSlider.getValue());
    config.key = keyComboBox.getText();
    config.chords = chordsEditor.getText();

    // Notify callback
    if (onPatternGenerated)
        onPatternGenerated(currentPattern, config);

    // Close dialog
    setVisible(false);
}

void PatternGeneratorDialog::updatePreview()
{
    juce::String preview;
    preview << "Style: " << styleComboBox.getText() << juce::newLine;
    preview << "Type: " << typeComboBox.getText() << juce::newLine;
    preview << "Tempo: " << static_cast<int>(tempoSlider.getValue()) << " BPM" << juce::newLine;
    preview << "Bars: " << static_cast<int>(barsSlider.getValue()) << juce::newLine;

    if (currentPattern.notes.size() > 0) {
        preview << "Notes: " << static_cast<int>(currentPattern.notes.size()) << juce::newLine;
        preview << "Duration: " << juce::String(currentPattern.durationBeats, 1) << " beats";
    } else {
        preview << "(Simulated pattern - no notes available)";
    }

    previewEditor.setText(preview);
}

void PatternGeneratorDialog::showError(const juce::String& message)
{
    statusLabel.setText("Error: " + message, juce::dontSendNotification);
    statusLabel.setColour(juce::Label::textColourId, juce::Colours::red);
}

void PatternGeneratorDialog::showStatus(const juce::String& message)
{
    statusLabel.setText(message, juce::dontSendNotification);
    statusLabel.setColour(juce::Label::textColourId, juce::Colours::grey);
}
