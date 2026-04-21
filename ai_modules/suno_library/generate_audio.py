#!/usr/bin/env python3
"""Generate test MP3 audio files for Suno Library API

Creates simple silent/tonal MP3 files for testing the audio streaming endpoint.
Uses pydub if available, otherwise generates minimal MP3 files.
"""

import os
import struct
from pathlib import Path

try:
    from pydub import AudioSegment
    from pydub.generators import Sine
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def create_minimal_mp3(filepath, duration_ms=1000, freq=440):
    """Create a minimal MP3 file.
    
    If pydub available: generates sine wave
    Otherwise: creates a minimal valid MP3-like file (for testing purposes)
    """
    if PYDUB_AVAILABLE:
        # Generate sine wave
        sine_wave = Sine(freq).to_audio_segment(duration=duration_ms)
        sine_wave.export(filepath, format="mp3", bitrate="64k")
        return True
    else:
        # Create a minimal MP3 frame (simplified - for testing only)
        # This creates a valid MP3 frame header but minimal content
        return create_stub_mp3(filepath)


def create_stub_mp3(filepath):
    """Create a minimal MP3 file stub.
    
    Creates a file with valid MP3 frame headers but silent content.
    This is sufficient for testing the streaming endpoint.
    """
    # MP3 frame header for MPEG-1 Layer 3, 44100 Hz, 128 kbps, stereo
    # Hex: FFF3 8480 0000 0000 0000 0000 0000 0000
    frame_header = bytes.fromhex('FFF3')
    
    # Create a minimal file with some frames
    with open(filepath, 'wb') as f:
        # Write ID3 tag (minimal)
        id3_header = b'ID3\x03\x00\x00\x00\x00\x00\x00'
        f.write(id3_header)
        
        # Write a few MP3 frames (silent)
        for _ in range(50):  # ~1 second of frames
            f.write(frame_header)
            f.write(b'\x84\x80')  # Bitrate/sample rate info
            f.write(b'\x00' * 418)  # Frame payload (silent)
    
    return True


def generate_all_audio_files():
    """Generate all 10 test audio files."""
    audio_dir = Path(__file__).parent / "audio"
    audio_dir.mkdir(exist_ok=True)
    
    tracks = [
        ("track_001.mp3", 440),   # Neon Dreams - A4
        ("track_002.mp3", 330),   # Acoustic Morning - E4
        ("track_003.mp3", 220),   # Drum Loop A - A3
        ("track_004.mp3", 130),   # Deep Bass - C3
        ("track_005.mp3", 523),   # Ambient Pad - C5
        ("track_006.mp3", 392),   # Pop Melody - G4
        ("track_007.mp3", 165),   # Rock Riff - E3
        ("track_008.mp3", 294),   # Jazz Chords - D4
        ("track_009.mp3", 196),   # Hip Hop Beat - G3
        ("track_010.mp3", 262),   # Techno Pulse - C4
    ]
    
    print("Generating test audio files...")
    if not PYDUB_AVAILABLE:
        print("(pydub not available - creating minimal MP3 stubs)")
    
    for filename, freq in tracks:
        filepath = audio_dir / filename
        if create_minimal_mp3(filepath, duration_ms=1500, freq=freq):
            size = filepath.stat().st_size
            print(f"  ✅ {filename} ({size} bytes, {freq}Hz)")
        else:
            print(f"  ❌ Failed to create {filename}")
    
    print(f"\n✅ Audio files created in: {audio_dir}")
    print(f"Total files: {len(tracks)}")


if __name__ == "__main__":
    print("=" * 50)
    print("Suno Library Test Audio Generator")
    print("=" * 50)
    
    if PYDUB_AVAILABLE:
        print("Using pydub for audio generation\n")
    else:
        print("pydub not installed - creating minimal MP3 stubs")
        print("Install with: pip install pydub\n")
    
    generate_all_audio_files()
