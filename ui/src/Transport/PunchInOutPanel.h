#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

/**
 * PunchInOutPanel - UI for configuring punch-in/out recording
 * 
 * Provides controls for:
 * - Punch-in position (beat/bar)
 * - Punch-out position (optional)
 * - Pre-roll duration
 * - Arm/Disarm recording
 * - Status display
 */
class PunchInOutPanel : public juce::Component
{
public:
    PunchInOutPanel();
    ~PunchInOutPanel() override;

    void paint(juce::Graphics& g) override;
    void resized() override;

    // Setters (called from engine callbacks)
    void setPunchIn(double beats);
    void setPunchOut(double beats);  // -1 to clear
    void setPreRoll(double beats);
    void setPunchState(int state);  // 0=disarmed, 1=armed, 2=preroll, 3=recording, 4=completed
    void setEnabled(bool enabled);

    // Getters
    double getPunchIn() const { return currentPunchIn; }
    double getPunchOut() const { return currentPunchOut; }
    double getPreRoll() const { return currentPreRoll; }
    bool isEnabled() const { return punchEnabled; }
    int getPunchState() const { return currentState; }

    // Callbacks (connect to EngineBridge)
    std::function<void(double beats)> onPunchInChanged;
    std::function<void(double beats)> onPunchOutChanged;  // -1 to clear
    std::function<void(double beats)> onPreRollChanged;
    std::function<void()> onArmPressed;
    std::function<void()> onDisarmPressed;
    std::function<void(bool enabled)> onEnabledChanged;

private:
    void setupUI();
    void updateUIState();
    juce::String formatBeatTime(double beats);
    double parseBeatTime(const juce::String& text);
    juce::Colour getStateColor() const;

    // UI Components
    juce::Label titleLabel{"Title", "Punch In/Out"};
    juce::ToggleButton enableButton{"Enabled"};
    
    juce::Label punchInLabel{"In:", "Punch In:"};
    juce::TextEditor punchInEditor;
    
    juce::Label punchOutLabel{"Out:", "Punch Out:"};
    juce::TextEditor punchOutEditor;
    juce::TextButton clearOutButton{"Clear"};
    
    juce::Label preRollLabel{"Pre:", "Pre-Roll:"};
    juce::ComboBox preRollCombo;
    
    juce::TextButton armButton{"Arm"};
    juce::Label statusLabel{"Status", "Disarmed"};
    
    juce::Label progressLabel{"Progress", ""};
    juce::ProgressBar progressBar{0.0};

    // State
    double currentPunchIn = 4.0;
    double currentPunchOut = 8.0;
    double currentPreRoll = 2.0;
    int currentState = 0;  // 0=disarmed, 1=armed, 2=preroll, 3=recording, 4=completed
    bool punchEnabled = true;
    double currentProgress = 0.0;
    double currentBeat = 0.0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(PunchInOutPanel)
};
