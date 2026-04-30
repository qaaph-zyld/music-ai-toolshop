# OpenDAW Manual Testing Protocol

**Version:** 1.0  
**Date:** 2026-05-01  
**Purpose:** QA checklist for manual verification of OpenDAW functionality

---

## Overview

This document provides step-by-step testing procedures for manual QA verification of the OpenDAW application. Tests should be performed before each release to ensure critical functionality works as expected.

---

## Test Environment Setup

### Prerequisites
- [ ] OpenDAW built successfully (`cargo build --release` + CMake build)
- [ ] Test audio interface connected and configured (48kHz/44.1kHz)
- [ ] MIDI keyboard or virtual MIDI device available
- [ ] Test audio files available (WAV format, 44.1/48kHz)

### Build Verification
```bash
cd daw-engine
cargo test --lib        # Should show 505+ tests passing
cargo test --tests      # Should show integration tests passing
cargo check --lib       # Should show 0 errors
```

---

## Section 1: Transport Controls

### 1.1 Basic Play/Stop Functionality
**Test ID:** TRANS-001  
**Priority:** Critical

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Launch OpenDAW | Application starts, UI loads | ☐ |
| 2 | Press Play button | Transport starts, play button highlights green | ☐ |
| 3 | Observe time display | Time counter increments | ☐ |
| 4 | Press Stop button | Transport stops, position holds | ☐ |
| 5 | Press Play again | Transport resumes from stopped position | ☐ |
| 6 | Press Stop twice | Position resets to 0 | ☐ |

### 1.2 Keyboard Shortcuts
**Test ID:** TRANS-002  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Press Spacebar | Play/Stop toggles | ☐ |
| 2 | Press Shift+Space | Rewind to start + Play | ☐ |
| 3 | Press Ctrl+R | Record mode activates | ☐ |
| 4 | Press Return/Enter | Rewind to start | ☐ |

### 1.3 Loop Playback
**Test ID:** TRANS-003  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Create loop region (bars 1-2) | Loop markers visible on timeline | ☐ |
| 2 | Enable Loop button | Loop button highlights | ☐ |
| 3 | Start playback before loop end | Playback continues to loop end | ☐ |
| 4 | Reach loop end | Position jumps to loop start | ☐ |
| 5 | Verify loop repeats | Playback continues looping | ☐ |
| 6 | Disable Loop | Playback continues past loop end | ☐ |

### 1.4 Record MIDI
**Test ID:** TRANS-004  
**Priority:** Critical

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Arm track 1 for recording | Record arm indicator on | ☐ |
| 2 | Press Record button | Record button highlights red | ☐ |
| 3 | Play MIDI keyboard | Input received, notes captured | ☐ |
| 4 | Press Stop | Recording stops | ☐ |
| 5 | Verify clip created | MIDI clip appears in track 1 | ☐ |
| 6 | Play clip | Recorded notes playback | ☐ |

---

## Section 2: Session View

### 2.1 Clip Slots
**Test ID:** SESS-001  
**Priority:** Critical

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Load sample into clip slot | Clip name displayed in slot | ☐ |
| 2 | Click clip slot | Clip slot highlights | ☐ |
| 3 | Press Space to play | Sample plays | ☐ |
| 4 | Click different clip | Previous stops, new plays | ☐ |
| 5 | Click playing clip | Playback stops | ☐ |

### 2.2 Scene Launch
**Test ID:** SESS-002  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Load clips in scene 1 (multiple tracks) | All slots show clip names | ☐ |
| 2 | Click Scene 1 button | All clips in scene start playing | ☐ |
| 3 | Launch Scene 2 while Scene 1 playing | Scene 1 clips quantize stop, Scene 2 starts | ☐ |
| 4 | Click Scene button of playing scene | All clips in scene stop | ☐ |

### 2.3 Track Controls
**Test ID:** SESS-003  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Adjust track volume slider | Volume changes in real-time | ☐ |
| 2 | Mute track | Mute button lights, no audio from track | ☐ |
| 3 | Solo track | Only soloed track audible | ☐ |
| 4 | Unmute/Unsolo | Normal playback resumes | ☐ |
| 5 | Record arm track | Arm indicator on, track ready for recording | ☐ |

---

## Section 3: Mixer

### 3.1 Level Meters
**Test ID:** MIX-001  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Play audio through track | Level meter shows activity | ☐ |
| 2 | Verify peak meter | Peak level matches audio amplitude | ☐ |
| 3 | Verify RMS meter | RMS level smoother than peak | ☐ |
| 4 | Stop audio | Meters drop to zero | ☐ |
| 5 | Master meter | Shows combined output level | ☐ |

### 3.2 Channel Strip Controls
**Test ID:** MIX-002  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Adjust fader | Volume changes smoothly | ☐ |
| 2 | Pan left/right | Stereo position shifts | ☐ |
| 3 | Click FX button | Plugin chain dialog opens | ☐ |

---

## Section 4: Plugin Chain

### 4.1 Plugin Browser
**Test ID:** PLUG-001  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Open plugin browser | Plugin list displays | ☐ |
| 2 | Search for plugin | List filters correctly | ☐ |
| 3 | Double-click plugin | Plugin added to chain | ☐ |

### 4.2 Plugin Chain Audio Processing
**Test ID:** PLUG-002  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Add gain plugin | Plugin appears in chain | ☐ |
| 2 | Adjust gain parameter | Audio level changes | ☐ |
| 3 | Bypass plugin | Audio returns to original level | ☐ |
| 4 | Re-enable plugin | Audio affected again | ☐ |
| 5 | Remove plugin | Plugin removed, audio unaffected | ☐ |

### 4.3 Plugin Reordering
**Test ID:** PLUG-003  
**Priority:** Low

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Add two different plugins | Both in chain | ☐ |
| 2 | Drag to reorder | Plugins swap positions | ☐ |
| 3 | Verify audio changes | Different processing order audible | ☐ |

---

## Section 5: Suno Browser

### 5.1 Track Browsing
**Test ID:** SUNO-001  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Open Suno browser panel | Track list loads | ☐ |
| 2 | Scroll track list | More tracks load as scrolling | ☐ |
| 3 | Use search box | Results filter by query | ☐ |
| 4 | Use genre filter | Results filter by genre | ☐ |

### 5.2 Track Import
**Test ID:** SUNO-002  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Select track | Track highlights | ☐ |
| 2 | Click Import button | Track downloads and converts | ☐ |
| 3 | Wait for import | Clip created in selected slot | ☐ |
| 4 | Play imported track | Audio plays correctly | ☐ |

---

## Section 6: Time Signature and Tempo

### 6.1 Time Signature Changes
**Test ID:** TEMPO-001  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | View time signature track | Default 4/4 displayed | ☐ |
| 2 | Double-click bar 5 | New signature change added | ☐ |
| 3 | Set to 3/4 | Signature shows 3/4 at bar 5 | ☐ |
| 4 | Play through change | Beat grouping changes at bar 5 | ☐ |

### 6.2 Tempo Automation
**Test ID:** TEMPO-002  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | View tempo automation track | Default tempo displayed | ☐ |
| 2 | Double-click to add breakpoint | New point appears | ☐ |
| 3 | Drag vertical to change BPM | BPM value updates | ☐ |
| 4 | Play through tempo change | Playback speed changes | ☐ |

### 6.3 Bar/Beat Display
**Test ID:** TEMPO-003  
**Priority:** Low

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Observe transport display | Shows bars and beats | ☐ |
| 2 | Play transport | Display increments correctly | ☐ |
| 3 | Verify format | Format is "Bar X Beat Y" | ☐ |

---

## Section 7: MIDI Editing

### 7.1 Piano Roll
**Test ID:** MIDI-001  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Double-click MIDI clip | Piano roll opens | ☐ |
| 2 | View notes | Notes displayed on grid | ☐ |
| 3 | Click note | Note selects | ☐ |
| 4 | Drag note | Note moves to new position/pitch | ☐ |

### 7.2 Note Editing
**Test ID:** MIDI-002  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Select multiple notes | Multiple notes highlighted | ☐ |
| 2 | Press Delete | Selected notes removed | ☐ |
| 3 | Click on grid | New note created | ☐ |
| 4 | Quantize notes | Notes snap to grid | ☐ |
| 5 | Transpose | All notes shift pitch | ☐ |

---

## Section 8: Project Management

### 8.1 Save Project
**Test ID:** PROJ-001  **Priority:** Critical

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Create project with clips | Clips visible in session | ☐ |
| 2 | File → Save | Save dialog opens | ☐ |
| 3 | Choose location and save | File saved (.opendaw format) | ☐ |
| 4 | Close application | Application exits cleanly | ☐ |

### 8.2 Load Project
**Test ID:** PROJ-002  
**Priority:** Critical

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Reopen OpenDAW | Application starts | ☐ |
| 2 | File → Open | Open dialog appears | ☐ |
| 3 | Select saved project | Project loads | ☐ |
| 4 | Verify clips | All clips present and playable | ☐ |
| 5 | Verify settings | Tempo, time signature correct | ☐ |

### 8.3 Export Audio
**Test ID:** PROJ-003  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | File → Export Audio | Export dialog opens | ☐ |
| 2 | Configure export (WAV, range) | Settings applied | ☐ |
| 3 | Click Export | Export process starts | ☐ |
| 4 | Wait for completion | Success message shown | ☐ |
| 5 | Verify exported file | File plays in external player | ☐ |

---

## Section 9: Audio Export

### 9.1 WAV Export
**Test ID:** EXP-001  
**Priority:** High

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Set loop range (bars 1-4) | Loop markers set | ☐ |
| 2 | File → Export Audio | Export dialog opens | ☐ |
| 3 | Select WAV format | Format selected | ☐ |
| 4 | Set 48kHz, 16-bit | Settings configured | ☐ |
| 5 | Export | Progress bar shows progress | ☐ |
| 6 | Complete | File created, success alert | ☐ |
| 7 | Verify | File plays correctly, correct duration | ☐ |

---

## Section 10: Performance and Stress Testing

### 10.1 CPU Usage
**Test ID:** PERF-001  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Launch Tracy profiler | Profiler connected | ☐ |
| 2 | Play session with 8 tracks | CPU usage displayed | ☐ |
| 3 | Monitor for 60 seconds | No audio dropouts, CPU stable | ☐ |
| 4 | Verify real-time safe | Latency budget maintained | ☐ |

### 10.2 Memory Stability
**Test ID:** PERF-002  
**Priority:** Medium

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1 | Open large project (>20 tracks) | Project loads | ☐ |
| 2 | Play for 5 minutes | Memory usage stable | ☐ |
| 3 | Stop/Start multiple times | No memory leaks | ☐ |

---

## Test Summary

| Section | Total Tests | Passed | Failed | Blocked |
|---------|-------------|--------|--------|---------|
| Transport Controls | 4 | | | |
| Session View | 3 | | | |
| Mixer | 2 | | | |
| Plugin Chain | 3 | | | |
| Suno Browser | 2 | | | |
| Time Signature/Tempo | 3 | | | |
| MIDI Editing | 2 | | | |
| Project Management | 3 | | | |
| Audio Export | 1 | | | |
| Performance | 2 | | | |
| **TOTAL** | **25** | | | |

---

## Sign-off

**Tester:** _________________________  **Date:** ___________  
**Tested Version:** _________________________  
**Platform:** _________________________  

**Notes:**

---

*Document generated for OpenDAW Session B E2E Integration Testing*  
*Last updated: 2026-05-01*
