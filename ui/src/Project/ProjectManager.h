#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "../Engine/EngineBridge.h"

/**
 * ProjectManager - Handles project-related UI dialogs and operations
 *
 * This class provides file dialogs for New, Open, Save, and Save As operations,
 * integrating with the EngineBridge project management API.
 */
class ProjectManager
{
public:
    ProjectManager();
    ~ProjectManager();

    // Project operations - these show dialogs and execute via EngineBridge
    bool newProject(juce::Component* parentComponent);
    bool openProject(juce::Component* parentComponent);
    bool saveProject(juce::Component* parentComponent);
    bool saveProjectAs(juce::Component* parentComponent);

    // Check if project has unsaved changes
    bool hasUnsavedChanges() const;

    // Show confirmation dialog for unsaved changes
    // Returns: true = proceed with operation, false = cancel
    bool confirmDiscardChanges(juce::Component* parentComponent, const juce::String& operation);

    // Get the file extension filter for OpenDAW projects
    static juce::String getProjectFileExtension();
    static juce::String getProjectFileDescription();

    // Callbacks for UI integration
    std::function<void(const juce::String& projectPath)> onProjectLoaded;
    std::function<void(const juce::String& projectPath)> onProjectSaved;
    std::function<void()> onProjectNew;

private:
    // Get the last used project directory (or default)
    juce::File getInitialProjectDirectory() const;

    // Save the directory for future use
    void saveProjectDirectory(const juce::File& directory);

    // Check for unsaved changes and prompt if needed
    // Returns false if user cancels the operation
    bool checkUnsavedAndPrompt(juce::Component* parentComponent, const juce::String& operation);

    // Default project location
    static const juce::String defaultProjectLocation;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ProjectManager)
};
