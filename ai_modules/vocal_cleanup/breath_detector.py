"""Breath Detector for Vocal Cleanup

Detects breath sounds in vocal recordings using spectral analysis.
Uses librosa for feature extraction.

Breath characteristics:
- Low spectral centroid (low frequency energy)
- High zero-crossing rate (noise-like)
- Short duration (100-800ms)
- Lower amplitude than speech
"""

import numpy as np
import librosa
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class BreathConfig:
    """Configuration for breath detection."""
    sensitivity: float = 0.5  # 0.0 to 1.0
    min_breath_duration: float = 0.1  # seconds
    max_breath_duration: float = 0.8  # seconds
    frame_size: int = 512
    hop_length: int = 256


class BreathDetector:
    """Detects breath sounds in vocal audio.
    
    Uses spectral analysis to identify breath segments:
    - Low spectral centroid (breaths are low-freq)
    - High zero-crossing rate (noise-like quality)
    - Energy patterns (breaths are quieter)
    """
    
    def __init__(self, sensitivity: float = 0.5,
                 min_breath_duration: float = 0.1,
                 max_breath_duration: float = 0.8):
        self.sensitivity = sensitivity
        self.min_breath_duration = min_breath_duration
        self.max_breath_duration = max_breath_duration
        self.frame_size = 512
        self.hop_length = 256
    
    def detect(self, audio_path: str) -> List[Dict[str, float]]:
        """Detect breath segments in audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of breath dictionaries with 'start', 'end', 'duration', 
            'type', 'confidence'
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Load audio
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        
        # Extract features
        features = self._extract_features(y, sr)
        
        # Detect breath segments
        breath_segments = self._detect_breath_segments(features, sr)
        
        # Convert to output format
        breaths = []
        for start_sample, end_sample, confidence in breath_segments:
            start_sec = start_sample / sr
            end_sec = end_sample / sr
            duration = end_sec - start_sec
            
            breaths.append({
                'start': round(start_sec, 3),
                'end': round(end_sec, 3),
                'duration': round(duration, 3),
                'type': 'breath',
                'confidence': round(confidence, 3)
            })
        
        return breaths
    
    def _extract_features(self, y: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        """Extract audio features for breath detection."""
        # Spectral centroid (frequency center of mass)
        spectral_centroid = librosa.feature.spectral_centroid(
            y=y, sr=sr, n_fft=self.frame_size, hop_length=self.hop_length
        )[0]
        
        # Zero crossing rate (noisiness)
        zcr = librosa.feature.zero_crossing_rate(
            y, frame_length=self.frame_size, hop_length=self.hop_length
        )[0]
        
        # RMS energy
        rms = librosa.feature.rms(
            y=y, frame_length=self.frame_size, hop_length=self.hop_length
        )[0]
        
        # Spectral rolloff (frequency below which X% of energy lies)
        rolloff = librosa.feature.spectral_rolloff(
            y=y, sr=sr, n_fft=self.frame_size, hop_length=self.hop_length
        )[0]
        
        return {
            'spectral_centroid': spectral_centroid,
            'zcr': zcr,
            'rms': rms,
            'rolloff': rolloff
        }
    
    def _detect_breath_segments(self, features: Dict[str, np.ndarray], sr: int) -> List[Tuple[int, int, float]]:
        """Detect breath segments from features.
        
        Returns list of (start_sample, end_sample, confidence) tuples.
        """
        spectral_centroid = features['spectral_centroid']
        zcr = features['zcr']
        rms = features['rms']
        
        # Normalize features
        sc_norm = (spectral_centroid - np.min(spectral_centroid)) / (np.max(spectral_centroid) - np.min(spectral_centroid) + 1e-8)
        zcr_norm = (zcr - np.min(zcr)) / (np.max(zcr) - np.min(zcr) + 1e-8)
        rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-8)
        
        # Breath likelihood score
        # Low spectral centroid + high ZCR + low RMS = breath
        breath_score = (1 - sc_norm) + zcr_norm + (1 - rms_norm)
        breath_score /= 3.0  # Normalize to 0-1
        
        # Apply sensitivity threshold
        threshold = 0.3 + (1 - self.sensitivity) * 0.4  # 0.3 to 0.7
        is_breath = breath_score > threshold
        
        # Find contiguous breath segments
        segments = []
        in_breath = False
        start_idx = 0
        
        for i, is_b in enumerate(is_breath):
            if is_b and not in_breath:
                # Start of breath
                in_breath = True
                start_idx = i
            elif not is_b and in_breath:
                # End of breath
                in_breath = False
                end_idx = i
                
                # Convert frame indices to samples
                start_sample = start_idx * self.hop_length
                end_sample = end_idx * self.hop_length
                duration_sec = (end_sample - start_sample) / sr
                
                # Check duration constraints
                if self.min_breath_duration <= duration_sec <= self.max_breath_duration:
                    # Calculate confidence from average breath score
                    avg_confidence = float(np.mean(breath_score[start_idx:end_idx]))
                    segments.append((start_sample, end_sample, avg_confidence))
        
        # Handle case where breath extends to end
        if in_breath:
            end_idx = len(is_breath)
            start_sample = start_idx * self.hop_length
            end_sample = end_idx * self.hop_length
            duration_sec = (end_sample - start_sample) / sr
            
            if self.min_breath_duration <= duration_sec <= self.max_breath_duration:
                avg_confidence = float(np.mean(breath_score[start_idx:end_idx]))
                segments.append((start_sample, end_sample, avg_confidence))
        
        return segments


if __name__ == '__main__':
    # Test run
    import tempfile
    import wave
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sample_rate = 44100
        
        # Create speech - breath - speech pattern
        t1 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        speech1 = 0.6 * np.sin(2 * np.pi * 200 * t1)
        
        t_b = np.linspace(0, 0.3, int(0.3 * sample_rate))
        breath = 0.15 * np.random.randn(len(t_b))
        breath = np.convolve(breath, np.ones(10)/10, mode='same')
        
        t2 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        speech2 = 0.6 * np.sin(2 * np.pi * 200 * t2)
        
        audio = np.concatenate([speech1, breath, speech2])
        audio = (audio * 32767).astype(np.int16)
        
        with wave.open(f.name, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        test_file = f.name
    
    # Test detection
    detector = BreathDetector(sensitivity=0.5)
    breaths = detector.detect(test_file)
    
    print(f"Detected {len(breaths)} breath segments:")
    for breath in breaths:
        print(f"  Start: {breath['start']:.3f}s, End: {breath['end']:.3f}s, "
              f"Duration: {breath['duration']:.3f}s, Confidence: {breath['confidence']:.3f}")
    
    # Cleanup
    Path(test_file).unlink()
