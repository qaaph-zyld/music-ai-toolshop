# StemSlicer

A free, open-source Windows desktop application for high-quality audio stem separation using Demucs.

## Features

- **Simple GUI**: Clean, professional interface built with PySide6
- **Multiple Formats**: Supports MP3, WAV, FLAC, M4A
- **Batch Processing**: Process multiple files sequentially
- **Cancellable**: Stop processing at any time
- **Live Logging**: Real-time subprocess output
- **Multiple Models**: Choose from htdemucs_ft (4-stem), htdemucs_6s (6-stem)
- **Quality Presets**: Fast, Balanced, High, Ultra
- **Karaoke Mode**: Extract vocals and instrumental separately

## Requirements

- Windows 10/11
- Python 3.10 or higher (3.11 recommended)
- FFmpeg (required for audio decoding)
- Demucs (installed via pip)

## Installation

### Step 1: Install FFmpeg

**Option A (Recommended) - Using Anaconda:**
```bash
# In Anaconda Prompt:
conda install -c conda-forge ffmpeg
```

**Option B - Manual Installation:**
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract and add to your system PATH

### Step 2: Install Python Dependencies

```bash
# Install required packages
python -m pip install -U demucs SoundFile pyside6
```

### Step 3: Install StemSlicer

```bash
# Clone or download this repository
cd stemslicer

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

## Running the Application

```bash
python -m src.stemslicer.main
```

Or navigate to the `src/stemslicer` directory:
```bash
cd src/stemslicer
python main.py
```

## Usage

1. **Add Files**: Click "Add Files..." or "Add Folder..." to queue audio files
2. **Select Output**: Choose where to save the separated stems
3. **Configure Settings**:
   - Model: `htdemucs_ft` (4-stem) or `htdemucs_6s` (6-stem)
   - Mode: Stems (default) or Karaoke (vocals/instrumental)
   - Device: Auto, CPU, or CUDA (GPU)
   - Quality: Fast, Balanced, High, or Ultra
4. **Start Processing**: Click "Start" to begin separation
5. **Monitor Progress**: Watch the log panel for real-time updates

## Models

- **htdemucs_ft**: Fine-tuned Hybrid Transformer model - best for general 4-stem separation (vocals, drums, bass, other)
- **htdemucs_6s**: Experimental 6-source model (vocals, drums, bass, other, guitar, piano)

## Quality Presets

- **Fast**: shifts=0, overlap=0.10 (quickest, lower quality)
- **Balanced**: shifts=1, overlap=0.25 (recommended)
- **High**: shifts=2, overlap=0.25 (better quality, slower)
- **Ultra**: shifts=4, overlap=0.25 (best quality, slowest)

Note: High and Ultra presets require GPU (CUDA). CPU processing uses shifts=0 automatically.

## Advanced Settings

- **Overlap**: Higher values improve quality but increase processing time
- **Segment**: Lower values use less GPU memory but process slower
- **Jobs**: Number of parallel jobs (higher uses more RAM)

## Output Structure

Stems are saved in:
```
<output_folder>/separated/<model>/<trackname>/
  ├── vocals.wav
  ├── drums.wav
  ├── bass.wav
  └── other.wav
```

Each run creates a `run.json` manifest with processing details.

## Packaging as Executable (Optional)

To create a standalone Windows executable:

```bash
pip install pyinstaller

# Create executable (onedir recommended for torch)
pyinstaller --onedir --windowed --name StemSlicer src/stemslicer/main.py

# Note: FFmpeg must be in PATH or bundled separately
```

## Troubleshooting

### "FFmpeg not found"
- Ensure FFmpeg is installed and in your system PATH
- Test with: `ffmpeg -version`

### "Demucs not found"
- Install Demucs: `pip install -U demucs`
- Test with: `demucs -h`

### "CUDA not available"
- Install PyTorch with CUDA support: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

### Processing is very slow
- Use GPU if available (CUDA device)
- Lower quality preset (Fast or Balanced)
- Reduce segment size in advanced settings

### UI freezes
- The UI should remain responsive during processing
- If frozen, cancel and restart the application

## License

MIT License - See LICENSE file for details.

This project uses:
- **Demucs** (MIT License) by Facebook Research
- **PySide6** (LGPL) - Qt for Python
- **PyTorch** (BSD-style license)

## Credits

Built with [Demucs](https://github.com/facebookresearch/demucs) by Facebook Research.
