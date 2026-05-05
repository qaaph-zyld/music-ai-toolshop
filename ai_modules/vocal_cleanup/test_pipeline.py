"""TDD Tests for Vocal Cleanup Pipeline - Integration Tests

Tests the full pipeline: Silence Detection -> Breath Detection -> Gap Removal -> Output
"""

import pytest
import numpy as np
import wave
from pathlib import Path


class TestVocalCleanupPipeline:
    """Integration tests for the full vocal cleanup pipeline."""
    
    def create_test_vocal_with_gaps_and_breath(self, tmp_path):
        """Helper: Create realistic test vocal with gaps and breath sounds.
        Pattern: speech - breath - silence - speech
        """
        sample_rate = 44100
        
        # Speech segment 1 (0.6s harmonic content)
        t1 = np.linspace(0, 0.6, int(0.6 * sample_rate))
        speech1 = 0.7 * np.sin(2 * np.pi * 220 * t1) + 0.3 * np.sin(2 * np.pi * 440 * t1)
        
        # Breath (0.25s filtered noise, low amplitude)
        t_breath = np.linspace(0, 0.25, int(0.25 * sample_rate))
        breath = 0.12 * np.random.randn(len(t_breath))
        breath = np.convolve(breath, np.ones(10)/10, mode='same')
        
        # Silence gap (0.5s)
        silence = np.zeros(int(0.5 * sample_rate))
        
        # Speech segment 2
        t2 = np.linspace(0, 0.6, int(0.6 * sample_rate))
        speech2 = 0.7 * np.sin(2 * np.pi * 220 * t2) + 0.3 * np.sin(2 * np.pi * 440 * t2)
        
        audio = np.concatenate([speech1, breath, silence, speech2])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_vocal.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        original_duration = len(audio) / sample_rate
        return test_wav, original_duration
    
    def test_pipeline_end_to_end(self, tmp_path):
        """RED: Full pipeline should process vocal and produce cleaned output."""
        from pipeline import VocalCleanupPipeline
        
        test_wav, original_duration = self.create_test_vocal_with_gaps_and_breath(tmp_path)
        output_wav = tmp_path / "output_clean.wav"
        
        pipeline = VocalCleanupPipeline(
            silence_threshold_db=-40,
            silence_min_duration=0.2,
            gap_compress_ratio=0.2,
            breath_sensitivity=0.5
        )
        
        result = pipeline.process(str(test_wav), str(output_wav))
        
        # Verify output file exists
        assert output_wav.exists()
        
        # Verify output is shorter (gaps removed)
        with wave.open(str(output_wav), 'rb') as wav:
            output_duration = wav.getnframes() / wav.getframerate()
        
        assert output_duration < original_duration
        
        # Verify result metadata
        assert 'gaps_detected' in result
        assert 'breaths_detected' in result
        assert 'original_duration' in result
        assert 'output_duration' in result
    
    def test_pipeline_detects_silence_and_breath(self, tmp_path):
        """RED: Pipeline should detect both silence gaps and breath segments."""
        from pipeline import VocalCleanupPipeline
        
        test_wav, _ = self.create_test_vocal_with_gaps_and_breath(tmp_path)
        output_wav = tmp_path / "output_detected.wav"
        
        pipeline = VocalCleanupPipeline()
        result = pipeline.process(str(test_wav), str(output_wav))
        
        # Should detect at least 1 gap (the silence)
        assert result['gaps_detected'] >= 1
        
        # Should detect at least 1 breath
        assert result['breaths_detected'] >= 1
    
    def test_pipeline_respects_settings(self, tmp_path):
        """RED: Pipeline should respect user settings for compression."""
        from pipeline import VocalCleanupPipeline
        
        test_wav, original_duration = self.create_test_vocal_with_gaps_and_breath(tmp_path)
        
        # Test with aggressive compression
        output_aggressive = tmp_path / "output_aggressive.wav"
        pipeline1 = VocalCleanupPipeline(gap_compress_ratio=0.0)
        result1 = pipeline1.process(str(test_wav), str(output_aggressive))
        
        # Test with gentle compression
        output_gentle = tmp_path / "output_gentle.wav"
        pipeline2 = VocalCleanupPipeline(gap_compress_ratio=0.7)
        result2 = pipeline2.process(str(test_wav), str(output_gentle))
        
        # Aggressive should be shorter than gentle
        assert result1['output_duration'] < result2['output_duration']
    
    def test_pipeline_preserves_audio_format(self, tmp_path):
        """RED: Output should match input format (sample rate, bit depth)."""
        from pipeline import VocalCleanupPipeline
        
        test_wav, _ = self.create_test_vocal_with_gaps_and_breath(tmp_path)
        output_wav = tmp_path / "output_format.wav"
        
        # Get input format
        with wave.open(str(test_wav), 'rb') as wav:
            input_channels = wav.getnchannels()
            input_width = wav.getsampwidth()
            input_rate = wav.getframerate()
        
        pipeline = VocalCleanupPipeline()
        pipeline.process(str(test_wav), str(output_wav))
        
        # Verify output format matches
        with wave.open(str(output_wav), 'rb') as wav:
            assert wav.getnchannels() == input_channels
            assert wav.getsampwidth() == input_width
            assert wav.getframerate() == input_rate
    
    def test_pipeline_handles_no_gaps(self, tmp_path):
        """RED: Should handle clean audio without gaps gracefully."""
        from pipeline import VocalCleanupPipeline
        
        sample_rate = 44100
        
        # Create audio with no gaps or breaths
        t = np.linspace(0, 1.0, int(1.0 * sample_rate))
        clean_audio = 0.7 * np.sin(2 * np.pi * 440 * t)
        clean_audio = (clean_audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_clean.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(clean_audio.tobytes())
        
        output_wav = tmp_path / "output_clean.wav"
        pipeline = VocalCleanupPipeline()
        result = pipeline.process(str(test_wav), str(output_wav))
        
        # Should complete without errors
        assert output_wav.exists()
        assert result['gaps_detected'] == 0
        assert result['breaths_detected'] == 0
    
    def test_pipeline_progress_callback(self, tmp_path):
        """RED: Should call progress callback during processing."""
        from pipeline import VocalCleanupPipeline
        
        test_wav, _ = self.create_test_vocal_with_gaps_and_breath(tmp_path)
        output_wav = tmp_path / "output_progress.wav"
        
        progress_calls = []
        
        def on_progress(stage, percent):
            progress_calls.append((stage, percent))
        
        pipeline = VocalCleanupPipeline()
        pipeline.process(str(test_wav), str(output_wav), progress_callback=on_progress)
        
        # Should have received progress updates
        assert len(progress_calls) > 0
        # First call should be early stage
        assert progress_calls[0][1] >= 0
        # Last call should be complete
        assert progress_calls[-1][1] == 100


class TestPipelineResultFormat:
    """Tests for pipeline result format."""
    
    def test_result_contains_gap_details(self, tmp_path):
        """RED: Result should include details about detected gaps."""
        from pipeline import VocalCleanupPipeline
        
        sample_rate = 44100
        
        # Create simple gap
        t1 = np.linspace(0, 0.4, int(0.4 * sample_rate))
        sound1 = 0.7 * np.sin(2 * np.pi * 440 * t1)
        gap = np.zeros(int(0.4 * sample_rate))
        t2 = np.linspace(0, 0.4, int(0.4 * sample_rate))
        sound2 = 0.7 * np.sin(2 * np.pi * 440 * t2)
        
        audio = np.concatenate([sound1, gap, sound2])
        audio = (audio * 32767).astype(np.int16)
        
        test_wav = tmp_path / "test_result.wav"
        with wave.open(str(test_wav), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        output_wav = tmp_path / "output_result.wav"
        pipeline = VocalCleanupPipeline()
        result = pipeline.process(str(test_wav), str(output_wav))
        
        assert 'gaps' in result
        assert isinstance(result['gaps'], list)
        
        if len(result['gaps']) > 0:
            gap = result['gaps'][0]
            assert 'start' in gap
            assert 'end' in gap
            assert 'duration' in gap


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
