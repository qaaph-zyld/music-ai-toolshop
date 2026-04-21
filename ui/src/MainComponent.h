#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_gui_extra/juce_gui_extra.h>
#include "SessionView/SessionGridComponent.h"
#include "Transport/TransportBar.h"
#include "Mixer/MixerPanel.h"
#include "Recording/RecordingPanel.h"
#include "Project/ProjectManager.h"
#include "SunoBrowser/SunoBrowserComponent.h"
#include "PatternGen/PatternGeneratorDialog.h"

/**
 * MainMenuBarModel - File menu for OpenDAW
 */
class MainMenuBarModel : public juce::MenuBarModel
{
public:
    MainMenuBarModel();
    ~MainMenuBarModel() override;

    juce::StringArray getMenuBarNames() override
    {
        return { "File", "View", "Tools" };
    }

    juce::PopupMenu getMenuForIndex(int menuIndex, const juce::String& menuName) override;
    void menuItemSelected(int menuItemID, int topLevelMenuIndex) override;

    // Callbacks for menu actions
    std::function<void()> onNewProject;
    std::function<void()> onOpenProject;
    std::function<void()> onSaveProject;
    std::function<void()> onSaveProjectAs;
    std::function<void()> onExit;
    std::function<void()> onToggleSunoBrowser;
    std::function<void()> onGeneratePattern;

private:
    juce::PopupMenu createFileMenu();
    juce::PopupMenu createViewMenu();
    juce::PopupMenu createToolsMenu();

    enum MenuIDs
    {
        fileNew = 1001,
        fileOpen,
        fileSave,
        fileSaveAs,
        fileSeparator1,
        fileExit,
        viewSunoBrowser = 2001,
        viewMenu = 2000,
        toolsGeneratePattern = 3001,
        toolsMenu = 3000
    };
};

class MainComponent : public juce::Component
{
public:
    MainComponent();
    ~MainComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    bool keyPressed(const juce::KeyPress& key) override;

private:
    // Menu bar
    std::unique_ptr<MainMenuBarModel> menuBarModel;
    std::unique_ptr<juce::MenuBarComponent> menuBar;

    // Project management
    std::unique_ptr<ProjectManager> projectManager;

    // Main UI sections
    std::unique_ptr<TransportBar> transportBar;
    std::unique_ptr<RecordingPanel> recordingPanel;
    std::unique_ptr<SessionGridComponent> sessionGrid;
    std::unique_ptr<MixerPanel> mixerPanel;
    std::unique_ptr<SunoBrowserComponent> sunoBrowser;

    // Layout dividers
    juce::StretchableLayoutManager verticalLayout;
    std::unique_ptr<juce::StretchableLayoutResizerBar> resizerBar;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(MainComponent)
};
