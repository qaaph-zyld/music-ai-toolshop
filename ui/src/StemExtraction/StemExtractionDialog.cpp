#include "StemExtractionDialog.h"

// ContentComponent implementation
StemExtractionDialog::ContentComponent::ContentComponent(StemExtractionDialog& owner)
    : dialogOwner(owner),
      overallProgressBar(owner.overallProgress)
{
    // Status label
    statusLabel.setText("Initializing stem extraction...", juce::dontSendNotification);
    statusLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(statusLabel);
    
    // Overall progress
    overallProgressBar.setPercentageDisplay(true);
    addAndMakeVisible(overallProgressBar);
    
    // Stem labels
    drumsLabel.setText("Drums:", juce::dontSendNotification);
    bassLabel.setText("Bass:", juce::dontSendNotification);
    vocalsLabel.setText("Vocals:", juce::dontSendNotification);
    otherLabel.setText("Other:", juce::dontSendNotification);
    
    addAndMakeVisible(drumsLabel);
    addAndMakeVisible(bassLabel);
    addAndMakeVisible(vocalsLabel);
    addAndMakeVisible(otherLabel);
    
    // Cancel button
    cancelButton.setButtonText("Cancel");
    cancelButton.onClick = [&owner]() {
        owner.isCancelled.store(true);
        EngineBridge::getInstance().cancelStemExtraction();
        owner.signalThreadShouldExit();
    };
    addAndMakeVisible(cancelButton);
}

void StemExtractionDialog::ContentComponent::resized()
{
    auto bounds = getLocalBounds().reduced(20);
    
    // Status label at top
    statusLabel.setBounds(bounds.removeFromTop(30));
    bounds.removeFromTop(10);
    
    // Overall progress
    overallProgressBar.setBounds(bounds.removeFromTop(20));
    bounds.removeFromTop(20);
    
    // Stem labels (simplified layout)
    auto labelHeight = 20;
    
    drumsLabel.setBounds(bounds.removeFromTop(labelHeight));
    bassLabel.setBounds(bounds.removeFromTop(labelHeight));
    vocalsLabel.setBounds(bounds.removeFromTop(labelHeight));
    otherLabel.setBounds(bounds.removeFromTop(labelHeight));
    
    bounds.removeFromTop(20);
    
    // Cancel button at bottom
    cancelButton.setBounds(bounds.removeFromBottom(30).withSizeKeepingCentre(100, 30));
}

// StemExtractionDialog implementation
StemExtractionDialog::StemExtractionDialog(const juce::String& audioPath,
                                           const juce::String& outDir)
    : juce::DialogWindow("Extracting Stems", juce::Colours::darkgrey, true, true),
      juce::Thread("StemExtraction"),
      audioFilePath(audioPath),
      outputDir(outDir)
{
    // Create content component
    content = std::make_unique<ContentComponent>(*this);
    
    // Set up the dialog
    setContentOwned(content.get(), true);
    setContentComponentSize(400, 300);
    centreWithSize(400, 300);
    setResizable(false, false);
    setUsingNativeTitleBar(true);
    
    // Set up async updater
    asyncUpdater.owner = this;
    
    // Start the extraction thread
    startThread();
}

StemExtractionDialog::~StemExtractionDialog()
{
    signalThreadShouldExit();
    stopThread(5000); // Wait up to 5 seconds for thread to finish
}

void StemExtractionDialog::run()
{
    // Check if demucs is available
    if (!EngineBridge::getInstance().isStemSeparationAvailable())
    {
        juce::MessageManager::callAsync([this]() {
            content->statusLabel.setText("Error: Demucs not available. Please install demucs.", 
                                       juce::dontSendNotification);
            content->cancelButton.setButtonText("Close");
            content->cancelButton.onClick = [this]() { closeButtonPressed(); };
        });
        
        if (onExtractionCancelled)
            onExtractionCancelled();
        return;
    }
    
    // Update status
    juce::MessageManager::callAsync([this]() {
        content->statusLabel.setText("Separating audio into stems...", juce::dontSendNotification);
    });
    
    // Run extraction
    extractionResult = EngineBridge::getInstance().extractStems(
        audioFilePath,
        outputDir,
        [this](float progress) {
            overallProgress = static_cast<double>(progress);
            juce::MessageManager::callAsync([this]() {
                content->repaint();
            });
        }
    );
    
    isComplete.store(true);
    
    // Update UI based on result
    juce::MessageManager::callAsync([this]() {
        if (isCancelled.load())
        {
            content->statusLabel.setText("Extraction cancelled.", juce::dontSendNotification);
            content->cancelButton.setButtonText("Close");
            content->cancelButton.onClick = [this]() { closeButtonPressed(); };
            
            if (onExtractionCancelled)
                onExtractionCancelled();
        }
        else if (extractionResult.success)
        {
            int stemCount = 0;
            if (!extractionResult.drums.isEmpty()) stemCount++;
            if (!extractionResult.bass.isEmpty()) stemCount++;
            if (!extractionResult.vocals.isEmpty()) stemCount++;
            if (!extractionResult.other.isEmpty()) stemCount++;
            
            content->statusLabel.setText("Complete! Extracted " + juce::String(stemCount) + " stems.",
                                       juce::dontSendNotification);
            content->cancelButton.setButtonText("Close");
            content->cancelButton.onClick = [this]() { closeButtonPressed(); };
            
            if (onExtractionComplete)
                onExtractionComplete(extractionResult);
        }
        else
        {
            content->statusLabel.setText("Extraction failed. Check that demucs is installed.",
                                       juce::dontSendNotification);
            content->cancelButton.setButtonText("Close");
            content->cancelButton.onClick = [this]() { closeButtonPressed(); };
            
            if (onExtractionCancelled)
                onExtractionCancelled();
        }
    });
}

void StemExtractionDialog::closeButtonPressed()
{
    signalThreadShouldExit();
    EngineBridge::getInstance().cancelStemExtraction();
    
    // If still running, cancel it
    if (isThreadRunning())
    {
        stopThread(1000);
    }
    
    setVisible(false);
    exitModalState(0);
}

void StemExtractionDialog::onProgressUpdate(float progress)
{
    overallProgress = static_cast<double>(progress);
}

void StemExtractionDialog::AsyncUpdater::handleAsyncUpdate()
{
    if (owner != nullptr && owner->content != nullptr)
    {
        owner->content->repaint();
    }
}
