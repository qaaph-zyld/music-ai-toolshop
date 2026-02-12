# music-ai-toolshop

CLI toolshop to orchestrate music AI tools (self-contained):

- **Suno** – library listing, batch analysis, and text export (external sync optional)
- **BPM/Key Analysis** – detect tempo and musical key using librosa
- **YouTube** – search, metadata, download, summarize for Suno prompts
- **Track Reverse Engineering** – basic structure analysis (BPM, key, spectral features)
- **Voice Effects Detection** – identify vocal processing (reverb, pitch shift, compression, auto-tune, etc.)

## Installation

```bash
pip install -e .
pip install librosa numpy yt-dlp  # Optional dependencies
```

Or install with optional dependency groups:

```bash
pip install -e ".[all]"        # Everything
pip install -e ".[audio]"      # librosa + numpy + scipy for BPM/key
pip install -e ".[youtube]"    # yt-dlp for YouTube tools
pip install -e ".[voice]"      # Voice effects detection (parselmouth + librosa)
pip install -e ".[voice-full]" # Voice + crepe neural pitch (requires tensorflow)
```

## Quick Start

```bash
# Analyze a local audio file
toolshop analyze bpm-key song.wav

# Search YouTube and analyze the first result
toolshop yt analyze "https://youtube.com/watch?v=VIDEO_ID"

# Batch-analyze your Suno library
toolshop suno analyze --root path/to/suno_library

# Detect voice effects on an audio file
toolshop voice analyze recording.wav
```

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
```

---

## Repository Layout

```
toolshop/
├── cli.py                        # CLI entrypoint
├── suno_adapter.py               # Suno tools (list/analyze/export; sync stub)
├── bpm_adapter.py                # librosa-based BPM/key analysis
├── yt_scraper_adapter.py         # yt-dlp library integration
├── yt_summarizer_adapter.py      # Suno prompt generation
├── reverse_engineering_adapter.py # Pure librosa-based track analysis
└── voice_effects_adapter.py      # Voice effects detection (12 detectors)
```

## Dependencies

- **Required:** Python 3.10+
- **Audio analysis:** `librosa`, `numpy`, `scipy`
- **YouTube tools:** `yt-dlp`
- **Track reverse engineering:** Pure librosa-based (no external repos required)
- **Voice effects (core):** `librosa`, `numpy`, `scipy`, `parselmouth`, `soundfile`
- **Voice effects (full):** Above + `crepe`, `tensorflow` (neural pitch detection)

## License

MIT
