# Voice Effects Analysis Report
## RAF Camora - VENDETTA (prod. by The Royals & The Cratez)

---

### 📊 Audio Information
- **Duration:** 155.67 seconds
- **Sample Rate:** 22,050 Hz
- **Fundamental Frequency (F0):** 51.5 Hz
- **Voice Detected:** ✅ Yes
- **Analysis Tools:** librosa ✅ | parselmouth ✅ | crepe ✅

---

### 🎵 Detected Effects (Sorted by Confidence)

#### 🔴 HIGH CONFIDENCE (80%+)

**Pitch Shift** - **95% Confidence** ⭐⭐⭐⭐⭐
- **Evidence:** F0 (51Hz) below expected range (200-400Hz) for detected formants
- **Parameters:**
  - Detected F0: 51.5 Hz
  - Formants: F1=745.2 Hz, F2=1987.3 Hz, F3=3068.1 Hz
  - Expected F0 Range: 200-400 Hz
  - **Estimated Shift:** -23.5 semitones (2 octaves down)

**Distortion** - **95% Confidence** ⭐⭐⭐⭐⭐
- **Evidence:** High THD: 96.8% (heavy distortion/saturation)
- **Parameters:**
  - Fundamental: 80.7 Hz
  - THD: 96.83%
  - Even/Odd Harmonic Ratio: 1.02

**Delay/Echo** - **89% Confidence** ⭐⭐⭐⭐⭐
- **Evidence:** Strong echo at 488ms (correlation: 0.79), Multiple echo peaks detected (3)
- **Parameters:**
  - Delay Time: 488 ms (0.488 seconds)
  - Correlation Strength: 0.788
  - Echo Count: 3 peaks

#### 🟡 MEDIUM CONFIDENCE (50-79%)

**Reverb** - **64% Confidence** ⭐⭐⭐⭐
- **Evidence:** Energy decay RT60 ~ 2.41s
- **Parameters:**
  - RT60: 2.412 seconds
  - Type: Room reverb

**Chorus/Doubling** - **60% Confidence** ⭐⭐⭐⭐
- **Evidence:** Periodic bandwidth modulation detected (4 peaks), Low phase coherence: 0.632 (typical of chorus)
- **Parameters:**
  - Phase Coherence: 0.6322
  - Bandwidth CV: 0.1803

#### 🟢 LOW CONFIDENCE (<50%)

**Auto-tune/Pitch Correction** - **20% Confidence** ⭐⭐
- **Evidence:** Pitch concentrated at semitone centers (43% peak)
- **Parameters:**
  - Mean Pitch Deviation: 19.42 cents
  - Pitch Jump Ratio: 0.2016
  - Clean Jump Ratio: 0.286
  - Pitch Histogram Peak: 0.428

**Compression** - **10% Confidence** ⭐
- **Evidence:** Minimal dynamic range reduction detected
- **Parameters:** Low compression ratio detected

---

### ❌ Effects Not Detected

| Effect | Confidence | Reason |
|--------|------------|--------|
| Formant Shift | 0% | Formants match expected values for natural voice |
| EQ/Filtering | 0% | No significant spectral shaping detected |
| De-essing | 0% | No sibilant reduction patterns found |
| Vocoder | 0% | No carrier signal characteristics detected |
| Noise Gate | 0% | No gate transition patterns identified |

---

### 🎯 Production Analysis

**This track uses a heavily processed vocal chain:**

1. **Extreme Pitch Processing** (-23.5 semitones = 2 octaves down)
2. **Aggressive Distortion** (96.8% THD) for saturation effect
3. **Spatial Effects**: Delay (488ms), Reverb (2.4s RT60), Chorus
4. **Light Pitch Correction** (20% confidence)

**Style Classification:** Modern trap/hip-hop vocal production with extreme pitch manipulation and heavy saturation.

---

### 📈 Technical Notes

- **Pitch Shift Detection**: Based on F0-formant mismatch analysis
- **Distortion Analysis**: Total Harmonic Distortion (THD) measurement
- **Delay Detection**: Autocorrelation peak analysis
- **Reverb Analysis**: RT60 energy decay estimation
- **Chorus Detection**: Phase coherence and bandwidth modulation

*Analysis performed using librosa, parselmouth (Praat), and CREPE neural pitch detection*
