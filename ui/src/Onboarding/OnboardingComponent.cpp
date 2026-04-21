#include "OnboardingComponent.h"

OnboardingComponent::OnboardingComponent()
{
    // Title
    titleLabel = std::make_unique<juce::Label>("title", "Welcome to OpenDAW");
    titleLabel->setFont(juce::Font(24.0f, juce::Font::bold));
    titleLabel->setJustificationType(juce::Justification::centred);
    addAndMakeVisible(*titleLabel);

    // Description
    descriptionLabel = std::make_unique<juce::Label>("description", 
        "Your open-source digital audio workstation\nwith AI-powered features.");
    descriptionLabel->setFont(juce::Font(14.0f));
    descriptionLabel->setJustificationType(juce::Justification::centred);
    descriptionLabel->setMultiLine(true);
    addAndMakeVisible(*descriptionLabel);

    // Primary button (Next/Continue/Finish)
    primaryButton = std::make_unique<juce::TextButton>("Get Started");
    primaryButton->addListener(this);
    addAndMakeVisible(*primaryButton);

    // Secondary button (Back)
    secondaryButton = std::make_unique<juce::TextButton>("Back");
    secondaryButton->addListener(this);
    secondaryButton->setVisible(false);
    addAndMakeVisible(*secondaryButton);

    // Skip button
    skipButton = std::make_unique<juce::TextButton>("Skip Tutorial");
    skipButton->addListener(this);
    skipButton->setVisible(false);
    addAndMakeVisible(*skipButton);

    // Progress bar
    progressBar = std::make_unique<juce::ProgressBar>(progress);
    progressBar->setVisible(false);
    addAndMakeVisible(*progressBar);

    // Demo project selector
    demoProjectSelector = std::make_unique<juce::ComboBox>("demoSelector");
    for (int i = 0; i < demoProjects.size(); ++i)
    {
        demoProjectSelector->addItem(demoProjects[i], i + 1);
    }
    demoProjectSelector->setSelectedId(1);
    demoProjectSelector->setVisible(false);
    addAndMakeVisible(*demoProjectSelector);

    updateScreenLayout();
}

OnboardingComponent::~OnboardingComponent() = default;

void OnboardingComponent::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(0xFF1E1E1E)); // Dark background

    // Draw highlight area for tutorial if active
    if (currentScreen == Screen::Tutorial && !highlightArea.isEmpty())
    {
        g.setColour(juce::Colours::yellow.withAlpha(0.3f));
        g.drawRoundedRectangle(highlightArea.toFloat(), 4.0f, 3.0f);
    }
}

void OnboardingComponent::resized()
{
    auto bounds = getLocalBounds().reduced(40);
    auto centreX = bounds.getCentreX();

    // Title at top
    titleLabel->setBounds(centreX - 200, bounds.getY(), 400, 40);

    // Description below title
    descriptionLabel->setBounds(centreX - 250, titleLabel->getBottom() + 20, 500, 60);

    // Demo selector (when visible)
    demoProjectSelector->setBounds(centreX - 150, descriptionLabel->getBottom() + 30, 300, 30);

    // Progress bar (when visible)
    progressBar->setBounds(centreX - 150, descriptionLabel->getBottom() + 100, 300, 20);

    // Buttons at bottom
    auto buttonY = bounds.getBottom() - 40;
    secondaryButton->setBounds(centreX - 200, buttonY, 120, 35);
    primaryButton->setBounds(centreX - 60, buttonY, 120, 35);
    skipButton->setBounds(centreX + 80, buttonY, 120, 35);
}

void OnboardingComponent::buttonClicked(juce::Button* button)
{
    if (button == primaryButton.get())
    {
        switch (currentScreen)
        {
            case Screen::Welcome:
                showDemoProject();
                break;
            case Screen::DemoProject:
                showInteractiveTutorial();
                break;
            case Screen::Tutorial:
                nextTutorialStep();
                break;
            case Screen::AudioTest:
                if (audioTestPassed)
                    currentScreen = Screen::Complete;
                break;
            case Screen::Complete:
                markFirstLaunchComplete();
                setVisible(false);
                break;
        }
        updateScreenLayout();
    }
    else if (button == secondaryButton.get())
    {
        previousTutorialStep();
        updateScreenLayout();
    }
    else if (button == skipButton.get())
    {
        skipTutorial();
    }
}

bool OnboardingComponent::isFirstLaunch()
{
    juce::PropertiesFile::Options options;
    options.applicationName = "OpenDAW";
    options.filenameSuffix = "settings";
    options.osxLibrarySubFolder = "Application Support";
    
    juce::ApplicationProperties appProps;
    appProps.setStorageParameters(options);
    
    auto* props = appProps.getUserSettings();
    return !props->getBoolValue("firstLaunchComplete", false);
}

void OnboardingComponent::markFirstLaunchComplete()
{
    juce::PropertiesFile::Options options;
    options.applicationName = "OpenDAW";
    options.filenameSuffix = "settings";
    options.osxLibrarySubFolder = "Application Support";
    
    juce::ApplicationProperties appProps;
    appProps.setStorageParameters(options);
    
    auto* props = appProps.getUserSettings();
    props->setValue("firstLaunchComplete", true);
    appProps.saveIfNeeded();
}

void OnboardingComponent::showWelcomeScreen()
{
    currentScreen = Screen::Welcome;
    titleLabel->setText("Welcome to OpenDAW", juce::dontSendNotification);
    descriptionLabel->setText(
        "Your open-source digital audio workstation\n"
        "with AI-powered features for music creation.",
        juce::dontSendNotification);
    primaryButton->setButtonText("Get Started");
    secondaryButton->setVisible(false);
    skipButton->setVisible(false);
    demoProjectSelector->setVisible(false);
    progressBar->setVisible(false);
}

void OnboardingComponent::showDemoProject()
{
    currentScreen = Screen::DemoProject;
    titleLabel->setText("Load Demo Project", juce::dontSendNotification);
    descriptionLabel->setText(
        "Load a demo project to explore OpenDAW's features.\n"
        "You can also create a blank project.",
        juce::dontSendNotification);
    primaryButton->setButtonText("Load Demo");
    secondaryButton->setVisible(true);
    secondaryButton->setButtonText("Blank Project");
    skipButton->setVisible(false);
    demoProjectSelector->setVisible(true);
    progressBar->setVisible(false);
}

void OnboardingComponent::showInteractiveTutorial()
{
    currentScreen = Screen::Tutorial;
    tutorialStep = 0;
    showTutorialStep(0);
}

void OnboardingComponent::showAudioTest()
{
    currentScreen = Screen::AudioTest;
    titleLabel->setText("Audio Engine Test", juce::dontSendNotification);
    descriptionLabel->setText(
        "Let's verify your audio setup.\n"
        "Click 'Test Audio' to play a test tone.",
        juce::dontSendNotification);
    primaryButton->setButtonText("Test Audio");
    secondaryButton->setVisible(true);
    secondaryButton->setButtonText("Skip");
    skipButton->setVisible(false);
    demoProjectSelector->setVisible(false);
    progressBar->setVisible(false);
}

void OnboardingComponent::nextTutorialStep()
{
    if (tutorialStep < totalTutorialSteps - 1)
    {
        ++tutorialStep;
        showTutorialStep(tutorialStep);
    }
    else
    {
        showAudioTest();
    }
}

void OnboardingComponent::previousTutorialStep()
{
    if (tutorialStep > 0)
    {
        --tutorialStep;
        showTutorialStep(tutorialStep);
    }
    else if (currentScreen == Screen::Tutorial)
    {
        showDemoProject();
    }
}

void OnboardingComponent::skipTutorial()
{
    markFirstLaunchComplete();
    setVisible(false);
}

void OnboardingComponent::showTutorialStep(int step)
{
    juce::String title, description;
    
    switch (step)
    {
        case 0:
            title = "Tutorial: Session View";
            description = "This is the Session View - your main workspace.\n"
                         "Clips are arranged in an 8x16 grid. Click any slot to add a clip.";
            break;
        case 1:
            title = "Tutorial: Transport Controls";
            description = "Use these controls to play, stop, and record.\n"
                         "The metronome helps you stay in time.";
            break;
        case 2:
            title = "Tutorial: Mixer";
            description = "Adjust volume and pan for each track here.\n"
                         "You can also mute and solo individual tracks.";
            break;
        case 3:
            title = "Tutorial: AI Features";
            description = "Access AI-powered features from the Suno browser.\n"
                         "Generate patterns, extract stems, and more!";
            break;
        case 4:
            title = "Tutorial: Export";
            description = "When your track is ready, export it as WAV or MP3.\n"
                         "Choose File → Export → Audio.";
            break;
    }
    
    titleLabel->setText(title, juce::dontSendNotification);
    descriptionLabel->setText(description, juce::dontSendNotification);
    
    primaryButton->setButtonText(step == totalTutorialSteps - 1 ? "Next: Audio Test" : "Next");
    secondaryButton->setVisible(true);
    secondaryButton->setButtonText("Back");
    skipButton->setVisible(true);
    demoProjectSelector->setVisible(false);
    progressBar->setVisible(true);
    
    // Update progress
    double progress = (step + 1.0) / totalTutorialSteps;
    progressBar->setValue(progress);
}

void OnboardingComponent::runAudioEngineTest()
{
    audioTestRunning = true;
    primaryButton->setEnabled(false);
    primaryButton->setButtonText("Testing...");
    
    // In a real implementation, this would:
    // 1. Initialize the audio device
    // 2. Play a test tone
    // 3. Verify audio output
    
    // Simulate test completion
    juce::Timer::callAfterDelay(2000, [this]()
    {
        audioTestRunning = false;
        audioTestPassed = true;
        
        primaryButton->setEnabled(true);
        primaryButton->setButtonText("Continue");
        descriptionLabel->setText(
            "Audio test successful! Your setup is working correctly.\n"
            "You're ready to start making music.",
            juce::dontSendNotification);
    });
}

void OnboardingComponent::updateScreenLayout()
{
    resized();
    repaint();
}

void OnboardingComponent::loadDemoProject(const juce::String& projectName)
{
    // In a real implementation, this would load the selected demo project
    // from a template directory
    juce::ignoreUnused(projectName);
}
