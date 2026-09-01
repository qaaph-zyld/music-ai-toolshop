# WAV Reverse Engineering Tool

A powerful tool for analyzing and reverse engineering audio files. This tool provides insights into the musical and technical aspects of audio tracks — from local files or directly from YouTube URLs.

## Features

- **YouTube Integration** — Analyze any YouTube video directly by URL
- Audio visualization (waveform, spectrogram)
- Beat and tempo detection
- Key and scale detection
- Chord recognition
- Note transcription
- Instrument identification
- Effects analysis
- Source separation (HPSS, Spleeter, Demucs)
- REST API for headless analysis

## Installation

```bash
git clone https://github.com/qaaph-zyld/track_reverse_engineering.git
cd track_reverse_engineering/wav_reverse_engineer
pip install -e .
```

For full features (source separation, advanced pitch tracking, etc.):

```bash
pip install -e ".[full]"
```

## Quick Start

### Analyze a Local File

```bash
wav-reverse-engineer analyze path/to/audio.wav --export-json --summary
```

### Analyze a YouTube Video (NEW!)

```bash
wav-reverse-engineer yt-analyze "https://www.youtube.com/watch?v=VIDEO_ID" --export-json --summary
```

Options:
- `--keep-audio` — Keep the downloaded audio file
- `--effects` — Run advanced effects analysis
- `--instruments` — Run instrument recognition
- `--separate hpss|demucs` — Perform source separation
 - `--summary` — Print a concise human-readable summary after analysis

### Python API

```python
from audio_analyzer.audio_processor import AudioProcessor
from audio_analyzer.feature_extractor import FeatureExtractor

# Load an audio file
audio, sr = AudioProcessor.load_audio("path/to/your/audio.wav")

# Extract features
extractor = FeatureExtractor()
features = extractor.extract_features(audio, sr)

# Print the analysis results
print(features)
```

### YouTube Ingestion (Python)

```python
from audio_analyzer.youtube_ingestion import YouTubeIngestion

yt = YouTubeIngestion(output_dir="downloads", keep_files=True)
audio_path, video_info = yt.download_audio("https://youtube.com/watch?v=VIDEO_ID")

print(f"Downloaded: {video_info['title']}")
print(f"Audio file: {audio_path}")
```

### REST API

Start the API server:

```bash
pip install -e ".[api]"
uvicorn wav_reverse_engineer.api.app:app --host 0.0.0.0 --port 8000
```

Endpoints:
- `POST /analyze` — Upload a file for analysis
- `POST /analyze-youtube` — Analyze a YouTube URL

Example:

```bash
curl -X POST "http://localhost:8000/analyze-youtube" \
  -F "url=https://www.youtube.com/watch?v=VIDEO_ID" \
  -F "effects=false"
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `analyze <file>` | Analyze a local audio file (use `--summary` for a human-readable report) |
| `yt-analyze <url>` | Analyze audio from a YouTube URL (use `--summary` for a human-readable report) |
| `batch <dir>` | Process multiple files in a directory |
| `version` | Show version information |

## Dependencies

Core:
- librosa, numpy, matplotlib, scipy
- pydub, soundfile
- yt-dlp (for YouTube integration)

Optional (via extras):
- torch, torchcrepe (pitch tracking)
- spleeter, demucs (source separation)
- fastapi, uvicorn (REST API)

## License

MIT
