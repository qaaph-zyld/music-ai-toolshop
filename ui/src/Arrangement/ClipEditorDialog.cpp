#include "ClipEditorDialog.h"
#include "../Engine/EngineBridge.h"
#include <iostream>

ClipEditorDialog::ClipEditorDialog(juce::Component* parent, const EngineBridge::ArrangementClipInfo& clipInfo)
    : juce::DialogWindow("Edit Clip", juce::Colours::darkgrey, true, false),
      clipId(clipInfo.id),
      originalName(clipInfo.name),
      originalIsAudio(clipInfo.isAudio)
{
    std::cout << "ClipEditorDialog: Creating for clip " << (int64_t)clipId << std::endl;

    // Set up color based on clip type
    if (clipInfo.isAudio)
    {
        originalColor = juce::Colour(0xFF6B8E9F);  // Blue for audio
    }
    else
    {
        originalColor = juce::Colour(0xFF8E9F6B);  // Green for MIDI
    }

    // Title
    titleLabel.setText("Edit Clip Properties", juce::dontSendNotification);
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    addAndMakeVisible(&titleLabel);

    // Name field
    nameLabel.setText("Name:", juce::dontSendNotification);
    nameLabel.setJustificationType(juce::Justification::right);
    addAndMakeVisible(&nameLabel);

    nameEditor.setText(originalName);
    addAndMakeVisible(&nameEditor);

    // Type display
    typeLabel.setText("Type:", juce::dontSendNotification);
    typeLabel.setJustificationType(juce::Justification::right);
    addAndMakeVisible(&typeLabel);

    typeValueLabel.setText(originalIsAudio ? "Audio" : "MIDI", juce::dontSendNotification);
    addAndMakeVisible(&typeValueLabel);

    // Color picker
    colorLabel.setText("Color:", juce::dontSendNotification);
    colorLabel.setJustificationType(juce::Justification::right);
    addAndMakeVisible(&colorLabel);

    setupColorOptions();
    addAndMakeVisible(&colorComboBox);
    colorComboBox.addListener(this);

    // Buttons
    okButton.setButtonText("OK");
    okButton.addListener(this);
    addAndMakeVisible(&okButton);

    cancelButton.setButtonText("Cancel");
    cancelButton.addListener(this);
    addAndMakeVisible(&cancelButton);

    // Set dialog size and position
    setSize(dialogWidth, dialogHeight);
    centreAroundComponent(parent, dialogWidth, dialogHeight);

    // Show modal
    setVisible(true);
    setAlwaysOnTop(true);
}

ClipEditorDialog::~ClipEditorDialog()
{
    std::cout << "ClipEditorDialog: Destroyed" << std::endl;
}

void ClipEditorDialog::setupColorOptions()
{
    // Color options
    colorNames.add("Green (MIDI)");
    colorValues.push_back(juce::Colour(0xFF8E9F6B));

    colorNames.add("Blue (Audio)");
    colorValues.push_back(juce::Colour(0xFF6B8E9F));

    colorNames.add("Red");
    colorValues.push_back(juce::Colours::lightcoral);

    colorNames.add("Yellow");
    colorValues.push_back(juce::Colours::lightyellow);

    colorNames.add("Purple");
    colorValues.push_back(juce::Colours::plum);

    colorNames.add("Orange");
    colorValues.push_back(juce::Colours::lightsalmon);

    colorNames.add("Cyan");
    colorValues.push_back(juce::Colours::lightcyan);

    for (int i = 0; i < colorNames.size(); ++i)
    {
        colorComboBox.addItem(colorNames[i], i + 1);
    }

    // Select current color
    int currentIndex = findColorIndex(originalColor);
    colorComboBox.setSelectedItemIndex(currentIndex, juce::dontSendNotification);
}

int ClipEditorDialog::findColorIndex(juce::Colour color)
{
    for (size_t i = 0; i < colorValues.size(); ++i)
    {
        if (colorValues[i] == color)
            return static_cast<int>(i);
    }
    return 0;  // Default to first color
}

void ClipEditorDialog::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void ClipEditorDialog::resized()
{
    auto bounds = getLocalBounds().reduced(20);
    auto rowHeight = 30;
    auto labelWidth = 80;
    auto buttonWidth = 80;
    auto buttonHeight = 30;

    // Title
    titleLabel.setBounds(bounds.removeFromTop(30));
    bounds.removeFromTop(20);

    // Name row
    auto nameRow = bounds.removeFromTop(rowHeight);
    nameLabel.setBounds(nameRow.removeFromLeft(labelWidth));
    nameRow.removeFromLeft(10);
    nameEditor.setBounds(nameRow);
    bounds.removeFromTop(10);

    // Type row
    auto typeRow = bounds.removeFromTop(rowHeight);
    typeLabel.setBounds(typeRow.removeFromLeft(labelWidth));
    typeRow.removeFromLeft(10);
    typeValueLabel.setBounds(typeRow);
    bounds.removeFromTop(10);

    // Color row
    auto colorRow = bounds.removeFromTop(rowHeight);
    colorLabel.setBounds(colorRow.removeFromLeft(labelWidth));
    colorRow.removeFromLeft(10);
    colorComboBox.setBounds(colorRow);
    bounds.removeFromTop(20);

    // Buttons
    auto buttonRow = bounds.removeFromTop(buttonHeight);
    auto cancelBounds = buttonRow.removeFromRight(buttonWidth);
    buttonRow.removeFromRight(10);
    auto okBounds = buttonRow.removeFromRight(buttonWidth);

    okButton.setBounds(okBounds);
    cancelButton.setBounds(cancelBounds);
}

void ClipEditorDialog::buttonClicked(juce::Button* button)
{
    if (button == &okButton)
    {
        std::cout << "ClipEditorDialog: OK clicked" << std::endl;

        juce::String newName = nameEditor.getText();
        int colorIndex = colorComboBox.getSelectedItemIndex();
        juce::Colour newColor = (colorIndex >= 0 && colorIndex < static_cast<int>(colorValues.size()))
                                     ? colorValues[colorIndex]
                                     : originalColor;

        if (onClipEdited)
        {
            onClipEdited(newName, newColor, originalIsAudio);
        }

        setVisible(false);
        exitModalState(1);
    }
    else if (button == &cancelButton)
    {
        std::cout << "ClipEditorDialog: Cancel clicked" << std::endl;
        setVisible(false);
        exitModalState(0);
    }
}

void ClipEditorDialog::comboBoxChanged(juce::ComboBox* comboBox)
{
    (void)comboBox;
    // Color selection changed - could update preview here
}

void ClipEditorDialog::closeButtonPressed()
{
    std::cout << "ClipEditorDialog: Close button pressed" << std::endl;
    setVisible(false);
    exitModalState(0);
}
