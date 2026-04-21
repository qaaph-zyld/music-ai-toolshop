#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_gui_extra/juce_gui_extra.h>

class ExportDialog : public juce::DialogWindow,
                     public juce::Button::Listener,
                     public juce::ComboBox::Listener,
                     public juce::Thread,
                     public juce::Timer
{
public:
    ExportDialog(juce::Component* parent);
    ~ExportDialog() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void buttonClicked(juce::Button* button) override;
    void comboBoxChanged(juce::ComboBox* comboBox) override;
    void run() override;
    void timerCallback() override;
    void closeButtonPressed() override;

    // Export result callback
    std::function<void(bool success, const juce::String& message)> onExportComplete;

private:
    // UI Components
    juce::Label titleLabel;
    juce::Label formatLabel;
    juce::ComboBox formatComboBox;
    juce::Label sampleRateLabel;
    juce::ComboBox sampleRateComboBox;
    juce::Label bitDepthLabel;
    juce::ComboBox bitDepthComboBox;
    juce::ToggleButton stemExportButton;
    juce::Label filePathLabel;
    juce::TextButton browseButton;
    juce::TextButton exportButton;
    juce::TextButton cancelButton;
    double progressValue = 0.0;
    juce::ProgressBar progressBar{progressValue};
    juce::Label statusLabel;

    // Export settings
    juce::File outputFile;
    bool isExporting = false;
    void* exportHandle = nullptr;

    // Export thread
    void performExport();
    void browseForFile();

    // Layout constants
    static constexpr int dialogWidth = 450;
    static constexpr int dialogHeight = 350;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ExportDialog)
};
