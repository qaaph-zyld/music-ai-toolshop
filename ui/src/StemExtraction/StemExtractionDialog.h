#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "../Engine/EngineBridge.h"

/**
 * StemExtractionDialog - Progress dialog for AI stem separation
 * 
 * Shows progress for each stem type (drums, bass, vocals, other)
 * with a cancel button and status messages.
 */
class StemExtractionDialog : public juce::DialogWindow,
                              public juce::Thread
{
public:
    StemExtractionDialog(const juce::String& audioFilePath,
                         const juce::String& outputDir);
    ~StemExtractionDialog() override;

    // Thread entry point - runs the extraction
    void run() override;

    // Callback when extraction completes
    std::function<void(const EngineBridge::StemPaths& result)> onExtractionComplete;

    // Callback when extraction is cancelled
    std::function<void()> onExtractionCancelled;

private:
    void closeButtonPressed() override;

    // Content component that holds all UI elements
    // Required because DialogWindow doesn't support direct addAndMakeVisible
    class ContentComponent : public juce::Component
    {
    public:
        ContentComponent(StemExtractionDialog& owner);
        void resized() override;

        // UI Components
        juce::Label statusLabel;
        juce::ProgressBar overallProgressBar;
        juce::TextButton cancelButton;
        
        // Individual stem progress labels
        juce::Label drumsLabel;
        juce::Label bassLabel;
        juce::Label vocalsLabel;
        juce::Label otherLabel;

    private:
        StemExtractionDialog& dialogOwner;
        JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ContentComponent)
    };

    std::unique_ptr<ContentComponent> content;

    // State
    juce::String audioFilePath;
    juce::String outputDir;
    double overallProgress = 0.0;
    std::atomic<bool> isCancelled{false};
    std::atomic<bool> isComplete{false};
    
    EngineBridge::StemPaths extractionResult;

    // Update UI from message thread
    class AsyncUpdater : public juce::AsyncUpdater
    {
    public:
        StemExtractionDialog* owner = nullptr;
        void handleAsyncUpdate() override;
    };
    AsyncUpdater asyncUpdater;

    // Progress callback from EngineBridge
    void onProgressUpdate(float progress);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(StemExtractionDialog)
};
