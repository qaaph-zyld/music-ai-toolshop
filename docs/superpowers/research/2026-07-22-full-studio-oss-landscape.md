# Music Generation & Synthesis Tooling — Research Report

## WS1: Composition & MIDI Engine

### Music Generation (AI/ML)
- **Magenta (original)** — Archived, inactive. TensorFlow-based. Individual repos now under Magenta GitHub org.
- **Magenta RealTime 2** — SOTA real-time music generation. `magenta-rt` Python lib (JAX/MLX backends). PyTorch fork (`multimodalart/magenta-realtime-torch`) makes it `transformers`-compatible. Real-time streaming requires Apple Silicon; offline works on Apple Silicon or NVIDIA GPU. **No CPU-only path for real-time.**
- **MusicLang** — Python framework for symbolic music writing/analysis/transformation/prediction. LLM-based prediction via `musiclang_predict`. Chord progression control, generation from existing music. **Fast inference on CPU.** Actively maintained.

### Chord Progression Generation
- **`ayk-caglayan/harmonic-space`** — Generates/ranks chord progressions from pitch classes, matches against When-in-Rome corpus. Exports text/JSON/MusicXML.
- **`ColdVale/chordgen`** — Transformer-based chord progression model, API available.
- **`hlm628/chord-striker`** — Random harmonic song structures with musical coherence. PDF chord charts (Lilypond) + MIDI export.
- **`Feli021/Music-Idea-Genarator`** — CLI tool for moods/themes/chord progressions/song structures.
- **MidiGen** — OOP MIDI generation with music theory support including chord progressions.

### Drum Pattern Generation
- **`james-see/beatstoch`** — BPM-aware stochastic drum MIDI generator. Multiple styles, time signatures, humanization. MIDI export.
- **`fsecada01/midi-drums`** — 4 genres, 28 styles, 7 drummer personalities. EZDrummer-compatible output. AI-powered NL pattern generation.
- **`scribbletune/pydrums`** — AI-powered drum pattern generation via Ollama (few-shot learning). Text descriptions → MIDI.
- **`david-a-campbell/W1_Hit`** — TCN for expressive single-voice MIDI drum patterns. Ableton Live integration.

### MIDI Humanization & Quantization
- **`shakfu/aldakit`** — Alda parser/MIDI generator. Transformers: quantize, humanize, swing, stretch, accent, crescendo, normalize.
- **`shakfu/coremusic`** — Python bindings for Apple CoreAudio/CoreMIDI. Pipeline: transpose, quantize, humanize. **macOS only.**
- **`JakebGutierrez/wobblemidi`** — Humanizes drum MIDI with timing/velocity distributions learned from real drummers (Groove MIDI Dataset). Per-instrument, per-grid-position deviation sampling.
- **`erwald/midihum`** — ML-based MIDI humanization (gradient boosted trees for velocity adjustment).

---

## WS2: Synthesis & Instrument Palette

### VST Hosting & Offline Rendering
- **DawDreamer** — JUCE-based audio processing framework with Python interface via `nanobind`. Supports VST instruments/effects, parameter automation, FAUST, JAX, Warp Markers. Offline rendering. VST3/VST2/AU compatibility varies by OS. **Actively maintained, 2025 releases.**
- **Pedalboard (Spotify)** — Python library for audio effects. VST3 + Audio Unit hosting on macOS/Windows/Linux. Built-in effects (Compressor, Reverb, Delay, Chorus, Distortion, etc.). MIDI input to VST instruments. Live audio streaming via `AudioStream`. **Very actively maintained (v0.9.24, July 2026).** GPL-3.0. Tested with Python 3.10–3.14. Releases GIL for multi-core. **No CLAP support.**
- **Carla** — Fully-featured plugin host (LADSPA, DSSI, LV2, VST2, VST3, AU). SF2/3 + SFZ support. OSC remote control. Rack/Patchbay modes. Windows builds available (v2.5.10). Python bindings via `carla_backend`. MCP server exists (`bivex/carla-mcp-server`) for LLM-driven control. **GPL-2.0+.**

### Synthesizers (Headless-Capable)
- **Surge XT** — Free open-source hybrid synth. Python bindings (`surgepy`) for direct native access, headless operation. **Actively maintained, 2026 updates.**
- **Vital** — Spectral warping wavetable synth. GPLv3 source. Updated on delay after binary releases. Non-GPLv3 licensing available on request.
- **FluidSynth (`pyfluidsynth`)** — SoundFont-based software synthesizer. Can play audio or return chunks for custom output. All major platforms. **Actively maintained, 2026 releases.**
- **sfizz / pysfizz** — SFZ format sample-based synthesizer. Python bindings with prebuilt wheels for Python 3.9–3.14 on Linux/macOS/Windows. Offline note rendering: `synth.render_note(pitch, vel, note_dur, render_dur)`. **BSD-2-Clause.** Note: sfizz repo is now **archived** (last release 1.2.3, Jan 2024), but pysfizz wheels remain functional.

### Pitch Correction
- **x42 Auto Tune** — LV2 plugin, based on zita-at1. Scale-based or MIDI-controlled pitch correction. **Linux/LV2 only.**
- **GVST GSnap** — Free VST autotune effect. Fixed scale + MIDI-controlled correction. Subtle to extreme robot voice.
- **QPitch (`Skynse/qpitch`)** — JUCE-based, VST3 + CLAP builds. Formant preservation.
- **OpenTune (`bemtorres/opentune`)** — Zero-latency pitch correction, JUCE. Real-time granular synthesis pitch shifting, intelligent scale snapping.

---

## WS3: Mixing Toolchain

### Source Separation
- **Demucs v4** — Hybrid Transformer source separation. 4-stem (drums/bass/other/vocals) + 6-stem (+guitar/piano). CPU mode: ~1.5x track duration. GPU: 3GB min VRAM. **v4.1.0 released July 2026** — pyproject.toml overhaul, Python 3.10+, torch 2.1+. MIT license. Windows support documented.
- **BS-Roformer** — Band-Split RoFormer for source separation. `bs-roformer-infer` package (openmirlab) actively maintained — v0.1.5 (July 2026) re-hosted all 9 dead-URL checkpoints. Weights available via HuggingFace (safetensors format via AEmotionStudio). GPL-3.0.

### Audio Effects (Python-Native)
- **Pedalboard** (see WS2) — Also serves as mixing toolchain: Compressor, Limiter, EQ filters, Reverb, Convolution, PitchShift, Bitcrush, MP3Compressor. 300x faster than pySoX for single transforms.

### LSP Plugins
- **LSP (Linux Studio Plugins)** — CLAP, LADSPA, LV2, VST2/LinuxVST, VST3 formats. **Actively developed, 2026 releases.** Moving toward Windows support but **not planning free Windows distribution** — paid Windows builds planned.

---

## WS4: Vocal Production Chain

### Voice Conversion
- **RVC (Retrieval-based Voice Conversion)** — MIT license. 35K+ stars. Training requires NVIDIA GPU (4GB+ VRAM). **CPU inference works** (10–20x slower, acceptable for batch). Real-time: 90ms latency with GPU. Last update: June 2024 (original project no longer maintained).
- **Applio (`IAHispano/Applio`)** — MIT license, actively maintained RVC fork. VITS-based voice conversion. Built-in autotune, split audio processing.
- **GPT-SoVITS** — MIT license, 60K+ stars. Zero-shot TTS (5s sample) + few-shot (1min data). Cross-lingual. **CPU-optimized inference version exists** (`baicai-1145/GPT-SoVITS-CPUFast`). RTF 0.526 on M4 CPU. Last push: July 2026. **Actively maintained.**
- **so-vits-svc-fork** — 206 releases, v4.2.30 (Feb 2026). Real-time voice conversion. `pip install` ready. GPU 4GB+ VRAM, **CPU inference "fast enough"** per docs. BSD-3-Clause (original archived), fork actively maintained.

### De-essing
- **Nebula De-Esser** — Rust + nih-plug. VST3. Specialist transparent de-esser, 64-bit double-precision DSP. Windows x86_64 + ARM64. AGPLv3. MIDI sidechain trigger. **Actively maintained (v3.3.0).**
- **Morass** — Complete vocal channel strip (JUCE 8). AU/AUv3/VST3. 143 presets. Full chain: gate → hiss-killer → HPF → mic modeling → EQ → compressor → de-esser → air → saturation → doubler → reverb. Mid/Side processing. GPLv3. macOS/Windows/Linux. **New (July 2026).**
- **Seraph** — Choir/vocal processor (JUCE 8). De-ess, air, compressor, 4-voice doubler. AU/VST3. AGPLv3. Pre-1.0, active development.

### De-breathing
- **DeBreather for Audacity** — Nyquist plugins (Detect + Reduce). Spectral detection of breath sounds, configurable gain reduction (-20dB default). Audacity 3.2+. GPL v2. **New (April 2026).**
- **`@audio/denoise-debreath`** — JavaScript/npm. VAD-driven inverse gate. Energy + spectral flatness detection. For web-based audio processing.

### Pitch Correction (see WS2 above for full list)

---

## WS5: Rhythm & Groove Tools

### Drum Machines & Samplers
- **Hydrogen** — Advanced drum machine for Linux/macOS/Windows. C++. GPL-2.0. v1.2.6 (July 2025). MIDI support, OSC API for automation, pattern-based programming + drum synth. **No Python bindings** (declined Python binding proposal #1313 — no stable API). Lua scripting via `lua4hydrogen` (midi_to_h2song, sf2_to_drumkit). Qt6 support added. **Actively maintained, last push June 2026.**
- **DrumGizmo** — Open-source multi-channel drum sampler. VSTi for Windows (tested with Cubase/Reaper). LV2. XML-based kit/instrument/midimap formats. Multi-channel with bleed control. **Last release: v0.9.20.** Development appears slow — last git activity ~2021. Rust port (`rustick`) exists but **Linux-only.**

### Drum Pattern Generation (see WS1 above)

---

## WS6: Local Generation Landscape (GPU Shelf)

### Full-Song Generation Models

| Model | Architecture | Min VRAM | CPU Feasible | License | Last Active | Windows |
|-------|-------------|----------|-------------|---------|-------------|---------|
| **ACE-Step v1.5** | Hybrid LM + DiT | **<4GB** (offloaded) | No (GPU required) | MIT | June 2026 | Yes (triton-windows) |
| **DiffRhythm v1.2** | Diffusion | 8GB (chunked) | No | Apache 2.0 | May 2025 | Yes |
| **YuE** | LLM-based | 8GB (quantized) / 24GB (full) | No | Apache 2.0 | March 2025 | Yes (Pinokio/Docker) |
| **MusicGen** | Autoregressive Transformer | 5GB (small) / 16GB (medium) | **Yes** (2-3 min/track) | MIT | 2024+ | Yes |
| **Stable Audio Open Small** | Diffusion | ~4GB | **Yes** (Arm CPU optimized) | OpenRAIL++ | 2025 | Yes |

**Key findings:**
- **ACE-Step v1.5** is the current SOTA for local generation — commercial-grade quality, <4GB VRAM, 50+ language lyrics, LoRA training from 8 songs. 11.5K stars. Turbo checkpoints distill to 4-8 steps. Available in HuggingFace diffusers.
- **YuE** requires significant VRAM (24GB+ for practical use, 80GB for full songs). `YuEGP` fork extends to 12GB profiles. No CPU path. Apache 2.0.
- **MusicGen** is the only model with a practical **CPU inference path** — 2-3 minutes per 30s track on CPU. Small model (300M) works on minimal hardware. Available via `transformers` library.
- **Stable Audio Open Small** has Arm CPU optimization path via LiteRT. `aria` project (C inference engine) runs Stable Audio 3 on CPU natively (no Python/DL framework).
- **audio.cpp** — Pure C++ ggml-based inference engine for audio models. Supports Stable Audio, TTS, ASR, VAD, voice conversion, music generation. CUDA + CPU backends. Windows build scripts provided. **Active (July 2026).**

### Audio-to-MIDI Transcription
- **Basic Pitch (Spotify)** — Lightweight AMT, <20MB peak memory, <17K parameters. Polyphonic, instrument-agnostic, pitch bend detection. ONNX on Windows by default (no TensorFlow needed). Apache 2.0. **v0.4.0 (Aug 2024), last push Nov 2025.** CLI + Python API.

---

## WS7: Fleet Orchestration

### File Sync / Transfer
- **Syncthing** — P2P continuous bidirectional sync. No cloud middleman. NAT traversal. Cross-platform. Best for: real-time sync between live workstations. 1-5s propagation latency. Higher idle resource usage (1-5% CPU, 50-200MB RAM).
- **rclone** — Batch, on-demand sync. 70+ cloud provider backends. Built-in encryption (`crypt:`). Windows native. Zero resources when idle. Best for: scheduled backups, cloud-to-cloud migration. `--inplace` for large file updates.
- **Recommendation:** Use **both** — Syncthing for real-time inter-workstation sync, rclone for nightly cloud/offsite backups.

### OSC (Open Sound Control)
- **python-osc** — Pure Python OSC server/client. UDP + TCP, asyncio support. **v1.10.2 (April 2026)** — actively maintained. No external dependencies. Best choice for new projects.
- **osc4py3** — Last release 2018. Production/stable status but unmaintained. More complex scheduling models. CeCILL-2.1 license. **Not recommended for new projects.**

---

## WS8: Hardware Unlock Map

### CPU-Only Feasibility Summary

| Task | CPU Feasible? | Best Tool | Notes |
|------|--------------|-----------|-------|
| Symbolic music generation | **Yes** | MusicLang | Fast CPU inference |
| Audio-to-MIDI transcription | **Yes** | Basic Pitch | <20MB, ONNX on Windows |
| Source separation | **Yes** (slow) | Demucs v4 | ~1.5x track duration |
| VST hosting/rendering | **Yes** | Pedalboard, DawDreamer | Native processing |
| SoundFont synthesis | **Yes** | FluidSynth, sfizz | Designed for CPU |
| Music generation (neural) | **Marginal** | MusicGen (small) | 2-3 min/30s track |
| Voice conversion (inference) | **Yes** (batch) | RVC, so-vits-svc-fork | 10-20x slower than GPU |
| TTS + voice cloning | **Yes** | GPT-SoVITS-CPUFast | RTF 0.526 on M4 |
| Full-song generation (SOTA) | **No** | ACE-Step, YuE | GPU required |
| Stable Audio | **Yes** (Arm) | aria, Stable Audio Open Small | C engine, no Python |

### GPU Requirements Summary

| Model/Tool | Min VRAM (GPU) | Recommended |
|-----------|---------------|-------------|
| ACE-Step v1.5 | 4GB (offloaded) | 8GB+ |
| DiffRhythm | 8GB (chunked) | 12GB+ |
| YuE (quantized) | 8-12GB | 24GB+ |
| MusicGen small | 5GB | 8GB |
| Demucs v4 | 3GB | 7GB |
| RVC inference | 4GB | 8GB |
| RVC training | 4GB | 8GB+ |
| BS-Roformer | 4GB | 8GB |

---

## WS9: DAW Integration Refresh

### Ableton Live
- **`ableton-set-builder`** — Build Ableton sets programmatically via Python. Parse compressed/uncompressed `.als`. Create audio tracks, add scenes, build ALS. **PyPI, May 2025.**
- **`Beennnn/als-wire`** — Wire plugin parameters to rack macros and MIDI mappings directly in `.als` files. Batch, scriptable, no GUI. Python 3 stdlib only. Tested with Live 12.4.
- **`mattypie/ableton-project-processor`** — Batch clean tracks, ungroup, strip unused devices, sort/recolor, quantize/transpose MIDI, generate reports. XML-level, no Live needed. Live 12 & 11. **New (April 2026).**
- **`maranedah/pyableton`** — Parse `.als` files, extract track/clip data, export to MIDI.
- **`madisonrickert/ableton-tools`** — Claude Code toolkit: stem verification, tempo/drift analysis, MIDI transcription/comparison, safe `.als` editing. Dry-run by default, backup on commit.

### REAPER
- **reapy-next** (`wiccy46/reapy-next`) — Continuation of `RomeoDespres/reapy` (original unmaintained since 2020). Pythonic wrapper for ReaScript API. **v0.10.1 (April 2025).** MIT. Tested on REAPER v7.36. **macOS guide only** — Windows/Linux not documented but should work. External API calls limited to 30-60/s via defer loop; use `reapy.inside_reaper` context manager for performance.

### Open-Source DAWs
- **Zrythm** — C++23, Qt6/QML, JUCE. VST3/CLAP/LV2/LADSPA/AU. **v2.0.0-alpha.1 (May 2026)** — complete rewrite. Guile scripting interface for project generation. Cross-platform (Linux/macOS/Windows with ASIO). Many v1 features not yet ported. **Alpha — not production-ready.**
- **LMMS** — Cross-platform music production. C++. New plugin API in development (CLAP + VST3 support planned). Qt6 support nearing completion. **Actively maintained** (July 2025 progress report, 13 PRs merged). No Python scripting interface.

---

## WS10: Adapt-vs-Mine Audit

### Tools to Adapt (fork/wrap existing)

| Tool | Why Adapt | Effort |
|------|----------|--------|
| MusicLang | CPU inference, chord control, symbolic music | Low — Python, pip-installable |
| Pedalboard | VST3 hosting, built-in effects, Spotify-backed | Low — just use directly |
| Demucs v4 | Source separation, CPU fallback | Low — pip-installable |
| Basic Pitch | Audio-to-MIDI, ONNX on Windows | Low — pip-installable |
| FluidSynth/pyfluidsynth | SoundFont synthesis, all platforms | Low — pip-installable |
| pysfizz | SFZ playback, offline rendering | Low — prebuilt wheels |
| Surge XT (surgepy) | Headless synth with Python bindings | Low — use bindings directly |
| python-osc | OSC protocol for hardware control | Low — pure Python, no deps |
| ableton-set-builder | Programmatic ALS generation | Low — PyPI package |
| reapy-next | REAPER scripting | Medium — macOS docs only |
| beatstoch / midi-drums | Drum pattern generation | Medium — adapt for project needs |
| wobblemidi | MIDI humanization from real drummer data | Medium — integrate as pipeline stage |

### Tools to Mine (extract algorithms/patterns)

| Tool | What to Extract | Effort |
|------|----------------|--------|
| midihum | ML-based velocity humanization (GBT) | Medium — extract model/pipeline |
| harmonic-space | Chord progression ranking logic | Medium — extract ranking algorithm |
| Nebula De-Esser | Spectral de-essing DSP | High — Rust/nih-plug, would need port |
| Morass | Full vocal chain DSP | High — JUCE C++, would need port |
| aria (Stable Audio C engine) | CPU-first inference approach | High — C, but architecture insights valuable |

### Tools to Build from Scratch

| Component | Why Build | Dependencies |
|-----------|----------|-------------|
| Fleet orchestrator | No existing tool combines sync + generation + rendering | rclone, Syncthing, python-osc |
| Pipeline glue | Connect composition → synthesis → mixing → export | Pedalboard, DawDreamer, FluidSynth |

---

## WS11: Decided-Stack Delta Check

### Confirmed Available & Compatible (Windows + CPU where needed)

- **Composition:** MusicLang (CPU) ✅
- **MIDI humanization:** wobblemidi (CPU) ✅, aldakit (CPU) ✅
- **Drum generation:** beatstoch (CPU) ✅, midi-drums (CPU) ✅
- **Synthesis (headless):** FluidSynth (CPU) ✅, pysfizz (CPU) ✅, Surge XT/surgepy (CPU) ✅
- **VST hosting:** Pedalboard (VST3, Windows) ✅, DawDreamer (VST3, Windows) ✅
- **Source separation:** Demucs v4 (CPU, Windows) ✅, BS-Roformer (CPU, Windows) ✅
- **Audio-to-MIDI:** Basic Pitch (ONNX, Windows) ✅
- **Pitch correction:** OpenTune, QPitch (VST3) ✅
- **De-essing:** Nebula De-Esser (VST3, Windows) ✅
- **Voice conversion:** RVC/Applio (CPU inference) ✅, GPT-SoVITS (CPU) ✅
- **DAW integration:** ableton-set-builder ✅, reapy-next ✅
- **OSC:** python-osc ✅
- **File sync:** rclone ✅, Syncthing ✅

### Gaps & Risks

- **LSP Plugins** — Windows builds will be **paid**, not free. Consider Pedalboard built-in effects as alternative for mixing.
- **sfizz** — Repo archived (Jan 2024). pysfizz wheels still work but no future updates. Consider FluidSynth as primary SFZ/SF2 player.
- **ACE-Step v1.5** — Best local generation model but **no CPU path**. Requires GPU with ≥4GB VRAM. If target hardware is CPU-only, fall back to MusicGen small or Stable Audio Open Small (via aria).
- **Hydrogen** — No Python bindings (explicitly declined). OSC API available for automation, but programmatic drum generation requires external MIDI generation + Hydrogen playback.
- **Zrythm v2** — Alpha, not production-ready. Many v1 features missing. Do not depend on for production workflows.
- **reapy-next** — Documentation is macOS-only. Windows functionality unverified but should work via ReaScript API.
- **Pedalboard VST3 on Windows** — Known bug where VST3 effect plugins render dry audio (PR #476, open as of April 2026). Test before relying on specific VST3 effects.
