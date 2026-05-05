"""Vocal Cleanup Pipeline

Full processing pipeline that combines:
1. Silence Detection - Find gaps between phrases
2. Breath Detection - Identify breath sounds
3. Gap Removal - Remove/compress gaps to "close the bridge"

Usage:
    from pipeline import VocalCleanupPipeline
    
    pipeline = VocalCleanupPipeline(
        silence_threshold_db=-40,
        gap_compress_ratio=0.3
    )
    
    result = pipeline.process("input.wav", "output_clean.wav")
    print(f"Removed {result['time_removed']:.2f}s of gaps")
"""

from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from silence_detector import SilenceDetector
from breath_detector import BreathDetector
from gap_remover import GapRemover


@dataclass
class PipelineConfig:
    """Configuration for vocal cleanup pipeline."""
    silence_threshold_db: float = -40.0
    silence_min_duration: float = 0.2
    silence_padding_sec: float = 0.01
    gap_compress_ratio: float = 0.3
    gap_crossfade_ms: float = 10.0
    gap_min_to_remove: float = 0.05
    breath_sensitivity: float = 0.5
    breath_min_duration: float = 0.1
    breath_max_duration: float = 0.8


class VocalCleanupPipeline:
    """Complete vocal cleanup pipeline.
    
    Orchestrates silence detection, breath detection, and gap removal
    to produce cleaned vocal tracks with tightened timing.
    """
    
    def __init__(self,
                 silence_threshold_db: float = -40.0,
                 silence_min_duration: float = 0.2,
                 gap_compress_ratio: float = 0.3,
                 gap_crossfade_ms: float = 10.0,
                 breath_sensitivity: float = 0.5,
                 silence_padding_sec: float = 0.01,
                 gap_min_to_remove: float = 0.05,
                 breath_min_duration: float = 0.1,
                 breath_max_duration: float = 0.8):
        self.config = PipelineConfig(
            silence_threshold_db=silence_threshold_db,
            silence_min_duration=silence_min_duration,
            silence_padding_sec=silence_padding_sec,
            gap_compress_ratio=gap_compress_ratio,
            gap_crossfade_ms=gap_crossfade_ms,
            gap_min_to_remove=gap_min_to_remove,
            breath_sensitivity=breath_sensitivity,
            breath_min_duration=breath_min_duration,
            breath_max_duration=breath_max_duration
        )
        
        # Initialize detectors
        self.silence_detector = SilenceDetector(
            threshold_db=self.config.silence_threshold_db,
            min_duration_sec=self.config.silence_min_duration,
            padding_sec=self.config.silence_padding_sec
        )
        
        self.breath_detector = BreathDetector(
            sensitivity=self.config.breath_sensitivity,
            min_breath_duration=self.config.breath_min_duration,
            max_breath_duration=self.config.breath_max_duration
        )
        
        self.gap_remover = GapRemover(
            compress_ratio=self.config.gap_compress_ratio,
            crossfade_ms=self.config.gap_crossfade_ms,
            min_gap_to_remove=self.config.gap_min_to_remove
        )
    
    def process(self, input_path: str, output_path: str,
                progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """Process audio file through full pipeline.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output cleaned audio
            progress_callback: Optional callback(stage, percent)
            
        Returns:
            Dictionary with processing results and metadata
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Get original duration
        import wave
        with wave.open(str(input_path), 'rb') as wav:
            original_duration = wav.getnframes() / wav.getframerate()
        
        # Stage 1: Silence Detection
        if progress_callback:
            progress_callback("detecting_silence", 0)
        
        gaps = self.silence_detector.detect(str(input_path))
        
        if progress_callback:
            progress_callback("detecting_silence", 50)
        
        # Stage 2: Breath Detection
        breaths = self.breath_detector.detect(str(input_path))
        
        if progress_callback:
            progress_callback("detecting_breath", 100)
        
        # Stage 3: Gap Removal
        if progress_callback:
            progress_callback("removing_gaps", 0)
        
        self.gap_remover.process(str(input_path), str(output_path), gaps)
        
        if progress_callback:
            progress_callback("removing_gaps", 100)
        
        # Get output duration
        with wave.open(str(output_path), 'rb') as wav:
            output_duration = wav.getnframes() / wav.getframerate()
        
        # Calculate time removed
        time_removed = original_duration - output_duration
        
        # Build result
        result = {
            'gaps_detected': len(gaps),
            'breaths_detected': len(breaths),
            'original_duration': round(original_duration, 3),
            'output_duration': round(output_duration, 3),
            'time_removed': round(time_removed, 3),
            'gaps': gaps,
            'breaths': breaths,
            'input_file': str(input_path),
            'output_file': str(output_path),
        }
        
        return result
    
    def preview(self, input_path: str) -> Dict[str, Any]:
        """Preview what would be done without processing.
        
        Args:
            input_path: Path to input audio file
            
        Returns:
            Dictionary with detection results only (no processing)
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        import wave
        with wave.open(str(input_path), 'rb') as wav:
            original_duration = wav.getnframes() / wav.getframerate()
        
        # Detect only
        gaps = self.silence_detector.detect(str(input_path))
        breaths = self.breath_detector.detect(str(input_path))
        
        # Estimate time that would be removed
        total_gap_time = sum(gap['duration'] for gap in gaps)
        time_removed = total_gap_time * (1 - self.config.gap_compress_ratio)
        estimated_output = original_duration - time_removed
        
        return {
            'gaps_detected': len(gaps),
            'breaths_detected': len(breaths),
            'original_duration': round(original_duration, 3),
            'estimated_output_duration': round(estimated_output, 3),
            'estimated_time_removed': round(time_removed, 3),
            'gaps': gaps,
            'breaths': breaths,
        }


if __name__ == '__main__':
    # Test run
    import tempfile
    import numpy as np
    import wave
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sample_rate = 44100
        
        # Create test audio with gap
        t1 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound1 = 0.8 * np.sin(2 * np.pi * 440 * t1)
        gap = np.zeros(int(0.5 * sample_rate))
        t2 = np.linspace(0, 0.5, int(0.5 * sample_rate))
        sound2 = 0.8 * np.sin(2 * np.pi * 440 * t2)
        
        audio = np.concatenate([sound1, gap, sound2])
        audio = (audio * 32767).astype(np.int16)
        
        with wave.open(f.name, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio.tobytes())
        
        input_file = f.name
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        output_file = f.name
    
    # Test pipeline
    pipeline = VocalCleanupPipeline(
        silence_threshold_db=-40,
        silence_min_duration=0.1,
        gap_compress_ratio=0.0
    )
    
    def on_progress(stage, percent):
        print(f"  {stage}: {percent}%")
    
    print("Preview:")
    preview = pipeline.preview(input_file)
    print(f"  Gaps: {preview['gaps_detected']}")
    print(f"  Breaths: {preview['breaths_detected']}")
    print(f"  Est. time removed: {preview['estimated_time_removed']:.3f}s")
    
    print("\nProcessing:")
    result = pipeline.process(input_file, output_file, on_progress)
    print(f"  Original: {result['original_duration']:.3f}s")
    print(f"  Output: {result['output_duration']:.3f}s")
    print(f"  Time removed: {result['time_removed']:.3f}s")
    
    # Cleanup
    Path(input_file).unlink()
    Path(output_file).unlink()
