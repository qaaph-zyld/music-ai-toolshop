# Session Z - Onboarding Flow

```markdown
@ai_dev_meta_layer/framework_loader.md

**Task**: Create first-launch onboarding experience - demo project, interactive tutorial, audio test

**Session Type**: New Feature / UX Design

**Context**: Currently launches to empty project. New users need guidance: demo project pre-loaded, interactive tutorial ("Click here..."), audio test tone, user type selection (new/experienced). See NEXT_STEPS.md Phase 10.3.

---

## Toolkit Selection

| Toolkit | Selected | Rationale |
|---------|----------|-----------|
| Superpowers | ✅ Yes | TDD for onboarding logic |
| UI UX Pro Max | ✅ Yes | Designing onboarding UX |
| Frontend Design | ✅ Yes | JUCE dialog components |
| Claude-Mem | ⬜ No | Not a long-term context task |
| Awesome Claude Code | ⬜ No | No specialized tools needed |

**Meta Layer Skills Emphasized**:
- ✅ brainstorming
- ✅ verification-before-completion
- ✅ test-driven-development
- ⬜ Other: UX flow design

---

## Documentation Plan

**Utilization Log**: `ai_dev_meta_layer/utilization_logs/session_Z_YYYY-MM-DD.md`

**Planned Checkpoints**:
- [ ] Post-bootstrap (user flow design)
- [ ] Post-plan (after UX wireframes)
- [ ] Mid-implementation (after dialogs + tutorial)
- [ ] Pre-completion (before E2E test)
- [ ] Post-completion (user flow verification)

---

## Bite-Sized Tasks

### Task Z.1: User Flow Design
**File**: `docs/onboarding_design.md` (new)  
**Time**: 10 min (design, no code)

Document the flow:
```markdown
# Onboarding Flow

## Entry Points
1. First launch (no settings file) → Show onboarding
2. Subsequent launch → Skip to empty project
3. Help menu → "Show Onboarding" available anytime

## Flow Steps
1. **Welcome Screen**
   - "Welcome to OpenDAW"
   - Two buttons: "I'm New" | "I'm Experienced"
   - Skip link (bottom)

2. **Audio Test** (if "I'm New" or always)
   - "Let's test your audio"
   - Play test tone button
   - "I can hear it" / "No audio" buttons
   - Audio settings link

3. **Demo Project** (if "I'm New")
   - "Try a demo project?"
   - Description: "Pre-loaded with samples and patterns"
   - Yes / No thanks

4. **Interactive Tutorial** (if Yes to demo)
   - Highlighted walkthrough:
     - "Click here to play" (transport play button highlighted)
     - "This is the mixer" (mixer panel highlighted)
     - "Try launching a clip" (clip slot highlighted)
   - "Next tip" / "Skip tutorial" buttons

5. **Complete**
   - "You're ready!"
   - "Start new project" | "Open demo project again"
```

**Verification**: Design reviewed, approved

---

### Task Z.2: Settings Manager (First-Launch Detection)
**File**: `ui/src/Settings/SettingsManager.h` and `.cpp` (new)  
**Time**: 10 min

Create settings management:
```cpp
class SettingsManager {
public:
    static bool isFirstLaunch();
    static void markOnboardingComplete();
    static bool shouldShowOnboarding();
    static void setShowOnboardingOnStartup(bool show);
    
private:
    static juce::File getSettingsFile();
    static juce::var loadSettings();
    static void saveSettings(const juce::var& settings);
};

// Implementation
bool SettingsManager::isFirstLaunch() {
    return !getSettingsFile().existsAsFile();
}

void SettingsManager::markOnboardingComplete() {
    auto settings = loadSettings();
    settings.getDynamicObject()->setProperty("onboardingComplete", true);
    saveSettings(settings);
}
```

**Verification**: First-launch detection works

---

### Task Z.3: Welcome Dialog
**File**: `ui/src/Onboarding/WelcomeDialog.h` and `.cpp` (new)  
**Time**: 15 min

Create welcome UI:
```cpp
class WelcomeDialog : public juce::Component {
public:
    WelcomeDialog();
    
    std::function<void()> onNewUserSelected;
    std::function<void()> onExperiencedUserSelected;
    std::function<void()> onSkip;
    
private:
    juce::Label titleLabel;
    juce::Label subtitleLabel;
    juce::TextButton newUserButton;
    juce::TextButton experiencedButton;
    juce::TextButton skipButton;
    
    void paint(juce::Graphics& g) override;
    void resized() override;
};

// Implementation
WelcomeDialog::WelcomeDialog() {
    titleLabel.setText("Welcome to OpenDAW", juce::dontSendNotification);
    titleLabel.setFont(juce::Font(24.0f, juce::Font::bold));
    
    subtitleLabel.setText("Let's get you started with music production", juce::dontSendNotification);
    
    newUserButton.setButtonText("I'm New - Show Me Around");
    newUserButton.onClick = [this] { if (onNewUserSelected) onNewUserSelected(); };
    
    experiencedButton.setButtonText("I'm Experienced");
    experiencedButton.onClick = [this] { if (onExperiencedUserSelected) onExperiencedUserSelected(); };
    
    skipButton.setButtonText("Skip for now");
    skipButton.onClick = [this] { if (onSkip) onSkip(); };
}
```

**Verification**: Dialog displays, buttons work

---

### Task Z.4: Audio Test Dialog
**File**: `ui/src/Onboarding/AudioTestDialog.h` and `.cpp` (new)  
**Time**: 15 min

Create audio test UI:
```cpp
class AudioTestDialog : public juce::Component, public juce::Timer {
public:
    AudioTestDialog();
    ~AudioTestDialog() override;
    
    std::function<void()> onAudioWorking;
    std::function<void()> onAudioNotWorking;
    std::function<void()> onOpenSettings;
    
private:
    juce::Label titleLabel;
    juce::Label instructionLabel;
    juce::TextButton playToneButton;
    juce::TextButton yesButton;
    juce::TextButton noButton;
    juce::TextButton settingsButton;
    
    bool isPlayingTone = false;
    
    void paint(juce::Graphics& g) override;
    void resized() override;
    void timerCallback() override;
    
    void playTestTone();
    void stopTestTone();
};

// Implementation
void AudioTestDialog::playTestTone() {
    // Call EngineBridge to play 1kHz sine wave
    auto& engine = EngineBridge::getInstance();
    engine.playTestTone(1000.0f, 0.5f); // 1kHz, 0.5 amplitude
    isPlayingTone = true;
    startTimer(2000); // Stop after 2 seconds
}
```

**Verification**: Test tone plays, buttons functional

---

### Task Z.5: Demo Project Loader
**File**: `ui/src/Project/DemoProjectLoader.h` and `.cpp` (new)  
**Time**: 15 min

Create demo project:
```cpp
class DemoProjectLoader {
public:
    static bool loadDemoProject(MainComponent* mainComponent);
    static bool isDemoProjectAvailable();
    
private:
    static juce::File getDemoProjectPath();
    static void createDemoProjectFiles();
};

// Implementation
bool DemoProjectLoader::loadDemoProject(MainComponent* mainComponent) {
    // Create demo project with:
    // - 4 tracks with different patterns
    // - Pre-loaded drum clip on track 1
    // - Pre-loaded bass pattern on track 2
    // - Mixer with preset levels
    // - Transport at 128 BPM
    
    auto& engine = EngineBridge::getInstance();
    
    // Set BPM
    engine.setTempo(128.0);
    
    // Add clips to session grid
    mainComponent->setClip(0, 0, "Kick Pattern", juce::Colours::red);
    mainComponent->setClip(1, 0, "Bass Loop", juce::Colours::blue);
    mainComponent->setClip(2, 0, "Synth Stab", juce::Colours::green);
    
    // Set mixer levels
    engine.setTrackFader(0, 0.8f);
    engine.setTrackFader(1, 0.7f);
    engine.setTrackFader(2, 0.6f);
    
    return true;
}
```

**Verification**: Demo loads, clips visible, mixer set

---

### Task Z.6: Interactive Tutorial System
**File**: `ui/src/Onboarding/TutorialOverlay.h` and `.cpp` (new)  
**Time**: 20 min

Create tutorial overlay:
```cpp
struct TutorialStep {
    juce::String title;
    juce::String message;
    juce::Component* targetComponent; // Component to highlight
    juce::Rectangle<int> highlightBounds;
};

class TutorialOverlay : public juce::Component {
public:
    TutorialOverlay();
    
    void startTutorial(const std::vector<TutorialStep>& steps);
    void nextStep();
    void skipTutorial();
    
    std::function<void()> onTutorialComplete;
    
private:
    std::vector<TutorialStep> steps;
    size_t currentStep = 0;
    
    juce::Label titleLabel;
    juce::Label messageLabel;
    juce::TextButton nextButton;
    juce::TextButton skipButton;
    
    void paint(juce::Graphics& g) override;
    void resized() override;
    
    void updateForCurrentStep();
};

// Implementation
void TutorialOverlay::paint(juce::Graphics& g) {
    // Darken entire screen
    g.fillAll(juce::Colours::black.withAlpha(0.7f));
    
    // Cut out hole for highlighted component
    if (currentStep < steps.size()) {
        auto bounds = steps[currentStep].highlightBounds;
        g.excludeClipRegion(bounds);
        g.fillAll(juce::Colours::black.withAlpha(0.0f)); // Clear in hole
        
        // Draw border around highlighted area
        g.setColour(juce::Colours::yellow);
        g.drawRect(bounds, 3);
    }
}
```

**Verification**: Overlay highlights components, steps advance

---

### Task Z.7: MainComponent Integration
**File**: `ui/src/MainComponent.cpp` (add to constructor)  
**Time**: 10 min

Wire up in MainComponent:
```cpp
MainComponent::MainComponent() {
    // ... existing setup ...
    
    // Check if onboarding should show
    if (SettingsManager::isFirstLaunch() || SettingsManager::shouldShowOnboarding()) {
        showOnboarding();
    }
}

void MainComponent::showOnboarding() {
    welcomeDialog = std::make_unique<WelcomeDialog>();
    
    welcomeDialog->onNewUserSelected = [this] {
        welcomeDialog->setVisible(false);
        showAudioTest();
    };
    
    welcomeDialog->onExperiencedUserSelected = [this] {
        SettingsManager::markOnboardingComplete();
        welcomeDialog.reset();
    };
    
    welcomeDialog->onSkip = [this] {
        SettingsManager::markOnboardingComplete();
        welcomeDialog.reset();
    };
    
    addAndMakeVisible(welcomeDialog.get());
    welcomeDialog->setBounds(getLocalBounds());
}

void MainComponent::showAudioTest() {
    audioTestDialog = std::make_unique<AudioTestDialog>();
    
    audioTestDialog->onAudioWorking = [this] {
        audioTestDialog->setVisible(false);
        showDemoProjectOffer();
    };
    
    // ... etc
}
```

**Verification**: Onboarding shows on first launch

---

### Task Z.8: E2E Test
**File**: `daw-engine/tests/integration_onboarding.rs` (new)  
**Time**: 10 min

Create test (settings-based):
```rust
#[test]
fn test_first_launch_detection() {
    // Create temp settings directory
    let temp_dir = tempdir().unwrap();
    let settings_file = temp_dir.path().join("settings.json");
    
    // No settings file = first launch
    assert!(!settings_file.exists());
    // Simulate detection logic
    assert_eq!(detect_first_launch(&settings_file), true);
    
    // Create settings file
    std::fs::write(&settings_file, r#"{"onboardingComplete": true}"#).unwrap();
    assert_eq!(detect_first_launch(&settings_file), false);
}
```

**Verification**: Test passes

---

## Agent Report Format

Return exactly:
```markdown
**Status**: [✅ COMPLETE / ⚠️ PARTIAL / ❌ BLOCKED]

**Files Modified**:
- [exact paths]

**Test Results**:
- cargo test --lib: [X passed, Y failed]
- cmake build: [errors/warnings]
- onboarding E2E test: [pass/fail]

**Blockers**: [if any, with evidence]

**User Flow Verified**:
- [ ] Welcome dialog shows
- [ ] Audio test plays tone
- [ ] Demo project loads
- [ ] Tutorial highlights components

**Recommended Next Actions**:
```

---

Proceed with systematic approach per Core Memories.
