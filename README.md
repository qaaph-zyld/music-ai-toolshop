# music-ai-toolshop

![CI](https://github.com/qaaph-zyld/music-ai-toolshop/actions/workflows/ci.yml/badge.svg)

CLI toolshop to orchestrate music AI tools (self-contained):

- **Suno** – library listing, batch analysis, and text export (external sync optional)
- **BPM/Key Analysis** – detect tempo and musical key using librosa
- **YouTube** – search, metadata, download, summarize for Suno prompts
- **Track Reverse Engineering** – advanced structure analysis (BPM, key, chords, notes, effects, instruments, source separation)
- **Voice Effects Detection** – identify vocal processing (reverb, pitch shift, compression, auto-tune, etc.)
- **Stem Extraction** – separate instrumentals, main/backing vocals, and Demucs 4/6-stems with a unified, resumable command
- **Audio Cleaning** – remove pauses, breaths, coughs, clicks, and align to beat grid

## Installation

Requires **Python 3.11** (3.13 is not supported by several audio-ML packages).

```bash
# Create a Python 3.11 venv first
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[audio,youtube,voice,cleaning,track,stems]"
```

Or install with optional dependency groups:

```bash
pip install -e ".[all]"        # Core groups (audio, youtube, voice, cleaning, track)
pip install -e ".[audio]"      # librosa + numpy + scipy for BPM/key
pip install -e ".[youtube]"    # yt-dlp for YouTube tools
pip install -e ".[voice]"      # Voice effects detection (parselmouth + librosa)
pip install -e ".[voice-full]" # Voice + crepe neural pitch (requires tensorflow)
pip install -e ".[stems]"      # Stem extraction (audio-separator + demucs)
pip install -e ".[cleaning]"   # Audio cleaning pipeline
pip install -e ".[track]"      # Reverse engineering analysis
```

## Hardware profile

This repo is developed on a **CPU-only** Windows 10 machine:

- CPU-only inference is the default; modern CUDA/DirectML require a newer GPU.
- Measured: ~12 min/track for the full reverse-engineering pipeline in fast mode.
- FLAC output is the default for stems to save disk.

Run `toolshop doctor` after install to verify Python version, ffmpeg, packages, disk space, and the model-cache directory.

## Quick Start

```bash
# Verify environment after install
toolshop doctor

# Analyze a local audio file
toolshop analyze bpm-key song.wav

# Search YouTube and analyze the first result
toolshop yt analyze "https://youtube.com/watch?v=VIDEO_ID"

# Batch-analyze your Suno library
toolshop suno analyze --root path/to/suno_library

# Detect voice effects on an audio file
toolshop voice analyze recording.wav

# List available stem presets and models
toolshop stems --list-models

# Extract stems from an audio file (karaoke = 2-stem fast)
toolshop stems song.wav --preset karaoke --device cpu

# High-quality vocals separation
toolshop stems song.wav --preset full-vocals --device cpu

# Demucs 4-stem separation
toolshop stems song.wav --preset 4stem --device cpu

# Batch process a folder, resumable
toolshop stems ./songs --preset karaoke --limit 10 --offset 5

# Create a remix at a target BPM/key
toolshop remix song.wav --target-bpm 95 --target-key Gm --output remix.wav

# Extract a sample pack from a track
toolshop remix song.wav --mode sample --segment-beats 4 --output-dir ./samples
```

## Data boundary

Audio inputs and generated outputs (stems, batches, personal libraries) live outside this repository. Default data root is `D:\MusicData\toolshop\`; override with the `TOOLSHOP_DATA_DIR` environment variable.

---

## Commands Reference

### Suno Tools (`toolshop suno`)

```bash
# (Optional) Sync liked clips from Suno using your own downloader
# NOTE: `toolshop` no longer imports the sibling Suno repo directly.
toolshop suno sync-liked --output-dir suno_library   # currently a stub that raises

# Bulk download *liked* Suno clips (standalone app) as WAV only
# (run from: projects/Suno/bulk_downloader_app)
# PowerShell:
#   $env:SUNO_WAV_ONLY=1
#   .\.venv\Scripts\python.exe suno_downloader.py

# List tracks in local library
toolshop suno list --root suno_library

# Batch-analyze all tracks for BPM/key
toolshop suno analyze --root suno_library --output analysis.json

# Export lyrics + descriptions from liked tracks (grouped/sorted)
toolshop suno export-text --root suno_library \
  --json-out suno_library/lyrics_export.json \
  --txt-out  suno_library/lyrics_export.txt
```

### BPM/Key Analysis (`toolshop analyze`)

```bash
# Single file analysis
toolshop analyze bpm-key song.wav
toolshop analyze bpm-key song.wav --json

# Batch analysis of a directory
toolshop analyze library ./music --ext wav,mp3 --output results.json
```

**Example output:**
```
File: song.wav
BPM: 152.0
Key: F major
Duration: 294.28s
```

### YouTube Tools (`toolshop yt`)

```bash
# Search YouTube
toolshop yt search "lofi beats" --limit 5
toolshop yt search "hardcore pop" --json

# Get video metadata
toolshop yt info VIDEO_ID
toolshop yt info "https://youtube.com/watch?v=..." --json

# Generate Suno-ready prompt from video
toolshop yt summarize "https://youtube.com/watch?v=..."
toolshop yt summarize URL --for keywords  # Extract genre/mood hints

# Download audio
toolshop yt download URL --output-dir ./downloads --format wav

# Download + analyze in one step (NEW)
toolshop yt analyze URL
toolshop yt analyze URL --full  # Include chord detection
```

**Example `yt summarize` output:**
```
Best of lofi hip hop 2021 ✨ [beats to relax/study to] | Tags: lofi, chill beats, relaxing
```

### Track Analysis (`toolshop track`)

```bash
# Structure analysis (BPM, key, spectral features)
toolshop track analyze song.wav
toolshop track analyze song.wav --summary
toolshop track analyze song.wav --export-json --output-dir ./results

# Advanced analysis using the external wav_reverse_engineer backend
toolshop track analyze song.wav --chords --notes --effects --instruments --separation hpss

# Batch analyze a directory of audio files
toolshop track batch ./tracks --recursive --output batch_analysis.json

# Download and analyze a YouTube video
toolshop track yt-analyze <url> --output-dir ./yt --keep-audio

# Generate visualizations
toolshop track visualize song.wav --output-dir ./plots
```

**Example output:**
```
=== Track Analysis Summary ===
File: song.wav
Duration: 294.28s
BPM: 152.0
Key: F major
Harmonic Ratio: 0.7862
Backend: basic_librosa

Chord Progression:
  Fm @ 54.22s
  Fm @ 57.52s
  F @ 65.43s
```

### Voice Effects Detection (`toolshop voice`)

```bash
# Analyze a voice recording for applied effects
toolshop voice analyze recording.wav

# JSON output for programmatic use
toolshop voice analyze recording.wav --json

# Export analysis to file
toolshop voice analyze recording.wav --export-json --output-dir ./results
```

**Detected effects** (12 categories):
- Reverb (RT60, room type)
- Pitch shift (semitone estimate via F0-formant mismatch)
- Formant shift (formant ratio anomalies)
- Compression (crest factor, dynamic range)
- EQ / Filtering (spectral shape, HP/LP detection, presence boost)
- Distortion / Saturation (THD, clipping, harmonic ratios)
- Chorus / Doubling (phase coherence, bandwidth modulation)
- Auto-tune / Pitch correction (F0 quantization, transition sharpness)
- De-essing (sibilant energy analysis)
- Vocoder (carrier detection, MFCC regularity)
- Noise gate (transition sharpness, silence floor)
- Delay / Echo (autocorrelation peaks)

**Example output:**
```
============================================================
  VOICE EFFECTS ANALYSIS REPORT
============================================================
  File:       recording.wav
  Duration:   45.2s
  Voice:      Detected
  F0:         185.3Hz

  DETECTED EFFECTS:
  --------------------------------------------------------
  [91%] ####################  Compression
        > Very low crest factor: 4.2dB (heavy compression)
        > Very narrow dynamic range: 5.1dB
        Params: crest_factor_db=4.2, estimated_ratio=8:1+

  [87%] #################    Reverb
        > Energy decay RT60 ~ 1.20s
        Params: estimated_rt60_seconds=1.2, type=room

  [72%] ##############       Pitch Shift
        > F0 (185Hz) above expected range (75-190Hz)
        Params: estimated_semitones=+3.0
```

### Stem Extraction (`toolshop stems`)

Unified, resumable stem separation supporting both audio-separator models and Demucs.

```bash
# List available presets and registered models
toolshop stems --list-models

# Extract stems from a single file
toolshop stems song.wav --preset karaoke --device cpu
toolshop stems song.wav --preset full-vocals --device cpu --format flac

# Demucs 4-stem or 6-stem
toolshop stems song.wav --preset 4stem --device cpu
toolshop stems song.wav --preset 6stem --device cpu

# Batch process a directory, resumable by default
toolshop stems ./songs --preset karaoke --limit 10 --offset 5

# Reprocess everything, ignoring a previous batch_status.json
toolshop stems ./songs --preset karaoke --no-resume

# JSON output for programmatic use
toolshop stems song.wav --preset karaoke --json
```

**Presets:**
| preset | description | backend |
|--------|-------------|---------|
| `karaoke` | Fast 2-stem: instrumental + main vocals | audio-separator (MDX-Net) |
| `vocals-hq` | HQ 2-stem: instrumental + main vocals | audio-separator (BS-Roformer) |
| `full-vocals` | Fast 3-stem: instrumental + main + backing vocals | audio-separator (2-pass) |
| `full-vocals-hq` | HQ 3-stem: instrumental + main + backing vocals | audio-separator (2-pass) |
| `4stem` | Drums, bass, other, vocals | demucs |
| `6stem` | Drums, bass, other, vocals, guitar, piano | demucs |

**Requirements:**
- Install with `pip install -e ".[stems]"` (audio-separator + demucs).
- CPU inference is the default; `--device gpu` warns/falls back on the unsupported GT 640.
- Outputs are written to `<TOOLSHOP_DATA_DIR>/stems/<preset>/<slug>/` unless `--out` is provided.

**Output:** each run produces the selected stem files plus a `manifest.json` containing source hash, models used, device, and version.

**Example output:**
```
Extracted stems from song.wav
  Preset: karaoke
  Output: D:\MusicData\toolshop\stems\karaoke\song_abc123
  Format: flac
  GPU: False
  instrumental: song_Instrumental.flac
  main_vocals: song_Vocals.flac
```

---

### Audio Cleaning (`toolshop clean`)

Multi-stage pipeline to clean audio tracks by removing pauses, breaths, coughs, clicks, and analyzing beat alignment.

**Installation:**
```bash
pip install -e ".[cleaning]"  # librosa + pyyaml + soundfile
```

**Commands:**

```bash
# Run full cleaning pipeline
toolshop clean pipeline audio.wav --config clean_config.yaml

# Remove long pauses/silences only
toolshop clean pause-remove audio.wav --threshold -40

# Detect and attenuate breath sounds
toolshop clean breath-detect audio.wav --attenuation 15

# Detect and remove discrete events
toolshop clean event-detect audio.wav --detect coughs,clicks

# Analyze beat alignment
toolshop clean beat-align audio.wav --mode analyze

# Generate configuration template
toolshop clean config-template --output clean_config.yaml
```

**Pipeline Stages:**

1. **Preprocessing** – Load audio, detect BPM/key, extract features
2. **Pause Removal** – Remove long silences with crossfades
3. **Breath Detection** – Frequency/energy-based detection with attenuation
4. **Event Detection** – Detect coughs, clicks, pops using spectral analysis
5. **Beat Alignment** – Detect beats and tempo analysis
6. **Final Assembly** – Normalization, metadata, export

**Configuration Example:**

```yaml
stages:
  preprocessing:
    target_sample_rate: 44100
    normalize_input: true
  pause_removal:
    min_silence: 0.3
    max_keep: 0.5
    threshold_db: -40
  breath_detection:
    method: combined  # frequency, energy, or combined
    attenuation_db: 15
  event_detection:
    detect_coughs: true
    detect_clicks: true
    detect_pops: true
    confidence_threshold: 0.7
  beat_alignment:
    mode: analyze  # or 'align'
```

---

### Remix / Sample Forge (`toolshop remix`)

Create tempo/key-matched remixes or sliced sample packs from any audio up to 4 minutes.
Uses `pedalboard` (Rubber Band) for high-quality time-stretch and pitch-shift, plus `librosa`
for beat/onset slicing.

```bash
# Remix a track to a target BPM/key with FX
toolshop remix song.wav --target-bpm 95 --target-key Gm --fx reverb delay --output remix.wav

# Extract a sample pack from a full mix
toolshop remix song.wav --mode sample --output-dir ./samples

# Remix using a stem from a toolshop stems output directory
toolshop remix song.wav --stems-dir ./stems/karaoke/my_song_unknown --target-bpm 90

# Batch sample extraction
toolshop remix ./songs --mode sample --output-dir D:\MusicData\toolshop\samples --limit 10
```

- Inputs longer than `--max-duration` seconds (default: 240) are truncated with a warning.
- `--mode remix` writes one output file and a manifest.
- `--mode sample` writes a directory of samples and a manifest.
- `--fx` supports `reverb`, `delay`, `gain`, `compressor`, `distortion`.
- Output defaults to `D:\MusicData\toolshop\remixes` or `D:\MusicData\toolshop\samples`.

#### Section-aware Sample Forge

Slice a track by externally-provided song sections (JSON) instead of generic beat/onset
chopping. Each sample is labeled by section and named `<key>_<bpm>_<section>_<n>.<ext>`.

**JSON schema:**

```json
{
  "sections": [
    {"label": "intro", "start": 0.0, "end": 8.0},
    {"label": "verse", "start": 8.0, "end": 24.0},
    {"label": "chorus", "start": 24.0, "end": 40.0}
  ]
}
```

**Example:**

```bash
toolshop remix song.wav --mode sample --sections sections.json --output ./pack
toolshop remix song.wav --mode sample --sections sections.json --sub-slice-beats 4 --no-beat-snap
```

- `--sections` — path to JSON file with section boundaries (requires `--mode sample`).
- `--sub-slice-beats N` — sub-slice each section every N beats (requires `--sections`).
- `--no-beat-snap` — disable snapping section boundaries to the nearest beat grid point.
- Sample filenames follow the pattern `A_120_chorus_01.flac` (key, BPM, section, index).
- The manifest includes a `"section"` field for each sample.
- **Automatic section detection is deferred** to a future H2 structure detector. For now,
  sections must be provided externally (e.g. from a manual annotation or third-party tool).

---

## Python API

All adapters can be imported directly:

```python
from toolshop import bpm_adapter, yt_scraper_adapter, reverse_engineering_adapter, voice_effects_adapter

# BPM/key analysis
result = bpm_adapter.analyze_track(Path("song.wav"))
print(f"{result['bpm']} BPM, {result['key']} {result['mode']}")

# YouTube search
videos = yt_scraper_adapter.search("lofi beats", limit=5)
for v in videos:
    print(v['title'], v['url'])

# Full track analysis
analysis = reverse_engineering_adapter.analyze_track(Path("song.wav"))
print(analysis['chord_progression'])

# Voice effects detection
result = voice_effects_adapter.analyze_voice(Path("recording.wav"))
for effect in result['effects_detected']:
    if effect['confidence'] > 0.2:
        print(f"{effect['effect']}: {effect['confidence']:.0%}")

# Audio cleaning pipeline
from toolshop import cleaning_pipeline_adapter

config = cleaning_pipeline_adapter.get_default_config()
pipeline = cleaning_pipeline_adapter.AudioCleaningPipeline(config)
summary = pipeline.process("input.wav", "cleaned_output.wav")

print(f"Breaths detected: {summary['stage_reports'][2].get('breaths_detected', 0)}")
print(f"Events removed: {summary['stage_reports'][3].get('events_detected', 0)}")
print(f"Time removed: {summary['stage_reports'][1].get('time_removed', 0):.2f}s")

# Remix / sample creation
from toolshop import remix_adapter

result = remix_adapter.create_remix(
    Path("song.wav"),
    Path("remix.wav"),
    target_bpm=95.0,
    target_key="Gm",
    fx_chain=["reverb"],
)
print(f"Remix: {result.output_file} ({result.bpm:.2f} BPM, key {result.key})")
```

---

## Repository Layout

```
toolshop/
├── cli.py                        # CLI entrypoint
├── doctor.py                     # Environment health-check diagnostics
├── suno_adapter.py               # Suno tools (list/analyze/export; sync stub)
├── bpm_adapter.py                # librosa-based BPM/key analysis
├── yt_scraper_adapter.py         # yt-dlp library integration
├── yt_summarizer_adapter.py      # Suno prompt generation
├── reverse_engineering_adapter.py # wav_reverse_engineer wrapper with librosa fallback
├── voice_effects_adapter.py      # Voice effects detection (12 detectors)
├── stem_extractor_adapter.py     # Stem separation (instrumentals/vocals)
├── cleaning_stages.py          # Audio cleaning pipeline stages
└── cleaning_pipeline_adapter.py  # Pipeline controller and CLI
```

## Dependencies

- **Required:** Python 3.11
- **Audio analysis:** `librosa`, `numpy`, `scipy`
- **YouTube tools:** `yt-dlp`
- **Stems:** `audio-separator`, `onnxruntime`, `demucs`, `soundfile`
- **Track reverse engineering:** `wav_reverse_engineer` (cloned sub-project) with librosa fallback
- **Voice effects (core):** `librosa`, `numpy`, `scipy`, `parselmouth`, `soundfile`
- **Voice effects (full):** Above + `crepe`, `tensorflow` (neural pitch detection)
- **Cleaning:** `librosa`, `numpy`, `scipy`, `soundfile`, `pyyaml`

## License

MIT
