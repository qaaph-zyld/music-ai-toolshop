#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

class SceneLaunchComponent : public juce::Component
{
public:
    explicit SceneLaunchComponent(int sceneIndex);
    ~SceneLaunchComponent() override = default;

    void paint(juce::Graphics& g) override;
    void resized() override;

    void mouseDown(const juce::MouseEvent& event) override;

    void launchScene();
    void setSceneName(const juce::String& name);

private:
    int sceneIdx;
    juce::String sceneName{"Scene " + juce::String(sceneIdx + 1)};
    bool isHovered = false;
    bool isPressed = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(SceneLaunchComponent)
};
