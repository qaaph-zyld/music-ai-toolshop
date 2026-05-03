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
        return createEditMenu();
    else if (menuIndex == 2)
        return createViewMenu();
    else if (menuIndex == 3)
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
    menu.addItem(fileExport, "Export Audio...");
    menu.addItem(fileExit, "Exit");

    return menu;
}

juce::PopupMenu MainMenuBarModel::createViewMenu()
{
    juce::PopupMenu menu;
    menu.addItem(viewSunoBrowser, "Suno Library");
    menu.addItem(viewPluginBrowser, "Plugin Browser");
    menu.addItem(viewArrangement, "Arrangement View");
    return menu;
}

juce::PopupMenu MainMenuBarModel::createEditMenu()
{
    juce::PopupMenu menu;
    menu.addItem(editDuplicateClip, "Duplicate Clip\tCtrl+D");
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
        case fileExport:
            if (onExportAudio)
                onExportAudio();
            break;
        case viewSunoBrowser:
            if (onToggleSunoBrowser)
                onToggleSunoBrowser();
            break;
        case viewPluginBrowser:
            if (onTogglePluginBrowser)
                onTogglePluginBrowser();
            break;
        case viewArrangement:
            if (onToggleArrangementView)
                onToggleArrangementView();
            break;
        case toolsGeneratePattern:
            if (onGeneratePattern)
                onGeneratePattern();
            break;
        case editDuplicateClip:
            if (onDuplicateClip)
                onDuplicateClip();
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

    std::cout << "MainComponent: Creating TimeSignatureTrack..." << std::endl;
    timeSignatureTrack = std::make_unique<TimeSignatureTrack>();
    addAndMakeVisible(timeSignatureTrack.get());
    std::cout << "MainComponent: TimeSignatureTrack created" << std::endl;

    std::cout << "MainComponent: Creating TempoAutomationTrack..." << std::endl;
    tempoAutomationTrack = std::make_unique<TempoAutomationTrack>();
    addAndMakeVisible(tempoAutomationTrack.get());
    std::cout << "MainComponent: TempoAutomationTrack created" << std::endl;

    std::cout << "MainComponent: Creating LoopMarkersComponent..." << std::endl;
    loopMarkers = std::make_unique<LoopMarkersComponent>();
    addAndMakeVisible(loopMarkers.get());
    std::cout << "MainComponent: LoopMarkersComponent created" << std::endl;

    std::cout << "MainComponent: Creating RecordingPanel..." << std::endl;
    recordingPanel = std::make_unique<RecordingPanel>();
    addAndMakeVisible(recordingPanel.get());
    std::cout << "MainComponent: RecordingPanel created" << std::endl;

    std::cout << "MainComponent: Creating SessionGrid..." << std::endl;
    sessionGrid = std::make_unique<SessionGridComponent>(8, 16);
    addAndMakeVisible(sessionGrid.get());
    std::cout << "MainComponent: SessionGrid created" << std::endl;

    std::cout << "MainComponent: Creating ArrangementTrack..." << std::endl;
    arrangementTrack = std::make_unique<ArrangementTrack>();
    arrangementTrack->setVisible(false);  // Hidden by default (Session View is primary)
    addAndMakeVisible(arrangementTrack.get());
    std::cout << "MainComponent: ArrangementTrack created" << std::endl;

    std::cout << "MainComponent: Creating MixerPanel..." << std::endl;
    mixerPanel = std::make_unique<MixerPanel>(8);
    addAndMakeVisible(mixerPanel.get());
    std::cout << "MainComponent: MixerPanel created" << std::endl;

    std::cout << "MainComponent: Creating SunoBrowser..." << std::endl;
    sunoBrowser = std::make_unique<SunoBrowserComponent>();
    sunoBrowser->setVisible(false);
    addAndMakeVisible(sunoBrowser.get());
    std::cout << "MainComponent: SunoBrowser created" << std::endl;

    std::cout << "MainComponent: Creating PluginBrowser..." << std::endl;
    pluginBrowser = std::make_unique<PluginBrowserComponent>();
    pluginBrowser->setVisible(false);
    addAndMakeVisible(pluginBrowser.get());
    std::cout << "MainComponent: PluginBrowser created" << std::endl;

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

    menuBarModel->onTogglePluginBrowser = [this]() {
        if (pluginBrowser)
        {
            pluginBrowser->setVisible(!pluginBrowser->isVisible());
            pluginBrowser->refreshPlugins();
            resized();
        }
    };

    menuBarModel->onToggleArrangementView = [this]() {
        if (arrangementTrack && sessionGrid)
        {
            showingArrangementView = !showingArrangementView;
            arrangementTrack->setVisible(showingArrangementView);
            sessionGrid->setVisible(!showingArrangementView);
            
            // Initialize arrangement on first show
            if (showingArrangementView)
            {
                auto& engine = EngineBridge::getInstance();
                engine.initArrangement(8);
                
                // Sync playhead position
                arrangementTrack->setPlayheadPosition(engine.getCurrentBeat());
            }
            
            resized();
        }
    };

    // Wire up File menu - Export Audio
    menuBarModel->onExportAudio = [this]() {
        auto dialog = std::make_unique<ExportDialog>(this);
        dialog->onExportComplete = [this](bool success, const juce::String& message) {
            juce::AlertWindow::showMessageBoxAsync(
                success ? juce::AlertWindow::InfoIcon : juce::AlertWindow::WarningIcon,
                success ? "Export Complete" : "Export Failed",
                message
            );
        };
        dialog.release();
    };

    // Wire up Edit menu - Duplicate Clip
    menuBarModel->onDuplicateClip = [this]() {
        auto& engine = EngineBridge::getInstance();
        
        // Get selected clip from session grid (track 0, scene 0 for now)
        int fromTrack = 0;
        int fromScene = 0;
        int toTrack = 0;
        int toScene = 1;  // Duplicate to next scene
        
        if (engine.duplicateMidiClip(fromTrack, fromScene, toTrack, toScene))
        {
            // Update UI to show duplicated clip
            sessionGrid->setClip(toTrack, toScene, "Duplicated Clip", juce::Colours::green);
            std::cout << "MainComponent: Clip duplicated from (" << fromTrack << "," << fromScene 
                      << ") to (" << toTrack << "," << toScene << ")" << std::endl;
        }
        else
        {
            std::cerr << "MainComponent: Failed to duplicate clip" << std::endl;
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

    // Wire recording completion to create clip - Phase 6 (MIDI Recording Integration)
    recordingPanel->onRecordingComplete = [this](int track, int scene, const juce::Array<EngineBridge::RecordedNote>& notes) {
        juce::Colour clipColor = juce::Colours::cyan;
        sessionGrid->setClip(track, scene, "MIDI Recording", clipColor);

        // Create MIDI clip in the engine with recorded notes
        if (!notes.isEmpty())
        {
            auto& engine = EngineBridge::getInstance();

            // Convert JUCE Array to std::vector for EngineBridge
            std::vector<EngineBridge::RecordedNote> notesVector;
            notesVector.reserve(notes.size());
            for (int i = 0; i < notes.size(); ++i)
            {
                notesVector.push_back(notes[i]);
            }

            bool success = engine.createMidiClip(track, scene, notesVector, "MIDI Recording");
            if (!success)
            {
                std::cerr << "MainComponent: Failed to create MIDI clip in engine" << std::endl;
            }
            else
            {
                std::cout << "MainComponent: Created MIDI clip with " << notes.size() << " notes at track "
                          << (track + 1) << ", scene " << (scene + 1) << std::endl;
            }
        }
    };

    // Wire up LoopMarkersComponent callbacks - Phase 10.2
    auto refreshLoopRegions = [this]() {
        auto& engine = EngineBridge::getInstance();
        auto regions = engine.getAllLoopRegions();

        std::vector<LoopRegionView> views;
        juce::String activeId = engine.getActiveLoopRegionId();
        for (const auto& region : regions)
        {
            LoopRegionView view;
            view.id = region.id;
            view.name = region.name;
            view.startBeat = region.startBeat;
            view.endBeat = region.endBeat;
            view.enabled = region.enabled;
            view.color = juce::Colour::fromString(region.color);
            view.isActive = (region.id == activeId);
            views.push_back(view);
        }
        loopMarkers->setLoopRegions(views);
        loopMarkers->setLoopingEnabled(engine.isLoopingEnabled());
    };

    loopMarkers->onRegionMoved = [this, refreshLoopRegions](const juce::String& id, double newStart, double newEnd) {
        auto& engine = EngineBridge::getInstance();
        engine.updateLoopRegion(id, newStart, newEnd);
        refreshLoopRegions();
    };

    loopMarkers->onRegionSelected = [this, refreshLoopRegions](const juce::String& id) {
        auto& engine = EngineBridge::getInstance();
        engine.setActiveLoopRegion(id);
        refreshLoopRegions();
    };

    loopMarkers->onRegionCreated = [this, refreshLoopRegions](double start, double end, const juce::String& name) {
        auto& engine = EngineBridge::getInstance();
        engine.createLoopRegion(name, start, end);
        refreshLoopRegions();
    };

    loopMarkers->onRegionDeleted = [this, refreshLoopRegions](const juce::String& id) {
        auto& engine = EngineBridge::getInstance();
        engine.deleteLoopRegion(id);
        refreshLoopRegions();
    };

    loopMarkers->onRegionRenamed = [this, refreshLoopRegions](const juce::String& id, const juce::String& newName) {
        auto& engine = EngineBridge::getInstance();
        engine.renameLoopRegion(id, newName);
        refreshLoopRegions();
    };

    loopMarkers->onRegionEnabledChanged = [this, refreshLoopRegions](const juce::String& id, bool enabled) {
        auto& engine = EngineBridge::getInstance();
        engine.setLoopRegionEnabled(id, enabled);
        refreshLoopRegions();
    };

    loopMarkers->onLoopingEnabledChanged = [this, refreshLoopRegions](bool enabled) {
        auto& engine = EngineBridge::getInstance();
        engine.setLoopingEnabled(enabled);
        refreshLoopRegions();
    };

    // Initial load of loop regions
    refreshLoopRegions();

    // Wire up TimeSignatureTrack callbacks - Phase 10.4
    auto refreshTimeSignatures = [this]() {
        auto& engine = EngineBridge::getInstance();
        auto sigs = engine.getAllTimeSignatureChanges();

        std::vector<TimeSignatureChange> changes;
        for (const auto& sig : sigs)
        {
            TimeSignatureChange change;
            change.bar = sig.bar;
            change.numerator = sig.numerator;
            change.denominator = sig.denominator;
            changes.push_back(change);
        }
        timeSignatureTrack->setTimeSignatureChanges(changes);
    };

    timeSignatureTrack->onChangeAdded = [this, refreshTimeSignatures](uint32_t bar, uint8_t num, uint8_t den) {
        auto& engine = EngineBridge::getInstance();
        engine.addTimeSignatureChange(bar, num, den);
        refreshTimeSignatures();
    };

    timeSignatureTrack->onChangeRemoved = [this, refreshTimeSignatures](uint32_t bar) {
        auto& engine = EngineBridge::getInstance();
        engine.removeTimeSignatureChange(bar);
        refreshTimeSignatures();
    };

    timeSignatureTrack->onChangeModified = [this, refreshTimeSignatures](uint32_t bar, uint8_t num, uint8_t den) {
        auto& engine = EngineBridge::getInstance();
        engine.removeTimeSignatureChange(bar);
        engine.addTimeSignatureChange(bar, num, den);
        refreshTimeSignatures();
    };

    // Initial load of time signatures
    refreshTimeSignatures();

    // Wire up TempoAutomationTrack callbacks - Phase 10.3
    auto refreshTempoBreakpoints = [this]() {
        auto& engine = EngineBridge::getInstance();

        std::vector<TempoBreakpoint> breakpoints;
        int count = engine.getTempoBreakpointCount();
        for (int i = 0; i < count; ++i)
        {
            auto bp = engine.getTempoBreakpointAt(i);
            TempoBreakpoint viewBp;
            viewBp.beat = bp.beat;
            viewBp.bpm = bp.bpm;
            viewBp.interpolation = bp.interpolation;
            breakpoints.push_back(viewBp);
        }
        tempoAutomationTrack->setBreakpoints(breakpoints);
    };

    tempoAutomationTrack->onBreakpointAdded = [this, refreshTempoBreakpoints](double beat, double bpm, int interpolation) {
        auto& engine = EngineBridge::getInstance();
        engine.addTempoBreakpoint(beat, bpm, interpolation);
        refreshTempoBreakpoints();
    };

    tempoAutomationTrack->onBreakpointRemoved = [this, refreshTempoBreakpoints](double beat) {
        auto& engine = EngineBridge::getInstance();
        engine.removeTempoBreakpoint(beat);
        refreshTempoBreakpoints();
    };

    tempoAutomationTrack->onBreakpointModified = [this, refreshTempoBreakpoints](double oldBeat, double newBeat, double newBpm, int interpolation) {
        auto& engine = EngineBridge::getInstance();
        engine.updateTempoBreakpoint(oldBeat, newBeat, newBpm, interpolation);
        refreshTempoBreakpoints();
    };

    // Initial tempo automation setup
    {
        auto& engine = EngineBridge::getInstance();
        engine.initTempoAutomation(120.0); // Initialize with default 120 BPM
        refreshTempoBreakpoints();
    }

    // Wire up ArrangementTrack callbacks - Phase 10.5
    auto refreshArrangementClips = [this]() {
        auto& engine = EngineBridge::getInstance();
        
        arrangementTrack->clearAllClips();
        
        uint32_t trackCount = engine.getArrangementTrackCount();
        for (uint32_t trackIdx = 0; trackIdx < trackCount; ++trackIdx)
        {
            auto clips = engine.getAllArrangementClips(trackIdx);
            for (const auto& clip : clips)
            {
                ArrangementClipInfo info;
                info.id = clip.id;
                info.trackIndex = clip.trackIndex;
                info.startBeat = clip.startBeat;
                info.durationBeats = clip.durationBeats;
                info.name = juce::String(clip.name);
                info.isAudio = clip.isAudio;
                arrangementTrack->addClip(info);
            }
        }
    };
    
    arrangementTrack->onClipAdded = [this, refreshArrangementClips](int trackIdx, double startBeat, const juce::String& name, bool isAudio) {
        auto& engine = EngineBridge::getInstance();
        
        if (isAudio)
        {
            engine.addAudioClipToArrangement(trackIdx, startBeat, name, 4.0, "");
        }
        else
        {
            engine.addMidiClipToArrangement(trackIdx, startBeat, name, 4.0);
        }
        refreshArrangementClips();
    };
    
    arrangementTrack->onClipRemoved = [this, refreshArrangementClips](uint64_t clipId) {
        auto& engine = EngineBridge::getInstance();
        
        // Find which track contains this clip
        uint32_t trackCount = engine.getArrangementTrackCount();
        for (uint32_t trackIdx = 0; trackIdx < trackCount; ++trackIdx)
        {
            auto clips = engine.getAllArrangementClips(trackIdx);
            for (const auto& clip : clips)
            {
                if (clip.id == clipId)
                {
                    engine.removeClipFromArrangement(trackIdx, clipId);
                    refreshArrangementClips();
                    return;
                }
            }
        }
    };
    
    arrangementTrack->onClipMoved = [this, refreshArrangementClips](uint64_t clipId, int newTrackIdx, double newStartBeat) {
        auto& engine = EngineBridge::getInstance();
        
        // Find current track and move clip
        uint32_t trackCount = engine.getArrangementTrackCount();
        for (uint32_t trackIdx = 0; trackIdx < trackCount; ++trackIdx)
        {
            auto clips = engine.getAllArrangementClips(trackIdx);
            for (const auto& clip : clips)
            {
                if (clip.id == clipId)
                {
                    engine.moveClipInArrangement(trackIdx, clipId, newTrackIdx, newStartBeat);
                    refreshArrangementClips();
                    return;
                }
            }
        }
    };
    
    arrangementTrack->onClipResized = [this, refreshArrangementClips](uint64_t clipId, double newDuration) {
        auto& engine = EngineBridge::getInstance();
        
        // Find which track contains this clip
        uint32_t trackCount = engine.getArrangementTrackCount();
        for (uint32_t trackIdx = 0; trackIdx < trackCount; ++trackIdx)
        {
            auto clips = engine.getAllArrangementClips(trackIdx);
            for (const auto& clip : clips)
            {
                if (clip.id == clipId)
                {
                    engine.resizeClipInArrangement(trackIdx, clipId, newDuration);
                    refreshArrangementClips();
                    return;
                }
            }
        }
    };
    
    arrangementTrack->onClipSelected = [this](uint64_t clipId) {
        (void)clipId;
        // Handle clip selection - could show clip info or properties
    };
    
    arrangementTrack->onClipDoubleClicked = [this](uint64_t clipId) {
        // Find the clip info
        auto& engine = EngineBridge::getInstance();
        uint32_t trackCount = engine.getArrangementTrackCount();
        EngineBridge::ArrangementClipInfo clipInfo;
        bool found = false;
        
        for (uint32_t trackIdx = 0; trackIdx < trackCount && !found; ++trackIdx)
        {
            auto clips = engine.getAllArrangementClips(trackIdx);
            for (const auto& clip : clips)
            {
                if (clip.id == clipId)
                {
                    clipInfo = clip;
                    found = true;
                    break;
                }
            }
        }
        
        if (found)
        {
            auto dialog = std::make_unique<ClipEditorDialog>(this, clipInfo);
            dialog->onClipEdited = [this, clipId](const juce::String& newName, juce::Colour newColor, bool isAudio) {
                (void)newColor;
                (void)isAudio;
                // TODO: Update clip name in engine via EngineBridge
                std::cout << "Clip " << (int64_t)clipId << " renamed to: " << newName.toStdString() << std::endl;
            };
            dialog.release();  // Dialog self-destructs when closed
        }
    };
    
    arrangementTrack->onEmptyAreaDoubleClicked = [this, refreshArrangementClips](double beat, int trackIdx) {
        // Add a MIDI clip at the clicked position
        auto& engine = EngineBridge::getInstance();
        engine.addMidiClipToArrangement(trackIdx, beat, "New Clip", 4.0);
        refreshArrangementClips();
    };
    
    // Session H: Wire up session clip dropped callback
    arrangementTrack->onSessionClipDropped = [this, refreshArrangementClips](int sourceTrack, int sourceScene, int targetTrack, double targetBeat) {
        auto& engine = EngineBridge::getInstance();
        
        // Create a clip in the arrangement based on session clip
        // Use session grid clip name if available
        juce::String clipName = "Session Clip " + juce::String(sourceTrack + 1) + "." + juce::String(sourceScene + 1);
        
        // Add as MIDI clip for now (could be enhanced to detect audio clips)
        engine.addMidiClipToArrangement(targetTrack, targetBeat, clipName, 4.0);
        
        std::cout << "Session clip dropped: track " << sourceTrack << " scene " << sourceScene 
                  << " -> arrangement track " << targetTrack << " beat " << targetBeat << std::endl;
        
        refreshArrangementClips();
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

    // Handle Plugin browser side panel (left side)
    if (pluginBrowser && pluginBrowser->isVisible())
    {
        auto browserWidth = 300;
        pluginBrowser->setBounds(bounds.removeFromLeft(browserWidth));
    }

    // Handle Suno browser side panel (right side)
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
    // Note: LoopMarkersComponent has fixed height, others use verticalLayout
    auto topBounds = bounds.removeFromTop(60); // Transport bar
    transportBar->setBounds(topBounds);

    // Recording panel
    auto recordingBounds = bounds.removeFromTop(80);
    recordingPanel->setBounds(recordingBounds);

    // Time signature track (above tempo automation) - fixed 24px height
    auto timeSigBounds = bounds.removeFromTop(24);
    timeSignatureTrack->setBounds(timeSigBounds);

    // Tempo automation track (above loop markers) - fixed 40px height
    auto tempoBounds = bounds.removeFromTop(40);
    tempoAutomationTrack->setBounds(tempoBounds);

    // Loop markers (timeline ruler) - fixed height
    auto loopMarkerBounds = bounds.removeFromTop(60);
    loopMarkers->setBounds(loopMarkerBounds);

    // Remaining space split between session grid and mixer
    juce::Component* mainComponents[] = {
        sessionGrid.get(),
        mixerPanel.get()
    };

    verticalLayout.layOutComponents(mainComponents, 2,
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

    // Ctrl+D - Duplicate Clip
    if (key == juce::KeyPress('d', juce::ModifierKeys::ctrlModifier, 0))
    {
        if (menuBarModel->onDuplicateClip)
        {
            menuBarModel->onDuplicateClip();
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

    // Ctrl+Shift+P - Toggle Plugin Browser
    if (key == juce::KeyPress('P', juce::ModifierKeys::ctrlModifier | juce::ModifierKeys::shiftModifier, 0))
    {
        if (menuBarModel->onTogglePluginBrowser)
        {
            menuBarModel->onTogglePluginBrowser();
            return true;
        }
    }

    return false; // Let other handlers process
}
