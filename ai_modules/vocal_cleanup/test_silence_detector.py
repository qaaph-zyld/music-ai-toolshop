"""TDD Tests for Silence Detector - Vocal Cleanup Module

Tests MUST fail initially (RED), then pass after implementation (GREEN).
"""

import pytest
import numpy as np
import wave
import io
from pathlib import Path


class TestSilenceDetectorInitialization:
    """Tests for SilenceDetector class creation and configuration."""
    
    def test_detector_can_be_created(self):
        """RED: Should create SilenceDetector with default settings."""
        from silence_detector import SilenceDetector
        detector = SilenceDetector()
        assert detector is not None
    
    def test_detector_accepts_threshold(self):
        """RED: Should accept silence threshold in dB."""
        from silence_detector import SilenceDetector
        detector = SilenceDetector(threshold_db=-40)
        assert detector.threshold_db == -40
    
    def test_detector_accepts_min_duration(self):
        """RED: Should accept minimum gap duration in seconds."""
        from silence_detector import SilenceDetector
        detector = SilenceDetector(min_duration_sec=0.3)
        assert detector.min_duration_sec == 0.3
    
    def test_detector_has_default_values(self):
        """RED: Should have sensible defaults."""
        from silence_detector import SilenceDetector
        detector = SilenceDetector()
        assert detector.threshold_db == -50  # -50 dB default
        assert detector.min_duration_sec == 0.2  # 200ms default
        assert detector.padding_sec == 0.01  # 10ms default


class TestSilenceDetectorWithAudio:
    """Tests for silence detection on actual audio data."""
    
    def create_test_wav(self, pattern):
        """Helper: Create test WAV file with known pattern.
        pattern: list of (duration_sec, amplitude) tuples
        """
        sample_rate = 44100
        samples = []
        for duration, amp in pattern:
            num_samples = int(duration * sample_rate)
            samples.extend([amp] * num_samples)
        
        # Convert to 16-bit PCM
        audio_data = np.array(samples, dtype=np.float32)
        audio_data = (audio_data * 32767).astype(np.int16)
        
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data.tobytes())
        
        buf.seek(0)
        return buf
    
    def test_detects_silence_gap(self, tmp_path):
        """RED: Should detect a single silence gap in audio.
        Pattern: 0.5s sound, 0.5s silence, 0.5s sound
        """
        from silence_detector import SilenceDetector
        
        # Create test file
        test_wav = tmp_path / "test_silence.wav"
        pattern = [
            (0.5, 0.8),   # Sound (0-0.5s)
            (0.5, 0.0),   # Silence (0.5-1.0s)
            (0.5, 0.8),   # Sound (1.0-1.5s)
        ]
        
        buf = self.create_test_wav(pattern)
        test_wav.write_bytes(buf.read())
        
        detector = SilenceDetector(threshold_db=-40, min_duration_sec=0.1)
        gaps = detector.detect(str(test_wav))
        
        assert len(gaps) == 1
        assert abs(gaps[0]['start'] - 0.5) < 0.05  # ~0.5s
        assert abs(gaps[0]['end'] - 1.0) < 0.05    # ~1.0s
        assert abs(gaps[0]['duration'] - 0.5) < 0.05
    
    def test_detects_multiple_gaps(self, tmp_path):
        """RED: Should detect multiple silence gaps.
        Pattern: sound-silence-sound-silence-sound
        """
        from silence_detector import SilenceDetector
        
        test_wav = tmp_path / "test_multi.wav"
        pattern = [
            (0.3, 0.8),   # Sound
            (0.4, 0.0),   # Silence 1
            (0.3, 0.8),   # Sound
            (0.4, 0.0),   # Silence 2
            (0.3, 0.8),   # Sound
        ]
        
        buf = self.create_test_wav(pattern)
        test_wav.write_bytes(buf.read())
        
        detector = SilenceDetector(threshold_db=-40, min_duration_sec=0.1)
        gaps = detector.detect(str(test_wav))
        
        assert len(gaps) == 2
    
    def test_ignores_short_silences(self, tmp_path):
        """RED: Should ignore silences below min_duration.
        Pattern: sound-0.1s silence-sound (min=0.3s)
        """
        from silence_detector import SilenceDetector
        
        test_wav = tmp_path / "test_short.wav"
        pattern = [
            (0.5, 0.8),
            (0.1, 0.0),   # Too short
            (0.5, 0.8),
        ]
        
        buf = self.create_test_wav(pattern)
        test_wav.write_bytes(buf.read())
        
        detector = SilenceDetector(threshold_db=-40, min_duration_sec=0.3)
        gaps = detector.detect(str(test_wav))
        
        assert len(gaps) == 0
    
    def test_respects_threshold_db(self, tmp_path):
        """RED: Should only detect below threshold dB.
        Pattern: quiet noise (-60dB) vs true silence
        """
        from silence_detector import SilenceDetector
        
        test_wav = tmp_path / "test_threshold.wav"
        # -60dB amplitude = 0.001
        pattern = [
            (0.3, 0.8),
            (0.3, 0.001),  # Very quiet but not silent
            (0.3, 0.8),
        ]
        
        buf = self.create_test_wav(pattern)
        test_wav.write_bytes(buf.read())
        
        # With -50dB threshold, 0.001 (-60dB) should be detected as silence
        detector = SilenceDetector(threshold_db=-50, min_duration_sec=0.1)
        gaps = detector.detect(str(test_wav))
        
        assert len(gaps) == 1


class TestSilenceDetectorOutput:
    """Tests for output format and metadata."""
    
    def test_output_has_required_fields(self, tmp_path):
        """RED: Output should have start, end, duration fields."""
        from silence_detector import SilenceDetector
        
        test_wav = tmp_path / "test_fields.wav"
        pattern = [(0.3, 0.8), (0.5, 0.0), (0.3, 0.8)]
        
        buf = io.BytesIO()
        sample_rate = 44100
        samples = []
        for duration, amp in pattern:
            num_samples = int(duration * sample_rate)
            samples.extend([amp] * num_samples)
        
        audio_data = np.array(samples, dtype=np.float32)
        audio_data = (audio_data * 32767).astype(np.int16)
        
        with wave.open(buf, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data.tobytes())
        
        buf.seek(0)
        test_wav.write_bytes(buf.read())
        
        detector = SilenceDetector(threshold_db=-40, min_duration_sec=0.1)
        gaps = detector.detect(str(test_wav))
        
        assert len(gaps) > 0
        gap = gaps[0]
        assert 'start' in gap
        assert 'end' in gap
        assert 'duration' in gap
        assert isinstance(gap['start'], float)
        assert isinstance(gap['end'], float)
        assert isinstance(gap['duration'], float)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
