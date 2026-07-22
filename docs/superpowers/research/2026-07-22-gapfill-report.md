# Gap-Fill Research Report

**Date:** 2026-07-22  
**Context:** Windows 10/11, CPU-only (i7-4770-class, 16 GB), Python 3.11, open-source/free only  
**Method:** Exhaustive web search per item, verified against live repo/project pages

---

## 1. Free Mixing Plugin Suites with Windows VST3 Builds

### 1.1 Plugin Suites

| Item | Repo/URL | License | Last Release/Commit | Windows VST3 | Verdict | Confidence |
|------|----------|---------|-------------------|--------------|---------|------------|
| **Airwindows Consolidated** | [github.com/baconpaul/airwin2rack](https://github.com/baconpaul/airwin2rack) | MIT | Builds updated weekly; ~500+ algorithms as of March 2026 | Yes — VST3 native, CLAP, AU, LV2, standalone. Windows installer (.exe) and .zip | **INTEGRATE** | Verified |
| **Dragonfly Reverb** | [github.com/michaelwillis/dragonfly-reverb](https://github.com/michaelwillis/dragonfly-reverb) | GPL-3.0 | v3.2.10 (2023-04-23); last push 2026-02-03; 51 releases | Yes — VST3, CLAP, LV2. Windows 32/64-bit .zip downloads | **INTEGRATE** | Verified |
| **ZL Equalizer 2** | [github.com/ZL-Audio/ZLEqualizer](https://github.com/ZL-Audio/ZLEqualizer) | AGPL-3.0 | v1.2.2 (2026-06-27); 878 stars; 27 releases | Yes — VST3, LV2, AAX. Windows x86-64 MSI installer | **INTEGRATE** | Verified |
| **ZL Compressor** | [github.com/ZL-Audio/ZLCompressor](https://github.com/ZL-Audio/ZLCompressor) | AGPL-3.0 | v0.5.0 (2026-05-06) | Yes — VST3, LV2, AAX. Windows x86-64 MSI installer | **INTEGRATE** | Verified |
| **LSP (Linux Studio Plugins)** | [github.com/lsp-plugins/lsp-plugins](https://github.com/lsp-plugins/lsp-plugins) | LGPL-3.0 | v1.2.29 (2026-04-01); 790 stars | VST3 full support in source. **Windows binaries are PAID** — free only for Linux/FreeBSD. Can build from source on Windows (MinGW) | **EVALUATE** | Verified |
| **x42 plugins** | [x42-plugins.com](https://x42-plugins.com/x42/) | GPL-2.0 | Windows LV2 builds 2026-01-26 | **No VST3** — LV2 only. Developer explicitly stated no VST3/CLAP plans | **SKIP** | Verified |
| **Calf Studio Gear** | [github.com/calf-studio-gear/calf](https://github.com/calf-studio-gear/calf) | LGPL-2.1 | Last push 2026-01-18; 769 stars | **No VST3** — LV2 only, Linux-focused. Windows build possible via vcpkg but LV2 format only | **SKIP** | Verified |
| **oXygen (Mastering)** | [github.com/Wamphyre/oXygen](https://github.com/Wamphyre/oXygen) | BSD-3-Clause | v1.0.4 (2026-04-15); 30 stars | VST3. Windows build via CMake + VS2022 (manual). No pre-built Windows binaries | **EVALUATE** | Verified |
| **Hott Master** | [github.com/pndias/hott-master-vst](https://github.com/pndias/hott-master-vst) | GPL-3.0 | 2 stars; JUCE 7 | VST3. Windows build via `build-windows.bat`. Pre-built downloads on Releases page | **EVALUATE** | Verified |
| **Triptych** | [github.com/basilica-audio/Triptych](https://github.com/basilica-audio/Triptych) | AGPL-3.0 | Created 2026-07-14; pre-1.0 | VST3 planned. No pre-built binaries yet | **EVALUATE** | Verified |

**Summary — Plugin Suites:**

- **Best picks for free Windows VST3 mixing:** Airwindows Consolidated (500+ FX, MIT, weekly updates), ZL Equalizer 2 + ZL Compressor (AGPL, very active 2026), Dragonfly Reverb (GPL, reverb suite).
- **LSP:** Excellent plugin suite but Windows binaries are paid. Source is free (LGPL-3.0) and buildable with MinGW, but the build process is non-trivial on Windows. Evaluate if build effort is worth it.
- **x42 and Calf:** Both are LV2-only. Would need an LV2-to-VST3 host wrapper (like Carla) to use in a VST3-only workflow. Not worth the complexity.

### 1.2 Auto-Mixing Tools (Honest Maturity)

| Item | Repo/URL | License | Last Activity | Interface | Verdict | Confidence |
|------|----------|---------|--------------|-----------|---------|------------|
| **Keel** | [github.com/fcarvajalbrown/Keel](https://github.com/fcarvajalbrown/Keel) | AGPL-3.0 (engine), PolyForm Noncommercial (GUI) | Created 2026-06-15; beta | Python CLI + Qt6 standalone GUI. VST plugin planned | **EVALUATE** | Verified |
| **Phantom** | [github.com/fadelabs/phantom](https://github.com/fadelabs/phantom) | AGPL-3.0 | v1.3.1 on PyPI; active | Python MCP tools (19 analysis tools), CLI, Reaper integration | **INTEGRATE** | Verified |
| **Demucs automix.py** | [github.com/facebookresearch/demucs/blob/main/tools/automix.py](https://github.com/facebookresearch/demucs/blob/main/tools/automix.py) | MIT | Part of demucs repo | Python script (research utility, not a product) | **EVALUATE** | Verified |
| **MixMaid** | [github.com/GareBear99/MixMaid](https://github.com/GareBear99/MixMaid) | MIT (free tier) | 2026; 4 stars | VST3 plugin | **EVALUATE** | Verified |

**Honest maturity assessment:**

- **No production-grade open-source auto-mixing tool exists.** All projects are either brand-new (Keel, created June 2026), research scripts (Demucs automix.py), or early-stage plugins (MixMaid).
- **Phantom** is the most mature for *analysis* (masking, loudness, spectral balance) but does not perform auto-mixing — it diagnoses and suggests. It integrates with Reaper via MCP, not as a VST3.
- **Keel** is the closest to deterministic auto-mix + auto-master (LUFS balancing, true-peak limiting) but is beta and the GUI is non-commercial license only.
- **Nothing credible exists** for AI-driven automatic mixing at production quality. The field is at the "diagnose and suggest" stage, not "automatically mix."

### 1.3 Per-Stem Loudness/Masking Analysis OSS

| Item | Repo/URL | License | Last Activity | Interface | Verdict | Confidence |
|------|----------|---------|--------------|-----------|---------|------------|
| **Phantom** | [github.com/fadelabs/phantom](https://github.com/fadelabs/phantom) | AGPL-3.0 | v1.3.1 PyPI; active 2026 | Python (MCP tools, CLI) | **INTEGRATE** | Verified |
| **pyloudnorm** | [pypi.org/project/pyloudnorm](https://pypi.org/project/pyloudnorm) | MIT | Maintained | Python library (ITU-R BS.1770-4) | **INTEGRATE** | Likely |

**Phantom details:**
- 19 MCP tools covering: spectrum, loudness (EBU R128), dynamics, stereo field, phase coherence, frequency masking between stems, problem detection (clipping, hum, DC offset, sibilance), genre reference profiles
- `multi_stem_masking` tool: per-octave frequency overlap between stems, collision severity ranking
- `batch_diagnostic`: up to 50 files in parallel
- Patent notice: weighted frequency masking analysis is patent-pending (US Provisional 64/055,566), but AGPL-3.0 includes automatic patent grant for open-source users
- Python 3.10–3.13, pip installable: `pip install phantom-audio`

---

## 2. Vocal Time-Alignment and Pitch-Shift Harmony/Doubles

### 2.1 Vocal Time-Alignment (VocAlign-style) OSS

| Item | Repo/URL | License | Last Activity | Interface | Verdict | Confidence |
|------|----------|---------|--------------|-----------|---------|------------|
| **VocalForge** | [github.com/Artemarius/VocalForge](https://github.com/Artemarius/VocalForge) | Not specified (components MIT/BSD) | Active | Python + PySide6 GUI | **EVALUATE** | Verified |
| **OttoAlign2** | [github.com/sebedard-creator/OttoAlign2](https://github.com/sebedard-creator/OttoAlign2) | Not specified | Active | Python 3.11 + Flask web UI | **EVALUATE** | Verified |
| **PodSync** | [github.com/kaushikgopal/podsync](https://github.com/kaushikgopal/podsync) | Not specified | 2026-03-23; Rust CLI | Rust CLI | **SKIP** | Verified |
| **TrackSnap** | [tracksnapfx.com](https://tracksnapfx.com) | Proprietary (free Early Access until 06/30/2026) | 2026 | VST3, Windows/Mac | **SKIP** | Verified |

**Assessment:**

- **No credible open-source VocAlign equivalent exists.** VocAlign uses proprietary time-warping DSP (based on acoustic fingerprinting and dynamic time warping) that has not been replicated in open source.
- **VocalForge** does cross-correlation-based alignment (not time-warping). It aligns takes by finding the best offset, not by warping timing to match a reference. Useful for aligning a recording to a backing track, but not for tightening vocal doubles.
- **OttoAlign2** uses GCC-PHAT + cubic spline interpolation for sub-sample alignment. Designed for post-production AAF workflows (lavalier/boom alignment), not vocal doubles. High-quality alignment but not time-warping.
- **PodSync** is podcast double-ender alignment (MFCC cross-correlation). Not applicable.
- **TrackSnap** is the closest functional equivalent to VocAlign but is proprietary (free during Early Access only, expires June 2026). Not open source.
- **"Nothing credible exists" for open-source VocAlign-style time-warping alignment.** The gap is real. A Python implementation using DTW (dynamic time warping) on pitch contours + PSOLA resynthesis is theoretically possible but would be novel work.

### 2.2 Pitch-Shift-Based Harmony/Doubles Generation

| Item | Repo/URL | License | Last Activity | Interface | Verdict | Confidence |
|------|----------|---------|--------------|-----------|---------|------------|
| **Rubber Band Library** | [github.com/breakfastquay/rubberband](https://github.com/breakfastquay/rubberband) | GPL-2.0 (commercial available) | v4.0.0; Debian 4.0.0-2 (2026) | CLI (`rubberband`), C++ library, LADSPA/LV2 | **INTEGRATE** | Verified |
| **HachiTune** | [github.com/KCKT0112/HachiTune](https://github.com/KCKT0112/HachiTune) | AGPL-3.0 | v0.1.2 (2026-03-08); 101 stars | VST3/AU plugin + standalone, Windows | **EVALUATE** | Verified |
| **DiffSinger pitch transposition** | [github.com/nathanstep55/pitch-transposition-using-DiffSinger](https://github.com/nathanstep55/pitch-transposition-using-DiffSinger) | Apache-2.0 | 2025-03-20 | Python CLI | **EVALUATE** | Verified |
| **MIT AI Harmonizer** | [github.com/mitmedialab/ai-harmonizer-nime2025](https://github.com/mitmedialab/ai-harmonizer-nime2025) | Not specified (RVC fork) | NIME 2025 paper | Python | **EVALUATE** | Verified |
| **PitchShifter (vanishady)** | [github.com/vanishady/PitchShifter](https://github.com/vanishady/PitchShifter) | GPL-3.0 | 2024 | VST plugin, standalone | **EVALUATE** | Verified |
| **RVC (SawitProject fork)** | [github.com/SawitProject/rvc](https://github.com/SawitProject/rvc) | MIT | 2026 | Python CLI, REST API | **EVALUATE** | Verified |

**Assessment:**

- **Rubber Band** is the gold standard for offline pitch-shifting CLI. Already used by OpenSonic and AI_DJ. GPL-2.0 means toolshop must be GPL-compatible or acquire a commercial license. The `rubberband` CLI is callable from Python via subprocess. R3 engine produces high-quality results on vocals.
- **For doubles generation:** Pitch-shift by ±0.1–0.3 semitones + slight time-stretch (Rubber Band) + panning is the classic approach. No dedicated OSS "doubles generator" tool exists, but the building blocks (Rubber Band + librosa) are available.
- **For harmony generation:** No production-ready OSS tool exists. MIT AI Harmonizer is a research prototype biased toward baroque music. RVC can pitch-shift vocals but is voice-conversion, not harmony generation.
- **HachiTune** is the most interesting: neural pitch detection + vocoder resynthesis in a VST3 plugin. Can edit pitch in a piano roll and export. Could be used for manual harmony creation. AGPL-3.0, Windows VST3. Still v0.1.2.
- **DiffSinger pitch transposition** uses PC-NSF-HiFiGAN vocoder for high-quality pitch shifting. Python CLI. Apache-2.0. More advanced than Rubber Band for vocal-specific pitch shifting but requires model weights and CPU inference.

---

## 3. Python MIDI Foundation: music21 vs pretty_midi vs mido vs miditoolkit

| Library | Repo | License | Latest Release | Last Push | Stars | Python | Verdict | Confidence |
|---------|------|---------|---------------|-----------|-------|--------|---------|------------|
| **mido** | [github.com/mido/mido](https://github.com/mido/mido) | MIT | v1.3.3 (2024-10-25) | 2026-06-27 | 1625 | 3.7+ | **INTEGRATE** | Verified |
| **pretty_midi** | [github.com/craffel/pretty-midi](https://github.com/craffel/pretty-midi) | MIT | v0.2.11 (2025-10-08) | 2026-02-18 | 1031 | 3.7+ | **INTEGRATE** | Verified |
| **music21** | [github.com/cuthbertLab/music21](https://github.com/cuthbertLab/music21) | BSD-3-Clause | v10.5.0 (2026-06-17) | 2026-03-08 | 2450 | 3.11+ | **EVALUATE** | Verified |
| **miditoolkit** | [github.com/YatingMusic/miditoolkit](https://github.com/YatingMusic/miditoolkit) | MIT | v1.0.1 (2023-11-23) | 2024-06-10 | 277 | 3.7+ | **SKIP** | Verified |

**Maintenance state:**

- **mido:** Actively maintained. Last push June 2026. Low-level MIDI messages, ports, file I/O. Backend for both pretty_midi and miditoolkit. Full MIDI standard support (all 18 message types). SYX file support. Socket ports for MIDI over TCP/IP.
- **pretty_midi:** Actively maintained. v0.2.11 in October 2025. Last push February 2026. Works in **seconds** time unit. Includes fluidsynth synthesis support. Good for music transcription / audio-related workflows.
- **music21:** Very actively maintained. Multiple releases in 2026 (v9.9.0 → v10.5.0). 2450 stars. Focused on **musicological analysis** — chord analysis, key detection, voice leading, corpus studies. Heavy dependency (20 MB wheel). Requires Python 3.11+.
- **miditoolkit:** **Stale.** No commits since June 2024. No releases since November 2023. Works in **ticks** time unit. Piano-roll extraction. The README itself acknowledges it's inspired by pretty_midi. The only advantage (ticks vs seconds) is niche.

**Recommended combination for a 2026 project:**

```
mido (low-level I/O, ports, messages)
  + pretty_midi (high-level manipulation, seconds, synthesis)
```

- Use **mido** for raw MIDI file reading/writing and real-time I/O.
- Use **pretty_midi** for musical manipulation (note extraction, pitch/class representation, piano-roll, synthesis via fluidsynth).
- Add **music21** only if you need musicological analysis (key detection, chord labeling, voice-leading checks). It's a heavy dependency but unmatched for theory.
- **Skip miditoolkit** — it's stale and its ticks-based approach is a minor optimization that pretty_midi doesn't need for a toolshop project.

---

## 4. Legal Free Instrument Content for Trap/Drill/Pop

### 4.1 SFZ/SF2 Sources

| Source | URL | Format | License | Size | Content | Verdict | Confidence |
|--------|-----|--------|---------|------|---------|---------|------------|
| **VCSL (Versilian Community Sample Library)** | [github.com/sgossner/VCSL](https://github.com/sgossner/VCSL) | SFZ | **CC0 (Public Domain)** | 5 GB | Orchestral, world, experimental: strings, brass, woodwinds, percussion, keys | **INTEGRATE** | Verified |
| **VCSL Keys** | [versilian-studios.com/vcsl-keys](https://versilian-studios.com/vcsl-keys/) | SFZ | **CC0** | 680 MB | 3 grands, 2 uprights, 5 harpsichords | **INTEGRATE** | Verified |
| **Salamander Grand Piano** | [github.com/sfzinstruments/SalamanderGrandPiano](https://github.com/sfzinstruments/SalamanderGrandPiano) | SFZ | CC-BY-3.0 | 394+ MB | Yamaha C5, 16 velocity layers, 48kHz 24bit | **INTEGRATE** | Verified |
| **Sonatina Symphonic Orchestra (SSO)** | [github.com/peastman/sso](https://github.com/peastman/sso) | SFZ | CC Sampling Plus 1.0 | ~300 MB | Full orchestra: strings, brass, woodwinds, percussion | **EVALUATE** | Verified |
| **Virtual Playing Orchestra** | [virtualplaying.com](https://virtualplaying.com/virtual-playing-orchestra/) | SFZ | Various CC (see source licenses) | ~2 GB | Orchestral: sustain, staccato, pizzicato, tremolo articulations | **EVALUATE** | Verified |
| **FreePats General MIDI** | [freepats.zenvoid.org](http://freepats.zenvoid.org/) | SF2 + SFZ | **GPL-3.0+** (with special exception) | 227 MB (SF2) | General MIDI sound set | **EVALUATE** | Verified |
| **Meadowlark Factory Library** | [github.com/MeadowlarkDAW/meadowlark-factory-library](https://github.com/MeadowlarkDAW/meadowlark-factory-library) | WAV (SFZ planned) | **CC0** | — | One-shot electronic drums: 808s, kicks, snares, claps, hi-hats (EDM, House, DnB, Trap, Dubstep, Pop) | **INTEGRATE** | Verified |
| **GareBear99 Free 808 Producer Kit** | [github.com/GareBear99/Free-808-Producer-Kit](https://github.com/GareBear99/Free-808-Producer-Kit) | WAV | Free for commercial/non-commercial, no credit required. Do not redistribute as sample pack. | 94 files | 94 hand-crafted 808 bass samples, all chromatic keys, 7 characters, 70-160 BPM | **INTEGRATE** | Verified |
| **TR808-fischer** | [github.com/zynthian/TR808-fischer](https://github.com/zynthian/TR808-fischer) | SFZ | **CC0** | — | Roland TR-808 samples, 116 sounds, 16-bit 44.1kHz | **INTEGRATE** | Verified |
| **genAudio 808TK SFZ** | [github.com/sourc3array/genAudio_808TK_SFZ](https://github.com/sourc3array/genAudio_808TK_SFZ) | SFZ | GPL-3.0 (SFZ mapping); samples from Wave Alchemy 808 Tape (free) | 53 samples | 808 drum kit, 16 pads, 24-bit | **EVALUATE** | Verified |
| **Wave Alchemy 808 Tape** | [wavealchemy.co.uk/product/808-tape](https://www.wavealchemy.co.uk/product/808-tape/) | WAV | Free download; royalty-free for use in music production | — | TR-808 samples recorded to analog tape | **INTEGRATE** | Likely |
| **Aspirin-DX Soundbank (Fairytale Edition)** | [github.com/NeoSoundFonts/Aspirin-DX-Soundbank](https://github.com/NeoSoundFonts/Aspirin-DX-Soundbank) | SF2 | **CC0** (Fairytale Edition only) | — | General MIDI soundbank, removes non-free samples | **EVALUATE** | Verified |

### 4.2 SFZ Players (Required to Play SFZ Files)

| Player | URL | License | Last Release | Windows VST3 | Verdict | Confidence |
|--------|-----|---------|-------------|--------------|---------|------------|
| **Plogue sforzando** | [plogue.com/products/sforzando](https://www.plogue.com/products/sforzando.html) | Free (proprietary) | v1.982 (April 14, 2026) | Yes — VST3, AU, CLAP, AAX, standalone | **INTEGRATE** | Verified |
| **sfizz** | [github.com/sfztools/sfizz](https://github.com/sfztools/sfizz) | BSD-2-Clause | v1.2.3 (2024-01-14); **archived** | Yes — VST3, AU, LV2 | **EVALUATE** | Verified |

**Assessment:**

- **Best CC0 sources for trap/drill/pop:**
  - **808s:** GareBear99 Free 808 Producer Kit (94 chromatic WAVs, commercial-use OK), TR808-fischer (CC0 SFZ), Meadowlark Factory Library (CC0, trap-specific one-shots), Wave Alchemy 808 Tape (free, royalty-free)
  - **Keys:** VCSL Keys (CC0, 3 grands + 2 uprights + 5 harpsichords), Salamander Grand Piano (CC-BY-3.0, high quality)
  - **Strings/Brass:** VCSL (CC0, full orchestra), Virtual Playing Orchestra (various CC, better articulations), SSO (CC Sampling Plus 1.0, lightweight)
- **SFZ player:** Plogue sforzando is the reference SFZ player. Free, VST3, actively updated (April 2026). sfizz is open-source (BSD-2) but archived since 2025.
- **License hierarchy for safety:** CC0 > CC-BY > CC Sampling Plus > GPL. All CC0 sources are safe for commercial use without attribution. CC-BY requires attribution. CC Sampling Plus 1.0 allows sampling but has redistribution quirks.

---

## 5. AbletonOSC Maintenance Status + FL Studio Programmatic Generation

### 5.1 AbletonOSC

| Field | Value |
|-------|-------|
| **Repo** | [github.com/ideoforms/AbletonOSC](https://github.com/ideoforms/AbletonOSC) |
| **License** | MIT |
| **Stars** | 728 |
| **Last push** | 2025-11-19 |
| **Latest release** | No formal releases (commit-based) |
| **Open PRs** | 5+ open PRs (June 2026), including Windows WSAECONNRESET fix (#214), OSC response routing fix (#208), compressor sidechain routing (#210), nested device discovery (#209) |
| **Contributors** | 20 |
| **Status** | **Maintained but slow.** Core functionality works with Ableton Live 11+. Community PRs are pending (not merged). No formal releases — users install from master. |

**Verdict: INTEGRATE** | Confidence: Verified

**Details:**
- AbletonOSC remains the only viable OSC bridge for Ableton Live.
- The maintainer (ideoforms) is still active but PR merge velocity is low — 5+ community PRs from May-June 2026 remain unmerged.
- Windows-specific fix (#214 for WSAECONNRESET) is important for Windows users and may need to be applied locally.
- No alternative exists. Ableton Live does not provide any other external control API.
- Requires Ableton Live 11+ (MIDI Remote Script surface).

### 5.2 FL Studio Project Format — Programmatic Generation

| Tool | Repo/URL | License | Last Activity | Capability | Verdict | Confidence |
|------|----------|---------|--------------|------------|---------|------------|
| **PyFLP** | [github.com/demberto/PyFLP](https://github.com/demberto/PyFLP) | GPL-3.0 | v2.2.1 (2023-06-05); dev v2.2.2.dev6 | Parse + modify FLP. Can read/write metadata, patterns, notes, playlist, mixer. **Cannot create from scratch.** Alpha status. | **EVALUATE** | Verified |
| **Music2DAW** | [github.com/jihadkhawaja/Music2DAW](https://github.com/jihadkhawaja/Music2DAW) | Not specified | 2026; .NET 10 | Inspect, edit, export FLP. Can create new FLP from template, edit tempo/channel/notes/playlist/mixer. MCP server for AI agents. | **EVALUATE** | Verified |
| **FL Studio MCP Server** | [github.com/CryptoJones/FL-Studio-MCP-Server](https://github.com/CryptoJones/FL-Studio-MCP-Server) | Not specified | 2026 | Offline FLP creation via PyFLP + live control via Flapi. Can create new .flp from Empty template, load samples, set metadata. | **EVALUATE** | Verified |
| **ts-flp** | [github.com/SpendLessDaw/ts-flp](https://github.com/SpendLessDaw/ts-flp) | Not specified | 2026 | TypeScript library. Non-destructive FLP read/modify. Metadata + sample paths only. | **SKIP** | Verified |
| **Flapi** | FL Studio built-in | N/A | Current | FL Studio's internal Python API (427+ functions). Runs inside FL only. Cannot create channels/patterns from scratch at runtime. Cannot load plugins via API. | **N/A** | Verified |

**Verdict: FL Studio is NO LONGER a complete dead end, but remains severely limited.** | Confidence: Verified

**Key findings:**

1. **FLP format is undocumented and evolving.** All tools are reverse-engineered. PyFLP's last release was June 2023; the dev version (2.2.2.dev6) is the current state.
2. **Music2DAW** (2026, .NET 10) is the most capable tool: can create new FLP from a template, edit notes, playlist, mixer, and export MIDI. It handles the FL Studio 25 (2025) 80-byte playlist record layout that PyFLP 2.2.1 cannot round-trip. However, it's .NET-only (not Python).
3. **FL Studio MCP Server** wraps PyFLP for offline creation + Flapi for live control. Can create new .flp from Empty template with metadata and loaded samples. But: "Composing new channels, patterns, and notes from scratch is not exposed by PyFLP's public model API" — that requires Flapi (live, FL running).
4. **Hard limitations remain:**
   - Cannot load/insert VST plugins via any API (FL Studio or external)
   - Cannot click "Render to WAV" via API
   - Piano Roll note injection requires a keyboard shortcut trigger (not pure API)
   - FL's native Undo is unreliable for API scripts
5. **Compared to AbletonOSC:** AbletonOSC provides full OSC control of a running Live instance (transport, clips, mixer, devices, parameters). FL Studio's Flapi is more powerful (427+ functions) but runs inside FL only and has the limitations above. For programmatic *generation* (not live control), AbletonOSC + Ableton Live is more capable.

**Bottom line:** FL Studio project format is no longer a complete dead end — Music2DAW and FL Studio MCP Server can create and edit .flp files programmatically. But it remains far more limited than Ableton Live + AbletonOSC for programmatic music production. The format's undocumented nature and FL's API restrictions (no plugin loading, no audio render, limited note injection) make it a poor choice for automated production pipelines.

---

## Summary Table

| Topic | Best Pick(s) | Verdict |
|-------|-------------|---------|
| **Free VST3 mixing plugins** | Airwindows Consolidated (MIT), ZL Equalizer 2 + Compressor (AGPL), Dragonfly Reverb (GPL) | 3 INTEGRATE |
| **Auto-mixing tools** | Keel (deterministic automix, beta), Phantom (analysis only) | Nothing production-grade exists |
| **Per-stem masking analysis** | Phantom (AGPL, MCP tools, patent-pending masking) | 1 INTEGRATE |
| **Vocal time-alignment OSS** | Nothing credible exists for VocAlign-style time-warping | No credible OSS equivalent |
| **Harmony/doubles generation** | Rubber Band CLI (GPL, pitch-shift building block), HachiTune (AGPL, VST3 pitch editor) | No dedicated tool; building blocks available |
| **Python MIDI** | mido + pretty_midi (both MIT, active) | Recommended combination |
| **Free instruments (808s)** | GareBear99 808 Kit (free commercial), TR808-fischer (CC0), Meadowlark (CC0), Wave Alchemy 808 Tape (free) | 4 INTEGRATE |
| **Free instruments (keys/strings/brass)** | VCSL (CC0), VCSL Keys (CC0), Salamander Grand (CC-BY) | 3 INTEGRATE |
| **SFZ player** | Plogue sforzando (free, VST3, April 2026) | 1 INTEGRATE |
| **AbletonOSC** | Still the only OSC bridge for Ableton Live. Maintained but slow. | INTEGRATE |
| **FL Studio programmatic** | Music2DAW (.NET, 2026) can create/edit FLP. No longer dead end but severely limited. | EVALUATE — not a viable production pipeline target |
