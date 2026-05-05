#pragma once

#include <juce_gui_extra/juce_gui_extra.h>
#include "../Engine/EngineBridge.h"

class VocalCleanupDialog : public juce::DialogWindow
{
public:
    VocalCleanupDialog(EngineBridge& engine);
    ~VocalCleanupDialog() override;

    void closeButtonPressed() override;

    class VocalCleanupComponent : public juce::Component,
                                   public juce::Button::Listener,
                                   public juce::Slider::Listener
    {
    public:
        VocalCleanupComponent(EngineBridge& engine, VocalCleanupDialog* dialog);
        ~VocalCleanupComponent() override;

        void paint(juce::Graphics& g) override;
        void resized() override;
        void buttonClicked(juce::Button* button) override;
        void sliderValueChanged(juce::Slider* slider) override;

        void processVocalCleanup();
        void previewVocalCleanup();

    private:
        EngineBridge& engine;
        VocalCleanupDialog* dialog;

        // Settings sliders
        juce::Slider silenceThresholdSlider;
        juce::Slider silenceMinDurationSlider;
        juce::Slider gapCompressRatioSlider;
        juce::Slider crossfadeMsSlider;
        juce::Slider breathSensitivitySlider;

        // Labels
        juce::Label silenceThresholdLabel;
        juce::Label silenceMinDurationLabel;
        juce::Label gapCompressRatioLabel;
        juce::Label crossfadeMsLabel;
        juce::Label breathSensitivityLabel;

        // Buttons
        juce::TextButton browseButton;
        juce::TextButton previewButton;
        juce::TextButton processButton;
        juce::TextButton closeButton;

        // File path
        juce::Label filePathLabel;
        juce::String currentFilePath;

        // Status
        juce::Label statusLabel;

        JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VocalCleanupComponent)
    };

private:
    std::unique_ptr<VocalCleanupComponent> contentComponent;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VocalCleanupDialog)
};
