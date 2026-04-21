#include "ProjectManager.h"

// OpenDAW project file extension
const juce::String ProjectManager::defaultProjectLocation = "OpenDAW/Projects";

juce::String ProjectManager::getProjectFileExtension()
{
    return ".opendaw";
}

juce::String ProjectManager::getProjectFileDescription()
{
    return "OpenDAW Project Files (*" + getProjectFileExtension() + ")";
}

ProjectManager::ProjectManager()
{
}

ProjectManager::~ProjectManager()
{
}

bool ProjectManager::hasUnsavedChanges() const
{
    return EngineBridge::getInstance().isProjectModified();
}

bool ProjectManager::confirmDiscardChanges(juce::Component* parentComponent, const juce::String& operation)
{
    if (!hasUnsavedChanges())
        return true; // No unsaved changes, proceed

    juce::String title = "Unsaved Changes";
    juce::String message = "The current project has unsaved changes.\n\nDo you want to save before " + operation + "?";

    // JUCE 7 compatible: Use NativeMessageBox for synchronous dialog
    // NativeMessageBox::showYesNoBox returns: true = yes, false = no
    bool result = juce::NativeMessageBox::showYesNoBox(
        juce::AlertWindow::QuestionIcon,
        title,
        message,
        parentComponent,
        nullptr  // no specific callback needed for sync version
    );

    if (result)
    {
        // User clicked "Yes" (Save)
        return saveProject(parentComponent);
    }
    else
    {
        // User clicked "No" (Don't Save) - proceed without saving
        return true;
    }
}

bool ProjectManager::checkUnsavedAndPrompt(juce::Component* parentComponent, const juce::String& operation)
{
    return confirmDiscardChanges(parentComponent, operation);
}

bool ProjectManager::newProject(juce::Component* parentComponent)
{
    // Check for unsaved changes
    if (!checkUnsavedAndPrompt(parentComponent, "creating a new project"))
        return false;

    auto& engine = EngineBridge::getInstance();

    if (engine.newProject())
    {
        if (onProjectNew)
            onProjectNew();

        return true;
    }

    juce::AlertWindow::showMessageBoxAsync(
        juce::AlertWindow::WarningIcon,
        "Error",
        "Failed to create new project.",
        "OK",
        parentComponent
    );

    return false;
}

bool ProjectManager::openProject(juce::Component* parentComponent)
{
    // Check for unsaved changes
    if (!checkUnsavedAndPrompt(parentComponent, "opening another project"))
        return false;

    auto* chooser = new juce::FileChooser(
        "Open OpenDAW Project",
        getInitialProjectDirectory(),
        getProjectFileDescription()
    );

    chooser->launchAsync(
        juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles,
        [this, chooser, parentComponent](const juce::FileChooser& fc)
    {
        if (fc.getResult() != juce::File())
        {
            auto file = fc.getResult();
            auto& engine = EngineBridge::getInstance();

            if (engine.loadProject(file.getFullPathName()))
            {
                saveProjectDirectory(file.getParentDirectory());

                if (onProjectLoaded)
                    onProjectLoaded(file.getFullPathName());
            }
            else
            {
                juce::AlertWindow::showMessageBoxAsync(
                    juce::AlertWindow::WarningIcon,
                    "Error",
                    "Failed to load project:\n" + file.getFullPathName(),
                    "OK",
                    parentComponent
                );
            }
        }
        delete chooser;
    });

    return true; // Async operation started
}

bool ProjectManager::saveProject(juce::Component* parentComponent)
{
    auto& engine = EngineBridge::getInstance();
    auto currentPath = engine.getCurrentProjectPath();

    // If no current path, do Save As instead
    if (currentPath.isEmpty())
    {
        return saveProjectAs(parentComponent);
    }

    if (engine.saveCurrentProject())
    {
        if (onProjectSaved)
            onProjectSaved(currentPath);

        return true;
    }

    juce::AlertWindow::showMessageBoxAsync(
        juce::AlertWindow::WarningIcon,
        "Error",
        "Failed to save project.",
        "OK",
        parentComponent
    );

    return false;
}

bool ProjectManager::saveProjectAs(juce::Component* parentComponent)
{
    auto* chooser = new juce::FileChooser(
        "Save OpenDAW Project As",
        getInitialProjectDirectory().getChildFile("Untitled" + getProjectFileExtension()),
        getProjectFileDescription()
    );

    chooser->launchAsync(
        juce::FileBrowserComponent::saveMode | juce::FileBrowserComponent::canSelectFiles | juce::FileBrowserComponent::warnAboutOverwriting,
        [this, chooser, parentComponent](const juce::FileChooser& fc)
    {
        if (fc.getResult() != juce::File())
        {
            auto file = fc.getResult();
            auto& engine = EngineBridge::getInstance();

            // Ensure file has correct extension
            juce::File targetFile = file;
            if (!file.getFileExtension().equalsIgnoreCase(getProjectFileExtension()))
            {
                targetFile = file.withFileExtension(getProjectFileExtension());
            }

            if (engine.saveProject(targetFile.getFullPathName()))
            {
                saveProjectDirectory(targetFile.getParentDirectory());

                if (onProjectSaved)
                    onProjectSaved(targetFile.getFullPathName());
            }
            else
            {
                juce::AlertWindow::showMessageBoxAsync(
                    juce::AlertWindow::WarningIcon,
                    "Error",
                    "Failed to save project:\n" + targetFile.getFullPathName(),
                    "OK",
                    parentComponent
                );
            }
        }
        delete chooser;
    });

    return true; // Async operation started
}

juce::File ProjectManager::getInitialProjectDirectory() const
{
    // Try to load from application properties
    juce::PropertiesFile::Options options;
    options.applicationName = "OpenDAW";
    options.filenameSuffix = ".settings";
    options.osxLibrarySubFolder = "Application Support";

    juce::ApplicationProperties appProps;
    appProps.setStorageParameters(options);

    auto* userProps = appProps.getUserSettings();
    if (userProps != nullptr)
    {
        juce::String lastDir = userProps->getValue("lastProjectDirectory", juce::String());
        if (lastDir.isNotEmpty())
        {
            juce::File dir(lastDir);
            if (dir.exists() && dir.isDirectory())
                return dir;
        }
    }

    // Default to user's documents folder
    return juce::File::getSpecialLocation(juce::File::userDocumentsDirectory)
           .getChildFile(defaultProjectLocation);
}

void ProjectManager::saveProjectDirectory(const juce::File& directory)
{
    if (!directory.exists() || !directory.isDirectory())
        return;

    juce::PropertiesFile::Options options;
    options.applicationName = "OpenDAW";
    options.filenameSuffix = ".settings";
    options.osxLibrarySubFolder = "Application Support";

    juce::ApplicationProperties appProps;
    appProps.setStorageParameters(options);

    auto* userProps = appProps.getUserSettings();
    if (userProps != nullptr)
    {
        userProps->setValue("lastProjectDirectory", directory.getFullPathName());
        userProps->saveIfNeeded();
    }
}
