"""TDD Tests for Breath Detector - Vocal Cleanup Module

Tests MUST fail initially (RED), then pass after implementation (GREEN).
"""

import pytest
import numpy as np
import wave
import io
from pathlib import Path


class TestBreathDetectorInitialization:
    """Tests for BreathDetector class creation and configuration."""
    
    def test_detector_can_be_created(self):
        """RED: Should create BreathDetector with default settings."""
        from breath_detector import BreathDetector
        detector = BreathDetector()
        assert detector is not None
    
    def test_detector_has_sensitivity_setting(self):
        """RED: Should accept sensitivity threshold."""
        from breath_detector import BreathDetector
        detector = BreathDetector(sensitivity=0.7)
        assert detector.sensitivity == 0.7
    
    def test_detector_has_default_values(self):
        """RED: Should have sensible defaults."""
        from breath_detector import BreathDetector
        detector = BreathDetector()
        assert detector.sensitivity == 0.5  # Medium sensitivity
        assert detector.min_breath_duration == 0.1  # 100ms minimum
        assert detector.max_breath_duration == 0.8  # 800ms maximum


class TestBreathDetectorWithAudio:
    """Tests for breath detection on actual audio data."""
    
    def create_test_wav_with_breath(self, tmp_path, filename="test_breath.wav"):
        """Helper: Create test WAV with breath-like characteristics.
        
        Breath characteristics:
        - Low spectral centroid (low frequency content)
        - High zero-crossing rate (noise-like)
        - Short duration (100-500ms)
        - Lower amplitude than speech
        """
        sample_rate = 44100
        
        # Pattern: speech - breath - speech
        # Breath = filtered noise (low freq + high ZCR)
        duration_speech1 = 0.5
        duration_breath = 0.3
        duration_speech2 = 0.5
        
        # Generate speech-like signal (harmonic)
        t1 = np.linspace(0, duration_speech1, int(duration_speech1 * sample_rate))
        speech1 = 0.6 * np.sin(2 * np.pi * 200 * t1) + 0.3 * np.sin(2 * np.pi * 400 * t1)
        
        # Generate breath-like signal (filtered noise, low amplitude)
        t_breath = np.linspace(0, duration_breath, int(duration_breath * sample_rate))
        breath = 0.15 * np.random.randn(len(t_breath))  # Low amplitude noise
        # Low-pass filter approximation (simple averaging)
        breath = np.convolve(breath, np.ones(10)/10, mode='same')
        
        # Generate more speech
        t2 = np.linspace(0, duration_speech2, int(duration_speech2 * sample_rate))
        speech2 = 0.6 * np.sin(2 * np.pi * 200 * t2)
        
        # Concatenate
        audio = np.concatenate([speech1, breath, speech2])
        audio = (audio * 32767).astype(np.int16)
        
        # Write WAV
        test_wav = tmp_path / filename
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        return test_wav
    
    def test_detects_breath_segment(self, tmp_path):
        """RED: Should detect breath segment between speech.
        Pattern: speech - breath - speech
        """
        from breath_detector import BreathDetector
        
        test_wav = self.create_test_wav_with_breath(tmp_path)
        
        detector = BreathDetector(sensitivity=0.5)
        breaths = detector.detect(str(test_wav))
        
        assert len(breaths) >= 1
        # Should find breath around 0.5s
        breath = breaths[0]
        assert abs(breath['start'] - 0.5) < 0.15  # ~0.5s
        assert abs(breath['end'] - 0.8) < 0.15    # ~0.8s
    
    def test_breath_has_confidence_score(self, tmp_path):
        """RED: Should return confidence score for breath detection."""
        from breath_detector import BreathDetector
        
        test_wav = self.create_test_wav_with_breath(tmp_path)
        
        detector = BreathDetector(sensitivity=0.5)
        breaths = detector.detect(str(test_wav))
        
        assert len(breaths) > 0
        assert 'confidence' in breaths[0]
        assert 0.0 <= breaths[0]['confidence'] <= 1.0
    
    def test_breath_has_type_field(self, tmp_path):
        """RED: Should identify segment type as 'breath'."""
        from breath_detector import BreathDetector
        
        test_wav = self.create_test_wav_with_breath(tmp_path)
        
        detector = BreathDetector()
        breaths = detector.detect(str(test_wav))
        
        assert len(breaths) > 0
        assert breaths[0]['type'] == 'breath'
    
    def test_does_not_detect_speech_as_breath(self, tmp_path):
        """RED: Should not detect pure speech as breath.
        Pattern: continuous speech
        """
        from breath_detector import BreathDetector
        
        sample_rate = 44100
        duration = 1.5
        t = np.linspace(0, duration, int(duration * sample_rate))
        # Pure harmonic speech (no breath characteristics)
        speech = 0.7 * np.sin(2 * np.pi * 200 * t) + 0.3 * np.sin(2 * np.pi * 600 * t)
        speech = (speech * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_speech_only.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(speech.tobytes())
        
        detector = BreathDetector(sensitivity=0.5)
        breaths = detector.detect(str(test_wav))
        
        assert len(breaths) == 0
    
    def test_detects_multiple_breaths(self, tmp_path):
        """RED: Should detect multiple breath segments.
        Pattern: speech - breath - speech - breath - speech
        """
        from breath_detector import BreathDetector
        
        sample_rate = 44100
        
        # Create pattern with 2 breaths
        t1 = np.linspace(0, 0.4, int(0.4 * sample_rate))
        speech1 = 0.6 * np.sin(2 * np.pi * 200 * t1)
        
        t_b1 = np.linspace(0, 0.25, int(0.25 * sample_rate))
        breath1 = 0.12 * np.random.randn(len(t_b1))
        breath1 = np.convolve(breath1, np.ones(10)/10, mode='same')
        
        t2 = np.linspace(0, 0.4, int(0.4 * sample_rate))
        speech2 = 0.6 * np.sin(2 * np.pi * 200 * t2)
        
        t_b2 = np.linspace(0, 0.25, int(0.25 * sample_rate))
        breath2 = 0.12 * np.random.randn(len(t_b2))
        breath2 = np.convolve(breath2, np.ones(10)/10, mode='same')
        
        t3 = np.linspace(0, 0.4, int(0.4 * sample_rate))
        speech3 = 0.6 * np.sin(2 * np.pi * 200 * t3)
        
        audio = np.concatenate([speech1, breath1, speech2, breath2, speech3])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_multi_breath.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        detector = BreathDetector(sensitivity=0.4)
        breaths = detector.detect(str(test_wav))
        
        assert len(breaths) == 2


class TestBreathDetectorOutput:
    """Tests for output format and metadata."""
    
    def test_output_has_required_fields(self, tmp_path):
        """RED: Output should have all required fields."""
        from breath_detector import BreathDetector
        
        sample_rate = 44100
        t1 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        speech = 0.6 * np.sin(2 * np.pi * 200 * t1)
        
        t_b = np.linspace(0, 0.3, int(0.3 * sample_rate))
        breath = 0.15 * np.random.randn(len(t_b))
        breath = np.convolve(breath, np.ones(10)/10, mode='same')
        
        audio = np.concatenate([speech, breath, speech])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_fields.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        detector = BreathDetector()
        breaths = detector.detect(str(test_wav))
        
        assert len(breaths) > 0
        breath = breaths[0]
        required_fields = ['start', 'end', 'duration', 'type', 'confidence']
        for field in required_fields:
            assert field in breath, f"Missing field: {field}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
