#include "MainComponent.h"
#include "Engine/EngineBridge.h"

// ============================================================================
// MainMenuBarModel Implementation
// ============================================================================

MainMenuBarModel::MainMenuBarModel()
{
    // Menu will be updated automatically when setApplicationCommandManagerToWatch
    // is called on the component
}

MainMenuBarModel::~MainMenuBarModel()
{
}

juce::PopupMenu MainMenuBarModel::getMenuForIndex(int menuIndex, const juce::String& menuName)
{
    (void)menuName;

    if (menuIndex == 0)
        return createFileMenu();
    else if (menuIndex == 1)
        return createViewMenu();
    else if (menuIndex == 2)
        return createToolsMenu();

    return {};
}

juce::PopupMenu MainMenuBarModel::createFileMenu()
{
    juce::PopupMenu menu;

    menu.addItem(fileNew, "New Project");
    menu.addItem(fileOpen, "Open Project...");
    menu.addSeparator();
    menu.addItem(fileSave, "Save Project");
    menu.addItem(fileSaveAs, "Save Project As...");
    menu.addSeparator();
    menu.addItem(fileExit, "Exit");

    return menu;
}

juce::PopupMenu MainMenuBarModel::createViewMenu()
{
    juce::PopupMenu menu;
    menu.addItem(viewSunoBrowser, "Suno Library");
    return menu;
}

juce::PopupMenu MainMenuBarModel::createToolsMenu()
{
    juce::PopupMenu menu;
    menu.addItem(toolsGeneratePattern, "Generate Pattern...");
    return menu;
}

void MainMenuBarModel::menuItemSelected(int menuItemID, int topLevelMenuIndex)
{
    (void)topLevelMenuIndex;

    switch (menuItemID)
    {
        case fileNew:
            if (onNewProject)
                onNewProject();
            break;
        case fileOpen:
            if (onOpenProject)
                onOpenProject();
            break;
        case fileSave:
            if (onSaveProject)
                onSaveProject();
            break;
        case fileSaveAs:
            if (onSaveProjectAs)
                onSaveProjectAs();
            break;
        case fileExit:
            if (onExit)
                onExit();
            break;
        case viewSunoBrowser:
            if (onToggleSunoBrowser)
                onToggleSunoBrowser();
            break;
        case toolsGeneratePattern:
            if (onGeneratePattern)
                onGeneratePattern();
            break;
        default:
            break;
    }
}

// ============================================================================
// MainComponent Implementation
// ============================================================================

MainComponent::MainComponent()
{
    std::cout << "MainComponent constructor - START" << std::endl;
    
    std::cout << "MainComponent: Getting EngineBridge instance..." << std::endl;
    auto& engine = EngineBridge::getInstance();
    std::cout << "MainComponent: EngineBridge instance obtained" << std::endl;
    
    // TEMPORARILY DISABLED - Testing if crash is in init
    // if (!engine.isInitialized())
    // {
    //     std::cout << "MainComponent: Initializing EngineBridge..." << std::endl;
    //     engine.initialize(48000, 512);
    //     std::cout << "MainComponent: EngineBridge initialized" << std::endl;
    // }

    std::cout << "MainComponent: Setting up look and feel..." << std::endl;
    getLookAndFeel().setColour(juce::ResizableWindow::backgroundColourId, juce::Colour(0xFF2B2B2B));
    std::cout << "MainComponent: Look and feel set" << std::endl;

    std::cout << "MainComponent: Enabling keyboard focus..." << std::endl;
    setWantsKeyboardFocus(true);
    grabKeyboardFocus();
    std::cout << "MainComponent: Keyboard focus enabled" << std::endl;

    std::cout << "MainComponent: Creating menu bar..." << std::endl;
    menuBarModel = std::make_unique<MainMenuBarModel>();
    menuBar = std::make_unique<juce::MenuBarComponent>(menuBarModel.get());
    addAndMakeVisible(menuBar.get());
    std::cout << "MainComponent: Menu bar created" << std::endl;

    std::cout << "MainComponent: Creating ProjectManager..." << std::endl;
    projectManager = std::make_unique<ProjectManager>();
    std::cout << "MainComponent: ProjectManager created" << std::endl;

    std::cout << "MainComponent: Creating TransportBar..." << std::endl;
    transportBar = std::make_unique<TransportBar>();
    addAndMakeVisible(transportBar.get());
    std::cout << "MainComponent: TransportBar created" << std::endl;

    std::cout << "MainComponent: Creating RecordingPanel..." << std::endl;
    recordingPanel = std::make_unique<RecordingPanel>();
    addAndMakeVisible(recordingPanel.get());
    std::cout << "MainComponent: RecordingPanel created" << std::endl;

    std::cout << "MainComponent: Creating SessionGrid..." << std::endl;
    sessionGrid = std::make_unique<SessionGridComponent>(8, 16);
    addAndMakeVisible(sessionGrid.get());
    std::cout << "MainComponent: SessionGrid created" << std::endl;

    std::cout << "MainComponent: Creating MixerPanel..." << std::endl;
    mixerPanel = std::make_unique<MixerPanel>(8);
    addAndMakeVisible(mixerPanel.get());
    std::cout << "MainComponent: MixerPanel created" << std::endl;

    std::cout << "MainComponent: Creating SunoBrowser..." << std::endl;
    sunoBrowser = std::make_unique<SunoBrowserComponent>();
    sunoBrowser->setVisible(false);
    addAndMakeVisible(sunoBrowser.get());
    std::cout << "MainComponent: SunoBrowser created" << std::endl;

    std::cout << "MainComponent: Setting up layout..." << std::endl;
    menuBarModel->onNewProject = [this]() {
        if (projectManager)
            projectManager->newProject(this);
    };

    menuBarModel->onOpenProject = [this]() {
        if (projectManager)
            projectManager->openProject(this);
    };

    menuBarModel->onSaveProject = [this]() {
        if (projectManager)
            projectManager->saveProject(this);
    };

    menuBarModel->onSaveProjectAs = [this]() {
        if (projectManager)
            projectManager->saveProjectAs(this);
    };

    menuBarModel->onExit = [this]() {
        juce::JUCEApplication::getInstance()->systemRequestedQuit();
    };

    menuBarModel->onToggleSunoBrowser = [this]() {
        if (sunoBrowser)
        {
            sunoBrowser->setVisible(!sunoBrowser->isVisible());
            resized();
        }
    };

    // Wire up Tools menu - Phase 8.3
    menuBarModel->onGeneratePattern = [this]() {
        auto dialog = std::make_unique<PatternGeneratorDialog>(this);
        dialog->onPatternGenerated = [this](const OpenDAW::PatternData& pattern, const OpenDAW::PatternConfig& config) {
            // Create a clip in the session grid with the generated pattern
            juce::Colour clipColor;
            juce::String clipName;
            switch (config.type) {
                case OpenDAW::PatternType::Drums:
                    clipColor = juce::Colours::lightblue;
                    clipName = "Drums: " + OpenDAW::MmmFFI::styleToString(config.style);
                    break;
                case OpenDAW::PatternType::Bass:
                    clipColor = juce::Colours::lightgreen;
                    clipName = "Bass: " + OpenDAW::MmmFFI::styleToString(config.style);
                    break;
                case OpenDAW::PatternType::Melody:
                    clipColor = juce::Colours::lightcoral;
                    clipName = "Melody: " + OpenDAW::MmmFFI::styleToString(config.style);
                    break;
            }
            // Add to first empty slot in track 0, scene 0 (or find empty slot)
            sessionGrid->setClip(0, 0, clipName, clipColor);
            (void)pattern; // TODO: Store actual MIDI notes in clip
        };
        // Dialog will self-delete when closed
        dialog.release();
    };

    std::cout << "MainComponent: Setting up callbacks..." << std::endl;

    // Wire up project callbacks
    projectManager->onProjectNew = [this]() {
        sessionGrid->clearAllClips();
    };

    projectManager->onProjectLoaded = [this](const juce::String& path) {
        (void)path;
    };

    projectManager->onProjectSaved = [this](const juce::String& path) {
        (void)path;
    };

    // Wire track arming to recording panel - Phase 7.1
    SessionGridComponent::onTrackArmChanged = [this](int trackIndex, bool armed) {
        if (armed)
        {
            recordingPanel->setTargetTrack(trackIndex);
            recordingPanel->updateTargetLabel();
        }
    };

    // Wire recording completion to create clip - Phase 7.1
    recordingPanel->onRecordingComplete = [this](int track, int scene, const juce::Array<EngineBridge::RecordedNote>& notes) {
        juce::Colour clipColor = juce::Colours::cyan;
        sessionGrid->setClip(track, scene, "MIDI Recording", clipColor);
        (void)notes;
    };

    // Wire up import callback - Phase 8.5 (Complete with audio loading)
    sunoBrowser->onTrackImported = [this](const juce::String& trackId, int track, int scene, const juce::String& audioFilePath) {
        juce::Colour clipColor = juce::Colours::orange;
        sessionGrid->setClip(track, scene, "Suno: " + trackId, clipColor);
        
        // Load the audio file into the clip slot
        auto& engine = EngineBridge::getInstance();
        engine.loadClip(track, scene, audioFilePath);
    };

    std::cout << "MainComponent: Callbacks set up" << std::endl;

    std::cout << "MainComponent: Setting up layout..." << std::endl;
    // Set up vertical layout: Menu | Transport | Recording | Session Grid | Mixer
    // Note: Menu bar is handled separately, so we start layout from index 1
    verticalLayout.setItemLayout(0, 60, 60, 60);        // Transport: fixed 60px
    verticalLayout.setItemLayout(1, 70, 100, 80);     // Recording: fixed 80px
    verticalLayout.setItemLayout(2, 300, -1.0, -0.7);   // Session: 70% remaining
    verticalLayout.setItemLayout(3, 150, 300, 200);    // Mixer: 200px

    setSize(1200, 800);
    std::cout << "MainComponent constructor - COMPLETE" << std::endl;
}

MainComponent::~MainComponent() = default;

void MainComponent::paint(juce::Graphics& g)
{
    g.fillAll(getLookAndFeel().findColour(juce::ResizableWindow::backgroundColourId));
}

void MainComponent::resized()
{
    auto bounds = getLocalBounds();

    // Menu bar at the top (standard height 20-25px)
    if (menuBar != nullptr)
    {
        menuBar->setBounds(bounds.removeFromTop(25));
    }

    // Handle Suno browser side panel
    if (sunoBrowser && sunoBrowser->isVisible())
    {
        auto browserWidth = 350;
        sunoBrowser->setBounds(bounds.removeFromRight(browserWidth));
        
        // Resizer bar between browser and main content
        if (resizerBar == nullptr)
        {
            resizerBar = std::make_unique<juce::StretchableLayoutResizerBar>(&verticalLayout, 2, true);
            addAndMakeVisible(resizerBar.get());
        }
        resizerBar->setBounds(bounds.removeFromRight(5));
    }
    else
    {
        resizerBar.reset();
    }

    // Apply layout to remaining components
    juce::Component* components[] = {
        transportBar.get(),
        recordingPanel.get(),
        sessionGrid.get(),
        mixerPanel.get()
    };

    verticalLayout.layOutComponents(components, 4,
                                    bounds.getX(), bounds.getY(),
                                    bounds.getWidth(), bounds.getHeight(),
                                    true, true);
}

bool MainComponent::keyPressed(const juce::KeyPress& key)
{
    // Handle keyboard shortcuts
    const auto modifiers = key.getModifiers();

    // Ctrl+N - New Project
    if (key == juce::KeyPress('n', juce::ModifierKeys::ctrlModifier, 0))
    {
        if (projectManager)
        {
            projectManager->newProject(this);
            return true;
        }
    }

    // Ctrl+O - Open Project
    if (key == juce::KeyPress('o', juce::ModifierKeys::ctrlModifier, 0))
    {
        if (projectManager)
        {
            projectManager->openProject(this);
            return true;
        }
    }

    // Ctrl+S - Save Project
    if (key == juce::KeyPress('s', juce::ModifierKeys::ctrlModifier, 0))
    {
        if (projectManager)
        {
            projectManager->saveProject(this);
            return true;
        }
    }

    // Ctrl+Shift+S - Save Project As
    if (key == juce::KeyPress('s', juce::ModifierKeys::ctrlModifier | juce::ModifierKeys::shiftModifier, 0))
    {
        if (projectManager)
        {
            projectManager->saveProjectAs(this);
            return true;
        }
    }

    // Space - Play/Stop toggle
    if (key == juce::KeyPress::spaceKey)
    {
        auto& engine = EngineBridge::getInstance();
        if (engine.isPlaying())
        {
            engine.stop();
        }
        else
        {
            engine.play();
        }
        return true;
    }

    // Shift+Space - Rewind and Play
    if (key == juce::KeyPress::spaceKey && modifiers.isShiftDown())
    {
        auto& engine = EngineBridge::getInstance();
        engine.setPosition(0.0);
        engine.play();
        return true;
    }

    // Ctrl+R - Record toggle
    if (key == juce::KeyPress('r', juce::ModifierKeys::ctrlModifier, 0))
    {
        auto& engine = EngineBridge::getInstance();
        engine.record();
        return true;
    }

    // Return - Rewind to start
    if (key == juce::KeyPress::returnKey)
    {
        auto& engine = EngineBridge::getInstance();
        engine.setPosition(0.0);
        return true;
    }

    return false; // Let other handlers process
}
