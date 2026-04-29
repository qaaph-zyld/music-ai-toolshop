#include "PluginChainDialog.h"

// ============================================================================
// PluginSlotComponent
// ============================================================================

PluginSlotComponent::PluginSlotComponent(int slotIndex, const EngineBridge::PluginInfo& info)
    : slotIdx(slotIndex), pluginInfo(info)
{
    // Name label
    nameLabel.setText(info.name, juce::dontSendNotification);
    nameLabel.setJustificationType(juce::Justification::centred);
    nameLabel.setFont(juce::Font(12.0f, juce::Font::bold));
    addAndMakeVisible(&nameLabel);

    // Bypass button
    bypassButton.setToggleState(false, juce::dontSendNotification);
    bypassButton.setColour(juce::ToggleButton::tickColourId, juce::Colours::orange);
    bypassButton.onClick = [this] {
        if (onBypass)
            onBypass(bypassButton.getToggleState());
    };
    addAndMakeVisible(&bypassButton);

    // Move left button
    moveLeftButton.setTooltip("Move left");
    moveLeftButton.onClick = [this] {
        if (onMoveLeft)
            onMoveLeft();
    };
    addAndMakeVisible(&moveLeftButton);

    // Move right button
    moveRightButton.setTooltip("Move right");
    moveRightButton.onClick = [this] {
        if (onMoveRight)
            onMoveRight();
    };
    addAndMakeVisible(&moveRightButton);

    // Delete button
    deleteButton.setTooltip("Remove plugin");
    deleteButton.setColour(juce::TextButton::buttonColourId, juce::Colours::darkred);
    deleteButton.onClick = [this] {
        if (onDelete)
            onDelete();
    };
    addAndMakeVisible(&deleteButton);

    setSize(120, 140);
}

void PluginSlotComponent::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds();

    // Background
    g.fillAll(juce::Colour(0xFF4B4B4B));

    // Border
    g.setColour(juce::Colour(0xFF6B6B6B));
    g.drawRect(bounds, 1);

    // Bypass indicator (orange tint when bypassed)
    if (bypassButton.getToggleState())
    {
        g.setColour(juce::Colours::orange.withAlpha(0.1f));
        g.fillAll();
    }
}

void PluginSlotComponent::resized()
{
    auto bounds = getLocalBounds().reduced(5);

    // Name at top
    nameLabel.setBounds(bounds.removeFromTop(40));
    bounds.removeFromTop(10);

    // Bypass button
    bypassButton.setBounds(bounds.removeFromTop(25));
    bounds.removeFromTop(10);

    // Move buttons row
    auto moveRow = bounds.removeFromTop(25);
    moveLeftButton.setBounds(moveRow.removeFromLeft(moveRow.getWidth() / 2).reduced(1));
    moveRightButton.setBounds(moveRow.reduced(1));
    bounds.removeFromTop(10);

    // Delete button at bottom
    deleteButton.setBounds(bounds.removeFromTop(25));
}

void PluginSlotComponent::setBypass(bool bypassed)
{
    bypassButton.setToggleState(bypassed, juce::dontSendNotification);
    repaint();
}

// ============================================================================
// PluginChainDialog
// ============================================================================

PluginChainDialog::PluginChainDialog(int trackIndex, juce::Component* parentComponent)
    : juce::DialogWindow("Plugin Chain - Track " + juce::String(trackIndex + 1),
                         juce::Colours::darkgrey, true, true),
      trackIdx(trackIndex)
{
    setUsingNativeTitleBar(true);
    setResizable(true, true);
    setSize(600, 200);
    centreAroundComponent(parentComponent, getWidth(), getHeight());

    // Slots container (horizontal layout)
    slotsContainer.setSize(600, 160);

    // Viewport to scroll if many plugins
    viewport.setViewedComponent(&slotsContainer, false);
    viewport.setScrollBarsShown(true, true);
    addAndMakeVisible(&viewport);

    // Empty label (shown when no plugins)
    emptyLabel.setJustificationType(juce::Justification::centred);
    slotsContainer.addAndMakeVisible(&emptyLabel);

    // Close button
    closeButton.onClick = [this] {
        closeButtonPressed();
    };
    addAndMakeVisible(&closeButton);

    // Load existing chain
    loadChain();
}

PluginChainDialog::~PluginChainDialog()
{
    viewport.setViewedComponent(nullptr, false);
}

void PluginChainDialog::closeButtonPressed()
{
    setVisible(false);
}

void PluginChainDialog::resized()
{
    auto bounds = getLocalBounds().reduced(10);

    // Close button at bottom
    closeButton.setBounds(bounds.removeFromBottom(30).removeFromRight(100));
    bounds.removeFromBottom(10);

    // Viewport fills the rest
    viewport.setBounds(bounds);

    // Update slots container size
    auto width = juce::jmax(600, static_cast<int>(slotComponents.size()) * 130 + 20);
    slotsContainer.setSize(width, bounds.getHeight() - 20);

    // Layout slots horizontally
    emptyLabel.setBounds(slotsContainer.getLocalBounds());

    int x = 10;
    for (auto& slot : slotComponents)
    {
        slot->setTopLeftPosition(x, 10);
        x += 130;
    }
}

// ============================================================================
// Drag and drop
// ============================================================================

bool PluginChainDialog::isInterestedInDragSource(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    auto desc = dragSourceDetails.description.toString();
    return desc.startsWith("plugin:");
}

void PluginChainDialog::itemDropped(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails)
{
    auto desc = dragSourceDetails.description.toString();
    if (!desc.startsWith("plugin:"))
        return;

    // Parse "plugin:unique_id:name"
    auto parts = juce::StringArray::fromTokens(desc, ":", "");
    if (parts.size() >= 2)
    {
        auto uniqueId = parts[1];
        addPlugin(uniqueId);
    }
}

// ============================================================================
// Chain management
// ============================================================================

void PluginChainDialog::loadChain()
{
    slotComponents.clear();

    auto& engine = EngineBridge::getInstance();
    auto plugins = engine.getPluginChain(trackIdx);

    if (plugins.empty())
    {
        emptyLabel.setVisible(true);
    }
    else
    {
        emptyLabel.setVisible(false);

        for (size_t i = 0; i < plugins.size(); ++i)
        {
            auto slot = std::make_unique<PluginSlotComponent>(static_cast<int>(i), plugins[i]);

            // Get current bypass state
            slot->setBypass(engine.getPluginBypass(trackIdx, static_cast<int>(i)));

            // Wire up callbacks
            const int slotIndex = static_cast<int>(i);

            slot->onDelete = [this, slotIndex] {
                removePlugin(slotIndex);
            };

            slot->onMoveLeft = [this, slotIndex] {
                if (slotIndex > 0)
                    movePlugin(slotIndex, slotIndex - 1);
            };

            slot->onMoveRight = [this, slotIndex] {
                movePlugin(slotIndex, slotIndex + 1);
            };

            slot->onBypass = [this, slotIndex](bool bypassed) {
                toggleBypass(slotIndex, bypassed);
            };

            slotsContainer.addAndMakeVisible(slot.get());
            slotComponents.push_back(std::move(slot));
        }
    }

    resized();
}

void PluginChainDialog::addPlugin(const juce::String& uniqueId)
{
    auto& engine = EngineBridge::getInstance();

    int slot = engine.addPluginToChain(trackIdx, uniqueId);
    if (slot >= 0)
    {
        // Successfully added, reload
        loadChain();
    }
}

void PluginChainDialog::removePlugin(int slotIndex)
{
    auto& engine = EngineBridge::getInstance();

    if (engine.removePluginFromChain(trackIdx, slotIndex))
    {
        loadChain();
    }
}

void PluginChainDialog::movePlugin(int fromSlot, int toSlot)
{
    if (fromSlot == toSlot)
        return;

    auto& engine = EngineBridge::getInstance();

    if (engine.movePluginInChain(trackIdx, fromSlot, toSlot))
    {
        loadChain();
    }
}

void PluginChainDialog::toggleBypass(int slotIndex, bool bypassed)
{
    auto& engine = EngineBridge::getInstance();
    engine.setPluginBypass(trackIdx, slotIndex, bypassed);
}
