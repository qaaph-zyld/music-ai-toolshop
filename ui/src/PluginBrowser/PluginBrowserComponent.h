#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "Engine/EngineBridge.h"

/**
 * PluginBrowserComponent - Searchable plugin list with drag-and-drop support
 *
 * A side panel component that displays available audio plugins from the registry.
 * Supports live search filtering and drag-to-channel-strip functionality.
 */
class PluginBrowserComponent : public juce::Component,
                               public juce::TableListBoxModel,
                               public juce::TextEditor::Listener
{
public:
    PluginBrowserComponent();
    ~PluginBrowserComponent() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // TableListBoxModel interface
    int getNumRows() override;
    void paintRowBackground(juce::Graphics& g, int rowNumber, int width, int height, bool rowIsSelected) override;
    void paintCell(juce::Graphics& g, int rowNumber, int columnId, int width, int height, bool rowIsSelected) override;
    juce::Component* refreshComponentForCell(int rowNumber, int columnId, bool isRowSelected,
                                              juce::Component* existingComponentToUpdate) override;
    void selectedRowsChanged(int lastRowSelected) override;

    // TextEditor::Listener
    void textEditorTextChanged(juce::TextEditor& editor) override;

    // Drag and drop support
    void startDrag(const int rowIndex);

    // Refresh plugin list
    void refreshPlugins();

private:
    enum ColumnIds
    {
        NameColumn = 1,
        VendorColumn,
        FormatColumn
    };

    juce::Label titleLabel;
    juce::TextEditor searchEditor;
    juce::TextButton refreshButton;
    juce::TableListBox pluginTable;
    juce::Label statusLabel;

    std::vector<EngineBridge::PluginInfo> allPlugins;
    std::vector<EngineBridge::PluginInfo> filteredPlugins;

    void filterPlugins(const juce::String& query);
    juce::String formatToString(int format) const;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(PluginBrowserComponent)
};
