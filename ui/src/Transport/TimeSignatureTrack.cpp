#include "TimeSignatureTrack.h"
#include "../Engine/EngineBridge.h"

TimeSignatureTrack::TimeSignatureTrack()
{
    setSize(800, trackHeight);

    // Add default 4/4 at bar 1
    changes.push_back({1, 4, 4});
}

TimeSignatureTrack::~TimeSignatureTrack() = default;

void TimeSignatureTrack::paint(juce::Graphics& g)
{
    // Background
    g.fillAll(juce::Colour(0xFF252525));

    auto bounds = getLocalBounds();
    float width = static_cast<float>(bounds.getWidth());
    float height = static_cast<float>(bounds.getHeight());

    // Draw bar lines
    g.setColour(juce::Colour(0xFF3A3A3A));
    for (uint32_t bar = visibleStartBar; bar <= visibleEndBar; ++bar)
    {
        float x = barToX(bar);
        if (x < width)
        {
            g.drawVerticalLine(static_cast<int>(x), 0.0f, height);
        }
    }

    // Draw time signature changes
    for (int i = 0; i < static_cast<int>(changes.size()); ++i)
    {
        const auto& change = changes[i];

        // Only draw if within visible range
        if (change.bar < visibleStartBar || change.bar > visibleEndBar)
            continue;

        float x = barToX(change.bar);
        if (x >= width)
            continue;

        // Draw selection background
        if (i == selectedIndex)
        {
            g.setColour(juce::Colour(0xFF4A90E2).withAlpha(0.3f));
            g.fillRect(static_cast<int>(x), 0, signatureWidth, static_cast<int>(height));
        }

        // Draw signature text
        g.setColour(juce::Colours::white);
        if (i == selectedIndex)
        {
            g.setColour(juce::Colour(0xFF4A90E2));
        }

        g.setFont(juce::Font(11.0f, juce::Font::bold));
        juce::String sigText = change.toString();

        // Center text in the bar
        float barWidth = barToX(change.bar + 1) - x;
        int textX = static_cast<int>(x + (barWidth - signatureWidth) / 2);

        g.drawText(sigText,
                   textX, 2,
                   signatureWidth, static_cast<int>(height) - 4,
                   juce::Justification::centred,
                   false);
    }

    // Draw border
    g.setColour(juce::Colour(0xFF4A4A4A));
    g.drawRect(getLocalBounds(), 1);

    // Draw label on the left
    g.setColour(juce::Colour(0xFF888888));
    g.setFont(juce::Font(9.0f));
    g.drawText("TIME SIG", 2, 0, 50, static_cast<int>(height) / 2, juce::Justification::left, false);
}

void TimeSignatureTrack::resized()
{
    // Component size changes don't affect internal drawing
    // Drawing is based on bar-to-pixel conversion
}

void TimeSignatureTrack::mouseDown(const juce::MouseEvent& event)
{
    if (event.mods.isPopupMenu())
    {
        // Right-click context menu
        int changeIndex = hitTestChange(static_cast<float>(event.x), static_cast<float>(event.y));
        if (changeIndex >= 0)
        {
            selectedIndex = changeIndex;
            contextMenuIndex = changeIndex;
            auto menu = createChangeContextMenu(changes[changeIndex]);
            menu.showMenuAsync(juce::PopupMenu::Options().withTargetComponent(this));
        }
        return;
    }

    int changeIndex = hitTestChange(static_cast<float>(event.x), static_cast<float>(event.y));

    if (changeIndex >= 0)
    {
        selectedIndex = changeIndex;

        // Double-click will open edit dialog, single click just selects
        repaint();
    }
    else
    {
        // Clicked on empty area
        selectedIndex = -1;
        repaint();
    }
}

void TimeSignatureTrack::mouseDoubleClick(const juce::MouseEvent& event)
{
    int changeIndex = hitTestChange(static_cast<float>(event.x), static_cast<float>(event.y));

    if (changeIndex >= 0)
    {
        // Edit existing change
        selectedIndex = changeIndex;
        openEditDialog(changes[changeIndex]);
    }
    else
    {
        // Add new change at clicked bar
        uint32_t bar = xToBar(static_cast<float>(event.x));

        // Check if a change already exists at this bar
        bool exists = false;
        for (const auto& change : changes)
        {
            if (change.bar == bar)
            {
                exists = true;
                break;
            }
        }

        if (!exists)
        {
            openAddDialog(bar);
        }
    }
}

void TimeSignatureTrack::setVisibleRange(uint32_t startBar, uint32_t endBar)
{
    visibleStartBar = std::max(1u, startBar);
    visibleEndBar = std::max(visibleStartBar + 1, endBar);
    repaint();
}

void TimeSignatureTrack::setTimeSignatureChanges(const std::vector<TimeSignatureChange>& newChanges)
{
    changes = newChanges;

    // Maintain selection if change still exists
    if (selectedIndex >= 0 && selectedIndex < static_cast<int>(changes.size()))
    {
        uint32_t selectedBar = changes[selectedIndex].bar;
        bool found = false;
        for (int i = 0; i < static_cast<int>(changes.size()); ++i)
        {
            if (changes[i].bar == selectedBar)
            {
                selectedIndex = i;
                found = true;
                break;
            }
        }
        if (!found)
            selectedIndex = -1;
    }

    repaint();
}

void TimeSignatureTrack::addTimeSignatureChange(uint32_t bar, uint8_t numerator, uint8_t denominator)
{
    if (onChangeAdded)
        onChangeAdded(bar, numerator, denominator);
}

juce::PopupMenu TimeSignatureTrack::createChangeContextMenu(const TimeSignatureChange& change)
{
    juce::PopupMenu menu;

    menu.addItem("Edit...", [this, &change]() {
        openEditDialog(change);
    });

    if (change.bar > 1)
    {
        menu.addItem("Delete", [this, &change]() {
            if (onChangeRemoved)
                onChangeRemoved(change.bar);
        });
    }

    menu.addSeparator();

    menu.addItem("Change to 4/4", true, change.numerator == 4 && change.denominator == 4, [this, &change]() {
        if (onChangeModified)
            onChangeModified(change.bar, 4, 4);
    });

    menu.addItem("Change to 3/4", true, change.numerator == 3 && change.denominator == 4, [this, &change]() {
        if (onChangeModified)
            onChangeModified(change.bar, 3, 4);
    });

    menu.addItem("Change to 6/8", true, change.numerator == 6 && change.denominator == 8, [this, &change]() {
        if (onChangeModified)
            onChangeModified(change.bar, 6, 8);
    });

    return menu;
}

void TimeSignatureTrack::openEditDialog(const TimeSignatureChange& change)
{
    // JUCE 7 async dialog with input field for editing time signature
    auto options = juce::MessageBoxOptions()
        .withIconType(juce::AlertWindow::QuestionIcon)
        .withTitle("Edit Time Signature")
        .withMessage("Enter new time signature (e.g., 4/4, 3/4, 6/8):")
        .withButton("OK")
        .withButton("Cancel")
        .withAssociatedComponent(this);

    juce::AlertWindow::showAsync(options, [this, change](int result) {
        if (result == 1) // OK button
        {
            // For JUCE 7, we need to use a different approach with input fields
            // Using AlertWindow directly with runModalLoop for input capability
            showEditAlertWithInput(change);
        }
    });
}

void TimeSignatureTrack::showEditAlertWithInput(const TimeSignatureChange& change)
{
    auto alert = std::make_unique<juce::AlertWindow>(
        "Edit Time Signature",
        "Enter new time signature for bar " + juce::String(change.bar) + ":",
        juce::AlertWindow::QuestionIcon, this);

    alert->addTextEditor("timeSig", change.toString(), "Time Signature:");
    alert->addButton("OK", 1, juce::KeyPress(juce::KeyPress::returnKey));
    alert->addButton("Cancel", 0, juce::KeyPress(juce::KeyPress::escapeKey));

    auto callback = [this, change, alert = alert.get()](int result) mutable {
        if (result == 1)
        {
            juce::String input = alert->getTextEditorContents("timeSig").trim();
            
            uint8_t newNum = 0, newDenom = 0;
            if (parseTimeSignature(input, newNum, newDenom))
            {
                if (onChangeModified)
                    onChangeModified(change.bar, newNum, newDenom);
            }
            else
            {
                // Show error
                juce::AlertWindow::showMessageBoxAsync(
                    juce::AlertWindow::WarningIcon,
                    "Invalid Time Signature",
                    "Please enter a valid time signature like '4/4', '3/4', or '6/8'.",
                    "OK", this);
            }
        }
    };

    alert->enterModalState(true, juce::ModalCallbackFunction::create(callback));
    alert.release();
}

bool TimeSignatureTrack::parseTimeSignature(const juce::String& input, uint8_t& numerator, uint8_t& denominator)
{
    juce::String trimmed = input.trim();
    
    // Handle formats like "4/4", "3 / 4", "6/8"
    if (trimmed.contains("/"))
    {
        auto parts = juce::StringArray::fromTokens(trimmed, "/", "");
        if (parts.size() == 2)
        {
            int num = parts[0].trim().getIntValue();
            int denom = parts[1].trim().getIntValue();
            
            // Validate reasonable time signature values
            if (num >= 1 && num <= 32 && denom >= 1 && denom <= 64)
            {
                numerator = static_cast<uint8_t>(num);
                denominator = static_cast<uint8_t>(denom);
                return true;
            }
        }
    }
    
    return false;
}

void TimeSignatureTrack::openAddDialog(uint32_t bar)
{
    // JUCE async dialog for adding new time signature
    auto alert = std::make_unique<juce::AlertWindow>(
        "Add Time Signature",
        "Enter time signature for bar " + juce::String(bar) + ":",
        juce::AlertWindow::QuestionIcon, this);

    alert->addTextEditor("timeSig", "4/4", "Time Signature:");
    alert->addButton("OK", 1, juce::KeyPress(juce::KeyPress::returnKey));
    alert->addButton("Cancel", 0, juce::KeyPress(juce::KeyPress::escapeKey));

    auto callback = [this, bar, alert = alert.get()](int result) mutable {
        if (result == 1)
        {
            juce::String input = alert->getTextEditorContents("timeSig").trim();
            
            uint8_t newNum = 0, newDenom = 0;
            if (parseTimeSignature(input, newNum, newDenom))
            {
                if (onChangeAdded)
                    onChangeAdded(bar, newNum, newDenom);
            }
            else
            {
                // Show error
                juce::AlertWindow::showMessageBoxAsync(
                    juce::AlertWindow::WarningIcon,
                    "Invalid Time Signature",
                    "Please enter a valid time signature like '4/4', '3/4', or '6/8'.",
                    "OK", this);
            }
        }
    };

    alert->enterModalState(true, juce::ModalCallbackFunction::create(callback));
    alert.release();
}

float TimeSignatureTrack::barToX(uint32_t bar) const
{
    if (bar < visibleStartBar)
        return 0.0f;

    uint32_t visibleBarCount = visibleEndBar - visibleStartBar;
    if (visibleBarCount == 0)
        return 0.0f;

    float pixelsPerBar = static_cast<float>(getWidth()) / static_cast<float>(visibleBarCount);
    return static_cast<float>(bar - visibleStartBar) * pixelsPerBar;
}

uint32_t TimeSignatureTrack::xToBar(float x) const
{
    uint32_t visibleBarCount = visibleEndBar - visibleStartBar;
    if (visibleBarCount == 0)
        return visibleStartBar;

    float pixelsPerBar = static_cast<float>(getWidth()) / static_cast<float>(visibleBarCount);
    uint32_t barOffset = static_cast<uint32_t>(x / pixelsPerBar);
    return visibleStartBar + barOffset;
}

int TimeSignatureTrack::hitTestChange(float x, float y) const
{
    (void)y;  // y not used - entire height is clickable

    for (int i = 0; i < static_cast<int>(changes.size()); ++i)
    {
        const auto& change = changes[i];
        if (change.bar < visibleStartBar || change.bar > visibleEndBar)
            continue;

        float changeX = barToX(change.bar);
        float barWidth = barToX(change.bar + 1) - changeX;

        // Check if x is within this bar's range
        if (x >= changeX && x < changeX + barWidth)
        {
            return i;
        }
    }

    return -1;
}
