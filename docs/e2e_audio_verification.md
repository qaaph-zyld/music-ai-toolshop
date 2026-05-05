# E2E Audio Verification Protocol

This document describes how to verify that audio playback works end-to-end through the full audio stack.

## Overview

The audio chain for verification:
```
Rust Test Code → CPAL → OS Audio API → Audio Driver → Hardware → Speakers
```

## Prerequisites

- Working audio output device (speakers, headphones, or line out)
- Audio device not muted
- Volume at a reasonable level (30-70%)

## Verification Steps

### Step 1: Run Automated Tests

These tests verify the software stack works correctly:

```bash
cd d:/Project/music-ai-toolshop/projects/06-opendaw/daw-engine
cargo test --test e2e_audio_output
```

**Expected Output**:
```
running 6 tests
test test_audio_stream_creation ... ok
test test_cpal_device_enumeration ... ok
test test_default_output_device ... ok
test test_error_handling_no_device ... ok
test test_output_configuration ... ok
test test_sine_wave_playback ... ok
test test_stream_latency ... ok
```

### Step 2: Run Manual Audio Test

This test produces actual audible output for human verification:

```bash
cargo run --example audio_e2e_test
```

**Expected Behavior**:
1. You should hear a 440Hz tone (musical note A4) for 1 second
2. The tone should be clean (no crackles, pops, or dropouts)
3. The terminal should show:
   ```
   ✓ Audio output device found
   ✓ Audio stream started successfully
   ✓ Audio playback completed
   E2E Audio Verification: PASSED ✓
   ```

### Step 3: Verify Full Stack

If you heard the tone, the following components are verified:

- ✅ Rust audio generation code
- ✅ CPAL audio abstraction layer
- ✅ Windows Core Audio / WASAPI
- ✅ Audio driver
- ✅ Audio hardware
- ✅ Speaker/headphone output

## Troubleshooting

### No Audio Device Found

**Symptom**: "No audio output device found!"

**Solutions**:
1. Check that speakers/headphones are connected
2. Check Windows Sound settings (right-click speaker icon → Open Sound settings)
3. Ensure the default output device is enabled
4. Try a different audio port (if available)

### Audio Device Found But No Sound

**Symptom**: Test shows success but you hear nothing

**Solutions**:
1. Check volume is not muted
2. Check volume level is adequate (not 0%)
3. Verify correct output device is selected in Windows
4. Check if audio is going to a different output (e.g., HDMI, Bluetooth)

### Distorted or Crackling Audio

**Symptom**: Tone is audible but has artifacts

**Possible Causes**:
1. CPU load too high (close other applications)
2. Buffer underruns (system too slow)
3. Audio driver issues (try updating driver)
4. Hardware problems (try different speakers/headphones)

## Updating CURRENT_STATE.md

After successful verification, update the project state:

```markdown
| Audio playback through full stack | ✅ VERIFIED | 2026-MM-DD |
```

Remove from "What's NOT Verified (E2E)" section:
```markdown
- ~~Audio playback through full stack (Rust → CPAL → speakers)~~ ✅ VERIFIED
```

## CI/CD Note

These tests are designed to work in CI environments where no audio device exists:
- Automated tests gracefully skip when no device is found
- Manual test requires human verification and should not run in CI
- The `e2e_audio_output` integration tests will pass (with skips) in headless environments
