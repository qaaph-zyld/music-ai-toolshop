"""Vocal Cleanup Module for OpenDAW

Automated vocal cleanup that removes:
- Breath sounds between phrases
- Background noise and hiss
- Silent gaps ("close the bridge")

Usage:
    from vocal_cleanup import SilenceDetector, BreathDetector, GapRemover, VocalCleanupPipeline
    
    # Full pipeline
    pipeline = VocalCleanupPipeline(
        silence_threshold_db=-40,
        gap_compress_ratio=0.3
    )
    result = pipeline.process("vocal.wav", "clean_vocal.wav")
    
    # Or use individual components
    detector = SilenceDetector(threshold_db=-40, min_duration_sec=0.3)
    gaps = detector.detect("vocal.wav")
"""

from .silence_detector import SilenceDetector, SilenceConfig
from .breath_detector import BreathDetector, BreathConfig
from .gap_remover import GapRemover, GapRemoverConfig
from .pipeline import VocalCleanupPipeline, PipelineConfig

__version__ = "0.1.0"
__all__ = [
    "SilenceDetector",
    "SilenceConfig",
    "BreathDetector",
    "BreathConfig",
    "GapRemover",
    "GapRemoverConfig",
    "VocalCleanupPipeline",
    "PipelineConfig",
]
