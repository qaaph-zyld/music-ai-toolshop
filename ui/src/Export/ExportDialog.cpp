#include "ExportDialog.h"
#include "ExportFFI.h"

using namespace OpenDAW;

ExportDialog::ExportDialog(juce::Component* parent)
    : juce::DialogWindow("Export Audio", juce::Colours::darkgrey, true, false),
      juce::Thread("ExportThread")
{
    // Set dialog size
    setSize(dialogWidth, dialogHeight);
    centreAroundComponent(parent, getWidth(), getHeight());

    // Title
    titleLabel.setText("Export Project to Audio", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    titleLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(&titleLabel);

    // Format selection
    formatLabel.setText("Format:", juce::dontSendNotification);
    addAndMakeVisible(&formatLabel);

    formatComboBox.addItem("WAV", 1);
    formatComboBox.addItem("MP3", 2);
    formatComboBox.setSelectedId(1);
    formatComboBox.addListener(this);
    addAndMakeVisible(&formatComboBox);

    // Sample rate
    sampleRateLabel.setText("Sample Rate:", juce::dontSendNotification);
    addAndMakeVisible(&sampleRateLabel);

    sampleRateComboBox.addItem("44100 Hz", 1);
    sampleRateComboBox.addItem("48000 Hz", 2);
    sampleRateComboBox.addItem("96000 Hz", 3);
    sampleRateComboBox.setSelectedId(2);
    addAndMakeVisible(&sampleRateComboBox);

    // Bit depth
    bitDepthLabel.setText("Bit Depth:", juce::dontSendNotification);
    addAndMakeVisible(&bitDepthLabel);

    bitDepthComboBox.addItem("16-bit", 1);
    bitDepthComboBox.addItem("24-bit", 2);
    bitDepthComboBox.addItem("32-bit float", 3);
    bitDepthComboBox.setSelectedId(2);
    addAndMakeVisible(&bitDepthComboBox);

    // Stem export toggle
    stemExportButton.setButtonText("Export stems (individual tracks)");
    stemExportButton.setToggleState(false, juce::dontSendNotification);
    addAndMakeVisible(&stemExportButton);

    // File path
    filePathLabel.setText("Output: (not selected)", juce::dontSendNotification);
    filePathLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    addAndMakeVisible(&filePathLabel);

    browseButton.setButtonText("Browse...");
    browseButton.addListener(this);
    addAndMakeVisible(&browseButton);

    // Export button
    exportButton.setButtonText("Export");
    exportButton.addListener(this);
    exportButton.setEnabled(false);
    addAndMakeVisible(&exportButton);

    // Cancel button
    cancelButton.setButtonText("Cancel");
    cancelButton.addListener(this);
    addAndMakeVisible(&cancelButton);

    // Progress bar - JUCE 7 uses constructor with progress reference
    addAndMakeVisible(&progressBar);

    // Status label
    statusLabel.setText("Ready", juce::dontSendNotification);
    statusLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(&statusLabel);
}

ExportDialog::~ExportDialog()
{
    signalThreadShouldExit();
    waitForThreadToExit(1000);
    stopTimer();
    
    // Cleanup export handle if still active
    if (exportHandle) {
        ExportFFI::cancel(exportHandle);
        ExportFFI::destroy(exportHandle);
        exportHandle = nullptr;
    }
}

void ExportDialog::paint(juce::Graphics& g)
{
    g.fillAll(getLookAndFeel().findColour(juce::ResizableWindow::backgroundColourId));
}

void ExportDialog::resized()
{
    auto area = getLocalBounds().reduced(20);

    // Title
    titleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(15);

    // Format row
    auto formatRow = area.removeFromTop(25);
    formatLabel.setBounds(formatRow.removeFromLeft(100));
    formatComboBox.setBounds(formatRow.removeFromLeft(150));
    area.removeFromTop(10);

    // Sample rate row
    auto rateRow = area.removeFromTop(25);
    sampleRateLabel.setBounds(rateRow.removeFromLeft(100));
    sampleRateComboBox.setBounds(rateRow.removeFromLeft(150));
    area.removeFromTop(10);

    // Bit depth row
    auto depthRow = area.removeFromTop(25);
    bitDepthLabel.setBounds(depthRow.removeFromLeft(100));
    bitDepthComboBox.setBounds(depthRow.removeFromLeft(150));
    area.removeFromTop(15);

    // Stem export
    stemExportButton.setBounds(area.removeFromTop(25));
    area.removeFromTop(15);

    // File path row
    auto fileRow = area.removeFromTop(25);
    filePathLabel.setBounds(fileRow.removeFromLeft(280));
    browseButton.setBounds(fileRow.removeFromRight(100));
    area.removeFromTop(20);

    // Progress bar
    progressBar.setBounds(area.removeFromTop(20));
    area.removeFromTop(5);
    statusLabel.setBounds(area.removeFromTop(20));
    area.removeFromTop(15);

    // Buttons
    auto buttonRow = area.removeFromTop(30);
    cancelButton.setBounds(buttonRow.removeFromRight(100));
    buttonRow.removeFromRight(10);
    exportButton.setBounds(buttonRow.removeFromRight(100));
}

void ExportDialog::buttonClicked(juce::Button* button)
{
    if (button == &browseButton)
    {
        browseForFile();
    }
    else if (button == &exportButton)
    {
        if (!isExporting && outputFile != juce::File())
        {
            isExporting = true;
            exportButton.setEnabled(false);
            browseButton.setEnabled(false);
            startTimer(50); // Update progress UI
            startThread();
        }
    }
    else if (button == &cancelButton)
    {
        if (isExporting)
        {
            signalThreadShouldExit();
            statusLabel.setText("Cancelling...", juce::dontSendNotification);
        }
        else
        {
            closeButtonPressed();
        }
    }
}

void ExportDialog::comboBoxChanged(juce::ComboBox* comboBox)
{
    if (comboBox == &formatComboBox)
    {
        // Disable bit depth for MP3 (always uses internal format)
        bool isWav = formatComboBox.getSelectedId() == 1;
        bitDepthComboBox.setEnabled(isWav);
    }
}

void ExportDialog::browseForFile()
{
    auto chooserFlags = juce::FileBrowserComponent::saveMode | juce::FileBrowserComponent::canSelectFiles;
    auto chooser = std::make_unique<juce::FileChooser>("Save audio file...",
                                                        juce::File::getSpecialLocation(juce::File::userDesktopDirectory),
                                                        formatComboBox.getSelectedId() == 1 ? "*.wav" : "*.mp3");

    chooser->launchAsync(chooserFlags, [this](const juce::FileChooser& fc)
    {
        if (fc.getResult() != juce::File())
        {
            outputFile = fc.getResult();
            filePathLabel.setText("Output: " + outputFile.getFileName(), juce::dontSendNotification);
            filePathLabel.setColour(juce::Label::textColourId, juce::Colours::white);
            exportButton.setEnabled(true);
        }
    });
}

void ExportDialog::run()
{
    performExport();
}

void ExportDialog::performExport()
{
    // Create and configure export via FFI
    exportHandle = ExportFFI::createExport();
    if (!exportHandle) {
        juce::MessageManager::callAsync([this]() {
            statusLabel.setText("Error: Failed to create export", juce::dontSendNotification);
            exportButton.setEnabled(true);
            browseButton.setEnabled(true);
        });
        return;
    }
    
    // Map UI selections to export config
    ExportConfig config;
    config.filePath = outputFile.getFullPathName().toStdString();
    config.sampleRate = sampleRateComboBox.getSelectedId() == 1 ? 44100 :
                        sampleRateComboBox.getSelectedId() == 2 ? 48000 : 96000;
    config.stemExport = stemExportButton.getToggleState();
    
    // Map bit depth selection to format
    int bitDepthId = bitDepthComboBox.getSelectedId();
    if (bitDepthId == 1)
        config.format = ExportFormat::Wav16;
    else if (bitDepthId == 2)
        config.format = ExportFormat::Wav24;
    else
        config.format = ExportFormat::Wav32;
    
    // Configure export
    if (!ExportFFI::configure(exportHandle, config)) {
        ExportFFI::destroy(exportHandle);
        exportHandle = nullptr;
        juce::MessageManager::callAsync([this]() {
            statusLabel.setText("Error: Failed to configure export", juce::dontSendNotification);
            exportButton.setEnabled(true);
            browseButton.setEnabled(true);
        });
        return;
    }
    
    // Start export
    if (!ExportFFI::start(exportHandle)) {
        ExportFFI::destroy(exportHandle);
        exportHandle = nullptr;
        juce::MessageManager::callAsync([this]() {
            statusLabel.setText("Error: Failed to start export", juce::dontSendNotification);
            exportButton.setEnabled(true);
            browseButton.setEnabled(true);
        });
        return;
    }
    
    statusLabel.setText("Exporting...", juce::dontSendNotification);
    
    // Poll progress until complete
    while (!threadShouldExit()) {
        double progress = ExportFFI::getProgress(exportHandle);
        bool complete = ExportFFI::isComplete(exportHandle);
        
        progressValue = progress;
        
        if (complete) {
            ExportResult result = ExportFFI::getResult(exportHandle);
            
            isExporting = false;
            
            if (result == ExportResult::Success) {
                juce::MessageManager::callAsync([this]() {
                    statusLabel.setText("Export complete!", juce::dontSendNotification);
                    exportButton.setEnabled(true);
                    browseButton.setEnabled(true);
                    if (onExportComplete)
                        onExportComplete(true, "Exported to: " + outputFile.getFullPathName());
                });
            } else if (result == ExportResult::Cancelled) {
                juce::MessageManager::callAsync([this]() {
                    statusLabel.setText("Cancelled", juce::dontSendNotification);
                    exportButton.setEnabled(true);
                    browseButton.setEnabled(true);
                    if (onExportComplete)
                        onExportComplete(false, "Export cancelled by user");
                });
            } else {
                juce::MessageManager::callAsync([this]() {
                    statusLabel.setText("Export failed", juce::dontSendNotification);
                    exportButton.setEnabled(true);
                    browseButton.setEnabled(true);
                    if (onExportComplete)
                        onExportComplete(false, "Export failed");
                });
            }
            
            break;
        }
        
        juce::Thread::sleep(50); // Poll every 50ms
    }
    
    // Cleanup
    if (exportHandle) {
        ExportFFI::destroy(exportHandle);
        exportHandle = nullptr;
    }
}

void ExportDialog::timerCallback()
{
    if (isExporting)
    {
        // ProgressBar updates automatically from progressValue reference
        // Just trigger a repaint to refresh the UI
        progressBar.repaint();
    }
    else
    {
        stopTimer();
    }
}

void ExportDialog::closeButtonPressed()
{
    setVisible(false);
    exitModalState(0);
}
