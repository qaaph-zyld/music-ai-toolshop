#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_gui_extra/juce_gui_extra.h>
#include "MmmFFI.h"

/**
 * Pattern Generator Dialog
 *
 * AI-powered MIDI pattern generation using MMM (Music Motion Machine).
 * Supports drums, bass, and melody generation with style selection.
 */

class PatternGeneratorDialog : public juce::DialogWindow,
                              public juce::Button::Listener,
                              public juce::ComboBox::Listener,
                              public juce::Slider::Listener,
                              public juce::Timer
{
public:
    PatternGeneratorDialog(juce::Component* parent);
    ~PatternGeneratorDialog() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void buttonClicked(juce::Button* button) override;
    void comboBoxChanged(juce::ComboBox* comboBox) override;
    void sliderValueChanged(juce::Slider* slider) override;
    void timerCallback() override;
    void closeButtonPressed() override;

    // Callback when pattern is generated
    std::function<void(const OpenDAW::PatternData& pattern, const OpenDAW::PatternConfig& config)> onPatternGenerated;

private:
    // UI Components - Header
    juce::Label titleLabel;
    juce::Label subtitleLabel;

    // Style selection
    juce::Label styleLabel;
    juce::ComboBox styleComboBox;

    // Pattern type
    juce::Label typeLabel;
    juce::ComboBox typeComboBox;

    // Tempo
    juce::Label tempoLabel;
    juce::Slider tempoSlider;
    juce::Label tempoValueLabel;

    // Key selection (for melody)
    juce::Label keyLabel;
    juce::ComboBox keyComboBox;

    // Chords input (for bass)
    juce::Label chordsLabel;
    juce::TextEditor chordsEditor;

    // Bars
    juce::Label barsLabel;
    juce::Slider barsSlider;
    juce::Label barsValueLabel;

    // Action buttons
    juce::TextButton generateButton;
    juce::TextButton cancelButton;
    juce::TextButton importButton;

    // Status
    juce::Label statusLabel;
    juce::ProgressBar progressBar{progressValue};
    double progressValue = 0.0;

    // Preview area
    juce::Label previewLabel;
    juce::TextEditor previewEditor;

    // MMM Handle
    void* mmmHandle = nullptr;
    bool isGenerating = false;
    OpenDAW::PatternData currentPattern;

    // Configuration
    void updateUIForPatternType();
    void startGeneration();
    void cancelGeneration();
    void importPattern();
    void updatePreview();
    void showError(const juce::String& message);
    void showStatus(const juce::String& message);

    // Layout constants
    static constexpr int dialogWidth = 480;
    static constexpr int dialogHeight = 520;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(PatternGeneratorDialog)
};
