#include "SceneLaunchComponent.h"
#include "../Engine/EngineBridge.h"

SceneLaunchComponent::SceneLaunchComponent(int sceneIndex)
    : sceneIdx(sceneIndex)
{
    setSize(120, 30);
    setRepaintsOnMouseActivity(true);
}

void SceneLaunchComponent::paint(juce::Graphics& g)
{
    auto bounds = getLocalBounds().toFloat();

    // Background color based on state
    juce::Colour bgColor;
    if (isPressed)
        bgColor = juce::Colours::green.darker(0.3f);
    else if (isHovered)
        bgColor = juce::Colour(0xFF5B5B5B).brighter(0.1f);
    else
        bgColor = juce::Colour(0xFF4B4B4B);

    g.setColour(bgColor);
    g.fillRoundedRectangle(bounds, 4.0f);

    // Border
    g.setColour(juce::Colour(0xFF5B5B5B));
    g.drawRoundedRectangle(bounds, 4.0f, 1.0f);

    // Scene number indicator (small box on left)
    auto indicatorBounds = bounds.removeFromLeft(25.0f).reduced(3.0f);
    g.setColour(juce::Colour(0xFF3B3B3B));
    g.fillRoundedRectangle(indicatorBounds, 2.0f);

    g.setColour(juce::Colours::white);
    g.setFont(juce::Font(11.0f, juce::Font::bold));
    g.drawText(juce::String(sceneIdx + 1), indicatorBounds, juce::Justification::centred, true);

    // Scene name
    g.setFont(juce::Font(11.0f));
    g.drawText(sceneName, bounds.reduced(4.0f, 0), juce::Justification::centredLeft, true);
}

void SceneLaunchComponent::resized()
{
    // Layout is handled in paint()
}

void SceneLaunchComponent::mouseDown(const juce::MouseEvent& event)
{
    isPressed = true;
    repaint();
    launchScene();
}

void SceneLaunchComponent::launchScene()
{
    // Launch all clips in this scene via EngineBridge
    EngineBridge::getInstance().launchScene(sceneIdx);

    // Visual feedback - reset pressed state after short delay
    juce::Timer::callAfterDelay(150, [this] {
        isPressed = false;
        repaint();
    });
}

void SceneLaunchComponent::setSceneName(const juce::String& name)
{
    sceneName = name;
    repaint();
}
