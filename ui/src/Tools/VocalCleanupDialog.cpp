#include "VocalCleanupDialog.h"

// C FFI declarations
extern "C" {
    typedef struct {
        float silence_threshold_db;
        float silence_min_duration;
        float gap_compress_ratio;
        float crossfade_ms;
        float breath_sensitivity;
    } VocalCleanupSettingsFFI;

    typedef struct {
        int gaps_detected;
        int breaths_detected;
        float original_duration;
        float output_duration;
        float time_removed;
        int success;
    } VocalCleanupResultFFI;

    VocalCleanupSettingsFFI vocal_cleanup_settings_default();
    int vocal_cleanup_is_available();
    int vocal_cleanup_process(const char* input_path, const char* output_path,
                               const VocalCleanupSettingsFFI* settings, VocalCleanupResultFFI* result);
    int vocal_cleanup_preview(const char* input_path, const VocalCleanupSettingsFFI* settings,
                             VocalCleanupResultFFI* result);
}

VocalCleanupDialog::VocalCleanupDialog(EngineBridge& engine)
    : DialogWindow("Vocal Cleanup", juce::Colours::darkgrey, true, true)
{
    contentComponent = std::make_unique<VocalCleanupComponent>(engine, this);
    setContentOwned(contentComponent.get(), true);
    centreWithSize(500, 450);
    setVisible(true);
}

VocalCleanupDialog::~VocalCleanupDialog()
{
}

void VocalCleanupDialog::closeButtonPressed()
{
    setVisible(false);
}

// VocalCleanupComponent implementation

VocalCleanupDialog::VocalCleanupComponent::VocalCleanupComponent(EngineBridge& e, VocalCleanupDialog* d)
    : engine(e), dialog(d)
{
    // Silence threshold slider (-60 to -20 dB)
    silenceThresholdSlider.setRange(-60.0, -20.0, 1.0);
    silenceThresholdSlider.setValue(-40.0);
    silenceThresholdSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    silenceThresholdSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    silenceThresholdSlider.addListener(this);
    addAndMakeVisible(silenceThresholdSlider);

    silenceThresholdLabel.setText("Silence Threshold (dB):", juce::dontSendNotification);
    silenceThresholdLabel.attachToComponent(&silenceThresholdSlider, true);
    addAndMakeVisible(silenceThresholdLabel);

    // Silence min duration slider (0.05 to 1.0 seconds)
    silenceMinDurationSlider.setRange(0.05, 1.0, 0.05);
    silenceMinDurationSlider.setValue(0.2);
    silenceMinDurationSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    silenceMinDurationSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    silenceMinDurationSlider.addListener(this);
    addAndMakeVisible(silenceMinDurationSlider);

    silenceMinDurationLabel.setText("Min Silence Duration (s):", juce::dontSendNotification);
    silenceMinDurationLabel.attachToComponent(&silenceMinDurationSlider, true);
    addAndMakeVisible(silenceMinDurationLabel);

    // Gap compression ratio slider (0.0 to 1.0)
    gapCompressRatioSlider.setRange(0.0, 1.0, 0.05);
    gapCompressRatioSlider.setValue(0.3);
    gapCompressRatioSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    gapCompressRatioSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    gapCompressRatioSlider.addListener(this);
    addAndMakeVisible(gapCompressRatioSlider);

    gapCompressRatioLabel.setText("Gap Compression (0=full, 1=none):", juce::dontSendNotification);
    gapCompressRatioLabel.attachToComponent(&gapCompressRatioSlider, true);
    addAndMakeVisible(gapCompressRatioLabel);

    // Crossfade slider (0 to 50 ms)
    crossfadeMsSlider.setRange(0.0, 50.0, 1.0);
    crossfadeMsSlider.setValue(10.0);
    crossfadeMsSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    crossfadeMsSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    crossfadeMsSlider.addListener(this);
    addAndMakeVisible(crossfadeMsSlider);

    crossfadeMsLabel.setText("Crossfade (ms):", juce::dontSendNotification);
    crossfadeMsLabel.attachToComponent(&crossfadeMsSlider, true);
    addAndMakeVisible(crossfadeMsLabel);

    // Breath sensitivity slider (0.0 to 1.0)
    breathSensitivitySlider.setRange(0.0, 1.0, 0.05);
    breathSensitivitySlider.setValue(0.5);
    breathSensitivitySlider.setSliderStyle(juce::Slider::LinearHorizontal);
    breathSensitivitySlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    breathSensitivitySlider.addListener(this);
    addAndMakeVisible(breathSensitivitySlider);

    breathSensitivityLabel.setText("Breath Sensitivity:", juce::dontSendNotification);
    breathSensitivityLabel.attachToComponent(&breathSensitivitySlider, true);
    addAndMakeVisible(breathSensitivityLabel);

    // Buttons
    browseButton.setButtonText("Browse...");
    browseButton.addListener(this);
    addAndMakeVisible(browseButton);

    previewButton.setButtonText("Preview");
    previewButton.addListener(this);
    addAndMakeVisible(previewButton);

    processButton.setButtonText("Process");
    processButton.setColour(juce::TextButton::buttonColourId, juce::Colours::green);
    processButton.addListener(this);
    addAndMakeVisible(processButton);

    closeButton.setButtonText("Close");
    closeButton.addListener(this);
    addAndMakeVisible(closeButton);

    // File path label
    filePathLabel.setText("No file selected", juce::dontSendNotification);
    addAndMakeVisible(filePathLabel);

    // Status label
    statusLabel.setText("Ready", juce::dontSendNotification);
    addAndMakeVisible(statusLabel);

    // Check availability
    if (vocal_cleanup_is_available() == 0) {
        statusLabel.setText("Vocal cleanup not available (Python bridge not found)", juce::dontSendNotification);
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::red);
        previewButton.setEnabled(false);
        processButton.setEnabled(false);
    }
}

VocalCleanupDialog::VocalCleanupComponent::~VocalCleanupComponent()
{
}

void VocalCleanupDialog::VocalCleanupComponent::paint(juce::Graphics& g)
{
    g.fillAll(getLookAndFeel().findColour(juce::ResizableWindow::backgroundColourId));
}

void VocalCleanupDialog::VocalCleanupComponent::resized()
{
    auto area = getLocalBounds().reduced(20);

    // File selection at top
    auto fileArea = area.removeFromTop(30);
    browseButton.setBounds(fileArea.removeFromRight(100));
    fileArea.removeFromRight(10);
    filePathLabel.setBounds(fileArea);

    area.removeFromTop(20); // Spacing

    // Sliders
    auto sliderHeight = 30;
    silenceThresholdSlider.setBounds(area.removeFromTop(sliderHeight));
    area.removeFromTop(10);
    silenceMinDurationSlider.setBounds(area.removeFromTop(sliderHeight));
    area.removeFromTop(10);
    gapCompressRatioSlider.setBounds(area.removeFromTop(sliderHeight));
    area.removeFromTop(10);
    crossfadeMsSlider.setBounds(area.removeFromTop(sliderHeight));
    area.removeFromTop(10);
    breathSensitivitySlider.setBounds(area.removeFromTop(sliderHeight));

    area.removeFromTop(20); // Spacing

    // Status
    statusLabel.setBounds(area.removeFromTop(30));

    area.removeFromTop(20); // Spacing

    // Buttons at bottom
    auto buttonArea = area.removeFromTop(40);
    previewButton.setBounds(buttonArea.removeFromLeft(100));
    buttonArea.removeFromLeft(10);
    processButton.setBounds(buttonArea.removeFromLeft(100));
    buttonArea.removeFromLeft(10);
    closeButton.setBounds(buttonArea.removeFromRight(100));
}

void VocalCleanupDialog::VocalCleanupComponent::buttonClicked(juce::Button* button)
{
    if (button == &browseButton) {
        juce::FileChooser chooser("Select audio file...",
                                  juce::File(),
                                  "*.wav;*.mp3;*.flac;*.aiff");
        // JUCE 7.0.9: Use launchAsync instead of browseForFileToOpen
        chooser.launchAsync(juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles,
            [this](const juce::FileChooser& fc) {
                if (fc.getResults().size() > 0) {
                    auto file = fc.getResult();
                    currentFilePath = file.getFullPathName();
                    filePathLabel.setText(file.getFileName(), juce::dontSendNotification);
                    statusLabel.setText("File selected: " + file.getFileName(), juce::dontSendNotification);
                    statusLabel.setColour(juce::Label::textColourId, juce::Colours::white);
                }
            });
    }
    else if (button == &previewButton) {
        previewVocalCleanup();
    }
    else if (button == &processButton) {
        processVocalCleanup();
    }
    else if (button == &closeButton) {
        if (dialog != nullptr) {
            dialog->closeButtonPressed();
        }
    }
}

void VocalCleanupDialog::VocalCleanupComponent::sliderValueChanged(juce::Slider* slider)
{
    // Sliders update automatically - could add real-time preview here
}

void VocalCleanupDialog::VocalCleanupComponent::previewVocalCleanup()
{
    if (currentFilePath.isEmpty()) {
        statusLabel.setText("Please select a file first", juce::dontSendNotification);
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::orange);
        return;
    }

    statusLabel.setText("Analyzing...", juce::dontSendNotification);
    statusLabel.setColour(juce::Label::textColourId, juce::Colours::yellow);

    // Build settings
    VocalCleanupSettingsFFI settings;
    settings.silence_threshold_db = (float)silenceThresholdSlider.getValue();
    settings.silence_min_duration = (float)silenceMinDurationSlider.getValue();
    settings.gap_compress_ratio = (float)gapCompressRatioSlider.getValue();
    settings.crossfade_ms = (float)crossfadeMsSlider.getValue();
    settings.breath_sensitivity = (float)breathSensitivitySlider.getValue();

    // Call FFI
    VocalCleanupResultFFI result;
    int ret = vocal_cleanup_preview(currentFilePath.toRawUTF8(), &settings, &result);

    if (ret == 0 && result.success) {
        juce::String msg = juce::String("Preview: Found ") +
                          juce::String(result.gaps_detected) + " gaps, " +
                          juce::String(result.breaths_detected) + " breaths. " +
                          "Est. time removed: " +
                          juce::String(result.time_removed, 2) + "s";
        statusLabel.setText(msg, juce::dontSendNotification);
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::green);
    } else {
        statusLabel.setText("Preview failed (error code: " + juce::String(ret) + ")", juce::dontSendNotification);
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::red);
    }
}

void VocalCleanupDialog::VocalCleanupComponent::processVocalCleanup()
{
    if (currentFilePath.isEmpty()) {
        statusLabel.setText("Please select a file first", juce::dontSendNotification);
        statusLabel.setColour(juce::Label::textColourId, juce::Colours::orange);
        return;
    }

    // Ask for output file
    juce::File inputFile(currentFilePath);
    juce::String suggestedName = inputFile.getFileNameWithoutExtension() + "_cleaned.wav";
    juce::FileChooser chooser("Save cleaned vocal...",
                              inputFile.getParentDirectory().getChildFile(suggestedName),
                              "*.wav");
    // JUCE 7.0.9: Use launchAsync instead of browseForFileToSave
    chooser.launchAsync(juce::FileBrowserComponent::saveMode | juce::FileBrowserComponent::canSelectFiles,
        [this, inputFile](const juce::FileChooser& fc) {
            if (fc.getResults().size() > 0) {
                juce::String outputPath = fc.getResult().getFullPathName();

                statusLabel.setText("Processing...", juce::dontSendNotification);
                statusLabel.setColour(juce::Label::textColourId, juce::Colours::yellow);

                // Build settings
                VocalCleanupSettingsFFI settings;
                settings.silence_threshold_db = (float)silenceThresholdSlider.getValue();
                settings.silence_min_duration = (float)silenceMinDurationSlider.getValue();
                settings.gap_compress_ratio = (float)gapCompressRatioSlider.getValue();
                settings.crossfade_ms = (float)crossfadeMsSlider.getValue();
                settings.breath_sensitivity = (float)breathSensitivitySlider.getValue();
            }
        });
}
