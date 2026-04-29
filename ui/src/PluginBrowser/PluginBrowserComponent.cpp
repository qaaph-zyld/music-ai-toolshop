#include "PluginBrowserComponent.h"

PluginBrowserComponent::PluginBrowserComponent()
{
    // Title
    titleLabel.setText("Plugin Browser", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(18.0f, juce::Font::bold));
    addAndMakeVisible(&titleLabel);

    // Search
    searchEditor.setTextToShowWhenEmpty("Search plugins...", juce::Colours::grey);
    searchEditor.addListener(this);
    addAndMakeVisible(&searchEditor);

    // Refresh button
    refreshButton.setButtonText("Refresh");
    refreshButton.onClick = [this] { refreshPlugins(); };
    addAndMakeVisible(&refreshButton);

    // Table setup
    pluginTable.setModel(this);
    pluginTable.setColour(juce::ListBox::outlineColourId, juce::Colours::grey);
    pluginTable.setOutlineThickness(1);
    pluginTable.setMultipleSelectionEnabled(false);

    // Add columns
    pluginTable.getHeader().addColumn("Name", NameColumn, 150, 80, 300, juce::TableHeaderComponent::defaultFlags);
    pluginTable.getHeader().addColumn("Vendor", VendorColumn, 100, 60, 200, juce::TableHeaderComponent::defaultFlags);
    pluginTable.getHeader().addColumn("Format", FormatColumn, 60, 50, 80, juce::TableHeaderComponent::defaultFlags);

    addAndMakeVisible(&pluginTable);

    // Status label
    statusLabel.setText("Click Refresh to load plugins", juce::dontSendNotification);
    statusLabel.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(&statusLabel);
}

PluginBrowserComponent::~PluginBrowserComponent()
{
    searchEditor.removeListener(this);
}

void PluginBrowserComponent::paint(juce::Graphics& g)
{
    g.fillAll(getLookAndFeel().findColour(juce::ResizableWindow::backgroundColourId));
}

void PluginBrowserComponent::resized()
{
    auto area = getLocalBounds().reduced(10);

    // Title at top
    titleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(10);

    // Search row
    auto searchRow = area.removeFromTop(30);
    searchEditor.setBounds(searchRow.removeFromLeft(searchRow.getWidth() - 80));
    searchRow.removeFromLeft(5);
    refreshButton.setBounds(searchRow);
    area.removeFromTop(10);

    // Status (when empty)
    if (filteredPlugins.empty() && !allPlugins.empty())
    {
        statusLabel.setBounds(area.removeFromTop(30));
        area.removeFromTop(10);
    }

    // Table fills remaining space
    pluginTable.setBounds(area);
}

// ============================================================================
// TableListBoxModel interface
// ============================================================================

int PluginBrowserComponent::getNumRows()
{
    return static_cast<int>(filteredPlugins.size());
}

void PluginBrowserComponent::paintRowBackground(juce::Graphics& g, int rowNumber, int width, int height, bool rowIsSelected)
{
    (void)width;
    (void)height;

    if (rowIsSelected)
        g.fillAll(juce::Colours::lightblue.withAlpha(0.3f));
    else if (rowNumber % 2 == 0)
        g.fillAll(juce::Colours::white.withAlpha(0.05f));
}

void PluginBrowserComponent::paintCell(juce::Graphics& g, int rowNumber, int columnId, int width, int height, bool rowIsSelected)
{
    if (rowNumber < 0 || rowNumber >= static_cast<int>(filteredPlugins.size()))
        return;

    const auto& plugin = filteredPlugins[rowNumber];
    juce::String text;

    switch (columnId)
    {
        case NameColumn: text = plugin.name; break;
        case VendorColumn: text = plugin.vendor; break;
        case FormatColumn: text = formatToString(plugin.format); break;
        default: return;
    }

    g.setColour(rowIsSelected ? juce::Colours::black : juce::Colours::white);
    g.setFont(14.0f);
    g.drawText(text, 5, 0, width - 10, height, juce::Justification::centredLeft, true);
}

juce::Component* PluginBrowserComponent::refreshComponentForCell(int rowNumber, int columnId, bool isRowSelected,
                                                                  juce::Component* existingComponentToUpdate)
{
    (void)rowNumber;
    (void)columnId;
    (void)isRowSelected;
    (void)existingComponentToUpdate;
    return nullptr;  // Simple text cells, no custom components needed
}

void PluginBrowserComponent::selectedRowsChanged(int lastRowSelected)
{
    (void)lastRowSelected;
    // Selection changed, could trigger preview or info display
}

// ============================================================================
// TextEditor::Listener
// ============================================================================

void PluginBrowserComponent::textEditorTextChanged(juce::TextEditor& editor)
{
    if (&editor == &searchEditor)
    {
        filterPlugins(searchEditor.getText());
    }
}

// ============================================================================
// Plugin management
// ============================================================================

void PluginBrowserComponent::refreshPlugins()
{
    auto& engine = EngineBridge::getInstance();

    statusLabel.setText("Loading plugins...", juce::dontSendNotification);

    allPlugins = engine.scanPluginRegistry();
    filteredPlugins = allPlugins;

    if (allPlugins.empty())
    {
        statusLabel.setText("No plugins found", juce::dontSendNotification);
    }
    else
    {
        statusLabel.setText(juce::String(allPlugins.size()) + " plugins loaded", juce::dontSendNotification);
    }

    pluginTable.updateContent();
    resized();
}

void PluginBrowserComponent::filterPlugins(const juce::String& query)
{
    if (query.isEmpty())
    {
        filteredPlugins = allPlugins;
    }
    else
    {
        filteredPlugins.clear();
        auto lowerQuery = query.toLowerCase();

        for (const auto& plugin : allPlugins)
        {
            if (plugin.name.toLowerCase().contains(lowerQuery) ||
                plugin.vendor.toLowerCase().contains(lowerQuery))
            {
                filteredPlugins.push_back(plugin);
            }
        }
    }

    pluginTable.updateContent();
}

juce::String PluginBrowserComponent::formatToString(int format) const
{
    switch (format)
    {
        case 0: return "VST3";
        case 1: return "AU";
        case 2: return "Internal";
        default: return "Unknown";
    }
}

// ============================================================================
// Drag and drop
// ============================================================================

void PluginBrowserComponent::startDrag(const int rowIndex)
{
    if (rowIndex < 0 || rowIndex >= static_cast<int>(filteredPlugins.size()))
        return;

    const auto& plugin = filteredPlugins[rowIndex];

    // Create drag description with plugin unique ID
    juce::String dragDesc = "plugin:" + plugin.uniqueId + ":" + plugin.name;

    auto dragImage = juce::Image(juce::Image::ARGB, 200, 30, true);
    juce::Graphics g(dragImage);
    g.fillAll(juce::Colours::darkgrey);
    g.setColour(juce::Colours::white);
    g.setFont(14.0f);
    g.drawText(plugin.name, 10, 5, 180, 20, juce::Justification::centredLeft);

    beginDragAutoRepeat(50);
    juce::DragAndDropContainer::performExternalDragDropOfText(dragDesc, false, nullptr);
}
