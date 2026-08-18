"""TDD Tests for Gap Remover - Vocal Cleanup Module

Tests MUST fail initially (RED), then pass after implementation (GREEN).
"""

import pytest
import numpy as np
import wave
from pathlib import Path


class TestGapRemoverInitialization:
    """Tests for GapRemover class creation and configuration."""
    
    def test_remover_can_be_created(self):
        """RED: Should create GapRemover with default settings."""
        from gap_remover import GapRemover
        remover = GapRemover()
        assert remover is not None
    
    def test_remover_accepts_compress_ratio(self):
        """RED: Should accept gap compression ratio."""
        from gap_remover import GapRemover
        remover = GapRemover(compress_ratio=0.3)
        assert remover.compress_ratio == 0.3
    
    def test_remover_has_crossfade_setting(self):
        """RED: Should accept crossfade duration."""
        from gap_remover import GapRemover
        remover = GapRemover(crossfade_ms=15)
        assert remover.crossfade_ms == 15
    
    def test_remover_has_default_values(self):
        """RED: Should have sensible defaults."""
        from gap_remover import GapRemover
        remover = GapRemover()
        assert remover.compress_ratio == 0.3  # Keep 30% of gap
        assert remover.crossfade_ms == 10  # 10ms crossfade
        assert remover.min_gap_to_remove == 0.05  # 50ms minimum


class TestGapRemoverWithAudio:
    """Tests for gap removal on actual audio data."""
    
    def create_test_wav_with_gap(self, tmp_path, filename="test_gap.wav"):
        """Helper: Create test WAV with silence gap.
        Pattern: sound - silence - sound
        """
        sample_rate = 44100
        
        # Pattern: 0.5s sound, 0.5s silence, 0.5s sound
        duration_sound = 0.5
        duration_silence = 0.5
        
        t_sound = np.linspace(0, duration_sound, int(duration_sound * sample_rate))
        sound1 = 0.8 * np.sin(2 * np.pi * 440 * t_sound)
        
        silence = np.zeros(int(duration_silence * sample_rate))
        
        t_sound2 = np.linspace(0, duration_sound, int(duration_sound * sample_rate))
        sound2 = 0.8 * np.sin(2 * np.pi * 440 * t_sound2)
        
        audio = np.concatenate([sound1, silence, sound2])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / filename
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        return test_wav, duration_sound * 2 + duration_silence
    
    def test_removes_silence_gap(self, tmp_path):
        """RED: Should remove silence gap and shorten file.
        Original: 1.5s (0.5 + 0.5 + 0.5)
        After: ~1.2s (0.5 + 0.2 + 0.5) with 30% compression
        """
        from gap_remover import GapRemover
        
        test_wav, original_duration = self.create_test_wav_with_gap(tmp_path)
        output_wav = tmp_path / "output.wav"
        
        # Define gap to remove
        gaps = [{'start': 0.5, 'end': 1.0, 'duration': 0.5}]
        
        remover = GapRemover(compress_ratio=0.0)  # 0% = full removal
        remover.process(str(test_wav), str(output_wav), gaps)
        
        # Check output duration is shorter
        with wave.open(str(output_wav), 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            new_duration = frames / rate
        
        # Should be ~1.0s (removed 0.5s gap entirely)
        assert new_duration < original_duration - 0.4
    
    def test_compresses_gap_partially(self, tmp_path):
        """RED: Should compress gap when compress_ratio > 0.
        Original: 1.5s with 0.5s gap
        After 50% compression: ~1.25s (gap becomes 0.25s)
        """
        from gap_remover import GapRemover
        
        test_wav, original_duration = self.create_test_wav_with_gap(tmp_path)
        output_wav = tmp_path / "output_compressed.wav"
        
        gaps = [{'start': 0.5, 'end': 1.0, 'duration': 0.5}]
        
        remover = GapRemover(compress_ratio=0.5)  # Keep 50% of gap
        remover.process(str(test_wav), str(output_wav), gaps)
        
        with wave.open(str(output_wav), 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            new_duration = frames / rate
        
        # Should be between 1.25s and 1.3s (50% of gap removed)
        expected_duration = original_duration - (0.5 * 0.5)  # Remove half the gap
        assert abs(new_duration - expected_duration) < 0.1
    
    def test_removes_multiple_gaps(self, tmp_path):
        """RED: Should remove multiple gaps from file.
        Pattern: sound-gap-sound-gap-sound
        """
        from gap_remover import GapRemover
        
        sample_rate = 44100
        
        # Create audio with 2 gaps
        t = np.linspace(0, 0.4, int(0.4 * sample_rate))
        sound = 0.8 * np.sin(2 * np.pi * 440 * t)
        gap = np.zeros(int(0.4 * sample_rate))
        
        audio = np.concatenate([sound, gap, sound, gap, sound])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_multi_gap.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        original_duration = len(audio) / sample_rate
        output_wav = tmp_path / "output_multi.wav"
        
        gaps = [
            {'start': 0.4, 'end': 0.8, 'duration': 0.4},
            {'start': 1.2, 'end': 1.6, 'duration': 0.4}
        ]
        
        remover = GapRemover(compress_ratio=0.0)
        remover.process(str(test_wav), str(output_wav), gaps)
        
        with wave.open(str(output_wav), 'rb') as wav:
            frames = wav.getnframes()
            new_duration = frames / sample_rate
        
        # Should have removed both gaps (0.8s total)
        assert new_duration < original_duration - 0.7
    
    def test_preserves_audio_quality(self, tmp_path):
        """RED: Should preserve non-silent audio without artifacts.
        Audio before and after gap should be unchanged.
        """
        from gap_remover import GapRemover
        
        sample_rate = 44100
        
        # Create simple sine wave with gap
        t1 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound1 = 0.8 * np.sin(2 * np.pi * 440 * t1)
        gap = np.zeros(int(0.3 * sample_rate))
        t2 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound2 = 0.8 * np.sin(2 * np.pi * 440 * t2)
        
        audio = np.concatenate([sound1, gap, sound2])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_quality.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        output_wav = tmp_path / "output_quality.wav"
        gaps = [{'start': 0.5, 'end': 0.8, 'duration': 0.3}]
        
        remover = GapRemover(compress_ratio=0.0, crossfade_ms=5)
        remover.process(str(test_wav), str(output_wav), gaps)
        
        # Read output and check first part matches original
        with wave.open(str(output_wav), 'rb') as wav:
            output_frames = wav.readframes(wav.getnframes())
            output_audio = np.frombuffer(output_frames, dtype=np.int16)
        
        # First 0.4s should match original (within crossfade region)
        original_start = audio[:int(0.4 * sample_rate)]
        output_start = output_audio[:int(0.4 * sample_rate)]
        
        # Allow for small differences due to crossfade
        correlation = np.corrcoef(original_start.astype(float), output_start.astype(float))[0, 1]
        assert correlation > 0.95  # High correlation = preserved quality
    
    def test_ignores_short_gaps(self, tmp_path):
        """RED: Should not process gaps below min_gap_to_remove.
        Gaps shorter than threshold should be kept unchanged.
        """
        from gap_remover import GapRemover
        
        sample_rate = 44100
        
        # Create audio with short gap (30ms)
        t1 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound1 = 0.8 * np.sin(2 * np.pi * 440 * t1)
        short_gap = np.zeros(int(0.03 * sample_rate))  # 30ms
        t2 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound2 = 0.8 * np.sin(2 * np.pi * 440 * t2)
        
        audio = np.concatenate([sound1, short_gap, sound2])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_short_gap.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        output_wav = tmp_path / "output_short.wav"
        gaps = [{'start': 0.5, 'end': 0.53, 'duration': 0.03}]
        
        remover = GapRemover(min_gap_to_remove=0.05)  # 50ms minimum
        remover.process(str(test_wav), str(output_wav), gaps)
        
        # Duration should be unchanged (short gap kept)
        with wave.open(str(output_wav), 'rb') as wav:
            frames = wav.getnframes()
            new_duration = frames / sample_rate
        
        original_duration = len(audio) / sample_rate
        assert abs(new_duration - original_duration) < 0.02


class TestGapRemoverOutput:
    """Tests for output file format."""
    
    def test_output_is_valid_wav(self, tmp_path):
        """RED: Output should be valid WAV file."""
        from gap_remover import GapRemover
        
        sample_rate = 44100
        t1 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound1 = 0.8 * np.sin(2 * np.pi * 440 * t1)
        gap = np.zeros(int(0.3 * sample_rate))
        t2 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound2 = 0.8 * np.sin(2 * np.pi * 440 * t2)
        
        audio = np.concatenate([sound1, gap, sound2])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_output.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        output_wav = tmp_path / "output_valid.wav"
        gaps = [{'start': 0.5, 'end': 0.8, 'duration': 0.3}]
        
        remover = GapRemover()
        remover.process(str(test_wav), str(output_wav), gaps)
        
        # Verify output is valid WAV
        with wave.open(str(output_wav), 'rb') as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == sample_rate
            assert wav.getnframes() > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
