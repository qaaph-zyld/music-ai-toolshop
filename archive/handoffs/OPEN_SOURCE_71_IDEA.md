# Building an open-source DAW: 71 components for every stage of production

**A fully open-source Digital Audio Workstation is now buildable from modular parts.** This catalog identifies 71 distinct open-source projects spanning all 17 categories of the audio production pipeline — from low-level audio I/O and DSP cores through AI-assisted composition, stem separation, and final audio/video export. The majority carry permissive licenses (MIT, BSD, Apache 2.0, ISC), with GPL-licensed projects included only where they represent irreplaceable industry standards. Every project listed offers C/C++, Rust, Python, or JavaScript/TypeScript integration paths suitable for a modular architecture.

---

## The audio engine layer: 4 foundations to build on

The DSP core determines everything about a DAW's real-time performance. **miniaudio** (https://github.com/mackron/miniaudio) stands out as the most integration-friendly option — a single-file, zero-dependency C library providing device I/O, mixing, and a built-in node graph for effects processing across every major platform and audio backend (WASAPI, CoreAudio, ALSA, JACK, PulseAudio, Web Audio). Licensed under **Public Domain/MIT-0**, it eliminates legal friction entirely.

For DSP algorithm development, **FAUST** (https://github.com/grame-cncm/faust) is the industry-standard functional DSP language. Its compiler translates signal processing specifications into optimized C++, LLVM IR, WebAssembly, or Rust — generating standalone apps or plugins for VST/AU/LV2/CLAP from a single source. The compiler is **GPL-2.0** but the runtime libraries and generated code use **LGPL-2.1+**, making it practical for DAW integration.

Two additional DSP libraries fill complementary roles. **Cycfi Q** (https://github.com/cycfi/q) provides a modern C++ DSP toolkit with advanced pitch detection, filters, dynamics processors, and envelope followers under **MIT** license — its core has zero dependencies. **Maximilian** (https://github.com/micknoise/Maximilian) offers a self-contained synthesis and signal processing library with oscillators, granular synthesis, FFT, and JavaScript/WebAssembly bindings, also under **MIT**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 1 | miniaudio | github.com/mackron/miniaudio | Public Domain/MIT-0 | C |
| 2 | FAUST | github.com/grame-cncm/faust | GPL-2.0 / LGPL-2.1+ | C++/Faust |
| 3 | Cycfi Q | github.com/cycfi/q | MIT | C++ |
| 4 | Maximilian | github.com/micknoise/Maximilian | MIT | C++ |

---

## Plugin hosting: the CLAP-LV2-DPF triad

A DAW lives or dies by its plugin ecosystem. Three projects form the essential plugin hosting stack. **CLAP** (https://github.com/free-audio/clap), the CLever Audio Plugin API created by u-he and Bitwig, defines a modern **MIT-licensed** C ABI with features no legacy format offers: per-note modulation, polyphonic parameter automation, and collaborative multi-core threading. The companion `clap-wrapper` project enables wrapping CLAP plugins as VST3/AU.

**LV2** (https://github.com/lv2/lv2) provides the open plugin specification that dominates the Linux audio ecosystem. Its extensible architecture supports audio, MIDI, atom messaging, and worker threads. The companion library **Lilv** (https://github.com/lv2/lilv) handles all LV2 plugin discovery, metadata querying, and instance management — both are licensed under the permissive **ISC** license.

**DPF** (https://github.com/DISTRHO/DPF), the DISTRHO Plugin Framework, bridges all major formats from a single C++ codebase: LADSPA, DSSI, LV2, VST2, VST3, and CLAP. Its companion **DPF-Plugins** (https://github.com/DISTRHO/DPF-Plugins) provides a ready-made collection of effects and instruments. DPF uses the **ISC** license.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 5 | CLAP SDK | github.com/free-audio/clap | MIT | C |
| 6 | LV2 | github.com/lv2/lv2 | ISC | C |
| 7 | Lilv | github.com/lv2/lilv | ISC | C |
| 8 | DPF | github.com/DISTRHO/DPF | ISC | C++ |
| 9 | DPF-Plugins | github.com/DISTRHO/DPF-Plugins | Various (ISC/MIT/GPL) | C++ |

---

## Recording, I/O, and file formats: 8 essential libraries

Cross-platform audio I/O requires choosing between two mature options. **PortAudio** (https://github.com/PortAudio/portaudio) provides a C API supporting every major backend — ASIO, WASAPI, CoreAudio, ALSA, JACK, PulseAudio — and powers Audacity. **RtAudio** (https://github.com/thestk/rtaudio) offers the same breadth in a cleaner C++ object-oriented design. Both are **MIT-licensed**.

On Linux, two sound servers matter. **JACK2** (https://github.com/jackaudio/jack2) remains the professional standard for low-latency inter-application routing (client library is **LGPL-2.1**). **PipeWire** (https://gitlab.freedesktop.org/pipewire/pipewire) is the modern replacement, now default on Fedora and Ubuntu, providing ABI-compatible JACK and PulseAudio layers under a mostly **MIT** license.

For file I/O, **libsndfile** (https://github.com/libsndfile/libsndfile) is the industry-standard unified API for WAV, AIFF, FLAC, Ogg/Vorbis, Opus, and MP3 under **LGPL-2.1+**. The lightweight alternative **dr_libs** (https://github.com/mackron/dr_libs) provides single-header decoders for WAV, FLAC, and MP3 under **Public Domain**. **FFmpeg** (https://github.com/FFmpeg/FFmpeg) handles virtually every other audio and video format via libavcodec/libavformat (**LGPL-2.1+** default). **Opus** (https://github.com/xiph/opus), the **BSD-3-Clause** IETF codec, enables high-quality compressed streaming and export.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 10 | PortAudio | github.com/PortAudio/portaudio | MIT | C |
| 11 | RtAudio | github.com/thestk/rtaudio | MIT-like | C++ |
| 12 | JACK2 | github.com/jackaudio/jack2 | GPL-2.0 / LGPL-2.1 | C++ |
| 13 | PipeWire | gitlab.freedesktop.org/pipewire/pipewire | MIT | C |
| 14 | libsndfile | github.com/libsndfile/libsndfile | LGPL-2.1+ | C |
| 15 | dr_libs | github.com/mackron/dr_libs | Public Domain/MIT-0 | C |
| 16 | FFmpeg | github.com/FFmpeg/FFmpeg | LGPL-2.1+ | C |
| 17 | Opus | github.com/xiph/opus | BSD-3-Clause | C |

---

## MIDI sequencing and piano roll: from I/O to UI

MIDI connectivity requires a platform abstraction layer. **libremidi** (https://github.com/celtera/libremidi) is the modern choice — a C++20 library supporting MIDI 1.0 and 2.0 with hotplug detection, zero-allocation modes, and all major backends, licensed under **BSD-2-Clause**. The venerable **RtMidi** (https://github.com/thestk/rtmidi) provides the same cross-platform MIDI I/O in simpler C++ under a **MIT-like** license, while **midifile** (https://github.com/craigsapp/midifile) handles Standard MIDI File parsing and writing (**BSD-2-Clause**).

For the visual piano roll editor, **webaudio-pianoroll** (https://github.com/g200kg/webaudio-pianoroll) provides a ready-made Web Component with grid/drag editing modes, zoom, and Web Audio API integration under **Apache-2.0** — ideal for browser-based or Electron DAW frontends.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 18 | libremidi | github.com/celtera/libremidi | BSD-2-Clause | C++ |
| 19 | RtMidi | github.com/thestk/rtmidi | MIT-like | C++ |
| 20 | midifile | github.com/craigsapp/midifile | BSD-2-Clause | C++ |
| 21 | webaudio-pianoroll | github.com/g200kg/webaudio-pianoroll | Apache-2.0 | JavaScript |

---

## AI-assisted composition: 5 generative engines

**AudioCraft** (https://github.com/facebookresearch/audiocraft) from Meta is the most capable open-source music generation framework, containing MusicGen (text-to-music), AudioGen (text-to-sound effects), and EnCodec (neural audio codec). MusicGen generates high-quality music from text prompts or melody conditioning using a single-stage Transformer. Code is **MIT**; model weights are CC-BY-NC 4.0.

**Magenta** (https://github.com/magenta/magenta) from Google offers a broader toolkit including MelodyRNN, MusicVAE, Music Transformer, and DDSP models under **Apache 2.0**, with Ableton Live integrations and browser-ready Magenta.js. **Stable Audio Tools** (https://github.com/Stability-AI/stable-audio-tools) from Stability AI uses latent diffusion transformers for variable-length stereo generation at 44.1kHz (code **MIT**). **Riffusion** (https://github.com/riffusion/riffusion-hobby) takes an innovative approach, applying stable diffusion to spectrograms for real-time music generation (**MIT**). **DDSP** (https://github.com/magenta/ddsp) combines differentiable DSP with deep learning for timbre transfer and neural synthesis under **Apache 2.0**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 22 | AudioCraft/MusicGen | github.com/facebookresearch/audiocraft | MIT (code) | Python |
| 23 | Magenta | github.com/magenta/magenta | Apache 2.0 | Python |
| 24 | Stable Audio Tools | github.com/Stability-AI/stable-audio-tools | MIT (code) | Python |
| 25 | Riffusion | github.com/riffusion/riffusion-hobby | MIT | Python |
| 26 | DDSP | github.com/magenta/ddsp | Apache 2.0 | Python |

---

## Lyrics, rhyme engines, and songwriting AI

For lyric writing assistance, four Python libraries cover the spectrum from dictionary lookups to neural generation. **Pronouncing** (https://github.com/aparrish/pronouncingpy) wraps the CMU Pronouncing Dictionary with functions for rhyme finding, syllable counting, and phonetic pattern search — zero dependencies, **BSD** licensed. **Phyme** (https://github.com/emo-eth/Phyme) extends this with advanced songwriting-specific rhyme types: perfect, family, partner, assonance, and consonance rhymes under **MIT**.

For AI-powered generation, **HuggingArtists** (https://github.com/AlekseyKorshuk/huggingartists) fine-tunes GPT-2 for artist-specific lyrics generation (**MIT**), while **Xandly5** (https://github.com/dreoporto/xandly5) uses bidirectional LSTMs trained on public-domain works to generate structured songs with configurable verse/chorus/bridge sections (**MIT**). Serbian language support can be achieved by fine-tuning these models on Serbian lyric datasets or integrating multilingual transformer models from Hugging Face.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 27 | Pronouncing | github.com/aparrish/pronouncingpy | BSD | Python |
| 28 | Phyme | github.com/emo-eth/Phyme | MIT | Python |
| 29 | HuggingArtists | github.com/AlekseyKorshuk/huggingartists | MIT | Python |
| 30 | Xandly5 | github.com/dreoporto/xandly5 | MIT | Python |

---

## Stem separation: three models, one workflow

**Demucs** (https://github.com/facebookresearch/demucs) from Meta represents the state of the art. The v4 Hybrid Transformer architecture achieves **9.0+ dB SDR** on MUSDB HQ, separating drums, bass, vocals, and other stems (the 6-stem variant adds piano and guitar). Licensed under **MIT**.

**Spleeter** (https://github.com/deezer/spleeter) from Deezer provides the fastest option — **100x faster than real-time** on GPU — with U-Net models for 2, 4, or 5 stem separation. It has been integrated into commercial tools like iZotope RX, confirming production quality. Also **MIT** licensed.

**Open-Unmix** (https://github.com/sigsep/open-unmix-pytorch) takes a simpler, more extensible approach with bidirectional LSTM and Wiener filtering, designed for research reproducibility. Multiple pre-trained models (umx, umxhq, umxl) are available under **MIT**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 31 | Demucs | github.com/facebookresearch/demucs | MIT | Python |
| 32 | Spleeter | github.com/deezer/spleeter | MIT | Python |
| 33 | Open-Unmix | github.com/sigsep/open-unmix-pytorch | MIT | Python |

---

## Audio effects: from single-header reverbs to 300+ plugin collections

**Airwindows** (https://github.com/airwindows/airwindows) is a treasure trove — **over 300 open-source audio plugins** by Chris Johnson covering reverb, delay, EQ, compression, saturation, and dozens of esoteric effects. Each is a standalone C++ class. The consolidated `airwin2rack` library (https://github.com/baconpaul/airwin2rack) provides a uniform API for DAW integration. Core code is **MIT**.

For lightweight embedded effects, three single-header libraries stand out. **sndfilter** (https://github.com/velipso/sndfilter) implements Freeverb-based reverb, Chromium-derived compression, and biquad filters in clean C under the **0BSD** (public domain equivalent) license. **verblib** (https://github.com/blastbay/verblib) provides Jezar's Freeverb algorithm as a single C header under **Public Domain**. **MVerb** (https://github.com/martineastwood/mverb) implements Dattorro's studio-quality figure-of-eight reverb in a single C++ header under **BSD**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 34 | Airwindows | github.com/airwindows/airwindows | MIT | C++ |
| 35 | sndfilter | github.com/velipso/sndfilter | 0BSD | C |
| 36 | verblib | github.com/blastbay/verblib | Public Domain | C |
| 37 | MVerb | github.com/martineastwood/mverb | BSD | C++ |

---

## Mixing and mastering: loudness, limiting, and automated matching

Loudness measurement is non-negotiable for modern mastering. **libebur128** (https://github.com/jiixyj/libebur128) implements the EBU R 128 standard in pure C with zero dependencies — providing momentary, short-term, and integrated loudness plus loudness range under **MIT**. A Rust port exists at github.com/sdroege/ebur128. **pyloudnorm** (https://github.com/csteinmetz1/pyloudnorm) adds ITU-R BS.1770-4 measurement with NumPy integration for Python-based pipelines, also **MIT**.

For dynamics, **SimpleCompressor** (https://github.com/DanielRudrich/SimpleCompressor) provides educational-yet-practical C++ look-ahead compressor/limiter classes, and **cylimiter** (https://github.com/pzelasko/cylimiter) offers a C++/Cython streaming limiter with configurable parameters under **Apache-2.0**.

**Matchering** (https://github.com/sergree/matchering) automates reference-track mastering — analyzing a reference track's RMS, frequency response, peak amplitude, and stereo width, then applying those characteristics to a target. Available as a Python library and Docker web app under **GPL-3.0**. **master_me** (https://github.com/trummerschlunk/master_me) provides a zero-latency automatic mastering plugin chain (leveler, multiband dynamics, EQ, limiter) as VST3/LV2/CLAP/AU under **GPL-3.0**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 38 | libebur128 | github.com/jiixyj/libebur128 | MIT | C |
| 39 | pyloudnorm | github.com/csteinmetz1/pyloudnorm | MIT | Python |
| 40 | SimpleCompressor | github.com/DanielRudrich/SimpleCompressor | GPL-3.0 | C++ |
| 41 | cylimiter | github.com/pzelasko/cylimiter | Apache-2.0 | C++/Python |
| 42 | Matchering | github.com/sergree/matchering | GPL-3.0 | Python |
| 43 | master_me | github.com/trummerschlunk/master_me | GPL-3.0 | Faust/C++ |

---

## Vocal processing: pitch correction, time-stretching, and vocoders

**Rubber Band Library** (https://github.com/breakfastquay/rubberband) is the industry standard for time-stretching and pitch-shifting. Its v3+ R3 engine and v4+ live-shifter API provide both offline and lock-free real-time modes with C/C++ APIs and LADSPA/LV2 plugins. Licensed **GPL-2.0+** with commercial licensing available.

**Autotalent** (https://github.com/michaeldonovan/AutoTalent) is the original open-source auto-tune — real-time pitch correction with key/scale constraints, formant warping, and vibrato control as LADSPA/VST/AU under **GPL-2.0**. An LV2 port exists as TalentedHack (https://github.com/jeremysalwen/TalentedHack).

For pitch detection, **aubio** (https://github.com/aubio/aubio) provides multiple algorithms (YIN, spectral, harmonic comb) optimized for real-time use with Python bindings (**GPL-3.0**). **CREPE** (https://github.com/marl/crepe) uses deep CNNs for state-of-the-art monophonic pitch tracking that outperforms traditional methods (**MIT**).

**WORLD Vocoder** (https://github.com/mmorise/World) decomposes speech into F0, spectral envelope, and aperiodicity for independent pitch/formant/time manipulation under **Modified BSD**, with Python bindings via PyWorld. **stftPitchShift** (https://github.com/jurihock/stftPitchShift) adds real-time STFT-based pitch shifting with formant preservation via cepstral envelope extraction under **MIT**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 44 | Rubber Band | github.com/breakfastquay/rubberband | GPL-2.0+ | C++ |
| 45 | Autotalent | github.com/michaeldonovan/AutoTalent | GPL-2.0 | C/C++ |
| 46 | aubio | github.com/aubio/aubio | GPL-3.0 | C |
| 47 | CREPE | github.com/marl/crepe | MIT | Python |
| 48 | WORLD Vocoder | github.com/mmorise/World | Modified BSD | C++ |
| 49 | stftPitchShift | github.com/jurihock/stftPitchShift | MIT | C++/Python |

---

## AI-powered noise removal and intelligent mastering

**RNNoise** (https://github.com/xiph/rnnoise) from Xiph.org bakes a trained RNN directly into C code for **zero-dependency, real-time noise suppression** at 48kHz with minimal CPU usage — perfect for cleaning vocal recordings. Licensed **BSD-3-Clause**.

**DeepFilterNet** (https://github.com/Rikorose/DeepFilterNet) achieves state-of-the-art full-band noise suppression (PESQ 3.5–4.0+) with 10–20ms latency. Uniquely, it ships as a **LADSPA plugin** for direct DAW integration, plus Rust binaries and Python APIs. Dual-licensed **MIT/Apache 2.0**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 50 | RNNoise | github.com/xiph/rnnoise | BSD-3-Clause | C |
| 51 | DeepFilterNet | github.com/Rikorose/DeepFilterNet | MIT / Apache 2.0 | Rust/Python |

---

## Sample management, synthesis engines, and sound design

For sample playback, **sfizz** (https://github.com/sfztools/sfizz) provides a high-quality SFZ parser and synthesizer with C/C++ APIs under **BSD-2-Clause**. **FluidSynth** (https://github.com/FluidSynth/fluidsynth) handles SoundFont 2 playback with a comprehensive C API under **LGPL-2.1+**. **Shortcircuit XT** (https://github.com/surge-synthesizer/shortcircuit-xt), rebuilt by the Surge team, offers a creative sampler with 16 parts, multiple engines, and advanced modulation under **GPL-3.0**.

For synthesis, **Surge XT** (https://github.com/surge-synthesizer/surge) is a full-featured hybrid synthesizer with 12 oscillator algorithms, wavetable support, and Lua scripting under **GPL-3.0**. **STK** (https://github.com/thestk/stk), Stanford's Synthesis ToolKit, provides physical modeling, FM, and granular synthesis classes developed since 1996 under a **MIT-style** license. **libsamplerate** (https://github.com/libsndfile/libsamplerate) handles high-quality sample rate conversion with sinc-based algorithms under **BSD-2-Clause**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 52 | sfizz | github.com/sfztools/sfizz | BSD-2-Clause | C++ |
| 53 | FluidSynth | github.com/FluidSynth/fluidsynth | LGPL-2.1+ | C |
| 54 | Shortcircuit XT | github.com/surge-synthesizer/shortcircuit-xt | GPL-3.0 | C++ |
| 55 | Surge XT | github.com/surge-synthesizer/surge | GPL-3.0 | C++ |
| 56 | STK | github.com/thestk/stk | MIT-style | C++ |
| 57 | libsamplerate | github.com/libsndfile/libsamplerate | BSD-2-Clause | C |

---

## Notation and score editing: render any format

**VexFlow** (https://github.com/vexflow/vexflow) is the foundational TypeScript library for rendering standard notation and guitar tablature to Canvas/SVG, with an EasyScore API for quick notation creation (**MIT**). **OpenSheetMusicDisplay** (https://github.com/opensheetmusicdisplay/opensheetmusicdisplay) builds on VexFlow to parse and render MusicXML — the de facto interchange format — with automatic layout under **BSD-3-Clause**.

**abcjs** (https://github.com/paulrosen/abcjs) parses ABC notation into rendered sheet music with built-in synthesized playback and MIDI generation (**MIT**). For native desktop integration, **Lomse** (https://github.com/lenmus/lomse) provides a C++ library for rendering, editing, and playing back scores with MusicXML import/export and SMuFL-compliant fonts under **MIT**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 58 | VexFlow | github.com/vexflow/vexflow | MIT | TypeScript |
| 59 | OpenSheetMusicDisplay | github.com/opensheetmusicdisplay/opensheetmusicdisplay | BSD-3-Clause | TypeScript |
| 60 | abcjs | github.com/paulrosen/abcjs | MIT | JavaScript |
| 61 | Lomse | github.com/lenmus/lomse | MIT | C++ |

---

## Waveform visualization and spectrum analysis

**wavesurfer.js** (https://github.com/katspaugh/wavesurfer.js) is the go-to TypeScript library for interactive waveform rendering with plugins for regions, timeline, minimap, spectrogram, and recording — all under **BSD-3-Clause**. The BBC's **peaks.js** (https://github.com/bbc/peaks.js) provides Canvas-based zoomable overview + detail views with point/segment markers under **LGPL-3.0**, paired with **audiowaveform** (https://github.com/bbc/audiowaveform), a C++ tool that pre-computes waveform data from audio files for efficient loading (**GPL-3.0**).

**audioMotion-analyzer** (https://github.com/hvianna/audioMotion-analyzer) delivers a high-resolution real-time spectrum analyzer with logarithmic/linear/Bark/Mel frequency scales, **up to 240 bands**, and A/B/C/D/ITU-R 468 weighting filters. Note its **AGPL-3.0** license.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 62 | wavesurfer.js | github.com/katspaugh/wavesurfer.js | BSD-3-Clause | TypeScript |
| 63 | peaks.js | github.com/bbc/peaks.js | LGPL-3.0 | JavaScript |
| 64 | audiowaveform | github.com/bbc/audiowaveform | GPL-3.0 | C++ |
| 65 | audioMotion-analyzer | github.com/hvianna/audioMotion-analyzer | AGPL-3.0 | JavaScript |

---

## Audio/video remastering and media export

**FFmpeg** covers audio and video encoding/decoding/muxing comprehensively (listed above as #16). Three additional frameworks handle the video production pipeline. **GStreamer** (https://github.com/GStreamer/gstreamer) provides a pipeline-based multimedia framework with a plugin architecture for building complex real-time A/V processing chains, with Python bindings, under **LGPL-2.1+**. **MLT** (https://github.com/mltframework/mlt) is specifically designed for non-linear video editing — it powers Shotcut and Kdenlive — with FFmpeg, SDL, and LADSPA backend support under **LGPL-2.1**. **SoX** (https://sourceforge.net/projects/sox/) is the "Swiss Army knife" of audio processing for format conversion, sample rate conversion, channel mixing, and batch effects under **GPL-2.0+/LGPL**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 66 | GStreamer | github.com/GStreamer/gstreamer | LGPL-2.1+ | C |
| 67 | MLT Framework | github.com/mltframework/mlt | LGPL-2.1 | C |
| 68 | SoX | sourceforge.net/projects/sox/ | GPL-2.0+ / LGPL | C |

---

## Collaboration and version control for audio projects

Large binary audio files break standard Git workflows. **Git LFS** (https://github.com/git-lfs/git-lfs) solves this by replacing large files with lightweight pointers while storing actual content on remote servers — seamless integration with standard Git commands under **MIT**. **DVC** (https://github.com/iterative/dvc) extends this concept with any-backend storage (S3, Azure, GCS, NAS), pipeline tracking, and experiment management under **Apache-2.0**. For massive-scale audio libraries, **lakeFS** (https://github.com/treeverse/lakeFS) transforms object storage into Git-like repositories with zero-copy branching and S3-compatible APIs under **Apache-2.0**.

| # | Project | Repo | License | Language |
|---|---------|------|---------|----------|
| 69 | Git LFS | github.com/git-lfs/git-lfs | MIT | Go |
| 70 | DVC | github.com/iterative/dvc | Apache-2.0 | Python |
| 71 | lakeFS | github.com/treeverse/lakeFS | Apache-2.0 | Go |

---

## Conclusion: architectural strategy and licensing reality

This catalog of **71 projects** covers every stage of the production pipeline, but the integration strategy matters as much as the parts list. Three architectural insights emerge from this survey.

**The permissive core is achievable.** A DAW's kernel — audio I/O (miniaudio/PortAudio), DSP (Cycfi Q), plugin hosting (CLAP + LV2/Lilv), file I/O (dr_libs + libsndfile), MIDI (libremidi), and loudness metering (libebur128) — can be built entirely from MIT/BSD/ISC-licensed components. This keeps the core proprietary-compatible while loading GPL plugins (Surge, Airwindows, Autotalent) as external processes or dynamically linked modules.

**Python is the AI bridge.** Every AI component — AudioCraft, Demucs, DeepFilterNet, CREPE, Matchering — runs in Python/PyTorch. The practical pattern is to run these as microservices or subprocess workers, communicating with the C/C++ core via shared memory, sockets, or a message bus. DeepFilterNet's LADSPA plugin is a notable exception that runs natively in the audio thread.

**The web stack is surprisingly strong for UI.** Between wavesurfer.js, peaks.js, VexFlow, OSMD, webaudio-pianoroll, and audioMotion-analyzer, a complete DAW frontend can be built in TypeScript — suggesting an Electron/Tauri architecture where a native C/C++ audio engine powers a web-based UI. This matches the direction taken by modern DAWs like Bitwig (which co-created CLAP) and emerging web audio workstations.