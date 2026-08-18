"""Silence Detector for Vocal Cleanup

Detects silent gaps in audio files using FFmpeg's silencedetect filter.
Designed for TDD - minimal implementation to pass tests.
"""

import subprocess
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class SilenceConfig:
    """Configuration for silence detection."""
    threshold_db: float = -50.0
    min_duration_sec: float = 0.2
    padding_sec: float = 0.01


class SilenceDetector:
    """Detects silent gaps in audio files.
    
    Uses FFmpeg silencedetect filter for robust detection.
    """
    
    def __init__(self, threshold_db: float = -50.0, 
                 min_duration_sec: float = 0.2,
                 padding_sec: float = 0.01):
        self.threshold_db = threshold_db
        self.min_duration_sec = min_duration_sec
        self.padding_sec = padding_sec
    
    def detect(self, audio_path: str) -> List[Dict[str, float]]:
        """Detect silence gaps in audio file.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            List of gap dictionaries with 'start', 'end', 'duration'
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Use FFmpeg silencedetect to find silence periods
        cmd = [
            'ffmpeg',
            '-i', str(audio_path),
            '-af', f'silencedetect=noise={self.threshold_db}dB:d={self.min_duration_sec}',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # FFmpeg exits with 1 on null output
            )
        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
        
        # Parse FFmpeg output for silence detection
        gaps = self._parse_silencedetect_output(result.stderr)
        
        return gaps
    
    def _parse_silencedetect_output(self, output: str) -> List[Dict[str, float]]:
        """Parse FFmpeg silencedetect filter output.
        
        FFmpeg outputs lines like:
        [silencedetect @ ...] silence_start: 0.5
        [silencedetect @ ...] silence_end: 1.0 | silence_duration: 0.5
        """
        gaps = []
        
        # Extract silence_start times
        silence_starts = re.findall(r'silence_start: ([\d.]+)', output)
        silence_ends = re.findall(r'silence_end: ([\d.]+)', output)
        silence_durations = re.findall(r'silence_duration: ([\d.]+)', output)
        
        # Pair up starts and ends
        for i, start in enumerate(silence_starts):
            if i < len(silence_ends):
                start_sec = float(start)
                end_sec = float(silence_ends[i])
                duration = float(silence_durations[i]) if i < len(silence_durations) else end_sec - start_sec
                
                # Apply padding (reduce gap slightly to avoid cutting into audio)
                if duration > (2 * self.padding_sec):
                    start_sec += self.padding_sec
                    end_sec -= self.padding_sec
                    duration = end_sec - start_sec
                
                gaps.append({
                    'start': round(start_sec, 3),
                    'end': round(end_sec, 3),
                    'duration': round(duration, 3)
                })
        
        return gaps


if __name__ == '__main__':
    # Simple test run
    import tempfile
    import wave
    import numpy as np
    import io
    
    # Create test file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sample_rate = 44100
        pattern = [
            (0.5, 0.8),
            (0.5, 0.0),
            (0.5, 0.8),
        ]
        
        samples = []
        for duration, amp in pattern:
            num_samples = int(duration * sample_rate)
            samples.extend([amp] * num_samples)
        
        audio_data = np.array(samples, dtype=np.float32)
        audio_data = (audio_data * 32767).astype(np.int16)
        
        with wave.open(f.name, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data.tobytes())
        
        test_file = f.name
    
    # Test detection
    detector = SilenceDetector(threshold_db=-40, min_duration_sec=0.1)
    gaps = detector.detect(test_file)
    
    print(f"Detected {len(gaps)} silence gaps:")
    for gap in gaps:
        print(f"  Start: {gap['start']:.3f}s, End: {gap['end']:.3f}s, Duration: {gap['duration']:.3f}s")
    
    # Cleanup
    Path(test_file).unlink()
