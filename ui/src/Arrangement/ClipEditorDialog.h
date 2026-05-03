#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include "../Engine/EngineBridge.h"

class ClipEditorDialog : public juce::DialogWindow,
                        public juce::Button::Listener,
                        public juce::ComboBox::Listener
{
public:
    ClipEditorDialog(juce::Component* parent, const EngineBridge::ArrangementClipInfo& clipInfo);
    ~ClipEditorDialog() override;

    void paint(juce::Graphics& g) override;
    void resized() override;
    void buttonClicked(juce::Button* button) override;
    void comboBoxChanged(juce::ComboBox* comboBox) override;
    void closeButtonPressed() override;

    // Callback when clip is edited
    std::function<void(const juce::String& newName, juce::Colour newColor, bool isAudio)> onClipEdited;

private:
    // Clip data
    uint64_t clipId;
    juce::String originalName;
    juce::Colour originalColor;
    bool originalIsAudio;

    // UI Components
    juce::Label titleLabel;
    juce::Label nameLabel;
    juce::TextEditor nameEditor;
    juce::Label typeLabel;
    juce::Label typeValueLabel;
    juce::Label colorLabel;
    juce::ComboBox colorComboBox;
    juce::TextButton okButton;
    juce::TextButton cancelButton;

    // Color options
    juce::StringArray colorNames;
    std::vector<juce::Colour> colorValues;

    void setupColorOptions();
    int findColorIndex(juce::Colour color);

    // Layout constants
    static constexpr int dialogWidth = 350;
    static constexpr int dialogHeight = 220;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ClipEditorDialog)
};
