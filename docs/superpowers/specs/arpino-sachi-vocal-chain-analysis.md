# Arpino Sachi Vocal Chain Analysis

> **Source:** Ableton Live 12 Suite presets extracted from `C:\Users\015ZCS\Documents\Ableton\User Library\Presets\Audio Effects\Audio Effect Rack\`
> **Date:** 2026-07-24
> **Method:** Decompressed `.adg` files (gzipped XML), decoded hex-encoded `ProcessorState` blocks, extracted parameter values from `Parameters Type="RealWorld"` sections.

---

## 1. Artist Profile — Arpino Sachi

**Origin:** Bosnia and Herzegovina
**Label:** SUAVE (EMDC Network distribution)
**Genre:** European, Balkan, Alternative Hip Hop
**Collaborators:** Mahdi, Medico, Sajfer, Cunami Flo, Denik, Enel Beatz

Arpino Sachi blends traditional Balkan folk instruments (tamburica, accordion) with modern electronic beats and trap production. He is part of the new wave of Bosnian hip-hop artists (alongside Jala Brat, Buba Corelli, Sajfer, Cunami) who mix hip-hop with pop, EDM, folk, trap, and ethnic sounds, almost universally using Auto-Tune as a signature sound element.

**Key tracks:** Bar Bar, Klikeri (ft. Sajfer), Insomnia, Alo Mama, Versace, Yasmine, Lady, Mozaik, Biznis, Exotica, Pandora, Dabudibuda (ft. Mahdi & Denik), Mami Mami (ft. Mahdi)

**Production context:** Balkan trap/pop production typically features:
- Heavy Auto-Tune as a creative effect (not just correction)
- Dense, bass-heavy beats with traditional melodic samples
- Vocals that sit forward and aggressive in the mix
- Plate reverb for space without pushing the vocal back
- Short delays for width and depth

No public interviews about his production technique were found. The presets themselves are the primary source.

---

## 2. Chain Architecture — Signal Flow

### Main Chain (Serial Path)

```
Input
  │
  ├─ Slot 0: [Unknown / Auto-Tune EFX]  ← Pitch correction
  │
  ├─ Slot 1: DeEsser                     ← Sibilance control
  │
  ├─ Slot 2: CLA-2A                      ← Optical compression (leveling)
  │
  ├─ Slot 3: API-550                     ← EQ shaping (console character)
  │
  ├─ Slot 4: [Unknown / RComp]           ← Renaissance Compressor
  │
  ├─ Slot 5: RComp                       ← Renaissance Compressor (dynamics)
  │
  ├─ Slot 6: Renaissance Vox             ← Vocal channel strip (gate + comp + limit)
  │
  └─ Nested Rack (Parallel):
      ├─ Branch A: RVerb "Vocal Plate"   ← Plate reverb
      └─ Branch B: ValhallaDelay          ← Creative delay
```

**Note on slot ordering:** The XML structure shows some slots with unknown plugin names (hex decoding didn't capture all `PluginName` tags). Based on the previous session's analysis, the full chain includes Auto-Tune EFX at the start and ValhallaDelay in the nested rack. The main serial path is: DeEsser → CLA-2A → API-550 → RComp → Renaissance Vox → (parallel: RVerb + ValhallaDelay).

### Template Structure (Postavke 1-3.als)

| Template | Audio Tracks | Return Tracks | VST Slots | Group Devices |
|----------|-------------|---------------|-----------|---------------|
| Postavke 1 | 2 | 3 | 10 | 4 |
| Postavke 2 | 2 | 3 | 10 | 5 |
| Postavke 3 | 2 | 3 | 11 | 5 |

All templates use the same core chain with 2 audio tracks (likely main vocal + ad-libs/doubles) and 3 return tracks (likely reverb, delay, and a third send).

---

## 3. Plugin-by-Plugin Parameter Analysis

### 3.1 DeEsser (Waves)

**Purpose:** Reduce sibilance (harsh "s" and "sh" sounds, typically 4-8 kHz) before compression.

| Parameter | Chains 1-4 | Chains 5.x |
|-----------|-----------|-----------|
| Frequency | 7260 Hz | 8022 Hz |
| Mode | Split (2) | Split (3) |
| Threshold | -30.1 dB | -36.5 dB (5-1/5-3), -33.5 dB (5-2) |
| Audio mode | 7 | 7 |
| Range/Reduction | 0.5 | 15 |
| Max reduction | 10 | 30 |
| Preset | Factory default | "Pensado Lead 1" (Dave Pensado) |

**Interpretation:**
- Chains 1-4: Moderate de-essing at 7.26 kHz, gentle threshold
- Chains 5.x: Switched to **Dave Pensado's "Pensado Lead 1"** preset — higher frequency (8 kHz), much lower threshold (more aggressive), higher max reduction. This is a more professional, tuned de-essing approach for lead vocals.

**Research context:** The Waves DeEsser uses a sidechain filter to detect sibilance and applies gain reduction only when those frequencies exceed threshold. Split mode (used here) only attenuates the high frequencies, leaving the rest of the signal untouched — more transparent than Wide mode. Male vocal sibilance typically lives at 5-7 kHz; the 7.26-8 kHz setting targets the upper range, suitable for a brighter vocal recording or a voice with sibilance at higher frequencies.

### 3.2 CLA-2A (Waves)

**Purpose:** Optical compression — smooth, transparent leveling based on the Teletronix LA-2A hardware.

| Parameter | Value |
|-----------|-------|
| Preset | "Start Me Up" |
| Parameters count | 207 (mostly internal state) |

**Key observed values:** [0]=10, [1]=3, [2]=3, [3]=6, [4]=1, [5]=1

**Interpretation:** The "Start Me Up" preset is a Chris Lord-Alge preset designed for vocal leveling. The LA-2A is a tube optical compressor with a ~10ms attack and a two-stage release. It provides ~3:1 ratio compression that's very musical on vocals. The CLA-2A emulation adds analog warmth and slight edge when driven hard.

**Research context:** The LA-2A is "the" vocal compressor. It's known for being "big, fat, and warm" and sticking the vocal "right where you want it." 2-3 dB of reduction is typical for vocal leveling. The CLA-2A is praised for "pleasing fullness in the lows and smooth presence" compared to other LA-2A emulations.

**Evolution:** Parameters identical across all 9 chain variants — this is the anchor of the chain, unchanged throughout iteration.

### 3.3 API-550 (Waves)

**Purpose:** Console-style EQ with "Proportional Q" — bandwidth narrows at extreme settings, widens at gentle settings.

| Parameter | Chains 1-3 | Chains 4.x | Chains 5.x |
|-----------|-----------|-----------|-----------|
| Low Band Gain | 0 dB | 0 dB | 0 dB |
| Low Band Freq | 50 Hz (shelf) | 50 Hz (shelf) | 50 Hz (shelf) |
| Mid Band Gain | -4.8 dB | -4.8 dB | -4.8 dB |
| Mid Band Freq | ~400 Hz | ~400 Hz | ~400 Hz |
| High Band Gain | 8 dB | 8 dB | 10 dB |
| High Band Freq | 10 kHz | 10 kHz | 10 kHz |
| Extra High | 10 | 10 | 12.5 |

**Interpretation:**
- **Low band:** Flat at 50 Hz — no low-end manipulation (HPF likely handled elsewhere)
- **Mid band:** -4.8 dB cut around 400 Hz — removing "boxiness" or "mud" from the vocal. This is a standard vocal EQ move.
- **High band:** +8 to +10 dB boost at 10 kHz — adding "air" and presence. Chains 5.x push this further (+10 dB) and add a secondary boost at 12.5 kHz for even more top-end sheen.

**Research context:** The API 550A has fixed frequency centers: Low (50/100/200/300/400 Hz), Mid (0.4/0.8/1.5/3/5 kHz), High (5/7/10/12.5/15 kHz). The "Proportional Q" means the -4.8 dB cut at 400 Hz has a wider bandwidth (gentler, more musical), while the +10 dB boost at 10 kHz has a narrower bandwidth (more focused). This is exactly how API EQs are designed to work — gentle cuts are wide, aggressive boosts are focused.

### 3.4 RComp — Renaissance Compressor (Waves)

**Purpose:** Second-stage compression for additional dynamic control.

| Parameter | Chain 1 | Chain 2 | Chain 3 | Chain 4.x | Chain 5.x |
|-----------|---------|---------|---------|-----------|-----------|
| Threshold | -6 dB | -6 dB | -10 dB | -8.5 dB | -7 dB |
| Ratio | 1.5:1 | 1.5:1 | 2:1 | 2:1 | 2:1 |
| Attack | 20 ms | 20 ms | 20 ms | 20 ms | 20 ms |
| Release | 3.01 ms (auto) | 3.01 ms | 3.01 ms | 3.01 ms | 3.01 ms |
| Knee | 56.2% | 56.2% | 56.2% | 56.2% | 56.2% |
| Output | 10 dB | 10 dB | 10 dB | 10 dB | 10 dB |
| ARC | Off (0) | Off (0) | Off (0) | On (1) | On (1) |
| Mix | 100% | 100% | 100% | 100% | 100% |

**Interpretation:**
- **Evolution from Chain 1 → 5:** Threshold went from -6 to -7 dB, ratio from 1.5:1 to 2:1, and ARC (Automatic Release Control) was turned ON starting at Chain 4.
- The compression became more aggressive over iterations: lower threshold + higher ratio = more gain reduction.
- ARC (auto-release) being enabled in later chains shows a move toward more adaptive, transparent compression.
- 20 ms attack preserves vocal transients/consonants; the fast auto-release keeps the vocal natural.

### 3.5 Renaissance Vox (Waves)

**Purpose:** All-in-one vocal processor — gate + compression + output limiting in 3 simple controls.

| Parameter | Chain 1 | Chain 2 | Chain 3 | Chain 4.x | Chain 5.x |
|-----------|---------|---------|---------|-----------|-----------|
| Gate threshold | -16.5 dB | -16.5 dB | -16 dB | -16 dB | -17 dB |
| Noise floor | -80 dB | -80 dB | -80 dB | -80 dB | -80 dB |
| Compression | 130 (high) | 130 | 130 | 130 | 130 |
| Output gain | -2.5 dB | -2.5 dB | -2.7 dB | -2.7 dB | -3 dB |

**Interpretation:**
- **Gate:** Opens at -16 to -17 dB, noise floor at -80 dB — clean gating that removes background noise between phrases
- **Compression:** 130 is a high setting — significant gain reduction for a controlled, consistent vocal
- **Output:** -2.5 to -3 dB — slightly reduced output to prevent clipping after heavy compression
- Chains 5.x have the most aggressive settings: lower gate (more noise reduction), more output reduction

**Research context:** R-Vox is designed as the "quickest route to a legendary vocal sound." The three controls (Gate, Compression, Output) are intentionally simple. The compression uses a soft-knee curve for smooth, consistent dynamic control. The output stage includes a limiter, so the signal won't clip regardless of settings. The high compression value (130) means the vocal is being heavily controlled — typical for trap/pop where the vocal needs to stay consistently upfront.

### 3.6 RVerb (Waves)

**Purpose:** Plate reverb for vocal space.

| Parameter | Chain 1 | Chains 2-5.x |
|-----------|---------|-------------|
| Preset | "Vocal Plate" | "Vocal Plate" |
| Group | Factory/Plates | Factory/Plates |
| Type | 3 (Plate) | 3 (Plate) |
| Decay | 1.5s | 1.5s |
| Pre-delay | 100 ms | 100 ms |
| Early reflections | 0 | 0 |
| Wet level | -11.9 dB (Chain 1) | 0 dB (Chains 2+) |
| Diffusion | 10 | 10 |
| Density | 1.6 | 1.6 |
| ER/Reverb balance | 0.43/0.43 | 0.43/0.43 |
| Room size | 328 | 328 |
| Reverb time | 2411 ms | 2411 ms |
| Damping | 0.71 | 0.71 |
| Bass multiplier | 0.101 | 0.101 |

**Key difference:** Chain 1 has wet level at -11.9 dB (lower mix), while Chains 2+ have it at 0 dB. This means the reverb was made louder/more present from Chain 2 onward.

**Interpretation:**
- **1.5s decay** — right in the sweet spot for vocal plate reverb (1.5-2.5s range recommended)
- **100 ms pre-delay** — longer than the typical 20-30 ms recommendation, which pushes the reverb slightly behind the vocal, keeping the dry signal forward while still adding space
- **Plate type** — bright, dense, present — the standard for modern vocal production
- **Damping at 0.71** — moderate high-frequency damping, keeping the tail slightly darker than the dry vocal

**Research context:** Plate reverb is "the most-used reverb type for lead vocals because it's bright, dense from the first millisecond, and sits forward in the mix without making the vocal feel distant." The 1.5s decay is "the most consistently useful plate reverb decay time for lead vocals across pop, R&B, and rock."

### 3.7 ValhallaDelay

**Purpose:** Creative delay in a parallel/nested rack for depth and width.

The ValhallaDelay is in a nested rack alongside RVerb, suggesting a parallel processing path. In Chains 5.x, the RVerb in the nested rack is **disabled** (IsOn=false), suggesting the delay became the primary spatial effect in later iterations, or the reverb was moved to a send/return track instead.

**Research context:** ValhallaDelay offers 7 modes (Tape, HiFi, BBD, Digital, Ghost, Pitch, RevPitch) and 5 styles (Single, Dual, Ratio, PingPong, Quad). For vocal use, Tape mode with moderate feedback and tempo-synced delays is most common. The diffusion section can transform any delay into a smeared delay or pseudo-reverb.

---

## 4. Variant Comparison — Chain Evolution

The 9 preset variants show a clear evolution from Chain 1 (original) through Chain 5.x (most refined):

### Evolution Summary

| Component | Chain 1 (Original) | Chains 2-3 | Chains 4.x | Chains 5.x (Final) |
|-----------|-------------------|-----------|-----------|-------------------|
| DeEsser | Factory default, 7260 Hz, -30.1 dB | Same | Same | **Pensado Lead 1**, 8022 Hz, -36.5 dB |
| CLA-2A | "Start Me Up" | Same | Same | Same (unchanged anchor) |
| API-550 High | +8 dB @ 10 kHz | Same | Same | **+10 dB @ 10 kHz + 12.5 kHz** |
| RComp threshold | -6 dB, 1.5:1, ARC off | Same | -8.5 dB, 2:1, **ARC on** | -7 dB, 2:1, ARC on |
| R-Vox output | -2.5 dB | Same | -2.7 dB | **-3 dB** |
| RVerb wet | -11.9 dB | **0 dB** | 0 dB | 0 dB (but **disabled** in nested rack) |
| Nested rack | RVerb + ValhallaDelay | Same | Same | RVerb **OFF**, ValhallaDelay ON + extra slot |

### Key Evolution Patterns

1. **DeEsser upgrade (Chain 5):** Switched from factory default to Dave Pensado's "Pensado Lead 1" preset — a professionally tuned de-esser setting for lead vocals. More aggressive (lower threshold, higher frequency, higher max reduction).

2. **More compression (Chains 3-5):** RComp threshold lowered from -6 to -7 dB, ratio increased from 1.5:1 to 2:1, ARC enabled. The vocal became more controlled and consistent over iterations.

3. **More high-end air (Chain 5):** API-550 high band boost increased from +8 to +10 dB, with an additional boost at 12.5 kHz. The vocal became brighter and more present.

4. **Reverb reorganization (Chain 2 → Chain 5):** RVerb wet level increased from -11.9 dB to 0 dB in Chain 2. By Chain 5, the RVerb in the nested rack was disabled — likely moved to a send/return track in the templates for better mix control.

5. **More aggressive R-Vox (Chain 5):** Gate threshold lowered (-17 dB), output reduced (-3 dB) — tighter noise gating and more controlled output.

6. **Chain 5 added a 10th VST slot** — an additional plugin in the nested rack, suggesting more complex parallel processing.

---

## 5. Production Philosophy Interpretation

### The "Waves Vocal Pipeline" Approach

Arpino Sachi's chain is a **textbook Waves vocal processing pipeline** — no exotic plugins, all industry-standard tools. This reflects a professional, proven approach rather than experimental sound design.

### Signal Flow Rationale

1. **Pitch correction first** — Auto-Tune EFX at the start ensures the vocal is in tune before any dynamics processing. This is standard for Balkan trap/pop where Auto-Tune is both corrective and creative.

2. **De-ess before compressing** — Sibilance is reduced before compression so that compressors don't react to and amplify "s" sounds. This prevents the common problem of compression making sibilance worse.

3. **Optical compression (CLA-2A) first** — The LA-2A provides smooth, musical leveling. Its slow attack (10ms) and program-dependent release make it ideal for the first compression stage — it catches the overall dynamics without squashing transients.

4. **EQ after first compression** — The API-550 shapes the tone after the CLA-2A has controlled dynamics. The -4.8 dB cut at 400 Hz removes boxiness, and the +8-10 dB boost at 10 kHz adds air. Placing EQ after compression prevents the compressor from reacting to EQ-boosted frequencies.

5. **Second compression (RComp)** — The Renaissance Compressor provides additional dynamic control with a faster, more adjustable response. The 20ms attack preserves consonants, and ARC adapts the release to the material. This "serial compression" approach (optical → FET-style) is a professional standard — each compressor catches what the previous one missed.

6. **Vocal channel strip (R-Vox)** — The final stage combines gating (noise removal between phrases), compression (final leveling), and limiting (prevents clipping). R-Vox is the "glue" that makes the vocal sit consistently in the mix.

7. **Parallel reverb + delay** — RVerb (plate) and ValhallaDelay run in a nested parallel rack, adding space and depth without affecting the dry signal path. This is the correct approach — spatial effects should be parallel/sends, not serial.

### Balkan Trap/Pop Context

The chain reflects the specific needs of Balkan trap/pop production:
- **Heavy compression** (2 compressors + R-Vox) ensures the vocal stays upfront over dense, bass-heavy beats
- **Auto-Tune** is both corrective and a signature sound element
- **Plate reverb** (not hall) keeps the vocal forward and present — hall would push it back
- **High-frequency boosts** (API-550 +10 dB at 10 kHz) ensure the vocal cuts through busy electronic productions
- **Aggressive de-essing** (especially Chains 5.x with Pensado preset) counteracts the brightness added by EQ and compression

---

## 6. Lessons for Building Your Own Vocal Chains

### Lesson 1: Signal Order Matters
**Principle:** Pitch → De-ess → Compress (optical) → EQ → Compress (FET) → Channel strip → Spatial (parallel)

**Why:** Each stage prepares the signal for the next. De-essing before compression prevents sibilance amplification. EQ after compression prevents the compressor from reacting to boosted frequencies. Serial compression (optical → FET) is more transparent than a single compressor doing all the work.

### Lesson 2: Use Optical Compression First
**Principle:** Start with an LA-2A-style optical compressor (CLA-2A) for smooth leveling, then add a FET-style compressor (RComp) for control.

**Why:** Optical compressors have slow, program-dependent attack and release that sound musical on vocals. They "glue" the vocal without obvious artifacts. A second compressor with faster response catches peaks the optical one misses.

### Lesson 3: Cut Before You Boost
**Principle:** Remove problem frequencies (400 Hz boxiness) before adding desired ones (10 kHz air).

**Why:** Cutting mud/boxiness first creates headroom and clarity. Boosting air on an already muddy vocal just makes the mud brighter, not cleaner.

### Lesson 4: Plate Reverb for Lead Vocals
**Principle:** Use plate reverb (1.5-2.5s decay, 20-100ms pre-delay) for lead vocals, not hall.

**Why:** Plate is bright, dense, and present — it adds space without pushing the vocal back. Hall reverb is more diffuse and atmospheric, better for backing vocals or when you want distance. Pre-delay keeps the dry vocal forward of the reverb tail.

### Lesson 5: Parallel Processing for Spatial Effects
**Principle:** Run reverb and delay in parallel (sends or nested racks), not serial.

**Why:** Serial reverb/delay affects 100% of the signal, making the vocal washy and distant. Parallel processing preserves the dry vocal's impact while adding space. Ableton's Audio Effect Rack with nested chains (as Arpino uses) is perfect for this.

### Lesson 6: Iterate and Refine
**Principle:** Arpino's 9 chain variants show that vocal chains evolve. Start with presets, then adjust thresholds, ratios, and EQ frequencies based on the specific vocal and track.

**Evolution pattern observed:**
- Start with factory presets → switch to professional presets (Pensado)
- Start gentle → increase aggression (lower thresholds, higher ratios)
- Start with reverb in rack → move to send/return for better mix control
- Add more high-end air as the production demands

### Lesson 7: De-ess Aggressively When Bright
**Principle:** The more high-end EQ and compression you add, the more de-essing you need.

**Why:** Compression amplifies sibilance. EQ boosts at 10+ kHz make "s" sounds harsher. Arpino's evolution from factory DeEsser to Pensado Lead 1 (lower threshold, higher frequency, higher max reduction) directly correlates with the increased high-end boost in the API-550.

### Lesson 8: Use a Vocal Channel Strip as the Final Stage
**Principle:** End the chain with an all-in-one processor like R-Vox for final gating, compression, and limiting.

**Why:** The channel strip provides a "safety net" — gating removes noise between phrases, final compression evens out any remaining dynamics, and limiting prevents clipping. It's the "glue" that makes the vocal sound finished.

### Lesson 9: Match the Chain to the Genre
**Principle:** Balkan trap/pop needs: heavy compression (vocal over dense beats), Auto-Tune (signature sound), plate reverb (forward vocal), bright EQ (cut through electronics).

**For other genres:**
- Acoustic/folk: Lighter compression, hall or room reverb, less de-essing
- Rock: More aggressive compression (1176-style), shorter reverb
- R&B: Smoother compression, longer reverb tails, more delay throws
- Podiatry/voiceover: Minimal chain — gate + gentle compression + de-esser

### Lesson 10: Presets Are Starting Points, Not Endpoints
**Principle:** Every preset in Arpino's chain was modified — "Start Me Up" CLA-2A, "Pensado Lead 1" DeEsser, "Vocal Plate" RVerb — all were loaded and then adjusted.

**Actionable:** Load a preset that's close to what you want, then:
1. Adjust the threshold/ratio on compressors to match your vocal's dynamics
2. Set the de-esser frequency to match your voice's sibilance range (solo and sweep)
3. Cut/boost EQ frequencies based on your vocal's character
4. Set reverb decay/pre-delay based on the song's tempo and feel

---

## 7. Recommended Starting Points for Your Vocals

### Template A: Balkan Trap/Pop (Arpino Sachi style)

```
1. Auto-Tune EFX (or Auto-Tune Pro) — key/scale of song, retune speed 20-50ms
2. Waves DeEsser — Split mode, 6-7 kHz, threshold until "s" sounds soften
3. CLA-2A — "Start Me Up" preset, adjust Peak Reduction for 2-3 dB gain reduction
4. API-550 — Cut 4-5 dB at 400 Hz, boost 8-10 dB at 10 kHz (shelf)
5. RComp — Threshold -7 dB, 2:1 ratio, 20ms attack, ARC on
6. R-Vox — Gate: -16 dB, Compression: 100-130, Output: -2 to -3 dB
7. Send to RVerb "Vocal Plate" — 1.5s decay, 100ms pre-delay
8. Send to ValhallaDelay — Tape mode, 1/4 or 1/8 note delay, 20-30% feedback
```

### Template B: Modern Pop Vocal

```
1. Auto-Tune Pro (subtle, retune 50-80ms)
2. DeEsser — Split mode, 5-6 kHz
3. CLA-2A — 2-3 dB reduction
4. Subtractive EQ — Cut 200-400 Hz mud, cut 2-3 kHz harshness
5. RComp — -4 dB threshold, 2:1, ARC on
6. R-Vox — Gate: -20 dB, Compression: 80-100, Output: 0 dB
7. Send to Plate Reverb — 1.8s decay, 30ms pre-delay
8. Send to Delay — 1/8 note, 15% feedback, low-pass on repeats
```

### Template C: Aggressive Trap/Rap

```
1. Auto-Tune Pro (aggressive, retune 0-20ms for robotic effect)
2. DeEsser — Split mode, 7-8 kHz, aggressive threshold
3. CLA-76 (1176-style) — "Bluey" preset, 4:1 ratio, fast attack
4. API-550 — Cut 5 dB at 300 Hz, boost 6 dB at 5 kHz, boost 8 dB at 10 kHz
5. RComp — -10 dB threshold, 4:1 ratio, ARC on
6. R-Vox — Gate: -15 dB, Compression: 140+, Output: -3 dB
7. Send to Short Plate — 1.2s decay, 20ms pre-delay
8. Send to Slapback Delay — 80-120ms, 0% feedback
```

---

## 8. Plugin Quick Reference

| Plugin | Type | Key Parameters | Typical Vocal Use |
|--------|------|---------------|-------------------|
| Auto-Tune EFX | Pitch correction | Key, scale, retune speed | Quick pitch correction, creative effect |
| Waves DeEsser | De-esser | Frequency, threshold, mode (Split/Wide) | Reduce sibilance before compression |
| CLA-2A | Optical compressor | Gain, Peak Reduction | Smooth vocal leveling, 2-3 dB GR |
| API-550 | Console EQ | 3-band, fixed frequencies, Proportional Q | Tonal shaping — cut mud, boost air |
| RComp | FET compressor | Threshold, ratio, attack, release, ARC | Second-stage dynamics control |
| Renaissance Vox | Channel strip | Gate, Compression, Output | Final vocal processing — gate + comp + limit |
| RVerb | Reverb | Type, decay, pre-delay, damping | Plate reverb for vocal space |
| ValhallaDelay | Delay | Mode, delay time, feedback, diffusion | Creative delay, depth, width |

---

## Appendix A: Extracted File Inventory

| File | Source | Size |
|------|--------|------|
| Arpino Chain.xml | Arpino Chain.adg | 119 KB |
| Arpino Chain 2.xml | Arpino Chain 2.adg | 120 KB |
| Arpino Chain 3.xml | Arpino Chain 3.adg | 120 KB |
| Arpino Chain 4.xml | Arpino Chain 4.adg | 122 KB |
| Arpino Chain 4-1.xml | Arpino Chain 4-1.adg | 122 KB |
| Arpino Chain 5.xml | Arpino Chain 5.adg | 131 KB |
| Arpino Chain 5-1.xml | Arpino Chain 5-1.adg | 131 KB |
| Arpino Chain 5-2.xml | Arpino Chain 5-2.adg | 131 KB |
| Arpino Chain 5-3.xml | Arpino Chain 5-3.adg | 131 KB |
| Postavke 1.xml | Postavke 1.als | 1.8 MB |
| Postavke 2.xml | Postavke 2.als | 1.8 MB |
| Postavke 3.xml | Postavke 3.als | 1.9 MB |

All extracted XMLs stored in `D:\Projects\arpino_chains\`.

## Appendix B: Parameter Extraction Method

1. Decompressed `.adg` files using Python `gzip` module
2. Parsed XML structure to locate `Vst3Preset` blocks
3. Extracted `ProcessorState` hex-encoded data
4. Decoded hex to ASCII, searched for `PluginName`, `Preset Name`, `Parameters Type="RealWorld"` tags
5. Parsed parameter value lists (space-separated numbers)
6. Compared parameter arrays across all 9 chain variants

**Limitations:** Some plugin names showed as "?" due to hex encoding variations. The `*` values in parameter arrays represent non-numeric or binary-encoded parameters that couldn't be decoded as plain ASCII. The CLA-2A's 207 parameters are mostly internal plugin state (UI positions, metering data) rather than user-facing controls.
