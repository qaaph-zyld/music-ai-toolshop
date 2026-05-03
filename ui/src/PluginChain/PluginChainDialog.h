#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "Engine/EngineBridge.h"

/**
 * PluginSlotComponent - Single plugin slot in the chain
 *
 * Displays plugin name with bypass toggle, move buttons, and delete button.
 */
class PluginSlotComponent : public juce::Component
{
public:
    PluginSlotComponent(int slotIndex, const EngineBridge::PluginInfo& info);

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Callbacks
    std::function<void()> onDelete;
    std::function<void()> onMoveLeft;
    std::function<void()> onMoveRight;
    std::function<void(bool)> onBypass;

    void setBypass(bool bypassed);
    bool isBypassed() const { return bypassButton.getToggleState(); }

private:
    int slotIdx;
    EngineBridge::PluginInfo pluginInfo;

    juce::Label nameLabel;
    juce::ToggleButton bypassButton{"Bypass"};
    juce::TextButton deleteButton{"X"};
    juce::TextButton moveLeftButton{"◀"};
    juce::TextButton moveRightButton{"▶"};

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(PluginSlotComponent)
};

/**
 * PluginChainDialog - Modal dialog for managing plugin chain
 *
 * Shows horizontal chain of plugins with ability to add, remove, reorder, and bypass.
 */
class PluginChainDialog : public juce::DialogWindow,
                          public juce::DragAndDropTarget
{
public:
    PluginChainDialog(int trackIndex, juce::Component* parentComponent);
    ~PluginChainDialog() override;

    // DialogWindow override
    void closeButtonPressed() override;
    void resized() override;

    // DragAndDropTarget interface
    bool isInterestedInDragSource(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;
    void itemDropped(const juce::DragAndDropTarget::SourceDetails& dragSourceDetails) override;

    // Load and refresh
    void loadChain();
    void addPlugin(const juce::String& uniqueId);
    void removePlugin(int slotIndex);
    void movePlugin(int fromSlot, int toSlot);
    void toggleBypass(int slotIndex, bool bypassed);

private:
    int trackIdx;

    juce::Viewport viewport;
    juce::Component slotsContainer;
    std::vector<std::unique_ptr<PluginSlotComponent>> slotComponents;

    juce::Label emptyLabel{"emptyLabel", "Drop plugins here or click Refresh to load"};
    juce::TextButton closeButton{"Close"};

    void rebuildSlots();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(PluginChainDialog)
};
